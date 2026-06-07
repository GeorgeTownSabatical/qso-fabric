from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Mapping

from qso_xr.arkit_adapter import ARKitAdapter
from qso_xr.avatar_engine import XRAvatarEngine
from qso_xr.dashboard import XRDashboard
from qso_xr.determinism import deterministic_frame_hash
from qso_xr.demo_examples import get_demo_example, list_demo_examples
from qso_xr.entanglement_propagator import XREntanglementPropagator
from qso_xr.knowledge_lattice import ConsistencyConflict, KnowledgeLattice
from qso_xr.llm_scene_director import LLMSceneDirector
from qso_xr.package_registry import coverage_summary
from qso_xr.physics_engine import XRPhysicsEngine
from qso_xr.qff_exporter import build_qff_document, export_qff_json
from qso_xr.scene_graph import XRSceneGraph
from qso_xr.stream_projection import XRStreamProjection


PROFILE_CONFIDENCE_THRESHOLDS: Dict[str, float] = {
    "cinematic_low_light": 0.55,
    "analytic_educational": 0.8,
}


class QSOXRRuntime:
    """MVP runtime that composes deterministic XR core + knowledge lattice."""

    def __init__(
        self,
        *,
        world_uri: str = "qso://xr.world/default",
        knowledge_state_dir: str | Path = ".codex/state/xr_knowledge",
        stream_max_size: int = 256,
        backpressure: str = "drop_oldest",
    ) -> None:
        self.scene_graph = XRSceneGraph(world_uri=world_uri)
        self.arkit_adapter = ARKitAdapter()
        self.physics_engine = XRPhysicsEngine()
        self.stream_projection = XRStreamProjection(max_size=stream_max_size, backpressure=backpressure)
        self.avatar_engine = XRAvatarEngine()
        self.entanglement = XREntanglementPropagator()
        self.knowledge_lattice = KnowledgeLattice(knowledge_state_dir)
        self.scene_director = LLMSceneDirector()
        self.dashboard = XRDashboard()
        self._frame = 0

    def upsert_world_node(self, node_uri: str, patch: Mapping[str, Any], *, actor: str = "xr.runtime") -> Dict[str, Any]:
        out = self.scene_graph.upsert_node(node_uri, patch)
        projection = self._compile_projection(uri=node_uri, delta=dict(patch), actor=actor)
        self.stream_projection.publish(projection)
        propagated = self.entanglement.propagate(node_uri, dict(patch))
        for row in propagated:
            self.stream_projection.publish(self._compile_projection(uri=row["uri"], delta=row["delta"], actor=actor, meta=row))
        return {"node": out, "projection": projection, "entangled_emissions": len(propagated)}

    def render_scene(self, *, viewpoint: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        self._frame += 1
        payload = self.scene_graph.project(viewpoint=viewpoint, frame=self._frame)
        payload["frame_hash"] = deterministic_frame_hash(payload)
        return payload

    def tick_physics(self, *, dt_ms: float = 16.0, gravity: Any = None, actor: str = "xr.physics") -> Dict[str, Any]:
        event = self.physics_engine.step(dt_ms=dt_ms, gravity=gravity)
        projection = self._compile_projection(
            uri=f"{self.scene_graph.world_uri}/physics",
            delta={"tick": event["tick"], "snapshot": event["snapshot"], "collisions": event["collisions"]},
            actor=actor,
        )
        self.stream_projection.publish(projection)
        return event

    def merge_knowledge(
        self,
        *,
        branch_name: str,
        claims: list[dict[str, Any]],
        vote_approved: bool = True,
        profile: str | None = None,
        enforce_profile_gate: bool = False,
    ) -> Dict[str, Any]:
        gate = self.evaluate_claim_gate(profile=profile, claims=claims)
        if enforce_profile_gate and gate["blocked"]:
            blocked_ids = [row["claim_id"] for row in gate["denied_claims"]]
            raise ConsistencyConflict(
                f"knowledge profile gate denied claims for profile={profile}: {', '.join(blocked_ids)}"
            )
        claims_for_merge = gate["accepted_claims"]
        report = self.knowledge_lattice.merge_sandbox(
            branch_name=branch_name,
            claims=claims_for_merge,
            vote_approved=vote_approved,
        )
        report["profile_gate"] = gate
        self.stream_projection.publish(
            self._compile_projection(
                uri=f"{self.scene_graph.world_uri}/knowledge",
                delta={
                    "branch": branch_name,
                    "approved": vote_approved,
                    "report": deepcopy(report),
                },
                actor="xr.knowledge",
            )
        )
        return report

    def apply_demo_example(self, example_name: str, *, actor: str = "xr.demo") -> Dict[str, Any]:
        demo = get_demo_example(example_name)
        node_results = []
        for row in demo.get("nodes", []):
            suffix = str(row.get("suffix", "")).strip()
            if not suffix:
                continue
            node_uri = f"{self.scene_graph.world_uri}/node/{suffix}"
            patch = row.get("patch", {})
            if isinstance(patch, dict) and patch.get("parent", None) == "":
                patch = dict(patch)
                patch.pop("parent", None)
            node_results.append(self.upsert_world_node(node_uri=node_uri, patch=patch, actor=actor))

        knowledge_report = self.merge_knowledge(
            branch_name=f"demo:{example_name}",
            claims=list(demo.get("knowledge_claims", [])),
            vote_approved=True,
            profile=str(demo.get("profile", "")),
            enforce_profile_gate=True,
        )
        render = self.render_scene(viewpoint=demo.get("viewpoint"))
        return {
            "example": example_name,
            "title": demo.get("title"),
            "input_reference": demo.get("input_reference"),
            "profile": demo.get("profile"),
            "distinct_needs": list(demo.get("distinct_needs", [])),
            "seeded_nodes": len(node_results),
            "knowledge_report": knowledge_report,
            "render_stats": render.get("stats", {}),
            "frame_hash": render.get("frame_hash"),
        }

    @staticmethod
    def available_demos() -> list[str]:
        return list_demo_examples()

    def export_qff(
        self,
        *,
        path: str | Path,
        viewpoint: Mapping[str, Any] | None = None,
        profile: str | None = None,
    ) -> Dict[str, Any]:
        render = self.render_scene(viewpoint=viewpoint)
        document = build_qff_document(
            world_uri=self.scene_graph.world_uri,
            scene_nodes=self.scene_graph.nodes_by_uri,
            knowledge_claims=self.knowledge_lattice.claims(),
            render_payload=render,
            profile=profile,
        )
        file_info = export_qff_json(path, document)
        return {
            "export": file_info,
            "world_uri": self.scene_graph.world_uri,
            "profile": str(profile or "default"),
            "state_hash": document["state_hash"],
            "frame_hash": render.get("frame_hash"),
            "node_count": len(self.scene_graph.nodes_by_uri),
            "claim_count": len(self.knowledge_lattice.claims()),
        }

    def propose_scene_direction(
        self,
        *,
        objective: str,
        profile: str = "default",
        max_patches: int = 3,
    ) -> Dict[str, Any]:
        return self.scene_director.propose(
            world_uri=self.scene_graph.world_uri,
            objective=objective,
            profile=profile,
            max_patches=max_patches,
        )

    def import_arkit_frame(self, frame: Mapping[str, Any], *, actor: str = "arkit.import") -> Dict[str, Any]:
        payload = self.arkit_adapter.import_frame(world_uri=self.scene_graph.world_uri, frame=frame)
        node_results = []
        for uri in sorted(payload["node_patches"].keys()):
            node_results.append(self.upsert_world_node(uri, payload["node_patches"][uri], actor=actor))
        render = self.render_scene()
        return {
            "import": payload,
            "nodes_written": len(node_results),
            "frame_hash": render.get("frame_hash"),
            "render_stats": render.get("stats", {}),
        }

    def export_arkit_scene(self) -> Dict[str, Any]:
        return self.arkit_adapter.export_scene(
            world_uri=self.scene_graph.world_uri,
            nodes_by_uri=self.scene_graph.nodes_by_uri,
        )

    @staticmethod
    def evaluate_claim_gate(*, profile: str | None, claims: list[dict[str, Any]]) -> Dict[str, Any]:
        selected_profile = str(profile or "default")
        threshold = PROFILE_CONFIDENCE_THRESHOLDS.get(selected_profile, 0.5)
        accepted: list[dict[str, Any]] = []
        denied: list[dict[str, Any]] = []
        for row in claims:
            confidence = float(row.get("confidence", 0.0))
            normalized = dict(row)
            normalized["confidence"] = confidence
            if confidence >= threshold:
                accepted.append(normalized)
            else:
                normalized["gate_reason"] = f"confidence<{threshold}"
                denied.append(normalized)
        return {
            "profile": selected_profile,
            "threshold": threshold,
            "accepted_claims": accepted,
            "denied_claims": denied,
            "blocked": len(denied) > 0,
        }

    def status(self) -> Dict[str, Any]:
        return {
            "package_coverage": coverage_summary(),
            "runtime": self.dashboard.runtime_view(self),
            "scene_validation": self.scene_graph.validate(),
        }

    def _compile_projection(
        self,
        *,
        uri: str,
        delta: Dict[str, Any],
        actor: str,
        meta: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        projection: Dict[str, Any] = {
            "uri": str(uri),
            "source": "xr_runtime",
            "event_index": self._frame,
            "render_delta": {"global": deepcopy(delta), "objects": []},
            "meta": {"actor": str(actor)},
        }
        if meta:
            projection["meta"].update({str(k): deepcopy(v) for k, v in meta.items() if k != "delta"})
        if isinstance(delta.get("position"), list) and len(delta["position"]) == 3:
            projection["render_delta"]["spatial"] = {"position": [float(v) for v in delta["position"]]}
        return projection
