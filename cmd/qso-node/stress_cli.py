from __future__ import annotations

import argparse
import pathlib
import sys
from dataclasses import asdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


PROFILES = {
    "10k": dict(total_events=10_000, partition_start=4_000, partition_duration=1_000, entangle_every=0),
    "100k": dict(total_events=100_000, partition_start=40_000, partition_duration=10_000, entangle_every=0),
    "1m": dict(total_events=1_000_000, partition_start=400_000, partition_duration=100_000, entangle_every=0),
    "cascade": dict(total_events=250_000, partition_start=100_000, partition_duration=25_000, entangle_every=100),
    "policy-conflict": dict(
        total_events=250_000,
        partition_start=100_000,
        partition_duration=25_000,
        entangle_every=100,
        policy_conflict_at=250_000 // 3,
    ),
}


def main() -> None:
    from tests.federation.stress_harness import run_phase

    parser = argparse.ArgumentParser(description="QSO federation stress harness")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="10k")
    parser.add_argument("--seed", type=int, default=1337)
    args = parser.parse_args()

    cfg = PROFILES[args.profile]
    report = run_phase(
        phase=f"cli_{args.profile}",
        total_events=cfg["total_events"],
        policy_churn_interval=5_000,
        measure_interval=2_500,
        partition_start=cfg["partition_start"],
        partition_duration=cfg["partition_duration"],
        entangle_every=cfg.get("entangle_every", 0),
        policy_conflict_at=cfg.get("policy_conflict_at"),
        seed=args.seed,
    )

    row = asdict(report)
    print("\\n--- STRESS HARNESS REPORT ---")
    for k in sorted(row):
        print(f"{k}: {row[k]}")


if __name__ == "__main__":
    main()
