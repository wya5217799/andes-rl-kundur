"""Generic R279 execution seam for frozen scalar residual controllers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

import numpy as np

from andes_rl_kundur.control.area_inertia_residual import r278_area_inertia_contract
from andes_rl_kundur.env.andes.icems_residual_env import ICEMSResidualEnv


class ResidualController(Protocol):
    def select_raw_actions(
        self,
        observations: Mapping[int, np.ndarray],
        *,
        deterministic: bool = True,
    ) -> np.ndarray: ...


def _trace_row(step: int, info: Mapping[str, Any], nominal_hz: float) -> dict[str, Any]:
    physical_frequency = np.asarray(info["freq_hz_physical"], dtype=float)
    return {
        "step": step,
        "t": float(info["time"]),
        "freq_hz_physical": physical_frequency.tolist(),
        "delta_f_physical_hz": (physical_frequency - nominal_hz).tolist(),
        "action_norm": np.asarray(
            info["r278_executed_md_action_norm"], dtype=float
        ).tolist(),
        "M_es": np.asarray(info["M_es"], dtype=float).tolist(),
        "D_es": np.asarray(info["D_es"], dtype=float).tolist(),
        "r278_raw_z": np.asarray(info["r278_raw_z"], dtype=float).tolist(),
        "r278_q": float(info["r278_q"]),
        "r278_residual_action_norm": np.asarray(
            info["r278_residual_action_norm"], dtype=float
        ).tolist(),
        "r278_physical_m_residual": np.asarray(
            info["r278_physical_m_residual"], dtype=float
        ).tolist(),
        "r278_physical_m_residual_sum": float(
            info["r278_physical_m_residual_sum"]
        ),
        "bess_requested_power_system_pu": np.asarray(
            info["bess_requested_power_system_pu"], dtype=float
        ).tolist(),
        "bess_commanded_power_system_pu": np.asarray(
            info["bess_commanded_power_system_pu"], dtype=float
        ).tolist(),
        "bess_actual_power_system_pu": np.asarray(
            info["bess_actual_power_system_pu"], dtype=float
        ).tolist(),
        "bess_soc": np.asarray(info["bess_soc"], dtype=float).tolist(),
        "bess_bus_voltage_pu": np.asarray(
            info["bess_bus_voltage_pu"], dtype=float
        ).tolist(),
        "bess_saturation_reasons": info["bess_saturation_reasons"],
        "bess_charge_energy_mwh_total": np.asarray(
            info["bess_charge_energy_mwh_total"], dtype=float
        ).tolist(),
        "bess_discharge_energy_mwh_total": np.asarray(
            info["bess_discharge_energy_mwh_total"], dtype=float
        ).tolist(),
        "bess_constraint_violations": info["bess_constraint_violations"],
    }


def run_r279_controller_scenario(
    controller: ResidualController,
    *,
    controller_name: str,
    controller_config: Mapping[str, Any],
    scenario_name: str,
    delta_u: Mapping[str, float],
    seed: int,
    steps: int,
    phase: str,
    evidence_hashes: Mapping[str, str],
) -> dict[str, Any]:
    """Run one deterministic R279 controller without changing the V4 plant."""
    if steps < 2:
        raise ValueError("R279 trajectories require at least two steps")
    from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
        AndesMultiVSGEnvV4Storage,
    )

    env = ICEMSResidualEnv(
        AndesMultiVSGEnvV4Storage(
            random_disturbance=False,
            comm_fail_prob=0.0,
        )
    )
    reset = getattr(controller, "reset", None)
    if callable(reset):
        reset()
    traces: list[dict[str, Any]] = []
    tds_failed = False
    nominal_hz = 60.0
    try:
        env.seed(seed)
        env.STEPS_PER_EPISODE = steps
        observation = env.reset(delta_u=dict(delta_u))
        nominal_hz = float(env.base_env.andes_nominal_frequency_hz)
        for step in range(steps):
            raw = np.asarray(
                controller.select_raw_actions(observation, deterministic=True),
                dtype=np.float32,
            )
            observation, _rewards, done, info = env.step(raw)
            if info.get("tds_failed"):
                tds_failed = True
                break
            traces.append(_trace_row(step, info, nominal_hz))
            if done:
                break
    finally:
        env.close()

    return {
        "schema_version": 1,
        "round": "R279",
        "question": "Q-0041",
        "experiment": "r279_reviewer_identifiability",
        "phase": phase,
        "controller": controller_name,
        "scenario": scenario_name,
        "delta_u": dict(delta_u),
        "env_version": "v4_plus_independent_esd1",
        "control_nominal_frequency_hz": float(env.base_env.FN),
        "andes_nominal_frequency_hz": nominal_hz,
        "frequency_reporting_basis": "legacy_control_hz",
        "metric_frequency_basis": "andes_physical_hz",
        "requested_steps": steps,
        "n_steps": len(traces),
        "tds_failed": tds_failed,
        "completed": not tds_failed and len(traces) == steps,
        "traces": traces,
        "controller_config": {
            **dict(controller_config),
            "area_residual": r278_area_inertia_contract().telemetry(),
        },
        "evidence_hashes": dict(evidence_hashes),
        "seed": seed,
    }
