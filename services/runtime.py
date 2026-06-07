from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from gdml.service import GDMLCoordinator
from qso_global_meta.service import GlobalMetaService
from services.crypto_access.service import CryptoAccessService
from services.entanglement_graph.service import EntanglementGraphService
from services.event_log.clock import LogicalClock
from services.event_log.service import EventLogService
from services.identity_authority.service import IdentityAuthorityService
from services.identity_verifier.service import IdentityVerifierService
from services.meta_learning.service import MetaLearningService
from services.plugins.service import PluginService
from services.quantum import QuantumManager, QuantumReplayEngine
from services.registry.service import RegistryService
from services.snapshot_exporter.service import SnapshotExporterService
from services.state_engine.service import StateEngineService
from services.transport import (
    DEFAULT_TRANSPORT_POLICY,
    CircuitRegistry,
    NetworkAuditLogger,
    TransportHealthMonitor,
    TransportManager,
    TransportMetricsCollector,
    TransportPolicyEngine,
    TransportStateStore,
)
from services.transport.dashboard import TransportVisualizationAPI
from storage.checkpoint_store import InMemoryCheckpointStore, JsonCheckpointStore
from storage.event_store import InMemoryEventStore, JsonlEventStore
from storage.indexing import EventIndex
from storage.snapshot_store import FileSnapshotStore, InMemorySnapshotStore


class QSOFabricRuntime:
    def __init__(self) -> None:
        self.mesh_mode = self._mesh_mode_enabled()
        self.registry = RegistryService()
        self.crypto = CryptoAccessService()
        self.clock = LogicalClock()
        self.event_index = EventIndex()
        self.event_store = self._build_event_store()
        self.checkpoint_store = self._build_checkpoint_store()
        self.snapshot_store = self._build_snapshot_store()
        self._enforce_mesh_persistence()
        self.event_log = EventLogService(self.crypto, event_store=self.event_store, index=self.event_index)
        self.state_engine = StateEngineService(self.registry, self.event_log, self.crypto, self.clock)
        self.entanglement = EntanglementGraphService()
        self.snapshot_exporter = SnapshotExporterService(self.crypto)
        self.meta_learning = MetaLearningService()
        self.plugins = PluginService()
        self.gdml = GDMLCoordinator(self.event_log, self.crypto, self.clock)
        self.global_meta = GlobalMetaService()
        self.quantum = QuantumManager(state_engine=self.state_engine, event_log=self.event_log)
        self.quantum_replay = QuantumReplayEngine(self.event_log)
        self.state_engine.set_policy_resolver(self.gdml.policy_sync.current)
        self.identity_authority = IdentityAuthorityService(self.state_engine, self.gdml.policy_sync)
        self.identity_verifier = IdentityVerifierService(
            state_engine=self.state_engine,
            event_log=self.event_log,
            snapshot_exporter=self.snapshot_exporter,
            crypto=self.crypto,
        )
        self.transport_policy = self._build_transport_policy()
        self.transport_state_store = self._build_transport_state_store()
        self.transport_audit = self._build_transport_audit_logger(self.crypto)
        self.transport_health = TransportHealthMonitor()
        self.transport_metrics = TransportMetricsCollector()
        self.transport_circuits = CircuitRegistry()
        self.transport = TransportManager(
            policy_engine=self.transport_policy,
            state_store=self.transport_state_store,
            audit_logger=self.transport_audit,
            health_monitor=self.transport_health,
            metrics_collector=self.transport_metrics,
            circuit_registry=self.transport_circuits,
            crypto=self.crypto,
        )
        self.transport_visualization = TransportVisualizationAPI(self.transport, self.transport_circuits)
        bootstrap_mode = os.getenv("QSO_TRANSPORT_MODE", "").strip().lower()
        if bootstrap_mode:
            try:
                self.transport.set_mode(
                    mode=bootstrap_mode,
                    actor="runtime-bootstrap",
                    policy_version=self.transport_policy.version,
                    node_id="bootstrap",
                )
            except Exception:
                pass

    @staticmethod
    def _build_event_store() -> InMemoryEventStore | JsonlEventStore:
        path = os.getenv("QSO_EVENT_STORE_PATH", "").strip()
        if path:
            return JsonlEventStore(path)
        return InMemoryEventStore()

    @staticmethod
    def _build_checkpoint_store() -> InMemoryCheckpointStore | JsonCheckpointStore:
        path = os.getenv("QSO_CHECKPOINT_STORE_PATH", "").strip()
        if path:
            return JsonCheckpointStore(path)
        return InMemoryCheckpointStore()

    @staticmethod
    def _build_snapshot_store() -> InMemorySnapshotStore | FileSnapshotStore:
        root = os.getenv("QSO_SNAPSHOT_STORE_DIR", "").strip()
        if root:
            return FileSnapshotStore(root)
        return InMemorySnapshotStore()

    @staticmethod
    def _build_transport_policy() -> TransportPolicyEngine:
        policy_path = os.getenv("QSO_TRANSPORT_POLICY_PATH", "").strip()
        policy_version = os.getenv("QSO_TRANSPORT_POLICY_VERSION", "v1").strip() or "v1"
        if policy_path:
            path = Path(policy_path)
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                return TransportPolicyEngine.from_mapping(payload, default_version=policy_version)
            except Exception:
                pass
        return TransportPolicyEngine.from_mapping(
            {
                "version": policy_version,
                "policy": DEFAULT_TRANSPORT_POLICY,
            },
            default_version=policy_version,
        )

    @staticmethod
    def _build_transport_state_store() -> TransportStateStore:
        path = os.getenv("QSO_TRANSPORT_STATE_PATH", ".codex/state/transport_state.json").strip()
        return TransportStateStore(path)

    @staticmethod
    def _build_transport_audit_logger(crypto: CryptoAccessService) -> NetworkAuditLogger:
        path = os.getenv("QSO_NETWORK_AUDIT_PATH", ".codex/state/network_audit.jsonl").strip()
        return NetworkAuditLogger(path, crypto=crypto)

    @staticmethod
    def _mesh_mode_enabled() -> bool:
        raw = os.getenv("QSO_MESH_MODE", "").strip().lower()
        return raw in {"1", "true", "yes", "on", "mesh", "required"}

    def _enforce_mesh_persistence(self) -> None:
        if not self.mesh_mode:
            return

        required_env = (
            "QSO_EVENT_STORE_PATH",
            "QSO_CHECKPOINT_STORE_PATH",
            "QSO_SNAPSHOT_STORE_DIR",
            "QSO_NETWORK_AUDIT_PATH",
            "QSO_TRANSPORT_STATE_PATH",
        )
        missing = [name for name in required_env if not os.getenv(name, "").strip()]
        if missing:
            formatted = ", ".join(sorted(missing))
            raise RuntimeError(f"mesh_mode_requires_env:{formatted}")

        unresolved = []
        if type(self.event_store) is InMemoryEventStore:
            unresolved.append("event_store=in_memory")
        if type(self.checkpoint_store) is InMemoryCheckpointStore:
            unresolved.append("checkpoint_store=in_memory")
        if type(self.snapshot_store) is InMemorySnapshotStore:
            unresolved.append("snapshot_store=in_memory")
        if unresolved:
            raise RuntimeError(f"mesh_mode_requires_persistent_stores:{','.join(unresolved)}")

    def health_report(self) -> Dict[str, Any]:
        components: Dict[str, Dict[str, Any]] = {}

        if isinstance(self.event_store, JsonlEventStore):
            ok, detail = self._path_ready(self.event_store.path.parent)
            components["event_store"] = {
                "ok": ok,
                "mode": "jsonl",
                "path": str(self.event_store.path),
                "detail": detail,
            }
        else:
            components["event_store"] = {"ok": True, "mode": "in_memory", "detail": "ephemeral"}

        if isinstance(self.checkpoint_store, JsonCheckpointStore):
            ok, detail = self._path_ready(self.checkpoint_store.path.parent)
            components["checkpoint_store"] = {
                "ok": ok,
                "mode": "json",
                "path": str(self.checkpoint_store.path),
                "detail": detail,
            }
        else:
            components["checkpoint_store"] = {"ok": True, "mode": "in_memory", "detail": "ephemeral"}

        if isinstance(self.snapshot_store, FileSnapshotStore):
            ok, detail = self._path_ready(self.snapshot_store.root)
            components["snapshot_store"] = {
                "ok": ok,
                "mode": "filesystem",
                "path": str(self.snapshot_store.root),
                "detail": detail,
            }
        else:
            components["snapshot_store"] = {"ok": True, "mode": "in_memory", "detail": "ephemeral"}

        plugin_count = len(self.plugins.list_demo_plugins())
        components["plugins"] = {
            "ok": True,
            "count": plugin_count,
            "detail": "loaded",
        }

        transport_state_path = self.transport_state_store.path
        ok_state, detail_state = self._path_ready(transport_state_path.parent)
        components["transport_state"] = {
            "ok": ok_state and transport_state_path.exists(),
            "path": str(transport_state_path),
            "detail": detail_state,
        }

        transport_audit_path = self.transport_audit.path
        ok_audit, detail_audit = self._path_ready(transport_audit_path.parent)
        chain_ok = self.transport.verify_audit_chain() if transport_audit_path.exists() else True
        components["transport_audit"] = {
            "ok": ok_audit and chain_ok,
            "path": str(transport_audit_path),
            "detail": detail_audit,
            "hash_chain_ok": chain_ok,
        }

        ok = all(bool(component.get("ok")) for component in components.values())
        return {
            "ok": ok,
            "mesh_mode": self.mesh_mode,
            "components": components,
        }

    @staticmethod
    def _path_ready(path: Path) -> tuple[bool, str]:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return False, f"mkdir_failed:{exc}"

        if not os.access(path, os.R_OK | os.W_OK | os.X_OK):
            return False, "insufficient_permissions"

        return True, "ok"
