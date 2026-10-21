"""
Integration tests for Computer Vision Pipeline & Sell-First Risk Adjustment.
Tests real model inference, class mapping (including HALF_RIPE), artifact failure fallback,
and risk engine score updates.
"""

import io
from PIL import Image
import numpy as np
import pytest

from app.services.risk_engine import evaluate_batch_risk, calculate_vision_penalty
import app.services.vision_service as vs

def create_synthetic_image_bytes(color_rgb=(255, 215, 0)):
    """Creates in-memory PNG bytes of a 224x224 banana test image."""
    arr = np.ones((224, 224, 3), dtype=np.uint8) * 245
    arr[40:180, 40:180] = color_rgb
    im = Image.fromarray(arr)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    buf.seek(0)
    return buf

def test_vision_upload_runs_real_model_and_sets_provenance(client):
    client.post("/api/batches", json={"id": "BATCH-VIS-REAL", "variety": "Cavendish"})

    # Send a yellow test image
    img_bytes = create_synthetic_image_bytes(color_rgb=(255, 215, 0))
    files = {"file": ("banana_yellow.png", img_bytes, "image/png")}
    data = {"batch_id": "BATCH-VIS-REAL"}

    resp = client.post("/api/vision/assess", data=data, files=files)
    assert resp.status_code == 201
    res = resp.json()

    assert res["batch_id"] == "BATCH-VIS-REAL"
    assert res["model_version"] == "color-rf-v1"
    assert res["is_mock_inference"] is False
    assert res["ripeness_stage"] in ["UNDER_RIPE", "HALF_RIPE", "RIPE", "OVER_RIPE"]
    assert 0.0 <= res["confidence_score"] <= 1.0

def test_half_ripe_stage_risk_penalty_and_engine_integration():
    """Verifies that HALF_RIPE penalty is documented and applied correctly."""
    assert calculate_vision_penalty("HALF_RIPE") == 20.0

    # Evaluate batch risk with HALF_RIPE
    result = evaluate_batch_risk(
        temperature_c=14.0,       # Penalty 0.0, weight 0.25
        relative_humidity_pct=88.0,# Penalty 0.0, weight 0.20
        gas_raw=0.98,             # Penalty 0.0, weight 0.15
        ripeness_stage="HALF_RIPE", # Penalty 20.0, weight 0.40
    )
    assert result["assessment_completeness"] == "COMPLETE"
    assert result["factor_penalties"]["vision"] == 20.0
    # Expected: 0.40 * 20.0 = 8.0 composite score
    assert result["composite_score"] == 8.0
    assert result["risk_tier"] == "LOW"

def test_vision_never_outputs_decay_without_pathology_data(client):
    """Verifies that vision output is strictly constrained to verified classes."""
    client.post("/api/batches", json={"id": "BATCH-VIS-DECAY-CHECK", "variety": "Cavendish"})

    # Send completely dark/brown image
    img_bytes = create_synthetic_image_bytes(color_rgb=(40, 20, 10))
    files = {"file": ("dark_banana.png", img_bytes, "image/png")}
    data = {"batch_id": "BATCH-VIS-DECAY-CHECK"}

    resp = client.post("/api/vision/assess", data=data, files=files)
    assert resp.status_code == 201
    res = resp.json()

    # Must NOT classify as DECAYING or ROTTEN
    assert res["ripeness_stage"] != "DECAYING"
    assert res["ripeness_stage"] != "ROTTEN"
    assert res["ripeness_stage"] in ["UNDER_RIPE", "HALF_RIPE", "RIPE", "OVER_RIPE"]

def test_vision_fallback_when_artifact_missing(client, monkeypatch):
    """Verifies graceful fallback to is_mock_inference=True when model artifact fails."""
    client.post("/api/batches", json={"id": "BATCH-VIS-FALLBACK", "variety": "Cavendish"})

    # Monkeypatch get_model_artifact to return None
    monkeypatch.setattr(vs, "get_model_artifact", lambda: None)

    img_bytes = create_synthetic_image_bytes()
    files = {"file": ("fallback_banana.png", img_bytes, "image/png")}
    data = {"batch_id": "BATCH-VIS-FALLBACK"}

    resp = client.post("/api/vision/assess", data=data, files=files)
    assert resp.status_code == 201
    res = resp.json()

    # Must fall back gracefully with mock flag set to True
    assert res["is_mock_inference"] is True
    assert "placeholder" in res["model_version"]
    assert res["confidence_score"] == 0.50

def test_sell_first_advisor_reflects_real_model_provenance(client):
    client.post("/api/batches", json={"id": "BATCH-VIS-PROV", "variety": "Cavendish"})
    
    # Ingest simulated telemetry
    client.post("/api/telemetry/simulated", json={
        "batch_id": "BATCH-VIS-PROV",
        "temperature_c": 19.0,
        "relative_humidity_pct": 82.0,
        "gas_resistance_raw": 0.92,
    })

    # Upload banana image
    img_bytes = create_synthetic_image_bytes()
    files = {"file": ("banana.png", img_bytes, "image/png")}
    client.post("/api/vision/assess", data={"batch_id": "BATCH-VIS-PROV"}, files=files)

    # Query Sell-First Advisor
    resp = client.get("/api/advisor/sell-first")
    assert resp.status_code == 200
    data = resp.json()

    target = next((b for b in data["ranked_batches"] if b["batch_id"] == "BATCH-VIS-PROV"), None)
    assert target is not None
    assert target["data_provenance"]["sensor_provenance"] == "SIMULATED"
    assert target["data_provenance"]["vision_provenance"] == "REAL_MODEL"
    assert target["assessment_completeness"] == "COMPLETE"
