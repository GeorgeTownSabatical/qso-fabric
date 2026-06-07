from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class _Link:
    source_uri: str
    target_uri: str
    relationship: str
    strength: float
    sync_mode: str
    latency_target_ms: int


class XREntanglementPropagator:
    """Deterministic link graph for XR delta propagation."""

    def __init__(self) -> None:
        self._links_by_source: Dict[str, List[_Link]] = {}

    def entangle(
        self,
        uri_a: str,
        uri_b: str,
        relationship: str,
        *,
        strength: float = 1.0,
        sync_mode: str = "eager",
        latency_target_ms: int = 16,
        bidirectional: bool = True,
    ) -> List[Dict[str, Any]]:
        left = str(uri_a)
        right = str(uri_b)
        rel = str(relationship)
        safe_strength = max(0.0, float(strength))
        safe_latency = max(0, int(latency_target_ms))
        mode = str(sync_mode)

        inserted = [
            self._insert_link(_Link(left, right, rel, safe_strength, mode, safe_latency)),
        ]
        if bidirectional:
            inserted.append(self._insert_link(_Link(right, left, rel, safe_strength, mode, safe_latency)))
        return inserted

    def propagate(self, source_uri: str, delta: Dict[str, Any]) -> List[Dict[str, Any]]:
        source = str(source_uri)
        links = sorted(
            self._links_by_source.get(source, []),
            key=lambda link: (link.target_uri, link.relationship, link.sync_mode, link.latency_target_ms),
        )
        out: List[Dict[str, Any]] = []
        for link in links:
            out.append(
                {
                    "uri": link.target_uri,
                    "entangled_from": source,
                    "relationship": link.relationship,
                    "strength": round(link.strength, 6),
                    "sync_mode": link.sync_mode,
                    "latency_target_ms": link.latency_target_ms,
                    "delta": _scale_delta(delta, link.strength),
                }
            )
        return out

    def snapshot(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for source in sorted(self._links_by_source.keys()):
            for link in sorted(
                self._links_by_source[source],
                key=lambda row: (row.target_uri, row.relationship, row.sync_mode, row.latency_target_ms),
            ):
                rows.append(
                    {
                        "source_uri": link.source_uri,
                        "target_uri": link.target_uri,
                        "relationship": link.relationship,
                        "strength": round(link.strength, 6),
                        "sync_mode": link.sync_mode,
                        "latency_target_ms": link.latency_target_ms,
                    }
                )
        return rows

    def _insert_link(self, link: _Link) -> Dict[str, Any]:
        bucket = self._links_by_source.setdefault(link.source_uri, [])
        if link not in bucket:
            bucket.append(link)
        return {
            "source_uri": link.source_uri,
            "target_uri": link.target_uri,
            "relationship": link.relationship,
            "strength": round(link.strength, 6),
            "sync_mode": link.sync_mode,
            "latency_target_ms": link.latency_target_ms,
        }


def _scale_delta(value: Any, strength: float) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value) * strength, 6)
    if isinstance(value, list):
        return [_scale_delta(item, strength) for item in value]
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key in sorted(value.keys()):
            out[str(key)] = _scale_delta(value[key], strength)
        return out
    return deepcopy(value)
