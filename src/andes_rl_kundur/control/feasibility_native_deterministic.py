"""Feasibility-native deterministic controllers in normalized action space.

This module implements the R376 Gate B deterministic laws from
``paper/paralleled_vsg_marl/working/gate_b_deterministic_physical_contract.md``.
Every controller returns one scalar normalized action per VSG inside
``[-0.70, 0.70]``; the feasibility-native map converts it into the VSG's
current feasible power interval, and the outer energy-port projection must be
identity.  Nothing here writes power directly and nothing here is a learned
policy, reward, or scientific result.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

ACTION_CLIP = 0.70


def _frequency_vector(
    frequencies_hz: Sequence[float] | np.ndarray,
    *,
    device_count: int,
) -> np.ndarray:
    frequency = np.asarray(frequencies_hz, dtype=float)
    if (
        frequency.shape != (device_count,)
        or not np.all(np.isfinite(frequency))
    ):
        raise ValueError("frequencies_hz must be a finite device vector")
    return frequency


def _laplacian(
    adjacency: Mapping[int, Sequence[int]],
    *,
    device_count: int,
) -> np.ndarray:
    graph = {
        int(index): tuple(int(neighbour) for neighbour in neighbours)
        for index, neighbours in adjacency.items()
    }
    if set(graph) != set(range(device_count)):
        raise ValueError("adjacency must cover all devices")
    laplacian = np.zeros((device_count, device_count), dtype=float)
    for index, neighbours in graph.items():
        if (
            index in neighbours
            or len(set(neighbours)) != len(neighbours)
            or any(neighbour not in graph for neighbour in neighbours)
            or any(index not in graph[neighbour] for neighbour in neighbours)
        ):
            raise ValueError("adjacency must be simple, undirected, and closed")
        laplacian[index, index] = len(neighbours)
        for neighbour in neighbours:
            laplacian[index, neighbour] = -1.0
    return laplacian


class FeasibilityNativeLocalController:
    """Four independent normalized PI laws with local information only."""

    architecture = "local_feasibility_native"

    def __init__(
        self,
        *,
        device_count: int,
        nominal_frequency_hz: float,
        kp_n_per_hz: float,
        ki_n_per_hz_s: float,
        action_clip: float = ACTION_CLIP,
    ) -> None:
        self.device_count = int(device_count)
        self.nominal_frequency_hz = float(nominal_frequency_hz)
        self.kp_n = float(kp_n_per_hz)
        self.ki_n = float(ki_n_per_hz_s)
        self.action_clip = float(action_clip)
        if self.device_count < 2 or min(self.kp_n, self.ki_n) < 0.0:
            raise ValueError("device count and PI gains must be non-negative")
        if not 0.0 < self.action_clip <= 1.0:
            raise ValueError("action_clip must lie inside (0, 1]")
        self.reset()

    def reset(self) -> None:
        self._integral = np.zeros(self.device_count, dtype=float)
        self._was_clipped = np.zeros(self.device_count, dtype=bool)

    def act(
        self,
        *,
        frequencies_hz: Sequence[float] | np.ndarray,
        dt_seconds: float,
    ) -> np.ndarray:
        frequency = _frequency_vector(
            frequencies_hz,
            device_count=self.device_count,
        )
        dt = float(dt_seconds)
        if not np.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt_seconds must be finite and positive")
        error = self.nominal_frequency_hz - frequency
        frozen = self._was_clipped
        self._integral = self._integral + np.where(
            frozen, 0.0, self.ki_n * error * dt
        )
        raw = self.kp_n * error + self._integral
        action = np.clip(raw, -self.action_clip, self.action_clip)
        self._was_clipped = ~np.isclose(raw, action, rtol=0.0, atol=1.0e-12)
        return action.copy()


class FeasibilityNativeDistributedController:
    """Normalized PI with dynamic-average common channel and Laplacian sync.

    The common channel runs a dynamic-average consensus estimator over the
    frozen one-hop ring; the sync channel is the zero-sum Laplacian term.
    Both enter the same normalized action before the feasibility-native map.
    """

    architecture = "distributed_feasibility_native"

    def __init__(
        self,
        *,
        adjacency: Mapping[int, Sequence[int]],
        device_count: int,
        nominal_frequency_hz: float,
        kp_n_per_hz: float,
        ki_n_per_hz_s: float,
        ks_n_per_hz: float,
        kc_n_per_s: float,
        action_clip: float = ACTION_CLIP,
    ) -> None:
        self.device_count = int(device_count)
        self.nominal_frequency_hz = float(nominal_frequency_hz)
        self.kp_n = float(kp_n_per_hz)
        self.ki_n = float(ki_n_per_hz_s)
        self.ks_n = float(ks_n_per_hz)
        self.kc_n = float(kc_n_per_s)
        self.action_clip = float(action_clip)
        if min(self.kp_n, self.ki_n, self.ks_n, self.kc_n) < 0.0:
            raise ValueError("controller gains must be non-negative")
        if not 0.0 < self.action_clip <= 1.0:
            raise ValueError("action_clip must lie inside (0, 1]")
        self.laplacian = _laplacian(
            adjacency,
            device_count=self.device_count,
        )
        self.reset()

    def reset(self) -> None:
        self._common_estimate: np.ndarray | None = None
        self._previous_error: np.ndarray | None = None
        self._integral = np.zeros(self.device_count, dtype=float)
        self._was_clipped = np.zeros(self.device_count, dtype=bool)

    def act(
        self,
        *,
        frequencies_hz: Sequence[float] | np.ndarray,
        dt_seconds: float,
    ) -> np.ndarray:
        frequency = _frequency_vector(
            frequencies_hz,
            device_count=self.device_count,
        )
        dt = float(dt_seconds)
        if not np.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt_seconds must be finite and positive")
        error = self.nominal_frequency_hz - frequency
        if self._common_estimate is None:
            estimate = error.copy()
        else:
            assert self._previous_error is not None
            estimate = (
                self._common_estimate
                + error
                - self._previous_error
                - self.kc_n
                * dt
                * (self.laplacian @ self._common_estimate)
            )
        frozen = self._was_clipped
        self._integral = self._integral + np.where(
            frozen, 0.0, self.ki_n * estimate * dt
        )
        common = self.kp_n * estimate + self._integral
        sync = -self.ks_n * (self.laplacian @ frequency)
        raw = common + sync
        action = np.clip(raw, -self.action_clip, self.action_clip)
        self._was_clipped = ~np.isclose(raw, action, rtol=0.0, atol=1.0e-12)
        self._common_estimate = estimate
        self._previous_error = error.copy()
        return action.copy()


def candidate_arm_ids() -> list[str]:
    """Return the frozen R376 distributed candidate ids."""
    return [
        "distributed_feasibility_native_ks0p5_kc0p5",
        "distributed_feasibility_native_ks0p5_kc1",
        "distributed_feasibility_native_ks1_kc0p5",
        "distributed_feasibility_native_ks1_kc1",
    ]


class HPDampingDistributedController:
    """High-pass filtered mutual damping with dynamic-average common channel.

    The successor Gate B-2 law: neighbour messages enter only the differential
    channel through a first-order high-pass state on the Laplacian frequency
    difference sum, so sustained action-domain probes are attenuated while
    oscillatory differential motion is damped.  The common channel keeps the
    R376 dynamic-average estimator.
    """

    architecture = "distributed_hp_damping"

    def __init__(
        self,
        *,
        adjacency: Mapping[int, Sequence[int]],
        device_count: int,
        nominal_frequency_hz: float,
        kp_n_per_hz: float,
        ki_n_per_hz_s: float,
        ks_n_per_hz: float,
        kc_n_per_s: float,
        highpass_alpha: float,
        action_clip: float = ACTION_CLIP,
    ) -> None:
        self.device_count = int(device_count)
        self.nominal_frequency_hz = float(nominal_frequency_hz)
        self.kp_n = float(kp_n_per_hz)
        self.ki_n = float(ki_n_per_hz_s)
        self.ks_n = float(ks_n_per_hz)
        self.kc_n = float(kc_n_per_s)
        self.alpha = float(highpass_alpha)
        self.action_clip = float(action_clip)
        if min(self.kp_n, self.ki_n, self.ks_n, self.kc_n) < 0.0:
            raise ValueError("controller gains must be non-negative")
        if not 0.0 < self.alpha < 1.0:
            raise ValueError("highpass_alpha must lie inside (0, 1)")
        if not 0.0 < self.action_clip <= 1.0:
            raise ValueError("action_clip must lie inside (0, 1]")
        self.laplacian = _laplacian(
            adjacency,
            device_count=self.device_count,
        )
        self.reset()

    def reset(self) -> None:
        self._common_estimate: np.ndarray | None = None
        self._previous_error: np.ndarray | None = None
        self._highpass_state = np.zeros(self.device_count, dtype=float)
        self._previous_message = np.zeros(self.device_count, dtype=float)
        self._integral = np.zeros(self.device_count, dtype=float)
        self._was_clipped = np.zeros(self.device_count, dtype=bool)

    def act(
        self,
        *,
        frequencies_hz: Sequence[float] | np.ndarray,
        dt_seconds: float,
    ) -> np.ndarray:
        frequency = _frequency_vector(
            frequencies_hz,
            device_count=self.device_count,
        )
        dt = float(dt_seconds)
        if not np.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt_seconds must be finite and positive")
        error = self.nominal_frequency_hz - frequency
        if self._common_estimate is None:
            estimate = error.copy()
        else:
            assert self._previous_error is not None
            estimate = (
                self._common_estimate
                + error
                - self._previous_error
                - self.kc_n
                * dt
                * (self.laplacian @ self._common_estimate)
            )
        frozen = self._was_clipped
        self._integral = self._integral + np.where(
            frozen, 0.0, self.ki_n * estimate * dt
        )
        common = self.kp_n * estimate + self._integral
        message = self.laplacian @ frequency
        highpass = self.alpha * (
            self._highpass_state + message - self._previous_message
        )
        sync = -self.ks_n * highpass
        raw = common + sync
        action = np.clip(raw, -self.action_clip, self.action_clip)
        self._was_clipped = ~np.isclose(raw, action, rtol=0.0, atol=1.0e-12)
        self._common_estimate = estimate
        self._previous_error = error.copy()
        self._highpass_state = highpass
        self._previous_message = message
        return action.copy()


def hp_damping_candidate_arm_ids() -> list[str]:
    """Return the frozen Gate B-2 distributed candidate ids (alpha fixed)."""
    return [
        f"distributed_hp_damping_ks{sync_gain:g}_kc{consensus_gain:g}_alpha0p6"
        .replace(".", "p")
        for sync_gain in (0.5, 1.0)
        for consensus_gain in (0.5, 1.0)
    ]


def low_hp_damping_candidate_arm_ids() -> list[str]:
    """Return the frozen Gate B-3 distributed candidate ids (alpha 0.90)."""
    return [
        f"distributed_lowhp_damping_ks{sync_gain:g}_kc{consensus_gain:g}_alpha0p9"
        .replace(".", "p")
        for sync_gain in (0.5, 1.0)
        for consensus_gain in (0.5, 1.0)
    ]
