from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.batch import Batch
from app.models.vision_record import VisionRecord
from app.schemas.vision import VisionResponse
from app.services.vision_service import process_image_upload

router = APIRouter(prefix="/api/vision", tags=["Computer Vision"])

@router.post("/assess", response_model=VisionResponse, status_code=status.HTTP_201_CREATED)
async def assess_banana_image(
    batch_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Accepts banana image upload and generates a clearly labeled placeholder assessment.
    NOTE: In Phase 1, is_mock_inference is explicitly TRUE.
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch '{batch_id}' not found."
        )

    try:
        result = process_image_upload(batch_id=batch_id, file=file)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    now = datetime.now(timezone.utc)
    record = VisionRecord(
        batch_id=batch_id,
        timestamp=now,
        image_filename=result["image_filename"],
        image_path=result["image_path"],
        ripeness_stage=result["ripeness_stage"],
        confidence_score=result["confidence_score"],
        model_version=result["model_version"],
        is_mock_inference=result["is_mock_inference"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return VisionResponse(
        record_id=record.id,
        batch_id=record.batch_id,
        timestamp=record.timestamp,
        ripeness_stage=record.ripeness_stage,
        confidence_score=record.confidence_score,
        model_version=record.model_version,
        is_mock_inference=record.is_mock_inference,
        image_filename=record.image_filename,
    )
