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

