"""Verification agent that updates hypothesis confidence from evidence."""

from __future__ import annotations

from core.evidence_scoring import score_evidence, update_confidence


class VerificationAgent:
    def verify(self, hypothesis: dict, evidence: list[dict]) -> dict:
        score = score_evidence(evidence)
        new_conf = update_confidence(float(hypothesis.get("confidence", 0.0)), score["score"])

        if new_conf >= 0.8:
            status = "confirmed"
        elif new_conf <= 0.2:
            status = "rejected"
        elif score["support"] == 0 and score["contradict"] == 0:
            status = "needs more data"
        else:
            status = "open"

        out = dict(hypothesis)
        out["confidence"] = new_conf
        out["status"] = status
        out["supporting_evidence"] = [e["detail"] for e in evidence if e.get("polarity") == "support"]
        out["contradicting_evidence"] = [e["detail"] for e in evidence if e.get("polarity") == "contradict"]
        out["evidence_score"] = score
        return out
