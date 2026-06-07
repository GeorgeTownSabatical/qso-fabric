from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecoveryPolicy:
    required_devices: int
    time_delay_sec: int


def recovery_allowed(
    *,
    registered_devices: set[str],
    approving_devices: set[str],
    policy: RecoveryPolicy,
    elapsed_sec: int,
) -> bool:
    if policy.required_devices <= 0:
        return False
    if elapsed_sec < policy.time_delay_sec:
        return False

    valid_approvers = approving_devices.intersection(registered_devices)
    return len(valid_approvers) >= policy.required_devices
