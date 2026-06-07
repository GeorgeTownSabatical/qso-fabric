from __future__ import annotations

from dataclasses import asdict
from typing import List

from tests.federation.stress_harness import StressReport, run_phase


def run_full_battery(seed: int = 1337) -> List[StressReport]:
    reports: List[StressReport] = []

    reports.append(
        run_phase(
            phase="phase_1_100k_baseline",
            total_events=100_000,
            policy_churn_interval=5_000,
            measure_interval=2_500,
            partition_start=40_000,
            partition_duration=10_000,
            entangle_every=0,
            seed=seed,
        )
    )

    reports.append(
        run_phase(
            phase="phase_2_1m_scaling",
            total_events=1_000_000,
            policy_churn_interval=5_000,
            measure_interval=2_500,
            partition_start=400_000,
            partition_duration=100_000,
            entangle_every=0,
            seed=seed,
        )
    )

    reports.append(
        run_phase(
            phase="phase_3_entanglement_cascade",
            total_events=250_000,
            policy_churn_interval=5_000,
            measure_interval=2_500,
            partition_start=100_000,
            partition_duration=25_000,
            entangle_every=100,
            seed=seed,
        )
    )

    reports.append(
        run_phase(
            phase="phase_4_policy_conflict_injection",
            total_events=250_000,
            policy_churn_interval=5_000,
            measure_interval=2_500,
            partition_start=100_000,
            partition_duration=25_000,
            entangle_every=100,
            policy_conflict_at=250_000 // 3,
            seed=seed,
        )
    )

    return reports


if __name__ == "__main__":
    out = run_full_battery()
    print("\\n--- STRESS BATTERY REPORT ---")
    for report in out:
        row = asdict(report)
        print(f"{row['phase']}: events={row['total_events']} duration_s={row['duration_s']} "
              f"peak_mem_mb={round(row['peak_memory_bytes']/1024/1024,2)} reconcile_ms={row['reconcile_ms']} "
              f"policy=v{row['policy_version']} rejected={row['rejected_events']}")
