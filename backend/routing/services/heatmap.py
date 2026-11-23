"""
Heatmap Service for Weather-Aware Truck Routing.

Computes corridor weather heatmap data points [latitude, longitude, intensity]
for the route corridor across the 0 to 48-hour forecast timeline.
"""

from typing import List, Dict, Any
from .risk_engine import (
    evaluate_checkpoint_risk,
    RISK_SEVERITY_ORDER,
)


def generate_corridor_heatmap_timeline(
    checkpoints: List[Dict[str, Any]],
    load_weight_lb: float
) -> Dict[int, List[Dict[str, Any]]]:
    """
    Generate hourly heatmap data points along checkpoints for offsets 0 to 48 hours.
    
    Returns a dict mapping hour_offset (0..48) -> list of heatmap points:
    [
        {
            "lat": float,
            "lon": float,
            "intensity": float,  # 0.1 to 1.0
            "wind_mph": float,
            "rain_in_hr": float,
            "snow_in_hr": float,
            "risk_level": str,
        },
        ...
    ]
    """
    timeline_heatmap: Dict[int, List[Dict[str, Any]]] = {}

    for hour_offset in range(0, 49):
        points = []
        for cp in checkpoints:
            lat = cp["latitude"]
            lon = cp["longitude"]
            timeline = cp.get("hourly_timeline", [])
            
            # Find matching hour offset in checkpoint's timeline
            entry = None
            if hour_offset < len(timeline):
                entry = timeline[hour_offset]
            elif timeline:
                entry = timeline[-1]

            if entry:
                wind = entry["wind_speed_mph"]
                rain = entry["rain_intensity_in_hr"]
                snow = entry["snow_intensity_in_hr"]
            else:
                wind = cp.get("wind_speed_mph", 0.0)
                rain = cp.get("rain_intensity_in_hr", 0.0)
                snow = cp.get("snow_intensity_in_hr", 0.0)

            risk_eval = evaluate_checkpoint_risk(wind, rain, snow, load_weight_lb)
            risk_score = risk_eval["risk_score"]
            # Intensity normalized to 0.2, 0.4, 0.6, 0.8, 1.0
            intensity = round(risk_score / 5.0, 2)

            points.append({
                "lat": lat,
                "lon": lon,
                "intensity": intensity,
                "wind_mph": wind,
                "rain_in_hr": rain,
                "snow_in_hr": snow,
                "risk_level": risk_eval["final_risk"],
                "reason": risk_eval["reason"],
            })
        timeline_heatmap[hour_offset] = points

    return timeline_heatmap
