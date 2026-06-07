from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import tarfile
from copy import deepcopy
from typing import Any, Dict, Iterable, List

from api.schemas.models import QSOEvent
from core.identity.events import parse_identity_event_type
from core.identity.model import IdentityKernelEvent, IdentityLifecycleStatus
from core.identity.reducer import reduce_identity_timeline
from core.identity.uri import validate_identity_person_uri
from services.crypto_access.service import CryptoAccessService
from services.event_log.service import EventLogService
from services.event_log.signing import qso_event_payload
from services.snapshot_exporter.service import SnapshotExporterService
from services.state_engine.service import StateEngineService


class IdentityVerifierService:
    def __init__(
        self,
        state_engine: StateEngineService,
        event_log: EventLogService,
        snapshot_exporter: SnapshotExporterService,
        crypto: CryptoAccessService,
    ) -> None:
        self.state_engine = state_engine
        self.event_log = event_log
        self.snapshot_exporter = snapshot_exporter
        self.crypto = crypto

    def export_bundle(
        self,
        uri: str,
        trust_roots: List[str] | None = None,
        strict: bool = True,
    ) -> Dict[str, Any]:
        validate_identity_person_uri(uri)
        obj = self.state_engine.read(uri)
        timeline = [event.model_dump(mode="json") for event in self.event_log.replay(uri, strict=strict)]
        identity_runtime = self.state_engine.rebuild_identity_state(uri, strict=strict)
        policy_version = str(identity_runtime.get("policy_version_pointer", "v1"))

        snapshot_qff = self.snapshot_exporter.export_snapshot(
            uri=uri,
            state=obj.state_layer,
            entanglement=[link.model_dump(mode="json") for link in self.state_engine.registry.read(uri).entanglement_layer],
            event_count=len(self.event_log.timeline(uri)),
            policy_version=policy_version,
        )
        snapshot_hash = hashlib.sha256(snapshot_qff).hexdigest()
        block_manifest = self._block_manifest(snapshot_qff)
        credential_manifest = self._credential_manifest(identity_runtime)
        declared_state_hash = str(identity_runtime.get("state_hash", ""))

        bundle = {
            "identity_uri": uri,
            "policy_version": policy_version,
            "declared_state_hash": declared_state_hash,
            "snapshot_hash": snapshot_hash,
            "identity_snapshot_qff_b64": base64.b64encode(snapshot_qff).decode("ascii"),
            "block_manifest": block_manifest,
            "credential_manifest": credential_manifest,
            "trust_roots": list(trust_roots or []),
            "timeline": timeline,
        }
        return self.sign_bundle(bundle)

    def sign_bundle(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        sealed = deepcopy(bundle)
        sealed["transfer_sig"] = self.crypto.sign(self._bundle_signing_payload(sealed))
        return sealed

    def verify_bundle(
        self,
        bundle: Dict[str, Any],
        strict_archival: bool = True,
        reject_archived: bool = True,
    ) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = []
        try:
            uri = str(bundle.get("identity_uri", ""))
            validate_identity_person_uri(uri)
        except Exception as exc:
            return self._fail("bundle.identity_uri", str(exc), steps)

        try:
            snapshot_qff = self._snapshot_bytes(bundle)
            actual_block_manifest = self._block_manifest(snapshot_qff)
            expected_block_manifest = bundle.get("block_manifest")
            if not isinstance(expected_block_manifest, dict):
                raise ValueError("bundle.block_manifest missing or invalid")
            if actual_block_manifest != expected_block_manifest:
                raise ValueError("block hash manifest mismatch")
            steps.append({"step": "validate_block_hashes", "ok": True})
        except Exception as exc:
            return self._fail("validate_block_hashes", str(exc), steps)

        try:
            transfer_sig = str(bundle.get("transfer_sig", ""))
            if not transfer_sig:
                raise ValueError("bundle.transfer_sig missing")
            if not self.crypto.verify(self._bundle_signing_payload(bundle), transfer_sig):
                raise ValueError("bundle transfer signature validation failed")

            parsed_snapshot = self.snapshot_exporter.import_snapshot(snapshot_qff, verify_signature=True)
            timeline_events = self._timeline_events(bundle.get("timeline"))
            for event in timeline_events:
                if not self.crypto.verify(qso_event_payload(event), event.signature):
                    raise ValueError(f"event signature validation failed for {event.event_id}")
            steps.append({"step": "validate_signatures", "ok": True})
        except Exception as exc:
            return self._fail("validate_signatures", str(exc), steps)

        try:
            bundle_policy_version = str(bundle.get("policy_version", ""))
            if not bundle_policy_version:
                raise ValueError("bundle.policy_version missing")

            header = parsed_snapshot.get("header", {})
            snapshot_policy_version = str(header.get("policy_version", ""))
            if snapshot_policy_version != bundle_policy_version:
                raise ValueError(
                    f"policy version mismatch: snapshot={snapshot_policy_version}, bundle={bundle_policy_version}"
                )

            for event in timeline_events:
                if event.policy_version != bundle_policy_version:
                    raise ValueError(
                        f"timeline event policy mismatch: {event.event_id}={event.policy_version}, expected={bundle_policy_version}"
                    )
            steps.append({"step": "validate_policy_version", "ok": True, "policy_version": bundle_policy_version})
        except Exception as exc:
            return self._fail("validate_policy_version", str(exc), steps)

        try:
            identity_events = self._identity_kernel_events_from_timeline(timeline_events)
            replayed = reduce_identity_timeline(uri, identity_events, policy_version=bundle_policy_version)
            lifecycle = str(replayed.get("revocation_state", {}).get("status", IdentityLifecycleStatus.ACTIVE.value))
            if lifecycle not in {
                IdentityLifecycleStatus.ACTIVE.value,
                IdentityLifecycleStatus.FROZEN.value,
                IdentityLifecycleStatus.ARCHIVED.value,
            }:
                raise ValueError(f"invalid revocation lifecycle status: {lifecycle}")
            if reject_archived and lifecycle == IdentityLifecycleStatus.ARCHIVED.value:
                raise ValueError("identity archived and rejected by verifier policy")
            steps.append({"step": "validate_revocation_status", "ok": True, "status": lifecycle})
        except Exception as exc:
            return self._fail("validate_revocation_status", str(exc), steps)

        try:
            deterministic_a = reduce_identity_timeline(uri, identity_events, policy_version=bundle_policy_version)
            deterministic_b = reduce_identity_timeline(uri, identity_events, policy_version=bundle_policy_version)
            if deterministic_a != deterministic_b:
                raise ValueError("deterministic replay divergence")
            steps.append({"step": "deterministic_replay", "ok": True})
        except Exception as exc:
            return self._fail("deterministic_replay", str(exc), steps)

        try:
            declared_state_hash = str(bundle.get("declared_state_hash", ""))
            if not declared_state_hash:
                raise ValueError("bundle.declared_state_hash missing")

            snapshot_state = parsed_snapshot.get("state", {})
            snapshot_identity = snapshot_state.get("identity_runtime", {})
            snapshot_state_hash = str(snapshot_identity.get("state_hash", ""))
            if snapshot_state_hash != declared_state_hash:
                raise ValueError(
                    f"declared hash mismatch with snapshot state: declared={declared_state_hash}, snapshot={snapshot_state_hash}"
                )

            computed_state_hash = str(deterministic_a.get("state_hash", ""))
            if computed_state_hash != declared_state_hash:
                raise ValueError(
                    f"computed hash mismatch: declared={declared_state_hash}, computed={computed_state_hash}"
                )
            steps.append(
                {
                    "step": "compare_state_hash",
                    "ok": True,
                    "declared_state_hash": declared_state_hash,
                    "computed_state_hash": computed_state_hash,
                }
            )
        except Exception as exc:
            return self._fail("compare_state_hash", str(exc), steps)

        result = {
            "accepted": True,
            "reason": "verification_passed",
            "identity_uri": uri,
            "policy_version": bundle_policy_version,
            "strict_archival": strict_archival,
            "steps": steps,
        }
        return result

    def verify_bundle_or_raise(
        self,
        bundle: Dict[str, Any],
        strict_archival: bool = True,
        reject_archived: bool = True,
    ) -> Dict[str, Any]:
        result = self.verify_bundle(bundle, strict_archival=strict_archival, reject_archived=reject_archived)
        if result.get("accepted"):
            return result
        raise ValueError(str(result.get("reason", "verification_failed")))

    def _bundle_signing_payload(self, bundle: Dict[str, Any]) -> str:
        payload = {
            "identity_uri": bundle.get("identity_uri"),
            "policy_version": bundle.get("policy_version"),
            "declared_state_hash": bundle.get("declared_state_hash"),
            "snapshot_hash": bundle.get("snapshot_hash"),
            "block_manifest": bundle.get("block_manifest"),
            "credential_manifest": bundle.get("credential_manifest"),
            "trust_roots": bundle.get("trust_roots", []),
            "timeline": bundle.get("timeline", []),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _credential_manifest(identity_state: Dict[str, Any]) -> Dict[str, str]:
        credentials = identity_state.get("credential_refs", {})
        if not isinstance(credentials, dict):
            return {}
        rows: Dict[str, str] = {}
        for credential_id, record in credentials.items():
            if not isinstance(record, dict):
                continue
            rows[str(credential_id)] = str(record.get("status", "unknown"))
        return rows

    @staticmethod
    def _snapshot_bytes(bundle: Dict[str, Any]) -> bytes:
        direct = bundle.get("identity_snapshot_qff")
        if isinstance(direct, (bytes, bytearray)):
            return bytes(direct)

        encoded = bundle.get("identity_snapshot_qff_b64")
        if isinstance(encoded, str) and encoded:
            try:
                return base64.b64decode(encoded.encode("ascii"))
            except Exception as exc:
                raise ValueError("invalid identity_snapshot_qff_b64 payload") from exc
        raise ValueError("identity snapshot payload missing")

    @staticmethod
    def _block_manifest(snapshot_qff: bytes) -> Dict[str, str]:
        entries = IdentityVerifierService._snapshot_entries(snapshot_qff)
        rows = {name: hashlib.sha256(content).hexdigest() for name, content in entries.items()}
        return {name: rows[name] for name in sorted(rows)}

    @staticmethod
    def _snapshot_entries(snapshot_qff: bytes) -> Dict[str, bytes]:
        try:
            raw = gzip.decompress(snapshot_qff)
        except Exception as exc:
            raise ValueError("snapshot is not valid gzip payload") from exc

        entries: Dict[str, bytes] = {}
        try:
            with tarfile.open(fileobj=io.BytesIO(raw), mode="r") as tar:
                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    f = tar.extractfile(member)
                    if f is None:
                        continue
                    entries[member.name] = f.read()
        except Exception as exc:
            raise ValueError("snapshot is not valid tar payload") from exc

        if not entries:
            raise ValueError("snapshot has no file entries")
        return entries

    @staticmethod
    def _timeline_events(raw: Any) -> List[QSOEvent]:
        if not isinstance(raw, list):
            raise ValueError("bundle.timeline missing or invalid")
        events = [QSOEvent.model_validate(row) for row in raw]
        events.sort(key=lambda e: (e.timestamp.isoformat(), e.event_id, e.node_id))
        return events

    @staticmethod
    def _identity_kernel_events_from_timeline(events: Iterable[QSOEvent]) -> List[IdentityKernelEvent]:
        out: List[IdentityKernelEvent] = []
        for event in events:
            raw_identity_event = event.delta.get("identity_event")
            if not isinstance(raw_identity_event, dict):
                raise ValueError(f"timeline event missing identity_event payload: {event.event_id}")
            raw_payload = raw_identity_event.get("payload", {})
            payload = deepcopy(raw_payload if isinstance(raw_payload, dict) else {})
            out.append(
                IdentityKernelEvent(
                    event_id=str(raw_identity_event.get("event_id", event.event_id)),
                    event_type=parse_identity_event_type(str(raw_identity_event.get("event_type", ""))),
                    actor=str(raw_identity_event.get("actor", event.actor)),
                    policy_version=str(raw_identity_event.get("policy_version", event.policy_version)),
                    payload=payload,
                    node_id=str(raw_identity_event.get("node_id", event.node_id)),
                    timestamp=str(raw_identity_event.get("timestamp", event.timestamp.isoformat())),
                )
            )
        if not out:
            raise ValueError("bundle timeline contains no identity events")
        return out

    @staticmethod
    def _fail(step: str, reason: str, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        steps.append({"step": step, "ok": False, "reason": reason})
        return {"accepted": False, "reason": reason, "failed_step": step, "steps": steps}
