"""Conclusion-affecting seams for the R359 causal residual study.

The probe turns the frozen R358 development partition into normalized targets
and owns the prospective three-way decision.  It does not load repository
artifacts, execute a simulator, fit from holdout data, or write a verdict.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from andes_rl_kundur.control.model_first_distributed_edge import (
    EndpointObservation,
    LocalEdgeObservation,
)
from andes_rl_kundur.control.neighbour_causal_residual import (
    AffineNeighbourResidualController,
    fit_affine_edge_controller,
)
from andes_rl_kundur.env.andes.model_first_contract import ACTION_EDGES


def _finite_matrix(values: object, *, columns: int, name: str) -> np.ndarray:
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] != columns or not np.all(np.isfinite(matrix)):
        raise ValueError(f"{name} must be a finite matrix with {columns} columns")
    return matrix


def reconstruct_causal_observations(
    *,
    frequency_hz_after_action: object,
    commanded_node_power_after_action: object,
    soc_after_action: object,
    voltage_after_action: object,
    executed_edge_flows_after_action: object,
    physical_contract: Any,
    nominal_frequency_hz: float,
    sample_period_seconds: float,
    startup_zero_steps: int,
) -> dict[tuple[int, int], tuple[LocalEdgeObservation, ...]]:
    """Reconstruct only edge observations with complete pre-action history."""

    frequency = _finite_matrix(
        frequency_hz_after_action,
        columns=4,
        name="frequency_hz_after_action",
    )
    commanded = _finite_matrix(
        commanded_node_power_after_action,
        columns=4,
        name="commanded_node_power_after_action",
    )
    soc = _finite_matrix(soc_after_action, columns=4, name="soc_after_action")
    voltage = _finite_matrix(
        voltage_after_action,
        columns=4,
        name="voltage_after_action",
    )
    edge_flows = _finite_matrix(
        executed_edge_flows_after_action,
        columns=3,
        name="executed_edge_flows_after_action",
    )
    horizon = frequency.shape[0]
    if any(values.shape[0] != horizon for values in (commanded, soc, voltage, edge_flows)):
        raise ValueError("trace arrays must share one horizon")
    nominal = float(nominal_frequency_hz)
    sample_period = float(sample_period_seconds)
    startup = int(startup_zero_steps)
    if not np.isfinite(nominal) or nominal <= 0.0:
        raise ValueError("nominal frequency must be positive and finite")
    if not np.isfinite(sample_period) or sample_period <= 0.0:
        raise ValueError("sample period must be positive and finite")
    if startup < 2 or startup >= horizon:
        raise ValueError("at least two startup rows must precede reconstructed observations")

    reconstructed: dict[tuple[int, int], list[LocalEdgeObservation]] = {
        edge: [] for edge in ACTION_EDGES
    }
    for step in range(startup, horizon):
        previous_index = step - 1
        frequency_before = frequency[previous_index]
        rocof = (frequency[previous_index] - frequency[previous_index - 1]) / sample_period
        previous_command = commanded[previous_index]
        current_soc = soc[previous_index]
        current_voltage = voltage[previous_index]
        lower, upper = physical_contract.feasible_power_bounds(
            previous_power_system_pu=previous_command,
            soc=current_soc,
            voltage_pu=current_voltage,
            dt_seconds=sample_period,
        )
        lower = np.asarray(lower, dtype=float)
        upper = np.asarray(upper, dtype=float)
        if (
            lower.shape != (4,)
            or upper.shape != (4,)
            or not np.all(np.isfinite(lower))
            or not np.all(np.isfinite(upper))
            or np.any(lower > upper)
        ):
            raise ValueError("physical contract returned invalid endpoint bounds")
        endpoints = {
            node_id: EndpointObservation(
                node_id=node_id,
                frequency_deviation_hz=float(frequency_before[node_id] - nominal),
                rocof_hz_s=float(rocof[node_id]),
                previous_command_system_pu=float(previous_command[node_id]),
                soc=float(current_soc[node_id]),
                voltage_pu=float(current_voltage[node_id]),
                lower_residual_power_system_pu=float(lower[node_id]),
                upper_residual_power_system_pu=float(upper[node_id]),
            )
            for node_id in range(4)
        }
        for edge_index, edge in enumerate(ACTION_EDGES):
            reconstructed[edge].append(
                LocalEdgeObservation(
                    edge=edge,
                    source=endpoints[edge[0]],
                    target=endpoints[edge[1]],
                    previous_edge_flow_system_pu=float(edge_flows[previous_index, edge_index]),
                )
            )
    return {edge: tuple(rows) for edge, rows in reconstructed.items()}


def build_observations_from_parent_inventory(
    *,
    inventory: Sequence[Mapping[str, Any]],
    physical_contract: Any,
    nominal_frequency_hz: float,
    sample_period_seconds: float,
    startup_zero_steps: int,
    expected_horizon: int,
) -> dict[str, dict[tuple[int, int], tuple[LocalEdgeObservation, ...]]]:
    """Adapt verified R352 selected-local rows to the exact public observation."""

    observations: dict[str, dict[tuple[int, int], tuple[LocalEdgeObservation, ...]]] = {}
    for parent in inventory:
        scenario_id = str(parent.get("scenario_id"))
        if not scenario_id or scenario_id in observations:
            raise ValueError("parent scenario identities must be unique and non-empty")
        arms = parent.get("arms")
        if not isinstance(arms, Mapping) or set(arms) != {"zero_edge", "selected_local"}:
            raise ValueError("parent must contain one exact zero/selected-local pair")
        selected = arms["selected_local"]
        if not isinstance(selected, Mapping):
            raise ValueError("selected-local parent arm is malformed")
        trace = selected.get("trace")
        if not isinstance(trace, Mapping):
            raise ValueError("selected-local trace is malformed")
        rows = trace.get("rows")
        if not isinstance(rows, Sequence) or len(rows) != int(expected_horizon):
            raise ValueError("selected-local trace horizon drift")
        try:
            frequency = [row["freq_hz_physical"] for row in rows]
            commanded = [row["bess_commanded_power_system_pu"] for row in rows]
            soc = [row["bess_soc"] for row in rows]
            voltage = [row["bess_bus_voltage_pu"] for row in rows]
            edge_flows = [row["executed_edge_flows_system_pu"] for row in rows]
        except (KeyError, TypeError) as error:
            raise ValueError("selected-local trace lacks a required causal field") from error
        observations[scenario_id] = reconstruct_causal_observations(
            frequency_hz_after_action=frequency,
            commanded_node_power_after_action=commanded,
            soc_after_action=soc,
            voltage_after_action=voltage,
            executed_edge_flows_after_action=edge_flows,
            physical_contract=physical_contract,
            nominal_frequency_hz=nominal_frequency_hz,
            sample_period_seconds=sample_period_seconds,
            startup_zero_steps=startup_zero_steps,
        )
    return observations


def _fit_controllers(
    *,
    training_scenario_ids: Sequence[str],
    observations_by_scenario: Mapping[
        str, Mapping[tuple[int, int], Sequence[LocalEdgeObservation]]
    ],
    normalized_targets_by_scenario: Mapping[str, object],
    horizon: int,
    startup_zero_steps: int,
) -> tuple[AffineNeighbourResidualController, ...]:
    controllers: list[AffineNeighbourResidualController] = []
    for edge_index, edge in enumerate(ACTION_EDGES):
        observations: list[LocalEdgeObservation] = []
        actions: list[float] = []
        for scenario_id in training_scenario_ids:
            scenario_observations = observations_by_scenario[scenario_id]
            if set(scenario_observations) != set(ACTION_EDGES):
                raise ValueError("every scenario must contain exactly three edge observations")
            edge_observations = tuple(scenario_observations[edge])
            if len(edge_observations) != horizon - startup_zero_steps:
                raise ValueError("observation rows do not match the reconstructible horizon")
            target = np.asarray(normalized_targets_by_scenario[scenario_id], dtype=float)
            if target.shape != (horizon, 3) or not np.all(np.isfinite(target)):
                raise ValueError("normalized target matrix has the wrong shape")
            if np.any(np.abs(target) > 1.0 + 1.0e-12):
                raise ValueError("normalized targets exceed the public action interval")
            if not np.array_equal(target[:startup_zero_steps], np.zeros((startup_zero_steps, 3))):
                raise ValueError("startup targets must be fixed to zero")
            observations.extend(edge_observations)
            actions.extend(target[startup_zero_steps:, edge_index].tolist())
        controllers.append(
            fit_affine_edge_controller(
                edge=edge,
                observations=observations,
                normalized_actions=actions,
            )
        )
    return tuple(controllers)


def leave_one_scenario_out_proposals(
    *,
    observations_by_scenario: Mapping[
        str, Mapping[tuple[int, int], Sequence[LocalEdgeObservation]]
    ],
    normalized_targets_by_scenario: Mapping[str, object],
    horizon: int,
    startup_zero_steps: int,
) -> dict[str, np.ndarray]:
    """Predict each development scenario without reading its target rows."""

    scenario_ids = tuple(sorted(str(item) for item in observations_by_scenario))
    if len(scenario_ids) < 3 or set(scenario_ids) != {
        str(item) for item in normalized_targets_by_scenario
    }:
        raise ValueError("leave-one-out requires at least three aligned scenarios")
    steps = int(horizon)
    startup = int(startup_zero_steps)
    if steps < 1 or startup < 0 or startup >= steps:
        raise ValueError("startup mask must lie within the positive horizon")

    proposals: dict[str, np.ndarray] = {}
    for heldout in scenario_ids:
        training_ids = tuple(item for item in scenario_ids if item != heldout)
        controllers = _fit_controllers(
            training_scenario_ids=training_ids,
            observations_by_scenario=observations_by_scenario,
            normalized_targets_by_scenario=normalized_targets_by_scenario,
            horizon=steps,
            startup_zero_steps=startup,
        )
        predicted = np.zeros((steps, 3), dtype=float)
        heldout_observations = observations_by_scenario[heldout]
        for edge_index, (edge, controller) in enumerate(
            zip(ACTION_EDGES, controllers, strict=True)
        ):
            rows = tuple(heldout_observations[edge])
            if len(rows) != steps - startup:
                raise ValueError("heldout observations do not match the horizon")
            predicted[startup:, edge_index] = [controller.act(row) for row in rows]
        proposals[heldout] = predicted
    return proposals


def fit_full_development_controllers(
    *,
    observations_by_scenario: Mapping[
        str, Mapping[tuple[int, int], Sequence[LocalEdgeObservation]]
    ],
    normalized_targets_by_scenario: Mapping[str, object],
    horizon: int,
    startup_zero_steps: int,
) -> tuple[AffineNeighbourResidualController, ...]:
    """Fit the one frozen formal map on every development scenario once."""

    scenario_ids = tuple(sorted(str(item) for item in observations_by_scenario))
    if not scenario_ids or set(scenario_ids) != {
        str(item) for item in normalized_targets_by_scenario
    }:
        raise ValueError("full fit requires aligned non-empty development scenarios")
    return _fit_controllers(
        training_scenario_ids=scenario_ids,
        observations_by_scenario=observations_by_scenario,
        normalized_targets_by_scenario=normalized_targets_by_scenario,
        horizon=int(horizon),
        startup_zero_steps=int(startup_zero_steps),
    )


def predict_with_frozen_controllers(
    *,
    controllers: Sequence[AffineNeighbourResidualController],
    observations: Mapping[tuple[int, int], Sequence[LocalEdgeObservation]],
    horizon: int,
    startup_zero_steps: int,
) -> np.ndarray:
    """Apply three fixed edge maps to one unlabelled causal scenario."""

    ordered = tuple(controllers)
    if tuple(controller.edge for controller in ordered) != ACTION_EDGES:
        raise ValueError("controllers must follow the exact three-edge order")
    if set(observations) != set(ACTION_EDGES):
        raise ValueError("one observation sequence is required for every edge")
    steps = int(horizon)
    startup = int(startup_zero_steps)
    if steps < 1 or startup < 0 or startup >= steps:
        raise ValueError("startup mask must lie within the positive horizon")
    proposal = np.zeros((steps, 3), dtype=float)
    for edge_index, controller in enumerate(ordered):
        rows = tuple(observations[controller.edge])
        if len(rows) != steps - startup:
            raise ValueError("unlabelled observations do not match the horizon")
        proposal[startup:, edge_index] = [controller.act(row) for row in rows]
    return proposal


def build_development_targets(
    *,
    scenario_ids: Sequence[str],
    candidate_results: Sequence[Mapping[str, Any]],
    inherited_infeasible_scenario_ids: Sequence[str],
    horizon: int,
    edge_flow_limit_system_pu: float,
    startup_zero_steps: int,
) -> dict[str, np.ndarray]:
    """Return exact normalized development labels with retained controls."""

    identities = tuple(str(item) for item in scenario_ids)
    if not identities or len(set(identities)) != len(identities):
        raise ValueError("development scenario identities must be unique")
    steps = int(horizon)
    startup = int(startup_zero_steps)
    limit = float(edge_flow_limit_system_pu)
    if steps < 1 or startup < 0 or startup > steps:
        raise ValueError("startup mask must lie within the positive horizon")
    if not np.isfinite(limit) or limit <= 0.0:
        raise ValueError("edge flow limit must be positive and finite")

    candidates: dict[str, Mapping[str, Any]] = {}
    for row in candidate_results:
        scenario_id = str(row.get("scenario_id"))
        if scenario_id in candidates:
            raise ValueError(f"duplicate candidate scenario: {scenario_id}")
        candidates[scenario_id] = row
    negative = {str(item) for item in inherited_infeasible_scenario_ids}
    if set(candidates) & negative or set(candidates) | negative != set(identities):
        raise ValueError("candidate and negative-control identities must partition development")

    targets: dict[str, np.ndarray] = {}
    for scenario_id in identities:
        if scenario_id in negative:
            normalized = np.zeros((steps, 3), dtype=float)
        else:
            row = candidates[scenario_id]
            if row.get("accepted") is not True or row.get("target_feasible") is not True:
                raise ValueError(f"candidate is not an accepted physical witness: {scenario_id}")
            actions = np.asarray(row.get("edge_actions"), dtype=float)
            if actions.shape != (steps, 3) or not np.all(np.isfinite(actions)):
                raise ValueError(f"candidate action shape is invalid: {scenario_id}")
            if np.any(np.abs(actions) > limit + 1.0e-12):
                raise ValueError(f"candidate exceeds the frozen edge limit: {scenario_id}")
            normalized = actions / limit
        normalized = np.asarray(normalized, dtype=float).copy()
        normalized[:startup] = 0.0
        targets[scenario_id] = normalized
    return targets


def classify_neighbour_causal_gate(
    *,
    integrity_checks: Mapping[str, bool],
    scientific_checks: Mapping[str, bool],
) -> dict[str, Any]:
    """Classify R359 while keeping every learning authorization false."""

    if not integrity_checks or not scientific_checks:
        raise ValueError("integrity and scientific checks must both be populated")
    failed_integrity = sorted(
        str(name) for name, passed in integrity_checks.items() if passed is not True
    )
    failed_scientific = sorted(
        str(name) for name, passed in scientific_checks.items() if passed is not True
    )
    if failed_integrity:
        classification = "ANALYSIS-INVALID"
    elif failed_scientific:
        classification = "NO-NEIGHBOUR-CAUSAL-HEADROOM"
    else:
        classification = "NEIGHBOUR-CAUSAL-PROBE-ELIGIBLE"
    return {
        "classification": classification,
        "failed_integrity_checks": failed_integrity,
        "failed_scientific_checks": failed_scientific,
        "physical_residual_probe_authorized": (classification == "NEIGHBOUR-CAUSAL-PROBE-ELIGIBLE"),
        "training_authorized": False,
        "simulation_authorized": False,
        "eval_authorized": False,
    }
