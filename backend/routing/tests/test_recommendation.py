"""
Tests for Route Analysis Metrics and Lexicographical Recommendation Algorithm.
Covers:
- Risk-miles segment attribution
- Lexicographical sorting order (Severe miles -> High miles -> Avg risk -> Travel time)
- Hard safety constraint disqualifying No-Travel routes
- Handling scenario where all routes contain No-Travel hazards
"""

import pytest
from routing.services.route_analyzer import analyze_route_metrics
from routing.services.recommendation import select_recommended_route, route_sort_key
from routing.services.risk_engine import (
    RISK_LOW,
    RISK_MODERATE,
    RISK_HIGH,
    RISK_SEVERE,
    RISK_NO_TRAVEL,
)


class TestRouteMetricsAndAttribution:
    def test_segment_attribution_conservative_rule(self):
        # 3 checkpoints:
        # cp_0 (0 mi, Low), cp_1 (50 mi, High), cp_2 (100 mi, Low)
        # Segment 0..50 has Low and High -> attributed as High (50 mi)
        # Segment 50..100 has High and Low -> attributed as High (50 mi)
        route = {"distance_miles": 100.0, "duration_seconds": 7200.0}
        checkpoints = [
            {"id": "cp_0", "distance_from_origin_miles": 0.0, "latitude": 40.0, "longitude": -75.0, "final_risk": RISK_LOW},
            {"id": "cp_1", "distance_from_origin_miles": 50.0, "latitude": 40.5, "longitude": -75.5, "final_risk": RISK_HIGH},
            {"id": "cp_2", "distance_from_origin_miles": 100.0, "latitude": 41.0, "longitude": -76.0, "final_risk": RISK_LOW},
        ]
        metrics = analyze_route_metrics(route, checkpoints)

        assert metrics["high_risk_miles"] == 100.0
        assert metrics["low_risk_miles"] == 0.0
        assert metrics["severe_risk_miles"] == 0.0
        assert metrics["no_travel_miles"] == 0.0
        assert metrics["is_safe_for_travel"] is True
        assert metrics["overall_route_risk"] == RISK_HIGH


def make_test_route(
    route_id: str,
    name: str,
    duration_seconds: float,
    distance_miles: float,
    severe_risk_miles: float = 0.0,
    high_risk_miles: float = 0.0,
    no_travel_miles: float = 0.0,
    unknown_risk_miles: float = 0.0,
    average_risk_score: float = 1.0,
    has_missing_weather: bool = False,
    is_safe_for_travel: bool = True,
    is_simulated: bool = False,
    is_verified_road_route: bool = True,
    duration_formatted: str = "",
) -> dict:
    if duration_formatted == "":
        try:
            import math
            if isinstance(duration_seconds, (int, float)) and math.isfinite(duration_seconds):
                duration_formatted = f"{int(duration_seconds // 3600)}h {int((duration_seconds % 3600) // 60)}m"
            else:
                duration_formatted = str(duration_seconds)
        except Exception:
            duration_formatted = str(duration_seconds)

    return {
        "id": route_id,
        "name": name,
        "duration_seconds": duration_seconds,
        "duration_formatted": duration_formatted,
        "distance_miles": distance_miles,
        "is_simulated": is_simulated,
        "is_verified_road_route": is_verified_road_route,
        "metrics": {
            "severe_risk_miles": severe_risk_miles,
            "high_risk_miles": high_risk_miles,
            "no_travel_miles": no_travel_miles,
            "unknown_risk_miles": unknown_risk_miles,
            "has_missing_weather": has_missing_weather,
            "average_risk_score": average_risk_score,
            "is_safe_for_travel": is_safe_for_travel,
        }
    }


class TestLexicographicalRecommendation:
    def test_priority_1_fewest_severe_miles_beats_shorter_travel_time(self):
        # Route A: 10 miles Severe, 5 hours
        # Route B: 0 miles Severe, 10 hours
        # Lexicographical comparison must recommend Route B even though Route A is 5 hours faster!
        route_a = make_test_route(
            "route_a", "Route A (Faster but Severe)", 18000.0, 300.0,
            severe_risk_miles=10.0, high_risk_miles=0.0, average_risk_score=2.5
        )
        route_b = make_test_route(
            "route_b", "Route B (Slower but 0 Severe)", 36000.0, 350.0,
            severe_risk_miles=0.0, high_risk_miles=50.0, average_risk_score=2.2
        )

        rec = select_recommended_route([route_a, route_b])
        assert rec["recommended_route_id"] == "route_b"
        assert rec["is_any_safe"] is True

    def test_priority_2_fewest_high_miles_when_severe_tied(self):
        # Both have 0 Severe miles
        # Route A: 20 miles High
        # Route B: 5 miles High
        # Route B must win
        route_a = make_test_route(
            "route_a", "Route A", 20000.0, 300.0,
            severe_risk_miles=0.0, high_risk_miles=20.0, average_risk_score=1.8
        )
        route_b = make_test_route(
            "route_b", "Route B", 22000.0, 310.0,
            severe_risk_miles=0.0, high_risk_miles=5.0, average_risk_score=1.5
        )
        rec = select_recommended_route([route_a, route_b])
        assert rec["recommended_route_id"] == "route_b"

    def test_priority_3_and_4_average_risk_and_travel_time(self):
        # Identical Severe (0) and High (0)
        # Route A: 1.2 average risk score
        # Route B: 1.5 average risk score
        route_a = make_test_route(
            "route_a", "Route A", 20000.0, 300.0,
            severe_risk_miles=0.0, high_risk_miles=0.0, average_risk_score=1.2
        )
        route_b = make_test_route(
            "route_b", "Route B", 18000.0, 290.0,
            severe_risk_miles=0.0, high_risk_miles=0.0, average_risk_score=1.5
        )
        rec = select_recommended_route([route_a, route_b])
        assert rec["recommended_route_id"] == "route_a"

    def test_no_travel_hard_constraint(self):
        # Route A has No-Travel segments (disqualified)
        # Route B is safe
        route_a = make_test_route(
            "route_a", "Route A (No Travel Danger)", 10000.0, 150.0,
            no_travel_miles=15.0, average_risk_score=2.0, is_safe_for_travel=False
        )
        route_b = make_test_route(
            "route_b", "Route B (Safe Route)", 30000.0, 400.0,
            severe_risk_miles=5.0, high_risk_miles=20.0, average_risk_score=2.3, is_safe_for_travel=True
        )
        rec = select_recommended_route([route_a, route_b])
        assert rec["recommended_route_id"] == "route_b"
        assert rec["is_any_safe"] is True


    def test_all_routes_no_travel_warning(self):
        # If all routes have No-Travel conditions
        route_1 = {
            "id": "r1", "name": "R1", "duration_seconds": 10000, "metrics": {"no_travel_miles": 5.0, "severe_risk_miles": 0.0, "high_risk_miles": 0.0}
        }
        route_2 = {
            "id": "r2", "name": "R2", "duration_seconds": 12000, "metrics": {"no_travel_miles": 10.0, "severe_risk_miles": 0.0, "high_risk_miles": 0.0}
        }
        rec = select_recommended_route([route_1, route_2])
        assert rec["is_any_safe"] is False
        assert rec["recommended_route_id"] is None
        assert "CRITICAL SAFETY WARNING: No route is currently safe" in rec["explanation"]

    def test_route_with_missing_weather_not_marked_safe(self):
        # Route has missing weather data -> cannot be marked safe
        route_missing = {
            "id": "r_missing",
            "name": "Route With Missing Data",
            "duration_seconds": 10000,
            "has_missing_weather": True,
            "metrics": {
                "severe_risk_miles": 0.0,
                "high_risk_miles": 0.0,
                "no_travel_miles": 0.0,
                "unknown_risk_miles": 25.0,
                "average_risk_score": 1.0,
            }
        }
        rec = select_recommended_route([route_missing])
        assert rec["is_any_safe"] is False
        assert "incomplete" in rec["explanation"].lower() or "missing" in rec["explanation"].lower() or "unavailable" in rec["explanation"].lower()

    def test_simulated_route_not_marked_safe(self):
        # Route is simulated geometry fallback -> cannot be certified safe
        route_sim = {
            "id": "r_sim",
            "name": "Simulated Route",
            "duration_seconds": 10000,
            "is_simulated": True,
            "metrics": {
                "severe_risk_miles": 0.0,
                "high_risk_miles": 0.0,
                "no_travel_miles": 0.0,
                "unknown_risk_miles": 0.0,
                "average_risk_score": 1.0,
            }
        }
        rec = select_recommended_route([route_sim])
        assert rec["is_any_safe"] is False
        assert "simulated" in rec["explanation"].lower()

    def test_partial_missing_weather_never_receives_safe_travel_clearance(self):
        # Checkpoints where one checkpoint has partial missing weather (e.g. wind=10, rain=None, snow=0)
        route = {"id": "route_partial", "name": "Corridor Alpha", "distance_miles": 100.0, "duration_seconds": 7200.0}
        checkpoints = [
            {
                "id": "cp_0",
                "distance_from_origin_miles": 0.0,
                "latitude": 40.0,
                "longitude": -75.0,
                "final_risk": RISK_LOW,
                "forecast_available": True,
            },
            {
                "id": "cp_1",
                "distance_from_origin_miles": 50.0,
                "latitude": 40.5,
                "longitude": -75.5,
                "final_risk": "Data Unavailable",
                "forecast_available": False,  # Missing rain
            },
            {
                "id": "cp_2",
                "distance_from_origin_miles": 100.0,
                "latitude": 41.0,
                "longitude": -76.0,
                "final_risk": RISK_LOW,
                "forecast_available": True,
            },
        ]
        metrics = analyze_route_metrics(route, checkpoints)
        assert metrics["has_missing_weather"] is True
        assert metrics["is_safe_for_travel"] is False
        assert metrics["unknown_risk_miles"] > 0.0

        route["metrics"] = metrics
        rec = select_recommended_route([route])
        assert rec["is_any_safe"] is False
        assert "SAFETY CLEARANCE WITHHELD" in rec["explanation"]

    def test_partial_missing_weather_with_moderate_hazard_still_withholds_safety_clearance(self):
        # Checkpoint has wind=30 mph (Moderate), but snow is missing (forecast_available=False)
        route = {"id": "route_mod_missing", "name": "Corridor Beta", "distance_miles": 100.0, "duration_seconds": 7200.0}
        checkpoints = [
            {
                "id": "cp_0",
                "distance_from_origin_miles": 0.0,
                "latitude": 40.0,
                "longitude": -75.0,
                "final_risk": RISK_LOW,
                "forecast_available": True,
            },
            {
                "id": "cp_1",
                "distance_from_origin_miles": 100.0,
                "latitude": 41.0,
                "longitude": -76.0,
                "final_risk": RISK_MODERATE,
                "forecast_available": False,  # Moderate wind, but snow missing
            },
        ]
        metrics = analyze_route_metrics(route, checkpoints)
        assert metrics["has_missing_weather"] is True
        assert metrics["is_safe_for_travel"] is False

        route["metrics"] = metrics
        rec = select_recommended_route([route])
        assert rec["is_any_safe"] is False
        assert "SAFETY CLEARANCE WITHHELD" in rec["explanation"]

    def test_strict_four_tuple_ranking_for_eligible_routes(self):
        # 3 eligible routes:
        # Route 1: severe=0, high=10, avg=1.8, dur=10000
        # Route 2: severe=0, high=10, avg=1.5, dur=12000 (wins on avg_score)
        # Route 3: severe=5, high=0,  avg=1.2, dur=8000  (loses on severe)
        r1 = make_test_route("r1", "R1", 10000.0, 200.0, severe_risk_miles=0.0, high_risk_miles=10.0, average_risk_score=1.8)
        r2 = make_test_route("r2", "R2", 12000.0, 210.0, severe_risk_miles=0.0, high_risk_miles=10.0, average_risk_score=1.5)
        r3 = make_test_route("r3", "R3", 8000.0, 190.0, severe_risk_miles=5.0, high_risk_miles=0.0, average_risk_score=1.2)
        rec = select_recommended_route([r1, r2, r3])
        assert rec["is_any_safe"] is True
        assert rec["recommended_route_id"] == "r2"
        # Rankings order: r2 (0 severe, 10 high, 1.5 avg), r1 (0 severe, 10 high, 1.8 avg), r3 (5 severe)
        ranking_ids = [item["route_id"] for item in rec["sorted_rankings"]]
        assert ranking_ids == ["r2", "r1", "r3"]


class TestFailClosedRecommendationEligibility:
    """
    Regression tests for Issue 2: Fail-closed recommendation eligibility.
    Missing or invalid required safety fields must strictly disqualify the route.
    """

    def test_missing_or_empty_metrics_disqualifies_route(self):
        from routing.services.recommendation import is_route_eligible
        r_no_metrics = {"id": "r1", "duration_seconds": 1000, "is_verified_road_route": True, "is_simulated": False}
        assert is_route_eligible(r_no_metrics) is False

        r_empty_metrics = {
            "id": "r1", "duration_seconds": 1000, "is_verified_road_route": True, "is_simulated": False, "metrics": {}
        }
        assert is_route_eligible(r_empty_metrics) is False

    def test_unverified_road_route_disqualifies_route(self):
        from routing.services.recommendation import is_route_eligible
        r = make_test_route("r1", "R1", 1000, 50, is_verified_road_route=False)
        assert is_route_eligible(r) is False

        r_none = make_test_route("r1", "R1", 1000, 50)
        del r_none["is_verified_road_route"]
        assert is_route_eligible(r_none) is False

    def test_simulated_geometry_disqualifies_route(self):
        from routing.services.recommendation import is_route_eligible
        r = make_test_route("r1", "R1", 1000, 50, is_simulated=True)
        assert is_route_eligible(r) is False

        r_missing = make_test_route("r1", "R1", 1000, 50)
        del r_missing["is_simulated"]
        assert is_route_eligible(r_missing) is False

    def test_missing_weather_flag_disqualifies_route(self):
        from routing.services.recommendation import is_route_eligible
        r = make_test_route("r1", "R1", 1000, 50, has_missing_weather=True)
        assert is_route_eligible(r) is False

    def test_non_zero_unknown_risk_miles_disqualifies_route(self):
        from routing.services.recommendation import is_route_eligible
        r = make_test_route("r1", "R1", 1000, 50, unknown_risk_miles=15.0)
        assert is_route_eligible(r) is False

    def test_non_zero_no_travel_miles_disqualifies_route(self):
        from routing.services.recommendation import is_route_eligible
        r = make_test_route("r1", "R1", 1000, 50, no_travel_miles=5.0)
        assert is_route_eligible(r) is False

    def test_missing_safety_clearance_flag_disqualifies_route(self):
        from routing.services.recommendation import is_route_eligible
        r = make_test_route("r1", "R1", 1000, 50, is_safe_for_travel=False)
        assert is_route_eligible(r) is False

    def test_invalid_duration_disqualifies_route(self):
        from routing.services.recommendation import is_route_eligible
        r_zero = make_test_route("r1", "R1", 0.0, 50)
        assert is_route_eligible(r_zero) is False

        r_neg = make_test_route("r1", "R1", -100.0, 50)
        assert is_route_eligible(r_neg) is False

    def test_nan_in_numeric_metrics_disqualifies_route(self):
        from routing.services.recommendation import is_route_eligible
        nan = float("nan")

        assert is_route_eligible(make_test_route("r1", "R1", nan, 50)) is False
        assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, severe_risk_miles=nan)) is False
        assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, high_risk_miles=nan)) is False
        assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, average_risk_score=nan)) is False
        assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, unknown_risk_miles=nan)) is False
        assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, no_travel_miles=nan)) is False

    def test_infinity_in_numeric_metrics_disqualifies_route(self):
        from routing.services.recommendation import is_route_eligible
        pos_inf = float("inf")
        neg_inf = float("-inf")

        for inf_val in (pos_inf, neg_inf):
            assert is_route_eligible(make_test_route("r1", "R1", inf_val, 50)) is False
            assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, severe_risk_miles=inf_val)) is False
            assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, high_risk_miles=inf_val)) is False
            assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, average_risk_score=inf_val)) is False
            assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, unknown_risk_miles=inf_val)) is False
            assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, no_travel_miles=inf_val)) is False

    def test_boolean_values_in_numeric_metrics_disqualifies_route(self):
        from routing.services.recommendation import is_route_eligible

        # In Python, isinstance(True, int) is True, but booleans are NOT valid mileage or durations
        assert is_route_eligible(make_test_route("r1", "R1", True, 50)) is False  # type: ignore
        assert is_route_eligible(make_test_route("r1", "R1", False, 50)) is False  # type: ignore
        assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, severe_risk_miles=True)) is False  # type: ignore
        assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, high_risk_miles=True)) is False  # type: ignore
        assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, average_risk_score=True)) is False  # type: ignore
        # Even though False == 0.0 in Python, False is a boolean and must be disqualified!
        assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, unknown_risk_miles=False)) is False  # type: ignore
        assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, no_travel_miles=False)) is False  # type: ignore

    def test_negative_numeric_metrics_disqualify_route(self):
        from routing.services.recommendation import is_route_eligible

        assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, severe_risk_miles=-1.0)) is False
        assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, high_risk_miles=-5.0)) is False
        assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, average_risk_score=-0.5)) is False
        assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, unknown_risk_miles=-10.0)) is False
        assert is_route_eligible(make_test_route("r1", "R1", 1000, 50, no_travel_miles=-2.0)) is False



class TestUnknownWeatherMileageAccounting:
    """
    Regression tests for Issue 3: Separately track miles affected by incomplete/unavailable
    weather data without counting them as fully verified Low, Moderate, High, or Severe exposure.
    Preserve known hazards (No Travel or Severe) during partial weather data.
    """

    def test_partial_weather_preserves_severe_hazard_without_verified_exposure_count(self):
        # 100-mile corridor: cp_0..cp_1 has 50 miles of Severe wind (48 mph), but rain is None
        route = {"id": "r_partial_sev", "name": "Severe Partial", "distance_miles": 100.0, "duration_seconds": 7200.0}
        checkpoints = [
            {
                "id": "cp_0", "distance_from_origin_miles": 0.0, "latitude": 40.0, "longitude": -75.0,
                "final_risk": RISK_SEVERE, "forecast_available": False  # Severe wind, but rain missing
            },
            {
                "id": "cp_1", "distance_from_origin_miles": 50.0, "latitude": 40.5, "longitude": -75.5,
                "final_risk": RISK_LOW, "forecast_available": False  # Low wind, but rain missing
            },
            {
                "id": "cp_2", "distance_from_origin_miles": 100.0, "latitude": 41.0, "longitude": -76.0,
                "final_risk": RISK_LOW, "forecast_available": True
            },
        ]

        metrics = analyze_route_metrics(route, checkpoints)

        # 1. Miles affected by incomplete weather are tracked in unknown_risk_miles
        assert metrics["unknown_risk_miles"] == 100.0
        # 2. Incomplete miles are NOT counted as verified severe exposure
        assert metrics["severe_risk_miles"] == 0.0
        assert metrics["verified_severe_risk_miles"] == 0.0
        # 3. Known severe hazard is preserved
        assert metrics["known_hazard_severe_miles"] == 50.0
        assert metrics["partial_data_hazard_miles"] == 50.0
        assert metrics["overall_route_risk"] == RISK_SEVERE  # Not hidden as Data Unavailable
        # 4. Safe travel clearance is withheld
        assert metrics["is_safe_for_travel"] is False
        assert metrics["has_missing_weather"] is True

    def test_partial_weather_preserves_no_travel_hazard(self):
        # 60-mile corridor with 60 mph hurricane wind, but snow is None
        route = {"id": "r_partial_nt", "name": "No Travel Partial", "distance_miles": 60.0, "duration_seconds": 3600.0}
        checkpoints = [
            {
                "id": "cp_0", "distance_from_origin_miles": 0.0, "latitude": 40.0, "longitude": -75.0,
                "final_risk": RISK_NO_TRAVEL, "forecast_available": False
            },
            {
                "id": "cp_1", "distance_from_origin_miles": 60.0, "latitude": 40.5, "longitude": -75.5,
                "final_risk": RISK_NO_TRAVEL, "forecast_available": False
            },
        ]
        metrics = analyze_route_metrics(route, checkpoints)

        # No Travel condition is preserved
        assert metrics["no_travel_miles"] == 60.0
        assert metrics["unknown_risk_miles"] == 60.0
        assert metrics["overall_route_risk"] == RISK_NO_TRAVEL
        assert metrics["is_safe_for_travel"] is False

    def test_partial_weather_with_moderate_wind_preserves_moderate_hazard(self):
        # 100-mile corridor with 30 mph wind (Moderate), but rain is missing
        route = {"id": "r_partial_mod", "name": "Moderate Partial", "distance_miles": 100.0, "duration_seconds": 7200.0}
        checkpoints = [
            {
                "id": "cp_0", "distance_from_origin_miles": 0.0, "latitude": 40.0, "longitude": -75.0,
                "final_risk": RISK_MODERATE, "forecast_available": False
            },
            {
                "id": "cp_1", "distance_from_origin_miles": 100.0, "latitude": 41.0, "longitude": -76.0,
                "final_risk": RISK_MODERATE, "forecast_available": False
            },
        ]
        metrics = analyze_route_metrics(route, checkpoints)

        # Tracked as unknown miles, NOT as verified moderate exposure
        assert metrics["unknown_risk_miles"] == 100.0
        assert metrics["moderate_risk_miles"] == 0.0
        assert metrics["verified_moderate_risk_miles"] == 0.0
        # Preserved hazard
        assert metrics["known_hazard_moderate_miles"] == 100.0
        assert metrics["overall_route_risk"] == RISK_MODERATE
        assert metrics["is_safe_for_travel"] is False

    def test_all_low_conditions_with_missing_variable_classifies_as_data_unavailable(self):
        # 80-mile corridor: all measurements Low, but rain is None -> final_risk is Data Unavailable
        from routing.services.risk_engine import RISK_UNKNOWN
        route = {"id": "r_low_missing", "name": "Low Missing", "distance_miles": 80.0, "duration_seconds": 4800.0}
        checkpoints = [
            {
                "id": "cp_0", "distance_from_origin_miles": 0.0, "latitude": 40.0, "longitude": -75.0,
                "final_risk": RISK_UNKNOWN, "forecast_available": False
            },
            {
                "id": "cp_1", "distance_from_origin_miles": 80.0, "latitude": 41.0, "longitude": -76.0,
                "final_risk": RISK_UNKNOWN, "forecast_available": False
            },
        ]
        metrics = analyze_route_metrics(route, checkpoints)

        assert metrics["unknown_risk_miles"] == 80.0
        assert metrics["low_risk_miles"] == 0.0
        assert metrics["overall_route_risk"] == RISK_UNKNOWN  # Missing data is never classified as Low
        assert metrics["is_safe_for_travel"] is False




