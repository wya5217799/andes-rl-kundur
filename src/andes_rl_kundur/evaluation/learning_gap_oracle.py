"""R277 optimistic zero-sum inertia learning-gap primitives."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from andes_rl_kundur.control.active_power import DroopPIActivePowerController
from andes_rl_kundur.evaluation.active_power_authority import (
    R272_KI_SYSTEM_PU_PER_HZ_S_PER_DEVICE,
    R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE,
)
from andes_rl_kundur.evaluation.fast_md_authority import summarise_fast_md_trace

BASELINE_CONTROLLER = "r275_combined"
PRIMARY_ENDPOINTS = (
    "normalized_sync_loss_hz2",
    "fast_inter_area_iae_hz_s",
)
COMMON_GUARD_ENDPOINTS = (
    "max_abs_rocof_hz_s",
    "worst_bus_peak_abs_hz",
)
RESTORATION_GUARD_ENDPOINTS = (
    "vsg_mean_iae_hz_s",
    "final_window_common_abs_mean_hz",
)
ENDPOINTS = (
    *PRIMARY_ENDPOINTS,
    *COMMON_GUARD_ENDPOINTS,
    *RESTORATION_GUARD_ENDPOINTS,
)

_UNSIGNED_BASIS = (
    ("h1", (1.0, 1.0, -1.0, -1.0)),
    ("h2", (1.0, -1.0, 1.0, -1.0)),
    ("h3", (1.0, -1.0, -1.0, 1.0)),
)
CANDIDATE_PATTERNS: dict[str, tuple[float, float, float, float]] = {
    f"{name}_{sign_name}": tuple(sign * value for value in pattern)
    for name, pattern in _UNSIGNED_BASIS
    for sign_name, sign in (("pos", 1.0), ("neg", -1.0))
}
CANDIDATE_NAMES = tuple(CANDIDATE_PATTERNS)


def frozen_learning_gap_contract() -> dict[str, Any]:
    """Return the JSON-serializable R277 action and selection contract."""
    common_amplitude = 0.25
    differential_amplitude = 0.25
    active_steps = 15
    dt_seconds = 0.2
    baseline_m = 200.0
    dm_max = 600.0
    return {
        "schema_version": 1,
        "name": "zero_sum_hadamard_inertia_library",
        "selection_evidence": {
            "common_pulse": "R275 sealed common_M_pos",
            "differential_basis": "R270 development-only area_M amplitude/window",
            "role": "optimistic_outcome_seeing_learning_margin",
        },
        "schedule": {
            "common_m_action_norm": common_amplitude,
            "differential_m_action_norm": differential_amplitude,
            "d_action_norm": 0.0,
            "active_steps": active_steps,
            "active_duration_s": active_steps * dt_seconds,
            "inactive_action_norm": 0.0,
            "candidate_order": list(CANDIDATE_NAMES),
            "patterns": {
                name: list(pattern)
                for name, pattern in CANDIDATE_PATTERNS.items()
            },
        },
        "physical": {
            "baseline_m": baseline_m,
            "baseline_d": 100.0,
            "dm_max": dm_max,
            "active_min_m": baseline_m,
            "active_max_m": baseline_m
            + dm_max * (common_amplitude + differential_amplitude),
            "active_fleet_mean_m": baseline_m + dm_max * common_amplitude,
            "inactive_m": baseline_m,
            "d": 100.0,
            "control_dt_s": dt_seconds,
        },
        "budgets": {
            "residual_sum": 0.0,
            "max_abs_differential_action_norm": differential_amplitude,
            "min_executed_m_action_norm": 0.0,
            "max_executed_m_action_norm": (
                common_amplitude + differential_amplitude
            ),
            "mean_executed_m_action_norm": common_amplitude,
            "max_abs_d_action_norm": 0.0,
            "action_l1_agent_s": (
                common_amplitude * active_steps * dt_seconds
            ),
            "in_trace_total_variation": common_amplitude,
            "boundary_aware_total_variation": 2.0 * common_amplitude,
            "max_action_slew_per_step": (
                common_amplitude + differential_amplitude
            ),
            "action_saturation_fraction": 0.0,
        },
        "oracle": {
            "objective": (
                "0.5*(candidate_sync/baseline_sync"
                " + candidate_fast_interarea/baseline_fast_interarea)"
            ),
            "primary_no_worse_fraction": 0.0,
            "common_guard_fraction": 0.05,
            "restoration_guard_fraction": 0.02,
            "tie_break": ["baseline", *CANDIDATE_NAMES],
        },
    }


@dataclass(frozen=True)
class FrozenZeroSumInertiaPulse:
    """One R277 common-plus-differential scheduled inertia action."""

    candidate_name: str

    def __post_init__(self) -> None:
        if self.candidate_name not in CANDIDATE_PATTERNS:
            raise ValueError(f"unknown R277 candidate: {self.candidate_name}")

    def __call__(
        self,
        step: int,
        obs: dict[int, np.ndarray],
        n_agents: int,
    ) -> dict[int, np.ndarray]:
        del obs
        if n_agents != 4:
            raise ValueError(f"R277 zero-sum pulse requires 4 agents, got {n_agents}")
        if step < 0:
            raise ValueError("step must be non-negative")
        contract = frozen_learning_gap_contract()
        schedule = contract["schedule"]
        if step < schedule["active_steps"]:
            common = float(schedule["common_m_action_norm"])
            differential = float(schedule["differential_m_action_norm"])
            pattern = CANDIDATE_PATTERNS[self.candidate_name]
            m_actions = common + differential * np.asarray(pattern, dtype=float)
        else:
            m_actions = np.zeros(4, dtype=float)
        return {
            index: np.asarray([m_actions[index], 0.0], dtype=np.float32)
            for index in range(4)
        }

    def telemetry(self) -> dict[str, Any]:
        contract = frozen_learning_gap_contract()
        return {
            "candidate": self.candidate_name,
            "pattern": list(CANDIDATE_PATTERNS[self.candidate_name]),
            "contract": contract,
        }


def run_learning_gap_scenario(
    scenario_name: str,
    delta_u: dict[str, float],
    *,
    candidate_name: str,
    seed: int = 42,
    steps: int = 300,
) -> dict[str, Any]:
    """Run one R277 candidate around the unchanged slow active-power layer."""
    from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
        AndesMultiVSGEnvV4Storage,
    )

    env = AndesMultiVSGEnvV4Storage(
        random_disturbance=False,
        comm_fail_prob=0.0,
    )
    fast_controller = FrozenZeroSumInertiaPulse(candidate_name)
    slow_controller: DroopPIActivePowerController | None = None
    traces: list[dict[str, Any]] = []
    tds_failed = False
    nominal_frequency_hz = 60.0
    try:
        env.seed(seed)
        env.STEPS_PER_EPISODE = steps
        obs = env.reset(delta_u=delta_u)
        nominal_frequency_hz = float(env.andes_nominal_frequency_hz)
        slow_controller = DroopPIActivePowerController(
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
            requested_power = slow_controller.act(
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
        "experiment": "r277_learning_gap_oracle",
        "controller": candidate_name,
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
            "fast_md": fast_controller.telemetry(),
        },
        "seed": seed,
    }


def audit_zero_sum_action(record: dict[str, Any]) -> dict[str, bool]:
    """Check exact R277 M/D schedule and physical fleet-mean invariants."""
    candidate = str(record["controller"])
    if candidate not in CANDIDATE_PATTERNS:
        raise ValueError(f"unknown candidate in trace: {candidate}")
    contract = frozen_learning_gap_contract()
    schedule = contract["schedule"]
    physical = contract["physical"]
    expected_controller = FrozenZeroSumInertiaPulse(candidate)
    checks = {
        "completed": bool(record.get("completed")),
        "tds_not_failed": not bool(record.get("tds_failed")),
        "exact_action": True,
        "residual_zero_sum": True,
        "fleet_mean_action_exact": True,
        "physical_m_exact": True,
        "fleet_mean_m_exact": True,
        "d_exact": True,
    }
    obs = {index: np.zeros(1, dtype=np.float32) for index in range(4)}
    for step_index, trace in enumerate(record.get("traces", [])):
        actual_action = np.asarray(trace["action_norm"], dtype=float)
        expected_action = np.asarray(
            [
                expected_controller(step_index, obs, 4)[index]
                for index in range(4)
            ],
            dtype=float,
        )
        checks["exact_action"] &= bool(
            np.allclose(actual_action, expected_action, rtol=0.0, atol=1e-9)
        )
        if step_index < schedule["active_steps"]:
            residual = actual_action[:, 0] - float(
                schedule["common_m_action_norm"]
            )
            expected_mean_action = float(schedule["common_m_action_norm"])
            expected_mean_m = float(physical["active_fleet_mean_m"])
        else:
            residual = actual_action[:, 0]
            expected_mean_action = 0.0
            expected_mean_m = float(physical["inactive_m"])
        checks["residual_zero_sum"] &= bool(
            np.isclose(np.sum(residual), 0.0, rtol=0.0, atol=1e-9)
        )
        checks["fleet_mean_action_exact"] &= bool(
            np.isclose(
                np.mean(actual_action[:, 0]),
                expected_mean_action,
                rtol=0.0,
                atol=1e-9,
            )
        )
        actual_m = np.asarray(trace["M_es"], dtype=float)
        expected_m = float(physical["baseline_m"]) + float(
            physical["dm_max"]
        ) * actual_action[:, 0]
        checks["physical_m_exact"] &= bool(
            np.allclose(actual_m, expected_m, rtol=0.0, atol=1e-8)
        )
        checks["fleet_mean_m_exact"] &= bool(
            np.isclose(
                np.mean(actual_m),
                expected_mean_m,
                rtol=0.0,
                atol=1e-8,
            )
        )
        checks["d_exact"] &= bool(
            np.allclose(
                np.asarray(trace["D_es"], dtype=float),
                float(physical["d"]),
                rtol=0.0,
                atol=1e-8,
            )
            and np.allclose(actual_action[:, 1], 0.0, rtol=0.0, atol=1e-9)
        )
    return {name: bool(value) for name, value in checks.items()}


def summarise_learning_gap_trace(
    record: dict[str, Any],
    *,
    final_window_steps: int = 50,
    fast_window_steps: int = 15,
) -> dict[str, Any]:
    """Summarise one completed R277 or reused R275 trace."""
    return summarise_fast_md_trace(
        record,
        final_window_steps=final_window_steps,
        fast_window_steps=fast_window_steps,
    )


def select_outcome_oracle(
    baseline_by_scenario: Mapping[str, Mapping[str, float]],
    candidates_by_scenario: Mapping[
        str,
        Mapping[str, Mapping[str, float] | None],
    ],
    *,
    valid_candidates: Mapping[str, Mapping[str, bool]],
) -> tuple[dict[str, Any], dict[str, dict[str, float]]]:
    """Select the best guarded full-outcome schedule per scenario."""
    if set(baseline_by_scenario) != set(candidates_by_scenario):
        raise ValueError("baseline and candidate scenario sets differ")
    selections: dict[str, Any] = {}
    selected: dict[str, dict[str, float]] = {}
    counts = {BASELINE_CONTROLLER: 0, **{name: 0 for name in CANDIDATE_NAMES}}
    reason_counts: dict[str, int] = {}
    eps = 1e-12
    for scenario in baseline_by_scenario:
        baseline = dict(baseline_by_scenario[scenario])
        if any(float(baseline[endpoint]) <= 0.0 for endpoint in PRIMARY_ENDPOINTS):
            raise ValueError(f"non-positive primary baseline for {scenario}")
        candidate_rows: list[dict[str, Any]] = []
        eligible_rows: list[tuple[float, int, str, dict[str, float]]] = []
        for order, name in enumerate(CANDIDATE_NAMES, start=1):
            summary = candidates_by_scenario[scenario].get(name)
            reasons: list[str] = []
            if not valid_candidates[scenario].get(name, False):
                reasons.append("invalid_contract_or_completion")
            if summary is None:
                reasons.append("missing_summary")
            if summary is not None and not reasons:
                candidate = dict(summary)
                for endpoint in PRIMARY_ENDPOINTS:
                    if float(candidate[endpoint]) > float(baseline[endpoint]) + eps:
                        reasons.append(f"{endpoint}_worse")
                for endpoint in COMMON_GUARD_ENDPOINTS:
                    if float(candidate[endpoint]) > 1.05 * float(
                        baseline[endpoint]
                    ) + eps:
                        reasons.append(f"{endpoint}_over_5pct")
                for endpoint in RESTORATION_GUARD_ENDPOINTS:
                    if float(candidate[endpoint]) > 1.02 * float(
                        baseline[endpoint]
                    ) + eps:
                        reasons.append(f"{endpoint}_over_2pct")
                if int(candidate["bess_constraint_violation_count"]) != 0:
                    reasons.append("bess_constraint_violation")
                if int(candidate["bess_saturation_reason_count"]) != 0:
                    reasons.append("bess_saturation")
                score = 0.5 * (
                    float(candidate[PRIMARY_ENDPOINTS[0]])
                    / float(baseline[PRIMARY_ENDPOINTS[0]])
                    + float(candidate[PRIMARY_ENDPOINTS[1]])
                    / float(baseline[PRIMARY_ENDPOINTS[1]])
                )
            else:
                candidate = None
                score = None
            eligible = not reasons
            candidate_rows.append(
                {
                    "candidate": name,
                    "eligible": eligible,
                    "reasons": reasons,
                    "objective": score,
                }
            )
            for reason in reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            if eligible and candidate is not None and score is not None:
                eligible_rows.append((float(score), order, name, candidate))

        baseline_score = 1.0
        best = (baseline_score, 0, BASELINE_CONTROLLER, baseline)
        for row in eligible_rows:
            if (row[0], row[1]) < (best[0], best[1]):
                best = row
        _, _, selected_name, selected_summary = best
        counts[selected_name] += 1
        selected[scenario] = selected_summary
        selections[scenario] = {
            "selected": selected_name,
            "selected_objective": float(best[0]),
            "candidate_rows": candidate_rows,
        }
    return {
        "role": "outcome_seeing_development_upper_bound",
        "selection_counts": counts,
        "nonbaseline_selection_count": sum(
            count for name, count in counts.items() if name != BASELINE_CONTROLLER
        ),
        "ineligibility_reason_counts": dict(sorted(reason_counts.items())),
        "scenarios": selections,
    }, selected


def classify_learning_gap(
    *,
    contrast: Mapping[str, Any] | None,
    nonbaseline_selection_count: int,
    provenance_guard_pass: bool,
    completion_guard_pass: bool,
    action_contract_guard_pass: bool,
    storage_contract_guard_pass: bool,
    storage_relative_guard_pass: bool,
    tail_guard_pass: bool,
) -> dict[str, Any]:
    """Apply the registered R277 learning-margin gate."""
    integrity_guards = {
        "provenance_guard_pass": provenance_guard_pass,
        "completion_guard_pass": completion_guard_pass,
        "action_contract_guard_pass": action_contract_guard_pass,
        "storage_contract_guard_pass": storage_contract_guard_pass,
    }
    if contrast is None or not all(integrity_guards.values()):
        return {
            "classification": "INVALID",
            "reason": (
                "paired endpoint contrast unavailable"
                if contrast is None
                else "one or more provenance, completion, action, or storage contracts failed"
            ),
            "guards": integrity_guards,
            "endpoint_decisions": {},
        }

    endpoint_decisions: dict[str, Any] = {}
    for endpoint in ENDPOINTS:
        evidence = contrast["endpoints"][endpoint]["ratio_of_means_percent"]
        point = float(evidence["point"])
        lower, upper = (
            float(value) for value in evidence["percentile_95_interval"]
        )
        endpoint_decisions[endpoint] = {
            "point_percent": point,
            "percentile_95_interval": [lower, upper],
            "primary_clear": (
                endpoint in PRIMARY_ENDPOINTS
                and point <= -2.0
                and upper < 0.0
            ),
            "guard_clear": (
                endpoint in (*COMMON_GUARD_ENDPOINTS, *RESTORATION_GUARD_ENDPOINTS)
                and point <= 2.0
                and upper < 5.0
            ),
        }

    cleared_primary = [
        endpoint
        for endpoint in PRIMARY_ENDPOINTS
        if endpoint_decisions[endpoint]["primary_clear"]
    ]
    common_restoration_guard_pass = all(
        endpoint_decisions[endpoint]["guard_clear"]
        for endpoint in (*COMMON_GUARD_ENDPOINTS, *RESTORATION_GUARD_ENDPOINTS)
    )
    performance_guards = {
        "storage_relative_guard_pass": storage_relative_guard_pass,
        "tail_guard_pass": tail_guard_pass,
        "common_restoration_guard_pass": common_restoration_guard_pass,
        "nonbaseline_selected": nonbaseline_selection_count > 0,
    }
    guards = {**integrity_guards, **performance_guards}
    performance_pass = all(performance_guards.values())
    if len(cleared_primary) == len(PRIMARY_ENDPOINTS) and performance_pass:
        classification = "LEARNING-GAP-PRESENT"
        reason = "both differential endpoints clear with every guard"
    elif len(cleared_primary) == 1 and performance_pass:
        classification = "LEARNING-GAP-PARTIAL"
        reason = "exactly one differential endpoint clears without guarded harm"
    else:
        classification = "NO-RL-NEEDED"
        reason = "the optimistic oracle does not clear the guarded joint differential gate"
    return {
        "classification": classification,
        "reason": reason,
        "guards": guards,
        "cleared_primary_endpoints": cleared_primary,
        "endpoint_decisions": endpoint_decisions,
    }
