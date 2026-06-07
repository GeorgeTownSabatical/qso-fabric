from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping


def _vec3(value: Any, default: tuple[float, float, float]) -> tuple[float, float, float]:
    if isinstance(value, list) and len(value) == 3 and all(isinstance(v, (int, float)) for v in value):
        return float(value[0]), float(value[1]), float(value[2])
    return default


def _quat(value: Any, default: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    if isinstance(value, list) and len(value) == 4 and all(isinstance(v, (int, float)) for v in value):
        x, y, z, w = float(value[0]), float(value[1]), float(value[2]), float(value[3])
        length = math.sqrt(x * x + y * y + z * z + w * w)
        if length > 1e-9:
            return x / length, y / length, z / length, w / length
    return default


def _aabb(value: Any) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    if isinstance(value, dict):
        lo = _vec3(value.get("min"), (-0.5, -0.5, -0.5))
        hi = _vec3(value.get("max"), (0.5, 0.5, 0.5))
        return lo, hi
    return (-0.5, -0.5, -0.5), (0.5, 0.5, 0.5)


def _identity() -> list[float]:
    return [
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
    ]


def _mul4(a: list[float], b: list[float]) -> list[float]:
    out = [0.0] * 16
    for r in range(4):
        r0 = r * 4
        for c in range(4):
            out[r0 + c] = (
                a[r0 + 0] * b[c + 0]
                + a[r0 + 1] * b[c + 4]
                + a[r0 + 2] * b[c + 8]
                + a[r0 + 3] * b[c + 12]
            )
    return out


def _transform_point(m: list[float], p: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = p
    return (
        m[0] * x + m[1] * y + m[2] * z + m[3],
        m[4] * x + m[5] * y + m[6] * z + m[7],
        m[8] * x + m[9] * y + m[10] * z + m[11],
    )


def _trs(pos: tuple[float, float, float], rot: tuple[float, float, float, float], scl: tuple[float, float, float]) -> list[float]:
    x, y, z, w = rot
    xx = x * x
    yy = y * y
    zz = z * z
    xy = x * y
    xz = x * z
    yz = y * z
    wx = w * x
    wy = w * y
    wz = w * z

    r00 = 1.0 - 2.0 * (yy + zz)
    r01 = 2.0 * (xy - wz)
    r02 = 2.0 * (xz + wy)
    r10 = 2.0 * (xy + wz)
    r11 = 1.0 - 2.0 * (xx + zz)
    r12 = 2.0 * (yz - wx)
    r20 = 2.0 * (xz - wy)
    r21 = 2.0 * (yz + wx)
    r22 = 1.0 - 2.0 * (xx + yy)

    sx, sy, sz = scl
    px, py, pz = pos
    return [
        r00 * sx,
        r01 * sy,
        r02 * sz,
        px,
        r10 * sx,
        r11 * sy,
        r12 * sz,
        py,
        r20 * sx,
        r21 * sy,
        r22 * sz,
        pz,
        0.0,
        0.0,
        0.0,
        1.0,
    ]


def _round_matrix(values: list[float]) -> list[float]:
    return [round(v, 6) for v in values]


@dataclass(frozen=True)
class _Node:
    uri: str
    node_id: str
    parent: str | None
    pos: tuple[float, float, float]
    rot: tuple[float, float, float, float]
    scl: tuple[float, float, float]
    bounds_min: tuple[float, float, float]
    bounds_max: tuple[float, float, float]
    layer_mask: int
    mesh_uri: str | None
    material_uri: str | None


class SceneRenderProjector:
    """Deterministic scene projector for `scene.render_v1`."""

    def validate(
        self,
        *,
        world_uri: str,
        nodes_by_uri: Mapping[str, Mapping[str, Any]],
    ) -> Dict[str, Any]:
        nodes = self._nodes_for_world(world_uri=world_uri, nodes_by_uri=nodes_by_uri)
        issues = self._integrity_issues(nodes)
        return {
            "world_uri": world_uri,
            "node_count": len(nodes),
            "ok": len(issues) == 0,
            "issues": issues,
        }

    def project(
        self,
        *,
        world_uri: str,
        nodes_by_uri: Mapping[str, Mapping[str, Any]],
        viewpoint: Mapping[str, Any] | None = None,
        frame: int = 0,
    ) -> Dict[str, Any]:
        nodes = self._nodes_for_world(world_uri=world_uri, nodes_by_uri=nodes_by_uri)
        integrity_issues = self._integrity_issues(nodes)

        children: Dict[str, list[str]] = {uri: [] for uri in nodes}
        for uri, node in nodes.items():
            if node.parent and node.parent in children:
                children[node.parent].append(uri)
        for uri in children:
            children[uri].sort()

        roots = sorted(
            [
                uri
                for uri, node in nodes.items()
                if node.parent is None or node.parent not in nodes
            ]
        )

        world_mats: Dict[str, list[float]] = {}
        local_mats: Dict[str, list[float]] = {uri: _trs(n.pos, n.rot, n.scl) for uri, n in nodes.items()}

        def _walk(uri: str, parent_world: list[float], lineage: set[str]) -> None:
            if uri in lineage:
                return
            current_world = _mul4(parent_world, local_mats[uri])
            world_mats[uri] = current_world
            next_lineage = set(lineage)
            next_lineage.add(uri)
            for child_uri in children.get(uri, []):
                _walk(child_uri, current_world, next_lineage)

        for uri in roots:
            _walk(uri, _identity(), set())
        for uri in sorted(nodes.keys()):
            if uri not in world_mats:
                _walk(uri, _identity(), set())

        vis = self._viewpoint_filters(viewpoint)
        visible: list[Dict[str, Any]] = []
        culled = 0

        for uri in sorted(nodes.keys()):
            node = nodes[uri]
            world = world_mats[uri]
            center, radius = self._world_bounds(node, world)
            if not self._is_relevant(uri, node, center, radius, vis):
                culled += 1
                continue

            visible.append(
                {
                    "uri": uri,
                    "node_id": node.node_id,
                    "world_matrix": _round_matrix(world),
                    "mesh": node.mesh_uri,
                    "material": node.material_uri,
                    "layer_mask": node.layer_mask,
                    "world_bounds": {
                        "center": [round(center[0], 6), round(center[1], 6), round(center[2], 6)],
                        "radius": round(radius, 6),
                    },
                }
            )

        return {
            "projection": "scene.render_v1",
            "world_uri": world_uri,
            "frame": int(frame),
            "matrix_order": "row_major",
            "visible": visible,
            "stats": {
                "total_nodes": len(nodes),
                "visible": len(visible),
                "culled": culled,
            },
            "integrity": {
                "ok": len(integrity_issues) == 0,
                "issues": integrity_issues,
            },
        }

    def _nodes_for_world(
        self,
        *,
        world_uri: str,
        nodes_by_uri: Mapping[str, Mapping[str, Any]],
    ) -> Dict[str, _Node]:
        nodes: Dict[str, _Node] = {}
        prefix = world_uri.rstrip("/") + "/node/"
        for uri in sorted(nodes_by_uri.keys()):
            if not uri.startswith(prefix):
                continue
            state = nodes_by_uri.get(uri, {})
            if not isinstance(state, Mapping):
                continue
            nodes[uri] = self._parse_node(uri, state)
        return nodes

    def _integrity_issues(self, nodes: Mapping[str, _Node]) -> list[Dict[str, Any]]:
        issues: list[Dict[str, Any]] = []

        for uri in sorted(nodes.keys()):
            node = nodes[uri]
            if node.parent == uri:
                issues.append({"type": "self_parent", "uri": uri})
            elif node.parent is not None and node.parent not in nodes:
                issues.append({"type": "missing_parent", "uri": uri, "parent": node.parent})

        by_id: Dict[str, list[str]] = {}
        for uri in sorted(nodes.keys()):
            by_id.setdefault(nodes[uri].node_id, []).append(uri)
        for node_id in sorted(by_id.keys()):
            uris = by_id[node_id]
            if len(uris) > 1:
                issues.append({"type": "duplicate_node_id", "node_id": node_id, "uris": uris})

        color: Dict[str, int] = {}
        cycle_keys: set[tuple[str, ...]] = set()

        def _visit(uri: str, path: list[str]) -> None:
            color[uri] = 1
            path.append(uri)
            parent = nodes[uri].parent
            if parent in nodes:
                p = str(parent)
                state = color.get(p, 0)
                if state == 0:
                    _visit(p, path)
                elif state == 1:
                    start = 0
                    for i, item in enumerate(path):
                        if item == p:
                            start = i
                            break
                    cycle = path[start:] + [p]
                    key = tuple(sorted(set(cycle)))
                    if key not in cycle_keys:
                        cycle_keys.add(key)
                        issues.append({"type": "parent_cycle", "cycle_uris": cycle})
            path.pop()
            color[uri] = 2

        for uri in sorted(nodes.keys()):
            if color.get(uri, 0) == 0:
                _visit(uri, [])

        return issues

    def _parse_node(self, uri: str, state: Mapping[str, Any]) -> _Node:
        node_id = str(state.get("id", uri.rsplit("/", 1)[-1]))
        parent_raw = state.get("parent")
        parent = str(parent_raw).strip() if isinstance(parent_raw, str) and parent_raw.strip() else None

        transform = state.get("transform")
        if isinstance(transform, Mapping):
            pos = _vec3(transform.get("pos", transform.get("position")), (0.0, 0.0, 0.0))
            rot = _quat(transform.get("rot", transform.get("rotation")), (0.0, 0.0, 0.0, 1.0))
            scl = _vec3(transform.get("scl", transform.get("scale")), (1.0, 1.0, 1.0))
        else:
            pos = (0.0, 0.0, 0.0)
            rot = (0.0, 0.0, 0.0, 1.0)
            scl = (1.0, 1.0, 1.0)

        bounds_min, bounds_max = _aabb(state.get("bounds"))

        layer_mask_raw = state.get("layer_mask", 1)
        try:
            layer_mask = int(layer_mask_raw)
        except Exception:
            layer_mask = 1
        if layer_mask < 0:
            layer_mask = 0

        mesh_uri = None
        material_uri = None
        components = state.get("components")
        if isinstance(components, Mapping):
            mesh = components.get("mesh")
            if isinstance(mesh, Mapping) and isinstance(mesh.get("uri"), str):
                mesh_uri = str(mesh["uri"])
            material = components.get("material")
            if isinstance(material, Mapping) and isinstance(material.get("uri"), str):
                material_uri = str(material["uri"])

        return _Node(
            uri=uri,
            node_id=node_id,
            parent=parent,
            pos=pos,
            rot=rot,
            scl=scl,
            bounds_min=bounds_min,
            bounds_max=bounds_max,
            layer_mask=layer_mask,
            mesh_uri=mesh_uri,
            material_uri=material_uri,
        )

    def _world_bounds(self, node: _Node, world: list[float]) -> tuple[tuple[float, float, float], float]:
        cx = (node.bounds_min[0] + node.bounds_max[0]) * 0.5
        cy = (node.bounds_min[1] + node.bounds_max[1]) * 0.5
        cz = (node.bounds_min[2] + node.bounds_max[2]) * 0.5
        ex = (node.bounds_max[0] - node.bounds_min[0]) * 0.5
        ey = (node.bounds_max[1] - node.bounds_min[1]) * 0.5
        ez = (node.bounds_max[2] - node.bounds_min[2]) * 0.5
        local_radius = math.sqrt(ex * ex + ey * ey + ez * ez)
        scale_max = max(abs(node.scl[0]), abs(node.scl[1]), abs(node.scl[2]), 1e-6)
        world_center = _transform_point(world, (cx, cy, cz))
        return world_center, local_radius * scale_max

    def _viewpoint_filters(self, viewpoint: Mapping[str, Any] | None) -> Dict[str, Any]:
        if not isinstance(viewpoint, Mapping):
            return {}

        center = _vec3(viewpoint.get("center"), (0.0, 0.0, 0.0))
        radius_raw = viewpoint.get("radius", float("inf"))
        max_distance_raw = viewpoint.get("max_distance", float("inf"))
        layer_mask_raw = viewpoint.get("layer_mask")

        try:
            radius = float(radius_raw)
        except Exception:
            radius = float("inf")
        if radius <= 0:
            radius = float("inf")

        try:
            max_distance = float(max_distance_raw)
        except Exception:
            max_distance = float("inf")
        if max_distance <= 0:
            max_distance = float("inf")

        layer_mask = None
        if layer_mask_raw is not None:
            try:
                layer_mask = int(layer_mask_raw)
            except Exception:
                layer_mask = None

        focus_uris = set()
        raw_focus = viewpoint.get("focus_uris")
        if isinstance(raw_focus, list):
            focus_uris = {str(v) for v in raw_focus if isinstance(v, str)}

        allow_prefixes: list[str] = []
        raw_allow = viewpoint.get("allow_prefixes")
        if isinstance(raw_allow, list):
            allow_prefixes = [str(v) for v in raw_allow if isinstance(v, str)]

        deny_prefixes: list[str] = []
        raw_deny = viewpoint.get("deny_prefixes")
        if isinstance(raw_deny, list):
            deny_prefixes = [str(v) for v in raw_deny if isinstance(v, str)]

        return {
            "center": center,
            "radius": radius,
            "max_distance": max_distance,
            "layer_mask": layer_mask,
            "focus_uris": focus_uris,
            "allow_prefixes": allow_prefixes,
            "deny_prefixes": deny_prefixes,
        }

    def _is_relevant(
        self,
        uri: str,
        node: _Node,
        center: tuple[float, float, float],
        radius: float,
        filters: Mapping[str, Any],
    ) -> bool:
        layer_mask = filters.get("layer_mask")
        if isinstance(layer_mask, int) and (node.layer_mask & layer_mask) == 0:
            return False

        focus_uris = filters.get("focus_uris")
        if isinstance(focus_uris, set) and focus_uris and uri not in focus_uris:
            return False

        allow_prefixes = filters.get("allow_prefixes")
        if isinstance(allow_prefixes, list) and allow_prefixes:
            if not any(uri.startswith(prefix) for prefix in allow_prefixes):
                return False

        deny_prefixes = filters.get("deny_prefixes")
        if isinstance(deny_prefixes, list) and deny_prefixes:
            if any(uri.startswith(prefix) for prefix in deny_prefixes):
                return False

        vp_center = filters.get("center")
        vp_radius = filters.get("radius", float("inf"))
        vp_max_distance = filters.get("max_distance", float("inf"))
        if not isinstance(vp_center, tuple) or len(vp_center) != 3:
            return True

        dx = center[0] - vp_center[0]
        dy = center[1] - vp_center[1]
        dz = center[2] - vp_center[2]
        dist_sq = dx * dx + dy * dy + dz * dz
        dist = math.sqrt(dist_sq)

        if math.isfinite(vp_radius) and dist > (vp_radius + radius):
            return False
        if math.isfinite(vp_max_distance) and dist > (vp_max_distance + radius):
            return False
        return True
