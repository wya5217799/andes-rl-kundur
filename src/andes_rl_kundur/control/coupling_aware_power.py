"""Coupling-aware active-power controllers for R294 development.

The two vector controllers deliberately share the same physical gains and
independent per-device active-power interface.  They differ only in the
declared information/coordination law: the centralized controller uses the
global mean projector, while DAPI uses a row-normalized neighbour Laplacian.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

from andes_rl_kundur.control.active_power import PowerProjection


def row_normalized_laplacian(
    adjacency: Mapping[int, Sequence[int]],
    *,
    device_count: int,
) -> np.ndarray:
    """Return ``I-D^-1 A`` after validating an undirected connected graph."""
    if device_count < 2:
        raise ValueError("device_count must be at least two")
    expected = set(range(device_count))
    if set(adjacency) != expected:
        raise ValueError("adjacency keys must equal range(device_count)")
    graph = {index: tuple(int(item) for item in adjacency[index]) for index in expected}
    for index, neighbours in graph.items():
        if not neighbours:
            raise ValueError("every device must have at least one neighbour")
        if len(set(neighbours)) != len(neighbours):
            raise ValueError("neighbour lists must not contain duplicates")
        if index in neighbours or any(item not in expected for item in neighbours):
            raise ValueError("adjacency contains a self-loop or unknown device")
        if any(index not in graph[item] for item in neighbours):
            raise ValueError("adjacency must be undirected")

    reached = {0}
    frontier = [0]
    while frontier:
        node = frontier.pop()
        for neighbour in graph[node]:
            if neighbour not in reached:
                reached.add(neighbour)
                frontier.append(neighbour)
    if reached != expected:
        raise ValueError("adjacency must be connected")

    laplacian = np.eye(device_count, dtype=float)
    for index, neighbours in graph.items():
        weight = 1.0 / len(neighbours)
        for neighbour in neighbours:
            laplacian[index, neighbour] = -weight
    return laplacian


def _frequency_vector(
    frequencies_hz: list[float] | np.ndarray,
    *,
    device_count: int,
) -> np.ndarray:
    values = np.asarray(frequencies_hz, dtype=float)
    if values.shape != (device_count,) or not np.all(np.isfinite(values)):
        raise ValueError("frequencies_hz must be a finite device vector")
    return values


def _saturation_mask(previous_projection: PowerProjection | None) -> np.ndarray | None:
    if previous_projection is None:
        return None
    requested = np.asarray(previous_projection.requested_power_system_pu, dtype=float)
    commanded = np.asarray(previous_projection.commanded_power_system_pu, dtype=float)
    if requested.shape != commanded.shape:
        raise ValueError("previous projection request/command shapes differ")
    return ~np.isclose(requested, commanded, rtol=0.0, atol=1e-12)


class CentralizedCouplingAwarePI:
    """Joint-observation vector PI with explicit common/differential action."""

    architecture = "centralized_joint_observation_vector_action"

    def __init__(
        self,
        *,
        device_count: int,
        nominal_frequency_hz: float,
        kp_system_pu_per_hz_per_device: float,
        ki_system_pu_per_hz_s_per_device: float,
        sync_gain_system_pu_per_hz: float,
    ) -> None:
        self.device_count = int(device_count)
        self.nominal_frequency_hz = float(nominal_frequency_hz)
        self.kp = float(kp_system_pu_per_hz_per_device)
        self.ki = float(ki_system_pu_per_hz_s_per_device)
        self.sync_gain = float(sync_gain_system_pu_per_hz)
        if self.device_count < 2 or min(self.kp, self.ki, self.sync_gain) < 0.0:
            raise ValueError("device_count and controller gains must be non-negative")
        self.reset()

    def reset(self) -> None:
        self._common_integral_power_system_pu = 0.0

    def act(
        self,
        *,
        frequencies_hz: list[float] | np.ndarray,
        dt_seconds: float,
        previous_projection: PowerProjection | None = None,
    ) -> np.ndarray:
        frequency = _frequency_vector(frequencies_hz, device_count=self.device_count)
        if not np.isfinite(dt_seconds) or dt_seconds <= 0.0:
            raise ValueError("dt_seconds must be finite and positive")
        error = self.nominal_frequency_hz - frequency
        common_error = float(np.mean(error))
        blocked = False
        saturation = _saturation_mask(previous_projection)
        if saturation is not None and np.any(saturation):
            previous_direction = float(
                np.mean(previous_projection.requested_power_system_pu)
            )
            blocked = common_error * previous_direction > 0.0
        if not blocked:
            self._common_integral_power_system_pu += self.ki * common_error * dt_seconds

        differential_frequency = frequency - float(np.mean(frequency))
        return (
            self.kp * error
            + self._common_integral_power_system_pu
            - self.sync_gain * differential_frequency
        )


class DistributedDAPIController:
    """Neighbour-only distributed averaging PI with independent local actions.

    For agent ``i`` the implemented law is

    ``eta_dot_i = ki*(f_nom-f_i) - kc*sum_j L_ij*eta_j`` and
    ``u_i = kp*(f_nom-f_i) + eta_i - ks*sum_j L_ij*f_j``.

    Each row of the Laplacian uses only the agent and its declared neighbours;
    there is no runtime joint-observation server or output aggregation.
    """

    architecture = "neighbour_distributed_independent_vector_action"

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
        self.nominal_frequency_hz = float(nominal_frequency_hz)
        self.kp = float(kp_system_pu_per_hz_per_device)
        self.ki = float(ki_system_pu_per_hz_s_per_device)
        self.sync_gain = float(sync_gain_system_pu_per_hz)
        self.consensus_gain = float(consensus_gain_per_s)
        if min(self.kp, self.ki, self.sync_gain, self.consensus_gain) < 0.0:
            raise ValueError("controller gains must be non-negative")
        self.laplacian = row_normalized_laplacian(
            adjacency,
            device_count=self.device_count,
        )
        self.reset()

    def reset(self) -> None:
        self._integral_power_system_pu = np.zeros(self.device_count, dtype=float)

    def act(
        self,
        *,
        frequencies_hz: list[float] | np.ndarray,
        dt_seconds: float,
        previous_projection: PowerProjection | None = None,
    ) -> np.ndarray:
        frequency = _frequency_vector(frequencies_hz, device_count=self.device_count)
        if not np.isfinite(dt_seconds) or dt_seconds <= 0.0:
            raise ValueError("dt_seconds must be finite and positive")
        error = self.nominal_frequency_hz - frequency
        derivative = (
            self.ki * error
            - self.consensus_gain * (self.laplacian @ self._integral_power_system_pu)
        )
        saturation = _saturation_mask(previous_projection)
        if saturation is not None:
            previous_request = np.asarray(
                previous_projection.requested_power_system_pu,
                dtype=float,
            )
            if previous_request.shape != (self.device_count,):
                raise ValueError("previous projection has the wrong device count")
            windup = saturation & (derivative * previous_request > 0.0)
            derivative = np.where(windup, 0.0, derivative)
        self._integral_power_system_pu += derivative * dt_seconds
        return (
            self.kp * error
            + self._integral_power_system_pu
            - self.sync_gain * (self.laplacian @ frequency)
        )
