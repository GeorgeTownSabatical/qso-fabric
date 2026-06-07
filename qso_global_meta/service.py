from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from qso_global_meta.meta_sync_engine import MetaSyncEngine


class GlobalMetaService:
    """High-level service wrapper so runtime code can call one thing."""

    def __init__(self) -> None:
        self.engine = MetaSyncEngine()

    def ingest_policy(self, node_id: str, policy: Mapping[str, Any]) -> Dict[str, Any]:
        return self.engine.ingest_policy(node_id=node_id, policy=policy)

    def ingest_learning(self, node_id: str, signals: Mapping[str, Any]) -> Dict[str, Any]:
        return self.engine.ingest_learning(node_id=node_id, signals=signals)

    def sync(self, *, total_nodes: Optional[int] = None, quorum: float = 0.51) -> Dict[str, Any]:
        return self.engine.sync(total_nodes=total_nodes, quorum=quorum)

    def snapshot(self) -> Dict[str, Any]:
        return self.engine.snapshot()

    def suggest(self) -> Dict[str, Any]:
        """Convenience accessor used by dashboards."""
        snap = self.engine.snapshot()
        last = snap.get("last_sync", {})
        if isinstance(last, dict) and last.get("status") == "ok":
            return last
        # If no sync yet, still provide deterministic shape
        return {
            "status": "idle",
            "consensus": snap.get("consensus"),
            "learning": snap.get("learning"),
        }

    def sync_from_runtime(self, runtime: Any, *, node_id: str = "local") -> Dict[str, Any]:
        """Optional helper: pull current policy from runtime GDML and ingest it."""
        policy = None
        try:
            if hasattr(runtime, "gdml") and hasattr(runtime.gdml, "policy_sync"):
                policy = runtime.gdml.policy_sync.current()
        except Exception:
            policy = None

        if isinstance(policy, dict):
            self.ingest_policy(node_id=node_id, policy=policy)

        return self.sync(total_nodes=None)
