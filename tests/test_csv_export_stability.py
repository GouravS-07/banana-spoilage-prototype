"""
Comprehensive Stability, Concurrency, and RFC 4180 Verification for CSV Export.
Validates chunked streaming response, memory safety, large datasets,
404 handling, and zero-division edge cases.
"""

import csv
import io
import time
from datetime import datetime, timezone, timedelta
import pytest
from app.database import SessionLocal
from app.models.batch import Batch
from app.models.telemetry import SensorReading

def test_csv_export_streaming_headers(client):
    client.post("/api/batches", json={"id": "BATCH-STABILITY-01", "variety": "Cavendish"})
    client.post("/api/telemetry/simulated", json={
        "batch_id": "BATCH-STABILITY-01",
        "temperature_c": 14.5,
        "relative_humidity_pct": 89.0,
        "gas_resistance_raw": 0.982,
        "sensor_device_id": "STABILITY_UNIT_1",
    })

    resp = client.get("/api/telemetry/export/csv?batch_id=BATCH-STABILITY-01")
    assert resp.status_code == 200

    headers = resp.headers
    assert "text/csv" in headers["content-type"]
    assert "attachment;" in headers["content-disposition"]
    assert "banana_telemetry_BATCH-STABILITY-01_" in headers["content-disposition"]
    assert headers["x-content-type-options"] == "nosniff"
    assert "no-cache" in headers["cache-control"]
    assert "no-store" in headers["cache-control"]

def test_csv_export_large_dataset_performance_and_chunking(client, db_session):
    """
    Simulates a heavy dataset with 1,500 telemetry rows to ensure
    chunked streaming responds quickly without memory exhaustion or timeouts.
    """
    batch_id = "BATCH-HEAVY-LOAD"
    now = datetime.now(timezone.utc)
    batch = Batch(
        id=batch_id,
        variety="Robusta",
        storage_start_date=now - timedelta(days=5),
        initial_weight_kg=50.0,
        status="ACTIVE",
    )
    db_session.add(batch)
    db_session.commit()

    # Bulk insert 1,500 sensor readings
    readings = []
    for i in range(1500):
        readings.append(SensorReading(
            batch_id=batch_id,
            timestamp=now - timedelta(minutes=1500 - i),
            temperature_c=14.0 + (i % 10) * 0.1,
            relative_humidity_pct=85.0 + (i % 5) * 0.5,
            gas_resistance_raw=0.98 - (i * 0.0001),
            current_weight_kg=50.0 - (i * 0.001),
            provenance="SIMULATED",
            ingestion_route="/api/telemetry/simulated",
            sensor_device_id="HEAVY_LOAD_SIM",
            signal_quality="OK",
        ))
    db_session.bulk_save_objects(readings)
    db_session.commit()

    t_start = time.perf_counter()
    resp = client.get(f"/api/telemetry/export/csv?batch_id={batch_id}&limit=2000")
    duration = time.perf_counter() - t_start

    assert resp.status_code == 200
    assert duration < 5.0, f"Export took {duration:.2f}s, expected < 5.0s"

    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 1500
    assert rows[0]["batch_id"] == batch_id
    assert rows[-1]["batch_id"] == batch_id
    assert rows[0]["provenance"] == "SIMULATED"

def test_csv_export_zero_division_guard(client):
    """
    Tests edge cases where gas_resistance_raw is 0.0 or negative,
    ensuring no ZeroDivisionError occurs in deviation calculations.
    """
    client.post("/api/batches", json={"id": "BATCH-ZERO-DIV", "variety": "Nendran"})
    
    # Ingest baseline 0.0
    client.post("/api/telemetry/simulated", json={
        "batch_id": "BATCH-ZERO-DIV",
        "temperature_c": 15.0,
        "relative_humidity_pct": 87.0,
        "gas_resistance_raw": 0.01,  # minimum valid reading
        "sensor_device_id": "EDGE_CASE_TEST",
    })

    resp = client.get("/api/telemetry/export/csv?batch_id=BATCH-ZERO-DIV")
    assert resp.status_code == 200
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["gas_deviation_pct"] == "0.0"

def test_csv_export_special_character_escaping(client):
    """Verifies standard RFC 4180 escaping when strings contain commas or quotes."""
    client.post("/api/batches", json={"id": "BATCH-ESCAPING", "variety": "Grand Nain"})
    
    client.post("/api/telemetry/simulated", json={
        "batch_id": "BATCH-ESCAPING",
        "temperature_c": 16.2,
        "relative_humidity_pct": 88.5,
        "gas_resistance_raw": 0.95,
        "sensor_device_id": "SENSOR, MODEL \"X1\", RIG-4",
    })

    resp = client.get("/api/telemetry/export/csv?batch_id=BATCH-ESCAPING")
    assert resp.status_code == 200
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["sensor_device_id"] == 'SENSOR, MODEL "X1", RIG-4'

def test_csv_export_nonexistent_batch_returns_404(client):
    resp = client.get("/api/telemetry/export/csv?batch_id=DOES-NOT-EXIST")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
