from __future__ import annotations

from typing import Any, Dict, List

from qso_xr.determinism import sha256_hex


class LLMSceneDirector:
    """Deterministic proposal engine; never mutates runtime directly."""

    def propose(
        self,
        *,
        world_uri: str,
        objective: str,
        profile: str = "default",
        max_patches: int = 3,
    ) -> Dict[str, Any]:
        normalized_objective = str(objective).strip()
        if not normalized_objective:
            raise ValueError("objective must be non-empty")

        lower = normalized_objective.lower()
        patch_candidates: List[Dict[str, Any]] = []
        claim_candidates: List[Dict[str, Any]] = []

        if "mood" in lower or "lighting" in lower or profile == "cinematic_low_light":
            patch_candidates.append(
                {
                    "node_suffix": "director_light_rig",
                    "patch": {"render_hints": {"exposure": 0.32, "rim_light": 0.14, "fog_density": 0.2}},
                }
            )
            claim_candidates.append(
                {
                    "section": "direction.cinematic",
                    "claim_id": "dir-cinematic-001",
                    "statement": "Director recommends low-key lighting envelope with stable red accents.",
                    "confidence": 0.74,
                }
            )

        if "annotation" in lower or "legend" in lower or "topology" in lower or profile == "analytic_educational":
            patch_candidates.append(
                {
                    "node_suffix": "director_annotation_overlay",
                    "patch": {
                        "overlay": {
                            "legend_locked": True,
                            "label_scale": 1.0,
                            "palette_mode": "semantic_separable",
                        }
                    },
                }
            )
            claim_candidates.append(
                {
                    "section": "direction.analytic",
                    "claim_id": "dir-analytic-001",
                    "statement": "Director recommends fixed-camera annotation-preserving render policy.",
                    "confidence": 0.88,
                }
            )

        if not patch_candidates:
            patch_candidates.append(
                {
                    "node_suffix": "director_composition_anchor",
                    "patch": {"render_hints": {"stability_mode": "balanced", "camera_jitter": 0.0}},
                }
            )
            claim_candidates.append(
                {
                    "section": "direction.general",
                    "claim_id": "dir-general-001",
                    "statement": "Director recommends deterministic framing with no stochastic camera offsets.",
                    "confidence": 0.7,
                }
            )

        patches = patch_candidates[: max(1, int(max_patches))]
        claims = claim_candidates[: max(1, int(max_patches))]
        proposal = {
            "world_uri": str(world_uri),
            "profile": str(profile),
            "objective": normalized_objective,
            "direct_mutation_allowed": False,
            "proposed_node_patches": patches,
            "proposed_claims": claims,
        }
        proposal["proposal_hash"] = sha256_hex(proposal)
        return proposal
