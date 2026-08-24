"""Reusable physical probes for corrected M/D revalidation.

This module owns scenario selection, trace execution, and physical validity
checks. Command-line runners remain orchestration-only.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from andes_rl_kundur.probes.andes_common.paper_constants import (
    DEFAULT_PROBE_SEED,
    DEFAULT_PROBE_STEPS_SHORT,
    LS1_DELTA_U,
    LS2_DELTA_U,
)

ZERO_SCENARIOS = (("ls1", LS1_DELTA_U), ("ls2", LS2_DELTA_U))


def zero_contract(*, round_id: str) -> dict[str, Any]:
    """Return the frozen zero-action bank contract."""
    return {
        "round": round_id,
        "family": "zero",
        "env": "andes_vsg_env_v4 corrected base convention (md_convention)",
        "scenarios": [
            {"id": scenario_id, "delta_u": delta_u}
            for scenario_id, delta_u in ZERO_SCENARIOS
        ],
        "seed": DEFAULT_PROBE_SEED,
        "n_steps": DEFAULT_PROBE_STEPS_SHORT,
        "record_extras": ["freq_hz", "M_es", "D_es"],
        "runtime_readback_note": (
            "M_es/D_es are device-base telemetry derived from ANDES runtime "
            "readback; x_sys = x_dev * S_n / S_b."
        ),
    }


def run_zero_action_bank(env_class: type) -> dict[str, dict[str, Any]]:
    """Execute and validate the registered zero-action trace bank."""
    return {
        scenario_id: run_zero_action_scenario(
            env_class, scenario_id=scenario_id, delta_u=delta_u
        )
        for scenario_id, delta_u in ZERO_SCENARIOS
    }


def run_zero_action_scenario(
    env_class: type, *, scenario_id: str, delta_u: dict[str, float]
) -> dict[str, Any]:
    """Execute one registered scenario and enforce zero-action M/D invariants."""
    from andes_rl_kundur.probes.andes_common.tracers import run_zero_action_trace

    result = run_zero_action_trace(
        env_class,
        delta_u,
        h_forced=None,
        n_steps=DEFAULT_PROBE_STEPS_SHORT,
        seed=DEFAULT_PROBE_SEED,
        env_patch=None,
        record_extras=("freq_hz", "M_es", "D_es"),
    )
    if result["tds_failed"]:
        raise RuntimeError(f"zero-action TDS failure: {scenario_id}")
    traj = result["traj"]
    m_values = traj.get("M_es") or []
    d_values = traj.get("D_es") or []
    if not m_values or not d_values:
        raise RuntimeError(f"zero-action missing M/D extras: {scenario_id}")
    m0 = np.asarray(m_values[0], dtype=float)
    d0 = np.asarray(d_values[0], dtype=float)
    m_constant = all(
        np.allclose(np.asarray(value, dtype=float), m0) for value in m_values
    )
    d_constant = all(
        np.allclose(np.asarray(value, dtype=float), d0) for value in d_values
    )
    if not m_constant or not d_constant:
        raise RuntimeError(f"zero-action M/D drift: {scenario_id}")
    return {
        "max_df": float(result["max_df"]),
        "final_df": float(result["final_df"]),
        "n_steps": int(result["n_steps"]),
        "tds_failed": False,
        "delta_u": result["delta_u"],
        "traj": traj,
        "df_traj": result["df_traj"],
    }


def summarize_zero_action_bank(
    records: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Return rehearsal-safe summaries without full trace payloads."""
    return {
        scenario_id: {
            "n_steps": record["n_steps"],
            "max_df": record["max_df"],
            "final_df": record["final_df"],
            "M_es_first": record["traj"]["M_es"][0],
            "D_es_first": record["traj"]["D_es"][0],
        }
        for scenario_id, record in records.items()
    }
