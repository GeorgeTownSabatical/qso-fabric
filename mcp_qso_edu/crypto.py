from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from nacl.encoding import Base64Encoder
from nacl.signing import SigningKey, VerifyKey


def canonical_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Identity:
    name: str
    signing_key: SigningKey

    @property
    def verify_key(self) -> VerifyKey:
        return self.signing_key.verify_key

    @classmethod
    def from_seed_text(cls, name: str, seed_text: str) -> "Identity":
        seed = hashlib.sha256(seed_text.encode("utf-8")).digest()
        return cls(name=name, signing_key=SigningKey(seed))

    def sign(self, payload: dict[str, Any]) -> dict[str, str]:
        digest = canonical_hash(payload)
        signature = self.signing_key.sign(digest.encode("utf-8")).signature
        return {
            "hash": digest,
            "signature": Base64Encoder.encode(signature).decode("utf-8"),
            "pubkey": Base64Encoder.encode(self.verify_key.encode()).decode("utf-8"),
        }


def verify(payload: dict[str, Any], proof: dict[str, Any]) -> bool:
    expected = canonical_hash(payload)
    if expected != str(proof.get("hash", "")):
        return False
    verify_key = VerifyKey(Base64Encoder.decode(str(proof["pubkey"])))
    verify_key.verify(expected.encode("utf-8"), Base64Encoder.decode(str(proof["signature"])))
    return True
