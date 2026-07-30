"""Objective post-hoc evaluation for completed four-VSG controller traces.

EVAL-v2 deliberately separates three questions that older reward-only probes
mixed together:

1. Are the traces complete, paired, physically reported, and contract-valid?
2. What are the paired physical effects and their uncertainty/tail behaviour?
3. What did each controller execute?

The module never produces a composite score or winner rank.  Its output is a
diagnostic scorecard, not a replacement for a prospectively sealed round.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from andes_rl_kundur.evaluation.reviewer_identifiability import (
    hierarchical_seed_scenario_ratio_bootstrap,
)
from andes_rl_kundur.evaluation.sealed_bank import (
    empirical_upper_tail,
    paired_bootstrap_contrasts,
)

SCHEMA_VERSION = 1
AGENT_COUNT = 4
DEFAULT_ACTIVE_STEPS = 15
DEFAULT_FINAL_WINDOW_STEPS = 50
PERFORMANCE_METRICS = (
    "normalized_sync_loss_hz2",
    "fast_inter_area_iae_hz_s",
    "first_3s_common_iae_hz_s",
    "full_inter_area_iae_hz_s",
    "vsg_mean_iae_hz_s",
    "final_window_common_abs_mean_hz",
    "worst_bus_peak_abs_hz",
    "max_abs_rocof_hz_s",
    "secondary_3_to_10s_common_peak_abs_hz",
    "secondary_3_to_10s_inter_area_rms_hz",
)
PRIMARY_METRICS = (
    "normalized_sync_loss_hz2",
    "fast_inter_area_iae_hz_s",
)
STORAGE_VECTOR_FIELDS = (
    "bess_actual_power_system_pu",
    "bess_commanded_power_system_pu",
    "bess_requested_power_system_pu",
    "bess_soc",
    "bess_charge_energy_mwh_total",
    "bess_discharge_energy_mwh_total",
)
CONTROLLER_PATTERN = re.compile(r"^(centralized|shared)_s(\d+)$")


class EvaluationContractError(ValueError):
    """Raised when inputs cannot support a complete paired evaluation."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_record(path: Path) -> dict[str, Any]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationContractError(f"cannot read trace {path}: {exc}") from exc
    if not isinstance(record, dict):
        raise EvaluationContractError(f"{path.name}: trace root must be an object")
    required = ("scenario", "controller", "completed", "tds_failed", "traces")
    missing = [key for key in required if key not in record]
    if missing:
        raise EvaluationContractError(f"{path.name}: missing fields {missing}")
    if record["completed"] is not True or record["tds_failed"] is not False:
        raise EvaluationContractError(f"{path.name}: trace is not completed")
    traces = record["traces"]
    if not isinstance(traces, list) or len(traces) < 2:
        raise EvaluationContractError(f"{path.name}: traces must contain at least two rows")
    expected = int(record.get("requested_steps", len(traces)))
    reported = int(record.get("n_steps", len(traces)))
    if len(traces) != expected or reported != expected:
        raise EvaluationContractError(
            f"{path.name}: step mismatch traces={len(traces)}, "
            f"n_steps={reported}, requested_steps={expected}"
        )
    if record.get("metric_frequency_basis") != "andes_physical_hz":
        raise EvaluationContractError(
            f"{path.name}: metric_frequency_basis must be andes_physical_hz"
        )
    if not np.isclose(
        float(record.get("andes_nominal_frequency_hz", math.nan)),
        60.0,
        rtol=0.0,
        atol=1e-12,
    ):
        raise EvaluationContractError(f"{path.name}: andes_nominal_frequency_hz must be 60")
    return record


def _trace_arrays(record: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray, float]:
    rows = record["traces"]
    try:
        time = np.asarray([row["t"] for row in rows], dtype=float)
        frequency = np.asarray(
            [row["delta_f_physical_hz"] for row in rows],
            dtype=float,
        )
        absolute_frequency = np.asarray(
            [row["freq_hz_physical"] for row in rows],
            dtype=float,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise EvaluationContractError(
            f"{record['scenario']}/{record['controller']}: malformed physical trace"
        ) from exc
    if frequency.shape != (len(rows), AGENT_COUNT):
        raise EvaluationContractError(
            f"{record['scenario']}/{record['controller']}: "
            "delta_f_physical_hz must have shape [time, 4]"
        )
    if absolute_frequency.shape != frequency.shape or not np.all(np.isfinite(absolute_frequency)):
        raise EvaluationContractError(
            f"{record['scenario']}/{record['controller']}: "
            "freq_hz_physical must have shape [time, 4]"
        )
    if not np.allclose(
        absolute_frequency - 60.0,
        frequency,
        rtol=0.0,
        atol=1e-9,
    ):
        raise EvaluationContractError(
            f"{record['scenario']}/{record['controller']}: "
            "60-Hz absolute and deviation frequency traces disagree"
        )
    if not np.all(np.isfinite(time)) or not np.all(np.isfinite(frequency)):
        raise EvaluationContractError("trace time and frequency must be finite")
    intervals = np.diff(time)
    if np.any(intervals <= 0.0) or not np.all(np.isfinite(intervals)):
        raise EvaluationContractError("trace time must be finite and strictly increasing")
    dt = float(np.median(intervals))
    if not np.allclose(intervals, dt, rtol=0.0, atol=max(1e-10, abs(dt) * 1e-8)):
        raise EvaluationContractError("EVAL-v2 requires a uniform sample interval")
    return time, frequency, dt


def _active_steps(record: Mapping[str, Any], row_count: int) -> int:
    config = record.get("controller_config", {})
    if isinstance(config, Mapping):
        area = config.get("area_residual", {})
        if isinstance(area, Mapping) and "active_steps" in area:
            value = int(area["active_steps"])
            if value > 0:
                return min(value, row_count)
    return min(DEFAULT_ACTIVE_STEPS, row_count)


def _trace_metrics(record: Mapping[str, Any]) -> tuple[dict[str, float], dict[str, float]]:
    time, frequency, dt = _trace_arrays(record)
    row_count = len(time)
    active_steps = _active_steps(record, row_count)
    common = np.mean(frequency, axis=1)
    differential = np.mean(frequency[:, :2], axis=1) - np.mean(
        frequency[:, 2:],
        axis=1,
    )
    centered = frequency - common[:, None]
    final_steps = min(DEFAULT_FINAL_WINDOW_STEPS, row_count)
    elapsed = time - time[0]
    secondary_mask = (elapsed >= 3.0) & (elapsed <= 10.0)
    if not np.any(secondary_mask):
        secondary_mask[-1] = True
    rocof = np.diff(frequency, axis=0) / np.diff(time)[:, None]
    metrics = {
        "normalized_sync_loss_hz2": float(np.mean(np.square(centered))),
        "fast_inter_area_iae_hz_s": float(np.sum(np.abs(differential[:active_steps])) * dt),
        "first_3s_common_iae_hz_s": float(np.sum(np.abs(common[:active_steps])) * dt),
        "full_inter_area_iae_hz_s": float(np.sum(np.abs(differential)) * dt),
        "vsg_mean_iae_hz_s": float(np.sum(np.abs(common)) * dt),
        "final_window_common_abs_mean_hz": float(np.mean(np.abs(common[-final_steps:]))),
        "worst_bus_peak_abs_hz": float(np.max(np.abs(frequency))),
        "max_abs_rocof_hz_s": float(np.max(np.abs(rocof))),
        "secondary_3_to_10s_common_peak_abs_hz": float(np.max(np.abs(common[secondary_mask]))),
        "secondary_3_to_10s_inter_area_rms_hz": float(
            np.sqrt(np.mean(np.square(differential[secondary_mask])))
        ),
    }
    legacy = {
        "paper_cum_rf_sum_hz2": float(-np.sum(np.square(centered))),
        "time_steps": float(row_count),
        "agent_count": float(AGENT_COUNT),
    }
    return metrics, legacy


def _as_array(
    rows: Sequence[Mapping[str, Any]],
    key: str,
    *,
    columns: int | None = None,
) -> np.ndarray | None:
    if not all(key in row for row in rows):
        return None
    try:
        values = np.asarray([row[key] for row in rows], dtype=float)
    except (TypeError, ValueError):
        return None
    expected = (len(rows),) if columns is None else (len(rows), columns)
    if values.shape != expected or not np.all(np.isfinite(values)):
        return None
    return values


def _nested_count(value: Any) -> int:
    if isinstance(value, list):
        return sum(_nested_count(item) for item in value) if value else 0
    return 1


def _action_and_storage(
    record: Mapping[str, Any],
    *,
    q_audit_tolerance: float,
) -> tuple[dict[str, float], dict[str, Any], list[str]]:
    rows = record["traces"]
    _, _, dt = _trace_arrays(record)
    q = _as_array(rows, "r278_q")
    residual = _as_array(rows, "r278_residual_action_norm", columns=AGENT_COUNT)
    raw = _as_array(rows, "r278_raw_z", columns=AGENT_COUNT)
    physical_sum = _as_array(rows, "r278_physical_m_residual_sum")
    violations: list[str] = []
    action: dict[str, float] = {}

    config = record.get("controller_config", {})
    area = config.get("area_residual", {}) if isinstance(config, Mapping) else {}
    q_max = float(area.get("q_max", 0.25)) if isinstance(area, Mapping) else 0.25
    q_slew_max = float(area.get("q_slew_max", 0.25)) if isinstance(area, Mapping) else 0.25
    active_steps = _active_steps(record, len(rows))

    if q is None:
        violations.append("missing_or_invalid_r278_q")
    else:
        boundary = np.diff(np.concatenate(([0.0], q)))
        action.update(
            {
                "max_abs_q": float(np.max(np.abs(q))),
                "max_abs_q_slew_per_step": float(np.max(np.abs(boundary))),
                "q_total_variation": float(np.sum(np.abs(boundary))),
                "active_q_l1_s": float(np.sum(np.abs(q[:active_steps])) * dt),
                "post_window_max_abs_q": float(
                    np.max(np.abs(q[active_steps:])) if len(q) > active_steps else 0.0
                ),
            }
        )
        if action["max_abs_q"] > q_max + q_audit_tolerance:
            violations.append("q_magnitude")
        if action["max_abs_q_slew_per_step"] > q_slew_max + q_audit_tolerance:
            violations.append("q_slew")
        if action["post_window_max_abs_q"] > 1e-9:
            violations.append("post_window_q_nonzero")

    if residual is None:
        violations.append("missing_or_invalid_residual_action")
    else:
        action["max_abs_normalized_residual_sum"] = float(np.max(np.abs(np.sum(residual, axis=1))))
        if action["max_abs_normalized_residual_sum"] > 1e-9:
            violations.append("normalized_zero_sum")
    if physical_sum is None:
        violations.append("missing_or_invalid_physical_residual_sum")
    else:
        action["max_abs_physical_m_residual_sum"] = float(np.max(np.abs(physical_sum)))
        physical_tolerance = float(4 * np.spacing(np.float32(500.0)))
        if action["max_abs_physical_m_residual_sum"] > physical_tolerance:
            violations.append("physical_zero_sum")
    if raw is not None:
        action["raw_vote_cross_agent_std_mean"] = float(np.mean(np.std(raw[:active_steps], axis=1)))
        action["raw_vote_abs_mean"] = float(np.mean(np.abs(raw[:active_steps])))

    action_norm = _as_array(rows, "action_norm")
    if action_norm is not None:
        # Scalar extraction intentionally handles only the flattened case.
        action["max_abs_action_norm"] = float(np.max(np.abs(action_norm)))
    elif all("action_norm" in row for row in rows):
        try:
            multidimensional = np.asarray(
                [row["action_norm"] for row in rows],
                dtype=float,
            )
            if multidimensional.shape == (len(rows), AGENT_COUNT, 2):
                action["max_abs_m_action_norm"] = float(np.max(np.abs(multidimensional[:, :, 0])))
                action["max_abs_d_action_norm"] = float(np.max(np.abs(multidimensional[:, :, 1])))
                if action["max_abs_d_action_norm"] > 1e-9:
                    violations.append("d_action_nonzero")
                if action["max_abs_m_action_norm"] > 0.5 + 1e-9:
                    violations.append("m_action_range")
        except (TypeError, ValueError):
            violations.append("invalid_action_norm")

    constraint_count = sum(
        len(row.get("bess_constraint_violations", []))
        if isinstance(row.get("bess_constraint_violations", []), list)
        else 1
        for row in rows
    )
    saturation_count = sum(_nested_count(row.get("bess_saturation_reasons", [])) for row in rows)
    storage: dict[str, Any] = {
        "constraint_violation_count": int(constraint_count),
        "saturation_reason_count": int(saturation_count),
    }
    for key in STORAGE_VECTOR_FIELDS:
        if _as_array(rows, key, columns=AGENT_COUNT) is None:
            violations.append(f"missing_or_invalid_{key}")
    if not all(isinstance(row.get("bess_constraint_violations"), list) for row in rows):
        violations.append("missing_or_invalid_bess_constraint_violations")
    if not all(
        isinstance(row.get("bess_saturation_reasons"), list)
        and len(row["bess_saturation_reasons"]) == AGENT_COUNT
        for row in rows
    ):
        violations.append("missing_or_invalid_bess_saturation_reasons")
    for source_key, output_key, reducer in (
        ("bess_actual_power_system_pu", "max_abs_actual_power_system_pu", "max_abs"),
        (
            "bess_commanded_power_system_pu",
            "max_abs_commanded_power_system_pu",
            "max_abs",
        ),
        ("bess_requested_power_system_pu", "max_abs_requested_power_system_pu", "max_abs"),
        ("bess_soc", "min_soc", "min"),
        ("bess_soc", "max_soc", "max"),
        ("bess_charge_energy_mwh_total", "max_charge_energy_mwh", "max"),
        ("bess_discharge_energy_mwh_total", "max_discharge_energy_mwh", "max"),
    ):
        values = _as_array(rows, source_key, columns=AGENT_COUNT)
        if values is None:
            continue
        if reducer == "max_abs":
            storage[output_key] = float(np.max(np.abs(values)))
        elif reducer == "min":
            storage[output_key] = float(np.min(values))
        else:
            storage[output_key] = float(np.max(values))
    if constraint_count:
        violations.append("storage_constraint_violation")
    if saturation_count:
        violations.append("storage_saturation")
    if storage.get("min_soc", 0.0) < 0.0 or storage.get("max_soc", 1.0) > 1.0:
        violations.append("soc_out_of_bounds")
    return action, storage, sorted(set(violations))


def _verify_sidecars(
    trace_paths: Sequence[Path],
    trace_hashes: Mapping[str, str],
) -> dict[str, Any]:
    verified = 0
    missing: list[str] = []
    mismatched: list[str] = []
    provided = 0
    for path in trace_paths:
        sidecar = path.with_suffix(path.suffix + ".sha256")
        if not sidecar.is_file():
            missing.append(path.name)
            continue
        provided += 1
        expected = sidecar.read_text(encoding="utf-8").strip().split()[0]
        if expected == trace_hashes[path.name]:
            verified += 1
        else:
            mismatched.append(path.name)
    if provided == 0:
        status = "not_provided"
        passed = False
    elif missing or mismatched:
        status = "failed"
        passed = False
    else:
        status = "all_verified"
        passed = True
    return {
        "status": status,
        "pass": passed,
        "verified_count": verified,
        "missing": missing,
        "mismatched": mismatched,
    }


def _controller_identity(name: str) -> dict[str, Any]:
    match = CONTROLLER_PATTERN.fullmatch(name)
    if match:
        return {
            "family": match.group(1),
            "training_seed": int(match.group(2)),
            "learned": True,
        }
    return {
        "family": name,
        "training_seed": None,
        "learned": name not in {"q0", "causal"},
    }


def _plain_summary(values: Mapping[str, float]) -> dict[str, Any]:
    array = np.asarray(list(values.values()), dtype=float)
    return {
        "n": int(array.size),
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "minimum": float(np.min(array)),
        "maximum": float(np.max(array)),
    }


def _aggregate_storage(rows: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    keys = set().union(*(set(row) for row in rows.values()))
    for key in sorted(keys):
        values = [float(row[key]) for row in rows.values() if key in row]
        if not values:
            continue
        if key.startswith("min_"):
            result[key] = float(min(values))
        elif key.endswith("_count"):
            result[key] = int(sum(values))
        else:
            result[key] = float(max(values))
    return result


def _family_effects(
    endpoints: Mapping[str, Mapping[str, Mapping[str, float]]],
    *,
    baseline: str,
    resamples: int,
    seed: int,
) -> dict[str, Any]:
    families: dict[str, dict[int, Mapping[str, Mapping[str, float]]]] = defaultdict(dict)
    for controller, scenario_rows in endpoints.items():
        identity = _controller_identity(controller)
        training_seed = identity["training_seed"]
        if training_seed is not None:
            families[str(identity["family"])][int(training_seed)] = scenario_rows
    baseline_rows = endpoints[baseline]
    result: dict[str, Any] = {
        "method": "two-level bootstrap over training seeds then shared scenarios",
        "comparisons": {},
    }

    def calculate(
        name: str,
        left_family: str,
        right_family: str | None,
    ) -> None:
        left = families.get(left_family, {})
        right = families.get(right_family, {}) if right_family else None
        if len(left) < 2:
            result["comparisons"][name] = {
                "status": "unavailable",
                "reason": "at least two training seeds are required",
            }
            return
        if right is not None and set(left) != set(right):
            result["comparisons"][name] = {
                "status": "unavailable",
                "reason": "learned families do not share matched seed IDs",
            }
            return
        metrics: dict[str, Any] = {}
        for offset, metric in enumerate(PERFORMANCE_METRICS):
            left_by_seed = {
                seed_id: {
                    scenario: float(values[metric]) for scenario, values in scenario_rows.items()
                }
                for seed_id, scenario_rows in left.items()
            }
            right_by_seed = (
                {
                    seed_id: {
                        scenario: float(values[metric])
                        for scenario, values in scenario_rows.items()
                    }
                    for seed_id, scenario_rows in right.items()
                }
                if right is not None
                else None
            )
            right_fixed = (
                {scenario: float(values[metric]) for scenario, values in baseline_rows.items()}
                if right is None
                else None
            )
            arrays = [value for rows in left_by_seed.values() for value in rows.values()]
            if right_by_seed is not None:
                arrays.extend(value for rows in right_by_seed.values() for value in rows.values())
            else:
                assert right_fixed is not None
                arrays.extend(right_fixed.values())
            if any(value <= 0.0 for value in arrays):
                metrics[metric] = {
                    "status": "unavailable",
                    "reason": "ratio bootstrap requires strictly positive endpoints",
                }
                continue
            metrics[metric] = hierarchical_seed_scenario_ratio_bootstrap(
                left_by_seed,
                right_by_seed=right_by_seed,
                right_deterministic=right_fixed,
                resamples=resamples,
                seed=seed + offset,
            )
        result["comparisons"][name] = {"status": "available", "metrics": metrics}

    if "centralized" in families:
        calculate("centralized_minus_baseline", "centralized", None)
    if "shared" in families:
        calculate("shared_minus_baseline", "shared", None)
    if "centralized" in families and "shared" in families:
        calculate("shared_minus_centralized", "shared", "centralized")
    if not result["comparisons"]:
        result["status"] = "unavailable"
        result["reason"] = "no recognized multi-seed learned controller families"
    else:
        result["status"] = "available"
    return result


def evaluate_trace_directory(
    trace_dir: str | Path,
    *,
    baseline: str = "q0",
    bootstrap_resamples: int = 10_000,
    bootstrap_seed: int = 2026073101,
    tail_fraction: float = 0.10,
    q_audit_tolerance: float = 1e-9,
) -> dict[str, Any]:
    """Evaluate one complete controller-by-scenario trace matrix."""
    directory = Path(trace_dir)
    if not directory.is_dir():
        raise EvaluationContractError(f"trace directory does not exist: {directory}")
    if bootstrap_resamples < 100:
        raise EvaluationContractError("bootstrap_resamples must be at least 100")
    if not 0.0 < tail_fraction <= 1.0:
        raise EvaluationContractError("tail_fraction must be in (0, 1]")
    if not math.isfinite(q_audit_tolerance) or q_audit_tolerance < 0.0:
        raise EvaluationContractError("q_audit_tolerance must be finite and non-negative")

    trace_paths = sorted(directory.glob("*.json"))
    if not trace_paths:
        raise EvaluationContractError(f"no JSON traces found in {directory}")
    trace_hashes = {path.name: _sha256_file(path) for path in trace_paths}
    records = [(path, _load_record(path)) for path in trace_paths]
    keyed: dict[tuple[str, str], tuple[Path, dict[str, Any]]] = {}
    for path, record in records:
        key = (str(record["controller"]), str(record["scenario"]))
        if key in keyed:
            raise EvaluationContractError(f"duplicate controller/scenario pair: {key}")
        keyed[key] = (path, record)
    controllers = sorted({key[0] for key in keyed}, key=lambda name: (name != baseline, name))
    scenarios = sorted({key[1] for key in keyed})
    if baseline not in controllers:
        raise EvaluationContractError(f"baseline controller not found: {baseline}")
    missing_pairs = [
        f"{scenario}/{controller}"
        for controller in controllers
        for scenario in scenarios
        if (controller, scenario) not in keyed
    ]
    if missing_pairs:
        raise EvaluationContractError(
            f"incomplete paired matrix; missing {len(missing_pairs)} pairs: "
            + ", ".join(missing_pairs[:5])
        )
    for scenario in scenarios:
        _, baseline_record = keyed[(baseline, scenario)]
        baseline_time, _, _ = _trace_arrays(baseline_record)
        baseline_active_steps = _active_steps(
            baseline_record,
            len(baseline_record["traces"]),
        )
        for controller in controllers:
            _, candidate_record = keyed[(controller, scenario)]
            candidate_time, _, _ = _trace_arrays(candidate_record)
            candidate_active_steps = _active_steps(
                candidate_record,
                len(candidate_record["traces"]),
            )
            if (
                candidate_time.shape != baseline_time.shape
                or not np.allclose(
                    candidate_time,
                    baseline_time,
                    rtol=0.0,
                    atol=1e-12,
                )
                or candidate_active_steps != baseline_active_steps
            ):
                raise EvaluationContractError(
                    f"{scenario}/{controller}: paired time grid or active window "
                    f"does not match {baseline}"
                )

    metric_rows: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    legacy_rows: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    action_rows: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    storage_rows: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    action_violations: list[dict[str, Any]] = []
    for controller in controllers:
        for scenario in scenarios:
            _, record = keyed[(controller, scenario)]
            metrics, legacy = _trace_metrics(record)
            action, storage, violations = _action_and_storage(
                record,
                q_audit_tolerance=q_audit_tolerance,
            )
            metric_rows[controller][scenario] = metrics
            legacy_rows[controller][scenario] = legacy
            action_rows[controller][scenario] = action
            storage_rows[controller][scenario] = storage
            if violations:
                action_violations.append(
                    {
                        "controller": controller,
                        "scenario": scenario,
                        "failed_checks": violations,
                    }
                )

    provenance_values: dict[str, set[str]] = {
        "formal_bank_sha256": set(),
        "formal_seal_sha256": set(),
    }
    for _, record in records:
        for key in provenance_values:
            value = record.get(key)
            if value:
                provenance_values[key].add(str(value))
    provenance_present = all(
        bool(record.get(key)) for _, record in records for key in provenance_values
    )
    provenance_pass = provenance_present and all(
        len(values) == 1 for values in provenance_values.values()
    )
    sidecars = _verify_sidecars(trace_paths, trace_hashes)
    overall_pass = not action_violations and provenance_pass and sidecars["pass"]

    controller_summaries: dict[str, Any] = {}
    for controller in controllers:
        metric_summaries = {
            metric: empirical_upper_tail(
                {scenario: metric_rows[controller][scenario][metric] for scenario in scenarios},
                tail_fraction=tail_fraction,
            )
            for metric in PERFORMANCE_METRICS
        }
        action_keys = set().union(*(set(row) for row in action_rows[controller].values()))
        action_summaries = {
            key: empirical_upper_tail(
                {
                    scenario: action_rows[controller][scenario][key]
                    for scenario in scenarios
                    if key in action_rows[controller][scenario]
                },
                tail_fraction=tail_fraction,
            )
            for key in sorted(action_keys)
        }
        controller_summaries[controller] = {
            "identity": _controller_identity(controller),
            "scenario_count": len(scenarios),
            "metrics": metric_summaries,
            "action_diagnostics": action_summaries,
            "storage_diagnostics": _aggregate_storage(storage_rows[controller]),
            "legacy_compatibility": {
                "paper_cum_rf_sum_hz2": _plain_summary(
                    {
                        scenario: legacy_rows[controller][scenario]["paper_cum_rf_sum_hz2"]
                        for scenario in scenarios
                    }
                ),
                "not_used_for_ranking": True,
            },
        }

    endpoints_for_bootstrap = {
        controller: {
            metric: [metric_rows[controller][scenario][metric] for scenario in scenarios]
            for metric in PERFORMANCE_METRICS
        }
        for controller in controllers
    }
    contrasts = [
        (f"{controller}_minus_{baseline}", controller, baseline)
        for controller in controllers
        if controller != baseline
    ]
    paired = (
        paired_bootstrap_contrasts(
            endpoints_for_bootstrap,
            contrasts=contrasts,
            seed=bootstrap_seed,
            n_resamples=bootstrap_resamples,
        )
        if contrasts
        else {
            "seed": bootstrap_seed,
            "n_resamples": bootstrap_resamples,
            "confidence": 0.95,
            "shared_index_resampling": True,
            "contrasts": {},
        }
    )

    manifest_payload = json.dumps(
        trace_hashes,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    failed_checks = Counter(check for row in action_violations for check in row["failed_checks"])
    scorecard = {
        "schema_version": SCHEMA_VERSION,
        "contract": {
            "name": "EVAL-v2-objective-controller-scorecard",
            "status": "POST_HOC_DIAGNOSTIC",
            "canonical_evidence": False,
            "frequency_basis": "andes_physical_hz",
            "baseline": baseline,
            "all_performance_metrics_lower_is_better": True,
            "performance_metrics": list(PERFORMANCE_METRICS),
            "primary_metrics": list(PRIMARY_METRICS),
            "tail_fraction": tail_fraction,
            "bootstrap_resamples": bootstrap_resamples,
            "bootstrap_seed": bootstrap_seed,
            "q_audit_tolerance": q_audit_tolerance,
            "no_composite_score_or_rank": True,
        },
        "source": {
            "trace_directory": str(directory.resolve()),
            "trace_count": len(trace_paths),
            "controller_count": len(controllers),
            "scenario_count": len(scenarios),
            "controllers": controllers,
            "scenarios": scenarios,
            "trace_sha256": trace_hashes,
            "input_manifest_sha256": _sha256_bytes(manifest_payload),
            "provenance_values": {key: sorted(values) for key, values in provenance_values.items()},
        },
        "validity": {
            "overall_pass": overall_pass,
            "evidence_eligible": overall_pass,
            "interpretation": (
                "valid_post_hoc_diagnostic"
                if overall_pass
                else "invalid_diagnostic_only_do_not_make_performance_claims"
            ),
            "complete_paired_matrix": True,
            "physical_frequency_basis": True,
            "provenance_consistent": provenance_pass,
            "sidecar_sha256": sidecars,
            "action_contract": {
                "pass": not action_violations,
                "violation_count": len(action_violations),
                "failed_check_counts": dict(sorted(failed_checks.items())),
                "violations": action_violations,
            },
        },
        "controllers": controller_summaries,
        "paired_vs_baseline": paired,
        "family_effects": _family_effects(
            metric_rows,
            baseline=baseline,
            resamples=bootstrap_resamples,
            seed=bootstrap_seed + 100,
        ),
        "legacy_compatibility": {
            "paper_probe": "Yang2023 global cumulative frequency reward",
            "identity": (
                "paper_cum_rf_sum_hz2 = -time_steps * agent_count * normalized_sync_loss_hz2"
            ),
            "scope": "exact only for the same trace, units, agents, and horizon",
            "warning": (
                "This probe measures differential synchronization only; "
                "it cannot establish common-mode frequency restoration."
            ),
        },
        "interpretation_rules": [
            "Validity is a hard gate; invalid outputs are diagnostic only.",
            "Use paired effects and confidence intervals, not unpaired means.",
            "Inspect empirical upper-tail risk and retained failures.",
            "Keep action and constraint diagnostics architecture-specific.",
            "Do not collapse endpoints into a composite winner score.",
            "A post-hoc scorecard cannot replace a prospectively sealed evaluation.",
        ],
    }
    return scorecard


def _format_number(value: float | None, digits: int = 5) -> str:
    if value is None:
        return "NA"
    return f"{float(value):.{digits}g}"


def render_markdown(scorecard: Mapping[str, Any]) -> str:
    """Render a compact, human-auditable scorecard."""
    valid = bool(scorecard["validity"]["overall_pass"])
    status = "**VALID POST-HOC DIAGNOSTIC**" if valid else "**INVALID / DIAGNOSTIC ONLY**"
    contract = scorecard["contract"]
    source = scorecard["source"]
    baseline = str(contract["baseline"])
    controllers = list(source["controllers"])
    lines = [
        "# EVAL-v2 objective scorecard",
        "",
        f"Status: {status}",
        "",
        (
            f"Input: {source['trace_count']} traces, {source['scenario_count']} paired "
            f"scenarios, {source['controller_count']} controllers. "
            f"Baseline: `{baseline}`. Frequency basis: "
            f"`{contract['frequency_basis']}`."
        ),
        "",
        "No composite score or winner rank is produced.",
        "",
        "## Validity gate",
        "",
        "| Check | Result |",
        "|---|---:|",
        f"| Complete paired matrix | {scorecard['validity']['complete_paired_matrix']} |",
        f"| Physical 60-Hz basis | {scorecard['validity']['physical_frequency_basis']} |",
        f"| Provenance consistent | {scorecard['validity']['provenance_consistent']} |",
        f"| SHA-256 sidecars | {scorecard['validity']['sidecar_sha256']['status']} |",
        (
            "| Action/storage contract | "
            f"{scorecard['validity']['action_contract']['pass']} "
            f"({scorecard['validity']['action_contract']['violation_count']} failing traces) |"
        ),
        "",
    ]
    failed_counts = scorecard["validity"]["action_contract"]["failed_check_counts"]
    if failed_counts:
        lines.extend(
            [
                "Failed checks: "
                + ", ".join(f"`{key}`={value}" for key, value in failed_counts.items()),
                "",
            ]
        )

    lines.extend(
        [
            "## Physical endpoints",
            "",
            "All values are controller means across paired scenarios; lower is better.",
            "",
            (
                "| Controller | Sync loss (Hz^2) | Fast inter-area IAE (Hz*s) | "
                "Full common IAE (Hz*s) | Worst-bus peak (Hz) |"
            ),
            "|---|---:|---:|---:|---:|",
        ]
    )
    for controller in controllers:
        metrics = scorecard["controllers"][controller]["metrics"]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{controller}`",
                    _format_number(metrics["normalized_sync_loss_hz2"]["mean"]),
                    _format_number(metrics["fast_inter_area_iae_hz_s"]["mean"]),
                    _format_number(metrics["vsg_mean_iae_hz_s"]["mean"]),
                    _format_number(metrics["worst_bus_peak_abs_hz"]["mean"]),
                ]
            )
            + " |"
        )

    contrasts = scorecard["paired_vs_baseline"]["contrasts"]
    if contrasts:
        lines.extend(
            [
                "",
                "## Paired effects versus baseline",
                "",
                "Ratio-of-means effects are percentages; negative favours the left controller.",
                "",
                "| Contrast | Endpoint | Effect [95% CI] | Improved scenarios |",
                "|---|---|---:|---:|",
            ]
        )
        for name, contrast in contrasts.items():
            for metric in PRIMARY_METRICS:
                endpoint = contrast["endpoints"][metric]
                relative = endpoint["ratio_of_means_percent"]
                interval = relative["percentile_95_interval"]
                effect = (
                    "NA"
                    if relative["point"] is None
                    else (
                        f"{_format_number(relative['point'])}% "
                        f"[{_format_number(interval[0])}, {_format_number(interval[1])}]"
                    )
                )
                lines.append(
                    f"| `{name}` | `{metric}` | {effect} | "
                    f"{endpoint['scenario_improvement_count']}/{contrast['n_paired']} |"
                )

    lines.extend(
        [
            "",
            "## Tail risk and execution",
            "",
            (
                "| Controller | Sync-loss max / upper-tail CVaR | "
                "Worst-bus peak max / upper-tail CVaR | Max abs(q) | Max q slew | "
                "Constraint events |"
            ),
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for controller in controllers:
        row = scorecard["controllers"][controller]
        sync = row["metrics"]["normalized_sync_loss_hz2"]
        peak = row["metrics"]["worst_bus_peak_abs_hz"]
        action = row["action_diagnostics"]
        storage = row["storage_diagnostics"]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{controller}`",
                    (
                        f"{_format_number(sync['maximum'])} / "
                        f"{_format_number(sync['cvar_upper_tail'])}"
                    ),
                    (
                        f"{_format_number(peak['maximum'])} / "
                        f"{_format_number(peak['cvar_upper_tail'])}"
                    ),
                    _format_number(action.get("max_abs_q", {}).get("maximum")),
                    _format_number(action.get("max_abs_q_slew_per_step", {}).get("maximum")),
                    str(storage.get("constraint_violation_count", 0)),
                ]
            )
            + " |"
        )

    family = scorecard["family_effects"]
    if family.get("comparisons"):
        lines.extend(
            [
                "",
                "## Training-seed family effects",
                "",
                "| Comparison | Endpoint | Effect [95% CI] |",
                "|---|---|---:|",
            ]
        )
        for name, comparison in family["comparisons"].items():
            if comparison["status"] != "available":
                lines.append(f"| `{name}` | unavailable | {comparison['reason']} |")
                continue
            for metric in PRIMARY_METRICS:
                result = comparison["metrics"][metric]
                if result.get("status") == "unavailable":
                    lines.append(f"| `{name}` | `{metric}` | unavailable |")
                    continue
                effect = result["ratio_of_means_percent"]
                interval = effect["percentile_95_interval"]
                lines.append(
                    f"| `{name}` | `{metric}` | {_format_number(effect['point'])}% "
                    f"[{_format_number(interval[0])}, {_format_number(interval[1])}] |"
                )

    legacy = scorecard["legacy_compatibility"]
    lines.extend(
        [
            "",
            "## Relationship to the old paper probe",
            "",
            f"`{legacy['identity']}`.",
            "",
            f"Boundary: {legacy['warning']}",
            "",
            "## Interpretation boundary",
            "",
        ]
    )
    lines.extend(f"- {rule}" for rule in scorecard["interpretation_rules"])
    lines.append("")
    return "\n".join(lines)


def write_scorecard(
    scorecard: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, str]:
    """Write deterministic JSON/Markdown artifacts and SHA-256 sidecars."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "scorecard.json"
    markdown_path = directory / "scorecard.md"
    targets = (json_path, markdown_path)
    if not overwrite and any(path.exists() for path in targets):
        existing = [str(path) for path in targets if path.exists()]
        raise FileExistsError(f"refusing to overwrite existing scorecard: {existing}")
    json_bytes = (
        json.dumps(scorecard, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    markdown_bytes = render_markdown(scorecard).encode("utf-8")
    json_path.write_bytes(json_bytes)
    markdown_path.write_bytes(markdown_bytes)
    for path, data in ((json_path, json_bytes), (markdown_path, markdown_bytes)):
        sidecar = path.with_suffix(path.suffix + ".sha256")
        sidecar.write_text(
            f"{_sha256_bytes(data)}  {path.name}\n",
            encoding="utf-8",
        )
    return {
        "json": str(json_path.resolve()),
        "markdown": str(markdown_path.resolve()),
        "json_sha256": _sha256_bytes(json_bytes),
        "markdown_sha256": _sha256_bytes(markdown_bytes),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build an objective EVAL-v2 scorecard from completed paired four-VSG trace JSON files."
        )
    )
    parser.add_argument("--trace-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--baseline", default="q0")
    parser.add_argument("--bootstrap-resamples", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=2026073101)
    parser.add_argument("--tail-fraction", type=float, default=0.10)
    parser.add_argument("--q-audit-tolerance", type=float, default=1e-9)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; invalid scorecards are written but return exit code 2."""
    args = _parser().parse_args(argv)
    scorecard = evaluate_trace_directory(
        args.trace_dir,
        baseline=args.baseline,
        bootstrap_resamples=args.bootstrap_resamples,
        bootstrap_seed=args.bootstrap_seed,
        tail_fraction=args.tail_fraction,
        q_audit_tolerance=args.q_audit_tolerance,
    )
    outputs = write_scorecard(scorecard, args.output_dir, overwrite=args.overwrite)
    print(json.dumps({"validity": scorecard["validity"], "outputs": outputs}, indent=2))
    return 0 if scorecard["validity"]["overall_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
