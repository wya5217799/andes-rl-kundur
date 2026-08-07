"""Rehearse, seal, and execute the create-only R359 causal residual gate.

The adapter fits one affine controller per physical edge from the exact public
fifteen-field neighbour observation.  Development is evaluated leave-one-case
out.  A failed development gate stops before the frozen holdout controller,
holdout counterfactuals, simulation, or training.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

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

from probes import r353_matched_residual_headroom as r353_probe  # noqa: E402
from probes.r359_neighbour_causal_residual import (  # noqa: E402
    build_development_targets,
    build_observations_from_parent_inventory,
    classify_neighbour_causal_gate,
    fit_full_development_controllers,
    leave_one_scenario_out_proposals,
    predict_with_frozen_controllers,
)
from scripts import run_r353_matched_residual_headroom as r353_parent  # noqa: E402

from andes_rl_kundur.control.active_power import (  # noqa: E402
    r272_frozen_bess_contract,
)
from andes_rl_kundur.control.residual_headroom import endpoint_values  # noqa: E402

ROUND_ID = "R359"
QUESTION_ID = "Q-0096"
SAMPLES_PER_TRACE = 25
STARTUP_ZERO_STEPS = 2
EDGE_FLOW_LIMIT = 0.05
MINIMUM_IMPROVEMENT = 0.02
CONFIDENCE_LEVEL = 0.95
MAXIMUM_SINGLE_SCENARIO_RATIO = 1.05
MODEL_ADEQUACY_TOLERANCE = 1.0e-8
MAXIMUM_ITERATIONS = 20_000
FUNCTION_TOLERANCE = 1.0e-9
FEASIBILITY_TOLERANCE = 1.0e-8

PLAN = ROOT / "memory/rounds/R359/plan.md"
QUESTION = ROOT / "memory/questions/Q-0096.md"
CAPACITY = ROOT / "memory/rounds/R359/capacity_evidence.json"
DEFAULT_REHEARSAL = ROOT / "memory/rounds/R359/rehearsal.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R359/analysis_seal.json"
DEFAULT_OUT = ROOT / "results/r359_neighbour_causal_residual"
R358_ANALYSIS = ROOT / "results/r358_physical_joint_endpoint_qp/analysis.json"
R358_MANIFEST = ROOT / "results/r358_physical_joint_endpoint_qp/manifest.json"
R358_SEAL = ROOT / "memory/rounds/R358/analysis_seal.json"
R358_CLAIM = ROOT / "memory/claims/CLM-0940.md"
R358_VERDICT = ROOT / "memory/rounds/R358/verdict.md"
R358_FEED = ROOT / "paper/decoupling_marl_model_first/reports/R358.md"


def build_contract() -> dict[str, Any]:
    """Return the prospectively frozen exact-information analysis contract."""

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "exact-neighbour-causal-affine-residual-gate",
        "inventory": {
            "development_pairs": 16,
            "holdout_pairs": 16,
            "positive_development_targets": 10,
            "zero_development_targets": 6,
            "samples_per_trace": SAMPLES_PER_TRACE,
        },
        "information": {
            "edge_actor_count": 3,
            "continuous_fields_per_actor": 15,
            "startup_zero_steps": STARTUP_ZERO_STEPS,
            "forbidden_fields": [
                "achieved_power",
                "operating_point",
                "disturbance_channel",
                "disturbance_sign",
                "scenario_identity",
                "other_edge_observations",
                "future_values",
                "realized_endpoints",
                "oracle_values",
            ],
        },
        "controller": {
            "maps": "one-standardized-affine-least-squares-map-per-edge",
            "development_validation": "leave-one-scenario-out",
            "formal_fit": "all-development-rows-once",
            "normalized_action_interval": [-1.0, 1.0],
            "edge_flow_limit_system_pu": EDGE_FLOW_LIMIT,
            "tuning_executed": False,
        },
        "statistics": {
            "minimum_improvement_fraction": MINIMUM_IMPROVEMENT,
            "confidence_level": CONFIDENCE_LEVEL,
            "maximum_single_scenario_ratio": MAXIMUM_SINGLE_SCENARIO_RATIO,
            "subgroups": ["point", "channel", "sign"],
        },
        "decision": {
            "positive": "NEIGHBOUR-CAUSAL-PROBE-ELIGIBLE",
            "negative": "NO-NEIGHBOUR-CAUSAL-HEADROOM",
            "invalid": "ANALYSIS-INVALID",
            "development_before_holdout": True,
            "retry_authorized": False,
        },
        "execution": {
            "worker_processes": 1,
            "native_threads_per_process": 1,
            "create_only": True,
        },
        "authorizations": {
            "simulation_authorized": False,
            "training_authorized": False,
            "distributed_runtime_authorized": False,
            "eval_authorized": False,
        },
    }


def source_paths(*, include_rehearsal: bool) -> dict[str, Path]:
    """Return the complete R359 implementation closure."""

    paths = {
        "plan": PLAN,
        "question": QUESTION,
        "capacity": CAPACITY,
        "adapter": Path(__file__).resolve(),
        "probe": ROOT / "probes/r359_neighbour_causal_residual.py",
        "probe_tests": ROOT / "tests/test_r359_neighbour_causal_residual.py",
        "controller_tests": ROOT / "tests/test_neighbour_causal_residual.py",
        "adapter_tests": ROOT / "tests/test_r359_neighbour_causal_residual_analysis.py",
        "r353_adapter": Path(r353_parent.__file__).resolve(),
        "r353_probe": Path(r353_probe.__file__).resolve(),
    }
    package_root = ROOT / "src/andes_rl_kundur"
    for path in sorted(package_root.rglob("*.py")):
        relative = path.relative_to(package_root).as_posix()
        paths[f"package_{relative}"] = path
    if include_rehearsal:
        paths["rehearsal"] = DEFAULT_REHEARSAL
    return paths


def parent_paths() -> dict[str, Path]:
    """Return exact R341/R352 trace parents plus the terminal R358 evidence."""

    paths = dict(r353_parent.parent_paths())
    paths.update(
        {
            "r358_analysis": R358_ANALYSIS,
            "r358_manifest": R358_MANIFEST,
            "r358_seal": R358_SEAL,
            "r358_claim": R358_CLAIM,
            "r358_verdict": R358_VERDICT,
            "r358_feed": R358_FEED,
        }
    )
    return paths


def _record(path: Path) -> dict[str, str]:
    try:
        rendered = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        rendered = path.resolve().as_posix()
    return {"path": rendered, "sha256": r353_parent._sha256_file(path)}


def _source_snapshot(
    *,
    include_rehearsal: bool,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
) -> dict[str, dict[str, str]]:
    paths = source_paths(include_rehearsal=False)
    if include_rehearsal:
        paths["rehearsal"] = rehearsal_path
    return {name: _record(path) for name, path in paths.items()}


def _parent_snapshot() -> dict[str, dict[str, str]]:
    return {name: _record(path) for name, path in parent_paths().items()}


def _verify_r358_parent() -> dict[str, Any]:
    for path in (R358_ANALYSIS, R358_MANIFEST, R358_SEAL):
        r353_parent._verify_sidecar(path)
    analysis = r353_parent._read_json(R358_ANALYSIS)
    if (
        analysis.get("round") != "R358"
        or analysis.get("question") != "Q-0095"
        or analysis.get("classification") != "PHYSICAL-HEADROOM-FOUND"
        or analysis.get("accepted_physical_feasible_candidate_count") != 10
        or analysis.get("inherited_relaxed_infeasible_count") != 6
        or analysis.get("information_constraints_included") is not False
        or analysis.get("physical_constraints_included") is not True
        or analysis.get("holdout_cases_read") != 0
        or analysis.get("andes_executed") is not False
        or analysis.get("training_authorized") is not False
        or analysis.get("simulation_authorized") is not False
    ):
        raise RuntimeError("R358 parent decision drift")
    candidates = analysis.get("candidate_results")
    partition = analysis.get("r356_status_partition")
    if (
        not isinstance(candidates, list)
        or len(candidates) != 10
        or not all(
            row.get("accepted") is True and row.get("target_feasible") is True for row in candidates
        )
        or not isinstance(partition, Mapping)
        or len(partition.get("primal_infeasible", [])) != 6
    ):
        raise RuntimeError("R358 target partition drift")
    return analysis


def _verify_entry_preconditions(
    out_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if out_dir.exists():
        raise FileExistsError(f"R359 result root already exists: {out_dir}")
    if "state: active" not in PLAN.read_text(encoding="utf-8"):
        raise RuntimeError("R359 active plan identity is missing")
    question_text = QUESTION.read_text(encoding="utf-8")
    if "status: in-flight" not in question_text or "R359:" not in question_text:
        raise RuntimeError("R359 in-flight question identity is missing")
    for path in source_paths(include_rehearsal=False).values():
        if not path.is_file():
            raise RuntimeError(f"R359 source is missing: {path}")
    r353_parent._verify_parent_decisions()
    r358 = _verify_r358_parent()
    development = r353_parent.load_parent_inventory("development")
    holdout = r353_parent.load_parent_inventory("holdout")
    if len(development) != 16 or len(holdout) != 16:
        raise RuntimeError("R359 requires sixteen exact pairs per bank")
    return development, holdout, r358


def _observations(
    inventory: Sequence[Mapping[str, Any]],
) -> dict[str, dict[tuple[int, int], tuple[Any, ...]]]:
    return build_observations_from_parent_inventory(
        inventory=inventory,
        physical_contract=r272_frozen_bess_contract(),
        nominal_frequency_hz=60.0,
        sample_period_seconds=0.2,
        startup_zero_steps=STARTUP_ZERO_STEPS,
        expected_horizon=SAMPLES_PER_TRACE,
    )


def _targets(
    cases: Sequence[Mapping[str, Any]],
    r358: Mapping[str, Any],
) -> dict[str, np.ndarray]:
    return build_development_targets(
        scenario_ids=[str(case["scenario_id"]) for case in cases],
        candidate_results=r358["candidate_results"],
        inherited_infeasible_scenario_ids=r358["r356_status_partition"]["primal_infeasible"],
        horizon=SAMPLES_PER_TRACE,
        edge_flow_limit_system_pu=EDGE_FLOW_LIMIT,
        startup_zero_steps=STARTUP_ZERO_STEPS,
    )


def _baseline_rows(cases: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": str(case["scenario_id"]),
            "base_endpoints": endpoint_values(
                case["base_outputs"],
                sample_period_seconds=0.2,
            ),
        }
        for case in cases
    ]


def _endpoint_gates(
    cases: Sequence[Mapping[str, Any]],
    projected: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    baseline = _baseline_rows(cases)
    return {
        "nominal": r353_probe.candidate_gate(
            cases,
            baseline,
            projected,
            candidate="local",
            endpoint_field="nominal_endpoints",
            minimum_improvement_fraction=MINIMUM_IMPROVEMENT,
            confidence_level=CONFIDENCE_LEVEL,
            maximum_single_scenario_ratio=MAXIMUM_SINGLE_SCENARIO_RATIO,
        ),
        "mismatch_bounded": r353_probe.candidate_gate(
            cases,
            baseline,
            projected,
            candidate="local",
            endpoint_field="mismatch_bounded_endpoints",
            minimum_improvement_fraction=MINIMUM_IMPROVEMENT,
            confidence_level=CONFIDENCE_LEVEL,
            maximum_single_scenario_ratio=MAXIMUM_SINGLE_SCENARIO_RATIO,
        ),
    }


def _project_cases(
    cases: Sequence[Mapping[str, Any]],
    proposals: Mapping[str, np.ndarray],
) -> list[dict[str, Any]]:
    return [
        r353_probe.project_local_case(
            case,
            proposals[str(case["scenario_id"])] * EDGE_FLOW_LIMIT,
            maximum_iterations=MAXIMUM_ITERATIONS,
            function_tolerance=FUNCTION_TOLERANCE,
            feasibility_tolerance=FEASIBILITY_TOLERANCE,
        )
        for case in cases
    ]


def _development_stage(
    inventory: Sequence[Mapping[str, Any]],
    r358: Mapping[str, Any],
) -> dict[str, Any]:
    cases = r353_parent._build_cases(list(inventory))
    envelopes = r353_probe.development_envelopes(cases)
    r353_probe.assign_envelopes(cases, envelopes)
    observations = _observations(inventory)
    targets = _targets(cases, r358)
    proposals = leave_one_scenario_out_proposals(
        observations_by_scenario=observations,
        normalized_targets_by_scenario=targets,
        horizon=SAMPLES_PER_TRACE,
        startup_zero_steps=STARTUP_ZERO_STEPS,
    )
    projected = _project_cases(cases, proposals)
    gates = _endpoint_gates(cases, projected)
    integrity = {
        "complete_inventory": len(cases) == 16 and len(observations) == 16 and len(targets) == 16,
        "exact_information": all(
            len(edge_rows) == 3
            and all(
                len(rows) == SAMPLES_PER_TRACE - STARTUP_ZERO_STEPS for rows in edge_rows.values()
            )
            for edge_rows in observations.values()
        ),
        "startup_mask": all(
            np.array_equal(
                proposal[:STARTUP_ZERO_STEPS],
                np.zeros((STARTUP_ZERO_STEPS, 3)),
            )
            for proposal in proposals.values()
        ),
        "physical_projection": all(row.get("feasible") is True for row in projected),
    }
    scientific = {
        "nominal_endpoints": gates["nominal"]["pass"],
        "mismatch_bounded_endpoints": gates["mismatch_bounded"]["pass"],
    }
    decision = classify_neighbour_causal_gate(
        integrity_checks=integrity,
        scientific_checks=scientific,
    )
    return {
        "cases": cases,
        "envelopes": envelopes,
        "observations": observations,
        "targets": targets,
        "proposals": proposals,
        "projected": projected,
        "gates": gates,
        "integrity_checks": integrity,
        "scientific_checks": scientific,
        "decision": decision,
    }


def _controller_payload(controllers: Sequence[Any]) -> list[dict[str, Any]]:
    return [
        {
            "edge": list(controller.edge),
            "mean": controller.model.mean.tolist(),
            "scale": controller.model.scale.tolist(),
            "coefficients": controller.model.coefficients.tolist(),
        }
        for controller in controllers
    ]


def rehearsal(
    record_path: Path = DEFAULT_REHEARSAL,
    *,
    out_dir: Path = DEFAULT_OUT,
) -> str:
    """Exercise the same pre-attempt closure without outcome evaluation."""

    if record_path.exists():
        raise FileExistsError(f"create-only output already exists: {record_path}")
    development, holdout, r358 = _verify_entry_preconditions(out_dir)
    development_observations = _observations(development)
    holdout_observations = _observations(holdout)
    cases = r353_parent._build_cases(development)
    targets = _targets(cases, r358)
    if not (
        len(development_observations) == 16
        and len(holdout_observations) == 16
        and len(targets) == 16
        and sum(np.any(target, axis=None) for target in targets.values()) == 10
    ):
        raise RuntimeError("R359 rehearsal inventory or observation check failed")
    contract = build_contract()
    return r353_parent._write_new_json(
        record_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_payload_sha256": r353_parent._payload_sha256(contract),
            "development_pair_count": len(development),
            "holdout_pair_count": len(holdout),
            "development_target_partition": {"positive": 10, "zero": 6},
            "observation_fields_per_edge": 15,
            "observation_rows_per_edge": SAMPLES_PER_TRACE - STARTUP_ZERO_STEPS,
            "holdout_residual_labels_read": 0,
            "source_snapshot": _source_snapshot(include_rehearsal=False),
            "parent_snapshot": _parent_snapshot(),
            "formal_output_absent": True,
            "attempt_created": False,
            "result_created": False,
            "simulator_executed": False,
            "training_executed": False,
        },
    )


def prepare(
    seal_path: Path = DEFAULT_SEAL,
    *,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
    out_dir: Path = DEFAULT_OUT,
) -> str:
    """Create the exact source-, parent-, and rehearsal-bound R359 seal."""

    if seal_path.exists():
        raise FileExistsError(f"create-only output already exists: {seal_path}")
    _verify_entry_preconditions(out_dir)
    r353_parent._verify_sidecar(rehearsal_path)
    record = r353_parent._read_json(rehearsal_path)
    contract = build_contract()
    sources = _source_snapshot(include_rehearsal=False)
    parents = _parent_snapshot()
    if (
        record.get("round") != ROUND_ID
        or record.get("question") != QUESTION_ID
        or record.get("contract_payload_sha256") != r353_parent._payload_sha256(contract)
        or record.get("development_pair_count") != 16
        or record.get("holdout_pair_count") != 16
        or record.get("development_target_partition") != {"positive": 10, "zero": 6}
        or record.get("holdout_residual_labels_read") != 0
        or record.get("source_snapshot") != sources
        or record.get("parent_snapshot") != parents
        or record.get("formal_output_absent") is not True
        or record.get("attempt_created") is not False
    ):
        raise RuntimeError("R359 rehearsal record drift")
    return r353_parent._write_new_json(
        seal_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract": contract,
            "contract_payload_sha256": r353_parent._payload_sha256(contract),
            "sources": _source_snapshot(
                include_rehearsal=True,
                rehearsal_path=rehearsal_path,
            ),
            "parents": parents,
            "result_root_absent_at_freeze": True,
            "retry_authorized": False,
        },
    )


def load_seal(
    path: Path,
    expected_sha256: str,
    *,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
    out_dir: Path = DEFAULT_OUT,
) -> tuple[dict[str, Any], str]:
    """Verify the exact R359 seal and complete immutable closure."""

    payload = r353_parent._read_json(path)
    actual = r353_parent._sha256_file(path)
    if actual != expected_sha256:
        raise RuntimeError(f"R359 seal digest mismatch: {actual}")
    r353_parent._verify_sidecar(path)
    _verify_entry_preconditions(out_dir)
    contract = payload.get("contract")
    if (
        payload.get("round") != ROUND_ID
        or payload.get("question") != QUESTION_ID
        or contract != build_contract()
        or payload.get("contract_payload_sha256") != r353_parent._payload_sha256(contract)
        or payload.get("sources")
        != _source_snapshot(
            include_rehearsal=True,
            rehearsal_path=rehearsal_path,
        )
        or payload.get("parents") != _parent_snapshot()
        or payload.get("retry_authorized") is not False
    ):
        raise RuntimeError("R359 contract, source, or parent drift")
    return payload, actual


def analyse(
    expected_sha256: str,
    *,
    out_dir: Path = DEFAULT_OUT,
    seal_path: Path = DEFAULT_SEAL,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
) -> str:
    """Execute the single sealed staged offline R359 analysis."""

    seal, seal_digest = load_seal(
        seal_path,
        expected_sha256,
        rehearsal_path=rehearsal_path,
        out_dir=out_dir,
    )
    development_inventory, holdout_inventory, r358 = _verify_entry_preconditions(out_dir)
    out_dir.mkdir(parents=True, exist_ok=False)
    attempt_path = out_dir / "analysis_attempt.json"
    attempt_digest = r353_parent._write_new_json(
        attempt_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "worker_processes": 1,
            "native_threads_per_process": 1,
            "retry_authorized": False,
            "holdout_residual_labels_read": 0,
            "simulator_executed": False,
            "training_executed": False,
        },
    )
    started = time.perf_counter()
    try:
        development = _development_stage(development_inventory, r358)
        decision = development["decision"]
        holdout_payload: dict[str, Any] | None = None
        frozen_entries: list[dict[str, str]] = []
        holdout_cases_read = 0
        if decision["classification"] == "NEIGHBOUR-CAUSAL-PROBE-ELIGIBLE":
            controllers = fit_full_development_controllers(
                observations_by_scenario=development["observations"],
                normalized_targets_by_scenario=development["targets"],
                horizon=SAMPLES_PER_TRACE,
                startup_zero_steps=STARTUP_ZERO_STEPS,
            )
            controller_path = out_dir / "frozen_controller.json"
            controller_digest = r353_parent._write_new_json(
                controller_path,
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "controllers": _controller_payload(controllers),
                    "development_scenario_ids": sorted(development["targets"]),
                    "holdout_labels_read_before_freeze": 0,
                },
            )
            holdout_observations = _observations(holdout_inventory)
            normalized_predictions = {
                scenario_id: predict_with_frozen_controllers(
                    controllers=controllers,
                    observations=rows,
                    horizon=SAMPLES_PER_TRACE,
                    startup_zero_steps=STARTUP_ZERO_STEPS,
                )
                for scenario_id, rows in holdout_observations.items()
            }
            predictions_path = out_dir / "holdout_predictions.json"
            predictions_digest = r353_parent._write_new_json(
                predictions_path,
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "controller_sha256": controller_digest,
                    "predictions": {
                        key: value.tolist() for key, value in sorted(normalized_predictions.items())
                    },
                    "holdout_labels_read_before_freeze": 0,
                },
            )
            frozen_entries.extend(
                [
                    {
                        "path": controller_path.relative_to(ROOT).as_posix(),
                        "sha256": controller_digest,
                    },
                    {
                        "path": predictions_path.relative_to(ROOT).as_posix(),
                        "sha256": predictions_digest,
                    },
                ]
            )
            holdout_cases = r353_parent._build_cases(holdout_inventory)
            r353_probe.assign_envelopes(holdout_cases, development["envelopes"])
            adequacy = r353_probe.model_adequacy_gate(
                holdout_cases,
                development["envelopes"],
                absolute_tolerance=MODEL_ADEQUACY_TOLERANCE,
            )
            projected = _project_cases(holdout_cases, normalized_predictions)
            gates = _endpoint_gates(holdout_cases, projected)
            holdout_integrity = {
                "complete_inventory": len(holdout_cases) == 16,
                "frozen_controller_before_outcomes": True,
                "holdout_model_adequacy": adequacy["pass"],
                "physical_projection": all(row.get("feasible") is True for row in projected),
            }
            holdout_scientific = {
                "nominal_endpoints": gates["nominal"]["pass"],
                "mismatch_bounded_endpoints": gates["mismatch_bounded"]["pass"],
            }
            decision = classify_neighbour_causal_gate(
                integrity_checks=holdout_integrity,
                scientific_checks=holdout_scientific,
            )
            holdout_payload = {
                "case_count": len(holdout_cases),
                "model_adequacy": adequacy,
                "projected": projected,
                "gates": gates,
                "integrity_checks": holdout_integrity,
                "scientific_checks": holdout_scientific,
                "decision": decision,
            }
            holdout_cases_read = len(holdout_cases)

        analysis_path = out_dir / "analysis.json"
        analysis_digest = r353_parent._write_new_json(
            analysis_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "seal_sha256": seal_digest,
                "contract_payload_sha256": seal["contract_payload_sha256"],
                "analysis_attempt_sha256": attempt_digest,
                "elapsed_seconds": time.perf_counter() - started,
                "classification": decision["classification"],
                "development": {
                    "case_count": len(development["cases"]),
                    "target_partition": {"positive": 10, "zero": 6},
                    "projected": development["projected"],
                    "gates": development["gates"],
                    "integrity_checks": development["integrity_checks"],
                    "scientific_checks": development["scientific_checks"],
                    "decision": development["decision"],
                },
                "holdout": holdout_payload,
                "holdout_cases_read": holdout_cases_read,
                "holdout_residual_labels_read": 0,
                "exact_information_constraints_included": True,
                "physical_constraints_included": True,
                "simulation_authorized": False,
                "training_authorized": False,
                "distributed_runtime_executed": False,
                "eval_executed": False,
                "simulator_executed": False,
            },
        )
        manifest_path = out_dir / "manifest.json"
        manifest_digest = r353_parent._write_new_json(
            manifest_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "entries": [
                    {
                        "path": attempt_path.relative_to(ROOT).as_posix(),
                        "sha256": attempt_digest,
                    },
                    *frozen_entries,
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
            r353_parent._write_new_json(
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
                    "holdout_cases_read": 0,
                    "training_authorized": False,
                    "simulation_authorized": False,
                },
            )
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("rehearsal")
    subparsers.add_parser("prepare")
    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--expected-seal-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rehearsal":
        print(f"rehearsal_sha256={rehearsal()}", flush=True)
    elif args.command == "prepare":
        print(f"seal_sha256={prepare()}", flush=True)
    else:
        analyse(str(args.expected_seal_sha256))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
