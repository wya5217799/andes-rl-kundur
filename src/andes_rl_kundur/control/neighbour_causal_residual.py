"""Exact public information seam for causal neighbour residual actors.

The module converts the deployed ``LocalEdgeObservation`` object into the
single numeric contract shared by deterministic residual controllers and any
future learned edge actor.  It owns no simulator, experiment split, oracle,
or research classification.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from andes_rl_kundur.control.model_first_distributed_edge import (
    LocalEdgeObservation,
)
from andes_rl_kundur.control.residual_headroom import (
    StandardizedAffineModel,
    apply_standardized_affine,
    fit_standardized_affine,
)

OBSERVATION_DIMENSION = 15


def observation_vector(observation: LocalEdgeObservation) -> np.ndarray:
    """Return the ordered fifteen-field vector exposed to one edge actor."""

    source = observation.source
    target = observation.target
    vector = np.asarray(
        (
            source.frequency_deviation_hz,
            target.frequency_deviation_hz,
            source.rocof_hz_s,
            target.rocof_hz_s,
            observation.previous_edge_flow_system_pu,
            source.previous_command_system_pu,
            target.previous_command_system_pu,
            source.soc,
            target.soc,
            source.voltage_pu,
            target.voltage_pu,
            source.lower_residual_power_system_pu,
            target.lower_residual_power_system_pu,
            source.upper_residual_power_system_pu,
            target.upper_residual_power_system_pu,
        ),
        dtype=float,
    )
    if vector.shape != (OBSERVATION_DIMENSION,) or not np.all(np.isfinite(vector)):
        raise ValueError("edge observation vector must contain fifteen finite values")
    return vector


@dataclass(frozen=True)
class AffineNeighbourResidualController:
    """One fixed endpoint-local affine controller with normalized output."""

    edge: tuple[int, int]
    model: StandardizedAffineModel

    def act(self, observation: LocalEdgeObservation) -> float:
        """Return one clipped normalized action without cross-edge input."""

        if observation.edge != self.edge:
            raise ValueError("observation edge does not match this residual controller")
        prediction = apply_standardized_affine(
            self.model,
            observation_vector(observation).reshape(1, -1),
        )
        return float(np.clip(np.asarray(prediction).reshape(-1)[0], -1.0, 1.0))


def fit_affine_edge_controller(
    *,
    edge: tuple[int, int],
    observations: Sequence[LocalEdgeObservation],
    normalized_actions: Sequence[float],
) -> AffineNeighbourResidualController:
    """Fit the no-tuning affine policy for one independently owned edge."""

    canonical_edge = tuple(int(value) for value in edge)
    if len(canonical_edge) != 2 or canonical_edge[0] >= canonical_edge[1]:
        raise ValueError("edge must use source-before-target orientation")
    if len(observations) < 2 or len(observations) != len(normalized_actions):
        raise ValueError("observations and actions must contain aligned rows")
    if any(observation.edge != canonical_edge for observation in observations):
        raise ValueError("every observation must belong to the fitted edge")
    targets = np.asarray(normalized_actions, dtype=float)
    if (
        targets.shape != (len(observations),)
        or not np.all(np.isfinite(targets))
        or np.any(np.abs(targets) > 1.0)
    ):
        raise ValueError("normalized actions must be finite values in [-1, 1]")
    features = np.vstack([observation_vector(item) for item in observations])
    return AffineNeighbourResidualController(
        edge=canonical_edge,
        model=fit_standardized_affine(features, targets),
    )
