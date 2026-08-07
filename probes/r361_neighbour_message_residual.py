"""Conclusion-affecting seams for the R361 message-extended learnability gate.

The probe rebuilds the R359 exact causal observations, attaches the frozen
one-hop neighbour messages, fits the four pre-registered frozen non-neural map
families per edge, evaluates every family leave-one-scenario-out on
development rows, and owns the prospective four-way OR decision.  It does not
load repository artifacts, execute a simulator, fit from holdout data, or
write a verdict.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from andes_rl_kundur.control.model_first_distributed_edge import (
    EndpointObservation,
    LocalEdgeObservation,
)
from andes_rl_kundur.control.neighbour_message_residual import (
    MESSAGE_CONTROLLER_FAMILY,
    ONE_HOP_NEIGHBOUR_MESSAGES,
    MessageExtendedObservation,
)
from andes_rl_kundur.env.andes.model_first_contract import ACTION_EDGES

from probes import r359_neighbour_causal_residual as r359_probe


def _node_observation(
    edge_rows: Mapping[tuple[int, int], Sequence[LocalEdgeObservation]],
    node_id: int,
    step: int,
) -> EndpointObservation:
    """Return one node's endpoint observation at one causal step."""

    node = int(node_id)
    if node < 0 or node > 3:
        raise ValueError("node_id must lie in the frozen four-node plant")
    for edge, rows in edge_rows.items():
        if edge[0] == node:
            return rows[step].source
        if edge[1] == node:
            return rows[step].target
    raise ValueError(f"no observation row exposes node {node}")


def _verify_node_consistency(
    edge_rows: Mapping[tuple[int, int], Sequence[LocalEdgeObservation]],
    horizon: int,
) -> None:
    """Confirm every node's observation is identical across exposing edges."""

    for node_id in range(4):
        observed: dict[tuple[int, int], list[tuple[float, ...]]] = {}
        for edge, rows in edge_rows.items():
            if edge[0] == node_id or edge[1] == node_id:
                observed[edge] = []
                for row in rows:
                    endpoint = row.source if edge[0] == node_id else row.target
                    observed[edge].append(
                        (
                            endpoint.frequency_deviation_hz,
                            endpoint.rocof_hz_s,
                            endpoint.previous_command_system_pu,
                            endpoint.soc,
                            endpoint.voltage_pu,
                            endpoint.lower_residual_power_system_pu,
                            endpoint.upper_residual_power_system_pu,
                        )
                    )
        if not observed:
            raise ValueError(f"node {node_id} is not exposed by any action edge")
        reference = next(iter(observed.values()))
        if any(len(rows) != horizon for rows in observed.values()):
            raise ValueError("node observation rows must share one horizon")
        for edge, rows in observed.items():
            for step, (reference_row, row) in enumerate(zip(reference, rows, strict=True)):
                if row != reference_row:
                    raise ValueError(
                        f"node {node_id} observation diverges between edges at step {step}"
                    )


def build_message_observations_from_parent_inventory(
    *,
    inventory: Sequence[Mapping[str, Any]],
    physical_contract: Any,
    nominal_frequency_hz: float,
    sample_period_seconds: float,
    startup_zero_steps: int,
    expected_horizon: int,
) -> dict[str, dict[tuple[int, int], tuple[MessageExtendedObservation, ...]]]:
    """Rebuild exact R359 observations and attach frozen one-hop messages."""

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
    message_observations: dict[
        str, dict[tuple[int, int], tuple[MessageExtendedObservation, ...]]
    ] = {}
    for scenario_id, edge_rows in sorted(local_observations.items()):
        if set(edge_rows) != set(ACTION_EDGES):
            raise ValueError("every scenario must contain exactly three edge observations")
        _verify_node_consistency(edge_rows, steps - startup)
        extended: dict[tuple[int, int], list[MessageExtendedObservation]] = {
            edge: [] for edge in ACTION_EDGES
        }
        for edge in ACTION_EDGES:
            rows = edge_rows[edge]
            if len(rows) != steps - startup:
                raise ValueError("edge observation rows do not match the reconstructible horizon")
            source_neighbour_id, target_neighbour_id = ONE_HOP_NEIGHBOUR_MESSAGES[edge]
            for step in range(steps - startup):
                extended[edge].append(
                    MessageExtendedObservation(
                        edge=edge,
                        observation=rows[step],
                        source_neighbour=_node_observation(
                            edge_rows,
                            source_neighbour_id,
                            step,
                        ),
                        target_neighbour=_node_observation(
                            edge_rows,
                            target_neighbour_id,
                            step,
                        ),
                    )
                )
        message_observations[str(scenario_id)] = {
            edge: tuple(rows) for edge, rows in extended.items()
        }
    return message_observations


def _edge_observations(
    observations_by_scenario: Mapping[
        str, Mapping[tuple[int, int], Sequence[MessageExtendedObservation]]
    ],
    edge: tuple[int, int],
) -> list[MessageExtendedObservation]:
    rows: list[MessageExtendedObservation] = []
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
        str, Mapping[tuple[int, int], Sequence[MessageExtendedObservation]]
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
        name: {} for name in MESSAGE_CONTROLLER_FAMILY
    }
    for edge_index, edge in enumerate(ACTION_EDGES):
        observations: list[MessageExtendedObservation] = []
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
        for name, fitter in MESSAGE_CONTROLLER_FAMILY.items():
            family_controllers[name][edge] = fitter(
                edge=edge,
                observations=observations,
                normalized_actions=actions,
            )
    return family_controllers


def leave_one_scenario_out_family_proposals(
    *,
    observations_by_scenario: Mapping[
        str, Mapping[tuple[int, int], Sequence[MessageExtendedObservation]]
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
        name: {} for name in MESSAGE_CONTROLLER_FAMILY
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
    observations: Mapping[tuple[int, int], Sequence[MessageExtendedObservation]],
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


def classify_message_gate(
    *,
    integrity_checks: Mapping[str, bool],
    family_scientific_checks: Mapping[str, Mapping[str, bool]],
) -> dict[str, Any]:
    """Classify R361 with pre-registered four-way OR semantics."""

    if not integrity_checks or not family_scientific_checks:
        raise ValueError("integrity and family checks must both be populated")
    if set(family_scientific_checks) != set(MESSAGE_CONTROLLER_FAMILY):
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
