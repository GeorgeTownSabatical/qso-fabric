from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


class TransportMode(str, Enum):
    DIRECT = "direct"
    VPN = "vpn"
    TOR = "tor"


@dataclass(slots=True)
class TransportRequest:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    timeout_seconds: float = 10.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_inputs(
        cls,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str] | None = None,
        body: bytes | str | None = None,
        timeout_seconds: float = 10.0,
        metadata: Mapping[str, Any] | None = None,
    ) -> "TransportRequest":
        encoded_body: bytes
        if body is None:
            encoded_body = b""
        elif isinstance(body, bytes):
            encoded_body = body
        else:
            encoded_body = body.encode("utf-8")

        return cls(
            method=str(method).upper(),
            url=str(url),
            headers={str(k): str(v) for k, v in dict(headers or {}).items()},
            body=encoded_body,
            timeout_seconds=float(timeout_seconds),
            metadata={str(k): v for k, v in dict(metadata or {}).items()},
        )


@dataclass(slots=True)
class TransportResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes
    elapsed_ms: float
    mode: TransportMode
    adapter: str
    exit_fingerprint: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return 200 <= int(self.status_code) < 400 and not self.error

    def body_text(self) -> str:
        try:
            return self.body.decode("utf-8")
        except UnicodeDecodeError:
            return ""


@dataclass(slots=True)
class TransportState:
    mode: TransportMode = TransportMode.DIRECT
    node_id: str = "local"
    latency_ms: float = 0.0
    throughput_mbps: float = 0.0
    risk_profile: str = "balanced"
    policy_version: str = "v1"
    health_status: str = "unknown"
    exit_fingerprint: str = ""
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TransportState":
        mode_raw = str(payload.get("mode", TransportMode.DIRECT.value)).strip().lower()
        try:
            mode = TransportMode(mode_raw)
        except ValueError:
            mode = TransportMode.DIRECT

        return cls(
            mode=mode,
            node_id=str(payload.get("node_id", "local")),
            latency_ms=float(payload.get("latency_ms", 0.0)),
            throughput_mbps=float(payload.get("throughput_mbps", 0.0)),
            risk_profile=str(payload.get("risk_profile", "balanced")),
            policy_version=str(payload.get("policy_version", "v1")),
            health_status=str(payload.get("health_status", "unknown")),
            exit_fingerprint=str(payload.get("exit_fingerprint", "")),
            updated_at=str(payload.get("updated_at", datetime.now(timezone.utc).isoformat())),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "node_id": self.node_id,
            "latency_ms": round(float(self.latency_ms), 6),
            "throughput_mbps": round(float(self.throughput_mbps), 6),
            "risk_profile": self.risk_profile,
            "policy_version": self.policy_version,
            "health_status": self.health_status,
            "exit_fingerprint": self.exit_fingerprint,
            "updated_at": self.updated_at,
        }
