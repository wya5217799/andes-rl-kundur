"""Unit-valid per-VSG inertia/damping controls for the fixed-title line.

The protected V4 environment exposes frequency and RoCoF observations on its
legacy 50-Hz controller scale even though the ANDES plant is physically 60 Hz.
This module provides the explicit boundary used by every new-line controller:
convert those slots once, then keep deterministic and learned policies on the
same four-row observation and two-action-per-device interface.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np


DEVICE_COUNT = 4
OBSERVATION_DIM = 7
LEGACY_CONTROL_NOMINAL_FREQUENCY_HZ = 50.0
PHYSICAL_NOMINAL_FREQUENCY_HZ = 60.0
FREQUENCY_OBSERVATION_SLOTS = (1, 2, 3, 4, 5, 6)
GAIN_GRID = (0.5, 1.0, 2.0)


@dataclass(frozen=True)
class LocalNeighbourMDContract:
    """One candidate in the frozen object-matched deterministic family."""

    inertia_gain: float
    damping_gain: float
    action_slew_limit: float = 0.25
    action_coordinates: tuple[str, str] = (
        "normalized_delta_M",
        "normalized_delta_D",
    )

    def __post_init__(self) -> None:
        if not np.isfinite(self.inertia_gain) or self.inertia_gain <= 0.0:
            raise ValueError("inertia_gain must be finite and positive")
        if not np.isfinite(self.damping_gain) or self.damping_gain <= 0.0:
            raise ValueError("damping_gain must be finite and positive")
        if not 0.0 < self.action_slew_limit <= 2.0:
            raise ValueError("action_slew_limit must lie in (0, 2]")

    @property
    def name(self) -> str:
        inertia = f"{self.inertia_gain:g}".replace(".", "p")
        damping = f"{self.damping_gain:g}".replace(".", "p")
        return f"local_neighbour_md_km{inertia}_kd{damping}"


def local_neighbour_md_candidates() -> tuple[LocalNeighbourMDContract, ...]:
    """Return the prospectively frozen three-by-three deterministic grid."""

    return tuple(
        LocalNeighbourMDContract(inertia_gain=inertia, damping_gain=damping)
        for inertia in GAIN_GRID
        for damping in GAIN_GRID
    )


class LocalMDActionProjector:
    """Elementwise bounds and slew for one VSG's normalized M/D action."""

    def __init__(self, *, action_slew_limit: float) -> None:
        limit = float(action_slew_limit)
        if not np.isfinite(limit) or not 0.0 < limit <= 2.0:
            raise ValueError("action_slew_limit must lie in (0, 2]")
        self.action_slew_limit = limit
        self.reset()

    def reset(self) -> None:
        self.previous_action = np.zeros(2, dtype=np.float32)

    def project(self, target_action: Sequence[float] | np.ndarray) -> np.ndarray:
        target = np.asarray(target_action, dtype=np.float32)
        if target.shape != (2,) or not np.all(np.isfinite(target)):
            raise ValueError("target action must be a finite vector with shape (2,)")
        # R402 slew-representation repair: compute the slew clip in float64 and
        # snap the stored float32 one ulp toward the previous action whenever
        # rounding would let the recorded delta exceed the exact slew bound.
        # The physical clip is unchanged; only the stored representation is
        # made conservative so the frozen <=0.25 recorded-slew guard holds.
        previous = self.previous_action
        slew64 = float(self.action_slew_limit)
        prev64 = previous.astype(np.float64)
        delta = np.clip(target.astype(np.float64) - prev64, -slew64, slew64)
        action64 = prev64 + delta
        action = np.clip(action64, -1.0, 1.0).astype(np.float32)
        overshoot = (action.astype(np.float64) - prev64) > slew64
        undershoot = (action.astype(np.float64) - prev64) < -slew64
        if np.any(overshoot):
            action[overshoot] = np.nextafter(
                action[overshoot], np.float32(-np.inf)
            )
        if np.any(undershoot):
            action[undershoot] = np.nextafter(
                action[undershoot], np.float32(np.inf)
            )
        action = np.clip(action, -1.0, 1.0).astype(np.float32)
        self.previous_action = action.copy()
        return action


class PerVSGMDActionProjector:
    """Reusable separable post-processing for four deterministic or learned actions."""

    architecture = "four_independent_rowwise_clip_and_slew_projectors"

    def __init__(self, *, action_slew_limit: float) -> None:
        self.projectors = tuple(
            LocalMDActionProjector(action_slew_limit=action_slew_limit)
            for _ in range(DEVICE_COUNT)
        )

    def reset(self) -> None:
        for projector in self.projectors:
            projector.reset()

    def project(self, target_actions: Sequence[Sequence[float]] | np.ndarray) -> np.ndarray:
        targets = np.asarray(target_actions, dtype=np.float32)
        if targets.shape != (DEVICE_COUNT, 2) or not np.all(np.isfinite(targets)):
            raise ValueError("target actions must be a finite matrix with shape (4, 2)")
        return np.stack(
            [self.projectors[actor].project(targets[actor]) for actor in range(DEVICE_COUNT)]
        ).astype(np.float32)


class LocalNeighbourMDAgent:
    """One stateful VSG controller that can see only one local observation row."""

    def __init__(self, *, agent_id: int, contract: LocalNeighbourMDContract) -> None:
        self.agent_id = int(agent_id)
        self.contract = contract
        self.action_projector = LocalMDActionProjector(
            action_slew_limit=contract.action_slew_limit
        )

    def reset(self) -> None:
        self.action_projector.reset()

    @property
    def previous_action(self) -> np.ndarray:
        return self.action_projector.previous_action.copy()

    def act(self, observation: Sequence[float] | np.ndarray) -> np.ndarray:
        row = np.asarray(observation, dtype=np.float32)
        if row.shape != (OBSERVATION_DIM,):
            raise ValueError("each local observation must have shape (7,)")
        if not np.all(np.isfinite(row)):
            raise ValueError("local observation must contain only finite values")

        own_frequency = float(row[1])
        own_rocof = float(row[2])
        neighbour_frequency = row[3:5].astype(np.float64)
        neighbour_rocof = row[5:7].astype(np.float64)
        own_severity = abs(own_frequency) + abs(own_rocof)
        neighbour_severity = float(
            np.mean(np.abs(neighbour_frequency) + np.abs(neighbour_rocof))
        )
        inertia_target = np.tanh(
            self.contract.inertia_gain * (own_severity - neighbour_severity)
        )
        damping_signal = (
            abs(own_frequency)
            + float(np.mean(np.abs(own_frequency - neighbour_frequency)))
            + float(np.mean(np.abs(own_rocof - neighbour_rocof)))
        )
        damping_target = np.tanh(self.contract.damping_gain * damping_signal)
        target = np.asarray([inertia_target, damping_target], dtype=np.float32)
        return self.action_projector.project(target)


class LocalNeighbourMDExecution:
    """Route one observation row to each independent per-VSG M/D agent."""

    architecture = "local_rows_independent_per_vsg_md_actions"

    def __init__(self, contract: LocalNeighbourMDContract) -> None:
        self.contract = contract
        self.agents = tuple(
            LocalNeighbourMDAgent(agent_id=actor, contract=contract)
            for actor in range(DEVICE_COUNT)
        )

    def reset(self) -> None:
        for agent in self.agents:
            agent.reset()

    def act(
        self,
        observations: Mapping[int, Sequence[float] | np.ndarray],
    ) -> np.ndarray:
        if set(observations) != set(range(DEVICE_COUNT)):
            raise ValueError("observations must contain exactly actors 0..3")
        return np.stack(
            [self.agents[actor].act(observations[actor]) for actor in range(DEVICE_COUNT)]
        ).astype(np.float32)


def adapt_v4_observations_to_physical(
    observations: Mapping[int, Sequence[float] | np.ndarray],
    *,
    control_nominal_frequency_hz: float = LEGACY_CONTROL_NOMINAL_FREQUENCY_HZ,
    physical_nominal_frequency_hz: float = PHYSICAL_NOMINAL_FREQUENCY_HZ,
) -> dict[int, np.ndarray]:
    """Return copied V4 observations calibrated to the physical frequency base."""

    expected = set(range(DEVICE_COUNT))
    if set(observations) != expected:
        raise ValueError("observations must contain exactly actors 0..3")
    control_nominal = float(control_nominal_frequency_hz)
    physical_nominal = float(physical_nominal_frequency_hz)
    if not np.isfinite(control_nominal) or control_nominal <= 0.0:
        raise ValueError("control nominal frequency must be finite and positive")
    if not np.isclose(
        control_nominal,
        LEGACY_CONTROL_NOMINAL_FREQUENCY_HZ,
        rtol=0.0,
        atol=0.0,
    ):
        raise ValueError("control nominal frequency must be 50 Hz")
    if not np.isclose(
        physical_nominal,
        PHYSICAL_NOMINAL_FREQUENCY_HZ,
        rtol=0.0,
        atol=0.0,
    ):
        raise ValueError("physical nominal frequency must be 60 Hz")
    ratio = physical_nominal / control_nominal
    result: dict[int, np.ndarray] = {}
    for actor in range(DEVICE_COUNT):
        row = np.asarray(observations[actor], dtype=np.float32)
        if row.shape != (OBSERVATION_DIM,):
            raise ValueError("each observation must have shape (7,)")
        if not np.all(np.isfinite(row)):
            raise ValueError("observations must contain only finite values")
        converted = row.copy()
        converted[list(FREQUENCY_OBSERVATION_SLOTS)] *= np.float32(ratio)
        result[actor] = converted
    return result


__all__ = [
    "LocalNeighbourMDContract",
    "LocalNeighbourMDExecution",
    "PerVSGMDActionProjector",
    "adapt_v4_observations_to_physical",
    "local_neighbour_md_candidates",
]
