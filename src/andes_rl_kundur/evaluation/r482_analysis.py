"""Four-test boundary analysis and Phase-3 pair for the R482 corrected-card
learning re-verification + all-fresh source factorial.

Motivation: the frozen n=26 design (source_factorial_power_plan.json) replaces
the n=6 two-factor U2 analysis. This module owns the round-bound inference
layer only: the four registered materiality tests (exact one-sided Wilcoxon
signed-rank at log(1.10), Holm 4, FWER 0.05), the registered symmetry check
with the fixed-seed sign-flip fallback, the Phase-3 trade-off pair (family of
2, FWER 0.05), and classification precedence. Record reading, integrity
collection, and file I/O stay in the round runner.

Usage: import the pure helpers; the runner calls boundary_test_rows(),
phase3_analysis(), and classify_r482() from its aggregate() command.

Failure modes: zero differences or tied absolute ranks invalidate the exact
Wilcoxon row (exact_valid=False; the permutation test becomes primary). Any
missing/duplicate/nonpositive factorial cell invalidates the whole seed
upstream in source_factorial_design.seed_effects. No asymptotic or
available-case fallback exists.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from andes_rl_kundur.evaluation.source_factorial_design import (
    exact_signed_rank_p_one_sided,
    holm_decisions,
)

REGISTERED_EFFECTS = (
    "actor_main",
    "critic_main",
    "actor_x_critic",
    "critic_x_reward",
)
MAIN_EFFECTS = ("actor_main", "critic_main")
INTERACTIONS = ("actor_x_critic", "critic_x_reward")
SYMMETRY_SKEW_THRESHOLD = 1.0
SIGNFLIP_DRAWS = 1_000_000
SIGNFLIP_RNG_SEED = 20260825
SIGNFLIP_CHUNK = 10_000
PHASE3_FAMILY_ALPHA = 0.05


def symmetry_skew(values: Sequence[float], null: float = 0.0) -> float:
    """Fisher-Pearson moment skewness coefficient of the null-centred effects.

    g1 = m3 / m2**1.5 with m_k = mean((x - mean(x))**k); a symmetric
    location-shift distribution has g1 = 0 and the Wilcoxon signed-rank test
    matches the mean estimand. |g1| above the registered threshold 1.0 marks
    a grossly skewed effect vector and switches the primary test to the
    sign-flip permutation test (exchangeability only).
    """
    centred = np.asarray(list(values), dtype=float) - float(null)
    if centred.size < 3 or not np.all(np.isfinite(centred)):
        raise ValueError("symmetry skew requires >= 3 finite values")
    deviations = centred - float(np.mean(centred))
    second = float(np.mean(deviations**2))
    if second == 0.0:
        return math.inf if float(np.mean(deviations**3)) != 0.0 else 0.0
    third = float(np.mean(deviations**3))
    return third / (second**1.5)


def signflip_p_one_sided_mc(
    values: Sequence[float],
    null: float,
    draws: int,
    rng_seed: int,
) -> tuple[float, float]:
    """Fixed-seed Monte Carlo sign-flip p (upper tail) with its MC standard error."""
    centred = np.asarray(list(values), dtype=float) - float(null)
    count = centred.size
    if count < 1 or not np.all(np.isfinite(centred)):
        raise ValueError("sign-flip input must be a non-empty finite vector")
    if draws < 1000:
        raise ValueError("draws must be >= 1000")
    observed = float(np.mean(centred))
    rng = np.random.default_rng(rng_seed)
    successes = 0
    for start in range(0, draws, SIGNFLIP_CHUNK):
        batch = min(SIGNFLIP_CHUNK, draws - start)
        signs = rng.integers(0, 2, size=(batch, count)) * 2 - 1
        means = signs @ centred / count
        successes += int(np.count_nonzero(means >= observed))
    p_value = successes / draws
    se = math.sqrt(p_value * (1.0 - p_value) / draws)
    return float(p_value), float(se)


def boundary_test_rows(
    seed_effects: Mapping[str, Mapping[int, float]],
    null_log: float,
) -> dict[str, dict[str, Any]]:
    """One row per registered hypothesis: exact Wilcoxon + symmetry + fallback."""
    if set(seed_effects) != set(REGISTERED_EFFECTS):
        raise ValueError(
            "seed_effects must contain exactly the four registered hypotheses"
        )
    rows: dict[str, dict[str, Any]] = {}
    for name in REGISTERED_EFFECTS:
        values = [
            float(seed_effects[name][seed])
            for seed in sorted(seed_effects[name])
        ]
        exact_p: float | None
        exact_valid = True
        try:
            exact_p = exact_signed_rank_p_one_sided(values, float(null_log))
        except ValueError:
            exact_p = None
            exact_valid = False
        skew = symmetry_skew(values, float(null_log))
        flip_p, flip_se = signflip_p_one_sided_mc(
            values, float(null_log), SIGNFLIP_DRAWS, SIGNFLIP_RNG_SEED
        )
        primary = (
            "signflip"
            if (not exact_valid or skew > SYMMETRY_SKEW_THRESHOLD)
            else "wilcoxon"
        )
        rows[name] = {
            "paired_log_effects": values,
            "mean_log_effect": float(np.mean(values)),
            "geometric_improvement": float(math.exp(float(np.mean(values))) - 1.0),
            "materiality_log": float(null_log),
            "wilcoxon_p_one_sided": exact_p,
            "wilcoxon_exact_valid": exact_valid,
            "symmetry_skew": skew,
            "symmetry_threshold": SYMMETRY_SKEW_THRESHOLD,
            "signflip_p_one_sided": flip_p,
            "signflip_p_mc_se": flip_se,
            "signflip_draws": SIGNFLIP_DRAWS,
            "signflip_rng_seed": SIGNFLIP_RNG_SEED,
            "primary_test": primary,
            "p_one_sided": flip_p if primary == "signflip" else exact_p,
            "direction_count_positive": int(sum(value > 0 for value in values)),
            "seed_min": float(np.min(values)),
            "seed_median": float(np.median(values)),
        }
    return rows


def phase3_analysis(
    endpoint_log_ratios: Sequence[float],
    stress_diffs: Sequence[float],
) -> dict[str, Any]:
    """Phase-3 trade-off pair: two one-sided tests at zero, Holm over 2.

    endpoint_log_ratios: per-seed log[L(RMS)/L(SAC)] on final checkpoints;
    the frozen direction is positive (penalty regresses endpoints).
    stress_diffs: per-seed (SAC stress - RMS stress); the frozen direction is
    positive (penalty lowers action stress).
    """
    if len(endpoint_log_ratios) != len(stress_diffs) or len(endpoint_log_ratios) < 2:
        raise ValueError("phase-3 inputs must be paired vectors of equal length >= 2")

    def one_sided(values: Sequence[float]) -> dict[str, Any]:
        signed = [float(value) for value in values]
        exact_p: float | None
        exact_valid = True
        try:
            exact_p = exact_signed_rank_p_one_sided(signed, 0.0)
        except ValueError:
            exact_p = None
            exact_valid = False
        flip_p, flip_se = signflip_p_one_sided_mc(
            signed, 0.0, SIGNFLIP_DRAWS, SIGNFLIP_RNG_SEED
        )
        primary = "signflip" if not exact_valid else "wilcoxon"
        return {
            "paired_values": signed,
            "wilcoxon_p_one_sided": exact_p,
            "wilcoxon_exact_valid": exact_valid,
            "signflip_p_one_sided": flip_p,
            "signflip_p_mc_se": flip_se,
            "primary_test": primary,
            "p_one_sided": flip_p if primary == "signflip" else exact_p,
        }

    rows: dict[str, Any] = {
        "endpoint_regression": one_sided(list(endpoint_log_ratios)),
        "action_stress_improvement": one_sided(list(stress_diffs)),
    }
    ordered = sorted(rows, key=lambda key: rows[key]["p_one_sided"])
    prior_pass = True
    for rank, key in enumerate(ordered):
        threshold = PHASE3_FAMILY_ALPHA / (2 - rank)
        rows[key]["holm_threshold"] = float(threshold)
        rows[key]["holm_reject"] = bool(
            prior_pass and rows[key]["p_one_sided"] <= threshold
        )
        prior_pass = rows[key]["holm_reject"]
    both = all(rows[key]["holm_reject"] for key in rows)
    rows["outcome"] = (
        "PHASE3-TRADE-OFF-REPRODUCED"
        if both
        else "PHASE3-TRADE-OFF-NOT-ESTABLISHED"
    )
    return rows


def classify_r482(
    *,
    design_valid: bool,
    missing_shards: Sequence[str],
    integrity_errors: Sequence[str],
    dynamics_stable: bool,
    factorial_rows: Mapping[str, Mapping[str, Any]],
    phase3_rows: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Classification precedence: design -> execution -> integrity -> effect."""
    execution_complete = not missing_shards
    integrity_pass = not integrity_errors
    validity_pass = bool(design_valid and execution_complete and integrity_pass)
    holm: dict[str, dict[str, Any]] = {}
    if factorial_rows and validity_pass:
        primary = {name: row["p_one_sided"] for name, row in factorial_rows.items()}
        holm = holm_decisions(primary)
    main_established = any(
        holm.get(name, {}).get("reject") for name in MAIN_EFFECTS
    )
    interaction_established = any(
        holm.get(name, {}).get("reject") for name in INTERACTIONS
    )
    if not design_valid:
        verdict = "DESIGN-INVALID"
    elif not execution_complete:
        verdict = "EXECUTION-INCOMPLETE"
    elif not integrity_pass:
        verdict = "INTEGRITY-INVALID"
    elif main_established and interaction_established:
        verdict = "MATERIAL-MAIN-EFFECT+MATERIAL-INTERACTION"
    elif main_established:
        verdict = "MATERIAL-MAIN-EFFECT"
    elif interaction_established:
        verdict = "MATERIAL-INTERACTION"
    else:
        verdict = "MATERIAL-EFFECT-NOT-ESTABLISHED"
    if validity_pass:
        material_effect = (
            "MAIN-EFFECT"
            if main_established
            else "INTERACTION"
            if interaction_established
            else "NOT_ESTABLISHED"
        )
        phase3_outcome = (
            phase3_rows.get("outcome")
            if isinstance(phase3_rows, dict)
            else "NOT_TESTED"
        )
    else:
        material_effect = "NOT_TESTED"
        phase3_outcome = "NOT_TESTED"
    return {
        "design": "VALID" if design_valid else "INVALID",
        "execution": "COMPLETE" if execution_complete else "INCOMPLETE",
        "integrity": "PASS" if integrity_pass else "FAIL",
        "training_dynamics": (
            "STABLE" if dynamics_stable else "UNSTABLE"
        ) if validity_pass else "NOT_ASSESSED",
        "material_effect": material_effect,
        "phase3_outcome": phase3_outcome,
        "verdict": verdict,
    }
