"""
Deterministic Risk Engine Unit Tests.
Verifies prototype formula, interval boundaries (including 12-13°C),
missing feature renormalization, and stale telemetry flags.
"""

from datetime import datetime, timezone, timedelta
from app.services.risk_engine import (
    calculate_temperature_penalty,
    calculate_humidity_penalty,
    calculate_gas_penalty,
    calculate_vision_penalty,
    evaluate_batch_risk,
)

def test_temperature_penalty_intervals():
    # 1. Optimal interval: 13.0 to 15.0°C
    assert calculate_temperature_penalty(13.0) == 0.0
    assert calculate_temperature_penalty(14.2) == 0.0
    assert calculate_temperature_penalty(15.0) == 0.0

    # 2. Defined transition cooling interval: 12.0 to 13.0°C
    assert calculate_temperature_penalty(12.5) == 5.0   # (13.0 - 12.5) * 10
    assert calculate_temperature_penalty(12.0) == 10.0  # (13.0 - 12.0) * 10

    # 3. Chilling injury zone: < 12.0°C
    assert calculate_temperature_penalty(11.0) == 30.0  # 10 + (12.0 - 11.0) * 20
    assert calculate_temperature_penalty(8.0) == 90.0   # 10 + (12.0 - 8.0) * 20

    # 4. Elevated storage interval: 15.0 to 20.0°C
    assert calculate_temperature_penalty(17.0) == 12.0  # (17.0 - 15.0) * 6
    assert calculate_temperature_penalty(20.0) == 30.0  # (20.0 - 15.0) * 6

    # 5. Severe thermal acceleration: > 20.0°C
    assert calculate_temperature_penalty(25.0) == 80.0  # 30 + (25.0 - 20.0) * 10
    assert calculate_temperature_penalty(35.0) == 100.0 # capped at 100

def test_humidity_penalty_intervals():
    # Optimal: 85.0 to 90.0%
    assert calculate_humidity_penalty(88.0) == 0.0
    # Over-humidity (> 90.0%)
    assert calculate_humidity_penalty(94.0) == 40.0   # (94.0 - 90.0) * 10
    # Under-humidity (< 85.0%)
    assert calculate_humidity_penalty(80.0) == 15.0   # (85.0 - 80.0) * 3

def test_gas_penalty_uncalibrated_ratio():
    # Clean air ratio >= 0.95
    assert calculate_gas_penalty(0.98) == 0.0
    assert calculate_gas_penalty(0.95) == 0.0
    # Sharp drop in resistance ratio
    assert calculate_gas_penalty(0.75) == 30.0  # (0.95 - 0.75) * 150

def test_missing_vision_feature_is_excluded_and_renormalized():
    """
    CONDITION 2: When vision is unassessed/None, it must NOT be treated as a stage.
    Vision weight must be excluded, and active weights must renormalize.
    """
    # 1. calculate_vision_penalty must return None for missing or UNASSESSED
    assert calculate_vision_penalty(None) is None
    assert calculate_vision_penalty("UNASSESSED") is None

    # 2. Evaluate batch with NO vision
    result = evaluate_batch_risk(
        temperature_c=14.0,       # Penalty: 0.0, weight: 0.25
        relative_humidity_pct=88.0,# Penalty: 0.0, weight: 0.20
        gas_raw=0.98,             # Penalty: 0.0, weight: 0.15
        ripeness_stage=None,      # EXCLUDED
    )

    assert result["assessment_completeness"] == "INCOMPLETE_VISION_PENDING"
    assert "vision" not in result["factor_penalties"]
    assert "vision" not in result["normalized_weights"]

    # Active weights sum to 0.25 + 0.20 + 0.15 = 0.60
    # Renormalized weights must sum to 1.0
    norm_weights = result["normalized_weights"]
    assert round(sum(norm_weights.values()), 2) == 1.0
    assert result["composite_score"] == 0.0
    assert result["risk_tier"] == "LOW"

def test_composite_risk_deterministic_calculation():
    # Test case with known non-zero factors
    # Temp 25°C -> penalty 80.0
    # RH 94% -> penalty 40.0
    # Gas 0.75 -> penalty 30.0
    # Vision RIPE -> penalty 35.0
    # Weights: vision 0.40, temp 0.25, rh 0.20, gas 0.15 (sum 1.0)
    # Expected: 0.40*35 + 0.25*80 + 0.20*40 + 0.15*30 = 14 + 20 + 8 + 4.5 = 46.5
    result = evaluate_batch_risk(
        temperature_c=25.0,
        relative_humidity_pct=94.0,
        gas_raw=0.75,
        ripeness_stage="RIPE",
    )
    assert result["assessment_completeness"] == "COMPLETE"
    assert result["composite_score"] == 46.5
    assert result["risk_tier"] == "MODERATE"

def test_stale_telemetry_detection():
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(minutes=45) # Exceeds 30 min (1800s) threshold

    result = evaluate_batch_risk(
        temperature_c=14.0,
        relative_humidity_pct=88.0,
        gas_raw=0.98,
        ripeness_stage="RIPE",
        last_telemetry_time=old_time,
    )
    assert result["is_stale"] is True
