"""
Route Recommendation Algorithm Service.

Implements the exact lexicographical priority comparison required by Section 9:
1. Hard constraint: No-Travel routes disqualified from normal recommendation
2. Missing weather constraint: Routes with missing weather are never marked safe
3. Verified routing constraint: Simulated routes are clearly distinguished and never presented as verified
4. Priority 1: Fewest Severe miles
5. Priority 2: Fewest High miles
6. Priority 3: Lowest average risk score
7. Priority 4: Shortest travel time (tie-breaker)
"""

from typing import List, Dict, Any, Tuple


def is_route_eligible(route: Dict[str, Any]) -> bool:
    """
    Fail-closed safety eligibility validation.
    
    A route is eligible for safe recommendation IF AND ONLY IF:
    1. Route structure is valid and non-empty.
    2. Route is verified road geometry (is_verified_road_route is True).
    3. Route is NOT simulated geometry (is_simulated is False).
    4. Duration is a valid positive number.
    5. Route contains valid, non-empty metrics.
    6. Complete weather forecast data is available (has_missing_weather is False and unknown_risk_miles == 0.0).
    7. Zero miles of No Travel conditions (no_travel_miles == 0.0).
    8. Route is explicitly cleared as safe for travel (is_safe_for_travel is True).
    9. Severe and High risk miles and average risk score are valid numbers.
    
    Missing, None, or invalid required safety fields strictly disqualify the route.
    """
    if not isinstance(route, dict) or not route:
        return False

    # 1. Verification of road geometry
    if route.get("is_simulated") is not False:
        return False
    if route.get("is_verified_road_route") is not True:
        return False

    # 2. Duration check
    duration = route.get("duration_seconds")
    if not isinstance(duration, (int, float)) or duration <= 0:
        return False

    # 3. Metrics validation
    metrics = route.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        return False

    # 4. Weather completeness
    if metrics.get("has_missing_weather") is not False:
        return False
    unknown_miles = metrics.get("unknown_risk_miles")
    if not isinstance(unknown_miles, (int, float)) or unknown_miles != 0.0:
        return False

    # 5. No Travel constraint
    no_travel = metrics.get("no_travel_miles")
    if not isinstance(no_travel, (int, float)) or no_travel != 0.0:
        return False

    # 6. Explicit safety clearance
    if metrics.get("is_safe_for_travel") is not True:
        return False

    # 7. Safety risk metrics presence and validity
    severe = metrics.get("severe_risk_miles")
    if not isinstance(severe, (int, float)) or severe < 0:
        return False

    high = metrics.get("high_risk_miles")
    if not isinstance(high, (int, float)) or high < 0:
        return False

    avg_score = metrics.get("average_risk_score")
    if not isinstance(avg_score, (int, float)) or avg_score <= 0:
        return False

    return True


def eligible_route_sort_key(route: Dict[str, Any]) -> Tuple[float, float, float, float]:
    """
    Strict 4-tuple lexicographical sort key for eligible safe routes:
    1. Fewest Severe miles
    2. Fewest High miles
    3. Lowest average risk score
    4. Shortest duration (seconds)
    """
    metrics = route.get("metrics", {})
    severe = float(metrics.get("severe_risk_miles", 0.0))
    high = float(metrics.get("high_risk_miles", 0.0))
    avg_score = float(metrics.get("average_risk_score", 1.0))
    duration = float(route.get("duration_seconds", 0.0))
    return (severe, high, avg_score, duration)


def presentation_sort_key(route: Dict[str, Any]) -> Tuple[int, int, int, int, float, float, float, float]:
    """
    Presentation sort key to order all candidate routes (eligible first, then by hazard type):
    (
        ineligible (0=eligible, 1=ineligible),
        has_no_travel (0=no, 1=yes),
        has_missing_weather (0=no, 1=yes),
        is_simulated (0=no, 1=yes),
        severe_risk_miles,
        high_risk_miles,
        average_risk_score,
        duration_seconds
    )
    """
    eligible = is_route_eligible(route)
    ineligible = 0 if eligible else 1

    metrics = route.get("metrics") if isinstance(route, dict) else {}
    if not isinstance(metrics, dict):
        metrics = {}

    no_travel = float(metrics.get("no_travel_miles") or 0.0)
    has_missing = bool(metrics.get("has_missing_weather", False) or (float(metrics.get("unknown_risk_miles") or 0.0) > 0))
    is_sim = 1 if route.get("is_simulated", False) else 0
    has_no_travel = 1 if no_travel > 0.0 else 0
    missing_int = 1 if has_missing else 0

    severe = float(metrics.get("severe_risk_miles") or 0.0)
    high = float(metrics.get("high_risk_miles") or 0.0)
    avg_score = float(metrics.get("average_risk_score") or 999.0)
    duration = float(route.get("duration_seconds") or 999999.0)

    return (
        ineligible,
        has_no_travel,
        missing_int,
        is_sim,
        severe,
        high,
        avg_score,
        duration,
    )


# Backward compatibility alias
route_sort_key = presentation_sort_key


def select_recommended_route(routes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compare routes lexicographically and select the recommended route.
    Disqualifies any route with No Travel hazards, missing weather data, or simulated geometry.
    If no route is eligible, is_any_safe is False and recommended_route_id is None.
    """
    if not routes:
        return {
            "recommended_route_id": None,
            "recommended_route": None,
            "is_any_safe": False,
            "explanation": "No routes available for analysis.",
            "comparisons": [],
            "sorted_rankings": [],
        }

    sorted_routes = sorted(routes, key=presentation_sort_key)
    eligible_routes = [r for r in routes if is_route_eligible(r)]

    if eligible_routes:
        # Rank eligible routes by strict 4-tuple lexicographical priority
        sorted_eligible = sorted(eligible_routes, key=eligible_route_sort_key)
        best_route = sorted_eligible[0]
        best_metrics = best_route.get("metrics", {})
        is_any_safe = True
        recommended_route_id = best_route["id"]
        recommended_route = best_route

        reasons = []
        other_routes = [r for r in routes if r["id"] != best_route["id"]]
        severe = best_metrics.get("severe_risk_miles", 0.0)
        high = best_metrics.get("high_risk_miles", 0.0)
        avg_risk = best_metrics.get("average_risk_score", 1.0)
        duration_fmt = best_route.get("duration_formatted", "")

        if other_routes:
            other_severes = [r.get("metrics", {}).get("severe_risk_miles", 0.0) for r in other_routes]
            other_highs = [r.get("metrics", {}).get("high_risk_miles", 0.0) for r in other_routes]
            other_no_travel = [r.get("metrics", {}).get("no_travel_miles", 0.0) for r in other_routes]
            other_missing = [
                r.get("metrics", {}).get("has_missing_weather", False) or r.get("metrics", {}).get("unknown_risk_miles", 0.0) > 0
                for r in other_routes
            ]

            if any(ont > 0 for ont in other_no_travel):
                reasons.append("Avoids dangerous No-Travel conditions present on alternative corridors")
            if any(other_missing):
                reasons.append("Provides verified complete atmospheric forecast coverage unlike alternatives")
            if severe < min(other_severes, default=0.0):
                reasons.append(f"Minimizes Severe weather exposure ({severe:.1f} miles vs {min(other_severes):.1f} mi)")
            elif high < min(other_highs, default=0.0):
                reasons.append(f"Minimizes High-risk weather exposure ({high:.1f} miles vs {min(other_highs):.1f} mi)")
            else:
                reasons.append(f"Lowest overall verified risk score ({avg_risk:.2f})")
                reasons.append(f"Optimal travel time ({duration_fmt}) among safest options")
        else:
            reasons.append(f"Only available corridor meeting safety thresholds ({severe:.1f} severe miles)")

        explanation = (
            f"Recommended {best_route['name']} as the safest driving corridor. "
            + ". ".join(reasons)
            + f". Total distance: {best_route['distance_miles']} miles, estimated duration: {duration_fmt}."
        )
    else:
        # No route is eligible for safe travel clearance
        is_any_safe = False
        recommended_route_id = None
        recommended_route = None

        all_no_travel = all(r.get("metrics", {}).get("no_travel_miles", 0.0) > 0 for r in routes)
        all_missing = all(
            (r.get("metrics", {}).get("has_missing_weather", False) or r.get("metrics", {}).get("unknown_risk_miles", 0.0) > 0)
            for r in routes
        )
        all_simulated = all(r.get("is_simulated", False) for r in routes)

        if all_no_travel:
            explanation = (
                "CRITICAL SAFETY WARNING: No route is currently safe for travel under the supplied weather and truck load rules. "
                "All alternative corridors contain segments with active 'No Travel' weather restrictions (severe crosswinds, blizzard, or torrential rainfall). "
                "Dispatch should delay departure until conditions improve."
            )
        elif all_missing:
            explanation = (
                "SAFETY CLEARANCE WITHHELD: Atmospheric forecast data is incomplete or unavailable for all corridors. "
                "Routes cannot be certified safe when required weather data is missing. "
                "Dispatch clearance withheld until forecast data is confirmed."
            )
        elif all_simulated:
            explanation = (
                "DEMONSTRATION ONLY: All alternative routes are based on simulated geometry and have not been verified "
                "by a routing engine over live road networks. Safety clearance withheld."
            )
        else:
            explanation = (
                "SAFETY CLEARANCE WITHHELD: No route meets safe travel clearance criteria. "
                "Alternative corridors either encounter active No-Travel hazards, incomplete atmospheric forecasts, or unverified geometry."
            )

    # Attach recommendation status to every route
    for r in routes:
        r_metrics = r.get("metrics", {})
        r["is_recommended"] = (r["id"] == recommended_route_id) if is_any_safe else False
        r["is_critically_unsafe"] = r_metrics.get("no_travel_miles", 0.0) > 0
        r["has_missing_weather"] = r_metrics.get("has_missing_weather", False) or r_metrics.get("unknown_risk_miles", 0.0) > 0

    return {
        "recommended_route_id": recommended_route_id,
        "recommended_route": recommended_route,
        "is_any_safe": is_any_safe,
        "explanation": explanation,
        "sorted_rankings": [
            {
                "rank": idx + 1,
                "route_id": r["id"],
                "name": r["name"],
                "severe_miles": r.get("metrics", {}).get("severe_risk_miles", 0.0),
                "high_miles": r.get("metrics", {}).get("high_risk_miles", 0.0),
                "no_travel_miles": r.get("metrics", {}).get("no_travel_miles", 0.0),
                "unknown_risk_miles": r.get("metrics", {}).get("unknown_risk_miles", 0.0),
                "has_missing_weather": r.get("metrics", {}).get("has_missing_weather", False),
                "is_simulated": r.get("is_simulated", False),
                "average_risk_score": r.get("metrics", {}).get("average_risk_score", 1.0),
                "duration_formatted": r.get("duration_formatted", ""),
            }
            for idx, r in enumerate(sorted_routes)
        ],
    }
