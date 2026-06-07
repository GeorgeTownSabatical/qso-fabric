from __future__ import annotations

from solis.projectors.instability_engine import assess_instability
from solis.projectors.stellar_projector_v1 import StellarState, compute_collapse_probability


def test_collapse_probability_is_bounded() -> None:
    assert 0.0 <= compute_collapse_probability(entropy=100.0, magnetic=-5.0, fusion=100.0) <= 1.0
    assert 0.0 <= compute_collapse_probability(entropy=-10.0, magnetic=2.0, fusion=-3.0) <= 1.0


def test_instability_threshold_labels() -> None:
    stable = StellarState(
        star_id="s", chain_id="c", mass=1.0, luminosity=1.0, core_temp=1.0, magnetic_field=1.0, entropy_index=0.02, fusion_rate=0.8
    )
    warning = StellarState(
        star_id="s", chain_id="c", mass=1.0, luminosity=1.0, core_temp=1.0, magnetic_field=0.7, entropy_index=0.7, fusion_rate=0.8
    )
    critical = StellarState(
        star_id="s", chain_id="c", mass=1.0, luminosity=1.0, core_temp=1.0, magnetic_field=0.2, entropy_index=1.1, fusion_rate=1.2, collapse_probability=0.95
    )

    assert assess_instability(stable).phase == "stable"
    assert assess_instability(warning).phase in {"warning", "critical"}
    assert assess_instability(critical).phase == "critical"
    assert assess_instability(critical).collapse_imminent is True
