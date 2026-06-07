from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from solis.shared.hashing import sha256_hex_obj


@dataclass(slots=True)
class SettlementRecord:
    settlement_id: str
    qcu_consumed: float
    unit_price: float
    provider_id: str
    ts: str
    record_hash: str


class SettlementOracle:
    def settle(self, *, settlement_id: str, qcu_consumed: float, unit_price: float, provider_id: str) -> dict[str, Any]:
        ts = datetime.now(timezone.utc).isoformat()
        gross = float(qcu_consumed) * float(unit_price)
        payload = {
            "settlement_id": settlement_id,
            "qcu_consumed": float(qcu_consumed),
            "unit_price": float(unit_price),
            "gross": gross,
            "provider_id": provider_id,
            "ts": ts,
        }
        payload["record_hash"] = sha256_hex_obj(payload)
        return payload
