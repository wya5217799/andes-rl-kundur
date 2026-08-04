"""Explicit local-agent execution of the R294 DAPI control law."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from andes_rl_kundur.control.active_power import PowerProjection
from andes_rl_kundur.control.coupling_aware_power import row_normalized_laplacian


@dataclass(frozen=True)
class LocalDAPIObservation:
    """Exactly the runtime values delivered to one local DAPI agent."""

    own_frequency_hz: float
    neighbour_frequencies_hz: tuple[float, ...]
    neighbour_integrals_system_pu: tuple[float, ...]
    previous_requested_power_system_pu: float | None
    previous_commanded_power_system_pu: float | None


class LocalDAPIAgent:
    """One independently stateful DAPI agent with scalar local output."""

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
    ) -> None:
        self.agent_id = int(agent_id)
        self.neighbour_ids = tuple(int(item) for item in neighbour_ids)
        if not self.neighbour_ids:
            raise ValueError("a local DAPI agent requires at least one neighbour")
        self.nominal_frequency_hz = float(nominal_frequency_hz)
        self.kp = float(kp_system_pu_per_hz)
        self.ki = float(ki_system_pu_per_hz_s)
        self.sync_gain = float(sync_gain_system_pu_per_hz)
        self.consensus_gain = float(consensus_gain_per_s)
        if min(self.kp, self.ki, self.sync_gain, self.consensus_gain) < 0.0:
            raise ValueError("controller gains must be non-negative")
        self.reset()

    def reset(self) -> None:
        self.integral_power_system_pu = 0.0

    def propose(
        self,
        observation: LocalDAPIObservation,
        *,
        dt_seconds: float,
    ) -> tuple[float, float]:
        """Return next local integral and one scalar power request."""
        if not np.isfinite(dt_seconds) or dt_seconds <= 0.0:
            raise ValueError("dt_seconds must be finite and positive")
        neighbour_frequency = np.asarray(
            observation.neighbour_frequencies_hz,
            dtype=float,
        )
        neighbour_integral = np.asarray(
            observation.neighbour_integrals_system_pu,
            dtype=float,
        )
        if (
            neighbour_frequency.shape != (len(self.neighbour_ids),)
            or neighbour_integral.shape != (len(self.neighbour_ids),)
            or not np.all(np.isfinite(neighbour_frequency))
            or not np.all(np.isfinite(neighbour_integral))
            or not np.isfinite(observation.own_frequency_hz)
        ):
            raise ValueError("local observation does not match the neighbour contract")

        error = self.nominal_frequency_hz - observation.own_frequency_hz
        integral_disagreement = self.integral_power_system_pu - float(
            np.mean(neighbour_integral)
        )
        derivative = self.ki * error - self.consensus_gain * integral_disagreement
        if (
            observation.previous_requested_power_system_pu is not None
            and observation.previous_commanded_power_system_pu is not None
        ):
            saturated = not np.isclose(
                observation.previous_requested_power_system_pu,
                observation.previous_commanded_power_system_pu,
                rtol=0.0,
                atol=1e-12,
            )
            windup = (
                saturated
                and derivative * observation.previous_requested_power_system_pu > 0.0
            )
            if windup:
                derivative = 0.0

        next_integral = self.integral_power_system_pu + derivative * dt_seconds
        frequency_disagreement = observation.own_frequency_hz - float(
            np.mean(neighbour_frequency)
        )
        request = (
            self.kp * error
            + next_integral
            - self.sync_gain * frequency_disagreement
        )
        return float(next_integral), float(request)

    def commit(self, next_integral_power_system_pu: float) -> None:
        if not np.isfinite(next_integral_power_system_pu):
            raise ValueError("next local integral must be finite")
        self.integral_power_system_pu = float(next_integral_power_system_pu)


class DecentralizedDAPIExecution:
    """Single-process simulator harness for four explicit local agents.

    The harness only routes local measurements and neighbour messages.  The
    controller calculation and state live in each ``LocalDAPIAgent``; there is
    no action aggregation or global-frequency statistic.
    """

    architecture = "explicit_local_agents_neighbour_messages_independent_actions"

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
    ) -> None:
        self.device_count = int(device_count)
        row_normalized_laplacian(adjacency, device_count=self.device_count)
        self.adjacency = {
            index: tuple(int(item) for item in adjacency[index])
            for index in range(self.device_count)
        }
        self.agents = tuple(
            LocalDAPIAgent(
                agent_id=index,
                neighbour_ids=self.adjacency[index],
                nominal_frequency_hz=nominal_frequency_hz,
                kp_system_pu_per_hz=kp_system_pu_per_hz_per_device,
                ki_system_pu_per_hz_s=ki_system_pu_per_hz_s_per_device,
                sync_gain_system_pu_per_hz=sync_gain_system_pu_per_hz,
                consensus_gain_per_s=consensus_gain_per_s,
            )
            for index in range(self.device_count)
        )

    def reset(self) -> None:
        for agent in self.agents:
            agent.reset()

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
            proposals.append(agent.propose(observation, dt_seconds=dt_seconds))
        for agent, (next_integral, _) in zip(self.agents, proposals, strict=True):
            agent.commit(next_integral)
        return np.asarray([request for _, request in proposals], dtype=float)
