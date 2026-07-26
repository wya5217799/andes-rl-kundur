"""R272 hybrid V4 plus independent ESD1 active-power authority environment."""

from __future__ import annotations

from typing import Any

import numpy as np

from andes_rl_kundur.control.active_power import (
    EnergyFeasibleBESSContract,
    PowerProjection,
    r272_frozen_bess_contract,
)
from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4


class AndesMultiVSGEnvV4Storage(AndesMultiVSGEnvV4):
    """Keep V4 intact and add four independently commanded GFL ESD1 devices."""

    def __init__(
        self,
        *args: Any,
        bess_contract: EnergyFeasibleBESSContract | None = None,
        **kwargs: Any,
    ) -> None:
        self.bess_contract = bess_contract or r272_frozen_bess_contract()
        self.bess_idx = [
            f"R272_BESS_{index + 1}"
            for index in range(self.bess_contract.device_count)
        ]
        super().__init__(*args, **kwargs)

    def _pre_setup_addons(self, ss) -> None:
        super()._pre_setup_addons(ss)
        if self.bess_contract.device_count != len(self.VSG_BUSES):
            raise ValueError("R272 requires exactly one ESD1 per VSG bus")

        for index, (bess_idx, bus) in enumerate(
            zip(self.bess_idx, self.VSG_BUSES, strict=True)
        ):
            static_idx = f"R272_BESS_PV_{index + 1}"
            ss.add(
                "PV",
                {
                    "idx": static_idx,
                    "name": static_idx,
                    "bus": bus,
                    "Vn": self.NEW_BUS_VN,
                    "Sn": self.bess_contract.device_power_mva,
                    "p0": 0.0,
                    "q0": 0.0,
                    "pmax": 1.0,
                    "pmin": -1.0,
                    "qmax": 0.0,
                    "qmin": 0.0,
                    "v0": 1.0,
                },
            )
            ss.add(
                "ESD1",
                {
                    "idx": bess_idx,
                    "name": bess_idx,
                    "bus": bus,
                    "gen": static_idx,
                    "Sn": self.bess_contract.device_power_mva,
                    "fn": 60.0,
                    "xc": 0.0,
                    "pqflag": 1,
                    "qmx": 0.0,
                    "qmn": 0.0,
                    "pmx": 1.0,
                    "ddn": 0.0,
                    "ialim": self.bess_contract.active_current_limit_device_pu,
                    "tip": self.bess_contract.active_current_lag_seconds,
                    "tiq": self.bess_contract.active_current_lag_seconds,
                    "gammap": 1.0,
                    "gammaq": 1.0,
                    "Tf": 1.0,
                    "SOCmin": self.bess_contract.soc_min,
                    "SOCmax": self.bess_contract.soc_max,
                    "SOCinit": self.bess_contract.soc_initial,
                    "En": self.bess_contract.device_energy_mwh,
                    "EtaC": self.bess_contract.charge_efficiency,
                    "EtaD": self.bess_contract.discharge_efficiency,
                },
            )

    def reset(self, *args: Any, **kwargs: Any):
        obs = super().reset(*args, **kwargs)
        esd_indices = list(self.ss.ESD1.idx.v)
        self._bess_pos = [esd_indices.index(idx) for idx in self.bess_idx]
        self._previous_bess_command_system_pu = np.zeros(
            self.bess_contract.device_count,
            dtype=float,
        )
        self._previous_bess_projection: PowerProjection | None = None
        self._cumulative_charge_energy_mwh = np.zeros(
            self.bess_contract.device_count,
            dtype=float,
        )
        self._cumulative_discharge_energy_mwh = np.zeros(
            self.bess_contract.device_count,
            dtype=float,
        )
        return obs

    def _get_bess_soc(self) -> np.ndarray:
        return np.asarray(
            [self.ss.ESD1.SOC.v[pos] for pos in self._bess_pos],
            dtype=float,
        )

    def _get_bess_voltage(self) -> np.ndarray:
        return np.asarray(
            [self.ss.ESD1.v.v[pos] for pos in self._bess_pos],
            dtype=float,
        )

    def _get_bess_actual_power(self) -> np.ndarray:
        return np.asarray(
            [
                self.ss.ESD1.v.v[pos] * self.ss.ESD1.Ipout_y.v[pos]
                for pos in self._bess_pos
            ],
            dtype=float,
        )

    def get_vsg_frequency_physical_hz(self) -> np.ndarray:
        """Return current VSG frequencies on the ANDES physical-Hz basis."""
        return self._get_vsg_omega() * self.andes_nominal_frequency_hz

    @property
    def last_bess_projection(self) -> PowerProjection | None:
        """Return the previous public projection for controller anti-windup."""
        return self._previous_bess_projection

    def step(self, actions, *, bess_power_request_pu):
        requested = np.asarray(bess_power_request_pu, dtype=float)
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

        obs, rewards, done, info = super().step(actions)
        soc_after = self._get_bess_soc()
        actual_power = self._get_bess_actual_power()
        stored_delta_mwh = (
            soc_after - soc_before
        ) * self.bess_contract.device_energy_mwh
        charge_energy_mwh = np.maximum(stored_delta_mwh, 0.0)
        discharge_energy_mwh = np.maximum(-stored_delta_mwh, 0.0)
        self._cumulative_charge_energy_mwh += charge_energy_mwh
        self._cumulative_discharge_energy_mwh += discharge_energy_mwh

        violations: list[str] = []
        if np.any(soc_after < self.bess_contract.soc_min - 1e-9):
            violations.append("soc_below_min")
        if np.any(soc_after > self.bess_contract.soc_max + 1e-9):
            violations.append("soc_above_max")
        if np.any(
            np.abs(projection.commanded_power_system_pu)
            > self.bess_contract.device_power_limit_system_pu + 1e-12
        ):
            violations.append("command_power")

        info.update(
            {
                "bess_requested_power_system_pu": requested.copy(),
                "bess_commanded_power_system_pu": (
                    projection.commanded_power_system_pu.copy()
                ),
                "bess_actual_power_system_pu": actual_power,
                "bess_soc": soc_after,
                "bess_bus_voltage_pu": self._get_bess_voltage(),
                "bess_saturation_reasons": [
                    list(reasons) for reasons in projection.saturation_reasons
                ],
                "bess_charge_energy_mwh_step": charge_energy_mwh,
                "bess_discharge_energy_mwh_step": discharge_energy_mwh,
                "bess_charge_energy_mwh_total": (
                    self._cumulative_charge_energy_mwh.copy()
                ),
                "bess_discharge_energy_mwh_total": (
                    self._cumulative_discharge_energy_mwh.copy()
                ),
                "bess_constraint_violations": violations,
            }
        )
        self._previous_bess_command_system_pu = (
            projection.commanded_power_system_pu.copy()
        )
        self._previous_bess_projection = projection
        return obs, rewards, done, info
