from __future__ import annotations

from solis.config import SolisConfig
from solis.services.solis_constellation_service import SolisConstellationService
from solis.services.solis_star_service import SolisStarService


def test_entanglement_propagation_and_cascade_detection() -> None:
    config = SolisConfig(cascade_threshold=0.35)
    stars = SolisStarService(config=config)
    constellation = SolisConstellationService(star_service=stars, config=config)

    stars.create_star(star_id="alpha", chain_id="public")
    stars.create_star(star_id="beta", chain_id="public")

    constellation.create_constellation(domain="public", star_uris=["alpha", "beta"])

    beta_before = stars.get_star("beta")["state_layer"]["mass"]
    propagation = constellation.propagate_from_star(
        domain_or_uri="public",
        source_star_uri="alpha",
        event_type="token_mint",
        magnitude=2.0,
    )

    beta_after = stars.get_star("beta")["state_layer"]["mass"]
    assert propagation["impacted_stars"] == ["qso://solis.star.beta"]
    assert beta_after > beta_before

    stars.patch_star(star_uri_or_id="alpha", delta={"entropy_index": 1.5, "magnetic_field": -0.7, "luminosity": 4.0})
    stars.patch_star(star_uri_or_id="beta", delta={"entropy_index": 1.4, "magnetic_field": -0.6, "luminosity": 4.0})

    summary = constellation.recompute_constellation("public")
    assert summary["contagion_index"] >= 0.0
    assert summary["cascade_detected"] is True
