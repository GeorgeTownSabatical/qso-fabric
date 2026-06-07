from __future__ import annotations

from tests.federation.stress_harness import run_phase


def test_deterministic_federation_smoke() -> None:
    report = run_phase(
        phase="pytest_smoke",
        total_events=5_000,
        policy_churn_interval=500,
        measure_interval=250,
        partition_start=2_000,
        partition_duration=500,
        entangle_every=50,
        seed=1337,
    )

    assert report.policy_version > 1
    assert report.rejected_events >= 0
    assert len(report.event_hash_chain) == 64
    assert len(report.snapshot_hash) == 64
