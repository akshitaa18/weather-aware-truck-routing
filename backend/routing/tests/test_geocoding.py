"""
Tests for Geocoding Service.
Covers:
- Empty query validation
- Cache hit without external HTTP call
- Nominatim <= 1 req/sec rate-limiting enforcement
- Graceful fallback on HTTP 429/403 without immediate retry
- Configurable GEOCODING_PROVIDER ('photon' vs 'nominatim')
"""

import time
import pytest
from unittest.mock import patch, MagicMock
from routing.services.geocoding import (
    geocode_location,
    geocode_locations_concurrent,
    _GEOCODE_CACHE,
    _query_nominatim,
    _query_photon,
)


class TestGeocodingService:
    def setup_method(self):
        _GEOCODE_CACHE.clear()

    def test_empty_query_raises_value_error(self):
        with pytest.raises(ValueError) as excinfo:
            geocode_location("   ")
        assert "cannot be empty" in str(excinfo.value)

    def test_cache_hit_returns_immediately(self):
        _GEOCODE_CACHE["chicago, il"] = {
            "query": "Chicago, IL",
            "name": "Chicago, Illinois, USA",
            "latitude": 41.8781,
            "longitude": -87.6298,
        }
        with patch("routing.services.geocoding._query_photon") as mock_photon:
            with patch("routing.services.geocoding._query_nominatim") as mock_nom:
                res = geocode_location("Chicago, IL")
                assert res["latitude"] == 41.8781
                assert mock_photon.call_count == 0
                assert mock_nom.call_count == 0

    @patch("routing.services.geocoding._SESSION.get")
    def test_nominatim_rate_limiting_enforces_one_sec_delay(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"lat": "41.8781", "lon": "-87.6298", "display_name": "Chicago"}]
        mock_get.return_value = mock_resp

        start = time.time()
        _query_nominatim("Chicago, IL")
        _query_nominatim("Detroit, MI")
        elapsed = time.time() - start

        # Two consecutive Nominatim queries must take at least 1.0 second due to rate limiting
        assert elapsed >= 1.0

    @patch("routing.services.geocoding._SESSION.get")
    def test_nominatim_429_falls_back_to_photon_without_retry(self, mock_get):
        # First call to Nominatim returns HTTP 429
        nom_resp = MagicMock()
        nom_resp.status_code = 429

        # Fallback call to Photon returns HTTP 200
        photon_resp = MagicMock()
        photon_resp.status_code = 200
        photon_resp.json.return_value = {
            "features": [
                {
                    "geometry": {"coordinates": [-83.0458, 42.3314]},
                    "properties": {"name": "Detroit", "state": "Michigan", "country": "USA"}
                }
            ]
        }

        mock_get.side_effect = [nom_resp, photon_resp]

        with patch.dict("os.environ", {"GEOCODING_PROVIDER": "nominatim"}):
            res = geocode_location("Detroit, MI")
            assert res["latitude"] == 42.3314
            assert res["longitude"] == -83.0458
            assert "Detroit" in res["name"]

    @patch("routing.services.geocoding._SESSION.get")
    def test_default_provider_uses_photon_first(self, mock_get):
        photon_resp = MagicMock()
        photon_resp.status_code = 200
        photon_resp.json.return_value = {
            "features": [
                {
                    "geometry": {"coordinates": [-87.6298, 41.8781]},
                    "properties": {"name": "Chicago", "state": "Illinois", "country": "USA"}
                }
            ]
        }
        mock_get.return_value = photon_resp

        with patch.dict("os.environ", {"GEOCODING_PROVIDER": "photon"}):
            res = geocode_location("Chicago, IL")
            assert res["latitude"] == 41.8781
            assert mock_get.call_count == 1
            # Verified that Photon URL was queried
            assert "photon.komoot.io" in mock_get.call_args[0][0]
