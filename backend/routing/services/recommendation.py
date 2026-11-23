"""
Route Recommendation Algorithm Service.

Implements the exact lexicographical priority comparison required by Section 9:
1. Hard constraint: No-Travel routes disqualified from normal recommendation
2. Priority 1: Fewest Severe miles
3. Priority 2: Fewest High miles
4. Priority 3: Lowest average risk score
5. Priority 4: Shortest travel time (tie-breaker)
"""

from typing import List, Dict, Any, Tuple


def route_sort_key(route: Dict[str, Any]) -> Tuple[int, float, float, float, float, float]:
    """
    Lexicographical sort key for route recommendation:
    (
        has_no_travel: 0 for safe, 1 for unsafe,
        no_travel_miles: float,
        severe_risk_miles: float,
        high_risk_miles: float,
        average_risk_score: float,
        duration_seconds: float
    )
    """
    metrics = route.get("metrics", {})
    no_travel = metrics.get("no_travel_miles", 0.0)
    has_no_travel = 1 if no_travel > 0.0 else 0
    severe = metrics.get("severe_risk_miles", 0.0)
    high = metrics.get("high_risk_miles", 0.0)
    avg_score = metrics.get("average_risk_score", 1.0)
    duration = route.get("duration_seconds", 0.0)

    return (
        has_no_travel,
        no_travel,
        severe,
        high,
        avg_score,
        duration,
    )


def select_recommended_route(routes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compare routes lexicographically and select the recommended route.
    
    Returns a dict containing:
    - recommended_route_id: str | None
    - recommended_route: dict | None
    - is_any_safe: bool
    - explanation: str
    - comparisons: list of route comparisons
    """
    if not routes:
        return {
            "recommended_route_id": None,
            "recommended_route": None,
            "is_any_safe": False,
            "explanation": "No routes available for analysis.",
            "comparisons": [],
        }

    # Sort routes using the exact lexicographical hierarchy
    sorted_routes = sorted(routes, key=route_sort_key)
    best_route = sorted_routes[0]
    best_metrics = best_route.get("metrics", {})
    best_no_travel = best_metrics.get("no_travel_miles", 0.0)

    # Check if all routes have No-Travel conditions
    all_no_travel = all(r.get("metrics", {}).get("no_travel_miles", 0.0) > 0 for r in routes)

    if all_no_travel:
        explanation = (
            "CRITICAL SAFETY WARNING: No route is currently safe for travel under the supplied weather and truck load rules. "
            "All alternative routes contain segments with active 'No Travel' weather restrictions (severe crosswinds, blizzard, or torrential rainfall). "
            "Dispatch should delay departure until conditions improve."
        )
        is_any_safe = False
    elif best_no_travel > 0:
        explanation = (
            "No completely safe route is available. The best route still encounters No-Travel weather hazards. "
            "Travel is strongly discouraged."
        )
        is_any_safe = False
    else:
        is_any_safe = True
        # Build explanation of why best_route won
        reasons = []
        other_routes = [r for r in routes if r["id"] != best_route["id"]]
        
        severe = best_metrics.get("severe_risk_miles", 0.0)
        high = best_metrics.get("high_risk_miles", 0.0)
        avg_risk = best_metrics.get("average_risk_score", 1.0)
        duration_fmt = best_route.get("duration_formatted", "")

        # Compare with competitors
        if other_routes:
            other_severes = [r.get("metrics", {}).get("severe_risk_miles", 0.0) for r in other_routes]
            other_highs = [r.get("metrics", {}).get("high_risk_miles", 0.0) for r in other_routes]
            other_no_travel = [r.get("metrics", {}).get("no_travel_miles", 0.0) for r in other_routes]

            if any(ont > 0 for ont in other_no_travel):
                reasons.append("Avoids dangerous No-Travel conditions present on alternative corridors")
            elif severe < min(other_severes, default=0.0):
                reasons.append(f"Minimizes Severe weather exposure ({severe:.1f} miles vs {min(other_severes):.1f} mi)")
            elif high < min(other_highs, default=0.0):
                reasons.append(f"Minimizes High-risk weather exposure ({high:.1f} miles vs {min(other_highs):.1f} mi)")
            else:
                reasons.append(f"Lowest overall risk score ({avg_risk:.2f})")
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
        r["is_recommended"] = (r["id"] == best_route["id"]) if is_any_safe else False
        r["is_critically_unsafe"] = r.get("metrics", {}).get("no_travel_miles", 0.0) > 0

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
                "average_risk_score": r.get("metrics", {}).get("average_risk_score", 1.0),
                "duration_formatted": r.get("duration_formatted", ""),
            }
            for idx, r in enumerate(sorted_routes)
        ],
    }
