"""Entity resolution agent."""

from __future__ import annotations

from core.identity_resolution import EntitySnapshot, IdentityResolver, match_probability


class EntityResolutionAgent:
    def __init__(self):
        self.resolver = IdentityResolver()

    def resolve(self, names: list[str]) -> dict[str, str]:
        return self.resolver.resolve_many(names)

    def probabilistic_links(self, snapshots: list[EntitySnapshot], threshold: float = 0.75) -> list[dict]:
        links: list[dict] = []
        for i in range(len(snapshots)):
            for j in range(i + 1, len(snapshots)):
                a = snapshots[i]
                b = snapshots[j]
                score = match_probability(a, b)
                if score >= threshold:
                    links.append(
                        {
                            "entity_a": a.name,
                            "entity_b": b.name,
                            "probability": round(score, 4),
                        }
                    )
        links.sort(key=lambda x: x["probability"], reverse=True)
        return links
