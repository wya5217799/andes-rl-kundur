"""Pure analysis for the sealed R339 full-DAE input-bridge extraction."""

from __future__ import annotations

from typing import Any

import numpy as np

from andes_rl_kundur.env.andes.model_first_contract import (
    stage1_power_coordinates,
)
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    simulate_state_space,
)
from andes_rl_kundur.evaluation.model_first_input_bridge import (
    fit_normalized_era_realization,
    fold_zero_time_constant_states,
    post_step_sampled_realization,
    reduce_folded_descriptor,
)


def _finite(values: object, *, name: str, ndim: int) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != ndim or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite {ndim}-dimensional array")
    return array


def _relative_fro(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right) / max(np.linalg.norm(right), 1.0e-12))


def analyse_derivative_family(
    payload: dict[str, Any],
    *,
    relative_tolerance: float,
    midpoint_tolerance: float,
) -> dict[str, Any]:
    """Check the frozen three-scale derivative convergence contract."""

    steps = payload.get("steps")
    if not isinstance(steps, list) or len(steps) != 3:
        raise ValueError("input derivative family must contain three steps")
    expected_steps = [1.0e-4, 1.0e-5, 1.0e-6]
    derivatives: list[np.ndarray] = []
    midpoint_maxima: list[float] = []
    branch_passes: list[bool] = []
    for row, expected in zip(steps, expected_steps, strict=True):
        if float(row.get("step_system_pu", -1.0)) != expected:
            raise ValueError("finite-difference step order drift")
        f_input = _finite(row.get("f_input"), name="f_input", ndim=2)
        g_input = _finite(row.get("g_input"), name="g_input", ndim=2)
        if f_input.shape[1] != g_input.shape[1]:
            raise ValueError("f/g input derivative column mismatch")
        derivatives.append(np.vstack([f_input, g_input]))
        midpoint = _finite(row.get("midpoint_ratios"), name="midpoint_ratios", ndim=1)
        if midpoint.shape != (f_input.shape[1],):
            raise ValueError("midpoint ratio count does not match input columns")
        midpoint_maxima.append(float(np.max(midpoint)))
        branch_passes.append(row.get("all_branch_snapshots_match") is True)
    relative_differences = [
        _relative_fro(derivatives[index + 1], derivatives[index]) for index in range(2)
    ]
    integrity_pass = bool(payload.get("restored_exactly") is True and all(branch_passes))
    convergence_pass = bool(
        max(midpoint_maxima) <= midpoint_tolerance
        and max(relative_differences) <= relative_tolerance
    )
    passed = integrity_pass and convergence_pass
    return {
        "pass": passed,
        "integrity_pass": integrity_pass,
        "convergence_pass": convergence_pass,
        "relative_frobenius_differences": relative_differences,
        "maximum_midpoint_ratio": max(midpoint_maxima),
        "all_branch_snapshots_match": all(branch_passes),
        "restored_exactly": payload.get("restored_exactly") is True,
        "selected_step_system_pu": expected_steps[-1],
        "selected_f_input": steps[-1]["f_input"],
        "selected_g_input": steps[-1]["g_input"],
    }


def trajectory_metrics(prediction: object, truth: object) -> dict[str, float]:
    """Return the R336 normalized trajectory and peak-vector residuals."""

    predicted = _finite(prediction, name="prediction", ndim=2)
    observed = _finite(truth, name="truth", ndim=2)
    if predicted.shape != observed.shape:
        raise ValueError("prediction and truth shapes differ")
    error = predicted - observed
    return {
        "nrmse": float(np.linalg.norm(error) / max(np.linalg.norm(observed), 1.0e-15)),
        "peak_vector_residual": float(
            np.max(np.linalg.norm(error, axis=1))
            / max(np.max(np.linalg.norm(observed, axis=1)), 1.0e-15)
        ),
    }


def classify_r339(
    *,
    validity_pass: bool,
    descriptor_pass: bool,
    linearization_pass: bool,
    reduction_pass: bool,
) -> str:
    """Apply the frozen first-failure outcome tree."""

    if not validity_pass:
        return "INVALID"
    if not descriptor_pass:
        return "BLOCK-DESCRIPTOR"
    if not linearization_pass:
        return "BLOCK-LINEARIZATION"
    if not reduction_pass:
        return "QUALIFY-MECHANISM"
    return "ALLOW-CANDIDATE"


def _markov(realization: Any, steps: int) -> np.ndarray:
    output_count = realization.output_matrix.shape[0]
    input_count = realization.input_matrix.shape[1]
    tensor = np.zeros((steps, output_count, input_count), dtype=float)
    tensor[0] = realization.feedthrough_matrix
    power = np.eye(realization.state_matrix.shape[0])
    for index in range(1, steps):
        tensor[index] = realization.output_matrix @ power @ realization.input_matrix
        power = power @ realization.state_matrix
    return tensor


def _point_records(execution: dict[str, Any]) -> dict[str, dict[str, Any]]:
    points = execution.get("points")
    if not isinstance(points, list) or len(points) != 2:
        raise ValueError("R339 execution must contain two combined points")
    indexed = {str(row.get("point")): row for row in points}
    if set(indexed) != {"HS0", "HS1"}:
        raise ValueError("R339 point inventory mismatch")
    return indexed


def _r336_records(
    development: dict[str, Any],
    exposed_second_point: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    indexed = {
        str(development.get("operating_point")): development.get("records"),
        str(exposed_second_point.get("operating_point")): exposed_second_point.get("records"),
    }
    if set(indexed) != {"HS0", "HS1"} or not all(
        isinstance(rows, list) and len(rows) == 17 for rows in indexed.values()
    ):
        raise ValueError("R336 exposed-record inventory mismatch")
    return indexed


def analyse_r339_input_bridge(
    execution: dict[str, Any],
    r336_development: dict[str, Any],
    r336_second_point: dict[str, Any],
    r336_analysis: dict[str, Any],
) -> dict[str, Any]:
    """Analyse the sealed extraction without opening a fresh trajectory bank."""

    points = _point_records(execution)
    old_records = _r336_records(r336_development, r336_second_point)
    process_guard = bool(
        execution.get("job_count") == 16
        and execution.get("unique_process_count") == 16
        and execution.get("fresh_nonlinear_trajectory_executed") is False
        and execution.get("controller_executed") is False
        and execution.get("training_executed") is False
        and execution.get("eval_executed") is False
    )
    point_results: dict[str, dict[str, Any]] = {}
    all_validity = process_guard
    all_descriptor = True
    all_linearization = True
    all_reduction = True

    node_vectors = stage1_power_coordinates(1.0)
    node_basis = np.column_stack(
        [node_vectors[name] for name in ("common", "edge_0", "edge_1", "edge_2")]
    )
    input_scales = np.concatenate([1.0 / np.linalg.norm(node_basis, axis=0), np.ones(4)])

    for point_name in ("HS0", "HS1"):
        point = points[point_name]
        base = dict(point["base_snapshot"])
        control = analyse_derivative_family(
            dict(point["control_input_derivatives"]),
            relative_tolerance=1.0e-5,
            midpoint_tolerance=1.0e-6,
        )
        load = analyse_derivative_family(
            dict(point["load_input_derivatives"]),
            relative_tolerance=1.0e-5,
            midpoint_tolerance=1.0e-6,
        )
        base_f = _finite(base["f"], name="base f", ndim=1)
        base_g = _finite(base["g"], name="base g", ndim=1)
        equilibrium_residual = max(float(np.max(np.abs(base_f))), float(np.max(np.abs(base_g))))
        validity = bool(
            control["integrity_pass"]
            and load["integrity_pass"]
            and equilibrium_residual <= 1.0e-8
            and base.get("line_8_in_service") is True
            and bool(base.get("g4", [False])[0])
        )
        all_validity = all_validity and validity

        f_input = np.hstack(
            [
                _finite(control["selected_f_input"], name="control f", ndim=2),
                _finite(load["selected_f_input"], name="load f", ndim=2),
            ]
        )
        g_input = np.hstack(
            [
                _finite(control["selected_g_input"], name="control g", ndim=2),
                _finite(load["selected_g_input"], name="load g", ndim=2),
            ]
        )
        folded = fold_zero_time_constant_states(
            time_constants=base["Tf"],
            f_x=base["f_x"],
            f_y=base["f_y"],
            g_x=base["g_x"],
            g_y=base["g_y"],
            f_input=f_input,
            g_input=g_input,
        )
        descriptor_error: str | None = None
        state_relative_error: float | None = None
        state_maximum_error: float | None = None
        algebraic_reciprocal_condition = 0.0
        row_norms_equal = False
        state_names_match = False
        try:
            reduced = reduce_folded_descriptor(folded, minimum_reciprocal_condition=1.0e-12)
            dynamic_names = [
                str(base["state_names"][index]) for index in folded.dynamic_state_indices
            ]
            eig_names = [str(value) for value in base["eig_state_names"]]
            state_names_match = dynamic_names == eig_names
            eig_state = _finite(base["eig_state_matrix"], name="EIG state matrix", ndim=2)
            if reduced.state_matrix.shape == eig_state.shape and state_names_match:
                state_relative_error = _relative_fro(reduced.state_matrix, eig_state)
                state_maximum_error = float(np.max(np.abs(reduced.state_matrix - eig_state)))
            output_raw = _finite(base["output_map"], name="output map", ndim=2)
            folded_output_norm = float(np.linalg.norm(output_raw[:, folded.folded_state_indices]))
            if folded_output_norm > 0.0:
                raise ValueError("frequency output depends on a folded zero-Tf state")
            output_matrix = output_raw[:, folded.dynamic_state_indices]
            row_norms = np.linalg.norm(
                _finite(base["coordinate_forward"], name="coordinate map", ndim=2),
                axis=1,
            )
            row_norms_equal = bool(np.allclose(row_norms, row_norms[0], rtol=1.0e-12, atol=1.0e-12))
            descriptor_pass = bool(
                control["convergence_pass"]
                and load["convergence_pass"]
                and state_names_match
                and state_relative_error is not None
                and state_relative_error <= 1.0e-8
                and state_maximum_error is not None
                and state_maximum_error <= 1.0e-9
                and reduced.algebraic_reciprocal_condition >= 1.0e-12
                and row_norms_equal
            )
            algebraic_reciprocal_condition = reduced.algebraic_reciprocal_condition
        except (ValueError, np.linalg.LinAlgError) as error:
            descriptor_error = f"{type(error).__name__}: {error}"
            descriptor_pass = False
        all_descriptor = all_descriptor and descriptor_pass

        nonlinear_metrics: dict[str, dict[str, float]] = {}
        internal_metrics: dict[str, dict[str, float]] = {}
        spectral_radius: float | None = None
        if descriptor_pass:
            physical_input = reduced.input_matrix.copy()
            physical_input[:, :4] = physical_input[:, :4] @ node_basis
            sampled = post_step_sampled_realization(
                state_matrix=reduced.state_matrix,
                input_matrix=physical_input,
                output_matrix=output_matrix,
                feedthrough_matrix=np.zeros((4, 8)),
                sample_period_seconds=0.2,
            )
            full_markov = _markov(sampled, 25)
            reduced12 = fit_normalized_era_realization(
                full_markov,
                input_scales=input_scales,
                output_scales=np.ones(4),
                order=12,
                block_rows=8,
                block_columns=8,
            )
            spectral_radius = reduced12.spectral_radius
            reduced_markov = _markov(reduced12, 25)
            for channel in range(8):
                internal_metrics[str(channel)] = trajectory_metrics(
                    reduced_markov[:, :, channel], full_markov[:, :, channel]
                )
            reduction_pass = bool(
                spectral_radius < 1.0
                and all(
                    row["nrmse"] <= 0.10 and row["peak_vector_residual"] <= 0.10
                    for row in internal_metrics.values()
                )
            )
            zero_record = next(row for row in old_records[point_name] if row["channel"] == "zero")
            zero_output = _finite(zero_record["output_coordinates"], name="zero output", ndim=2)
            load_channel_index = {
                "PQ_0": 0,
                "PQ_1": 1,
                "PQ_Bus14": 2,
                "PQ_Bus15": 3,
            }
            for row in old_records[point_name]:
                channel_name = str(row["channel"])
                if channel_name == "zero":
                    continue
                profile = _finite(row["delta_profile_system_pu"], name="load profile", ndim=1)
                inputs = np.zeros((profile.size, 8), dtype=float)
                inputs[:, 4 + load_channel_index[channel_name]] = profile
                prediction = simulate_state_space(sampled, inputs)
                truth = (
                    _finite(row["output_coordinates"], name="nonlinear output", ndim=2)
                    - zero_output
                )
                key = "/".join([point_name, channel_name, str(row["shape"]), str(row["sign"])])
                nonlinear_metrics[key] = trajectory_metrics(prediction, truth)
            linearization_pass = all(
                row["nrmse"] <= 0.15 and row["peak_vector_residual"] <= 0.20
                for row in nonlinear_metrics.values()
            )
        else:
            linearization_pass = False
            reduction_pass = False
        all_linearization = all_linearization and linearization_pass
        all_reduction = all_reduction and reduction_pass
        point_results[point_name] = {
            "validity_pass": validity,
            "derivative_guards": {"control": control, "load": load},
            "equilibrium_residual_absolute_maximum": equilibrium_residual,
            "descriptor_pass": descriptor_pass,
            "descriptor_error": descriptor_error,
            "state_names_match": state_names_match,
            "state_matrix_relative_frobenius_error": state_relative_error,
            "state_matrix_maximum_absolute_error": state_maximum_error,
            "algebraic_reciprocal_condition": algebraic_reciprocal_condition,
            "output_row_norms_equal": row_norms_equal,
            "linearization_pass": linearization_pass,
            "nonlinear_record_metrics": nonlinear_metrics,
            "reduction_pass": reduction_pass,
            "order12_spectral_radius": spectral_radius,
            "full_to_order12_metrics": internal_metrics,
        }

    old_static_failed = bool(
        r336_analysis.get("classification") == "BLOCK"
        and any(
            float(row.get("total_nrmse", 0.0)) > 0.15
            or float(row.get("peak_vector_residual", 0.0)) > 0.20
            for row in r336_analysis.get("record_metrics", {}).values()
        )
    )
    classification = classify_r339(
        validity_pass=all_validity,
        descriptor_pass=all_descriptor,
        linearization_pass=all_linearization,
        reduction_pass=all_reduction,
    )
    return {
        "classification": classification,
        "validity_guards": {
            "sixteen_process_execution": process_guard,
            "all_point_validity": all_validity,
            "old_static_bridge_failed_registered_R336_envelope": old_static_failed,
            "fresh_nonlinear_trajectory_executed": False,
            "controller_executed": False,
            "training_executed": False,
            "eval_executed": False,
        },
        "descriptor_gate_pass": all_descriptor,
        "linearization_gate_pass": all_linearization,
        "order12_reduction_gate_pass": all_reduction,
        "points": point_results,
        "claim_ceiling": (
            "development diagnosis of the separate physical input bridge only; "
            "no fresh validation, controller, distributed-agent, learning, "
            "stability, safety, or generalization claim"
        ),
    }
