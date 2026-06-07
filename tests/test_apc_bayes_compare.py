from __future__ import annotations

import json
from pathlib import Path

from tools.apc_bayes_compare import run


def test_apc_bayes_compare_emits_prior_sensitivity_and_robustness(tmp_path: Path) -> None:
    paths = run(
        output_dir=tmp_path,
        n_samples=12000,
        seed=20260227,
        run_label="unit",
    )

    latest_json = Path(str(paths["latest_json"]))
    assert latest_json.exists()
    payload = json.loads(latest_json.read_text(encoding="utf-8"))

    matrix = payload.get("prior_sensitivity_matrix", [])
    assert isinstance(matrix, list)
    assert len(matrix) >= 4

    robustness = payload.get("bayes_factor_robustness_band", {})
    assert robustness.get("models_compared", 0) >= 4
    assert "bayes_factor_min" in robustness
    assert "bayes_factor_median" in robustness
    assert "bayes_factor_max" in robustness
    frac = float(robustness.get("support_fraction_for_baseline", 0.0))
    assert 0.0 <= frac <= 1.0
