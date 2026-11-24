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


class TestLexicographicalRecommendation:
    def test_priority_1_fewest_severe_miles_beats_shorter_travel_time(self):
        # Route A: 10 miles Severe, 5 hours
        # Route B: 0 miles Severe, 10 hours
        # Lexicographical comparison must recommend Route B even though Route A is 5 hours faster!
        route_a = {
            "id": "route_a",
            "name": "Route A (Faster but Severe)",
            "duration_seconds": 18000.0,  # 5 hours
            "duration_formatted": "5h 0m",
            "distance_miles": 300.0,
            "metrics": {
                "severe_risk_miles": 10.0,
                "high_risk_miles": 0.0,
                "no_travel_miles": 0.0,
                "average_risk_score": 2.5,
            }
        }
        route_b = {
            "id": "route_b",
            "name": "Route B (Slower but 0 Severe)",
            "duration_seconds": 36000.0,  # 10 hours
            "duration_formatted": "10h 0m",
            "distance_miles": 350.0,
            "metrics": {
                "severe_risk_miles": 0.0,
                "high_risk_miles": 50.0,
                "no_travel_miles": 0.0,
                "average_risk_score": 2.2,
            }
        }

        rec = select_recommended_route([route_a, route_b])
        assert rec["recommended_route_id"] == "route_b"
        assert rec["is_any_safe"] is True

    def test_priority_2_fewest_high_miles_when_severe_tied(self):
        # Both have 0 Severe miles
        # Route A: 20 miles High
        # Route B: 5 miles High
        # Route B must win
        route_a = {
            "id": "route_a",
            "name": "Route A",
            "duration_seconds": 20000.0,
            "duration_formatted": "5h 33m",
            "distance_miles": 300.0,
            "metrics": {
                "severe_risk_miles": 0.0,
                "high_risk_miles": 20.0,
                "no_travel_miles": 0.0,
                "average_risk_score": 1.8,
            }
        }
        route_b = {
            "id": "route_b",
            "name": "Route B",
            "duration_seconds": 22000.0,
            "duration_formatted": "6h 6m",
            "distance_miles": 310.0,
            "metrics": {
                "severe_risk_miles": 0.0,
                "high_risk_miles": 5.0,
                "no_travel_miles": 0.0,
                "average_risk_score": 1.5,
            }
        }
        rec = select_recommended_route([route_a, route_b])
        assert rec["recommended_route_id"] == "route_b"

    def test_priority_3_and_4_average_risk_and_travel_time(self):
        # Identical Severe (0) and High (0)
        # Route A: 1.2 average risk score
        # Route B: 1.5 average risk score
        route_a = {
            "id": "route_a",
            "name": "Route A",
            "duration_seconds": 20000.0,
            "duration_formatted": "5h 33m",
            "distance_miles": 300.0,
            "metrics": {
                "severe_risk_miles": 0.0,
                "high_risk_miles": 0.0,
                "no_travel_miles": 0.0,
                "average_risk_score": 1.2,
            }
        }
        route_b = {
            "id": "route_b",
            "name": "Route B",
            "duration_seconds": 18000.0,
            "duration_formatted": "5h 0m",
            "distance_miles": 290.0,
            "metrics": {
                "severe_risk_miles": 0.0,
                "high_risk_miles": 0.0,
                "no_travel_miles": 0.0,
                "average_risk_score": 1.5,
            }
        }
        rec = select_recommended_route([route_a, route_b])
        assert rec["recommended_route_id"] == "route_a"

    def test_no_travel_hard_constraint(self):
        # Route A has No-Travel segments (disqualified)
        # Route B is safe
        route_a = {
            "id": "route_a",
            "name": "Route A (No Travel Danger)",
            "duration_seconds": 10000.0,
            "duration_formatted": "2h 46m",
            "distance_miles": 150.0,
            "metrics": {
                "severe_risk_miles": 0.0,
                "high_risk_miles": 0.0,
                "no_travel_miles": 15.0,
                "average_risk_score": 2.0,
            }
        }
        route_b = {
            "id": "route_b",
            "name": "Route B (Safe Route)",
            "duration_seconds": 30000.0,
            "duration_formatted": "8h 20m",
            "distance_miles": 400.0,
            "metrics": {
                "severe_risk_miles": 5.0,
                "high_risk_miles": 20.0,
                "no_travel_miles": 0.0,
                "average_risk_score": 2.3,
            }
        }
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
        r1 = {
            "id": "r1", "name": "R1", "duration_seconds": 10000.0, "distance_miles": 200.0,
            "metrics": {"severe_risk_miles": 0.0, "high_risk_miles": 10.0, "no_travel_miles": 0.0, "unknown_risk_miles": 0.0, "has_missing_weather": False, "average_risk_score": 1.8}
        }
        r2 = {
            "id": "r2", "name": "R2", "duration_seconds": 12000.0, "distance_miles": 210.0,
            "metrics": {"severe_risk_miles": 0.0, "high_risk_miles": 10.0, "no_travel_miles": 0.0, "unknown_risk_miles": 0.0, "has_missing_weather": False, "average_risk_score": 1.5}
        }
        r3 = {
            "id": "r3", "name": "R3", "duration_seconds": 8000.0, "distance_miles": 190.0,
            "metrics": {"severe_risk_miles": 5.0, "high_risk_miles": 0.0, "no_travel_miles": 0.0, "unknown_risk_miles": 0.0, "has_missing_weather": False, "average_risk_score": 1.2}
        }
        rec = select_recommended_route([r1, r2, r3])
        assert rec["is_any_safe"] is True
        assert rec["recommended_route_id"] == "r2"
        # Rankings order: r2 (0 severe, 10 high, 1.5 avg), r1 (0 severe, 10 high, 1.8 avg), r3 (5 severe)
        ranking_ids = [item["route_id"] for item in rec["sorted_rankings"]]
        assert ranking_ids == ["r2", "r1", "r3"]



