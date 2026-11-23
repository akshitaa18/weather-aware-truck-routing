"""
Risk Calculation Engine for Weather-Aware Truck Routing.

Implements the exact deterministic risk classification rules, load-based risk adjustments,
and checkpoint aggregation priority specified in Section 8.
"""

from typing import Dict, Any, Optional

# Risk level constants
RISK_LOW = "Low"
RISK_MODERATE = "Moderate"
RISK_HIGH = "High"
RISK_SEVERE = "Severe"
RISK_NO_TRAVEL = "No Travel"

# Severity order for comparison: No Travel > Severe > High > Moderate > Low
RISK_SEVERITY_ORDER = {
    RISK_LOW: 1,
    RISK_MODERATE: 2,
    RISK_HIGH: 3,
    RISK_SEVERE: 4,
    RISK_NO_TRAVEL: 5,
}

REVERSE_SEVERITY_ORDER = {v: k for k, v in RISK_SEVERITY_ORDER.items()}


def classify_wind_risk(speed_mph: float) -> str:
    """
    Classify wind risk based on wind speed in mph.
    
    Thresholds:
    - Below 25 mph: Low
    - 25–34 mph: Moderate
    - 35–44 mph: High
    - 45–54 mph: Severe
    - 55 mph or above: No Travel
    
    Deterministic boundary: Higher risk category at exact shared threshold.
    """
    if speed_mph >= 55.0:
        return RISK_NO_TRAVEL
    elif speed_mph >= 45.0:
        return RISK_SEVERE
    elif speed_mph >= 35.0:
        return RISK_HIGH
    elif speed_mph >= 25.0:
        return RISK_MODERATE
    else:
        return RISK_LOW


def classify_rain_risk(rain_in_hr: float) -> str:
    """
    Classify rain risk based on precipitation intensity in inches/hour.
    
    Thresholds:
    - Below 0.10 in/hr: Low
    - 0.10–0.25 in/hr: Moderate
    - 0.25–0.50 in/hr: High
    - 0.50–1.00 in/hr: Severe
    - Above 1.00 in/hr: No Travel
    
    Deterministic boundary: Higher risk category at exact shared threshold.
    """
    if rain_in_hr > 1.00:
        return RISK_NO_TRAVEL
    elif rain_in_hr >= 0.50:
        return RISK_SEVERE
    elif rain_in_hr >= 0.25:
        return RISK_HIGH
    elif rain_in_hr >= 0.10:
        return RISK_MODERATE
    else:
        return RISK_LOW


def classify_snow_risk(snow_in_hr: float) -> str:
    """
    Classify snow risk based on snowfall intensity in inches/hour.
    
    Thresholds:
    - Below 0.5 in/hr: Low
    - 0.5–1.0 in/hr: Moderate
    - 1.0–2.0 in/hr: High
    - 2.0–3.0 in/hr: Severe
    - Above 3.0 in/hr: No Travel
    
    Deterministic boundary: Higher risk category at exact shared threshold.
    """
    if snow_in_hr > 3.0:
        return RISK_NO_TRAVEL
    elif snow_in_hr >= 2.0:
        return RISK_SEVERE
    elif snow_in_hr >= 1.0:
        return RISK_HIGH
    elif snow_in_hr >= 0.5:
        return RISK_MODERATE
    else:
        return RISK_LOW


def apply_load_based_rules(wind_mph: float, load_weight_lb: float) -> Optional[str]:
    """
    Apply load-based risk rules after classifying weather.
    
    Rules:
    1. Wind speed >= 55 mph:
       No Travel for every load.
    2. Wind speed between 45 and 54 mph (45.0 <= wind < 55.0) AND load weight > 30,000 lb:
       No Travel.
    3. Wind speed between 35 and 44 mph (35.0 <= wind < 45.0) AND load weight > 40,000 lb:
       Severe.
       
    Returns the minimum risk mandated by load rules, or None if no load rule applies.
    """
    if wind_mph >= 55.0:
        return RISK_NO_TRAVEL
    elif 45.0 <= wind_mph < 55.0 and load_weight_lb > 30000.0:
        return RISK_NO_TRAVEL
    elif 35.0 <= wind_mph < 45.0 and load_weight_lb > 40000.0:
        return RISK_SEVERE
    return None


def get_higher_risk(risk1: str, risk2: str) -> str:
    """Return the higher risk between two classifications."""
    score1 = RISK_SEVERITY_ORDER.get(risk1, 1)
    score2 = RISK_SEVERITY_ORDER.get(risk2, 1)
    return risk1 if score1 >= score2 else risk2


def evaluate_checkpoint_risk(
    wind_mph: float,
    rain_in_hr: float,
    snow_in_hr: float,
    load_weight_lb: float
) -> Dict[str, Any]:
    """
    Calculate checkpoint-level weather risks, apply load rules, and aggregate final risk.
    
    Risk priority:
    No Travel > Severe > High > Moderate > Low.
    
    Returns a dict containing:
    - wind_risk
    - rain_risk
    - snow_risk
    - weather_risk (highest of wind, rain, snow)
    - load_adjusted_risk (load rule outcome if triggered)
    - final_risk (highest applicable risk)
    - reason (human-readable explanation)
    """
    wind_risk = classify_wind_risk(wind_mph)
    rain_risk = classify_rain_risk(rain_in_hr)
    snow_risk = classify_snow_risk(snow_in_hr)
    
    # Pure weather risk
    weather_risk = get_higher_risk(get_higher_risk(wind_risk, rain_risk), snow_risk)
    
    # Load-based adjustment
    load_rule_risk = apply_load_based_rules(wind_mph, load_weight_lb)
    
    if load_rule_risk:
        final_risk = get_higher_risk(weather_risk, load_rule_risk)
    else:
        final_risk = weather_risk
        
    # Build explanation reasons
    reasons = []
    if final_risk == RISK_NO_TRAVEL:
        if wind_mph >= 55.0:
            reasons.append(f"Excessive wind ({wind_mph:.1f} mph >= 55 mph)")
        elif 45.0 <= wind_mph < 55.0 and load_weight_lb > 30000:
            reasons.append(f"High wind ({wind_mph:.1f} mph) with heavy load ({load_weight_lb:,.0f} lb > 30,000 lb)")
        if rain_in_hr > 1.0:
            reasons.append(f"Extreme rain ({rain_in_hr:.2f} in/hr > 1.00 in/hr)")
        if snow_in_hr > 3.0:
            reasons.append(f"Extreme snow ({snow_in_hr:.2f} in/hr > 3.00 in/hr)")
    elif final_risk == RISK_SEVERE:
        if 35.0 <= wind_mph < 45.0 and load_weight_lb > 40000:
            reasons.append(f"Moderate wind ({wind_mph:.1f} mph) with heavy load ({load_weight_lb:,.0f} lb > 40,000 lb)")
        elif 45.0 <= wind_mph < 55.0:
            reasons.append(f"Severe wind ({wind_mph:.1f} mph)")
        if 0.50 <= rain_in_hr <= 1.00:
            reasons.append(f"Severe rain ({rain_in_hr:.2f} in/hr)")
        if 2.0 <= snow_in_hr <= 3.0:
            reasons.append(f"Severe snow ({snow_in_hr:.2f} in/hr)")
    elif final_risk == RISK_HIGH:
        if 35.0 <= wind_mph < 45.0:
            reasons.append(f"High wind ({wind_mph:.1f} mph)")
        if 0.25 <= rain_in_hr < 0.50:
            reasons.append(f"Heavy rain ({rain_in_hr:.2f} in/hr)")
        if 1.0 <= snow_in_hr < 2.0:
            reasons.append(f"Heavy snow ({snow_in_hr:.2f} in/hr)")
    elif final_risk == RISK_MODERATE:
        if 25.0 <= wind_mph < 35.0:
            reasons.append(f"Moderate wind ({wind_mph:.1f} mph)")
        if 0.10 <= rain_in_hr < 0.25:
            reasons.append(f"Moderate rain ({rain_in_hr:.2f} in/hr)")
        if 0.5 <= snow_in_hr < 1.0:
            reasons.append(f"Moderate snow ({snow_in_hr:.2f} in/hr)")
    else:
        reasons.append("Favorable driving conditions")

    return {
        "wind_risk": wind_risk,
        "rain_risk": rain_risk,
        "snow_risk": snow_risk,
        "weather_risk": weather_risk,
        "load_adjusted_risk": load_rule_risk or "None",
        "final_risk": final_risk,
        "risk_score": RISK_SEVERITY_ORDER[final_risk],
        "reason": "; ".join(reasons)
    }
