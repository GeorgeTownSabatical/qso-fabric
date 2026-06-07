"""Deterministic coherent-recall scoring for fabric patches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.quantum.fabric.fabric import QSOFabric
from services.quantum.fabric.gluing import GluingEngine
from services.quantum.fabric.patch import Patch
from services.quantum.fabric.state import QuantumStateObject

CONTINUITY_ROLE_WEIGHTS = {
    "intent": 1.0,
    "memory": 1.0,
    "task": 0.9,
    "system": 0.9,
    "projection": 0.8,
    "repair": 0.75,
    "contradiction": 0.45,
}


@dataclass(frozen=True, slots=True)
class RecallScoringWeights:
    local_similarity: float = 0.45
    overlap_agreement: float = 0.25
    global_coherence: float = 0.15
    continuity_role: float = 0.10
    obstruction: float = 0.20
    traversal_depth: float = 0.05


def score_coherent_recall(
    fabric: QSOFabric,
    query_state: QuantumStateObject,
    *,
    coherence_threshold: float = 0.8,
    traversal_depths: dict[str, int] | None = None,
    weights: RecallScoringWeights | None = None,
) -> dict[str, Any]:
    """Rank patches by query similarity damped by gluing obstruction."""

    scoring_weights = weights or RecallScoringWeights()
    depths = traversal_depths or {}
    fabric_report = GluingEngine(coherence_threshold=coherence_threshold).analyze(fabric)
    pair_index = _pair_reports_by_patch(fabric_report)
    results = []
    for patch_id, patch in sorted(fabric.patches.items()):
        local_similarity = _local_similarity(query_state, patch)
        overlap_agreement = _average_pair_value(pair_index.get(patch_id, []), "coherence", default=1.0)
        local_obstruction = _sum_pair_value(pair_index.get(patch_id, []), "mismatch")
        role_weight = _continuity_role_weight(patch)
        traversal_depth = max(0, int(depths.get(patch_id, patch.state.metadata.get("traversal_depth", 0))))
        score = (
            scoring_weights.local_similarity * local_similarity
            + scoring_weights.overlap_agreement * overlap_agreement
            + scoring_weights.global_coherence * float(fabric_report["global_coherence"])
            + scoring_weights.continuity_role * role_weight
            - scoring_weights.obstruction * local_obstruction
            - scoring_weights.traversal_depth * traversal_depth
        )
        results.append(
            {
                "patch_id": patch_id,
                "state_id": patch.state.id,
                "domain": patch.domain,
                "score": score,
                "local_similarity": local_similarity,
                "overlap_agreement": overlap_agreement,
                "global_coherence": fabric_report["global_coherence"],
                "obstruction_score": local_obstruction,
                "continuity_role": patch.state.continuity_role,
                "continuity_role_weight": role_weight,
                "retrieval_weight": patch.state.retrieval_weight,
                "traversal_depth": traversal_depth,
                "child_fabric_uri": patch.state.child_fabric_uri,
            }
        )

    results.sort(key=lambda item: (-float(item["score"]), str(item["patch_id"])))
    return {
        "fabric_id": fabric.id,
        "query_state_id": query_state.id,
        "global_coherence": fabric_report["global_coherence"],
        "obstruction_score": fabric_report["obstruction_score"],
        "results": results,
    }


def _pair_reports_by_patch(fabric_report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for pair in fabric_report.get("pairs", []):
        if not isinstance(pair, dict):
            continue
        for patch_key in ("patch_a", "patch_b"):
            patch_id = str(pair.get(patch_key, ""))
            if patch_id:
                out.setdefault(patch_id, []).append(pair)
    return out


def _local_similarity(query_state: QuantumStateObject, patch: Patch) -> float:
    if query_state.dimension != patch.state.dimension:
        return 0.0
    return query_state.fidelity_with(patch.state)


def _average_pair_value(pairs: list[dict[str, Any]], key: str, *, default: float) -> float:
    if not pairs:
        return default
    return _sum_pair_value(pairs, key) / len(pairs)


def _sum_pair_value(pairs: list[dict[str, Any]], key: str) -> float:
    total = 0.0
    for pair in pairs:
        try:
            total += float(pair.get(key, 0.0))
        except (TypeError, ValueError):
            continue
    return total


def _continuity_role_weight(patch: Patch) -> float:
    role = (patch.state.continuity_role or "").strip().lower()
    base = CONTINUITY_ROLE_WEIGHTS.get(role, 0.7)
    return base * patch.state.retrieval_weight
