"""Data acquisition agent that gathers targeted evidence per hypothesis."""

from __future__ import annotations


class DataAcquisitionAgent:
    def __init__(self, graph_query_agent):
        self.graph_query = graph_query_agent

    def gather(self, hypothesis: dict) -> list[dict]:
        htype = hypothesis.get("type", "")
        evidence = []

        if htype == "control_network":
            entity = hypothesis.get("description", "").split("Entity ")[-1].split(" appears")[0]
            assets = self.graph_query.trace_entity_assets(entity)
            if assets:
                evidence.append({"source": "graph_query", "detail": f"{entity} linked to {len(assets)} parcels", "polarity": "support"})
            else:
                evidence.append({"source": "graph_query", "detail": f"No parcel links for {entity}", "polarity": "contradict"})

        elif htype == "ownership_cluster":
            clusters = self.graph_query.shared_address_clusters(threshold=2)
            if clusters:
                evidence.append({"source": "address_cluster", "detail": f"{len(clusters)} shared-address clusters found", "polarity": "support"})
            else:
                evidence.append({"source": "address_cluster", "detail": "No shared-address clusters", "polarity": "neutral"})

        elif htype == "transfer_velocity":
            evidence.append({"source": "reasoning_anomaly", "detail": "Rapid transfer parcel anomaly persisted", "polarity": "support"})

        elif htype == "undisclosed_relationship":
            evidence.append({"source": "link_prediction", "detail": "High-probability missing links exist", "polarity": "support"})
            evidence.append({"source": "external_registry", "detail": "External corroboration pending", "polarity": "neutral"})

        else:
            evidence.append({"source": "default", "detail": "Insufficient targeted evidence", "polarity": "neutral"})

        return evidence
