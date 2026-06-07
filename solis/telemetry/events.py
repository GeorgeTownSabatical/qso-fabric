from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from solis.schemas import SCHEMA_VERSION, parse_semver
from solis.shared.canonical_json import canonical_json
from solis.shared.hashing import sha256_hex_text

EXECUTION_TELEMETRY_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "execution_telemetry.schema.json"


class ExecutionTelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    event_id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    metric_ts: datetime
    latency_ms: int = Field(ge=0)
    slippage_bps: float
    reject_rate: float = Field(ge=0.0, le=1.0)
    model_drift_score: float = Field(ge=0.0)
    anomaly_flags: list[str] = Field(default_factory=list)
    extra_metrics: dict[str, float] = Field(default_factory=dict)
    event_hash: str | None = None

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, value: str) -> str:
        parse_semver(value)
        return value

    @field_validator("symbol")
    @classmethod
    def _normalize_symbol(cls, value: str) -> str:
        text = str(value).strip().upper()
        if not text:
            raise ValueError("symbol must be non-empty")
        return text

    def canonical_payload(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json", exclude={"event_hash"})
        return json.loads(canonical_json(payload))

    def compute_hash(self) -> str:
        return sha256_hex_text(canonical_json(self.canonical_payload()))

    def with_hash(self) -> "ExecutionTelemetryEvent":
        return self.model_copy(update={"event_hash": self.compute_hash()})


def validate_execution_telemetry_event(payload: dict[str, Any]) -> ExecutionTelemetryEvent:
    return ExecutionTelemetryEvent.model_validate(payload)


def load_execution_telemetry_schema(path: Path | None = None) -> dict[str, Any]:
    target = path or EXECUTION_TELEMETRY_SCHEMA_PATH
    loaded = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("execution telemetry schema must be a JSON object")
    return loaded
