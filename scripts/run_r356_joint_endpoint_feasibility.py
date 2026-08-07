"""Rehearse, seal, and run the create-only R356 feasibility diagnosis.

Usage::

    python scripts/run_r356_joint_endpoint_feasibility.py rehearsal
    python scripts/run_r356_joint_endpoint_feasibility.py prepare
    python scripts/run_r356_joint_endpoint_feasibility.py analyse \
        --expected-seal-sha256 <sha256>

The adapter reads only the sixteen already exposed development cases.  It
does not read holdout data, lower the frozen target, run ANDES, train, or
simulate.  Parent/source drift, a case-identity mismatch, an unsupported
solver version, an unaccepted certificate, or an existing create-only output
stops execution and never authorizes a retry.
"""

from __future__ import annotations

import argparse
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

import cvxopt  # noqa: E402
import numpy as np  # noqa: E402
from probes.r356_joint_endpoint_feasibility import (  # noqa: E402
    ACCEPTANCE_TOLERANCE,
    SOLVER_ABSOLUTE_TOLERANCE,
    SOLVER_FEASIBILITY_TOLERANCE,
    SOLVER_MAXIMUM_ITERATIONS,
    SOLVER_RELATIVE_TOLERANCE,
    classify_joint_endpoint_feasibility,
    solve_joint_endpoint_feasibility,
)
from scripts import run_r353_matched_residual_headroom as case_parent  # noqa: E402

from andes_rl_kundur.control.model_first_offline_feedback import (  # noqa: E402
    FeedbackLimits,
)
from andes_rl_kundur.control.residual_headroom import (  # noqa: E402
    build_control_response_map,
)

ROUND_ID = "R356"
QUESTION_ID = "Q-0094"
MINIMUM_IMPROVEMENT = 0.02
EXPECTED_CVXOPT_VERSION = "1.3.3"
DEFAULT_REHEARSAL = ROOT / "memory/rounds/R356/rehearsal.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R356/analysis_seal.json"
DEFAULT_OUT = ROOT / "results/r356_joint_endpoint_feasibility"
PLAN = ROOT / "memory/rounds/R356/plan.md"
R355_ROOT = ROOT / "results/r355_rehearsal_binding_residual_headroom"
R355_PLAN = ROOT / "memory/rounds/R355/plan.md"
R355_REHEARSAL = ROOT / "memory/rounds/R355/rehearsal.json"
R355_SEAL = ROOT / "memory/rounds/R355/analysis_seal.json"
R355_ATTEMPT = R355_ROOT / "analysis_attempt.json"
R355_ANALYSIS = R355_ROOT / "analysis.json"
R355_MANIFEST = R355_ROOT / "manifest.json"
R355_ADAPTER = ROOT / "scripts/run_r355_rehearsal_binding_residual_headroom.py"
FROZEN_R355 = {
    R355_PLAN: "6c2e2980ca47f687e92750cce20cfbea693567b77afee279af5be434e5c362ae",
    R355_REHEARSAL: "6e9e2afefe3d779a9e1b4b5589cc9fb6c07f12e6c3473ea738a28e4661637f3c",
    R355_SEAL: "bc70a3287a2fa29657af0963a3be2f53733517581c89dd23d8ba3ec35a59d97d",
    R355_ATTEMPT: "049ffd31e24c30f31e20ab19271136bd966f630a42f0a45291af28101e737dcd",
    R355_ANALYSIS: "66f1d797fe0cdd40724afef396df35866ed4570019bf3860bd7ab9c87f5edc24",
    R355_MANIFEST: "7642965a16f9207aff274f0d7e2b5179618d4ff61dac2148aa4abfdd8b1d1647",
    R355_ADAPTER: "dd9fe7cf84f50d9258d275e9087692581c2a2cb0976e6c7b6773b0323fcb1e18",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def payload_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def write_new_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
    except FileExistsError:
        raise FileExistsError(f"create-only output already exists: {path}") from None
    digest = sha256_file(path)
    sidecar = Path(f"{path}.sha256")
    try:
        with sidecar.open("x", encoding="ascii", newline="\n") as handle:
            handle.write(f"{digest}  {path.name}\n")
    except FileExistsError:
        raise FileExistsError(f"create-only sidecar already exists: {sidecar}") from None
    return digest


def verify_sidecar(path: Path) -> None:
    sidecar = Path(f"{path}.sha256")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    if sha256_file(path) != expected:
        raise RuntimeError(f"sidecar digest mismatch: {path}")


def build_contract() -> dict[str, Any]:
    """Return the prospectively frozen R356 diagnosis contract."""

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "independent-relaxed-joint-endpoint-feasibility",
        "inventory": {
            "development_cases": 16,
            "holdout_cases_read": 0,
            "samples_per_case": 25,
        },
        "target": {
            "minimum_improvement_fraction": MINIMUM_IMPROVEMENT,
            "common_coordinate_measure": "absolute-error-sum",
            "differential_coordinate_measure": "squared-error-sum",
        },
        "relaxation": {
            "edge_coordinates": 3,
            "physical_constraints_included": False,
            "information_constraints_included": False,
            "logical_direction": "accepted-primal-infeasible-implies-original-infeasible",
            "optimal_does_not_establish_physical_feasibility": True,
        },
        "solver": {
            "name": "cvxopt-socp",
            "version": EXPECTED_CVXOPT_VERSION,
            "absolute_tolerance": SOLVER_ABSOLUTE_TOLERANCE,
            "relative_tolerance": SOLVER_RELATIVE_TOLERANCE,
            "feasibility_tolerance": SOLVER_FEASIBILITY_TOLERANCE,
            "maximum_iterations": SOLVER_MAXIMUM_ITERATIONS,
            "acceptance_tolerance": ACCEPTANCE_TOLERANCE,
        },
        "execution": {
            "worker_processes": 1,
            "native_threads_per_process": 1,
            "wsl_python_processes": 0,
            "serial": True,
            "create_only": True,
            "retry_authorized": False,
        },
        "decision": {
            "accepted_infeasible": "NO-TRAINING",
            "all_accepted_optimal": "CLASSIFIER-REPAIR-ELIGIBLE",
            "invalid": "ANALYSIS-INVALID",
        },
        "authorizations": {
            "holdout_authorized": False,
            "training_authorized": False,
            "simulation_authorized": False,
            "andes_authorized": False,
            "distributed_runtime_authorized": False,
            "eval_authorized": False,
        },
    }


def source_paths(*, include_rehearsal: bool) -> dict[str, Path]:
    """Return the complete R356 implementation and package closure."""

    paths = {
        "plan": PLAN,
        "adapter": Path(__file__).resolve(),
        "probe": ROOT / "probes/r356_joint_endpoint_feasibility.py",
        "probe_tests": ROOT / "tests/test_r356_joint_endpoint_feasibility.py",
        "adapter_tests": ROOT / "tests/test_r356_joint_endpoint_analysis.py",
        "case_builder_adapter": ROOT / "scripts/run_r353_matched_residual_headroom.py",
        "case_builder_probe": ROOT / "probes/r353_matched_residual_headroom.py",
    }
    package_root = ROOT / "src/andes_rl_kundur"
    for path in sorted(package_root.rglob("*.py")):
        relative = path.relative_to(package_root).as_posix()
        paths[f"package_{relative}"] = path
    if include_rehearsal:
        paths["rehearsal"] = DEFAULT_REHEARSAL
    return paths


def parent_paths() -> dict[str, Path]:
    """Return R355 plus only the R341/R352 development parents used here."""

    paths = {
        "r355_plan": R355_PLAN,
        "r355_rehearsal": R355_REHEARSAL,
        "r355_seal": R355_SEAL,
        "r355_attempt": R355_ATTEMPT,
        "r355_analysis": R355_ANALYSIS,
        "r355_manifest": R355_MANIFEST,
        "r355_adapter": R355_ADAPTER,
        "r352_development_execution": case_parent.R352_DEVELOPMENT_EXECUTION,
        "r352_development_analysis": case_parent.R352_DEVELOPMENT_ANALYSIS,
        "r352_development_manifest": case_parent.R352_DEVELOPMENT_MANIFEST,
        "r341_validation_seal": case_parent.R341_VALIDATION_SEAL,
        "r341_analysis": case_parent.R341_ANALYSIS,
        "r341_candidate_models": case_parent.R341_CANDIDATE_MODELS,
        "r341_validation_manifest": case_parent.R341_VALIDATION_MANIFEST,
    }
    for case in case_parent.load_parent_inventory("development"):
        for arm, payload in case["arms"].items():
            name = f"development_trace_{case['scenario_id']}_{arm}"
            paths[name] = ROOT / payload["record"]["trace"]["path"]
    return paths


def source_record(path: Path) -> dict[str, str]:
    try:
        rendered = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        rendered = path.resolve().as_posix()
    return {"path": rendered, "sha256": sha256_file(path)}


def source_snapshot(
    *, include_rehearsal: bool, rehearsal_path: Path = DEFAULT_REHEARSAL
) -> dict[str, dict[str, str]]:
    paths = source_paths(include_rehearsal=False)
    if include_rehearsal:
        paths["rehearsal"] = rehearsal_path
    return {name: source_record(path) for name, path in paths.items()}


def parent_snapshot() -> dict[str, dict[str, str]]:
    return {name: source_record(path) for name, path in parent_paths().items()}


def build_development_cases() -> list[dict[str, Any]]:
    """Build exactly the already exposed R355 development cases."""

    from probes.r353_matched_residual_headroom import (
        assign_envelopes,
        development_envelopes,
    )

    cases = case_parent._build_cases(case_parent.load_parent_inventory("development"))
    assign_envelopes(cases, development_envelopes(cases))
    return cases


def case_identity(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Render case identity in the exact frozen R355 schema."""

    return case_parent._case_identity(cases)


def synthetic_solver_smoke() -> dict[str, dict[str, Any]]:
    """Exercise accepted infeasible and optimal solver exits."""

    limits = FeedbackLimits()
    infeasible = solve_joint_endpoint_feasibility(
        base_outputs=np.asarray([[1.0, 1.0, 0.0, 0.0]]),
        response_map=np.zeros((4, 3)),
        minimum_improvement_fraction=MINIMUM_IMPROVEMENT,
    )
    response = np.zeros((4, 3))
    response[0, 0] = -1.0 / limits.node_ramp
    response[1, 0] = -1.0 / limits.node_ramp
    response[2, 0] = 1.0 / limits.node_ramp
    feasible = solve_joint_endpoint_feasibility(
        base_outputs=np.asarray([[1.0, 1.0, 0.0, 0.0]]),
        response_map=response,
        minimum_improvement_fraction=MINIMUM_IMPROVEMENT,
    )
    return {"infeasible": infeasible, "feasible": feasible}


def verify_frozen_inputs() -> list[dict[str, Any]]:
    """Verify the terminal R355 fact and the exact development identity."""

    for path, expected in FROZEN_R355.items():
        if not path.is_file() or sha256_file(path) != expected:
            raise RuntimeError(f"R356 frozen R355 input drift: {path}")
    for path in (R355_REHEARSAL, R355_SEAL, R355_ATTEMPT, R355_ANALYSIS, R355_MANIFEST):
        verify_sidecar(path)
    analysis = read_json(R355_ANALYSIS)
    if (
        analysis.get("round") != "R355"
        or analysis.get("question") != QUESTION_ID
        or analysis.get("classification") != "ANALYSIS-INVALID"
        or analysis.get("holdout_case_identity") != []
        or analysis.get("holdout_counterfactuals_read") is not False
        or analysis.get("training_authorized") is not False
        or analysis.get("andes_executed") is not False
        or len(analysis.get("development_case_identity", [])) != 16
    ):
        raise RuntimeError("R356 terminal R355 identity drift")
    cases = build_development_cases()
    if case_identity(cases) != analysis["development_case_identity"]:
        raise RuntimeError("R356 development case identity drift")
    return cases


def verify_entry_preconditions(out_dir: Path = DEFAULT_OUT) -> list[dict[str, Any]]:
    if out_dir.exists():
        raise FileExistsError(f"R356 result root already exists: {out_dir}")
    plan_text = PLAN.read_text(encoding="utf-8")
    if "state: active" not in plan_text or QUESTION_ID not in plan_text:
        raise RuntimeError("R356 active plan identity is missing")
    for path in source_paths(include_rehearsal=False).values():
        if not path.is_file():
            raise RuntimeError(f"R356 source is missing: {path}")
    if cvxopt.__version__ != EXPECTED_CVXOPT_VERSION:
        raise RuntimeError(
            f"R356 CVXOPT version drift: {cvxopt.__version__}"
        )
    cases = verify_frozen_inputs()
    if len(cases) != 16:
        raise RuntimeError("R356 requires exactly sixteen development cases")
    return cases


def rehearsal(record_path: Path = DEFAULT_REHEARSAL) -> str:
    """Exercise the formal pre-attempt path without creating an attempt."""

    if record_path.exists():
        raise FileExistsError(f"create-only output already exists: {record_path}")
    cases = verify_entry_preconditions()
    smoke = synthetic_solver_smoke()
    if not (
        smoke["infeasible"].get("status") == "primal infeasible"
        and smoke["infeasible"].get("accepted") is True
        and smoke["feasible"].get("status") == "optimal"
        and smoke["feasible"].get("accepted") is True
    ):
        raise RuntimeError("R356 synthetic solver smoke failed")
    contract = build_contract()
    return write_new_json(
        record_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_payload_sha256": payload_sha256(contract),
            "development_case_identity": case_identity(cases),
            "development_case_count": len(cases),
            "holdout_cases_read": 0,
            "synthetic_solver_smoke": smoke,
            "source_snapshot": source_snapshot(include_rehearsal=False),
            "parent_snapshot": parent_snapshot(),
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
) -> str:
    """Create the source-, parent-, identity-, and rehearsal-bound seal."""

    if seal_path.exists():
        raise FileExistsError(f"create-only output already exists: {seal_path}")
    cases = verify_entry_preconditions()
    verify_sidecar(rehearsal_path)
    record = read_json(rehearsal_path)
    contract = build_contract()
    sources = source_snapshot(include_rehearsal=False)
    parents = parent_snapshot()
    if (
        record.get("round") != ROUND_ID
        or record.get("question") != QUESTION_ID
        or record.get("contract_payload_sha256") != payload_sha256(contract)
        or record.get("development_case_identity") != case_identity(cases)
        or record.get("holdout_cases_read") != 0
        or record.get("synthetic_solver_smoke") != synthetic_solver_smoke()
        or record.get("source_snapshot") != sources
        or record.get("parent_snapshot") != parents
        or record.get("formal_output_absent") is not True
        or record.get("attempt_created") is not False
    ):
        raise RuntimeError("R356 rehearsal record drift")
    return write_new_json(
        seal_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract": contract,
            "contract_payload_sha256": payload_sha256(contract),
            "development_case_identity": case_identity(cases),
            "sources": source_snapshot(
                include_rehearsal=True,
                rehearsal_path=rehearsal_path,
            ),
            "parents": parents,
            "result_root_absent_at_freeze": True,
            "retry_authorized": False,
        },
    )


def load_seal(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    """Verify the exact R356 seal and complete closure."""

    payload = read_json(path)
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise RuntimeError(f"R356 seal digest mismatch: {actual}")
    verify_sidecar(path)
    cases = verify_entry_preconditions()
    contract = payload.get("contract")
    if (
        payload.get("round") != ROUND_ID
        or payload.get("question") != QUESTION_ID
        or contract != build_contract()
        or payload.get("contract_payload_sha256") != payload_sha256(contract)
        or payload.get("development_case_identity") != case_identity(cases)
        or payload.get("sources") != source_snapshot(include_rehearsal=True)
        or payload.get("parents") != parent_snapshot()
        or payload.get("retry_authorized") is not False
    ):
        raise RuntimeError("R356 contract, identity, source, or parent drift")
    return payload, actual


def analyse(expected_sha256: str) -> str:
    """Execute the single sealed serial feasibility diagnosis."""

    seal, seal_digest = load_seal(DEFAULT_SEAL, expected_sha256)
    DEFAULT_OUT.mkdir(parents=True, exist_ok=False)
    attempt_path = DEFAULT_OUT / "analysis_attempt.json"
    attempt_digest = write_new_json(
        attempt_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "worker_processes": 1,
            "native_threads_per_process": 1,
            "wsl_python_processes": 0,
            "retry_authorized": False,
            "holdout_cases_read": 0,
            "andes_executed": False,
            "training_executed": False,
        },
    )
    started = time.perf_counter()
    try:
        cases = build_development_cases()
        if case_identity(cases) != seal["development_case_identity"]:
            raise RuntimeError("R356 formal case identity drift")
        rows: list[dict[str, Any]] = []
        for case in cases:
            outputs = np.asarray(case["base_outputs"], dtype=float)
            response = build_control_response_map(
                case["model"], horizon=int(outputs.shape[0])
            )
            result = solve_joint_endpoint_feasibility(
                base_outputs=outputs,
                response_map=response,
                minimum_improvement_fraction=MINIMUM_IMPROVEMENT,
            )
            rows.append(
                {
                    "scenario_id": case["scenario_id"],
                    "point": case["point"],
                    "channel": case["channel"],
                    "sign": case["sign"],
                    **result,
                }
            )
        decision = classify_joint_endpoint_feasibility(rows)
        analysis_path = DEFAULT_OUT / "analysis.json"
        analysis_digest = write_new_json(
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
                "development_case_identity": case_identity(cases),
                "development_results": rows,
                **decision,
                "holdout_case_identity": [],
                "holdout_cases_read": 0,
                "minimum_improvement_fraction": MINIMUM_IMPROVEMENT,
                "physical_constraints_included": False,
                "information_constraints_included": False,
                "one_percent_sensitivity_used": False,
                "andes_executed": False,
                "physical_trajectory_created": False,
                "distributed_runtime_executed": False,
                "eval_executed": False,
            },
        )
        manifest_digest = write_new_json(
            DEFAULT_OUT / "manifest.json",
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
        failure_path = DEFAULT_OUT / "failure.json"
        if not failure_path.exists():
            write_new_json(
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
    """Return the three create-only R356 commands."""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    rehearsal_parser = subparsers.add_parser("rehearsal")
    rehearsal_parser.add_argument("--record", type=Path, default=DEFAULT_REHEARSAL)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--expected-seal-sha256", required=True)
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
        analyse(args.expected_seal_sha256)
        return 0
    raise RuntimeError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
