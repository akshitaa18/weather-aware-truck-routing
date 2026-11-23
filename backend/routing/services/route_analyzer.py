"""
Route Analyzer Service.

Calculates segment-level risk miles, cumulative metrics, weighted average risk scores,
and overall route classifications according to Section 9 specifications.
Strictly distinguishes between verified Low-risk forecasts and missing weather data.
"""

from typing import List, Dict, Any
from .risk_engine import (
    RISK_LOW,
    RISK_MODERATE,
    RISK_HIGH,
    RISK_SEVERE,
    RISK_NO_TRAVEL,
    RISK_UNKNOWN,
    RISK_SEVERITY_ORDER,
    get_higher_risk,
)


def analyze_route_metrics(
    route: Dict[str, Any],
    checkpoints: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Compute route metrics from checkpoints using segment attribution:
    
    Segment Attribution Method:
    For consecutive checkpoints [cp_i, cp_{i+1}], the segment distance is
    (cp_{i+1}.distance - cp_i.distance). The segment risk is assigned as
    max(risk(cp_i), risk(cp_{i+1})) to ensure conservative safety representation.
    """
    total_distance_miles = route.get("distance_miles", 0.0)

    if not checkpoints or len(checkpoints) < 2:
        return {
            "low_risk_miles": 0.0,
            "moderate_risk_miles": 0.0,
            "high_risk_miles": 0.0,
            "severe_risk_miles": 0.0,
            "no_travel_miles": 0.0,
            "unknown_risk_miles": total_distance_miles,
            "has_missing_weather": True,
            "average_risk_score": 0.0,
            "overall_route_risk": RISK_UNKNOWN,
            "is_safe_for_travel": False,
            "checkpoint_count": len(checkpoints),
            "segments": [],
        }

    low_miles = 0.0
    mod_miles = 0.0
    high_miles = 0.0
    severe_miles = 0.0
    no_travel_miles = 0.0
    unknown_miles = 0.0

    segments = []
    total_known_miles = 0.0
    weighted_risk_sum = 0.0
    has_any_missing_cp = any(not cp.get("forecast_available", True) for cp in checkpoints)

    for i in range(len(checkpoints) - 1):
        cp_start = checkpoints[i]
        cp_end = checkpoints[i + 1]

        seg_dist = max(0.0, cp_end["distance_from_origin_miles"] - cp_start["distance_from_origin_miles"])
        seg_risk = get_higher_risk(cp_start["final_risk"], cp_end["final_risk"])
        risk_score = RISK_SEVERITY_ORDER.get(seg_risk, 0)

        if seg_risk == RISK_NO_TRAVEL:
            no_travel_miles += seg_dist
            weighted_risk_sum += seg_dist * 5.0
            total_known_miles += seg_dist
        elif seg_risk == RISK_SEVERE:
            severe_miles += seg_dist
            weighted_risk_sum += seg_dist * 4.0
            total_known_miles += seg_dist
        elif seg_risk == RISK_HIGH:
            high_miles += seg_dist
            weighted_risk_sum += seg_dist * 3.0
            total_known_miles += seg_dist
        elif seg_risk == RISK_MODERATE:
            mod_miles += seg_dist
            weighted_risk_sum += seg_dist * 2.0
            total_known_miles += seg_dist
        elif seg_risk == RISK_UNKNOWN:
            unknown_miles += seg_dist
        else:
            low_miles += seg_dist
            weighted_risk_sum += seg_dist * 1.0
            total_known_miles += seg_dist

        segments.append({
            "segment_index": i,
            "start_checkpoint_id": cp_start["id"],
            "end_checkpoint_id": cp_end["id"],
            "start_lat": cp_start["latitude"],
            "start_lon": cp_start["longitude"],
            "end_lat": cp_end["latitude"],
            "end_lon": cp_end["longitude"],
            "distance_miles": round(seg_dist, 2),
            "risk_level": seg_risk,
            "risk_score": risk_score,
        })

    # Weighted average risk score over verified segments
    if total_known_miles > 0:
        avg_score = round(weighted_risk_sum / total_known_miles, 2)
    else:
        avg_score = 0.0

    has_missing_weather = unknown_miles > 0.0 or has_any_missing_cp

    # Overall route risk determination
    if no_travel_miles > 0:
        overall_risk = RISK_NO_TRAVEL
        is_safe = False
    elif severe_miles > 0:
        overall_risk = RISK_SEVERE
        is_safe = not has_missing_weather
    elif high_miles > 0:
        overall_risk = RISK_HIGH
        is_safe = not has_missing_weather
    elif unknown_miles > 0:
        overall_risk = RISK_UNKNOWN
        is_safe = False  # NEVER safe if required weather data is unavailable
    elif mod_miles > 0:
        overall_risk = RISK_MODERATE
        is_safe = not has_missing_weather
    else:
        overall_risk = RISK_LOW
        is_safe = not has_missing_weather

    return {
        "low_risk_miles": round(low_miles, 1),
        "moderate_risk_miles": round(mod_miles, 1),
        "high_risk_miles": round(high_miles, 1),
        "severe_risk_miles": round(severe_miles, 1),
        "no_travel_miles": round(no_travel_miles, 1),
        "unknown_risk_miles": round(unknown_miles, 1),
        "has_missing_weather": has_missing_weather,
        "average_risk_score": avg_score,
        "overall_route_risk": overall_risk,
        "is_safe_for_travel": is_safe,
        "checkpoint_count": len(checkpoints),
        "segments": segments,
    }
