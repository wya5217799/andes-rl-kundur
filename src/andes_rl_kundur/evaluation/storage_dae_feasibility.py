"""Completion-only differential diagnostics for V4 versus zero-support ESD1."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np

PLANTS = ("original_v4", "storage_zero")


class _MessageCollector(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def _array_sha256(values: Any) -> str:
    array = np.ascontiguousarray(np.asarray(values))
    metadata = json.dumps(
        {"dtype": str(array.dtype), "shape": list(array.shape)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256()
    digest.update(metadata)
    digest.update(array.tobytes())
    return digest.hexdigest()


def _json_value(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _dae_snapshot(env: Any) -> dict[str, Any]:
    dae = env.ss.dae
    x = np.asarray(dae.x)
    y = np.asarray(dae.y)
    finite = bool(np.all(np.isfinite(x)) and np.all(np.isfinite(y)))
    return {
        "n": int(dae.n),
        "m": int(dae.m),
        "finite": finite,
        "x_sha256": _array_sha256(x),
        "y_sha256": _array_sha256(y),
        "simulator_time": float(dae.t),
    }


def _system_snapshot(env: Any) -> dict[str, Any]:
    model_counts = {}
    for name in ("Bus", "PQ", "PV", "GENCLS", "GENROU", "PVD1", "ESD1"):
        model = getattr(env.ss, name, None)
        model_counts[name] = int(getattr(model, "n", 0))
    config = env.ss.TDS.config
    config_values = config.as_dict() if hasattr(config, "as_dict") else {}
    return {
        "initial_dae": _dae_snapshot(env),
        "model_counts": model_counts,
        "tds_config": {
            str(key): _json_value(value)
            for key, value in config_values.items()
        },
        "power_flow_converged": bool(env.ss.PFlow.converged),
        "control_nominal_frequency_hz": float(env.FN),
        "andes_nominal_frequency_hz": float(env.andes_nominal_frequency_hz),
    }


def run_zero_support_feasibility_scenario(
    scenario_name: str,
    delta_u: dict[str, float],
    *,
    plant: str,
    seed: int = 42,
    steps: int = 300,
) -> dict[str, Any]:
    """Run one completion-only original-V4 or storage-zero diagnostic row."""
    if plant not in PLANTS:
        raise ValueError(f"unsupported feasibility plant: {plant}")
    if steps <= 0:
        raise ValueError("steps must be positive")

    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
        AndesMultiVSGEnvV4Storage,
    )

    env_class = (
        AndesMultiVSGEnvV4
        if plant == "original_v4"
        else AndesMultiVSGEnvV4Storage
    )
    env = env_class(random_disturbance=False, comm_fail_prob=0.0)
    collector = _MessageCollector()
    tds_logger = logging.getLogger("andes.routines.tds")
    tds_logger.addHandler(collector)

    started = time.perf_counter()
    setup_succeeded = False
    setup_error: dict[str, str] | None = None
    system_snapshot: dict[str, Any] = {}
    successful_steps = 0
    attempted_steps = 0
    tds_failed = False
    last_simulator_time: float | None = None
    m_values: list[float] = []
    d_values: list[float] = []
    bess_requested: list[float] = []
    bess_commanded: list[float] = []
    bess_actual: list[float] = []
    bess_soc: list[float] = []
    bess_constraint_violation_count = 0

    try:
        env.seed(seed)
        env.STEPS_PER_EPISODE = steps
        env.reset(delta_u=delta_u)
        setup_succeeded = True
        system_snapshot = _system_snapshot(env)
        zero_md = {
            index: np.zeros(2, dtype=float)
            for index in range(env.N_AGENTS)
        }
        zero_bess = np.zeros(env.N_AGENTS, dtype=float)

        for _ in range(steps):
            attempted_steps += 1
            if plant == "storage_zero":
                _, _, _, info = env.step(
                    zero_md,
                    bess_power_request_pu=zero_bess,
                )
            else:
                _, _, _, info = env.step(zero_md)

            last_simulator_time = float(info["time"])
            m_values.extend(np.asarray(info["M_es"], dtype=float).tolist())
            d_values.extend(np.asarray(info["D_es"], dtype=float).tolist())
            if plant == "storage_zero":
                bess_requested.extend(
                    np.asarray(
                        info["bess_requested_power_system_pu"],
                        dtype=float,
                    ).tolist()
                )
                bess_commanded.extend(
                    np.asarray(
                        info["bess_commanded_power_system_pu"],
                        dtype=float,
                    ).tolist()
                )
                bess_actual.extend(
                    np.asarray(
                        info["bess_actual_power_system_pu"],
                        dtype=float,
                    ).tolist()
                )
                bess_soc.extend(
                    np.asarray(info["bess_soc"], dtype=float).tolist()
                )
                bess_constraint_violation_count += len(
                    info["bess_constraint_violations"]
                )
            if bool(info["tds_failed"]):
                tds_failed = True
                break
            successful_steps += 1
    except Exception as exc:  # retained as an explicit diagnostic row
        setup_error = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        tds_failed = True
        if hasattr(env, "ss"):
            last_simulator_time = float(env.ss.dae.t)
    finally:
        tds_logger.removeHandler(collector)

    completed = (
        setup_succeeded
        and not tds_failed
        and successful_steps == steps
    )
    bess_audit = None
    if plant == "storage_zero":
        bess_audit = {
            "max_abs_requested_power": (
                float(np.max(np.abs(bess_requested))) if bess_requested else 0.0
            ),
            "max_abs_commanded_power": (
                float(np.max(np.abs(bess_commanded))) if bess_commanded else 0.0
            ),
            "max_abs_actual_power": (
                float(np.max(np.abs(bess_actual))) if bess_actual else 0.0
            ),
            "min_soc": float(np.min(bess_soc)) if bess_soc else 0.5,
            "max_soc": float(np.max(bess_soc)) if bess_soc else 0.5,
            "constraint_violation_count": bess_constraint_violation_count,
        }

    return {
        "experiment": "r273_storage_dae_feasibility",
        "scenario": scenario_name,
        "delta_u": dict(delta_u),
        "plant": plant,
        "seed": seed,
        "requested_steps": steps,
        "successful_steps": successful_steps,
        "attempted_steps": attempted_steps,
        "completed": completed,
        "tds_failed": tds_failed,
        "setup_succeeded": setup_succeeded,
        "setup_error": setup_error,
        "last_simulator_time": last_simulator_time,
        "wall_time_seconds": time.perf_counter() - started,
        "solver_messages": collector.messages,
        "initial_dae": system_snapshot.get("initial_dae"),
        "model_counts": system_snapshot.get("model_counts"),
        "tds_config": system_snapshot.get("tds_config"),
        "power_flow_converged": system_snapshot.get("power_flow_converged"),
        "control_nominal_frequency_hz": system_snapshot.get(
            "control_nominal_frequency_hz"
        ),
        "andes_nominal_frequency_hz": system_snapshot.get(
            "andes_nominal_frequency_hz"
        ),
        "m_unique": sorted(set(m_values)),
        "d_unique": sorted(set(d_values)),
        "bess_zero_support_audit": bess_audit,
    }


def classify_storage_dae_attribution(
    records: Iterable[dict[str, Any]],
    *,
    failure_scenarios: Sequence[str],
    control_scenarios: Sequence[str],
) -> dict[str, Any]:
    """Classify a frozen completion matrix without using performance endpoints."""
    rows = list(records)
    expected_scenarios = [*failure_scenarios, *control_scenarios]
    indexed = {
        (str(row["scenario"]), str(row["plant"])): row
        for row in rows
    }
    expected_keys = {
        (scenario, plant)
        for scenario in expected_scenarios
        for plant in PLANTS
    }
    if (
        len(rows) != len(expected_keys)
        or set(indexed) != expected_keys
        or not all(
        bool(row.get("provenance_valid", False)) for row in rows
        )
    ):
        return {
            "classification": "UNRESOLVED/INVALID",
            "reason": "completion matrix or row provenance is incomplete",
            "completion_vectors_match": False,
            "all_registered_failures_reproduced": False,
            "all_controls_complete": False,
        }

    completion_by_plant = {
        plant: [
            bool(indexed[(scenario, plant)]["completed"])
            for scenario in expected_scenarios
        ]
        for plant in PLANTS
    }
    completion_vectors_match = (
        completion_by_plant["original_v4"]
        == completion_by_plant["storage_zero"]
    )
    all_registered_failures_reproduced = all(
        not bool(indexed[(scenario, plant)]["completed"])
        for scenario in failure_scenarios
        for plant in PLANTS
    )
    all_controls_complete = all(
        bool(indexed[(scenario, plant)]["completed"])
        for scenario in control_scenarios
        for plant in PLANTS
    )

    if (
        completion_vectors_match
        and all_registered_failures_reproduced
        and all_controls_complete
    ):
        classification = "ENVELOPE-INFEASIBLE"
        reason = (
            "both plants reproduce every registered failure and complete "
            "every signed/location control"
        )
    else:
        original_only_completions = [
            scenario
            for scenario in failure_scenarios
            if bool(indexed[(scenario, "original_v4")]["completed"])
            and not bool(indexed[(scenario, "storage_zero")]["completed"])
        ]
        shared_failures = [
            scenario
            for scenario in failure_scenarios
            if not bool(indexed[(scenario, "original_v4")]["completed"])
            and not bool(indexed[(scenario, "storage_zero")]["completed"])
        ]
        if original_only_completions and not shared_failures:
            classification = "STORAGE-DAE-CONFOUND"
            reason = (
                "original V4 completes registered cases that zero-support "
                "storage deterministically fails"
            )
        elif original_only_completions and shared_failures:
            classification = "MIXED"
            reason = "shared plant failures and storage-specific failures coexist"
        else:
            classification = "UNRESOLVED/INVALID"
            reason = "the registered completion pattern does not identify one cause"

    return {
        "classification": classification,
        "reason": reason,
        "completion_vectors_match": completion_vectors_match,
        "all_registered_failures_reproduced": all_registered_failures_reproduced,
        "all_controls_complete": all_controls_complete,
        "completion_by_plant": completion_by_plant,
    }
