r"""
Deterministic Baseline Risk Engine for Banana Spoilage Prioritization.

SCIENTIFIC INTEGRITY & PROTOTYPE ASSUMPTION STATEMENT:
------------------------------------------------------
All scoring formulas below are documented, configurable PROTOTYPE ASSUMPTIONS.
They are NOT calibrated agricultural spoilage probabilities or validated shelf-life
survival models.

1. Temperature: $13-15°C$ represents standard commercial Cavendish storage.
   $12-13°C$ represents a transitional mild cooling zone.
   $<12°C$ represents chilling injury risk.
   $>20°C$ accelerates respiration and ethylene-driven softening.
2. Humidity: $85-90\%$ represents optimal relative humidity.
   $>90\%$ risks condensation and crown rot fungi.
   $<85\%$ leads to peel desiccation and moisture loss.
3. MQ-135 Gas: Treated solely as an uncalibrated relative electrical resistance ratio
   (Rs/R0), never as exact ethylene ppm or chemical assay.
4. Vision: Missing/unassessed vision is strictly EXCLUDED from penalty calculation;
   weights are renormalized across active signals, and incomplete assessments are flagged.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from app.config import settings

def calculate_temperature_penalty(temp_c: float) -> float:
    """Computes temperature stress penalty (0 - 100) using prototype intervals."""
    if settings.TEMP_OPTIMAL_MIN <= temp_c <= settings.TEMP_OPTIMAL_MAX:
        return 0.0
    # 12.0°C to 13.0°C: Defined transition cooling interval
    elif settings.TEMP_CHILLING_THRESHOLD <= temp_c < settings.TEMP_OPTIMAL_MIN:
        return round((settings.TEMP_OPTIMAL_MIN - temp_c) * 10.0, 2)
    # Below 12.0°C: Chilling injury risk
    elif temp_c < settings.TEMP_CHILLING_THRESHOLD:
        return round(min(100.0, 10.0 + (settings.TEMP_CHILLING_THRESHOLD - temp_c) * 20.0), 2)
    # 15.0°C to 20.0°C: Elevated storage temperature
    elif settings.TEMP_OPTIMAL_MAX < temp_c <= settings.TEMP_ELEVATED_MAX:
        return round((temp_c - settings.TEMP_OPTIMAL_MAX) * 6.0, 2)
    # Above 20.0°C: High thermal acceleration
    else:
        return round(min(100.0, 30.0 + (temp_c - settings.TEMP_ELEVATED_MAX) * 10.0), 2)

def calculate_humidity_penalty(rh_pct: float) -> float:
    """Computes humidity stress penalty (0 - 100) using prototype intervals."""
    if settings.HUMIDITY_OPTIMAL_MIN <= rh_pct <= settings.HUMIDITY_OPTIMAL_MAX:
        return 0.0
    elif rh_pct > settings.HUMIDITY_OPTIMAL_MAX:
        return round(min(100.0, (rh_pct - settings.HUMIDITY_OPTIMAL_MAX) * 10.0), 2)
    else:  # rh_pct < 85.0
        return round(min(60.0, (settings.HUMIDITY_OPTIMAL_MIN - rh_pct) * 3.0), 2)

def calculate_gas_penalty(raw_ratio: float) -> float:
    """
    Computes gas volatility penalty (0 - 100) from relative resistance ratio Rs/R0.
    NOTE: Uncalibrated auxiliary indicator; does NOT measure ethylene ppm.
    """
    if raw_ratio >= settings.GAS_RATIO_NOMINAL_MIN:
        return 0.0
    return round(min(100.0, (settings.GAS_RATIO_NOMINAL_MIN - raw_ratio) * 150.0), 2)

def calculate_vision_penalty(stage: Optional[str]) -> Optional[float]:
    """
    Maps validated ripeness stage to penalty.
    Returns None if vision is unavailable or unassessed (must NOT treat unassessed as a stage).
    """
    if not stage:
        return None
    stage_upper = stage.strip().upper()
    mapping = {
        "UNDER_RIPE": settings.PENALTY_RIPENESS_UNDER_RIPE,
        "HALF_RIPE": settings.PENALTY_RIPENESS_HALF_RIPE,
        "RIPE": settings.PENALTY_RIPENESS_RIPE,
        "OVER_RIPE": settings.PENALTY_RIPENESS_OVER_RIPE,
        "DECAYING": settings.PENALTY_RIPENESS_DECAYING,
    }
    return mapping.get(stage_upper, None)

def evaluate_batch_risk(
    temperature_c: Optional[float],
    relative_humidity_pct: Optional[float],
    gas_raw: Optional[float],
    ripeness_stage: Optional[str],
    last_telemetry_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Calculates deterministic composite risk score and completeness flags.
    Dynamically renormalizes active weights when signals (such as vision) are unavailable.
    """
    penalties: Dict[str, float] = {}
    base_weights: Dict[str, float] = {}

    # 1. Vision feature evaluation
    v_pen = calculate_vision_penalty(ripeness_stage)
    if v_pen is not None:
        penalties["vision"] = v_pen
        base_weights["vision"] = settings.DEFAULT_WEIGHT_VISION

    # 2. Temperature feature evaluation
    if temperature_c is not None:
        penalties["temperature"] = calculate_temperature_penalty(temperature_c)
        base_weights["temperature"] = settings.DEFAULT_WEIGHT_TEMP

    # 3. Humidity feature evaluation
    if relative_humidity_pct is not None:
        penalties["humidity"] = calculate_humidity_penalty(relative_humidity_pct)
        base_weights["humidity"] = settings.DEFAULT_WEIGHT_HUMIDITY

    # 4. Gas feature evaluation
    if gas_raw is not None:
        penalties["gas"] = calculate_gas_penalty(gas_raw)
        base_weights["gas"] = settings.DEFAULT_WEIGHT_GAS

    # Completeness check
    has_vision = "vision" in penalties
    has_telemetry = ("temperature" in penalties) or ("humidity" in penalties)

    if has_vision and has_telemetry:
        completeness = "COMPLETE"
    elif not has_vision and has_telemetry:
        completeness = "INCOMPLETE_VISION_PENDING"
    elif has_vision and not has_telemetry:
        completeness = "INCOMPLETE_TELEMETRY_MISSING"
    else:
        completeness = "NO_DATA_AVAILABLE"

    # Stale telemetry check
    is_stale = False
    if last_telemetry_time is not None:
        # Check against timezone-aware or naive UTC
        now_utc = datetime.now(timezone.utc)
        if last_telemetry_time.tzinfo is None:
            last_telemetry_time = last_telemetry_time.replace(tzinfo=timezone.utc)
        elapsed = (now_utc - last_telemetry_time).total_seconds()
        if elapsed > settings.STALE_THRESHOLD_SECONDS:
            is_stale = True

    # Weight renormalization
    total_active_weight = sum(base_weights.values())
    normalized_weights: Dict[str, float] = {}
    if total_active_weight > 0:
        for k, w in base_weights.items():
            normalized_weights[k] = round(w / total_active_weight, 4)
        composite_score = sum(normalized_weights[k] * penalties[k] for k in penalties)
        composite_score = round(composite_score, 2)
    else:
        composite_score = 0.0

    # Risk tier categorization
    if composite_score >= 70.0:
        tier = "CRITICAL"
        rec = "URGENT_SELL_PRIORITY"
    elif composite_score >= 50.0:
        tier = "HIGH"
        rec = "EXPEDITE_SALE"
    elif composite_score >= 30.0:
        tier = "MODERATE"
        rec = "MONITOR_CLOSELY"
    else:
        tier = "LOW"
        rec = "NORMAL_STORAGE_WINDOW"

    # Identify primary urgency driver
    primary_driver = "No risk factors identified; conditions nominal."
    if penalties:
        # Find factor with highest weighted contribution
        weighted_contributions = {
            k: normalized_weights[k] * penalties[k] for k in penalties
        }
        top_factor = max(weighted_contributions, key=weighted_contributions.get)
        if weighted_contributions[top_factor] > 0:
            if top_factor == "vision":
                primary_driver = f"Ripeness stage '{ripeness_stage}' contributes {penalties['vision']} risk penalty."
            elif top_factor == "temperature":
                primary_driver = f"Storage temperature {temperature_c}°C stresses storage tolerance (penalty {penalties['temperature']})."
            elif top_factor == "humidity":
                primary_driver = f"Relative humidity {relative_humidity_pct}% deviates from optimal 85-90% zone (penalty {penalties['humidity']})."
            elif top_factor == "gas":
                primary_driver = f"Auxiliary gas resistance ratio {gas_raw} indicates volatile activity (penalty {penalties['gas']})."

    return {
        "composite_score": composite_score,
        "risk_tier": tier,
        "recommendation": rec,
        "primary_driver": primary_driver,
        "assessment_completeness": completeness,
        "is_stale": is_stale,
        "factor_penalties": penalties,
        "normalized_weights": normalized_weights,
    }
