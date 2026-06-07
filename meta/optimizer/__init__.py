from __future__ import annotations

from typing import Any, Dict


def recommend(runtime: Any) -> Dict[str, Any]:
    summary = runtime.gdml.rewards.aggregate()
    return runtime.gdml.optimizer.recommend(summary)
