from datetime import datetime
from uuid import UUID
from typing import Optional, Literal

from app.core.logger import logger
from app.repositories.event_repository import EventRepository
from app.schemas.event_schema import EventRequest, EventResponse
from app.models.event import Event
from app.services.correlation_engine import CorrelationEngine
from app.services.risk_engine import RiskEngine
from app.models.risk_assessment import RiskAssessment
from app.repositories.risk_repository import RiskRepository

class EventProcessor:
    """Core service for event processing and risk evaluation."""

    def __init__(self, event_repository: EventRepository):
        self.event_repository = event_repository

    def process_event(self, event_data: EventRequest) -> EventResponse:
        """Validate, persist, and process an event.

        Args:
            event_data: Validated incoming event data

        Returns:
            Standardized response indicating processing status
        """
        try:
            # Convert to ORM model
            event = Event(
                id=event_data.event_id,
                session_id=event_data.session_id,
                event_type=event_data.event_type,
                source_app=event_data.source_app,
                timestamp=event_data.timestamp,
                payload=event_data.payload,
            )

            # Persist event
            saved_event = self.event_repository.save(event)
            logger.info(f"Processed event {saved_event.event_type} for session {saved_event.session_id}")

            # Update correlation engine (in-memory orchestration)
            # Use a module-level CorrelationEngine instance to coordinate analysis
            try:
                if not hasattr(self, "_correlation_engine"):
                    # initialize once per EventProcessor instance
                    self._correlation_engine = CorrelationEngine(
                        website_analyzer=None,
                        risk_engine=RiskEngine(),
                        warning_service=None,
                    )

                etype = (event_data.event_type or "").upper()
                payload = event_data.payload or {}

                if etype == "WEBSITE_OPENED":
                    url = payload.get("url") or payload.get("link")
                    title = payload.get("title")
                    self._correlation_engine.store_website_event(saved_event.session_id, url=url, title=title, timestamp=saved_event.timestamp, raw_payload=payload)

                if etype == "PAYMENT_STARTED":
                    amount = payload.get("amount")
                    receiver = payload.get("receiver")
                    self._correlation_engine.store_payment_started(saved_event.session_id, amount=amount, receiver=receiver, timestamp=saved_event.timestamp, extra=payload)

                if etype == "PAYMENT_COMPLETED":
                    amount = payload.get("amount")
                    receiver = payload.get("receiver")
                    self._correlation_engine.store_payment_completed(saved_event.session_id, amount=amount, receiver=receiver, timestamp=saved_event.timestamp, extra=payload)

                # Recalculate overall risk and persist
                try:
                    risk_result = self._correlation_engine.calculate_overall_risk(saved_event.session_id)
                    assessment = RiskAssessment(
                        session_id=saved_event.session_id,
                        score=risk_result.get("overall_score", 0),
                        level=risk_result.get("risk_level", "LOW"),
                        confidence=risk_result.get("confidence", 0),
                        triggered_rules=risk_result.get("reasons", []),
                        requires_physical_confirmation=risk_result.get("requires_physical_confirmation", False),
                    )
                    RiskRepository(self.event_repository.db).save(assessment)
                except Exception as e:
                    logger.warning(f"Failed to calculate/persist risk for session {saved_event.session_id}: {e}")
            except Exception as e:
                logger.warning(f"Correlation engine update failed: {e}")

            # Future extension points:
            # - AI processing pipeline
            # - Rule engine evaluation
            # - Asynchronous workflows

            return EventResponse(
                status="success",
                message=f"Event {saved_event.id} processed"
            )

        except Exception as e:
            logger.error(f"Event processing failed: {str(e)}")
            return EventResponse(
                status="error",
                message="Event processing failed"
            )