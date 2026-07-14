from typing import Any, Dict, Optional


class CorrelationEngine:
    """Central orchestrator that maintains session state and coordinates
    analysis services.

    Responsibilities:
    - Maintain in-memory session store (later can be persisted)
    - Collect events for sessions and update state
    - Coordinate Website Analyzer and Risk Engine (injected)
    - Expose simple API for storing events and calculating overall risk
    """

    def __init__(self, website_analyzer: Optional[Any] = None, risk_engine: Optional[Any] = None, warning_service: Optional[Any] = None):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.website_analyzer = website_analyzer
        self.risk_engine = risk_engine
        self.warning_service = warning_service

    def _ensure_session(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "session_id": session_id,
                "events": [],
                "website": {},
                "payment": {},
                "analysis": {},
                "overall_risk": None,
            }
        return self.sessions[session_id]

    def add_event(self, session_id: str, event: Dict[str, Any]) -> None:
        s = self._ensure_session(session_id)
        s["events"].append(event)

    def store_website_event(self, session_id: str, url: str, title: Optional[str] = None, timestamp: Optional[Any] = None, raw_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        s = self._ensure_session(session_id)
        s["website"] = {
            "url": url,
            "title": title,
            "timestamp": timestamp,
            "raw": raw_payload or {},
        }

        # Kick off website analysis if service provided
        if self.website_analyzer:
            analysis = self.website_analyzer.analyze(s["website"])
            s["analysis"]["website"] = analysis
        return s["website"]

    def store_payment_started(self, session_id: str, amount: Optional[float] = None, receiver: Optional[str] = None, timestamp: Optional[Any] = None, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        s = self._ensure_session(session_id)
        s["payment"] = {
            "status": "started",
            "amount": amount,
            "receiver": {"name": receiver} if receiver else {},
            "timestamp": timestamp,
            "raw": extra or {},
        }
        return s["payment"]

    def store_payment_completed(self, session_id: str, amount: Optional[float] = None, receiver: Optional[str] = None, timestamp: Optional[Any] = None, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        s = self._ensure_session(session_id)
        s["payment"] = {
            "status": "completed",
            "amount": amount,
            "receiver": {"name": receiver} if receiver else {},
            "timestamp": timestamp,
            "raw": extra or {},
        }
        return s["payment"]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.sessions.get(session_id)

    def calculate_overall_risk(self, session_id: str) -> Dict[str, Any]:
        s = self._ensure_session(session_id)

        website_analysis = s.get("analysis", {}).get("website") or {}
        website_risk = website_analysis.get("website_risk") if isinstance(website_analysis, dict) else None

        payment = s.get("payment") or {}

        receiver = payment.get("receiver") or {}

        behaviour = {
            # example behaviour inputs - keep simple for now
            "event_count": len(s.get("events", [])),
            "anomalies": s.get("analysis", {}).get("behaviour_anomalies", 0),
        }

        if not self.risk_engine:
            raise RuntimeError("Risk engine not configured")

        result = self.risk_engine.calculate_risk(
            website_risk=website_risk,
            payment_risk_or_data=payment,
            receiver_risk_or_data=receiver,
            behaviour_risk_or_data=behaviour,
        )

        s["overall_risk"] = result

        # Optionally trigger warning service
        if self.warning_service and result.get("overall_score", 0) >= getattr(self.warning_service, "threshold", 80):
            warning = self.warning_service.create_warning(session_id, result)
            s.setdefault("warnings", []).append(warning)

        return result
