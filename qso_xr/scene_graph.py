from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Mapping

from qso_vr_visualization.scene_render_projector import SceneRenderProjector


class XRSceneGraph:
    """Deterministic scene-graph facade for `qso://.../node/<id>` URIs."""

    def __init__(self, world_uri: str) -> None:
        self.world_uri = str(world_uri).rstrip("/")
        self._prefix = f"{self.world_uri}/node/"
        self._nodes_by_uri: Dict[str, Dict[str, Any]] = {}
        self._projector = SceneRenderProjector()

    @property
    def nodes_by_uri(self) -> Dict[str, Dict[str, Any]]:
        return {uri: deepcopy(payload) for uri, payload in sorted(self._nodes_by_uri.items())}

    def upsert_node(self, node_uri: str, patch: Mapping[str, Any]) -> Dict[str, Any]:
        uri = str(node_uri)
        if not uri.startswith(self._prefix):
            raise ValueError(f"node_uri must start with {self._prefix}")
        current = deepcopy(self._nodes_by_uri.get(uri, {}))
        merged = _deep_merge(current, dict(patch))
        self._nodes_by_uri[uri] = merged
        return {"uri": uri, "state": deepcopy(merged)}

    def patch_nodes(self, patches: Mapping[str, Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
        results: Dict[str, Dict[str, Any]] = {}
        for uri in sorted(patches.keys()):
            results[uri] = self.upsert_node(uri, patches[uri])
        return results

    def validate(self) -> Dict[str, Any]:
        return self._projector.validate(
            world_uri=self.world_uri,
            nodes_by_uri=self._nodes_by_uri,
        )

    def project(self, *, viewpoint: Mapping[str, Any] | None = None, frame: int = 0) -> Dict[str, Any]:
        return self._projector.project(
            world_uri=self.world_uri,
            nodes_by_uri=self._nodes_by_uri,
            viewpoint=viewpoint,
            frame=frame,
        )


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    for key in sorted(patch.keys()):
        incoming = patch[key]
        if isinstance(incoming, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(dict(base[key]), dict(incoming))
        else:
            base[key] = deepcopy(incoming)
    return base
