"""Strictly local zero-sum relative-RoCoF residual for explicit DAPI agents."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math

import numpy as np

from andes_rl_kundur.control.active_power import PowerProjection
from andes_rl_kundur.control.coupling_aware_power import row_normalized_laplacian
from andes_rl_kundur.control.decentralized_dapi import (
    LocalDAPIAgent,
    LocalDAPIObservation,
)


@dataclass(frozen=True)
class LocalRelativeRoCoFProposal:
    """One local agent's simultaneous state and action proposal."""

    next_integral_system_pu: float
    next_filtered_rocof_hz_s: float
    current_frequency_hz: float
    base_request_system_pu: float
    residual_request_system_pu: float

    @property
    def total_request_system_pu(self) -> float:
        return self.base_request_system_pu + self.residual_request_system_pu


class LocalRelativeRoCoFAgent:
    """One independent DAPI agent with a locally filtered RoCoF state."""

    def __init__(
        self,
        *,
        agent_id: int,
        neighbour_ids: Sequence[int],
        nominal_frequency_hz: float,
        kp_system_pu_per_hz: float,
        ki_system_pu_per_hz_s: float,
        sync_gain_system_pu_per_hz: float,
        consensus_gain_per_s: float,
        rocof_filter_time_constant_s: float,
        relative_rocof_gain_system_pu_s_per_hz: float,
    ) -> None:
        self.agent_id = int(agent_id)
        self.neighbour_ids = tuple(int(item) for item in neighbour_ids)
        self.base = LocalDAPIAgent(
            agent_id=self.agent_id,
            neighbour_ids=self.neighbour_ids,
            nominal_frequency_hz=nominal_frequency_hz,
            kp_system_pu_per_hz=kp_system_pu_per_hz,
            ki_system_pu_per_hz_s=ki_system_pu_per_hz_s,
            sync_gain_system_pu_per_hz=sync_gain_system_pu_per_hz,
            consensus_gain_per_s=consensus_gain_per_s,
        )
        self.filter_time_constant = float(rocof_filter_time_constant_s)
        self.residual_gain = float(relative_rocof_gain_system_pu_s_per_hz)
        if not np.isfinite(self.filter_time_constant) or self.filter_time_constant <= 0.0:
            raise ValueError("RoCoF filter time constant must be finite and positive")
        if not np.isfinite(self.residual_gain) or self.residual_gain < 0.0:
            raise ValueError("relative-RoCoF gain must be finite and non-negative")
        self.reset()

    @property
    def integral_power_system_pu(self) -> float:
        return self.base.integral_power_system_pu

    def reset(self) -> None:
        self.base.reset()
        self.previous_frequency_hz: float | None = None
        self.filtered_rocof_hz_s = 0.0

    def propose_filtered_rocof(
        self,
        own_frequency_hz: float,
        *,
        dt_seconds: float,
    ) -> float:
        if not np.isfinite(own_frequency_hz):
            raise ValueError("own frequency must be finite")
        if not np.isfinite(dt_seconds) or dt_seconds <= 0.0:
            raise ValueError("dt_seconds must be finite and positive")
        raw_rocof = (
            0.0
            if self.previous_frequency_hz is None
            else (float(own_frequency_hz) - self.previous_frequency_hz) / dt_seconds
        )
        alpha = math.exp(-dt_seconds / self.filter_time_constant)
        return float(alpha * self.filtered_rocof_hz_s + (1.0 - alpha) * raw_rocof)

    def propose(
        self,
        observation: LocalDAPIObservation,
        *,
        next_filtered_rocof_hz_s: float,
        neighbour_filtered_rocof_hz_s: Sequence[float],
        dt_seconds: float,
    ) -> LocalRelativeRoCoFProposal:
        neighbours = np.asarray(neighbour_filtered_rocof_hz_s, dtype=float)
        if neighbours.shape != (len(self.neighbour_ids),) or not np.all(
            np.isfinite(neighbours)
        ):
            raise ValueError("neighbour filtered RoCoF does not match local contract")
        if not np.isfinite(next_filtered_rocof_hz_s):
            raise ValueError("next filtered RoCoF must be finite")
        next_integral, base_request = self.base.propose(
            observation,
            dt_seconds=dt_seconds,
        )
        relative_rocof = float(next_filtered_rocof_hz_s - np.mean(neighbours))
        residual = -self.residual_gain * relative_rocof
        return LocalRelativeRoCoFProposal(
            next_integral_system_pu=next_integral,
            next_filtered_rocof_hz_s=float(next_filtered_rocof_hz_s),
            current_frequency_hz=float(observation.own_frequency_hz),
            base_request_system_pu=base_request,
            residual_request_system_pu=float(residual),
        )

    def commit(self, proposal: LocalRelativeRoCoFProposal) -> None:
        self.base.commit(proposal.next_integral_system_pu)
        self.filtered_rocof_hz_s = proposal.next_filtered_rocof_hz_s
        self.previous_frequency_hz = proposal.current_frequency_hz


class DecentralizedRelativeRoCoFResidualExecution:
    """Four explicit local agents with a strictly zero-sum edge residual.

    The required graph is undirected and regular. Under that contract the
    row-normalized Laplacian is symmetric, so the pre-projection residual sums
    to zero. The simulator harness only routes neighbour messages.
    """

    architecture = "explicit_local_dapi_with_zero_sum_relative_rocof_residual"

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
    ) -> None:
        self.device_count = int(device_count)
        row_normalized_laplacian(adjacency, device_count=self.device_count)
        self.adjacency = {
            index: tuple(int(item) for item in adjacency[index])
            for index in range(self.device_count)
        }
        degrees = {len(neighbours) for neighbours in self.adjacency.values()}
        if len(degrees) != 1:
            raise ValueError("strict zero-sum residual requires a regular graph")
        for index, neighbours in self.adjacency.items():
            if index in neighbours:
                raise ValueError("communication graph cannot contain self edges")
            if any(index not in self.adjacency[neighbour] for neighbour in neighbours):
                raise ValueError("strict zero-sum residual requires an undirected graph")
        self.agents = tuple(
            LocalRelativeRoCoFAgent(
                agent_id=index,
                neighbour_ids=self.adjacency[index],
                nominal_frequency_hz=nominal_frequency_hz,
                kp_system_pu_per_hz=kp_system_pu_per_hz_per_device,
                ki_system_pu_per_hz_s=ki_system_pu_per_hz_s_per_device,
                sync_gain_system_pu_per_hz=sync_gain_system_pu_per_hz,
                consensus_gain_per_s=consensus_gain_per_s,
                rocof_filter_time_constant_s=rocof_filter_time_constant_s,
                relative_rocof_gain_system_pu_s_per_hz=(
                    relative_rocof_gain_system_pu_s_per_hz
                ),
            )
            for index in range(self.device_count)
        )
        self.reset()

    def reset(self) -> None:
        for agent in self.agents:
            agent.reset()
        self.last_base_requests_system_pu = np.zeros(self.device_count, dtype=float)
        self.last_residual_requests_system_pu = np.zeros(self.device_count, dtype=float)
        self.last_filtered_rocof_hz_s = np.zeros(self.device_count, dtype=float)

    def act(
        self,
        *,
        frequencies_hz: list[float] | np.ndarray,
        dt_seconds: float,
        previous_projection: PowerProjection | None = None,
    ) -> np.ndarray:
        frequency = np.asarray(frequencies_hz, dtype=float)
        if frequency.shape != (self.device_count,) or not np.all(np.isfinite(frequency)):
            raise ValueError("frequencies_hz must be a finite device vector")
        previous_integrals = np.asarray(
            [agent.integral_power_system_pu for agent in self.agents],
            dtype=float,
        )
        next_filtered = np.asarray(
            [
                agent.propose_filtered_rocof(
                    float(frequency[agent.agent_id]),
                    dt_seconds=dt_seconds,
                )
                for agent in self.agents
            ],
            dtype=float,
        )
        if previous_projection is None:
            previous_requested = [None] * self.device_count
            previous_commanded = [None] * self.device_count
        else:
            requested = np.asarray(
                previous_projection.requested_power_system_pu,
                dtype=float,
            )
            commanded = np.asarray(
                previous_projection.commanded_power_system_pu,
                dtype=float,
            )
            if requested.shape != (self.device_count,) or commanded.shape != (
                self.device_count,
            ):
                raise ValueError("previous projection has the wrong device count")
            previous_requested = requested.tolist()
            previous_commanded = commanded.tolist()

        proposals = []
        for agent in self.agents:
            neighbours = agent.neighbour_ids
            observation = LocalDAPIObservation(
                own_frequency_hz=float(frequency[agent.agent_id]),
                neighbour_frequencies_hz=tuple(
                    float(frequency[index]) for index in neighbours
                ),
                neighbour_integrals_system_pu=tuple(
                    float(previous_integrals[index]) for index in neighbours
                ),
                previous_requested_power_system_pu=previous_requested[agent.agent_id],
                previous_commanded_power_system_pu=previous_commanded[agent.agent_id],
            )
            proposals.append(
                agent.propose(
                    observation,
                    next_filtered_rocof_hz_s=float(next_filtered[agent.agent_id]),
                    neighbour_filtered_rocof_hz_s=tuple(
                        float(next_filtered[index]) for index in neighbours
                    ),
                    dt_seconds=dt_seconds,
                )
            )
        for agent, proposal in zip(self.agents, proposals, strict=True):
            agent.commit(proposal)

        self.last_base_requests_system_pu = np.asarray(
            [proposal.base_request_system_pu for proposal in proposals],
            dtype=float,
        )
        self.last_residual_requests_system_pu = np.asarray(
            [proposal.residual_request_system_pu for proposal in proposals],
            dtype=float,
        )
        self.last_filtered_rocof_hz_s = next_filtered
        return self.last_base_requests_system_pu + self.last_residual_requests_system_pu
