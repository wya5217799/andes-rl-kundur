"""Conclusion-affecting seams for the R360 flexible residual learnability gate.

The probe fits the three pre-registered frozen non-neural map families per
edge, evaluates every family leave-one-scenario-out on development rows, and
owns the prospective three-way OR decision.  It does not load repository
artifacts, execute a simulator, fit from holdout data, or write a verdict.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from andes_rl_kundur.control.flexible_neighbour_residual import (
    FLEXIBLE_CONTROLLER_FAMILY,
)
from andes_rl_kundur.control.model_first_distributed_edge import (
    LocalEdgeObservation,
)
from andes_rl_kundur.env.andes.model_first_contract import ACTION_EDGES


def _edge_observations(
    observations_by_scenario: Mapping[
        str, Mapping[tuple[int, int], Sequence[LocalEdgeObservation]]
    ],
    edge: tuple[int, int],
) -> list[LocalEdgeObservation]:
    rows: list[LocalEdgeObservation] = []
    for scenario_id in sorted(str(item) for item in observations_by_scenario):
        scenario = observations_by_scenario[scenario_id]
        if set(scenario) != set(ACTION_EDGES):
            raise ValueError("every scenario must contain exactly three edge observations")
        rows.extend(scenario[edge])
    return rows


def _fit_family(
    *,
    training_scenario_ids: Sequence[str],
    observations_by_scenario: Mapping[
        str, Mapping[tuple[int, int], Sequence[LocalEdgeObservation]]
    ],
    normalized_targets_by_scenario: Mapping[str, object],
    horizon: int,
    startup_zero_steps: int,
) -> dict[str, dict[tuple[int, int], Any]]:
    """Fit all three frozen families on every edge for the training fold."""
    steps = int(horizon)
    startup = int(startup_zero_steps)
    if steps < 1 or startup < 0 or startup >= steps:
        raise ValueError("startup mask must lie within the positive horizon")
    family_controllers: dict[str, dict[tuple[int, int], Any]] = {
        name: {} for name in FLEXIBLE_CONTROLLER_FAMILY
    }
    for edge_index, edge in enumerate(ACTION_EDGES):
        observations: list[LocalEdgeObservation] = []
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
        for name, fitter in FLEXIBLE_CONTROLLER_FAMILY.items():
            family_controllers[name][edge] = fitter(
                edge=edge,
                observations=observations,
                normalized_actions=actions,
            )
    return family_controllers


def leave_one_scenario_out_family_proposals(
    *,
    observations_by_scenario: Mapping[
        str, Mapping[tuple[int, int], Sequence[LocalEdgeObservation]]
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
        name: {} for name in FLEXIBLE_CONTROLLER_FAMILY
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
    observations: Mapping[tuple[int, int], Sequence[LocalEdgeObservation]],
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


def classify_flexible_gate(
    *,
    integrity_checks: Mapping[str, bool],
    family_scientific_checks: Mapping[str, Mapping[str, bool]],
) -> dict[str, Any]:
    """Classify R360 with pre-registered OR semantics and false authorizations."""
    if not integrity_checks or not family_scientific_checks:
        raise ValueError("integrity and family checks must both be populated")
    if set(family_scientific_checks) != set(FLEXIBLE_CONTROLLER_FAMILY):
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
