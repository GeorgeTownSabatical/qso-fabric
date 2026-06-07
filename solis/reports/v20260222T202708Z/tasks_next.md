# Solis Next Task List

## P0
1. Enforce fixed-point end-to-end in projector/service boundary.
   - Replace float math in `stellar_projector_v1.py` and service ingress with `Fixed64` wrappers.
   - Acceptance: deterministic replay hashes unchanged across 3 nodes for 1000-event sequence.
2. Expand strict type safety from target-set to all `solis/services` and `solis/agent` modules.
   - Acceptance: `mypy --strict` passes for those directories in CI.
3. Gate telemetry rollups.
   - Aggregate `qso://solis.gate.*` into periodic health objects (`qso://solis.gate.health.*`).
   - Acceptance: per-scope pass/fail rates queryable from QSO.

## P1
4. Real on-chain anchoring transactions for Ethereum/SphereChain adapters.
   - Implement signed tx path in `solis/anchor/eth_anchor.py` and `solis/anchor/spherechain_anchor.py`.
   - Acceptance: integration test with local chain confirms emitted anchor tx hash.
5. Replace conceptual ZK stubs with circuit-backed proofs.
   - Wire circom/snarkjs command path in `solis/zk/generate_proof.py`/`verify_proof.py`.
   - Acceptance: proof generated + verified against canonical collapse formula.
6. Multi-node replay CI matrix hardening.
   - Run replay test across Python versions and two seed datasets.
   - Acceptance: stable state hash + merkle root + anchor payload hash matrix.

## P2
7. Production observability package finalization.
   - Add Prometheus endpoint and OTEL exporter config in hardening modules.
   - Acceptance: sample scrape/traces visible in local compose profile.
8. Policy gates for constellation contagion thresholds.
   - Add configurable deny/allow policy manifests for high-risk transitions.
   - Acceptance: denied transition emits explicit gate decision event.
9. Report automation.
   - Add `make solis-report` to regenerate versioned stats/charts/tasks bundle.
   - Acceptance: command outputs versioned report folder with SVG+PNG charts.
