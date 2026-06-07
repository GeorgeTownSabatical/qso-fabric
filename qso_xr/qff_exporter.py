from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping

from qso_xr.determinism import canonical_json, sha256_hex


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_qff_document(
    *,
    world_uri: str,
    scene_nodes: Mapping[str, Mapping[str, Any]],
    knowledge_claims: Mapping[str, Mapping[str, Any]],
    render_payload: Mapping[str, Any],
    profile: str | None = None,
) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "schema_version": "1.0",
        "format": "qso-xr-qff-json",
        "world_uri": str(world_uri),
        "profile": str(profile or "default"),
        "exported_at": _utc_now(),
        "scene": {
            "node_count": len(scene_nodes),
            "nodes_by_uri": {str(uri): dict(payload) for uri, payload in sorted(scene_nodes.items())},
        },
        "knowledge": {
            "claim_count": len(knowledge_claims),
            "claims_by_id": {str(claim_id): dict(payload) for claim_id, payload in sorted(knowledge_claims.items())},
        },
        "render": dict(render_payload),
    }
    base["state_hash"] = sha256_hex(
        {
            "world_uri": base["world_uri"],
            "profile": base["profile"],
            "scene": base["scene"],
            "knowledge": base["knowledge"],
            "render": base["render"],
        }
    )
    return base


def export_qff_json(path: str | Path, payload: Mapping[str, Any]) -> Dict[str, Any]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized = dict(payload)
    encoded = canonical_json(normalized)
    target.write_text(encoded, encoding="utf-8")
    return {
        "path": str(target),
        "bytes": len(encoded.encode("utf-8")),
        "sha256": sha256_hex(normalized),
    }


def load_qff_json(path: str | Path) -> Dict[str, Any]:
    target = Path(path)
    parsed = target.read_text(encoding="utf-8")
    # Keep parser explicit and deterministic.
    import json

    payload = json.loads(parsed)
    if not isinstance(payload, dict):
        raise ValueError("qff payload must be an object")
    return payload
