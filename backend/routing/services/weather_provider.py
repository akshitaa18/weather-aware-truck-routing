"""
Weather Provider Service.

Fetches accurate hourly weather forecasts using Open-Meteo API.
Batches coordinate requests, caches results, normalizes units (mph, in/hr),
and attaches hourly weather predictions matching checkpoint ETAs.
"""

import math
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# In-memory weather cache: (rounded_lat, rounded_lon) -> hourly_forecast_dict
_WEATHER_CACHE: Dict[str, Dict[str, Any]] = {}


def cache_key(lat: float, lon: float) -> str:
    """Round coordinates to 2 decimal places (~1.1 km) for caching."""
    return f"{round(lat, 2)}_{round(lon, 2)}"


class WeatherProvider:
    """Interface for weather data providers."""
    def fetch_weather_for_checkpoints(
        self, checkpoints: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError


class OpenMeteoWeatherProvider(WeatherProvider):
    """
    Open-Meteo weather implementation supporting batched queries,
    hourly resolution, and native mph & inch units.
    """
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def fetch_weather_for_checkpoints(
        self, checkpoints: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not checkpoints:
            return checkpoints

        # Identify unique coordinates needing fetch
        needed_coords = []
        for cp in checkpoints:
            ck = cache_key(cp["latitude"], cp["longitude"])
            if ck not in _WEATHER_CACHE and (cp["latitude"], cp["longitude"]) not in needed_coords:
                needed_coords.append((cp["latitude"], cp["longitude"]))

        # Batch in chunks of 50
        chunk_size = 50
        for i in range(0, len(needed_coords), chunk_size):
            chunk = needed_coords[i : i + chunk_size]
            self._fetch_batch(chunk)

        # Now attach weather to each checkpoint
        for cp in checkpoints:
            ck = cache_key(cp["latitude"], cp["longitude"])
            forecast_data = _WEATHER_CACHE.get(ck)
            
            if not forecast_data:
                # Fallback if network or data missing
                cp["wind_speed_mph"] = 0.0
                cp["rain_intensity_in_hr"] = 0.0
                cp["snow_intensity_in_hr"] = 0.0
                cp["temperature_f"] = 65.0
                cp["forecast_available"] = False
                cp["hourly_timeline"] = []
                continue

            times = forecast_data.get("time", [])
            winds = forecast_data.get("windspeed_10m", [])
            precips = forecast_data.get("precipitation", [])
            snows = forecast_data.get("snowfall", [])
            temps = forecast_data.get("temperature_2m", [])

            # Match checkpoint ETA hour
            target_hour = cp.get("forecast_lookup_hour")
            matched_idx = -1
            
            if target_hour and target_hour in times:
                matched_idx = times.index(target_hour)
            else:
                # Find closest available hour
                matched_idx = self._find_closest_time_index(times, target_hour)

            if matched_idx >= 0 and matched_idx < len(winds):
                cp["wind_speed_mph"] = round(float(winds[matched_idx] or 0.0), 1)
                cp["rain_intensity_in_hr"] = round(float(precips[matched_idx] or 0.0), 2)
                cp["snow_intensity_in_hr"] = round(float(snows[matched_idx] or 0.0), 2)
                
                # Temperature in Celsius -> Fahrenheit
                raw_temp = float(temps[matched_idx] or 15.0)
                cp["temperature_f"] = round(raw_temp * 9.0 / 5.0 + 32.0, 1)
                cp["forecast_available"] = True
                
                # Build 48-hour timeline starting from matched_idx or index 0 for the slider
                timeline = []
                for offset in range(0, 49):
                    t_idx = matched_idx + offset
                    if t_idx < len(times):
                        timeline.append({
                            "offset_hours": offset,
                            "time": times[t_idx],
                            "wind_speed_mph": round(float(winds[t_idx] or 0.0), 1),
                            "rain_intensity_in_hr": round(float(precips[t_idx] or 0.0), 2),
                            "snow_intensity_in_hr": round(float(snows[t_idx] or 0.0), 2),
                        })
                cp["hourly_timeline"] = timeline
            else:
                cp["wind_speed_mph"] = 0.0
                cp["rain_intensity_in_hr"] = 0.0
                cp["snow_intensity_in_hr"] = 0.0
                cp["temperature_f"] = 65.0
                cp["forecast_available"] = False
                cp["hourly_timeline"] = []

        return checkpoints

    def _fetch_batch(self, coords: List[tuple]):
        if not coords:
            return

        lats_str = ",".join(str(c[0]) for c in coords)
        lons_str = ",".join(str(c[1]) for c in coords)

        params = {
            "latitude": lats_str,
            "longitude": lons_str,
            "hourly": "temperature_2m,windspeed_10m,precipitation,snowfall",
            "windspeed_unit": "mph",
            "precipitation_unit": "inch",
            "forecast_days": 7,
            "timezone": "UTC",
        }

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # If single location returned as object vs list of objects
                if isinstance(data, dict):
                    results = [data]
                else:
                    results = data

                for i, res in enumerate(results):
                    if i < len(coords):
                        coord = coords[i]
                        ck = cache_key(coord[0], coord[1])
                        hourly = res.get("hourly", {})
                        _WEATHER_CACHE[ck] = hourly
        except Exception as e:
            # Silently log error, fallback handled by caller
            print(f"Weather API error: {e}")

    def _find_closest_time_index(self, times: List[str], target_iso: Optional[str]) -> int:
        if not times:
            return -1
        if not target_iso:
            return 0
        try:
            target_dt = datetime.fromisoformat(target_iso)
            best_idx = 0
            best_diff = float("inf")
            for idx, t_str in enumerate(times):
                t_dt = datetime.fromisoformat(t_str)
                diff = abs((t_dt - target_dt).total_seconds())
                if diff < best_diff:
                    best_diff = diff
                    best_idx = idx
            return best_idx
        except Exception:
            return 0


# Default provider instance
weather_provider = OpenMeteoWeatherProvider()
