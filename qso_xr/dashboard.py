from __future__ import annotations

from typing import Any, Dict

from qso_xr.package_registry import coverage_summary


class XRDashboard:
    """Compact operational views for package coverage and runtime posture."""

    def package_view(self) -> Dict[str, Any]:
        return coverage_summary()

    def runtime_view(self, runtime: Any) -> Dict[str, Any]:
        return {
            "world_uri": getattr(runtime.scene_graph, "world_uri", ""),
            "scene_node_count": len(getattr(runtime.scene_graph, "nodes_by_uri", {})),
            "physics_tick": int(getattr(runtime.physics_engine, "tick", 0)),
            "stream_queue_size": int(runtime.stream_projection.size()),
            "entanglement_links": len(runtime.entanglement.snapshot()),
            "knowledge_claim_count": len(runtime.knowledge_lattice.claims()),
        }
