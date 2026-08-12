"""Pure construction gate for the R380 four-control/three-load source model."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from andes_rl_kundur.evaluation.model_first_input_bridge import (
    SampledInputModel,
    fold_zero_time_constant_states,
    post_step_sampled_realization,
    reduce_folded_descriptor,
)
from andes_rl_kundur.evaluation.vsg_energy_port_source_adapter import (
    AndesVSGEnergyPortDescriptorSnapshot,
)
from andes_rl_kundur.evaluation.vsg_energy_port_source_bridge import (
    VSGEnergyPortInputBridge,
)

_STEPS = (1.0e-4, 1.0e-5, 1.0e-6)


@dataclass(frozen=True)
class VSGEnergyPortSourceModelResult:
    """One source-model construction result with no trajectory evidence."""

    passed: bool
    sampled_model: SampledInputModel | None
    metrics: dict[str, object]
    dynamic_state_names: list[str]
    error: str | None


def _relative_column_differences(
    previous_f: np.ndarray,
    previous_g: np.ndarray,
    current_f: np.ndarray,
    current_g: np.ndarray,
) -> list[float]:
    previous = np.vstack((previous_f, previous_g))
    current = np.vstack((current_f, current_g))
    return [
        float(
            np.linalg.norm(current[:, column] - previous[:, column])
            / max(np.linalg.norm(previous[:, column]), 1.0e-12)
        )
        for column in range(previous.shape[1])
    ]


def _failure(
    *,
    metrics: dict[str, object],
    error: str,
    dynamic_state_names: list[str] | None = None,
) -> VSGEnergyPortSourceModelResult:
    return VSGEnergyPortSourceModelResult(
        passed=False,
        sampled_model=None,
        metrics=metrics,
        dynamic_state_names=dynamic_state_names or [],
        error=error,
    )


def construct_vsg_energy_port_source_model(
    *,
    snapshot: AndesVSGEnergyPortDescriptorSnapshot,
    bridges: tuple[
        VSGEnergyPortInputBridge,
        VSGEnergyPortInputBridge,
        VSGEnergyPortInputBridge,
    ],
) -> VSGEnergyPortSourceModelResult:
    """Apply the frozen derivative, descriptor, sampling, and rank gates."""

    metrics: dict[str, object] = {}
    if tuple(float(bridge.control.step) for bridge in bridges) != _STEPS or tuple(
        float(bridge.disturbance.step) for bridge in bridges
    ) != _STEPS:
        return _failure(metrics=metrics, error="finite-difference step order drift")
    provenance = {
        (
            bridge.provenance.vsg_port_ids,
            bridge.provenance.pq_load_ids,
            bridge.provenance.source_fingerprint,
        )
        for bridge in bridges
    }
    if len(provenance) != 1:
        return _failure(metrics=metrics, error="source identity drift across difference steps")

    control_differences: list[list[float]] = []
    disturbance_differences: list[list[float]] = []
    for previous, current in zip(bridges[:-1], bridges[1:], strict=True):
        control_differences.append(
            _relative_column_differences(
                previous.control.f_input,
                previous.control.g_input,
                current.control.f_input,
                current.control.g_input,
            )
        )
        disturbance_differences.append(
            _relative_column_differences(
                previous.disturbance.f_input,
                previous.disturbance.g_input,
                current.disturbance.f_input,
                current.disturbance.g_input,
            )
        )
    maximum_relative_difference = max(
        value
        for family in (control_differences, disturbance_differences)
        for adjacent_pair in family
        for value in adjacent_pair
    )
    maximum_midpoint_ratio = max(
        float(np.max(jacobians.midpoint_ratios))
        for bridge in bridges
        for jacobians in (bridge.control, bridge.disturbance)
    )
    metrics.update(
        {
            "control_relative_column_differences": control_differences,
            "disturbance_relative_column_differences": disturbance_differences,
            "maximum_relative_column_difference": maximum_relative_difference,
            "maximum_midpoint_ratio": maximum_midpoint_ratio,
            "selected_step_system_pu": _STEPS[-1],
        }
    )
    if maximum_relative_difference > 1.0e-5 or maximum_midpoint_ratio > 1.0e-6:
        return _failure(
            metrics=metrics,
            error="finite-difference input columns did not converge",
        )

    selected = bridges[-1]
    joint_f = selected.joint_f_input
    joint_g = selected.joint_g_input
    try:
        folded = fold_zero_time_constant_states(
            time_constants=snapshot.time_constants,
            f_x=snapshot.f_x,
            f_y=snapshot.f_y,
            g_x=snapshot.g_x,
            g_y=snapshot.g_y,
            f_input=joint_f,
            g_input=joint_g,
        )
        reduced = reduce_folded_descriptor(
            folded,
            minimum_reciprocal_condition=1.0e-12,
        )
    except (ValueError, np.linalg.LinAlgError) as error:
        return _failure(
            metrics=metrics,
            error=f"descriptor reduction failed: {type(error).__name__}: {error}",
        )

    dynamic_names = [
        snapshot.state_names[int(index)] for index in folded.dynamic_state_indices
    ]
    state_names_match = dynamic_names == snapshot.eig_state_names
    state_shape_match = reduced.state_matrix.shape == snapshot.eig_state_matrix.shape
    if state_names_match and state_shape_match:
        state_difference = reduced.state_matrix - snapshot.eig_state_matrix
        state_relative_error = float(
            np.linalg.norm(state_difference)
            / max(np.linalg.norm(snapshot.eig_state_matrix), 1.0e-12)
        )
        state_maximum_error = float(np.max(np.abs(state_difference)))
    else:
        state_relative_error = None
        state_maximum_error = None
    folded_output_norm = float(
        np.linalg.norm(snapshot.frequency_output_map[:, folded.folded_state_indices])
    )
    metrics.update(
        {
            "dynamic_state_names_match_eig": state_names_match,
            "state_matrix_shape_match_eig": state_shape_match,
            "state_matrix_relative_frobenius_error": state_relative_error,
            "state_matrix_maximum_absolute_error": state_maximum_error,
            "algebraic_reciprocal_condition": reduced.algebraic_reciprocal_condition,
            "folded_frequency_output_norm": folded_output_norm,
        }
    )
    if (
        not state_names_match
        or not state_shape_match
        or (state_relative_error is not None and state_relative_error > 1.0e-8)
        or (state_maximum_error is not None and state_maximum_error > 1.0e-9)
        or reduced.algebraic_reciprocal_condition < 1.0e-12
        or folded_output_norm != 0.0
    ):
        return _failure(
            metrics=metrics,
            dynamic_state_names=dynamic_names,
            error="descriptor model did not reconcile with installed ANDES",
        )

    sampled = post_step_sampled_realization(
        state_matrix=reduced.state_matrix,
        input_matrix=reduced.input_matrix,
        output_matrix=snapshot.frequency_output_map[:, folded.dynamic_state_indices],
        feedthrough_matrix=np.zeros((4, 7), dtype=float),
        sample_period_seconds=0.2,
    )
    control_input = sampled.input_matrix[:, :4]
    control_feedthrough = sampled.feedthrough_matrix[:, :4]
    markov_blocks = [control_feedthrough]
    state_power = np.eye(sampled.state_matrix.shape[0])
    for _lag in range(1, 25):
        markov_blocks.append(sampled.output_matrix @ state_power @ control_input)
        state_power = state_power @ sampled.state_matrix
    markov_stack = np.vstack(markov_blocks)
    singular_values = np.linalg.svd(markov_stack, compute_uv=False)
    tolerance = (
        max(markov_stack.shape)
        * np.finfo(float).eps
        * (float(singular_values[0]) if singular_values.size else 0.0)
    )
    control_rank = int(np.sum(singular_values > tolerance))
    metrics.update(
        {
            "control_markov_horizon": 25,
            "control_markov_rank": control_rank,
            "control_markov_rank_tolerance": tolerance,
            "control_markov_singular_values": singular_values.tolist(),
            "sampled_spectral_radius": sampled.spectral_radius,
        }
    )
    if control_rank != 4:
        return _failure(
            metrics=metrics,
            dynamic_state_names=dynamic_names,
            error="four-channel finite-horizon control authority failed",
        )
    return VSGEnergyPortSourceModelResult(
        passed=True,
        sampled_model=sampled,
        metrics=metrics,
        dynamic_state_names=dynamic_names,
        error=None,
    )
