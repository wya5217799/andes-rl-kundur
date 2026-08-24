"""R479 corrected-card zero-action H sensitivity.

The module owns the six-cell scientific contract and deterministic analysis.
The CLI adapter owns seals and immutable artifact I/O.  All M/D telemetry is
device-base; ANDES runtime conversion is inherited from the sealed R478 code.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ROUND_ID = "R479"
H_LEVELS_S = (10.0, 100.0, 300.0)
D0_DEVICE = 100.0
FORMAL_STEPS = 150
SHORT_STEPS = 30
DT_S = 0.2
SEED = 42
MATERIALITY_FRACTION = 0.10
ANCHOR_TOL = 1e-9
SETTLING_BAND_HZ = 0.02


def _cell_id(h_device_s: float, scenario_id: str) -> str:
    return f"h{int(h_device_s)}_{scenario_id}"


def build_contract() -> dict[str, Any]:
    """Return the prospectively frozen six-cell contract."""

    from andes_rl_kundur.probes.andes_common.paper_constants import (
        LS1_DELTA_U,
        LS2_DELTA_U,
    )

    scenarios = {"ls1": LS1_DELTA_U, "ls2": LS2_DELTA_U}
    cells = [
        {
            "cell_id": _cell_id(h, scenario_id),
            "h_device_s": h,
            "m_device_s": 2.0 * h,
            "d_device": D0_DEVICE,
            "scenario_id": scenario_id,
            "delta_u": scenarios[scenario_id],
        }
        for h in H_LEVELS_S
        for scenario_id in scenarios
    ]
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "factor": "uniform-device-base-H0",
        "h_levels_device_s": list(H_LEVELS_S),
        "d0_device": D0_DEVICE,
        "zero_action": True,
        "steps": FORMAL_STEPS,
        "short_window_steps": SHORT_STEPS,
        "dt_s": DT_S,
        "seed": SEED,
        "cells": cells,
        "h300_semantics": "stress-point-not-paper-bound",
        "materiality_fraction": MATERIALITY_FRACTION,
        "settling_band_hz": SETTLING_BAND_HZ,
        "frequency_coordinates": {
            "primary": "controller-50-Hz-paper-coordinate",
            "secondary": "ANDES-physical-frequency-coordinate",
            "pooled": False,
        },
        "claim_boundary": {
            "open_loop_h_sensitivity": True,
            "damping_realism": False,
            "controller_ordering": False,
            "learning_robustness": False,
            "stability_certificate": False,
            "yang_baseline_reproduction": False,
        },
    }


def _first_enter_and_stay(
    df_traj: np.ndarray,
    *,
    dt_s: float = DT_S,
    band_hz: float = SETTLING_BAND_HZ,
) -> float | None:
    if df_traj.size == 0:
        return None
    deviation = np.abs(df_traj - df_traj[-1])
    for index in range(deviation.size):
        if np.all(deviation[index:] <= band_hz):
            return float(index * dt_s)
    return None


def summarize_cell(
    record: Mapping[str, Any],
    *,
    expected_steps: int = FORMAL_STEPS,
) -> dict[str, Any]:
    """Validate one trace and derive the pre-registered short/long endpoints."""

    reasons: list[str] = []
    h = float(record.get("h_device_s", float("nan")))
    scenario_id = str(record.get("scenario_id", ""))
    n_steps = int(record.get("n_steps", 0))
    if record.get("tds_failed") is not False:
        reasons.append("tds_failed")
    if n_steps != expected_steps:
        reasons.append("wrong_step_count")
    if not np.isfinite(h) or h not in H_LEVELS_S:
        reasons.append("unknown_h_level")
    if scenario_id not in {"ls1", "ls2"}:
        reasons.append("unknown_scenario")

    df = np.asarray(record.get("df_traj", []), dtype=float)
    trajectory = record.get("traj", {})
    if not isinstance(trajectory, Mapping):
        trajectory = {}
    freq = np.asarray(trajectory.get("freq_hz", []), dtype=float)
    freq_physical = np.asarray(
        trajectory.get("freq_hz_physical", []), dtype=float
    )
    physical_nominal = np.asarray(
        trajectory.get("andes_nominal_frequency_hz", []), dtype=float
    )
    m_values = np.asarray(trajectory.get("M_es", []), dtype=float)
    d_values = np.asarray(trajectory.get("D_es", []), dtype=float)
    for name, values in (
        ("df", df),
        ("frequency", freq),
        ("physical_frequency", freq_physical),
        ("physical_nominal_frequency", physical_nominal),
        ("m_readback", m_values),
        ("d_readback", d_values),
    ):
        if values.shape[0] != expected_steps:
            reasons.append(f"{name}_length")
        if values.size == 0 or not np.all(np.isfinite(values)):
            reasons.append(f"{name}_nonfinite")

    if m_values.size and np.isfinite(h):
        if not np.allclose(m_values, 2.0 * h, atol=ANCHOR_TOL, rtol=0.0):
            reasons.append("m_readback_drift")
    if d_values.size:
        if not np.allclose(d_values, D0_DEVICE, atol=ANCHOR_TOL, rtol=0.0):
            reasons.append("d_readback_drift")

    summary: dict[str, Any] = {
        "cell_id": str(record.get("cell_id", _cell_id(h, scenario_id))),
        "h_device_s": h,
        "scenario_id": scenario_id,
        "n_steps": n_steps,
        "horizon_s": float(expected_steps * DT_S),
        "valid": not reasons,
        "invalid_reasons": sorted(set(reasons)),
    }
    if reasons or df.size < SHORT_STEPS:
        return summary

    physical_df = np.max(
        np.abs(freq_physical - physical_nominal.reshape(-1, 1)), axis=1
    )

    summary.update(
        {
            "max_df_6s_hz": float(np.max(df[:SHORT_STEPS])),
            "final_df_6s_hz": float(df[SHORT_STEPS - 1]),
            "physical_max_df_6s_hz": float(
                np.max(physical_df[:SHORT_STEPS])
            ),
            "physical_final_df_6s_hz": float(physical_df[SHORT_STEPS - 1]),
        }
    )
    if expected_steps >= FORMAL_STEPS:
        late = freq[SHORT_STEPS:]
        settling = _first_enter_and_stay(df)
        summary.update(
            {
                "max_df_30s_hz": float(np.max(df)),
                "final_df_30s_hz": float(df[-1]),
                "physical_max_df_30s_hz": float(np.max(physical_df)),
                "physical_final_df_30s_hz": float(physical_df[-1]),
                "late_6_to_30s_bus_span_hz": float(
                    np.max(np.ptp(late, axis=0)) if late.size else 0.0
                ),
                "settled_by_30s": settling is not None,
                "settling_s_30": settling,
            }
        )
    return summary


def _relative_change(value: float, reference: float) -> float | None:
    if reference == 0.0:
        return 0.0 if value == 0.0 else None
    return float((value - reference) / abs(reference))


def analyze_bank(
    records: Sequence[Mapping[str, Any]],
    rehearsal_summary: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify the complete bank without strengthening its claim boundary."""

    contract = build_contract()
    expected_ids = {cell["cell_id"] for cell in contract["cells"]}
    actual_ids = [str(record.get("cell_id", "")) for record in records]
    reasons: list[str] = []
    if set(actual_ids) != expected_ids or len(actual_ids) != len(expected_ids):
        reasons.append("cell_identity_mismatch")

    summaries = [summarize_cell(record) for record in records]
    if any(not summary["valid"] for summary in summaries):
        reasons.append("invalid_cell")
    if rehearsal_summary.get("valid") is not True:
        reasons.append("invalid_rehearsal")

    by_key = {
        (summary["h_device_s"], summary["scenario_id"]): summary
        for summary in summaries
        if summary["valid"]
    }
    anchor = by_key.get((100.0, "ls1"))
    if anchor is None:
        reasons.append("missing_h100_ls1_anchor")
    elif rehearsal_summary.get("valid") is True:
        for key in ("max_df_6s_hz", "final_df_6s_hz"):
            if abs(float(anchor[key]) - float(rehearsal_summary[key])) > ANCHOR_TOL:
                reasons.append("h100_rehearsal_anchor_mismatch")
                break

    comparisons: list[dict[str, Any]] = []
    material_triggers: list[dict[str, Any]] = []
    if not reasons:
        for scenario_id in ("ls1", "ls2"):
            reference = by_key[(100.0, scenario_id)]
            for h in (10.0, 300.0):
                candidate = by_key[(h, scenario_id)]
                peak_change = _relative_change(
                    float(candidate["max_df_6s_hz"]),
                    float(reference["max_df_6s_hz"]),
                )
                final_change = _relative_change(
                    float(candidate["final_df_6s_hz"]),
                    float(reference["final_df_6s_hz"]),
                )
                settling_flip = (
                    bool(candidate["settled_by_30s"])
                    != bool(reference["settled_by_30s"])
                )
                row = {
                    "scenario_id": scenario_id,
                    "h_device_s": h,
                    "reference_h_device_s": 100.0,
                    "max_df_6s_relative_change": peak_change,
                    "final_df_6s_relative_change": final_change,
                    "settling_status_flip": settling_flip,
                }
                comparisons.append(row)
                peak_material = peak_change is None or (
                    abs(peak_change) + 1e-15 >= MATERIALITY_FRACTION
                )
                final_material = final_change is None or (
                    abs(final_change) + 1e-15 >= MATERIALITY_FRACTION
                )
                if peak_material or final_material or settling_flip:
                    material_triggers.append(row)

    valid = not reasons
    if not valid:
        classification = "ENGINEERING-INVALID"
    elif material_triggers:
        classification = "OPEN-LOOP-H-SENSITIVE"
    else:
        classification = "NO-MATERIAL-OPEN-LOOP-H-SENSITIVITY-DETECTED"
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "classification": classification,
        "valid": valid,
        "invalid_reasons": sorted(set(reasons)),
        "materiality_fraction": MATERIALITY_FRACTION,
        "summaries": sorted(
            summaries, key=lambda item: (item["scenario_id"], item["h_device_s"])
        ),
        "comparisons": comparisons,
        "material_triggers": material_triggers,
        "claim_boundary": contract["claim_boundary"],
    }


def run_cell(spec: Mapping[str, Any], *, steps: int = FORMAL_STEPS) -> dict[str, Any]:
    """Run one WSL-only corrected V4 zero-action cell."""

    if os.name != "posix":
        raise RuntimeError("R479 physical cells are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R479 must run through scripts/andes_scratch.py")

    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.probes.andes_common.tracers import run_zero_action_trace

    h = float(spec["h_device_s"])
    scenario_id = str(spec["scenario_id"])
    result = run_zero_action_trace(
        AndesMultiVSGEnvV4,
        dict(spec["delta_u"]),
        h_forced=h,
        n_steps=steps,
        seed=SEED,
        record_extras=(
            "freq_hz",
            "freq_hz_physical",
            "andes_nominal_frequency_hz",
            "M_es",
            "D_es",
        ),
    )
    result.update(
        {
            "round": ROUND_ID,
            "cell_id": _cell_id(h, scenario_id),
            "h_device_s": h,
            "scenario_id": scenario_id,
            "worker_pid": os.getpid(),
        }
    )
    return result


def run_cell_captured(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Return a durable invalid record instead of losing a worker exception."""

    try:
        return run_cell(spec)
    except Exception as error:  # formal failure must remain inspectable
        h = float(spec["h_device_s"])
        scenario_id = str(spec["scenario_id"])
        return {
            "round": ROUND_ID,
            "cell_id": _cell_id(h, scenario_id),
            "h_device_s": h,
            "scenario_id": scenario_id,
            "n_steps": 0,
            "tds_failed": True,
            "df_traj": [],
            "traj": {},
            "worker_pid": os.getpid(),
            "error_type": type(error).__name__,
            "error": str(error)[:500],
        }


__all__ = [
    "ANCHOR_TOL",
    "D0_DEVICE",
    "FORMAL_STEPS",
    "H_LEVELS_S",
    "MATERIALITY_FRACTION",
    "SHORT_STEPS",
    "analyze_bank",
    "build_contract",
    "run_cell",
    "run_cell_captured",
    "summarize_cell",
]
