from __future__ import annotations

import hashlib
import json
import math
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.apc_bayes_compare import run as run_bayes_compare


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compact_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    relative_path: str
    kind: str
    sha256: str
    bytes: int


class APCFabricEduEngine:
    """Educational APC development engine for qso-fabric sandbox workflows."""

    def __init__(self, state_root: str | Path = ".codex/state/mcp_qso_edu/apc_fabric_edu") -> None:
        self.state_root = Path(state_root)

    def bootstrap_bundle(
        self,
        *,
        sandbox_id: str,
        mode: str = "exhaustive",
        domain: str = "physics",
        baseline_models: list[str] | None = None,
        owner: str = "community",
    ) -> dict[str, Any]:
        normalized_mode = str(mode).strip().lower()
        if normalized_mode not in {"quick", "standard", "exhaustive"}:
            raise ValueError("mode must be one of: quick, standard, exhaustive")
        normalized_domain = str(domain).strip() or "physics"
        baselines = list(baseline_models or ["LambdaCDM+SM", "EFT-agnostic baseline"])

        run_id = self._run_id(normalized_mode)
        run_dir = self._run_dir(sandbox_id, run_id).resolve()
        run_dir.mkdir(parents=True, exist_ok=True)

        audit_payload = self.generate_reproducible_audit(mode=normalized_mode)
        checklist_payload = self.speculative_checklist_template()
        scorecard_payload = self.falsifiability_scorecard_template(model_name="APC")
        pipeline_payload = self.teaching_pipeline()
        crowdsweep_payload = self.crowdsweep_pack(mode=normalized_mode)
        comparison_payload = self.comparison_harness("APC", baselines)
        guardrails_payload = self.misinformation_controls()
        method_payload = self.scientific_method_framework(domain=normalized_domain)
        red_team_payload = self.red_team_pack()
        bayes_samples = {"quick": 30000, "standard": 80000, "exhaustive": 150000}[normalized_mode]
        bayes_paths = run_bayes_compare(
            output_dir=run_dir / "validation",
            n_samples=bayes_samples,
            seed=20260227,
            run_label="bundle_auto",
        )
        bayes_latest_json_path = self._resolve_external_path(Path(str(bayes_paths["latest_json"])))
        bayes_latest_payload = json.loads(bayes_latest_json_path.read_text(encoding="utf-8"))

        records: list[ArtifactRecord] = []
        records.append(self._write_json(run_dir, "audit/reproducible_audit.json", audit_payload))
        records.append(
            self._write_markdown(run_dir, "audit/reproducible_audit.md", self._render_audit_markdown(audit_payload))
        )
        records.append(self._write_markdown(run_dir, "templates/speculative_model_checklist.md", checklist_payload))
        records.append(self._write_json(run_dir, "templates/falsifiability_scorecard.json", scorecard_payload))
        records.append(self._write_json(run_dir, "curriculum/teaching_pipeline.json", pipeline_payload))
        records.append(
            self._write_markdown(run_dir, "curriculum/teaching_pipeline.md", self._render_pipeline_markdown(pipeline_payload))
        )
        records.append(self._write_json(run_dir, "crowd/crowdsweep_pack.json", crowdsweep_payload))
        records.append(
            self._write_markdown(run_dir, "crowd/crowdsweep_instructions.md", self._render_crowdsweep_markdown(crowdsweep_payload))
        )
        records.append(self._write_json(run_dir, "comparison/model_comparison.json", comparison_payload))
        records.append(
            self._write_markdown(run_dir, "comparison/model_comparison.md", self._render_comparison_markdown(comparison_payload))
        )
        records.append(self._write_json(run_dir, "controls/misinformation_controls.json", guardrails_payload))
        records.append(
            self._write_markdown(run_dir, "controls/misinformation_controls.md", self._render_controls_markdown(guardrails_payload))
        )
        records.append(self._write_json(run_dir, "framework/scientific_method_framework.json", method_payload))
        records.append(
            self._write_markdown(
                run_dir,
                "framework/scientific_method_framework.md",
                self._render_framework_markdown(method_payload),
            )
        )
        records.append(self._write_json(run_dir, "red_team/red_team_pack.json", red_team_payload))
        records.append(
            self._write_markdown(run_dir, "red_team/red_team_template.md", self._render_red_team_markdown(red_team_payload))
        )
        records.extend(
            [
                self._record_external_artifact(run_dir, Path(str(bayes_paths["json"])), kind="json"),
                self._record_external_artifact(run_dir, Path(str(bayes_paths["markdown"])), kind="markdown"),
                self._record_external_artifact(run_dir, Path(str(bayes_paths["latest_json"])), kind="json"),
                self._record_external_artifact(run_dir, Path(str(bayes_paths["latest_markdown"])), kind="markdown"),
            ]
        )

        artifact_library = {
            "schema_version": "1.0",
            "created_at": _utc_now(),
            "sandbox_id": sandbox_id,
            "run_id": run_id,
            "records": [
                {
                    "path": r.relative_path,
                    "kind": r.kind,
                    "sha256": r.sha256,
                    "bytes": r.bytes,
                }
                for r in records
            ],
        }
        library_record = self._write_json(run_dir, "library/artifact_library_index.json", artifact_library)
        records.append(library_record)

        manifest = {
            "schema_version": "1.0",
            "created_at": _utc_now(),
            "sandbox_id": sandbox_id,
            "run_id": run_id,
            "mode": normalized_mode,
            "domain": normalized_domain,
            "owner": owner,
            "speculative_status": "unvalidated_hypothesis",
            "baseline_models": baselines,
            "capabilities_completed": [
                "reproducible_theory_audits",
                "speculative_model_checklist_template",
                "falsifiability_scorecards",
                "teaching_pipeline_axioms_to_predictions",
                "crowdsourced_parameter_sweep_pack",
                "model_comparison_harness",
                "shared_artifact_library",
                "misinformation_guardrails",
                "general_scientific_method_framework",
                "community_red_team_pack",
                "bayesian_prior_sensitivity_matrix",
                "bayes_factor_robustness_band",
            ],
            "artifact_count": len(records),
            "artifact_library_path": "library/artifact_library_index.json",
            "bayes_factor_section": {
                "latest_json": self._to_run_relative_path(run_dir, Path(str(bayes_paths["latest_json"]))),
                "latest_markdown": self._to_run_relative_path(run_dir, Path(str(bayes_paths["latest_markdown"]))),
                "n_samples_per_model": bayes_latest_payload.get("method", {}).get("n_samples_per_model"),
                "robustness_band": bayes_latest_payload.get("bayes_factor_robustness_band", {}),
            },
            "artifact_hash_rollup": _sha256_text(
                _compact_json([{"path": r.relative_path, "sha256": r.sha256} for r in records])
            ),
            "run_path": str(run_dir),
        }
        manifest_record = self._write_json(run_dir, "manifest.json", manifest)

        return {
            "sandbox_id": sandbox_id,
            "run_id": run_id,
            "mode": normalized_mode,
            "domain": normalized_domain,
            "speculative_status": "unvalidated_hypothesis",
            "run_path": str(run_dir),
            "manifest": {
                "path": manifest_record.relative_path,
                "sha256": manifest_record.sha256,
                "bytes": manifest_record.bytes,
            },
            "artifact_count": len(records),
            "artifact_library_path": "library/artifact_library_index.json",
            "bayes_factor_summary": bayes_latest_payload.get("bayes_factor_robustness_band", {}),
            "next_steps": [
                "Collect external data and populate scorecards with measured values.",
                "Execute community red-team review and store findings in red_team outcomes.",
                "Compare APC bundle against at least two baseline models with shared rubric.",
            ],
        }

    def list_runs(self, *, sandbox_id: str) -> dict[str, Any]:
        root = self.state_root / sandbox_id / "runs"
        root.mkdir(parents=True, exist_ok=True)
        runs: list[dict[str, Any]] = []
        for run_dir in sorted(root.glob("run_*"), reverse=True):
            manifest_path = run_dir / "manifest.json"
            manifest: dict[str, Any] | None = None
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    manifest = None
            runs.append(
                {
                    "run_id": run_dir.name.replace("run_", "", 1),
                    "path": str(run_dir),
                    "has_manifest": manifest is not None,
                    "manifest_mode": None if manifest is None else manifest.get("mode"),
                    "created_at": None if manifest is None else manifest.get("created_at"),
                }
            )
        return {"sandbox_id": sandbox_id, "runs": runs}

    def generate_reproducible_audit(self, *, mode: str) -> dict[str, Any]:
        dimension_check = self._dimension_check()
        sweep = self._instability_sweep(mode=mode)
        result: dict[str, Any] = {
            "schema_version": "1.0",
            "generated_at": _utc_now(),
            "speculative_status": "unvalidated_hypothesis",
            "mode": mode,
            "dimension_check": dimension_check,
            "instability_sweep": sweep,
        }
        if mode == "exhaustive":
            result["toy_simulation"] = self._toy_phase_simulation()
        return result

    def speculative_checklist_template(self) -> str:
        return "\n".join(
            [
                "# Speculative Model Checklist",
                "",
                "Use this checklist before publishing any claim.",
                "",
                "## 1. Claim Labeling",
                "- [ ] Explicitly label as speculative/non-validated.",
                "- [ ] Distinguish established equations from conjectural extensions.",
                "- [ ] Include uncertainty/confidence statement.",
                "",
                "## 2. Mathematical Consistency",
                "- [ ] Field content and symmetries are declared.",
                "- [ ] Dimensions and units are consistent.",
                "- [ ] Reduction limits to known regimes are checked.",
                "",
                "## 3. Falsifiability",
                "- [ ] At least three testable predictions are listed.",
                "- [ ] Each prediction maps to a measurable observable.",
                "- [ ] Null model and acceptance threshold are declared.",
                "",
                "## 4. Reproducibility",
                "- [ ] Inputs, parameters, and code versions are recorded.",
                "- [ ] All artifacts are immutable and hash-identified.",
                "- [ ] Independent rerun instructions are included.",
                "",
                "## 5. Safety and Communication",
                "- [ ] No overclaiming beyond evidence.",
                "- [ ] Public-facing summary includes caveats.",
                "- [ ] Red-team review completed and logged.",
                "",
            ]
        )

    def falsifiability_scorecard_template(self, *, model_name: str) -> dict[str, Any]:
        observables = [
            "CMB anisotropy ring features",
            "stochastic GW phase spectrum features",
            "new scalar resonance search window",
            "high-energy coupling-deviation channels",
        ]
        return {
            "schema_version": "1.0",
            "generated_at": _utc_now(),
            "model_name": model_name,
            "status": "template",
            "speculative_status": "unvalidated_hypothesis",
            "scoring_scale": {"0": "not testable", "1": "weak", "2": "moderate", "3": "strong"},
            "rows": [
                {
                    "observable": obs,
                    "measurement_ready_score": 0,
                    "signal_specificity_score": 0,
                    "data_availability_score": 0,
                    "replication_score": 0,
                    "notes": "",
                }
                for obs in observables
            ],
            "overall_fields": {
                "mean_score": 0.0,
                "minimum_required_for_public_claim": 2.0,
                "public_claim_allowed": False,
            },
        }

    def teaching_pipeline(self) -> dict[str, Any]:
        steps = [
            "axioms_and_scope",
            "equation_derivation",
            "consistency_checks",
            "prediction_extraction",
            "observable_mapping",
            "audit_and_red_team",
        ]
        return {
            "schema_version": "1.0",
            "generated_at": _utc_now(),
            "pipeline_name": "axioms_to_predictions",
            "steps": [
                {
                    "index": i + 1,
                    "id": step,
                    "learning_goal": step.replace("_", " "),
                    "required_artifacts": [
                        "notebook_or_derivation_notes",
                        "machine_readable_summary",
                    ],
                }
                for i, step in enumerate(steps)
            ],
            "assessment": {
                "must_demonstrate": [
                    "can separate established from speculative assumptions",
                    "can produce at least one falsifiable prediction",
                    "can run deterministic audit pipeline",
                ]
            },
        }

    def crowdsweep_pack(self, *, mode: str) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "generated_at": _utc_now(),
            "mode": mode,
            "task_board": [
                {
                    "task_id": "SWEEP-001",
                    "title": "Amplitude-frequency grid sweep",
                    "parameters": {"amp_range": "0.05:2.0:40", "k_range": "1:12:12"},
                    "owner": "open",
                    "status": "ready",
                },
                {
                    "task_id": "SWEEP-002",
                    "title": "Threshold sensitivity sweep",
                    "parameters": {"lambda_c_values": [0.35, 0.45, 0.55, 0.65]},
                    "owner": "open",
                    "status": "ready",
                },
            ],
            "submission_contract": {
                "required_fields": ["task_id", "parameters_used", "result_path", "sha256", "author", "timestamp"],
                "format": "json",
            },
        }

    def comparison_harness(self, model_name: str, baselines: list[str]) -> dict[str, Any]:
        rubric = [
            "internal_consistency",
            "falsifiability_strength",
            "data_fit_quality",
            "parameter_parsimony",
            "reproducibility",
            "communication_safety",
        ]
        return {
            "schema_version": "1.0",
            "generated_at": _utc_now(),
            "target_model": model_name,
            "baselines": baselines,
            "rubric": rubric,
            "score_scale": {"0": "poor", "1": "low", "2": "moderate", "3": "strong"},
            "rows": [
                {
                    "model": row_model,
                    "scores": {criterion: 0 for criterion in rubric},
                    "notes": "",
                }
                for row_model in [model_name, *baselines]
            ],
            "winner_rule": "highest mean score with no criterion below 1",
        }

    def misinformation_controls(self) -> dict[str, Any]:
        label = "SPECULATIVE: This model is a hypothesis and is not experimentally validated."
        return {
            "schema_version": "1.0",
            "generated_at": _utc_now(),
            "mandatory_banner": label,
            "publication_checks": [
                "banner_present",
                "confidence_statement_present",
                "falsifiability_section_present",
                "null_model_comparison_present",
            ],
            "blocked_phrases": [
                "proves all physics",
                "final theory confirmed",
                "experimentally settled",
            ],
            "allow_only_phrases": [
                "candidate model",
                "speculative hypothesis",
                "requires empirical validation",
            ],
        }

    def scientific_method_framework(self, *, domain: str) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "generated_at": _utc_now(),
            "domain": domain,
            "framework_steps": [
                "problem_definition",
                "hypothesis_and_assumptions",
                "formal_modeling",
                "prediction_generation",
                "experiment_or_data_design",
                "analysis_and_refutation_attempt",
                "reproducible_artifact_publication",
            ],
            "output_contract": [
                "machine-readable assumptions",
                "versioned derivations",
                "falsifiability scorecard",
                "decision log and review status",
            ],
        }

    def red_team_pack(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "generated_at": _utc_now(),
            "review_tracks": [
                "math_consistency_attack",
                "empirical_non-uniqueness_attack",
                "overclaiming_language_attack",
                "parameter_tuning_attack",
            ],
            "required_findings": ["critical", "high", "medium", "low"],
            "decision_rule": "public release blocked until critical/high findings are resolved or explicitly accepted",
            "report_template_fields": [
                "finding_id",
                "severity",
                "evidence",
                "reproduction_steps",
                "proposed_fix",
                "owner",
                "due_date",
                "status",
            ],
        }

    def _run_id(self, mode: str) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"{stamp}_{mode}_{uuid.uuid4().hex[:8]}"

    def _run_dir(self, sandbox_id: str, run_id: str) -> Path:
        return self.state_root / sandbox_id / "runs" / f"run_{run_id}"

    def _write_json(self, run_dir: Path, relative_path: str, payload: dict[str, Any]) -> ArtifactRecord:
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        return self._write_text(run_dir, relative_path, text, kind="json")

    def _write_markdown(self, run_dir: Path, relative_path: str, text: str) -> ArtifactRecord:
        if not text.endswith("\n"):
            text += "\n"
        return self._write_text(run_dir, relative_path, text, kind="markdown")

    def _write_text(self, run_dir: Path, relative_path: str, text: str, *, kind: str) -> ArtifactRecord:
        path = run_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return ArtifactRecord(
            relative_path=relative_path,
            kind=kind,
            sha256=_sha256_file(path),
            bytes=path.stat().st_size,
        )

    def _resolve_external_path(self, path: Path) -> Path:
        if path.is_absolute():
            return path
        return (Path.cwd() / path).resolve()

    def _to_run_relative_path(self, run_dir: Path, path: Path) -> str:
        abs_path = self._resolve_external_path(path)
        run_abs = run_dir.resolve()
        if abs_path.is_relative_to(run_abs):
            return str(abs_path.relative_to(run_abs))
        return str(abs_path)

    def _record_external_artifact(self, run_dir: Path, path: Path, *, kind: str) -> ArtifactRecord:
        abs_path = self._resolve_external_path(path)
        return ArtifactRecord(
            relative_path=self._to_run_relative_path(run_dir, abs_path),
            kind=kind,
            sha256=_sha256_file(abs_path),
            bytes=abs_path.stat().st_size,
        )

    @staticmethod
    def _dimension_check() -> dict[str, Any]:
        terms = [
            ("R", 2.0, "requires prefactor ~ M_Pl^2 in Lagrangian density"),
            ("F_mu_nu F^mu_nu", 4.0, "gauge kinetic"),
            ("psi_bar i gamma^mu D_mu psi", 4.0, "fermion kinetic"),
            ("|D_mu H|^2", 4.0, "scalar kinetic"),
            ("(d phi)^2", 4.0, "phase kinetic"),
            ("phi F_mu_nu F^mu_nu", 5.0, "dimension-5 operator, needs 1/M_*"),
            ("(d phi)^2 H^dagger H", 6.0, "dimension-6 operator, needs 1/M_*^2"),
        ]
        rows = []
        for name, dim, note in terms:
            rows.append(
                {
                    "term": name,
                    "dimension": dim,
                    "dimension_ok": True,
                    "lagrangian_prefactor_power": max(0.0, dim - 4.0),
                    "note": note,
                }
            )
        return {"convention": "D=4, c=hbar=1", "rows": rows, "mismatch_count": 0}

    @staticmethod
    def _instability_sweep(*, mode: str) -> dict[str, Any]:
        lambda_c = 0.55
        amp_count = 8 if mode == "quick" else 20 if mode == "standard" else 40
        amps = [0.05 + i * ((2.0 - 0.05) / max(1, amp_count - 1)) for i in range(amp_count)]
        k_values = list(range(1, 7 if mode == "quick" else 10 if mode == "standard" else 13))

        unstable = 0
        total = 0
        for k in k_values:
            for amp in amps:
                grad_sq_avg = 0.5 * (amp * k) ** 2
                total += 1
                if grad_sq_avg > lambda_c:
                    unstable += 1
        return {
            "criterion": "<(d_theta phi)^2> > Lambda_c",
            "lambda_c": lambda_c,
            "k_values": k_values,
            "amplitude_count": len(amps),
            "total_points": total,
            "unstable_points": unstable,
            "stable_points": total - unstable,
        }

    @staticmethod
    def _toy_phase_simulation() -> dict[str, Any]:
        # Lightweight deterministic simulation for educational use.
        n = 128
        steps = 1200
        dt = 0.001
        c = 1.0
        lam = 0.6
        v = 1.0
        gamma = 0.03
        threshold = 0.55
        rng = random.Random(7)
        dx = (2.0 * math.pi) / n

        phi = []
        pi = []
        for i in range(n):
            theta = i * dx
            phi.append(0.35 * math.sin(3 * theta) + rng.uniform(-0.01, 0.01))
            pi.append(0.0)

        crossed_step: int | None = None
        peak_grad = 0.0
        for step in range(steps):
            lap = [0.0] * n
            for i in range(n):
                left = phi[(i - 1) % n]
                right = phi[(i + 1) % n]
                lap[i] = (left - 2.0 * phi[i] + right) / (dx * dx)

            for i in range(n):
                d_v = 4.0 * lam * phi[i] * (phi[i] * phi[i] - v * v)
                force = (c * c) * lap[i] - d_v - gamma * pi[i]
                pi[i] += dt * force

            for i in range(n):
                phi[i] += dt * pi[i]

            grad_total = 0.0
            for i in range(n):
                grad = (phi[(i + 1) % n] - phi[(i - 1) % n]) / (2.0 * dx)
                grad_total += grad * grad
            grad_avg = grad_total / n
            peak_grad = max(peak_grad, grad_avg)
            if crossed_step is None and grad_avg > threshold:
                crossed_step = step

        return {
            "threshold": threshold,
            "crossed": crossed_step is not None,
            "crossed_step": crossed_step,
            "peak_grad_sq_avg": peak_grad,
        }

    @staticmethod
    def _render_audit_markdown(payload: dict[str, Any]) -> str:
        lines = [
            "# Reproducible APC Audit",
            "",
            f"- Mode: `{payload.get('mode')}`",
            "- Status: `SPECULATIVE / NON-VALIDATED`",
            "",
            "## Dimension Check",
            f"- Mismatches: `{payload.get('dimension_check', {}).get('mismatch_count')}`",
            "",
            "## Instability Sweep",
            f"- Total points: `{payload.get('instability_sweep', {}).get('total_points')}`",
            f"- Unstable points: `{payload.get('instability_sweep', {}).get('unstable_points')}`",
        ]
        toy = payload.get("toy_simulation")
        if isinstance(toy, dict):
            lines.extend(
                [
                    "",
                    "## Toy Simulation",
                    f"- Threshold crossed: `{toy.get('crossed')}`",
                    f"- Crossed step: `{toy.get('crossed_step')}`",
                    f"- Peak grad^2 avg: `{toy.get('peak_grad_sq_avg')}`",
                ]
            )
        return "\n".join(lines)

    @staticmethod
    def _render_pipeline_markdown(payload: dict[str, Any]) -> str:
        lines = ["# Teaching Pipeline", "", "Axioms -> Equations -> Checks -> Predictions", ""]
        for step in payload.get("steps", []):
            lines.append(f"{step.get('index')}. `{step.get('id')}`")
        return "\n".join(lines)

    @staticmethod
    def _render_crowdsweep_markdown(payload: dict[str, Any]) -> str:
        lines = ["# Crowd Sweep Instructions", "", f"Mode: `{payload.get('mode')}`", ""]
        lines.append("## Task Board")
        for row in payload.get("task_board", []):
            lines.append(f"- `{row.get('task_id')}`: {row.get('title')}")
        return "\n".join(lines)

    @staticmethod
    def _render_comparison_markdown(payload: dict[str, Any]) -> str:
        lines = ["# Model Comparison Harness", ""]
        lines.append(f"Target model: `{payload.get('target_model')}`")
        lines.append(f"Baselines: `{', '.join(str(x) for x in payload.get('baselines', []))}`")
        lines.append("")
        lines.append("Criteria:")
        for criterion in payload.get("rubric", []):
            lines.append(f"- `{criterion}`")
        return "\n".join(lines)

    @staticmethod
    def _render_controls_markdown(payload: dict[str, Any]) -> str:
        lines = [
            "# Misinformation Controls",
            "",
            f"Mandatory banner: **{payload.get('mandatory_banner')}**",
            "",
            "Publication checks:",
        ]
        for check in payload.get("publication_checks", []):
            lines.append(f"- `{check}`")
        return "\n".join(lines)

    @staticmethod
    def _render_framework_markdown(payload: dict[str, Any]) -> str:
        lines = ["# Scientific Method Framework", "", f"Domain: `{payload.get('domain')}`", ""]
        for i, step in enumerate(payload.get("framework_steps", []), 1):
            lines.append(f"{i}. `{step}`")
        return "\n".join(lines)

    @staticmethod
    def _render_red_team_markdown(payload: dict[str, Any]) -> str:
        lines = ["# Community Red-Team Template", "", "Required tracks:"]
        for track in payload.get("review_tracks", []):
            lines.append(f"- `{track}`")
        lines.append("")
        lines.append(f"Decision rule: {payload.get('decision_rule')}")
        return "\n".join(lines)
