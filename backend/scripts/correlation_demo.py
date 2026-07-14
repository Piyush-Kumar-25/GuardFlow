from datetime import datetime

from app.services.correlation_engine import CorrelationEngine
from app.services.risk_engine import RiskEngine


class StubWebsiteAnalyzer:
    def analyze(self, website: dict) -> dict:
        # very small deterministic stub: longer URLs slightly more risky
        url = website.get("url", "")
        score = min(100, len(url)) if url else 0
        return {"website_risk": float(score), "reason": "stub analysis", "confidence": 80}


class StubWarningService:
    threshold = 70

    def create_warning(self, session_id: str, result: dict) -> dict:
        return {"session_id": session_id, "message": f"Risk {result.get('overall_score')} exceeds threshold"}


def demo():
    now = datetime.utcnow()

    risk_engine = RiskEngine()
    website_analyzer = StubWebsiteAnalyzer()
    warning_service = StubWarningService()

    engine = CorrelationEngine(website_analyzer=website_analyzer, risk_engine=risk_engine, warning_service=warning_service)

    # Simulate a website_opened event
    engine.store_website_event("ABC123", url="https://example.com/suspicious-offer", title="Special Offer", timestamp=now)

    # Simulate payment started
    engine.store_payment_started("ABC123", amount=50000, receiver="XYZ Pvt Ltd", timestamp=now)

    # Optionally complete payment
    engine.store_payment_completed("ABC123", amount=50000, receiver="XYZ Pvt Ltd", timestamp=now)

    # Calculate overall risk
    result = engine.calculate_overall_risk("ABC123")

    print("Session:")
    print(engine.get_session("ABC123"))
    print("\nRisk Result:")
    print(result)


if __name__ == "__main__":
    demo()
