from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.orm import relationship
from app.database import Base

class Batch(Base):
    __tablename__ = "batches"

    id = Column(String(64), primary_key=True, index=True)
    variety = Column(String(64), nullable=False, default="Cavendish")
    storage_start_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    harvest_date = Column(DateTime, nullable=True)
    initial_weight_kg = Column(Float, nullable=True)
    status = Column(String(32), nullable=False, default="ACTIVE")  # ACTIVE, SOLD, DISCARDED
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    telemetry_readings = relationship("SensorReading", back_populates="batch", cascade="all, delete-orphan", order_by="desc(SensorReading.timestamp)")
    vision_records = relationship("VisionRecord", back_populates="batch", cascade="all, delete-orphan", order_by="desc(VisionRecord.timestamp)")
