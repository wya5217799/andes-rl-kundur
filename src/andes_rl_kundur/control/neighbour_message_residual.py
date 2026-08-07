"""Frozen non-neural message-extended residual controllers for one edge actor.

The module owns the R359 fixed affine map and the R360 three tuning-free
non-neural families (RBF kernel ridge, k-NN, quadratic polynomial basis)
evaluated on the public observation extended with one-hop neighbour node
messages on the frozen communication ring.  Every family is fitted and
evaluated through the same ``act`` interface over ``MessageExtendedObservation``
rows; no hyperparameter, kernel, seed, reward, or candidate scan exists, and
no neural or reinforcement-learning object is used.  The module owns no
simulator, experiment split, oracle, or research classification.

The extended observation is frozen as the fifteen-field vector plus the
four-field message (frequency deviation, RoCoF, SOC, voltage) of each of the
two one-hop neighbour nodes, giving twenty-three fields total.  The four-field
message keeps the R360 quadratic polynomial basis fittable under the frozen
345-row leave-one-scenario-out training folds (299 basis columns).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from andes_rl_kundur.control.flexible_neighbour_residual import (
    KNN_NEIGHBOUR_COUNT,
    RBF_REGULARIZATION,
)
from andes_rl_kundur.control.model_first_distributed_edge import (
    EndpointObservation,
    LocalEdgeObservation,
)
from andes_rl_kundur.control.neighbour_causal_residual import (
    OBSERVATION_DIMENSION,
    observation_vector,
)
from andes_rl_kundur.control.residual_headroom import (
    StandardizedAffineModel,
    apply_standardized_affine,
    fit_standardized_affine,
)

NEIGHBOUR_MESSAGE_DIMENSION = 4
MESSAGE_EXTENDED_OBSERVATION_DIMENSION = (
    OBSERVATION_DIMENSION + 2 * NEIGHBOUR_MESSAGE_DIMENSION
)

# Frozen one-hop neighbour table on the communication ring
# {(0,1),(1,2),(2,3),(0,3)}: for action edge (i,j), the source-side neighbour
# is the ring neighbour of i that is not j, and the target-side neighbour is
# the ring neighbour of j that is not i.
ONE_HOP_NEIGHBOUR_MESSAGES: dict[tuple[int, int], tuple[int, int]] = {
    (0, 1): (3, 2),
    (1, 2): (0, 3),
    (2, 3): (1, 0),
}


@dataclass(frozen=True)
class MessageExtendedObservation:
    """The complete deployed input of one message-extended edge actor."""

    edge: tuple[int, int]
    observation: LocalEdgeObservation
    source_neighbour: EndpointObservation
    target_neighbour: EndpointObservation

    def __post_init__(self) -> None:
        edge = tuple(int(value) for value in self.edge)
        if edge not in ONE_HOP_NEIGHBOUR_MESSAGES:
            raise ValueError("edge must be one of the frozen action edges")
        source_id, target_id = ONE_HOP_NEIGHBOUR_MESSAGES[edge]
        if (self.source_neighbour.node_id, self.target_neighbour.node_id) != (
            source_id,
            target_id,
        ):
            raise ValueError("neighbour observations do not match the frozen neighbour table")


def neighbour_message_vector(endpoint: EndpointObservation) -> np.ndarray:
    """Return the frozen four-field neighbour message (frequency, RoCoF, SOC, voltage)."""

    vector = np.asarray(
        (
            endpoint.frequency_deviation_hz,
            endpoint.rocof_hz_s,
            endpoint.soc,
            endpoint.voltage_pu,
        ),
        dtype=float,
    )
    if vector.shape != (NEIGHBOUR_MESSAGE_DIMENSION,) or not np.all(np.isfinite(vector)):
        raise ValueError("neighbour message must contain four finite values")
    return vector


def message_extended_observation_vector(
    item: MessageExtendedObservation,
) -> np.ndarray:
    """Return the ordered twenty-three-field message-extended vector."""

    vector = np.concatenate(
        (
            observation_vector(item.observation),
            neighbour_message_vector(item.source_neighbour),
            neighbour_message_vector(item.target_neighbour),
        )
    )
    if (
        vector.shape != (MESSAGE_EXTENDED_OBSERVATION_DIMENSION,)
        or not np.all(np.isfinite(vector))
    ):
        raise ValueError(
            "message-extended observation vector must contain twenty-three finite values"
        )
    return vector


def _edge_features(
    observations: Sequence[MessageExtendedObservation],
) -> np.ndarray:
    """Stack the exact message-extended observation vectors for one edge."""

    return np.vstack([message_extended_observation_vector(item) for item in observations])


def _validate_edge(edge: object, canonical_edge: tuple[int, int]) -> None:
    if canonical_edge != tuple(int(value) for value in edge):
        raise ValueError("observation edge does not match this residual controller")


@dataclass(frozen=True)
class MessageAffineNeighbourResidualController:
    """One fixed standardized-affine controller over the extended observation."""

    edge: tuple[int, int]
    model: StandardizedAffineModel

    def act(self, observation: MessageExtendedObservation) -> float:
        """Return one clipped normalized action without cross-edge input."""

        _validate_edge(observation.edge, self.edge)
        feature = message_extended_observation_vector(observation).reshape(1, -1)
        prediction = apply_standardized_affine(self.model, feature)
        return float(np.clip(np.asarray(prediction).reshape(-1)[0], -1.0, 1.0))


def fit_message_affine_edge_controller(
    *,
    edge: tuple[int, int],
    observations: Sequence[MessageExtendedObservation],
    normalized_actions: Sequence[float],
) -> MessageAffineNeighbourResidualController:
    """Fit the no-tuning standardized affine map for one message-extended edge."""

    canonical_edge = tuple(int(value) for value in edge)
    if canonical_edge not in ONE_HOP_NEIGHBOUR_MESSAGES:
        raise ValueError("edge must be one of the frozen action edges")
    if len(observations) < 2 or len(observations) != len(normalized_actions):
        raise ValueError("observations and actions must contain aligned rows")
    if any(item.edge != canonical_edge for item in observations):
        raise ValueError("every observation must belong to the fitted edge")
    targets = np.asarray(normalized_actions, dtype=float)
    if (
        targets.shape != (len(observations),)
        or not np.all(np.isfinite(targets))
        or np.any(np.abs(targets) > 1.0)
    ):
        raise ValueError("normalized actions must be finite values in [-1, 1]")
    features = _edge_features(observations)
    return MessageAffineNeighbourResidualController(
        edge=canonical_edge,
        model=fit_standardized_affine(features, targets),
    )


@dataclass(frozen=True)
class MessageRbfKernelRidgeNeighbourResidualController:
    """RBF kernel-ridge map over the extended observation with frozen width."""

    edge: tuple[int, int]
    training_features: np.ndarray
    alpha: np.ndarray
    width: float
    regularization: float

    def act(self, observation: MessageExtendedObservation) -> float:
        """Return one clipped normalized action without cross-edge input."""

        _validate_edge(observation.edge, self.edge)
        feature = message_extended_observation_vector(observation).reshape(1, -1)
        squared = (
            np.sum(feature * feature, axis=1, keepdims=True)
            + np.sum(self.training_features * self.training_features, axis=1, keepdims=True).T
            - 2.0 * feature @ self.training_features.T
        )
        kernel = np.exp(-squared / (2.0 * self.width * self.width))
        prediction = float(np.asarray(kernel @ self.alpha).reshape(-1)[0])
        return float(np.clip(prediction, -1.0, 1.0))


def fit_message_rbf_kernel_ridge_edge_controller(
    *,
    edge: tuple[int, int],
    observations: Sequence[MessageExtendedObservation],
    normalized_actions: Sequence[float],
) -> MessageRbfKernelRidgeNeighbourResidualController:
    """Fit the frozen RBF kernel-ridge map for one message-extended edge."""

    canonical_edge = tuple(int(value) for value in edge)
    if canonical_edge not in ONE_HOP_NEIGHBOUR_MESSAGES:
        raise ValueError("edge must be one of the frozen action edges")
    if len(observations) < 2 or len(observations) != len(normalized_actions):
        raise ValueError("observations and actions must contain aligned rows")
    if any(item.edge != canonical_edge for item in observations):
        raise ValueError("every observation must belong to the fitted edge")
    targets = np.asarray(normalized_actions, dtype=float)
    if (
        targets.shape != (len(observations),)
        or not np.all(np.isfinite(targets))
        or np.any(np.abs(targets) > 1.0)
    ):
        raise ValueError("normalized actions must be finite values in [-1, 1]")
    features = _edge_features(observations)
    pairwise = np.sum(features * features, axis=1, keepdims=True)
    squared = pairwise + pairwise.T - 2.0 * features @ features.T
    distances = np.sqrt(np.maximum(squared, 0.0))
    upper = distances[np.triu_indices_from(distances, k=1)]
    if upper.size == 0:
        raise ValueError("at least two distinct training rows are required")
    width = float(np.median(upper))
    if not np.isfinite(width) or width <= 0.0:
        raise ValueError("kernel width must be positive and finite")
    kernel = np.exp(-squared / (2.0 * width * width))
    regularized = kernel + RBF_REGULARIZATION * np.eye(kernel.shape[0])
    alpha = np.linalg.solve(regularized, targets)
    return MessageRbfKernelRidgeNeighbourResidualController(
        edge=canonical_edge,
        training_features=features,
        alpha=alpha,
        width=width,
        regularization=RBF_REGULARIZATION,
    )


@dataclass(frozen=True)
class MessageKnnNeighbourResidualController:
    """k-nearest-neighbour map over the extended observation with frozen k."""

    edge: tuple[int, int]
    training_features: np.ndarray
    training_targets: np.ndarray
    mean: np.ndarray
    scale: np.ndarray
    neighbour_count: int

    def act(self, observation: MessageExtendedObservation) -> float:
        """Return one clipped normalized action without cross-edge input."""

        _validate_edge(observation.edge, self.edge)
        feature = message_extended_observation_vector(observation).reshape(1, -1)
        standardized = (feature - self.mean) / self.scale
        standardized_train = (self.training_features - self.mean) / self.scale
        squared = np.sum(
            (standardized_train - standardized) * (standardized_train - standardized),
            axis=1,
        )
        neighbours = np.argsort(squared, kind="stable")[: self.neighbour_count]
        prediction = float(np.mean(self.training_targets[neighbours]))
        return float(np.clip(prediction, -1.0, 1.0))


def fit_message_knn_edge_controller(
    *,
    edge: tuple[int, int],
    observations: Sequence[MessageExtendedObservation],
    normalized_actions: Sequence[float],
) -> MessageKnnNeighbourResidualController:
    """Fit the frozen k-nearest-neighbour map for one message-extended edge."""

    canonical_edge = tuple(int(value) for value in edge)
    if canonical_edge not in ONE_HOP_NEIGHBOUR_MESSAGES:
        raise ValueError("edge must be one of the frozen action edges")
    if len(observations) < KNN_NEIGHBOUR_COUNT or len(observations) != len(normalized_actions):
        raise ValueError("observations must provide at least k aligned rows")
    if any(item.edge != canonical_edge for item in observations):
        raise ValueError("every observation must belong to the fitted edge")
    targets = np.asarray(normalized_actions, dtype=float)
    if (
        targets.shape != (len(observations),)
        or not np.all(np.isfinite(targets))
        or np.any(np.abs(targets) > 1.0)
    ):
        raise ValueError("normalized actions must be finite values in [-1, 1]")
    features = _edge_features(observations)
    mean = np.mean(features, axis=0)
    scale = np.std(features, axis=0)
    if np.any(~np.isfinite(mean)) or np.any(~np.isfinite(scale)) or np.any(scale <= 0.0):
        raise ValueError("feature standardization must be finite and strictly positive")
    return MessageKnnNeighbourResidualController(
        edge=canonical_edge,
        training_features=features,
        training_targets=targets,
        mean=mean,
        scale=scale,
        neighbour_count=KNN_NEIGHBOUR_COUNT,
    )


@dataclass(frozen=True)
class MessageQuadraticPolynomialNeighbourResidualController:
    """Quadratic polynomial-basis least-squares map with standardization."""

    edge: tuple[int, int]
    mean: np.ndarray
    scale: np.ndarray
    coefficients: np.ndarray

    def _basis(self, feature: np.ndarray) -> np.ndarray:
        standard = (feature - self.mean) / self.scale
        dimension = standard.shape[1]
        interactions: list[np.ndarray] = []
        for first in range(dimension):
            for second in range(first, dimension):
                interactions.append((standard[:, first] * standard[:, second]).reshape(-1, 1))
        return np.hstack([standard, *interactions])

    def act(self, observation: MessageExtendedObservation) -> float:
        """Return one clipped normalized action without cross-edge input."""

        _validate_edge(observation.edge, self.edge)
        feature = message_extended_observation_vector(observation).reshape(1, -1)
        basis = self._basis(feature)
        prediction = float(np.asarray(basis @ self.coefficients).reshape(-1)[0])
        return float(np.clip(prediction, -1.0, 1.0))


def fit_message_quadratic_polynomial_edge_controller(
    *,
    edge: tuple[int, int],
    observations: Sequence[MessageExtendedObservation],
    normalized_actions: Sequence[float],
) -> MessageQuadraticPolynomialNeighbourResidualController:
    """Fit the frozen quadratic polynomial-basis map for one message-extended edge."""

    canonical_edge = tuple(int(value) for value in edge)
    if canonical_edge not in ONE_HOP_NEIGHBOUR_MESSAGES:
        raise ValueError("edge must be one of the frozen action edges")
    if len(observations) < 2 or len(observations) != len(normalized_actions):
        raise ValueError("observations and actions must contain aligned rows")
    if any(item.edge != canonical_edge for item in observations):
        raise ValueError("every observation must belong to the fitted edge")
    targets = np.asarray(normalized_actions, dtype=float)
    if (
        targets.shape != (len(observations),)
        or not np.all(np.isfinite(targets))
        or np.any(np.abs(targets) > 1.0)
    ):
        raise ValueError("normalized actions must be finite values in [-1, 1]")
    features = _edge_features(observations)
    mean = np.mean(features, axis=0)
    scale = np.std(features, axis=0)
    if np.any(~np.isfinite(mean)) or np.any(~np.isfinite(scale)) or np.any(scale <= 0.0):
        raise ValueError("feature standardization must be finite and strictly positive")
    standard = (features - mean) / scale
    dimension = standard.shape[1]
    interaction_blocks: list[np.ndarray] = []
    for first in range(dimension):
        for second in range(first, dimension):
            interaction_blocks.append(
                (standard[:, first] * standard[:, second]).reshape(-1, 1)
            )
    basis = np.hstack([standard, *interaction_blocks])
    if basis.shape[0] <= basis.shape[1]:
        raise ValueError("quadratic basis requires more rows than basis columns")
    coefficients, *_ = np.linalg.lstsq(basis, targets, rcond=None)
    return MessageQuadraticPolynomialNeighbourResidualController(
        edge=canonical_edge,
        mean=mean,
        scale=scale,
        coefficients=coefficients,
    )


MESSAGE_CONTROLLER_FAMILY = {
    "affine": fit_message_affine_edge_controller,
    "rbf_kernel_ridge": fit_message_rbf_kernel_ridge_edge_controller,
    "knn": fit_message_knn_edge_controller,
    "quadratic_polynomial": fit_message_quadratic_polynomial_edge_controller,
}
