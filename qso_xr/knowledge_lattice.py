from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_event(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


class ConsistencyConflict(RuntimeError):
    pass


class KnowledgeLattice:
    """Append-only claim lattice with deterministic merge + immutable version snapshots."""

    def __init__(self, state_dir: str | Path) -> None:
        self.state_dir = Path(state_dir)
        self.events_path = self.state_dir / "knowledge_events.jsonl"
        self.versions_dir = self.state_dir / "versions"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        if not self.events_path.exists():
            self.events_path.write_text("", encoding="utf-8")

        self._claims: Dict[str, Dict[str, Any]] = {}
        self._event_count = 0
        self._last_hash = "GENESIS"
        self._load()

    def claims(self) -> Dict[str, Dict[str, Any]]:
        return {claim_id: dict(row) for claim_id, row in sorted(self._claims.items())}

    def append_claim(self, *, section: str, claim_id: str, statement: str, confidence: float) -> Dict[str, Any]:
        key = str(claim_id).strip()
        if not key:
            raise ValueError("claim_id must be non-empty")
        record = {
            "section": str(section),
            "claim_id": key,
            "statement": str(statement),
            "confidence": _safe_confidence(confidence),
        }
        event_type = "knowledge_claim_add" if key not in self._claims else "knowledge_claim_update"
        event = self._append_event(event_type=event_type, payload=record)
        self._claims[key] = dict(record)
        return event

    def merge_sandbox(
        self,
        *,
        branch_name: str,
        claims: Iterable[Dict[str, Any]],
        vote_approved: bool = True,
    ) -> Dict[str, Any]:
        incoming = [_normalize_claim(dict(row)) for row in claims]
        incoming.sort(key=lambda row: (row["claim_id"], row["section"], row["statement"]))

        new_claims: List[Dict[str, Any]] = []
        modified_claims: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        unchanged_count = 0
        overlap_count = 0
        conflict_count = 0

        for row in incoming:
            key = row["claim_id"]
            if key not in self._claims:
                new_claims.append(row)
                continue
            overlap_count += 1
            current = self._claims[key]
            if current["statement"] != row["statement"]:
                conflict_count += 1
                modified_claims.append((dict(current), row))
            else:
                unchanged_count += 1

        if conflict_count > 0 and not vote_approved:
            raise ConsistencyConflict(
                f"sandbox merge blocked: {conflict_count} conflict(s) for branch {branch_name}"
            )

        if not vote_approved:
            return {
                "branch": str(branch_name),
                "approved": False,
                "new_claims": len(new_claims),
                "modified_claims": len(modified_claims),
                "unchanged_claims": unchanged_count,
                "overlap_count": overlap_count,
                "conflict_count": conflict_count,
                "knowledge_curvature": _curvature(conflict_count, overlap_count),
                "version_id": None,
            }

        for row in new_claims:
            self.append_claim(
                section=row["section"],
                claim_id=row["claim_id"],
                statement=row["statement"],
                confidence=row["confidence"],
            )
        for _, row in modified_claims:
            self.append_claim(
                section=row["section"],
                claim_id=row["claim_id"],
                statement=row["statement"],
                confidence=row["confidence"],
            )

        snapshot = self._write_version_snapshot(
            branch_name=str(branch_name),
            overlap_count=overlap_count,
            conflict_count=conflict_count,
            new_claim_count=len(new_claims),
            modified_claim_count=len(modified_claims),
            unchanged_claim_count=unchanged_count,
        )
        self._append_event(
            event_type="knowledge_snapshot",
            payload={
                "branch": str(branch_name),
                "version_id": snapshot["version_id"],
                "state_hash": snapshot["state_hash"],
                "path": str(snapshot["path"]),
            },
        )

        return {
            "branch": str(branch_name),
            "approved": True,
            "new_claims": len(new_claims),
            "modified_claims": len(modified_claims),
            "unchanged_claims": unchanged_count,
            "overlap_count": overlap_count,
            "conflict_count": conflict_count,
            "knowledge_curvature": _curvature(conflict_count, overlap_count),
            "version_id": snapshot["version_id"],
            "version_path": str(snapshot["path"]),
            "state_hash": snapshot["state_hash"],
        }

    def section_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for claim_id in sorted(self._claims.keys()):
            section = str(self._claims[claim_id]["section"])
            counts[section] = counts.get(section, 0) + 1
        return counts

    def _load(self) -> None:
        self._claims = {}
        self._event_count = 0
        self._last_hash = "GENESIS"
        for raw in self.events_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line:
                continue
            event = json.loads(line)
            self._event_count += 1
            expected_prev = self._last_hash
            actual_prev = str(event.get("prev_hash", ""))
            if actual_prev != expected_prev:
                raise ConsistencyConflict("knowledge event hash chain broken")
            payload_without_hash = {k: event[k] for k in event if k != "hash"}
            expected_hash = _hash_event(payload_without_hash)
            actual_hash = str(event.get("hash", ""))
            if actual_hash != expected_hash:
                raise ConsistencyConflict("knowledge event hash mismatch")
            self._last_hash = actual_hash
            event_type = str(event.get("event_type", ""))
            payload = event.get("payload", {})
            if event_type in {"knowledge_claim_add", "knowledge_claim_update"} and isinstance(payload, dict):
                normalized = _normalize_claim(payload)
                self._claims[normalized["claim_id"]] = normalized

    def _append_event(self, *, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        next_id = self._event_count + 1
        row = {
            "schema_version": "1.0",
            "event_id": f"ev-{next_id:08d}",
            "ts": _utc_now(),
            "event_type": str(event_type),
            "payload": dict(payload),
            "prev_hash": self._last_hash,
        }
        row["hash"] = _hash_event(row)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(_canonical_json(row) + "\n")
        self._event_count = next_id
        self._last_hash = row["hash"]
        return row

    def _write_version_snapshot(
        self,
        *,
        branch_name: str,
        overlap_count: int,
        conflict_count: int,
        new_claim_count: int,
        modified_claim_count: int,
        unchanged_claim_count: int,
    ) -> Dict[str, Any]:
        stamp = _utc_now()
        stamp_compact = stamp.replace(":", "").replace("-", "").replace("Z", "Z")
        run_id = f"run-{self._event_count + 1:08d}"
        claims_sorted = [self._claims[key] for key in sorted(self._claims.keys())]
        base_payload = {
            "schema_version": "1.0",
            "created_at": stamp,
            "branch": branch_name,
            "run_id": run_id,
            "stats": {
                "claim_count": len(claims_sorted),
                "new_claim_count": int(new_claim_count),
                "modified_claim_count": int(modified_claim_count),
                "unchanged_claim_count": int(unchanged_claim_count),
                "overlap_count": int(overlap_count),
                "conflict_count": int(conflict_count),
                "knowledge_curvature": _curvature(conflict_count, overlap_count),
            },
            "claims": claims_sorted,
        }
        state_hash = _hash_event(base_payload)
        version_id = f"{stamp_compact}-{run_id}-{state_hash[:12]}"
        payload = dict(base_payload)
        payload["version_id"] = version_id
        payload["state_hash"] = state_hash
        path = self.versions_dir / f"{version_id}.json"
        if path.exists():
            raise ConsistencyConflict(f"version file already exists: {path}")
        path.write_text(_canonical_json(payload), encoding="utf-8")
        return {"version_id": version_id, "state_hash": state_hash, "path": path}


def _normalize_claim(row: Dict[str, Any]) -> Dict[str, Any]:
    claim_id = str(row.get("claim_id", "")).strip()
    if not claim_id:
        raise ValueError("claim row requires non-empty claim_id")
    return {
        "section": str(row.get("section", "unknown")),
        "claim_id": claim_id,
        "statement": str(row.get("statement", "")),
        "confidence": _safe_confidence(row.get("confidence", 0.5)),
    }


def _safe_confidence(value: Any) -> float:
    try:
        f = float(value)
    except Exception:
        f = 0.5
    if f < 0.0:
        return 0.0
    if f > 1.0:
        return 1.0
    return round(f, 6)


def _curvature(conflict_count: int, overlap_count: int) -> float:
    if overlap_count <= 0:
        return 0.0
    return round(float(conflict_count) / float(overlap_count), 6)
