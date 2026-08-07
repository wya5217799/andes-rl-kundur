"""Prepare and execute the create-only R363 common-channel headroom gate.

Usage::

    python scripts/run_r363_common_channel_qp.py rehearsal
    python scripts/run_r363_common_channel_qp.py prepare
    python scripts/run_r363_common_channel_qp.py analyse \\
        --expected-seal-sha256 <sha256>

The adapter reads the exact exposed R358 development bank, extends the action
basis with the frozen common residual-power channel, solves the same physical
joint-endpoint QP per case over the four-channel basis, and compares the
feasible count against the R358 10/16 baseline.  Any source drift, numerical
ambiguity, or persistent-output collision fails closed; retry, holdout access,
simulation, and training are unavailable.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cvxopt
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

from probes.r363_common_channel_qp import (  # noqa: E402
    DEVELOPMENT_CASE_COUNT,
    R358_BASELINE_FEASIBLE_COUNT,
    build_development_cases,
    classify_common_channel_gate,
    r358_status_partition,
    solve_common_channel_bank,
)
from scripts import run_r358_physical_joint_endpoint_qp as r358_parent  # noqa: E402

from andes_rl_kundur.control.common_channel_qp import (  # noqa: E402
    build_four_channel_control_response_map,
    solve_common_channel_joint_endpoint_qp,
)

ROUND_ID = "R363"
QUESTION_ID = "Q-0100"
MINIMUM_IMPROVEMENT = 0.02
EXPECTED_CVXOPT_VERSION = "1.3.3"
PLAN = ROOT / "memory/rounds/R363/plan.md"
QUESTION = ROOT / "memory/questions/Q-0100.md"
CAPACITY = ROOT / "memory/rounds/R363/capacity_evidence.json"
DEFAULT_REHEARSAL = ROOT / "memory/rounds/R363/rehearsal.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R363/analysis_seal.json"
DEFAULT_OUT = ROOT / "results/r363_common_channel_qp"

R358_PATHS = {
    "r358_plan": ROOT / "memory/rounds/R358/plan.md",
    "r358_rehearsal": ROOT / "memory/rounds/R358/rehearsal.json",
    "r358_seal": ROOT / "memory/rounds/R358/analysis_seal.json",
    "r358_attempt": ROOT / "results/r358_physical_joint_endpoint_qp/analysis_attempt.json",
    "r358_analysis": ROOT / "results/r358_physical_joint_endpoint_qp/analysis.json",
    "r358_manifest": ROOT / "results/r358_physical_joint_endpoint_qp/manifest.json",
    "r358_verdict": ROOT / "memory/rounds/R358/verdict.md",
    "r358_feed": ROOT / "paper/decoupling_marl_model_first/reports/R358.md",
    "r358_claim": ROOT / "memory/claims/CLM-0940.md",
}


def source_paths(*, include_rehearsal: bool) -> dict[str, Path]:
    """Return the complete R363 implementation closure."""

    paths = {
        "plan": PLAN,
        "question": QUESTION,
        "capacity": CAPACITY,
        "adapter": Path(__file__).resolve(),
        "probe": ROOT / "probes/r363_common_channel_qp.py",
        "probe_tests": ROOT / "tests/test_r363_common_channel_qp.py",
        "controller_src": ROOT / "src/andes_rl_kundur/control/common_channel_qp.py",
        "adapter_tests": ROOT / "tests/test_r363_common_channel_qp_analysis.py",
        "r358_adapter": Path(r358_parent.__file__).resolve(),
        "r358_probe": ROOT / "probes/physical_joint_endpoint_qp.py",
    }
    package_root = ROOT / "src/andes_rl_kundur"
    for path in sorted(package_root.rglob("*.py")):
        relative = path.relative_to(package_root).as_posix()
        paths[f"package_{relative}"] = path
    if include_rehearsal:
        paths["rehearsal"] = DEFAULT_REHEARSAL
    return paths


def parent_paths() -> dict[str, Path]:
    """Return exact R341/R352/R356/R357 trace parents plus R358 evidence."""

    paths = dict(r358_parent.source_paths(include_rehearsal=False))
    paths.update(R358_PATHS)
    return paths


def _record(path: Path) -> dict[str, str]:
    try:
        rendered = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        rendered = path.resolve().as_posix()
    return {"path": rendered, "sha256": r358_parent.predecessor.parent.sha256_file(path)}


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


def verify_r358_parent() -> dict[str, Any]:
    """Verify the exact R358 decision and every frozen evidence sidecar."""

    for name in ("r358_seal", "r358_attempt", "r358_analysis", "r358_manifest"):
        r358_parent.predecessor.parent.verify_sidecar(R358_PATHS[name])
    analysis = r358_parent.predecessor.read_json(R358_PATHS["r358_analysis"])
    if (
        analysis.get("round") != "R358"
        or analysis.get("question") != "Q-0095"
        or analysis.get("classification") != "PHYSICAL-HEADROOM-FOUND"
        or analysis.get("accepted_physical_feasible_candidate_count") != 10
        or analysis.get("inherited_relaxed_infeasible_count") != 6
        or analysis.get("holdout_cases_read") != 0
        or analysis.get("training_authorized") is not False
        or analysis.get("simulation_authorized") is not False
    ):
        raise RuntimeError("R358 parent decision drift")
    return analysis


def verify_entry_preconditions(out_dir: Path = DEFAULT_OUT) -> list[dict[str, Any]]:
    """Verify the active identity and every pre-attempt dependency."""

    if out_dir.exists():
        raise FileExistsError(f"R363 result root already exists: {out_dir}")
    plan_text = PLAN.read_text(encoding="utf-8")
    if "state: active" not in plan_text or ROUND_ID not in plan_text:
        raise RuntimeError("R363 active plan identity is missing")
    question_text = QUESTION.read_text(encoding="utf-8")
    if "status: in-flight" not in question_text or "R363:" not in question_text:
        raise RuntimeError("R363 in-flight question identity is missing")
    for path in source_paths(include_rehearsal=False).values():
        if not path.is_file():
            raise RuntimeError(f"R363 source is missing: {path}")
    if cvxopt.__version__ != EXPECTED_CVXOPT_VERSION:
        raise RuntimeError(f"R363 CVXOPT version drift: {cvxopt.__version__}")
    verify_r358_parent()
    cases = build_development_cases()
    if len(cases) != DEVELOPMENT_CASE_COUNT:
        raise RuntimeError("R363 requires exactly sixteen development cases")
    return cases


def synthetic_solver_smoke() -> dict[str, dict[str, Any]]:
    """Exercise verified feasible and target-infeasible four-channel decisions."""

    from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits

    limits = FeedbackLimits()
    feasible_response = np.zeros((4, 4))
    feasible_response[0, 0] = -1.0 / limits.node_ramp
    feasible_response[1, 0] = -1.0 / limits.node_ramp
    feasible_response[2, 0] = 1.0 / limits.node_ramp
    fixed_differential_response = np.zeros((4, 4))
    fixed_differential_response[0, 0] = -1.0 / limits.node_ramp
    common = {
        "base_outputs": np.asarray([[1.0, 1.0, 0.0, 0.0]]),
        "base_node_commands": np.zeros((1, 4)),
        "previous_node_command": np.zeros(4),
        "initial_soc": np.full(4, 0.5),
        "minimum_improvement_fraction": MINIMUM_IMPROVEMENT,
        "limits": limits,
    }
    return {
        "feasible": solve_common_channel_joint_endpoint_qp(
            **common,
            response_map=feasible_response,
        ),
        "target_infeasible": solve_common_channel_joint_endpoint_qp(
            **common,
            response_map=fixed_differential_response,
        ),
    }


def rehearsal(
    record_path: Path = DEFAULT_REHEARSAL,
    *,
    out_dir: Path = DEFAULT_OUT,
) -> str:
    """Exercise the formal pre-attempt path without solving the full bank."""

    if record_path.exists():
        raise FileExistsError(f"create-only output already exists: {record_path}")
    cases = verify_entry_preconditions(out_dir)
    smoke = synthetic_solver_smoke()
    if not (
        smoke["feasible"].get("status") == "optimal"
        and smoke["feasible"].get("accepted") is True
        and smoke["feasible"].get("target_feasible") is True
        and smoke["target_infeasible"].get("status") == "optimal"
        and smoke["target_infeasible"].get("accepted") is True
        and smoke["target_infeasible"].get("target_feasible") is False
    ):
        raise RuntimeError("R363 solver rehearsal checks failed")
    contract = build_contract()
    return r358_parent.predecessor.parent.write_new_json(
        record_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_payload_sha256": r358_parent.predecessor.parent.payload_sha256(contract),
            "development_case_identity": r358_parent.case_identity(cases),
            "development_case_count": len(cases),
            "r356_status_partition": r358_status_partition(),
            "synthetic_solver_smoke": smoke,
            "complete_bank_solved": False,
            "holdout_cases_read": 0,
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
    """Create the source-, parent-, identity-, and rehearsal-bound seal."""

    if seal_path.exists():
        raise FileExistsError(f"create-only output already exists: {seal_path}")
    cases = verify_entry_preconditions(out_dir)
    r358_parent.predecessor.parent.verify_sidecar(rehearsal_path)
    record = r358_parent.predecessor.read_json(rehearsal_path)
    contract = build_contract()
    sources = _source_snapshot(include_rehearsal=False)
    parents = _parent_snapshot()
    smoke = synthetic_solver_smoke()
    if (
        record.get("round") != ROUND_ID
        or record.get("question") != QUESTION_ID
        or record.get("contract_payload_sha256")
        != r358_parent.predecessor.parent.payload_sha256(contract)
        or record.get("development_case_identity") != r358_parent.case_identity(cases)
        or record.get("r356_status_partition") != r358_status_partition()
        or record.get("synthetic_solver_smoke") != smoke
        or record.get("complete_bank_solved") is not False
        or record.get("holdout_cases_read") != 0
        or record.get("source_snapshot") != sources
        or record.get("parent_snapshot") != parents
        or record.get("formal_output_absent") is not True
        or record.get("attempt_created") is not False
    ):
        raise RuntimeError("R363 rehearsal record drift")
    return r358_parent.predecessor.parent.write_new_json(
        seal_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract": contract,
            "contract_payload_sha256": r358_parent.predecessor.parent.payload_sha256(contract),
            "development_case_identity": r358_parent.case_identity(cases),
            "r356_status_partition": r358_status_partition(),
            "synthetic_solver_smoke": smoke,
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
    """Verify the exact R363 seal and complete immutable closure."""

    payload = r358_parent.predecessor.read_json(path)
    actual = r358_parent.predecessor.parent.sha256_file(path)
    if actual != expected_sha256:
        raise RuntimeError(f"R363 seal digest mismatch: {actual}")
    r358_parent.predecessor.parent.verify_sidecar(path)
    cases = verify_entry_preconditions(out_dir)
    contract = payload.get("contract")
    if (
        payload.get("round") != ROUND_ID
        or payload.get("question") != QUESTION_ID
        or contract != build_contract()
        or payload.get("contract_payload_sha256")
        != r358_parent.predecessor.parent.payload_sha256(contract)
        or payload.get("development_case_identity") != r358_parent.case_identity(cases)
        or payload.get("sources")
        != _source_snapshot(
            include_rehearsal=True,
            rehearsal_path=rehearsal_path,
        )
        or payload.get("parents") != _parent_snapshot()
        or payload.get("retry_authorized") is not False
    ):
        raise RuntimeError("R363 contract, source, or parent drift")
    return payload, actual


def analyse(expected_sha256: str) -> str:
    """Execute the single sealed serial four-channel feasibility analysis."""

    seal, seal_digest = load_seal(DEFAULT_SEAL, expected_sha256)
    DEFAULT_OUT.mkdir(parents=True, exist_ok=False)
    attempt_path = DEFAULT_OUT / "analysis_attempt.json"
    attempt_digest = r358_parent.predecessor.parent.write_new_json(
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
        },
    )
    started = time.perf_counter()
    try:
        cases = build_development_cases()
        if r358_parent.case_identity(cases) != seal["development_case_identity"]:
            raise RuntimeError("R363 formal case identity drift")
        rows = solve_common_channel_bank(cases)
        decision = classify_common_channel_gate(cases=cases, rows=rows)
        analysis_path = DEFAULT_OUT / "analysis.json"
        analysis_digest = r358_parent.predecessor.parent.write_new_json(
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
                "development_case_identity": r358_parent.case_identity(cases),
                "r356_status_partition": seal["r356_status_partition"],
                "r358_baseline_feasible_count": R358_BASELINE_FEASIBLE_COUNT,
                "common_channel_results": rows,
                **decision,
                "holdout_case_identity": [],
                "holdout_cases_read": 0,
                "minimum_improvement_fraction": MINIMUM_IMPROVEMENT,
                "physical_constraints_included": True,
                "information_constraints_included": False,
                "common_channel_included": True,
                "target_changed": False,
                "andes_executed": False,
                "physical_trajectory_created": False,
                "distributed_runtime_executed": False,
                "eval_executed": False,
            },
        )
        manifest_digest = r358_parent.predecessor.parent.write_new_json(
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
        print(f"feasible_count={decision['feasible_count']}", flush=True)
        print(f"analysis_sha256={analysis_digest}", flush=True)
        print(f"manifest_sha256={manifest_digest}", flush=True)
        return analysis_digest
    except Exception as error:
        failure_path = DEFAULT_OUT / "failure.json"
        if not failure_path.exists():
            r358_parent.predecessor.parent.write_new_json(
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


def build_contract() -> dict[str, Any]:
    """Return the prospectively frozen R363 execution contract."""

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "common-channel-physical-headroom-gate",
        "inventory": {
            "development_cases": 16,
            "samples_per_case": 25,
            "action_basis": "four-channel common-plus-three-edge",
            "r358_baseline_feasible_count": R358_BASELINE_FEASIBLE_COUNT,
            "holdout_cases_read": 0,
        },
        "target": {
            "minimum_improvement_fraction": MINIMUM_IMPROVEMENT,
            "common_coordinate_measure": "absolute-error-sum",
            "differential_coordinate_measure": "squared-error-sum",
        },
        "solver": {
            "name": "cvxopt-qp",
            "version": EXPECTED_CVXOPT_VERSION,
            "absolute_tolerance": 1.0e-10,
            "relative_tolerance": 1.0e-10,
            "feasibility_tolerance": 1.0e-10,
            "maximum_iterations": 200,
            "acceptance_tolerance": 1.0e-8,
        },
        "common_channel": {
            "node_action_basis": "[ones(4), active_power_incidence()]",
            "fleet_net_power_authority": True,
            "edge_channels_zero_sum": True,
            "physical_limits": "R358 exact node-power/ramp/SOC/energy/voltage-current",
            "tuning_executed": False,
        },
        "authorization": {
            "training": False,
            "simulation": False,
            "eval": False,
            "holdout_cases_read": 0,
        },
    }


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
