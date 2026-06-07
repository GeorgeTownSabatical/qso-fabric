"""Evidence scoring for hypothesis verification."""

from __future__ import annotations


def score_evidence(evidence_items: list[dict]) -> dict:
    if not evidence_items:
        return {"score": 0.0, "support": 0, "contradict": 0, "neutral": 0}

    support = sum(1 for e in evidence_items if e.get("polarity") == "support")
    contradict = sum(1 for e in evidence_items if e.get("polarity") == "contradict")
    neutral = sum(1 for e in evidence_items if e.get("polarity") not in {"support", "contradict"})

    raw = support - contradict
    score = raw / max(len(evidence_items), 1)
    return {
        "score": score,
        "support": support,
        "contradict": contradict,
        "neutral": neutral,
    }


def update_confidence(base_confidence: float, evidence_score: float) -> float:
    updated = base_confidence + (0.35 * evidence_score)
    return max(0.0, min(1.0, round(updated, 4)))
