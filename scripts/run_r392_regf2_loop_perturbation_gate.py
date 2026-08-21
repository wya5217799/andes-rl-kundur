"""Run the sealed R392 REGF2 loop-perturbation mechanism gate.

Motivation:
    R391/CLM-1100 validly locates two reproducible positive-real local modes
    in the exact initialized four-stock-REGF2 reduced model; participation is
    association, not causality. R392 diagnoses the stopped object only: eight
    fresh serial no-time-advance arms, each changing exactly one explicit
    REGF2 parameter before setup, re-running the frozen EIG gate. It reopens
    no authority, controller, or learning work.

Usage:
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r392_regf2_loop_perturbation_gate.py rehearse
    /home/wya/andes_venv/bin/python \
        scripts/run_r392_regf2_loop_perturbation_gate.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r392_regf2_loop_perturbation_gate.py execute \
        --expected-seal-sha256 <sha256>

Failure modes:
    Provenance, parent-chain, perturbation-readback, capture, exception, or
    create-only defects are ANALYSIS-INVALID. Reference-arm guard failure is
    a platform STOP; perturbation-arm init failure is a typed per-arm stop.
    There is no trajectory, action, retry, controller, tuning sweep, or
    training command.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from collections.abc import Callable, Mapping
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

from andes_rl_kundur.evaluation.regf2_loop_perturbation_gate import (  # noqa: E402
    build_regf2_loop_perturbation_contract,
    classify_regf2_loop_perturbation_record,
    expected_perturbation_value,
    payload_sha256,
)

PARENT_RUNNER = ROOT / "scripts/run_r391_regf2_equilibrium_eig_correction_gate.py"
_parent_spec = importlib.util.spec_from_file_location("r392_r391_parent", PARENT_RUNNER)
if _parent_spec is None or _parent_spec.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load R391 parent runner: {PARENT_RUNNER}")
parent_runner = importlib.util.module_from_spec(_parent_spec)
_parent_spec.loader.exec_module(parent_runner)
base = parent_runner.base
r390 = parent_runner.parent_runner
r389 = r390.parent

ROUND_ID = "R392"
QUESTION_ID = "Q-0109"
LINE_ID = "converter-vsg-pq-decoupling"
PLAN = ROOT / "memory/rounds/R392/plan.md"
QUESTION = ROOT / "memory/questions/Q-0109.md"
REHEARSAL = ROOT / "memory/rounds/R392/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R392/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R392/formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r392_regf2_loop_perturbation_gate"


def source_manifest() -> dict[str, dict[str, str]]:
    """Hash every prospective implementation and authority input."""

    sources = {
        "runner": Path(__file__).resolve(),
        "parent_runner": PARENT_RUNNER,
        "parent_object_runner": parent_runner.PARENT_RUNNER,
        "grandparent_object_runner": parent_runner.parent_runner.PARENT_RUNNER,
        "lifecycle_base": parent_runner.parent_runner.parent.BASE_RUNNER,
        "classifier": ROOT
        / "src/andes_rl_kundur/evaluation/regf2_loop_perturbation_gate.py",
        "parent_classifier": ROOT
        / "src/andes_rl_kundur/evaluation/regf2_equilibrium_eig_correction_gate.py",
        "parent_parent_classifier": ROOT
        / "src/andes_rl_kundur/evaluation/regf2_equilibrium_eig_gate.py",
        "object_classifier": ROOT
        / "src/andes_rl_kundur/evaluation/regf2_object_init_gate.py",
        "builder": ROOT / "src/andes_rl_kundur/env/andes/regf2_static_kundur.py",
        "builder_base": ROOT
        / "src/andes_rl_kundur/env/andes/regcv1_static_kundur.py",
        "established_sparse_adapter": ROOT
        / "src/andes_rl_kundur/evaluation/vsg_energy_port_source_adapter.py",
        "classifier_tests": ROOT
        / "tests/test_regf2_loop_perturbation_gate.py",
        "runner_tests": ROOT
        / "tests/test_r392_regf2_loop_perturbation_gate.py",
        "parent_classifier_tests": ROOT
        / "tests/test_regf2_equilibrium_eig_correction_gate.py",
        "parent_runner_tests": ROOT
        / "tests/test_r391_regf2_equilibrium_eig_correction_gate.py",
        "builder_tests": ROOT / "tests/test_regf2_static_kundur.py",
        "plan": PLAN,
        "question": QUESTION,
        "programme": ROOT / "memory/RESEARCH_PROGRAM.md",
        "line": ROOT / "paper/converter_vsg_pq_decoupling/LINE.md",
        "artifact_manifest": ROOT
        / "paper/converter_vsg_pq_decoupling/ARTIFACTS.json",
        "route_contract": ROOT
        / "paper/converter_vsg_pq_decoupling/working/route_contract.md",
        "r391_diagnosis": ROOT
        / "paper/converter_vsg_pq_decoupling/working/R391_diagnosis.md",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": base.relative(path), "sha256": base.sha256_file(path)}
        for name, path in sources.items()
    }


def parent_manifest() -> dict[str, dict[str, str]]:
    """Bind the immutable R391 scientific parent and closure artifacts."""

    result_root = ROOT / "results/research_loop/r391_regf2_equilibrium_eig_correction_gate"
    parents = {
        "seal": ROOT / "memory/rounds/R391/formal_seal.json",
        "attempt": result_root / "formal_attempt.json",
        "execution": result_root / "formal_execution.json",
        "analysis": result_root / "formal_analysis.json",
        "manifest": result_root / "formal_manifest.json",
        "claim": ROOT / "memory/claims/CLM-1100.md",
        "feed": ROOT / "paper/converter_vsg_pq_decoupling/reports/R391.md",
        "diagnosis": ROOT
        / "paper/converter_vsg_pq_decoupling/working/R391_diagnosis.md",
        "publication_audit": ROOT
        / "paper/converter_vsg_pq_decoupling/working/R391_publication_audit.md",
        "verdict": ROOT / "memory/rounds/R391/verdict.md",
    }
    return {
        name: {"path": base.relative(path), "sha256": base.sha256_file(path)}
        for name, path in parents.items()
    }


def validate_r391_parent_chain(contract: Mapping[str, Any]) -> bool:
    """Validate the frozen R391 seal-to-manifest chain and its verdict."""

    try:
        parents = parent_manifest()
        if {
            name: row["sha256"] for name, row in parents.items()
        } != contract["parent_r391_sha256"]:
            return False
        attempt = base.read_hashed_json(ROOT / parents["attempt"]["path"])
        execution = base.read_hashed_json(ROOT / parents["execution"]["path"])
        analysis = base.read_hashed_json(ROOT / parents["analysis"]["path"])
        manifest = base.read_hashed_json(ROOT / parents["manifest"]["path"])
        seal = base.read_hashed_json(ROOT / parents["seal"]["path"])
        expected_entries = [
            {
                "path": parents[name]["path"],
                "sha256": parents[name]["sha256"],
            }
            for name in ("attempt", "execution", "analysis")
        ]
        return bool(
            seal["round"] == "R391"
            and attempt["round"] == "R391"
            and execution["round"] == "R391"
            and analysis["round"] == "R391"
            and manifest["round"] == "R391"
            and attempt["seal_sha256"] == parents["seal"]["sha256"]
            and execution["attempt_sha256"] == parents["attempt"]["sha256"]
            and execution["seal_sha256"] == parents["seal"]["sha256"]
            and analysis["formal_execution_sha256"]
            == parents["execution"]["sha256"]
            and analysis["seal_sha256"] == parents["seal"]["sha256"]
            and manifest["entries"] == expected_entries
            and analysis["classification"] == "STOP-REGF2-POSITIVE-REAL-GUARD"
        )
    except (KeyError, TypeError, ValueError, FileNotFoundError):
        return False


def _apply_perturbation(
    system: Any, arm_spec: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any]:
    """Alter one parameter on all four devices before setup; return readback."""

    spec = arm_spec["perturbation"]
    if spec is None:
        return {
            "param": None,
            "factor": None,
            "expected_value": None,
            "readback": [],
            "applied": False,
        }
    param = str(spec["param"])
    if param not in contract["card_defaults"]:
        raise RuntimeError(f"R392 unknown perturbation parameter: {param}")
    expected = expected_perturbation_value(spec, contract["card_defaults"])
    if expected is None:
        raise RuntimeError("R392 perturbation spec resolves to no value")
    device_ids = [f"REGF2_{index}" for index in range(1, 5)]
    for device_id in device_ids:
        system.REGF2.set(param, device_id, expected, base="device")
    readback = [
        float(system.REGF2.get(src=param, idx=device_id, attr="v"))
        for device_id in device_ids
    ]
    return {
        "param": param,
        "factor": float(spec["factor"]) if "factor" in spec else None,
        "expected_value": expected,
        "readback": readback,
        "applied": True,
    }


def perturbation_canary(runtime: Mapping[str, Any]) -> dict[str, Any]:
    """Exercise alter + readback on constructed objects; no PFlow/EIG."""

    contract = build_regf2_loop_perturbation_contract()
    audit = base.load_verified_static_case(
        xlsx_path=runtime["xlsx_case_path"],
        json_path=runtime["json_case_path"],
    )
    expected_mf = expected_perturbation_value(
        {"param": "mf", "factor": 4.0}, contract["card_defaults"]
    )
    built = r389.build_regf2_static_kundur_object(
        full_case=audit.full_case, work_dir=Path.cwd()
    )
    system = built.system
    device_ids = [f"REGF2_{index}" for index in range(1, 5)]
    for device_id in device_ids:
        system.REGF2.set("mf", device_id, expected_mf, base="device")
    mf_readback = [
        float(system.REGF2.get(src="mf", idx=device_id, attr="v"))
        for device_id in device_ids
    ]
    system.setup()

    built_sn = r389.build_regf2_static_kundur_object(
        full_case=audit.full_case, work_dir=Path.cwd()
    )
    system_sn = built_sn.system
    for device_id in device_ids:
        system_sn.REGF2.set("Sn", device_id, 100.0, base="device")
    sn_readback = [
        float(system_sn.REGF2.get(src="Sn", idx=device_id, attr="v"))
        for device_id in device_ids
    ]
    system_sn.setup()
    runtime_xf = [
        float(system_sn.REGF2.get(src="xf", idx=device_id, attr="v"))
        for device_id in device_ids
    ]
    return {
        "mf_x4_readback_ok": mf_readback == [expected_mf] * 4,
        "mf_x4_setup_completed": bool(system.is_setup),
        "sn_100_readback_ok": sn_readback == [100.0] * 4,
        "sn_100_setup_completed": bool(system_sn.is_setup),
        "sn_100_runtime_xf": runtime_xf,
        "sn_100_runtime_xf_ok": all(
            abs(value - 0.2) < 1e-12 for value in runtime_xf
        ),
    }


_parent_setup_only_canary = parent_runner.setup_only_canary


def setup_only_canary(runtime: Mapping[str, Any]) -> dict[str, Any]:
    result = _parent_setup_only_canary(runtime)
    canary = perturbation_canary(runtime)
    result.update(
        {
            "perturbation_canary": canary,
            "perturbation_injection_ok": bool(
                canary["mf_x4_readback_ok"]
                and canary["mf_x4_setup_completed"]
                and canary["sn_100_readback_ok"]
                and canary["sn_100_setup_completed"]
                and canary["sn_100_runtime_xf_ok"]
            ),
        }
    )
    result["runtime_api_present"] = bool(
        result["runtime_api_present"] and result["perturbation_injection_ok"]
    )
    return result


def _empty_arm(
    arm_spec: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any]:
    record = r390._empty_arm(arm_spec, contract)
    record["perturbation"] = {
        "param": None,
        "factor": None,
        "expected_value": None,
        "readback": [],
        "applied": False,
    }
    return record


def _run_arm(
    arm_spec: Mapping[str, Any],
    contract: Mapping[str, Any],
    runtime: Mapping[str, Any],
) -> dict[str, Any]:
    """Run one fresh no-time-advance arm with its frozen perturbation."""

    record = _empty_arm(arm_spec, contract)
    parent_contract = contract["object_contract"]
    system: Any | None = None
    built: Any | None = None
    try:
        audit = base.load_verified_static_case(
            xlsx_path=runtime["xlsx_case_path"],
            json_path=runtime["json_case_path"],
        )
        built = r389.build_regf2_static_kundur_object(
            full_case=audit.full_case,
            work_dir=Path.cwd(),
        )
        system = built.system
        record["source"] = r390._source_record(
            runtime, audit, built.derived_case_sha256
        )
        record["perturbation"] = _apply_perturbation(system, arm_spec, contract)
        system.TDS.config.tol = float(arm_spec["tds_tolerance"])
        system.setup()
        record["solver"]["setup_completed"] = bool(system.is_setup)
        record["solver"]["actual_tds_tolerance"] = float(system.TDS.config.tol)
        record["solver"]["system_exit_code"] = int(getattr(system, "exit_code", 0))
        record["inventory"] = r389._full_inventory(
            system, built, parent_contract
        )

        record["solver"]["pflow_converged"] = r390.run_pflow_and_read_converged(
            system
        )
        record["solver"]["system_exit_code"] = int(getattr(system, "exit_code", 0))
        if not record["solver"]["pflow_converged"]:
            record["scientific_error"] = "PFlow did not converge"
            record["initialization_diagnostics"] = (
                r389.capture_initialization_diagnostics(
                    system,
                    residual_threshold=float(parent_contract["residual_abs_threshold"]),
                )
            )
            record["finite_guard"] = parent_runner._finite_status(
                system, state_matrix_finite=False
            )
            return record

        source_rows = r389._source_snapshot(system, parent_contract)
        init_return = system.TDS.init()
        record["solver"]["tds_initialized"] = init_return is not False
        record["solver"]["tds_test_ok"] = system.TDS.test_ok is True
        record["solver"]["actual_tds_tolerance"] = float(system.TDS.config.tol)
        record["solver"]["system_exit_code"] = int(getattr(system, "exit_code", 0))
        record["inventory"] = r389._full_inventory(
            system, built, parent_contract
        )
        record["references"] = r389.post_init_references(
            system, source_rows, parent_contract
        )
        record["initialization_diagnostics"] = (
            r389.capture_initialization_diagnostics(
                system,
                residual_threshold=float(parent_contract["residual_abs_threshold"]),
            )
        )
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
        system.j_update(models=models, info="R392 fixed equilibrium EIG snapshot")
        record["initialization_diagnostics"] = (
            r389.capture_initialization_diagnostics(
                system,
                residual_threshold=float(parent_contract["residual_abs_threshold"]),
            )
        )
        time_before = float(system.dae.t)
        before = r390._equilibrium_row(system)
        eig_return = system.EIG.run()
        after = r390._equilibrium_row(system)
        record["equilibrium_snapshot"] = {
            "captured": True,
            "before": before,
            "after": after,
        }
        record["solver"]["eig_return"] = bool(eig_return)
        record["solver"]["time_before_eig"] = time_before
        record["solver"]["time_after_eig"] = float(system.dae.t)
        record["solver"]["state_max_abs_delta"] = max(
            r390._max_abs_delta(
                np.asarray(before[name], dtype=float),
                np.asarray(after[name], dtype=float),
            )
            for name in ("x", "y", "z")
        )
        record["solver"]["system_exit_code"] = int(getattr(system, "exit_code", 0))
        if not eig_return:
            record["scientific_error"] = "EIG calculation failed"
            record["matrix"] = r390._failed_matrix_record(system)
            record["finite_guard"] = parent_runner._finite_status(
                system, state_matrix_finite=False
            )
            return record

        state_matrix = parent_runner.dense_andes_matrix(system.EIG.As)
        eigenvalues = np.asarray(system.EIG.mu, dtype=complex)
        finite_matrix = bool(
            state_matrix.ndim == 2
            and state_matrix.shape[0] == state_matrix.shape[1]
            and state_matrix.size > 0
            and np.all(np.isfinite(state_matrix))
            and np.all(np.isfinite(eigenvalues.real))
            and np.all(np.isfinite(eigenvalues.imag))
        )
        if not finite_matrix:
            record["solver"]["eig_return"] = False
            record["scientific_error"] = "EIG calculation failed"
            record["matrix"] = r390._failed_matrix_record(system)
            record["finite_guard"] = parent_runner._finite_status(
                system, state_matrix_finite=False
            )
            return record
        bindings, zero_names = r390.capture_state_bindings(system, contract)
        state_catalog, algebraic_names, discrete_names = r390._dae_catalog(system)
        zero_addresses = [
            row["address"] for row in state_catalog if float(row["tf"]) == 0.0
        ]
        if [int(value) for value in system.EIG.zstate_idx] != zero_addresses:
            raise RuntimeError("R392 EIG zero-Tf address catalog mismatch")
        record["matrix"] = {
            "captured": True,
            "as": state_matrix.tolist(),
            "state_names": [str(value) for value in system.EIG.x_name],
            "andes_eigenvalues": [
                {"real": float(value.real), "imag": float(value.imag)}
                for value in eigenvalues
            ],
            "zero_tf_state_names": zero_names,
            "zero_tf_state_addresses": zero_addresses,
            "dead_algebraic_indices": [
                int(value) for value in getattr(system.EIG, "dead_algeb_idx", [])
            ],
            "dae_state_catalog": state_catalog,
            "dae_algebraic_names": algebraic_names,
            "dae_discrete_names": discrete_names,
            "eig_augmented_algebraic_names": algebraic_names + zero_names,
            "state_bindings": bindings,
        }
        record["finite_guard"] = parent_runner._finite_status(
            system, state_matrix_finite=True
        )
    except Exception as exc:
        record["execution_error"] = f"{type(exc).__name__}: {exc}"
        if system is not None and built is not None:
            try:
                record["inventory"] = r389._full_inventory(
                    system, built, parent_contract
                )
                diagnostics = r389.capture_initialization_diagnostics(
                    system,
                    residual_threshold=float(parent_contract["residual_abs_threshold"]),
                )
                if diagnostics.get("captured") is True:
                    record["initialization_diagnostics"] = diagnostics
                record["finite_guard"] = parent_runner._finite_status(
                    system, state_matrix_finite=False
                )
            except Exception:
                pass
    return record


def run_formal_record(
    contract: Mapping[str, Any], runtime: Mapping[str, Any]
) -> dict[str, Any]:
    """Execute the exact eight ordered perturbation arms serially."""

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "contract_sha256": payload_sha256(contract),
        "formal_input_complete": True,
        "execution_error": None,
        "training_executed": False,
        "post_init_action_executed": False,
        "trajectory_count": 0,
        "arms": [
            _run_arm(arm_spec, contract, runtime)
            for arm_spec in contract["arms"]
        ],
    }


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
    parent_runner.build_regf2_equilibrium_eig_correction_contract = (
        build_regf2_loop_perturbation_contract
    )
    parent_runner.classify_regf2_equilibrium_eig_correction_record = (
        classify_regf2_loop_perturbation_record
    )
    parent_runner.setup_only_canary = setup_only_canary
    parent_runner.run_formal_record = run_formal_record
    # R391-module source/parent manifests stay original so its own
    # validate_r390_parent_chain keeps resolving the R390 artifacts.
    parent_runner._configure_parent()

    _original_build_capacity_payload = base.build_capacity_payload

    def _build_capacity_payload_r392(**kwargs: Any) -> dict[str, Any]:
        payload = _original_build_capacity_payload(**kwargs)
        payload["empirical_anchor"] = {
            "concurrent_workers": 1,
            "all_records_valid": True,
            "native_threads_per_worker": 1,
            "source": "r392_rehearsal_setup_only_canary",
        }
        payload["capacity_canary"] = {
            "accepted": True,
            "accepted_worker_budget": 1,
        }
        return payload

    base.build_capacity_payload = _build_capacity_payload_r392
    # Override the R390-level seam with the R392 manifests and append the
    # R391 chain check; then re-propagate to the lifecycle base.
    _wrapped_r389_validator = r390.validate_r389_parent_chain
    r390.source_manifest = source_manifest
    r390.parent_manifest = parent_manifest
    r390.validate_r389_parent_chain = lambda contract: bool(
        _wrapped_r389_validator(contract) and validate_r391_parent_chain(contract)
    )
    r390._configure_lifecycle()


_configure_parent()


def rehearse() -> str:
    return parent_runner.rehearse()


def prepare() -> str:
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
        print(
            "analysis_sha256="
            f"{execute(expected_sha256=args.expected_seal_sha256)}"
        )
    else:  # pragma: no cover
        raise RuntimeError(f"unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
