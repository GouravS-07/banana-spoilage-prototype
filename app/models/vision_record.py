from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class VisionRecord(Base):
    __tablename__ = "vision_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), ForeignKey("batches.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    
    image_filename = Column(String(255), nullable=False)
    image_path = Column(String(255), nullable=False)
    ripeness_stage = Column(String(32), nullable=False)   # "UNDER_RIPE", "RIPE", "OVER_RIPE", "DECAYING"
    confidence_score = Column(Float, nullable=False)       # 0.0 to 1.0
    
    # Provenance and model versioning
    model_version = Column(String(64), nullable=False)    # e.g. "placeholder-heuristic-v1"
    is_mock_inference = Column(Boolean, nullable=False, default=True) # Must be True for placeholder

    batch = relationship("Batch", back_populates="vision_records")
