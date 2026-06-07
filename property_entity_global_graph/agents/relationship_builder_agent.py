"""Build graph nodes/edges from ingested records."""

from __future__ import annotations

from core.entity_normalizer import normalize_address, normalize_company, normalize_name


def _entity_type(name: str) -> str:
    text = normalize_name(name)
    if "TRUST" in text:
        return "Trust"
    if "LLC" in text:
        return "LLC"
    if any(k in text for k in ["INC", "CORP", "CORPORATION", "HOLDINGS"]):
        return "Corporation"
    return "Person"


class RelationshipBuilderAgent:
    def __init__(self, graph_store, event_store):
        self.graph = graph_store
        self.events = event_store

    def ingest_parcels(self, rows: list[dict]) -> None:
        for row in rows:
            apn = row["apn"]
            owner = row["owner_name"]
            addr = normalize_address(row["address"])
            self.graph.upsert_node(apn, "Parcel", apn=apn)
            self.graph.upsert_node(owner, _entity_type(owner), name=normalize_name(owner))
            self.graph.upsert_node(addr, "Address", address=addr)
            self.graph.add_edge(owner, "OWNS", apn, from_ts=row.get("recorded_date"))
            self.graph.add_edge(apn, "REGISTERED_AT", addr)
            self.events.append("parcel_ingested", row)

    def ingest_recorder_docs(self, rows: list[dict]) -> None:
        for row in rows:
            doc = row["document_number"]
            apn = row["apn"]
            grantor = row["grantor"]
            grantee = row["grantee"]
            self.graph.upsert_node(doc, "Document", instrument_type=row.get("instrument_type", ""), date=row.get("recording_date", ""))
            self.graph.upsert_node(apn, "Parcel", apn=apn)
            self.graph.upsert_node(grantor, _entity_type(grantor), name=normalize_name(grantor))
            self.graph.upsert_node(grantee, _entity_type(grantee), name=normalize_name(grantee))
            self.graph.add_edge(grantor, "TRANSFERRED", apn, date=row.get("recording_date"), document=doc)
            self.graph.add_edge(apn, "OWNED_BY", grantee, date=row.get("recording_date"), document=doc)
            self.graph.add_edge(doc, "RECORDED_IN", apn, date=row.get("recording_date"))
            self.events.append("recorder_doc_ingested", row)

    def ingest_corporate_registry(self, rows: list[dict]) -> None:
        for row in rows:
            company = normalize_company(row["company_name"])
            address = normalize_address(row["registered_address"])
            self.graph.upsert_node(company, "Company", name=company, formation_date=row.get("formation_date"))
            self.graph.upsert_node(address, "Address", address=address)
            self.graph.add_edge(company, "REGISTERED_AT", address)
            for director in row.get("directors", []):
                d = normalize_name(director)
                self.graph.upsert_node(d, "Person", name=d)
                self.graph.add_edge(d, "DIRECTOR_OF", company)
            self.events.append("corporate_registry_ingested", row)

    def ingest_sec_filings(self, rows: list[dict]) -> None:
        for row in rows:
            company = normalize_company(row["company"])
            self.graph.upsert_node(company, "SECEntity", name=company)
            for officer in row.get("officers", []):
                off = normalize_name(officer)
                self.graph.upsert_node(off, "Person", name=off)
                self.graph.add_edge(off, "OFFICER_OF", company)
            for sub in row.get("subsidiaries", []):
                sub_name = normalize_company(sub)
                self.graph.upsert_node(sub_name, "Company", name=sub_name)
                self.graph.add_edge(sub_name, "SUBSIDIARY_OF", company)
            self.events.append("sec_filing_ingested", row)

    def ingest_court_records(self, rows: list[dict]) -> None:
        for row in rows:
            case_id = row["case_id"]
            plaintiff = normalize_name(row["plaintiff"])
            defendant = normalize_name(row["defendant"])
            self.graph.upsert_node(case_id, "CourtCase", case_type=row.get("case_type", ""), filed_date=row.get("filed_date", ""))
            self.graph.upsert_node(plaintiff, _entity_type(plaintiff), name=plaintiff)
            self.graph.upsert_node(defendant, _entity_type(defendant), name=defendant)
            self.graph.add_edge(plaintiff, "INVOLVED_IN", case_id, role="plaintiff")
            self.graph.add_edge(defendant, "INVOLVED_IN", case_id, role="defendant")
            self.events.append("court_record_ingested", row)
