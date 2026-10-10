from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.batch import Batch
from app.models.telemetry import SensorReading
from app.schemas.telemetry import TelemetryIngestPayload, TelemetryResponse

router = APIRouter(prefix="/api/telemetry/simulated", tags=["Telemetry (Simulated)"])

@router.post("", response_model=TelemetryResponse, status_code=status.HTTP_201_CREATED)
def ingest_simulated_telemetry(payload: TelemetryIngestPayload, db: Session = Depends(get_db)):
    """
    Ingest simulated sensor telemetry.
    STRICT PROVENANCE: All readings sent to this endpoint are immutably tagged
    as 'SIMULATED' by the server. Client claims are ignored.
    """
    # Verify batch exists
    batch = db.query(Batch).filter(Batch.id == payload.batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch '{payload.batch_id}' does not exist. Create the batch first."
        )

    reading = SensorReading(
        batch_id=payload.batch_id,
        timestamp=payload.timestamp or datetime.now(timezone.utc),
        temperature_c=payload.temperature_c,
        relative_humidity_pct=payload.relative_humidity_pct,
        gas_resistance_raw=payload.gas_resistance_raw,
        current_weight_kg=payload.current_weight_kg,
        provenance="SIMULATED",  # Server-enforced provenance
        ingestion_route="/api/telemetry/simulated",
        sensor_device_id=payload.sensor_device_id or "SIMULATOR_V1",
        signal_quality="OK",
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading
