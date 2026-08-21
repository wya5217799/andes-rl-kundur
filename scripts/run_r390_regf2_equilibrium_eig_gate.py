"""Run the sealed R390 exact-R389 equilibrium/reduced-spectrum gate.

Motivation:
    R389 stops the exact stock four-REGF2 object at a no-action stationarity
    gate but cannot distinguish local model-spectrum growth from a trajectory-
    integration effect. R390 inspects two independently initialized reduced
    state matrices without advancing simulation time.

Usage:
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r390_regf2_equilibrium_eig_gate.py rehearse
    /home/wya/andes_venv/bin/python \
        scripts/run_r390_regf2_equilibrium_eig_gate.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r390_regf2_equilibrium_eig_gate.py execute \
        --expected-seal-sha256 <sha256>

Failure modes:
    Provenance, schema, source, state-binding, diagnostic, seal, or create-only
    defects are ANALYSIS-INVALID. Complete equilibrium qualification and
    numerical-spectrum failures are scientific STOPs. A reproducible positive-
    real mode is also a paper-facing STOP, not a physical-stability claim.
    There is no trajectory, action, retry, controller, tuning, or training
    command.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import time
from collections.abc import Mapping
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
os.environ["DISABLE_TOGGLER"] = "1"

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.evaluation.regf2_equilibrium_eig_gate import (  # noqa: E402
    build_regf2_equilibrium_eig_contract,
    classify_regf2_equilibrium_eig_record,
)

PARENT_RUNNER = ROOT / "scripts/run_r389_regf2_object_init_gate.py"
_parent_spec = importlib.util.spec_from_file_location("r390_r389_parent", PARENT_RUNNER)
if _parent_spec is None or _parent_spec.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load R389 parent runner: {PARENT_RUNNER}")
parent = importlib.util.module_from_spec(_parent_spec)
_parent_spec.loader.exec_module(parent)
base = parent.base

ROUND_ID = "R390"
QUESTION_ID = "Q-0108"
LINE_ID = "converter-vsg-pq-decoupling"
PLAN = ROOT / "memory/rounds/R390/plan.md"
QUESTION = ROOT / "memory/questions/Q-0108.md"
REHEARSAL = ROOT / "memory/rounds/R390/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R390/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R390/formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r390_regf2_equilibrium_eig_gate"


def source_manifest() -> dict[str, dict[str, str]]:
    """Hash every prospective implementation and authority input."""

    sources = {
        "runner": Path(__file__).resolve(),
        "parent_runner": PARENT_RUNNER,
        "lifecycle_base": parent.BASE_RUNNER,
        "builder": ROOT / "src/andes_rl_kundur/env/andes/regf2_static_kundur.py",
        "builder_base": ROOT / "src/andes_rl_kundur/env/andes/regcv1_static_kundur.py",
        "parent_classifier": ROOT
        / "src/andes_rl_kundur/evaluation/regf2_object_init_gate.py",
        "classifier": ROOT
        / "src/andes_rl_kundur/evaluation/regf2_equilibrium_eig_gate.py",
        "builder_tests": ROOT / "tests/test_regf2_static_kundur.py",
        "parent_classifier_tests": ROOT / "tests/test_regf2_object_init_gate.py",
        "classifier_tests": ROOT / "tests/test_regf2_equilibrium_eig_gate.py",
        "runner_tests": ROOT / "tests/test_r390_regf2_equilibrium_eig_gate.py",
        "plan": PLAN,
        "question": QUESTION,
        "programme": ROOT / "memory/RESEARCH_PROGRAM.md",
        "line": ROOT / "paper/converter_vsg_pq_decoupling/LINE.md",
        "route_contract": ROOT
        / "paper/converter_vsg_pq_decoupling/working/route_contract.md",
        "artifact_manifest": ROOT
        / "paper/converter_vsg_pq_decoupling/ARTIFACTS.json",
        "route_audit": ROOT
        / "paper/converter_vsg_pq_decoupling/working/REGF2_successor_route_audit.md",
        "r389_diagnosis": ROOT
        / "paper/converter_vsg_pq_decoupling/working/R389_diagnosis.md",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": base.relative(path), "sha256": base.sha256_file(path)}
        for name, path in sources.items()
    }


def parent_manifest() -> dict[str, dict[str, str]]:
    """Bind the immutable R389 scientific parent and closure artifacts."""

    result_root = ROOT / "results/research_loop/r389_regf2_object_init_gate"
    parents = {
        "r389_claim": ROOT / "memory/claims/CLM-1090.md",
        "r389_feed": ROOT / "paper/converter_vsg_pq_decoupling/reports/R389.md",
        "r389_diagnosis": ROOT
        / "paper/converter_vsg_pq_decoupling/working/R389_diagnosis.md",
        "r389_verdict": ROOT / "memory/rounds/R389/verdict.md",
        "r389_seal": ROOT / "memory/rounds/R389/formal_seal.json",
        "r389_execution": result_root / "formal_execution.json",
        "r389_analysis": result_root / "formal_analysis.json",
        "r389_manifest": result_root / "formal_manifest.json",
    }
    return {
        name: {"path": base.relative(path), "sha256": base.sha256_file(path)}
        for name, path in parents.items()
    }


def validate_r389_parent_chain(contract: Mapping[str, Any]) -> bool:
    """Validate the frozen R389 seal-to-manifest chain, not only snapshots."""

    try:
        result_root = ROOT / "results/research_loop/r389_regf2_object_init_gate"
        paths = {
            "formal_seal": ROOT / "memory/rounds/R389/formal_seal.json",
            "formal_attempt": result_root / "formal_attempt.json",
            "formal_execution": result_root / "formal_execution.json",
            "formal_analysis": result_root / "formal_analysis.json",
            "formal_manifest": result_root / "formal_manifest.json",
        }
        expected = contract["r389_parent_sha256"]
        if set(expected) != set(paths) or any(
            base.sha256_file(path) != expected[name]
            for name, path in paths.items()
        ):
            return False
        seal = base.read_hashed_json(paths["formal_seal"])
        attempt = base.read_hashed_json(paths["formal_attempt"])
        execution = base.read_hashed_json(paths["formal_execution"])
        analysis = base.read_hashed_json(paths["formal_analysis"])
        manifest = base.read_hashed_json(paths["formal_manifest"])
        expected_entries = [
            {
                "path": base.relative(paths[name]),
                "sha256": expected[name],
            }
            for name in ("formal_attempt", "formal_execution", "formal_analysis")
        ]
        return bool(
            seal["round"] == "R389"
            and attempt["round"] == "R389"
            and execution["round"] == "R389"
            and analysis["round"] == "R389"
            and manifest["round"] == "R389"
            and attempt["seal_sha256"] == expected["formal_seal"]
            and execution["seal_sha256"] == expected["formal_seal"]
            and execution["attempt_sha256"] == expected["formal_attempt"]
            and analysis["seal_sha256"] == expected["formal_seal"]
            and analysis["formal_execution_sha256"] == expected["formal_execution"]
            and manifest["entries"] == expected_entries
        )
    except (KeyError, TypeError, ValueError, OSError):
        return False


def installed_runtime() -> dict[str, Any]:
    """Return the R389 runtime identity plus the EIG/PLL/numerics sources."""

    import inspect

    import scipy
    from andes.models.measurement import pll
    from andes.routines import eig as eig_module
    from andes.routines import tds as tds_module
    from andes.system import System
    from andes.variables import dae as dae_module

    runtime = parent.installed_runtime()
    eig_path = Path(eig_module.__file__).resolve()
    pll_path = Path(pll.__file__).resolve()
    system_path = Path(inspect.getsourcefile(System)).resolve()
    tds_path = Path(tds_module.__file__).resolve()
    dae_path = Path(dae_module.__file__).resolve()
    runtime.update(
        {
            "eig_source_path": str(eig_path),
            "eig_source_sha256": base.sha256_file(eig_path),
            "pll2_source_path": str(pll_path),
            "pll2_source_sha256": base.sha256_file(pll_path),
            "numpy_version": str(np.__version__),
            "scipy_version": str(scipy.__version__),
            "system_source_path": str(system_path),
            "system_source_sha256": base.sha256_file(system_path),
            "tds_source_path": str(tds_path),
            "tds_source_sha256": base.sha256_file(tds_path),
            "dae_source_path": str(dae_path),
            "dae_source_sha256": base.sha256_file(dae_path),
        }
    )
    return runtime


def installed_runtime_matches_contract(
    runtime: Mapping[str, Any], contract: Mapping[str, Any]
) -> bool:
    """Fail closed on any case, model, solver, or numerical-library drift."""

    parent_contract = contract["object_contract"]
    expected = {
        "andes_version": parent_contract["andes_version"],
        "xlsx_case_sha256": parent_contract["xlsx_case_sha256"],
        "json_case_sha256": parent_contract["json_case_sha256"],
        "derived_case_sha256": parent_contract["derived_case_sha256"],
        "regf1_model_sha256": parent_contract["regf1_source_sha256"],
        "regf2_model_sha256": parent_contract["regf2_source_sha256"],
        "eig_source_sha256": contract["eig_source_sha256"],
        "pll2_source_sha256": contract["pll2_source_sha256"],
        "numpy_version": contract["numpy_version"],
        "scipy_version": contract["scipy_version"],
        "system_source_sha256": contract["system_source_sha256"],
        "tds_source_sha256": contract["tds_source_sha256"],
        "dae_source_sha256": contract["dae_source_sha256"],
    }
    return all(runtime.get(key) == value for key, value in expected.items())


def setup_only_canary(runtime: Mapping[str, Any]) -> dict[str, Any]:
    """Validate construction and APIs without PFlow, initialization, or EIG."""

    started = time.perf_counter()
    contract = build_regf2_equilibrium_eig_contract()
    parent_contract = contract["object_contract"]
    audit = base.load_verified_static_case(
        xlsx_path=runtime["xlsx_case_path"],
        json_path=runtime["json_case_path"],
    )
    built = parent.build_regf2_static_kundur_object(
        full_case=audit.full_case,
        work_dir=Path.cwd(),
    )
    system = built.system
    system.setup()
    inventory = parent._full_inventory(system, built, parent_contract)
    eig_api_present = bool(
        callable(getattr(system.EIG, "run", None))
        and callable(getattr(system.EIG, "calc_As", None))
    )
    registered_state_api_present = all(
        hasattr(getattr(system, model), variable)
        for model, variables in contract["registered_state_variables"].items()
        for variable in variables
    )
    runtime_api_present = bool(
        callable(getattr(system.PFlow, "run", None))
        and hasattr(system.PFlow, "converged")
        and callable(getattr(system.TDS, "init", None))
        and callable(getattr(system.TDS, "fg_update", None))
        and hasattr(system.TDS.config, "tol")
        and callable(getattr(system, "j_update", None))
        and all(
            hasattr(system.dae, name)
            for name in ("x_name", "y_name", "z_name", "Tf", "x", "y", "z", "f", "g")
        )
        and all(
            hasattr(system.EIG, name)
            for name in (
                "As",
                "mu",
                "x_name",
                "zstate_idx",
                "dead_algeb_idx",
            )
        )
        and all(
            hasattr(system.dae, name)
            for name in (
                "x",
                "y",
                "z",
                "f",
                "g",
                "fx",
                "fy",
                "gx",
                "gy",
                "Tf",
                "x_name",
                "y_name",
            )
        )
    )
    elapsed = time.perf_counter() - started
    return {
        "setup_completed": bool(system.is_setup),
        "derived_case_sha256": built.derived_case_sha256,
        "forbidden_model_counts": inventory["forbidden_model_counts"],
        "forbidden_dae_names": inventory["forbidden_dae_names"],
        "regf2_count": int(system.REGF2.n),
        "pll2_count": int(system.PLL2.n),
        "mapping_ids": [row["idx"] for row in inventory["regf2"]],
        "expected_mapping_ids": [
            row["idx"] for row in parent_contract["expected_mapping"]
        ],
        "input_parameter_cards_match": all(
            row["input_parameter_card"] == parent_contract["parameter_card"]
            for row in inventory["regf2"]
        ),
        "runtime_parameter_cards_match": all(
            row["runtime_parameter_card"]
            == parent_contract["runtime_parameter_card"]
            for row in inventory["regf2"]
        ),
        "pll_buses": [row["bus"] for row in inventory["pll2"]],
        "eig_api_present": eig_api_present,
        "registered_state_api_present": registered_state_api_present,
        "runtime_api_present": runtime_api_present,
        "physical_trajectory_executed": False,
        "setup_only_wall_seconds": elapsed,
    }


def capture_state_bindings(
    system: Any, contract: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Bind registered model variables to the post-reduction EIG name catalog."""

    dae_names = [str(value) for value in system.dae.x_name]
    reduced_names = [str(value) for value in system.EIG.x_name]
    zero_addresses = {int(value) for value in system.EIG.zstate_idx}
    if len(dae_names) != len(set(dae_names)):
        raise RuntimeError("R390 DAE state names are not unique")
    zero_names = [dae_names[address] for address in sorted(zero_addresses)]
    bindings: list[dict[str, Any]] = []
    for model_name, variables in contract["registered_state_variables"].items():
        model = getattr(system, model_name)
        for position, idx in enumerate(model.idx.v):
            for variable_name in variables:
                variable = getattr(model, variable_name)
                address = int(variable.a[position])
                if not 0 <= address < len(dae_names):
                    raise RuntimeError(
                        f"R390 {model_name}.{variable_name} address is out of range"
                    )
                dae_name = dae_names[address]
                matches = [
                    index for index, value in enumerate(reduced_names) if value == dae_name
                ]
                if address in zero_addresses:
                    if matches:
                        raise RuntimeError(
                            f"R390 folded state {dae_name!r} remains in reduced names"
                        )
                    status = "folded"
                    reduced_index = None
                else:
                    if len(matches) == 0:
                        status = "eliminated"
                        reduced_index = None
                    elif len(matches) != 1:
                        raise RuntimeError(
                            f"R390 state name {dae_name!r} has {len(matches)} reduced matches"
                        )
                    else:
                        status = "retained"
                        reduced_index = matches[0]
                bindings.append(
                    {
                        "model": model_name,
                        "idx": str(idx),
                        "variable": variable_name,
                        "dae_name": dae_name,
                        "original_address": address,
                        "status": status,
                        "reduced_index": reduced_index,
                    }
                )
    return bindings, zero_names


def _empty_matrix_record() -> dict[str, Any]:
    return {
        "captured": False,
        "as": [],
        "state_names": [],
        "andes_eigenvalues": [],
        "zero_tf_state_names": [],
        "zero_tf_state_addresses": [],
        "dead_algebraic_indices": [],
        "dae_state_catalog": [],
        "dae_algebraic_names": [],
        "dae_discrete_names": [],
        "eig_augmented_algebraic_names": [],
        "state_bindings": [],
    }


def _empty_equilibrium_snapshot() -> dict[str, Any]:
    return {"captured": False, "before": None, "after": None}


def _empty_arm(
    arm_spec: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any]:
    parent_contract = contract["object_contract"]
    return {
        "name": arm_spec["name"],
        "tds_tolerance": arm_spec["tds_tolerance"],
        "execution_error": None,
        "scientific_error": None,
        "trajectory_attempted": False,
        "physical_trajectory_executed": False,
        "trajectory_count": 0,
        "source": {
            "andes_version": parent_contract["andes_version"],
            "xlsx_json_static_equal": False,
            "derived_case_deterministic": False,
            "xlsx_case_sha256": None,
            "json_case_sha256": None,
            "derived_case_sha256": None,
            "regf1_source_sha256": None,
            "regf2_source_sha256": None,
            "eig_source_sha256": None,
            "pll2_source_sha256": None,
            "numpy_version": None,
            "scipy_version": None,
            "system_source_sha256": None,
            "tds_source_sha256": None,
            "dae_source_sha256": None,
        },
        "inventory": {
            "network": {},
            "forbidden_model_counts": {},
            "forbidden_dae_names": [],
            "regf2": [],
            "pll2": [],
        },
        "references": {
            "phase": None,
            "checked": False,
            "absolute_tolerance": parent_contract["reference_abs_tolerance"],
            "rows": [],
        },
        "initialization_diagnostics": {
            "captured": False,
            "equation_count": 0,
            "bad_combined_indices": [],
            "residual_count": 0,
            "residuals": [],
            "clamped_limits": [],
        },
        "solver": {
            "setup_completed": False,
            "pflow_converged": False,
            "tds_initialized": False,
            "tds_test_ok": False,
            "eig_return": False,
            "system_exit_code": 0,
            "actual_tds_tolerance": arm_spec["tds_tolerance"],
            "time_before_eig": 0.0,
            "time_after_eig": 0.0,
            "state_max_abs_delta": 0.0,
        },
        "finite_guard": {
            "checked": False,
            "dae_finite": False,
            "jacobian_finite": False,
            "state_matrix_finite": False,
        },
        "matrix": _empty_matrix_record(),
        "equilibrium_snapshot": _empty_equilibrium_snapshot(),
    }


def _dense_matrix(value: Any) -> np.ndarray:
    if hasattr(value, "toarray"):
        value = value.toarray()
    return np.asarray(value, dtype=float)


def _finite_status(system: Any, *, state_matrix_finite: bool) -> dict[str, bool]:
    dae_finite, _ = parent.finite_guards(system)
    jacobian_finite = True
    for name in ("fx", "fy", "gx", "gy"):
        try:
            matrix = _dense_matrix(getattr(system.dae, name))
            jacobian_finite = jacobian_finite and bool(np.all(np.isfinite(matrix)))
        except (AttributeError, TypeError, ValueError):
            jacobian_finite = False
    return {
        "checked": True,
        "dae_finite": dae_finite,
        "jacobian_finite": jacobian_finite,
        "state_matrix_finite": state_matrix_finite,
    }


def _source_record(
    runtime: Mapping[str, Any], audit: Any, derived_case_sha256: str
) -> dict[str, Any]:
    return {
        "andes_version": runtime["andes_version"],
        "xlsx_json_static_equal": audit.xlsx_json_static_equal,
        "derived_case_deterministic": derived_case_sha256
        == runtime["derived_case_sha256"],
        "xlsx_case_sha256": audit.xlsx_sha256,
        "json_case_sha256": audit.json_sha256,
        "derived_case_sha256": derived_case_sha256,
        "regf1_source_sha256": runtime["regf1_model_sha256"],
        "regf2_source_sha256": runtime["regf2_model_sha256"],
        "eig_source_sha256": runtime["eig_source_sha256"],
        "pll2_source_sha256": runtime["pll2_source_sha256"],
        "numpy_version": runtime["numpy_version"],
        "scipy_version": runtime["scipy_version"],
        "system_source_sha256": runtime["system_source_sha256"],
        "tds_source_sha256": runtime["tds_source_sha256"],
        "dae_source_sha256": runtime["dae_source_sha256"],
    }


def _max_abs_delta(before: np.ndarray, after: np.ndarray) -> float:
    if before.shape != after.shape:
        raise RuntimeError("R390 EIG changed a DAE vector dimension")
    return 0.0 if before.size == 0 else float(np.max(np.abs(after - before)))


def _dae_catalog(system: Any) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    names = [str(value) for value in system.dae.x_name]
    tf = np.asarray(system.dae.Tf, dtype=float)
    algebraic_names = [str(value) for value in system.dae.y_name]
    discrete_names = [str(value) for value in system.dae.z_name]
    if (
        len(names) != len(tf)
        or len(names) != len(set(names))
        or len(algebraic_names) != len(set(algebraic_names))
        or len(discrete_names) != len(set(discrete_names))
        or not np.all(np.isfinite(tf))
    ):
        raise RuntimeError("R390 DAE state/algebraic catalog is malformed")
    return (
        [
            {"address": index, "name": name, "tf": float(tf[index])}
            for index, name in enumerate(names)
        ],
        algebraic_names,
        discrete_names,
    )


def _equilibrium_row(system: Any) -> dict[str, Any]:
    return {
        "time": float(system.dae.t),
        **{
            name: np.asarray(getattr(system.dae, name), dtype=float).tolist()
            for name in ("x", "y", "z", "f", "g")
        },
    }


def _failed_matrix_record(system: Any) -> dict[str, Any]:
    state_catalog, algebraic_names, discrete_names = _dae_catalog(system)
    zero_addresses = [
        row["address"] for row in state_catalog if float(row["tf"]) == 0.0
    ]
    return {
        **_empty_matrix_record(),
        "zero_tf_state_names": [
            state_catalog[address]["name"] for address in zero_addresses
        ],
        "zero_tf_state_addresses": zero_addresses,
        "dead_algebraic_indices": [
            int(value) for value in getattr(system.EIG, "dead_algeb_idx", [])
        ],
        "dae_state_catalog": state_catalog,
        "dae_algebraic_names": algebraic_names,
        "dae_discrete_names": discrete_names,
        "eig_augmented_algebraic_names": algebraic_names
        + [state_catalog[address]["name"] for address in zero_addresses],
    }


def run_pflow_and_read_converged(system: Any) -> bool:
    """Run PFlow and return its authoritative scalar convergence flag."""

    system.PFlow.run()
    return system.PFlow.converged is True


def _run_arm(
    arm_spec: Mapping[str, Any],
    contract: Mapping[str, Any],
    runtime: Mapping[str, Any],
) -> dict[str, Any]:
    """Run one fresh equilibrium/EIG arm without advancing a trajectory."""

    record = _empty_arm(arm_spec, contract)
    parent_contract = contract["object_contract"]
    system: Any | None = None
    built: Any | None = None
    try:
        audit = base.load_verified_static_case(
            xlsx_path=runtime["xlsx_case_path"],
            json_path=runtime["json_case_path"],
        )
        built = parent.build_regf2_static_kundur_object(
            full_case=audit.full_case,
            work_dir=Path.cwd(),
        )
        system = built.system
        record["source"] = _source_record(runtime, audit, built.derived_case_sha256)
        system.TDS.config.tol = float(arm_spec["tds_tolerance"])
        system.setup()
        record["solver"]["setup_completed"] = bool(system.is_setup)
        record["solver"]["actual_tds_tolerance"] = float(system.TDS.config.tol)
        record["solver"]["system_exit_code"] = int(getattr(system, "exit_code", 0))
        record["inventory"] = parent._full_inventory(
            system, built, parent_contract
        )

        record["solver"]["pflow_converged"] = run_pflow_and_read_converged(system)
        record["solver"]["system_exit_code"] = int(getattr(system, "exit_code", 0))
        if not record["solver"]["pflow_converged"]:
            record["scientific_error"] = "PFlow did not converge"
            record["initialization_diagnostics"] = (
                parent.capture_initialization_diagnostics(
                    system,
                    residual_threshold=float(parent_contract["residual_abs_threshold"]),
                )
            )
            record["finite_guard"] = _finite_status(
                system, state_matrix_finite=False
            )
            return record

        source_rows = parent._source_snapshot(system, parent_contract)
        init_return = system.TDS.init()
        record["solver"]["tds_initialized"] = init_return is not False
        record["solver"]["tds_test_ok"] = system.TDS.test_ok is True
        record["solver"]["actual_tds_tolerance"] = float(system.TDS.config.tol)
        record["solver"]["system_exit_code"] = int(getattr(system, "exit_code", 0))
        record["inventory"] = parent._full_inventory(
            system, built, parent_contract
        )
        record["references"] = parent.post_init_references(
            system, source_rows, parent_contract
        )
        record["initialization_diagnostics"] = (
            parent.capture_initialization_diagnostics(
                system,
                residual_threshold=float(parent_contract["residual_abs_threshold"]),
            )
        )
        if not (
            record["solver"]["tds_initialized"]
            and record["solver"]["tds_test_ok"]
        ):
            record["scientific_error"] = "TDS initialization failed"
            record["finite_guard"] = _finite_status(
                system, state_matrix_finite=False
            )
            return record

        models = system.exist.pflow_tds
        system.TDS.fg_update(models=models)
        system.j_update(models=models, info="R390 fixed equilibrium EIG snapshot")
        record["initialization_diagnostics"] = (
            parent.capture_initialization_diagnostics(
                system,
                residual_threshold=float(parent_contract["residual_abs_threshold"]),
            )
        )
        time_before = float(system.dae.t)
        before = _equilibrium_row(system)
        eig_return = system.EIG.run()
        after = _equilibrium_row(system)
        record["equilibrium_snapshot"] = {
            "captured": True,
            "before": before,
            "after": after,
        }
        record["solver"]["eig_return"] = bool(eig_return)
        record["solver"]["time_before_eig"] = time_before
        record["solver"]["time_after_eig"] = float(system.dae.t)
        record["solver"]["state_max_abs_delta"] = max(
            _max_abs_delta(
                np.asarray(before[name], dtype=float),
                np.asarray(after[name], dtype=float),
            )
            for name in ("x", "y", "z")
        )
        record["solver"]["system_exit_code"] = int(getattr(system, "exit_code", 0))
        if not eig_return:
            record["scientific_error"] = "EIG calculation failed"
            record["matrix"] = _failed_matrix_record(system)
            record["finite_guard"] = _finite_status(
                system, state_matrix_finite=False
            )
            return record

        state_matrix = _dense_matrix(system.EIG.As)
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
            record["matrix"] = _failed_matrix_record(system)
            record["finite_guard"] = _finite_status(
                system, state_matrix_finite=False
            )
            return record
        bindings, zero_names = capture_state_bindings(system, contract)
        state_catalog, algebraic_names, discrete_names = _dae_catalog(system)
        zero_addresses = [
            row["address"] for row in state_catalog if float(row["tf"]) == 0.0
        ]
        if [int(value) for value in system.EIG.zstate_idx] != zero_addresses:
            raise RuntimeError("R390 EIG zero-Tf address catalog mismatch")
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
        record["finite_guard"] = _finite_status(
            system, state_matrix_finite=True
        )
    except Exception as exc:
        record["execution_error"] = f"{type(exc).__name__}: {exc}"
        if system is not None and built is not None:
            try:
                record["inventory"] = parent._full_inventory(
                    system, built, parent_contract
                )
                diagnostics = parent.capture_initialization_diagnostics(
                    system,
                    residual_threshold=float(parent_contract["residual_abs_threshold"]),
                )
                if diagnostics.get("captured") is True:
                    record["initialization_diagnostics"] = diagnostics
                record["finite_guard"] = _finite_status(
                    system, state_matrix_finite=False
                )
            except Exception:
                pass
    return record


def run_formal_record(
    contract: Mapping[str, Any], runtime: Mapping[str, Any]
) -> dict[str, Any]:
    """Execute the exact two ordered equilibrium arms serially."""

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "contract_sha256": base.payload_sha256(contract),
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


def rehearse() -> str:
    """Create setup-only resource/provenance evidence; run no scientific seam."""

    base.assert_wsl_scratch()
    collisions = [
        path for path in (REHEARSAL, CAPACITY, SEAL, DEFAULT_OUT) if path.exists()
    ]
    if collisions:
        raise FileExistsError(f"R390 pre-attempt artifact exists: {collisions}")
    runtime = installed_runtime()
    contract = build_regf2_equilibrium_eig_contract()
    other = base.other_research_python_processes()
    logical, physical, available = base.memory_resources()
    capacity = base.build_capacity_payload(
        logical_processors=logical,
        physical_memory_bytes=physical,
        wsl_memory_available_bytes=available,
        disk_free_bytes=int(base.shutil.disk_usage(ROOT).free),
        competing_processes=other,
    )
    canary = setup_only_canary(runtime)
    sources = source_manifest()
    parents = parent_manifest()
    parent_contract = contract["object_contract"]
    checks = {
        "source_hash": bool(sources),
        "parent_hash": bool(parents),
        "parent_chain": validate_r389_parent_chain(contract),
        "installed_runtime": installed_runtime_matches_contract(runtime, contract),
        "installed_cases": Path(runtime["xlsx_case_path"]).is_file()
        and Path(runtime["json_case_path"]).is_file(),
        "static_table_identity": runtime["xlsx_json_static_equal"] is True,
        "derived_case_determinism": canary["derived_case_sha256"]
        == runtime["derived_case_sha256"],
        "structural_absence": all(
            value == 0 for value in canary["forbidden_model_counts"].values()
        )
        and canary["forbidden_dae_names"] == [],
        "setup_only_canary": canary["setup_completed"] is True
        and canary["regf2_count"] == 4
        and canary["pll2_count"] == 4
        and canary["mapping_ids"] == canary["expected_mapping_ids"]
        and canary["input_parameter_cards_match"] is True
        and canary["runtime_parameter_cards_match"] is True
        and canary["pll_buses"] == [1, 2, 3, 4]
        and canary["eig_api_present"] is True
        and canary["registered_state_api_present"] is True,
        "runtime_api_surface": canary["runtime_api_present"] is True,
        "canonical_object": parent_contract
        == parent.build_regf2_object_init_contract(),
        "native_thread_environment": all(
            os.environ.get(name) == "1"
            for name in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
            )
        ),
        "output_absence": not DEFAULT_OUT.exists() and not SEAL.exists(),
        "question_in_flight": "status: in-flight"
        in QUESTION.read_text(encoding="utf-8"),
        "active_plan": "state: active" in PLAN.read_text(encoding="utf-8")
        and f"manuscript_line: {LINE_ID}" in PLAN.read_text(encoding="utf-8"),
        "no_competing_research_process": not other,
        "physical_trajectory_executed": False,
    }
    if (
        not base.rehearsal_checks({"checks": checks})
        or capacity["readiness"] != "RUN-READY"
    ):
        raise RuntimeError(f"R390 rehearsal/capacity gate did not pass: {checks}")

    r389_execution = base.read_hashed_json(
        ROOT
        / "results/research_loop/r389_regf2_object_init_gate/formal_execution.json"
    )
    prior_wall = float(r389_execution["wall_seconds"])
    capacity.update(
        {
            "installed_runtime": runtime,
            "sources": sources,
            "parents": parents,
            "setup_only_canary": canary,
            "setup_only_wall_seconds": canary["setup_only_wall_seconds"],
            "prior_r389_one_trajectory_wall_seconds": prior_wall,
            "estimated_formal_wall_seconds_upper_bound": 2.0
            * max(prior_wall, float(canary["setup_only_wall_seconds"])),
            "formal_arm_count": 2,
            "formal_worker_count": 1,
            "native_threads_per_process": 1,
        }
    )
    capacity_digest = base.write_new_json(CAPACITY, capacity)
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": base.payload_sha256(contract),
        "sources": sources,
        "parents": parents,
        "installed_runtime": runtime,
        "setup_only_canary": canary,
        "capacity_sha256": capacity_digest,
        "checks": checks,
        "formal_authority": False,
        "training_executed": False,
    }
    return base.write_new_json(REHEARSAL, payload)


def prepare() -> str:
    """Seal R390 after a fresh zero-competing-process measurement."""

    base.assert_posix_runtime()
    rehearsal = base.read_hashed_json(REHEARSAL)
    capacity = base.read_hashed_json(CAPACITY)
    if not base.rehearsal_checks(rehearsal):
        raise RuntimeError("R390 rehearsal did not pass")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R390 capacity gate is not RUN-READY")
    sources = source_manifest()
    parents = parent_manifest()
    runtime = installed_runtime()
    contract = build_regf2_equilibrium_eig_contract()
    if not validate_r389_parent_chain(contract):
        raise RuntimeError("R390 frozen R389 parent chain failed before sealing")
    if rehearsal["sources"] != sources or capacity["sources"] != sources:
        raise RuntimeError("R390 source drift before sealing")
    if rehearsal["parents"] != parents or capacity["parents"] != parents:
        raise RuntimeError("R390 parent drift before sealing")
    if (
        rehearsal["installed_runtime"] != runtime
        or capacity["installed_runtime"] != runtime
        or not installed_runtime_matches_contract(runtime, contract)
    ):
        raise RuntimeError("R390 installed runtime drift before sealing")
    if DEFAULT_OUT.exists() or SEAL.exists():
        raise FileExistsError("R390 seal/formal output collision")
    competing = base.other_research_python_processes()
    process_check = {
        "created_utc": datetime.now(UTC).isoformat(),
        "other_research_python_processes": competing,
        "other_reserved_processes": len(competing),
        "passed": not competing,
    }
    if competing:
        raise RuntimeError(
            "R390 HOLD: competing research processes found immediately before seal"
        )
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_sha256": base.payload_sha256(contract),
        "sources": sources,
        "parents": parents,
        "installed_runtime": runtime,
        "rehearsal_sha256": base.sha256_file(REHEARSAL),
        "capacity_sha256": base.sha256_file(CAPACITY),
        "preseal_process_check": process_check,
        "launch": {
            "host_process_budget": 1,
            "wsl_python_processes": 1,
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
        },
        "formal_artifacts_create_only": True,
        "retry_authorized": False,
        "training_authorized": False,
    }
    return base.write_new_json(SEAL, payload)


def _configure_lifecycle() -> None:
    base.ROUND_ID = ROUND_ID
    base.QUESTION_ID = QUESTION_ID
    base.LINE_ID = LINE_ID
    base.PLAN = PLAN
    base.QUESTION = QUESTION
    base.REHEARSAL = REHEARSAL
    base.CAPACITY = CAPACITY
    base.SEAL = SEAL
    base.DEFAULT_OUT = DEFAULT_OUT
    base.build_clean_contract = build_regf2_equilibrium_eig_contract
    base.classify_regcv1_clean_init_record = classify_regf2_equilibrium_eig_record
    base.source_manifest = source_manifest
    base.parent_manifest = parent_manifest
    base.installed_runtime = installed_runtime
    base.run_formal_record = run_formal_record


_configure_lifecycle()


def execute(*, expected_sha256: str) -> str:
    """Execute through the reused create-only lifecycle at the R390 path."""

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
