"""Pure source-input bridge for the four VSG energy-port object.

The module converts incremental per-VSG active-power commands into the literal
``SynGen.pref/tm0`` perturbations seen by a fixed-state DAE residual source,
derives four control and three physical-load input columns independently, and
restores the source after every evaluation.  It runs no simulator trajectory
and owns no model-validity or research classification.

Callers provide a fixed-state residual source and a bound four-port identity.
Invalid bindings or residual shapes fail closed; live ANDES binding remains a
separately authorized adapter outside this pure module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from andes_rl_kundur.env.andes.model_first_contract import (
    InputJacobians,
    finite_difference_input_jacobians,
)

VSG_ENERGY_PORT_SEMANTICS = "VSG-owned sampled pref/tm0 port; no ESD1"
VSG_NOMINAL_FREQUENCY_HZ = 60.0
VSG_SAMPLE_PERIOD_SECONDS = 0.2


class FixedStateVSGResidualSource(Protocol):
    """Residual source restored to one fixed ``x,y`` point after every call."""

    binding: VSGEnergyPortSourceBinding

    def evaluate_fixed_residual(
        self,
        *,
        vsg_tm0_delta_system_pu: np.ndarray,
        pq_active_power_delta_system_pu: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]: ...

    def restore(self) -> None: ...


@dataclass(frozen=True)
class VSGEnergyPortSourceBinding:
    """Installed identities and sampled speed for four VSG power ports."""

    vsg_port_ids: tuple[str, ...]
    pq_load_ids: tuple[str, ...]
    sampled_omega_pu: np.ndarray
    source_fingerprint: str
    port_semantics: str = VSG_ENERGY_PORT_SEMANTICS
    legacy_md_action_enabled: bool = False
    nominal_frequency_hz: float = VSG_NOMINAL_FREQUENCY_HZ
    sample_period_seconds: float = VSG_SAMPLE_PERIOD_SECONDS

    def __post_init__(self) -> None:
        vsg_ids = tuple(str(value).strip() for value in self.vsg_port_ids)
        load_ids = tuple(str(value).strip() for value in self.pq_load_ids)
        if (
            len(vsg_ids) != 4
            or len(set(vsg_ids)) != 4
            or not all(vsg_ids)
            or len(load_ids) != 3
            or len(set(load_ids)) != 3
            or not all(load_ids)
        ):
            raise ValueError(
                "binding requires four distinct VSG and three distinct PQ identities"
            )
        omega = np.asarray(self.sampled_omega_pu, dtype=float)
        if omega.shape != (4,) or not np.all(np.isfinite(omega)) or np.any(omega <= 0):
            raise ValueError("sampled_omega_pu must contain four positive values")
        fingerprint = str(self.source_fingerprint).strip()
        if not fingerprint:
            raise ValueError("source_fingerprint must be non-empty")
        if self.port_semantics != VSG_ENERGY_PORT_SEMANTICS:
            raise ValueError("port_semantics must bind the VSG pref/tm0 object")
        if bool(self.legacy_md_action_enabled):
            raise ValueError("legacy_md_action_enabled must remain false")
        nominal_frequency = float(self.nominal_frequency_hz)
        if nominal_frequency != VSG_NOMINAL_FREQUENCY_HZ:
            raise ValueError("nominal_frequency_hz must remain 60 Hz")
        sample_period = float(self.sample_period_seconds)
        if sample_period != VSG_SAMPLE_PERIOD_SECONDS:
            raise ValueError("sample_period_seconds must remain 0.2 s")
        object.__setattr__(self, "vsg_port_ids", vsg_ids)
        object.__setattr__(self, "pq_load_ids", load_ids)
        object.__setattr__(self, "sampled_omega_pu", omega.copy())
        object.__setattr__(self, "source_fingerprint", fingerprint)
        object.__setattr__(self, "legacy_md_action_enabled", False)
        object.__setattr__(self, "nominal_frequency_hz", nominal_frequency)
        object.__setattr__(self, "sample_period_seconds", sample_period)


@dataclass(frozen=True)
class VSGEnergyPortSourceProvenance:
    """Identity record carried with derived input columns."""

    vsg_port_ids: tuple[str, ...]
    pq_load_ids: tuple[str, ...]
    source_fingerprint: str
    port_semantics: str
    nominal_frequency_hz: float
    sample_period_seconds: float
    step_system_pu: float
    derivative_scheme: str


@dataclass(frozen=True)
class VSGEnergyPortInputBridge:
    """Separate control/load input columns for the existing reduction modules."""

    control: InputJacobians
    disturbance: InputJacobians
    power_to_tm0_jacobian: np.ndarray
    provenance: VSGEnergyPortSourceProvenance

    @property
    def joint_f_input(self) -> np.ndarray:
        return np.hstack((self.control.f_input, self.disturbance.f_input))

    @property
    def joint_g_input(self) -> np.ndarray:
        return np.hstack((self.control.g_input, self.disturbance.g_input))


def derive_vsg_energy_port_input_bridge(
    *,
    binding: VSGEnergyPortSourceBinding,
    source: FixedStateVSGResidualSource,
    step_system_pu: float,
) -> VSGEnergyPortInputBridge:
    """Derive four power-control and four physical-load residual columns."""

    source_binding = getattr(source, "binding", None)
    if not isinstance(source_binding, VSGEnergyPortSourceBinding) or not (
        source_binding.vsg_port_ids == binding.vsg_port_ids
        and source_binding.pq_load_ids == binding.pq_load_ids
        and source_binding.source_fingerprint == binding.source_fingerprint
        and source_binding.port_semantics == binding.port_semantics
        and source_binding.nominal_frequency_hz == binding.nominal_frequency_hz
        and source_binding.sample_period_seconds == binding.sample_period_seconds
        and np.array_equal(
            source_binding.sampled_omega_pu,
            binding.sampled_omega_pu,
        )
    ):
        raise ValueError("source binding does not match the declared VSG object")

    zero_control = np.zeros(4, dtype=float)
    zero_disturbance = np.zeros(3, dtype=float)
    power_to_tm0 = np.diag(1.0 / binding.sampled_omega_pu)

    def evaluate_control(power_delta: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        try:
            return source.evaluate_fixed_residual(
                vsg_tm0_delta_system_pu=power_to_tm0 @ power_delta,
                pq_active_power_delta_system_pu=zero_disturbance.copy(),
            )
        finally:
            source.restore()

    def evaluate_disturbance(load_delta: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        try:
            return source.evaluate_fixed_residual(
                vsg_tm0_delta_system_pu=zero_control.copy(),
                pq_active_power_delta_system_pu=load_delta.copy(),
            )
        finally:
            source.restore()

    control = finite_difference_input_jacobians(
        evaluate_control,
        equilibrium_input=zero_control,
        step=step_system_pu,
    )
    disturbance = finite_difference_input_jacobians(
        evaluate_disturbance,
        equilibrium_input=zero_disturbance,
        step=step_system_pu,
    )
    return VSGEnergyPortInputBridge(
        control=control,
        disturbance=disturbance,
        power_to_tm0_jacobian=power_to_tm0,
        provenance=VSGEnergyPortSourceProvenance(
            vsg_port_ids=tuple(binding.vsg_port_ids),
            pq_load_ids=tuple(binding.pq_load_ids),
            source_fingerprint=str(binding.source_fingerprint),
            port_semantics=binding.port_semantics,
            nominal_frequency_hz=binding.nominal_frequency_hz,
            sample_period_seconds=binding.sample_period_seconds,
            step_system_pu=float(step_system_pu),
            derivative_scheme=control.scheme,
        ),
    )
