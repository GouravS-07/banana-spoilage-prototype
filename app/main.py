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
    telemetry_data_router,
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

            # Seed realistic time-series telemetry (strictly tagged as SIMULATED)
            # 10 historical readings per batch across the past 12 hours
            readings_to_seed = []
            
            # Batch 1: Optimal Cold Storage (stable baseline ~0.98, temp ~14°C, RH ~88%)
            for i in range(10, -1, -1):
                readings_to_seed.append(SensorReading(
                    batch_id=b1.id,
                    timestamp=now - timedelta(hours=i * 1.2),
                    temperature_c=round(14.0 + (i % 3) * 0.1, 2),
                    relative_humidity_pct=round(88.0 + (i % 2) * 0.5, 2),
                    gas_resistance_raw=round(0.98 - (10 - i) * 0.001, 3),
                    current_weight_kg=round(25.0 - (10 - i) * 0.01, 2),
                    provenance="SIMULATED",
                    ingestion_route="/api/telemetry/simulated",
                    sensor_device_id="SIMULATOR_SEED",
                    signal_quality="OK",
                ))

            # Batch 2: Ambient Store Shelf (mild volatile activity, gas drops 0.96 -> 0.91)
            for i in range(10, -1, -1):
                readings_to_seed.append(SensorReading(
                    batch_id=b2.id,
                    timestamp=now - timedelta(hours=i * 1.2),
                    temperature_c=round(19.2 + (i % 3) * 0.2, 2),
                    relative_humidity_pct=round(82.0 + (i % 2) * 0.8, 2),
                    gas_resistance_raw=round(0.96 - (10 - i) * 0.005, 3),
                    current_weight_kg=round(20.0 - (10 - i) * 0.04, 2),
                    provenance="SIMULATED",
                    ingestion_route="/api/telemetry/simulated",
                    sensor_device_id="SIMULATOR_SEED",
                    signal_quality="OK",
                ))

            # Batch 3: Hot & Humid Chamber (volatile surge, gas drops 0.92 -> 0.65)
            for i in range(10, -1, -1):
                readings_to_seed.append(SensorReading(
                    batch_id=b3.id,
                    timestamp=now - timedelta(hours=i * 1.2),
                    temperature_c=round(26.2 + (i % 3) * 0.3, 2),
                    relative_humidity_pct=round(93.5 + (i % 2) * 0.5, 2),
                    gas_resistance_raw=round(0.92 - (10 - i) * 0.027, 3),
                    current_weight_kg=round(28.0 - (10 - i) * 0.08, 2),
                    provenance="SIMULATED",
                    ingestion_route="/api/telemetry/simulated",
                    sensor_device_id="SIMULATOR_SEED",
                    signal_quality="OK",
                ))

            db.add_all(readings_to_seed)

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
app.include_router(telemetry_data_router)
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
