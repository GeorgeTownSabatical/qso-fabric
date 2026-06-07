"""Typed payload structures for pipeline artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class ParcelProfile:
    apn: str
    address: str
    owner_name: str
    land_use: str
    lot_size: str
    year_built: str
    assessed_value: str
    last_sale_date: str
    last_sale_price: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RecorderDocument:
    document_number: str
    date: str
    type: str
    grantor: str
    grantee: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GISProfile:
    apn: str
    lat: float
    lon: float
    neighbors: list[str]
    zoning: str
    tract_map: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
