from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class TelemetryIngestPayload(BaseModel):
    batch_id: str = Field(..., description="ID of the batch this reading belongs to")
    timestamp: Optional[datetime] = Field(default=None, description="Timestamp of observation")
    temperature_c: float = Field(..., ge=-10.0, le=60.0, description="Temperature in °C")
    relative_humidity_pct: float = Field(..., ge=0.0, le=100.0, description="Relative humidity %")
    gas_resistance_raw: float = Field(..., gt=0.0, description="Raw uncalibrated sensor output/ratio")
    current_weight_kg: Optional[float] = Field(default=None, ge=0.0, description="Optional batch weight in kg")
    sensor_device_id: Optional[str] = Field(default=None, description="Optional device identifier")

class TelemetryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: str
    timestamp: datetime
    temperature_c: float
    relative_humidity_pct: float
    gas_resistance_raw: float
    current_weight_kg: Optional[float]
    provenance: str
    ingestion_route: str
    sensor_device_id: str
    signal_quality: str
