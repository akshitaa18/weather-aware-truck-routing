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
