"""Pure construction and analysis for R341 staged fresh validation."""

from __future__ import annotations

from typing import Any

import numpy as np
from probes.r339_input_bridge_diagnosis import (
    analyse_derivative_family,
    trajectory_metrics,
)

from andes_rl_kundur.env.andes.model_first_contract import stage1_power_coordinates
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    StateSpaceRealization,
    simulate_state_space,
)
from andes_rl_kundur.evaluation.model_first_input_bridge import (
    fit_normalized_era_realization,
    fold_zero_time_constant_states,
    post_step_sampled_realization,
    reduce_folded_descriptor,
)

POINT_NAMES = ("FV0", "FV1")
LOAD_CHANNELS = {
    "PQ_0": 0,
    "PQ_1": 1,
    "PQ_Bus14": 2,
    "PQ_Bus15": 3,
}


def _finite(values: object, *, name: str, ndim: int) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != ndim or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite {ndim}-dimensional array")
    return array


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _relative_fro(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right) / max(np.linalg.norm(right), 1.0e-12))


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


def _realization_payload(realization: Any) -> dict[str, Any]:
    payload = {
        "state_matrix": realization.state_matrix,
        "input_matrix": realization.input_matrix,
        "output_matrix": realization.output_matrix,
        "feedthrough_matrix": realization.feedthrough_matrix,
        "spectral_radius": realization.spectral_radius,
    }
    retained = getattr(realization, "retained_singular_values", None)
    if retained is not None:
        payload["retained_singular_values"] = retained
    return _jsonable(payload)


def realization_from_payload(payload: dict[str, Any]) -> StateSpaceRealization:
    """Recreate a zero-state predictor from one persisted R340 payload."""

    state = _finite(payload.get("state_matrix"), name="state matrix", ndim=2)
    inputs = _finite(payload.get("input_matrix"), name="input matrix", ndim=2)
    outputs = _finite(payload.get("output_matrix"), name="output matrix", ndim=2)
    feedthrough = _finite(payload.get("feedthrough_matrix"), name="feedthrough matrix", ndim=2)
    retained = np.asarray(payload.get("retained_singular_values", []), dtype=float)
    if retained.ndim != 1 or not np.all(np.isfinite(retained)):
        raise ValueError("retained singular values must be a finite vector")
    return StateSpaceRealization(
        state_matrix=state,
        input_matrix=inputs,
        output_matrix=outputs,
        feedthrough_matrix=feedthrough,
        retained_singular_values=retained,
    )


def build_point_candidate(point: dict[str, Any]) -> dict[str, Any]:
    """Apply the frozen R339 construction to one untouched equilibrium."""

    point_name = str(point.get("point"))
    result: dict[str, Any] = {
        "point": point_name,
        "base_snapshot_sha256": point.get("base_snapshot_sha256"),
        "construction_pass": False,
    }
    try:
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
        physical_validity = bool(
            control["integrity_pass"]
            and load["integrity_pass"]
            and equilibrium_residual <= 1.0e-8
            and base.get("line_8_in_service") is True
            and bool(base.get("g4", [False])[0])
        )

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
        reduced = reduce_folded_descriptor(folded, minimum_reciprocal_condition=1.0e-12)
        dynamic_names = [str(base["state_names"][index]) for index in folded.dynamic_state_indices]
        eig_names = [str(value) for value in base["eig_state_names"]]
        state_names_match = dynamic_names == eig_names
        eig_state = _finite(base["eig_state_matrix"], name="EIG state", ndim=2)
        state_relative_error = (
            _relative_fro(reduced.state_matrix, eig_state)
            if reduced.state_matrix.shape == eig_state.shape and state_names_match
            else float("inf")
        )
        state_maximum_error = (
            float(np.max(np.abs(reduced.state_matrix - eig_state)))
            if reduced.state_matrix.shape == eig_state.shape and state_names_match
            else float("inf")
        )
        output_raw = _finite(base["output_map"], name="output map", ndim=2)
        folded_output_norm = float(np.linalg.norm(output_raw[:, folded.folded_state_indices]))
        output_matrix = output_raw[:, folded.dynamic_state_indices]
        coordinate_map = _finite(base["coordinate_forward"], name="coordinate map", ndim=2)
        row_norms = np.linalg.norm(coordinate_map, axis=1)
        row_norms_equal = bool(np.allclose(row_norms, row_norms[0], rtol=1.0e-12, atol=1.0e-12))
        descriptor_pass = bool(
            physical_validity
            and control["convergence_pass"]
            and load["convergence_pass"]
            and state_names_match
            and state_relative_error <= 1.0e-8
            and state_maximum_error <= 1.0e-9
            and reduced.algebraic_reciprocal_condition >= 1.0e-12
            and folded_output_norm == 0.0
            and row_norms_equal
        )

        node_vectors = stage1_power_coordinates(1.0)
        node_basis = np.column_stack(
            [node_vectors[name] for name in ("common", "edge_0", "edge_1", "edge_2")]
        )
        physical_input = reduced.input_matrix.copy()
        physical_input[:, :4] = physical_input[:, :4] @ node_basis
        full = post_step_sampled_realization(
            state_matrix=reduced.state_matrix,
            input_matrix=physical_input,
            output_matrix=output_matrix,
            feedthrough_matrix=np.zeros((4, 8)),
            sample_period_seconds=0.2,
        )
        full_markov = _markov(full, 25)
        input_scales = np.concatenate([1.0 / np.linalg.norm(node_basis, axis=0), np.ones(4)])
        order12 = fit_normalized_era_realization(
            full_markov,
            input_scales=input_scales,
            output_scales=np.ones(4),
            order=12,
            block_rows=8,
            block_columns=8,
        )
        reduced_markov = _markov(order12, 25)
        internal_metrics = {
            str(channel): trajectory_metrics(
                reduced_markov[:, :, channel], full_markov[:, :, channel]
            )
            for channel in range(8)
        }
        internal_pass = bool(
            order12.spectral_radius < 1.0
            and all(
                row["nrmse"] <= 0.10 and row["peak_vector_residual"] <= 0.10
                for row in internal_metrics.values()
            )
        )
        result.update(
            {
                "physical_validity_pass": physical_validity,
                "derivative_guards": {"control": control, "load": load},
                "equilibrium_residual_absolute_maximum": equilibrium_residual,
                "descriptor_pass": descriptor_pass,
                "state_names_match": state_names_match,
                "state_matrix_relative_frobenius_error": state_relative_error,
                "state_matrix_maximum_absolute_error": state_maximum_error,
                "algebraic_reciprocal_condition": reduced.algebraic_reciprocal_condition,
                "folded_output_norm": folded_output_norm,
                "output_row_norms_equal": row_norms_equal,
                "internal_reduction_pass": internal_pass,
                "full_to_order12_metrics": internal_metrics,
                "full_sampled": _realization_payload(full),
                "order12": _realization_payload(order12),
                "construction_pass": descriptor_pass and internal_pass,
                "construction_error": None,
            }
        )
    except (KeyError, TypeError, ValueError, np.linalg.LinAlgError) as error:
        result.update(
            {
                "descriptor_pass": False,
                "internal_reduction_pass": False,
                "construction_pass": False,
                "construction_error": f"{type(error).__name__}: {error}",
            }
        )
    return _jsonable(result)


def build_candidate_bank(points: list[dict[str, Any]]) -> dict[str, Any]:
    """Construct both point-scheduled candidates with no trajectory input."""

    indexed = {str(point.get("point")): point for point in points}
    if set(indexed) != set(POINT_NAMES):
        raise ValueError("R340 candidate point inventory mismatch")
    built = {name: build_point_candidate(indexed[name]) for name in POINT_NAMES}
    return {
        "construction_method": "frozen-R339-point-scheduled-descriptor-to-order12",
        "trajectory_fit_count": 0,
        "trajectory_selection_count": 0,
        "points": built,
        "construction_pass": all(row["construction_pass"] is True for row in built.values()),
    }


def classify_r340(
    *,
    validity_pass: bool,
    construction_pass: bool,
    full_linearization_pass: bool,
    reduction_pass: bool,
) -> str:
    """Apply the prospectively frozen R340 first-failure tree."""

    if not validity_pass:
        return "INVALID"
    if not construction_pass:
        return "BLOCK-CONSTRUCTION"
    if not full_linearization_pass:
        return "BLOCK-FULL-LINEARIZATION"
    if not reduction_pass:
        return "BLOCK-REDUCTION"
    return "ALLOW-MODEL-GATE"


def analyse_development_canary(
    *,
    candidate_payload: dict[str, Any],
    records: list[dict[str, Any]],
    chain_valid: bool,
) -> dict[str, Any]:
    """Judge the fixed 18-record exposed-point canary without formal claims."""

    point_names = ("HS0", "HS1")
    point_models = candidate_payload.get("points")
    if not isinstance(point_models, dict) or set(point_models) != set(point_names):
        raise ValueError("R341 development candidate inventory mismatch")
    if len(records) != 18:
        raise ValueError("R341 development record inventory mismatch")
    indices = [int(row.get("record_index", -1)) for row in records]
    if sorted(indices) != list(range(18)) or len(set(indices)) != 18:
        raise ValueError("R341 development record indices are incomplete or duplicated")

    metrics: dict[str, dict[str, Any]] = {}
    full_pass = True
    reduction_pass = True
    all_record_guards = True
    for point_name in point_names:
        point_records = [row for row in records if row.get("operating_point") == point_name]
        if len(point_records) != 9:
            raise ValueError(f"R341 {point_name} development inventory mismatch")
        zero_rows = [row for row in point_records if row.get("channel") == "zero"]
        if len(zero_rows) != 1:
            raise ValueError(f"R341 {point_name} development zero mismatch")
        zero = _finite(zero_rows[0].get("output_coordinates"), name="zero output", ndim=2)
        full = realization_from_payload(dict(point_models[point_name]["full_sampled"]))
        order12 = realization_from_payload(dict(point_models[point_name]["order12"]))
        for row in point_records:
            all_record_guards = all_record_guards and row.get("record_valid") is True
            if row.get("channel") == "zero":
                continue
            channel = str(row.get("channel"))
            if channel not in LOAD_CHANNELS:
                raise ValueError(f"unknown R341 development load channel: {channel}")
            profile = _finite(row.get("delta_profile_system_pu"), name="load profile", ndim=1)
            inputs = np.zeros((profile.size, 8), dtype=float)
            inputs[:, 4 + LOAD_CHANNELS[channel]] = profile
            truth = _finite(row.get("output_coordinates"), name="nonlinear output", ndim=2) - zero
            full_metrics = trajectory_metrics(simulate_state_space(full, inputs), truth)
            reduced_metrics = trajectory_metrics(simulate_state_space(order12, inputs), truth)
            key = "/".join([point_name, channel, str(row.get("sign"))])
            metrics[key] = {
                "full_sampled_vs_nonlinear": full_metrics,
                "order12_vs_nonlinear": reduced_metrics,
            }
            full_pass = full_pass and (
                full_metrics["nrmse"] <= 0.15
                and full_metrics["peak_vector_residual"] <= 0.20
            )
            reduction_pass = reduction_pass and (
                reduced_metrics["nrmse"] <= 0.15
                and reduced_metrics["peak_vector_residual"] <= 0.20
            )

    construction_pass = bool(
        candidate_payload.get("construction_pass") is True
        and all(row.get("construction_pass") is True for row in point_models.values())
    )
    classification = classify_r340(
        validity_pass=bool(chain_valid and all_record_guards),
        construction_pass=construction_pass,
        full_linearization_pass=full_pass,
        reduction_pass=reduction_pass,
    )
    if classification == "ALLOW-MODEL-GATE":
        classification = "PASS-DEVELOPMENT"
    return {
        "classification": classification,
        "identity": "DEVELOPMENT",
        "formal_evidence": False,
        "validity_pass": bool(chain_valid and all_record_guards),
        "construction_pass": construction_pass,
        "full_linearization_pass": full_pass,
        "order12_reduction_pass": reduction_pass,
        "record_metrics": metrics,
    }


def analyse_r341_prefix(
    *,
    candidate_payload: dict[str, Any],
    records: list[dict[str, Any]],
    expected_record_indices: list[int],
    stage_name: str,
    chain_valid: bool,
) -> dict[str, Any]:
    """Judge one complete cumulative formal prefix and permit an early block."""

    point_models = candidate_payload.get("points")
    if not isinstance(point_models, dict) or set(point_models) != set(POINT_NAMES):
        raise ValueError("R341 prefix candidate inventory mismatch")
    indices = [int(row.get("record_index", -1)) for row in records]
    if sorted(indices) != sorted(expected_record_indices) or len(set(indices)) != len(indices):
        raise ValueError("R341 prefix record inventory mismatch")

    metrics: dict[str, dict[str, Any]] = {}
    full_pass = True
    reduction_pass = True
    all_record_guards = True
    for point_name in POINT_NAMES:
        point_records = [row for row in records if row.get("operating_point") == point_name]
        zero_rows = [row for row in point_records if row.get("channel") == "zero"]
        if len(zero_rows) != 1:
            raise ValueError(f"R341 {point_name} prefix zero mismatch")
        zero = _finite(zero_rows[0].get("output_coordinates"), name="zero output", ndim=2)
        full = realization_from_payload(dict(point_models[point_name]["full_sampled"]))
        order12 = realization_from_payload(dict(point_models[point_name]["order12"]))
        for row in point_records:
            all_record_guards = all_record_guards and row.get("record_valid") is True
            if row.get("channel") == "zero":
                continue
            channel = str(row.get("channel"))
            if channel not in LOAD_CHANNELS:
                raise ValueError(f"unknown R341 prefix load channel: {channel}")
            profile = _finite(row.get("delta_profile_system_pu"), name="load profile", ndim=1)
            inputs = np.zeros((profile.size, 8), dtype=float)
            inputs[:, 4 + LOAD_CHANNELS[channel]] = profile
            truth = _finite(row.get("output_coordinates"), name="nonlinear output", ndim=2) - zero
            full_metrics = trajectory_metrics(simulate_state_space(full, inputs), truth)
            reduced_metrics = trajectory_metrics(simulate_state_space(order12, inputs), truth)
            key = "/".join(
                [
                    point_name,
                    channel,
                    str(row.get("waveform")),
                    f"{float(row.get('amplitude_system_pu')):.12g}",
                    str(row.get("sign")),
                ]
            )
            metrics[key] = {
                "full_sampled_vs_nonlinear": full_metrics,
                "order12_vs_nonlinear": reduced_metrics,
            }
            full_pass = full_pass and (
                full_metrics["nrmse"] <= 0.15
                and full_metrics["peak_vector_residual"] <= 0.20
            )
            reduction_pass = reduction_pass and (
                reduced_metrics["nrmse"] <= 0.15
                and reduced_metrics["peak_vector_residual"] <= 0.20
            )

    construction_pass = bool(
        candidate_payload.get("construction_pass") is True
        and all(row.get("construction_pass") is True for row in point_models.values())
    )
    classification = classify_r340(
        validity_pass=bool(chain_valid and all_record_guards),
        construction_pass=construction_pass,
        full_linearization_pass=full_pass,
        reduction_pass=reduction_pass,
    )
    if classification == "ALLOW-MODEL-GATE":
        classification = "PASS-PREFIX"
    return {
        "classification": classification,
        "stage": stage_name,
        "record_count": len(records),
        "expected_record_indices": sorted(expected_record_indices),
        "validity_pass": bool(chain_valid and all_record_guards),
        "construction_pass": construction_pass,
        "full_linearization_pass": full_pass,
        "order12_reduction_pass": reduction_pass,
        "record_metrics": metrics,
        "claim_ceiling": "completed fresh-validation prefix only unless all 66 records pass",
    }


def _modal_frequencies(realization: StateSpaceRealization) -> list[float]:
    poles = np.linalg.eigvals(realization.state_matrix)
    frequencies = sorted(
        {
            round(abs(float(np.angle(pole))) / (2.0 * np.pi * 0.2), 9)
            for pole in poles
            if abs(float(np.angle(pole))) > 1.0e-12
        }
    )
    return frequencies


def analyse_r340_validation(
    *,
    candidate_payload: dict[str, Any],
    execution: dict[str, Any],
    chain_valid: bool,
) -> dict[str, Any]:
    """Compare both sealed predictors with the untouched nonlinear bank."""

    point_models = candidate_payload.get("points")
    records = execution.get("records")
    if not isinstance(point_models, dict) or set(point_models) != set(POINT_NAMES):
        raise ValueError("R340 candidate inventory mismatch")
    if not isinstance(records, list) or len(records) != 66:
        raise ValueError("R340 nonlinear record inventory mismatch")
    indices = [int(row.get("record_index", -1)) for row in records]
    if sorted(indices) != list(range(66)) or len(set(indices)) != 66:
        raise ValueError("R340 nonlinear record indices are incomplete or duplicated")

    metrics: dict[str, dict[str, Any]] = {}
    full_pass = True
    reduction_pass = True
    all_record_guards = True
    modal_report: dict[str, Any] = {}
    for point_name in POINT_NAMES:
        point_records = [row for row in records if row.get("operating_point") == point_name]
        if len(point_records) != 33:
            raise ValueError(f"R340 {point_name} record inventory mismatch")
        zero_rows = [row for row in point_records if row.get("channel") == "zero"]
        if len(zero_rows) != 1:
            raise ValueError(f"R340 {point_name} zero reference mismatch")
        zero = _finite(zero_rows[0].get("output_coordinates"), name="zero output", ndim=2)
        full = realization_from_payload(dict(point_models[point_name]["full_sampled"]))
        order12 = realization_from_payload(dict(point_models[point_name]["order12"]))
        modal_report[point_name] = {
            "full_sampled_frequencies_hz": _modal_frequencies(full),
            "order12_frequencies_hz": _modal_frequencies(order12),
            "registered_bands_hz": [[0.50, 0.62], [0.72, 0.86]],
        }
        for row in point_records:
            all_record_guards = all_record_guards and row.get("record_valid") is True
            if row.get("channel") == "zero":
                continue
            channel = str(row.get("channel"))
            if channel not in LOAD_CHANNELS:
                raise ValueError(f"unknown R340 load channel: {channel}")
            profile = _finite(row.get("delta_profile_system_pu"), name="load profile", ndim=1)
            inputs = np.zeros((profile.size, 8), dtype=float)
            inputs[:, 4 + LOAD_CHANNELS[channel]] = profile
            truth = _finite(row.get("output_coordinates"), name="nonlinear output", ndim=2) - zero
            full_metrics = trajectory_metrics(simulate_state_space(full, inputs), truth)
            reduced_metrics = trajectory_metrics(simulate_state_space(order12, inputs), truth)
            key = "/".join(
                [
                    point_name,
                    channel,
                    str(row.get("waveform")),
                    f"{float(row.get('amplitude_system_pu')):.2f}",
                    str(row.get("sign")),
                ]
            )
            metrics[key] = {
                "full_sampled_vs_nonlinear": full_metrics,
                "order12_vs_nonlinear": reduced_metrics,
            }
            full_pass = full_pass and (
                full_metrics["nrmse"] <= 0.15 and full_metrics["peak_vector_residual"] <= 0.20
            )
            reduction_pass = reduction_pass and (
                reduced_metrics["nrmse"] <= 0.15 and reduced_metrics["peak_vector_residual"] <= 0.20
            )

    construction_pass = bool(
        candidate_payload.get("construction_pass") is True
        and all(row.get("construction_pass") is True for row in point_models.values())
    )
    validity_pass = bool(
        chain_valid
        and all_record_guards
        and execution.get("record_count") == 66
        and execution.get("candidate_precedes_every_trajectory") is True
        and execution.get("controller_executed") is False
        and execution.get("distributed_runtime_executed") is False
        and execution.get("training_executed") is False
        and execution.get("eval_executed") is False
    )
    classification = classify_r340(
        validity_pass=validity_pass,
        construction_pass=construction_pass,
        full_linearization_pass=full_pass,
        reduction_pass=reduction_pass,
    )
    return {
        "classification": classification,
        "validity_pass": validity_pass,
        "construction_pass": construction_pass,
        "full_linearization_pass": full_pass,
        "order12_reduction_pass": reduction_pass,
        "all_record_guards_pass": all_record_guards,
        "record_metrics": metrics,
        "modal_attribution_only": modal_report,
        "controller_executed": False,
        "distributed_runtime_executed": False,
        "training_executed": False,
        "eval_executed": False,
        "claim_ceiling": (
            "fresh nonlinear validation of the frozen point-scheduled input-aware "
            "predictor construction only; no controller, distributed-agent, "
            "learning, stability, safety, topology-generalization, or title claim"
        ),
    }
