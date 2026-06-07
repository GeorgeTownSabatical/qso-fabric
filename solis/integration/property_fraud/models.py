from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Mapping


def _require_text(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    text = str(value).strip() if value is not None else ""
    if not text:
        raise ValueError(f"missing required field: {key}")
    return text


def _optional_text(data: Mapping[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(data: Mapping[str, Any], key: str) -> float | None:
    value = data.get(key)
    if value is None or value == "":
        return None
    return float(value)


def _require_float(data: Mapping[str, Any], key: str) -> float:
    if key not in data:
        raise ValueError(f"missing required field: {key}")
    value = data.get(key)
    if value is None or value == "":
        raise ValueError(f"missing required field: {key}")
    return float(value)


def _parse_recording_date(value: str) -> date:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return date.fromisoformat(text)


def _normalize_distress_flags(data: Mapping[str, Any]) -> tuple[str, ...]:
    raw = data.get("grantor_distress_flags", ())
    if raw is None:
        return ()
    if isinstance(raw, str):
        parts = [piece.strip() for piece in raw.split(",")]
        return tuple(piece for piece in parts if piece)
    if isinstance(raw, (list, tuple)):
        out = [str(item).strip() for item in raw]
        return tuple(item for item in out if item)
    raise ValueError("grantor_distress_flags must be a string, list, or tuple")


@dataclass(frozen=True)
class DeedTransferEvent:
    state_fips: str
    county_fips: str
    apn: str
    situs_address: str
    recording_date: date
    instrument_type: str
    document_number: str
    grantor_name: str
    grantee_name: str
    consideration_amount: float
    market_value_estimate: float | None = None
    grantor_address: str | None = None
    grantee_address: str | None = None
    grantor_distress_flags: tuple[str, ...] = field(default_factory=tuple)
    book: str | None = None
    page: str | None = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> DeedTransferEvent:
        return cls(
            state_fips=_require_text(raw, "state_fips"),
            county_fips=_require_text(raw, "county_fips"),
            apn=_require_text(raw, "apn"),
            situs_address=_require_text(raw, "situs_address"),
            recording_date=_parse_recording_date(_require_text(raw, "recording_date")),
            instrument_type=_require_text(raw, "instrument_type"),
            document_number=_require_text(raw, "document_number"),
            grantor_name=_require_text(raw, "grantor_name"),
            grantee_name=_require_text(raw, "grantee_name"),
            consideration_amount=_require_float(raw, "consideration_amount"),
            market_value_estimate=_optional_float(raw, "market_value_estimate"),
            grantor_address=_optional_text(raw, "grantor_address"),
            grantee_address=_optional_text(raw, "grantee_address"),
            grantor_distress_flags=_normalize_distress_flags(raw),
            book=_optional_text(raw, "book"),
            page=_optional_text(raw, "page"),
        )


@dataclass(frozen=True)
class TransferTokens:
    property_token_id: str
    grantor_token_id: str
    grantee_token_id: str
    instrument_token_id: str


@dataclass(frozen=True)
class FraudFeatures:
    holding_period_days: int | None
    transfer_count_90d: int
    transfer_count_365d: int
    rapid_flip_180d: bool
    consideration_to_value_ratio: float | None
    undervalue_transfer: bool
    severe_undervalue_transfer: bool
    related_party_overlap: bool
    risky_instrument_type: bool
    grantee_acquisitions_90d: int
    distress_signal_count: int


@dataclass(frozen=True)
class FraudRiskScore:
    score: int
    risk_tier: str
    reason_codes: tuple[str, ...]
    confidence: float


@dataclass(frozen=True)
class ScoredTransfer:
    event: DeedTransferEvent
    tokens: TransferTokens
    features: FraudFeatures
    risk: FraudRiskScore

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_fips": self.event.state_fips,
            "county_fips": self.event.county_fips,
            "apn": self.event.apn,
            "situs_address": self.event.situs_address,
            "recording_date": self.event.recording_date.isoformat(),
            "instrument_type": self.event.instrument_type,
            "document_number": self.event.document_number,
            "grantor_name": self.event.grantor_name,
            "grantee_name": self.event.grantee_name,
            "consideration_amount": self.event.consideration_amount,
            "market_value_estimate": self.event.market_value_estimate,
            "grantor_address": self.event.grantor_address,
            "grantee_address": self.event.grantee_address,
            "grantor_distress_flags": list(self.event.grantor_distress_flags),
            "book": self.event.book,
            "page": self.event.page,
            "tokens": {
                "property_token_id": self.tokens.property_token_id,
                "grantor_token_id": self.tokens.grantor_token_id,
                "grantee_token_id": self.tokens.grantee_token_id,
                "instrument_token_id": self.tokens.instrument_token_id,
            },
            "features": {
                "holding_period_days": self.features.holding_period_days,
                "transfer_count_90d": self.features.transfer_count_90d,
                "transfer_count_365d": self.features.transfer_count_365d,
                "rapid_flip_180d": self.features.rapid_flip_180d,
                "consideration_to_value_ratio": self.features.consideration_to_value_ratio,
                "undervalue_transfer": self.features.undervalue_transfer,
                "severe_undervalue_transfer": self.features.severe_undervalue_transfer,
                "related_party_overlap": self.features.related_party_overlap,
                "risky_instrument_type": self.features.risky_instrument_type,
                "grantee_acquisitions_90d": self.features.grantee_acquisitions_90d,
                "distress_signal_count": self.features.distress_signal_count,
            },
            "risk": {
                "score": self.risk.score,
                "risk_tier": self.risk.risk_tier,
                "reason_codes": list(self.risk.reason_codes),
                "confidence": self.risk.confidence,
            },
        }
