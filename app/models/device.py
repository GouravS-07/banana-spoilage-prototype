from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean
from app.database import Base

class RegisteredDevice(Base):
    __tablename__ = "registered_devices"

    device_id = Column(String(64), primary_key=True)
    device_token = Column(String(128), nullable=False)   # Pre-shared hardware auth token
    description = Column(String(255), nullable=True)    # e.g. "ESP32 Lab Rig 1"
    is_active = Column(Boolean, nullable=False, default=True)
    registered_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
