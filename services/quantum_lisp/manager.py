from __future__ import annotations

from math import sqrt
from typing import Any

from services.event_log.service import EventLogService
from services.quantum.backends import QuantumBackend
from services.quantum.fabric import GluingEngine, Overlap, Patch, QSOFabric, QuantumStateObject, ReasoningPath, RestrictionMap, UncertaintyField
from services.quantum.models import QuantumJob
from services.quantum_lisp.compiler import QuantumLispCompiler
from services.state_engine.service import StateEngineService
from solis.shared.hashing import sha256_hex_obj


class QuantumLispReasoningManager:
    def __init__(
        self,
        *,
        state_engine: StateEngineService,
        event_log: EventLogService,
        backends: dict[str, QuantumBackend],
    ) -> None:
        self.state_engine = state_engine
        self.event_log = event_log
        self.backends = backends
        self.compiler = QuantumLispCompiler()

    def compile(self, source: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.compiler.compile(source, metadata=metadata).to_json_dict()

    def analyze(
        self,
        uri: str,
        *,
        actor: str = "quantum-lisp",
        policy_version: str = "v1",
        node_id: str = "local",
    ) -> dict[str, Any]:
        obj = self.state_engine.read(uri)
        payload = dict(obj.state_layer)
        source = str(payload.get("source", ""))
        if not source.strip():
            raise ValueError("quantum_lisp_program requires source")
        compiled = self.compiler.compile(source, metadata=dict(payload.get("metadata", {}))).to_json_dict()
        report = self.evaluate(compiled)
        delta = {
            "object_kind": "reasoning_trace",
            "compiled_ir": compiled,
            "reasoning_report": report,
            "verification_hash": sha256_hex_obj({"uri": uri, "compiled_ir": compiled, "reasoning_report": report}),
        }
        event = self.state_engine.patch(uri=uri, delta=delta, actor=actor, policy_version=policy_version, node_id=node_id)
        return {"event": event.model_dump(mode="json"), "result": report}

    def replay(self, uri: str, *, strict: bool = True) -> dict[str, Any]:
        return {"uri": uri, "state": self.state_engine.rebuild_from_log(uri, strict=strict)}

    def evaluate(self, compiled_ir: dict[str, Any]) -> dict[str, Any]:
        fabric = self._fabric_from_ir(compiled_ir)
        fabric_report = GluingEngine(coherence_threshold=0.8).analyze(fabric)
        backend_reports = self._backend_reports(compiled_ir)
        reasoning_paths = self._reasoning_paths(compiled_ir, fabric_report, backend_reports)
        uncertainty_fields = self._uncertainty_fields(fabric_report, backend_reports)
        repair_proposals = self._repair_proposals(compiled_ir, fabric_report)
        projection_candidates = self._projection_candidates(compiled_ir, backend_reports)
        report = {
            "engine": "qso.quantum_lisp",
            "status": "completed",
            "ir_hash": compiled_ir["ir_hash"],
            "fabric_report": fabric_report,
            "backend_reports": backend_reports,
            "reasoning_paths": [path.to_json_dict() for path in reasoning_paths],
            "uncertainty_fields": [field.to_json_dict() for field in uncertainty_fields],
            "repair_proposals": repair_proposals,
            "projection_candidates": projection_candidates,
        }
        return {**report, "verification_hash": sha256_hex_obj(report)}

    def _fabric_from_ir(self, compiled_ir: dict[str, Any]) -> QSOFabric:
        fabric = QSOFabric(id=f"qlisp.fabric.{compiled_ir['ir_hash'][:12]}", metadata={"ir_hash": compiled_ir["ir_hash"]})
        patch_ids: list[str] = []
        for idx, form in enumerate(compiled_ir["forms"]):
            op = str(form["op"])
            if op not in {"defintent", "observe", "hypothesis", "repair", "project", "trust", "algebra", "reason"}:
                continue
            patch_id = f"patch.{op}.{idx}"
            phase = (idx + 1) / max(1, len(compiled_ir["forms"]))
            vector = (1.0, complex(phase, 1.0 - phase))
            state = QuantumStateObject(
                id=f"state.{op}.{idx}",
                vector=vector,
                phase=phase,
                uncertainty=round(1.0 - min(0.95, 0.55 + phase / 3.0), 8),
                metadata={"form": form},
            )
            fabric.add_patch(Patch(id=patch_id, domain=f"qlisp.{op}", basis=["|assert>", "|context>"], state=state, metadata={"form": form}))
            patch_ids.append(patch_id)
        if len(patch_ids) == 1:
            twin = patch_ids[0] + ".context"
            fabric.add_patch(
                Patch(
                    id=twin,
                    domain="qlisp.context",
                    basis=["|assert>", "|context>"],
                    state=QuantumStateObject(id=twin.replace("patch.", "state."), vector=(1.0, 0.2), metadata={"synthetic_context": True}),
                )
            )
            patch_ids.append(twin)
        for idx, (left, right) in enumerate(zip(patch_ids, patch_ids[1:])):
            fabric.add_overlap(
                Overlap(
                    id=f"overlap.qlisp.{idx}",
                    patch_a=left,
                    patch_b=right,
                    shared_domain=[f"reasoning.step.{idx}"],
                    restriction_a=self._identity_restriction(f"restrict.{idx}.a", left),
                    restriction_b=self._identity_restriction(f"restrict.{idx}.b", right),
                    metadata={"kind": "reasoning_continuity"},
                )
            )
        return fabric

    def _identity_restriction(self, restriction_id: str, source_patch: str) -> RestrictionMap:
        return RestrictionMap(
            id=restriction_id,
            source_patch=source_patch,
            target_patch=restriction_id.replace("restrict.", "overlap."),
            projection=[[1.0, 0.0], [0.0, 1.0]],
        )

    def _backend_reports(self, compiled_ir: dict[str, Any]) -> list[dict[str, Any]]:
        reports = []
        circuit_spec = self._circuit_spec(compiled_ir)
        for backend_name in compiled_ir.get("backend_targets", []):
            if backend_name == "fabric_gluing":
                reports.append({"backend": backend_name, "status": "completed", "role": "local_to_global_gluing"})
                continue
            backend = self.backends.get(backend_name)
            if backend is None:
                reports.append({"backend": backend_name, "status": "unavailable", "reason": "backend_not_registered"})
                continue
            job = QuantumJob(
                uri=f"qso://quantum.state/qlisp_{compiled_ir['ir_hash'][:12]}_{backend_name}",
                backend=backend_name,
                qubit_count=2,
                circuit_spec=circuit_spec,
                measurement_schema={"shots": 128},
                metadata={"ir_hash": compiled_ir["ir_hash"]},
            )
            result = backend.execute(job)
            reports.append(
                {
                    "backend": result.backend,
                    "status": result.status,
                    "measurement_results": result.measurement_results,
                    "noise_profile": result.noise_profile,
                    "execution_proof": result.execution_proof,
                    "verification_hash": result.verification_hash,
                }
            )
        return reports

    def _circuit_spec(self, compiled_ir: dict[str, Any]) -> dict[str, Any]:
        gate_count = max(1, min(6, len(compiled_ir.get("forms", []))))
        gates: list[dict[str, Any]] = [{"name": "h", "target": 0}]
        if gate_count > 1:
            gates.append({"name": "cnot", "control": 0, "target": 1})
        for idx in range(2, gate_count):
            gates.append({"name": "z" if idx % 2 else "x", "target": idx % 2})
        return {"gates": gates, "source": "quantum_lisp_projection"}

    def _reasoning_paths(self, compiled_ir: dict[str, Any], fabric_report: dict[str, Any], backend_reports: list[dict[str, Any]]) -> list[ReasoningPath]:
        backend_penalty = sum(1 for report in backend_reports if report.get("status") != "completed") * 0.05
        confidence = max(0.0, min(1.0, float(fabric_report["global_coherence"]) - backend_penalty))
        path_refs = [f"form.{idx}.{form['op']}" for idx, form in enumerate(compiled_ir["forms"])]
        return [
            ReasoningPath(
                id=f"reasoning.path.{compiled_ir['ir_hash'][:12]}",
                path_refs=path_refs,
                path_type="quantum_lisp_descriptive",
                confidence=round(confidence, 8),
                cost=round(sqrt(max(0.0, float(fabric_report["obstruction_score"]))), 8),
                metadata={"backend_targets": list(compiled_ir.get("backend_targets", []))},
            )
        ]

    def _uncertainty_fields(self, fabric_report: dict[str, Any], backend_reports: list[dict[str, Any]]) -> list[UncertaintyField]:
        backend_entropy = sum(0.1 for report in backend_reports if report.get("status") != "completed")
        uncertainty = max(0.0, min(1.0, 1.0 - float(fabric_report["global_coherence"]) + backend_entropy))
        return [
            UncertaintyField(
                id=f"uncertainty.{fabric_report['fabric_id']}",
                target_ref=str(fabric_report["fabric_id"]),
                uncertainty=round(uncertainty, 8),
                entropy=round(float(fabric_report["obstruction_score"]) + backend_entropy, 8),
                source_refs=[str(report.get("backend")) for report in backend_reports],
                metadata={"model": "fabric_obstruction_plus_backend_availability"},
            )
        ]

    def _repair_proposals(self, compiled_ir: dict[str, Any], fabric_report: dict[str, Any]) -> list[dict[str, Any]]:
        if fabric_report["healthy"]:
            return []
        return [
            {
                "id": f"repair.{compiled_ir['ir_hash'][:12]}.reconcile",
                "operator": "reconcile",
                "reason": "global_coherence_below_threshold",
                "applies": False,
            }
        ]

    def _projection_candidates(self, compiled_ir: dict[str, Any], backend_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "id": f"projection.{compiled_ir['ir_hash'][:12]}.{idx}",
                "backend": report.get("backend"),
                "supported": report.get("status") == "completed",
                "applies": False,
            }
            for idx, report in enumerate(backend_reports)
        ]
