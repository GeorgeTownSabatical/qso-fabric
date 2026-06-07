from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


@dataclass
class NodeLearningState:
    node_id: str
    rewards_by_uri: Dict[str, float]


class SelfLearningSync:
    """Aggregates lightweight learning signals across nodes.

    Inputs can be:
      - per-URI reward hints (0..1)
      - per-URI penalty hints (0..1)
      - arbitrary features (ignored unless numeric)

    Output:
      - aggregated rewards_by_uri (mean across nodes)
      - simple policy hint (balanced vs stability) derived from dispersion
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, NodeLearningState] = {}

    def update(self, node_id: str, signals: Mapping[str, Any]) -> NodeLearningState:
        nid = str(node_id)
        state = self._nodes.get(nid) or NodeLearningState(node_id=nid, rewards_by_uri={})

        rewards = signals.get("rewards_by_uri") or {}
        penalties = signals.get("penalties_by_uri") or {}

        if isinstance(rewards, Mapping):
            for uri, r in rewards.items():
                try:
                    state.rewards_by_uri[str(uri)] = float(r)
                except Exception:
                    continue

        if isinstance(penalties, Mapping):
            for uri, p in penalties.items():
                try:
                    # penalty reduces reward deterministically
                    prior = float(state.rewards_by_uri.get(str(uri), 0.0))
                    state.rewards_by_uri[str(uri)] = max(0.0, min(1.0, prior - float(p)))
                except Exception:
                    continue

        self._nodes[nid] = state
        return state

    def snapshot(self) -> Dict[str, Any]:
        return {
            "nodes": {
                nid: {"rewards_by_uri": deepcopy(st.rewards_by_uri)}
                for nid, st in self._nodes.items()
            }
        }

    def aggregate_rewards(self) -> Dict[str, float]:
        sums: Dict[str, float] = {}
        counts: Dict[str, int] = {}

        for st in self._nodes.values():
            for uri, r in st.rewards_by_uri.items():
                sums[uri] = sums.get(uri, 0.0) + float(r)
                counts[uri] = counts.get(uri, 0) + 1

        out: Dict[str, float] = {}
        for uri, total in sums.items():
            out[uri] = round(total / max(1, counts.get(uri, 1)), 6)
        return out

    def policy_hint(self) -> Dict[str, Any]:
        """A tiny heuristic: if rewards are generally low, bias toward stability."""
        agg = self.aggregate_rewards()
        if not agg:
            return {"mode": "balanced", "reason": "no_rewards"}

        mean = sum(agg.values()) / len(agg)
        mode = "stability" if mean < 0.5 else "balanced"
        return {"mode": mode, "reason": "mean_reward", "mean_reward": round(mean, 6)}

    def best_uri(self) -> Optional[str]:
        agg = self.aggregate_rewards()
        if not agg:
            return None
        return max(sorted(agg.keys()), key=lambda u: agg[u])
