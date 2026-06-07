from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Mapping


def _vec3(value: Any, default: List[float]) -> List[float]:
    if isinstance(value, list) and len(value) == 3 and all(isinstance(v, (int, float)) for v in value):
        return [float(value[0]), float(value[1]), float(value[2])]
    return list(default)


def _quat(value: Any, default: List[float]) -> List[float]:
    if isinstance(value, list) and len(value) == 4 and all(isinstance(v, (int, float)) for v in value):
        x, y, z, w = float(value[0]), float(value[1]), float(value[2]), float(value[3])
        norm = (x * x + y * y + z * z + w * w) ** 0.5
        if norm > 1e-9:
            return [x / norm, y / norm, z / norm, w / norm]
    return list(default)


def _clean_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "unknown_anchor"
    out = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in text)
    return out.strip("_") or "unknown_anchor"


class ARKitAdapter:
    """Baseline ARKit <-> QSO scene import/export adapter."""

    schema_version = "1.0"

    def import_frame(self, *, world_uri: str, frame: Mapping[str, Any]) -> Dict[str, Any]:
        world_uri = str(world_uri).rstrip("/")
        anchors_raw = frame.get("anchors", [])
        anchors = anchors_raw if isinstance(anchors_raw, list) else []
        node_patches: Dict[str, Dict[str, Any]] = {}

        for index, anchor in enumerate(sorted(anchors, key=lambda row: str(dict(row).get("anchor_id", "")) if isinstance(row, Mapping) else "")):
            if not isinstance(anchor, Mapping):
                continue
            anchor_id = _clean_id(anchor.get("anchor_id") or f"anchor_{index}")
            node_uri = f"{world_uri}/node/arkit_{anchor_id}"

            transform = anchor.get("transform", {})
            transform = transform if isinstance(transform, Mapping) else {}
            position = _vec3(transform.get("position"), [0.0, 0.0, 0.0])
            rotation = _quat(transform.get("rotation"), [0.0, 0.0, 0.0, 1.0])
            scale = _vec3(transform.get("scale"), [1.0, 1.0, 1.0])
            extent = _vec3(anchor.get("extent"), [0.3, 0.3, 0.3])
            label = str(anchor.get("classification", "unknown"))

            node_patches[node_uri] = {
                "id": f"arkit_{anchor_id}",
                "transform": {
                    "pos": position,
                    "rot": rotation,
                    "scl": scale,
                },
                "bounds": {
                    "min": [-extent[0] * 0.5, -extent[1] * 0.5, -extent[2] * 0.5],
                    "max": [extent[0] * 0.5, extent[1] * 0.5, extent[2] * 0.5],
                },
                "layer_mask": 2,
                "arkit": {
                    "anchor_id": anchor_id,
                    "classification": label,
                    "tracking_state": str(anchor.get("tracking_state", "unknown")),
                },
            }

        camera_raw = frame.get("camera", {})
        camera = camera_raw if isinstance(camera_raw, Mapping) else {}
        camera_transform = camera.get("transform", {})
        camera_transform = camera_transform if isinstance(camera_transform, Mapping) else {}
        camera_patch = {
            "id": "arkit_camera",
            "transform": {
                "pos": _vec3(camera_transform.get("position"), [0.0, 1.6, 0.0]),
                "rot": _quat(camera_transform.get("rotation"), [0.0, 0.0, 0.0, 1.0]),
                "scl": [1.0, 1.0, 1.0],
            },
            "layer_mask": 4,
            "arkit_camera": {
                "tracking_state": str(camera.get("tracking_state", "unknown")),
                "exposure": float(camera.get("exposure", 0.0)) if isinstance(camera.get("exposure"), (int, float)) else 0.0,
            },
        }

        camera_uri = f"{world_uri}/node/arkit_camera"
        node_patches[camera_uri] = camera_patch

        return {
            "schema_version": self.schema_version,
            "world_uri": world_uri,
            "anchors_ingested": len([uri for uri in node_patches if uri != camera_uri]),
            "node_patches": node_patches,
            "source": {
                "session_id": str(frame.get("session_id", "")),
                "timestamp_ms": int(frame.get("timestamp_ms", 0)) if isinstance(frame.get("timestamp_ms"), (int, float)) else 0,
            },
        }

    def export_scene(self, *, world_uri: str, nodes_by_uri: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
        world_uri = str(world_uri).rstrip("/")
        prefix = f"{world_uri}/node/"
        anchors: List[Dict[str, Any]] = []
        camera_payload: Dict[str, Any] | None = None

        for uri in sorted(nodes_by_uri.keys()):
            if not uri.startswith(prefix):
                continue
            state = nodes_by_uri[uri]
            if not isinstance(state, Mapping):
                continue

            transform = state.get("transform", {})
            transform = transform if isinstance(transform, Mapping) else {}
            position = _vec3(transform.get("pos", transform.get("position")), [0.0, 0.0, 0.0])
            rotation = _quat(transform.get("rot", transform.get("rotation")), [0.0, 0.0, 0.0, 1.0])
            scale = _vec3(transform.get("scl", transform.get("scale")), [1.0, 1.0, 1.0])

            if str(state.get("id", "")).strip() == "arkit_camera":
                camera_payload = {
                    "transform": {"position": position, "rotation": rotation},
                    "tracking_state": str(dict(state.get("arkit_camera", {})).get("tracking_state", "unknown")),
                }
                continue

            bounds = state.get("bounds", {})
            bounds = bounds if isinstance(bounds, Mapping) else {}
            bmin = _vec3(bounds.get("min"), [-0.15, -0.15, -0.15])
            bmax = _vec3(bounds.get("max"), [0.15, 0.15, 0.15])
            extent = [max(0.01, bmax[0] - bmin[0]), max(0.01, bmax[1] - bmin[1]), max(0.01, bmax[2] - bmin[2])]

            arkit_meta = state.get("arkit", {})
            arkit_meta = arkit_meta if isinstance(arkit_meta, Mapping) else {}
            anchor_id = _clean_id(arkit_meta.get("anchor_id") or state.get("id") or uri.rsplit("/", 1)[-1])
            anchors.append(
                {
                    "anchor_id": anchor_id,
                    "classification": str(arkit_meta.get("classification", "unknown")),
                    "tracking_state": str(arkit_meta.get("tracking_state", "mapped")),
                    "transform": {
                        "position": position,
                        "rotation": rotation,
                        "scale": scale,
                    },
                    "extent": extent,
                }
            )

        return {
            "schema_version": self.schema_version,
            "world_uri": world_uri,
            "session_id": f"arkit-export-{_clean_id(world_uri.split('://', 1)[-1])}",
            "timestamp_ms": 0,
            "camera": camera_payload
            or {
                "transform": {"position": [0.0, 1.6, 0.0], "rotation": [0.0, 0.0, 0.0, 1.0]},
                "tracking_state": "unknown",
            },
            "anchors": anchors,
        }

    def roundtrip(self, *, world_uri: str, frame: Mapping[str, Any]) -> Dict[str, Any]:
        imported = self.import_frame(world_uri=world_uri, frame=frame)
        exported = self.export_scene(world_uri=world_uri, nodes_by_uri=imported["node_patches"])
        return {
            "imported": deepcopy(imported),
            "exported": deepcopy(exported),
            "anchor_count_in": len(frame.get("anchors", [])) if isinstance(frame.get("anchors"), list) else 0,
            "anchor_count_out": len(exported.get("anchors", [])),
        }
