"""Predict likely hidden links between nodes."""

from __future__ import annotations

import networkx as nx


def predict_links(graph, top_k: int = 20) -> list[dict]:
    ug = nx.Graph(graph.to_undirected())
    preds = []
    for u, v, score in nx.jaccard_coefficient(ug):
        if score <= 0:
            continue
        preds.append({"source": u, "target": v, "score": float(score)})
    preds.sort(key=lambda x: x["score"], reverse=True)
    return preds[:top_k]
