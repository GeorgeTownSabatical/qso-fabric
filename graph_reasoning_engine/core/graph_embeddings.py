"""Graph embedding generation with Node2Vec optional fallback."""

from __future__ import annotations

import hashlib
import random


def _deterministic_vector(node: str, dimensions: int) -> list[float]:
    seed = int(hashlib.sha256(str(node).encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed)
    return [round(rng.uniform(-1.0, 1.0), 6) for _ in range(dimensions)]


def generate_embeddings(graph, dimensions: int = 64) -> dict[str, list[float]]:
    try:
        from node2vec import Node2Vec
    except Exception:
        return {node: _deterministic_vector(str(node), dimensions) for node in graph.nodes()}

    ug = graph.to_undirected()
    if ug.number_of_nodes() == 0:
        return {}

    model = Node2Vec(ug, dimensions=dimensions, walk_length=20, num_walks=100, workers=1, quiet=True).fit(window=5, min_count=1)
    return {node: list(model.wv[node]) for node in ug.nodes()}
