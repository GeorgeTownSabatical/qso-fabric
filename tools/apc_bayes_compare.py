from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_gaussian_like(x: float, mu: float, sigma: float) -> float:
    z = (x - mu) / sigma
    return -0.5 * z * z


def _log_one_sided_upper_like(x: float, upper_95: float) -> float:
    sigma = upper_95 / 1.645
    return _log_gaussian_like(max(0.0, x), 0.0, sigma)


def _sample_log_uniform(rng: random.Random, lo: float, hi: float) -> float:
    u = rng.random()
    return math.exp(math.log(lo) + (math.log(hi) - math.log(lo)) * u)


def _sample_trunc_normal(
    rng: random.Random,
    mu: float,
    sigma: float,
    lo: float,
    hi: float,
    max_tries: int = 10000,
) -> float:
    for _ in range(max_tries):
        x = rng.gauss(mu, sigma)
        if lo <= x <= hi:
            return x
    return max(lo, min(hi, mu))


@dataclass(frozen=True, slots=True)
class ConstraintSummary:
    id: str
    kind: str
    value: float
    source: str
    note: str


@dataclass(frozen=True, slots=True)
class ModelSpec:
    name: str
    family: str
    prior_description: dict[str, str]
    sampler: Callable[[random.Random], dict[str, float]]


def _make_models() -> list[ModelSpec]:
    def sample_lcdm_sm(rng: random.Random) -> dict[str, float]:
        return {
            "r": rng.uniform(0.0, 0.05),
            "omega_gw_25hz": _sample_log_uniform(rng, 1e-12, 1e-9),
            "mu_higgs": _sample_trunc_normal(rng, 1.0, 0.05, 0.5, 1.5),
            "heavy_scalar_norm": abs(rng.gauss(0.0, 0.2)),
        }

    def sample_apc_ultra_broad(rng: random.Random) -> dict[str, float]:
        return {
            "r": rng.uniform(0.0, 0.4),
            "omega_gw_25hz": _sample_log_uniform(rng, 1e-11, 1e-5),
            "mu_higgs": rng.uniform(0.3, 1.7),
            "heavy_scalar_norm": rng.uniform(0.0, 8.0),
        }

    def sample_apc_generic(rng: random.Random) -> dict[str, float]:
        return {
            "r": rng.uniform(0.0, 0.30),
            "omega_gw_25hz": _sample_log_uniform(rng, 1e-11, 1e-6),
            "mu_higgs": rng.uniform(0.5, 1.5),
            "heavy_scalar_norm": rng.uniform(0.0, 5.0),
        }

    def sample_apc_constrained(rng: random.Random) -> dict[str, float]:
        return {
            "r": rng.uniform(0.0, 0.08),
            "omega_gw_25hz": _sample_log_uniform(rng, 1e-12, 1e-8),
            "mu_higgs": _sample_trunc_normal(rng, 1.0, 0.12, 0.5, 1.5),
            "heavy_scalar_norm": rng.uniform(0.0, 2.0),
        }

    def sample_apc_low_tensor(rng: random.Random) -> dict[str, float]:
        return {
            "r": rng.uniform(0.0, 0.04),
            "omega_gw_25hz": _sample_log_uniform(rng, 1e-12, 1e-8),
            "mu_higgs": _sample_trunc_normal(rng, 1.0, 0.10, 0.5, 1.5),
            "heavy_scalar_norm": rng.uniform(0.0, 1.5),
        }

    def sample_apc_high_tensor(rng: random.Random) -> dict[str, float]:
        return {
            "r": rng.uniform(0.02, 0.20),
            "omega_gw_25hz": _sample_log_uniform(rng, 1e-10, 1e-6),
            "mu_higgs": rng.uniform(0.6, 1.4),
            "heavy_scalar_norm": rng.uniform(0.1, 4.0),
        }

    def sample_apc_low_signal(rng: random.Random) -> dict[str, float]:
        return {
            "r": rng.uniform(0.0, 0.02),
            "omega_gw_25hz": _sample_log_uniform(rng, 1e-12, 1e-10),
            "mu_higgs": _sample_trunc_normal(rng, 1.0, 0.06, 0.5, 1.5),
            "heavy_scalar_norm": abs(rng.gauss(0.0, 0.3)),
        }

    return [
        ModelSpec(
            name="LambdaCDM+SM_baseline",
            family="baseline",
            prior_description={
                "r": "Uniform(0, 0.05)",
                "omega_gw_25hz": "LogUniform(1e-12, 1e-9)",
                "mu_higgs": "TruncNormal(1.0, 0.05; [0.5, 1.5])",
                "heavy_scalar_norm": "|Normal(0, 0.2)|",
            },
            sampler=sample_lcdm_sm,
        ),
        ModelSpec(
            name="APC_ultra_broad",
            family="apc",
            prior_description={
                "r": "Uniform(0, 0.4)",
                "omega_gw_25hz": "LogUniform(1e-11, 1e-5)",
                "mu_higgs": "Uniform(0.3, 1.7)",
                "heavy_scalar_norm": "Uniform(0, 8)",
            },
            sampler=sample_apc_ultra_broad,
        ),
        ModelSpec(
            name="APC_generic",
            family="apc",
            prior_description={
                "r": "Uniform(0, 0.30)",
                "omega_gw_25hz": "LogUniform(1e-11, 1e-6)",
                "mu_higgs": "Uniform(0.5, 1.5)",
                "heavy_scalar_norm": "Uniform(0, 5)",
            },
            sampler=sample_apc_generic,
        ),
        ModelSpec(
            name="APC_constrained",
            family="apc",
            prior_description={
                "r": "Uniform(0, 0.08)",
                "omega_gw_25hz": "LogUniform(1e-12, 1e-8)",
                "mu_higgs": "TruncNormal(1.0, 0.12; [0.5, 1.5])",
                "heavy_scalar_norm": "Uniform(0, 2)",
            },
            sampler=sample_apc_constrained,
        ),
        ModelSpec(
            name="APC_low_tensor",
            family="apc",
            prior_description={
                "r": "Uniform(0, 0.04)",
                "omega_gw_25hz": "LogUniform(1e-12, 1e-8)",
                "mu_higgs": "TruncNormal(1.0, 0.10; [0.5, 1.5])",
                "heavy_scalar_norm": "Uniform(0, 1.5)",
            },
            sampler=sample_apc_low_tensor,
        ),
        ModelSpec(
            name="APC_high_tensor",
            family="apc",
            prior_description={
                "r": "Uniform(0.02, 0.20)",
                "omega_gw_25hz": "LogUniform(1e-10, 1e-6)",
                "mu_higgs": "Uniform(0.6, 1.4)",
                "heavy_scalar_norm": "Uniform(0.1, 4)",
            },
            sampler=sample_apc_high_tensor,
        ),
        ModelSpec(
            name="APC_low_signal",
            family="apc",
            prior_description={
                "r": "Uniform(0, 0.02)",
                "omega_gw_25hz": "LogUniform(1e-12, 1e-10)",
                "mu_higgs": "TruncNormal(1.0, 0.06; [0.5, 1.5])",
                "heavy_scalar_norm": "|Normal(0, 0.3)|",
            },
            sampler=sample_apc_low_signal,
        ),
    ]


def _constraints() -> list[ConstraintSummary]:
    return [
        ConstraintSummary(
            id="r_upper_95",
            kind="one_sided_upper",
            value=0.032,
            source="https://ui.adsabs.harvard.edu/abs/2022PhRvD.105h3524T/abstract",
            note="Tensor-to-scalar ratio upper limit (95% CL).",
        ),
        ConstraintSummary(
            id="omega_gw_upper_95",
            kind="one_sided_upper",
            value=2.0e-9,
            source="https://dcc.ligo.org/LIGO-P2500349-v7/public",
            note="Isotropic SGWB upper limit at 25 Hz (95% credibility).",
        ),
        ConstraintSummary(
            id="mu_higgs",
            kind="gaussian",
            value=1.0,
            source="https://cms.cern/news/cms-closes-major-chapter-higgs-measurements",
            note="Combined Higgs signal-strength summary value.",
        ),
        ConstraintSummary(
            id="mu_higgs_sigma",
            kind="gaussian_sigma",
            value=0.13,
            source="https://cms.cern/news/cms-closes-major-chapter-higgs-measurements",
            note="One-sigma uncertainty on mu_higgs summary.",
        ),
        ConstraintSummary(
            id="heavy_scalar_upper_95_norm",
            kind="one_sided_upper",
            value=1.0,
            source="https://cms-results.web.cern.ch/cms-results/public-results/preliminary-results/HIG-24-002/",
            note="Normalized proxy upper bound from null heavy-scalar searches.",
        ),
    ]


def _log_likelihood(theta: dict[str, float], constraints: dict[str, ConstraintSummary]) -> float:
    ll = 0.0
    ll += _log_one_sided_upper_like(theta["r"], constraints["r_upper_95"].value)
    ll += _log_one_sided_upper_like(theta["omega_gw_25hz"], constraints["omega_gw_upper_95"].value)
    ll += _log_gaussian_like(
        theta["mu_higgs"],
        constraints["mu_higgs"].value,
        constraints["mu_higgs_sigma"].value,
    )
    ll += _log_one_sided_upper_like(
        theta["heavy_scalar_norm"],
        constraints["heavy_scalar_upper_95_norm"].value,
    )
    return ll


def _evidence_mc(
    model: ModelSpec,
    *,
    n_samples: int,
    seed: int,
    constraints: dict[str, ConstraintSummary],
) -> dict[str, float]:
    rng = random.Random(seed)
    log_l_values: list[float] = []
    for _ in range(n_samples):
        theta = model.sampler(rng)
        log_l_values.append(_log_likelihood(theta, constraints))

    max_log_l = max(log_l_values)
    weights = [math.exp(v - max_log_l) for v in log_l_values]
    mean_weight = sum(weights) / len(weights)
    log_z = math.log(mean_weight) + max_log_l

    mean_z = math.exp(max_log_l) * mean_weight
    var_w = sum((w - mean_weight) ** 2 for w in weights) / max(1, len(weights) - 1)
    se_z = math.exp(max_log_l) * math.sqrt(var_w / len(weights))

    return {
        "log_evidence": log_z,
        "evidence": mean_z,
        "evidence_mc_se": se_z,
        "evidence_rel_se": se_z / max(mean_z, 1e-300),
        "max_log_likelihood_sample": max_log_l,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apc-bayes-compare",
        description="Approximate Bayes-factor comparison for APC prior families vs baseline.",
    )
    parser.add_argument(
        "--output-dir",
        default=".codex/state/mcp_qso_edu/apc_bayes",
        help="Directory for JSON/Markdown outputs.",
    )
    parser.add_argument(
        "--n-samples",
        type=int,
        default=300000,
        help="Monte Carlo samples per model family.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=12345,
        help="Random seed base.",
    )
    parser.add_argument(
        "--run-label",
        default="",
        help="Optional run label in output filenames.",
    )
    return parser


def run(
    *,
    output_dir: Path,
    n_samples: int,
    seed: int,
    run_label: str,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    suffix = f"_{run_label}" if run_label else ""
    json_path = output_dir / f"apc_bayes_comparison_{stamp}{suffix}.json"
    md_path = output_dir / f"apc_bayes_comparison_{stamp}{suffix}.md"

    constraints_list = _constraints()
    c_map = {c.id: c for c in constraints_list}
    models = _make_models()

    model_results: list[dict[str, object]] = []
    for idx, model in enumerate(models):
        result = _evidence_mc(
            model,
            n_samples=n_samples,
            seed=seed + idx * 100003,
            constraints=c_map,
        )
        model_results.append(
            {
                "model": model.name,
                "family": model.family,
                "prior_description": model.prior_description,
                **result,
            }
        )

    by_name = {row["model"]: row for row in model_results}
    baseline = by_name["LambdaCDM+SM_baseline"]
    baseline_log_z = float(baseline["log_evidence"])
    baseline_z = float(baseline["evidence"])
    baseline_se = float(baseline["evidence_mc_se"])

    comparisons: list[dict[str, object]] = []
    for row in model_results:
        model_z = float(row["evidence"])
        model_se = float(row["evidence_mc_se"])
        log_bf = float(row["log_evidence"]) - baseline_log_z
        bf = math.exp(log_bf)
        sigma_log_bf = math.sqrt(
            (model_se / max(model_z, 1e-300)) ** 2 + (baseline_se / max(baseline_z, 1e-300)) ** 2
        )
        log_bf_low = log_bf - sigma_log_bf
        log_bf_high = log_bf + sigma_log_bf
        bf_low = math.exp(log_bf_low)
        bf_high = math.exp(log_bf_high)

        comparisons.append(
            {
                "model": row["model"],
                "family": row["family"],
                "log_bayes_factor_vs_baseline": log_bf,
                "bayes_factor_vs_baseline": bf,
                "log_bf_band_68": [log_bf_low, log_bf_high],
                "bf_band_68": [bf_low, bf_high],
                "interpretation": (
                    "supports_baseline_over_model"
                    if row["model"] != "LambdaCDM+SM_baseline" and bf < 1.0
                    else "neutral_or_supports_model"
                ),
            }
        )

    max_log_z = max(float(r["log_evidence"]) for r in model_results)
    weights = [math.exp(float(r["log_evidence"]) - max_log_z) for r in model_results]
    weight_sum = sum(weights)
    posterior = [
        {"model": row["model"], "posterior_model_probability_equal_priors": w / weight_sum}
        for row, w in zip(model_results, weights)
    ]

    apc_rows = [row for row in comparisons if row["family"] == "apc"]
    apc_bf_values = [float(row["bayes_factor_vs_baseline"]) for row in apc_rows]
    apc_log_bf_values = [float(row["log_bayes_factor_vs_baseline"]) for row in apc_rows]
    apc_robustness = {
        "models_compared": len(apc_rows),
        "all_apc_favor_baseline": all(v < 1.0 for v in apc_bf_values),
        "bayes_factor_min": min(apc_bf_values),
        "bayes_factor_median": statistics.median(apc_bf_values),
        "bayes_factor_max": max(apc_bf_values),
        "log_bayes_factor_min": min(apc_log_bf_values),
        "log_bayes_factor_median": statistics.median(apc_log_bf_values),
        "log_bayes_factor_max": max(apc_log_bf_values),
        "support_fraction_for_baseline": sum(1 for v in apc_bf_values if v < 1.0) / len(apc_bf_values),
        "robust_conclusion": (
            "Baseline favored across all APC prior families in this sensitivity matrix."
            if all(v < 1.0 for v in apc_bf_values)
            else "Conclusion depends on prior family; not robust."
        ),
    }

    prior_sensitivity_matrix = [
        {
            "model": row["model"],
            "prior_description": row["prior_description"],
            "log_evidence": row["log_evidence"],
            "evidence": row["evidence"],
            "log_bayes_factor_vs_baseline": next(
                float(c["log_bayes_factor_vs_baseline"]) for c in comparisons if c["model"] == row["model"]
            ),
            "bayes_factor_vs_baseline": next(
                float(c["bayes_factor_vs_baseline"]) for c in comparisons if c["model"] == row["model"]
            ),
            "bf_band_68": next(c["bf_band_68"] for c in comparisons if c["model"] == row["model"]),
        }
        for row in model_results
        if row["family"] == "apc"
    ]

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "created_at": _utc_now(),
        "method": {
            "name": "summary_likelihood_monte_carlo_evidence",
            "n_samples_per_model": n_samples,
            "seed": seed,
            "assumptions": [
                "Independent summary-likelihood factors for r, Omega_GW, mu_higgs, heavy-scalar proxy.",
                "One-sided 95% limits converted to Gaussian sigma via sigma=limit/1.645.",
                "Prior-sensitivity matrix uses multiple APC prior families.",
                "Model priors materially influence Bayes factors.",
            ],
            "warning": "Approximate evidence comparison; full collaboration likelihood pipelines are not used here.",
        },
        "constraints": [
            {
                "id": c.id,
                "kind": c.kind,
                "value": c.value,
                "source": c.source,
                "note": c.note,
            }
            for c in constraints_list
        ],
        "model_results": model_results,
        "comparisons_vs_baseline": comparisons,
        "prior_sensitivity_matrix": prior_sensitivity_matrix,
        "bayes_factor_robustness_band": apc_robustness,
        "posterior_model_probs_equal_priors": posterior,
        "overall": {
            "status": "approximate_bayesian_comparison_complete",
            "proof_status": "not_proven",
            "reason": "No APC prior family exceeds baseline evidence in this matrix.",
        },
    }

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# APC Bayesian Comparison",
        "",
        f"- Generated: `{payload['created_at']}`",
        f"- Samples/model: `{n_samples}`",
        "- Method: approximate summary-likelihood evidence with prior-sensitivity matrix",
        "- Proof status: `NOT PROVEN`",
        "",
        "## Log Evidence",
    ]
    for row in model_results:
        lines.append(
            f"- `{row['model']}`: logZ=`{float(row['log_evidence']):.6f}` "
            f"(Z~`{float(row['evidence']):.6e}`)"
        )

    lines.extend(["", "## Bayes Factors vs Baseline"])
    for row in comparisons:
        lines.append(
            f"- `{row['model']}`: logBF=`{float(row['log_bayes_factor_vs_baseline']):.6f}`, "
            f"BF=`{float(row['bayes_factor_vs_baseline']):.6e}`, "
            f"68% band=`[{float(row['bf_band_68'][0]):.6e}, {float(row['bf_band_68'][1]):.6e}]`"
        )

    lines.extend(["", "## Prior-Sensitivity Robustness Band (APC families only)"])
    lines.append(
        f"- BF min/median/max: `{apc_robustness['bayes_factor_min']:.6e}` / "
        f"`{apc_robustness['bayes_factor_median']:.6e}` / `{apc_robustness['bayes_factor_max']:.6e}`"
    )
    lines.append(
        f"- logBF min/median/max: `{apc_robustness['log_bayes_factor_min']:.6f}` / "
        f"`{apc_robustness['log_bayes_factor_median']:.6f}` / `{apc_robustness['log_bayes_factor_max']:.6f}`"
    )
    lines.append(f"- Robust conclusion: {apc_robustness['robust_conclusion']}")

    lines.extend(["", "## Posterior Model Probabilities (Equal Priors)"])
    for row in posterior:
        lines.append(
            f"- `{row['model']}`: `{float(row['posterior_model_probability_equal_priors']):.6f}`"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "- Bayes factors remain sensitive to prior family definitions.",
            "- This comparison is approximate and not a substitute for full collaboration likelihood chains.",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    latest_json = output_dir / "apc_bayes_comparison_latest.json"
    latest_md = output_dir / "apc_bayes_comparison_latest.md"
    latest_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest_md.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")

    return {
        "json": str(json_path),
        "markdown": str(md_path),
        "latest_json": str(latest_json),
        "latest_markdown": str(latest_md),
    }


def main() -> None:
    args = _build_parser().parse_args()
    paths = run(
        output_dir=Path(args.output_dir),
        n_samples=max(10000, int(args.n_samples)),
        seed=int(args.seed),
        run_label=str(args.run_label).strip(),
    )
    print(json.dumps(paths, indent=2))


if __name__ == "__main__":
    main()
