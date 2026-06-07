"""Pluggable OC source clients.

These default to deterministic mock data so the pipeline is runnable without private APIs.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta

from core.apn_parser import normalize_apn


class MockAssessorClient:
    def lookup(self, apn: str) -> dict:
        norm = normalize_apn(apn)["formatted"]
        seed = int(hashlib.sha256(norm.encode()).hexdigest()[:8], 16)
        return {
            "apn": norm,
            "address": f"{100 + (seed % 900)} Mockingbird Ln, Orange County, CA",
            "owner_name": "SMITH FAMILY TRUST" if seed % 2 else "PACIFIC HOLDINGS LLC",
            "land_use": "SFR" if seed % 3 else "CONDO",
            "lot_size": str(4000 + (seed % 7000)),
            "year_built": str(1950 + (seed % 70)),
            "assessed_value": str(400000 + (seed % 1500000)),
            "last_sale_date": str(date(2010, 1, 1) + timedelta(days=seed % 3650)),
            "last_sale_price": str(250000 + (seed % 1000000)),
        }


class MockRecorderClient:
    def fetch_documents(self, apn: str) -> list[dict]:
        norm = normalize_apn(apn)["formatted"]
        base = int(hashlib.sha256((norm + "docs").encode()).hexdigest()[:6], 16)
        docs = []
        for i, instrument in enumerate(["Grant Deed", "Deed of Trust", "Quitclaim Deed"], start=1):
            docs.append(
                {
                    "document_number": f"202{2+i}{base+i:07d}",
                    "date": str(date(2022 + i, max(1, i), min(28, 10 + i))),
                    "type": instrument,
                    "grantor": "SMITH TRUST" if i % 2 else "PACIFIC HOLDINGS LLC",
                    "grantee": "JONES LLC" if i % 2 else "SMITH TRUST",
                }
            )
        return docs


class MockGISClient:
    def get_geometry(self, apn: str) -> dict:
        norm = normalize_apn(apn)["formatted"]
        parts = normalize_apn(apn)
        book, page, parcel = int(parts["book"]), int(parts["page"]), int(parts["parcel"])
        lat = 33.5 + ((book % 400) / 10000)
        lon = -117.9 + ((page % 400) / 10000)
        neighbors = [
            f"{parts['book']}-{parts['page']}-{max(parcel-1,1):02d}",
            f"{parts['book']}-{parts['page']}-{parcel+1:02d}",
        ]
        return {
            "apn": norm,
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "neighbors": neighbors,
            "zoning": "R1",
            "tract_map": f"TRACT-{book}-{page}",
        }
