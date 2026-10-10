from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.advisor import SellFirstResponse
from app.services.advisor_engine import generate_sell_first_ranking

router = APIRouter(prefix="/api/advisor", tags=["Advisor Engine"])

@router.get("/sell-first", response_model=SellFirstResponse)
def get_sell_first_priorities(db: Session = Depends(get_db)):
    """
    Returns active banana batches ranked by relative spoilage risk.
    Highlights top urgency drivers, provenance badges, and completeness flags.
    """
    return generate_sell_first_ranking(db)
