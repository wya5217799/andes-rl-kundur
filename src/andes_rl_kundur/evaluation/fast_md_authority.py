"""Frozen R275 fast-inertia value gate above the R274 slow controller."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from andes_rl_kundur.control.active_power import DroopPIActivePowerController
from andes_rl_kundur.evaluation.active_power_authority import (
    R272_KI_SYSTEM_PU_PER_HZ_S_PER_DEVICE,
    R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE,
    summarise_active_power_trace,
)

BASELINE_CONTROLLER = "slow_droop_pi_fixed_md"
CANDIDATE_CONTROLLER = "slow_droop_pi_plus_common_m_pos"
FAST_ENDPOINTS = (
    "max_abs_rocof_hz_s",
    "worst_bus_peak_abs_hz",
    "normalized_sync_loss_hz2",
    "fast_inter_area_iae_hz_s",
)
COMMON_FAST_ENDPOINTS = frozenset(
    {"max_abs_rocof_hz_s", "worst_bus_peak_abs_hz"}
)
DIFFERENTIAL_FAST_ENDPOINTS = frozenset(
    {"normalized_sync_loss_hz2", "fast_inter_area_iae_hz_s"}
)
SLOW_ENDPOINTS = (
    "vsg_mean_iae_hz_s",
    "final_window_common_abs_mean_hz",
)


def frozen_fast_md_contract() -> dict[str, Any]:
    """Return the prospectively fixed, JSON-serializable R275 action contract."""
    amplitude = 0.25
    active_steps = 15
    dt_seconds = 0.2
    baseline_m = 200.0
    baseline_d = 100.0
    dm_max = 600.0
    pulse_delta_m = amplitude * dm_max
    return {
        "schema_version": 1,
        "name": "common_M_pos",
        "selection_evidence": {
            "round": "R270",
            "role": "development_only",
            "selected_oracle_scenarios": 5,
            "total_oracle_scenarios": 8,
        },
        "schedule": {
            "agent_pattern": [1.0, 1.0, 1.0, 1.0],
            "m_action_norm": amplitude,
            "d_action_norm": 0.0,
            "active_steps": active_steps,
            "active_duration_s": active_steps * dt_seconds,
            "inactive_m_action_norm": 0.0,
        },
        "physical": {
            "baseline_m": baseline_m,
            "baseline_d": baseline_d,
            "dm_max": dm_max,
            "pulse_delta_m": pulse_delta_m,
            "pulse_m": baseline_m + pulse_delta_m,
            "pulse_d": baseline_d,
            "control_dt_s": dt_seconds,
        },
        "budgets": {
            "max_abs_m_action_norm": amplitude,
            "max_abs_d_action_norm": 0.0,
            "max_action_slew_per_step": amplitude,
            "max_physical_m_target_change_per_step": pulse_delta_m,
            "max_interpolated_m_rate_per_s": pulse_delta_m / dt_seconds,
            "action_l1_agent_s": amplitude * active_steps * dt_seconds,
            "in_trace_total_variation": amplitude,
            "boundary_aware_total_variation": 2.0 * amplitude,
            "action_saturation_fraction": 0.0,
            "min_m": baseline_m,
            "max_m": baseline_m + pulse_delta_m,
            "min_d": baseline_d,
            "max_d": baseline_d,
        },
    }


@dataclass(frozen=True)
class FrozenCommonInertiaPulse:
    """The only R275 candidate fast M/D law."""

    amplitude: float = 0.25
    active_steps: int = 15

    def __post_init__(self) -> None:
        contract = frozen_fast_md_contract()
        if not np.isclose(
            self.amplitude,
            contract["schedule"]["m_action_norm"],
            rtol=0.0,
            atol=1e-15,
        ):
            raise ValueError("R275 amplitude is frozen at 0.25")
        if self.active_steps != contract["schedule"]["active_steps"]:
            raise ValueError("R275 active_steps is frozen at 15")

    def __call__(
        self,
        step: int,
        obs: dict[int, np.ndarray],
        n_agents: int,
    ) -> dict[int, np.ndarray]:
        del obs
        if n_agents != 4:
            raise ValueError(f"R275 common inertia pulse requires 4 agents, got {n_agents}")
        if step < 0:
            raise ValueError("step must be non-negative")
        m_action = self.amplitude if step < self.active_steps else 0.0
        return {
            index: np.asarray([m_action, 0.0], dtype=np.float32)
            for index in range(n_agents)
        }

    def telemetry(self) -> dict[str, Any]:
        return frozen_fast_md_contract()


def run_fast_md_scenario(
    scenario_name: str,
    delta_u: dict[str, float],
    *,
    seed: int = 42,
    steps: int = 300,
) -> dict[str, Any]:
    """Run one R275 candidate scenario through the public storage seam."""
    from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
        AndesMultiVSGEnvV4Storage,
    )

    env = AndesMultiVSGEnvV4Storage(
        random_disturbance=False,
        comm_fail_prob=0.0,
    )
    controller: DroopPIActivePowerController | None = None
    fast_controller = FrozenCommonInertiaPulse()
    traces: list[dict[str, Any]] = []
    tds_failed = False
    nominal_frequency_hz = 60.0
    try:
        env.seed(seed)
        env.STEPS_PER_EPISODE = steps
        obs = env.reset(delta_u=delta_u)
        nominal_frequency_hz = float(env.andes_nominal_frequency_hz)
        controller = DroopPIActivePowerController(
            device_count=env.bess_contract.device_count,
            nominal_frequency_hz=nominal_frequency_hz,
            kp_system_pu_per_hz_per_device=(
                R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE
            ),
            ki_system_pu_per_hz_s_per_device=(
                R272_KI_SYSTEM_PU_PER_HZ_S_PER_DEVICE
            ),
        )
        for step in range(steps):
            requested_power = controller.act(
                frequencies_hz=env.get_vsg_frequency_physical_hz(),
                dt_seconds=env.DT,
                previous_projection=env.last_bess_projection,
            )
            md_actions = fast_controller(step, obs, env.N_AGENTS)
            obs, _, done, info = env.step(
                md_actions,
                bess_power_request_pu=requested_power,
            )
            if info.get("tds_failed"):
                tds_failed = True
                break

            physical_frequency = np.asarray(
                info["freq_hz_physical"],
                dtype=float,
            )
            traces.append(
                {
                    "step": step,
                    "t": float(info["time"]),
                    "freq_hz_physical": physical_frequency.tolist(),
                    "delta_f_physical_hz": (
                        physical_frequency - nominal_frequency_hz
                    ).tolist(),
                    "action_norm": [
                        np.asarray(md_actions[index], dtype=float).tolist()
                        for index in range(env.N_AGENTS)
                    ],
                    "M_es": np.asarray(info["M_es"], dtype=float).tolist(),
                    "D_es": np.asarray(info["D_es"], dtype=float).tolist(),
                    "bess_requested_power_system_pu": np.asarray(
                        info["bess_requested_power_system_pu"],
                        dtype=float,
                    ).tolist(),
                    "bess_commanded_power_system_pu": np.asarray(
                        info["bess_commanded_power_system_pu"],
                        dtype=float,
                    ).tolist(),
                    "bess_actual_power_system_pu": np.asarray(
                        info["bess_actual_power_system_pu"],
                        dtype=float,
                    ).tolist(),
                    "bess_soc": np.asarray(info["bess_soc"], dtype=float).tolist(),
                    "bess_bus_voltage_pu": np.asarray(
                        info["bess_bus_voltage_pu"],
                        dtype=float,
                    ).tolist(),
                    "bess_saturation_reasons": info["bess_saturation_reasons"],
                    "bess_charge_energy_mwh_total": np.asarray(
                        info["bess_charge_energy_mwh_total"],
                        dtype=float,
                    ).tolist(),
                    "bess_discharge_energy_mwh_total": np.asarray(
                        info["bess_discharge_energy_mwh_total"],
                        dtype=float,
                    ).tolist(),
                    "bess_constraint_violations": info[
                        "bess_constraint_violations"
                    ],
                }
            )
            if done:
                break
    finally:
        env.close()

    return {
        "experiment": "r275_fast_md_authority",
        "controller": CANDIDATE_CONTROLLER,
        "scenario": scenario_name,
        "delta_u": dict(delta_u),
        "env_version": "v4_plus_independent_esd1",
        "control_nominal_frequency_hz": float(env.FN),
        "andes_nominal_frequency_hz": nominal_frequency_hz,
        "frequency_reporting_basis": "legacy_control_hz",
        "metric_frequency_basis": "andes_physical_hz",
        "requested_steps": steps,
        "n_steps": len(traces),
        "tds_failed": tds_failed,
        "completed": not tds_failed and len(traces) == steps,
        "traces": traces,
        "controller_config": {
            "kp_system_pu_per_hz_per_device": (
                R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE
            ),
            "ki_system_pu_per_hz_s_per_device": (
                R272_KI_SYSTEM_PU_PER_HZ_S_PER_DEVICE
            ),
            "fast_md": frozen_fast_md_contract(),
        },
        "seed": seed,
    }


def summarise_fast_md_trace(
    record: dict[str, Any],
    *,
    final_window_steps: int,
    fast_window_steps: int = 15,
) -> dict[str, Any]:
    """Add the registered fast inter-area and exact M/D action endpoints."""
    result = dict(
        summarise_active_power_trace(
            record,
            final_window_steps=final_window_steps,
        )
    )
    traces = record["traces"]
    if fast_window_steps < 1 or fast_window_steps > len(traces):
        raise ValueError("fast_window_steps must fit inside the completed trace")
    delta_f = np.asarray(
        [step["delta_f_physical_hz"] for step in traces],
        dtype=float,
    )
    if delta_f.shape[1] != 4:
        raise ValueError("R275 inter-area endpoint requires four VSG frequencies")
    dt = float(result["sample_interval_s"])
    area_mode = np.mean(delta_f[:, :2], axis=1) - np.mean(
        delta_f[:, 2:],
        axis=1,
    )
    actions = np.asarray(
        [step["action_norm"] for step in traces],
        dtype=float,
    )
    m_values = np.asarray([step["M_es"] for step in traces], dtype=float)
    d_values = np.asarray([step["D_es"] for step in traces], dtype=float)
    if actions.shape != (len(traces), 4, 2):
        raise ValueError("R275 action_norm must have shape [time, 4, 2]")
    initial_zero = np.zeros((1, 4, 2), dtype=float)
    boundary_diff = np.diff(
        np.concatenate([initial_zero, actions], axis=0),
        axis=0,
    )
    result.update(
        {
            "fast_window_steps": fast_window_steps,
            "fast_window_duration_s": fast_window_steps * dt,
            "fast_inter_area_iae_hz_s": float(
                np.sum(np.abs(area_mode[:fast_window_steps])) * dt
            ),
            "fast_inter_area_peak_abs_hz": float(
                np.max(np.abs(area_mode[:fast_window_steps]))
            ),
            "action_boundary_aware_total_variation": float(
                np.sum(
                    np.mean(
                        np.sum(np.abs(boundary_diff), axis=2),
                        axis=1,
                    )
                )
            ),
            "max_abs_action_slew_per_step": float(
                np.max(np.abs(boundary_diff))
            ),
            "max_abs_m_action_norm": float(np.max(np.abs(actions[:, :, 0]))),
            "max_abs_d_action_norm": float(np.max(np.abs(actions[:, :, 1]))),
            "min_m": float(np.min(m_values)),
            "max_m": float(np.max(m_values)),
            "min_d": float(np.min(d_values)),
            "max_d": float(np.max(d_values)),
        }
    )
    return result


def audit_fast_md_action(summary: dict[str, Any]) -> dict[str, bool]:
    """Check one completed candidate trace against the immutable action budget."""
    budgets = frozen_fast_md_contract()["budgets"]

    def exact(key: str, expected_key: str, *, atol: float = 1e-9) -> bool:
        return bool(
            np.isclose(
                float(summary[key]),
                float(budgets[expected_key]),
                rtol=0.0,
                atol=atol,
            )
        )

    return {
        "action_l1_exact": exact("action_l1_agent_s", "action_l1_agent_s"),
        "in_trace_tv_exact": exact(
            "action_total_variation",
            "in_trace_total_variation",
        ),
        "boundary_tv_exact": exact(
            "action_boundary_aware_total_variation",
            "boundary_aware_total_variation",
        ),
        "m_amplitude_exact": exact(
            "max_abs_m_action_norm",
            "max_abs_m_action_norm",
        ),
        "d_action_zero": exact(
            "max_abs_d_action_norm",
            "max_abs_d_action_norm",
        ),
        "slew_exact": exact(
            "max_abs_action_slew_per_step",
            "max_action_slew_per_step",
        ),
        "m_min_exact": exact("min_m", "min_m"),
        "m_max_exact": exact("max_m", "max_m"),
        "d_min_exact": exact("min_d", "min_d"),
        "d_max_exact": exact("max_d", "max_d"),
        "zero_action_saturation": exact(
            "action_saturation_fraction",
            "action_saturation_fraction",
        ),
    }


def _relative_decision(
    primary_contrast: dict[str, Any],
    endpoint: str,
) -> dict[str, float | bool]:
    effect = primary_contrast["endpoints"][endpoint]["ratio_of_means_percent"]
    point = float(effect["point"])
    upper = float(effect["percentile_95_interval"][1])
    return {
        "point_percent": point,
        "ci_upper_percent": upper,
        "material_improvement": point <= -2.0 and upper < 0.0,
    }


def classify_fast_md_authority(
    *,
    controller_summaries: dict[str, dict[str, Any]],
    primary_contrast: dict[str, Any] | None,
    total_scenarios: int,
    provenance_hashes_match: bool,
    action_budget_pass: bool,
    storage_guard_pass: bool,
    tail_guard_pass: bool,
) -> dict[str, Any]:
    """Apply the prospectively registered R275 four-way gate."""
    baseline = controller_summaries[BASELINE_CONTROLLER]
    candidate = controller_summaries[CANDIDATE_CONTROLLER]
    guards = {
        "provenance_hashes_match": provenance_hashes_match,
        "complete_primary_pairs": (
            baseline["complete_count"] == total_scenarios
            and candidate["complete_count"] == total_scenarios
        ),
        "candidate_failure_not_higher": (
            candidate["failure_count"] <= baseline["failure_count"]
        ),
        "zero_constraint_violations": (
            baseline["constraint_violation_count"] == 0
            and candidate["constraint_violation_count"] == 0
        ),
        "action_budget_pass": action_budget_pass,
        "storage_guard_pass": storage_guard_pass,
        "tail_guard_pass": tail_guard_pass,
    }
    validity_guard_names = (
        "provenance_hashes_match",
        "complete_primary_pairs",
        "candidate_failure_not_higher",
        "zero_constraint_violations",
        "action_budget_pass",
        "storage_guard_pass",
    )
    if primary_contrast is None or not all(
        guards[name] for name in validity_guard_names
    ):
        return {
            "classification": "INVALID",
            "reason": (
                "no complete paired endpoint contrast is available"
                if primary_contrast is None
                else "one or more provenance, completion, action, or storage guards failed"
            ),
            "guards": guards,
            "fast_endpoints": {},
            "slow_endpoints": {},
            "cleared_fast_endpoint_count": 0,
        }

    fast = {
        endpoint: _relative_decision(primary_contrast, endpoint)
        for endpoint in FAST_ENDPOINTS
    }
    slow = {
        endpoint: _relative_decision(primary_contrast, endpoint)
        for endpoint in SLOW_ENDPOINTS
    }
    cleared = {
        endpoint
        for endpoint, decision in fast.items()
        if decision["material_improvement"]
    }
    fast_no_harm = all(
        float(decision["point_percent"]) <= 5.0
        for decision in fast.values()
    )
    slow_guard_pass = all(
        float(decision["point_percent"]) <= 2.0
        and float(decision["ci_upper_percent"]) < 5.0
        for decision in slow.values()
    )
    common_clear = bool(cleared & COMMON_FAST_ENDPOINTS)
    differential_clear = bool(cleared & DIFFERENTIAL_FAST_ENDPOINTS)
    joint_fast_gate = (
        len(cleared) >= 2
        and common_clear
        and differential_clear
        and fast_no_harm
    )
    guards.update(
        {
            "fast_no_harm_over_5pct": fast_no_harm,
            "slow_restoration_guard_pass": slow_guard_pass,
            "common_fast_endpoint_clear": common_clear,
            "differential_fast_endpoint_clear": differential_clear,
        }
    )

    if not fast_no_harm:
        classification = "NO-INDEPENDENT-FAST-VALUE"
        reason = "at least one registered fast endpoint worsens by more than 5%"
    elif not cleared:
        classification = "NO-INDEPENDENT-FAST-VALUE"
        reason = "no registered fast endpoint clears materiality and uncertainty"
    elif joint_fast_gate and slow_guard_pass and tail_guard_pass:
        classification = "FAST-LAYER-POSITIVE"
        reason = "common and differential fast value clears with all guards"
    else:
        classification = "FAST-LAYER-PARTIAL"
        reason = "some fast value clears but the full joint, restoration, or tail gate does not"

    return {
        "classification": classification,
        "reason": reason,
        "guards": guards,
        "fast_endpoints": fast,
        "slow_endpoints": slow,
        "cleared_fast_endpoints": sorted(cleared),
        "cleared_fast_endpoint_count": len(cleared),
    }
