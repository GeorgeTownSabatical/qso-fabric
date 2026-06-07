from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict


def _canonical_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class XRAvatarEngine:
    """Avatar registry with deterministic attestation and signed motion trails."""

    def __init__(self) -> None:
        self._avatars: Dict[str, Dict[str, Any]] = {}

    def register_avatar(self, avatar_id: str, *, biometric_binding: str, skeleton: Dict[str, Any] | None = None) -> Dict[str, Any]:
        key = str(avatar_id).strip()
        if not key:
            raise ValueError("avatar_id must be non-empty")
        biometric_hash = _sha256_text(str(biometric_binding))
        skeleton_payload = deepcopy(skeleton or {})
        attestation = _sha256_text(_canonical_json({"avatar_id": key, "biometric_hash": biometric_hash, "skeleton": skeleton_payload}))
        row = {
            "avatar_id": key,
            "biometric_hash": biometric_hash,
            "attestation": attestation,
            "skeleton": skeleton_payload,
            "motion_log": [],
        }
        self._avatars[key] = row
        return deepcopy(row)

    def apply_motion(self, avatar_id: str, joints: Dict[str, Any], *, actor: str = "xr.motion") -> Dict[str, Any]:
        key = str(avatar_id)
        if key not in self._avatars:
            raise KeyError(key)
        avatar = self._avatars[key]
        motion_payload = deepcopy(joints)
        motion_index = len(avatar["motion_log"])
        signature = _sha256_text(
            _canonical_json(
                {
                    "avatar_id": key,
                    "actor": str(actor),
                    "motion_index": motion_index,
                    "payload": motion_payload,
                    "attestation": avatar["attestation"],
                }
            )
        )
        event = {
            "avatar_id": key,
            "actor": str(actor),
            "motion_index": motion_index,
            "payload": motion_payload,
            "signature": signature,
        }
        avatar["motion_log"].append(event)
        return deepcopy(event)

    def verify_attestation(self, avatar_id: str, attestation: str) -> bool:
        key = str(avatar_id)
        if key not in self._avatars:
            return False
        return self._avatars[key]["attestation"] == str(attestation)

    def read_avatar(self, avatar_id: str) -> Dict[str, Any]:
        key = str(avatar_id)
        if key not in self._avatars:
            raise KeyError(key)
        return deepcopy(self._avatars[key])
