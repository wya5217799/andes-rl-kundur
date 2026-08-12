"""Four-agent energy-port adapter for the existing V4 VSG environment.

This wrapper deliberately leaves the legacy inertia/damping action path at
zero.  Its only control write is one sampled ``SynGen.pref`` value for each of
the four VSG indices.  For governor-free ``GENCLS`` models the installed ANDES
contract routes that setpoint to ``tm0``, so energy is settled from read-back
torque times rotor speed rather than by treating torque as constant power.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from andes_rl_kundur.control.active_power import r272_frozen_bess_contract
from andes_rl_kundur.control.vsg_energy_port import VSGEnergyPortContract


class AndesVSGEnergyPortEnv:
    """Expose four energy-constrained active-power actions on V4 VSGs."""

    def __init__(
        self,
        *,
        base_env: Any | None = None,
        port_contract: VSGEnergyPortContract | None = None,
    ) -> None:
        if base_env is None:
            from andes_rl_kundur.env.andes.andes_vsg_env_v4 import (
                AndesMultiVSGEnvV4,
            )

            base_env = AndesMultiVSGEnvV4(
                random_disturbance=False,
                comm_fail_prob=0.0,
            )
        if int(base_env.N_AGENTS) != 4:
            raise ValueError("energy-port adapter requires exactly four VSG agents")

        self.base_env = base_env
        self.port_contract = port_contract or VSGEnergyPortContract(
            r272_frozen_bess_contract()
        )
        if self.port_contract.energy_contract.device_count != 4:
            raise ValueError("energy contract must describe exactly four devices")

        self._baseline_pref_system_pu: np.ndarray | None = None
        self._soc: np.ndarray | None = None
        self._previous_power_system_pu: np.ndarray | None = None
        self._charged_energy_mwh: np.ndarray | None = None
        self._discharged_energy_mwh: np.ndarray | None = None

    def reset(self, *args: Any, **kwargs: Any) -> Any:
        """Reset V4, bind one pref baseline per VSG, and reset energy state."""

        observation = self.base_env.reset(*args, **kwargs)
        indices = self._vsg_indices()
        self._baseline_pref_system_pu = np.asarray(
            [
                float(self.base_env.ss.SynGen.get_pref(self.base_env.ss, index))
                for index in indices
            ],
            dtype=float,
        )
        initial_soc = self.port_contract.energy_contract.soc_initial
        self._soc = np.full(4, initial_soc, dtype=float)
        self._previous_power_system_pu = np.zeros(4, dtype=float)
        self._charged_energy_mwh = np.zeros(4, dtype=float)
        self._discharged_energy_mwh = np.zeros(4, dtype=float)
        return observation

    def step(self, requested_power_system_pu: np.ndarray) -> tuple[Any, Any, Any, dict]:
        """Project four power requests, write four prefs, and settle readback."""

        self._require_reset()
        assert self._baseline_pref_system_pu is not None
        assert self._soc is not None
        assert self._previous_power_system_pu is not None
        assert self._charged_energy_mwh is not None
        assert self._discharged_energy_mwh is not None

        omega_before = self._vsg_vector("omega")
        voltage_before = self._vsg_vector("v")
        dispatch = self.port_contract.dispatch(
            requested_power_system_pu=requested_power_system_pu,
            previous_power_system_pu=self._previous_power_system_pu,
            soc=self._soc,
            voltage_pu=voltage_before,
            sampled_omega_pu=omega_before,
            baseline_pref_system_pu=self._baseline_pref_system_pu,
            dt_seconds=float(self.base_env.DT),
        )

        for index, pref in zip(
            self._vsg_indices(),
            dispatch.pref_system_pu,
            strict=True,
        ):
            self.base_env.ss.SynGen.set_pref(
                self.base_env.ss,
                index,
                float(pref),
            )

        zero_md_actions = {index: np.zeros(2) for index in range(4)}
        observation, rewards, done, info = self.base_env.step(zero_md_actions)

        actual_pref = np.asarray(
            [
                float(self.base_env.ss.SynGen.get_pref(self.base_env.ss, index))
                for index in self._vsg_indices()
            ],
            dtype=float,
        )
        actual_torque = self._vsg_vector("tm")
        omega_after = self._vsg_vector("omega")
        average_omega = 0.5 * (omega_before + omega_after)
        settlement = self.port_contract.settle(
            soc=self._soc,
            actual_torque_system_pu=actual_torque,
            baseline_pref_system_pu=self._baseline_pref_system_pu,
            actual_omega_pu=average_omega,
            dt_seconds=float(self.base_env.DT),
        )

        self._soc = settlement.next_soc.copy()
        self._previous_power_system_pu = dispatch.commanded_power_system_pu.copy()
        self._charged_energy_mwh += settlement.charged_energy_mwh
        self._discharged_energy_mwh += settlement.discharged_energy_mwh

        merged_info = dict(info)
        merged_info.update(
            {
                "vsg_energy_port_requested_power_system_pu": (
                    dispatch.requested_power_system_pu.copy()
                ),
                "vsg_energy_port_commanded_power_system_pu": (
                    dispatch.commanded_power_system_pu.copy()
                ),
                "vsg_energy_port_sampled_omega_pu": (
                    dispatch.sampled_omega_pu.copy()
                ),
                "vsg_energy_port_baseline_pref_system_pu": (
                    self._baseline_pref_system_pu.copy()
                ),
                "vsg_energy_port_pref_written_system_pu": (
                    dispatch.pref_system_pu.copy()
                ),
                "vsg_energy_port_pref_readback_system_pu": actual_pref.copy(),
                "vsg_energy_port_torque_readback_system_pu": (
                    actual_torque.copy()
                ),
                "vsg_energy_port_achieved_power_system_pu": (
                    settlement.achieved_power_system_pu.copy()
                ),
                "vsg_energy_port_soc": self._soc.copy(),
                "vsg_energy_port_charged_energy_mwh": (
                    settlement.charged_energy_mwh.copy()
                ),
                "vsg_energy_port_discharged_energy_mwh": (
                    settlement.discharged_energy_mwh.copy()
                ),
                "vsg_energy_port_total_charged_energy_mwh": (
                    self._charged_energy_mwh.copy()
                ),
                "vsg_energy_port_total_discharged_energy_mwh": (
                    self._discharged_energy_mwh.copy()
                ),
                "vsg_energy_port_saturation_reasons": (
                    dispatch.saturation_reasons
                ),
                "vsg_energy_port_md_action_norm": np.zeros((4, 2)),
                "vsg_energy_port_object_semantics": (
                    "VSG-owned sampled pref/tm0 port; no ESD1"
                ),
            }
        )
        return observation, rewards, done, merged_info

    def seed(self, *args: Any, **kwargs: Any) -> Any:
        return self.base_env.seed(*args, **kwargs)

    def close(self) -> Any:
        return self.base_env.close()

    def _require_reset(self) -> None:
        if self._baseline_pref_system_pu is None:
            raise RuntimeError("reset must be called before step")

    def _vsg_indices(self) -> tuple[Any, ...]:
        indices = tuple(self.base_env.vsg_idx)
        if len(indices) != 4 or len(set(indices)) != 4:
            raise ValueError("require four distinct VSG indices")
        return indices

    def _vsg_vector(self, variable_name: str) -> np.ndarray:
        positions = tuple(self.base_env._vsg_pos)
        if len(positions) != 4 or len(set(positions)) != 4:
            raise ValueError("require four distinct VSG positions")
        variable = getattr(self.base_env.ss.GENCLS, variable_name)
        values = np.asarray(variable.v, dtype=float)
        selected = np.asarray([values[position] for position in positions], dtype=float)
        if selected.shape != (4,) or not np.all(np.isfinite(selected)):
            raise ValueError(f"GENCLS {variable_name} must provide four finite values")
        return selected
