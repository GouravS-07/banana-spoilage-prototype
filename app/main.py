"""
FastAPI Main Application Entrypoint.
Post-Harvest Spoilage Prediction & Sell-First Advisor (Banana Prototype).
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings, UPLOAD_DIR
from app.database import engine, Base, SessionLocal
from app.models.batch import Batch
from app.models.telemetry import SensorReading
from app.models.vision_record import VisionRecord
from app.models.device import RegisteredDevice
from app.api import (
    batches_router,
    telemetry_sim_router,
    telemetry_hw_router,
    vision_router,
    advisor_router,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

def seed_demo_data():
    """Seeds 3 demo batches and test device if database is unpopulated."""
    db = SessionLocal()
    try:
        # 1. Seed demo hardware device
        if not db.query(RegisteredDevice).filter(RegisteredDevice.device_id == "ESP32-DEV-RIG1").first():
            dev = RegisteredDevice(
                device_id="ESP32-DEV-RIG1",
                device_token="dev-esp32-secret-token-123",
                description="Member A ESP32 Breadboard Prototype (DHT22 + MQ-135)",
                is_active=True,
            )
            db.add(dev)

        # 2. Seed 3 demo batches if none exist
        if db.query(Batch).count() == 0:
            now = datetime.now(timezone.utc)
            
            # Batch 1: Optimal Cold Storage (Low Risk)
            b1 = Batch(
                id="BATCH-001-COLD",
                variety="Cavendish",
                storage_start_date=now - timedelta(days=2),
                harvest_date=now - timedelta(days=5),
                initial_weight_kg=25.0,
                status="ACTIVE",
                notes="Cold storage room 1; optimal climate target."
            )
            # Batch 2: Ambient Store Shelf (Moderate Risk)
            b2 = Batch(
                id="BATCH-002-AMBIENT",
                variety="Robusta",
                storage_start_date=now - timedelta(days=4),
                harvest_date=now - timedelta(days=8),
                initial_weight_kg=20.0,
                status="ACTIVE",
                notes="Retail display shelf; standard room ambient temperature."
            )
            # Batch 3: Hot & Humid Chamber (Critical Sell-First Priority)
            b3 = Batch(
                id="BATCH-003-HOTBOX",
                variety="Cavendish",
                storage_start_date=now - timedelta(days=6),
                harvest_date=now - timedelta(days=12),
                initial_weight_kg=28.0,
                status="ACTIVE",
                notes="Unventilated back storage; high temperature and moisture risk."
            )
            db.add_all([b1, b2, b3])
            db.commit()

            # Seed initial telemetry (strictly tagged as SIMULATED)
            # B1: Optimal temp (14°C), ideal humidity (88%), nominal clean air gas ratio (0.98)
            r1 = SensorReading(
                batch_id=b1.id,
                timestamp=now - timedelta(minutes=5),
                temperature_c=14.2,
                relative_humidity_pct=88.0,
                gas_resistance_raw=0.98,
                current_weight_kg=24.9,
                provenance="SIMULATED",
                ingestion_route="/api/telemetry/simulated",
                sensor_device_id="SIMULATOR_SEED",
                signal_quality="OK",
            )
            # B2: Warm temp (19°C), slightly low humidity (82%), mild gas variation (0.92)
            r2 = SensorReading(
                batch_id=b2.id,
                timestamp=now - timedelta(minutes=4),
                temperature_c=19.5,
                relative_humidity_pct=82.0,
                gas_resistance_raw=0.92,
                current_weight_kg=19.4,
                provenance="SIMULATED",
                ingestion_route="/api/telemetry/simulated",
                sensor_device_id="SIMULATOR_SEED",
                signal_quality="OK",
            )
            # B3: High heat (26.5°C), high humidity (94%), sharp gas resistance drop (0.68)
            r3 = SensorReading(
                batch_id=b3.id,
                timestamp=now - timedelta(minutes=2),
                temperature_c=26.5,
                relative_humidity_pct=94.0,
                gas_resistance_raw=0.68,
                current_weight_kg=26.8,
                provenance="SIMULATED",
                ingestion_route="/api/telemetry/simulated",
                sensor_device_id="SIMULATOR_SEED",
                signal_quality="OK",
            )
            db.add_all([r1, r2, r3])

            # Seed placeholder vision records (is_mock_inference=True)
            v1 = VisionRecord(
                batch_id=b1.id,
                timestamp=now - timedelta(minutes=10),
                image_filename="b1_seed.jpg",
                image_path="uploads/b1_seed.jpg",
                ripeness_stage="UNDER_RIPE",
                confidence_score=0.85,
                model_version="placeholder-mock-heuristic-v1",
                is_mock_inference=True,
            )
            v2 = VisionRecord(
                batch_id=b2.id,
                timestamp=now - timedelta(minutes=8),
                image_filename="b2_seed.jpg",
                image_path="uploads/b2_seed.jpg",
                ripeness_stage="RIPE",
                confidence_score=0.80,
                model_version="placeholder-mock-heuristic-v1",
                is_mock_inference=True,
            )
            v3 = VisionRecord(
                batch_id=b3.id,
                timestamp=now - timedelta(minutes=5),
                image_filename="b3_seed.jpg",
                image_path="uploads/b3_seed.jpg",
                ripeness_stage="OVER_RIPE",
                confidence_score=0.92,
                model_version="placeholder-mock-heuristic-v1",
                is_mock_inference=True,
            )
            db.add_all([v1, v2, v3])
            db.commit()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    seed_demo_data()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Post-Harvest Banana Spoilage Risk Scoring and Sell-First Prioritization Engine.",
    lifespan=lifespan,
)

# Register API routers
app.include_router(batches_router)
app.include_router(telemetry_sim_router)
app.include_router(telemetry_hw_router)
app.include_router(vision_router)
app.include_router(advisor_router)

# Mount static files and frontend
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", include_in_schema=False)
def serve_dashboard():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Banana Spoilage Advisor API is active. Visit /docs for Swagger API documentation."}

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "phase": "Phase 1 - Software Skeleton",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
