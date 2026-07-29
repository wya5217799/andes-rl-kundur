"""Reviewer-driven identifiability diagnostics for R279.

The functions in this module are deliberately read-only: they decompose already
sealed R275/R277/R278 traces and do not relabel any historical decision.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

ACTIVE_STEPS = 15
AREA_COUNT = 4


def _frequency_modes(
    record: Mapping[str, Any],
    *,
    steps: int | None = None,
) -> tuple[np.ndarray, np.ndarray, float]:
    traces = record.get("traces")
    if not isinstance(traces, list) or not traces:
        raise ValueError("trace record must contain non-empty traces")
    selected = traces if steps is None else traces[:steps]
    if steps is not None and len(selected) != steps:
        raise ValueError(f"trace has fewer than {steps} requested steps")
    frequency = np.asarray(
        [row["delta_f_physical_hz"] for row in selected],
        dtype=float,
    )
    time = np.asarray([row["t"] for row in selected], dtype=float)
    if frequency.shape != (len(selected), AREA_COUNT):
        raise ValueError("delta_f_physical_hz must have shape [time, 4]")
    if len(time) < 2 or not np.all(np.isfinite(frequency)):
        raise ValueError("frequency traces must be finite and have at least two steps")
    intervals = np.diff(time)
    if not np.all(np.isfinite(intervals)) or np.any(intervals <= 0.0):
        raise ValueError("trace time must be finite and strictly increasing")
    dt = float(np.median(intervals))
    common = np.mean(frequency, axis=1)
    differential = np.mean(frequency[:, :2], axis=1) - np.mean(
        frequency[:, 2:], axis=1
    )
    return common, differential, dt


def _safe_correlation(left: np.ndarray, right: np.ndarray) -> float | None:
    if left.shape != right.shape or left.size < 2:
        raise ValueError("correlation arrays must have equal non-trivial shape")
    if np.std(left) <= 1e-14 or np.std(right) <= 1e-14:
        return None
    return float(np.corrcoef(left, right)[0, 1])


def _sign_agreement(action: np.ndarray, signal: np.ndarray) -> dict[str, float | int]:
    mask = (np.abs(action) > 1e-9) & (np.abs(signal) > 1e-12)
    count = int(np.count_nonzero(mask))
    if count == 0:
        return {"count": 0, "fraction": 0.0}
    agreement = np.sign(action[mask]) == np.sign(-signal[mask])
    return {"count": count, "fraction": float(np.mean(agreement))}


def analyse_seed_policy_actions(
    records: Sequence[Mapping[str, Any]],
    *,
    active_steps: int = ACTIVE_STEPS,
    q_max: float = 0.25,
) -> dict[str, Any]:
    """Diagnose whether an R278 policy behaves like causal inter-area feedback.

    ``available_*`` signals are aligned with the observation available before
    action ``q_t``: step zero uses the reset equilibrium and later actions use
    the preceding trace sample. This prevents post-action response from being
    mistaken for a causal input.
    """
    if len(records) < 2:
        raise ValueError("policy audit requires at least two scenarios")
    if active_steps < 2 or q_max <= 0.0:
        raise ValueError("invalid action-audit contract")

    scenario_rows: list[dict[str, Any]] = []
    all_q: list[np.ndarray] = []
    all_raw_z: list[np.ndarray] = []
    all_current: list[np.ndarray] = []
    all_available: list[np.ndarray] = []
    all_rocof: list[np.ndarray] = []
    for record in sorted(records, key=lambda row: str(row["scenario"])):
        common, differential, dt = _frequency_modes(record, steps=active_steps)
        traces = record["traces"][:active_steps]
        q = np.asarray([row["r278_q"] for row in traces], dtype=float)
        if q.shape != (active_steps,) or not np.all(np.isfinite(q)):
            raise ValueError("r278_q must be a finite scalar at every active step")
        available = np.concatenate(([0.0], differential[:-1]))
        rocof = np.concatenate(([0.0], np.diff(available) / dt))
        raw_z = None
        if all("r278_raw_z" in row for row in traces):
            raw_z = np.asarray([row["r278_raw_z"] for row in traces], dtype=float)
            if raw_z.shape != (active_steps, AREA_COUNT) or not np.all(
                np.isfinite(raw_z)
            ):
                raise ValueError("r278_raw_z must have shape [active_steps, 4]")
        scenario_rows.append(
            {
                "scenario": str(record["scenario"]),
                "first_q": float(q[0]),
                "mean_q": float(np.mean(q)),
                "negative_q_fraction": float(np.mean(q < -1e-9)),
                "exact_q_saturation_fraction": float(
                    np.mean(np.isclose(np.abs(q), q_max, rtol=0.0, atol=1e-6))
                ),
                "q_fraction_at_or_above_95_percent_bound": float(
                    np.mean(np.abs(q) >= 0.95 * q_max)
                ),
                "raw_vote_saturation_fraction": (
                    None
                    if raw_z is None
                    else float(
                        np.mean(
                            np.isclose(np.abs(raw_z), 1.0, rtol=0.0, atol=1e-6)
                        )
                    )
                ),
                "available_frequency_sign_agreement": _sign_agreement(q, available),
                "available_rocof_sign_agreement": _sign_agreement(q, rocof),
                "first_3s_common_iae_hz_s": float(np.sum(np.abs(common)) * dt),
                "first_3s_inter_area_iae_hz_s": float(
                    np.sum(np.abs(differential)) * dt
                ),
            }
        )
        all_q.append(q)
        if raw_z is not None:
            all_raw_z.append(raw_z.reshape(-1))
        all_current.append(differential)
        all_available.append(available)
        all_rocof.append(rocof)

    q_values = np.concatenate(all_q)
    if all_raw_z and len(all_raw_z) != len(records):
        raise ValueError("raw actor votes are missing from only some policy traces")
    raw_z_values = np.concatenate(all_raw_z) if all_raw_z else None
    current = np.concatenate(all_current)
    available = np.concatenate(all_available)
    rocof = np.concatenate(all_rocof)
    first_actions = np.asarray([row["first_q"] for row in scenario_rows])
    invariant_span = float(np.max(first_actions) - np.min(first_actions))
    return {
        "scenario_count": len(scenario_rows),
        "active_steps": active_steps,
        "sample_count": int(q_values.size),
        "alignment": {
            "current_frequency": "post-action response in the same trace row",
            "available_frequency": "reset zero at t=0, then previous trace row",
            "available_rocof": "finite difference of available inter-area frequency",
        },
        "first_action": {
            "values": first_actions.tolist(),
            "minimum": float(np.min(first_actions)),
            "maximum": float(np.max(first_actions)),
            "span": invariant_span,
            "scenario_invariant_at_1e_7": bool(invariant_span <= 1e-7),
        },
        "pooled_active_window": {
            "mean_q": float(np.mean(q_values)),
            "median_q": float(np.median(q_values)),
            "negative_q_fraction": float(np.mean(q_values < -1e-9)),
            "positive_q_fraction": float(np.mean(q_values > 1e-9)),
            "near_zero_q_fraction": float(np.mean(np.abs(q_values) <= 1e-9)),
            "saturation_definition": {
                "exact_q": "abs(abs(q)-q_max)<=1e-6",
                "near_bound_q": "abs(q)>=0.95*q_max",
                "raw_vote": "abs(abs(z)-1)<=1e-6",
            },
            "exact_q_saturation_fraction": float(
                np.mean(np.isclose(np.abs(q_values), q_max, rtol=0.0, atol=1e-6))
            ),
            "q_fraction_at_or_above_95_percent_bound": float(
                np.mean(np.abs(q_values) >= 0.95 * q_max)
            ),
            "raw_vote_saturation_fraction": (
                None
                if raw_z_values is None
                else float(
                    np.mean(
                        np.isclose(
                            np.abs(raw_z_values), 1.0, rtol=0.0, atol=1e-6
                        )
                    )
                )
            ),
            "correlation_q_with_same_step_inter_area_frequency": _safe_correlation(
                q_values, current
            ),
            "correlation_q_with_available_inter_area_frequency": _safe_correlation(
                q_values, available
            ),
            "correlation_q_with_available_inter_area_rocof": _safe_correlation(
                q_values, rocof
            ),
            "negative_feedback_sign_agreement_frequency": _sign_agreement(
                q_values, available
            ),
            "negative_feedback_sign_agreement_rocof": _sign_agreement(q_values, rocof),
        },
        "by_scenario": scenario_rows,
    }


def _iae(values: np.ndarray, dt: float) -> float:
    return float(np.sum(np.abs(values)) * dt)


def _trace_endpoints(record: Mapping[str, Any], *, active_steps: int) -> dict[str, float]:
    common, differential, dt = _frequency_modes(record)
    frequency = np.asarray(
        [row["delta_f_physical_hz"] for row in record["traces"]], dtype=float
    )
    centered = frequency - np.mean(frequency, axis=1, keepdims=True)
    return {
        "normalized_sync_loss_hz2": float(np.mean(np.square(centered))),
        "fast_inter_area_iae_hz_s": _iae(differential[:active_steps], dt),
        "first_3s_common_iae_hz_s": _iae(common[:active_steps], dt),
        "vsg_mean_iae_hz_s": _iae(common, dt),
        "worst_bus_peak_abs_hz": float(np.max(np.abs(frequency))),
    }


def _effect_summary(
    baseline: Mapping[str, Mapping[str, Any]],
    candidate: Mapping[str, Mapping[str, Any]],
    *,
    active_steps: int,
) -> dict[str, Any]:
    if set(baseline) != set(candidate):
        raise ValueError("candidate and baseline scenario sets differ")
    endpoints = {
        scenario: (
            _trace_endpoints(baseline[scenario], active_steps=active_steps),
            _trace_endpoints(candidate[scenario], active_steps=active_steps),
        )
        for scenario in sorted(baseline)
    }
    result: dict[str, Any] = {}
    for name in next(iter(endpoints.values()))[0]:
        reference = np.asarray([pair[0][name] for pair in endpoints.values()])
        values = np.asarray([pair[1][name] for pair in endpoints.values()])
        if float(np.mean(reference)) <= 0.0:
            raise ValueError(f"non-positive baseline mean for endpoint {name}")
        paired_percent = 100.0 * (values - reference) / reference
        result[name] = {
            "ratio_of_means_percent": float(
                100.0 * (np.mean(values) / np.mean(reference) - 1.0)
            ),
            "median_paired_percent": float(np.median(paired_percent)),
            "scenario_improvement_count": int(np.count_nonzero(values < reference)),
            "scenario_tie_count": int(np.count_nonzero(values == reference)),
            "scenario_count": int(values.size),
        }
    return result


def _aggregate_metric(rows: Sequence[Mapping[str, float]], key: str) -> dict[str, float]:
    values = np.asarray([row[key] for row in rows], dtype=float)
    return {
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "maximum": float(np.max(values)),
        "minimum": float(np.min(values)),
    }


def analyse_signed_h1_pairs(
    baseline_records: Mapping[str, Mapping[str, Any]],
    h1_pos_records: Mapping[str, Mapping[str, Any]],
    h1_neg_records: Mapping[str, Mapping[str, Any]],
    *,
    active_steps: int = ACTIVE_STEPS,
) -> dict[str, Any]:
    """Measure intended differential response and unintended common leakage."""
    scenarios = set(baseline_records)
    if scenarios != set(h1_pos_records) or scenarios != set(h1_neg_records):
        raise ValueError("baseline/h1 signed-pair scenario sets must match")
    if not scenarios:
        raise ValueError("signed-pair audit needs at least one scenario")

    decomposition: list[dict[str, float | str]] = []
    max_fleet_mean_shift = 0.0
    for scenario in sorted(scenarios):
        base = baseline_records[scenario]
        pos = h1_pos_records[scenario]
        neg = h1_neg_records[scenario]
        common_0, diff_0, dt = _frequency_modes(base, steps=active_steps)
        common_pos, diff_pos, dt_pos = _frequency_modes(pos, steps=active_steps)
        common_neg, diff_neg, dt_neg = _frequency_modes(neg, steps=active_steps)
        if not np.isclose(dt, dt_pos) or not np.isclose(dt, dt_neg):
            raise ValueError("signed-pair traces use different sample intervals")

        odd_common = 0.5 * (common_pos - common_neg)
        odd_diff = 0.5 * (diff_pos - diff_neg)
        even_common = 0.5 * (common_pos + common_neg) - common_0
        even_diff = 0.5 * (diff_pos + diff_neg) - diff_0
        pos_m = np.asarray([row["M_es"] for row in pos["traces"][:active_steps]])
        neg_m = np.asarray([row["M_es"] for row in neg["traces"][:active_steps]])
        base_m = np.asarray([row["M_es"] for row in base["traces"][:active_steps]])
        fleet_mean_shift = max(
            float(np.max(np.abs(np.mean(pos_m - base_m, axis=1)))),
            float(np.max(np.abs(np.mean(neg_m - base_m, axis=1)))),
        )
        max_fleet_mean_shift = max(max_fleet_mean_shift, fleet_mean_shift)
        decomposition.append(
            {
                "scenario": scenario,
                "odd_common_iae_hz_s": _iae(odd_common, dt),
                "odd_differential_iae_hz_s": _iae(odd_diff, dt),
                "even_common_iae_hz_s": _iae(even_common, dt),
                "even_differential_iae_hz_s": _iae(even_diff, dt),
                "odd_common_peak_abs_hz": float(np.max(np.abs(odd_common))),
                "odd_differential_peak_abs_hz": float(np.max(np.abs(odd_diff))),
                "even_common_peak_abs_hz": float(np.max(np.abs(even_common))),
                "even_differential_peak_abs_hz": float(np.max(np.abs(even_diff))),
                "max_abs_fleet_mean_m_shift_vs_q0": fleet_mean_shift,
            }
        )

    metric_names = [
        key
        for key in decomposition[0]
        if key != "scenario" and key != "max_abs_fleet_mean_m_shift_vs_q0"
    ]
    aggregate = {key: _aggregate_metric(decomposition, key) for key in metric_names}
    odd_diff_mean = aggregate["odd_differential_iae_hz_s"]["mean"]
    aggregate["leakage_ratios"] = {
        "odd_common_to_odd_differential_iae": float(
            aggregate["odd_common_iae_hz_s"]["mean"] / max(odd_diff_mean, 1e-15)
        ),
        "even_common_to_odd_differential_iae": float(
            aggregate["even_common_iae_hz_s"]["mean"] / max(odd_diff_mean, 1e-15)
        ),
        "even_differential_to_odd_differential_iae": float(
            aggregate["even_differential_iae_hz_s"]["mean"]
            / max(odd_diff_mean, 1e-15)
        ),
    }
    return {
        "scenario_count": len(scenarios),
        "active_steps": active_steps,
        "interpretation": {
            "odd": "0.5*(y(h1_pos)-y(h1_neg)); signed input sensitivity",
            "even": "0.5*(y(h1_pos)+y(h1_neg))-y(q0); nonlinear/common shift",
            "dynamic_decoupling_note": (
                "zero fleet-mean inertia shift is an input budget identity, not "
                "proof of zero common-frequency response"
            ),
        },
        "maximum_abs_fleet_mean_m_shift_vs_q0": max_fleet_mean_shift,
        "aggregate": aggregate,
        "by_scenario": decomposition,
        "h1_pos_minus_q0": _effect_summary(
            baseline_records, h1_pos_records, active_steps=active_steps
        ),
        "h1_neg_minus_q0": _effect_summary(
            baseline_records, h1_neg_records, active_steps=active_steps
        ),
    }

def hierarchical_seed_scenario_ratio_bootstrap(
    left_by_seed: Mapping[int, Mapping[str, float]],
    *,
    right_by_seed: Mapping[int, Mapping[str, float]] | None = None,
    right_deterministic: Mapping[str, float] | None = None,
    resamples: int = 10_000,
    seed: int = 2026072706,
) -> dict[str, Any]:
    """Bootstrap a lower-is-better ratio over seeds and shared scenarios.

    Seeds are sampled first and scenario indices are then sampled once per
    replicate and shared by both sides. ``right_by_seed`` is for a matched
    learned comparator; ``right_deterministic`` is for a frozen controller
    whose scenario rows have no training-seed dimension.
    """
    if (right_by_seed is None) == (right_deterministic is None):
        raise ValueError("provide exactly one right-hand comparator")
    if resamples < 100:
        raise ValueError("hierarchical bootstrap requires at least 100 resamples")
    seed_ids = sorted(left_by_seed)
    if len(seed_ids) < 2:
        raise ValueError("hierarchical bootstrap requires at least two seeds")
    scenario_ids = sorted(next(iter(left_by_seed.values())))
    if len(scenario_ids) < 2:
        raise ValueError("hierarchical bootstrap requires at least two scenarios")
    expected_scenarios = set(scenario_ids)
    if any(set(rows) != expected_scenarios for rows in left_by_seed.values()):
        raise ValueError("left seed rows must share one scenario set")

    left = np.asarray(
        [[left_by_seed[seed_id][name] for name in scenario_ids] for seed_id in seed_ids],
        dtype=float,
    )
    if right_by_seed is not None:
        if set(right_by_seed) != set(seed_ids):
            raise ValueError("matched learned comparators must share seed IDs")
        if any(set(rows) != expected_scenarios for rows in right_by_seed.values()):
            raise ValueError("right seed rows must share the left scenario set")
        right_seeded = np.asarray(
            [
                [right_by_seed[seed_id][name] for name in scenario_ids]
                for seed_id in seed_ids
            ],
            dtype=float,
        )
        right_fixed = None
    else:
        assert right_deterministic is not None
        if set(right_deterministic) != expected_scenarios:
            raise ValueError("deterministic comparator must share the scenario set")
        right_fixed = np.asarray(
            [right_deterministic[name] for name in scenario_ids], dtype=float
        )
        right_seeded = None

    arrays = [left, right_seeded if right_seeded is not None else right_fixed]
    if any(not np.all(np.isfinite(array)) for array in arrays):
        raise ValueError("bootstrap inputs must be finite")
    if any(np.any(array <= 0.0) for array in arrays):
        raise ValueError("ratio bootstrap inputs must be strictly positive")

    observed_right = (
        float(np.mean(right_seeded))
        if right_seeded is not None
        else float(np.mean(right_fixed))
    )
    observed_percent = 100.0 * (float(np.mean(left)) / observed_right - 1.0)
    rng = np.random.default_rng(seed)
    samples = np.empty(resamples, dtype=float)
    seed_count, scenario_count = left.shape
    for index in range(resamples):
        sampled_seeds = rng.integers(0, seed_count, size=seed_count)
        sampled_scenarios = rng.integers(0, scenario_count, size=scenario_count)
        left_mean = float(
            np.mean(left[np.ix_(sampled_seeds, sampled_scenarios)])
        )
        if right_seeded is not None:
            right_mean = float(
                np.mean(right_seeded[np.ix_(sampled_seeds, sampled_scenarios)])
            )
        else:
            right_mean = float(np.mean(right_fixed[sampled_scenarios]))
        samples[index] = 100.0 * (left_mean / right_mean - 1.0)

    interval = np.percentile(samples, [2.5, 97.5])
    return {
        "method": "two-level percentile bootstrap: seeds then shared scenario indices",
        "lower_is_better": True,
        "seed": seed,
        "resamples": resamples,
        "seed_count": seed_count,
        "scenario_count": scenario_count,
        "right_has_seed_dimension": right_seeded is not None,
        "ratio_of_means_percent": {
            "point": observed_percent,
            "percentile_95_interval": [float(interval[0]), float(interval[1])],
        },
        "bootstrap_probability_left_improves": float(np.mean(samples < 0.0)),
    }
