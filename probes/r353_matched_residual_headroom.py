"""Create-only primitives for the R353 matched residual-headroom gate.

Motivation: test whether a neighbour-local residual has offline headroom above
the matched R352 controller without running a simulator or training process.
Usage: pass already verified parent payloads to the public case, proposal,
projection, and gate functions; the stable R353 adapter owns persistence.
Failure modes: malformed parent identity, non-causal or non-finite arrays,
uncertified optimization, infeasible projection, or a failed scientific gate.
Every failure remains non-training evidence under the frozen R353 contract.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Mapping, Sequence, Set
from typing import Any

import numpy as np

from andes_rl_kundur.control.residual_headroom import (
    StandardizedAffineModel,
    apply_standardized_affine,
    finite_matrix,
    fit_standardized_affine,
    paired_endpoint_gate,
)

PRIMARY_ARMS = ("zero_edge", "selected_local")


def select_parent_records(
    records: Sequence[Mapping[str, Any]],
    *,
    bank: str,
    selected_candidate_id: str,
) -> list[dict[str, Any]]:
    """Select the frozen zero/local arms and normalize development arm naming."""

    if bank not in {"development", "holdout"}:
        raise ValueError("bank must be 'development' or 'holdout'")
    expected_mode = "development" if bank == "development" else "formal"
    selected: list[dict[str, Any]] = []
    for raw in records:
        if raw.get("mode") != expected_mode or raw.get("training_executed") is not False:
            raise ValueError(f"R352 {bank} record execution boundary drift")
        arm = str(raw.get("arm", ""))
        if bank == "development" and arm == "local_candidate":
            if raw.get("candidate_id") != selected_candidate_id:
                continue
            normalized = dict(raw)
            normalized["source_arm"] = arm
            normalized["arm"] = "selected_local"
            selected.append(normalized)
        elif arm in {"zero_edge", "selected_local", "joint_upper"}:
            normalized = dict(raw)
            normalized["source_arm"] = arm
            selected.append(normalized)
    return selected


def verify_parent_trace_identity(
    record: Mapping[str, Any],
    trace: Mapping[str, Any],
    *,
    bank: str,
    samples_per_trace: int,
) -> None:
    """Cross-check one manifest-bound trace against its execution record."""

    if bank not in {"development", "holdout"}:
        raise ValueError("bank must be 'development' or 'holdout'")
    spec = trace.get("spec")
    if not isinstance(spec, Mapping):
        raise ValueError("parent trace must contain a spec object")
    expected_mode = "development" if bank == "development" else "formal"
    expected_identity = "DEVELOPMENT" if bank == "development" else "HOLDOUT"
    expected_waveform = "ramp_hold_unit" if bank == "development" else "staggered_rise_unit"
    if (
        record.get("round") != "R352"
        or record.get("question") != "Q-0093"
        or record.get("mode") != expected_mode
        or record.get("identity") != expected_identity
    ):
        raise ValueError("parent record identity drift")
    scenario = str(record.get("scenario_id", ""))
    parts = scenario.split("__")
    if len(parts) != 4:
        raise ValueError("parent scenario identity is malformed")
    expected_prefix = "development" if bank == "development" else "holdout"
    if parts[0] != expected_prefix or record.get("point") != parts[1]:
        raise ValueError("parent record scenario point or bank mismatch")
    expected = {
        "scenario_id": scenario,
        "point": str(record.get("point", "")),
        "sign": parts[3],
        "mode": expected_mode,
        "identity": expected_identity,
        "arm": str(record.get("source_arm", record.get("arm", ""))),
        "candidate_id": record.get("candidate_id"),
        "record_index": int(record.get("record_index", -1)),
        "total_steps": int(samples_per_trace),
        "waveform": expected_waveform,
    }
    for field, value in expected.items():
        if spec.get(field) != value:
            raise ValueError(f"parent trace {field} does not match its record")
    channel = spec.get("channel")
    if not isinstance(channel, Mapping) or channel.get("device_idx") != parts[2]:
        raise ValueError("parent trace channel does not match its scenario")
    if (
        trace.get("round") != "R352"
        or trace.get("question") != "Q-0093"
        or len(trace.get("rows", [])) != samples_per_trace
    ):
        raise ValueError("parent trace round, question, or horizon drift")


def pair_primary_records(
    records: Sequence[Mapping[str, Any]],
    *,
    manifest_entries: Mapping[str, str],
    expected_scenarios: Set[str],
    selected_candidate_id: str,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Return exact manifest-bound zero/local pairs and exclude the joint arm."""

    expected = {str(item) for item in expected_scenarios}
    pairs: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records:
        arm = str(record.get("arm", ""))
        if arm == "joint_upper":
            continue
        if arm not in PRIMARY_ARMS:
            raise ValueError(f"unexpected parent arm: {arm}")
        guard_fields = (
            "integrity_valid",
            "information_action_contract_pass",
            "physical_guards_pass",
        )
        if any(record.get(field) is not True for field in guard_fields):
            raise ValueError("primary parent record failed a required guard")

        scenario = str(record.get("scenario_id", ""))
        if scenario not in expected:
            raise ValueError(f"unexpected parent scenario: {scenario}")
        trace = record.get("trace")
        if not isinstance(trace, Mapping):
            raise ValueError("parent record must contain trace provenance")
        path = str(trace.get("path", ""))
        digest = str(trace.get("sha256", ""))
        if not path or not digest or manifest_entries.get(path) != digest:
            raise ValueError(f"trace is not manifest-bound: {path}")
        if arm == "selected_local" and record.get("candidate_id") != selected_candidate_id:
            raise ValueError("selected-local candidate does not match the frozen parent")

        scenario_arms = pairs.setdefault(scenario, {})
        if arm in scenario_arms:
            raise ValueError(f"duplicate parent arm: {scenario}/{arm}")
        scenario_arms[arm] = dict(record)

    if set(pairs) != expected:
        raise ValueError("parent inventory does not contain the exact scenario bank")
    if any(set(arms) != set(PRIMARY_ARMS) for arms in pairs.values()):
        raise ValueError("every parent scenario must contain one zero/local pair")
    return pairs


def causal_edge_features(
    *,
    frequency_hz_before_action: object,
    executed_edge_flows_after_action: object,
    achieved_node_power_after_action: object,
    commanded_node_power_after_action: object,
    soc_before_action: object,
    voltage_before_action: object,
    edge: tuple[int, int],
    edge_index: int,
    nominal_frequency_hz: float,
    sample_period_seconds: float,
) -> np.ndarray:
    """Build one edge's causal 13-column endpoint-local feature matrix."""

    frequency = finite_matrix(
        frequency_hz_before_action,
        name="frequency_hz_before_action",
        columns=4,
    )
    edge_flows = finite_matrix(
        executed_edge_flows_after_action,
        name="executed_edge_flows_after_action",
        columns=3,
    )
    achieved = finite_matrix(
        achieved_node_power_after_action,
        name="achieved_node_power_after_action",
        columns=4,
    )
    commanded = finite_matrix(
        commanded_node_power_after_action,
        name="commanded_node_power_after_action",
        columns=4,
    )
    soc = finite_matrix(soc_before_action, name="soc_before_action", columns=4)
    voltage = finite_matrix(
        voltage_before_action,
        name="voltage_before_action",
        columns=4,
    )
    if (
        len({item.shape[0] for item in (frequency, edge_flows, achieved, commanded, soc, voltage)})
        != 1
    ):
        raise ValueError("causal feature arrays must share one horizon")

    source, target = (int(edge[0]), int(edge[1]))
    if source == target or min(source, target) < 0 or max(source, target) >= 4:
        raise ValueError("edge endpoints must be two distinct device indices")
    own_edge = int(edge_index)
    if own_edge < 0 or own_edge >= 3:
        raise ValueError("edge_index must identify one of the three edge actions")
    nominal = float(nominal_frequency_hz)
    sample_period = float(sample_period_seconds)
    if not np.isfinite(nominal) or nominal <= 0.0:
        raise ValueError("nominal_frequency_hz must be positive and finite")
    if not np.isfinite(sample_period) or sample_period <= 0.0:
        raise ValueError("sample_period_seconds must be positive and finite")

    frequency_deviation = frequency[:, (source, target)] - nominal
    rocof = np.zeros_like(frequency_deviation)
    rocof[1:] = np.diff(frequency[:, (source, target)], axis=0) / sample_period
    previous_edge_flow = np.zeros((frequency.shape[0], 1))
    previous_edge_flow[1:, 0] = edge_flows[:-1, own_edge]
    previous_achieved = np.zeros((frequency.shape[0], 2))
    previous_achieved[1:] = achieved[:-1, (source, target)]
    previous_commanded = np.zeros((frequency.shape[0], 2))
    previous_commanded[1:] = commanded[:-1, (source, target)]
    return np.column_stack(
        (
            frequency_deviation,
            rocof,
            previous_edge_flow,
            previous_achieved,
            previous_commanded,
            soc[:, (source, target)],
            voltage[:, (source, target)],
        )
    )


def fit_edge_estimators(
    development_features: Mapping[str, Sequence[object]],
    development_targets: Mapping[str, object],
) -> tuple[StandardizedAffineModel, StandardizedAffineModel, StandardizedAffineModel]:
    """Fit three edge-local maps from development scenarios only."""

    scenario_ids = sorted(str(item) for item in development_features)
    if not scenario_ids or set(scenario_ids) != {str(item) for item in development_targets}:
        raise ValueError("development features and targets must share scenario ids")
    edge_inputs: list[list[np.ndarray]] = [[], [], []]
    edge_targets: list[list[np.ndarray]] = [[], [], []]
    for scenario_id in scenario_ids:
        feature_set = development_features[scenario_id]
        if len(feature_set) != 3:
            raise ValueError("each development scenario must provide three edge feature matrices")
        target = finite_matrix(
            development_targets[scenario_id],
            name="development_targets",
            columns=3,
        )
        for edge_index, values in enumerate(feature_set):
            features = finite_matrix(
                values,
                name="development_features",
                columns=13,
            )
            if features.shape[0] != target.shape[0]:
                raise ValueError("development feature and target horizons must align")
            edge_inputs[edge_index].append(features)
            edge_targets[edge_index].append(target[:, edge_index])
    return tuple(
        fit_standardized_affine(np.vstack(edge_inputs[index]), np.concatenate(edge_targets[index]))
        for index in range(3)
    )  # type: ignore[return-value]


def predict_edge_estimators(
    models: Sequence[StandardizedAffineModel],
    feature_matrices: Sequence[object],
) -> np.ndarray:
    """Apply three frozen estimators to an unlabelled scenario."""

    if len(models) != 3 or len(feature_matrices) != 3:
        raise ValueError("prediction requires exactly three edge models and feature matrices")
    predictions = []
    horizon: int | None = None
    for model, values in zip(models, feature_matrices, strict=True):
        features = finite_matrix(values, name="feature_matrices", columns=13)
        if horizon is None:
            horizon = features.shape[0]
        elif features.shape[0] != horizon:
            raise ValueError("edge feature matrices must share one horizon")
        prediction = np.asarray(apply_standardized_affine(model, features), dtype=float)
        if prediction.shape != (features.shape[0],):
            raise ValueError("each edge estimator must produce one scalar per sample")
        predictions.append(prediction)
    return np.column_stack(predictions)


def leave_one_scenario_out_proposals(
    development_features: Mapping[str, Sequence[object]],
    development_targets: Mapping[str, object],
) -> dict[str, np.ndarray]:
    """Predict each development scenario without fitting on its oracle target."""

    scenario_ids = sorted(str(item) for item in development_features)
    if len(scenario_ids) < 2 or set(scenario_ids) != {str(item) for item in development_targets}:
        raise ValueError("leave-one-out requires aligned features and targets")
    proposals: dict[str, np.ndarray] = {}
    for heldout in scenario_ids:
        training_features = {
            scenario_id: development_features[scenario_id]
            for scenario_id in scenario_ids
            if scenario_id != heldout
        }
        training_targets = {
            scenario_id: development_targets[scenario_id]
            for scenario_id in scenario_ids
            if scenario_id != heldout
        }
        models = fit_edge_estimators(training_features, training_targets)
        proposals[heldout] = predict_edge_estimators(
            models,
            development_features[heldout],
        )
    return proposals


def classify_residual_gate(
    *,
    integrity_checks: Mapping[str, bool],
    scientific_checks: Mapping[str, bool],
) -> dict[str, Any]:
    """Classify the frozen gate without authorizing training in any branch."""

    if not integrity_checks or not scientific_checks:
        raise ValueError("integrity and scientific checks must both be populated")
    failed_integrity = sorted(
        str(name) for name, passed in integrity_checks.items() if passed is not True
    )
    failed_scientific = sorted(
        str(name) for name, passed in scientific_checks.items() if passed is not True
    )
    if failed_integrity:
        conclusion = "ANALYSIS-INVALID"
    elif failed_scientific:
        conclusion = "NO-TRAINING"
    else:
        conclusion = "RESIDUAL-PROBE-ELIGIBLE"
    return {
        "conclusion": conclusion,
        "failed_integrity_checks": failed_integrity,
        "failed_scientific_checks": failed_scientific,
        "residual_probe_eligible": conclusion == "RESIDUAL-PROBE-ELIGIBLE",
        "training_authorized": False,
    }


def residual_endpoint_gate(
    baseline_values: object,
    candidate_values: object,
    *,
    groups: Mapping[str, Sequence[str]],
    minimum_improvement_fraction: float,
    confidence_level: float,
    maximum_single_scenario_ratio: float,
) -> dict[str, Any]:
    """Apply the paired endpoint gate plus the frozen worst-case ratio cap."""

    baseline = np.asarray(baseline_values, dtype=float)
    candidate = np.asarray(candidate_values, dtype=float)
    if (
        baseline.ndim != 1
        or candidate.shape != baseline.shape
        or baseline.size < 2
        or not np.all(np.isfinite(baseline))
        or not np.all(np.isfinite(candidate))
        or np.any(baseline <= 0.0)
        or np.any(candidate < 0.0)
    ):
        raise ValueError("endpoint values must be aligned finite non-negative vectors")
    maximum_ratio = float(maximum_single_scenario_ratio)
    if not np.isfinite(maximum_ratio) or maximum_ratio <= 0.0:
        raise ValueError("maximum_single_scenario_ratio must be positive and finite")

    ratios = candidate / baseline
    paired = paired_endpoint_gate(
        ratios - 1.0,
        groups=groups,
        minimum_improvement_fraction=minimum_improvement_fraction,
        confidence_level=confidence_level,
    )
    observed = float(np.max(ratios))
    return {
        "pass": bool(paired["pass"] and observed <= maximum_ratio),
        "paired_gate": paired,
        "maximum_observed_ratio": observed,
        "maximum_single_scenario_ratio": maximum_ratio,
        "single_scenario_ratio_pass": bool(observed <= maximum_ratio),
    }


def _canonical_payload_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_frozen_point_model(
    candidate_models: Mapping[str, Any],
    *,
    point: str,
    expected_digest: str,
) -> Any:
    """Recreate one frozen R341 order-12 point model after payload verification."""

    from andes_rl_kundur.control.model_first_separate_input import (
        SeparateInputRealization,
    )
    from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
        StateSpaceRealization,
    )

    try:
        raw = candidate_models["points"][point]["order12"]
    except (KeyError, TypeError) as error:
        raise ValueError(f"missing R341 order-12 point model: {point}") from error
    if _canonical_payload_sha256(raw) != str(expected_digest):
        raise ValueError(f"R341 point model digest drift: {point}")
    joint = StateSpaceRealization(
        state_matrix=np.asarray(raw["state_matrix"], dtype=float),
        input_matrix=np.asarray(raw["input_matrix"], dtype=float),
        output_matrix=np.asarray(raw["output_matrix"], dtype=float),
        feedthrough_matrix=np.asarray(raw["feedthrough_matrix"], dtype=float),
        retained_singular_values=np.asarray(raw["retained_singular_values"], dtype=float),
    )
    return SeparateInputRealization.from_joint(joint)


def build_matched_cases(
    inventory: Sequence[Mapping[str, Any]],
    *,
    candidate_models: Mapping[str, Any],
    point_model_digests: Mapping[str, str],
    samples_per_trace: int,
    nominal_frequency_hz: float,
    sample_period_seconds: float,
) -> list[dict[str, Any]]:
    """Convert verified R352 pairs into causal R353 offline cases."""

    from andes_rl_kundur.control.residual_headroom import build_control_response_map
    from andes_rl_kundur.evaluation.model_first_physical_bridge import (
        frequency_coordinate_trace,
    )

    action_edges = ((0, 1), (1, 2), (2, 3))
    reference = np.full(4, float(nominal_frequency_hz))
    models: dict[str, Any] = {}
    cases: list[dict[str, Any]] = []
    for parent in inventory:
        arms = parent.get("arms")
        if not isinstance(arms, Mapping) or set(arms) != set(PRIMARY_ARMS):
            raise ValueError("R353 case requires one exact zero/local pair")
        local = arms["selected_local"]
        zero = arms["zero_edge"]
        local_trace = local["trace"]
        zero_trace = zero["trace"]
        local_rows = local_trace["rows"]
        zero_rows = zero_trace["rows"]
        point = str(parent["point"])
        if point not in models:
            models[point] = load_frozen_point_model(
                candidate_models,
                point=point,
                expected_digest=point_model_digests[point],
            )
        observed_edges = tuple(
            tuple(int(value) for value in edge)
            for edge in local_trace["structural_contract"]["action_edges"]
        )
        if observed_edges != action_edges:
            raise ValueError(f"R352 action-edge drift: {parent['scenario_id']}")
        inertia = np.asarray(
            local_trace["structural_contract"]["operating_point"]["vsg_m_system"],
            dtype=float,
        )
        local_frequency = finite_matrix(
            [row["freq_hz_physical"] for row in local_rows],
            name="local_frequency",
            columns=4,
        )
        zero_frequency = finite_matrix(
            [row["freq_hz_physical"] for row in zero_rows],
            name="zero_frequency",
            columns=4,
        )
        if (
            local_frequency.shape[0] != samples_per_trace
            or zero_frequency.shape[0] != samples_per_trace
        ):
            raise ValueError("R352 parent horizon drift")
        base_outputs = frequency_coordinate_trace(
            local_frequency,
            reference_frequency_hz=reference,
            inertia_system=inertia,
        )
        zero_outputs = frequency_coordinate_trace(
            zero_frequency,
            reference_frequency_hz=reference,
            inertia_system=inertia,
        )
        edge_flows = finite_matrix(
            [row["executed_edge_flows_system_pu"] for row in local_rows],
            name="edge_flows",
            columns=3,
        )
        achieved = finite_matrix(
            [row["bess_actual_power_system_pu"] for row in local_rows],
            name="achieved_power",
            columns=4,
        )
        commanded = finite_matrix(
            [row["bess_commanded_power_system_pu"] for row in local_rows],
            name="commanded_power",
            columns=4,
        )
        soc_after = finite_matrix(
            [row["bess_soc"] for row in local_rows],
            name="soc_after",
            columns=4,
        )
        voltage_after = finite_matrix(
            [row["bess_bus_voltage_pu"] for row in local_rows],
            name="voltage_after",
            columns=4,
        )
        initial_soc = np.full(
            4,
            float(local_trace["structural_contract"]["operating_point"]["initial_soc"]),
        )
        # R352 stores post-action frequency.  At action k, row k-1 is the
        # causal pre-action sample; a causal RoCoF therefore becomes exact only
        # from k=2.  Proposal builders below exclude k=0 and k=1.
        frequency_before = np.vstack((local_frequency[:1], local_frequency[:-1]))
        soc_before = np.vstack((initial_soc.reshape(1, 4), soc_after[:-1]))
        voltage_before = np.vstack((voltage_after[:1], voltage_after[:-1]))
        features = tuple(
            causal_edge_features(
                frequency_hz_before_action=frequency_before,
                executed_edge_flows_after_action=edge_flows,
                achieved_node_power_after_action=achieved,
                commanded_node_power_after_action=commanded,
                soc_before_action=soc_before,
                voltage_before_action=voltage_before,
                edge=edge,
                edge_index=edge_index,
                nominal_frequency_hz=nominal_frequency_hz,
                sample_period_seconds=sample_period_seconds,
            )
            for edge_index, edge in enumerate(action_edges)
        )
        response = build_control_response_map(models[point], horizon=samples_per_trace)
        predicted = (response @ edge_flows.reshape(-1)).reshape(samples_per_trace, 4)
        cases.append(
            {
                "scenario_id": parent["scenario_id"],
                "point": point,
                "channel": parent["channel"],
                "sign": parent["sign"],
                "model": models[point],
                "base_outputs": base_outputs,
                "zero_outputs": zero_outputs,
                "base_node_commands": commanded,
                "previous_node_command": np.zeros(4),
                "initial_soc": initial_soc,
                "features": features,
                "model_innovation": (base_outputs - zero_outputs) - predicted,
                "parent_record_index": int(local["record"]["record_index"]),
                "parent_trace": local["record"]["trace"],
                "zero_parent_record_index": int(zero["record"]["record_index"]),
                "zero_parent_trace": zero["record"]["trace"],
            }
        )
    return cases


def development_envelopes(cases: Sequence[Mapping[str, Any]]) -> dict[str, np.ndarray]:
    """Freeze one maximum-absolute development innovation envelope per point."""

    envelopes: dict[str, np.ndarray] = {}
    for point in sorted({str(case["point"]) for case in cases}):
        rows = np.vstack([case["model_innovation"] for case in cases if case["point"] == point])
        envelopes[point] = np.max(np.abs(rows), axis=0)
    return envelopes


def assign_envelopes(
    cases: Sequence[dict[str, Any]],
    envelopes: Mapping[str, object],
) -> None:
    """Attach the frozen point envelope needed by robust endpoint evaluation."""

    for case in cases:
        case["mismatch_envelope"] = np.asarray(envelopes[str(case["point"])], dtype=float)


def model_adequacy_gate(
    cases: Sequence[Mapping[str, Any]],
    envelopes: Mapping[str, object],
    *,
    absolute_tolerance: float,
) -> dict[str, Any]:
    """Check holdout innovations against development-only point envelopes."""

    points: dict[str, Any] = {}
    passed = True
    for point in sorted(envelopes):
        observed = np.max(
            np.abs(
                np.vstack([case["model_innovation"] for case in cases if case["point"] == point])
            ),
            axis=0,
        )
        permitted = np.asarray(envelopes[point], dtype=float) + float(absolute_tolerance)
        point_pass = bool(np.all(observed <= permitted))
        passed &= point_pass
        points[point] = {
            "pass": point_pass,
            "observed_max_abs_innovation": observed.tolist(),
            "development_envelope_plus_tolerance": permitted.tolist(),
        }
    return {"pass": bool(passed), "absolute_tolerance": float(absolute_tolerance), "points": points}


def _learning_data(
    cases: Sequence[Mapping[str, Any]],
    oracle: Sequence[Mapping[str, Any]],
    *,
    startup_samples: int,
) -> tuple[dict[str, tuple[np.ndarray, ...]], dict[str, np.ndarray]]:
    if startup_samples < 0:
        raise ValueError("startup_samples must be non-negative")
    oracle_by_id = {str(row["scenario_id"]): row for row in oracle}
    if len(oracle_by_id) != len(oracle):
        raise ValueError("oracle scenario ids must be unique")
    features: dict[str, tuple[np.ndarray, ...]] = {}
    targets: dict[str, np.ndarray] = {}
    for case in cases:
        scenario_id = str(case["scenario_id"])
        if scenario_id not in oracle_by_id:
            raise ValueError("cases and oracle rows must share scenario ids")
        features[scenario_id] = tuple(
            np.asarray(matrix, dtype=float)[startup_samples:] for matrix in case["features"]
        )
        targets[scenario_id] = np.asarray(oracle_by_id[scenario_id]["edge_actions"], dtype=float)[
            startup_samples:
        ]
    return features, targets


def development_proposals(
    cases: Sequence[Mapping[str, Any]],
    oracle: Sequence[Mapping[str, Any]],
    *,
    startup_samples: int,
) -> list[np.ndarray]:
    """Build leave-one-scenario-out proposals with causal startup actions zeroed."""

    features, targets = _learning_data(cases, oracle, startup_samples=startup_samples)
    predictions = leave_one_scenario_out_proposals(features, targets)
    prefix = np.zeros((startup_samples, 3))
    return [np.vstack((prefix, predictions[str(case["scenario_id"])])) for case in cases]


def holdout_proposals(
    development_cases: Sequence[Mapping[str, Any]],
    development_oracle: Sequence[Mapping[str, Any]],
    holdout_cases: Sequence[Mapping[str, Any]],
    *,
    startup_samples: int,
) -> list[np.ndarray]:
    """Fit once on development and predict holdout without holdout labels."""

    features, targets = _learning_data(
        development_cases,
        development_oracle,
        startup_samples=startup_samples,
    )
    models = fit_edge_estimators(features, targets)
    prefix = np.zeros((startup_samples, 3))
    proposals: list[np.ndarray] = []
    for case in holdout_cases:
        prediction = predict_edge_estimators(
            models,
            tuple(np.asarray(matrix, dtype=float)[startup_samples:] for matrix in case["features"]),
        )
        proposals.append(np.vstack((prefix, prediction)))
    return proposals


def _certificate_payload(certificate: object) -> dict[str, Any]:
    return {
        "valid": bool(certificate.valid),
        "message": str(certificate.message),
        "projected_gradient_infinity_norm": float(certificate.projected_gradient_infinity_norm),
        "stationarity_infinity_norm": float(certificate.stationarity_infinity_norm),
        "complementarity_infinity_norm": float(certificate.complementarity_infinity_norm),
        "primal_violation_infinity_norm": float(certificate.primal_violation_infinity_norm),
        "dual_violation_infinity_norm": float(certificate.dual_violation_infinity_norm),
        "multipliers": certificate.multipliers.tolist(),
    }


def _start_payload(start: object) -> dict[str, Any]:
    result = start.result
    return {
        "name": str(start.name),
        "feasible": bool(result.feasible),
        "optimizer_status_success": bool(result.optimizer_status_success),
        "target_feasible": bool(result.target_feasible),
        "message": str(result.message),
        "solver_iterations": int(result.solver_iterations),
        "maximum_constraint_residual": float(result.maximum_constraint_residual),
        "maximum_target_shortfall": float(result.maximum_target_shortfall),
        "objective_value": float(result.objective_value),
        "certificate": _certificate_payload(result.certificate),
    }


def _candidate_endpoints(
    case: Mapping[str, Any],
    edge_actions: object,
) -> tuple[np.ndarray, dict[str, float], dict[str, float]]:
    from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
    from andes_rl_kundur.control.residual_headroom import (
        build_control_response_map,
        endpoint_values,
    )

    edges = finite_matrix(edge_actions, name="edge_actions", columns=3)
    response = build_control_response_map(case["model"], horizon=edges.shape[0])
    counterfactual = np.asarray(case["base_outputs"], dtype=float) + (
        response @ edges.reshape(-1)
    ).reshape(edges.shape[0], 4)
    limits = FeedbackLimits()
    nominal = endpoint_values(
        counterfactual,
        sample_period_seconds=limits.sample_period_seconds,
    )
    envelope = np.asarray(case["mismatch_envelope"], dtype=float)
    robust_magnitude = np.abs(counterfactual) + envelope.reshape(1, 4)
    robust = {
        "common_coordinate_iae": float(
            limits.sample_period_seconds * np.sum(robust_magnitude[:, 0])
        ),
        "differential_coordinate_energy": float(
            limits.sample_period_seconds * np.sum(np.square(robust_magnitude[:, 1:]))
        ),
    }
    return counterfactual, nominal, robust


def solve_oracle_case(
    case: Mapping[str, Any],
    *,
    minimum_improvement_fraction: float,
    maximum_iterations: int,
    function_tolerance: float,
    feasibility_tolerance: float,
) -> dict[str, Any]:
    """Solve and serialize the frozen R350 three-start oracle for one case."""

    from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
    from andes_rl_kundur.control.residual_headroom import (
        build_control_response_map,
        endpoint_values,
        solve_three_start_edge_residual,
    )

    started = time.perf_counter()
    limits = FeedbackLimits()
    base_outputs = np.asarray(case["base_outputs"], dtype=float)
    response = build_control_response_map(case["model"], horizon=base_outputs.shape[0])
    solved = solve_three_start_edge_residual(
        base_outputs=base_outputs,
        base_node_commands=case["base_node_commands"],
        previous_node_command=case["previous_node_command"],
        initial_soc=case["initial_soc"],
        response_map=response,
        limits=limits,
        minimum_improvement_fraction=minimum_improvement_fraction,
        maximum_iterations=maximum_iterations,
        function_tolerance=function_tolerance,
        feasibility_tolerance=feasibility_tolerance,
    )
    starts = [_start_payload(start) for start in solved.starts]
    selected = solved.selected
    base = endpoint_values(
        base_outputs,
        sample_period_seconds=limits.sample_period_seconds,
    )
    zero = endpoint_values(
        case["zero_outputs"],
        sample_period_seconds=limits.sample_period_seconds,
    )
    common = {
        "scenario_id": case["scenario_id"],
        "worker_pid": os.getpid(),
        "elapsed_seconds": time.perf_counter() - started,
        "base_endpoints": base,
        "zero_control_endpoints": zero,
        "selected_start": solved.selected_start,
        "certified_start_count": solved.certified_start_count,
        "r348_optimizer_valid": solved.normalized_warm_start_valid,
        "starts": starts,
    }
    if selected is None:
        return {
            **common,
            "feasible": False,
            "optimizer_valid": False,
            "target_feasible": False,
            "message": "no fixed R350 start passed the independent certificate",
            "solver_iterations": int(sum(item["solver_iterations"] for item in starts)),
            "maximum_constraint_residual": float(
                max(item["maximum_constraint_residual"] for item in starts)
            ),
            "maximum_target_shortfall": float(
                max(item["maximum_target_shortfall"] for item in starts)
            ),
            "objective_value": float("inf"),
        }
    _counterfactual, nominal, robust = _candidate_endpoints(case, selected.edge_actions)
    return {
        **common,
        "feasible": True,
        "optimizer_valid": True,
        "target_feasible": bool(selected.target_feasible),
        "message": selected.message,
        "solver_iterations": selected.solver_iterations,
        "maximum_constraint_residual": selected.maximum_constraint_residual,
        "maximum_target_shortfall": selected.maximum_target_shortfall,
        "objective_value": selected.objective_value,
        "nominal_endpoints": nominal,
        "mismatch_bounded_endpoints": robust,
        "edge_actions": selected.edge_actions.tolist(),
        "residual_node_actions": selected.residual_node_actions.tolist(),
        "counterfactual_node_commands": selected.counterfactual_node_commands.tolist(),
        "counterfactual_soc": selected.counterfactual_soc.tolist(),
        "certificate": _certificate_payload(selected.certificate),
    }


def project_local_case(
    case: Mapping[str, Any],
    proposal: object,
    *,
    maximum_iterations: int,
    function_tolerance: float,
    feasibility_tolerance: float,
) -> dict[str, Any]:
    """Project one neighbour-local proposal through the frozen headroom governor."""

    from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
    from andes_rl_kundur.control.residual_headroom import (
        project_edge_sequence_to_headroom,
    )

    started = time.perf_counter()
    proposed = finite_matrix(proposal, name="proposal", columns=3)
    solution = project_edge_sequence_to_headroom(
        proposed_edge_actions=proposed,
        base_node_commands=case["base_node_commands"],
        previous_node_command=case["previous_node_command"],
        initial_soc=case["initial_soc"],
        limits=FeedbackLimits(),
        maximum_iterations=maximum_iterations,
        function_tolerance=function_tolerance,
        feasibility_tolerance=feasibility_tolerance,
    )
    _counterfactual, nominal, robust = _candidate_endpoints(case, solution.edge_actions)
    return {
        "scenario_id": case["scenario_id"],
        "worker_pid": os.getpid(),
        "elapsed_seconds": time.perf_counter() - started,
        "feasible": bool(solution.feasible),
        "message": solution.message,
        "solver_iterations": solution.solver_iterations,
        "maximum_constraint_residual": solution.maximum_constraint_residual,
        "projection_objective_value": solution.objective_value,
        "nominal_endpoints": nominal,
        "mismatch_bounded_endpoints": robust,
        "proposed_edge_actions": proposed.tolist(),
        "edge_actions": solution.edge_actions.tolist(),
        "residual_node_actions": solution.residual_node_actions.tolist(),
        "counterfactual_node_commands": solution.counterfactual_node_commands.tolist(),
        "counterfactual_soc": solution.counterfactual_soc.tolist(),
    }


def candidate_gate(
    cases: Sequence[Mapping[str, Any]],
    oracle: Sequence[Mapping[str, Any]],
    local: Sequence[Mapping[str, Any]],
    *,
    candidate: str,
    endpoint_field: str,
    minimum_improvement_fraction: float,
    confidence_level: float,
    maximum_single_scenario_ratio: float,
) -> dict[str, Any]:
    """Evaluate both registered endpoints for one candidate family."""

    if candidate not in {"oracle", "local"}:
        raise ValueError("candidate must be 'oracle' or 'local'")
    oracle_by_id = {str(row["scenario_id"]): row for row in oracle}
    local_by_id = {str(row["scenario_id"]): row for row in local}
    selected = oracle_by_id if candidate == "oracle" else local_by_id
    groups = {
        "point": [str(case["point"]) for case in cases],
        "channel": [str(case["channel"]) for case in cases],
        "sign": [str(case["sign"]) for case in cases],
    }
    endpoint_gates: dict[str, Any] = {}
    for endpoint in ("common_coordinate_iae", "differential_coordinate_energy"):
        baseline = [
            oracle_by_id[str(case["scenario_id"])]["base_endpoints"][endpoint] for case in cases
        ]
        values = [selected[str(case["scenario_id"])][endpoint_field][endpoint] for case in cases]
        endpoint_gates[endpoint] = residual_endpoint_gate(
            baseline,
            values,
            groups=groups,
            minimum_improvement_fraction=minimum_improvement_fraction,
            confidence_level=confidence_level,
            maximum_single_scenario_ratio=maximum_single_scenario_ratio,
        )
    return {
        "pass": all(item["pass"] for item in endpoint_gates.values()),
        "endpoints": endpoint_gates,
    }


def stage_decision(
    cases: Sequence[Mapping[str, Any]],
    oracle: Sequence[Mapping[str, Any]],
    local: Sequence[Mapping[str, Any]],
    *,
    model_adequacy: Mapping[str, Any] | None,
    include_mismatch: bool,
    minimum_improvement_fraction: float,
    confidence_level: float,
    maximum_single_scenario_ratio: float,
) -> dict[str, Any]:
    """Apply the complete registered R353 stage classification."""

    integrity_checks = {
        "parent_and_source_closure": True,
        "oracle_certificates": all(
            row.get("optimizer_valid") is True
            and int(row.get("certified_start_count", 0)) >= 1
            and row.get("certificate", {}).get("valid") is True
            for row in oracle
        ),
        "local_projection_numerics": all(row.get("feasible") is True for row in local),
    }
    gates: dict[str, Any] = {
        "oracle_certified": integrity_checks["oracle_certificates"],
        "local_projection_feasible": integrity_checks["local_projection_numerics"],
    }
    if not all(integrity_checks.values()):
        return {
            "gates": gates,
            **classify_residual_gate(
                integrity_checks=integrity_checks,
                scientific_checks={"candidate_endpoints_evaluated": False},
            ),
        }
    gates.update(
        {
            "oracle_nominal": candidate_gate(
                cases,
                oracle,
                local,
                candidate="oracle",
                endpoint_field="nominal_endpoints",
                minimum_improvement_fraction=minimum_improvement_fraction,
                confidence_level=confidence_level,
                maximum_single_scenario_ratio=maximum_single_scenario_ratio,
            ),
            "local_nominal": candidate_gate(
                cases,
                oracle,
                local,
                candidate="local",
                endpoint_field="nominal_endpoints",
                minimum_improvement_fraction=minimum_improvement_fraction,
                confidence_level=confidence_level,
                maximum_single_scenario_ratio=maximum_single_scenario_ratio,
            ),
        }
    )
    if model_adequacy is not None:
        gates["holdout_model_adequacy"] = dict(model_adequacy)
    if include_mismatch:
        gates["oracle_mismatch_bounded"] = candidate_gate(
            cases,
            oracle,
            local,
            candidate="oracle",
            endpoint_field="mismatch_bounded_endpoints",
            minimum_improvement_fraction=minimum_improvement_fraction,
            confidence_level=confidence_level,
            maximum_single_scenario_ratio=maximum_single_scenario_ratio,
        )
        gates["local_mismatch_bounded"] = candidate_gate(
            cases,
            oracle,
            local,
            candidate="local",
            endpoint_field="mismatch_bounded_endpoints",
            minimum_improvement_fraction=minimum_improvement_fraction,
            confidence_level=confidence_level,
            maximum_single_scenario_ratio=maximum_single_scenario_ratio,
        )
    scientific_checks = {
        name: bool(value if isinstance(value, bool) else value["pass"])
        for name, value in gates.items()
    }
    decision = classify_residual_gate(
        integrity_checks=integrity_checks,
        scientific_checks=scientific_checks,
    )
    return {"gates": gates, **decision}


def _oracle_integrity_decision(oracle: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    integrity_checks = {
        "parent_and_source_closure": True,
        "oracle_certificates": bool(oracle)
        and all(
            row.get("optimizer_valid") is True
            and int(row.get("certified_start_count", 0)) >= 1
            and row.get("certificate", {}).get("valid") is True
            for row in oracle
        ),
    }
    return {
        "gates": {"oracle_certified": integrity_checks["oracle_certificates"]},
        **classify_residual_gate(
            integrity_checks=integrity_checks,
            scientific_checks={"candidate_endpoints_evaluated": False},
        ),
    }


def evaluate_development_stage(
    cases: Sequence[dict[str, Any]],
    *,
    minimum_improvement_fraction: float,
    confidence_level: float,
    maximum_single_scenario_ratio: float,
    startup_samples: int,
    maximum_iterations: int,
    function_tolerance: float,
    feasibility_tolerance: float,
) -> dict[str, Any]:
    """Run the complete development analysis with an oracle-integrity stop."""

    oracle = [
        solve_oracle_case(
            case,
            minimum_improvement_fraction=minimum_improvement_fraction,
            maximum_iterations=maximum_iterations,
            function_tolerance=function_tolerance,
            feasibility_tolerance=feasibility_tolerance,
        )
        for case in cases
    ]
    oracle_integrity = _oracle_integrity_decision(oracle)
    if oracle_integrity["conclusion"] == "ANALYSIS-INVALID":
        return {"oracle": oracle, "local": [], "decision": oracle_integrity}
    proposals = development_proposals(cases, oracle, startup_samples=startup_samples)
    local = [
        project_local_case(
            case,
            proposal,
            maximum_iterations=maximum_iterations,
            function_tolerance=function_tolerance,
            feasibility_tolerance=feasibility_tolerance,
        )
        for case, proposal in zip(cases, proposals, strict=True)
    ]
    return {
        "oracle": oracle,
        "local": local,
        "decision": stage_decision(
            cases,
            oracle,
            local,
            model_adequacy=None,
            include_mismatch=False,
            minimum_improvement_fraction=minimum_improvement_fraction,
            confidence_level=confidence_level,
            maximum_single_scenario_ratio=maximum_single_scenario_ratio,
        ),
    }


def evaluate_holdout_stage(
    development_cases: Sequence[dict[str, Any]],
    development_oracle: Sequence[Mapping[str, Any]],
    holdout_cases: Sequence[dict[str, Any]],
    envelopes: Mapping[str, object],
    *,
    model_adequacy_tolerance: float,
    minimum_improvement_fraction: float,
    confidence_level: float,
    maximum_single_scenario_ratio: float,
    startup_samples: int,
    maximum_iterations: int,
    function_tolerance: float,
    feasibility_tolerance: float,
) -> dict[str, Any]:
    """Run the sealed holdout stage without fitting on any holdout target."""

    adequacy = model_adequacy_gate(
        holdout_cases,
        envelopes,
        absolute_tolerance=model_adequacy_tolerance,
    )
    if not adequacy["pass"]:
        decision = {
            "gates": {"holdout_model_adequacy": adequacy},
            **classify_residual_gate(
                integrity_checks={"parent_and_source_closure": True},
                scientific_checks={"holdout_model_adequacy": False},
            ),
        }
        return {"model_adequacy": adequacy, "oracle": [], "local": [], "decision": decision}
    oracle = [
        solve_oracle_case(
            case,
            minimum_improvement_fraction=minimum_improvement_fraction,
            maximum_iterations=maximum_iterations,
            function_tolerance=function_tolerance,
            feasibility_tolerance=feasibility_tolerance,
        )
        for case in holdout_cases
    ]
    oracle_integrity = _oracle_integrity_decision(oracle)
    if oracle_integrity["conclusion"] == "ANALYSIS-INVALID":
        oracle_integrity["gates"]["holdout_model_adequacy"] = adequacy
        return {
            "model_adequacy": adequacy,
            "oracle": oracle,
            "local": [],
            "decision": oracle_integrity,
        }
    proposals = holdout_proposals(
        development_cases,
        development_oracle,
        holdout_cases,
        startup_samples=startup_samples,
    )
    local = [
        project_local_case(
            case,
            proposal,
            maximum_iterations=maximum_iterations,
            function_tolerance=function_tolerance,
            feasibility_tolerance=feasibility_tolerance,
        )
        for case, proposal in zip(holdout_cases, proposals, strict=True)
    ]
    return {
        "model_adequacy": adequacy,
        "oracle": oracle,
        "local": local,
        "decision": stage_decision(
            holdout_cases,
            oracle,
            local,
            model_adequacy=adequacy,
            include_mismatch=True,
            minimum_improvement_fraction=minimum_improvement_fraction,
            confidence_level=confidence_level,
            maximum_single_scenario_ratio=maximum_single_scenario_ratio,
        ),
    }
