"""Live fixed-state ANDES residual source for the R380 energy-port model.

The adapter binds an already initialized :class:`AndesVSGEnergyPortEnv`,
captures one exact DAE point, applies only the declared ``SynGen.pref/tm0``
and positive-baseline ``PQ.Ppf`` inputs, and restores every captured value.
It advances no trajectory and performs no research classification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from andes_rl_kundur.evaluation.vsg_energy_port_source_bridge import (
    VSGEnergyPortSourceBinding,
)

POSITIVE_REAL_TOLERANCE = 1.0e-7


def _finite_vector(values: object, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite vector")
    return array


def _dense_matrix(values: object, *, name: str) -> np.ndarray:
    try:
        array = np.asarray(values, dtype=float)
    except (TypeError, ValueError):
        from andes.shared import matrix

        array = np.asarray(matrix(values), dtype=float)
    if array.ndim != 2 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite matrix")
    return array


def _scalar_exit_code(value: object) -> int:
    array = np.asarray(value)
    if array.size != 1:
        raise ValueError("ANDES exit_code must be scalar")
    return int(array.reshape(-1)[0])


@dataclass(frozen=True)
class AndesVSGEnergyPortDescriptorSnapshot:
    """Source matrices and named state catalogs captured at one fixed point."""

    time_constants: np.ndarray
    f_x: np.ndarray
    f_y: np.ndarray
    g_x: np.ndarray
    g_y: np.ndarray
    state_names: list[str]
    algebraic_names: list[str]
    eig_state_matrix: np.ndarray
    eig_state_names: list[str]
    frequency_output_map: np.ndarray
    omega_state_addresses: np.ndarray
    equilibrium_x: np.ndarray
    equilibrium_y: np.ndarray
    equilibrium_z: np.ndarray
    equilibrium_f: np.ndarray
    equilibrium_g: np.ndarray
    initialization_residual_tolerance: float
    initialization_max_abs_f: float
    initialization_max_abs_g: float
    eig_eigenvalues: np.ndarray
    positive_real_tolerance: float
    positive_real_count: int


class AndesVSGEnergyPortFixedStateSource:
    """Restorable fixed-``x,y`` residual source bound to one initialized plant."""

    def __init__(
        self,
        *,
        system: Any,
        binding: VSGEnergyPortSourceBinding,
        models: Any,
        baseline_pref_system_pu: np.ndarray,
        baseline_load_system_pu: np.ndarray,
        load_positions: np.ndarray,
        descriptor_snapshot: AndesVSGEnergyPortDescriptorSnapshot,
    ) -> None:
        self.system = system
        self.binding = binding
        self._models = models
        self._baseline_pref_system_pu = baseline_pref_system_pu.copy()
        self._baseline_load_system_pu = baseline_load_system_pu.copy()
        self._load_positions = load_positions.copy()
        self.descriptor_snapshot = descriptor_snapshot

    @property
    def baseline_load_system_pu(self) -> np.ndarray:
        """Return a defensive copy of the three bound load baselines."""

        return self._baseline_load_system_pu.copy()

    @classmethod
    def from_initialized_energy_port_env(
        cls,
        environment: Any,
        *,
        pq_load_ids: tuple[str, str, str],
        source_fingerprint: str,
    ) -> AndesVSGEnergyPortFixedStateSource:
        """Capture one initialized energy-port environment without stepping it."""

        if getattr(environment, "_baseline_pref_system_pu", None) is None:
            raise RuntimeError("energy-port environment must be reset before binding")
        base_env = environment.base_env
        system = base_env.ss
        if float(base_env.DT) != 0.2:
            raise ValueError("energy-port source requires a 0.2 s sample period")
        if system.PFlow.converged is not True:
            raise RuntimeError("ANDES power flow is not converged")
        if system.TDS.test_ok is not True or _scalar_exit_code(system.exit_code) != 0:
            raise RuntimeError("ANDES TDS initialization is not valid")
        if int(getattr(system.ESD1, "n", 0)) != 0:
            raise ValueError("energy-port source must not contain ESD1 devices")

        vsg_ids = tuple(str(value) for value in environment._vsg_indices())
        sampled_omega = _finite_vector(
            environment._vsg_vector("omega"),
            name="sampled VSG omega",
        )
        binding = VSGEnergyPortSourceBinding(
            vsg_port_ids=vsg_ids,
            pq_load_ids=tuple(pq_load_ids),
            sampled_omega_pu=sampled_omega,
            source_fingerprint=source_fingerprint,
        )
        load_positions = np.asarray(
            [int(system.PQ.idx2uid(name)) for name in binding.pq_load_ids],
            dtype=int,
        )
        baseline_load = _finite_vector(
            np.asarray(system.PQ.Ppf.v, dtype=float)[load_positions],
            name="PQ active-power baseline",
        )
        if np.any(baseline_load <= 0.0):
            raise ValueError("declared PQ inputs must have positive active-power baselines")
        baseline_pref = _finite_vector(
            [system.SynGen.get_pref(system, name) for name in binding.vsg_port_ids],
            name="VSG pref baseline",
        )

        models = system.exist.pflow_tds
        system.TDS.fg_update(models=models)
        system.j_update(models=models, info="R380 fixed-state descriptor snapshot")
        equilibrium_x = _finite_vector(system.dae.x, name="equilibrium x").copy()
        equilibrium_y = _finite_vector(system.dae.y, name="equilibrium y").copy()
        equilibrium_z = _finite_vector(system.dae.z, name="equilibrium z").copy()
        equilibrium_f = _finite_vector(system.dae.f, name="equilibrium f").copy()
        equilibrium_g = _finite_vector(system.dae.g, name="equilibrium g").copy()
        residual_tolerance = float(system.TDS.config.tol)
        maximum_f = float(np.max(np.abs(equilibrium_f)))
        maximum_g = float(np.max(np.abs(equilibrium_g)))
        if (
            not np.isfinite(residual_tolerance)
            or residual_tolerance <= 0.0
            or max(maximum_f, maximum_g) >= residual_tolerance
        ):
            raise RuntimeError("ANDES initialization residual guard failed")
        state_names = [str(value) for value in system.dae.x_name]
        algebraic_names = [str(value) for value in system.dae.y_name]
        if len(state_names) != equilibrium_x.size or len(algebraic_names) != equilibrium_y.size:
            raise ValueError("ANDES state catalogs do not match DAE vectors")

        vsg_positions = np.asarray(base_env._vsg_pos, dtype=int)
        omega_addresses = np.asarray(system.GENCLS.omega.a, dtype=int)[vsg_positions]
        if (
            omega_addresses.shape != (4,)
            or len(set(int(value) for value in omega_addresses)) != 4
            or np.any(omega_addresses < 0)
            or np.any(omega_addresses >= equilibrium_x.size)
        ):
            raise ValueError("four distinct VSG omega state addresses are required")
        frequency_output = np.zeros((4, equilibrium_x.size), dtype=float)
        for output_index, state_address in enumerate(omega_addresses):
            frequency_output[output_index, state_address] = 60.0

        eig_state_matrix = _dense_matrix(
            system.EIG.calc_As(dense=True),
            name="EIG state matrix",
        ).copy()
        eigenvalues = np.linalg.eigvals(eig_state_matrix)
        if not np.all(np.isfinite(eigenvalues)):
            raise RuntimeError("ANDES EIG spectrum is not finite")
        positive_real_count = int(
            np.count_nonzero(np.real(eigenvalues) > POSITIVE_REAL_TOLERANCE)
        )
        if positive_real_count:
            raise RuntimeError("ANDES EIG positive-real guard failed")

        snapshot = AndesVSGEnergyPortDescriptorSnapshot(
            time_constants=_finite_vector(system.dae.Tf, name="Tf").copy(),
            f_x=_dense_matrix(system.dae.fx, name="f_x").copy(),
            f_y=_dense_matrix(system.dae.fy, name="f_y").copy(),
            g_x=_dense_matrix(system.dae.gx, name="g_x").copy(),
            g_y=_dense_matrix(system.dae.gy, name="g_y").copy(),
            state_names=state_names,
            algebraic_names=algebraic_names,
            eig_state_matrix=eig_state_matrix,
            eig_state_names=[str(value) for value in system.EIG.x_name],
            frequency_output_map=frequency_output,
            omega_state_addresses=omega_addresses.copy(),
            equilibrium_x=equilibrium_x,
            equilibrium_y=equilibrium_y,
            equilibrium_z=equilibrium_z,
            equilibrium_f=equilibrium_f,
            equilibrium_g=equilibrium_g,
            initialization_residual_tolerance=residual_tolerance,
            initialization_max_abs_f=maximum_f,
            initialization_max_abs_g=maximum_g,
            eig_eigenvalues=eigenvalues.copy(),
            positive_real_tolerance=POSITIVE_REAL_TOLERANCE,
            positive_real_count=positive_real_count,
        )
        source = cls(
            system=system,
            binding=binding,
            models=models,
            baseline_pref_system_pu=baseline_pref,
            baseline_load_system_pu=baseline_load,
            load_positions=load_positions,
            descriptor_snapshot=snapshot,
        )
        source.restore()
        return source

    def evaluate_fixed_residual(
        self,
        *,
        vsg_tm0_delta_system_pu: np.ndarray,
        pq_active_power_delta_system_pu: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Evaluate the exact captured point under declared port perturbations."""

        control = _finite_vector(
            vsg_tm0_delta_system_pu,
            name="VSG tm0 delta",
        )
        disturbance = _finite_vector(
            pq_active_power_delta_system_pu,
            name="PQ active-power delta",
        )
        if control.shape != (4,) or disturbance.shape != (3,):
            raise ValueError("R380 residual source requires four control and three load inputs")
        perturbed_load = self._baseline_load_system_pu + disturbance
        if np.any(perturbed_load < 0.0):
            raise ValueError("input perturbation would create a negative physical load")

        self._restore_values(check=False)
        for device_id, value in zip(
            self.binding.vsg_port_ids,
            self._baseline_pref_system_pu + control,
            strict=True,
        ):
            self.system.SynGen.set_pref(self.system, device_id, float(value))
        for device_id, value in zip(
            self.binding.pq_load_ids,
            perturbed_load,
            strict=True,
        ):
            self.system.PQ.set("Ppf", device_id, float(value), attr="v")
        self.system.TDS.fg_update(models=self._models)
        f_value = _finite_vector(self.system.dae.f, name="perturbed f").copy()
        g_value = _finite_vector(self.system.dae.g, name="perturbed g").copy()
        return f_value, g_value

    def restore(self) -> None:
        """Restore ports, loads, DAE vectors, and residuals exactly."""

        self._restore_values(check=True)

    def _restore_values(self, *, check: bool) -> None:
        snapshot = self.descriptor_snapshot
        self.system.dae.x[:] = snapshot.equilibrium_x
        self.system.dae.y[:] = snapshot.equilibrium_y
        self.system.dae.z[:] = snapshot.equilibrium_z
        for device_id, value in zip(
            self.binding.vsg_port_ids,
            self._baseline_pref_system_pu,
            strict=True,
        ):
            self.system.SynGen.set_pref(self.system, device_id, float(value))
        for device_id, value in zip(
            self.binding.pq_load_ids,
            self._baseline_load_system_pu,
            strict=True,
        ):
            self.system.PQ.set("Ppf", device_id, float(value), attr="v")
        self.system.TDS.fg_update(models=self._models)
        if not check:
            return
        restored_pref = np.asarray(
            [
                self.system.SynGen.get_pref(self.system, device_id)
                for device_id in self.binding.vsg_port_ids
            ],
            dtype=float,
        )
        restored_load = np.asarray(self.system.PQ.Ppf.v, dtype=float)[
            self._load_positions
        ]
        pairs = (
            (self.system.dae.x, snapshot.equilibrium_x),
            (self.system.dae.y, snapshot.equilibrium_y),
            (self.system.dae.z, snapshot.equilibrium_z),
            (self.system.dae.f, snapshot.equilibrium_f),
            (self.system.dae.g, snapshot.equilibrium_g),
            (restored_pref, self._baseline_pref_system_pu),
            (restored_load, self._baseline_load_system_pu),
        )
        if not all(np.array_equal(np.asarray(actual), expected) for actual, expected in pairs):
            raise RuntimeError("fixed-state residual source did not restore exactly")
