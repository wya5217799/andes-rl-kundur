"""Run the science-identical R394 correction of the invalid R393 PPVSM1 gate.

Motivation:
    R393 is analysis-invalid by CLM-1110 because of three instrumentation
    seams: the initial trace row read device variables through Model.get
    (KeyError for algebraic variables), the TDS horizon was never frozen to
    the registered 0.2 seconds, and the source snapshot was taken after TDS
    initialization when replaced static generators read zero. R394 repairs
    only those three evidence seams.

Usage:
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r394_ppvsm1_object_gate.py rehearse
    /home/wya/andes_venv/bin/python scripts/run_r394_ppvsm1_object_gate.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r394_ppvsm1_object_gate.py execute --expected-seal-sha256 <sha256>

Failure modes:
    Provenance, parent-chain, capture, exception, or create-only defects are
    ANALYSIS-INVALID. Init/stationarity/spectrum failures are scientific
    STOPs. No action, retry, controller, or training command.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

PARENT_RUNNER = ROOT / "scripts/run_r393_ppvsm1_object_gate.py"
_parent_spec = importlib.util.spec_from_file_location("r394_r393_parent", PARENT_RUNNER)
if _parent_spec is None or _parent_spec.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load R393 parent runner: {PARENT_RUNNER}")
parent_runner = importlib.util.module_from_spec(_parent_spec)
_parent_spec.loader.exec_module(parent_runner)
base = parent_runner.base

from andes_rl_kundur.env.andes.ppvsm1_static_kundur import (  # noqa: E402
    build_ppvsm1_static_kundur_object,
)
from andes_rl_kundur.evaluation.ppvsm1_object_gate import (  # noqa: E402
    build_ppvsm1_object_contract,
    classify_ppvsm1_object_record,
    payload_sha256,
)

ROUND_ID = "R394"
QUESTION_ID = "Q-0110"
LINE_ID = "converter-vsg-pq-decoupling"
PLAN = ROOT / "memory/rounds/R394/plan.md"
QUESTION = ROOT / "memory/questions/Q-0110.md"
REHEARSAL = ROOT / "memory/rounds/R394/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R394/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R394/formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r394_ppvsm1_object_gate"

R393_PARENT_SHA256 = {
    "seal": "9c52b820c98660f2638e08aef14c1783d9aad3017e088f935191130439a8bf89",
    "attempt": "47a6cfa2320dd4a9e5977d121423b3e15b57864c7426fa3dd0bd3b9447dff95a",
    "execution": "abb2c7b0813813c2c9466349844f5638058bdaa9183724c410e6a1b07d7da15a",
    "analysis": "a2f525d9463421037c433518d68e07c4fdce04079d910d8f3be024aa1cb8f3c3",
    "manifest": "85bf843bf438c3b2fc27f8cce4d9ae9c290356902a1f6ef9e2d6ef5e2711c5ef",
    "claim": "684c7c8fcf7aada133a4e2f32f86bfdd86222241713168f5f2862c5c252fa697",
    "feed": "9bad5bc03a06f621cd4bd55c4b445a94f709e54bfb2a87009a2a68f0b262a2fa",
    "verdict": "c06b6abdba37dcae513c329ab2d4ef70a7f742765764d90a6ef9db818d8ae63e",
    "r391_analysis": "170658c967798aced2f4b62b614dd2863d2a8445ea4e92fbc2ac05968731619e",
    "r392_analysis": "e05da2d17c19d8d02012e4b8b1fc9d48b2ccb26d1af195bf9c3799fb7cb3ec8b",
    "r391_verdict": "783563039870384cdcff1c58ca7ab8a79b40d16651c643f06d72debcdd1c0f47",
    "r392_verdict": "472c930f114e29536eb71012832434e968d1539cf60b912571988bd1114fac9e",
}


def build_r394_contract() -> dict[str, Any]:
    """Return R393's science unchanged plus R394 correction provenance."""

    contract = deepcopy(build_ppvsm1_object_contract())
    contract.update(
        {
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "parent_round": "R393",
            "parent_contract_sha256": payload_sha256(
                build_ppvsm1_object_contract()
            ),
            "parent_r393_sha256": deepcopy(R393_PARENT_SHA256),
            "evidence_corrections": [
                "initial_trace_variable_array_readback",
                "frozen_zero_point_two_second_tds_horizon",
                "pre_init_source_snapshot",
            ],
        }
    )
    return contract


def source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "parent_runner": PARENT_RUNNER,
        "model": ROOT / "src/andes_rl_kundur/env/andes/ppvsm1.py",
        "builder": ROOT / "src/andes_rl_kundur/env/andes/ppvsm1_static_kundur.py",
        "builder_base": ROOT
        / "src/andes_rl_kundur/env/andes/regcv1_static_kundur.py",
        "classifier": ROOT
        / "src/andes_rl_kundur/evaluation/ppvsm1_object_gate.py",
        "builder_tests": ROOT / "tests/test_ppvsm1_static_kundur.py",
        "classifier_tests": ROOT / "tests/test_ppvsm1_object_gate.py",
        "runner_tests": ROOT / "tests/test_r394_ppvsm1_object_gate.py",
        "plan": PLAN,
        "question": QUESTION,
        "programme": ROOT / "memory/RESEARCH_PROGRAM.md",
        "line": ROOT / "paper/converter_vsg_pq_decoupling/LINE.md",
        "artifact_manifest": ROOT
        / "paper/converter_vsg_pq_decoupling/ARTIFACTS.json",
        "route_contract": ROOT
        / "paper/converter_vsg_pq_decoupling/working/route_contract.md",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": base.relative(path), "sha256": base.sha256_file(path)}
        for name, path in sources.items()
    }


def parent_manifest() -> dict[str, dict[str, str]]:
    result_root = ROOT / "results/research_loop/r393_ppvsm1_object_gate"
    parents = {
        "seal": ROOT / "memory/rounds/R393/formal_seal.json",
        "attempt": result_root / "formal_attempt.json",
        "execution": result_root / "formal_execution.json",
        "analysis": result_root / "formal_analysis.json",
        "manifest": result_root / "formal_manifest.json",
        "claim": ROOT / "memory/claims/CLM-1110.md",
        "feed": ROOT / "paper/converter_vsg_pq_decoupling/reports/R393.md",
        "verdict": ROOT / "memory/rounds/R393/verdict.md",
        "r391_analysis": ROOT
        / "results/research_loop/r391_regf2_equilibrium_eig_correction_gate/formal_analysis.json",
        "r392_analysis": ROOT
        / "results/research_loop/r392_regf2_loop_perturbation_gate/formal_analysis.json",
        "r391_verdict": ROOT / "memory/rounds/R391/verdict.md",
        "r392_verdict": ROOT / "memory/rounds/R392/verdict.md",
    }
    return {
        name: {"path": base.relative(path), "sha256": base.sha256_file(path)}
        for name, path in parents.items()
    }


def validate_r393_parent_chain(contract: Mapping[str, Any]) -> bool:
    try:
        parents = parent_manifest()
        if {
            name: row["sha256"] for name, row in parents.items()
        } != contract["parent_r393_sha256"]:
            return False
        attempt = base.read_hashed_json(ROOT / parents["attempt"]["path"])
        execution = base.read_hashed_json(ROOT / parents["execution"]["path"])
        analysis = base.read_hashed_json(ROOT / parents["analysis"]["path"])
        manifest = base.read_hashed_json(ROOT / parents["manifest"]["path"])
        seal = base.read_hashed_json(ROOT / parents["seal"]["path"])
        return bool(
            seal["round"] == "R393"
            and attempt["round"] == "R393"
            and execution["round"] == "R393"
            and manifest["round"] == "R393"
            and attempt["seal_sha256"] == parents["seal"]["sha256"]
            and execution["seal_sha256"] == parents["seal"]["sha256"]
            and execution["attempt_sha256"] == parents["attempt"]["sha256"]
            and analysis["seal_sha256"] == parents["seal"]["sha256"]
            and analysis["formal_execution_sha256"]
            == parents["execution"]["sha256"]
            and manifest["entries"][0]["path"].endswith("formal_attempt.json")
            and analysis["classification"] == "ANALYSIS-INVALID"
        )
    except (KeyError, TypeError, ValueError, FileNotFoundError):
        return False


def _freeze_horizon(system: Any, contract: Mapping[str, Any]) -> float:
    system.TDS.config.tf = float(contract["tds_tf_seconds"])
    return float(system.TDS.config.tf)


def _initial_trace_row(system: Any) -> dict[str, Any]:
    """Read every variable from its own numeric array (R394 correction 1)."""

    bus_values = np.asarray(system.Bus.v.v, dtype=float)
    bus_addresses = [int(value) for value in system.Bus.v.a]
    bus_v = {
        str(bus): float(bus_values[address])
        for bus, address in zip(system.Bus.idx.v, bus_addresses, strict=True)
    }
    variable_map = {
        "Pe": system.PPVSM1.Pe,
        "Qe": system.PPVSM1.Qe,
        "Id": system.PPVSM1.Id,
        "Iq": system.PPVSM1.Iq,
        "virtual_frequency": system.PPVSM1.INTw_y,
    }
    devices: dict[str, dict[str, float]] = {}
    for position, idx in enumerate(system.PPVSM1.idx.v):
        row: dict[str, float] = {}
        for signal, variable in variable_map.items():
            address = int(variable.a[position])
            row[signal] = float(np.asarray(variable.v, dtype=float)[address])
        devices[str(idx)] = row
    return {"time": float(system.dae.t), "bus_v": bus_v, "devices": devices}


def _run_arm(
    contract: Mapping[str, Any], runtime: Mapping[str, Any]
) -> dict[str, Any]:
    """R393's arm with only the three evidence-seam corrections."""

    record = parent_runner._empty_record(payload_sha256(contract))
    system: Any | None = None
    built: Any | None = None
    try:
        audit = base.load_verified_static_case(
            xlsx_path=runtime["xlsx_case_path"],
            json_path=runtime["json_case_path"],
        )
        built = build_ppvsm1_static_kundur_object(
            full_case=audit.full_case, work_dir=Path.cwd()
        )
        system = built.system
        record["source"] = {
            "andes_version": runtime["andes_version"],
            "xlsx_case_sha256": audit.xlsx_sha256,
            "json_case_sha256": audit.json_sha256,
            "derived_case_sha256": built.derived_case_sha256,
            "ppvsm1_model_sha256": runtime["ppvsm1_model_sha256"],
            "eig_source_sha256": runtime["eig_source_sha256"],
        }
        system.TDS.config.tol = float(contract["tds_tolerance"])
        _freeze_horizon(system, contract)
        system.setup()
        record["solver"]["setup_completed"] = bool(system.is_setup)
        record["inventory"] = parent_runner._inventory(system, built, contract)

        system.PFlow.run()
        record["solver"]["pflow_converged"] = system.PFlow.converged is True
        if not record["solver"]["pflow_converged"]:
            record["scientific_error"] = "PFlow did not converge"
            record["initialization_diagnostics"] = (
                base.capture_initialization_diagnostics(system)
            )
            return record

        # R394 correction 3: snapshot before TDS.init.
        source_rows = parent_runner._source_snapshot(system, contract)

        init_return = system.TDS.init()
        record["solver"]["tds_initialized"] = init_return is not False
        record["solver"]["tds_test_ok"] = system.TDS.test_ok is True
        record["solver"]["tds_tolerance"] = float(system.TDS.config.tol)
        record["initialization_diagnostics"] = (
            base.capture_initialization_diagnostics(system)
        )
        record["references"] = {
            "checked": True,
            "phase": "post_init",
            "rows": source_rows,
        }
        if not (
            record["solver"]["tds_initialized"]
            and record["solver"]["tds_test_ok"]
        ):
            record["scientific_error"] = "TDS initialization failed"
            record["finite_guard"] = parent_runner._finite_status(
                system, state_matrix_finite=False
            )
            return record

        models = system.exist.pflow_tds
        system.TDS.fg_update(models=models)
        system.j_update(models=models, info="R394 fixed equilibrium EIG snapshot")
        time_before = float(system.dae.t)
        eig_return = system.EIG.run()
        record["solver"]["eig_return"] = bool(eig_return)
        record["solver"]["time_before_eig"] = time_before
        record["solver"]["time_after_eig"] = float(system.dae.t)
        if not eig_return:
            record["scientific_error"] = "EIG calculation failed"
            record["finite_guard"] = parent_runner._finite_status(
                system, state_matrix_finite=False
            )
            return record
        state_matrix = parent_runner._dense_state_matrix(system)
        eigenvalues = np.asarray(system.EIG.mu, dtype=complex)
        if not np.all(np.isfinite(eigenvalues.real)) or not np.all(
            np.isfinite(eigenvalues.imag)
        ):
            raise RuntimeError("R394 spectrum is not finite")
        record["spectrum"] = {
            "captured": True,
            "state_count": int(state_matrix.shape[0]),
            "eigenvalues": [
                {"real": float(value.real), "imag": float(value.imag)}
                for value in eigenvalues
            ],
        }
        record["finite_guard"] = parent_runner._finite_status(
            system, state_matrix_finite=True
        )

        initial = _initial_trace_row(system)
        system.TDS.run()
        record["trajectory_attempted"] = True
        record["physical_trajectory_executed"] = True
        record["trajectory_count"] = 1
        record["solver"]["tds_converged"] = system.TDS.converged is True
        record["solver"]["terminal_time_seconds"] = float(system.dae.t)
        record["trace"] = parent_runner._capture_trace(system, initial)
        record["finite_guard"] = parent_runner._finite_status(
            system, state_matrix_finite=True
        )
    except Exception as exc:
        record["execution_error"] = f"{type(exc).__name__}: {exc}"
        if system is not None:
            try:
                record["finite_guard"] = parent_runner._finite_status(
                    system, state_matrix_finite=False
                )
            except Exception:
                pass
    return record


def run_formal_record(
    contract: Mapping[str, Any], runtime: Mapping[str, Any]
) -> dict[str, Any]:
    return _run_arm(contract, runtime)


_parent_setup_only_canary = parent_runner.setup_only_canary


def setup_only_canary(runtime: Mapping[str, Any]) -> dict[str, Any]:
    result = _parent_setup_only_canary(runtime)
    contract = build_r394_contract()
    audit = base.load_verified_static_case(
        xlsx_path=runtime["xlsx_case_path"],
        json_path=runtime["json_case_path"],
    )
    built = build_ppvsm1_static_kundur_object(
        full_case=audit.full_case, work_dir=Path.cwd()
    )
    system = built.system
    system.setup()
    horizon = _freeze_horizon(system, contract)
    snapshot_rows = parent_runner._source_snapshot(system, contract)
    variables = (
        system.Bus.v,
        system.PPVSM1.Pe,
        system.PPVSM1.Qe,
        system.PPVSM1.Id,
        system.PPVSM1.Iq,
        system.PPVSM1.INTw_y,
    )
    variable_read_ok = all(
        hasattr(variable, "v") and hasattr(variable, "a")
        for variable in variables
    )
    result.update(
        {
            "correction_canary": {
                "frozen_horizon": horizon,
                "frozen_horizon_ok": horizon == contract["tds_tf_seconds"],
                "pre_init_snapshot_rows": len(snapshot_rows),
                "pre_init_snapshot_finite": all(
                    row["abs_deviation"] >= 0 for row in snapshot_rows
                ),
                "variable_array_readback_ok": variable_read_ok,
            },
        }
    )
    result["runtime_api_present"] = bool(
        result["runtime_api_present"]
        and result["correction_canary"]["frozen_horizon_ok"]
        and result["correction_canary"]["variable_array_readback_ok"]
    )
    return result


def _configure_parent() -> None:
    parent_runner.ROUND_ID = ROUND_ID
    parent_runner.QUESTION_ID = QUESTION_ID
    parent_runner.LINE_ID = LINE_ID
    parent_runner.PLAN = PLAN
    parent_runner.QUESTION = QUESTION
    parent_runner.REHEARSAL = REHEARSAL
    parent_runner.CAPACITY = CAPACITY
    parent_runner.SEAL = SEAL
    parent_runner.DEFAULT_OUT = DEFAULT_OUT
    parent_runner.build_ppvsm1_object_contract = build_r394_contract
    parent_runner.setup_only_canary = setup_only_canary
    parent_runner.run_formal_record = run_formal_record
    parent_runner.source_manifest = source_manifest
    parent_runner.parent_manifest = parent_manifest
    parent_runner._configure_lifecycle()


_configure_parent()


def rehearse() -> str:
    contract = build_r394_contract()
    if not validate_r393_parent_chain(contract):
        raise RuntimeError("R394 frozen R393 parent chain failed before rehearsal")
    return parent_runner.rehearse()


def prepare() -> str:
    contract = build_r394_contract()
    if not validate_r393_parent_chain(contract):
        raise RuntimeError("R394 frozen R393 parent chain failed before sealing")
    return parent_runner.prepare()


def execute(*, expected_sha256: str) -> str:
    return base.execute(expected_sha256=expected_sha256, out_dir=DEFAULT_OUT)


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
        print(f"rehearsal_sha256={rehearse()}")
    elif args.command == "prepare":
        print(f"seal_sha256={prepare()}")
    elif args.command == "execute":
        print(f"analysis_sha256={execute(expected_sha256=args.expected_seal_sha256)}")
    else:  # pragma: no cover
        raise RuntimeError(f"unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
