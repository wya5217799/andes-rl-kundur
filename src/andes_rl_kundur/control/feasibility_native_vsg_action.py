"""Four-agent VSG actions parameterized inside the physical power box.

This module is an implementation seam, not a controller, reward, or scientific
result. It supports a direct zero-anchored action for diagnostics and a selected
deterministic-baseline-anchored residual action. Both map one scalar per VSG
inside that VSG's current power/ramp/capability/SOC/energy interval, so the
existing VSG energy-port projection is an identity guard rather than a repair.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from andes_rl_kundur.control.active_power import (
    EnergyFeasibleBESSContract,
    PowerProjection,
)


@dataclass(frozen=True)
class FeasibilityNativeVSGAction:
    """Auditable four-VSG command produced without central action aggregation."""

    normalized_actions: np.ndarray
    lower_power_system_pu: np.ndarray
    upper_power_system_pu: np.ndarray
    zero_anchor_power_system_pu: np.ndarray
    feasible_power_system_pu: np.ndarray
    external_projection: PowerProjection
    external_projection_identity: bool


@dataclass(frozen=True)
class FeasibilityNativeVSGResidualAction:
    """Auditable residual command anchored at a feasible deterministic action."""

    normalized_residual_actions: np.ndarray
    baseline_power_system_pu: np.ndarray
    lower_power_system_pu: np.ndarray
    upper_power_system_pu: np.ndarray
    feasible_power_system_pu: np.ndarray
    external_projection: PowerProjection
    external_projection_identity: bool


def _finite_vector(
    values: Sequence[float] | np.ndarray,
    *,
    size: int,
    name: str,
) -> np.ndarray:
    vector = np.asarray(values, dtype=float)
    if vector.shape != (size,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must be a finite vector with shape ({size},)")
    return vector


class FeasibilityNativeVSGActionMap:
    """Map one scalar per VSG directly to its current feasible power interval."""

    def __init__(self, physical_contract: EnergyFeasibleBESSContract) -> None:
        if physical_contract.device_count != 4:
            raise ValueError("feasibility-native VSG execution requires four devices")
        self.physical_contract = physical_contract

    @staticmethod
    def execution_contract() -> Mapping[str, Any]:
        """Return the literal deployment semantics used by comparison audits."""

        return {
            "actor_count": 4,
            "per_actor_action_dimension": 1,
            "executed_node_action_dimension": 4,
            "action_coordinates": "per_vsg_normalized_feasible_power",
            "central_action_aggregation": False,
            "external_projection_role": "identity_guard_only",
            "training_authorized": False,
        }

    @staticmethod
    def residual_execution_contract() -> Mapping[str, Any]:
        """Return the selected baseline-anchored residual semantics."""

        return {
            "actor_count": 4,
            "per_actor_action_dimension": 1,
            "executed_node_action_dimension": 4,
            "action_coordinates": "per_vsg_normalized_feasible_power_residual",
            "baseline_anchor": "feasible_deterministic_power",
            "zero_residual_behavior": "exact_deterministic_baseline",
            "central_action_aggregation": False,
            "external_projection_role": "identity_guard_only",
            "training_authorized": False,
        }

    def map_action(
        self,
        *,
        normalized_actions: Sequence[float] | np.ndarray,
        previous_power_system_pu: Sequence[float] | np.ndarray,
        soc: Sequence[float] | np.ndarray,
        voltage_pu: Sequence[float] | np.ndarray,
        dt_seconds: float,
    ) -> FeasibilityNativeVSGAction:
        """Return four feasible node commands from four bounded actor outputs.

        A zero actor output maps to zero power whenever zero lies in the current
        feasible interval. If ramp or another physical constraint temporarily
        excludes zero, it maps to the feasible point closest to zero. Positive
        and negative outputs then span the remaining upper and lower headroom
        without clipping or pooling another actor's action.
        """

        size = self.physical_contract.device_count
        action = _finite_vector(
            normalized_actions,
            size=size,
            name="normalized actions",
        )
        if np.any(action < -1.0) or np.any(action > 1.0):
            raise ValueError("normalized actions must remain inside [-1, 1]")
        previous = _finite_vector(
            previous_power_system_pu,
            size=size,
            name="previous power",
        )
        current_soc = _finite_vector(soc, size=size, name="soc")
        voltage = _finite_vector(voltage_pu, size=size, name="voltage")
        if np.any(current_soc < self.physical_contract.soc_min) or np.any(
            current_soc > self.physical_contract.soc_max
        ):
            raise ValueError("soc must remain inside the registered bounds")
        if np.any(voltage < 0.0):
            raise ValueError("voltage must be nonnegative")
        dt = float(dt_seconds)
        if not np.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt_seconds must be finite and positive")

        lower, upper = self.physical_contract.feasible_power_bounds(
            previous_power_system_pu=previous,
            soc=current_soc,
            voltage_pu=voltage,
            dt_seconds=dt,
        )
        if np.any(lower > upper):
            raise RuntimeError("physical contract returned an invalid feasible interval")
        zero_anchor = np.clip(np.zeros(size, dtype=float), lower, upper)
        positive_headroom = upper - zero_anchor
        negative_headroom = zero_anchor - lower
        feasible = zero_anchor + np.where(
            action >= 0.0,
            action * positive_headroom,
            action * negative_headroom,
        )

        projection = self.physical_contract.project_power(
            requested_power_system_pu=feasible,
            previous_power_system_pu=previous,
            soc=current_soc,
            voltage_pu=voltage,
            dt_seconds=dt,
        )
        identity = bool(
            np.allclose(
                projection.commanded_power_system_pu,
                feasible,
                rtol=0.0,
                atol=1.0e-12,
            )
            and not any(projection.saturation_reasons)
        )
        if not identity:
            raise RuntimeError("feasibility-native action failed the outer identity guard")
        return FeasibilityNativeVSGAction(
            normalized_actions=action.copy(),
            lower_power_system_pu=lower.copy(),
            upper_power_system_pu=upper.copy(),
            zero_anchor_power_system_pu=zero_anchor.copy(),
            feasible_power_system_pu=feasible.copy(),
            external_projection=projection,
            external_projection_identity=True,
        )

    def map_residual_action(
        self,
        *,
        normalized_residual_actions: Sequence[float] | np.ndarray,
        baseline_power_system_pu: Sequence[float] | np.ndarray,
        previous_power_system_pu: Sequence[float] | np.ndarray,
        soc: Sequence[float] | np.ndarray,
        voltage_pu: Sequence[float] | np.ndarray,
        dt_seconds: float,
    ) -> FeasibilityNativeVSGResidualAction:
        """Map four residuals into the headroom around a feasible baseline.

        Zero residual returns the deterministic baseline exactly. Positive and
        negative residuals span only the baseline's remaining upper and lower
        headroom. The baseline must already be feasible; this seam never clips
        or repairs the deterministic controller.
        """

        size = self.physical_contract.device_count
        residual = _finite_vector(
            normalized_residual_actions,
            size=size,
            name="normalized residual actions",
        )
        if np.any(residual < -1.0) or np.any(residual > 1.0):
            raise ValueError("normalized residual actions must remain inside [-1, 1]")
        baseline = _finite_vector(
            baseline_power_system_pu,
            size=size,
            name="baseline power",
        )
        previous = _finite_vector(
            previous_power_system_pu,
            size=size,
            name="previous power",
        )
        current_soc = _finite_vector(soc, size=size, name="soc")
        voltage = _finite_vector(voltage_pu, size=size, name="voltage")
        if np.any(current_soc < self.physical_contract.soc_min) or np.any(
            current_soc > self.physical_contract.soc_max
        ):
            raise ValueError("soc must remain inside the registered bounds")
        if np.any(voltage < 0.0):
            raise ValueError("voltage must be nonnegative")
        dt = float(dt_seconds)
        if not np.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt_seconds must be finite and positive")

        lower, upper = self.physical_contract.feasible_power_bounds(
            previous_power_system_pu=previous,
            soc=current_soc,
            voltage_pu=voltage,
            dt_seconds=dt,
        )
        if np.any(lower > upper):
            raise RuntimeError("physical contract returned an invalid feasible interval")
        if np.any(baseline < lower) or np.any(baseline > upper):
            raise ValueError("baseline power must already lie inside the feasible interval")

        positive_headroom = upper - baseline
        negative_headroom = baseline - lower
        feasible = baseline + np.where(
            residual >= 0.0,
            residual * positive_headroom,
            residual * negative_headroom,
        )
        projection = self.physical_contract.project_power(
            requested_power_system_pu=feasible,
            previous_power_system_pu=previous,
            soc=current_soc,
            voltage_pu=voltage,
            dt_seconds=dt,
        )
        identity = bool(
            np.allclose(
                projection.commanded_power_system_pu,
                feasible,
                rtol=0.0,
                atol=1.0e-12,
            )
            and not any(projection.saturation_reasons)
        )
        if not identity:
            raise RuntimeError("feasibility-native residual failed the outer identity guard")
        return FeasibilityNativeVSGResidualAction(
            normalized_residual_actions=residual.copy(),
            baseline_power_system_pu=baseline.copy(),
            lower_power_system_pu=lower.copy(),
            upper_power_system_pu=upper.copy(),
            feasible_power_system_pu=feasible.copy(),
            external_projection=projection,
            external_projection_identity=True,
        )
