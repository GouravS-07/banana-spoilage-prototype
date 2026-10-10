from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.batch import Batch
from app.models.device import RegisteredDevice
from app.models.telemetry import SensorReading
from app.schemas.telemetry import TelemetryIngestPayload, TelemetryResponse

router = APIRouter(prefix="/api/telemetry/physical", tags=["Telemetry (Physical Hardware)"])

@router.post("", response_model=TelemetryResponse, status_code=status.HTTP_201_CREATED)
def ingest_physical_telemetry(
    payload: TelemetryIngestPayload,
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token"),
    db: Session = Depends(get_db)
):
    """
    Ingest physical ESP32 sensor telemetry.
    STRICT PROVENANCE: Requires valid X-Device-Token header corresponding to
    a registered hardware device. Tags reading immutably as 'PHYSICAL_HARDWARE'.
    """
    if not x_device_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing 'X-Device-Token' header required for physical hardware telemetry."
        )

    # Verify device authorization
    device = db.query(RegisteredDevice).filter(
        RegisteredDevice.device_token == x_device_token,
        RegisteredDevice.is_active == True
    ).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or deactivated device token."
        )

    # Verify batch exists
    batch = db.query(Batch).filter(Batch.id == payload.batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch '{payload.batch_id}' does not exist."
        )

    reading = SensorReading(
        batch_id=payload.batch_id,
        timestamp=payload.timestamp or datetime.now(timezone.utc),
        temperature_c=payload.temperature_c,
        relative_humidity_pct=payload.relative_humidity_pct,
        gas_resistance_raw=payload.gas_resistance_raw,
        current_weight_kg=payload.current_weight_kg,
        provenance="PHYSICAL_HARDWARE",  # Server-verified hardware provenance
        ingestion_route="/api/telemetry/physical",
        sensor_device_id=device.device_id,
        signal_quality="OK",
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading
