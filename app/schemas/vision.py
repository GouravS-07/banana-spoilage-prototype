from datetime import datetime
from pydantic import BaseModel, ConfigDict

class VisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    record_id: int
    batch_id: str
    timestamp: datetime
    ripeness_stage: str
    confidence_score: float
    model_version: str
    is_mock_inference: bool
    image_filename: str
