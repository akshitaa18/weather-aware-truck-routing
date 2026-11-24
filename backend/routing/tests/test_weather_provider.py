"""
Tests for Weather Provider (Open-Meteo Integration).
Covers:
- Hourly timeline preserving missing rain/snow as None (never converting to 0.0).
- ETA-based checkpoint forecast preserving missing rain/snow as None.
- Forecast availability being False when any required measurement (wind, rain, or snow) is missing.
- Ensuring a forecast is never marked complete just because wind data exists.
"""

import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from routing.services.weather_provider import (
    OpenMeteoWeatherProvider,
    _WEATHER_CACHE,
    cache_key,
)


class TestOpenMeteoWeatherProvider:
    def setup_method(self):
        _WEATHER_CACHE.clear()

    @patch.object(OpenMeteoWeatherProvider, "_fetch_batch")
    def test_partial_missing_precipitation_and_snow_preserved_as_none_and_unavailable(self, mock_fetch):
        lat, lon = 41.8781, -87.6298
        ck = cache_key(lat, lon)

        # Generate 49 hours of timestamps matching departure time + offsets
        base_dt = datetime(2026, 11, 24, 8, 0, tzinfo=timezone.utc)
        times = [(base_dt + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(49)]

        # Open-Meteo returns wind data, but precipitation and snowfall are None
        _WEATHER_CACHE[ck] = {
            "time": times,
            "windspeed_10m": [18.5] * len(times),
            "precipitation": [None] * len(times),  # Missing precipitation
            "snowfall": [None] * len(times),       # Missing snowfall
            "temperature_2m": [10.0] * len(times),
        }

        provider = OpenMeteoWeatherProvider()
        checkpoints = [
            {
                "id": "cp_0",
                "latitude": lat,
                "longitude": lon,
                "forecast_lookup_hour": "2026-11-24T08:00",
            }
        ]

        enriched = provider.fetch_weather_for_checkpoints(
            checkpoints=checkpoints,
            departure_time_utc_iso="2026-11-24T08:00:00+00:00",
        )

        cp = enriched[0]
        # Checkpoint ETA weather: wind exists, but rain and snow are None
        assert cp["wind_speed_mph"] == 18.5
        assert cp["rain_intensity_in_hr"] is None  # Must NOT be 0.0!
        assert cp["snow_intensity_in_hr"] is None  # Must NOT be 0.0!
        assert cp["forecast_available"] is False   # Must NOT be marked complete just because wind exists!

        # Hourly timeline
        timeline = cp["hourly_timeline"]
        assert len(timeline) == 49
        for entry in timeline:
            assert entry["wind_speed_mph"] == 18.5
            assert entry["rain_intensity_in_hr"] is None  # Preserved as None, not 0.0
            assert entry["snow_intensity_in_hr"] is None  # Preserved as None, not 0.0
            assert entry["forecast_available"] is False

    @patch.object(OpenMeteoWeatherProvider, "_fetch_batch")
    def test_wind_and_rain_available_snow_missing(self, mock_fetch):
        lat, lon = 41.8781, -87.6298
        ck = cache_key(lat, lon)

        base_dt = datetime(2026, 11, 24, 8, 0, tzinfo=timezone.utc)
        times = [(base_dt + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(49)]

        # Wind and rain exist, but snowfall is None
        _WEATHER_CACHE[ck] = {
            "time": times,
            "windspeed_10m": [15.0] * len(times),
            "precipitation": [0.25] * len(times),
            "snowfall": [None] * len(times),
            "temperature_2m": [5.0] * len(times),
        }

        provider = OpenMeteoWeatherProvider()
        checkpoints = [
            {
                "id": "cp_0",
                "latitude": lat,
                "longitude": lon,
                "forecast_lookup_hour": "2026-11-24T08:00",
            }
        ]

        enriched = provider.fetch_weather_for_checkpoints(
            checkpoints=checkpoints,
            departure_time_utc_iso="2026-11-24T08:00:00+00:00",
        )

        cp = enriched[0]
        assert cp["wind_speed_mph"] == 15.0
        assert cp["rain_intensity_in_hr"] == 0.25
        assert cp["snow_intensity_in_hr"] is None
        assert cp["forecast_available"] is False

        entry_0 = cp["hourly_timeline"][0]
        assert entry_0["wind_speed_mph"] == 15.0
        assert entry_0["rain_intensity_in_hr"] == 0.25
        assert entry_0["snow_intensity_in_hr"] is None
        assert entry_0["forecast_available"] is False

    @patch.object(OpenMeteoWeatherProvider, "_fetch_batch")
    def test_all_measurements_available_yields_forecast_available_true(self, mock_fetch):
        lat, lon = 41.8781, -87.6298
        ck = cache_key(lat, lon)

        base_dt = datetime(2026, 11, 24, 8, 0, tzinfo=timezone.utc)
        times = [(base_dt + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(49)]

        _WEATHER_CACHE[ck] = {
            "time": times,
            "windspeed_10m": [15.0] * len(times),
            "precipitation": [0.05] * len(times),
            "snowfall": [0.0] * len(times),
            "temperature_2m": [5.0] * len(times),
        }

        provider = OpenMeteoWeatherProvider()
        checkpoints = [
            {
                "id": "cp_0",
                "latitude": lat,
                "longitude": lon,
                "forecast_lookup_hour": "2026-11-24T08:00",
            }
        ]

        enriched = provider.fetch_weather_for_checkpoints(
            checkpoints=checkpoints,
            departure_time_utc_iso="2026-11-24T08:00:00+00:00",
        )

        cp = enriched[0]
        assert cp["wind_speed_mph"] == 15.0
        assert cp["rain_intensity_in_hr"] == 0.05
        assert cp["snow_intensity_in_hr"] == 0.0
        assert cp["forecast_available"] is True
        assert cp["hourly_timeline"][0]["forecast_available"] is True

    def test_ttl_cache_expiration_and_retrieval(self):
        import time
        from routing.services.weather_provider import get_cached_weather

        lat, lon = 40.0, -75.0
        ck = cache_key(lat, lon)

        # Fresh cache entry
        _WEATHER_CACHE[ck] = {
            "data": {"time": ["2026-11-24T08:00"], "windspeed_10m": [12.0]},
            "timestamp": time.time(),
        }
        assert get_cached_weather(ck) is not None
        assert get_cached_weather(ck)["windspeed_10m"] == [12.0]

        # Expired cache entry (older than 900 seconds)
        _WEATHER_CACHE[ck] = {
            "data": {"time": ["2026-11-24T08:00"], "windspeed_10m": [12.0]},
            "timestamp": time.time() - 950,
        }
        assert get_cached_weather(ck) is None
        assert ck not in _WEATHER_CACHE

    @patch.object(OpenMeteoWeatherProvider, "_fetch_batch")
    def test_prefetch_weather_for_multiple_routes_deduplicates(self, mock_fetch):
        # 3 routes sharing the origin and destination coordinates
        common_origin = (41.8781, -87.6298)
        common_dest = (42.3314, -83.0458)
        waypoint_1 = (41.9, -86.0)
        waypoint_2 = (42.0, -85.0)

        route_1_cps = [
            {"id": "r1_cp0", "latitude": common_origin[0], "longitude": common_origin[1]},
            {"id": "r1_cp1", "latitude": waypoint_1[0], "longitude": waypoint_1[1]},
            {"id": "r1_cp2", "latitude": common_dest[0], "longitude": common_dest[1]},
        ]
        route_2_cps = [
            {"id": "r2_cp0", "latitude": common_origin[0], "longitude": common_origin[1]},
            {"id": "r2_cp1", "latitude": waypoint_2[0], "longitude": waypoint_2[1]},
            {"id": "r2_cp2", "latitude": common_dest[0], "longitude": common_dest[1]},
        ]

        provider = OpenMeteoWeatherProvider()
        provider.prefetch_weather_for_multiple_routes([route_1_cps, route_2_cps])

        # Total 6 checkpoints, but only 4 unique coordinates
        assert mock_fetch.call_count == 1
        fetched_coords = mock_fetch.call_args[0][0]
        assert len(fetched_coords) == 4

    @patch.object(OpenMeteoWeatherProvider, "_fetch_batch")
    def test_snowfall_alone_does_not_trigger_rain_risk(self, mock_fetch):
        # Heavy snow (2.5 in/hr), no rain or showers (0.0)
        lat, lon = 41.8781, -87.6298
        ck = cache_key(lat, lon)

        base_dt = datetime(2026, 11, 24, 8, 0, tzinfo=timezone.utc)
        times = [(base_dt + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(49)]

        _WEATHER_CACHE[ck] = {
            "time": times,
            "windspeed_10m": [12.0] * len(times),
            "rain": [0.0] * len(times),
            "showers": [0.0] * len(times),
            "snowfall": [2.5] * len(times),
            "temperature_2m": [-2.0] * len(times),
        }

        provider = OpenMeteoWeatherProvider()
        checkpoints = [
            {
                "id": "cp_snow",
                "latitude": lat,
                "longitude": lon,
                "forecast_lookup_hour": "2026-11-24T08:00",
            }
        ]

        enriched = provider.fetch_weather_for_checkpoints(
            checkpoints=checkpoints,
            departure_time_utc_iso="2026-11-24T08:00:00+00:00",
        )

        cp = enriched[0]
        # Liquid rain must be 0.0, NOT elevated by snow!
        assert cp["rain_intensity_in_hr"] == 0.0
        assert cp["snow_intensity_in_hr"] == 2.5
        assert cp["forecast_available"] is True

        # Now evaluate risk
        from routing.services.risk_engine import evaluate_checkpoint_risk, RISK_LOW, RISK_SEVERE
        risk = evaluate_checkpoint_risk(
            cp["wind_speed_mph"],
            cp["rain_intensity_in_hr"],
            cp["snow_intensity_in_hr"],
            30000.0,
            forecast_available=cp["forecast_available"]
        )
        assert risk["rain_risk"] == RISK_LOW  # Rain risk is Low!
        assert risk["snow_risk"] == RISK_SEVERE  # Snow risk is Severe
        assert risk["final_risk"] == RISK_SEVERE

    @patch.object(OpenMeteoWeatherProvider, "_fetch_batch")
    def test_liquid_rain_sums_rain_and_showers(self, mock_fetch):
        # rain=0.35, showers=0.25 -> total liquid rain = 0.60 in/hr (Severe)
        lat, lon = 41.8781, -87.6298
        ck = cache_key(lat, lon)

        base_dt = datetime(2026, 11, 24, 8, 0, tzinfo=timezone.utc)
        times = [(base_dt + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(49)]

        _WEATHER_CACHE[ck] = {
            "time": times,
            "windspeed_10m": [10.0] * len(times),
            "rain": [0.35] * len(times),
            "showers": [0.25] * len(times),
            "snowfall": [0.0] * len(times),
            "temperature_2m": [15.0] * len(times),
        }

        provider = OpenMeteoWeatherProvider()
        checkpoints = [
            {
                "id": "cp_rain_sum",
                "latitude": lat,
                "longitude": lon,
                "forecast_lookup_hour": "2026-11-24T08:00",
            }
        ]

        enriched = provider.fetch_weather_for_checkpoints(
            checkpoints=checkpoints,
            departure_time_utc_iso="2026-11-24T08:00:00+00:00",
        )

        cp = enriched[0]
        assert cp["rain_intensity_in_hr"] == 0.60
        assert cp["snow_intensity_in_hr"] == 0.0

        from routing.services.risk_engine import evaluate_checkpoint_risk, RISK_SEVERE
        risk = evaluate_checkpoint_risk(
            cp["wind_speed_mph"],
            cp["rain_intensity_in_hr"],
            cp["snow_intensity_in_hr"],
            30000.0,
        )
        assert risk["rain_risk"] == RISK_SEVERE

