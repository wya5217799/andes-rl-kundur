"""Edge-selective zero-sum increments around the local relative-RoCoF DAPI law.

Each undirected communication edge computes one antisymmetric active-power
flow from only its two endpoint filtered-RoCoF measurements.  Summing incident
flows at the devices preserves exact pre-projection zero sum without a global
mean or centralized action aggregator.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math

import numpy as np

from andes_rl_kundur.control.active_power import PowerProjection
from andes_rl_kundur.control.relative_rocof_residual import (
    DecentralizedRelativeRoCoFResidualExecution,
)


Edge = tuple[int, int]


def canonical_edge(source: int, target: int) -> Edge:
    """Return one stable undirected-edge coordinate."""

    left, right = int(source), int(target)
    if left == right:
        raise ValueError("an edge cannot connect a device to itself")
    return (left, right) if left < right else (right, left)


@dataclass(frozen=True)
class LocalEdgeRoCoFChannel:
    """One neighbour-to-neighbour antisymmetric residual channel."""

    edge: Edge
    gain_system_pu_s_per_hz: float
    graph_degree: int

    def flow_system_pu(self, filtered_rocof_hz_s: np.ndarray) -> float:
        source, target = self.edge
        return float(
            -self.gain_system_pu_s_per_hz
            * (filtered_rocof_hz_s[source] - filtered_rocof_hz_s[target])
            / self.graph_degree
        )


class DecentralizedEdgeSelectiveRelativeRoCoFExecution:
    """Explicit local DAPI agents plus independently gated edge increments."""

    architecture = "explicit_local_dapi_with_edge_selective_relative_rocof"

    def __init__(
        self,
        *,
        adjacency: Mapping[int, Sequence[int]],
        device_count: int,
        nominal_frequency_hz: float,
        kp_system_pu_per_hz_per_device: float,
        ki_system_pu_per_hz_s_per_device: float,
        sync_gain_system_pu_per_hz: float,
        consensus_gain_per_s: float,
        rocof_filter_time_constant_s: float,
        relative_rocof_gain_system_pu_s_per_hz: float,
        extra_edge_gains_system_pu_s_per_hz: Mapping[Edge, float],
    ) -> None:
        self.base = DecentralizedRelativeRoCoFResidualExecution(
            adjacency=adjacency,
            device_count=device_count,
            nominal_frequency_hz=nominal_frequency_hz,
            kp_system_pu_per_hz_per_device=kp_system_pu_per_hz_per_device,
            ki_system_pu_per_hz_s_per_device=ki_system_pu_per_hz_s_per_device,
            sync_gain_system_pu_per_hz=sync_gain_system_pu_per_hz,
            consensus_gain_per_s=consensus_gain_per_s,
            rocof_filter_time_constant_s=rocof_filter_time_constant_s,
            relative_rocof_gain_system_pu_s_per_hz=(
                relative_rocof_gain_system_pu_s_per_hz
            ),
        )
        self.device_count = int(device_count)
        self.adjacency = dict(self.base.adjacency)
        degrees = {len(neighbours) for neighbours in self.adjacency.values()}
        if len(degrees) != 1:
            raise ValueError("edge increments require the regular base graph")
        self.graph_degree = next(iter(degrees))
        graph_edges = {
            canonical_edge(index, neighbour)
            for index, neighbours in self.adjacency.items()
            for neighbour in neighbours
        }
        provided: dict[Edge, float] = {}
        for edge, raw_gain in extra_edge_gains_system_pu_s_per_hz.items():
            normalized = canonical_edge(*edge)
            gain = float(raw_gain)
            if normalized not in graph_edges:
                raise ValueError(f"extra residual edge is not in the graph: {normalized}")
            if normalized in provided:
                raise ValueError(f"duplicate undirected edge gain: {normalized}")
            if not math.isfinite(gain) or gain < 0.0:
                raise ValueError("extra edge gain must be finite and non-negative")
            provided[normalized] = gain
        self.edge_channels = tuple(
            LocalEdgeRoCoFChannel(
                edge=edge,
                gain_system_pu_s_per_hz=provided.get(edge, 0.0),
                graph_degree=self.graph_degree,
            )
            for edge in sorted(graph_edges)
        )
        self.reset()

    @property
    def agents(self):
        """Expose the four independent base-agent objects for audit."""

        return self.base.agents

    def reset(self) -> None:
        self.base.reset()
        self.last_base_requests_system_pu = np.zeros(self.device_count, dtype=float)
        self.last_residual_requests_system_pu = np.zeros(self.device_count, dtype=float)
        self.last_extra_requests_system_pu = np.zeros(self.device_count, dtype=float)
        self.last_filtered_rocof_hz_s = np.zeros(self.device_count, dtype=float)
        self.last_extra_edge_flows_system_pu = {
            channel.edge: 0.0 for channel in self.edge_channels
        }

    def act(
        self,
        *,
        frequencies_hz: list[float] | np.ndarray,
        dt_seconds: float,
        previous_projection: PowerProjection | None = None,
    ) -> np.ndarray:
        base_request = self.base.act(
            frequencies_hz=frequencies_hz,
            dt_seconds=dt_seconds,
            previous_projection=previous_projection,
        )
        filtered = self.base.last_filtered_rocof_hz_s.copy()
        extra = np.zeros(self.device_count, dtype=float)
        flows: dict[Edge, float] = {}
        for channel in self.edge_channels:
            source, target = channel.edge
            flow = channel.flow_system_pu(filtered)
            extra[source] += flow
            extra[target] -= flow
            flows[channel.edge] = flow
        if not math.isclose(float(np.sum(extra)), 0.0, rel_tol=0.0, abs_tol=1e-15):
            raise RuntimeError("edge-local increment violated its zero-sum contract")

        self.last_base_requests_system_pu = (
            self.base.last_base_requests_system_pu.copy()
        )
        self.last_residual_requests_system_pu = (
            self.base.last_residual_requests_system_pu.copy()
        )
        self.last_extra_requests_system_pu = extra
        self.last_filtered_rocof_hz_s = filtered
        self.last_extra_edge_flows_system_pu = flows
        return base_request + extra
