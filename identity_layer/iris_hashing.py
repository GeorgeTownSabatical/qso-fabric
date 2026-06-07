from __future__ import annotations

import hashlib


class IrisHasher:
    def hash_iris(self, image_data: bytes) -> str:
        return hashlib.sha256(image_data).hexdigest()

    def derive_key(self, iris_hash: str) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", iris_hash.encode("utf-8"), b"qso", 1000, dklen=32)
