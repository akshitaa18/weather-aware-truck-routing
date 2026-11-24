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
            "unknown_risk_miles": round(total_distance_miles, 1),
            "verified_low_risk_miles": 0.0,
            "verified_moderate_risk_miles": 0.0,
            "verified_high_risk_miles": 0.0,
            "verified_severe_risk_miles": 0.0,
            "verified_no_travel_miles": 0.0,
            "known_hazard_severe_miles": 0.0,
            "known_hazard_high_miles": 0.0,
            "known_hazard_moderate_miles": 0.0,
            "partial_data_hazard_miles": 0.0,
            "has_missing_weather": True,
            "average_risk_score": 0.0,
            "overall_route_risk": RISK_UNKNOWN,
            "is_safe_for_travel": False,
            "checkpoint_count": len(checkpoints) if checkpoints else 0,
            "segments": [],
        }

    verified_low_miles = 0.0
    verified_mod_miles = 0.0
    verified_high_miles = 0.0
    verified_severe_miles = 0.0
    verified_no_travel_miles = 0.0
    no_travel_miles = 0.0
    unknown_miles = 0.0


    # Separate trackers for known hazards on partial/incomplete weather segments
    known_hazard_severe_miles = 0.0
    known_hazard_high_miles = 0.0
    known_hazard_moderate_miles = 0.0
    partial_data_hazard_miles = 0.0

    segments = []
    total_verified_miles = 0.0
    weighted_risk_sum = 0.0
    has_any_missing_cp = any(not cp.get("forecast_available", True) for cp in checkpoints)

    for i in range(len(checkpoints) - 1):
        cp_start = checkpoints[i]
        cp_end = checkpoints[i + 1]

        seg_dist = max(0.0, cp_end["distance_from_origin_miles"] - cp_start["distance_from_origin_miles"])
        seg_risk = get_higher_risk(cp_start["final_risk"], cp_end["final_risk"])
        risk_score = RISK_SEVERITY_ORDER.get(seg_risk, 0)

        # Check whether both endpoints have verified complete forecasts
        seg_fully_verified = (
            bool(cp_start.get("forecast_available", True))
            and bool(cp_end.get("forecast_available", True))
            and cp_start.get("final_risk") != RISK_UNKNOWN
            and cp_end.get("final_risk") != RISK_UNKNOWN
        )

        if seg_fully_verified:
            if seg_risk == RISK_NO_TRAVEL:
                verified_no_travel_miles += seg_dist
                no_travel_miles += seg_dist
                weighted_risk_sum += seg_dist * 5.0
                total_verified_miles += seg_dist

            elif seg_risk == RISK_SEVERE:
                verified_severe_miles += seg_dist
                weighted_risk_sum += seg_dist * 4.0
                total_verified_miles += seg_dist
            elif seg_risk == RISK_HIGH:
                verified_high_miles += seg_dist
                weighted_risk_sum += seg_dist * 3.0
                total_verified_miles += seg_dist
            elif seg_risk == RISK_MODERATE:
                verified_mod_miles += seg_dist
                weighted_risk_sum += seg_dist * 2.0
                total_verified_miles += seg_dist
            else:
                verified_low_miles += seg_dist
                weighted_risk_sum += seg_dist * 1.0
                total_verified_miles += seg_dist
        else:
            # Segment has incomplete/unavailable forecast data
            unknown_miles += seg_dist

            # Preserve known hazards detected during partial weather data
            if seg_risk == RISK_NO_TRAVEL:
                no_travel_miles += seg_dist
                partial_data_hazard_miles += seg_dist
            elif seg_risk == RISK_SEVERE:
                known_hazard_severe_miles += seg_dist
                partial_data_hazard_miles += seg_dist
            elif seg_risk == RISK_HIGH:
                known_hazard_high_miles += seg_dist
                partial_data_hazard_miles += seg_dist
            elif seg_risk == RISK_MODERATE:
                known_hazard_moderate_miles += seg_dist
                partial_data_hazard_miles += seg_dist

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
            "is_verified": seg_fully_verified,
        })

    # Weighted average risk score over verified segments
    if total_verified_miles > 0:
        avg_score = round(weighted_risk_sum / total_verified_miles, 2)
    else:
        avg_score = 0.0

    has_missing_weather = unknown_miles > 0.0 or has_any_missing_cp

    # Overall route risk determination - preserves known hazards even with partial data
    if no_travel_miles > 0:
        overall_risk = RISK_NO_TRAVEL
        is_safe = False
    elif verified_severe_miles > 0 or known_hazard_severe_miles > 0:
        overall_risk = RISK_SEVERE
        is_safe = False if has_missing_weather else True
    elif verified_high_miles > 0 or known_hazard_high_miles > 0:
        overall_risk = RISK_HIGH
        is_safe = False if has_missing_weather else True
    elif verified_mod_miles > 0 or known_hazard_moderate_miles > 0:
        overall_risk = RISK_MODERATE
        is_safe = False if has_missing_weather else True
    elif has_missing_weather:
        overall_risk = RISK_UNKNOWN
        is_safe = False  # NEVER safe if required weather data is unavailable
    else:
        overall_risk = RISK_LOW
        is_safe = True

    return {
        "low_risk_miles": round(verified_low_miles, 1),
        "moderate_risk_miles": round(verified_mod_miles, 1),
        "high_risk_miles": round(verified_high_miles, 1),
        "severe_risk_miles": round(verified_severe_miles, 1),
        "no_travel_miles": round(no_travel_miles, 1),
        "verified_no_travel_miles": round(verified_no_travel_miles, 1),
        "unknown_risk_miles": round(unknown_miles, 1),
        "verified_low_risk_miles": round(verified_low_miles, 1),
        "verified_moderate_risk_miles": round(verified_mod_miles, 1),
        "verified_high_risk_miles": round(verified_high_miles, 1),
        "verified_severe_risk_miles": round(verified_severe_miles, 1),

        "known_hazard_severe_miles": round(known_hazard_severe_miles, 1),
        "known_hazard_high_miles": round(known_hazard_high_miles, 1),
        "known_hazard_moderate_miles": round(known_hazard_moderate_miles, 1),
        "partial_data_hazard_miles": round(partial_data_hazard_miles, 1),
        "has_missing_weather": has_missing_weather,
        "average_risk_score": avg_score,
        "overall_route_risk": overall_risk,
        "is_safe_for_travel": is_safe,
        "checkpoint_count": len(checkpoints),
        "segments": segments,
    }

