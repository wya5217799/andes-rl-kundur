"""Bounded outcome-seeing residual witness for the four VSG power ports.

The module contains no simulator or learning dependency.  It freezes the
finite R382 candidate family, derives non-causal differential residual
schedules from immutable local-baseline traces, and classifies only the
bounded headroom contrast declared by the round.  A positive result is an
attainability witness, never a deployable controller or global optimum.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np


MODES: dict[str, list[float]] = {
    "common": [1.0, 1.0, 1.0, 1.0],
    "inter_area": [1.0, 1.0, -1.0, -1.0],
    "local_area_1": [1.0, -1.0, 0.0, 0.0],
    "local_area_2": [0.0, 0.0, 1.0, -1.0],
}


def build_contract() -> dict[str, Any]:
    """Return the JSON-safe R382 scientific contract."""

    candidate_specs = [
        {
            "candidate_id": f"amp{amplitude:.2f}_pol{polarity_name}".replace(
                ".", "p"
            ),
            "amplitude": amplitude,
            "polarity": polarity,
        }
        for amplitude in (0.25, 0.50)
        for polarity_name, polarity in (("neg", -1.0), ("pos", 1.0))
    ]
    source_jobs = [
        {
            "experiment_kind": "probe",
            "condition_id": "dev3_probe_bus15_minus_0p45",
            "delta_u": {"PQ_Bus15": -0.45},
            "input_mode": mode,
            "sign": sign,
        }
        for mode in MODES
        for sign in ("positive", "negative")
    ] + [
        {
            "experiment_kind": "disturbance",
            "condition_id": condition_id,
            "delta_u": delta_u,
            "input_mode": None,
            "sign": None,
        }
        for condition_id, delta_u in (
            ("dev3_disturbance_pq1_plus_0p65", {"PQ_1": 0.65}),
            ("dev3_disturbance_bus14_minus_0p55", {"PQ_Bus14": -0.55}),
        )
    ]
    return {
        "schema_version": 1,
        "round": "R382",
        "device_count": 4,
        "steps": 50,
        "dt_seconds": 0.2,
        "nominal_frequency_hz": 60.0,
        "expected_vsg_idx": ["VSG_1", "VSG_2", "VSG_3", "VSG_4"],
        "expected_vsg_buses": [12, 16, 14, 15],
        "soc_min": 0.20,
        "soc_max": 0.80,
        "soc_initial": 0.50,
        "modes": MODES,
        "mode_ids": list(MODES),
        "local_gains": {"kp_n_per_hz": 4.0, "ki_n_per_hz_s": 0.8},
        "probe_component_action": 0.25,
        "controller_action_clip": 0.70,
        "source_condition_count": 10,
        "source_jobs": source_jobs,
        "lead_steps": 2,
        "candidate_specs": candidate_specs,
        "candidate_record_count": 40,
        "maximum_residual_amplitude": 0.50,
        "thresholds": {
            "headroom_ratio_max": 0.95,
            "probe_diagonal_floor_ratio": 0.90,
            "common_frequency_ratio_max": 1.05,
            "peak_and_rocof_ratio_max": 1.10,
            "settling_band_hz": 0.01,
            "schedule_variation_floor": 1.0e-6,
            "numeric_atol": 1.0e-9,
        },
        "oracle_role": "non_deployable_finite_family_outcome_witness",
        "training_authorized": False,
    }


def derive_residual_schedule(
    parent_record: Mapping[str, Any],
    *,
    amplitude: float,
    polarity: float,
    lead_steps: int,
) -> np.ndarray:
    """Derive one future-shifted zero-sum residual schedule.

    The schedule uses the complete parent frequency trajectory, so it is
    intentionally non-causal.  Global trajectory normalization preserves
    relative time and device magnitudes while keeping the requested bound.
    """

    magnitude = float(amplitude)
    direction = float(polarity)
    lead = int(lead_steps)
    if not np.isfinite(magnitude) or not 0.0 < magnitude <= 1.0:
        raise ValueError("amplitude must be finite and inside (0, 1]")
    if direction not in {-1.0, 1.0}:
        raise ValueError("polarity must be -1 or +1")
    if lead < 0:
        raise ValueError("lead_steps must be non-negative")
    steps = list(parent_record.get("steps", []))
    frequency = np.asarray(
        [row["freq_hz_physical"] for row in steps],
        dtype=float,
    )
    if (
        frequency.ndim != 2
        or frequency.shape[1] != 4
        or frequency.shape[0] == 0
        or not np.all(np.isfinite(frequency))
    ):
        raise ValueError("parent frequency must be a finite step-by-four matrix")
    differential = frequency - np.mean(frequency, axis=1, keepdims=True)
    indices = np.minimum(np.arange(len(differential)) + lead, len(differential) - 1)
    shifted = differential[indices]
    scale = float(np.max(np.abs(shifted)))
    if scale <= 0.0:
        raise ValueError("parent trajectory has no differential frequency signal")
    schedule = -direction * magnitude * shifted / scale
    schedule -= np.mean(schedule, axis=1, keepdims=True)
    return schedule


def _positive_ratio(numerator: object, denominator: object) -> float:
    value = float(numerator)
    reference = float(denominator)
    if not np.isfinite(value) or not np.isfinite(reference) or reference <= 0.0:
        raise ValueError("headroom endpoints require finite positive baselines")
    return value / reference


def select_disturbance_candidate(
    baseline: Mapping[str, Any],
    candidates: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Select the lowest-energy eligible disturbance result with fallback."""

    eligible = [dict(baseline)] + [
        dict(row) for row in candidates if row.get("eligible") is True
    ]
    return min(
        eligible,
        key=lambda row: (
            float(row["differential_frequency_energy_hz2_s"]),
            str(row["candidate_id"]),
        ),
    )


def select_probe_pair(
    baseline: Mapping[str, Any],
    candidate_pairs: list[Mapping[str, Any]],
    *,
    diagonal_floor_ratio: float,
) -> dict[str, Any]:
    """Select the least cross-coupled pair without collapsing direct response."""

    floor = float(diagonal_floor_ratio) * float(
        baseline["diagonal_response_energy_hz2_s"]
    )
    eligible = [dict(baseline)] + [
        dict(row)
        for row in candidate_pairs
        if float(row["diagonal_response_energy_hz2_s"]) >= floor - 1.0e-15
    ]
    return min(
        eligible,
        key=lambda row: (
            float(row["off_diagonal_response_energy_hz2_s"]),
            float(row["off_diagonal_to_diagonal_energy_ratio"]),
            str(row["pair_id"]),
        ),
    )


def record_key(record: Mapping[str, Any]) -> tuple[str, str, str | None, str | None]:
    """Return the condition identity shared by baseline and candidates."""

    return (
        str(record.get("experiment_kind", "")),
        str(record.get("condition_id", "")),
        None if record.get("input_mode") is None else str(record["input_mode"]),
        None if record.get("sign") is None else str(record["sign"]),
    )


def _step_matrix(
    record: Mapping[str, Any],
    key: str,
    *,
    columns: int,
) -> np.ndarray:
    rows = list(record.get("steps", []))
    values = np.asarray([row[key] for row in rows], dtype=float)
    if values.shape != (len(rows), columns) or not np.all(np.isfinite(values)):
        raise ValueError(f"{key} must be a finite step-by-{columns} matrix")
    return values


def _project_modes(values: np.ndarray, contract: Mapping[str, Any]) -> np.ndarray:
    columns = []
    for mode in contract["mode_ids"]:
        basis = np.asarray(contract["modes"][mode], dtype=float)
        columns.append(values @ basis / float(basis @ basis))
    return np.column_stack(columns)


def _settling_seconds(
    differential: np.ndarray,
    *,
    band: float,
    dt: float,
) -> float:
    for index in range(differential.shape[0]):
        if np.all(np.abs(differential[index:]) <= band):
            return float((index + 1) * dt)
    return float(differential.shape[0] * dt)


def summarize_frequency_record(
    record: Mapping[str, Any],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute condition endpoints without assigning deployable meaning."""

    frozen = build_contract() if contract is None else contract
    frequency = _step_matrix(record, "freq_hz_physical", columns=4)
    dt = float(frozen["dt_seconds"])
    nominal = float(frozen["nominal_frequency_hz"])
    coordinates = _project_modes(frequency - nominal, frozen)
    differential = coordinates[:, 1:]
    rocof = np.diff(frequency, axis=0) / dt
    return {
        "differential_frequency_energy_hz2_s": float(
            dt * np.sum(np.square(differential))
        ),
        "differential_settling_seconds": _settling_seconds(
            differential,
            band=float(frozen["thresholds"]["settling_band_hz"]),
            dt=dt,
        ),
        "common_frequency_iae_hz_s": float(
            dt * np.sum(np.abs(coordinates[:, 0]))
        ),
        "worst_device_peak_abs_hz": float(np.max(np.abs(frequency - nominal))),
        "max_rocof_hz_per_s": (
            float(np.max(np.abs(rocof))) if rocof.size else 0.0
        ),
    }


def candidate_record_guard(
    record: Mapping[str, Any],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate one physical residual trajectory against the frozen seam."""

    frozen = build_contract() if contract is None else contract
    errors: list[str] = []
    rows = list(record.get("steps", []))
    expected_steps = int(frozen["steps"])
    if (
        len(rows) != expected_steps
        or int(record.get("completed_steps", -1)) != expected_steps
        or bool(record.get("tds_failed"))
        or record.get("failure") is not None
    ):
        errors.append("incomplete or failed trajectory")
    if record.get("identity") != {
        "n_agents": int(frozen["device_count"]),
        "vsg_idx": list(frozen["expected_vsg_idx"]),
        "vsg_buses": list(frozen["expected_vsg_buses"]),
    }:
        errors.append("VSG identity drift")
    if not errors:
        try:
            dt = float(frozen["dt_seconds"])
            atol = float(frozen["thresholds"]["numeric_atol"])
            times = np.asarray([row["time"] for row in rows], dtype=float)
            if not np.all(np.isfinite(times)) or not np.allclose(
                np.diff(times), dt, rtol=0.0, atol=atol
            ):
                raise ValueError("timing drift")
            _step_matrix(record, "freq_hz_physical", columns=4)
            requested = _step_matrix(
                record, "requested_power_system_pu", columns=4
            )
            commanded = _step_matrix(
                record, "commanded_power_system_pu", columns=4
            )
            _step_matrix(record, "achieved_power_system_pu", columns=4)
            residual = _step_matrix(
                record, "normalized_residual_action", columns=4
            )
            baseline = _step_matrix(
                record, "baseline_power_system_pu", columns=4
            )
            lower = _step_matrix(record, "lower_power_system_pu", columns=4)
            upper = _step_matrix(record, "upper_power_system_pu", columns=4)
            feasible = _step_matrix(
                record, "feasible_power_system_pu", columns=4
            )
            soc = _step_matrix(record, "soc", columns=4)
            md = np.asarray([row["md_action_norm"] for row in rows], dtype=float)
            if md.shape != (expected_steps, 4, 2) or not np.allclose(
                md, 0.0, rtol=0.0, atol=atol
            ):
                raise ValueError("legacy M/D action is nonzero or malformed")
            if np.max(np.abs(residual)) > float(
                frozen["maximum_residual_amplitude"]
            ) + atol:
                raise ValueError("residual bound violation")
            if np.max(np.abs(np.sum(residual, axis=1))) > atol:
                raise ValueError("residual is not zero-sum")
            variation = float(np.sum(np.abs(np.diff(residual, axis=0))))
            if variation <= float(
                frozen["thresholds"]["schedule_variation_floor"]
            ):
                raise ValueError("residual schedule is constant")
            if np.any(baseline < lower - atol) or np.any(baseline > upper + atol):
                raise ValueError("baseline power is infeasible")
            if np.any(feasible < lower - atol) or np.any(feasible > upper + atol):
                raise ValueError("residual power is infeasible")
            if not np.allclose(requested, feasible, rtol=0.0, atol=atol):
                raise ValueError("requested power differs from residual map")
            if not np.allclose(commanded, requested, rtol=0.0, atol=atol):
                raise ValueError("outer projection is not identity")
            if np.any(soc < float(frozen["soc_min"]) - atol) or np.any(
                soc > float(frozen["soc_max"]) + atol
            ):
                raise ValueError("SOC outside frozen bounds")
            if any(
                bool(reason)
                for row in rows
                for reason in row["saturation_reasons"]
            ):
                raise ValueError("energy projection saturated")
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(str(exc))
    return {"passed": not errors, "errors": errors}


def summarize_probe_pair(
    positive: Mapping[str, Any],
    negative: Mapping[str, Any],
    *,
    input_mode: str,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute direct and cross response for one signed probe pair."""

    frozen = build_contract() if contract is None else contract
    if input_mode not in frozen["mode_ids"]:
        raise ValueError("unknown input mode")
    nominal = float(frozen["nominal_frequency_hz"])
    positive_frequency = _step_matrix(
        positive, "freq_hz_physical", columns=4
    )
    negative_frequency = _step_matrix(
        negative, "freq_hz_physical", columns=4
    )
    paired = 0.5 * (
        _project_modes(positive_frequency - nominal, frozen)
        - _project_modes(negative_frequency - nominal, frozen)
    )
    input_index = list(frozen["mode_ids"]).index(input_mode)
    energy = float(frozen["dt_seconds"]) * np.sum(np.square(paired), axis=0)
    diagonal = float(energy[input_index])
    off_diagonal = float(np.sum(energy) - diagonal)
    return {
        "diagonal_response_energy_hz2_s": diagonal,
        "off_diagonal_response_energy_hz2_s": off_diagonal,
        "off_diagonal_to_diagonal_energy_ratio": (
            off_diagonal / diagonal if diagonal > 0.0 else float("inf")
        ),
    }


def _aggregate_disturbance(rows: list[Mapping[str, Any]]) -> dict[str, float]:
    if not rows:
        raise ValueError("disturbance selection is empty")
    return {
        "mean_differential_frequency_energy_hz2_s": float(
            np.mean([row["differential_frequency_energy_hz2_s"] for row in rows])
        ),
        "mean_differential_settling_seconds": float(
            np.mean([row["differential_settling_seconds"] for row in rows])
        ),
        "mean_common_frequency_iae_hz_s": float(
            np.mean([row["common_frequency_iae_hz_s"] for row in rows])
        ),
        "mean_worst_device_peak_abs_hz": float(
            np.mean([row["worst_device_peak_abs_hz"] for row in rows])
        ),
        "mean_max_rocof_hz_per_s": float(
            np.mean([row["max_rocof_hz_per_s"] for row in rows])
        ),
    }


def assemble_outcome_oracle(
    baseline_records: list[Mapping[str, Any]],
    candidate_records: list[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the privileged finite-family oracle and classify its headroom."""

    frozen = build_contract() if contract is None else contract
    expected_keys = {
        (
            str(row["experiment_kind"]),
            str(row["condition_id"]),
            row["input_mode"],
            row["sign"],
        )
        for row in frozen["source_jobs"]
    }
    baseline_by_key = {record_key(row): row for row in baseline_records}
    candidate_ids = [str(row["candidate_id"]) for row in frozen["candidate_specs"]]
    candidate_by_key: dict[tuple[tuple[str, str, str | None, str | None], str], Mapping[str, Any]] = {}
    duplicates = False
    for row in candidate_records:
        key = (record_key(row), str(row.get("candidate_id", "")))
        duplicates = duplicates or key in candidate_by_key
        candidate_by_key[key] = row
    expected_candidate_keys = {
        (source_key, candidate_id)
        for source_key in expected_keys
        for candidate_id in candidate_ids
    }
    complete = (
        not duplicates
        and set(baseline_by_key) == expected_keys
        and set(candidate_by_key) == expected_candidate_keys
        and len(candidate_records) == int(frozen["candidate_record_count"])
    )
    guards = {
        f"{source_key}|{candidate_id}": candidate_record_guard(
            record,
            contract=frozen,
        )
        for (source_key, candidate_id), record in candidate_by_key.items()
    }
    all_valid = complete and all(row["passed"] for row in guards.values())
    if not all_valid:
        decision = classify_headroom(
            {},
            {},
            all_candidate_records_valid=False,
            contract=frozen,
        )
        return {
            "baseline": None,
            "oracle": None,
            "selection": {},
            "candidate_guards": guards,
            "decision": decision,
        }

    baseline_disturbances: list[dict[str, Any]] = []
    selected_disturbances: list[dict[str, Any]] = []
    disturbance_selection: list[dict[str, Any]] = []
    common_limit = float(frozen["thresholds"]["common_frequency_ratio_max"])
    other_limit = float(frozen["thresholds"]["peak_and_rocof_ratio_max"])
    for source_key in sorted(key for key in expected_keys if key[0] == "disturbance"):
        baseline_metric = summarize_frequency_record(
            baseline_by_key[source_key], contract=frozen
        )
        baseline_metric.update(
            {"candidate_id": "baseline_fallback", "eligible": True}
        )
        candidate_metrics: list[dict[str, Any]] = []
        for candidate_id in candidate_ids:
            metric = summarize_frequency_record(
                candidate_by_key[(source_key, candidate_id)], contract=frozen
            )
            metric.update(
                {
                    "candidate_id": candidate_id,
                    "eligible": bool(
                        metric["differential_settling_seconds"]
                        <= baseline_metric["differential_settling_seconds"] + 1.0e-12
                        and metric["common_frequency_iae_hz_s"]
                        <= common_limit * baseline_metric["common_frequency_iae_hz_s"]
                        and metric["worst_device_peak_abs_hz"]
                        <= other_limit * baseline_metric["worst_device_peak_abs_hz"]
                        and metric["max_rocof_hz_per_s"]
                        <= other_limit * baseline_metric["max_rocof_hz_per_s"]
                    ),
                }
            )
            candidate_metrics.append(metric)
        selected = select_disturbance_candidate(baseline_metric, candidate_metrics)
        baseline_disturbances.append(baseline_metric)
        selected_disturbances.append(selected)
        disturbance_selection.append(
            {"source_key": source_key, "selected_candidate_id": selected["candidate_id"]}
        )

    baseline_probe_rows: list[dict[str, Any]] = []
    selected_probe_rows: list[dict[str, Any]] = []
    probe_selection: list[dict[str, Any]] = []
    probe_condition = next(
        key[1] for key in expected_keys if key[0] == "probe"
    )
    for input_mode in frozen["mode_ids"]:
        positive_key = ("probe", probe_condition, str(input_mode), "positive")
        negative_key = ("probe", probe_condition, str(input_mode), "negative")
        baseline_pair = summarize_probe_pair(
            baseline_by_key[positive_key],
            baseline_by_key[negative_key],
            input_mode=str(input_mode),
            contract=frozen,
        )
        baseline_pair["pair_id"] = "baseline_fallback"
        candidate_pairs: list[dict[str, Any]] = []
        for positive_id in candidate_ids:
            for negative_id in candidate_ids:
                pair = summarize_probe_pair(
                    candidate_by_key[(positive_key, positive_id)],
                    candidate_by_key[(negative_key, negative_id)],
                    input_mode=str(input_mode),
                    contract=frozen,
                )
                pair["pair_id"] = f"{positive_id}|{negative_id}"
                candidate_pairs.append(pair)
        selected_pair = select_probe_pair(
            baseline_pair,
            candidate_pairs,
            diagonal_floor_ratio=float(
                frozen["thresholds"]["probe_diagonal_floor_ratio"]
            ),
        )
        baseline_probe_rows.append(baseline_pair)
        selected_probe_rows.append(selected_pair)
        probe_selection.append(
            {"input_mode": input_mode, "selected_pair_id": selected_pair["pair_id"]}
        )

    def aggregate_probe(rows: list[Mapping[str, Any]]) -> dict[str, float]:
        diagonal = float(sum(row["diagonal_response_energy_hz2_s"] for row in rows))
        off_diagonal = float(
            sum(row["off_diagonal_response_energy_hz2_s"] for row in rows)
        )
        return {
            "diagonal_response_energy_hz2_s": diagonal,
            "off_diagonal_response_energy_hz2_s": off_diagonal,
            "off_diagonal_to_diagonal_energy_ratio": (
                off_diagonal / diagonal if diagonal > 0.0 else float("inf")
            ),
        }

    baseline_summary = {
        "disturbance": _aggregate_disturbance(baseline_disturbances),
        "probe": aggregate_probe(baseline_probe_rows),
    }
    oracle_summary = {
        "disturbance": _aggregate_disturbance(selected_disturbances),
        "probe": aggregate_probe(selected_probe_rows),
    }
    decision = classify_headroom(
        baseline_summary,
        oracle_summary,
        all_candidate_records_valid=True,
        contract=frozen,
    )
    return {
        "baseline": baseline_summary,
        "oracle": oracle_summary,
        "selection": {
            "disturbance": disturbance_selection,
            "probe": probe_selection,
        },
        "candidate_guards": guards,
        "decision": decision,
    }


def classify_headroom(
    baseline: Mapping[str, Any],
    oracle: Mapping[str, Any],
    *,
    all_candidate_records_valid: bool,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify the frozen joint disturbance/probe headroom contrast."""

    frozen = build_contract() if contract is None else contract
    if not all_candidate_records_valid:
        return {
            "schema_version": 1,
            "round": frozen["round"],
            "classification": "ANALYSIS-INVALID",
            "checks": {"complete_valid_candidate_bank": False},
            "training_authorized": False,
        }
    baseline_disturbance = baseline["disturbance"]
    oracle_disturbance = oracle["disturbance"]
    baseline_probe = baseline["probe"]
    oracle_probe = oracle["probe"]
    thresholds = frozen["thresholds"]
    headroom_limit = float(thresholds["headroom_ratio_max"])
    checks = {
        "complete_valid_candidate_bank": True,
        "disturbance_energy_headroom": _positive_ratio(
            oracle_disturbance["mean_differential_frequency_energy_hz2_s"],
            baseline_disturbance["mean_differential_frequency_energy_hz2_s"],
        )
        <= headroom_limit,
        "settling_no_harm": float(
            oracle_disturbance["mean_differential_settling_seconds"]
        )
        <= float(baseline_disturbance["mean_differential_settling_seconds"])
        + 1.0e-12,
        "probe_absolute_cross_headroom": _positive_ratio(
            oracle_probe["off_diagonal_response_energy_hz2_s"],
            baseline_probe["off_diagonal_response_energy_hz2_s"],
        )
        <= headroom_limit,
        "probe_normalized_cross_headroom": _positive_ratio(
            oracle_probe["off_diagonal_to_diagonal_energy_ratio"],
            baseline_probe["off_diagonal_to_diagonal_energy_ratio"],
        )
        <= headroom_limit,
        "common_frequency_no_harm": _positive_ratio(
            oracle_disturbance["mean_common_frequency_iae_hz_s"],
            baseline_disturbance["mean_common_frequency_iae_hz_s"],
        )
        <= float(thresholds["common_frequency_ratio_max"]),
        "peak_no_harm": _positive_ratio(
            oracle_disturbance["mean_worst_device_peak_abs_hz"],
            baseline_disturbance["mean_worst_device_peak_abs_hz"],
        )
        <= float(thresholds["peak_and_rocof_ratio_max"]),
        "rocof_no_harm": _positive_ratio(
            oracle_disturbance["mean_max_rocof_hz_per_s"],
            baseline_disturbance["mean_max_rocof_hz_per_s"],
        )
        <= float(thresholds["peak_and_rocof_ratio_max"]),
    }
    return {
        "schema_version": 1,
        "round": frozen["round"],
        "classification": (
            "BOUNDED-HEADROOM-WITNESS-PASS"
            if all(checks.values())
            else "STOP-NO-DETECTED-JOINT-HEADROOM"
        ),
        "checks": checks,
        "ratios": {
            "disturbance_energy": _positive_ratio(
                oracle_disturbance["mean_differential_frequency_energy_hz2_s"],
                baseline_disturbance["mean_differential_frequency_energy_hz2_s"],
            ),
            "probe_absolute_cross": _positive_ratio(
                oracle_probe["off_diagonal_response_energy_hz2_s"],
                baseline_probe["off_diagonal_response_energy_hz2_s"],
            ),
            "probe_normalized_cross": _positive_ratio(
                oracle_probe["off_diagonal_to_diagonal_energy_ratio"],
                baseline_probe["off_diagonal_to_diagonal_energy_ratio"],
            ),
        },
        "oracle_deployable": False,
        "claim_scope": "frozen finite outcome-seeing development family only",
        "next_gate": (
            "local_information_predictability"
            if all(checks.values())
            else None
        ),
        "training_authorized": False,
    }


__all__ = [
    "build_contract",
    "classify_headroom",
    "derive_residual_schedule",
    "assemble_outcome_oracle",
    "candidate_record_guard",
    "record_key",
    "select_disturbance_candidate",
    "select_probe_pair",
    "summarize_frequency_record",
    "summarize_probe_pair",
]
