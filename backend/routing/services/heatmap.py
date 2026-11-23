"""
Heatmap Service for Weather-Aware Truck Routing.

Computes corridor weather heatmap data and dynamic checkpoint risk states
across the 0 to 48-hour forecast timeline relative to trip departure time.
Handles missing forecasts explicitly without repeating the last forecast.
"""

from typing import List, Dict, Any
from .risk_engine import (
    evaluate_checkpoint_risk,
    get_higher_risk,
    RISK_UNKNOWN,
)


def generate_corridor_heatmap_timeline(
    checkpoints: List[Dict[str, Any]],
    load_weight_lb: float
) -> Dict[int, Dict[str, Any]]:
    """
    Generate hourly checkpoint states and heatmap segments for offsets 0 to 48 hours relative to departure.
    
    Returns a dict mapping hour_offset (0..48) -> {
        "checkpoints": [ ... dynamic checkpoint states with recalculated risks ... ],
        "segments": [ ... dynamic route segments with recalculated segment risks ... ],
    }
    """
    timeline_heatmap: Dict[int, Dict[str, Any]] = {}

    for hour_offset in range(0, 49):
        dynamic_checkpoints = []

        for cp in checkpoints:
            timeline = cp.get("hourly_timeline", [])
            entry = None

            # Look for exact offset in checkpoint's departure-relative timeline
            if hour_offset < len(timeline):
                entry = timeline[hour_offset]

            if entry and entry.get("forecast_available"):
                wind = entry["wind_speed_mph"]
                rain = entry["rain_intensity_in_hr"]
                snow = entry["snow_intensity_in_hr"]
                is_avail = True
            else:
                # Missing forecast: DO NOT repeat last forecast!
                wind = None
                rain = None
                snow = None
                is_avail = False

            # Recalculate risk at this checkpoint for the selected hour
            risk_eval = evaluate_checkpoint_risk(
                wind, rain, snow, load_weight_lb, forecast_available=is_avail
            )

            dynamic_checkpoints.append({
                "id": cp["id"],
                "checkpoint_index": cp.get("checkpoint_index", 0),
                "latitude": cp["latitude"],
                "longitude": cp["longitude"],
                "distance_from_origin_miles": cp.get("distance_from_origin_miles", 0.0),
                "is_origin": cp.get("is_origin", False),
                "is_destination": cp.get("is_destination", False),
                "wind_speed_mph": wind,
                "rain_intensity_in_hr": rain,
                "snow_intensity_in_hr": snow,
                "wind_risk": risk_eval["wind_risk"],
                "rain_risk": risk_eval["rain_risk"],
                "snow_risk": risk_eval["snow_risk"],
                "load_adjusted_risk": risk_eval["load_adjusted_risk"],
                "final_risk": risk_eval["final_risk"],
                "risk_score": risk_eval["risk_score"],
                "forecast_available": is_avail,
                "reason": risk_eval["reason"],
            })

        # Recalculate dynamic route heatmap segments for this hour
        dynamic_segments = []
        for i in range(len(dynamic_checkpoints) - 1):
            cp_start = dynamic_checkpoints[i]
            cp_end = dynamic_checkpoints[i + 1]

            seg_risk = get_higher_risk(cp_start["final_risk"], cp_end["final_risk"])
            seg_dist = max(
                0.0,
                cp_end["distance_from_origin_miles"] - cp_start["distance_from_origin_miles"]
            )

            dynamic_segments.append({
                "segment_index": i,
                "start_checkpoint_id": cp_start["id"],
                "end_checkpoint_id": cp_end["id"],
                "start_lat": cp_start["latitude"],
                "start_lon": cp_start["longitude"],
                "end_lat": cp_end["latitude"],
                "end_lon": cp_end["longitude"],
                "distance_miles": round(seg_dist, 2),
                "risk_level": seg_risk,
            })

        timeline_heatmap[hour_offset] = {
            "checkpoints": dynamic_checkpoints,
            "segments": dynamic_segments,
        }

    return timeline_heatmap
