"""Frozen non-neural flexible residual controllers for one edge actor.

The module owns three tuning-free map families -- RBF kernel ridge, k-nearest
neighbour, and a quadratic polynomial basis -- that share the exact public
fifteen-field observation vector with the R359 affine controller.  Every
family is fitted and evaluated through the same ``act`` interface; no
hyperparameter, kernel, seed, reward, or candidate scan exists, and no neural
or reinforcement-learning object is used.  The module owns no simulator,
experiment split, oracle, or research classification.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from andes_rl_kundur.control.model_first_distributed_edge import (
    LocalEdgeObservation,
)
from andes_rl_kundur.control.neighbour_causal_residual import (
    OBSERVATION_DIMENSION,
    observation_vector,
)

RBF_REGULARIZATION = 1.0e-3
KNN_NEIGHBOUR_COUNT = 5
POLYNOMIAL_DEGREE = 2


def _edge_features(observations: Sequence[LocalEdgeObservation]) -> np.ndarray:
    """Stack the exact public observation vectors for one edge."""
    return np.vstack([observation_vector(item) for item in observations])


def _validate_edge(edge: object, canonical_edge: tuple[int, int]) -> None:
    if canonical_edge != tuple(int(value) for value in edge):
        raise ValueError("observation edge does not match this residual controller")


@dataclass(frozen=True)
class RbfKernelRidgeNeighbourResidualController:
    """RBF kernel-ridge map with frozen median-distance width."""

    edge: tuple[int, int]
    training_features: np.ndarray
    alpha: np.ndarray
    width: float
    regularization: float

    def act(self, observation: LocalEdgeObservation) -> float:
        """Return one clipped normalized action without cross-edge input."""
        _validate_edge(observation.edge, self.edge)
        feature = observation_vector(observation).reshape(1, -1)
        squared = (
            np.sum(feature * feature, axis=1, keepdims=True)
            + np.sum(self.training_features * self.training_features, axis=1, keepdims=True).T
            - 2.0 * feature @ self.training_features.T
        )
        kernel = np.exp(-squared / (2.0 * self.width * self.width))
        prediction = float(np.asarray(kernel @ self.alpha).reshape(-1)[0])
        return float(np.clip(prediction, -1.0, 1.0))


def fit_rbf_kernel_ridge_edge_controller(
    *,
    edge: tuple[int, int],
    observations: Sequence[LocalEdgeObservation],
    normalized_actions: Sequence[float],
) -> RbfKernelRidgeNeighbourResidualController:
    """Fit the frozen RBF kernel-ridge map for one independently owned edge."""
    canonical_edge = tuple(int(value) for value in edge)
    if len(canonical_edge) != 2 or canonical_edge[0] >= canonical_edge[1]:
        raise ValueError("edge must use source-before-target orientation")
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
    return RbfKernelRidgeNeighbourResidualController(
        edge=canonical_edge,
        training_features=features,
        alpha=alpha,
        width=width,
        regularization=RBF_REGULARIZATION,
    )


@dataclass(frozen=True)
class KnnNeighbourResidualController:
    """k-nearest-neighbour map with frozen k on standardized features."""

    edge: tuple[int, int]
    training_features: np.ndarray
    training_targets: np.ndarray
    mean: np.ndarray
    scale: np.ndarray
    neighbour_count: int

    def act(self, observation: LocalEdgeObservation) -> float:
        """Return one clipped normalized action without cross-edge input."""
        _validate_edge(observation.edge, self.edge)
        feature = observation_vector(observation).reshape(1, -1)
        standardized = (feature - self.mean) / self.scale
        standardized_train = (self.training_features - self.mean) / self.scale
        squared = np.sum(
            (standardized_train - standardized) * (standardized_train - standardized),
            axis=1,
        )
        neighbours = np.argsort(squared, kind="stable")[: self.neighbour_count]
        prediction = float(np.mean(self.training_targets[neighbours]))
        return float(np.clip(prediction, -1.0, 1.0))


def fit_knn_edge_controller(
    *,
    edge: tuple[int, int],
    observations: Sequence[LocalEdgeObservation],
    normalized_actions: Sequence[float],
) -> KnnNeighbourResidualController:
    """Fit the frozen k-nearest-neighbour map for one independently owned edge."""
    canonical_edge = tuple(int(value) for value in edge)
    if len(canonical_edge) != 2 or canonical_edge[0] >= canonical_edge[1]:
        raise ValueError("edge must use source-before-target orientation")
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
    return KnnNeighbourResidualController(
        edge=canonical_edge,
        training_features=features,
        training_targets=targets,
        mean=mean,
        scale=scale,
        neighbour_count=KNN_NEIGHBOUR_COUNT,
    )


@dataclass(frozen=True)
class QuadraticPolynomialNeighbourResidualController:
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
    def act(self, observation: LocalEdgeObservation) -> float:
        """Return one clipped normalized action without cross-edge input."""
        _validate_edge(observation.edge, self.edge)
        feature = observation_vector(observation).reshape(1, -1)
        basis = self._basis(feature)
        prediction = float(np.asarray(basis @ self.coefficients).reshape(-1)[0])
        return float(np.clip(prediction, -1.0, 1.0))


def fit_quadratic_polynomial_edge_controller(
    *,
    edge: tuple[int, int],
    observations: Sequence[LocalEdgeObservation],
    normalized_actions: Sequence[float],
) -> QuadraticPolynomialNeighbourResidualController:
    """Fit the frozen quadratic polynomial-basis map for one edge."""
    canonical_edge = tuple(int(value) for value in edge)
    if len(canonical_edge) != 2 or canonical_edge[0] >= canonical_edge[1]:
        raise ValueError("edge must use source-before-target orientation")
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
    return QuadraticPolynomialNeighbourResidualController(
        edge=canonical_edge,
        mean=mean,
        scale=scale,
        coefficients=coefficients,
    )


FLEXIBLE_CONTROLLER_FAMILY = {
    "rbf_kernel_ridge": fit_rbf_kernel_ridge_edge_controller,
    "knn": fit_knn_edge_controller,
    "quadratic_polynomial": fit_quadratic_polynomial_edge_controller,
}
