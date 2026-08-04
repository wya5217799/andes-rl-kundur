"""Fail-closed Stage-1 source-record guards for diagnostic EVAL views."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from andes_rl_kundur.evaluation.model_first_stage1_eval_view import (
    build_fresh_stage1_eval_view,
)

_FINITE_TELEMETRY_FIELDS = (
    "freq_hz_physical",
    "delta_f_physical_hz",
    "bess_requested_power_system_pu",
    "bess_commanded_power_system_pu",
    "bess_actual_power_system_pu",
    "bess_soc",
)


def _finite_telemetry(rows: list[Mapping[str, object]]) -> bool:
    try:
        for row in rows:
            if row.get("finite_state_algebraic") is not True:
                return False
            if not np.isfinite(float(row["t"])):
                return False
            for field in _FINITE_TELEMETRY_FIELDS:
                values = np.asarray(row[field], dtype=float)
                if values.shape != (4,) or not np.all(np.isfinite(values)):
                    return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def synthesize_fresh_stage1_eval_guards(
    record: Mapping[str, object],
) -> dict[str, bool | int]:
    """Derive EVAL-v2 record guards from authoritative Stage-1 source fields.

    A source ``guards`` object is intentionally ignored. Invalid, incomplete,
    or unknown source state raises instead of emitting a partially trusted
    diagnostic view.
    """

    rows_value = record.get("traces")
    if not isinstance(rows_value, list) or not rows_value:
        raise ValueError("Stage-1 source must contain non-empty trace rows")
    if not all(isinstance(row, Mapping) for row in rows_value):
        raise ValueError("every Stage-1 trace row must be an object")
    rows: list[Mapping[str, object]] = rows_value

    try:
        completed = (
            record.get("completed") is True
            and record.get("tds_failed") is False
            and int(record.get("n_steps", -1)) == len(rows)
            and int(record.get("requested_steps", -1)) == len(rows)
        )
    except (TypeError, ValueError):
        completed = False
    if not completed:
        raise ValueError("Stage-1 source completion contract is not valid")

    initialization = record.get("initialization_solver")
    if not isinstance(initialization, Mapping):
        raise ValueError("Stage-1 source initialization solver is missing")
    if initialization.get("tds_test_ok") is not True:
        raise ValueError("Stage-1 source TDS initialization did not pass")
    if initialization.get("system_exit_code") != 0:
        raise ValueError("Stage-1 source initialization exit code is nonzero")

    if any(
        row.get("tds_failed") is not False or row.get("system_exit_code") != 0
        for row in rows
    ):
        raise ValueError("Stage-1 source contains a failed or nonzero-exit step")
    if not _finite_telemetry(rows):
        raise ValueError("Stage-1 source telemetry is missing or non-finite")

    return {
        "completed": True,
        "tds_test_ok": True,
        "system_exit_code": 0,
        "finite_telemetry": True,
    }


def build_guarded_fresh_stage1_eval_view(
    record: dict[str, Any],
    *,
    source_path: str,
    source_sha256: str,
    expected_round: str = "R310",
    expected_question: str = "Q-0066",
) -> dict[str, Any]:
    """Build a source-bound paired view with freshly synthesized guards."""

    guards = synthesize_fresh_stage1_eval_guards(record)
    view = build_fresh_stage1_eval_view(
        record,
        source_path=source_path,
        source_sha256=source_sha256,
        expected_round=expected_round,
        expected_question=expected_question,
    )
    view["guards"] = guards
    return view
