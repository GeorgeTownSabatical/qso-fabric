from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple


@dataclass(frozen=True)
class OptimizationHint:
    uri: str
    patch: Dict[str, Any]
    reason: str
    score: float


class DistributedOptimizer:
    """Turns aggregated reward signals into deterministic patch recommendations.

    This is intentionally conservative:
      - never deletes keys
      - only proposes additive / boolean / scalar nudges
    """

    def recommend(
        self,
        rewards_by_uri: Mapping[str, float],
        *,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        hints: List[OptimizationHint] = []
        for uri, reward in rewards_by_uri.items():
            try:
                r = float(reward)
            except Exception:
                continue

            # Very simple rule set; safe, deterministic suggestions.
            if r < 0.35:
                hints.append(
                    OptimizationHint(
                        uri=str(uri),
                        patch={"stabilize": True, "tuning": {"mode": "stability"}},
                        reason="low_reward_stabilize",
                        score=1.0 - r,
                    )
                )
            elif r > 0.75:
                hints.append(
                    OptimizationHint(
                        uri=str(uri),
                        patch={"tuning": {"mode": "balanced"}, "optimize": True},
                        reason="high_reward_optimize",
                        score=r,
                    )
                )
            else:
                hints.append(
                    OptimizationHint(
                        uri=str(uri),
                        patch={"tuning": {"mode": "balanced"}},
                        reason="mid_reward_hold",
                        score=0.5,
                    )
                )

        hints.sort(key=lambda h: (-h.score, h.uri, h.reason))
        return [
            {"uri": h.uri, "patch": dict(h.patch), "reason": h.reason, "score": round(h.score, 6)}
            for h in hints[:top_k]
        ]

    def best_target(self, rewards_by_uri: Mapping[str, float]) -> Optional[Tuple[str, float]]:
        items = []
        for uri, r in rewards_by_uri.items():
            try:
                items.append((str(uri), float(r)))
            except Exception:
                continue
        if not items:
            return None
        items.sort(key=lambda t: (-t[1], t[0]))
        return items[0]
