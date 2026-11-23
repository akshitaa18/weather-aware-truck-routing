"""
Tests for Risk Calculation Engine and Load Rules.
Covers:
- Wind risk thresholds and boundaries
- Rain risk thresholds and boundaries
- Snow risk thresholds and boundaries
- Load-based risk adjustments
- Checkpoint aggregation and priority hierarchy
"""

import pytest
from routing.services.risk_engine import (
    classify_wind_risk,
    classify_rain_risk,
    classify_snow_risk,
    apply_load_based_rules,
    evaluate_checkpoint_risk,
    RISK_LOW,
    RISK_MODERATE,
    RISK_HIGH,
    RISK_SEVERE,
    RISK_NO_TRAVEL,
)


class TestWindRiskThresholds:
    def test_wind_below_25_is_low(self):
        assert classify_wind_risk(0.0) == RISK_LOW
        assert classify_wind_risk(15.5) == RISK_LOW
        assert classify_wind_risk(24.9) == RISK_LOW

    def test_wind_25_to_34_is_moderate(self):
        # Exact shared threshold 25.0 uses higher category (Moderate)
        assert classify_wind_risk(25.0) == RISK_MODERATE
        assert classify_wind_risk(30.0) == RISK_MODERATE
        assert classify_wind_risk(34.9) == RISK_MODERATE

    def test_wind_35_to_44_is_high(self):
        # Exact shared threshold 35.0 uses higher category (High)
        assert classify_wind_risk(35.0) == RISK_HIGH
        assert classify_wind_risk(40.0) == RISK_HIGH
        assert classify_wind_risk(44.9) == RISK_HIGH

    def test_wind_45_to_54_is_severe(self):
        # Exact shared threshold 45.0 uses higher category (Severe)
        assert classify_wind_risk(45.0) == RISK_SEVERE
        assert classify_wind_risk(50.0) == RISK_SEVERE
        assert classify_wind_risk(54.9) == RISK_SEVERE

    def test_wind_55_and_above_is_no_travel(self):
        # Exact shared threshold 55.0 uses No Travel
        assert classify_wind_risk(55.0) == RISK_NO_TRAVEL
        assert classify_wind_risk(65.0) == RISK_NO_TRAVEL
        assert classify_wind_risk(100.0) == RISK_NO_TRAVEL


class TestRainRiskThresholds:
    def test_rain_below_0_10_is_low(self):
        assert classify_rain_risk(0.0) == RISK_LOW
        assert classify_rain_risk(0.05) == RISK_LOW
        assert classify_rain_risk(0.09) == RISK_LOW

    def test_rain_0_10_to_0_25_is_moderate(self):
        assert classify_rain_risk(0.10) == RISK_MODERATE
        assert classify_rain_risk(0.18) == RISK_MODERATE
        assert classify_rain_risk(0.24) == RISK_MODERATE

    def test_rain_0_25_to_0_50_is_high(self):
        assert classify_rain_risk(0.25) == RISK_HIGH
        assert classify_rain_risk(0.35) == RISK_HIGH
        assert classify_rain_risk(0.49) == RISK_HIGH

    def test_rain_0_50_to_1_00_is_severe(self):
        assert classify_rain_risk(0.50) == RISK_SEVERE
        assert classify_rain_risk(0.75) == RISK_SEVERE
        assert classify_rain_risk(1.00) == RISK_SEVERE

    def test_rain_above_1_00_is_no_travel(self):
        assert classify_rain_risk(1.01) == RISK_NO_TRAVEL
        assert classify_rain_risk(2.50) == RISK_NO_TRAVEL


class TestSnowRiskThresholds:
    def test_snow_below_0_5_is_low(self):
        assert classify_snow_risk(0.0) == RISK_LOW
        assert classify_snow_risk(0.2) == RISK_LOW
        assert classify_snow_risk(0.49) == RISK_LOW

    def test_snow_0_5_to_1_0_is_moderate(self):
        assert classify_snow_risk(0.5) == RISK_MODERATE
        assert classify_snow_risk(0.8) == RISK_MODERATE
        assert classify_snow_risk(0.99) == RISK_MODERATE

    def test_snow_1_0_to_2_0_is_high(self):
        assert classify_snow_risk(1.0) == RISK_HIGH
        assert classify_snow_risk(1.5) == RISK_HIGH
        assert classify_snow_risk(1.99) == RISK_HIGH

    def test_snow_2_0_to_3_0_is_severe(self):
        assert classify_snow_risk(2.0) == RISK_SEVERE
        assert classify_snow_risk(2.5) == RISK_SEVERE
        assert classify_snow_risk(3.0) == RISK_SEVERE

    def test_snow_above_3_0_is_no_travel(self):
        assert classify_snow_risk(3.01) == RISK_NO_TRAVEL
        assert classify_snow_risk(5.0) == RISK_NO_TRAVEL


class TestLoadBasedRiskRules:
    def test_wind_55_plus_no_travel_regardless_of_load(self):
        # Rule 1: Wind >= 55 mph -> No Travel for all loads (light or heavy)
        assert apply_load_based_rules(55.0, 10000.0) == RISK_NO_TRAVEL
        assert apply_load_based_rules(60.0, 50000.0) == RISK_NO_TRAVEL
        assert apply_load_based_rules(55.0, 0.0) == RISK_NO_TRAVEL

    def test_wind_45_to_54_with_heavy_load_over_30k(self):
        # Rule 2: Wind 45-54 mph AND load > 30,000 lb -> No Travel
        assert apply_load_based_rules(46.0, 35000.0) == RISK_NO_TRAVEL
        assert apply_load_based_rules(45.0, 30001.0) == RISK_NO_TRAVEL
        assert apply_load_based_rules(54.0, 45000.0) == RISK_NO_TRAVEL
        # If load <= 30,000 lb, Rule 2 does not trigger (retains severe from pure wind)
        assert apply_load_based_rules(48.0, 25000.0) is None
        assert apply_load_based_rules(45.0, 30000.0) is None

    def test_wind_35_to_44_with_heavy_load_over_40k(self):
        # Rule 3: Wind 35-44 mph AND load > 40,000 lb -> Severe
        assert apply_load_based_rules(36.0, 45000.0) == RISK_SEVERE
        assert apply_load_based_rules(35.0, 40001.0) == RISK_SEVERE
        assert apply_load_based_rules(44.0, 55000.0) == RISK_SEVERE
        # If load <= 40,000 lb, Rule 3 does not trigger
        assert apply_load_based_rules(38.0, 38000.0) is None
        assert apply_load_based_rules(35.0, 40000.0) is None


class TestCheckpointAggregation:
    def test_highest_risk_takes_precedence(self):
        # Low wind (10 mph), Moderate rain (0.15 in/hr), High snow (1.2 in/hr) -> High
        res = evaluate_checkpoint_risk(10.0, 0.15, 1.2, 20000.0)
        assert res["final_risk"] == RISK_HIGH
        assert res["wind_risk"] == RISK_LOW
        assert res["rain_risk"] == RISK_MODERATE
        assert res["snow_risk"] == RISK_HIGH

    def test_load_rule_elevates_risk(self):
        # Wind is 38 mph (High), Rain is 0.0, Snow is 0.0, Load is 45,000 lb (>40k)
        # Elevated to Severe by Load Rule 3
        res = evaluate_checkpoint_risk(38.0, 0.0, 0.0, 45000.0)
        assert res["wind_risk"] == RISK_HIGH
        assert res["load_adjusted_risk"] == RISK_SEVERE
        assert res["final_risk"] == RISK_SEVERE

    def test_load_rule_elevates_to_no_travel(self):
        # Wind is 48 mph (Severe), Load is 35,000 lb (>30k) -> No Travel
        res = evaluate_checkpoint_risk(48.0, 0.0, 0.0, 35000.0)
        assert res["final_risk"] == RISK_NO_TRAVEL


class TestMissingWeatherHandling:
    def test_missing_weather_values_return_unknown_never_low(self):
        from routing.services.risk_engine import (
            classify_wind_risk,
            classify_rain_risk,
            classify_snow_risk,
            RISK_UNKNOWN,
            RISK_LOW,
            get_higher_risk,
        )

        assert classify_wind_risk(None) == RISK_UNKNOWN
        assert classify_wind_risk(None) != RISK_LOW

        assert classify_rain_risk(None) == RISK_UNKNOWN
        assert classify_rain_risk(None) != RISK_LOW

        assert classify_snow_risk(None) == RISK_UNKNOWN
        assert classify_snow_risk(None) != RISK_LOW

    def test_checkpoint_with_missing_weather_evaluates_to_unknown(self):
        from routing.services.risk_engine import RISK_UNKNOWN, evaluate_checkpoint_risk

        # All values None
        res = evaluate_checkpoint_risk(None, None, None, 30000.0)
        assert res["final_risk"] == RISK_UNKNOWN
        assert res["forecast_available"] is False
        assert "unavailable" in res["reason"].lower()

    def test_checkpoint_with_forecast_unavailable_flag(self):
        from routing.services.risk_engine import RISK_UNKNOWN, evaluate_checkpoint_risk

        # Even if dummy numerical values exist, forecast_available=False forces RISK_UNKNOWN
        res = evaluate_checkpoint_risk(5.0, 0.0, 0.0, 30000.0, forecast_available=False)
        assert res["final_risk"] == RISK_UNKNOWN
        assert res["forecast_available"] is False

    def test_unknown_risk_takes_precedence_over_low_risk(self):
        from routing.services.risk_engine import RISK_UNKNOWN, RISK_LOW, RISK_SEVERE, get_higher_risk

        # Missing data is prioritized over Low risk so it cannot be certified safe
        assert get_higher_risk(RISK_UNKNOWN, RISK_LOW) == RISK_UNKNOWN
        assert get_higher_risk(RISK_LOW, RISK_UNKNOWN) == RISK_UNKNOWN

        # Severe / No Travel hazards still outrank Unknown
        assert get_higher_risk(RISK_UNKNOWN, RISK_SEVERE) == RISK_SEVERE

