"""Distributed common/differential control on per-VSG power ports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from andes_rl_kundur.control.active_power import PowerProjection


@dataclass(frozen=True)
class CrossCoordinateAction:
    """One auditable four-port request before the energy projection."""

    requested_power_system_pu: np.ndarray
    common_request_system_pu: np.ndarray
    differential_request_system_pu: np.ndarray
    common_estimate_hz: np.ndarray


def symmetric_laplacian(
    adjacency: Mapping[int, Sequence[int]],
    *,
    device_count: int,
) -> np.ndarray:
    """Return an undirected connected combinatorial graph Laplacian."""

    if device_count < 2 or set(adjacency) != set(range(device_count)):
        raise ValueError("adjacency must cover at least two indexed devices")
    graph = {
        index: tuple(int(neighbour) for neighbour in adjacency[index])
        for index in range(device_count)
    }
    for index, neighbours in graph.items():
        if (
            not neighbours
            or len(set(neighbours)) != len(neighbours)
            or index in neighbours
            or any(neighbour not in graph for neighbour in neighbours)
            or any(index not in graph[neighbour] for neighbour in neighbours)
        ):
            raise ValueError("adjacency must be simple, undirected, and complete")
    reached = {0}
    frontier = [0]
    while frontier:
        node = frontier.pop()
        for neighbour in graph[node]:
            if neighbour not in reached:
                reached.add(neighbour)
                frontier.append(neighbour)
    if len(reached) != device_count:
        raise ValueError("adjacency must be connected")
    laplacian = np.zeros((device_count, device_count), dtype=float)
    for index, neighbours in graph.items():
        laplacian[index, index] = len(neighbours)
        for neighbour in neighbours:
            laplacian[index, neighbour] = -1.0
    return laplacian


def _antiwindup(
    derivative: np.ndarray,
    previous_projection: PowerProjection | None,
    *,
    device_count: int,
) -> np.ndarray:
    if previous_projection is None:
        return derivative
    requested = np.asarray(
        previous_projection.requested_power_system_pu,
        dtype=float,
    )
    commanded = np.asarray(
        previous_projection.commanded_power_system_pu,
        dtype=float,
    )
    if requested.shape != (device_count,) or commanded.shape != (device_count,):
        raise ValueError("previous projection has the wrong device count")
    saturated = ~np.isclose(requested, commanded, rtol=0.0, atol=1.0e-12)
    return np.where(saturated & (derivative * requested > 0.0), 0.0, derivative)


class LocalDiagonalPIController:
    """Four independent PI states with no neighbour or fleet statistic."""

    architecture = "independent_local_diagonal_pi"

    def __init__(
        self,
        *,
        device_count: int,
        nominal_frequency_hz: float,
        kp_system_pu_per_hz: float,
        ki_system_pu_per_hz_s: float,
    ) -> None:
        self.device_count = int(device_count)
        self.nominal_frequency_hz = float(nominal_frequency_hz)
        self.kp = float(kp_system_pu_per_hz)
        self.ki = float(ki_system_pu_per_hz_s)
        if self.device_count < 2 or min(self.kp, self.ki) < 0.0:
            raise ValueError("device count and PI gains must be non-negative")
        self.reset()

    def reset(self) -> None:
        self._integral_system_pu = np.zeros(self.device_count, dtype=float)

    def act(
        self,
        *,
        frequencies_hz: list[float] | np.ndarray,
        dt_seconds: float,
        previous_projection: PowerProjection | None = None,
    ) -> CrossCoordinateAction:
        frequency = np.asarray(frequencies_hz, dtype=float)
        dt = float(dt_seconds)
        if frequency.shape != (self.device_count,) or not np.all(np.isfinite(frequency)):
            raise ValueError("frequencies_hz must be a finite device vector")
        if not np.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt_seconds must be finite and positive")
        error = self.nominal_frequency_hz - frequency
        derivative = _antiwindup(
            self.ki * error,
            previous_projection,
            device_count=self.device_count,
        )
        self._integral_system_pu += derivative * dt
        request = self.kp * error + self._integral_system_pu
        return CrossCoordinateAction(
            requested_power_system_pu=request.copy(),
            common_request_system_pu=request.copy(),
            differential_request_system_pu=np.zeros(self.device_count, dtype=float),
            common_estimate_hz=error.copy(),
        )


class DistributedCrossCoordinateController:
    """Dynamic-average common channel plus zero-sum neighbour sync channel."""

    architecture = "distributed_common_estimate_zero_sum_differential"

    def __init__(
        self,
        *,
        adjacency: Mapping[int, Sequence[int]],
        device_count: int,
        nominal_frequency_hz: float,
        kp_system_pu_per_hz: float,
        ki_system_pu_per_hz_s: float,
        sync_gain_system_pu_per_hz: float,
        consensus_gain_per_s: float,
    ) -> None:
        self.device_count = int(device_count)
        self.nominal_frequency_hz = float(nominal_frequency_hz)
        self.kp = float(kp_system_pu_per_hz)
        self.ki = float(ki_system_pu_per_hz_s)
        self.sync_gain = float(sync_gain_system_pu_per_hz)
        self.consensus_gain = float(consensus_gain_per_s)
        if min(self.kp, self.ki, self.sync_gain, self.consensus_gain) < 0.0:
            raise ValueError("controller gains must be non-negative")
        self.laplacian = symmetric_laplacian(
            adjacency,
            device_count=self.device_count,
        )
        self.reset()

    def reset(self) -> None:
        self._common_estimate_hz: np.ndarray | None = None
        self._previous_error_hz: np.ndarray | None = None
        self._common_integral_system_pu = np.zeros(self.device_count, dtype=float)

    def act(
        self,
        *,
        frequencies_hz: list[float] | np.ndarray,
        dt_seconds: float,
        previous_projection: PowerProjection | None = None,
    ) -> CrossCoordinateAction:
        frequency = np.asarray(frequencies_hz, dtype=float)
        dt = float(dt_seconds)
        if frequency.shape != (self.device_count,) or not np.all(np.isfinite(frequency)):
            raise ValueError("frequencies_hz must be a finite device vector")
        if not np.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt_seconds must be finite and positive")
        error = self.nominal_frequency_hz - frequency
        if self._common_estimate_hz is None:
            estimate = error.copy()
        else:
            assert self._previous_error_hz is not None
            estimate = (
                self._common_estimate_hz
                + error
                - self._previous_error_hz
                - self.consensus_gain
                * dt
                * (self.laplacian @ self._common_estimate_hz)
            )
        derivative = _antiwindup(
            self.ki * estimate,
            previous_projection,
            device_count=self.device_count,
        )
        self._common_integral_system_pu += derivative * dt
        common = self.kp * estimate + self._common_integral_system_pu
        differential = -self.sync_gain * (self.laplacian @ frequency)
        self._common_estimate_hz = estimate
        self._previous_error_hz = error.copy()
        return CrossCoordinateAction(
            requested_power_system_pu=(common + differential).copy(),
            common_request_system_pu=common.copy(),
            differential_request_system_pu=differential.copy(),
            common_estimate_hz=estimate.copy(),
        )
