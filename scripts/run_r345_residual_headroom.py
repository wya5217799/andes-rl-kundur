"""Seal and execute the R345 create-only residual-headroom analysis.

Usage::

    python scripts/run_r345_residual_headroom.py prepare
    python scripts/run_r345_residual_headroom.py analyse --expected-sha256 <sha256>

The adapter reads the immutable R344 paired records and R341 point models.  It
does not run ANDES, training, distributed control, or EVAL.  Result files are
create-only; any post-attempt failure requires a successor round.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

ROUND_ID = "R345"
QUESTION_ID = "Q-0091"
WORKERS = 16
MINIMUM_IMPROVEMENT = 0.02
CONFIDENCE_LEVEL = 0.95
MAXIMUM_ITERATIONS = 20_000
FUNCTION_TOLERANCE = 1.0e-9
FEASIBILITY_TOLERANCE = 1.0e-8
DEFAULT_SEAL = ROOT / "memory/rounds/R345/analysis_seal.json"
DEFAULT_OUT = ROOT / "results/r345_residual_headroom"
PLAN = ROOT / "memory/rounds/R345/plan.md"
FORMAL_SEAL = ROOT / "memory/rounds/R344/formal_seal.json"
FORMAL_EXECUTION = ROOT / "results/r344_deterministic_bridge/formal_execution.json"
FORMAL_ANALYSIS = ROOT / "results/r344_deterministic_bridge/formal_analysis.json"
FORMAL_MANIFEST = ROOT / "results/r344_deterministic_bridge/formal_manifest.json"
CANDIDATE_MODELS = ROOT / "results/r341_staged_fresh_model_validation/candidate_models.json"
EXPECTED_INPUT_HASHES = {
    "memory/rounds/R344/formal_seal.json": (
        "eec71696276e45ead9f85bd2f7c932f4a2aeae37f6ceabe3d570871e3c129a8d"
    ),
    "results/r344_deterministic_bridge/formal_execution.json": (
        "8a82763ce1b3f777c4e7a1429f92651eb88d94d0bc238ee0c06664be6676bbd1"
    ),
    "results/r344_deterministic_bridge/formal_analysis.json": (
        "41c8e73deadbf30d0352dc5a20f82938ad3723ca7f2467a86f2d8f494996ad72"
    ),
    "results/r344_deterministic_bridge/formal_manifest.json": (
        "3752b735536c599bc920b2f792ca1d677876436421858614c046707ab66e8b24"
    ),
    "results/r341_staged_fresh_model_validation/candidate_models.json": (
        "7a74cb78dca8c5e30f32a344ca43704079a1549c966ff21de492eba7a3f1e32e"
    ),
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _write_new_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
    except FileExistsError:
        raise FileExistsError(f"create-only output already exists: {path}") from None
    digest = _sha256_file(path)
    sidecar = Path(f"{path}.sha256")
    try:
        with sidecar.open("x", encoding="ascii", newline="\n") as handle:
            handle.write(f"{digest}  {path.name}\n")
    except FileExistsError:
        raise FileExistsError(f"create-only sidecar already exists: {sidecar}") from None
    return digest


def _source(path: Path) -> dict[str, str]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": _sha256_file(path),
    }


def build_contract() -> dict[str, Any]:
    """Return the frozen R345 scientific and execution contract."""

    from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits

    limits = FeedbackLimits()
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "create-only-offline-residual-headroom",
        "inventory": {
            "scenario_pairs": 16,
            "records": 32,
            "samples_per_trace": 25,
            "operating_points": 2,
            "disturbance_locations": 4,
            "signs": 2,
        },
        "residual": {
            "common_coordinate": 0.0,
            "edge_coordinates": 3,
            "objective": "minimum-l2-sequence-meeting-both-endpoint-targets",
            "minimum_improvement_fraction": MINIMUM_IMPROVEMENT,
            "model_error_envelope": "scenario-coordinate-max-absolute-innovation",
        },
        "local_information": {
            "per_edge_features": [
                "endpoint_frequency_deviation_hz",
                "endpoint_previous_achieved_power_system_pu",
                "endpoint_previous_commanded_power_system_pu",
            ],
            "forbidden_features": [
                "operating_point_label",
                "disturbance_location_label",
                "sign_label",
                "scenario_id",
                "future_value",
                "joint_coordinate",
                "oracle_endpoint",
            ],
            "estimator": "standardized-ordinary-least-squares",
            "validation": "leave-one-scenario-out",
            "governor": "minimum-l2-edge-sequence-projection",
        },
        "statistics": {
            "unit": "scenario",
            "signed_relative_change": "(candidate-base)/base",
            "confidence_level": CONFIDENCE_LEVEL,
            "bound": "one-sided-paired-student-t-upper",
            "subgroups": ["point", "channel", "sign"],
            "subgroup_rule": "every-subgroup-mean-directionally-improves",
        },
        "limits": asdict(limits),
        "solver": {
            "method": "SLSQP",
            "maximum_iterations": MAXIMUM_ITERATIONS,
            "function_tolerance": FUNCTION_TOLERANCE,
            "feasibility_tolerance": FEASIBILITY_TOLERANCE,
        },
        "execution": {
            "worker_processes": WORKERS,
            "native_threads_per_process": 1,
            "ready_job_cap": 16,
            "other_reserved_processes": 0,
            "host_capacity_anchor": ("memory/rounds/R344/capacity_ladder_attempt_2.json"),
            "create_only": True,
        },
        "decision": {
            "positive": "RESIDUAL-PROBE-ELIGIBLE",
            "negative": "NO-TRAINING",
            "invalid": "ANALYSIS-INVALID",
            "positive_authority": "one-separately-sealed-non-learning-physical-probe",
            "training_authorized": False,
            "distributed_runtime_authorized": False,
            "eval_authorized": False,
        },
        "exclusions": {
            "andes_executed": False,
            "physical_trajectory_created": False,
            "training_executed": False,
            "reward_defined": False,
            "architecture_selected": False,
            "distributed_runtime_executed": False,
            "eval_executed": False,
        },
    }


def _seal_sources() -> dict[str, dict[str, str]]:
    paths = {
        "plan": PLAN,
        "adapter": Path(__file__).resolve(),
        "probe": ROOT / "probes/r345_residual_headroom.py",
        "tests": ROOT / "tests/test_r345_residual_headroom.py",
        "r344_adapter": ROOT / "scripts/run_r344_deterministic_bridge.py",
        "separate_input": (ROOT / "src/andes_rl_kundur/control/model_first_separate_input.py"),
        "physical_bridge_metrics": (
            ROOT / "src/andes_rl_kundur/evaluation/model_first_physical_bridge.py"
        ),
        "offline_limits": (ROOT / "src/andes_rl_kundur/control/model_first_offline_feedback.py"),
        "formal_seal": FORMAL_SEAL,
        "formal_execution": FORMAL_EXECUTION,
        "formal_analysis": FORMAL_ANALYSIS,
        "formal_manifest": FORMAL_MANIFEST,
        "candidate_models": CANDIDATE_MODELS,
    }
    return {name: _source(path) for name, path in paths.items()}


def _verify_expected_inputs() -> None:
    for relative, expected in EXPECTED_INPUT_HASHES.items():
        path = ROOT / relative
        actual = _sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"frozen input drift: {relative}: {actual} != {expected}")


def prepare(seal_path: Path = DEFAULT_SEAL) -> str:
    """Create the source-bound R345 seal before reading residual outcomes."""

    _verify_expected_inputs()
    if seal_path.exists():
        raise FileExistsError(f"R345 seal already exists: {seal_path}")
    if DEFAULT_OUT.exists():
        raise FileExistsError(f"R345 result root already exists: {DEFAULT_OUT}")
    plan_text = PLAN.read_text(encoding="utf-8")
    if "state: active" not in plan_text or "Q-0091" not in plan_text:
        raise RuntimeError("R345 active plan identity is missing")
    contract = build_contract()
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "sources": _seal_sources(),
        "result_root_absent_at_freeze": True,
        "formal_retry_authorized": False,
    }
    return _write_new_json(seal_path, payload)


def load_seal(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    """Verify the exact R345 seal, contract, and every bound source."""

    payload = _read_json(path)
    actual = _sha256_file(path)
    if actual != expected_sha256:
        raise RuntimeError(f"R345 seal digest mismatch: {actual}")
    if payload.get("round") != ROUND_ID or payload.get("question") != QUESTION_ID:
        raise RuntimeError("R345 seal identity mismatch")
    contract = payload.get("contract")
    if contract != build_contract() or payload.get("contract_payload_sha256") != _payload_sha256(
        contract
    ):
        raise RuntimeError("R345 contract drift")
    if payload.get("sources") != _seal_sources():
        raise RuntimeError("R345 source drift")
    _verify_expected_inputs()
    return payload, actual


def _load_trace(path: Path, expected_sha256: str) -> dict[str, Any]:
    if _sha256_file(path) != expected_sha256:
        raise RuntimeError(f"R344 trace digest mismatch: {path}")
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise RuntimeError(f"R344 trace is not an object: {path}")
    return payload


def _load_point_model(point: str):
    import numpy as np
    from scripts import run_r344_deterministic_bridge as r344

    from andes_rl_kundur.control.model_first_separate_input import (
        SeparateInputRealization,
    )
    from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
        StateSpaceRealization,
    )

    payload = _read_json(CANDIDATE_MODELS)
    raw = payload["points"][point]["order12"]
    if r344._payload_sha256(raw) != r344.POINT_MODEL_DIGESTS[point]:
        raise RuntimeError(f"R341 point model drift: {point}")
    joint = StateSpaceRealization(
        state_matrix=np.asarray(raw["state_matrix"], dtype=float),
        input_matrix=np.asarray(raw["input_matrix"], dtype=float),
        output_matrix=np.asarray(raw["output_matrix"], dtype=float),
        feedthrough_matrix=np.asarray(raw["feedthrough_matrix"], dtype=float),
        retained_singular_values=np.asarray(raw["retained_singular_values"], dtype=float),
    )
    return SeparateInputRealization.from_joint(joint)


def _load_cases() -> list[dict[str, Any]]:
    import numpy as np
    from probes.r345_residual_headroom import physical_frequency_from_coordinates

    from andes_rl_kundur.evaluation.model_first_physical_bridge import (
        frequency_coordinate_trace,
    )

    execution = _read_json(FORMAL_EXECUTION)
    analysis = _read_json(FORMAL_ANALYSIS)
    manifest = _read_json(FORMAL_MANIFEST)
    if (
        execution.get("round") != "R344"
        or execution.get("record_count") != 32
        or len(execution.get("records", [])) != 32
        or analysis.get("classification") != "DETERMINISTIC-BRIDGE-PASS"
        or analysis.get("training_authorized") is not False
    ):
        raise RuntimeError("R344 parent decision or inventory mismatch")
    manifest_entries = {
        str(entry["path"]): str(entry["sha256"]) for entry in manifest.get("entries", [])
    }
    grouped: dict[str, dict[str, tuple[dict[str, Any], dict[str, Any]]]] = {}
    for record in execution["records"]:
        if (
            record.get("mode") != "formal"
            or record.get("integrity_valid") is not True
            or record.get("physical_guards_pass") is not True
            or record.get("fallback_count") != 0
            or record.get("training_executed") is not False
        ):
            raise RuntimeError("R344 record validity drift")
        trace_ref = record.get("trace", {})
        relative = str(trace_ref.get("path"))
        digest = str(trace_ref.get("sha256"))
        if manifest_entries.get(relative) != digest:
            raise RuntimeError(f"R344 manifest does not bind trace: {relative}")
        trace = _load_trace(ROOT / relative, digest)
        if len(trace.get("rows", [])) != 25:
            raise RuntimeError(f"R344 trace length drift: {relative}")
        grouped.setdefault(str(record["scenario_id"]), {})[str(record["arm"])] = (
            record,
            trace,
        )
    if len(grouped) != 16 or any(
        set(arms) != {"zero_control", "frozen_controller"} for arms in grouped.values()
    ):
        raise RuntimeError("R344 scenario pairing drift")

    models: dict[str, Any] = {}
    cases: list[dict[str, Any]] = []
    for scenario_id in sorted(grouped):
        zero_record, zero_trace = grouped[scenario_id]["zero_control"]
        controlled_record, controlled_trace = grouped[scenario_id]["frozen_controller"]
        spec = controlled_trace["spec"]
        if zero_trace["spec"]["point"] != spec["point"]:
            raise RuntimeError(f"R344 pair point mismatch: {scenario_id}")
        point = str(spec["point"])
        if point not in models:
            models[point] = _load_point_model(point)
        rows = controlled_trace["rows"]
        frequency = np.asarray([row["freq_hz_physical"] for row in rows], dtype=float)
        zero_frequency = np.asarray(
            [row["freq_hz_physical"] for row in zero_trace["rows"]],
            dtype=float,
        )
        inertia = np.asarray(
            controlled_trace["structural_contract"]["operating_point"]["vsg_m_system"],
            dtype=float,
        )
        reference = np.full(4, 60.0)
        outputs = frequency_coordinate_trace(
            frequency,
            reference_frequency_hz=reference,
            inertia_system=inertia,
        )
        zero_outputs = frequency_coordinate_trace(
            zero_frequency,
            reference_frequency_hz=reference,
            inertia_system=inertia,
        )
        delivered_before = np.asarray(
            [row["delivered_coordinates_before_action"] for row in rows],
            dtype=float,
        )
        frequency_before = physical_frequency_from_coordinates(
            delivered_before,
            reference_frequency_hz=reference,
            inertia_system=inertia,
        )
        achieved_before = np.asarray(
            [row["achieved_node_power_before_action"] for row in rows],
            dtype=float,
        )
        commanded_before = np.asarray(
            [row["commanded_node_power_before_action"] for row in rows],
            dtype=float,
        )
        commands = np.asarray(
            [row["bess_commanded_power_system_pu"] for row in rows],
            dtype=float,
        )
        innovations = np.asarray(
            [row["controller"]["innovation"] for row in rows],
            dtype=float,
        )
        cases.append(
            {
                "scenario_id": scenario_id,
                "point": point,
                "channel": str(spec["channel"]),
                "sign": str(spec["sign"]),
                "model": models[point],
                "base_outputs": outputs,
                "zero_outputs": zero_outputs,
                "base_node_commands": commands,
                "previous_node_command": commanded_before[0],
                "initial_soc": np.full(
                    4,
                    float(
                        controlled_trace["structural_contract"]["operating_point"]["initial_soc"]
                    ),
                ),
                "frequency_before": frequency_before,
                "achieved_before": achieved_before,
                "commanded_before": commanded_before,
                "mismatch_envelope": np.max(np.abs(innovations), axis=0),
                "parent_record_index": int(controlled_record["record_index"]),
                "parent_trace": controlled_record["trace"],
                "zero_parent_record_index": int(zero_record["record_index"]),
                "zero_parent_trace": zero_record["trace"],
            }
        )
    return cases


def _candidate_endpoints(
    case: dict[str, Any],
    edge_actions: Any,
) -> tuple[Any, dict[str, float], dict[str, float]]:
    import numpy as np
    from probes.r345_residual_headroom import (
        build_control_response_map,
        endpoint_values,
    )

    from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits

    edges = np.asarray(edge_actions, dtype=float)
    response = build_control_response_map(case["model"], horizon=edges.shape[0])
    counterfactual = case["base_outputs"] + (response @ edges.reshape(-1)).reshape(
        edges.shape[0], 4
    )
    nominal = endpoint_values(
        counterfactual,
        sample_period_seconds=FeedbackLimits().sample_period_seconds,
    )
    envelope = np.asarray(case["mismatch_envelope"], dtype=float)
    robust_magnitude = np.abs(counterfactual) + envelope.reshape(1, 4)
    sample_period = FeedbackLimits().sample_period_seconds
    robust = {
        "common_coordinate_iae": float(sample_period * np.sum(robust_magnitude[:, 0])),
        "differential_coordinate_energy": float(
            sample_period * np.sum(np.square(robust_magnitude[:, 1:]))
        ),
    }
    return counterfactual, nominal, robust


def _oracle_worker(case: dict[str, Any]) -> dict[str, Any]:
    import os

    from probes.r345_residual_headroom import (
        build_control_response_map,
        endpoint_values,
        solve_minimum_norm_edge_residual,
    )

    from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits

    started = time.perf_counter()
    limits = FeedbackLimits()
    response = build_control_response_map(
        case["model"],
        horizon=case["base_outputs"].shape[0],
    )
    solution = solve_minimum_norm_edge_residual(
        base_outputs=case["base_outputs"],
        base_node_commands=case["base_node_commands"],
        previous_node_command=case["previous_node_command"],
        initial_soc=case["initial_soc"],
        response_map=response,
        limits=limits,
        minimum_improvement_fraction=MINIMUM_IMPROVEMENT,
        maximum_iterations=MAXIMUM_ITERATIONS,
        function_tolerance=FUNCTION_TOLERANCE,
        feasibility_tolerance=FEASIBILITY_TOLERANCE,
    )
    base = endpoint_values(
        case["base_outputs"],
        sample_period_seconds=limits.sample_period_seconds,
    )
    zero = endpoint_values(
        case["zero_outputs"],
        sample_period_seconds=limits.sample_period_seconds,
    )
    _counterfactual, nominal, robust = _candidate_endpoints(case, solution.edge_actions)
    return {
        "scenario_id": case["scenario_id"],
        "worker_pid": os.getpid(),
        "elapsed_seconds": time.perf_counter() - started,
        "feasible": bool(solution.feasible),
        "optimizer_valid": bool(solution.optimizer_valid),
        "target_feasible": bool(solution.target_feasible),
        "message": solution.message,
        "solver_iterations": solution.solver_iterations,
        "maximum_constraint_residual": solution.maximum_constraint_residual,
        "maximum_target_shortfall": solution.maximum_target_shortfall,
        "objective_value": solution.objective_value,
        "base_endpoints": base,
        "zero_control_endpoints": zero,
        "nominal_endpoints": nominal,
        "mismatch_bounded_endpoints": robust,
        "edge_actions": solution.edge_actions.tolist(),
        "residual_node_actions": solution.residual_node_actions.tolist(),
        "counterfactual_node_commands": solution.counterfactual_node_commands.tolist(),
        "counterfactual_soc": solution.counterfactual_soc.tolist(),
    }


def _local_worker(payload: tuple[dict[str, Any], Any]) -> dict[str, Any]:
    import os

    from probes.r345_residual_headroom import project_edge_sequence_to_headroom

    from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits

    case, proposed = payload
    started = time.perf_counter()
    solution = project_edge_sequence_to_headroom(
        proposed_edge_actions=proposed,
        base_node_commands=case["base_node_commands"],
        previous_node_command=case["previous_node_command"],
        initial_soc=case["initial_soc"],
        limits=FeedbackLimits(),
        maximum_iterations=MAXIMUM_ITERATIONS,
        function_tolerance=FUNCTION_TOLERANCE,
        feasibility_tolerance=FEASIBILITY_TOLERANCE,
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


def _local_proposals(cases: list[dict[str, Any]], oracle: list[dict[str, Any]]):
    import numpy as np
    from probes.r345_residual_headroom import (
        apply_standardized_ols,
        causal_edge_features,
        fit_standardized_ols,
    )

    edges = ((0, 1), (1, 2), (2, 3))
    oracle_by_id = {row["scenario_id"]: row for row in oracle}
    features: dict[str, list[np.ndarray]] = {}
    for case in cases:
        features[case["scenario_id"]] = [
            causal_edge_features(
                frequency_hz_before_action=case["frequency_before"],
                achieved_node_power_before_action=case["achieved_before"],
                commanded_node_power_before_action=case["commanded_before"],
                edge=edge,
                nominal_frequency_hz=60.0,
            )
            for edge in edges
        ]
    proposals = []
    for heldout in cases:
        predicted_columns = []
        for edge_index in range(3):
            train_features = np.vstack(
                [
                    features[case["scenario_id"]][edge_index]
                    for case in cases
                    if case["scenario_id"] != heldout["scenario_id"]
                ]
            )
            train_targets = np.concatenate(
                [
                    np.asarray(
                        oracle_by_id[case["scenario_id"]]["edge_actions"],
                        dtype=float,
                    )[:, edge_index]
                    for case in cases
                    if case["scenario_id"] != heldout["scenario_id"]
                ]
            )
            model = fit_standardized_ols(train_features, train_targets)
            predicted_columns.append(
                apply_standardized_ols(
                    model,
                    features[heldout["scenario_id"]][edge_index],
                )
            )
        proposals.append(np.column_stack(predicted_columns))
    return proposals


def _candidate_gate(
    cases: list[dict[str, Any]],
    oracle: list[dict[str, Any]],
    local: list[dict[str, Any]],
    *,
    candidate: str,
    endpoint_field: str,
) -> dict[str, Any]:
    from probes.r345_residual_headroom import paired_endpoint_gate

    oracle_by_id = {row["scenario_id"]: row for row in oracle}
    local_by_id = {row["scenario_id"]: row for row in local}
    selected = oracle_by_id if candidate == "oracle" else local_by_id
    groups = {
        "point": [case["point"] for case in cases],
        "channel": [case["channel"] for case in cases],
        "sign": [case["sign"] for case in cases],
    }
    endpoints = ("common_coordinate_iae", "differential_coordinate_energy")
    endpoint_gates = {}
    for endpoint in endpoints:
        changes = []
        for case in cases:
            scenario_id = case["scenario_id"]
            base = oracle_by_id[scenario_id]["base_endpoints"][endpoint]
            value = selected[scenario_id][endpoint_field][endpoint]
            changes.append((value - base) / base)
        endpoint_gates[endpoint] = paired_endpoint_gate(
            changes,
            groups=groups,
            minimum_improvement_fraction=MINIMUM_IMPROVEMENT,
            confidence_level=CONFIDENCE_LEVEL,
        )
    return {
        "pass": all(item["pass"] for item in endpoint_gates.values()),
        "endpoints": endpoint_gates,
    }


def _classify(
    cases: list[dict[str, Any]],
    oracle: list[dict[str, Any]],
    local: list[dict[str, Any]],
) -> dict[str, Any]:
    gates = {
        "oracle_optimizer_valid": all(row["optimizer_valid"] for row in oracle),
        "oracle_target_feasible": all(row["target_feasible"] for row in oracle),
        "local_projection_feasible": all(row["feasible"] for row in local),
        "oracle_nominal": _candidate_gate(
            cases,
            oracle,
            local,
            candidate="oracle",
            endpoint_field="nominal_endpoints",
        ),
        "oracle_mismatch_bounded": _candidate_gate(
            cases,
            oracle,
            local,
            candidate="oracle",
            endpoint_field="mismatch_bounded_endpoints",
        ),
        "local_nominal": _candidate_gate(
            cases,
            oracle,
            local,
            candidate="local",
            endpoint_field="nominal_endpoints",
        ),
        "local_mismatch_bounded": _candidate_gate(
            cases,
            oracle,
            local,
            candidate="local",
            endpoint_field="mismatch_bounded_endpoints",
        ),
    }
    pass_flags = [
        gates["oracle_optimizer_valid"],
        gates["oracle_target_feasible"],
        gates["local_projection_feasible"],
        gates["oracle_nominal"]["pass"],
        gates["oracle_mismatch_bounded"]["pass"],
        gates["local_nominal"]["pass"],
        gates["local_mismatch_bounded"]["pass"],
    ]
    classification = "RESIDUAL-PROBE-ELIGIBLE" if all(pass_flags) else "NO-TRAINING"
    failed = [
        name
        for name, value in gates.items()
        if not (value if isinstance(value, bool) else value["pass"])
    ]
    return {
        "classification": classification,
        "gates": gates,
        "failed_gates": failed,
        "residual_probe_authorized": classification == "RESIDUAL-PROBE-ELIGIBLE",
        "training_authorized": False,
        "distributed_runtime_authorized": False,
        "eval_authorized": False,
    }


def analyse(expected_sha256: str, *, out_dir: Path = DEFAULT_OUT) -> str:
    """Execute the one sealed, create-only R345 analysis attempt."""

    seal, seal_digest = load_seal(DEFAULT_SEAL, expected_sha256)
    if out_dir.exists():
        raise FileExistsError(f"R345 result root already exists: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=False)
    attempt_path = out_dir / "analysis_attempt.json"
    attempt_digest = _write_new_json(
        attempt_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "worker_processes": WORKERS,
            "native_threads_per_process": 1,
            "retry_authorized": False,
            "andes_executed": False,
            "training_executed": False,
            "distributed_runtime_executed": False,
            "eval_executed": False,
        },
    )
    started = time.perf_counter()
    try:
        cases = _load_cases()
        with ProcessPoolExecutor(max_workers=WORKERS) as executor:
            oracle = list(executor.map(_oracle_worker, cases))
            if not all(row["optimizer_valid"] for row in oracle):
                raise RuntimeError("one or more outcome-seeing residual optimizers were not valid")
            proposals = _local_proposals(cases, oracle)
            local = list(executor.map(_local_worker, zip(cases, proposals, strict=True)))
        if not all(row["feasible"] for row in local):
            raise RuntimeError("one or more neighbour-local projections were not valid")
        decision = _classify(cases, oracle, local)
        case_identity = [
            {
                "scenario_id": case["scenario_id"],
                "point": case["point"],
                "channel": case["channel"],
                "sign": case["sign"],
                "mismatch_envelope": case["mismatch_envelope"].tolist(),
                "parent_record_index": case["parent_record_index"],
                "parent_trace": case["parent_trace"],
                "zero_parent_record_index": case["zero_parent_record_index"],
                "zero_parent_trace": case["zero_parent_trace"],
            }
            for case in cases
        ]
        analysis_payload = {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "contract_payload_sha256": seal["contract_payload_sha256"],
            "analysis_attempt_sha256": attempt_digest,
            "elapsed_seconds": time.perf_counter() - started,
            "worker_processes": WORKERS,
            "oracle_unique_worker_pids": len({row["worker_pid"] for row in oracle}),
            "local_unique_worker_pids": len({row["worker_pid"] for row in local}),
            "case_identity": case_identity,
            "oracle": oracle,
            "neighbour_local": local,
            **decision,
            "andes_executed": False,
            "physical_trajectory_created": False,
            "training_executed": False,
            "reward_defined": False,
            "architecture_selected": False,
            "distributed_runtime_executed": False,
            "eval_executed": False,
        }
        analysis_path = out_dir / "analysis.json"
        analysis_digest = _write_new_json(analysis_path, analysis_payload)
        manifest_path = out_dir / "manifest.json"
        manifest_digest = _write_new_json(
            manifest_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "entries": [
                    {
                        "path": attempt_path.relative_to(ROOT).as_posix(),
                        "sha256": attempt_digest,
                    },
                    {
                        "path": analysis_path.relative_to(ROOT).as_posix(),
                        "sha256": analysis_digest,
                    },
                ],
            },
        )
        print(f"classification={decision['classification']}", flush=True)
        print(f"analysis_sha256={analysis_digest}", flush=True)
        print(f"manifest_sha256={manifest_digest}", flush=True)
        return analysis_digest
    except Exception as error:
        failure_path = out_dir / "failure.json"
        if not failure_path.exists():
            _write_new_json(
                failure_path,
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "question": QUESTION_ID,
                    "classification": "ANALYSIS-INVALID",
                    "created_utc": datetime.now(UTC).isoformat(),
                    "seal_sha256": seal_digest,
                    "analysis_attempt_sha256": attempt_digest,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "retry_authorized": False,
                    "training_authorized": False,
                },
            )
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--expected-sha256", required=True)
    analyse_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare":
        print(prepare(args.seal), flush=True)
        return 0
    if args.command == "analyse":
        analyse(args.expected_sha256, out_dir=args.out)
        return 0
    raise AssertionError(f"unexpected command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
