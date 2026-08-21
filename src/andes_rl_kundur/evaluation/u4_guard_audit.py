"""Pure computations for the R461 U4 metric and finite-class guard audit."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


PAIR_KINDS = ("common", "differential", "localized")
TRANSFORM = np.asarray(
    [
        [0.5, 0.5, -0.5, -0.5],
        [1.0 / np.sqrt(2.0), -1.0 / np.sqrt(2.0), 0.0, 0.0],
        [0.0, 0.0, 1.0 / np.sqrt(2.0), -1.0 / np.sqrt(2.0)],
    ],
    dtype=float,
)
NUMERIC_KEYS = (
    "off_diagonal_response_energy",
    "disturbance_differential_energy",
    "common_frequency_iae_hz_s",
    "worst_unit_peak_hz",
    "worst_rocof_hz_s",
    "action_rms",
    "action_total_variation",
    "minimum_record_total_variation",
    "maximum_action_row_dispersion",
    "minimum_record_action_row_dispersion",
    "action_saturation_fraction",
)
PHASE_GUARDS = (
    "disturbance_differential_energy",
    "off_diagonal_response_energy",
    "common_frequency_iae_hz_s",
    "worst_unit_peak_hz",
    "worst_rocof_hz_s",
    "action_rms",
    "action_total_variation",
    "action_saturation_fraction",
)


def _array(value: object, shape: tuple[int, ...], name: str) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be finite with shape {shape}")
    return array


def _settling_time(response: np.ndarray, dt: float) -> float:
    norms = np.linalg.norm(response, axis=1)
    peak = float(np.max(norms))
    if peak == 0.0:
        return 0.0
    threshold = 0.02 * peak
    for index in range(norms.size):
        if np.all(norms[index:] <= threshold):
            return float((index + 1) * dt)
    return float(norms.size * dt)


def independent_profile_summary(
    records: Sequence[Mapping[str, Any]],
    profile: Mapping[str, Any],
    *,
    dt: float = 0.2,
    nominal_hz: float = 60.0,
    slew_limit: float = 0.25,
) -> dict[str, Any]:
    """Recompute a six-scenario profile directly from R460 raw rows."""

    if len(records) != 6:
        raise ValueError("exactly six records are required")
    profile_id = str(profile["profile_id"])
    expected = {str(row["scenario_id"]): row for row in profile["scenarios"]}
    if {str(row["scenario_id"]) for row in records} != set(expected):
        raise ValueError("scenario bank mismatch")
    baseline_m = _array(profile["baseline_m0"], (4,), "baseline M")
    baseline_d = _array(profile["baseline_d0"], (4,), "baseline D")
    arrays: dict[str, dict[str, np.ndarray]] = {}
    completion_rows: list[dict[str, Any]] = []
    mapping_pass = True
    bound_violation = False
    slew_violation = False
    for record in records:
        scenario_id = str(record["scenario_id"])
        rows = record.get("rows")
        if not isinstance(rows, list):
            raise ValueError("trajectory rows missing")
        frequencies = np.stack(
            [_array(row["freq_hz_physical"], (4,), "frequency") for row in rows]
        )
        actions = np.stack(
            [_array(row["executed_action"], (4, 2), "executed action") for row in rows]
        )
        previous = np.concatenate([np.zeros((1, 4, 2)), actions[:-1]], axis=0)
        differences = actions - previous
        expected_dm = np.where(actions[:, :, 0] >= 0.0, 600.0, 200.0) * actions[:, :, 0]
        expected_dd = np.where(actions[:, :, 1] >= 0.0, 600.0, 200.0) * actions[:, :, 1]
        actual_dm = np.stack(
            [_array(row["physical_command"]["delta_M"], (4,), "delta M") for row in rows]
        )
        actual_dd = np.stack(
            [_array(row["physical_command"]["delta_D"], (4,), "delta D") for row in rows]
        )
        actual_m = np.stack(
            [_array(row["physical_command"]["M_es"], (4,), "M") for row in rows]
        )
        actual_d = np.stack(
            [_array(row["physical_command"]["D_es"], (4,), "D") for row in rows]
        )
        mapping_pass = mapping_pass and all(
            (
                np.allclose(actual_dm, expected_dm, rtol=0.0, atol=3.0517578125e-5),
                np.allclose(actual_dd, expected_dd, rtol=0.0, atol=3.0517578125e-5),
                np.allclose(actual_m, np.maximum(baseline_m + expected_dm, 20.0), rtol=0.0, atol=3.0517578125e-5),
                np.allclose(actual_d, np.maximum(baseline_d + expected_dd, 10.0), rtol=0.0, atol=3.0517578125e-5),
            )
        )
        bound_violation = bound_violation or bool(np.any(np.abs(actions) > 1.0 + 1e-9))
        slew_violation = slew_violation or bool(np.any(np.abs(differences) > slew_limit + 1e-9))
        arrays[scenario_id] = {
            "frequencies": frequencies,
            "actions": actions,
            "differences": differences,
            "initial": _array(record["initial_frequency_hz"], (4,), "initial frequency"),
        }
        completion_rows.append(
            {
                "scenario_id": scenario_id,
                "attempted_steps": int(record.get("attempted_steps", len(rows))),
                "row_count": len(rows),
                "completed": bool(record.get("completed")),
                "tds_failed": bool(record.get("tds_failed")),
                "failure": record.get("failure"),
                "valid_row_count": sum(row.get("valid") is True for row in rows),
                "invalid_row_count": sum(row.get("valid") is not True for row in rows),
                "tds_row_count": sum(row.get("tds_failed") is True for row in rows),
            }
        )

    pair_responses: dict[str, dict[str, Any]] = {}
    for kind in PAIR_KINDS:
        positive = arrays[f"{profile_id}_{kind}_positive"]["frequencies"] - nominal_hz
        negative = arrays[f"{profile_id}_{kind}_negative"]["frequencies"] - nominal_hz
        odd = 0.5 * (positive - negative)
        pair_responses[kind] = {
            "common": np.mean(odd, axis=1),
            "differential": odd @ TRANSFORM.T,
            "magnitude": float(expected[f"{profile_id}_{kind}_positive"]["magnitude"]),
        }
    normalizers = {kind: float(row["magnitude"]) ** 2 for kind, row in pair_responses.items()}
    if not all(np.isfinite(value) and value > 1e-12 for value in normalizers.values()):
        raise ValueError("non-positive response normalizer")
    common_pair = pair_responses["common"]
    differential_pair = pair_responses["differential"]
    offdiag = (
        float(np.sum(np.mean(common_pair["differential"] ** 2, axis=1)))
        * dt
        / normalizers["common"]
        + float(np.sum(differential_pair["common"] ** 2))
        * dt
        / normalizers["differential"]
    )
    diff_energy = sum(
        float(np.sum(np.mean(pair_responses[kind]["differential"] ** 2, axis=1)))
        * dt
        / normalizers[kind]
        for kind in PAIR_KINDS
    )
    frequency_blocks = [value["frequencies"] for value in arrays.values()]
    action_blocks = [value["actions"] for value in arrays.values()]
    all_actions = np.stack(action_blocks)
    variations = [
        float(np.sum(np.mean(np.abs(value["differences"]), axis=(1, 2))))
        for value in arrays.values()
    ]
    dispersions = [float(np.max(np.ptp(actions, axis=1))) for actions in action_blocks]
    saturation = np.logical_or(all_actions <= -1.0 + 1e-9, all_actions >= 1.0 - 1e-9)
    complete = all(row["completed"] and row["row_count"] == 30 for row in completion_rows)
    no_tds = all(row["tds_failed"] is False and row["tds_row_count"] == 0 for row in completion_rows)
    summary = {
        "profile_id": profile_id,
        "split": str(profile.get("split", "evaluation")),
        "arm_id": str(records[0]["rows"][0]["arm_id"]),
        "record_count": 6,
        "off_diagonal_response_energy": offdiag,
        "disturbance_differential_energy": diff_energy,
        "common_frequency_iae_hz_s": sum(
            float(np.sum(np.abs(np.mean(freq - nominal_hz, axis=1))) * dt)
            for freq in frequency_blocks
        ),
        "worst_unit_peak_hz": max(float(np.max(np.abs(freq - nominal_hz))) for freq in frequency_blocks),
        "worst_rocof_hz_s": max(
            float(np.max(np.abs(np.diff(np.concatenate([value["initial"][None, :], value["frequencies"]]), axis=0) / dt)))
            for value in arrays.values()
        ),
        "differential_settling_seconds": {
            kind: _settling_time(pair_responses[kind]["differential"], dt)
            for kind in PAIR_KINDS
        },
        "action_rms": float(np.sqrt(np.mean(all_actions**2))),
        "action_total_variation": float(sum(variations)),
        "minimum_record_total_variation": float(min(variations)),
        "maximum_action_row_dispersion": float(max(dispersions)),
        "minimum_record_action_row_dispersion": float(min(dispersions)),
        "action_saturation_fraction": float(np.mean(saturation)),
        "action_bound_violation": bound_violation,
        "action_slew_violation": slew_violation,
        "actuator_mapping_pass": bool(mapping_pass),
        "completion_pass": complete,
        "tds_pass": no_tds,
        "completion_rows": completion_rows,
        "normalizers": normalizers,
    }
    numeric = np.asarray([summary[key] for key in NUMERIC_KEYS], dtype=float)
    summary["valid"] = bool(
        np.all(np.isfinite(numeric))
        and np.all(numeric >= 0.0)
        and mapping_pass
        and not bound_violation
        and not slew_violation
        and complete
        and no_tds
    )
    return summary


def phase_i_residuals(
    candidate: Mapping[str, Any], static: Mapping[str, Any]
) -> dict[str, float]:
    """Return dimensionless <=0 guard residuals for one profile/candidate."""

    factors = {
        "disturbance_differential_energy": 0.95,
        "off_diagonal_response_energy": 0.95,
        "common_frequency_iae_hz_s": 1.03,
        "worst_unit_peak_hz": 1.03,
        "worst_rocof_hz_s": 1.03,
        "action_rms": 1.10,
        "action_total_variation": 1.10,
    }
    residuals: dict[str, float] = {}
    for key, factor in factors.items():
        denominator = factor * float(static[key])
        if not np.isfinite(denominator) or denominator <= 1e-12:
            raise ValueError(f"invalid phase-I denominator: {key}")
        residuals[key] = float(candidate[key]) / denominator - 1.0
    residuals["action_saturation_fraction"] = (
        float(candidate["action_saturation_fraction"]) / 0.05 - 1.0
    )
    if not (
        candidate.get("valid") is True
        and candidate.get("actuator_mapping_pass") is True
        and candidate.get("action_bound_violation") is False
        and candidate.get("action_slew_violation") is False
    ):
        residuals["validity"] = float("inf")
    return residuals


def enumerate_phase_i(profile_tables: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Exactly enumerate shared candidate identities over all profile tables."""

    if len(profile_tables) != 4:
        raise ValueError("four profile tables are required")
    ids_by_profile = [
        {str(row["candidate_id"]) for row in table["candidate_rows"]}
        for table in profile_tables
    ]
    if any(ids != ids_by_profile[0] for ids in ids_by_profile[1:]):
        raise ValueError("candidate identities differ across profiles")
    candidate_ids = sorted(ids_by_profile[0])
    if len(candidate_ids) != 350:
        raise ValueError("the named phase-I class must contain 350 candidates")
    rows_by_profile = {
        str(table["profile_id"]): {
            str(row["candidate_id"]): row for row in table["candidate_rows"]
        }
        for table in profile_tables
    }
    tables_by_profile = {str(table["profile_id"]): table for table in profile_tables}
    rows: list[dict[str, Any]] = []
    for candidate_id in candidate_ids:
        profile_residuals: dict[str, dict[str, float]] = {}
        schedule = None
        k = None
        global_index = None
        for profile_id in sorted(rows_by_profile):
            row = rows_by_profile[profile_id][candidate_id]
            schedule = row["schedule"] if schedule is None else schedule
            if row["schedule"] != schedule:
                raise ValueError("shared candidate has inconsistent schedule")
            k = row["k"] if k is None else k
            global_index = row["global_index"] if global_index is None else global_index
            profile_residuals[profile_id] = phase_i_residuals(
                row["summary"], tables_by_profile[profile_id]["static"]
            )
        flat = [value for residuals in profile_residuals.values() for value in residuals.values()]
        t_value = max(flat)
        active = [
            {"profile_id": profile_id, "guard": guard, "residual": value}
            for profile_id, residuals in profile_residuals.items()
            for guard, value in residuals.items()
            if np.isclose(value, t_value, rtol=0.0, atol=1e-12)
        ]
        rows.append(
            {
                "candidate_id": candidate_id,
                "global_index": global_index,
                "k": k,
                "schedule": schedule,
                "t": t_value,
                "active_guards": active,
                "profile_residuals": profile_residuals,
            }
        )
    rows.sort(key=lambda row: (row["t"], row["candidate_id"]))
    winner = rows[0]
    return {
        "candidate_count": len(rows),
        "classification": (
            "FINITE-CLASS-FEASIBLE-WITNESS"
            if winner["t"] <= 0.0
            else "FINITE-CLASS-INFEASIBLE"
        ),
        "winner": winner,
        "runner_up": rows[1],
        "runner_up_margin": float(rows[1]["t"] - winner["t"]),
        "rows": rows,
        "scope": "exact only for the named 350-schedule class over eval_a..eval_d",
        "neural_policy_inference_authorized": False,
    }
