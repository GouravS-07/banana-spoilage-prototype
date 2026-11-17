"""
Gas-Sensor Monitoring, Baseline Tracking, and CSV Export Tests.
Verifies simulated telemetry database persistence, historical time-series queries,
baseline deviation calculations, and CSV export formatting.
"""

import csv
import io
import pytest

def test_simulated_gas_telemetry_database_storage(client):
    client.post("/api/batches", json={"id": "BATCH-GAS-01", "variety": "Cavendish"})

    # Send simulated reading with gas resistance ratio
    payload = {
        "batch_id": "BATCH-GAS-01",
        "temperature_c": 14.5,
        "relative_humidity_pct": 88.0,
        "gas_resistance_raw": 0.985,
        "current_weight_kg": 25.1,
        "sensor_device_id": "SIM_FEED_01",
    }
    resp = client.post("/api/telemetry/simulated", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["batch_id"] == "BATCH-GAS-01"
    assert data["gas_resistance_raw"] == 0.985
    assert data["provenance"] == "SIMULATED"
    assert data["ingestion_route"] == "/api/telemetry/simulated"

def test_historical_telemetry_query_and_chronology(client):
    client.post("/api/batches", json={"id": "BATCH-GAS-02", "variety": "Robusta"})

    # Ingest 3 successive simulated readings
    ratios = [0.98, 0.94, 0.88]
    for r in ratios:
        client.post("/api/telemetry/simulated", json={
            "batch_id": "BATCH-GAS-02",
            "temperature_c": 19.0,
            "relative_humidity_pct": 84.0,
            "gas_resistance_raw": r,
            "sensor_device_id": "SIM_TEST",
        })

    resp = client.get("/api/telemetry/history?batch_id=BATCH-GAS-02&limit=50")
    assert resp.status_code == 200
    res = resp.json()

    assert res["batch_id"] == "BATCH-GAS-02"
    assert res["total_points"] == 3
    points = res["points"]
    assert len(points) == 3

    # Verify chronological ascending order
    assert points[0]["gas_resistance_raw"] == 0.98
    assert points[2]["gas_resistance_raw"] == 0.88
    for pt in points:
        assert pt["provenance"] == "SIMULATED"
        assert pt["is_simulated"] is True

def test_gas_baseline_tracking_metrics(client):
    client.post("/api/batches", json={"id": "BATCH-GAS-03", "variety": "Cavendish"})

    # Send readings showing volatile accumulation (ratio drops 0.98 -> 0.70)
    for r in [0.98, 0.85, 0.70]:
        client.post("/api/telemetry/simulated", json={
            "batch_id": "BATCH-GAS-03",
            "temperature_c": 25.0,
            "relative_humidity_pct": 92.0,
            "gas_resistance_raw": r,
        })

    resp = client.get("/api/telemetry/gas-baseline/BATCH-GAS-03")
    assert resp.status_code == 200
    res = resp.json()

    metrics = res["metrics"]
    assert metrics["baseline_ratio"] == 0.98
    assert metrics["current_ratio"] == 0.70
    # Expected deviation: (0.98 - 0.70) / 0.98 * 100 = 28.57% -> 28.6%
    assert metrics["deviation_pct"] == 28.6
    assert metrics["trend_status"] == "ELEVATED_VOLATILE_SURGE"
    assert metrics["provenance"] == "SIMULATED"
    assert "not calibrated ethylene" in metrics["scientific_note"].lower()

def test_csv_export_endpoint_format_and_provenance(client):
    client.post("/api/batches", json={"id": "BATCH-GAS-04", "variety": "Cavendish"})

    client.post("/api/telemetry/simulated", json={
        "batch_id": "BATCH-GAS-04",
        "temperature_c": 14.2,
        "relative_humidity_pct": 87.5,
        "gas_resistance_raw": 0.975,
        "current_weight_kg": 24.8,
        "sensor_device_id": "SIM_CSV_TEST",
    })

    resp = client.get("/api/telemetry/export/csv?batch_id=BATCH-GAS-04")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment;" in resp.headers["content-disposition"]
    assert "BATCH-GAS-04" in resp.headers["content-disposition"]

    # Parse CSV content
    content = resp.text
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    assert len(rows) >= 1

    first_row = rows[0]
    assert first_row["batch_id"] == "BATCH-GAS-04"
    assert float(first_row["temperature_c"]) == 14.20
    assert float(first_row["gas_resistance_raw_ratio"]) == 0.975
    assert first_row["provenance"] == "SIMULATED"
    assert first_row["sensor_device_id"] == "SIM_CSV_TEST"

def test_csv_export_all_batches(client):
    client.post("/api/batches", json={"id": "BATCH-ALL-A", "variety": "Cavendish"})
    client.post("/api/batches", json={"id": "BATCH-ALL-B", "variety": "Robusta"})

    client.post("/api/telemetry/simulated", json={
        "batch_id": "BATCH-ALL-A",
        "temperature_c": 14.0,
        "relative_humidity_pct": 88.0,
        "gas_resistance_raw": 0.98,
    })
    client.post("/api/telemetry/simulated", json={
        "batch_id": "BATCH-ALL-B",
        "temperature_c": 20.0,
        "relative_humidity_pct": 80.0,
        "gas_resistance_raw": 0.90,
    })

    resp = client.get("/api/telemetry/export/csv")
    assert resp.status_code == 200
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    batch_ids = {r["batch_id"] for r in rows}
    assert "BATCH-ALL-A" in batch_ids
    assert "BATCH-ALL-B" in batch_ids
    for r in rows:
        assert r["provenance"] == "SIMULATED"

def test_nonexistent_batch_returns_404(client):
    resp_base = client.get("/api/telemetry/gas-baseline/NON-EXISTENT")
    assert resp_base.status_code == 404

    resp_hist = client.get("/api/telemetry/history?batch_id=NON-EXISTENT")
    assert resp_hist.status_code == 404

    resp_csv = client.get("/api/telemetry/export/csv?batch_id=NON-EXISTENT")
    assert resp_csv.status_code == 404
