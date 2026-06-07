from __future__ import annotations

from typing import Any


class QCCTokenModel:
    def mint_payload(self, *, wallet: str, qcu: float, nonce: str) -> dict[str, Any]:
        return {
            "wallet": wallet,
            "qcu": round(float(qcu), 8),
            "nonce": nonce,
            "token_type": "QCC",
        }

    def burn_payload(self, *, wallet: str, qcu: float, nonce: str) -> dict[str, Any]:
        return {
            "wallet": wallet,
            "qcu": round(float(qcu), 8),
            "nonce": nonce,
            "token_type": "QCC",
            "action": "burn",
        }
