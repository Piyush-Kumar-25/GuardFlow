from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class RiskEngine:
    """Aggregates structured sub-scores into a final overall risk score.

    The engine accepts either numeric sub-scores (0-100) or raw structured
    inputs for each category; when raw inputs are provided the engine will
    compute sub-scores using simple, replaceable helper functions. All
    scoring logic remains inside this module so the Correlation Engine only
    needs to supply pre-processed inputs.
    """

    weight_website: float = 0.35
    weight_payment: float = 0.35
    weight_receiver: float = 0.20
    weight_behaviour: float = 0.10

    def _normalize_score(self, v: Optional[float]) -> float:
        if v is None:
            return 0.0
        try:
            return max(0.0, min(100.0, float(v)))
        except Exception:
            return 0.0

    def _score_from_payment(self, payment: Dict[str, Any]) -> float:
        """Small heuristic to convert payment details into a 0-100 sub-score.

        This is intentionally simple and can be replaced by a more advanced
        model later. Keep logic here so Correlation Engine doesn't implement
        scoring.
        """
        if not payment:
            return 0.0
        amount = payment.get("amount") or 0
        status = (payment.get("status") or "").lower()
        r = payment.get("receiver") or ""
        if isinstance(r, dict):
            receiver = (r.get("name") or "").lower()
        else:
            receiver = str(r).lower()

        score = 0.0
        # larger amounts increase risk linearly (cap at 100)
        try:
            score += min(100.0, float(amount) / 1000.0)
        except Exception:
            score += 0.0

        # completed payments are slightly more risky than started (domain-specific)
        if status == "completed":
            score += 10.0

        # unknown or missing receiver increases risk
        if not receiver:
            score += 20.0

        return self._normalize_score(score)

    def _score_from_receiver(self, receiver_info: Dict[str, Any]) -> float:
        if not receiver_info:
            return 0.0
        # placeholder logic: unknown receiver -> higher risk
        name = (receiver_info.get("name") or "").strip()
        if not name:
            return 70.0
        # known safe receivers could be whitelisted later
        return 20.0

    def _score_from_behaviour(self, behaviour: Dict[str, Any]) -> float:
        if not behaviour:
            return 0.0
        # simple behaviour scoring: more anomalous => higher score
        anomalies = behaviour.get("anomalies", 0)
        return self._normalize_score(min(100.0, anomalies * 10))

    def calculate_risk(
        self,
        website_risk: Optional[float] = None,
        payment_risk_or_data: Optional[Any] = None,
        receiver_risk_or_data: Optional[Any] = None,
        behaviour_risk_or_data: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Calculate overall risk by combining sub-scores using weights.

        Each argument may be either a numeric 0-100 score or a structured
        dictionary which this engine will convert into a sub-score.
        Returns a dictionary with `overall_score`, `risk_level`, `confidence`,
        `reasons`, and `requires_physical_confirmation`.
        """
        # derive numeric sub-scores if raw data is provided
        website_score = self._normalize_score(website_risk)

        if isinstance(payment_risk_or_data, (int, float)):
            payment_score = self._normalize_score(payment_risk_or_data)
        else:
            payment_score = self._score_from_payment(payment_risk_or_data or {})

        if isinstance(receiver_risk_or_data, (int, float)):
            receiver_score = self._normalize_score(receiver_risk_or_data)
        else:
            receiver_score = self._score_from_receiver(receiver_risk_or_data or {})

        if isinstance(behaviour_risk_or_data, (int, float)):
            behaviour_score = self._normalize_score(behaviour_risk_or_data)
        else:
            behaviour_score = self._score_from_behaviour(behaviour_risk_or_data or {})

        overall = (
            website_score * self.weight_website
            + payment_score * self.weight_payment
            + receiver_score * self.weight_receiver
            + behaviour_score * self.weight_behaviour
        )

        overall = max(0.0, min(100.0, overall))

        # simple level mapping
        if overall >= 75:
            level = "CRITICAL"
        elif overall >= 50:
            level = "HIGH"
        elif overall >= 25:
            level = "MEDIUM"
        else:
            level = "LOW"

        # confidence derived from how many sub-scores are present and magnitude
        present = sum(1 for v in (website_score, payment_score, receiver_score, behaviour_score) if v > 0)
        confidence = int(min(95, 50 + present * 10 + overall / 10))

        reasons: List[str] = []
        if website_score > 50:
            reasons.append("Website analysis indicates concern")
        if payment_score > 50:
            reasons.append("Payment details look suspicious")
        if receiver_score > 50:
            reasons.append("Receiver information is incomplete or unknown")
        if behaviour_score > 50:
            reasons.append("Unusual user behaviour observed")

        return {
            "overall_score": int(round(overall)),
            "risk_level": level,
            "confidence": confidence,
            "reasons": reasons,
            "requires_physical_confirmation": level in ("HIGH", "CRITICAL"),
        }
