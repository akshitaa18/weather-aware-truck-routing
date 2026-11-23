"""
Arrival Time Calculation Service.

Calculates estimated travel time and estimated arrival timestamp at each checkpoint
along a route based on departure date/time and segment-based distance interpolation.
Ensures consistent timezone handling so checkpoint ETAs and Open-Meteo UTC forecast
timestamps refer to the exact same instant.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple


def parse_to_utc_datetime(
    departure_time_iso: str,
    user_timezone_offset_minutes: Optional[int] = None
) -> datetime:
    """
    Parse departure time string safely into a timezone-aware UTC datetime.
    
    Handles:
    - Timezone-aware ISO strings: e.g. '2026-11-24T08:00:00-05:00', '2026-11-24T13:00:00Z'
    - Timezone-naive ISO strings: e.g. '2026-11-24T08:00' with user_timezone_offset_minutes
    - Defaults to UTC if naive and no offset provided, avoiding silent timezone drift.
    """
    clean_iso = departure_time_iso.strip().replace("Z", "+00:00")
    
    try:
        dt = datetime.fromisoformat(clean_iso)
        if dt.tzinfo is not None:
            # Timezone-aware: convert to UTC
            return dt.astimezone(timezone.utc)
        
        # Timezone-naive
        if user_timezone_offset_minutes is not None:
            # JavaScript getTimezoneOffset() returns minutes *difference* from UTC:
            # e.g., US EST (UTC-5) returns +300 minutes.
            # Local = UTC - offset  =>  Offset from UTC = -user_timezone_offset_minutes
            tz = timezone(timedelta(minutes=-user_timezone_offset_minutes))
            dt_with_tz = dt.replace(tzinfo=tz)
            return dt_with_tz.astimezone(timezone.utc)
        else:
            # Fallback convention: treat naive input as UTC
            return dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def calculate_checkpoint_etas(
    checkpoints: List[Dict[str, Any]],
    departure_time_iso: str,
    total_duration_seconds: float,
    total_distance_miles: float,
    user_timezone_offset_minutes: Optional[int] = None
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Assign estimated arrival times (ETAs) to each checkpoint in UTC.
    
    Returns:
    (updated_checkpoints, departure_time_utc_iso)
    """
    dep_dt_utc = parse_to_utc_datetime(departure_time_iso, user_timezone_offset_minutes)
    departure_time_utc_iso = dep_dt_utc.isoformat()

    if total_distance_miles <= 0:
        total_distance_miles = 1.0

    for cp in checkpoints:
        dist = cp["distance_from_origin_miles"]
        ratio = min(1.0, max(0.0, dist / total_distance_miles))
        elapsed_seconds = ratio * total_duration_seconds
        
        eta_dt_utc = dep_dt_utc + timedelta(seconds=elapsed_seconds)
        
        cp["elapsed_seconds"] = round(elapsed_seconds, 1)
        cp["elapsed_hours"] = round(elapsed_seconds / 3600.0, 2)
        cp["estimated_arrival_time"] = eta_dt_utc.isoformat()
        cp["arrival_time_formatted"] = eta_dt_utc.strftime("%b %d, %Y %I:%M %p UTC")
        # Hour string for matching with Open-Meteo hourly forecast (YYYY-MM-DDTHH:00 UTC)
        cp["forecast_lookup_hour"] = eta_dt_utc.strftime("%Y-%m-%dT%H:00")

    return checkpoints, departure_time_utc_iso
