from __future__ import annotations

import hashlib
import json

from api.schemas.models import SnapshotManifest
from qff.deserializer.service import QFFDeserializer
from qff.serializer.service import QFFSerializer
from services.crypto_access.service import CryptoAccessService


class SnapshotExporterService:
    def __init__(self, crypto: CryptoAccessService) -> None:
        self.crypto = crypto
        self.serializer = QFFSerializer()
        self.deserializer = QFFDeserializer()

    def export_snapshot(
        self,
        uri: str,
        state: dict,
        entanglement: list,
        event_count: int,
        policy_version: str = "v1",
        runtime_version: str = "qso-fabric/0.1.0",
    ) -> bytes:
        event_hash_checkpoint = self._checkpoint_hash(uri, event_count, state)

        manifest = SnapshotManifest(
            uri=uri,
            event_count=event_count,
            policy_version=policy_version,
            runtime_version=runtime_version,
            event_hash_checkpoint=event_hash_checkpoint,
        )
        sign_payload = json.dumps(
            {
                "uri": uri,
                "state": state,
                "entanglement": entanglement,
                "event_hash_checkpoint": event_hash_checkpoint,
            },
            sort_keys=True,
        )
        signature = self.crypto.sign(sign_payload)
        return self.serializer.serialize(
            {
                "header": manifest.model_dump(mode="json"),
                "state": state,
                "entanglement": entanglement,
                "signature": signature,
            }
        )

    def import_snapshot(self, blob: bytes, verify_signature: bool = True) -> dict:
        parsed = self.deserializer.deserialize(blob)
        header = parsed.get("header", {})
        state = parsed.get("state", {})
        entanglement = parsed.get("entanglement", [])
        signature = str(parsed.get("signature", ""))

        if not isinstance(header, dict):
            raise ValueError("invalid snapshot header")

        uri = str(header.get("uri", ""))
        try:
            event_count = int(header.get("event_count", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid snapshot event_count") from exc

        expected_checkpoint = self._checkpoint_hash(uri, event_count, state)
        checkpoint = str(header.get("event_hash_checkpoint", ""))
        if checkpoint != expected_checkpoint:
            raise ValueError("snapshot checkpoint hash mismatch")

        if verify_signature:
            sign_payload = json.dumps(
                {
                    "uri": uri,
                    "state": state,
                    "entanglement": entanglement,
                    "event_hash_checkpoint": checkpoint,
                },
                sort_keys=True,
            )
            if not self.crypto.verify(sign_payload, signature):
                raise ValueError("snapshot signature validation failed")

        return parsed

    @staticmethod
    def _checkpoint_hash(uri: str, event_count: int, state: dict) -> str:
        checkpoint_payload = json.dumps({"uri": uri, "event_count": event_count, "state": state}, sort_keys=True)
        return hashlib.sha256(checkpoint_payload.encode("utf-8")).hexdigest()
