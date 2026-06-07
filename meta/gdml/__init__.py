from __future__ import annotations

from typing import Any, Dict


def summarize_global_policy(runtime: Any) -> Dict[str, Any]:
    return runtime.gdml.policy_sync.current()
