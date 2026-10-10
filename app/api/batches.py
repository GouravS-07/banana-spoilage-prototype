from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.batch import Batch
from app.schemas.batch import BatchCreate, BatchResponse

router = APIRouter(prefix="/api/batches", tags=["Batches"])

@router.get("", response_model=List[BatchResponse])
def list_batches(status_filter: str = "ACTIVE", db: Session = Depends(get_db)):
    """Retrieve tracked batches by status."""
    query = db.query(Batch)
    if status_filter != "ALL":
        query = query.filter(Batch.status == status_filter)
    return query.order_by(Batch.created_at.desc()).all()

@router.post("", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
def create_batch(payload: BatchCreate, db: Session = Depends(get_db)):
    """Create a new banana batch record."""
    existing = db.query(Batch).filter(Batch.id == payload.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Batch with ID '{payload.id}' already exists."
        )

    now = datetime.now(timezone.utc)
    new_batch = Batch(
        id=payload.id,
        variety=payload.variety,
        storage_start_date=payload.storage_start_date or now,
        harvest_date=payload.harvest_date,
        initial_weight_kg=payload.initial_weight_kg,
        status="ACTIVE",
        notes=payload.notes,
        created_at=now,
    )
    db.add(new_batch)
    db.commit()
    db.refresh(new_batch)
    return new_batch

@router.get("/{batch_id}", response_model=BatchResponse)
def get_batch(batch_id: str, db: Session = Depends(get_db)):
    """Retrieve details of a specific batch."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found.")
    return batch
