"""
Advisor Ranking and Sell-First Prioritization Tests.
Verifies rank sorting, transparent explanations, and image placeholder endpoint.
"""

import io

def test_sell_first_ranking_order_and_explanations(client):
    # Create 3 batches
    client.post("/api/batches", json={"id": "BATCH-RANK-A", "variety": "Cavendish"})
    client.post("/api/batches", json={"id": "BATCH-RANK-B", "variety": "Robusta"})
    client.post("/api/batches", json={"id": "BATCH-RANK-C", "variety": "Cavendish"})

    # Send simulated readings:
    # Batch A: Optimal (Low risk)
    client.post("/api/telemetry/simulated", json={
        "batch_id": "BATCH-RANK-A",
        "temperature_c": 14.0,
        "relative_humidity_pct": 88.0,
        "gas_resistance_raw": 0.98,
    })
    # Batch B: Moderate ambient
    client.post("/api/telemetry/simulated", json={
        "batch_id": "BATCH-RANK-B",
        "temperature_c": 19.0,
        "relative_humidity_pct": 80.0,
        "gas_resistance_raw": 0.90,
    })
    # Batch C: Hotbox decay (High risk)
    client.post("/api/telemetry/simulated", json={
        "batch_id": "BATCH-RANK-C",
        "temperature_c": 28.0,
        "relative_humidity_pct": 96.0,
        "gas_resistance_raw": 0.60,
    })

    # Query Sell-First Advisor
    resp = client.get("/api/advisor/sell-first")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_active_batches"] == 3

    ranked = data["ranked_batches"]
    assert len(ranked) == 3

    # Rank 1 must be BATCH-RANK-C (highest risk)
    assert ranked[0]["batch_id"] == "BATCH-RANK-C"
    assert ranked[0]["rank"] == 1
    assert ranked[0]["risk_score"] > ranked[1]["risk_score"]
    assert ranked[1]["risk_score"] > ranked[2]["risk_score"]

    # Integrity check: Ensure explanations do NOT claim exact shelf life in days
    for item in ranked:
        assert "days left" not in item["primary_driver"].lower()
        assert "sell within 72" not in item["recommendation"].lower()
        assert item["data_provenance"]["sensor_provenance"] == "SIMULATED"

def test_image_upload_returns_explicit_placeholder(client):
    client.post("/api/batches", json={"id": "BATCH-IMG-01", "variety": "Cavendish"})

    # Create dummy image bytes
    dummy_image = io.BytesIO(b"fake-image-bytes-jpeg")
    files = {"file": ("test_banana.jpg", dummy_image, "image/jpeg")}
    data = {"batch_id": "BATCH-IMG-01"}

    resp = client.post("/api/vision/assess", data=data, files=files)
    assert resp.status_code == 201
    res_data = resp.json()

    assert res_data["batch_id"] == "BATCH-IMG-01"
    assert res_data["is_mock_inference"] is True
    assert "placeholder" in res_data["model_version"]
    assert res_data["ripeness_stage"] == "RIPE"
