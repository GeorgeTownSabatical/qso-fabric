"""Hypothesis generation from graph reasoning patterns."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hid(seed: str) -> str:
    return "H-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10]


@dataclass
class Hypothesis:
    hypothesis_id: str
    type: str
    description: str
    confidence: float
    status: str
    supporting_evidence: list[str]
    contradicting_evidence: list[str]
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)


class HypothesisEngine:
    def generate(self, reasoning_summary: dict, anomalies: dict, clusters: list[dict], influence: list[dict]) -> list[Hypothesis]:
        out: list[Hypothesis] = []

        if anomalies.get("rapid_transfer_parcels"):
            parcel_count = len(anomalies.get("rapid_transfer_parcels", []))
            seed = f"rapid-transfer-{parcel_count}"
            out.append(
                Hypothesis(
                    hypothesis_id=_hid(seed),
                    type="transfer_velocity",
                    description=f"Rapid transfer pattern detected across {parcel_count} parcel(s); possible coordinated ownership maneuvering.",
                    confidence=0.45,
                    status="open",
                    supporting_evidence=[],
                    contradicting_evidence=[],
                    created_at=_utc(),
                )
            )

        high_influence = [r for r in influence if r.get("score", 0.0) > 0.2]
        if high_influence:
            top = high_influence[0]
            seed = f"influence-{top['node']}"
            out.append(
                Hypothesis(
                    hypothesis_id=_hid(seed),
                    type="control_network",
                    description=f"Entity {top['node']} appears as influence hub; potential hidden control network.",
                    confidence=0.40,
                    status="open",
                    supporting_evidence=[],
                    contradicting_evidence=[],
                    created_at=_utc(),
                )
            )

        large_clusters = [c for c in clusters if c.get("size", 0) >= 4]
        if large_clusters:
            seed = f"cluster-{len(large_clusters)}"
            out.append(
                Hypothesis(
                    hypothesis_id=_hid(seed),
                    type="ownership_cluster",
                    description=f"Detected {len(large_clusters)} dense cluster(s) that may indicate shared beneficial ownership.",
                    confidence=0.35,
                    status="open",
                    supporting_evidence=[],
                    contradicting_evidence=[],
                    created_at=_utc(),
                )
            )

        if reasoning_summary.get("predicted_links", 0) > 0:
            seed = f"links-{reasoning_summary.get('predicted_links')}"
            out.append(
                Hypothesis(
                    hypothesis_id=_hid(seed),
                    type="undisclosed_relationship",
                    description="High-probability link predictions suggest relationships not yet recorded in source graph.",
                    confidence=0.30,
                    status="open",
                    supporting_evidence=[],
                    contradicting_evidence=[],
                    created_at=_utc(),
                )
            )

        return out
