"""
Gas-Sensor Monitoring & Telemetry Baseline Tracking Service.

IMPORTANT SCIENTIFIC INTEGRITY NOTICE:
--------------------------------------
1. The MQ-135 is a broad-spectrum metal-oxide sensor (SnO2) that responds to
   multiple reducing gases and volatile organic compounds (VOCs) such as ethanol,
   ammonia, and CO. It is NOT chemically specific to ethylene.
2. All measurements are reported strictly as relative resistance ratios (Rs / R0),
   never as calibrated ethylene concentrations (ppm) or microbial spoilage assays.
3. Every generated reading in this module is labeled explicitly as SIMULATED.
"""

from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime, timezone
import csv
import io
from sqlalchemy.orm import Session
from app.models.telemetry import SensorReading
from app.config import settings

def compute_gas_baseline_metrics(
    readings: List[SensorReading],
    nominal_baseline: float = settings.GAS_BASELINE_DEFAULT_RATIO
) -> Dict[str, Any]:
    """
    Computes baseline tracking metrics from chronological sensor readings.
    - Baseline ratio: established from initial readings or nominal clean-air reference.
    - Current ratio: latest observation.
    - Deviation %: percentage drop in resistance ratio (drop indicates rising VOCs).
    - Trend status: categorized into stable, mild, elevated, or critical surge.
    """
    if not readings:
        return {
            "baseline_ratio": nominal_baseline,
            "current_ratio": None,
            "deviation_pct": 0.0,
            "trend_status": "NO_DATA",
            "trend_direction": "UNKNOWN",
            "sample_count": 0,
            "provenance": "SIMULATED",
            "is_simulated": True,
            "explanation": "No telemetry readings recorded for this batch yet."
        }

    # Use the earliest recorded reading as the baseline for this batch
    initial_sample = readings[0].gas_resistance_raw
    baseline_ratio = round(initial_sample, 3) if initial_sample > 0 else nominal_baseline
    latest_sample = readings[-1].gas_resistance_raw

    # In MQ sensors, resistance drops when reducing gases / VOCs are present.
    # Deviation calculates the percentage drop from baseline.
    if baseline_ratio > 0 and latest_sample < baseline_ratio:
        deviation_pct = round(((baseline_ratio - latest_sample) / baseline_ratio) * 100.0, 1)
    else:
        deviation_pct = 0.0

    # Trend status categorization
    if deviation_pct < 5.0 and latest_sample >= settings.GAS_RATIO_NOMINAL_MIN:
        trend_status = "BASELINE_STABLE"
        explanation = "Atmosphere clear; VOC volatile levels consistent with clean-air baseline."
    elif deviation_pct < 18.0:
        trend_status = "MILD_VOLATILE_ACTIVITY"
        explanation = "Mild drop in sensor resistance; early metabolic ripening emissions detected."
    elif deviation_pct < 32.0:
        trend_status = "ELEVATED_VOLATILE_SURGE"
        explanation = "Noticeable resistance reduction indicating volatile accumulation in storage."
    else:
        trend_status = "CRITICAL_FERMENTATION_RISK"
        explanation = "Sharp decrease in sensor resistance (~32%+ drop); indicates high volatile organic emissions."

    # Trend direction over last 5 readings if available
    if len(readings) >= 2:
        prev_sample = readings[-2].gas_resistance_raw
        if latest_sample < prev_sample - 0.01:
            trend_direction = "DECREASING_RESISTANCE_RISING_VOCS"
        elif latest_sample > prev_sample + 0.01:
            trend_direction = "INCREASING_RESISTANCE_VENTILATING"
        else:
            trend_direction = "STABLE"
    else:
        trend_direction = "INSUFFICIENT_HISTORY"

    return {
        "baseline_ratio": baseline_ratio,
        "current_ratio": round(latest_sample, 3),
        "deviation_pct": deviation_pct,
        "trend_status": trend_status,
        "trend_direction": trend_direction,
        "sample_count": len(readings),
        "first_timestamp": readings[0].timestamp.isoformat() if readings[0].timestamp else None,
        "latest_timestamp": readings[-1].timestamp.isoformat() if readings[-1].timestamp else None,
        "provenance": "SIMULATED",
        "is_simulated": True,
        "explanation": explanation,
        "scientific_note": "Auxiliary VOC relative resistance ratio (Rs/R0). Not calibrated ethylene concentration."
    }

def get_historical_telemetry(
    db: Session,
    batch_id: Optional[str] = None,
    limit: int = 150
) -> List[SensorReading]:
    """Retrieves chronological sensor telemetry points for a batch or all batches."""
    query = db.query(SensorReading)
    if batch_id and batch_id != "ALL":
        query = query.filter(SensorReading.batch_id == batch_id)
    # Order chronologically for graphing
    readings = query.order_by(SensorReading.timestamp.desc()).limit(limit).all()
    # Reverse to return ascending chronological order (oldest to newest)
    return list(reversed(readings))

def generate_telemetry_csv_stream(
    readings: List[SensorReading],
    chunk_size: int = 100
) -> Iterator[str]:
    """
    Streams sensor telemetry records into RFC 4180 CSV in chunks.
    Avoids monolithic in-memory string accumulation and prevents browser timeouts.
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    # CSV Headers
    writer.writerow([
        "reading_id",
        "batch_id",
        "timestamp_utc",
        "temperature_c",
        "relative_humidity_pct",
        "gas_resistance_raw_ratio",
        "gas_baseline_reference",
        "gas_deviation_pct",
        "current_weight_kg",
        "provenance",
        "sensor_device_id",
        "signal_quality",
    ])
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)

    # Establish baseline reference per batch (chronologically first sample seen)
    batch_baselines: Dict[str, float] = {}
    for r in readings:
        if r.batch_id not in batch_baselines:
            batch_baselines[r.batch_id] = r.gas_resistance_raw

    for idx, r in enumerate(readings, start=1):
        b_base = batch_baselines.get(r.batch_id, settings.GAS_BASELINE_DEFAULT_RATIO)
        if b_base > 0 and r.gas_resistance_raw < b_base:
            dev = round(((b_base - r.gas_resistance_raw) / b_base) * 100.0, 1)
        else:
            dev = 0.0
        ts_str = r.timestamp.isoformat() if r.timestamp else ""

        writer.writerow([
            r.id,
            r.batch_id,
            ts_str,
            f"{r.temperature_c:.2f}",
            f"{r.relative_humidity_pct:.2f}",
            f"{r.gas_resistance_raw:.3f}",
            f"{b_base:.3f}",
            f"{dev:.1f}",
            f"{r.current_weight_kg:.2f}" if r.current_weight_kg is not None else "",
            r.provenance,
            r.sensor_device_id,
            r.signal_quality,
        ])

        if idx % chunk_size == 0:
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    remainder = output.getvalue()
    if remainder:
        yield remainder

def format_telemetry_csv(readings: List[SensorReading]) -> str:
    """Formats sensor telemetry records into standard RFC 4180 CSV string."""
    return "".join(generate_telemetry_csv_stream(readings, chunk_size=500))
