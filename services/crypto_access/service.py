from __future__ import annotations

import hashlib
import hmac
import os


class CryptoAccessService:
    def __init__(self, secret: str | None = None) -> None:
        if secret is None:
            env = os.getenv("QSO_ENV", "dev").lower()
            env_secret = os.getenv("QSO_FABRIC_SECRET")
            if env_secret:
                secret = env_secret
            elif env in {"dev", "local"}:
                secret = "qso-fabric-dev-secret"
            else:
                raise ValueError("QSO_FABRIC_SECRET is required unless QSO_ENV is dev/local")
        self._secret = secret.encode("utf-8")

    def sign(self, payload: str) -> str:
        return hmac.new(self._secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify(self, payload: str, signature: str) -> bool:
        expected = self.sign(payload)
        return hmac.compare_digest(expected, signature)
