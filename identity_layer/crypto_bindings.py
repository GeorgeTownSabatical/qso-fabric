from __future__ import annotations

from services.crypto_access.service import CryptoAccessService


class PostQuantumCrypto:
    def __init__(self) -> None:
        self._crypto = CryptoAccessService()

    def sign(self, data: bytes) -> bytes:
        return self._crypto.sign(data.decode("utf-8", errors="ignore")).encode("utf-8")

    def verify(self, data: bytes, signature: bytes) -> bool:
        return self._crypto.verify(data.decode("utf-8", errors="ignore"), signature.decode("utf-8", errors="ignore"))

    def encrypt(self, data: bytes) -> bytes:
        return data

    def decrypt(self, ciphertext: bytes) -> bytes:
        return ciphertext
