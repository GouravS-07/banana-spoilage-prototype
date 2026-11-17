"""
Historical Telemetry, Gas Monitoring, and CSV Export Endpoints.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.batch import Batch
from app.services.gas_monitor import (
    get_historical_telemetry,
    compute_gas_baseline_metrics,
    generate_telemetry_csv_stream,
)

router = APIRouter(prefix="/api/telemetry", tags=["Telemetry Data & Gas Monitoring"])

@router.get("/history")
def get_telemetry_history(
    batch_id: Optional[str] = Query(None, description="Batch ID filter (e.g. BATCH-001-COLD) or omit for all"),
    limit: int = Query(150, ge=1, le=1000, description="Max readings to retrieve"),
    db: Session = Depends(get_db)
):
    """
    Retrieves chronological telemetry points for graphing and gas baseline analysis.
    All readings are explicitly labeled with their provenance ('SIMULATED').
    """
    if batch_id and batch_id != "ALL":
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found.")

    readings = get_historical_telemetry(db, batch_id=batch_id, limit=limit)
    gas_metrics = compute_gas_baseline_metrics(readings)

    points = [
        {
            "id": r.id,
            "batch_id": r.batch_id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "temperature_c": round(r.temperature_c, 2),
            "relative_humidity_pct": round(r.relative_humidity_pct, 2),
            "gas_resistance_raw": round(r.gas_resistance_raw, 3),
            "current_weight_kg": round(r.current_weight_kg, 2) if r.current_weight_kg is not None else None,
            "provenance": r.provenance,
            "is_simulated": (r.provenance == "SIMULATED"),
            "sensor_device_id": r.sensor_device_id,
            "signal_quality": r.signal_quality,
        }
        for r in readings
    ]

    return {
        "batch_id": batch_id or "ALL",
        "total_points": len(points),
        "gas_metrics": gas_metrics,
        "points": points,
    }

@router.get("/gas-baseline/{batch_id}")
def get_batch_gas_baseline(batch_id: str, db: Session = Depends(get_db)):
    """
    Returns gas monitoring baseline tracking and trend analysis for a batch.
    Includes deviation percentage, volatile trend status, and uncalibrated disclaimer.
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found.")

    readings = get_historical_telemetry(db, batch_id=batch_id, limit=200)
    metrics = compute_gas_baseline_metrics(readings)
    return {
        "batch_id": batch_id,
        "variety": batch.variety,
        "metrics": metrics,
    }

@router.get("/export/csv")
def export_telemetry_csv(
    batch_id: Optional[str] = Query(None, description="Batch ID filter or omit for all"),
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db)
):
    """
    Exports sensor telemetry history to downloadable CSV file via chunked streaming response.
    Includes raw readings, calculated baseline reference, deviation %, and simulation labels.
    Prevents browser hangs and high memory allocations on large exports.
    """
    if batch_id and batch_id != "ALL":
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found.")

    readings = get_historical_telemetry(db, batch_id=batch_id, limit=limit)

    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    b_slug = batch_id if (batch_id and batch_id != "ALL") else "all_batches"
    filename = f"banana_telemetry_{b_slug}_{now_str}.csv"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "text/csv; charset=utf-8",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "X-Content-Type-Options": "nosniff",
    }

    return StreamingResponse(
        content=generate_telemetry_csv_stream(readings, chunk_size=100),
        media_type="text/csv",
        headers=headers
    )
