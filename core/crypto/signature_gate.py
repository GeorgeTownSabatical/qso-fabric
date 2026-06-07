from __future__ import annotations

from services.crypto_access.service import CryptoAccessService


class SignatureGate:
    def __init__(self, crypto: CryptoAccessService | None = None) -> None:
        self.crypto = crypto or CryptoAccessService()

    def verify(self, payload: str, signature: str) -> bool:
        return self.crypto.verify(payload, signature)
