"""Physical-60-Hz model-first ANDES environment.

The class is additive: legacy V4 and ``AndesBaseEnv`` remain untouched.  The
model-first path advances TDS without writing GENCLS coefficients during
active-power probes and exposes independent live-array readbacks.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
    AndesMultiVSGEnvV4Storage,
)
from andes_rl_kundur.env.andes.model_first_contract import (
    ACTION_EDGES,
    ModelFirstConfig,
    active_power_incidence,
    device_to_system_base,
)
from andes_rl_kundur.env.andes.v4_config import V4Config

REQUIRED_ESD1_INTERNAL_FIELDS = (
    "Pext0",
    "Pext",
    "Pref",
    "Psum",
    "Ipul",
    "Ipcmd_y",
    "Ipout_y",
    "Ipmin",
    "Ipmax",
    "Fvl",
    "Fvh",
    "Ffl",
    "Ffh",
    "v",
    "SOC",
)
TIE_LINE_INDICES = ("Line_4", "Line_5", "Line_6")


class AndesModelFirstEnv(AndesMultiVSGEnvV4Storage):
    """Separate implementation-validity path for the model-first plant."""

    FN = 60.0

    def __init__(
        self,
        *,
        model_first_config: ModelFirstConfig | None = None,
        **kwargs: Any,
    ) -> None:
        config = model_first_config or ModelFirstConfig()
        if kwargs.get("random_disturbance", False) is not False:
            raise ValueError("model-first Stage-0 forbids random disturbance")
        if kwargs.get("comm_fail_prob", 0.0) != 0.0:
            raise ValueError("model-first Stage-0 forbids communication failures")
        kwargs["random_disturbance"] = False
        kwargs["comm_fail_prob"] = 0.0
        v4_config = V4Config(
            vsg_m0=float(config.vsg_m_device[0]),
            vsg_d0=float(config.vsg_d_device[0]),
            d0_per_agent=tuple(float(value) for value in config.vsg_d_device),
            zero_g4_inertia=False,
            lambda_smooth=0.0,
        )
        self.model_first_config = config
        self._model_first_md_write_count = 0
        self._model_first_solver_transition_count = 0
        self._model_first_initialization_solver_contract: dict[str, object] = {}
        super().__init__(config=v4_config, **kwargs)

        scale = config.vsg_device_mva / config.system_mva
        self.DM_MIN *= scale
        self.DM_MAX *= scale
        self.DD_MIN *= scale
        self.DD_MAX *= scale

    def _build_system(self):
        config = self.model_first_config
        self.M0 = np.asarray(config.vsg_m_device, dtype=float)
        self.D0 = np.asarray(config.vsg_d_device, dtype=float)
        self.D0_HETEROGENEOUS = self.D0.copy()
        system = super()._build_system()

        if config.tds_convergence_tolerance is not None:
            system.TDS.config.tol = config.tds_convergence_tolerance
            system.TDS.tol_zero = config.tds_tiny_correction_threshold

        expected_m = config.vsg_m_system
        expected_d = config.vsg_d_system
        for index, vsg_idx in enumerate(self.vsg_idx):
            system.GENCLS.set("M", vsg_idx, float(expected_m[index]), attr="v")
            system.GENCLS.set("D", vsg_idx, float(expected_d[index]), attr="v")

        self._model_first_tie_lines: dict[str, dict[str, float]] = {}
        for line_idx in TIE_LINE_INDICES:
            line_position = list(system.Line.idx.v).index(line_idx)
            scaled_r = float(
                system.Line.r.v[line_position] * config.tie_rx_scale
            )
            scaled_x = float(
                system.Line.x.v[line_position] * config.tie_rx_scale
            )
            system.Line.set("r", line_idx, scaled_r, attr="v")
            system.Line.set("x", line_idx, scaled_x, attr="v")
            self._model_first_tie_lines[line_idx] = {"r": scaled_r, "x": scaled_x}

        for bess_idx in self.bess_idx:
            system.ESD1.set("SOCinit", bess_idx, config.initial_soc, attr="v")

        if config.disable_default_toggler and hasattr(system, "Toggler"):
            for toggler_idx in list(system.Toggler.idx.v):
                system.Toggler.set("u", toggler_idx, 0.0, attr="v")

        self.M0 = expected_m.copy()
        self.D0 = expected_d.copy()
        return system

    def _apply_disturbance(self, delta_u=None, **kwargs: Any) -> None:
        if delta_u not in (None, {}):
            raise ValueError("R306 Stage-0 forbids every PQ edit")

    def reset(self, *args: Any, **kwargs: Any):
        delta_u = kwargs.pop("delta_u", None)
        if delta_u not in (None, {}):
            raise ValueError("R306 Stage-0 forbids every PQ edit")
        observation = super().reset(*args, delta_u=None, **kwargs)
        self._model_first_solver_transition_count = 0
        self._model_first_initialization_solver_contract = {
            "method": str(self.ss.TDS.config.method),
            "convergence_tolerance": float(self.ss.TDS.config.tol),
            "tiny_correction_threshold": float(self.ss.TDS.tol_zero),
            "tds_test_ok": self.ss.TDS.test_ok is True,
            "system_exit_code": self._system_exit_code(self.ss),
            "endpoint_seconds": float(self.ss.dae.t),
        }
        post_tolerance = (
            self.model_first_config.tds_post_initialization_convergence_tolerance
        )
        if post_tolerance is not None:
            self.ss.TDS.config.tol = post_tolerance
            self.ss.TDS.tol_zero = (
                self.model_first_config.tds_post_initialization_tiny_correction_threshold
            )
            self._model_first_solver_transition_count = 1
        self.M0 = self.model_first_config.vsg_m_system.copy()
        self.D0 = self.model_first_config.vsg_d_system.copy()
        self._prev_M = self._get_vsg_parameter("M")
        self._prev_D = self._get_vsg_parameter("D")
        self._model_first_md_write_count = 0
        return observation

    def _get_vsg_parameter(self, name: str) -> np.ndarray:
        parameter = getattr(self.ss.GENCLS, name)
        return np.asarray([parameter.v[pos] for pos in self._vsg_pos], dtype=float)

    def _get_esd1_vector(self, name: str) -> np.ndarray:
        owner = getattr(self.ss.ESD1, name, None)
        values = getattr(owner, "v", None)
        if values is None:
            raise RuntimeError(f"required ESD1 telemetry is unavailable: {name}")
        return np.asarray([values[pos] for pos in self._bess_pos], dtype=float)

    def _esd1_internal_snapshot(self) -> dict[str, np.ndarray]:
        return {
            name: self._get_esd1_vector(name)
            for name in REQUIRED_ESD1_INTERNAL_FIELDS
        }

    def _line_8_in_service(self) -> bool:
        indices = [str(value) for value in self.ss.Line.idx.v]
        if "Line_8" not in indices:
            raise RuntimeError("the frozen Line_8 index is missing")
        return bool(float(self.ss.Line.u.v[indices.index("Line_8")]) == 1.0)

    def _g4_snapshot(self) -> tuple[bool, float, float]:
        indices = list(self.ss.GENROU.idx.v)
        if 4 not in indices:
            raise RuntimeError("the original Kundur G4 index is missing")
        position = indices.index(4)
        status = float(self.ss.GENROU.u.v[position])
        m_value = float(self.ss.GENROU.M.v[position])
        d_value = float(self.ss.GENROU.D.v[position])
        return bool(status == 1.0 and m_value > 0.1), m_value, d_value

    def structural_contract(self) -> dict[str, object]:
        communication_edges = sorted(
            {
                tuple(sorted((int(node), int(neighbor))))
                for node, neighbors in self.COMM_ADJ.items()
                for neighbor in neighbors
            }
        )
        incidence = active_power_incidence()
        return {
            "node_device_rows": [
                [0, "VSG_1", "R272_BESS_1", 12, 7, 1],
                [1, "VSG_2", "R272_BESS_2", 16, 8, 1],
                [2, "VSG_3", "R272_BESS_3", 14, 10, 2],
                [3, "VSG_4", "R272_BESS_4", 15, 9, 2],
            ],
            "communication_edges": [list(edge) for edge in communication_edges],
            "action_edges": [list(edge) for edge in ACTION_EDGES],
            "action_incidence": incidence.tolist(),
            "action_rank": int(np.linalg.matrix_rank(incidence)),
            "disturbance_graph": {"kind": "none", "edited_devices": []},
            "operating_point": {
                "vsg_m_device": list(self.model_first_config.vsg_m_device),
                "vsg_d_device": list(self.model_first_config.vsg_d_device),
                "vsg_m_system": self.model_first_config.vsg_m_system.tolist(),
                "vsg_d_system": self.model_first_config.vsg_d_system.tolist(),
                "tie_rx_scale": self.model_first_config.tie_rx_scale,
                "initial_soc": self.model_first_config.initial_soc,
                "tie_lines": self._model_first_tie_lines,
            },
            "solver": {
                "method": str(self.ss.TDS.config.method),
                "convergence_tolerance": float(self.ss.TDS.config.tol),
                "tiny_correction_threshold": float(self.ss.TDS.tol_zero),
                "transition_count": self._model_first_solver_transition_count,
                "stopping_semantics": "max_abs_newton_correction",
                "readback_semantics": "post_control_step_recomputed_dae_g",
            },
            "initialization_solver": self._model_first_initialization_solver_contract,
        }

    @staticmethod
    def _system_exit_code(system: Any) -> int:
        raw = np.asarray(system.exit_code)
        if raw.shape != ():
            raise RuntimeError("ANDES system.exit_code must be scalar")
        return int(raw.item())

    def step(self, actions, *, bess_power_request_pu):
        action_matrix = np.asarray(
            [actions[index] for index in range(self.N_AGENTS)],
            dtype=float,
        )
        if action_matrix.shape != (self.N_AGENTS, 2):
            raise ValueError("M/D actions must have shape (4, 2)")
        if not np.all(np.isfinite(action_matrix)) or np.any(action_matrix != 0.0):
            raise ValueError("model-first active-power probes require exact zero M/D increments")

        requested = np.asarray(bess_power_request_pu, dtype=float)
        if requested.shape != (self.N_AGENTS,) or not np.all(np.isfinite(requested)):
            raise ValueError("bess_power_request_pu must be a finite four-vector")
        soc_before = self._get_bess_soc()
        projection = self.bess_contract.project_power(
            requested_power_system_pu=requested,
            previous_power_system_pu=self._previous_bess_command_system_pu,
            soc=soc_before,
            voltage_pu=self._get_bess_voltage(),
            dt_seconds=self.DT,
        )
        for bess_idx, command in zip(
            self.bess_idx,
            projection.commanded_power_system_pu,
            strict=True,
        ):
            self.ss.DG.set_paux(self.ss, bess_idx, float(command))

        current_time = float(self.ss.dae.t)
        dt_sub = self.DT / self.N_SUBSTEPS
        tds_failed = False
        for substep in range(self.N_SUBSTEPS):
            target = current_time + (substep + 1) * dt_sub
            self.ss.TDS.config.tf = target
            self.ss.TDS.busted = False
            self.ss.TDS.run()
            if float(self.ss.dae.t) < target - 1e-6:
                tds_failed = True
                break

        self.step_count += 1
        omega = self._get_vsg_omega()
        power = self._get_vsg_power()
        omega_dot = self._compute_omega_dot(omega, power)
        observation = self._build_obs(omega, omega_dot, power)
        zero = np.zeros(self.N_AGENTS, dtype=float)
        rewards, r_f, r_h, r_d = self._compute_rewards(
            omega,
            omega_dot,
            zero,
            zero,
        )
        done = self.step_count >= self.STEPS_PER_EPISODE or tds_failed
        if tds_failed:
            rewards = {index: -50.0 for index in range(self.N_AGENTS)}

        soc_after = self._get_bess_soc()
        actual_power = self._get_bess_actual_power()
        stored_delta_mwh = (
            (soc_after - soc_before) * self.bess_contract.device_energy_mwh
        )
        charge_energy_mwh = np.maximum(stored_delta_mwh, 0.0)
        discharge_energy_mwh = np.maximum(-stored_delta_mwh, 0.0)
        self._cumulative_charge_energy_mwh += charge_energy_mwh
        self._cumulative_discharge_energy_mwh += discharge_energy_mwh
        internal = self._esd1_internal_snapshot()

        dae_f = np.asarray(self.ss.dae.f, dtype=float)
        dae_g = np.asarray(self.ss.dae.g, dtype=float)
        dae_x = np.asarray(self.ss.dae.x, dtype=float)
        dae_y = np.asarray(self.ss.dae.y, dtype=float)
        residual_max = max(
            float(np.max(np.abs(dae_f))) if dae_f.size else 0.0,
            float(np.max(np.abs(dae_g))) if dae_g.size else 0.0,
        )
        differential_residual_max = (
            float(np.max(np.abs(dae_f))) if dae_f.size else 0.0
        )
        algebraic_residual_max = (
            float(np.max(np.abs(dae_g))) if dae_g.size else 0.0
        )
        g4_in_service, g4_m, g4_d = self._g4_snapshot()
        vsg_m_actual = self._get_vsg_parameter("M")
        vsg_d_actual = self._get_vsg_parameter("D")

        violations: list[str] = []
        if np.any(soc_after < self.bess_contract.soc_min - 1e-9):
            violations.append("soc_below_min")
        if np.any(soc_after > self.bess_contract.soc_max + 1e-9):
            violations.append("soc_above_max")

        info = {
            "time": float(self.ss.dae.t),
            "freq_hz": omega * self.FN,
            "freq_hz_physical": omega * self.andes_nominal_frequency_hz,
            "control_nominal_frequency_hz": float(self.FN),
            "andes_nominal_frequency_hz": float(self.andes_nominal_frequency_hz),
            "frequency_calibration_mismatch": not np.isclose(
                self.FN,
                self.andes_nominal_frequency_hz,
            ),
            "omega": omega.copy(),
            "omega_dot": omega_dot.copy(),
            "P_es": power.copy(),
            "M_es": vsg_m_actual.copy(),
            "D_es": vsg_d_actual.copy(),
            "vsg_m_actual_system": vsg_m_actual.copy(),
            "vsg_d_actual_system": vsg_d_actual.copy(),
            "vsg_m_nominal_device": np.asarray(
                self.model_first_config.vsg_m_device,
                dtype=float,
            ),
            "vsg_d_nominal_device": np.asarray(
                self.model_first_config.vsg_d_device,
                dtype=float,
            ),
            "md_write_count": self._model_first_md_write_count,
            "delta_M": zero.copy(),
            "delta_D": zero.copy(),
            "r_f": r_f,
            "r_h": r_h,
            "r_d": r_d,
            "r_smooth": 0.0,
            "pflow_converged": bool(self.ss.PFlow.converged),
            "tds_failed": tds_failed,
            "system_exit_code": self._system_exit_code(self.ss),
            "finite_state_algebraic": bool(
                np.all(np.isfinite(dae_x)) and np.all(np.isfinite(dae_y))
            ),
            "dae_residual_max": residual_max,
            "dae_f_residual_max": differential_residual_max,
            "dae_g_residual_max": algebraic_residual_max,
            "tds_convergence_tolerance": float(self.ss.TDS.config.tol),
            "tds_tiny_correction_threshold": float(self.ss.TDS.tol_zero),
            "tds_solver_transition_count": self._model_first_solver_transition_count,
            "bess_requested_power_system_pu": requested.copy(),
            "bess_commanded_power_system_pu": (
                projection.commanded_power_system_pu.copy()
            ),
            "bess_external_command_readback_system_pu": internal["Pext0"].copy(),
            "bess_internal_power_reference_system_pu": internal["Psum"].copy(),
            "bess_actual_power_system_pu": actual_power.copy(),
            "bess_soc": soc_after.copy(),
            "bess_bus_voltage_pu": self._get_bess_voltage(),
            "bess_internal": {name: value.copy() for name, value in internal.items()},
            "bess_saturation_reasons": [
                list(reasons) for reasons in projection.saturation_reasons
            ],
            "bess_charge_energy_mwh_step": charge_energy_mwh,
            "bess_discharge_energy_mwh_step": discharge_energy_mwh,
            "bess_charge_energy_mwh_total": self._cumulative_charge_energy_mwh.copy(),
            "bess_discharge_energy_mwh_total": (
                self._cumulative_discharge_energy_mwh.copy()
            ),
            "bess_constraint_violations": violations,
            "line_8_in_service": self._line_8_in_service(),
            "g4_in_service": g4_in_service,
            "g4_m_actual_system": g4_m,
            "g4_d_actual_system": g4_d,
        }
        self._previous_bess_command_system_pu = (
            projection.commanded_power_system_pu.copy()
        )
        self._previous_bess_projection = projection
        self._prev_omega = omega.copy()
        return observation, rewards, done, info


def expected_model_first_system_md(
    *,
    m_device=(200.0, 200.0, 200.0, 200.0),
    d_device=(100.0, 100.0, 100.0, 100.0),
) -> tuple[np.ndarray, np.ndarray]:
    """Public convenience readback target used by the stable adapter."""

    return (
        device_to_system_base(m_device, device_mva=200.0, system_mva=100.0),
        device_to_system_base(d_device, device_mva=200.0, system_mva=100.0),
    )
