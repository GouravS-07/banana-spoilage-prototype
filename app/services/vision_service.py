"""
Computer Vision Service - Real Color & Texture Baseline Model Inference.

SCIENTIFIC INTEGRITY & CALIBRATION DISCLOSURE:
---------------------------------------------
1. Supported Classes: Strictly limited to the 4 classes supported by verified training data:
   ["UNDER_RIPE", "HALF_RIPE", "RIPE", "OVER_RIPE"].
   Does NOT classify fruit as DECAYING or ROTTEN without validated pathological training data.
2. Confidence Score: Represents the ensemble tree-voting proportion (model agreement).
   It is UNCALIBRATED and must NOT be presented as a true Bayesian probability or food-safety guarantee.
3. Fail-Safe Provenance: Sets `is_mock_inference = False` only when model artifact loads and
   real inference succeeds. If the artifact is missing or unreadable, it explicitly falls back
   to `is_mock_inference = True` with a documented error flag.
"""

import shutil
import logging
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
from fastapi import UploadFile
import joblib

from app.config import UPLOAD_DIR, BASE_DIR
from app.services.vision_feature_extractor import extract_features_from_image

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Potential artifact locations
ARTIFACT_PATHS = [
    BASE_DIR / "vision_evaluation" / "baseline_color_rf.joblib",
    BASE_DIR / "app" / "models" / "baseline_color_rf.joblib",
]

_cached_model_data = None

def get_model_artifact():
    """Loads and caches the trained Random Forest artifact if available."""
    global _cached_model_data
    if _cached_model_data is not None:
        return _cached_model_data

    for p in ARTIFACT_PATHS:
        if p.exists():
            try:
                data = joblib.load(p)
                _cached_model_data = data
                logger.info(f"Loaded vision baseline artifact from {p}")
                return _cached_model_data
            except Exception as e:
                logger.error(f"Failed to load artifact from {p}: {e}")
    return None

def process_image_upload(batch_id: str, file: UploadFile) -> dict:
    """
    Saves image to uploads directory and runs the validated Color-RF baseline model.
    Falls back gracefully to mock placeholder if model artifact is unavailable.
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file format '{ext}'. Allowed: {ALLOWED_EXTENSIONS}")

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{batch_id}_{timestamp_str}{ext}"
    dest_path = UPLOAD_DIR / safe_filename

    # Save uploaded image to disk
    with dest_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    model_data = get_model_artifact()

    if model_data is not None:
        try:
            model = model_data["model"]
            class_codes = model_data["class_codes"]
            
            # Extract 12 explainable HSV and morphological features
            feats = extract_features_from_image(dest_path)
            feats_2d = feats.reshape(1, -1)

            # Perform real model inference
            pred_idx = int(model.predict(feats_2d)[0])
            predicted_stage = class_codes[pred_idx]

            # Compute tree-voting agreement proportion
            if hasattr(model, "predict_proba"):
                probs = model.predict_proba(feats_2d)[0]
                confidence = round(float(np.max(probs)), 3)
            else:
                confidence = 1.0

            return {
                "image_filename": safe_filename,
                "image_path": str(dest_path),
                "ripeness_stage": predicted_stage,
                "confidence_score": confidence,
                "model_version": "color-rf-v1",
                "is_mock_inference": False,
                "confidence_label": "uncalibrated_model_agreement",
            }
        except Exception as e:
            logger.error(f"Error during real vision inference on {safe_filename}: {e}")

    # Fallback if artifact is missing or inference encounters an error
    return {
        "image_filename": safe_filename,
        "image_path": str(dest_path),
        "ripeness_stage": "RIPE",
        "confidence_score": 0.50,
        "model_version": "placeholder-mock-heuristic-v1",
        "is_mock_inference": True,
        "confidence_label": "mock_placeholder",
    }
