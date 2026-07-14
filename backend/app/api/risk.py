from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.logger import logger
from app.database.database import get_db
from app.models.risk_assessment import RiskAssessment
from app.repositories.event_repository import EventRepository
from app.repositories.risk_repository import RiskRepository
from app.schemas.risk_schema import RiskResponse
from app.services.risk_engine import RiskEngine

# NOTE: no prefix here - main.py already mounts this router under "/api/v1".
# The previous version set prefix="/api/v1" on both this router AND on the
# include_router() call in main.py, which produced "/api/v1/api/v1/score/..."
router = APIRouter(
    tags=["Risk Assessment"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Resource not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Server error"},
    },
)

_rule_engine = RiskEngine()


@router.post(
    "/score/{session_id}",
    response_model=RiskResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute (and persist) the risk assessment for a session",
    responses={
        status.HTTP_200_OK: {"description": "Risk assessment computed successfully"},
        status.HTTP_404_NOT_FOUND: {"description": "No events found for session"},
    },
)
def get_risk_score(
    session_id: str,
    db: Session = Depends(get_db),
) -> RiskResponse:
    """Compute a risk assessment for a session from its stored events.

    Pulls every event recorded for the session, runs it through the rule
    engine, persists the resulting RiskAssessment row, and returns the score.

    Args:
        session_id: ID of the session to assess
        db: Database session dependency

    Returns:
        RiskResponse: Freshly computed risk assessment data

    Raises:
        HTTPException: 404 if no events exist for this session
    """
    events = EventRepository(db).find_by_session(session_id)

    if not events:
        logger.warning(f"No events found for session {session_id}, cannot score")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No events found for this session",
        )

    website_risk = None
    payment_data = {}
    receiver_data = {}
    behaviour_data = {"event_count": len(events), "anomalies": 0}

    for event in events:
        event_type = (event.event_type or "").upper()
        if event_type == "WEBSITE_OPENED":
            website_risk = event.payload.get("website_risk")
        elif event_type == "PAYMENT_STARTED":
            payment_data = {
                "amount": event.payload.get("amount"),
                "status": "started",
                "receiver": {"name": event.payload.get("receiver")},
            }
            receiver_data = payment_data["receiver"]
        elif event_type == "PAYMENT_COMPLETED":
            payment_data = {
                "amount": event.payload.get("amount"),
                "status": "completed",
                "receiver": {"name": event.payload.get("receiver")},
            }
            receiver_data = payment_data["receiver"]

    result = _rule_engine.calculate_risk(
        website_risk=website_risk,
        payment_risk_or_data=payment_data,
        receiver_risk_or_data=receiver_data,
        behaviour_risk_or_data=behaviour_data,
    )

    assessment = RiskAssessment(
        session_id=session_id,
        score=result["overall_score"],
        level=result["risk_level"],
        confidence=result["confidence"],
        triggered_rules=result["reasons"],
        requires_physical_confirmation=result["requires_physical_confirmation"],
    )
    RiskRepository(db).save(assessment)

    logger.info(
        f"Risk assessment for session {session_id}: "
        f"{result['overall_score']}/{result['risk_level']} (reasons: {result['reasons']})"
    )

    return RiskResponse(
        score=result["overall_score"],
        level=result["risk_level"],
        confidence=result["confidence"],
        triggered_rules=result["reasons"],
        requires_physical_confirmation=result["requires_physical_confirmation"],
    )