from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from solis.schemas import SCHEMA_VERSION, parse_semver

EXECUTION_INTENT_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "execution_intent.schema.json"

FORBIDDEN_ORDER_FIELDS = frozenset(
    {
        "qty",
        "quantity",
        "notional",
        "limit_price",
        "stop_price",
        "order_type",
        "side",
        "time_in_force",
        "client_order_id",
        "venue",
        "broker_order_id",
    }
)


class ExecutionIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    intent_id: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    as_of_ts: datetime
    symbol_set: list[str] = Field(min_length=1)
    requested_exposure_delta_bps: int = Field(ge=-10000, le=10000)
    horizon_ms: int = Field(gt=0)
    confidence: float = Field(ge=0.0, le=1.0)
    model_version: str = Field(min_length=1)
    features_commit_hash: str = Field(min_length=40, max_length=64)
    compiler_version: str | None = None
    policy_version: str | None = None
    risk_hints: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _reject_direct_order_authority(cls, raw: Any) -> Any:
        if not isinstance(raw, Mapping):
            return raw
        overlapping = sorted(field for field in raw.keys() if str(field) in FORBIDDEN_ORDER_FIELDS)
        if overlapping:
            raise ValueError(f"execution intent cannot contain direct order fields: {','.join(overlapping)}")
        return raw

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, value: str) -> str:
        parse_semver(value)
        return value

    @field_validator("symbol_set")
    @classmethod
    def _normalize_symbols(cls, symbols: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_symbol in symbols:
            symbol = str(raw_symbol).strip().upper()
            if not symbol:
                raise ValueError("symbol_set cannot contain empty symbols")
            if symbol in seen:
                continue
            seen.add(symbol)
            normalized.append(symbol)
        if not normalized:
            raise ValueError("symbol_set cannot be empty")
        return normalized

    @field_validator("features_commit_hash")
    @classmethod
    def _validate_commit_hash(cls, value: str) -> str:
        text = str(value).strip().lower()
        if len(text) not in {40, 64}:
            raise ValueError("features_commit_hash must be 40 or 64 hex chars")
        if any(ch not in "0123456789abcdef" for ch in text):
            raise ValueError("features_commit_hash must be lowercase hexadecimal")
        return text

    @field_validator("compiler_version")
    @classmethod
    def _validate_compiler_version(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parse_semver(value)
        return value

    @field_validator("policy_version")
    @classmethod
    def _validate_policy_version(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text.startswith("v") or not text[1:].isdigit():
            raise ValueError("policy_version must match v<integer>")
        return text


def validate_execution_intent(payload: Mapping[str, Any]) -> ExecutionIntent:
    return ExecutionIntent.model_validate(payload)


def load_execution_intent_schema(path: Path | None = None) -> dict[str, Any]:
    target = path or EXECUTION_INTENT_SCHEMA_PATH
    loaded = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("execution intent schema must be a JSON object")
    return loaded
