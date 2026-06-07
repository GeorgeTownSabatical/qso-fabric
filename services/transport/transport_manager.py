from __future__ import annotations

import hashlib
from typing import Any, Mapping

from services.crypto_access.service import CryptoAccessService
from services.transport.adapters import BaseTransport, DirectAdapter, TorAdapter, VPNAdapter
from services.transport.audit_logger import NetworkAuditLogger
from services.transport.circuit_registry import CircuitRegistry
from services.transport.exit_classifier import ExitClassifier
from services.transport.health_monitor import TransportHealthMonitor
from services.transport.metrics_collector import TransportMetricsCollector
from services.transport.models import TransportMode, TransportRequest
from services.transport.policy_engine import TransportPolicyEngine
from services.transport.state_store import TransportStateStore
from services.transport.tpm_identity import HardwareIdentity
from solis.shared.canonical_json import canonical_json


class TransportManager:
    OBJECT_URI = "qso://infra.transport"

    def __init__(
        self,
        *,
        policy_engine: TransportPolicyEngine,
        state_store: TransportStateStore,
        audit_logger: NetworkAuditLogger,
        health_monitor: TransportHealthMonitor | None = None,
        metrics_collector: TransportMetricsCollector | None = None,
        circuit_registry: CircuitRegistry | None = None,
        exit_classifier: ExitClassifier | None = None,
        adapters: Mapping[str, BaseTransport] | None = None,
        crypto: CryptoAccessService | None = None,
        hardware_identity: HardwareIdentity | None = None,
    ) -> None:
        self.policy_engine = policy_engine
        self.state_store = state_store
        self.audit_logger = audit_logger
        self.health_monitor = health_monitor or TransportHealthMonitor()
        self.metrics_collector = metrics_collector or TransportMetricsCollector()
        self.circuit_registry = circuit_registry or CircuitRegistry()
        self.exit_classifier = exit_classifier or ExitClassifier()
        self.crypto = crypto
        self.hardware_identity = hardware_identity or HardwareIdentity()

        self.adapters: dict[str, BaseTransport] = {
            TransportMode.DIRECT.value: DirectAdapter(),
            TransportMode.VPN.value: VPNAdapter(),
            TransportMode.TOR.value: TorAdapter(),
        }
        if adapters is not None:
            self.adapters.update({str(k): v for k, v in adapters.items()})

    def set_mode(
        self,
        mode: TransportMode | str,
        *,
        actor: str,
        policy_version: str,
        node_id: str = "local",
        workload_type: str = "transport_control",
    ) -> dict[str, Any]:
        normalized_mode = TransportMode(str(mode.value if isinstance(mode, TransportMode) else mode).strip().lower())
        self.policy_engine.enforce(workload_type, normalized_mode)

        state = self.state_store.set_mode(
            normalized_mode,
            actor=actor,
            policy_version=policy_version,
            node_id=node_id,
        )
        circuit_id = self.circuit_registry.register(mode=normalized_mode.value)
        audit = self.audit_logger.log(
            actor=actor,
            object_uri=self.OBJECT_URI,
            kind="transport_mode_switch",
            policy_version=policy_version,
            payload={
                "mode": normalized_mode.value,
                "node_id": node_id,
                "circuit_id": circuit_id,
                "hardware_identity_hash": self.hardware_identity.derive_identity(),
            },
        )

        return {
            "state": state.to_dict(),
            "audit_event": audit,
            "circuit_id": circuit_id,
        }

    def send(
        self,
        workload_type: str,
        request: TransportRequest,
        *,
        actor: str,
        policy_version: str,
    ) -> dict[str, Any]:
        state = self.state_store.get()
        mode = state.mode
        self.policy_engine.enforce(workload_type, mode)

        adapter = self.adapters.get(mode.value)
        if adapter is None:
            raise KeyError(f"transport adapter not configured for mode: {mode.value}")

        response = adapter.send(request)
        health_snapshot = self.health_monitor.record(response)
        self.metrics_collector.record(workload_type, response)

        circuit_id = self.circuit_registry.register(mode=mode.value, exit_fingerprint=response.exit_fingerprint)
        self.circuit_registry.record_sample(circuit_id, latency_ms=response.elapsed_ms, ok=response.ok)

        updated_state = self.state_store.update_metrics(
            latency_ms=health_snapshot.avg_latency_ms,
            throughput_mbps=health_snapshot.avg_throughput_mbps,
            health_status=health_snapshot.health_status,
            exit_fingerprint=response.exit_fingerprint,
        )

        request_hash = self._hash(
            {
                "method": request.method,
                "url": request.url,
                "headers": request.headers,
                "body": request.body.decode("utf-8", errors="ignore"),
            }
        )
        response_hash = self._hash(
            {
                "status_code": response.status_code,
                "headers": response.headers,
                "body": response.body.decode("utf-8", errors="ignore"),
                "error": response.error,
            }
        )

        exit_profile: dict[str, Any] = {}
        if mode is TransportMode.TOR:
            exit_profile = self.exit_classifier.classify(
                exit_ip=response.headers.get("x-tor-exit-ip", "unknown"),
                country_code=response.headers.get("x-tor-country", ""),
                asn=response.headers.get("x-tor-asn", ""),
                abuse_score=float(request.metadata.get("tor_abuse_score", 0.0) or 0.0),
            )

        audit = self.audit_logger.log(
            actor=actor,
            object_uri=self.OBJECT_URI,
            kind="transport_send",
            policy_version=policy_version,
            payload={
                "mode": mode.value,
                "workload_type": workload_type,
                "status_code": int(response.status_code),
                "ok": response.ok,
                "request_hash": request_hash,
                "response_hash": response_hash,
                "latency_ms": round(response.elapsed_ms, 6),
                "throughput_mbps": round(health_snapshot.avg_throughput_mbps, 6),
                "exit_fingerprint": response.exit_fingerprint,
                "circuit_id": circuit_id,
                "exit_profile": exit_profile,
                "hardware_identity_hash": self.hardware_identity.derive_identity(),
            },
        )

        return {
            "response": response,
            "state": updated_state.to_dict(),
            "health": health_snapshot.to_dict(),
            "audit_event": audit,
            "circuit_id": circuit_id,
            "exit_profile": exit_profile,
        }

    def status(self) -> dict[str, Any]:
        state = self.state_store.get().to_dict()
        state["hardware_identity_hash"] = self.hardware_identity.derive_identity()
        return state

    def health(self) -> dict[str, dict[str, float | int | str]]:
        return self.health_monitor.all_snapshots()

    def policy(self) -> dict[str, object]:
        return self.policy_engine.export()

    def metrics(self) -> dict[str, dict[str, float | int | str]]:
        return self.metrics_collector.summary()

    def verify_audit_chain(self) -> bool:
        return self.audit_logger.verify_chain(verify_signature=self.crypto is not None)

    @staticmethod
    def _hash(payload: Mapping[str, Any]) -> str:
        return hashlib.sha256(canonical_json(dict(payload)).encode("utf-8")).hexdigest()
