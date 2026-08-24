"""R478 zero-action bank — registered zero-action trace re-execution.

Owns the zero family's scientific content (Phase 1A/1C): the frozen
LS1/LS2 zero-action traces under the corrected M/D convention. The
``scripts/run_r478_md_revalidation.py`` adapter only dispatches here.

Physical phases are WSL-only and must run through the scratch launcher;
rehearsal walks the same-pre-attempt path without writing formal records.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

ROUND_ID = "R478"


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("physical phases are WSL/POSIX-only (ANDES runtime)")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("must run through scripts/andes_scratch.py")


def build_contract() -> dict[str, Any]:
    """Frozen zero-family contract (scenarios, seed, window, record keys)."""
    from andes_rl_kundur.probes.andes_common.paper_constants import (
        DEFAULT_PROBE_SEED,
        DEFAULT_PROBE_STEPS_SHORT,
        LS1_DELTA_U,
        LS2_DELTA_U,
    )
    return {
        "round": ROUND_ID,
        "family": "zero",
        "env": "andes_vsg_env_v4 corrected base convention (md_convention)",
        "scenarios": [
            {"id": "ls1", "delta_u": LS1_DELTA_U},
            {"id": "ls2", "delta_u": LS2_DELTA_U},
        ],
        "seed": DEFAULT_PROBE_SEED,
        "n_steps": DEFAULT_PROBE_STEPS_SHORT,
        "record_extras": ["freq_hz", "M_es", "D_es"],
        "runtime_readback_note": (
            "M_es/D_es are device-base telemetry; the runtime system-base "
            "values follow the declared exact conversion "
            "x_sys = x_dev * S_n / S_b (md_convention, S_n=200, S_b=100)."
        ),
    }


def _run_traces() -> dict[str, Any]:
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.probes.andes_common.paper_constants import (
        DEFAULT_PROBE_SEED,
        DEFAULT_PROBE_STEPS_SHORT,
        LS1_DELTA_U,
        LS2_DELTA_U,
    )
    from andes_rl_kundur.probes.andes_common.tracers import (
        run_zero_action_trace,
    )

    results = {}
    for scenario_id, delta_u in (("ls1", LS1_DELTA_U), ("ls2", LS2_DELTA_U)):
        result = run_zero_action_trace(
            AndesMultiVSGEnvV4,
            delta_u,
            h_forced=None,
            n_steps=DEFAULT_PROBE_STEPS_SHORT,
            seed=DEFAULT_PROBE_SEED,
            env_patch=None,
            record_extras=("freq_hz", "M_es", "D_es"),
        )
        if result["tds_failed"]:
            raise RuntimeError(f"zero trace TDS failure: {scenario_id}")
        results[scenario_id] = result
    return results


def rehearsal_payload() -> dict[str, Any]:
    """Same-pre-attempt rehearsal: zero-action M/D preservation, no records."""
    _assert_wsl_scratch()
    import numpy as np

    results = _run_traces()
    checked: dict[str, Any] = {}
    for scenario_id, result in results.items():
        traj = result["traj"]
        m_values = traj.get("M_es") or []
        d_values = traj.get("D_es") or []
        if not m_values or not d_values:
            raise RuntimeError(f"zero rehearsal missing M/D extras: {scenario_id}")
        m0 = np.asarray(m_values[0], dtype=float)
        d0 = np.asarray(d_values[0], dtype=float)
        if not all(
            np.allclose(np.asarray(v, dtype=float), m0) for v in m_values
        ) or not all(
            np.allclose(np.asarray(v, dtype=float), d0) for v in d_values
        ):
            raise RuntimeError(
                f"zero rehearsal invariant failure: M_es/D_es drift: {scenario_id}"
            )
        checked[scenario_id] = {
            "n_steps": int(result["n_steps"]),
            "max_df": float(result["max_df"]),
            "final_df": float(result["final_df"]),
            "M_es_first": m0.tolist(),
            "D_es_first": d0.tolist(),
        }
    return {
        "round": ROUND_ID,
        "family": "zero",
        "checks": [
            "same-pre-attempt-path",
            "zero-action-preserves-M_es-D_es",
            "tds-ok",
        ],
        "results": checked,
    }


def execute_payload() -> dict[str, Any]:
    """Formal zero-action records (create-only at the adapter layer)."""
    _assert_wsl_scratch()
    results = _run_traces()
    records = {}
    for scenario_id, result in results.items():
        records[scenario_id] = {
            "max_df": float(result["max_df"]),
            "final_df": float(result["final_df"]),
            "n_steps": int(result["n_steps"]),
            "tds_failed": bool(result["tds_failed"]),
            "delta_u": result["delta_u"],
            "traj": result["traj"],
            "df_traj": result["df_traj"],
        }
    return {"round": ROUND_ID, "records": records}
