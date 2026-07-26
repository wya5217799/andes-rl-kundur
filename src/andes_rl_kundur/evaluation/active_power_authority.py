"""Physical, terminal-window, and BESS audit endpoints for R272."""

from __future__ import annotations

from typing import Any

import numpy as np

from andes_rl_kundur.control.active_power import DroopPIActivePowerController
from andes_rl_kundur.evaluation.physical_endpoints import summarise_physical_trace

R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE = 2.0
R272_KI_SYSTEM_PU_PER_HZ_S_PER_DEVICE = 0.2


def classify_active_power_authority(
    *,
    controller_summaries: dict[str, dict[str, Any]],
    primary_contrast: dict[str, Any] | None,
    total_scenarios: int,
    provenance_hashes_match: bool,
) -> dict[str, Any]:
    """Apply the prospectively registered R272 joint authority gate."""
    baseline = controller_summaries["zero_support"]
    primary = controller_summaries["droop_pi"]
    basic_guards = {
        "provenance_hashes_match": provenance_hashes_match,
        "complete_primary_pairs": (
            baseline["complete_count"] == total_scenarios
            and primary["complete_count"] == total_scenarios
        ),
        "candidate_failure_not_higher": (
            primary["failure_count"] <= baseline["failure_count"]
        ),
        "zero_constraint_violations": (
            primary["constraint_violation_count"] == 0
        ),
    }
    if not provenance_hashes_match or baseline["failure_count"] > 0:
        reason = (
            "one or more frozen provenance hashes do not match"
            if not provenance_hashes_match
            else "the matched zero-support baseline is numerically infeasible on the formal bank"
        )
        return {
            "classification": "INVALID",
            "reason": reason,
            "co_primary": {},
            "guards": {
                **basic_guards,
                "safety_not_worse_over_5pct": False,
            },
            "safety_effects_percent": {},
        }

    def percent_effect(endpoint: str) -> float:
        reference = float(baseline["means"][endpoint])
        candidate = float(primary["means"][endpoint])
        if np.isclose(reference, 0.0, rtol=0.0, atol=1e-15):
            return 0.0 if np.isclose(candidate, 0.0, atol=1e-15) else float("inf")
        return 100.0 * (candidate / reference - 1.0)

    safety_effects = {
        endpoint: percent_effect(endpoint)
        for endpoint in (
            "normalized_sync_loss_hz2",
            "worst_bus_peak_abs_hz",
            "max_abs_rocof_hz_s",
        )
    }
    endpoint_decisions: dict[str, Any] = {}
    if primary_contrast is not None:
        for endpoint in (
            "vsg_mean_iae_hz_s",
            "final_window_common_abs_mean_hz",
        ):
            effect = primary_contrast["endpoints"][endpoint][
                "ratio_of_means_percent"
            ]
            point = float(effect["point"])
            upper = float(effect["percentile_95_interval"][1])
            endpoint_decisions[endpoint] = {
                "point_percent": point,
                "ci_upper_percent": upper,
                "material_improvement": point <= -2.0 and upper < 0.0,
            }

    guards = {
        **basic_guards,
        "safety_not_worse_over_5pct": all(
            effect <= 5.0 for effect in safety_effects.values()
        ),
    }

    if primary_contrast is None:
        classification = "INVALID"
        reason = "no complete paired physical endpoints are available"
    elif all(item["material_improvement"] for item in endpoint_decisions.values()) and all(
        guards.values()
    ):
        classification = "AUTHORITY-POSITIVE"
        reason = "both co-primary materiality/uncertainty gates and all guards pass"
    elif any(
        item["point_percent"] < 0.0 for item in endpoint_decisions.values()
    ):
        classification = "AUTHORITY-PARTIAL"
        reason = "restoration improves but a joint materiality, uncertainty, or guard failed"
    else:
        classification = "NO-MATERIAL-AUTHORITY"
        reason = "the valid primary controller does not improve either co-primary mean"

    return {
        "classification": classification,
        "reason": reason,
        "co_primary": endpoint_decisions,
        "guards": guards,
        "safety_effects_percent": safety_effects,
    }


def run_active_power_scenario(
    scenario_name: str,
    delta_u: dict[str, float],
    *,
    controller_name: str,
    seed: int = 42,
    steps: int = 300,
) -> dict[str, Any]:
    """Run one R272 controller/scenario pair through the storage public seam."""
    from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
        AndesMultiVSGEnvV4Storage,
    )

    if controller_name not in {"zero_support", "droop", "droop_pi"}:
        raise ValueError(f"unsupported R272 controller: {controller_name}")

    env = AndesMultiVSGEnvV4Storage(
        random_disturbance=False,
        comm_fail_prob=0.0,
    )
    controller: DroopPIActivePowerController | None = None
    traces: list[dict[str, Any]] = []
    tds_failed = False
    nominal_frequency_hz = 60.0
    try:
        env.seed(seed)
        env.STEPS_PER_EPISODE = steps
        env.reset(delta_u=delta_u)
        nominal_frequency_hz = float(env.andes_nominal_frequency_hz)
        if controller_name != "zero_support":
            controller = DroopPIActivePowerController(
                device_count=env.bess_contract.device_count,
                nominal_frequency_hz=nominal_frequency_hz,
                kp_system_pu_per_hz_per_device=(
                    R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE
                ),
                ki_system_pu_per_hz_s_per_device=(
                    R272_KI_SYSTEM_PU_PER_HZ_S_PER_DEVICE
                    if controller_name == "droop_pi"
                    else 0.0
                ),
            )
        zero_md = {
            index: np.zeros(2, dtype=float)
            for index in range(env.N_AGENTS)
        }
        for step in range(steps):
            if controller is None:
                requested_power = np.zeros(env.bess_contract.device_count)
            else:
                requested_power = controller.act(
                    frequencies_hz=env.get_vsg_frequency_physical_hz(),
                    dt_seconds=env.DT,
                    previous_projection=env.last_bess_projection,
                )
            _, _, done, info = env.step(
                zero_md,
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
                    "action_norm": [[0.0, 0.0] for _ in range(env.N_AGENTS)],
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
        "experiment": "r272_active_power_authority",
        "controller": controller_name,
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
                0.0
                if controller_name == "zero_support"
                else R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE
            ),
            "ki_system_pu_per_hz_s_per_device": (
                R272_KI_SYSTEM_PU_PER_HZ_S_PER_DEVICE
                if controller_name == "droop_pi"
                else 0.0
            ),
        },
        "seed": seed,
    }

def summarise_active_power_trace(
    record: dict[str, Any],
    *,
    final_window_steps: int,
) -> dict[str, Any]:
    """Extend physical endpoints with the registered active-power evidence."""
    result = dict(summarise_physical_trace(record))
    traces = record["traces"]
    if final_window_steps < 1 or final_window_steps > len(traces):
        raise ValueError("final_window_steps must fit inside the completed trace")

    delta_f = np.asarray(
        [step["delta_f_physical_hz"] for step in traces],
        dtype=float,
    )
    common_delta = np.mean(delta_f, axis=1)
    commands = np.asarray(
        [step["bess_commanded_power_system_pu"] for step in traces],
        dtype=float,
    )
    soc = np.asarray([step["bess_soc"] for step in traces], dtype=float)
    dt = float(result["sample_interval_s"])
    saturation_count = sum(
        bool(reasons)
        for step in traces
        for reasons in step["bess_saturation_reasons"]
    )
    device_steps = commands.shape[0] * commands.shape[1]
    violations = [
        violation
        for step in traces
        for violation in step["bess_constraint_violations"]
    ]
    result.update(
        {
            "final_window_steps": final_window_steps,
            "final_window_duration_s": final_window_steps * dt,
            "final_window_common_abs_mean_hz": float(
                np.mean(np.abs(common_delta[-final_window_steps:]))
            ),
            "terminal_common_abs_hz": float(abs(common_delta[-1])),
            "bess_command_l1_device_s": float(
                np.sum(np.mean(np.abs(commands), axis=1)) * dt
            ),
            "bess_command_total_variation": float(
                np.sum(np.mean(np.abs(np.diff(commands, axis=0)), axis=1))
            ),
            "bess_saturation_fraction": saturation_count / device_steps,
            "bess_min_soc": float(np.min(soc)),
            "bess_max_soc": float(np.max(soc)),
            "bess_terminal_soc_mean": float(np.mean(soc[-1])),
            "bess_charge_energy_mwh_total": float(
                np.sum(traces[-1]["bess_charge_energy_mwh_total"])
            ),
            "bess_discharge_energy_mwh_total": float(
                np.sum(traces[-1]["bess_discharge_energy_mwh_total"])
            ),
            "bess_constraint_violation_count": len(violations),
            "bess_constraint_violations": violations,
        }
    )
    return result
