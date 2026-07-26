"""Full-horizon R278 policy execution and action audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np

from andes_rl_kundur.agents.shared_area_td3 import SharedAreaTD3
from andes_rl_kundur.control.area_inertia_residual import (
    r278_area_inertia_contract,
)
from andes_rl_kundur.env.andes.icems_residual_env import ICEMSResidualEnv
from andes_rl_kundur.evaluation.fast_md_authority import (
    summarise_fast_md_trace,
)

CONTROLLER = "r278_shared_area_td3"
PRIMARY_ENDPOINTS = (
    "normalized_sync_loss_hz2",
    "fast_inter_area_iae_hz_s",
)
FAST_GUARD_ENDPOINTS = (
    "max_abs_rocof_hz_s",
    "worst_bus_peak_abs_hz",
)
SLOW_GUARD_ENDPOINTS = (
    "vsg_mean_iae_hz_s",
    "final_window_common_abs_mean_hz",
)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_icems_policy_scenario(
    checkpoint_path: str | Path,
    scenario_name: str,
    delta_u: dict[str, float],
    *,
    seed: int = 42,
    steps: int = 300,
    device: str = "cpu",
) -> dict[str, Any]:
    """Run one deterministic R278 checkpoint for a full physical horizon."""
    checkpoint = Path(checkpoint_path)
    agent = SharedAreaTD3(
        obs_dim=7,
        agent_count=4,
        hidden_sizes=[64, 64],
        device=device,
    )
    metadata = agent.load(checkpoint)
    if metadata.get("round") != "R278":
        raise ValueError("checkpoint is not an R278 policy")

    from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
        AndesMultiVSGEnvV4Storage,
    )

    env = ICEMSResidualEnv(
        AndesMultiVSGEnvV4Storage(
            random_disturbance=False,
            comm_fail_prob=0.0,
        )
    )
    traces: list[dict[str, Any]] = []
    tds_failed = False
    nominal_frequency_hz = 60.0
    try:
        env.seed(seed)
        env.STEPS_PER_EPISODE = steps
        observation = env.reset(delta_u=delta_u)
        nominal_frequency_hz = float(
            env.base_env.andes_nominal_frequency_hz
        )
        for step in range(steps):
            raw = agent.select_raw_actions(
                observation,
                deterministic=True,
            )
            observation, _rewards, done, info = env.step(raw)
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
                    "action_norm": np.asarray(
                        info["r278_executed_md_action_norm"],
                        dtype=float,
                    ).tolist(),
                    "M_es": np.asarray(info["M_es"], dtype=float).tolist(),
                    "D_es": np.asarray(info["D_es"], dtype=float).tolist(),
                    "r278_raw_z": np.asarray(
                        info["r278_raw_z"],
                        dtype=float,
                    ).tolist(),
                    "r278_q": float(info["r278_q"]),
                    "r278_residual_action_norm": np.asarray(
                        info["r278_residual_action_norm"],
                        dtype=float,
                    ).tolist(),
                    "r278_physical_m_residual": np.asarray(
                        info["r278_physical_m_residual"],
                        dtype=float,
                    ).tolist(),
                    "r278_physical_m_residual_sum": float(
                        info["r278_physical_m_residual_sum"]
                    ),
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
                    "bess_soc": np.asarray(
                        info["bess_soc"],
                        dtype=float,
                    ).tolist(),
                    "bess_bus_voltage_pu": np.asarray(
                        info["bess_bus_voltage_pu"],
                        dtype=float,
                    ).tolist(),
                    "bess_saturation_reasons": info[
                        "bess_saturation_reasons"
                    ],
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
        "experiment": "r278_icems_residual_pilot",
        "controller": CONTROLLER,
        "scenario": scenario_name,
        "delta_u": dict(delta_u),
        "env_version": "v4_plus_independent_esd1",
        "control_nominal_frequency_hz": float(env.base_env.FN),
        "andes_nominal_frequency_hz": nominal_frequency_hz,
        "frequency_reporting_basis": "legacy_control_hz",
        "metric_frequency_basis": "andes_physical_hz",
        "requested_steps": steps,
        "n_steps": len(traces),
        "tds_failed": tds_failed,
        "completed": not tds_failed and len(traces) == steps,
        "traces": traces,
        "controller_config": {
            "round": "R278",
            "checkpoint": str(checkpoint.resolve()),
            "checkpoint_sha256": sha256_file(checkpoint),
            "checkpoint_metadata": metadata,
            "area_residual": r278_area_inertia_contract().telemetry(),
        },
        "seed": seed,
    }


def summarise_icems_policy_trace(
    record: dict[str, Any],
    *,
    final_window_steps: int = 50,
    fast_window_steps: int = 15,
) -> dict[str, Any]:
    """Reuse registered physical endpoints and add learned-action telemetry."""
    summary = summarise_fast_md_trace(
        record,
        final_window_steps=final_window_steps,
        fast_window_steps=fast_window_steps,
    )
    traces = record["traces"]
    q = np.asarray([row["r278_q"] for row in traces], dtype=float)
    residual = np.asarray(
        [row["r278_residual_action_norm"] for row in traces],
        dtype=float,
    )
    physical_sum = np.asarray(
        [row["r278_physical_m_residual_sum"] for row in traces],
        dtype=float,
    )
    initial = np.asarray([0.0], dtype=float)
    q_boundary = np.diff(np.concatenate([initial, q]))
    summary.update(
        {
            "r278_max_abs_q": float(np.max(np.abs(q))),
            "r278_max_abs_q_slew": float(np.max(np.abs(q_boundary))),
            "r278_q_total_variation": float(np.sum(np.abs(q_boundary))),
            "r278_max_abs_residual_sum": float(
                np.max(np.abs(np.sum(residual, axis=1)))
            ),
            "r278_max_abs_physical_m_residual_sum": float(
                np.max(np.abs(physical_sum))
            ),
            "r278_post_window_max_abs_q": float(
                np.max(np.abs(q[fast_window_steps:]))
                if len(q) > fast_window_steps
                else 0.0
            ),
        }
    )
    return summary


def audit_icems_policy_action(summary: dict[str, Any]) -> dict[str, bool]:
    """Check the learned trace against the frozen R278 action contract."""
    contract = r278_area_inertia_contract()
    return {
        "q_magnitude": bool(
            summary["r278_max_abs_q"] <= contract.q_max + 1e-9
        ),
        "q_slew": bool(
            summary["r278_max_abs_q_slew"]
            <= contract.q_slew_max + 1e-9
        ),
        "normalized_zero_sum": bool(
            summary["r278_max_abs_residual_sum"] <= 1e-9
        ),
        "physical_zero_sum": bool(
            summary["r278_max_abs_physical_m_residual_sum"] <= 1e-8
        ),
        "post_window_zero": bool(
            summary["r278_post_window_max_abs_q"] <= 1e-9
        ),
        "d_action_zero": bool(summary["max_abs_d_action_norm"] <= 1e-9),
        "m_action_range": bool(
            summary["max_abs_m_action_norm"] <= 0.5 + 1e-9
            and summary["min_m"] >= 200.0 - 1e-8
            and summary["max_m"] <= 500.0 + 1e-8
        ),
    }


def classify_icems_pilot(
    *,
    primary_contrast: dict[str, Any] | None,
    provenance_valid: bool,
    complete_pairs: bool,
    action_guard_pass: bool,
    storage_guard_pass: bool,
    tail_guard_pass: bool,
) -> dict[str, Any]:
    """Apply the prospectively frozen R278 single-seed development gate."""
    validity_guards = {
        "provenance_valid": bool(provenance_valid),
        "complete_24_pairs": bool(complete_pairs),
        "action_guard_pass": bool(action_guard_pass),
        "storage_guard_pass": bool(storage_guard_pass),
    }
    if primary_contrast is None or not all(validity_guards.values()):
        return {
            "classification": "INVALID",
            "reason": (
                "no complete paired endpoint contrast is available"
                if primary_contrast is None
                else "one or more provenance, completion, action, or storage guards failed"
            ),
            "guards": {**validity_guards, "tail_guard_pass": bool(tail_guard_pass)},
            "primary_endpoints": {},
            "fast_guards": {},
            "slow_guards": {},
        }

    def effect(endpoint: str) -> tuple[float, float]:
        relative = primary_contrast["endpoints"][endpoint][
            "ratio_of_means_percent"
        ]
        return (
            float(relative["point"]),
            float(relative["percentile_95_interval"][1]),
        )

    primary = {}
    for endpoint in PRIMARY_ENDPOINTS:
        point, upper = effect(endpoint)
        primary[endpoint] = {
            "point_percent": point,
            "ci_upper_percent": upper,
            "material_improvement": point <= -2.0 and upper < 0.0,
        }
    fast = {}
    for endpoint in FAST_GUARD_ENDPOINTS:
        point, upper = effect(endpoint)
        fast[endpoint] = {
            "point_percent": point,
            "ci_upper_percent": upper,
            "mean_no_worse_5pct": point <= 5.0,
        }
    slow = {}
    for endpoint in SLOW_GUARD_ENDPOINTS:
        point, upper = effect(endpoint)
        slow[endpoint] = {
            "point_percent": point,
            "ci_upper_percent": upper,
            "mean_no_worse_2pct": point <= 2.0,
        }
    guards = {
        **validity_guards,
        "both_primary_endpoints_clear": all(
            row["material_improvement"] for row in primary.values()
        ),
        "fast_mean_guard_pass": all(
            row["mean_no_worse_5pct"] for row in fast.values()
        ),
        "slow_mean_guard_pass": all(
            row["mean_no_worse_2pct"] for row in slow.values()
        ),
        "tail_guard_pass": bool(tail_guard_pass),
    }
    go = all(guards.values())
    return {
        "classification": "PILOT-GO" if go else "PILOT-NO-GO",
        "reason": (
            "both co-primary endpoints clear the registered material and uncertainty gate"
            if go
            else "one or more registered efficacy or no-harm gates did not clear"
        ),
        "guards": guards,
        "primary_endpoints": primary,
        "fast_guards": fast,
        "slow_guards": slow,
    }
