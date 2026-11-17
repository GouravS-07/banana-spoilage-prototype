"""
Strict Server-Side Data Provenance Enforcement Tests.
Verifies that client payloads cannot falsify provenance, and physical hardware
ingestion strictly requires authenticated device tokens.
"""

def test_simulated_ingestion_enforces_simulated_provenance(client):
    # Setup batch
    client.post("/api/batches", json={"id": "BATCH-PROV-1", "variety": "Cavendish"})

    payload = {
        "batch_id": "BATCH-PROV-1",
        "temperature_c": 18.0,
        "relative_humidity_pct": 86.0,
        "gas_resistance_raw": 0.95,
        "sensor_device_id": "FAKE_CLIENT_CLAIM"
    }

    resp = client.post("/api/telemetry/simulated", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["provenance"] == "SIMULATED"
    assert data["ingestion_route"] == "/api/telemetry/simulated"

def test_physical_telemetry_disabled_by_default(client):
    """
    Verifies that physical telemetry ingestion is disabled by default
    when physical sensors/ESP32 are not connected.
    """
    client.post("/api/batches", json={"id": "BATCH-PROV-DISABLED", "variety": "Robusta"})

    payload = {
        "batch_id": "BATCH-PROV-DISABLED",
        "temperature_c": 18.0,
        "relative_humidity_pct": 86.0,
        "gas_resistance_raw": 0.95,
    }
    headers = {"X-Device-Token": "valid-test-token-xyz"}
    resp = client.post("/api/telemetry/physical", json=payload, headers=headers)
    assert resp.status_code == 503
    assert "Physical hardware telemetry ingestion is currently disabled" in resp.json()["detail"]

def test_physical_telemetry_rejects_missing_token_when_enabled(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "ENABLE_PHYSICAL_HARDWARE_INGESTION", True)

    client.post("/api/batches", json={"id": "BATCH-PROV-2", "variety": "Robusta"})

    payload = {
        "batch_id": "BATCH-PROV-2",
        "temperature_c": 18.0,
        "relative_humidity_pct": 86.0,
        "gas_resistance_raw": 0.95,
    }

    # No X-Device-Token header
    resp = client.post("/api/telemetry/physical", json=payload)
    assert resp.status_code == 401
    assert "Missing 'X-Device-Token'" in resp.json()["detail"]

def test_physical_telemetry_rejects_invalid_token_when_enabled(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "ENABLE_PHYSICAL_HARDWARE_INGESTION", True)

    client.post("/api/batches", json={"id": "BATCH-PROV-3", "variety": "Robusta"})

    payload = {
        "batch_id": "BATCH-PROV-3",
        "temperature_c": 18.0,
        "relative_humidity_pct": 86.0,
        "gas_resistance_raw": 0.95,
    }

    headers = {"X-Device-Token": "completely-bogus-token"}
    resp = client.post("/api/telemetry/physical", json=payload, headers=headers)
    assert resp.status_code == 401
    assert "Invalid or deactivated device token" in resp.json()["detail"]

def test_physical_telemetry_accepts_valid_token_and_sets_provenance_when_enabled(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "ENABLE_PHYSICAL_HARDWARE_INGESTION", True)

    client.post("/api/batches", json={"id": "BATCH-PROV-4", "variety": "Robusta"})

    payload = {
        "batch_id": "BATCH-PROV-4",
        "temperature_c": 14.5,
        "relative_humidity_pct": 87.0,
        "gas_resistance_raw": 0.98,
    }

    headers = {"X-Device-Token": "valid-test-token-xyz"}
    resp = client.post("/api/telemetry/physical", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["provenance"] == "PHYSICAL_HARDWARE"
    assert data["ingestion_route"] == "/api/telemetry/physical"
    assert data["sensor_device_id"] == "ESP32-TEST-UNIT"

def test_out_of_bounds_sensor_readings_rejected(client):
    client.post("/api/batches", json={"id": "BATCH-PROV-5", "variety": "Robusta"})

    # Impossible humidity > 100%
    payload_bad_rh = {
        "batch_id": "BATCH-PROV-5",
        "temperature_c": 20.0,
        "relative_humidity_pct": 115.0,
        "gas_resistance_raw": 0.90,
    }
    resp1 = client.post("/api/telemetry/simulated", json=payload_bad_rh)
    assert resp1.status_code == 422

    # Negative gas resistance
    payload_bad_gas = {
        "batch_id": "BATCH-PROV-5",
        "temperature_c": 20.0,
        "relative_humidity_pct": 80.0,
        "gas_resistance_raw": -5.0,
    }
    resp2 = client.post("/api/telemetry/simulated", json=payload_bad_gas)
    assert resp2.status_code == 422
