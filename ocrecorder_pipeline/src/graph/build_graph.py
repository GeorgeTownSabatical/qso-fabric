"""Graph construction for title-chain and community analysis."""

from __future__ import annotations

import networkx as nx
import pandas as pd


def build_title_multidigraph(df: pd.DataFrame) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    for row in df.itertuples(index=False):
        doc = f"doc:{row.doc_number}"
        apn = f"apn:{row.apn}"
        grantor = f"party:{row.grantor}"
        grantee = f"party:{row.grantee}"

        g.add_node(doc, kind="document", doc_type=row.doc_type, date=str(row.record_date))
        g.add_node(apn, kind="parcel")
        g.add_node(grantor, kind="party")
        g.add_node(grantee, kind="party")

        g.add_edge(grantor, doc, kind="grantor_of")
        g.add_edge(doc, grantee, kind="grantee_of")
        g.add_edge(doc, apn, kind="affects_parcel")
    return g


def build_projection_graph(df: pd.DataFrame) -> nx.Graph:
    ug = nx.Graph()
    for row in df.itertuples(index=False):
        ug.add_edge(f"party:{row.grantor}", f"apn:{row.apn}")
        ug.add_edge(f"party:{row.grantee}", f"apn:{row.apn}")
        if getattr(row, "notary", None):
            ug.add_edge(f"notary:{row.notary}", f"apn:{row.apn}")
    return ug
