from typing import Optional, Dict, Any
from pydantic import BaseModel

class SellFirstItem(BaseModel):
    rank: int
    batch_id: str
    variety: str
    risk_score: float
    risk_tier: str
    recommendation: str
    primary_driver: str
    assessment_completeness: str
    is_stale: bool
    data_provenance: Dict[str, str]
    factor_penalties: Dict[str, float]
    normalized_weights: Dict[str, float]
    latest_readings: Dict[str, Any]

class SellFirstResponse(BaseModel):
    generated_at: str
    total_active_batches: int
    ranked_batches: list[SellFirstItem]
