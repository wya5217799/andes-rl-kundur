"""Independent optimality acceptance layer for the R348 residual solver."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from probes.r345_residual_headroom import ResidualSolveResult, endpoint_values
from probes.r348_fully_normalized_residual import (
    solve_fully_normalized_minimum_norm_edge_residual,
)

from andes_rl_kundur.control.minimum_norm_certificate import (
    MinimumNormCertificate,
    certify_convex_minimum_norm,
)
from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.env.andes.model_first_contract import active_power_incidence


@dataclass(frozen=True)
class CertifiedResidualSolveResult:
    """One R348 candidate plus its solver-independent certificate."""

    solution: ResidualSolveResult
    certificate: MinimumNormCertificate | None
    base_optimizer_valid: bool


def _advance_soc_path(
    initial_soc: np.ndarray,
    node_commands: np.ndarray,
    limits: FeedbackLimits,
) -> np.ndarray:
    factor = limits.sample_period_seconds * limits.system_mva / (3600.0 * limits.energy_mwh)
    path = np.empty((node_commands.shape[0] + 1, 4))
    path[0] = initial_soc
    for step, command in enumerate(node_commands):
        delta = np.where(
            command >= 0.0,
            -factor * command / limits.discharge_efficiency,
            -factor * command * limits.charge_efficiency,
        )
        path[step + 1] = path[step] + delta
    return path


def solve_certified_fully_normalized_minimum_norm_edge_residual(
    *,
    base_outputs: object,
    base_node_commands: object,
    previous_node_command: object,
    initial_soc: object,
    response_map: object,
    limits: FeedbackLimits = FeedbackLimits(),
    minimum_improvement_fraction: float,
    maximum_iterations: int,
    function_tolerance: float,
    feasibility_tolerance: float,
) -> CertifiedResidualSolveResult:
    """Certify the unchanged R348 candidate without changing or restarting it."""

    base = solve_fully_normalized_minimum_norm_edge_residual(
        base_outputs=base_outputs,
        base_node_commands=base_node_commands,
        previous_node_command=previous_node_command,
        initial_soc=initial_soc,
        response_map=response_map,
        limits=limits,
        minimum_improvement_fraction=minimum_improvement_fraction,
        maximum_iterations=maximum_iterations,
        function_tolerance=function_tolerance,
        feasibility_tolerance=feasibility_tolerance,
    )
    if not base.target_feasible:
        return CertifiedResidualSolveResult(
            solution=base,
            certificate=None,
            base_optimizer_valid=bool(base.optimizer_valid),
        )

    outputs = np.asarray(base_outputs, dtype=float)
    commands = np.asarray(base_node_commands, dtype=float)
    previous = np.asarray(previous_node_command, dtype=float)
    soc0 = np.asarray(initial_soc, dtype=float)
    response = np.asarray(response_map, dtype=float)
    edges = np.asarray(base.edge_actions, dtype=float)
    steps = outputs.shape[0]
    action_scale = float(limits.node_ramp)
    soc_scale = float(limits.maximum_soc - limits.minimum_soc)
    tolerance = float(feasibility_tolerance)
    baseline_values = endpoint_values(
        outputs,
        sample_period_seconds=limits.sample_period_seconds,
    )
    baseline = np.asarray(
        [
            baseline_values["common_coordinate_iae"],
            baseline_values["differential_coordinate_energy"],
        ]
    )
    targets = (1.0 - float(minimum_improvement_fraction)) * baseline
    incidence = np.asarray(active_power_incidence(), dtype=float)

    def decode_scaled(
        scaled_values: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        decoded_edges = (action_scale * scaled_values).reshape(steps, 3)
        residual_nodes = decoded_edges @ incidence.T
        total_commands = commands + residual_nodes
        counterfactual = outputs + (response @ decoded_edges.reshape(-1)).reshape(steps, 4)
        soc_path = _advance_soc_path(soc0, total_commands, limits)
        return decoded_edges, residual_nodes, total_commands, counterfactual, soc_path

    def constraint_blocks(
        scaled_values: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        _decoded, _residual, total, counterfactual, soc_path = decode_scaled(scaled_values)
        endpoints = endpoint_values(
            counterfactual,
            sample_period_seconds=limits.sample_period_seconds,
        )
        endpoint_slacks = targets - np.asarray(
            [
                endpoints["common_coordinate_iae"],
                endpoints["differential_coordinate_energy"],
            ]
        )
        ramps = np.vstack((total[:1] - previous.reshape(1, 4), np.diff(total, axis=0)))
        return (
            endpoint_slacks,
            (limits.node_power - np.abs(total)).reshape(-1),
            (limits.node_ramp - np.abs(ramps)).reshape(-1),
            (soc_path[1:] - limits.minimum_soc).reshape(-1),
            (limits.maximum_soc - soc_path[1:]).reshape(-1),
        )

    def convex_constraints_scaled(scaled_values: np.ndarray) -> np.ndarray:
        endpoint, power, ramp, soc_lower, _soc_upper = constraint_blocks(scaled_values)
        return np.concatenate(
            (
                endpoint / baseline,
                power / limits.node_power,
                ramp / limits.node_ramp,
                soc_lower / soc_scale,
            )
        )

    scaled_candidate = edges.reshape(-1) / action_scale
    endpoint, power, ramp, soc_lower, soc_upper = constraint_blocks(scaled_candidate)
    original_slacks = np.concatenate((endpoint, power, ramp, soc_lower, soc_upper))
    maximum_residual = float(max(0.0, -float(np.min(original_slacks))))
    finite = bool(
        np.all(np.isfinite(scaled_candidate))
        and np.all(np.isfinite(original_slacks))
        and np.isfinite(base.objective_value)
    )
    certificate = certify_convex_minimum_norm(
        point=scaled_candidate,
        constraint_function=convex_constraints_scaled,
        feasibility_tolerance=tolerance,
        nonconvex_constraint_slacks=soc_upper / soc_scale,
    )
    accepted = bool(finite and maximum_residual <= tolerance and certificate.valid)
    decoded_edges, residual_nodes, total_commands, counterfactual, soc_path = decode_scaled(
        scaled_candidate
    )
    solution = ResidualSolveResult(
        feasible=accepted,
        optimizer_valid=accepted,
        target_feasible=True,
        edge_actions=decoded_edges,
        residual_node_actions=residual_nodes,
        counterfactual_node_commands=total_commands,
        counterfactual_outputs=counterfactual,
        counterfactual_soc=soc_path,
        objective_value=float(decoded_edges.reshape(-1) @ decoded_edges.reshape(-1)),
        solver_iterations=int(base.solver_iterations),
        maximum_constraint_residual=maximum_residual,
        maximum_target_shortfall=float(max(0.0, -float(np.min(endpoint)))),
        message=f"{base.message}; independent certificate: {certificate.reason}",
    )
    return CertifiedResidualSolveResult(
        solution=solution,
        certificate=certificate,
        base_optimizer_valid=bool(base.optimizer_valid),
    )
