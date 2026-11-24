"""
Tests for Routing Providers and Fallback Handling.
Covers:
- Real road routing returns is_simulated=False
- FallbackCorridorProvider returns is_simulated=True, is_verified_road_route=False, and simulation_warning
- MultiSourceRoutingManager raises error when real routing fails unless allow_simulated_fallback=True
"""

import pytest
import pytest
from unittest.mock import patch
from routing.services.routing_provider import (
    FallbackCorridorProvider,
    MultiSourceRoutingManager,
    OSRMProvider,
    OpenRouteServiceProvider,
)


class TestFallbackCorridorProvider:
    def test_fallback_explicitly_tagged_as_simulated(self):
        provider = FallbackCorridorProvider()
        start = (41.8781, -87.6298)
        end = (42.3314, -83.0458)

        routes = provider.get_three_routes(start, end, "Chicago, IL", "Detroit, MI")
        assert len(routes) == 3

        for r in routes:
            assert r["is_simulated"] is True
            assert r["is_verified_road_route"] is False
            assert "Simulated Geometry Engine" in r["provider"]
            assert "SIMULATED" in r["simulation_warning"]
            assert len(r["coordinates"]) > 2


class TestMultiSourceRoutingManager:
    @patch.object(OpenRouteServiceProvider, "get_three_routes", return_value=[])
    @patch.object(OSRMProvider, "get_three_routes", return_value=[])
    def test_manager_raises_error_when_real_routing_fails_by_default(self, mock_osrm, mock_ors):
        manager = MultiSourceRoutingManager()
        start = (41.8781, -87.6298)
        end = (42.3314, -83.0458)

        # By default allow_simulated_fallback=False
        with pytest.raises(ValueError) as excinfo:
            manager.get_three_routes(start, end, "Chicago, IL", "Detroit, MI", allow_simulated_fallback=False)

        assert "Routing provider unavailable" in str(excinfo.value)

    @patch.object(OpenRouteServiceProvider, "get_three_routes", return_value=[])
    @patch.object(OSRMProvider, "get_three_routes", return_value=[])
    def test_manager_engages_fallback_only_when_explicitly_allowed(self, mock_osrm, mock_ors):
        manager = MultiSourceRoutingManager()
        start = (41.8781, -87.6298)
        end = (42.3314, -83.0458)

        routes = manager.get_three_routes(start, end, "Chicago, IL", "Detroit, MI", allow_simulated_fallback=True)
        assert len(routes) == 3
        for r in routes:
            assert r["is_simulated"] is True
            assert r["is_verified_road_route"] is False
            assert r["routing_profile"] == "simulated"
            assert r["truck_restrictions_enforced"] is False
            assert "Simulated Corridor" in r["profile_disclosure"]

    def test_identical_geometry_with_different_reported_distances_is_rejected_as_duplicate(self):
        from routing.services.routing_provider import routes_are_substantially_different
        # Identical road coordinates, but different estimated distances (e.g. 100 vs 125 miles)
        r1 = {
            "distance_miles": 100.0,
            "coordinates": [[40.0, -75.0], [40.3, -74.8], [40.6, -74.5], [41.0, -74.0]]
        }
        r2 = {
            "distance_miles": 125.0,
            "coordinates": [[40.0, -75.0], [40.3, -74.8], [40.6, -74.5], [41.0, -74.0]]
        }
        # Distance difference alone is NOT sufficient; identical geometry must be rejected as duplicate
        assert routes_are_substantially_different(r1, r2) is False

    def test_substantially_overlapping_routes_with_minor_variation_rejected(self):
        from routing.services.routing_provider import routes_are_substantially_different
        # Routes share the same highway, diverging by at most 0.02 degrees (~1.2 miles)
        r1 = {
            "distance_miles": 100.0,
            "coordinates": [[40.0, -75.0], [40.3, -74.8], [40.6, -74.5], [41.0, -74.0]]
        }
        r2 = {
            "distance_miles": 102.0,
            "coordinates": [[40.0, -75.0], [40.3, -74.78], [40.6, -74.52], [41.0, -74.0]]
        }
        assert routes_are_substantially_different(r1, r2) is False

    def test_genuinely_distinct_corridors_accepted(self):
        from routing.services.routing_provider import routes_are_substantially_different
        # Route 1 takes a southern highway (lat ~40.0), Route 2 takes a northern highway (lat ~40.6)
        # Divergence is ~40 miles across the corridor
        r1 = {
            "distance_miles": 150.0,
            "coordinates": [
                [40.0, -75.0], [40.0, -74.5], [40.0, -74.0], [40.0, -73.5], [40.5, -73.0]
            ]
        }
        r2 = {
            "distance_miles": 160.0,
            "coordinates": [
                [40.0, -75.0], [40.6, -74.5], [40.6, -74.0], [40.6, -73.5], [40.5, -73.0]
            ]
        }
        assert routes_are_substantially_different(r1, r2) is True

    @patch.object(OpenRouteServiceProvider, "get_three_routes")
    @patch.object(OSRMProvider, "get_three_routes")
    def test_manager_deduplicates_and_reindexes_route_ids(self, mock_osrm, mock_ors):
        # ORS returns 2 routes
        ors_r1 = {
            "id": "route_1",
            "name": "ORS Primary",
            "distance_miles": 280.0,
            "coordinates": [[41.87, -87.62], [42.1, -85.5], [42.33, -83.04]],
            "routing_profile": "driving-hgv",
            "truck_restrictions_enforced": True,
        }
        ors_r2 = {
            "id": "route_2",
            "name": "ORS Alternative",
            "distance_miles": 310.0,
            "coordinates": [[41.87, -87.62], [41.5, -85.2], [42.33, -83.04]],
            "routing_profile": "driving-hgv",
            "truck_restrictions_enforced": True,
        }
        mock_ors.return_value = [ors_r1, ors_r2]

        # OSRM returns 1 duplicate of ors_r1 and 1 distinct corridor
        osrm_dup = {
            "id": "route_1",
            "name": "OSRM Primary Duplicate",
            "distance_miles": 280.2,
            "coordinates": [[41.87, -87.62], [42.1, -85.5], [42.33, -83.04]],
            "routing_profile": "driving (general)",
            "truck_restrictions_enforced": False,
        }
        osrm_distinct = {
            "id": "route_2",
            "name": "OSRM Northern",
            "distance_miles": 340.0,
            "coordinates": [[41.87, -87.62], [42.8, -85.0], [42.33, -83.04]],
            "routing_profile": "driving (general)",
            "truck_restrictions_enforced": False,
        }
        mock_osrm.return_value = [osrm_dup, osrm_distinct]

        manager = MultiSourceRoutingManager()
        routes = manager.get_three_routes((41.87, -87.62), (42.33, -83.04), "Chicago", "Detroit")

        assert len(routes) == 3
        # Unique sequential IDs
        assert [r["id"] for r in routes] == ["route_1", "route_2", "route_3"]
        # Duplicate osrm_dup was dropped; osrm_distinct was included
        names = [r["name"] for r in routes]
        assert "OSRM Primary Duplicate" not in names
        assert "OSRM Northern" in names


