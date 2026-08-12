"""R379 Gate B-3 frozen contract, guards, endpoints, and classification.

This module holds the byte-frozen R379 successor contract from
``paper/paralleled_vsg_marl/working/gate_b3_deterministic_physical_contract.md``.
It adapts the R376 guard/endpoint/selection structure with high-pass damping
candidates, disturbance-driven differential oscillation as primary endpoints,
and probe cross-response as a no-harm ceiling.  It is not a copy of any frozen
classifier; the R374/R375/R376 analysis modules remain immutable.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

MODES = {
    "common": [1.0, 1.0, 1.0, 1.0],
    "inter_area": [1.0, 1.0, -1.0, -1.0],
    "local_area_1": [1.0, -1.0, 0.0, 0.0],
    "local_area_2": [0.0, 0.0, 1.0, -1.0],
}

LOCAL_ARM = "local_feasibility_native"
ZERO_ARM = "zero_feedback"
SELECTED_ARM = "selected_distributed_lowhp_damping"
HIGH_PASS_ALPHA = 0.90


def _candidate_id(sync_gain: float, consensus_gain: float) -> str:
    return (
        f"distributed_lowhp_damping_ks{sync_gain:g}_kc{consensus_gain:g}_alpha0p9"
    ).replace(".", "p")


def build_contract() -> dict[str, Any]:
    """Return the JSON-safe frozen R377 Gate B-2 contract."""
    candidates = [
        {
            "arm_id": _candidate_id(sync_gain, consensus_gain),
            "sync_gain_per_hz": sync_gain,
            "consensus_gain_per_s": consensus_gain,
            "highpass_alpha": HIGH_PASS_ALPHA,
        }
        for sync_gain in (0.5, 1.0)
        for consensus_gain in (0.5, 1.0)
    ]
    probe_arms = [
        f"{mode}_{sign}"
        for mode in MODES
        for sign in ("positive", "negative")
    ]
    development_arms = [ZERO_ARM, LOCAL_ARM, *[c["arm_id"] for c in candidates]]
    evaluation_arms = [ZERO_ARM, LOCAL_ARM, SELECTED_ARM]
    return {
        "schema_version": 1,
        "round": "R379",
        "device_count": 4,
        "expected_vsg_idx": ["VSG_1", "VSG_2", "VSG_3", "VSG_4"],
        "expected_vsg_buses": [12, 16, 14, 15],
        "seed": 42,
        "steps": 50,
        "dt_seconds": 0.2,
        "nominal_frequency_hz": 60.0,
        "soc_min": 0.20,
        "soc_max": 0.80,
        "soc_initial": 0.50,
        "modes": MODES,
        "mode_ids": list(MODES),
        "probe_component_action": 0.25,
        "controller_action_clip": 0.70,
        "highpass_alpha": HIGH_PASS_ALPHA,
        "adjacency": {"0": [1, 3], "1": [0, 2], "2": [1, 3], "3": [2, 0]},
        "local_gains": {
            "kp_n_per_hz": 4.0,
            "ki_n_per_hz_s": 0.8,
        },
        "distributed_candidates": candidates,
        "probe_arm_ids": probe_arms,
        "development": {
            "arm_ids": development_arms,
            "probe_condition": {
                "condition_id": "dev3_probe_bus15_minus_0p45",
                "delta_u": {"PQ_Bus15": -0.45},
            },
            "disturbance_conditions": [
                {
                    "condition_id": "dev3_disturbance_pq1_plus_0p65",
                    "delta_u": {"PQ_1": 0.65},
                },
                {
                    "condition_id": "dev3_disturbance_bus14_minus_0p55",
                    "delta_u": {"PQ_Bus14": -0.55},
                },
            ],
            "record_count": len(development_arms) * (len(probe_arms) + 2),
        },
        "evaluation": {
            "arm_ids": evaluation_arms,
            "probe_condition": {
                "condition_id": "eval3_probe_pq0_minus_0p40",
                "delta_u": {"PQ_0": -0.40},
            },
            "disturbance_conditions": [
                {
                    "condition_id": "eval3_disturbance_pq0_plus_0p60",
                    "delta_u": {"PQ_0": 0.60},
                },
                {
                    "condition_id": "eval3_disturbance_bus15_plus_0p55",
                    "delta_u": {"PQ_Bus15": 0.55},
                },
            ],
            "record_count": len(evaluation_arms) * (len(probe_arms) + 2),
        },
        "thresholds": {
            "development_primary_ratio_max": 0.98,
            "development_settling_dt_improvement": 1,
            "heldout_primary_ratio_max": 0.95,
            "single_disturbance_ratio_max": 1.10,
            "common_iae_ratio_max": 1.05,
            "peak_and_rocof_ratio_max": 1.10,
            "probe_cross_no_harm_ratio_max": 1.10,
            "settling_band_hz": 0.01,
            "zero_sum_atol": 1.0e-12,
            "numeric_atol": 1.0e-9,
            "action_rank_tolerance": 1.0e-9,
        },
        "training_authorized": False,
    }


def probe_request(
    input_mode: str,
    sign: str,
    *,
    contract: Mapping[str, Any] | None = None,
) -> np.ndarray:
    """Return one frozen additive probe vector in the normalized-action domain."""
    frozen = contract or build_contract()
    if input_mode not in frozen["modes"] or sign not in {"positive", "negative"}:
        raise ValueError("unknown probe mode or sign")
    direction = 1.0 if sign == "positive" else -1.0
    return (
        direction
        * float(frozen["probe_component_action"])
        * np.asarray(frozen["modes"][input_mode], dtype=float)
    )


def phase_jobs(
    phase: str,
    *,
    selected_arm_id: str | None = None,
    contract: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Expand one frozen phase into its ordered independent trajectories."""
    frozen = contract or build_contract()
    if phase not in {"development", "evaluation"}:
        raise ValueError("phase must be development or evaluation")
    phase_contract = frozen[phase]
    arm_ids = list(phase_contract["arm_ids"])
    if phase == "evaluation":
        candidate_ids = {
            str(candidate["arm_id"])
            for candidate in frozen["distributed_candidates"]
        }
        if selected_arm_id not in candidate_ids:
            raise ValueError("evaluation requires one registered selected candidate")
        arm_ids = [
            selected_arm_id if arm == SELECTED_ARM else arm for arm in arm_ids
        ]
    jobs: list[dict[str, Any]] = []
    probe_condition = phase_contract["probe_condition"]
    for arm_id in arm_ids:
        for input_mode in frozen["mode_ids"]:
            for sign in ("positive", "negative"):
                jobs.append(
                    {
                        "order": len(jobs),
                        "phase": phase,
                        "arm_id": arm_id,
                        "experiment_kind": "probe",
                        "condition_id": probe_condition["condition_id"],
                        "delta_u": dict(probe_condition["delta_u"]),
                        "input_mode": input_mode,
                        "sign": sign,
                    }
                )
        for condition in phase_contract["disturbance_conditions"]:
            jobs.append(
                {
                    "order": len(jobs),
                    "phase": phase,
                    "arm_id": arm_id,
                    "experiment_kind": "disturbance",
                    "condition_id": condition["condition_id"],
                    "delta_u": dict(condition["delta_u"]),
                    "input_mode": None,
                    "sign": None,
                }
            )
    if len(jobs) != int(phase_contract["record_count"]):
        raise RuntimeError("expanded jobs do not match the frozen record count")
    return jobs


def controller_spec(
    arm_id: str,
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve one arm to its frozen runtime controller parameters."""
    frozen = contract or build_contract()
    local = frozen["local_gains"]
    if arm_id == ZERO_ARM:
        return {"architecture": "zero_feedback"}
    if arm_id == LOCAL_ARM:
        return {
            "architecture": "local_feasibility_native",
            "kp_n_per_hz": float(local["kp_n_per_hz"]),
            "ki_n_per_hz_s": float(local["ki_n_per_hz_s"]),
        }
    for candidate in frozen["distributed_candidates"]:
        if arm_id == candidate["arm_id"]:
            return {
                "architecture": "distributed_lowhp_damping",
                "kp_n_per_hz": float(local["kp_n_per_hz"]),
                "ki_n_per_hz_s": float(local["ki_n_per_hz_s"]),
                "sync_gain_per_hz": float(candidate["sync_gain_per_hz"]),
                "consensus_gain_per_s": float(
                    candidate["consensus_gain_per_s"]
                ),
                "highpass_alpha": float(candidate["highpass_alpha"]),
            }
    raise ValueError(f"unknown controller arm: {arm_id}")


def project_modes(
    values: np.ndarray,
    *,
    contract: Mapping[str, Any] | None = None,
) -> np.ndarray:
    """Project device rows onto the registered arithmetic coordinates."""
    frozen = contract or build_contract()
    array = np.asarray(values, dtype=float)
    if array.ndim != 2 or array.shape[1] != int(frozen["device_count"]):
        raise ValueError("values must have shape (steps, device_count)")
    if not np.all(np.isfinite(array)):
        raise ValueError("values must be finite")
    columns = []
    for mode in frozen["mode_ids"]:
        basis = np.asarray(frozen["modes"][mode], dtype=float)
        columns.append(array @ basis / float(basis @ basis))
    return np.column_stack(columns)


def _step_matrix(record: Mapping[str, Any], key: str, *, columns: int) -> np.ndarray:
    values = np.asarray([row[key] for row in record["steps"]], dtype=float)
    if values.shape != (len(record["steps"]), columns) or not np.all(
        np.isfinite(values)
    ):
        raise ValueError(f"{key} must be a finite step-by-{columns} matrix")
    return values


def _record_guard_errors(
    records: list[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    steps_expected = int(contract["steps"])
    dt = float(contract["dt_seconds"])
    atol = float(contract["thresholds"]["numeric_atol"])
    zero_sum_atol = float(contract["thresholds"]["zero_sum_atol"])
    maximum_common_distortion = 0.0
    maximum_differential_distortion = 0.0
    command_l1_device_seconds = 0.0
    command_total_variation = 0.0
    action_l1_sum = 0.0
    headroom_fractions: list[float] = []
    bound_contact_steps = 0
    for record_index, record in enumerate(records):
        rows = list(record.get("steps", []))
        if (
            len(rows) != steps_expected
            or int(record.get("completed_steps", -1)) != steps_expected
            or bool(record.get("tds_failed"))
            or record.get("failure") is not None
        ):
            errors.append(f"record {record_index}: incomplete or failed")
            continue
        try:
            times = np.asarray([row["time"] for row in rows], dtype=float)
            if not np.all(np.isfinite(times)) or not np.allclose(
                np.diff(times), dt, atol=atol, rtol=0.0
            ):
                raise ValueError("timing drift")
            frequency = _step_matrix(record, "freq_hz_physical", columns=4)
            requested = _step_matrix(
                record, "requested_power_system_pu", columns=4
            )
            commanded = _step_matrix(
                record, "commanded_power_system_pu", columns=4
            )
            _step_matrix(record, "achieved_power_system_pu", columns=4)
            normalized = _step_matrix(record, "normalized_action", columns=4)
            common_action = _step_matrix(record, "common_action", columns=4)
            differential_action = _step_matrix(
                record, "differential_action", columns=4
            )
            _step_matrix(record, "lower_power_system_pu", columns=4)
            _step_matrix(record, "upper_power_system_pu", columns=4)
            _step_matrix(record, "zero_anchor_power_system_pu", columns=4)
            _step_matrix(record, "feasible_power_system_pu", columns=4)
            headroom = _step_matrix(record, "headroom_fraction", columns=4)
            bound = _step_matrix(record, "bound_contact", columns=4)
            soc = _step_matrix(record, "soc", columns=4)
            md = np.asarray([row["md_action_norm"] for row in rows], dtype=float)
            if md.shape != (steps_expected, 4, 2) or not np.all(np.isfinite(md)):
                raise ValueError("legacy M/D telemetry drift")
            if not np.allclose(md, 0.0, atol=atol, rtol=0.0):
                raise ValueError("legacy M/D action is nonzero")
            if np.any(soc < float(contract["soc_min"]) - atol) or np.any(
                soc > float(contract["soc_max"]) + atol
            ):
                raise ValueError("SOC outside frozen bounds")
            if np.max(np.abs(np.sum(differential_action, axis=1))) > zero_sum_atol:
                raise ValueError("differential action is not zero-sum")
            if not np.allclose(
                normalized, common_action + differential_action, atol=atol, rtol=0.0
            ):
                raise ValueError("action channel reconstruction drift")
            if np.max(np.abs(normalized)) > 1.0 + zero_sum_atol:
                raise ValueError("normalized action exceeds [-1, 1]")
            if any(
                bool(reason)
                for row in rows
                for reason in row["saturation_reasons"]
            ):
                raise ValueError("energy projection saturated")
            residual = commanded - requested
            maximum_common_distortion = max(
                maximum_common_distortion,
                float(np.max(np.abs(np.mean(residual, axis=1)))),
            )
            residual_differential = residual - np.mean(
                residual, axis=1, keepdims=True
            )
            maximum_differential_distortion = max(
                maximum_differential_distortion,
                float(np.max(np.linalg.norm(residual_differential, axis=1))),
            )
            command_l1_device_seconds += float(np.sum(np.abs(commanded)) * dt)
            prior = np.vstack([np.zeros((1, 4)), commanded[:-1]])
            command_total_variation += float(np.sum(np.abs(commanded - prior)))
            action_l1_sum += float(np.sum(np.abs(normalized)) * dt)
            headroom_fractions.extend(float(value) for value in headroom.flatten())
            bound_contact_steps += int(
                np.any(bound.astype(bool), axis=1).sum()
            )
            if not np.all(np.isfinite(frequency)):
                raise ValueError("nonfinite frequency")
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"record {record_index}: {exc}")
    return errors, {
        "maximum_common_projection_distortion_system_pu": (
            maximum_common_distortion
        ),
        "maximum_differential_projection_distortion_system_pu": (
            maximum_differential_distortion
        ),
        "command_l1_device_seconds": command_l1_device_seconds,
        "command_total_variation_system_pu": command_total_variation,
        "action_l1_action_seconds": action_l1_sum,
        "mean_headroom_fraction": (
            float(np.mean(headroom_fractions)) if headroom_fractions else 0.0
        ),
        "max_headroom_fraction": (
            float(np.max(headroom_fractions)) if headroom_fractions else 0.0
        ),
        "bound_contact_steps": bound_contact_steps,
    }


def _probe_summary(
    records: list[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    if not records:
        return {
            "diagonal_response_energy_hz2_s": 0.0,
            "off_diagonal_response_energy_hz2_s": 0.0,
            "off_diagonal_to_diagonal_energy_ratio": 0.0,
            "response_energy_matrix_hz2_s": {},
            "probed_action_rank": 0,
        }
    by_key = {
        (str(record["input_mode"]), str(record["sign"])): record
        for record in records
    }
    expected = {
        (str(mode), sign)
        for mode in contract["mode_ids"]
        for sign in ("positive", "negative")
    }
    if len(by_key) != len(records) or set(by_key) != expected:
        raise ValueError("probe records do not match the registered paired bank")
    dt = float(contract["dt_seconds"])
    nominal = float(contract["nominal_frequency_hz"])
    matrix: dict[str, dict[str, float]] = {}
    diagonal = 0.0
    off_diagonal = 0.0
    executed_actions: list[np.ndarray] = []
    for input_mode in contract["mode_ids"]:
        positive = _step_matrix(
            by_key[(str(input_mode), "positive")],
            "freq_hz_physical",
            columns=4,
        )
        negative = _step_matrix(
            by_key[(str(input_mode), "negative")],
            "freq_hz_physical",
            columns=4,
        )
        paired = 0.5 * (
            project_modes(positive - nominal, contract=contract)
            - project_modes(negative - nominal, contract=contract)
        )
        row: dict[str, float] = {}
        for output_index, output_mode in enumerate(contract["mode_ids"]):
            energy = float(dt * np.sum(np.square(paired[:, output_index])))
            row[str(output_mode)] = energy
            if output_mode == input_mode:
                diagonal += energy
            else:
                off_diagonal += energy
        matrix[str(input_mode)] = row
        executed_actions.append(
            _step_matrix(
                by_key[(str(input_mode), "positive")],
                "normalized_action",
                columns=4,
            )
        )
        executed_actions.append(
            _step_matrix(
                by_key[(str(input_mode), "negative")],
                "normalized_action",
                columns=4,
            )
        )
    rank = int(np.linalg.matrix_rank(np.vstack(executed_actions)))
    ratio = off_diagonal / diagonal if diagonal > 0.0 else float("inf")
    return {
        "diagonal_response_energy_hz2_s": diagonal,
        "off_diagonal_response_energy_hz2_s": off_diagonal,
        "off_diagonal_to_diagonal_energy_ratio": ratio,
        "response_energy_matrix_hz2_s": matrix,
        "probed_action_rank": rank,
    }


def _settling_seconds(differential: np.ndarray, *, band: float, dt: float) -> float:
    for index in range(differential.shape[0]):
        if np.all(np.abs(differential[index:]) <= band):
            return float((index + 1) * dt)
    return float(differential.shape[0] * dt)


def _disturbance_summary(
    records: list[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    dt = float(contract["dt_seconds"])
    nominal = float(contract["nominal_frequency_hz"])
    band = float(contract["thresholds"]["settling_band_hz"])
    conditions: dict[str, Any] = {}
    for record in records:
        condition_id = str(record["condition_id"])
        if condition_id in conditions:
            raise ValueError("duplicate disturbance condition")
        frequency = _step_matrix(record, "freq_hz_physical", columns=4)
        coordinates = project_modes(frequency - nominal, contract=contract)
        differential = coordinates[:, 1:]
        rocof = np.diff(frequency, axis=0) / dt
        conditions[condition_id] = {
            "differential_frequency_energy_hz2_s": float(
                dt * np.sum(np.square(differential))
            ),
            "differential_settling_seconds": _settling_seconds(
                differential,
                band=band,
                dt=dt,
            ),
            "common_frequency_iae_hz_s": float(
                dt * np.sum(np.abs(coordinates[:, 0]))
            ),
            "worst_device_peak_abs_hz": float(
                np.max(np.abs(frequency - nominal))
            ),
            "max_rocof_hz_per_s": (
                float(np.max(np.abs(rocof))) if rocof.size else 0.0
            ),
        }
    if not conditions:
        return {
            "mean_differential_frequency_energy_hz2_s": 0.0,
            "mean_differential_settling_seconds": 0.0,
            "conditions": {},
        }
    return {
        "mean_differential_frequency_energy_hz2_s": float(
            np.mean(
                [
                    row["differential_frequency_energy_hz2_s"]
                    for row in conditions.values()
                ]
            )
        ),
        "mean_differential_settling_seconds": float(
            np.mean(
                [
                    row["differential_settling_seconds"]
                    for row in conditions.values()
                ]
            )
        ),
        "conditions": conditions,
    }


def summarize_arm_records(
    records: list[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize one controller arm without selecting a comparison winner."""
    frozen = contract or build_contract()
    guard_errors, stress = _record_guard_errors(records, frozen)
    probe = [record for record in records if record["experiment_kind"] == "probe"]
    disturbance = [
        record for record in records if record["experiment_kind"] == "disturbance"
    ]
    try:
        probe_summary = _probe_summary(probe, frozen)
        disturbance_summary = _disturbance_summary(disturbance, frozen)
        rank_limit = int(frozen["device_count"])
        if probe_summary["probed_action_rank"] < rank_limit:
            guard_errors.append("action rank collapses below four")
    except (KeyError, TypeError, ValueError) as exc:
        guard_errors.append(str(exc))
        probe_summary = {
            "diagonal_response_energy_hz2_s": float("nan"),
            "off_diagonal_response_energy_hz2_s": float("nan"),
            "off_diagonal_to_diagonal_energy_ratio": float("nan"),
            "response_energy_matrix_hz2_s": {},
            "probed_action_rank": 0,
        }
        disturbance_summary = {
            "mean_differential_frequency_energy_hz2_s": float("nan"),
            "mean_differential_settling_seconds": float("nan"),
            "conditions": {},
        }
    return {
        "probe": probe_summary,
        "disturbance": disturbance_summary,
        "stress": stress,
        "guard_errors": guard_errors,
        "guards_pass": not guard_errors,
    }


def summarize_phase_records(
    records: list[Mapping[str, Any]],
    *,
    phase: str,
    selected_arm_id: str | None = None,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate one complete phase bank and summarize each controller arm."""
    frozen = contract or build_contract()
    expected_jobs = phase_jobs(
        phase,
        selected_arm_id=selected_arm_id,
        contract=frozen,
    )

    def key(row: Mapping[str, Any]) -> tuple[object, ...]:
        return (
            row.get("arm_id"),
            row.get("experiment_kind"),
            row.get("condition_id"),
            row.get("input_mode"),
            row.get("sign"),
        )

    expected = {key(job): job for job in expected_jobs}
    actual = {key(record): record for record in records}
    if (
        len(actual) != len(records)
        or set(actual) != set(expected)
        or len(records) != len(expected_jobs)
    ):
        raise ValueError(f"{phase} records do not match the frozen job bank")
    expected_identity = {
        "n_agents": int(frozen["device_count"]),
        "vsg_idx": list(frozen["expected_vsg_idx"]),
        "vsg_buses": list(frozen["expected_vsg_buses"]),
    }
    for record_key, record in actual.items():
        job = expected[record_key]
        if dict(record.get("delta_u", {})) != dict(job["delta_u"]):
            raise ValueError(f"{phase} disturbance payload drift")
        if dict(record.get("identity", {})) != expected_identity:
            raise ValueError(f"{phase} VSG identity drift")
    arm_ids = list(dict.fromkeys(str(job["arm_id"]) for job in expected_jobs))
    return {
        "phase": phase,
        "record_count": len(records),
        "arm_summaries": {
            arm_id: summarize_arm_records(
                [record for record in records if record["arm_id"] == arm_id],
                contract=frozen,
            )
            for arm_id in arm_ids
        },
    }


def _positive_ratio(numerator: object, denominator: object) -> float:
    value = float(numerator)
    reference = float(denominator)
    if not np.isfinite(value) or not np.isfinite(reference) or reference <= 0.0:
        raise ValueError("comparison endpoints must be finite with a positive baseline")
    return value / reference


def _mean_condition_metric(summary: Mapping[str, Any], metric: str) -> float:
    conditions = summary["disturbance"]["conditions"]
    values = [float(row[metric]) for row in conditions.values()]
    if not values or not np.all(np.isfinite(values)):
        raise ValueError(f"missing or nonfinite disturbance metric: {metric}")
    return float(np.mean(values))


def _probe_no_harm(
    candidate: Mapping[str, Any],
    baseline: Mapping[str, Any],
) -> tuple[float, float]:
    candidate_probe = candidate["probe"]
    baseline_probe = baseline["probe"]
    return (
        _positive_ratio(
            candidate_probe["off_diagonal_response_energy_hz2_s"],
            baseline_probe["off_diagonal_response_energy_hz2_s"],
        ),
        _positive_ratio(
            candidate_probe["off_diagonal_to_diagonal_energy_ratio"],
            baseline_probe["off_diagonal_to_diagonal_energy_ratio"],
        ),
    )


def select_development_candidate(
    summaries: Mapping[str, Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply the frozen R377 development eligibility and ranking rule."""
    frozen = contract or build_contract()
    baseline = summaries.get(LOCAL_ARM)
    if baseline is None or not bool(baseline.get("guards_pass")):
        return {
            "classification": "ANALYSIS-INVALID",
            "selected_arm_id": None,
            "eligible_candidates": [],
            "training_authorized": False,
        }
    primary_threshold = float(frozen["thresholds"]["development_primary_ratio_max"])
    common_limit = float(frozen["thresholds"]["common_iae_ratio_max"])
    cross_limit = float(frozen["thresholds"]["probe_cross_no_harm_ratio_max"])
    settling_dt_improvement = int(
        frozen["thresholds"]["development_settling_dt_improvement"]
    )
    dt = float(frozen["dt_seconds"])
    local_settling = float(
        baseline["disturbance"]["mean_differential_settling_seconds"]
    )
    eligible: list[dict[str, Any]] = []
    for candidate_spec in frozen["distributed_candidates"]:
        arm_id = str(candidate_spec["arm_id"])
        candidate = summaries.get(arm_id)
        if candidate is None or not bool(candidate.get("guards_pass")):
            continue
        differential_ratio = _positive_ratio(
            candidate["disturbance"][
                "mean_differential_frequency_energy_hz2_s"
            ],
            baseline["disturbance"][
                "mean_differential_frequency_energy_hz2_s"
            ],
        )
        candidate_settling = float(
            candidate["disturbance"]["mean_differential_settling_seconds"]
        )
        settling_improvement = (
            candidate_settling <= local_settling - settling_dt_improvement * dt
        )
        common_ratio = _positive_ratio(
            _mean_condition_metric(candidate, "common_frequency_iae_hz_s"),
            _mean_condition_metric(baseline, "common_frequency_iae_hz_s"),
        )
        offdiag_ratio, normalized_cross_ratio = _probe_no_harm(candidate, baseline)
        if (
            differential_ratio <= primary_threshold
            and settling_improvement
            and common_ratio <= common_limit
            and offdiag_ratio <= cross_limit
            and normalized_cross_ratio <= cross_limit
        ):
            eligible.append(
                {
                    "arm_id": arm_id,
                    "differential_energy_ratio": differential_ratio,
                    "settling_seconds": candidate_settling,
                    "common_iae_ratio": common_ratio,
                    "probe_offdiag_ratio": offdiag_ratio,
                    "probe_cross_ratio": normalized_cross_ratio,
                    "rank_score": (
                        differential_ratio
                        * (
                            candidate_settling
                            / local_settling
                            if local_settling > 0.0
                            else 1.0
                        )
                    ),
                    "sync_gain_per_hz": float(
                        candidate_spec["sync_gain_per_hz"]
                    ),
                    "consensus_gain_per_s": float(
                        candidate_spec["consensus_gain_per_s"]
                    ),
                }
            )
    eligible.sort(
        key=lambda row: (
            float(row["rank_score"]),
            float(row["sync_gain_per_hz"]),
            float(row["consensus_gain_per_s"]),
        )
    )
    return {
        "classification": (
            "DEVELOPMENT-CANDIDATE-SELECTED"
            if eligible
            else "STOP-DEVELOPMENT-NO-CANDIDATE"
        ),
        "selected_arm_id": eligible[0]["arm_id"] if eligible else None,
        "eligible_candidates": eligible,
        "training_authorized": False,
    }


def classify_summaries(
    development: Mapping[str, Any],
    evaluation: Mapping[str, Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify verified development selection and held-out arm summaries."""
    frozen = contract or build_contract()
    selected_id = development.get("selected_arm_id")
    if development.get("classification") != "DEVELOPMENT-CANDIDATE-SELECTED":
        return {
            "classification": str(development.get("classification")),
            "checks": {},
            "selected_arm_id": selected_id,
            "training_authorized": False,
            "next_gate": None,
        }
    if not isinstance(selected_id, str):
        return {
            "classification": "ANALYSIS-INVALID",
            "checks": {},
            "selected_arm_id": None,
            "training_authorized": False,
            "next_gate": None,
        }
    try:
        selected = evaluation[selected_id]
        baselines = [evaluation[ZERO_ARM], evaluation[LOCAL_ARM]]
    except KeyError:
        return {
            "classification": "ANALYSIS-INVALID",
            "checks": {},
            "selected_arm_id": selected_id,
            "training_authorized": False,
            "next_gate": None,
        }
    primary_limit = float(frozen["thresholds"]["heldout_primary_ratio_max"])
    single_limit = float(frozen["thresholds"]["single_disturbance_ratio_max"])
    common_limit = float(frozen["thresholds"]["common_iae_ratio_max"])
    other_limit = float(frozen["thresholds"]["peak_and_rocof_ratio_max"])
    cross_limit = float(frozen["thresholds"]["probe_cross_no_harm_ratio_max"])
    dt = float(frozen["dt_seconds"])

    differential_mean_ratios = [
        _positive_ratio(
            selected["disturbance"][
                "mean_differential_frequency_energy_hz2_s"
            ],
            baseline["disturbance"][
                "mean_differential_frequency_energy_hz2_s"
            ],
        )
        for baseline in baselines
    ]
    selected_conditions = selected["disturbance"]["conditions"]
    per_condition_pass = True
    for condition_id, row in selected_conditions.items():
        for baseline in baselines:
            baseline_row = baseline["disturbance"]["conditions"][condition_id]
            per_condition_pass = per_condition_pass and (
                _positive_ratio(
                    row["differential_frequency_energy_hz2_s"],
                    baseline_row["differential_frequency_energy_hz2_s"],
                )
                <= single_limit
            )
    selected_settling = float(
        selected["disturbance"]["mean_differential_settling_seconds"]
    )
    baseline_settling = [
        float(item["disturbance"]["mean_differential_settling_seconds"])
        for item in baselines
    ]
    settling_pass = (
        all(selected_settling <= value + 1.0e-12 for value in baseline_settling)
        and selected_settling
        <= float(evaluation[LOCAL_ARM]["disturbance"][
            "mean_differential_settling_seconds"
        ])
        - dt
        + 1.0e-12
    )
    differential_pass = (
        all(ratio <= primary_limit for ratio in differential_mean_ratios)
        and per_condition_pass
        and settling_pass
    )

    common_pass = True
    for metric, limit in (
        ("common_frequency_iae_hz_s", common_limit),
        ("worst_device_peak_abs_hz", other_limit),
        ("max_rocof_hz_per_s", other_limit),
    ):
        selected_value = _mean_condition_metric(selected, metric)
        best_baseline = min(_mean_condition_metric(item, metric) for item in baselines)
        common_pass = common_pass and selected_value <= limit * best_baseline

    no_harm_pass = True
    for baseline in baselines:
        offdiag_ratio, normalized_cross_ratio = _probe_no_harm(selected, baseline)
        no_harm_pass = no_harm_pass and (
            offdiag_ratio <= cross_limit
            and normalized_cross_ratio <= cross_limit
        )

    physical_pass = bool(selected.get("guards_pass")) and all(
        bool(item.get("guards_pass")) for item in baselines
    )
    checks = {
        "differential_oscillation_reduction": differential_pass,
        "common_mode_no_harm": common_pass,
        "probe_cross_no_harm": no_harm_pass,
        "physical_and_execution_guards": physical_pass,
    }
    if not physical_pass:
        classification = "STOP-UNSAFE-CONTROL"
    elif not differential_pass:
        classification = "STOP-NO-DIFFERENTIAL-BENEFIT"
    elif not common_pass:
        classification = "STOP-COMMON-MODE-HARM"
    elif not no_harm_pass:
        classification = "STOP-NO-HARM-EXCEEDED"
    else:
        classification = "DETERMINISTIC-DECOUPLING-PASS"
    return {
        "classification": classification,
        "checks": checks,
        "selected_arm_id": selected_id,
        "differential_mean_ratios_vs_zero_and_local": (
            differential_mean_ratios
        ),
        "probe_cross_ratios_vs_zero_and_local": [
            _probe_no_harm(selected, baseline) for baseline in baselines
        ],
        "training_authorized": False,
        "next_gate": (
            "non_learning_time_varying_headroom"
            if classification == "DETERMINISTIC-DECOUPLING-PASS"
            else None
        ),
    }
