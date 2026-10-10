"""
Advisor Engine - Sell-First Priority Ranking and Explanation Generator.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.batch import Batch
from app.models.telemetry import SensorReading
from app.models.vision_record import VisionRecord
from app.services.risk_engine import evaluate_batch_risk

def generate_sell_first_ranking(db: Session) -> dict:
    """
    Computes risk scores across all active batches and ranks them in Sell-First order.
    """
    batches = db.query(Batch).filter(Batch.status == "ACTIVE").all()
    ranked_list = []

    for b in batches:
        # Get latest telemetry
        latest_reading = (
            db.query(SensorReading)
            .filter(SensorReading.batch_id == b.id)
            .order_by(SensorReading.timestamp.desc())
            .first()
        )
        
        # Get latest vision record
        latest_vision = (
            db.query(VisionRecord)
            .filter(VisionRecord.batch_id == b.id)
            .order_by(VisionRecord.timestamp.desc())
            .first()
        )

        temp = latest_reading.temperature_c if latest_reading else None
        rh = latest_reading.relative_humidity_pct if latest_reading else None
        gas = latest_reading.gas_resistance_raw if latest_reading else None
        telemetry_time = latest_reading.timestamp if latest_reading else None
        sensor_prov = latest_reading.provenance if latest_reading else "NO_DATA"

        stage = latest_vision.ripeness_stage if latest_vision else None
        vision_prov = (
            "PLACEHOLDER_MOCK" if (latest_vision and latest_vision.is_mock_inference)
            else ("REAL_MODEL" if latest_vision else "NO_DATA")
        )

        evaluation = evaluate_batch_risk(
            temperature_c=temp,
            relative_humidity_pct=rh,
            gas_raw=gas,
            ripeness_stage=stage,
            last_telemetry_time=telemetry_time,
        )

        latest_readings_summary = {
            "temperature_c": temp,
            "relative_humidity_pct": rh,
            "gas_raw": gas,
            "ripeness_stage": stage,
            "last_reading_time": telemetry_time.isoformat() if telemetry_time else None,
        }

        ranked_list.append({
            "batch_id": b.id,
            "variety": b.variety,
            "risk_score": evaluation["composite_score"],
            "risk_tier": evaluation["risk_tier"],
            "recommendation": evaluation["recommendation"],
            "primary_driver": evaluation["primary_driver"],
            "assessment_completeness": evaluation["assessment_completeness"],
            "is_stale": evaluation["is_stale"],
            "data_provenance": {
                "sensor_provenance": sensor_prov,
                "vision_provenance": vision_prov,
            },
            "factor_penalties": evaluation["factor_penalties"],
            "normalized_weights": evaluation["normalized_weights"],
            "latest_readings": latest_readings_summary,
        })

    # Sort descending: highest risk score comes first (Rank 1 = Sell First)
    ranked_list.sort(key=lambda x: x["risk_score"], reverse=True)

    # Assign sequential ranks
    for idx, item in enumerate(ranked_list, start=1):
        item["rank"] = idx

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_active_batches": len(ranked_list),
        "ranked_batches": ranked_list,
    }
