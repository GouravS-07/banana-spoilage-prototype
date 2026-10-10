"""
Batch CRUD and validation tests.
"""

def test_create_and_get_batch(client):
    payload = {
        "id": "BATCH-TEST-01",
        "variety": "Cavendish",
        "initial_weight_kg": 15.5,
        "notes": "Test room alpha"
    }
    resp = client.post("/api/batches", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == "BATCH-TEST-01"
    assert data["variety"] == "Cavendish"
    assert data["status"] == "ACTIVE"

    # Fetch batch
    get_resp = client.get("/api/batches/BATCH-TEST-01")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == "BATCH-TEST-01"

def test_duplicate_batch_id_rejected(client):
    payload = {"id": "BATCH-DUP", "variety": "Cavendish"}
    resp1 = client.post("/api/batches", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post("/api/batches", json=payload)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"]

def test_get_nonexistent_batch_returns_404(client):
    resp = client.get("/api/batches/NON-EXISTENT")
    assert resp.status_code == 404
