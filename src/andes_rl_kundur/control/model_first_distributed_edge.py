"""Matched endpoint-local deterministic and future-policy edge seam.

The module owns no simulator or research classification.  One edge controller
receives exactly two endpoint observations and returns one normalized action;
joint plant state and global statistics are not representable at this public
boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Mapping, Sequence

import numpy as np

from andes_rl_kundur.control.active_power import (
    EnergyFeasibleBESSContract,
    PowerProjection,
)
from andes_rl_kundur.control.headroom_aware_edge_allocation import (
    allocate_edge_flows_with_headroom,
)
from andes_rl_kundur.env.andes.model_first_contract import (
    ACTION_EDGES,
    active_power_incidence,
)


Edge = tuple[int, int]


def _canonical_edge(edge: Edge) -> Edge:
    source, target = (int(value) for value in edge)
    if source < 0 or target < 0 or source >= target:
        raise ValueError("edge must use non-negative source-before-target orientation")
    return source, target


@dataclass(frozen=True)
class EndpointObservation:
    """Runtime values owned by one endpoint of a deployed edge."""

    node_id: int
    frequency_deviation_hz: float
    rocof_hz_s: float
    previous_command_system_pu: float
    soc: float
    voltage_pu: float
    lower_residual_power_system_pu: float
    upper_residual_power_system_pu: float

    def __post_init__(self) -> None:
        if int(self.node_id) < 0:
            raise ValueError("node_id must be non-negative")
        numeric = (
            self.frequency_deviation_hz,
            self.rocof_hz_s,
            self.previous_command_system_pu,
            self.soc,
            self.voltage_pu,
            self.lower_residual_power_system_pu,
            self.upper_residual_power_system_pu,
        )
        if not all(math.isfinite(float(value)) for value in numeric):
            raise ValueError("endpoint observation must be finite")
        if self.lower_residual_power_system_pu > self.upper_residual_power_system_pu:
            raise ValueError("endpoint residual lower bound exceeds upper bound")


@dataclass(frozen=True)
class LocalEdgeObservation:
    """The complete deployed input of one deterministic or learned edge actor."""

    edge: Edge
    source: EndpointObservation
    target: EndpointObservation
    previous_edge_flow_system_pu: float

    def __post_init__(self) -> None:
        edge = _canonical_edge(self.edge)
        if (self.source.node_id, self.target.node_id) != edge:
            raise ValueError("endpoint observations do not match the edge orientation")
        if not math.isfinite(float(self.previous_edge_flow_system_pu)):
            raise ValueError("previous edge flow must be finite")


class LinearNeighbourEdgeController:
    """One deterministic endpoint-difference policy with a normalized action."""

    def __init__(
        self,
        *,
        edge: Edge,
        frequency_difference_gain_per_hz: float,
        rocof_difference_gain_s_per_hz: float,
    ) -> None:
        self.edge = _canonical_edge(edge)
        self.frequency_gain = float(frequency_difference_gain_per_hz)
        self.rocof_gain = float(rocof_difference_gain_s_per_hz)
        if not all(
            math.isfinite(value) and value >= 0.0
            for value in (self.frequency_gain, self.rocof_gain)
        ):
            raise ValueError("edge-controller gains must be finite and non-negative")

    def act(self, observation: LocalEdgeObservation) -> float:
        """Return one source-positive action in the normalized interval."""

        if observation.edge != self.edge:
            raise ValueError("observation edge does not match this controller")
        frequency_difference = (
            observation.source.frequency_deviation_hz
            - observation.target.frequency_deviation_hz
        )
        rocof_difference = (
            observation.source.rocof_hz_s - observation.target.rocof_hz_s
        )
        raw = -(
            self.frequency_gain * frequency_difference
            + self.rocof_gain * rocof_difference
        )
        return float(np.clip(raw, -1.0, 1.0))


class IndependentNeighbourEdgeExecution:
    """Order three independently evaluated endpoint-local edge actors."""

    architecture = "three_independent_endpoint_local_edge_actors"

    def __init__(
        self,
        controllers: Sequence[LinearNeighbourEdgeController],
    ) -> None:
        self.controllers = tuple(controllers)
        if tuple(controller.edge for controller in self.controllers) != ACTION_EDGES:
            raise ValueError("controllers must follow the frozen three-edge order")

    def act(
        self,
        observations: Mapping[Edge, LocalEdgeObservation],
    ) -> np.ndarray:
        """Return three actions without exposing any actor to another edge."""

        if set(observations) != set(ACTION_EDGES):
            raise ValueError("one observation is required for each frozen edge")
        return np.asarray(
            [controller.act(observations[controller.edge]) for controller in self.controllers],
            dtype=float,
        )


class JointInformationEdgeController:
    """Diagnostic joint-information law on the matched three-edge action space."""

    architecture = "joint_information_three_edge_upper_reference"

    def __init__(
        self,
        *,
        frequency_difference_gain_per_hz: float,
        rocof_difference_gain_s_per_hz: float,
    ) -> None:
        self.frequency_gain = float(frequency_difference_gain_per_hz)
        self.rocof_gain = float(rocof_difference_gain_s_per_hz)
        if not all(
            math.isfinite(value) and value >= 0.0
            for value in (self.frequency_gain, self.rocof_gain)
        ):
            raise ValueError("joint-controller gains must be finite and non-negative")

    def act(self, endpoints: Mapping[int, EndpointObservation]) -> np.ndarray:
        """Return tree-edge actions after an explicit joint mean removal."""

        if set(endpoints) != set(range(4)):
            raise ValueError("joint controller requires exactly four endpoint observations")
        ordered = tuple(endpoints[index] for index in range(4))
        if tuple(endpoint.node_id for endpoint in ordered) != tuple(range(4)):
            raise ValueError("endpoint keys and node identifiers must agree")
        frequency = np.asarray(
            [endpoint.frequency_deviation_hz for endpoint in ordered], dtype=float
        )
        rocof = np.asarray([endpoint.rocof_hz_s for endpoint in ordered], dtype=float)
        desired_node_action = -(
            self.frequency_gain * (frequency - np.mean(frequency))
            + self.rocof_gain * (rocof - np.mean(rocof))
        )
        edge_action, _, rank, _ = np.linalg.lstsq(
            active_power_incidence(), desired_node_action, rcond=None
        )
        if rank != len(ACTION_EDGES) or not np.allclose(
            active_power_incidence() @ edge_action,
            desired_node_action,
            rtol=0.0,
            atol=1.0e-12,
        ):
            raise RuntimeError("joint node action is not represented by the action tree")
        return np.clip(edge_action, -1.0, 1.0)


@dataclass(frozen=True)
class GovernedEdgeAction:
    """Auditable result of the action seam shared by all matched policies."""

    normalized_edge_actions: np.ndarray
    requested_edge_flows_system_pu: np.ndarray
    executed_edge_flows_system_pu: np.ndarray
    node_residual_power_system_pu: np.ndarray
    base_projection: PowerProjection
    physical_projection: PowerProjection


def _finite_vector(values: Sequence[float], *, size: int, name: str) -> np.ndarray:
    vector = np.asarray(values, dtype=float)
    if vector.shape != (size,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must be a finite vector with shape ({size},)")
    return vector


class MatchedEdgeActionGovernor:
    """Apply one identical three-edge and physical limit path to every arm."""

    EDGE_PHASES = (((0, 1), (2, 3)), ((1, 2),))

    def __init__(
        self,
        *,
        physical_contract: EnergyFeasibleBESSContract,
        edge_flow_limit_system_pu: float,
        edge_slew_limit_system_pu: float,
    ) -> None:
        if physical_contract.device_count != 4:
            raise ValueError("matched edge execution requires four physical devices")
        self.physical_contract = physical_contract
        self.edge_flow_limit = float(edge_flow_limit_system_pu)
        self.edge_slew_limit = float(edge_slew_limit_system_pu)
        if not (
            math.isfinite(self.edge_flow_limit)
            and math.isfinite(self.edge_slew_limit)
            and self.edge_flow_limit > 0.0
            and 0.0 < self.edge_slew_limit <= 2.0 * self.edge_flow_limit
        ):
            raise ValueError("edge flow and slew limits must be finite and positive")

    def govern(
        self,
        *,
        normalized_edge_actions: Sequence[float],
        previous_edge_flows_system_pu: Sequence[float],
        base_power_request_system_pu: Sequence[float],
        previous_commanded_power_system_pu: Sequence[float],
        soc: Sequence[float],
        voltage_pu: Sequence[float],
        dt_seconds: float,
    ) -> GovernedEdgeAction:
        """Return executed edge and node commands through the physical projector."""

        action = _finite_vector(
            normalized_edge_actions,
            size=len(ACTION_EDGES),
            name="normalized edge actions",
        )
        previous_edge = _finite_vector(
            previous_edge_flows_system_pu,
            size=len(ACTION_EDGES),
            name="previous edge flows",
        )
        base_request = _finite_vector(
            base_power_request_system_pu,
            size=4,
            name="base power request",
        )
        previous_command = _finite_vector(
            previous_commanded_power_system_pu,
            size=4,
            name="previous commanded power",
        )
        current_soc = _finite_vector(soc, size=4, name="soc")
        voltage = _finite_vector(voltage_pu, size=4, name="voltage")

        common_projection_args = {
            "previous_power_system_pu": previous_command,
            "soc": current_soc,
            "voltage_pu": voltage,
            "dt_seconds": dt_seconds,
        }
        base_projection = self.physical_contract.project_power(
            requested_power_system_pu=base_request,
            **common_projection_args,
        )
        lower, upper = self.physical_contract.feasible_power_bounds(
            **common_projection_args
        )
        target_edge = np.clip(action, -1.0, 1.0) * self.edge_flow_limit
        requested_edge = np.clip(
            target_edge,
            previous_edge - self.edge_slew_limit,
            previous_edge + self.edge_slew_limit,
        )
        requested_by_edge = {
            edge: float(requested_edge[index])
            for index, edge in enumerate(ACTION_EDGES)
        }
        allocation = allocate_edge_flows_with_headroom(
            base_power_system_pu=base_projection.commanded_power_system_pu,
            requested_edge_flows_system_pu=requested_by_edge,
            edge_phases=self.EDGE_PHASES,
            lower_power_system_pu=lower,
            upper_power_system_pu=upper,
        )
        executed_edge = np.asarray(
            [allocation.allocated_edge_flows_system_pu[edge] for edge in ACTION_EDGES],
            dtype=float,
        )
        node_residual = active_power_incidence() @ executed_edge
        physical_projection = self.physical_contract.project_power(
            requested_power_system_pu=allocation.commanded_power_system_pu,
            **common_projection_args,
        )
        if not np.allclose(
            physical_projection.commanded_power_system_pu,
            allocation.commanded_power_system_pu,
            rtol=0.0,
            atol=1.0e-12,
        ):
            raise RuntimeError("endpoint allocation disagrees with physical projection")
        return GovernedEdgeAction(
            normalized_edge_actions=np.clip(action, -1.0, 1.0),
            requested_edge_flows_system_pu=requested_edge,
            executed_edge_flows_system_pu=executed_edge,
            node_residual_power_system_pu=node_residual,
            base_projection=base_projection,
            physical_projection=physical_projection,
        )
