"""Deterministic state-aware fast/slow handoff for prospective R291.

The module contains no controller tuning and no ANDES setup.  It freezes the
R291 handoff contract, provides causal fast-action controllers, summarises one
retained trace, and applies the preregistered decision tree.  The execution
adapter lives in ``scripts/run_r291_state_aware_handoff.py``.

The stateful supervisors consume only measurements available after the
previous simulation step.  Their next action is therefore causal.  A hard
five-second envelope remains a safety budget; reaching it without the state
conditions is retained as ``forced_release`` rather than relabelled a
successful handoff.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from andes_rl_kundur.control.active_power import (
    DroopPIActivePowerController,
    r272_frozen_bess_contract,
)
from andes_rl_kundur.evaluation.active_power_authority import (
    R272_KI_SYSTEM_PU_PER_HZ_S_PER_DEVICE,
    R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE,
)
from andes_rl_kundur.evaluation.fast_md_authority import (
    summarise_fast_md_trace,
)

SLOW_ONLY = "slow_only"
FIXED_3S = "fixed_3s"
FIXED_5S = "fixed_5s"
COMMON_HANDOFF = "common_handoff"
FULL_HANDOFF = "full_handoff"
CONTROLLERS = (
    SLOW_ONLY,
    FIXED_3S,
    FIXED_5S,
    COMMON_HANDOFF,
    FULL_HANDOFF,
)

PRIMARY_ENDPOINTS = (
    "post_3_to_10s_worst_bus_iae_hz_s",
    "post_3_to_10s_common_secondary_peak_abs_hz",
)
_PRIMARY_ALIASES = {
    PRIMARY_ENDPOINTS[0]: "post_iae",
    PRIMARY_ENDPOINTS[1]: "secondary_peak",
}
GUARD_ENDPOINTS = (
    "vsg_mean_iae_hz_s",
    "final_window_common_abs_mean_hz",
    "max_abs_rocof_hz_s",
    "worst_bus_peak_abs_hz",
    "normalized_sync_loss_hz2",
    "fast_inter_area_iae_hz_s",
)


def frozen_handoff_contract() -> dict[str, Any]:
    """Return the exact JSON-serializable R291 controller contract."""
    dt = 0.2
    amplitude = 0.25
    minimum_on_steps = 5
    confirmation_steps = 3
    minimum_off_steps = 3
    taper_steps = 5
    hard_zero_step = 25
    frequency_resolution = 0.005
    rate_resolution = frequency_resolution / dt
    bess = r272_frozen_bess_contract()
    slow_gap = bess.device_ramp_limit_system_pu_per_s * dt
    return {
        "schema_version": 1,
        "round": "R291",
        "name": "deterministic_state_aware_smooth_handoff",
        "controllers": list(CONTROLLERS),
        "action": {
            "agent_pattern": [1.0, 1.0, 1.0, 1.0],
            "m_action_norm": amplitude,
            "d_action_norm": 0.0,
            "q_action_norm": 0.0,
        },
        "timing": {
            "control_dt_s": dt,
            "minimum_on_steps": minimum_on_steps,
            "minimum_on_s": minimum_on_steps * dt,
            "confirmation_steps": confirmation_steps,
            "confirmation_s": confirmation_steps * dt,
            "minimum_off_steps": minimum_off_steps,
            "minimum_off_s": minimum_off_steps * dt,
            "taper_steps": taper_steps,
            "taper_s": taper_steps * dt,
            "hard_taper_start_step": hard_zero_step - taper_steps,
            "hard_taper_start_s": (hard_zero_step - taper_steps) * dt,
            "hard_zero_step": hard_zero_step,
            "hard_zero_s": hard_zero_step * dt,
            "rate_filter_intervals": 3,
        },
        "thresholds": {
            "frequency_resolution_hz": frequency_resolution,
            "frequency_rate_resolution_hz_s": rate_resolution,
            "recovery_product_hz2_s": frequency_resolution * rate_resolution,
            "common_settling_band_hz": 0.05,
            "differential_band_hz": 0.05,
            "slow_gap_system_pu_per_device": slow_gap,
            "hysteresis_multiplier": 2.0,
        },
        "budgets": {
            "fixed_3s_action_l1_agent_s": amplitude * 15 * dt,
            "max_action_l1_agent_s": amplitude * hard_zero_step * dt,
            "max_abs_m_action_norm": amplitude,
            "max_abs_d_action_norm": 0.0,
            "adaptive_internal_slew_per_step": amplitude / taper_steps,
            "initial_boundary_slew": amplitude,
        },
        "causality": (
            "measurement after step k updates gate used by step k+1; "
            "initial gate is fixed before the first trajectory sample"
        ),
        "forced_release_semantics": (
            "hard budget withdrawal without ready state is retained failure evidence"
        ),
    }


@dataclass
class FixedFastController:
    """Frozen slow-only or rectangular common-inertia schedule."""

    active_steps: int
    amplitude: float = 0.25

    @property
    def gate(self) -> float:
        return 0.0

    def reset(self) -> None:
        """Stateless compatibility hook."""

    def actions(self, *, step: int, n_agents: int) -> dict[int, np.ndarray]:
        if step < 0:
            raise ValueError("step must be non-negative")
        if n_agents != 4:
            raise ValueError(f"R291 requires four agents, got {n_agents}")
        value = self.amplitude if step < self.active_steps else 0.0
        return {
            index: np.asarray([value, 0.0], dtype=np.float32)
            for index in range(n_agents)
        }

    def observe(self, **_: Any) -> None:
        """A fixed schedule ignores measurements."""

    def telemetry(self) -> dict[str, Any]:
        return {
            "gate": 0.0,
            "target_gate": 0.0,
            "ready": False,
            "forced_release": False,
            "switch_count": 0,
            "release_time_s": None,
            "minimum_inter_switch_time_s": None,
        }


class HandoffSupervisor:
    """Causal hysteretic state machine with bumpless fast-action taper."""

    def __init__(self, *, mode: Literal["common", "full"]) -> None:
        if mode not in {"common", "full"}:
            raise ValueError("mode must be 'common' or 'full'")
        self.mode = mode
        self.contract = frozen_handoff_contract()
        self.reset()

    def reset(self) -> None:
        timing = self.contract["timing"]
        self._error_history: deque[float] = deque(
            maxlen=int(timing["rate_filter_intervals"]) + 1
        )
        self._gate = 1.0
        self._target_gate = 1.0
        self._ready_count = 0
        self._reentry_count = 0
        self._last_switch_step: int | None = None
        self._switch_steps: list[int] = []
        self._forced_release = False
        self._release_time_s: float | None = None
        self._ready = False
        self._common_error_hz: float | None = None
        self._common_error_rate_hz_s: float | None = None
        self._differential_hz: float | None = None
        self._slow_gap_pu: float | None = None

    @property
    def gate(self) -> float:
        return float(self._gate)

    def actions(self, *, step: int, n_agents: int) -> dict[int, np.ndarray]:
        if step < 0:
            raise ValueError("step must be non-negative")
        if n_agents != 4:
            raise ValueError(f"R291 requires four agents, got {n_agents}")
        if step >= int(self.contract["timing"]["hard_zero_step"]):
            value = 0.0
        else:
            value = float(self.contract["action"]["m_action_norm"]) * self._gate
        return {
            index: np.asarray([value, 0.0], dtype=np.float32)
            for index in range(n_agents)
        }

    def _filtered_error_rate(self, error_hz: float) -> float | None:
        self._error_history.append(error_hz)
        intervals = int(self.contract["timing"]["rate_filter_intervals"])
        if len(self._error_history) < intervals + 1:
            return None
        return float(
            (self._error_history[-1] - self._error_history[0])
            / (intervals * float(self.contract["timing"]["control_dt_s"]))
        )

    def _set_target(self, target: float, step: int) -> None:
        if np.isclose(target, self._target_gate, rtol=0.0, atol=1e-15):
            return
        self._target_gate = float(target)
        self._last_switch_step = step
        self._switch_steps.append(step)

    def observe(
        self,
        *,
        step: int,
        frequencies_hz: np.ndarray | list[float],
        slow_requested_power_system_pu: np.ndarray | list[float],
        slow_actual_power_system_pu: np.ndarray | list[float],
    ) -> None:
        """Update the gate after step ``step`` for use at ``step + 1``."""
        if step < 0:
            raise ValueError("step must be non-negative")
        frequencies = np.asarray(frequencies_hz, dtype=float)
        requested = np.asarray(slow_requested_power_system_pu, dtype=float)
        actual = np.asarray(slow_actual_power_system_pu, dtype=float)
        if frequencies.shape != (4,) or requested.shape != (4,) or actual.shape != (4,):
            raise ValueError("R291 handoff measurements must all have shape (4,)")
        if not (
            np.all(np.isfinite(frequencies))
            and np.all(np.isfinite(requested))
            and np.all(np.isfinite(actual))
        ):
            raise ValueError("R291 handoff measurements must be finite")

        thresholds = self.contract["thresholds"]
        timing = self.contract["timing"]
        error = 60.0 - float(np.mean(frequencies))
        error_rate = self._filtered_error_rate(error)
        differential = float(
            np.mean(frequencies[:2]) - np.mean(frequencies[2:])
        )
        slow_gap = float(np.max(np.abs(requested - actual)))
        self._common_error_hz = error
        self._common_error_rate_hz_s = error_rate
        self._differential_hz = differential
        self._slow_gap_pu = slow_gap

        recovery = False
        settled = False
        destabilizing = False
        if error_rate is not None:
            product = error * error_rate
            recovery = (
                abs(error) >= float(thresholds["frequency_resolution_hz"])
                and product <= -float(thresholds["recovery_product_hz2_s"])
            )
            settled = (
                abs(error) <= float(thresholds["common_settling_band_hz"])
                and abs(error_rate)
                <= float(thresholds["frequency_rate_resolution_hz_s"])
            )
            hysteresis = float(thresholds["hysteresis_multiplier"])
            destabilizing = (
                abs(error)
                > hysteresis * float(thresholds["common_settling_band_hz"])
                or product
                >= hysteresis * float(thresholds["recovery_product_hz2_s"])
            )
        common_ready = recovery or settled
        full_ready = (
            common_ready
            and abs(differential) <= float(thresholds["differential_band_hz"])
            and slow_gap
            <= float(thresholds["slow_gap_system_pu_per_device"])
        )
        ready = common_ready if self.mode == "common" else full_ready
        self._ready = bool(ready)

        elapsed_steps = step + 1
        if elapsed_steps >= int(timing["minimum_on_steps"]) and ready:
            self._ready_count += 1
        else:
            self._ready_count = 0

        hysteresis = float(thresholds["hysteresis_multiplier"])
        full_destabilizing = destabilizing or (
            self.mode == "full"
            and (
                abs(differential)
                > hysteresis * float(thresholds["differential_band_hz"])
                or slow_gap
                > hysteresis
                * float(thresholds["slow_gap_system_pu_per_device"])
            )
        )
        if full_destabilizing:
            self._reentry_count += 1
        else:
            self._reentry_count = 0

        hard_taper = elapsed_steps >= int(timing["hard_taper_start_step"])
        if hard_taper:
            if self._target_gate > 0.0 and not ready:
                self._forced_release = True
            self._set_target(0.0, step)
        elif (
            self._target_gate > 0.0
            and self._ready_count >= int(timing["confirmation_steps"])
        ):
            self._set_target(0.0, step)
        elif self._target_gate <= 0.0 and (
            self._reentry_count >= int(timing["confirmation_steps"])
        ):
            off_steps = (
                elapsed_steps
                if self._last_switch_step is None
                else step - self._last_switch_step
            )
            if off_steps >= int(timing["minimum_off_steps"]):
                self._set_target(1.0, step)

        gate_step = 1.0 / int(timing["taper_steps"])
        if self._gate < self._target_gate:
            self._gate = min(self._target_gate, self._gate + gate_step)
        elif self._gate > self._target_gate:
            self._gate = max(self._target_gate, self._gate - gate_step)
        if self._gate <= 1e-15:
            self._gate = 0.0
            if self._release_time_s is None:
                self._release_time_s = elapsed_steps * float(
                    timing["control_dt_s"]
                )
        if elapsed_steps >= int(timing["hard_zero_step"]):
            self._gate = 0.0
            self._target_gate = 0.0

    def telemetry(self) -> dict[str, Any]:
        dt = float(self.contract["timing"]["control_dt_s"])
        inter_switch = np.diff(np.asarray(self._switch_steps, dtype=float))
        return {
            "mode": self.mode,
            "gate": float(self._gate),
            "target_gate": float(self._target_gate),
            "ready": bool(self._ready),
            "forced_release": bool(self._forced_release),
            "switch_count": len(self._switch_steps),
            "release_time_s": self._release_time_s,
            "minimum_inter_switch_time_s": (
                float(np.min(inter_switch) * dt) if inter_switch.size else None
            ),
            "common_error_hz": self._common_error_hz,
            "common_error_rate_hz_s": self._common_error_rate_hz_s,
            "differential_hz": self._differential_hz,
            "slow_gap_system_pu_per_device": self._slow_gap_pu,
        }


def make_fast_controller(
    controller: str,
) -> FixedFastController | HandoffSupervisor:
    """Create one of the five frozen R291 fast-action controllers."""
    if controller == SLOW_ONLY:
        return FixedFastController(active_steps=0)
    if controller == FIXED_3S:
        return FixedFastController(active_steps=15)
    if controller == FIXED_5S:
        return FixedFastController(active_steps=25)
    if controller == COMMON_HANDOFF:
        return HandoffSupervisor(mode="common")
    if controller == FULL_HANDOFF:
        return HandoffSupervisor(mode="full")
    raise ValueError(f"unknown R291 controller: {controller}")


def run_handoff_scenario(
    scenario_name: str,
    delta_u: dict[str, float],
    *,
    controller_name: str,
    seed: int = 42,
    steps: int = 300,
) -> dict[str, Any]:
    """Run one matched R291 arm through the public storage environment seam."""
    from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
        AndesMultiVSGEnvV4Storage,
    )

    if controller_name not in CONTROLLERS:
        raise ValueError(f"unknown R291 controller: {controller_name}")
    env = AndesMultiVSGEnvV4Storage(
        random_disturbance=False,
        comm_fail_prob=0.0,
    )
    fast_controller = make_fast_controller(controller_name)
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
            md_actions = fast_controller.actions(
                step=step,
                n_agents=env.N_AGENTS,
            )
            executed_gate = float(
                np.mean(
                    [
                        float(np.asarray(md_actions[index], dtype=float)[0])
                        for index in range(env.N_AGENTS)
                    ]
                )
                / float(frozen_handoff_contract()["action"]["m_action_norm"])
            )
            obs, _, done, info = env.step(
                md_actions,
                bess_power_request_pu=requested_power,
            )
            del obs
            if info.get("tds_failed"):
                tds_failed = True
                break
            fast_controller.observe(
                step=step,
                frequencies_hz=np.asarray(
                    info["freq_hz_physical"],
                    dtype=float,
                ),
                slow_requested_power_system_pu=np.asarray(
                    info["bess_requested_power_system_pu"],
                    dtype=float,
                ),
                slow_actual_power_system_pu=np.asarray(
                    info["bess_actual_power_system_pu"],
                    dtype=float,
                ),
            )
            handoff = dict(fast_controller.telemetry())
            handoff["gate"] = executed_gate
            handoff["next_gate"] = float(
                getattr(fast_controller, "gate", executed_gate)
            )
            if isinstance(fast_controller, FixedFastController):
                handoff["target_gate"] = executed_gate

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
                    "handoff": handoff,
                }
            )
            if done:
                break
    finally:
        env.close()

    return {
        "experiment": "r291_state_aware_handoff",
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
                R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE
            ),
            "ki_system_pu_per_hz_s_per_device": (
                R272_KI_SYSTEM_PU_PER_HZ_S_PER_DEVICE
            ),
            "fast_handoff": frozen_handoff_contract(),
        },
        "seed": seed,
    }


def summarise_handoff_trace(
    record: dict[str, Any],
    *,
    final_window_steps: int = 50,
    fast_window_steps: int = 15,
    post_window_start_step: int = 15,
    post_window_stop_step: int = 50,
) -> dict[str, Any]:
    """Add R291 post-handoff and state-machine endpoints to one trace."""
    result = dict(
        summarise_fast_md_trace(
            record,
            final_window_steps=final_window_steps,
            fast_window_steps=fast_window_steps,
        )
    )
    traces = record["traces"]
    if not 0 <= post_window_start_step < post_window_stop_step <= len(traces):
        raise ValueError("R291 post window must fit inside the completed trace")
    delta_f = np.asarray(
        [step["delta_f_physical_hz"] for step in traces],
        dtype=float,
    )
    window = delta_f[post_window_start_step:post_window_stop_step]
    dt = float(result["sample_interval_s"])
    worst_bus = np.max(np.abs(window), axis=1)
    common = np.mean(window, axis=1)
    actions = np.asarray(
        [step["action_norm"] for step in traces],
        dtype=float,
    )
    m_action = actions[:, :, 0]
    internal_slew = np.diff(m_action, axis=0)
    handoff_rows = [step.get("handoff", {}) for step in traces]
    gates = np.asarray(
        [
            row.get(
                "gate",
                float(np.mean(np.abs(m_action[index]))) / 0.25
                if np.any(m_action[index])
                else 0.0,
            )
            for index, row in enumerate(handoff_rows)
        ],
        dtype=float,
    )
    target = np.asarray(
        [row.get("target_gate", gates[index]) for index, row in enumerate(handoff_rows)],
        dtype=float,
    )
    switches = np.flatnonzero(
        ~np.isclose(np.diff(target), 0.0, rtol=0.0, atol=1e-15)
    )
    positive_seen = np.maximum.accumulate(gates > 1e-12)
    zero_after_positive = np.flatnonzero(positive_seen & (gates <= 1e-12))
    result.update(
        {
            "post_window_start_step": post_window_start_step,
            "post_window_stop_step": post_window_stop_step,
            "post_window_start_s": post_window_start_step * dt,
            "post_window_stop_s": post_window_stop_step * dt,
            "post_3_to_10s_worst_bus_iae_hz_s": float(
                np.sum(worst_bus) * dt
            ),
            "post_3_to_10s_common_secondary_peak_abs_hz": float(
                np.max(np.abs(common))
            ),
            "adaptive_internal_max_slew_per_step": float(
                np.max(np.abs(internal_slew)) if internal_slew.size else 0.0
            ),
            "handoff_switch_count": int(switches.size),
            "handoff_minimum_inter_switch_time_s": (
                float(np.min(np.diff(switches)) * dt)
                if switches.size >= 2
                else None
            ),
            "handoff_release_time_s": (
                float((zero_after_positive[0] + 1) * dt)
                if zero_after_positive.size
                else None
            ),
            "forced_release": any(
                bool(row.get("forced_release", False)) for row in handoff_rows
            ),
        }
    )
    return result


def _endpoint_entry(
    contrast: dict[str, Any],
    endpoint: str,
) -> dict[str, Any]:
    endpoints = contrast["endpoints"]
    if endpoint in endpoints:
        return endpoints[endpoint]
    alias = _PRIMARY_ALIASES.get(endpoint)
    if alias is not None and alias in endpoints:
        return endpoints[alias]
    if endpoint == "action_l1_agent_s" and "action_l1" in endpoints:
        return endpoints["action_l1"]
    raise KeyError(f"contrast is missing endpoint {endpoint}")


def _relative_bounds(entry: dict[str, Any]) -> tuple[float, float]:
    relative = entry["ratio_of_means_percent"]
    point = relative["point"]
    interval = relative["percentile_95_interval"]
    if point is None or interval is None:
        return float("inf"), float("inf")
    return float(point), float(interval[1])


def _material(contrast: dict[str, Any], endpoint: str) -> bool:
    point, upper = _relative_bounds(_endpoint_entry(contrast, endpoint))
    return point <= -2.0 and upper < 0.0


def _noninferior(contrast: dict[str, Any], endpoint: str) -> bool:
    _, upper = _relative_bounds(_endpoint_entry(contrast, endpoint))
    return upper <= 2.0


def _effort_benefit(contrast: dict[str, Any]) -> bool:
    point, upper = _relative_bounds(
        _endpoint_entry(contrast, "action_l1_agent_s")
    )
    return point <= -10.0 and upper < 0.0


def classify_state_aware_handoff(
    *,
    controller_summaries: dict[str, dict[str, Any]],
    contrasts: dict[str, dict[str, Any]],
    provenance_hashes_match: bool,
    guard_no_harm: dict[str, bool],
) -> dict[str, Any]:
    """Apply the prospectively registered R291 decision tree."""
    required_contrasts = {
        "common_vs_fixed3",
        "common_vs_fixed5",
        "full_vs_fixed3",
        "full_vs_fixed5",
        "full_vs_common",
        "fixed5_vs_fixed3",
    }
    required_guards = required_contrasts - {"fixed5_vs_fixed3"}
    structural = {
        "provenance_hashes_match": bool(provenance_hashes_match),
        "all_controller_summaries_present": set(CONTROLLERS).issubset(
            controller_summaries
        ),
        "all_contrasts_present": required_contrasts.issubset(contrasts),
        "all_no_harm_guards_present": required_guards.issubset(guard_no_harm),
    }
    if not all(structural.values()):
        return {
            "classification": "INVALID",
            "reason": "missing provenance, controller, contrast, or guard evidence",
            "guards": structural,
            "common_timing_gate": False,
            "full_incremental_gate": False,
            "recommended_state_set": "none",
        }

    controller_validity = {
        name: (
            int(summary.get("complete_count", -1)) == 24
            and int(summary.get("failure_count", -1)) == 0
            and int(summary.get("constraint_violation_count", -1)) == 0
            and bool(summary.get("action_budget_pass", False))
            and bool(summary.get("storage_guard_pass", False))
            and bool(summary.get("tail_guard_pass", False))
        )
        for name, summary in controller_summaries.items()
        if name in CONTROLLERS
    }
    structural["all_controllers_valid"] = (
        len(controller_validity) == len(CONTROLLERS)
        and all(controller_validity.values())
    )
    if not all(structural.values()):
        return {
            "classification": "INVALID",
            "reason": "one or more completion, physical, action, or tail guards failed",
            "guards": structural | {"controller_validity": controller_validity},
            "common_timing_gate": False,
            "full_incremental_gate": False,
            "recommended_state_set": "none",
        }

    common_fixed3 = contrasts["common_vs_fixed3"]
    common_fixed5 = contrasts["common_vs_fixed5"]
    full_fixed3 = contrasts["full_vs_fixed3"]
    full_fixed5 = contrasts["full_vs_fixed5"]
    full_common = contrasts["full_vs_common"]
    fixed5_fixed3 = contrasts["fixed5_vs_fixed3"]

    def both_material(contrast: dict[str, Any]) -> bool:
        return all(_material(contrast, endpoint) for endpoint in PRIMARY_ENDPOINTS)

    def timing_value(
        *,
        fixed3: dict[str, Any],
        fixed5: dict[str, Any],
        fixed3_guard: str,
        fixed5_guard: str,
    ) -> bool:
        practical = both_material(fixed3) and guard_no_harm[fixed3_guard]
        superiority = (
            any(_material(fixed5, endpoint) for endpoint in PRIMARY_ENDPOINTS)
            and guard_no_harm[fixed5_guard]
        )
        efficiency = (
            all(_noninferior(fixed5, endpoint) for endpoint in PRIMARY_ENDPOINTS)
            and _effort_benefit(fixed5)
            and guard_no_harm[fixed5_guard]
        )
        return practical and (superiority or efficiency)

    common_zero_forced = (
        int(controller_summaries[COMMON_HANDOFF]["forced_release_count"]) == 0
    )
    full_zero_forced = (
        int(controller_summaries[FULL_HANDOFF]["forced_release_count"]) == 0
    )
    common_timing = timing_value(
        fixed3=common_fixed3,
        fixed5=common_fixed5,
        fixed3_guard="common_vs_fixed3",
        fixed5_guard="common_vs_fixed5",
    ) and common_zero_forced
    full_timing = timing_value(
        fixed3=full_fixed3,
        fixed5=full_fixed5,
        fixed3_guard="full_vs_fixed3",
        fixed5_guard="full_vs_fixed5",
    ) and full_zero_forced
    full_incremental = (
        common_timing
        and full_timing
        and any(_material(full_common, endpoint) for endpoint in PRIMARY_ENDPOINTS)
        and guard_no_harm["full_vs_common"]
    )
    duration_value = both_material(fixed5_fixed3)

    guards: dict[str, Any] = structural | {
        "controller_validity": controller_validity,
        "common_zero_forced_release": common_zero_forced,
        "full_zero_forced_release": full_zero_forced,
        "registered_no_harm": dict(guard_no_harm),
    }
    any_state_signal = any(
        _material(contrast, endpoint)
        for contrast in (common_fixed3, full_fixed3)
        for endpoint in PRIMARY_ENDPOINTS
    )
    forced_state_handoff = not common_zero_forced or not full_zero_forced
    if full_incremental:
        classification = "HANDOFF-POSITIVE-FULL"
        reason = "full handoff clears timing value and adds value beyond common state"
        recommended = "common_differential_slow_gap"
    elif common_timing:
        classification = "HANDOFF-POSITIVE-COMMON"
        reason = "common-state handoff clears timing value; added state does not"
        recommended = "common_only"
    elif forced_state_handoff and any_state_signal:
        classification = "HANDOFF-PARTIAL"
        reason = "state-aware means signal benefit but at least one handoff was forced"
        recommended = "none"
    elif duration_value:
        classification = "FIXED-DURATION-ONLY"
        reason = "longer fixed support helps but state timing adds no identified value"
        recommended = "fixed_duration"
    elif any_state_signal:
        classification = "HANDOFF-PARTIAL"
        reason = "some state-aware signal exists but the joint timing gate does not clear"
        recommended = "none"
    else:
        classification = "NO-HANDOFF-VALUE"
        reason = "neither state timing nor fixed duration clears the registered gate"
        recommended = "fixed_3s_benchmark"

    return {
        "classification": classification,
        "reason": reason,
        "guards": guards,
        "common_timing_gate": bool(common_timing),
        "full_timing_gate": bool(full_timing),
        "full_incremental_gate": bool(full_incremental),
        "fixed_duration_gate": bool(duration_value),
        "recommended_state_set": recommended,
    }
