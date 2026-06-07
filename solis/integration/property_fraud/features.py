from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from solis.integration.property_fraud.models import DeedTransferEvent, FraudFeatures, TransferTokens
from solis.integration.property_fraud.tokenization import normalize_text


RISKY_INSTRUMENT_KEYWORDS = (
    "QUITCLAIM",
    "GIFT",
    "NOMINAL",
    "TRUST TRANSFER",
    "SPECIAL WARRANTY",
)


@dataclass
class FeatureState:
    property_history: dict[str, list[DeedTransferEvent]] = field(default_factory=dict)
    grantee_activity: dict[str, list[date]] = field(default_factory=dict)


def _days_between(current: date, prior: date) -> int:
    return (current - prior).days


def _related_party_overlap(event: DeedTransferEvent, tokens: TransferTokens) -> bool:
    if tokens.grantor_token_id == tokens.grantee_token_id:
        return True
    grantor_addr = normalize_text(event.grantor_address)
    grantee_addr = normalize_text(event.grantee_address)
    if grantor_addr and grantee_addr and grantor_addr == grantee_addr:
        return True
    return False


def _risky_instrument(instrument_type: str) -> bool:
    value = normalize_text(instrument_type)
    return any(keyword in value for keyword in RISKY_INSTRUMENT_KEYWORDS)


def build_features(event: DeedTransferEvent, tokens: TransferTokens, state: FeatureState) -> FraudFeatures:
    previous_property_events = state.property_history.get(tokens.property_token_id, [])
    previous_grantee_dates = state.grantee_activity.get(tokens.grantee_token_id, [])

    transfer_count_90d = 0
    transfer_count_365d = 0
    holding_period_days: int | None = None

    for prev in previous_property_events:
        diff = _days_between(event.recording_date, prev.recording_date)
        if diff < 0:
            continue
        if diff <= 90:
            transfer_count_90d += 1
        if diff <= 365:
            transfer_count_365d += 1

    if previous_property_events:
        latest = max(previous_property_events, key=lambda item: item.recording_date)
        diff = _days_between(event.recording_date, latest.recording_date)
        holding_period_days = diff if diff >= 0 else None

    grantee_acquisitions_90d = 0
    for prev_date in previous_grantee_dates:
        diff = _days_between(event.recording_date, prev_date)
        if 0 <= diff <= 90:
            grantee_acquisitions_90d += 1

    ratio: float | None = None
    if event.market_value_estimate and event.market_value_estimate > 0:
        ratio = event.consideration_amount / event.market_value_estimate

    undervalue = ratio is not None and ratio < 0.70
    severe_undervalue = ratio is not None and ratio < 0.50
    rapid_flip = holding_period_days is not None and holding_period_days <= 180
    related_party = _related_party_overlap(event, tokens)
    risky_instrument = _risky_instrument(event.instrument_type)

    return FraudFeatures(
        holding_period_days=holding_period_days,
        transfer_count_90d=transfer_count_90d,
        transfer_count_365d=transfer_count_365d,
        rapid_flip_180d=rapid_flip,
        consideration_to_value_ratio=ratio,
        undervalue_transfer=undervalue,
        severe_undervalue_transfer=severe_undervalue,
        related_party_overlap=related_party,
        risky_instrument_type=risky_instrument,
        grantee_acquisitions_90d=grantee_acquisitions_90d,
        distress_signal_count=len(event.grantor_distress_flags),
    )
