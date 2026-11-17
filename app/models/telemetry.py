from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base

class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), ForeignKey("batches.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Measurements
    temperature_c = Column(Float, nullable=False)
    relative_humidity_pct = Column(Float, nullable=False)
    gas_resistance_raw = Column(Float, nullable=False)  # Raw uncalibrated sensor signal (Rs or ADC)
    current_weight_kg = Column(Float, nullable=True)     # Optional load cell

    # Strict Data Provenance Enforcement
    provenance = Column(String(32), nullable=False)      # "SIMULATED" or "PHYSICAL_HARDWARE"
    ingestion_route = Column(String(64), nullable=False) # e.g. "/api/telemetry/simulated"
    sensor_device_id = Column(String(64), nullable=False)# Simulator ID or authenticated device ID
    signal_quality = Column(String(32), nullable=False, default="OK")

    batch = relationship("Batch", back_populates="telemetry_readings")

    __table_args__ = (
        Index("ix_sensor_readings_batch_timestamp", "batch_id", "timestamp"),
    )
