from __future__ import annotations


IMMUTABLE_KERNEL_INVARIANTS = {
    "append_only_events": True,
    "deterministic_replay": True,
    "signature_required": True,
    "policy_version_pinning": True,
    "entanglement_dag": True,
}
