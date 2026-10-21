"""
Tests for Vision Baseline Evaluation Pipeline.
Verifies feature extraction, model loading, and prediction contracts.
"""

from pathlib import Path
import numpy as np
import pytest
from PIL import Image
import joblib

from vision_evaluation.evaluate_baseline import (
    extract_features_from_image,
    CLASS_CODES,
)

BASE_DIR = Path(__file__).resolve().parent

@pytest.fixture
def dummy_banana_image(tmp_path):
    """Creates a temporary synthetic yellow banana patch image."""
    img_path = tmp_path / "test_yellow_banana.png"
    # Create 224x224 RGB image with central yellow banana area and white background
    arr = np.ones((224, 224, 3), dtype=np.uint8) * 245  # White background
    # Paint a yellow area in center (R=255, G=215, B=0)
    arr[50:180, 50:180, 0] = 255
    arr[50:180, 50:180, 1] = 215
    arr[50:180, 50:180, 2] = 20
    im = Image.fromarray(arr)
    im.save(img_path)
    return str(img_path)

def test_feature_extraction_dimension_and_bounds(dummy_banana_image):
    feats = extract_features_from_image(dummy_banana_image)
    assert isinstance(feats, np.ndarray)
    assert feats.shape == (12,)
    # Hue should be in yellow/green range (~40-60°)
    mean_h = feats[0]
    assert 20.0 <= mean_h <= 90.0
    # Yellow ratio should be high
    yellow_ratio = feats[7]
    assert yellow_ratio > 0.50

def test_saved_model_artifact_loading_and_inference(dummy_banana_image):
    artifact_path = BASE_DIR / "baseline_color_rf.joblib"
    assert artifact_path.exists(), "Trained model artifact baseline_color_rf.joblib must exist"

    data = joblib.load(artifact_path)
    model = data["model"]
    feature_names = data["feature_names"]
    class_codes = data["class_codes"]

    assert len(feature_names) == 12
    assert class_codes == ["UNDER_RIPE", "HALF_RIPE", "RIPE", "OVER_RIPE"]

    feats = extract_features_from_image(dummy_banana_image).reshape(1, -1)
    pred_idx = model.predict(feats)[0]
    pred_code = class_codes[pred_idx]
    probs = model.predict_proba(feats)[0]

    assert pred_code in class_codes
    assert len(probs) == 4
    assert np.isclose(np.sum(probs), 1.0)
