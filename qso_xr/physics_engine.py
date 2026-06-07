from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple


def _vec3(value: Iterable[float] | None, default: Tuple[float, float, float]) -> Tuple[float, float, float]:
    if value is None:
        return default
    values = list(value)
    if len(values) != 3:
        return default
    if not all(isinstance(v, (int, float)) for v in values):
        return default
    return float(values[0]), float(values[1]), float(values[2])


def _round_vec(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return round(v[0], 6), round(v[1], 6), round(v[2], 6)


@dataclass
class _Body:
    position: Tuple[float, float, float]
    velocity: Tuple[float, float, float]
    mass: float
    radius: float
    static: bool
    accumulated_force: Tuple[float, float, float]


class XRPhysicsEngine:
    """Deterministic physics integrator with replayable tick logs."""

    def __init__(self) -> None:
        self._bodies: Dict[str, _Body] = {}
        self._tick = 0
        self._tick_log: List[Dict[str, Any]] = []

    @property
    def tick(self) -> int:
        return self._tick

    def add_body(
        self,
        body_id: str,
        *,
        position: Iterable[float] | None = None,
        velocity: Iterable[float] | None = None,
        mass: float = 1.0,
        radius: float = 0.5,
        static: bool = False,
    ) -> Dict[str, Any]:
        key = str(body_id).strip()
        if not key:
            raise ValueError("body_id must be non-empty")
        safe_mass = max(float(mass), 1e-9)
        safe_radius = max(float(radius), 1e-6)
        body = _Body(
            position=_vec3(position, (0.0, 0.0, 0.0)),
            velocity=_vec3(velocity, (0.0, 0.0, 0.0)),
            mass=safe_mass,
            radius=safe_radius,
            static=bool(static),
            accumulated_force=(0.0, 0.0, 0.0),
        )
        self._bodies[key] = body
        return {"body_id": key, "state": self._body_payload(body)}

    def apply_force(self, body_id: str, force: Iterable[float]) -> Dict[str, Any]:
        key = str(body_id)
        if key not in self._bodies:
            raise KeyError(key)
        body = self._bodies[key]
        fx, fy, fz = _vec3(force, (0.0, 0.0, 0.0))
        ax, ay, az = body.accumulated_force
        body.accumulated_force = (ax + fx, ay + fy, az + fz)
        return {"body_id": key, "accumulated_force": [round(v, 6) for v in body.accumulated_force]}

    def apply_impulse(self, body_id: str, impulse: Iterable[float]) -> Dict[str, Any]:
        key = str(body_id)
        if key not in self._bodies:
            raise KeyError(key)
        body = self._bodies[key]
        if body.static:
            return {"body_id": key, "velocity": [round(v, 6) for v in body.velocity], "applied": False}
        ix, iy, iz = _vec3(impulse, (0.0, 0.0, 0.0))
        vx, vy, vz = body.velocity
        body.velocity = _round_vec((vx + (ix / body.mass), vy + (iy / body.mass), vz + (iz / body.mass)))
        return {"body_id": key, "velocity": [round(v, 6) for v in body.velocity], "applied": True}

    def step(self, *, dt_ms: float = 16.0, gravity: Iterable[float] | None = None) -> Dict[str, Any]:
        dt = max(float(dt_ms), 0.0) / 1000.0
        gx, gy, gz = _vec3(gravity, (0.0, -9.81, 0.0))

        for body_id in sorted(self._bodies.keys()):
            body = self._bodies[body_id]
            if body.static:
                body.accumulated_force = (0.0, 0.0, 0.0)
                continue

            fx, fy, fz = body.accumulated_force
            ax = gx + (fx / body.mass)
            ay = gy + (fy / body.mass)
            az = gz + (fz / body.mass)

            vx, vy, vz = body.velocity
            vx2 = vx + ax * dt
            vy2 = vy + ay * dt
            vz2 = vz + az * dt
            px, py, pz = body.position
            px2 = px + vx2 * dt
            py2 = py + vy2 * dt
            pz2 = pz + vz2 * dt

            body.velocity = _round_vec((vx2, vy2, vz2))
            body.position = _round_vec((px2, py2, pz2))
            body.accumulated_force = (0.0, 0.0, 0.0)

        collisions = self._detect_collisions()
        self._tick += 1
        event = {
            "tick": self._tick,
            "dt_ms": round(dt_ms, 6),
            "body_count": len(self._bodies),
            "collisions": collisions,
            "snapshot": self.snapshot(),
        }
        self._tick_log.append(event)
        return event

    def snapshot(self) -> Dict[str, Any]:
        return {
            "tick": self._tick,
            "bodies": {
                body_id: self._body_payload(self._bodies[body_id])
                for body_id in sorted(self._bodies.keys())
            },
        }

    def tick_log(self) -> List[Dict[str, Any]]:
        return [dict(item) for item in self._tick_log]

    @classmethod
    def replay(
        cls,
        *,
        bodies: MappingLike,
        force_schedule: Iterable[Dict[str, Any]],
        steps: int,
        dt_ms: float = 16.0,
        gravity: Iterable[float] | None = None,
    ) -> Dict[str, Any]:
        engine = cls()
        for body_id in sorted(bodies.keys()):
            spec = bodies[body_id]
            engine.add_body(
                body_id,
                position=spec.get("position"),
                velocity=spec.get("velocity"),
                mass=float(spec.get("mass", 1.0)),
                radius=float(spec.get("radius", 0.5)),
                static=bool(spec.get("static", False)),
            )

        schedule = sorted(
            [dict(item) for item in force_schedule],
            key=lambda item: (int(item.get("tick", 0)), str(item.get("body_id", ""))),
        )
        cursor = 0
        for tick in range(1, int(steps) + 1):
            while cursor < len(schedule) and int(schedule[cursor].get("tick", 0)) == tick:
                row = schedule[cursor]
                body_id = str(row.get("body_id", ""))
                if body_id in engine._bodies:
                    if "impulse" in row:
                        engine.apply_impulse(body_id, row.get("impulse", [0.0, 0.0, 0.0]))
                    if "force" in row:
                        engine.apply_force(body_id, row.get("force", [0.0, 0.0, 0.0]))
                cursor += 1
            engine.step(dt_ms=dt_ms, gravity=gravity)
        return engine.snapshot()

    def _detect_collisions(self) -> List[Dict[str, Any]]:
        ids = sorted(self._bodies.keys())
        collisions: List[Dict[str, Any]] = []
        for i, left_id in enumerate(ids):
            left = self._bodies[left_id]
            for right_id in ids[i + 1 :]:
                right = self._bodies[right_id]
                dx = left.position[0] - right.position[0]
                dy = left.position[1] - right.position[1]
                dz = left.position[2] - right.position[2]
                dist_sq = dx * dx + dy * dy + dz * dz
                limit = left.radius + right.radius
                if dist_sq <= limit * limit:
                    collisions.append(
                        {
                            "a": left_id,
                            "b": right_id,
                            "distance_sq": round(dist_sq, 6),
                            "threshold_sq": round(limit * limit, 6),
                        }
                    )
                    # Deterministic damped response keeps replay stable and bounded.
                    if not left.static:
                        left.velocity = (0.0, 0.0, 0.0)
                    if not right.static:
                        right.velocity = (0.0, 0.0, 0.0)
        return collisions

    @staticmethod
    def _body_payload(body: _Body) -> Dict[str, Any]:
        return {
            "position": [round(v, 6) for v in body.position],
            "velocity": [round(v, 6) for v in body.velocity],
            "mass": round(body.mass, 6),
            "radius": round(body.radius, 6),
            "static": body.static,
        }


MappingLike = Dict[str, Dict[str, Any]]
