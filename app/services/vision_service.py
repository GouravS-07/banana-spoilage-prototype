"""
Computer Vision Service - Phase 1 Placeholder Classifier.

IMPORTANT INTEGRITY DISCLOSURE:
In Phase 1, this service acts solely as an EXPLICITLY LABELED PLACEHOLDER.
It does NOT run a trained deep-learning model. It validates image upload,
saves the file to disk, and assigns an explicitly flagged placeholder ripeness
stage with is_mock_inference=True. Real model integration and evaluation occurs
in Phase 2 only after dataset licensing and validation are established.
"""

import shutil
from pathlib import Path
from datetime import datetime, timezone
from fastapi import UploadFile
from app.config import UPLOAD_DIR

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

def process_image_upload(batch_id: str, file: UploadFile) -> dict:
    """
    Saves image to uploads directory and returns an explicitly labeled mock inference.
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file format '{ext}'. Allowed: {ALLOWED_EXTENSIONS}")

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{batch_id}_{timestamp_str}{ext}"
    dest_path = UPLOAD_DIR / safe_filename

    # Save to disk
    with dest_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Return explicitly labeled placeholder
    return {
        "image_filename": safe_filename,
        "image_path": str(dest_path),
        "ripeness_stage": "RIPE",  # Default demonstration placeholder
        "confidence_score": 0.50,  # Explicit uncalibrated confidence
        "model_version": "placeholder-mock-heuristic-v1",
        "is_mock_inference": True,
    }
