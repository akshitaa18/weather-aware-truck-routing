"""
Weather Provider Service.

Fetches accurate hourly weather forecasts using Open-Meteo API.
Batches coordinate requests, caches results, normalizes units (mph, in/hr),
and attaches hourly weather predictions matching checkpoint ETAs.
Preserves forecast availability flags and never converts missing forecasts into zero-valued Low risk.
"""

import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

# In-memory weather cache: (rounded_lat, rounded_lon) -> hourly_forecast_dict
_WEATHER_CACHE: Dict[str, Dict[str, Any]] = {}


def cache_key(lat: float, lon: float) -> str:
    """Round coordinates to 2 decimal places (~1.1 km) for caching."""
    return f"{round(lat, 2)}_{round(lon, 2)}"


class WeatherProvider:
    """Interface for weather data providers."""
    def fetch_weather_for_checkpoints(
        self,
        checkpoints: List[Dict[str, Any]],
        departure_time_utc_iso: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError


class OpenMeteoWeatherProvider(WeatherProvider):
    """
    Open-Meteo weather implementation supporting batched queries,
    hourly resolution, and native mph & inch units.
    """
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def fetch_weather_for_checkpoints(
        self,
        checkpoints: List[Dict[str, Any]],
        departure_time_utc_iso: Optional[str] = None
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

        # Base departure time for 0-48h timeline calculation
        if departure_time_utc_iso:
            try:
                base_dep_dt = datetime.fromisoformat(departure_time_utc_iso.replace("Z", "+00:00"))
            except Exception:
                base_dep_dt = datetime.now(timezone.utc)
        else:
            base_dep_dt = datetime.now(timezone.utc)

        # Now attach weather to each checkpoint
        for cp in checkpoints:
            ck = cache_key(cp["latitude"], cp["longitude"])
            forecast_data = _WEATHER_CACHE.get(ck)
            
            if not forecast_data:
                # Do NOT substitute 0.0! Mark as unavailable
                cp["wind_speed_mph"] = None
                cp["rain_intensity_in_hr"] = None
                cp["snow_intensity_in_hr"] = None
                cp["temperature_f"] = None
                cp["forecast_available"] = False
                cp["hourly_timeline"] = []
                continue

            times = forecast_data.get("time", [])
            winds = forecast_data.get("windspeed_10m", [])
            precips = forecast_data.get("precipitation", [])
            snows = forecast_data.get("snowfall", [])
            temps = forecast_data.get("temperature_2m", [])

            # Match checkpoint ETA hour (in UTC)
            target_hour = cp.get("forecast_lookup_hour")
            matched_idx = -1
            
            if target_hour and target_hour in times:
                matched_idx = times.index(target_hour)

            # Check if target hour is genuinely available
            if matched_idx >= 0 and matched_idx < len(times):
                w_raw = winds[matched_idx] if matched_idx < len(winds) else None
                r_raw = precips[matched_idx] if matched_idx < len(precips) else None
                s_raw = snows[matched_idx] if matched_idx < len(snows) else None
                t_raw = temps[matched_idx] if matched_idx < len(temps) else None

                cp["wind_speed_mph"] = round(float(w_raw), 1) if w_raw is not None else None
                cp["rain_intensity_in_hr"] = round(float(r_raw), 2) if r_raw is not None else None
                cp["snow_intensity_in_hr"] = round(float(s_raw), 2) if s_raw is not None else None
                cp["temperature_f"] = round(float(t_raw) * 9.0 / 5.0 + 32.0, 1) if t_raw is not None else None

                # Require all three measurements (wind, rain, snow) for forecast_available=True
                cp["forecast_available"] = (
                    cp["wind_speed_mph"] is not None
                    and cp["rain_intensity_in_hr"] is not None
                    and cp["snow_intensity_in_hr"] is not None
                )
            else:
                # Out of forecast range or missing: NEVER classify as 0.0 Low risk
                cp["wind_speed_mph"] = None
                cp["rain_intensity_in_hr"] = None
                cp["snow_intensity_in_hr"] = None
                cp["temperature_f"] = None
                cp["forecast_available"] = False

            # Build 0-48 hour timeline strictly relative to DEPARTURE TIME
            # (departure_time + offset_hours, NOT ETA + offset_hours)
            timeline = []
            for offset in range(0, 49):
                target_dt = base_dep_dt + timedelta(hours=offset)
                target_str = target_dt.strftime("%Y-%m-%dT%H:00")

                if target_str in times:
                    t_idx = times.index(target_str)
                    w_val = winds[t_idx] if t_idx < len(winds) else None
                    r_val = precips[t_idx] if t_idx < len(precips) else None
                    s_val = snows[t_idx] if t_idx < len(snows) else None

                    w_mph = round(float(w_val), 1) if w_val is not None else None
                    r_in = round(float(r_val), 2) if r_val is not None else None
                    s_in = round(float(s_val), 2) if s_val is not None else None

                    # forecast_available=False if any required weather measurement is missing
                    is_avail = (w_mph is not None and r_in is not None and s_in is not None)

                    timeline.append({
                        "offset_hours": offset,
                        "time": target_str,
                        "wind_speed_mph": w_mph,
                        "rain_intensity_in_hr": r_in,
                        "snow_intensity_in_hr": s_in,
                        "forecast_available": is_avail,
                    })
                else:
                    # Outside provider horizon: do not repeat last forecast!
                    timeline.append({
                        "offset_hours": offset,
                        "time": target_str,
                        "wind_speed_mph": None,
                        "rain_intensity_in_hr": None,
                        "snow_intensity_in_hr": None,
                        "forecast_available": False,
                    })

            cp["hourly_timeline"] = timeline

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
            print(f"Weather API error: {e}")


# Default provider instance
weather_provider = OpenMeteoWeatherProvider()
