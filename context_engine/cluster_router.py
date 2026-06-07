from __future__ import annotations

CLUSTERS = (
    "QSO",
    "SOLIS",
    "SYMBOLIC_PHYSICS",
    "PROPERTY_INVESTIGATION",
    "AGENT_ORCHESTRATION",
    "XR_SIMULATION",
    "HYBRID_QUANTUM_OPTICAL",
    "GOVERNANCE_FRAMEWORK",
)


def normalize_cluster_id(cluster_id: str) -> str:
    normalized = cluster_id.strip().upper()
    if normalized not in CLUSTERS:
        raise ValueError(f"Unknown context cluster: {cluster_id}")
    return normalized
