from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class BatchCreate(BaseModel):
    id: str = Field(..., min_length=2, max_length=64, description="Unique batch ID, e.g. BATCH-001")
    variety: str = Field(default="Cavendish", max_length=64)
    storage_start_date: Optional[datetime] = None
    harvest_date: Optional[datetime] = None
    initial_weight_kg: Optional[float] = Field(None, gt=0, le=5000.0)
    notes: Optional[str] = Field(None, max_length=255)

class BatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    variety: str
    storage_start_date: datetime
    harvest_date: Optional[datetime] = None
    initial_weight_kg: Optional[float] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
