from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class SandboxPolicy:
    allow_network: bool = False
    allow_file_write: bool = True
    allow_exec: bool = False


def default_sandbox_policy() -> Dict[str, bool]:
    policy = SandboxPolicy()
    return {
        "allow_network": policy.allow_network,
        "allow_file_write": policy.allow_file_write,
        "allow_exec": policy.allow_exec,
    }
