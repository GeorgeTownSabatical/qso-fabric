from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, Mapping

from solis.physics.collapse_engine import collapse_probability_v1
from solis.physics.fixed_math import Fixed64

_FIXED_ZERO = Fixed64.zero()
_FIXED_ONE = Fixed64.one()
_FIXED_TEN = Fixed64.from_int(10)
_FIXED_EPSILON = Fixed64.from_str("0.000000001")


@dataclass(frozen=True)
class StellarState:
    star_id: str = ""
    chain_id: str = ""
    mass: float = 0.0
    luminosity: float = 0.0
    core_temp: float = 0.0
    magnetic_field: float = 0.0
    entropy_index: float = 0.0
    fusion_rate: float = 0.0
    collapse_probability: float = 0.0

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "StellarState":
        return cls(
            star_id=str(data.get("star_id", "")),
            chain_id=str(data.get("chain_id", "")),
            mass=_as_projection_float(data.get("mass", 0.0)),
            luminosity=_as_projection_float(data.get("luminosity", 0.0)),
            core_temp=_as_projection_float(data.get("core_temp", 0.0)),
            magnetic_field=_as_projection_float(data.get("magnetic_field", 0.0)),
            entropy_index=_as_projection_float(data.get("entropy_index", 0.0)),
            fusion_rate=_as_projection_float(data.get("fusion_rate", 0.0)),
            collapse_probability=_as_projection_float(data.get("collapse_probability", 0.0)),
        )

    def as_dict(self) -> Dict[str, object]:
        return {
            "star_id": self.star_id,
            "chain_id": self.chain_id,
            "mass": self.mass,
            "luminosity": self.luminosity,
            "core_temp": self.core_temp,
            "magnetic_field": self.magnetic_field,
            "entropy_index": self.entropy_index,
            "fusion_rate": self.fusion_rate,
            "collapse_probability": self.collapse_probability,
        }


def project_stellar_v1(state: StellarState, delta: Mapping[str, float]) -> StellarState:
    """Deterministic stellar physics projection.

    The function is pure and replay-safe: identical `(state, delta)` inputs produce
    identical outputs with no randomness or external state.
    """

    mass_fx = _sum_projection_fixed(state.mass, delta.get("mass", 0.0))
    luminosity_fx = _sum_projection_fixed(state.luminosity, delta.get("luminosity", 0.0))
    entropy_fx = _sum_projection_fixed(state.entropy_index, delta.get("entropy_index", 0.0))
    magnetic_fx = _sum_projection_fixed(state.magnetic_field, delta.get("magnetic_field", 0.0))

    mass_fx = _max_fixed(mass_fx, _FIXED_EPSILON)
    entropy_fx = _max_fixed(entropy_fx, _FIXED_ZERO)

    coefficient_fx = _fusion_coefficient_fixed(mass_fx, entropy_fx)
    core_temp_fx = mass_fx * coefficient_fx
    fusion_fx = luminosity_fx / mass_fx
    collapse_fx = collapse_probability_v1(entropy_fx, magnetic_fx, fusion_fx)

    mass = _fixed_to_float(mass_fx)
    luminosity = _fixed_to_float(luminosity_fx)
    entropy = _fixed_to_float(entropy_fx)
    magnetic = _fixed_to_float(magnetic_fx)
    core_temp = _fixed_to_float(core_temp_fx)
    fusion = _fixed_to_float(fusion_fx)
    collapse_probability = _fixed_to_float(collapse_fx)

    return StellarState(
        star_id=state.star_id,
        chain_id=state.chain_id,
        mass=mass,
        luminosity=luminosity,
        core_temp=core_temp,
        magnetic_field=magnetic,
        entropy_index=entropy,
        fusion_rate=fusion,
        collapse_probability=collapse_probability,
    )


def fusion_coefficient(mass: float, entropy: float) -> float:
    return _fixed_to_float(_fusion_coefficient_fixed(_as_fixed(mass), _as_fixed(entropy)))


def compute_collapse_probability(entropy: float, magnetic: float, fusion: float) -> float:
    return _fixed_to_float(
        collapse_probability_v1(
            _as_fixed(entropy),
            _as_fixed(magnetic),
            _as_fixed(fusion),
        )
    )


def _collapse_probability_fixed(entropy: float, magnetic: float, fusion: float) -> float:
    collapse = collapse_probability_v1(
        _as_fixed(entropy),
        _as_fixed(magnetic),
        _as_fixed(fusion),
    )
    return _fixed_to_float(collapse)


def _as_projection_float(value: object) -> float:
    return _fixed_to_float(_as_fixed(value))


def _sum_projection_fixed(a: object, b: object) -> Fixed64:
    return _as_fixed(a) + _as_fixed(b)


def _max_fixed(a: Fixed64, b: Fixed64) -> Fixed64:
    return a if a >= b else b


def _fusion_coefficient_fixed(mass: Fixed64, entropy: Fixed64) -> Fixed64:
    # Fixed-point approximation that keeps mass influence while avoiding float paths.
    entropy_damping = _FIXED_ONE / (_FIXED_ONE + _max_fixed(entropy, _FIXED_ZERO))
    mass_boost = mass / (mass + _FIXED_ONE)
    return entropy_damping * (_FIXED_ONE + (mass_boost / _FIXED_TEN))


def _as_fixed(value: object) -> Fixed64:
    if isinstance(value, Fixed64):
        return value
    if isinstance(value, int):
        return Fixed64.from_int(value)
    if isinstance(value, float):
        return Fixed64.from_str(_float_to_fixed_str(value))
    if isinstance(value, str):
        return Fixed64.from_str(value)
    raise TypeError(f"unsupported fixed-point value type: {type(value)!r}")


def _float_to_fixed_str(value: float) -> str:
    text = format(value, ".18g")
    try:
        normalized = format(Decimal(text), "f")
    except InvalidOperation as exc:
        raise ValueError(f"invalid float for fixed conversion: {value!r}") from exc
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    if normalized in {"", "-0"}:
        return "0"
    return normalized


def _fixed_to_float(value: Fixed64) -> float:
    return float(value.to_str(18))
