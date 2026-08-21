"""Run the sealed R388 integrity-corrected REGCV1 authority bank.

Motivation:
    R387's sole attempt is analysis-invalid because its evidence schema treated
    JSON mapping order as bus identity, omitted an explicit initial snapshot,
    and could not type an advanced partial native trajectory. R388 corrects
    only those three defects while preserving the exact scientific bank.

Usage:
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r388_regcv1_signed_authority_correction_gate.py rehearse
    /home/wya/andes_venv/bin/python \
        scripts/run_r388_regcv1_signed_authority_correction_gate.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r388_regcv1_signed_authority_correction_gate.py execute \
        --expected-seal-sha256 <sha256>

Failure modes:
    Source, contract, schema, capture, exception, bank, or create-only defects
    are ANALYSIS-INVALID. A valid complete or typed advanced-partial bank that
    fails any frozen scientific guard is STOP-REGCV1-SIGNED-AUTHORITY. There is
    no retry, tuning, controller, training, topology change, or substitution.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.evaluation.regcv1_signed_authority_correction_gate import (  # noqa: E402
    PARTIAL_ERROR,
    build_signed_authority_correction_contract,
    classify_regcv1_signed_authority_correction_record,
)
from andes_rl_kundur.evaluation.regcv1_signed_authority_gate import (  # noqa: E402
    apply_regcv1_setpoint_step,
    payload_sha256,
)

PARENT_RUNNER = ROOT / "scripts/run_r387_regcv1_signed_authority_gate.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load lifecycle dependency: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


parent_runner = _load_module("r388_r387_parent", PARENT_RUNNER)
lifecycle = parent_runner.lifecycle
reference = parent_runner.reference

ROUND_ID = "R388"
QUESTION_ID = "Q-0106"
LINE_ID = "converter-vsg-pq-decoupling"
PLAN = ROOT / "memory/rounds/R388/plan.md"
QUESTION = ROOT / "memory/questions/Q-0106.md"
REHEARSAL = ROOT / "memory/rounds/R388/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R388/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R388/formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r388_regcv1_signed_authority_correction_gate"


def source_manifest() -> dict[str, dict[str, str]]:
    """Return the exact R388 implementation and governance source manifest."""

    sources = {
        "runner": Path(__file__).resolve(),
        "parent_runner": PARENT_RUNNER,
        "lifecycle_base": parent_runner.BASE_RUNNER,
        "reference_base": parent_runner.REFERENCE_RUNNER,
        "builder": ROOT / "src/andes_rl_kundur/env/andes/regcv1_static_kundur.py",
        "classifier": ROOT
        / "src/andes_rl_kundur/evaluation/regcv1_signed_authority_correction_gate.py",
        "parent_classifier": ROOT
        / "src/andes_rl_kundur/evaluation/regcv1_signed_authority_gate.py",
        "base_classifier": ROOT
        / "src/andes_rl_kundur/evaluation/regcv1_clean_init_gate.py",
        "reference_classifier": ROOT
        / "src/andes_rl_kundur/evaluation/regcv1_reference_gate.py",
        "classifier_tests": ROOT
        / "tests/test_regcv1_signed_authority_correction_gate.py",
        "runner_tests": ROOT
        / "tests/test_r388_regcv1_signed_authority_correction_gate.py",
        "parent_classifier_tests": ROOT / "tests/test_regcv1_signed_authority_gate.py",
        "parent_runner_tests": ROOT / "tests/test_r387_regcv1_signed_authority_gate.py",
        "builder_tests": ROOT / "tests/test_regcv1_static_kundur.py",
        "plan": PLAN,
        "question": QUESTION,
        "programme": ROOT / "memory/RESEARCH_PROGRAM.md",
        "line": ROOT / "paper/converter_vsg_pq_decoupling/LINE.md",
        "artifact_manifest": ROOT / "paper/converter_vsg_pq_decoupling/ARTIFACTS.json",
        "route_contract": ROOT
        / "paper/converter_vsg_pq_decoupling/working/route_contract.md",
        "r387_diagnosis": ROOT
        / "paper/converter_vsg_pq_decoupling/working/R387_diagnosis.md",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": lifecycle.relative(path), "sha256": lifecycle.sha256_file(path)}
        for name, path in sources.items()
    }


def parent_manifest() -> dict[str, dict[str, str]]:
    """Bind R387's immutable invalidity diagnosis and R386 clean parent."""

    parents = {
        "r387_claim": ROOT / "memory/claims/CLM-1080.md",
        "r387_feed": ROOT / "paper/converter_vsg_pq_decoupling/reports/R387.md",
        "r387_verdict": ROOT / "memory/rounds/R387/verdict.md",
        "r387_seal": ROOT / "memory/rounds/R387/formal_seal.json",
        "r387_analysis": ROOT
        / "results/research_loop/r387_regcv1_signed_authority_gate/formal_analysis.json",
        "r387_manifest": ROOT
        / "results/research_loop/r387_regcv1_signed_authority_gate/formal_manifest.json",
        "r387_diagnosis": ROOT
        / "paper/converter_vsg_pq_decoupling/working/R387_diagnosis.md",
        "r386_claim": ROOT / "memory/claims/CLM-1075.md",
        "r386_verdict": ROOT / "memory/rounds/R386/verdict.md",
        "successor_adr": ROOT / "docs/adr/0017-structural-absence-regcv1-successor.md",
        "line_adr": ROOT / "docs/adr/0016-separate-converter-vsg-pq-decoupling-line.md",
    }
    return {
        name: {"path": lifecycle.relative(path), "sha256": lifecycle.sha256_file(path)}
        for name, path in parents.items()
    }


def _empty_initial() -> dict[str, Any]:
    return {
        "captured": False,
        "time_seconds": None,
        "dae_finite": False,
        "regcv1_finite": False,
        "bus_v": {},
        "regcv1": {},
    }


def _empty_arm(arm: Mapping[str, Any]) -> dict[str, Any]:
    row = parent_runner._empty_arm(arm)
    row["trajectory"] = {
        "captured": False,
        "start_time_seconds": None,
        "initial": _empty_initial(),
        "time": [],
        "dae_finite": False,
        "regcv1_finite": False,
        "bus_v": {},
        "regcv1": {},
    }
    return row


def capture_initial_snapshot(system: Any) -> dict[str, Any]:
    """Capture all registered signals at the explicit pre-run initial time."""

    idxes = [str(value) for value in system.REGCV1.idx.v]
    buses = [str(value) for value in system.Bus.idx.v]
    bus_values = [float(value) for value in np.asarray(system.Bus.v.v, dtype=float)]
    traces: dict[str, dict[str, float]] = {}
    for signal in ("Pe", "Qe", "Id", "Iq", "omega"):
        values = [
            float(value)
            for value in np.asarray(getattr(system.REGCV1, signal).v, dtype=float)
        ]
        if len(values) != len(idxes):
            raise RuntimeError(f"R388 initial {signal} identity/value mismatch")
        traces[signal] = dict(zip(idxes, values, strict=True))
    if len(bus_values) != len(buses):
        raise RuntimeError("R388 initial bus-voltage identity/value mismatch")
    dae_finite, model_finite = lifecycle.finite_guards(system)
    return {
        "captured": True,
        "time_seconds": float(system.dae.t),
        "dae_finite": dae_finite,
        "regcv1_finite": model_finite,
        "bus_v": dict(zip(buses, bus_values, strict=True)),
        "regcv1": traces,
    }


def capture_trajectory(
    system: Any,
    *,
    start_time_seconds: float,
    initial: Mapping[str, Any],
) -> dict[str, Any]:
    """Capture native post-start samples plus the separately sealed initial row."""

    trajectory = parent_runner.capture_trajectory(system)
    return {
        "captured": True,
        "start_time_seconds": start_time_seconds,
        "initial": dict(initial),
        "time": trajectory["time"],
        "dae_finite": trajectory["dae_finite"],
        "regcv1_finite": trajectory["regcv1_finite"],
        "bus_v": trajectory["bus_v"],
        "regcv1": trajectory["regcv1"],
    }


def _run_arm(
    arm: Mapping[str, Any],
    contract: Mapping[str, Any],
    runtime: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    row = _empty_arm(arm)
    audit = lifecycle.load_verified_static_case(
        xlsx_path=runtime["xlsx_case_path"],
        json_path=runtime["json_case_path"],
    )
    built = lifecycle.build_regcv1_static_kundur_object(
        full_case=audit.full_case,
        work_dir=Path.cwd(),
    )
    system = built.system
    row["solver"]["tds_tolerance"] = float(system.TDS.config.tol)
    system.setup()
    row["solver"]["setup_completed"] = bool(system.is_setup)
    row["inventory"] = parent_runner._inventory(system, contract)

    pflow_return = system.PFlow.run()
    row["solver"]["pflow_converged"] = bool(pflow_return)
    if not pflow_return:
        diagnostics = lifecycle.capture_initialization_diagnostics(system)
        if diagnostics["captured"] is not True:
            raise RuntimeError(
                "R388 initialization diagnostic capture failed after PFlow failure: "
                f"{diagnostics.get('capture_error', 'unknown error')}"
            )
        row["initialization_diagnostics"] = diagnostics
        row["scientific_error"] = "PFlow.run returned a non-success value"
        return row, built.derived_case_sha256

    source = reference.capture_reference_source(system, contract)
    row["reference_source"] = source
    system.TDS.config.tf = float(contract["tds_tf_seconds"])
    init_return = system.TDS.init()
    row["solver"]["tds_initialized"] = init_return is not False
    row["solver"]["tds_test_ok"] = system.TDS.test_ok is True
    row["inventory"] = parent_runner._inventory(system, contract)
    diagnostics = lifecycle.capture_initialization_diagnostics(system)
    row["initialization_diagnostics"] = diagnostics
    if diagnostics["captured"] is not True:
        raise RuntimeError(
            "R388 initialization diagnostic capture failed: "
            f"{diagnostics.get('capture_error', 'unknown error')}"
        )
    row["references"] = reference.post_init_references(system, source, contract)
    if not (row["solver"]["tds_initialized"] and row["solver"]["tds_test_ok"]):
        row["scientific_error"] = "native TDS initialization guard failed"
        return row, built.derived_case_sha256

    trajectory_start = float(system.dae.t)
    initial = capture_initial_snapshot(system)
    row["trajectory"]["start_time_seconds"] = trajectory_start
    row["trajectory"]["initial"] = initial
    row["action"] = apply_regcv1_setpoint_step(system, arm)
    system.TDS.run()
    terminal_time = float(system.dae.t)
    row["solver"]["terminal_time_seconds"] = terminal_time
    row["solver"]["tds_converged"] = bool(system.TDS.converged)
    if terminal_time <= trajectory_start:
        row["scientific_error"] = "TDS did not advance"
        return row, built.derived_case_sha256
    row["trajectory"] = capture_trajectory(
        system,
        start_time_seconds=trajectory_start,
        initial=initial,
    )
    tolerance = float(contract["tds_tolerance"])
    horizon = float(contract["tds_tf_seconds"])
    if terminal_time < horizon - tolerance:
        if row["solver"]["tds_converged"] is True:
            raise RuntimeError("R388 converged trajectory terminated before the horizon")
        row["scientific_error"] = PARTIAL_ERROR
    return row, built.derived_case_sha256


def run_formal_record(contract: Mapping[str, Any], runtime: Mapping[str, Any]) -> dict[str, Any]:
    """Execute the exact serial R388 bank and return one immutable record."""

    record: dict[str, Any] = {
        "schema_version": 2,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "contract_sha256": payload_sha256(contract),
        "formal_input_complete": True,
        "execution_error": None,
        "training_executed": False,
        "trajectory_attempted_count": 0,
        "trajectory_executed_count": 0,
        "source": {
            "andes_version": runtime["andes_version"],
            "xlsx_json_static_equal": runtime["xlsx_json_static_equal"],
            "derived_case_deterministic": True,
            "xlsx_case_sha256": runtime["xlsx_case_sha256"],
            "json_case_sha256": runtime["json_case_sha256"],
            "derived_case_sha256": runtime["derived_case_sha256"],
            "regcv1_source_sha256": runtime["regcv1_model_sha256"],
        },
        "arms": [],
    }
    try:
        for arm in contract["arm_order"]:
            record["trajectory_attempted_count"] += 1
            row, derived_digest = _run_arm(arm, contract, runtime)
            if derived_digest != runtime["derived_case_sha256"]:
                raise RuntimeError("R388 derived static-case digest drift")
            record["arms"].append(row)
            record["trajectory_executed_count"] += int(
                row["trajectory"]["captured"] is True
            )
    except Exception as exc:
        record["execution_error"] = f"{type(exc).__name__}: {exc}"
    return record


def _configure_lifecycle() -> None:
    lifecycle.ROUND_ID = ROUND_ID
    lifecycle.QUESTION_ID = QUESTION_ID
    lifecycle.LINE_ID = LINE_ID
    lifecycle.PLAN = PLAN
    lifecycle.QUESTION = QUESTION
    lifecycle.REHEARSAL = REHEARSAL
    lifecycle.CAPACITY = CAPACITY
    lifecycle.SEAL = SEAL
    lifecycle.DEFAULT_OUT = DEFAULT_OUT
    lifecycle.build_clean_contract = build_signed_authority_correction_contract
    lifecycle.classify_regcv1_clean_init_record = (
        classify_regcv1_signed_authority_correction_record
    )
    lifecycle.source_manifest = source_manifest
    lifecycle.parent_manifest = parent_manifest
    lifecycle.run_formal_record = run_formal_record


_configure_lifecycle()


def execute(*, expected_sha256: str) -> str:
    """Execute through the reviewed lifecycle with the R388 root explicit."""

    return lifecycle.execute(expected_sha256=expected_sha256, out_dir=DEFAULT_OUT)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("rehearse")
    commands.add_parser("prepare")
    formal = commands.add_parser("execute")
    formal.add_argument("--expected-seal-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rehearse":
        print(f"rehearsal_sha256={lifecycle.rehearse()}")
    elif args.command == "prepare":
        print(f"seal_sha256={lifecycle.prepare()}")
    elif args.command == "execute":
        print(f"analysis_sha256={execute(expected_sha256=args.expected_seal_sha256)}")
    else:  # pragma: no cover
        raise RuntimeError(f"unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
