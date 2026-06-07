from __future__ import annotations

from solis.integration.property_fraud.models import FraudFeatures, FraudRiskScore


def _risk_tier(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _confidence(features: FraudFeatures) -> float:
    signals = 0
    if features.holding_period_days is not None:
        signals += 1
    if features.consideration_to_value_ratio is not None:
        signals += 1
    if features.transfer_count_90d >= 0:
        signals += 1
    if features.transfer_count_365d >= 0:
        signals += 1
    if features.related_party_overlap:
        signals += 1
    if features.distress_signal_count > 0:
        signals += 1
    return min(0.99, 0.55 + 0.07 * signals)


def score_features(features: FraudFeatures) -> FraudRiskScore:
    score = 0
    reasons: list[str] = []

    if features.rapid_flip_180d:
        score += 25
        reasons.append("rapid_flip_180d")

    if features.transfer_count_90d >= 2:
        score += 20
        reasons.append("multi_transfer_90d")
    elif features.transfer_count_90d == 1:
        score += 10
        reasons.append("repeat_transfer_90d")

    if features.severe_undervalue_transfer:
        score += 25
        reasons.append("severe_undervalue_transfer")
    elif features.undervalue_transfer:
        score += 15
        reasons.append("undervalue_transfer")

    if features.related_party_overlap:
        score += 20
        reasons.append("related_party_overlap")

    if features.risky_instrument_type:
        score += 10
        reasons.append("risky_instrument_type")

    if features.grantee_acquisitions_90d >= 3:
        score += 10
        reasons.append("bulk_acquirer_90d")
    elif features.grantee_acquisitions_90d >= 1:
        score += 5
        reasons.append("repeat_acquirer_90d")

    if features.distress_signal_count > 0:
        score += min(15, features.distress_signal_count * 5)
        reasons.append("grantor_distress_context")

    if features.holding_period_days is not None and features.holding_period_days <= 30:
        score += 10
        reasons.append("sub_30d_holding_period")

    bounded_score = min(100, score)
    return FraudRiskScore(
        score=bounded_score,
        risk_tier=_risk_tier(bounded_score),
        reason_codes=tuple(reasons),
        confidence=round(_confidence(features), 3),
    )
