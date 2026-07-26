"""Prospective scenario-bank sealing and paired held-out statistics.

Motivation
----------
Q-0028 is the first project comparison whose random disturbance set must be
materialised and hashed before any controller sees it.  The reusable
functions here keep that evidence boundary separate from the ANDES runner:

* deterministic canonical JSON bytes and SHA-256 verification;
* generator/source provenance embedded in the bank manifest;
* exact binomial failure intervals without an extra statistics dependency;
* paired bootstrap effects using one shared scenario-index resample;
* transparent empirical worst-case and upper-tail summaries.

The module does not select controllers, tune a threshold, or invent a scalar
score.  A round driver supplies the frozen controllers and decision rule.

Failure modes
-------------
An existing bank is never overwritten.  A byte-level hash mismatch, malformed
manifest, non-finite endpoint, incomplete pairing, or zero reference mean
raises/returns an explicit error instead of silently dropping a scenario.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from andes_rl_kundur.evaluation.paper_strict_eval import generate_test_scenarios

SCENARIO_BANK_SCHEMA_VERSION = 1
CANONICAL_JSON_RULE = (
    "utf-8; json.dumps(sort_keys=True,separators=(',',':'),"
    "ensure_ascii=False); trailing LF"
)


def canonical_json_bytes(payload: object) -> bytes:
    """Return the byte contract used for sealed manifests and summaries."""
    text = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return (text + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    """Return a lowercase SHA-256 hex digest."""
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    """Stream a file into SHA-256 so checkpoints need not fit in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_scenario_bank(
    *,
    n: int,
    seed: int,
    repository_head: str,
    generator_source_sha256: str,
) -> dict[str, Any]:
    """Build the deterministic no-anchor bank manifest without writing it."""
    scenarios = generate_test_scenarios(n=n, seed=seed, include_anchors=False)
    names = [scenario.get("name") for scenario in scenarios]
    if len(scenarios) != n or len(set(names)) != n:
        raise ValueError("scenario generator returned wrong count or duplicate names")
    if any(name in {"load_step_1", "load_step_2"} for name in names):
        raise ValueError("sealed bank must not contain paper anchor scenarios")
    return {
        "schema_version": SCENARIO_BANK_SCHEMA_VERSION,
        "generator": (
            "andes_rl_kundur.evaluation.paper_strict_eval."
            "generate_test_scenarios"
        ),
        "generator_arguments": {
            "n": n,
            "seed": seed,
            "include_anchors": False,
        },
        "generator_source_sha256": generator_source_sha256,
        "repository_head": repository_head,
        "serialization": CANONICAL_JSON_RULE,
        "scenario_count": n,
        "scenarios": scenarios,
    }


def write_scenario_bank(path: Path, payload: Mapping[str, Any]) -> str:
    """Atomically persist a new bank and ``.sha256`` sidecar.

    Both targets must be absent.  This deliberately has no overwrite switch:
    a different bank requires a different path and a new prospective plan.
    """
    sidecar = Path(f"{path}.sha256")
    existing = [candidate for candidate in (path, sidecar) if candidate.exists()]
    if existing:
        raise FileExistsError(f"refusing to overwrite sealed bank artifacts: {existing}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(payload)
    digest = sha256_bytes(data)
    temporary = Path(f"{path}.tmp")
    if temporary.exists():
        raise FileExistsError(f"stale temporary bank exists: {temporary}")
    temporary.write_bytes(data)
    temporary.replace(path)
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def load_scenario_bank(
    path: Path,
    *,
    expected_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Load and structurally validate a sealed bank from its actual bytes."""
    data = path.read_bytes()
    digest = sha256_bytes(data)
    if expected_sha256 is not None and digest != expected_sha256.lower():
        raise ValueError(
            f"sealed bank SHA-256 mismatch: expected {expected_sha256}, got {digest}"
        )
    try:
        payload = json.loads(data)
    except json.JSONDecodeError as exc:
        raise ValueError(f"sealed bank is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("sealed bank root must be an object")
    if payload.get("schema_version") != SCENARIO_BANK_SCHEMA_VERSION:
        raise ValueError("unsupported sealed bank schema_version")
    if payload.get("serialization") != CANONICAL_JSON_RULE:
        raise ValueError("sealed bank serialization contract drifted")
    arguments = payload.get("generator_arguments")
    scenarios = payload.get("scenarios")
    if not isinstance(arguments, dict) or arguments.get("include_anchors") is not False:
        raise ValueError("sealed bank must declare include_anchors=False")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("sealed bank scenarios must be a non-empty list")
    if payload.get("scenario_count") != len(scenarios):
        raise ValueError("sealed bank scenario_count does not match payload")
    if arguments.get("n") != len(scenarios):
        raise ValueError("sealed bank generator n does not match payload")
    names: list[str] = []
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise ValueError("each sealed scenario must be an object")
        name = scenario.get("name")
        delta_u = scenario.get("delta_u")
        if not isinstance(name, str) or not isinstance(delta_u, dict) or len(delta_u) != 1:
            raise ValueError("each scenario requires a name and one-entry delta_u")
        names.append(name)
    if len(set(names)) != len(names):
        raise ValueError("sealed bank contains duplicate scenario names")
    if any(name in {"load_step_1", "load_step_2"} for name in names):
        raise ValueError("sealed bank contains a forbidden paper anchor")
    if canonical_json_bytes(payload) != data:
        raise ValueError("sealed bank bytes are not in canonical serialization")
    return payload, digest


def exact_binomial_interval(
    successes: int,
    trials: int,
    *,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Two-sided Clopper-Pearson interval using dependency-free bisection."""
    if trials < 1 or not 0 <= successes <= trials:
        raise ValueError("require trials >= 1 and 0 <= successes <= trials")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0, 1)")
    alpha_tail = (1.0 - confidence) / 2.0

    def cdf(k: int, p: float) -> float:
        return math.fsum(
            math.comb(trials, i) * p**i * (1.0 - p) ** (trials - i)
            for i in range(k + 1)
        )

    def survival(k: int, p: float) -> float:
        return 1.0 - cdf(k - 1, p)

    if successes == 0:
        lower = 0.0
    else:
        lo, hi = 0.0, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2.0
            if survival(successes, mid) < alpha_tail:
                lo = mid
            else:
                hi = mid
        lower = (lo + hi) / 2.0

    if successes == trials:
        upper = 1.0
    else:
        lo, hi = 0.0, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2.0
            if cdf(successes, mid) > alpha_tail:
                lo = mid
            else:
                hi = mid
        upper = (lo + hi) / 2.0
    return lower, upper


def binomial_rate_summary(events: int, trials: int) -> dict[str, Any]:
    """Count, rate, and exact 95% interval for failure/settling events."""
    lower, upper = exact_binomial_interval(events, trials)
    return {
        "count": events,
        "trials": trials,
        "rate": events / trials,
        "exact_95_interval": [lower, upper],
    }


def empirical_upper_tail(
    values_by_scenario: Mapping[str, float],
    *,
    tail_fraction: float = 0.10,
) -> dict[str, Any]:
    """Mean/median plus auditable worst entries and empirical upper-tail CVaR."""
    if not 0.0 < tail_fraction <= 1.0:
        raise ValueError("tail_fraction must be in (0, 1]")
    if not values_by_scenario:
        raise ValueError("at least one value is required")
    ordered: list[tuple[str, float]] = []
    for scenario, raw_value in values_by_scenario.items():
        value = float(raw_value)
        if not np.isfinite(value):
            raise ValueError(f"non-finite endpoint for {scenario}")
        ordered.append((scenario, value))
    ordered.sort(key=lambda item: item[1], reverse=True)
    values = np.asarray([item[1] for item in ordered], dtype=float)
    tail_count = max(1, math.ceil(values.size * tail_fraction))
    return {
        "n": int(values.size),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "minimum": float(np.min(values)),
        "maximum": float(np.max(values)),
        "worst_1": {"scenario": ordered[0][0], "value": ordered[0][1]},
        "worst_2": [
            {"scenario": scenario, "value": value}
            for scenario, value in ordered[: min(2, len(ordered))]
        ],
        "cvar_upper_tail": float(np.mean(values[:tail_count])),
        "tail_fraction": tail_fraction,
        "tail_count": tail_count,
    }


def paired_bootstrap_contrasts(
    controller_endpoints: Mapping[str, Mapping[str, Sequence[float]]],
    *,
    contrasts: Sequence[tuple[str, str, str]],
    seed: int,
    n_resamples: int,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Bootstrap predeclared controller contrasts with shared paired indices.

    ``controller_endpoints[controller][endpoint]`` must use the same scenario
    order for every controller.  One index matrix is generated and reused for
    every controller/endpoint/contrast, preserving the paired experimental
    unit instead of independently resampling controller observations.
    """
    if n_resamples < 1:
        raise ValueError("n_resamples must be positive")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0, 1)")
    if not controller_endpoints:
        raise ValueError("controller_endpoints cannot be empty")
    endpoint_names = set.intersection(
        *(set(endpoints) for endpoints in controller_endpoints.values())
    )
    if not endpoint_names:
        raise ValueError("controllers have no common endpoint")
    sample_sizes: set[int] = set()
    arrays: dict[str, dict[str, np.ndarray]] = {}
    for controller, endpoints in controller_endpoints.items():
        arrays[controller] = {}
        for endpoint in endpoint_names:
            values = np.asarray(endpoints[endpoint], dtype=float)
            if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)):
                raise ValueError(f"{controller}/{endpoint} requires finite 1-D values")
            arrays[controller][endpoint] = values
            sample_sizes.add(int(values.size))
    if len(sample_sizes) != 1:
        raise ValueError("all controller endpoints must have the same sample size")
    sample_size = sample_sizes.pop()
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, sample_size, size=(n_resamples, sample_size))
    alpha_tail = (1.0 - confidence) / 2.0
    quantiles = [alpha_tail, 1.0 - alpha_tail]

    result: dict[str, Any] = {}
    for contrast_name, left_name, right_name in contrasts:
        if left_name not in arrays or right_name not in arrays:
            raise ValueError(f"unknown controller in contrast {contrast_name}")
        endpoint_results: dict[str, Any] = {}
        for endpoint in sorted(endpoint_names):
            left = arrays[left_name][endpoint]
            right = arrays[right_name][endpoint]
            left_boot = np.mean(left[indices], axis=1)
            right_boot = np.mean(right[indices], axis=1)
            absolute_boot = left_boot - right_boot
            absolute_point = float(np.mean(left) - np.mean(right))
            paired_absolute = left - right
            improvement_count = int(np.sum(left < right))
            zero_reference = np.any(
                np.isclose(right_boot, 0.0, rtol=0.0, atol=1e-15)
            ) or np.any(np.isclose(right, 0.0, rtol=0.0, atol=1e-15))
            if zero_reference:
                relative_effect: dict[str, Any] = {
                    "point": None,
                    "percentile_95_interval": None,
                    "unavailable_reason": (
                        "reference mean/sample can be zero; absolute paired "
                        "difference remains defined"
                    ),
                }
                paired_relative_values = None
                median_paired_percent = None
                probability_left_improves = float(np.mean(absolute_boot < 0.0))
            else:
                relative_boot = 100.0 * (left_boot / right_boot - 1.0)
                relative_point = float(
                    100.0 * (np.mean(left) / np.mean(right) - 1.0)
                )
                paired_relative = 100.0 * (left / right - 1.0)
                relative_effect = {
                    "point": relative_point,
                    "percentile_95_interval": np.quantile(
                        relative_boot, quantiles
                    ).tolist(),
                }
                paired_relative_values = paired_relative.tolist()
                median_paired_percent = float(np.median(paired_relative))
                probability_left_improves = float(np.mean(relative_boot < 0.0))
            endpoint_results[endpoint] = {
                "direction": "negative_is_left_improvement",
                "absolute_mean_difference": {
                    "point": absolute_point,
                    "percentile_95_interval": np.quantile(
                        absolute_boot, quantiles
                    ).tolist(),
                },
                "ratio_of_means_percent": relative_effect,
                "bootstrap_probability_left_improves": probability_left_improves,
                "scenario_improvement_fraction": float(np.mean(left < right)),
                "scenario_improvement_count": improvement_count,
                "scenario_improvement_exact_95_interval": list(
                    exact_binomial_interval(improvement_count, sample_size)
                ),
                "scenario_tie_fraction": float(
                    np.mean(np.isclose(left, right, rtol=0.0, atol=1e-15))
                ),
                "paired_absolute_differences": paired_absolute.tolist(),
                "paired_relative_percent": paired_relative_values,
                "paired_difference_summary": {
                    "median_absolute": float(np.median(paired_absolute)),
                    "iqr_absolute": np.quantile(
                        paired_absolute, [0.25, 0.75]
                    ).tolist(),
                    "minimum_absolute": float(np.min(paired_absolute)),
                    "maximum_absolute": float(np.max(paired_absolute)),
                },
                "median_paired_percent": median_paired_percent,
            }
        result[contrast_name] = {
            "left": left_name,
            "right": right_name,
            "n_paired": sample_size,
            "endpoints": endpoint_results,
        }
    return {
        "seed": seed,
        "n_resamples": n_resamples,
        "confidence": confidence,
        "shared_index_resampling": True,
        "contrasts": result,
    }


def paired_binary_outcome_table(
    left_success: Sequence[bool],
    right_success: Sequence[bool],
) -> dict[str, Any]:
    """Paired 2x2 completion table with a two-sided exact McNemar p-value."""
    left = np.asarray(left_success, dtype=bool)
    right = np.asarray(right_success, dtype=bool)
    if left.ndim != 1 or right.ndim != 1 or left.size == 0 or left.shape != right.shape:
        raise ValueError("paired binary outcomes require equal non-empty 1-D sequences")
    both_success = int(np.sum(left & right))
    left_only_success = int(np.sum(left & ~right))
    right_only_success = int(np.sum(~left & right))
    both_failure = int(np.sum(~left & ~right))
    discordant = left_only_success + right_only_success
    if discordant == 0:
        p_value = 1.0
    else:
        smaller = min(left_only_success, right_only_success)
        lower_tail = math.fsum(
            math.comb(discordant, value) * 0.5**discordant
            for value in range(smaller + 1)
        )
        p_value = min(1.0, 2.0 * lower_tail)
    return {
        "both_success": both_success,
        "left_only_success": left_only_success,
        "right_only_success": right_only_success,
        "both_failure": both_failure,
        "discordant_pairs": discordant,
        "two_sided_exact_mcnemar_p": p_value,
    }


def classify_gate_replication(
    *,
    controller_summaries: Mapping[str, Mapping[str, Any]],
    primary_contrast: Mapping[str, Any] | None,
    gate_name: str,
    static_name: str,
    total_scenarios: int,
) -> dict[str, Any]:
    """Apply the prospectively fixed Q-0028 replication gate.

    The two co-primary endpoints must both have upper paired 95% bounds below
    zero for a positive result.  Exactly one clear endpoint plus a negative
    point estimate on the other is partial.  Physical tail, settling, failure,
    and action-variation guards can only downgrade a result.
    """
    gate = controller_summaries[gate_name]
    static = controller_summaries[static_name]
    co_primary = (
        "vsg_mean_iae_hz_s",
        "normalized_sync_loss_hz2",
    )

    def endpoint_tail_effect(endpoint: str, field: str) -> float:
        try:
            left = float(gate["endpoints"][endpoint][field])
            right = float(static["endpoints"][endpoint][field])
        except (KeyError, TypeError, ValueError):
            return math.inf
        if math.isclose(right, 0.0, rel_tol=0.0, abs_tol=1e-15):
            return math.inf if not math.isclose(left, 0.0, abs_tol=1e-15) else 0.0
        return 100.0 * (left / right - 1.0)

    failure_guard = gate["failures"]["count"] <= static["failures"]["count"]
    complete_primary_pair = (
        gate["complete_count"] == total_scenarios
        and static["complete_count"] == total_scenarios
    )
    settling_guard = gate["settling"]["count"] >= static["settling"]["count"]
    safety_cvar_effects = {
        endpoint: endpoint_tail_effect(endpoint, "cvar_upper_tail")
        for endpoint in ("worst_bus_peak_abs_hz", "max_abs_rocof_hz_s")
    }
    safety_worst_effects = {
        endpoint: endpoint_tail_effect(endpoint, "maximum")
        for endpoint in ("worst_bus_peak_abs_hz", "max_abs_rocof_hz_s")
    }
    action_tv_cvar_effect = endpoint_tail_effect(
        "action_total_variation", "cvar_upper_tail"
    )
    guards = {
        "complete_primary_pair_20_of_20": complete_primary_pair,
        "gate_failure_not_higher": failure_guard,
        "settling_success_not_lower": settling_guard,
        "safety_cvar90_not_worse_over_5pct": all(
            effect <= 5.0 for effect in safety_cvar_effects.values()
        ),
        "safety_worst1_not_worse_over_10pct": all(
            effect <= 10.0 for effect in safety_worst_effects.values()
        ),
        "action_tv_cvar90_not_worse_over_25pct": action_tv_cvar_effect <= 25.0,
    }
    all_guards = all(guards.values())

    endpoint_decisions: dict[str, Any] = {}
    if primary_contrast is not None:
        for endpoint in co_primary:
            effect = primary_contrast["endpoints"][endpoint][
                "ratio_of_means_percent"
            ]
            point = float(effect["point"])
            upper = float(effect["percentile_95_interval"][1])
            endpoint_decisions[endpoint] = {
                "point_percent": point,
                "ci_upper_percent": upper,
                "point_improves": point < 0.0,
                "ci_excludes_zero_in_improvement_direction": upper < 0.0,
            }

    if not all_guards or len(endpoint_decisions) != len(co_primary):
        classification = "NEGATIVE"
        reason = "one or more failure, completeness, tail, settling, or action guards failed"
    else:
        clear_count = sum(
            item["ci_excludes_zero_in_improvement_direction"]
            for item in endpoint_decisions.values()
        )
        all_points_improve = all(
            item["point_improves"] for item in endpoint_decisions.values()
        )
        if clear_count == len(co_primary):
            classification = "POSITIVE"
            reason = "both co-primary paired intervals exclude zero and all guards pass"
        elif clear_count == 1 and all_points_improve:
            classification = "PARTIAL"
            reason = "one co-primary interval excludes zero; the other point improves"
        else:
            classification = "NEGATIVE"
            reason = "co-primary evidence is null, reversed, or not jointly consistent"

    return {
        "classification": classification,
        "reason": reason,
        "co_primary": endpoint_decisions,
        "guards": guards,
        "tail_effects_percent": {
            "safety_cvar90": safety_cvar_effects,
            "safety_worst1": safety_worst_effects,
            "action_tv_cvar90": action_tv_cvar_effect,
        },
    }


def classify_smoothing_replication(
    *,
    controller_summaries: Mapping[str, Mapping[str, Any]],
    primary_contrast: Mapping[str, Any] | None,
    mechanism_contrast: Mapping[str, Any] | None,
    smooth_name: str,
    static_name: str,
    total_scenarios: int,
) -> dict[str, Any]:
    """Apply the prospectively fixed Q-0029 alpha-slew feasibility gate.

    Q-0029 asks whether both co-primary *mean directions* survive while the
    action-variation guard is repaired.  A positive result therefore requires
    both point estimates to improve, at least one interval to exclude zero,
    every Q-0028 safety/action guard, and lower mean action variation than the
    unsmoothed gate.  If both point estimates improve and all guards pass but
    neither interval excludes zero, the feasibility result is partial.
    """
    base = classify_gate_replication(
        controller_summaries=controller_summaries,
        primary_contrast=primary_contrast,
        gate_name=smooth_name,
        static_name=static_name,
        total_scenarios=total_scenarios,
    )

    mechanism_point: float | None = None
    if mechanism_contrast is not None:
        try:
            mechanism_point = float(
                mechanism_contrast["endpoints"]["action_total_variation"][
                    "ratio_of_means_percent"
                ]["point"]
            )
        except (KeyError, TypeError, ValueError):
            mechanism_point = None

    guards = {
        **base["guards"],
        "smooth_action_tv_mean_below_raw": (
            mechanism_point is not None and mechanism_point < 0.0
        ),
    }
    endpoint_decisions = base["co_primary"]
    all_points_improve = (
        len(endpoint_decisions) == 2
        and all(item["point_improves"] for item in endpoint_decisions.values())
    )
    clear_count = sum(
        item["ci_excludes_zero_in_improvement_direction"]
        for item in endpoint_decisions.values()
    )

    if not all(guards.values()) or not all_points_improve:
        classification = "NEGATIVE"
        reason = (
            "a co-primary mean direction, failure/tail/settling/action guard, "
            "or raw-gate action-TV mechanism check failed"
        )
    elif clear_count >= 1:
        classification = "POSITIVE"
        reason = (
            "both co-primary means improve, at least one paired interval "
            "excludes zero, action-TV falls versus raw, and all guards pass"
        )
    else:
        classification = "PARTIAL"
        reason = (
            "both co-primary means improve and all guards pass, but neither "
            "paired interval excludes zero"
        )

    return {
        **base,
        "classification": classification,
        "reason": reason,
        "guards": guards,
        "mechanism": {
            "smooth_minus_raw_action_tv_mean_percent": mechanism_point,
        },
    }
