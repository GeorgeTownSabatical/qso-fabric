from __future__ import annotations

import hashlib
import os
import platform
from dataclasses import dataclass


@dataclass(slots=True)
class HardwareIdentity:
    """Portable hardware fingerprint helper.

    This is a deterministic software fallback for local development.
    In production, replace with TPM/Secure Enclave attestation.
    """

    seed_env_var: str = "QSO_HARDWARE_IDENTITY_SEED"

    def derive_identity(self) -> str:
        seed = os.getenv(self.seed_env_var, "")
        parts = [
            platform.node(),
            platform.system(),
            platform.machine(),
            platform.processor(),
            seed,
        ]
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
