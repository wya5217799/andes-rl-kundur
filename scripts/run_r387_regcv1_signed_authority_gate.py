"""Run the sealed R387 signed per-device REGCV1 authority bank.

Motivation:
    R386 proves clean initialization and a short zero-input trajectory, but it
    does not prove that each REGCV1 Pref/Qref input has signed, target-attributed
    achieved P/Q authority. R387 executes the prospectively frozen 17-arm bank.

Usage:
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r387_regcv1_signed_authority_gate.py rehearse
    /home/wya/andes_venv/bin/python \
        scripts/run_r387_regcv1_signed_authority_gate.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r387_regcv1_signed_authority_gate.py execute \
        --expected-seal-sha256 <sha256>

Failure modes:
    Provenance, schema, source, diagnostics, capture, runtime, incomplete-bank,
    or create-only failures are ANALYSIS-INVALID. A complete bank that fails a
    native solver, electrical, identity, sign, attribution, or separation guard
    is STOP-REGCV1-SIGNED-AUTHORITY. There is no retry, tuning, controller,
    training, overwrite, topology-change, or model-substitution command.
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

from andes_rl_kundur.evaluation.regcv1_signed_authority_gate import (  # noqa: E402
    apply_regcv1_setpoint_step,
    build_signed_authority_contract,
    classify_regcv1_signed_authority_record,
    payload_sha256,
)

BASE_RUNNER = ROOT / "scripts/run_r385_regcv1_clean_init_gate.py"
REFERENCE_RUNNER = ROOT / "scripts/run_r386_regcv1_reference_capture_gate.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load lifecycle dependency: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lifecycle = _load_module("r387_r385_lifecycle", BASE_RUNNER)
reference = _load_module("r387_r386_reference", REFERENCE_RUNNER)

ROUND_ID = "R387"
QUESTION_ID = "Q-0106"
LINE_ID = "converter-vsg-pq-decoupling"
PLAN = ROOT / "memory/rounds/R387/plan.md"
QUESTION = ROOT / "memory/questions/Q-0106.md"
REHEARSAL = ROOT / "memory/rounds/R387/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R387/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R387/formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r387_regcv1_signed_authority_gate"


def source_manifest() -> dict[str, dict[str, str]]:
    """Return the exact R387 implementation/governance source manifest."""

    sources = {
        "runner": Path(__file__).resolve(),
        "lifecycle_base": BASE_RUNNER,
        "reference_base": REFERENCE_RUNNER,
        "builder": ROOT / "src/andes_rl_kundur/env/andes/regcv1_static_kundur.py",
        "classifier": ROOT / "src/andes_rl_kundur/evaluation/regcv1_signed_authority_gate.py",
        "base_classifier": ROOT / "src/andes_rl_kundur/evaluation/regcv1_clean_init_gate.py",
        "reference_classifier": ROOT / "src/andes_rl_kundur/evaluation/regcv1_reference_gate.py",
        "classifier_tests": ROOT / "tests/test_regcv1_signed_authority_gate.py",
        "runner_tests": ROOT / "tests/test_r387_regcv1_signed_authority_gate.py",
        "builder_tests": ROOT / "tests/test_regcv1_static_kundur.py",
        "plan": PLAN,
        "question": QUESTION,
        "programme": ROOT / "memory/RESEARCH_PROGRAM.md",
        "line": ROOT / "paper/converter_vsg_pq_decoupling/LINE.md",
        "artifact_manifest": ROOT / "paper/converter_vsg_pq_decoupling/ARTIFACTS.json",
        "route_contract": ROOT / "paper/converter_vsg_pq_decoupling/working/route_contract.md",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": lifecycle.relative(path), "sha256": lifecycle.sha256_file(path)}
        for name, path in sources.items()
    }


def parent_manifest() -> dict[str, dict[str, str]]:
    """Bind the exact R386 authority and its provenance artifacts."""

    parents = {
        "r386_claim": ROOT / "memory/claims/CLM-1075.md",
        "r386_feed": ROOT / "paper/converter_vsg_pq_decoupling/reports/R386.md",
        "r386_verdict": ROOT / "memory/rounds/R386/verdict.md",
        "r386_analysis": ROOT
        / "results/research_loop/r386_regcv1_reference_capture_gate/formal_analysis.json",
        "r386_manifest": ROOT
        / "results/research_loop/r386_regcv1_reference_capture_gate/formal_manifest.json",
        "successor_adr": ROOT / "docs/adr/0017-structural-absence-regcv1-successor.md",
        "line_adr": ROOT / "docs/adr/0016-separate-converter-vsg-pq-decoupling-line.md",
    }
    return {
        name: {"path": lifecycle.relative(path), "sha256": lifecycle.sha256_file(path)}
        for name, path in parents.items()
    }


def _inventory(system: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "network": {
            "bus_count": int(system.Bus.n),
            "bus_indices": [int(value) for value in system.Bus.idx.v],
            "line_count": int(system.Line.n),
            "pq_count": int(system.PQ.n),
            "static_gen_count": int(system.StaticGen.n),
            "static_generator_buses": [
                int(value) for value in system.StaticGen.get(src="bus", idx=[1, 2, 3, 4], attr="v")
            ],
        },
        "forbidden_model_counts": lifecycle.forbidden_model_counts(
            system, contract["forbidden_models"]
        ),
        "forbidden_dae_names": lifecycle.forbidden_dae_names(system, contract["forbidden_models"]),
        "regcv1": lifecycle.regcv1_inventory(system),
    }


def _empty_arm(arm: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **dict(arm),
        "scientific_error": None,
        "inventory": {},
        "reference_source": {
            "captured": False,
            "phase": None,
            "pflow_converged_at_capture": False,
            "tds_initialized_at_capture": False,
            "rows": [],
        },
        "references": {"checked": False, "absolute_tolerance": None, "rows": []},
        "initialization_diagnostics": {
            "captured": False,
            "equation_count": 0,
            "residual_count": 0,
            "bad_combined_indices": [],
            "residuals": [],
            "clamped_limits": [],
        },
        "solver": {
            "setup_completed": False,
            "pflow_converged": False,
            "tds_initialized": False,
            "tds_test_ok": False,
            "tds_converged": False,
            "tds_tolerance": None,
            "terminal_time_seconds": None,
        },
        "action": {
            "applied": False,
            "pre_setpoints": [],
            "post_setpoints": [],
            "requested_absolute": None,
            "applied_readback": None,
        },
        "trajectory": {
            "captured": False,
            "time": [],
            "dae_finite": False,
            "regcv1_finite": False,
            "bus_v": {},
            "regcv1": {},
        },
    }


def _matrix_rows(
    matrix: np.ndarray, addresses: list[int], labels: list[str]
) -> dict[str, list[float]]:
    if matrix.ndim != 2 or matrix.shape[0] < 2:
        raise RuntimeError("R387 stored trajectory matrix is incomplete")
    if len(addresses) != len(labels):
        raise RuntimeError("R387 trajectory address/label mismatch")
    return {
        label: [float(value) for value in matrix[:, address]]
        for label, address in zip(labels, addresses, strict=True)
    }


def capture_trajectory(system: Any) -> dict[str, Any]:
    """Serialize the complete R387 signal traces from the native DAE store."""

    system.dae.ts.unpack(attr="t", warn_empty=False)
    system.dae.ts.unpack(attr="x", warn_empty=False)
    system.dae.ts.unpack(attr="y", warn_empty=False)
    time_values = np.asarray(system.dae.ts.t, dtype=float)
    x_values = np.asarray(system.dae.ts.x, dtype=float)
    y_values = np.asarray(system.dae.ts.y, dtype=float)
    if time_values.ndim != 1 or len(time_values) < 2:
        raise RuntimeError("R387 stored time grid is incomplete")
    if not np.all(np.diff(time_values) > 0):
        raise RuntimeError("R387 stored time grid is not strictly increasing")

    idxes = [str(value) for value in system.REGCV1.idx.v]
    buses = [str(value) for value in system.Bus.idx.v]
    traces: dict[str, dict[str, list[float]]] = {}
    for signal in ("Pe", "Qe", "Id", "Iq", "omega"):
        variable = getattr(system.REGCV1, signal)
        matrix = x_values if variable.v_code == "x" else y_values
        traces[signal] = _matrix_rows(
            matrix,
            [int(value) for value in variable.a],
            idxes,
        )
    bus_v = _matrix_rows(
        y_values,
        [int(value) for value in system.Bus.v.a],
        buses,
    )
    dae_finite, model_finite = lifecycle.finite_guards(system)
    return {
        "captured": True,
        "time": [float(value) for value in time_values],
        "dae_finite": dae_finite
        and bool(np.isfinite(x_values).all())
        and bool(np.isfinite(y_values).all()),
        "regcv1_finite": model_finite,
        "bus_v": bus_v,
        "regcv1": traces,
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
    row["inventory"] = _inventory(system, contract)

    pflow_return = system.PFlow.run()
    row["solver"]["pflow_converged"] = bool(pflow_return)
    if not pflow_return:
        diagnostics = lifecycle.capture_initialization_diagnostics(system)
        if diagnostics["captured"] is not True:
            raise RuntimeError(
                "R387 initialization diagnostic capture failed after PFlow failure: "
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
    row["inventory"] = _inventory(system, contract)
    diagnostics = lifecycle.capture_initialization_diagnostics(system)
    row["initialization_diagnostics"] = diagnostics
    if diagnostics["captured"] is not True:
        raise RuntimeError(
            "R387 initialization diagnostic capture failed: "
            f"{diagnostics.get('capture_error', 'unknown error')}"
        )
    row["references"] = reference.post_init_references(system, source, contract)
    if not (row["solver"]["tds_initialized"] and row["solver"]["tds_test_ok"]):
        row["scientific_error"] = "native TDS initialization guard failed"
        return row, built.derived_case_sha256

    row["action"] = apply_regcv1_setpoint_step(system, arm)
    trajectory_start = float(system.dae.t)
    system.TDS.run()
    terminal_time = float(system.dae.t)
    row["solver"]["terminal_time_seconds"] = terminal_time
    row["solver"]["tds_converged"] = bool(system.TDS.converged)
    if terminal_time <= trajectory_start:
        row["scientific_error"] = "TDS did not advance"
        return row, built.derived_case_sha256
    row["trajectory"] = capture_trajectory(system)
    return row, built.derived_case_sha256


def run_formal_record(contract: Mapping[str, Any], runtime: Mapping[str, Any]) -> dict[str, Any]:
    """Execute the exact serial 17-arm bank and return one immutable record."""

    record: dict[str, Any] = {
        "schema_version": 1,
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
                raise RuntimeError("R387 derived static-case digest drift")
            record["arms"].append(row)
            record["trajectory_executed_count"] += int(row["trajectory"]["captured"] is True)
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
    lifecycle.build_clean_contract = build_signed_authority_contract
    lifecycle.classify_regcv1_clean_init_record = classify_regcv1_signed_authority_record
    lifecycle.source_manifest = source_manifest
    lifecycle.parent_manifest = parent_manifest
    lifecycle.run_formal_record = run_formal_record


_configure_lifecycle()


def execute(*, expected_sha256: str) -> str:
    """Execute through the reviewed lifecycle with the R387 root explicit."""

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
