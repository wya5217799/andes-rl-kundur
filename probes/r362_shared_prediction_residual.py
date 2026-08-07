"""Conclusion-affecting seams for the R362 shared-prediction learnability gate.

The probe rebuilds the R359 exact causal observations, attaches the frozen
R341-model shared prediction messages, fits the four pre-registered frozen
non-neural map families per edge, evaluates every family leave-one-scenario-out
on development rows, and owns the prospective four-way OR decision.  It does
not load repository artifacts, execute a simulator, fit from holdout data, or
write a verdict.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from andes_rl_kundur.control.flexible_neighbour_residual import (
    KNN_NEIGHBOUR_COUNT,
    RBF_REGULARIZATION,
)
from andes_rl_kundur.control.model_first_distributed_edge import (
    LocalEdgeObservation,
)
from andes_rl_kundur.control.neighbour_message_residual import (
    ONE_HOP_NEIGHBOUR_MESSAGES,
)
from andes_rl_kundur.control.residual_headroom import (
    StandardizedAffineModel,
    apply_standardized_affine,
    fit_standardized_affine,
)
from andes_rl_kundur.control.shared_prediction_residual import (
    SharedPredictionMessage,
    SharedPredictionObservation,
    generate_shared_predictions,
    shared_prediction_observation_vector,
)
from andes_rl_kundur.env.andes.model_first_contract import ACTION_EDGES

from probes import r359_neighbour_causal_residual as r359_probe

SHARED_PREDICTION_FAMILY = ("affine", "rbf_kernel_ridge", "knn", "quadratic_polynomial")


def build_shared_prediction_observations_from_parent_inventory(
    *,
    inventory: Sequence[Mapping[str, Any]],
    physical_contract: Any,
    candidate_models: Mapping[str, Any],
    point_model_digests: Mapping[str, str],
    output_scales_by_point: Mapping[str, Sequence[float]],
    nominal_frequency_hz: float,
    sample_period_seconds: float,
    startup_zero_steps: int,
    expected_horizon: int,
) -> dict[str, dict[tuple[int, int], tuple[SharedPredictionObservation, ...]]]:
    """Rebuild exact R359 observations and attach causal shared predictions."""

    from probes.r353_matched_residual_headroom import load_frozen_point_model

    local_observations = r359_probe.build_observations_from_parent_inventory(
        inventory=inventory,
        physical_contract=physical_contract,
        nominal_frequency_hz=nominal_frequency_hz,
        sample_period_seconds=sample_period_seconds,
        startup_zero_steps=startup_zero_steps,
        expected_horizon=expected_horizon,
    )
    steps = int(expected_horizon)
    startup = int(startup_zero_steps)
    if steps < 1 or startup < 0 or startup >= steps:
        raise ValueError("startup mask must lie within the positive horizon")
    models: dict[str, Any] = {}
    message_observations: dict[
        str, dict[tuple[int, int], tuple[SharedPredictionObservation, ...]]
    ] = {}
    for parent in inventory:
        scenario_id = str(parent["scenario_id"])
        if scenario_id not in local_observations:
            raise ValueError(f"missing local observations for {scenario_id}")
        edge_rows = local_observations[scenario_id]
        if set(edge_rows) != set(ACTION_EDGES):
            raise ValueError("every scenario must contain exactly three edge observations")
        point = str(parent["point"])
        if point not in models:
            models[point] = load_frozen_point_model(
                candidate_models,
                point=point,
                expected_digest=point_model_digests[point],
            )
        selected = parent["arms"]["selected_local"]
        rows = selected["trace"]["rows"]
        if len(rows) != steps:
            raise ValueError("selected-local trace horizon drift")
        frequency = np.asarray([row["freq_hz_physical"] for row in rows], dtype=float)
        commanded = np.asarray(
            [row["bess_commanded_power_system_pu"] for row in rows], dtype=float
        )
        achieved = np.asarray(
            [row["bess_actual_power_system_pu"] for row in rows], dtype=float
        )
        inertia = np.asarray(
            selected["trace"]["structural_contract"]["operating_point"][
                "vsg_m_system"
            ],
            dtype=float,
        )
        predictions = generate_shared_predictions(
            model=models[point],
            output_scales=output_scales_by_point[point],
            frequency_hz_after_action=frequency,
            commanded_node_power_after_action=commanded,
            achieved_node_power_after_action=achieved,
            inertia_system=inertia,
            nominal_frequency_hz=float(nominal_frequency_hz),
            sample_period_seconds=float(sample_period_seconds),
            startup_zero_steps=startup,
        )
        extended: dict[tuple[int, int], list[SharedPredictionObservation]] = {
            edge: [] for edge in ACTION_EDGES
        }
        for edge in ACTION_EDGES:
            rows_by_edge = edge_rows[edge]
            if len(rows_by_edge) != steps - startup:
                raise ValueError("edge observation rows do not match the horizon")
            source_id, target_id = ONE_HOP_NEIGHBOUR_MESSAGES[edge]
            for index in range(steps - startup):
                causal_step = startup + index
                extended[edge].append(
                    SharedPredictionObservation(
                        edge=edge,
                        observation=rows_by_edge[index],
                        source_neighbour_prediction=SharedPredictionMessage(
                            node_id=source_id,
                            values_hz=predictions[source_id][causal_step],
                        ),
                        target_neighbour_prediction=SharedPredictionMessage(
                            node_id=target_id,
                            values_hz=predictions[target_id][causal_step],
                        ),
                    )
                )
        message_observations[scenario_id] = {
            edge: tuple(rows) for edge, rows in extended.items()
        }
    return message_observations


def _edge_features(
    observations: Sequence[SharedPredictionObservation],
) -> np.ndarray:
    """Stack the exact twenty-three-field shared-prediction vectors for one edge."""

    return np.vstack(
        [shared_prediction_observation_vector(item) for item in observations]
    )


def _validate_edge(edge: object, canonical_edge: tuple[int, int]) -> None:
    if canonical_edge != tuple(int(value) for value in edge):
        raise ValueError("observation edge does not match this residual controller")


def _fit_family(
    *,
    training_scenario_ids: Sequence[str],
    observations_by_scenario: Mapping[
        str, Mapping[tuple[int, int], Sequence[SharedPredictionObservation]]
    ],
    normalized_targets_by_scenario: Mapping[str, object],
    horizon: int,
    startup_zero_steps: int,
) -> dict[str, dict[tuple[int, int], Any]]:
    """Fit all four frozen families on every edge for the training fold."""

    steps = int(horizon)
    startup = int(startup_zero_steps)
    if steps < 1 or startup < 0 or startup >= steps:
        raise ValueError("startup mask must lie within the positive horizon")
    family_controllers: dict[str, dict[tuple[int, int], Any]] = {
        name: {} for name in SHARED_PREDICTION_FAMILY
    }
    for edge_index, edge in enumerate(ACTION_EDGES):
        observations: list[SharedPredictionObservation] = []
        actions: list[float] = []
        for scenario_id in sorted(str(item) for item in training_scenario_ids):
            target = np.asarray(normalized_targets_by_scenario[scenario_id], dtype=float)
            if target.shape != (steps, 3) or not np.all(np.isfinite(target)):
                raise ValueError("normalized target matrix has the wrong shape")
            if np.any(np.abs(target) > 1.0 + 1.0e-12):
                raise ValueError("normalized targets exceed the public action interval")
            if not np.array_equal(target[:startup], np.zeros((startup, 3))):
                raise ValueError("startup targets must be fixed to zero")
            scenario = observations_by_scenario[scenario_id]
            if set(scenario) != set(ACTION_EDGES):
                raise ValueError("every scenario must contain exactly three edge observations")
            edge_observations = tuple(scenario[edge])
            if len(edge_observations) != steps - startup:
                raise ValueError("observation rows do not match the reconstructible horizon")
            observations.extend(edge_observations)
            actions.extend(target[startup:, edge_index].tolist())
        features = _edge_features(observations)
        targets = np.asarray(actions, dtype=float)
        if (
            targets.shape != (len(observations),)
            or not np.all(np.isfinite(targets))
            or np.any(np.abs(targets) > 1.0)
        ):
            raise ValueError("normalized actions must be finite values in [-1, 1]")
        family_controllers["affine"][edge] = _AffineWrapper(
            edge=edge,
            model=fit_standardized_affine(features, targets),
        )
        family_controllers["rbf_kernel_ridge"][edge] = _RbfWrapper(
            edge=edge,
            features=features,
            targets=targets,
        )
        family_controllers["knn"][edge] = _KnnWrapper(
            edge=edge,
            features=features,
            targets=targets,
        )
        family_controllers["quadratic_polynomial"][edge] = _QuadraticWrapper(
            edge=edge,
            features=features,
            targets=targets,
        )
    return family_controllers


class _AffineWrapper:
    def __init__(self, *, edge, model: StandardizedAffineModel) -> None:
        self.edge = tuple(int(value) for value in edge)
        self.model = model

    def act(self, observation: SharedPredictionObservation) -> float:
        _validate_edge(observation.edge, self.edge)
        feature = shared_prediction_observation_vector(observation).reshape(1, -1)
        prediction = apply_standardized_affine(self.model, feature)
        return float(np.clip(np.asarray(prediction).reshape(-1)[0], -1.0, 1.0))


class _RbfWrapper:
    def __init__(self, *, edge, features, targets) -> None:
        self.edge = tuple(int(value) for value in edge)
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
        self.training_features = features
        self.alpha = alpha
        self.width = width
        self.regularization = RBF_REGULARIZATION

    def act(self, observation: SharedPredictionObservation) -> float:
        _validate_edge(observation.edge, self.edge)
        feature = shared_prediction_observation_vector(observation).reshape(1, -1)
        squared = (
            np.sum(feature * feature, axis=1, keepdims=True)
            + np.sum(
                self.training_features * self.training_features, axis=1, keepdims=True
            ).T
            - 2.0 * feature @ self.training_features.T
        )
        kernel = np.exp(-squared / (2.0 * self.width * self.width))
        prediction = float(np.asarray(kernel @ self.alpha).reshape(-1)[0])
        return float(np.clip(prediction, -1.0, 1.0))


class _KnnWrapper:
    def __init__(self, *, edge, features, targets) -> None:
        self.edge = tuple(int(value) for value in edge)
        if len(features) < KNN_NEIGHBOUR_COUNT:
            raise ValueError("observations must provide at least k aligned rows")
        mean = np.mean(features, axis=0)
        scale = np.std(features, axis=0)
        if np.any(~np.isfinite(mean)) or np.any(~np.isfinite(scale)) or np.any(scale <= 0.0):
            raise ValueError("feature standardization must be finite and strictly positive")
        self.training_features = features
        self.training_targets = targets
        self.mean = mean
        self.scale = scale
        self.neighbour_count = KNN_NEIGHBOUR_COUNT

    def act(self, observation: SharedPredictionObservation) -> float:
        _validate_edge(observation.edge, self.edge)
        feature = shared_prediction_observation_vector(observation).reshape(1, -1)
        standardized = (feature - self.mean) / self.scale
        standardized_train = (self.training_features - self.mean) / self.scale
        squared = np.sum(
            (standardized_train - standardized) * (standardized_train - standardized),
            axis=1,
        )
        neighbours = np.argsort(squared, kind="stable")[: self.neighbour_count]
        prediction = float(np.mean(self.training_targets[neighbours]))
        return float(np.clip(prediction, -1.0, 1.0))


class _QuadraticWrapper:
    def __init__(self, *, edge, features, targets) -> None:
        self.edge = tuple(int(value) for value in edge)
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
        self.mean = mean
        self.scale = scale
        self.coefficients = coefficients

    def _basis(self, feature: np.ndarray) -> np.ndarray:
        standard = (feature - self.mean) / self.scale
        dimension = standard.shape[1]
        interactions: list[np.ndarray] = []
        for first in range(dimension):
            for second in range(first, dimension):
                interactions.append((standard[:, first] * standard[:, second]).reshape(-1, 1))
        return np.hstack([standard, *interactions])

    def act(self, observation: SharedPredictionObservation) -> float:
        _validate_edge(observation.edge, self.edge)
        feature = shared_prediction_observation_vector(observation).reshape(1, -1)
        basis = self._basis(feature)
        prediction = float(np.asarray(basis @ self.coefficients).reshape(-1)[0])
        return float(np.clip(prediction, -1.0, 1.0))


def leave_one_scenario_out_family_proposals(
    *,
    observations_by_scenario: Mapping[
        str, Mapping[tuple[int, int], Sequence[SharedPredictionObservation]]
    ],
    normalized_targets_by_scenario: Mapping[str, object],
    horizon: int,
    startup_zero_steps: int,
) -> dict[str, dict[str, np.ndarray]]:
    """Predict every development scenario with every family, scenario excluded."""

    scenario_ids = tuple(sorted(str(item) for item in observations_by_scenario))
    if len(scenario_ids) < 3 or set(scenario_ids) != {
        str(item) for item in normalized_targets_by_scenario
    }:
        raise ValueError("leave-one-out requires at least three aligned scenarios")
    steps = int(horizon)
    startup = int(startup_zero_steps)
    if steps < 1 or startup < 0 or startup >= steps:
        raise ValueError("startup mask must lie within the positive horizon")
    proposals: dict[str, dict[str, np.ndarray]] = {
        name: {} for name in SHARED_PREDICTION_FAMILY
    }
    for heldout in scenario_ids:
        training_ids = tuple(item for item in scenario_ids if item != heldout)
        family = _fit_family(
            training_scenario_ids=training_ids,
            observations_by_scenario=observations_by_scenario,
            normalized_targets_by_scenario=normalized_targets_by_scenario,
            horizon=steps,
            startup_zero_steps=startup,
        )
        heldout_observations = observations_by_scenario[heldout]
        for name, controllers in family.items():
            predicted = np.zeros((steps, 3), dtype=float)
            for edge_index, edge in enumerate(ACTION_EDGES):
                rows = tuple(heldout_observations[edge])
                if len(rows) != steps - startup:
                    raise ValueError("heldout observations do not match the horizon")
                predicted[startup:, edge_index] = [controllers[edge].act(row) for row in rows]
            proposals[name][heldout] = predicted
    return proposals


def predict_holdout_with_frozen_family(
    *,
    controllers: Mapping[tuple[int, int], Any],
    observations: Mapping[tuple[int, int], Sequence[SharedPredictionObservation]],
    horizon: int,
    startup_zero_steps: int,
) -> np.ndarray:
    """Apply one frozen family's three edge maps to one unlabelled scenario."""

    if set(controllers) != set(ACTION_EDGES):
        raise ValueError("controllers must cover the exact three-edge order")
    if set(observations) != set(ACTION_EDGES):
        raise ValueError("one observation sequence is required for every edge")
    steps = int(horizon)
    startup = int(startup_zero_steps)
    if steps < 1 or startup < 0 or startup >= steps:
        raise ValueError("startup mask must lie within the positive horizon")
    proposal = np.zeros((steps, 3), dtype=float)
    for edge_index, edge in enumerate(ACTION_EDGES):
        rows = tuple(observations[edge])
        if len(rows) != steps - startup:
            raise ValueError("unlabelled observations do not match the horizon")
        proposal[startup:, edge_index] = [controllers[edge].act(row) for row in rows]
    return proposal


def classify_shared_prediction_gate(
    *,
    integrity_checks: Mapping[str, bool],
    family_scientific_checks: Mapping[str, Mapping[str, bool]],
) -> dict[str, Any]:
    """Classify R362 with pre-registered four-way OR semantics."""

    if not integrity_checks or not family_scientific_checks:
        raise ValueError("integrity and family checks must both be populated")
    if set(family_scientific_checks) != set(SHARED_PREDICTION_FAMILY):
        raise ValueError("every registered family must have a scientific check record")
    failed_integrity = sorted(
        str(name) for name, passed in integrity_checks.items() if passed is not True
    )
    passing_families: list[str] = []
    family_failures: dict[str, list[str]] = {}
    for name, checks in family_scientific_checks.items():
        failed = sorted(str(key) for key, passed in checks.items() if passed is not True)
        family_failures[name] = failed
        if not failed:
            passing_families.append(name)
    if failed_integrity:
        classification = "ANALYSIS-INVALID"
    elif passing_families:
        classification = "NEIGHBOUR-LEARNABLE-STRUCTURE-FOUND"
    else:
        classification = "NO-NEIGHBOUR-LEARNABLE-STRUCTURE"
    return {
        "classification": classification,
        "failed_integrity_checks": failed_integrity,
        "passing_families": passing_families,
        "family_failed_scientific_checks": family_failures,
        "successor_question_authorized": (
            classification == "NEIGHBOUR-LEARNABLE-STRUCTURE-FOUND"
        ),
        "training_authorized": False,
        "simulation_authorized": False,
        "eval_authorized": False,
    }
