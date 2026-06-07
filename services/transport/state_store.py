from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Mapping

from services.transport.models import TransportMode, TransportState
from solis.shared.canonical_json import canonical_json
from solis.shared.file_lock import atomic_write_text, exclusive_path_lock


class TransportStateStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        with self._lock:
            with exclusive_path_lock(self.path):
                if not self.path.exists():
                    self._write_unlocked(TransportState())

    def get(self) -> TransportState:
        with self._lock:
            with exclusive_path_lock(self.path):
                state = self._read_unlocked()
                if state is None:
                    state = TransportState()
                    self._write_unlocked(state)
                return state

    def set_mode(
        self,
        mode: TransportMode | str,
        *,
        actor: str,
        policy_version: str,
        node_id: str | None = None,
    ) -> TransportState:
        normalized_mode = TransportMode(str(mode.value if isinstance(mode, TransportMode) else mode).lower())

        def _mutate(state: TransportState) -> TransportState:
            state.mode = normalized_mode
            state.policy_version = str(policy_version)
            if node_id:
                state.node_id = str(node_id)
            state.health_status = "switching"
            state.updated_at = self._utc_now()
            return state

        return self._mutate_state(_mutate)

    def update_metrics(
        self,
        *,
        latency_ms: float,
        throughput_mbps: float,
        health_status: str,
        exit_fingerprint: str = "",
    ) -> TransportState:
        def _mutate(state: TransportState) -> TransportState:
            state.latency_ms = float(latency_ms)
            state.throughput_mbps = float(throughput_mbps)
            state.health_status = str(health_status)
            if exit_fingerprint:
                state.exit_fingerprint = str(exit_fingerprint)
            state.updated_at = self._utc_now()
            return state

        return self._mutate_state(_mutate)

    def update_policy_version(self, policy_version: str) -> TransportState:
        def _mutate(state: TransportState) -> TransportState:
            state.policy_version = str(policy_version)
            state.updated_at = self._utc_now()
            return state

        return self._mutate_state(_mutate)

    def as_dict(self) -> dict[str, Any]:
        return self.get().to_dict()

    def _mutate_state(self, mutator: Callable[[TransportState], TransportState]) -> TransportState:
        with self._lock:
            with exclusive_path_lock(self.path):
                state = self._read_unlocked()
                if state is None:
                    state = TransportState()
                next_state = mutator(state)
                self._write_unlocked(next_state)
                return next_state

    def _read_unlocked(self) -> TransportState | None:
        if not self.path.exists():
            return None
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return TransportState()
        return TransportState.from_dict(payload)

    def _write_unlocked(self, state: TransportState) -> None:
        atomic_write_text(self.path, canonical_json(state.to_dict()), encoding="utf-8")

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()


def bootstrap_transport_state(path: str | Path, payload: Mapping[str, Any] | None = None) -> None:
    state = TransportState.from_dict(payload or {})
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with exclusive_path_lock(target):
        atomic_write_text(target, canonical_json(state.to_dict()), encoding="utf-8")
