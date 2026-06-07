from __future__ import annotations

from typing import Any, Dict


def propose_policy(runtime: Any, mode: str = "balanced") -> Dict[str, Any]:
    current = runtime.gdml.policy_sync.current()
    version = str(current.get("version", "v1"))
    next_num = int(version[1:]) + 1 if version.startswith("v") and version[1:].isdigit() else 2
    return {**current, "version": f"v{next_num}", "mode": mode}
