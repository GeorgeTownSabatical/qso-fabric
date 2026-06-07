from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Protocol

from api.mcp_tools.qso_tools import QSOMCPTools
from solis.telemetry.events import ExecutionTelemetryEvent


class TelemetrySink(Protocol):
    def emit(self, event: ExecutionTelemetryEvent) -> None: ...


@dataclass
class QSOTelemetrySink:
    tools: QSOMCPTools
    uri_prefix: str = "qso://solis.telemetry."
    actor: str = "solis.telemetry"
    policy_version: str = "v1"
    node_id: str = "solis"

    def emit(self, event: ExecutionTelemetryEvent) -> str:
        hashed = event.with_hash()
        uri = f"{self.uri_prefix}{hashed.event_id}"
        if not self.tools.runtime.registry.has(uri):
            self.tools.qso_create(uri, {"type": "solis_execution_telemetry"})
        self.tools.qso_patch(
            uri=uri,
            delta=hashed.model_dump(mode="json"),
            actor=self.actor,
            policy_version=self.policy_version,
            node_id=self.node_id,
        )
        return uri


class BoundedMemorySink:
    def __init__(self, *, max_events: int = 512) -> None:
        self.max_events = max(1, int(max_events))
        self._events: deque[dict[str, object]] = deque(maxlen=self.max_events)

    def emit(self, event: ExecutionTelemetryEvent) -> None:
        self._events.append(event.with_hash().model_dump(mode="json"))

    def drain(self) -> list[dict[str, object]]:
        rows = list(self._events)
        self._events.clear()
        return rows


class OpenTelemetrySink(BoundedMemorySink):
    pass


class PrometheusSink(BoundedMemorySink):
    pass


class TelemetryDispatcher:
    def __init__(
        self,
        *,
        qso_sink: QSOTelemetrySink,
        optional_sinks: list[TelemetrySink] | None = None,
    ) -> None:
        self.qso_sink = qso_sink
        self.optional_sinks = list(optional_sinks or [])

    def emit(self, event: ExecutionTelemetryEvent) -> str:
        uri = self.qso_sink.emit(event)
        for sink in self.optional_sinks:
            try:
                sink.emit(event)
            except Exception:
                # Optional sinks are intentionally best-effort and non-blocking.
                continue
        return uri
