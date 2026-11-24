"""
Tests for Arrival Time and ETA Calculation.
Covers:
- Segment-based distance duration interpolation
- Checkpoint ETA timestamp calculation
- Formatting and forecast hour lookup mapping
"""

import pytest
from datetime import datetime, timezone
from routing.services.arrival_time import calculate_checkpoint_etas, parse_to_utc_datetime


class TestArrivalTimeCalculation:
    def test_checkpoint_etas_interpolation(self):
        # 100-mile route taking 2 hours (7200 seconds)
        checkpoints = [
            {"id": "cp_0", "distance_from_origin_miles": 0.0},
            {"id": "cp_1", "distance_from_origin_miles": 50.0},
            {"id": "cp_2", "distance_from_origin_miles": 100.0},
        ]
        dep_time = "2026-11-24T08:00:00Z"
        total_duration = 7200.0  # 2 hours
        total_distance = 100.0

        updated, dep_utc_iso = calculate_checkpoint_etas(checkpoints, dep_time, total_duration, total_distance)

        assert "2026-11-24T08:00:00" in dep_utc_iso
        # cp_0: 0 seconds elapsed -> 08:00
        assert updated[0]["elapsed_seconds"] == 0.0
        assert updated[0]["elapsed_hours"] == 0.0
        assert "08:00" in updated[0]["estimated_arrival_time"]

        # cp_1: 50% along route -> 3600 seconds (1 hour) elapsed -> 09:00
        assert updated[1]["elapsed_seconds"] == 3600.0
        assert updated[1]["elapsed_hours"] == 1.0
        assert "09:00" in updated[1]["estimated_arrival_time"]
        assert updated[1]["forecast_lookup_hour"] == "2026-11-24T09:00"

        # cp_2: 100% along route -> 7200 seconds (2 hours) elapsed -> 10:00
        assert updated[2]["elapsed_seconds"] == 7200.0
        assert updated[2]["elapsed_hours"] == 2.0
        assert "10:00" in updated[2]["estimated_arrival_time"]
        assert updated[2]["forecast_lookup_hour"] == "2026-11-24T10:00"

    def test_handles_iso_formats(self):
        checkpoints = [{"id": "cp_0", "distance_from_origin_miles": 0.0}]
        dep_iso = "2026-11-24T14:30"
        updated, dep_utc_iso = calculate_checkpoint_etas(checkpoints, dep_iso, 3600.0, 50.0)
        assert "2026-11-24T14:30" in updated[0]["estimated_arrival_time"]

    def test_parse_to_utc_with_timezone_offset(self):
        # Browser in US EST (UTC-5): getTimezoneOffset() returns 300 minutes
        naive_iso = "2026-11-24T08:00"
        dt_utc = parse_to_utc_datetime(naive_iso, user_timezone_offset_minutes=300)
        # 08:00 EST is 13:00 UTC
        assert dt_utc.hour == 13
        assert dt_utc.tzinfo == timezone.utc

    def test_parse_to_utc_with_explicit_timezone_offset_string(self):
        # Timezone-aware string with -05:00 offset
        tz_aware_iso = "2026-11-24T08:00:00-05:00"
        dt_utc = parse_to_utc_datetime(tz_aware_iso)
        assert dt_utc.hour == 13
        assert dt_utc.tzinfo == timezone.utc

    def test_checkpoint_etas_match_utc_instant(self):
        # Route departing at 08:00 EST (13:00 UTC) with 1h travel
        checkpoints = [
            {"id": "cp_0", "distance_from_origin_miles": 0.0},
            {"id": "cp_1", "distance_from_origin_miles": 60.0},
        ]
        updated, dep_utc = calculate_checkpoint_etas(
            checkpoints,
            "2026-11-24T08:00",
            total_duration_seconds=3600.0,
            total_distance_miles=60.0,
            user_timezone_offset_minutes=300
        )
        # Checkpoint 0 lookup hour should be 13:00 UTC
        assert updated[0]["forecast_lookup_hour"] == "2026-11-24T13:00"
        # Checkpoint 1 lookup hour should be 14:00 UTC
        assert updated[1]["forecast_lookup_hour"] == "2026-11-24T14:00"


class TestDaylightSavingTransitions:
    """
    Regression tests for departure dates on either side of a daylight-saving transition.
    Validates both user_timezone_offset_minutes and timezone-aware ISO strings.
    """

    def test_summer_vs_winter_timezone_offset(self):
        # Summer date (US Eastern Daylight Time EDT: UTC-4 -> offset 240 minutes)
        summer_iso = "2026-07-15T08:00"
        summer_utc = parse_to_utc_datetime(summer_iso, user_timezone_offset_minutes=240)
        assert summer_utc.hour == 12  # 08:00 EDT -> 12:00 UTC
        assert summer_utc.month == 7
        assert summer_utc.day == 15

        # Winter date (US Eastern Standard Time EST: UTC-5 -> offset 300 minutes)
        winter_iso = "2026-11-24T08:00"
        winter_utc = parse_to_utc_datetime(winter_iso, user_timezone_offset_minutes=300)
        assert winter_utc.hour == 13  # 08:00 EST -> 13:00 UTC
        assert winter_utc.month == 11
        assert winter_utc.day == 24

    def test_dst_boundary_dates(self):
        # In 2026, US DST ends on Sunday, November 1.
        # Saturday Oct 31, 2026 (EDT, offset 240)
        pre_dst_iso = "2026-10-31T10:00"
        pre_dst_utc = parse_to_utc_datetime(pre_dst_iso, user_timezone_offset_minutes=240)
        assert pre_dst_utc.hour == 14  # 10:00 EDT -> 14:00 UTC

        # Monday Nov 2, 2026 (EST, offset 300)
        post_dst_iso = "2026-11-02T10:00"
        post_dst_utc = parse_to_utc_datetime(post_dst_iso, user_timezone_offset_minutes=300)
        assert post_dst_utc.hour == 15  # 10:00 EST -> 15:00 UTC

    def test_timezone_aware_iso_on_either_side_of_dst(self):
        # Timezone-aware ISO explicitly embedding -04:00 (EDT)
        dt_summer = parse_to_utc_datetime("2026-07-15T08:00:00-04:00")
        assert dt_summer.hour == 12
        assert dt_summer.tzinfo == timezone.utc

        # Timezone-aware ISO explicitly embedding -05:00 (EST)
        dt_winter = parse_to_utc_datetime("2026-11-24T08:00:00-05:00")
        assert dt_winter.hour == 13
        assert dt_winter.tzinfo == timezone.utc

    def test_checkpoint_etas_across_dst_dates(self):
        checkpoints = [
            {"id": "cp_0", "distance_from_origin_miles": 0.0},
            {"id": "cp_1", "distance_from_origin_miles": 60.0},
        ]
        # Summer trip (EDT, offset 240)
        updated_summer, dep_summer = calculate_checkpoint_etas(
            checkpoints, "2026-07-15T08:00", 3600.0, 60.0, user_timezone_offset_minutes=240
        )
        assert updated_summer[0]["forecast_lookup_hour"] == "2026-07-15T12:00"
        assert updated_summer[1]["forecast_lookup_hour"] == "2026-07-15T13:00"

        # Winter trip (EST, offset 300)
        updated_winter, dep_winter = calculate_checkpoint_etas(
            checkpoints, "2026-11-24T08:00", 3600.0, 60.0, user_timezone_offset_minutes=300
        )
        assert updated_winter[0]["forecast_lookup_hour"] == "2026-11-24T13:00"
        assert updated_winter[1]["forecast_lookup_hour"] == "2026-11-24T14:00"


