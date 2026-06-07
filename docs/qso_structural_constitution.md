# QSO Fabric v1.0 Structural Constitution

Kernel invariants:
- event immutability (append-only)
- deterministic replay (canonical order)
- policy version pinning
- measurement finality
- signature validation on apply/replay
- DAG enforcement for entanglement links

Meta-layer constraints:
- may propose new policy versions
- may not mutate kernel invariants
- may not bypass signature/policy checks
