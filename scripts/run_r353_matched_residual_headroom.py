"""Rehearse, seal, and execute the create-only R353 residual analysis.

The adapter reads frozen R352 traces and R341 point models.  It never runs a
simulator or training process, and every persistent output is create-only.

Usage::

    python scripts/run_r353_matched_residual_headroom.py rehearsal
    python scripts/run_r353_matched_residual_headroom.py prepare
    python scripts/run_r353_matched_residual_headroom.py analyse \
        --expected-seal-sha256 <sha256>

Failure modes include source/parent drift, an existing create-only output,
malformed parent identity, uncertified optimization, infeasible projection,
and a scientific stage stop.  None authorizes a retry, simulator, or training.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
import time
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


ROUND_ID = "R353"
QUESTION_ID = "Q-0094"
MINIMUM_IMPROVEMENT = 0.02
CONFIDENCE_LEVEL = 0.95
MAXIMUM_SINGLE_SCENARIO_RATIO = 1.05
MODEL_ADEQUACY_TOLERANCE = 1.0e-8
SELECTED_CANDIDATE_ID = "kf500_kr0"
SAMPLES_PER_TRACE = 25
UNRECOVERABLE_STARTUP_SAMPLES = 2
MAXIMUM_ITERATIONS = 20_000
FUNCTION_TOLERANCE = 1.0e-9
FEASIBILITY_TOLERANCE = 1.0e-8
POINT_MODEL_DIGESTS = {
    "FV0": "c858441f0fd48c7f69da98f569bca4a88f3547324af6a301ebf42de60c055cf5",
    "FV1": "c65ead6face6015ed951b7d55b13b90847fb557462ab946d730392666cf9200c",
}
DEFAULT_SEAL = ROOT / "memory/rounds/R353/analysis_seal.json"
DEFAULT_REHEARSAL = ROOT / "memory/rounds/R353/rehearsal.json"
DEFAULT_OUT = ROOT / "results/r353_matched_residual_headroom"
PLAN = ROOT / "memory/rounds/R353/plan.md"
R352_ROOT = ROOT / "results/r352_distributed_controller_loop_v2"
R352_DEVELOPMENT_EXECUTION = R352_ROOT / "development_execution.json"
R352_DEVELOPMENT_ANALYSIS = R352_ROOT / "development_analysis.json"
R352_DEVELOPMENT_MANIFEST = R352_ROOT / "development_manifest.json"
R352_FORMAL_EXECUTION = R352_ROOT / "formal_execution.json"
R352_FORMAL_ANALYSIS = R352_ROOT / "formal_analysis.json"
R352_FORMAL_MANIFEST = R352_ROOT / "formal_manifest.json"
R352_FORMAL_SEAL = ROOT / "memory/rounds/R352/formal_seal.json"
R341_ROOT = ROOT / "results/r341_staged_fresh_model_validation"
R341_CANDIDATE_MODELS = R341_ROOT / "candidate_models.json"
R341_ANALYSIS = R341_ROOT / "analysis.json"
R341_VALIDATION_MANIFEST = R341_ROOT / "validation_manifest.json"
R341_VALIDATION_SEAL = ROOT / "memory/rounds/R341/validation_seal.json"


def build_contract() -> dict[str, Any]:
    """Return the prospectively frozen R353 analysis contract."""

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "create-only-matched-neighbour-local-residual-headroom",
        "inventory": {
            "development_pairs": 16,
            "holdout_pairs": 16,
            "primary_records_per_bank": 32,
            "samples_per_trace": SAMPLES_PER_TRACE,
            "joint_arm_included": False,
        },
        "residual": {
            "common_coordinate": 0.0,
            "edge_coordinates": 3,
            "minimum_improvement_fraction": MINIMUM_IMPROVEMENT,
            "maximum_single_scenario_ratio": MAXIMUM_SINGLE_SCENARIO_RATIO,
            "holdout_model_adequacy_tolerance": MODEL_ADEQUACY_TOLERANCE,
            "oracle": "R350-certified-three-start-smooth-convex",
            "governor": "physical-headroom-projection",
        },
        "local_information": {
            "feature_count_per_edge": 13,
            "unrecoverable_startup_samples": UNRECOVERABLE_STARTUP_SAMPLES,
            "estimator": "one-standardized-affine-least-squares-map-per-edge",
            "development_validation": "leave-one-scenario-out",
            "formal_fit": "all-development-rows-once",
            "holdout_refit": False,
        },
        "statistics": {
            "unit": "scenario",
            "confidence_level": CONFIDENCE_LEVEL,
            "subgroups": ["point", "channel", "sign"],
        },
        "execution": {
            "worker_processes": 1,
            "native_threads_per_process": 1,
            "create_only": True,
            "development_before_holdout": True,
            "retry_authorized": False,
        },
        "decision": {
            "positive": "RESIDUAL-PROBE-ELIGIBLE",
            "negative": "NO-TRAINING",
            "invalid": "ANALYSIS-INVALID",
            "training_authorized": False,
        },
        "authorizations": {
            "simulation_authorized": False,
            "training_authorized": False,
            "distributed_runtime_authorized": False,
            "eval_authorized": False,
        },
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


def _verify_sidecar(path: Path) -> None:
    sidecar = Path(f"{path}.sha256")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    actual = _sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"sidecar digest mismatch: {path}")


def _load_trace(path: Path, expected_sha256: str) -> dict[str, Any]:
    if _sha256_file(path) != expected_sha256:
        raise RuntimeError(f"R352 trace digest mismatch: {path}")
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict) or len(payload.get("rows", [])) != SAMPLES_PER_TRACE:
        raise RuntimeError(f"R352 trace structure mismatch: {path}")
    return payload


def _expected_scenarios(bank: str) -> set[str]:
    prefix = "development" if bank == "development" else "holdout"
    return {
        f"{prefix}__{point}__{channel}__{sign}"
        for point in ("FV0", "FV1")
        for channel in ("PQ_0", "PQ_1", "PQ_Bus14", "PQ_Bus15")
        for sign in ("negative", "positive")
    }


def load_parent_inventory(bank: str) -> list[dict[str, Any]]:
    """Load one exact R352 zero/local bank with manifest-bound traces."""

    from probes.r353_matched_residual_headroom import (
        pair_primary_records,
        select_parent_records,
        verify_parent_trace_identity,
    )

    if bank == "development":
        execution_path = R352_DEVELOPMENT_EXECUTION
        manifest_path = R352_DEVELOPMENT_MANIFEST
        expected_record_count = 160
    elif bank == "holdout":
        execution_path = R352_FORMAL_EXECUTION
        manifest_path = R352_FORMAL_MANIFEST
        expected_record_count = 48
    else:
        raise ValueError("bank must be 'development' or 'holdout'")

    _verify_sidecar(execution_path)
    _verify_sidecar(manifest_path)
    execution = _read_json(execution_path)
    manifest = _read_json(manifest_path)
    records = execution.get("records", [])
    if (
        execution.get("round") != "R352"
        or execution.get("question") != "Q-0093"
        or execution.get("record_count") != expected_record_count
        or len(records) != expected_record_count
        or execution.get("training_executed") is not False
    ):
        raise RuntimeError(f"R352 {bank} execution identity drift")
    manifest_entries = {
        str(entry["path"]): str(entry["sha256"]) for entry in manifest.get("entries", [])
    }

    selected_records = select_parent_records(
        records,
        bank=bank,
        selected_candidate_id=SELECTED_CANDIDATE_ID,
    )

    pairs = pair_primary_records(
        selected_records,
        manifest_entries=manifest_entries,
        expected_scenarios=_expected_scenarios(bank),
        selected_candidate_id=SELECTED_CANDIDATE_ID,
    )
    inventory: list[dict[str, Any]] = []
    for scenario_id in sorted(pairs):
        arms: dict[str, dict[str, Any]] = {}
        for arm in ("zero_edge", "selected_local"):
            record = pairs[scenario_id][arm]
            trace_ref = record["trace"]
            trace = _load_trace(ROOT / trace_ref["path"], str(trace_ref["sha256"]))
            verify_parent_trace_identity(
                record,
                trace,
                bank=bank,
                samples_per_trace=SAMPLES_PER_TRACE,
            )
            arms[arm] = {"record": record, "trace": trace}
        selected_record = arms["selected_local"]["record"]
        inventory.append(
            {
                "scenario_id": scenario_id,
                "point": str(selected_record["point"]),
                "channel": scenario_id.split("__")[2],
                "sign": scenario_id.split("__")[3],
                "arms": arms,
            }
        )
    return inventory


def source_paths(*, include_rehearsal: bool) -> dict[str, Path]:
    """Return the full implementation closure bound by the R353 seal."""

    paths = {
        "plan": PLAN,
        "adapter": Path(__file__).resolve(),
        "probe": ROOT / "probes/r353_matched_residual_headroom.py",
        "probe_tests": ROOT / "tests/test_r353_matched_residual_headroom.py",
        "adapter_tests": ROOT / "tests/test_r353_matched_residual_analysis.py",
    }
    package_root = ROOT / "src/andes_rl_kundur"
    for path in sorted(package_root.rglob("*.py")):
        relative = path.relative_to(package_root).as_posix()
        paths[f"package_{relative}"] = path
    if include_rehearsal:
        paths["rehearsal"] = DEFAULT_REHEARSAL
    return paths


def parent_paths() -> dict[str, Path]:
    """Return R341/R352 parents plus exactly 64 zero/local trace files."""

    paths = {
        "r352_formal_seal": R352_FORMAL_SEAL,
        "r352_development_execution": R352_DEVELOPMENT_EXECUTION,
        "r352_development_analysis": R352_DEVELOPMENT_ANALYSIS,
        "r352_development_manifest": R352_DEVELOPMENT_MANIFEST,
        "r352_formal_execution": R352_FORMAL_EXECUTION,
        "r352_formal_analysis": R352_FORMAL_ANALYSIS,
        "r352_formal_manifest": R352_FORMAL_MANIFEST,
        "r341_validation_seal": R341_VALIDATION_SEAL,
        "r341_analysis": R341_ANALYSIS,
        "r341_candidate_models": R341_CANDIDATE_MODELS,
        "r341_validation_manifest": R341_VALIDATION_MANIFEST,
    }
    for bank in ("development", "holdout"):
        for case in load_parent_inventory(bank):
            for arm, payload in case["arms"].items():
                name = f"{bank}_trace_{case['scenario_id']}_{arm}"
                paths[name] = ROOT / payload["record"]["trace"]["path"]
    return paths


def _source(path: Path) -> dict[str, str]:
    try:
        rendered = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        rendered = path.resolve().as_posix()
    return {"path": rendered, "sha256": _sha256_file(path)}


def _source_snapshot(
    *,
    include_rehearsal: bool,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
) -> dict[str, dict[str, str]]:
    paths = source_paths(include_rehearsal=False)
    if include_rehearsal:
        paths["rehearsal"] = rehearsal_path
    return {name: _source(path) for name, path in paths.items()}


def _parent_snapshot() -> dict[str, dict[str, str]]:
    return {name: _source(path) for name, path in parent_paths().items()}


def _verify_parent_decisions() -> None:
    for path in parent_paths().values():
        _verify_sidecar(path)
    development = _read_json(R352_DEVELOPMENT_ANALYSIS)
    formal = _read_json(R352_FORMAL_ANALYSIS)
    model = _read_json(R341_ANALYSIS)
    if (
        development.get("classification") != "DEVELOPMENT-CANDIDATE-SELECTED"
        or development.get("selected", {}).get("candidate_id") != SELECTED_CANDIDATE_ID
        or development.get("holdout_records_inspected") is not False
        or development.get("training_authorized") is not False
    ):
        raise RuntimeError("R352 development decision drift")
    if (
        formal.get("classification") != "DISTRIBUTED-DETERMINISTIC-HOLDOUT-PASS"
        or formal.get("selected_controller", {}).get("candidate_id") != SELECTED_CANDIDATE_ID
        or formal.get("local_gate", {}).get("passed") is not True
        or formal.get("training_authorized") is not False
    ):
        raise RuntimeError("R352 formal decision drift")
    if (
        model.get("classification") != "ALLOW-MODEL-GATE"
        or model.get("validity_pass") is not True
        or model.get("training_executed") is not False
    ):
        raise RuntimeError("R341 model decision drift")


def _verify_entry_preconditions(out_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if out_dir.exists():
        raise FileExistsError(f"R353 result root already exists: {out_dir}")
    plan_text = PLAN.read_text(encoding="utf-8")
    if "state: active" not in plan_text or QUESTION_ID not in plan_text:
        raise RuntimeError("R353 active plan identity is missing")
    for path in source_paths(include_rehearsal=False).values():
        if not path.is_file():
            raise RuntimeError(f"R353 source is missing: {path}")
    _verify_parent_decisions()
    development = load_parent_inventory("development")
    holdout = load_parent_inventory("holdout")
    if len(development) != 16 or len(holdout) != 16:
        raise RuntimeError("R353 expected sixteen pairs in each parent bank")
    return development, holdout


def rehearsal(
    record_path: Path = DEFAULT_REHEARSAL,
    *,
    out_dir: Path = DEFAULT_OUT,
) -> str:
    """Exercise the formal entry's pre-attempt path without reading R353 outcomes."""

    if record_path.exists():
        raise FileExistsError(f"create-only output already exists: {record_path}")
    development, holdout = _verify_entry_preconditions(out_dir)
    contract = build_contract()
    return _write_new_json(
        record_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_payload_sha256": _payload_sha256(contract),
            "development_pair_count": len(development),
            "holdout_pair_count": len(holdout),
            "source_snapshot": _source_snapshot(include_rehearsal=False),
            "parent_snapshot": _parent_snapshot(),
            "formal_output_absent": True,
            "attempt_created": False,
            "result_created": False,
            "andes_executed": False,
            "training_executed": False,
        },
    )


def prepare(
    seal_path: Path = DEFAULT_SEAL,
    *,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
    out_dir: Path = DEFAULT_OUT,
) -> str:
    """Create the source- and parent-bound R353 seal after rehearsal."""

    if seal_path.exists():
        raise FileExistsError(f"create-only output already exists: {seal_path}")
    _verify_entry_preconditions(out_dir)
    _verify_sidecar(rehearsal_path)
    rehearsal_record = _read_json(rehearsal_path)
    contract = build_contract()
    current_sources = _source_snapshot(include_rehearsal=False)
    current_parents = _parent_snapshot()
    if (
        rehearsal_record.get("round") != ROUND_ID
        or rehearsal_record.get("question") != QUESTION_ID
        or rehearsal_record.get("contract_payload_sha256") != _payload_sha256(contract)
        or rehearsal_record.get("source_snapshot") != current_sources
        or rehearsal_record.get("parent_snapshot") != current_parents
        or rehearsal_record.get("formal_output_absent") is not True
        or rehearsal_record.get("attempt_created") is not False
    ):
        raise RuntimeError("R353 rehearsal record drift")
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "sources": _source_snapshot(
            include_rehearsal=True,
            rehearsal_path=rehearsal_path,
        ),
        "parents": current_parents,
        "result_root_absent_at_freeze": True,
        "retry_authorized": False,
    }
    return _write_new_json(seal_path, payload)


def load_seal(
    path: Path,
    expected_sha256: str,
    *,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
    out_dir: Path = DEFAULT_OUT,
) -> tuple[dict[str, Any], str]:
    """Verify the exact R353 seal, contract, and complete source closure."""

    payload = _read_json(path)
    actual = _sha256_file(path)
    if actual != expected_sha256:
        raise RuntimeError(f"R353 seal digest mismatch: {actual}")
    contract = payload.get("contract")
    if (
        payload.get("round") != ROUND_ID
        or payload.get("question") != QUESTION_ID
        or contract != build_contract()
        or payload.get("contract_payload_sha256") != _payload_sha256(contract)
        or payload.get("sources")
        != _source_snapshot(
            include_rehearsal=True,
            rehearsal_path=rehearsal_path,
        )
        or payload.get("parents") != _parent_snapshot()
    ):
        raise RuntimeError("R353 contract, source, or parent drift")
    _verify_entry_preconditions(out_dir)
    return payload, actual


def _build_cases(inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Load the frozen point payload and delegate scientific case construction."""

    from probes.r353_matched_residual_headroom import build_matched_cases

    return build_matched_cases(
        inventory,
        candidate_models=_read_json(R341_CANDIDATE_MODELS),
        point_model_digests=POINT_MODEL_DIGESTS,
        samples_per_trace=SAMPLES_PER_TRACE,
        nominal_frequency_hz=60.0,
        sample_period_seconds=0.2,
    )


def _case_identity(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
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


def analyse(expected_sha256: str, *, out_dir: Path = DEFAULT_OUT) -> str:
    """Execute the one sealed, staged, create-only R353 analysis attempt."""

    from probes.r353_matched_residual_headroom import (
        assign_envelopes,
        development_envelopes,
        evaluate_development_stage,
        evaluate_holdout_stage,
    )

    seal, seal_digest = load_seal(
        DEFAULT_SEAL,
        expected_sha256,
        out_dir=out_dir,
    )
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
            "worker_processes": 1,
            "native_threads_per_process": 1,
            "retry_authorized": False,
            "andes_executed": False,
            "training_executed": False,
        },
    )
    started = time.perf_counter()
    try:
        development_cases = _build_cases(load_parent_inventory("development"))
        envelopes = development_envelopes(development_cases)
        assign_envelopes(development_cases, envelopes)
        development_stage = evaluate_development_stage(
            development_cases,
            minimum_improvement_fraction=MINIMUM_IMPROVEMENT,
            confidence_level=CONFIDENCE_LEVEL,
            maximum_single_scenario_ratio=MAXIMUM_SINGLE_SCENARIO_RATIO,
            startup_samples=UNRECOVERABLE_STARTUP_SAMPLES,
            maximum_iterations=MAXIMUM_ITERATIONS,
            function_tolerance=FUNCTION_TOLERANCE,
            feasibility_tolerance=FEASIBILITY_TOLERANCE,
        )
        development_oracle = development_stage["oracle"]
        development_local = development_stage["local"]
        development_decision = development_stage["decision"]

        holdout_cases: list[dict[str, Any]] = []
        holdout_oracle: list[dict[str, Any]] = []
        holdout_local: list[dict[str, Any]] = []
        model_adequacy: dict[str, Any] | None = None
        if development_decision["conclusion"] != "RESIDUAL-PROBE-ELIGIBLE":
            final_decision = development_decision
            stage_stop = "development-scientific-gate"
            holdout_counterfactuals_read = False
        else:
            holdout_cases = _build_cases(load_parent_inventory("holdout"))
            assign_envelopes(holdout_cases, envelopes)
            holdout_stage = evaluate_holdout_stage(
                development_cases,
                development_oracle,
                holdout_cases,
                envelopes,
                model_adequacy_tolerance=MODEL_ADEQUACY_TOLERANCE,
                minimum_improvement_fraction=MINIMUM_IMPROVEMENT,
                confidence_level=CONFIDENCE_LEVEL,
                maximum_single_scenario_ratio=MAXIMUM_SINGLE_SCENARIO_RATIO,
                startup_samples=UNRECOVERABLE_STARTUP_SAMPLES,
                maximum_iterations=MAXIMUM_ITERATIONS,
                function_tolerance=FUNCTION_TOLERANCE,
                feasibility_tolerance=FEASIBILITY_TOLERANCE,
            )
            model_adequacy = holdout_stage["model_adequacy"]
            holdout_oracle = holdout_stage["oracle"]
            holdout_local = holdout_stage["local"]
            final_decision = holdout_stage["decision"]
            if not model_adequacy["pass"]:
                stage_stop = "holdout-model-adequacy"
                holdout_counterfactuals_read = False
            elif final_decision["conclusion"] == "ANALYSIS-INVALID":
                stage_stop = "holdout-numerical-integrity"
                holdout_counterfactuals_read = bool(holdout_oracle)
            else:
                stage_stop = None
                holdout_counterfactuals_read = True

        analysis_path = out_dir / "analysis.json"
        analysis_digest = _write_new_json(
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
                "development_case_identity": _case_identity(development_cases),
                "development_envelopes": {
                    point: values.tolist() for point, values in envelopes.items()
                },
                "development_oracle": development_oracle,
                "development_neighbour_local": development_local,
                "development_decision": development_decision,
                "holdout_case_identity": _case_identity(holdout_cases),
                "holdout_model_adequacy": model_adequacy,
                "holdout_oracle": holdout_oracle,
                "holdout_neighbour_local": holdout_local,
                "holdout_counterfactuals_read": holdout_counterfactuals_read,
                "stage_stop": stage_stop,
                "classification": final_decision["conclusion"],
                "final_decision": final_decision,
                "residual_probe_eligible": final_decision["residual_probe_eligible"],
                "training_authorized": False,
                "andes_executed": False,
                "physical_trajectory_created": False,
                "distributed_runtime_executed": False,
                "eval_executed": False,
            },
        )
        manifest_digest = _write_new_json(
            out_dir / "manifest.json",
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
        print(f"classification={final_decision['conclusion']}", flush=True)
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
    """Return the three-command create-only R353 CLI."""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    rehearsal_parser = subparsers.add_parser("rehearsal")
    rehearsal_parser.add_argument("--record", type=Path, default=DEFAULT_REHEARSAL)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--expected-seal-sha256", required=True)
    analyse_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rehearsal":
        print(rehearsal(args.record), flush=True)
        return 0
    if args.command == "prepare":
        print(prepare(args.seal), flush=True)
        return 0
    if args.command == "analyse":
        analyse(args.expected_seal_sha256, out_dir=args.out)
        return 0
    raise AssertionError(f"unexpected command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
