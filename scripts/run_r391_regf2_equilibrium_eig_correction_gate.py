"""Run the science-identical R391 correction of the invalid R390 EIG gate.

Motivation:
    R390 is analysis-invalid because its finite guard cannot convert installed
    ANDES sparse Jacobians and its name validator confuses configured indices
    with ANDES display ordinals. R391 corrects only those evidence seams.

Usage:
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r391_regf2_equilibrium_eig_correction_gate.py rehearse
    /home/wya/andes_venv/bin/python \
        scripts/run_r391_regf2_equilibrium_eig_correction_gate.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r391_regf2_equilibrium_eig_correction_gate.py execute \
        --expected-seal-sha256 <sha256>

Failure modes:
    Source, parent, correction-schema, raw-name, capture, exception, or
    create-only defects are ANALYSIS-INVALID. Complete valid scientific stops
    preserve R390's frozen taxonomy. There is no retry, controller, training,
    topology change, parameter change, or R390 reinterpretation.
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

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.evaluation.regf2_equilibrium_eig_correction_gate import (  # noqa: E402
    build_regf2_equilibrium_eig_correction_contract,
    classify_regf2_equilibrium_eig_correction_record,
    payload_sha256,
)

PARENT_RUNNER = ROOT / "scripts/run_r390_regf2_equilibrium_eig_gate.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load R391 parent dependency: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


parent_runner = _load_module("r391_r390_parent", PARENT_RUNNER)
base = parent_runner.base
_parent_installed_runtime = parent_runner.installed_runtime
_parent_installed_runtime_matches_contract = (
    parent_runner.installed_runtime_matches_contract
)

ROUND_ID = "R391"
QUESTION_ID = "Q-0108"
LINE_ID = "converter-vsg-pq-decoupling"
PLAN = ROOT / "memory/rounds/R391/plan.md"
QUESTION = ROOT / "memory/questions/Q-0108.md"
REHEARSAL = ROOT / "memory/rounds/R391/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R391/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R391/formal_seal.json"
DEFAULT_OUT = (
    ROOT / "results/research_loop/r391_regf2_equilibrium_eig_correction_gate"
)


def dense_andes_matrix(
    value: Any,
    *,
    sparse_converter: Callable[[Any], Any] | None = None,
) -> np.ndarray:
    """Return one finite two-dimensional ANDES matrix, including kvxopt."""

    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        if sparse_converter is None:
            from andes.shared import matrix as sparse_converter

        array = np.asarray(sparse_converter(value), dtype=float)
    if array.ndim != 2 or not np.all(np.isfinite(array)):
        raise ValueError("R391 Jacobian must be a finite two-dimensional matrix")
    return array


def sparse_adapter_canary() -> bool:
    """Exercise the installed kvxopt-to-dense conversion without a simulation."""

    try:
        from andes.shared import spmatrix

        value = spmatrix([1.0], [0], [0], (1, 1))
        converted = dense_andes_matrix(value)
        return bool(converted.shape == (1, 1) and converted[0, 0] == 1.0)
    except (ImportError, TypeError, ValueError):
        return False


def installed_runtime() -> dict[str, Any]:
    """Bind the correction-defining ANDES/kvxopt conversion runtime."""

    import kvxopt
    from andes import shared as andes_shared
    from kvxopt import base as kvxopt_base

    runtime = _parent_installed_runtime()
    shared_path = Path(andes_shared.__file__).resolve()
    kvxopt_base_path = Path(kvxopt_base.__file__).resolve()
    runtime.update(
        {
            "andes_shared_path": str(shared_path),
            "andes_shared_sha256": base.sha256_file(shared_path),
            "kvxopt_base_path": str(kvxopt_base_path),
            "kvxopt_base_sha256": base.sha256_file(kvxopt_base_path),
            "kvxopt_version": str(kvxopt.__version__),
        }
    )
    return runtime


def installed_runtime_matches_contract(
    runtime: Mapping[str, Any], contract: Mapping[str, Any]
) -> bool:
    """Require the inherited runtime and exact sparse-adapter identities."""

    expected = contract.get("sparse_adapter_runtime")
    return bool(
        _parent_installed_runtime_matches_contract(runtime, contract)
        and isinstance(expected, Mapping)
        and all(runtime.get(key) == value for key, value in expected.items())
    )


def _finite_status(system: Any, *, state_matrix_finite: bool) -> dict[str, bool]:
    dae_finite, _ = parent_runner.parent.finite_guards(system)
    jacobian_finite = True
    for name in ("fx", "fy", "gx", "gy"):
        try:
            dense_andes_matrix(getattr(system.dae, name))
        except (AttributeError, TypeError, ValueError):
            jacobian_finite = False
    return {
        "checked": True,
        "dae_finite": dae_finite,
        "jacobian_finite": jacobian_finite,
        "state_matrix_finite": state_matrix_finite,
    }


def source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "parent_runner": PARENT_RUNNER,
        "parent_object_runner": parent_runner.PARENT_RUNNER,
        "lifecycle_base": parent_runner.parent.BASE_RUNNER,
        "classifier": ROOT
        / "src/andes_rl_kundur/evaluation/regf2_equilibrium_eig_correction_gate.py",
        "parent_classifier": ROOT
        / "src/andes_rl_kundur/evaluation/regf2_equilibrium_eig_gate.py",
        "parent_object_classifier": ROOT
        / "src/andes_rl_kundur/evaluation/regf2_object_init_gate.py",
        "builder": ROOT / "src/andes_rl_kundur/env/andes/regf2_static_kundur.py",
        "builder_base": ROOT
        / "src/andes_rl_kundur/env/andes/regcv1_static_kundur.py",
        "classifier_tests": ROOT
        / "tests/test_regf2_equilibrium_eig_correction_gate.py",
        "runner_tests": ROOT
        / "tests/test_r391_regf2_equilibrium_eig_correction_gate.py",
        "parent_classifier_tests": ROOT
        / "tests/test_regf2_equilibrium_eig_gate.py",
        "parent_runner_tests": ROOT
        / "tests/test_r390_regf2_equilibrium_eig_gate.py",
        "builder_tests": ROOT / "tests/test_regf2_static_kundur.py",
        "established_sparse_adapter": ROOT
        / "src/andes_rl_kundur/evaluation/vsg_energy_port_source_adapter.py",
        "plan": PLAN,
        "question": QUESTION,
        "programme": ROOT / "memory/RESEARCH_PROGRAM.md",
        "line": ROOT / "paper/converter_vsg_pq_decoupling/LINE.md",
        "artifact_manifest": ROOT
        / "paper/converter_vsg_pq_decoupling/ARTIFACTS.json",
        "route_contract": ROOT
        / "paper/converter_vsg_pq_decoupling/working/route_contract.md",
        "r390_diagnosis": ROOT
        / "paper/converter_vsg_pq_decoupling/working/R390_diagnosis.md",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": base.relative(path), "sha256": base.sha256_file(path)}
        for name, path in sources.items()
    }


def parent_manifest() -> dict[str, dict[str, str]]:
    parents = {
        "seal": ROOT / "memory/rounds/R390/formal_seal.json",
        "attempt": ROOT
        / "results/research_loop/r390_regf2_equilibrium_eig_gate/formal_attempt.json",
        "execution": ROOT
        / "results/research_loop/r390_regf2_equilibrium_eig_gate/formal_execution.json",
        "analysis": ROOT
        / "results/research_loop/r390_regf2_equilibrium_eig_gate/formal_analysis.json",
        "manifest": ROOT
        / "results/research_loop/r390_regf2_equilibrium_eig_gate/formal_manifest.json",
        "claim": ROOT / "memory/claims/CLM-1095.md",
        "feed": ROOT / "paper/converter_vsg_pq_decoupling/reports/R390.md",
        "diagnosis": ROOT
        / "paper/converter_vsg_pq_decoupling/working/R390_diagnosis.md",
        "publication_audit": ROOT
        / "paper/converter_vsg_pq_decoupling/working/R390_publication_audit.md",
        "verdict": ROOT / "memory/rounds/R390/verdict.md",
    }
    return {
        name: {"path": base.relative(path), "sha256": base.sha256_file(path)}
        for name, path in parents.items()
    }


def validate_r390_parent_chain(contract: Mapping[str, Any]) -> bool:
    try:
        parents = parent_manifest()
        if {
            name: row["sha256"] for name, row in parents.items()
        } != contract["parent_r390_sha256"]:
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
            seal["round"] == "R390"
            and attempt["round"] == "R390"
            and execution["round"] == "R390"
            and analysis["round"] == "R390"
            and attempt["seal_sha256"] == parents["seal"]["sha256"]
            and execution["attempt_sha256"] == parents["attempt"]["sha256"]
            and execution["seal_sha256"] == parents["seal"]["sha256"]
            and analysis["formal_execution_sha256"]
            == parents["execution"]["sha256"]
            and analysis["seal_sha256"] == parents["seal"]["sha256"]
            and manifest["entries"] == expected_entries
            and manifest["round"] == "R390"
            and attempt["round"] == "R390"
        )
    except (KeyError, TypeError, ValueError, FileNotFoundError):
        return False


_parent_setup_only_canary = parent_runner.setup_only_canary


def setup_only_canary(runtime: Mapping[str, Any]) -> dict[str, Any]:
    result = _parent_setup_only_canary(runtime)
    sparse_ok = sparse_adapter_canary()
    result["installed_sparse_adapter_present"] = sparse_ok
    result["runtime_api_present"] = bool(result["runtime_api_present"] and sparse_ok)
    return result


def run_formal_record(
    contract: Mapping[str, Any], runtime: Mapping[str, Any]
) -> dict[str, Any]:
    """Execute R390's exact ordered arms with only the corrected finite guard."""

    return {
        "schema_version": 2,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "contract_sha256": payload_sha256(contract),
        "formal_input_complete": True,
        "execution_error": None,
        "training_executed": False,
        "post_init_action_executed": False,
        "trajectory_count": 0,
        "arms": [
            parent_runner._run_arm(arm_spec, contract, runtime)
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
    parent_runner.build_regf2_equilibrium_eig_contract = (
        build_regf2_equilibrium_eig_correction_contract
    )
    parent_runner.classify_regf2_equilibrium_eig_record = (
        classify_regf2_equilibrium_eig_correction_record
    )
    parent_runner.source_manifest = source_manifest
    parent_runner.parent_manifest = parent_manifest
    original_r389_validator = parent_runner.validate_r389_parent_chain
    parent_runner.validate_r389_parent_chain = lambda contract: bool(
        original_r389_validator(contract) and validate_r390_parent_chain(contract)
    )
    parent_runner.setup_only_canary = setup_only_canary
    parent_runner.installed_runtime = installed_runtime
    parent_runner.installed_runtime_matches_contract = (
        installed_runtime_matches_contract
    )
    parent_runner._finite_status = _finite_status
    parent_runner.run_formal_record = run_formal_record
    parent_runner._configure_lifecycle()


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
