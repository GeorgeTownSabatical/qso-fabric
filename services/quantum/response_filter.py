from __future__ import annotations

from typing import Any

from api.mcp_tools.qso_tools import QSOMCPTools
from services.quantum.models import QuantumJob
from solis.shared.hashing import sha256_hex_obj


class QuantumResponseFilter:
    """Attach deterministic quantum diagnostics to QSO-managed responses."""

    def __init__(
        self,
        *,
        tools: QSOMCPTools | None = None,
        backend: str = "itensor",
        uri_prefix: str = "qso://quantum.state/filter",
        max_qubits: int = 8,
    ) -> None:
        self.tools = tools or QSOMCPTools()
        self.backend = backend
        self.uri_prefix = uri_prefix.rstrip("/")
        self.max_qubits = max(2, int(max_qubits))

    def filter_payload(self, payload: dict[str, Any], *, conversation_id: str = "main", phase: str = "response") -> dict[str, Any]:
        canonical_payload = self._canonicalize_payload(payload, conversation_id=conversation_id)
        seed = sha256_hex_obj({"phase": phase, "conversation_id": conversation_id, "payload": canonical_payload})
        job = self._build_job(seed=seed, canonical_payload=canonical_payload)
        self._ensure_quantum_object(job)
        execution = self.tools.qso_quantum_execute(job.uri, actor="qso.quantum.filter", policy_version="v1", node_id="local")
        return {
            "uri": job.uri,
            "backend": self.backend,
            "phase": phase,
            "seed": seed,
            "qubit_count": job.qubit_count,
            "result": dict(execution.get("result", {})),
        }

    def _build_job(self, *, seed: str, canonical_payload: dict[str, Any]) -> QuantumJob:
        messages = canonical_payload.get("messages", [])
        message_count = len(messages) if isinstance(messages, list) else 0
        qubit_count = min(self.max_qubits, max(2, min(4 + message_count, 8)))
        gates: list[dict[str, Any]] = [{"name": "h", "target": 0}, {"name": "cnot", "control": 0, "target": 1}]
        for idx in range(2, qubit_count):
            gates.append({"name": "h", "target": idx})
            gates.append({"name": "cz", "control": idx - 1, "target": idx})
        for idx, ch in enumerate(seed[: qubit_count * 2]):
            if int(ch, 16) % 2 == 1:
                gates.append({"name": "x", "target": idx % qubit_count})
        return QuantumJob(
            uri=f"{self.uri_prefix}/{seed[:24]}",
            backend=self.backend,
            qubit_count=qubit_count,
            circuit_spec={"gates": gates},
            measurement_schema={"shots": 512},
            metadata={
                "conversation_id": canonical_payload.get("conversation_id", "main"),
                "message_count": message_count,
                "payload_hash": sha256_hex_obj(canonical_payload),
            },
        )

    def _ensure_quantum_object(self, job: QuantumJob) -> None:
        payload = {
            "backend": job.backend,
            "qubit_count": job.qubit_count,
            "circuit_spec": job.circuit_spec,
            "measurement_schema": job.measurement_schema,
            "metadata": job.metadata,
        }
        try:
            self.tools.qso_read(job.uri)
        except KeyError:
            self.tools.qso_quantum_create(
                uri=job.uri,
                payload=payload,
                actor="qso.quantum.filter",
                policy_version="v1",
                node_id="local",
            )
            return
        self.tools.qso_patch(
            job.uri,
            payload,
            actor="qso.quantum.filter",
            policy_version="v1",
            node_id="local",
        )

    def _canonicalize_payload(self, payload: dict[str, Any], *, conversation_id: str) -> dict[str, Any]:
        messages = payload.get("messages", [])
        canonical_messages = []
        if isinstance(messages, list):
            for message in messages:
                if not isinstance(message, dict):
                    continue
                canonical_messages.append(
                    {
                        "author": str(message.get("author", "")),
                        "role": str(message.get("role", "")),
                        "content": str(message.get("content", "")),
                    }
                )
        return {
            "uri": str(payload.get("uri", "")),
            "conversation_id": conversation_id,
            "messages": canonical_messages,
        }
