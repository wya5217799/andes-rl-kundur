"""Prospectively frozen R293 comparison statistics and decision tree.

Controller efficacy and physical/no-harm outcomes are deliberately separate
from evidence-integrity validity.  A poor or non-convergent controller is a
valid negative outcome unless sealing, provenance, action execution, budget,
or statistical implementation is broken.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

PRIMARY_ENDPOINTS = (
    "normalized_sync_loss_hz2",
    "fast_inter_area_iae_hz_s",
)


def hierarchical_ratio_bootstrap(
    left_by_seed: Mapping[int, Mapping[str, float]],
    *,
    right_by_seed: Mapping[int, Mapping[str, float]] | None = None,
    right_deterministic: Mapping[str, float] | None = None,
    resamples: int = 20_000,
    seed: int = 2026080204,
) -> dict[str, Any]:
    """Return two-sided superiority and one-sided non-inferiority bounds."""

    if (right_by_seed is None) == (right_deterministic is None):
        raise ValueError("provide exactly one right comparator")
    if resamples < 100:
        raise ValueError("bootstrap requires at least 100 resamples")
    seed_ids = sorted(left_by_seed)
    if len(seed_ids) < 2:
        raise ValueError("bootstrap requires at least two seeds")
    scenario_ids = sorted(next(iter(left_by_seed.values())))
    expected_scenarios = set(scenario_ids)
    if len(scenario_ids) < 2:
        raise ValueError("bootstrap requires at least two scenarios")
    if any(set(rows) != expected_scenarios for rows in left_by_seed.values()):
        raise ValueError("left seed scenario sets differ")
    left = np.asarray(
        [[left_by_seed[seed_id][name] for name in scenario_ids] for seed_id in seed_ids],
        dtype=float,
    )
    if right_by_seed is not None:
        if set(right_by_seed) != set(seed_ids):
            raise ValueError("matched learned comparators must share seed IDs")
        if any(set(rows) != expected_scenarios for rows in right_by_seed.values()):
            raise ValueError("right seed scenario sets differ")
        right_seeded = np.asarray(
            [[right_by_seed[seed_id][name] for name in scenario_ids] for seed_id in seed_ids],
            dtype=float,
        )
        right_fixed = None
    else:
        assert right_deterministic is not None
        if set(right_deterministic) != expected_scenarios:
            raise ValueError("deterministic comparator scenario set differs")
        right_fixed = np.asarray(
            [right_deterministic[name] for name in scenario_ids], dtype=float
        )
        right_seeded = None
    arrays = [left, right_seeded if right_seeded is not None else right_fixed]
    if any(not np.all(np.isfinite(array)) or np.any(array <= 0.0) for array in arrays):
        raise ValueError("ratio bootstrap inputs must be finite and positive")
    observed_right = (
        float(np.mean(right_seeded))
        if right_seeded is not None
        else float(np.mean(right_fixed))
    )
    point = 100.0 * (float(np.mean(left)) / observed_right - 1.0)
    rng = np.random.default_rng(seed)
    samples = np.empty(resamples, dtype=float)
    seed_count, scenario_count = left.shape
    for index in range(resamples):
        sampled_seeds = rng.integers(0, seed_count, size=seed_count)
        sampled_scenarios = rng.integers(0, scenario_count, size=scenario_count)
        left_mean = float(np.mean(left[np.ix_(sampled_seeds, sampled_scenarios)]))
        if right_seeded is not None:
            right_mean = float(
                np.mean(right_seeded[np.ix_(sampled_seeds, sampled_scenarios)])
            )
        else:
            right_mean = float(np.mean(right_fixed[sampled_scenarios]))
        samples[index] = 100.0 * (left_mean / right_mean - 1.0)
    interval = np.percentile(samples, [2.5, 97.5])
    return {
        "method": "two-level percentile bootstrap over seeds and shared scenarios",
        "lower_is_better": True,
        "seed": seed,
        "resamples": resamples,
        "seed_count": seed_count,
        "scenario_count": scenario_count,
        "right_has_seed_dimension": right_seeded is not None,
        "ratio_of_means_percent": {
            "point": point,
            "percentile_95_interval": [float(interval[0]), float(interval[1])],
            "one_sided_95_upper": float(np.percentile(samples, 95.0)),
        },
        "bootstrap_probability_left_improves": float(np.mean(samples < 0.0)),
    }


def paired_ratio_bootstrap(
    left: Mapping[str, float],
    right: Mapping[str, float],
    *,
    resamples: int = 20_000,
    seed: int = 2026080204,
) -> dict[str, Any]:
    """Paired scenario bootstrap for deterministic classical versus q0."""

    names = sorted(left)
    if set(names) != set(right) or len(names) < 2:
        raise ValueError("paired deterministic scenario sets must match")
    left_array = np.asarray([left[name] for name in names], dtype=float)
    right_array = np.asarray([right[name] for name in names], dtype=float)
    if any(
        not np.all(np.isfinite(array)) or np.any(array <= 0.0)
        for array in (left_array, right_array)
    ):
        raise ValueError("paired ratio inputs must be finite and positive")
    point = 100.0 * (float(np.mean(left_array)) / float(np.mean(right_array)) - 1.0)
    rng = np.random.default_rng(seed)
    samples = np.empty(resamples, dtype=float)
    for index in range(resamples):
        sampled = rng.integers(0, len(names), size=len(names))
        samples[index] = 100.0 * (
            float(np.mean(left_array[sampled])) / float(np.mean(right_array[sampled]))
            - 1.0
        )
    interval = np.percentile(samples, [2.5, 97.5])
    return {
        "method": "paired scenario percentile bootstrap",
        "lower_is_better": True,
        "seed": seed,
        "resamples": resamples,
        "scenario_count": len(names),
        "ratio_of_means_percent": {
            "point": point,
            "percentile_95_interval": [float(interval[0]), float(interval[1])],
        },
        "bootstrap_probability_left_improves": float(np.mean(samples < 0.0)),
    }


def _material(contrast: Mapping[str, Any], endpoint: str) -> bool:
    effect = contrast[endpoint]["ratio_of_means_percent"]
    return bool(effect["point"] <= -2.0 and effect["percentile_95_interval"][1] < 0.0)


def _noninferior(contrast: Mapping[str, Any], endpoint: str) -> bool:
    effect = contrast[endpoint]["ratio_of_means_percent"]
    return bool(effect["one_sided_95_upper"] < 5.0)


def classify_r293(
    *,
    integrity_valid: bool,
    distributed_vs_classical: Mapping[str, Any],
    central_vs_classical: Mapping[str, Any],
    distributed_vs_central: Mapping[str, Any],
    distributed_directional_seed_count: int,
    distributed_noninferior_seed_count: int,
    distributed_positive_claim_guards: Mapping[str, bool],
    central_positive_claim_guards: Mapping[str, bool],
) -> dict[str, Any]:
    """Apply the frozen R293 efficacy, NI, and integrity decision tree."""

    if not integrity_valid:
        return {
            "classification": "INTEGRITY-INVALID",
            "reason": "one or more sealing, provenance, budget, action-execution, or statistical implementation contracts failed",
        }
    distributed_effective = all(
        _material(distributed_vs_classical, endpoint) for endpoint in PRIMARY_ENDPOINTS
    ) and distributed_directional_seed_count >= 3
    central_effective = all(
        _material(central_vs_classical, endpoint) for endpoint in PRIMARY_ENDPOINTS
    )
    distributed_superior = all(
        _material(distributed_vs_central, endpoint) for endpoint in PRIMARY_ENDPOINTS
    )
    distributed_noninferior = all(
        _noninferior(distributed_vs_central, endpoint) for endpoint in PRIMARY_ENDPOINTS
    ) and distributed_noninferior_seed_count >= 3
    distributed_guards_pass = bool(distributed_positive_claim_guards) and all(
        distributed_positive_claim_guards.values()
    )
    central_guards_pass = bool(central_positive_claim_guards) and all(
        central_positive_claim_guards.values()
    )
    gates = {
        "distributed_vs_classical_both_primary": distributed_effective,
        "central_vs_classical_both_primary": central_effective,
        "distributed_vs_central_both_primary": distributed_superior,
        "distributed_vs_central_noninferior_both_primary": distributed_noninferior,
        "distributed_directional_seed_count": distributed_directional_seed_count,
        "distributed_noninferior_seed_count": distributed_noninferior_seed_count,
        "distributed_positive_claim_guards_pass": distributed_guards_pass,
        "central_positive_claim_guards_pass": central_guards_pass,
    }
    if distributed_effective and not distributed_guards_pass:
        classification = "DISTRIBUTED-EFFECTIVE-GUARD-FAIL"
        reason = "distributed efficacy clears but one or more physical, tail, storage, or controller-outcome guards fail"
    elif distributed_effective and distributed_superior:
        classification = "DISTRIBUTED-SUPERIOR"
        reason = "distributed residual materially beats the classical and centralized comparators on both primary endpoints"
    elif distributed_effective and distributed_noninferior:
        classification = "DISTRIBUTED-NONINFERIOR-LOCAL"
        reason = "distributed residual beats the classical comparator and is non-inferior to centralized control while using endpoint-neighbour information only"
    elif distributed_effective:
        classification = "DISTRIBUTED-EFFECTIVE-CENTRALIZED-SUPERIOR"
        reason = "distributed residual adds value over classical control but exceeds the frozen centralized non-inferiority margin"
    elif central_effective and not central_guards_pass:
        classification = "CENTRALIZED-EFFECTIVE-GUARD-FAIL"
        reason = "centralized efficacy clears but one or more positive-claim guards fail"
    elif central_effective:
        classification = "CENTRALIZED-SUPERIOR"
        reason = "only centralized residual control has guarded incremental value over the classical comparator"
    else:
        classification = "NO-NEURAL-INCREMENT"
        reason = "neither learned residual architecture clears both primary gates versus the tuned classical edge controller"
    return {
        "classification": classification,
        "reason": reason,
        "efficacy_and_guard_gates": gates,
    }
