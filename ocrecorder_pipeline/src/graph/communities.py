"""Community detection and report shaping."""

from __future__ import annotations

from collections import Counter

import networkx as nx
import pandas as pd

from normalize.names import extract_surname


def detect_communities(graph: nx.Graph) -> list[set[str]]:
    if graph.number_of_nodes() == 0:
        return []
    return [set(c) for c in nx.algorithms.community.greedy_modularity_communities(graph)]


def summarize_communities(graph: nx.Graph, df: pd.DataFrame) -> pd.DataFrame:
    communities = detect_communities(graph)
    if not communities:
        return pd.DataFrame(columns=["community_id", "node_count", "parcel_count", "party_count", "top_surnames", "top_notaries", "top_entities"])

    all_surnames = [extract_surname(x) for x in pd.concat([df["grantor"], df["grantee"]], ignore_index=True).astype(str)]
    top_surnames_global = [s for s, _ in Counter([s for s in all_surnames if s]).most_common(5)]
    top_notaries_global = [n for n, _ in Counter(df["notary"].astype(str)).most_common(5)]

    rows: list[dict] = []
    for idx, community in enumerate(communities, start=1):
        parcel_count = sum(1 for n in community if n.startswith("apn:"))
        party_count = sum(1 for n in community if n.startswith("party:"))
        entity_nodes = [n for n in community if n.startswith("party:") and any(k in n for k in ["TRUST", "LLC", "BANK", "INC", "LP", "LLP"])]

        rows.append(
            {
                "community_id": idx,
                "node_count": len(community),
                "parcel_count": parcel_count,
                "party_count": party_count,
                "top_surnames": "|".join(top_surnames_global),
                "top_notaries": "|".join(top_notaries_global),
                "top_entities": "|".join(entity_nodes[:10]),
            }
        )

    return pd.DataFrame(rows).sort_values(["parcel_count", "node_count"], ascending=False)
