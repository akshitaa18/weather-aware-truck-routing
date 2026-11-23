"""
Tests for Heatmap and Dynamic Hourly Timeline Service.
Covers:
- Slider offsets are relative to departure time (T_dep + H), NOT checkpoint ETA.
- Dynamic checkpoint risk updates when weather changes across timeline hours.
- Dynamic heatmap segments are correctly segmented and inherit maximum risk.
- Unavailable forecast hours are explicitly marked with forecast_available=False and Data Unavailable.
"""

import pytest
from datetime import datetime, timezone
from routing.services.heatmap import generate_corridor_heatmap_timeline
from routing.services.risk_engine import RISK_LOW, RISK_HIGH, RISK_UNKNOWN, RISK_SEVERE


class TestHeatmapDynamicTimeline:
    def test_slider_offsets_are_relative_to_departure_time(self):
        # 2 checkpoints with hourly_timeline
        # Checkpoint 0 is at origin (ETA = T_dep)
        # Checkpoint 1 is at 100mi (ETA = T_dep + 2h)
        base_dep = "2026-11-24T08:00:00+00:00"

        # Checkpoint 0 timeline
        cp0_timeline = [
            {"hour_offset": h, "wind_speed_mph": 10.0, "rain_intensity_in_hr": 0.0, "snow_intensity_in_hr": 0.0, "forecast_available": True}
            for h in range(49)
        ]
        # Checkpoint 1 timeline has high wind at hour 3 relative to departure
        cp1_timeline = [
            {
                "hour_offset": h,
                "wind_speed_mph": 40.0 if h == 3 else 10.0,
                "rain_intensity_in_hr": 0.0,
                "snow_intensity_in_hr": 0.0,
                "forecast_available": True
            }
            for h in range(49)
        ]

        checkpoints = [
            {
                "id": "cp_0",
                "checkpoint_index": 0,
                "latitude": 41.8781,
                "longitude": -87.6298,
                "distance_from_origin_miles": 0.0,
                "hourly_timeline": cp0_timeline,
            },
            {
                "id": "cp_1",
                "checkpoint_index": 1,
                "latitude": 42.3314,
                "longitude": -83.0458,
                "distance_from_origin_miles": 100.0,
                "hourly_timeline": cp1_timeline,
            },
        ]

        heatmap = generate_corridor_heatmap_timeline(checkpoints, load_weight_lb=30000.0)

        # Check all 49 hours are present
        assert len(heatmap) == 49
        assert 0 in heatmap
        assert 3 in heatmap
        assert 48 in heatmap

        # At hour 0 (departure time): cp1 has low wind
        assert heatmap[0]["checkpoints"][1]["wind_speed_mph"] == 10.0
        assert heatmap[0]["checkpoints"][1]["final_risk"] == RISK_LOW
        assert heatmap[0]["segments"][0]["risk_level"] == RISK_LOW

        # At hour 3 (departure time + 3 hours): cp1 has 40 mph wind -> High risk
        assert heatmap[3]["checkpoints"][1]["wind_speed_mph"] == 40.0
        assert heatmap[3]["checkpoints"][1]["final_risk"] == RISK_HIGH
        # Segment between cp0 and cp1 inherits highest risk (High)
        assert heatmap[3]["segments"][0]["risk_level"] == RISK_HIGH

    def test_unavailable_forecast_hours_marked_data_unavailable(self):
        base_dep = "2026-11-24T08:00:00+00:00"

        # Checkpoint with forecast ending at hour 24
        cp_timeline = []
        for h in range(49):
            if h <= 24:
                cp_timeline.append({
                    "hour_offset": h,
                    "wind_speed_mph": 12.0,
                    "rain_intensity_in_hr": 0.0,
                    "snow_intensity_in_hr": 0.0,
                    "forecast_available": True
                })
            else:
                cp_timeline.append({
                    "hour_offset": h,
                    "wind_speed_mph": None,
                    "rain_intensity_in_hr": None,
                    "snow_intensity_in_hr": None,
                    "forecast_available": False
                })

        checkpoints = [
            {
                "id": "cp_0",
                "checkpoint_index": 0,
                "latitude": 41.8781,
                "longitude": -87.6298,
                "distance_from_origin_miles": 0.0,
                "hourly_timeline": cp_timeline,
            },
            {
                "id": "cp_1",
                "checkpoint_index": 1,
                "latitude": 42.3314,
                "longitude": -83.0458,
                "distance_from_origin_miles": 50.0,
                "hourly_timeline": cp_timeline,
            },
        ]

        heatmap = generate_corridor_heatmap_timeline(checkpoints, load_weight_lb=30000.0)

        # At hour 20: forecast available, Low risk
        assert heatmap[20]["checkpoints"][0]["forecast_available"] is True
        assert heatmap[20]["checkpoints"][0]["final_risk"] == RISK_LOW

        # At hour 30: forecast unavailable, Data Unavailable (never Low)
        assert heatmap[30]["checkpoints"][0]["forecast_available"] is False
        assert heatmap[30]["checkpoints"][0]["final_risk"] == RISK_UNKNOWN
        assert heatmap[30]["checkpoints"][0]["final_risk"] != RISK_LOW
        assert heatmap[30]["segments"][0]["risk_level"] == RISK_UNKNOWN
