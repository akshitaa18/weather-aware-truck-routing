"""
Tests for Checkpoint Generation along Route Geometry.
Covers:
- Polyline distance calculation and interpolation
- Checkpoint generation at 10, 25, 50 mile intervals
- Mandatory destination checkpoint inclusion
- Avoidance of duplicate checkpoints
"""

import pytest
from routing.services.checkpoint_generator import (
    haversine_distance_miles,
    generate_checkpoints,
)


def create_straight_test_polyline(total_miles: float, segments: int = 10):
    """
    Creates a simulated polyline spanning approximately `total_miles`
    along latitude for deterministic testing.
    1 degree latitude is approx 69 miles.
    """
    deg_per_mile = 1.0 / 69.0
    start_lat = 40.0
    start_lon = -75.0
    coords = []
    for i in range(segments + 1):
        frac = i / segments
        lat = start_lat + (frac * total_miles * deg_per_mile)
        coords.append([lat, start_lon])
    return coords


class TestCheckpointGenerator:
    def test_haversine_distance_basic(self):
        # Distance between (40.0, -75.0) and (41.0, -75.0) is approx 69 miles
        d = haversine_distance_miles(40.0, -75.0, 41.0, -75.0)
        assert 68.0 < d < 70.0

    def test_checkpoints_at_25_mile_intervals(self):
        # 100-mile route with 25-mile sampling
        coords = create_straight_test_polyline(100.0, segments=20)
        cps = generate_checkpoints(coords, interval_miles=25.0, total_route_distance_miles=100.0)

        # Checkpoints should be at 0, 25, 50, 75, 100
        assert len(cps) == 5
        assert cps[0]["is_origin"] is True
        assert cps[0]["distance_from_origin_miles"] == 0.0
        assert cps[1]["distance_from_origin_miles"] == 25.0
        assert cps[2]["distance_from_origin_miles"] == 50.0
        assert cps[3]["distance_from_origin_miles"] == 75.0
        assert cps[4]["is_destination"] is True
        assert cps[4]["distance_from_origin_miles"] == 100.0

    def test_destination_included_when_not_exact_multiple(self):
        # 83-mile route with 25-mile sampling:
        # samples at 0, 25, 50, 75, and destination at 83
        coords = create_straight_test_polyline(83.0, segments=20)
        cps = generate_checkpoints(coords, interval_miles=25.0, total_route_distance_miles=83.0)

        assert len(cps) == 5
        assert cps[-1]["is_destination"] is True
        assert cps[-1]["distance_from_origin_miles"] == 83.0

    def test_checkpoints_at_10_and_50_mile_intervals(self):
        coords = create_straight_test_polyline(50.0, segments=15)
        
        # 10-mile interval: 0, 10, 20, 30, 40, 50 -> 6 checkpoints
        cps_10 = generate_checkpoints(coords, interval_miles=10.0, total_route_distance_miles=50.0)
        assert len(cps_10) == 6
        assert cps_10[-1]["is_destination"] is True

        # 50-mile interval: 0, 50 -> 2 checkpoints
        cps_50 = generate_checkpoints(coords, interval_miles=50.0, total_route_distance_miles=50.0)
        assert len(cps_50) == 2
        assert cps_50[0]["is_origin"] is True
        assert cps_50[-1]["is_destination"] is True

    def test_no_duplicate_checkpoint_when_interval_close_to_destination(self):
        # If route is 50.2 miles, sampling at 50 miles shouldn't produce both 50.0 and 50.2
        coords = create_straight_test_polyline(50.2, segments=20)
        cps = generate_checkpoints(coords, interval_miles=50.0, total_route_distance_miles=50.2)
        
        # Should contain 0.0 and 50.2 without duplicating near the end
        assert len(cps) == 2
        assert cps[-1]["distance_from_origin_miles"] == 50.2
        assert cps[-1]["is_destination"] is True
