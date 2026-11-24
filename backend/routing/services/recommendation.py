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


def route_sort_key(route: Dict[str, Any]) -> Tuple[int, int, int, float, float, float, float, float]:
    """
    Lexicographical sort key for route recommendation:
    (
        has_no_travel (0=safe, 1=unsafe),
        has_missing_weather (0=complete data, 1=missing data),
        is_simulated (0=verified road route, 1=simulated),
        severe_risk_miles,
        high_risk_miles,
        unknown_risk_miles,
        average_risk_score,
        duration_seconds
    )
    """
    metrics = route.get("metrics", {})
    no_travel = metrics.get("no_travel_miles", 0.0)
    has_no_travel = 1 if no_travel > 0.0 else 0
    has_missing_weather = 1 if (metrics.get("has_missing_weather", False) or metrics.get("unknown_risk_miles", 0.0) > 0) else 0
    is_simulated = 1 if route.get("is_simulated", False) else 0

    severe = metrics.get("severe_risk_miles", 0.0)
    high = metrics.get("high_risk_miles", 0.0)
    unknown = metrics.get("unknown_risk_miles", 0.0)
    avg_score = metrics.get("average_risk_score", 1.0)
    duration = route.get("duration_seconds", 0.0)

    return (
        has_no_travel,
        has_missing_weather,
        is_simulated,
        severe,
        high,
        unknown,
        avg_score,
        duration,
    )


def select_recommended_route(routes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compare routes lexicographically and select the recommended route.
    Never marks a route as safe if required weather data is missing or if the route is simulated.
    """
    if not routes:
        return {
            "recommended_route_id": None,
            "recommended_route": None,
            "is_any_safe": False,
            "explanation": "No routes available for analysis.",
            "comparisons": [],
        }

    sorted_routes = sorted(routes, key=route_sort_key)
    best_route = sorted_routes[0]
    best_metrics = best_route.get("metrics", {})
    best_no_travel = best_metrics.get("no_travel_miles", 0.0)
    best_missing = best_metrics.get("has_missing_weather", False) or best_metrics.get("unknown_risk_miles", 0.0) > 0
    best_simulated = best_route.get("is_simulated", False)

    all_no_travel = all(r.get("metrics", {}).get("no_travel_miles", 0.0) > 0 for r in routes)
    all_missing_weather = all(
        (r.get("metrics", {}).get("has_missing_weather", False) or r.get("metrics", {}).get("unknown_risk_miles", 0.0) > 0)
        for r in routes
    )

    if all_no_travel:
        explanation = (
            "CRITICAL SAFETY WARNING: No route is currently safe for travel under the supplied weather and truck load rules. "
            "All alternative corridors contain segments with active 'No Travel' weather restrictions (severe crosswinds, blizzard, or torrential rainfall). "
            "Dispatch should delay departure until conditions improve."
        )
        is_any_safe = False
    elif best_no_travel > 0:
        explanation = (
            "No completely safe route is available. The best route still encounters No-Travel weather hazards. "
            "Travel is strongly discouraged."
        )
        is_any_safe = False
    elif best_missing:
        unknown_mi = best_metrics.get("unknown_risk_miles", 0.0)
        loc_str = f"for {unknown_mi:.1f} miles along {best_route['name']}" if unknown_mi > 0 else f"at one or more checkpoints along {best_route['name']}"
        explanation = (
            f"SAFETY CLEARANCE WITHHELD: Atmospheric forecast data is incomplete or unavailable {loc_str}. "
            "Routes cannot be certified safe when required weather data is missing. "
            "Dispatch clearance withheld until forecast data is confirmed."
        )
        is_any_safe = False
    elif best_simulated:
        explanation = (
            f"DEMONSTRATION ONLY: {best_route['name']} is based on simulated geometry and has not been verified "
            "by a routing engine over live road networks. Not approved for active navigation."
        )
        is_any_safe = False
    else:
        is_any_safe = True
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
            reasons.append(f"Only available path meeting safety thresholds ({severe:.1f} severe miles)")

        explanation = (
            f"Recommended {best_route['name']} as the safest driving corridor. "
            + ". ".join(reasons)
            + f". Total distance: {best_route['distance_miles']} miles, estimated duration: {duration_fmt}."
        )

    # Attach recommendation status to every route
    for r in routes:
        r_metrics = r.get("metrics", {})
        r["is_recommended"] = (r["id"] == best_route["id"]) if is_any_safe else False
        r["is_critically_unsafe"] = r_metrics.get("no_travel_miles", 0.0) > 0
        r["has_missing_weather"] = r_metrics.get("has_missing_weather", False) or r_metrics.get("unknown_risk_miles", 0.0) > 0

    return {
        "recommended_route_id": best_route["id"] if is_any_safe else None,
        "recommended_route": best_route if is_any_safe else None,
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
