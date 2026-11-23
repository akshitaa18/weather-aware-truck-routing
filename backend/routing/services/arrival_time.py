"""
Arrival Time Calculation Service.

Calculates estimated travel time and estimated arrival timestamp at each checkpoint
along a route based on departure date/time and segment-based distance interpolation.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any


def calculate_checkpoint_etas(
    checkpoints: List[Dict[str, Any]],
    departure_time_iso: str,
    total_duration_seconds: float,
    total_distance_miles: float
) -> List[Dict[str, Any]]:
    """
    Assign estimated arrival times (ETAs) to each checkpoint.
    
    Uses segment-proportional elapsed travel time:
    elapsed_seconds = (distance_from_origin / total_distance) * total_duration_seconds
    ETA = departure_time + elapsed_seconds
    """
    try:
        # Handle formats like '2026-11-23T14:30' or '2026-11-23T14:30:00Z'
        clean_iso = departure_time_iso.replace("Z", "+00:00")
        if len(clean_iso) == 16:  # YYYY-MM-DDTHH:MM
            dep_dt = datetime.fromisoformat(clean_iso)
        else:
            dep_dt = datetime.fromisoformat(clean_iso)
    except Exception:
        # Fallback to current UTC time if invalid
        dep_dt = datetime.now()

    if total_distance_miles <= 0:
        total_distance_miles = 1.0

    for cp in checkpoints:
        dist = cp["distance_from_origin_miles"]
        ratio = min(1.0, max(0.0, dist / total_distance_miles))
        elapsed_seconds = ratio * total_duration_seconds
        
        eta_dt = dep_dt + timedelta(seconds=elapsed_seconds)
        
        cp["elapsed_seconds"] = round(elapsed_seconds, 1)
        cp["elapsed_hours"] = round(elapsed_seconds / 3600.0, 2)
        cp["estimated_arrival_time"] = eta_dt.isoformat()
        cp["arrival_time_formatted"] = eta_dt.strftime("%b %d, %Y %I:%M %p")
        # Hour string for matching with Open-Meteo hourly forecast (YYYY-MM-DDTHH:00)
        cp["forecast_lookup_hour"] = eta_dt.strftime("%Y-%m-%dT%H:00")

    return checkpoints
