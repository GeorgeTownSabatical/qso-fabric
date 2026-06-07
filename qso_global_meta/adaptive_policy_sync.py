from __future__ import annotations

from copy import deepcopy
from typing import Dict


class AdaptivePolicySync:
    def __init__(self) -> None:
        self._policies: Dict[str, Dict[str, object]] = {}

    def sync(self, policies):
        for node_id, policy in dict(policies or {}).items():
            if isinstance(policy, dict):
                self._policies[str(node_id)] = deepcopy(policy)
        return deepcopy(self._policies)
