"""Run the sealed R393 PPVSM1 two-unit object/stationarity/spectrum gate.

Motivation:
    R392/CLM-1105 stops the stock REGF2 object: coupled positive-real local
    modes plus two conserved integrator directions per device. PPVSM1 is the
    PI-authorized structural redesign (projected-passive dual-droop VSM). This
    gate qualifies the new two-unit object at clean initialization, zero-input
    0.2-second stationarity, and reduced-spectrum guards (no positive-real
    mode, no neutral degeneracy beyond the network common angle). It opens no
    authority, controller, or learning work.

Usage:
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r393_ppvsm1_object_gate.py rehearse
    /home/wya/andes_venv/bin/python scripts/run_r393_ppvsm1_object_gate.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r393_ppvsm1_object_gate.py execute --expected-seal-sha256 <sha256>

Failure modes:
    Provenance, source/card/inventory, diagnostic, trace, seal, runtime, or
    create-only defects are ANALYSIS-INVALID. Init/stationarity/spectrum
    failures are scientific STOPs. No action, retry, controller, or training.
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

from andes_rl_kundur.env.andes.ppvsm1_static_kundur import (  # noqa: E402
    build_ppvsm1_static_kundur_object,
)
from andes_rl_kundur.evaluation.ppvsm1_object_gate import (  # noqa: E402
    TRACE_SIGNALS,
    build_ppvsm1_object_contract,
    classify_ppvsm1_object_record,
    payload_sha256,
)

BASE_RUNNER = ROOT / "scripts/run_r385_regcv1_clean_init_gate.py"
_base_spec = importlib.util.spec_from_file_location("r393_r385_lifecycle", BASE_RUNNER)
if _base_spec is None or _base_spec.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load lifecycle base: {BASE_RUNNER}")
base = importlib.util.module_from_spec(_base_spec)
_base_spec.loader.exec_module(base)

ADAPTER_RUNNER = ROOT / "scripts/run_r391_regf2_equilibrium_eig_correction_gate.py"
_adapter_spec = importlib.util.spec_from_file_location("r393_r391_adapter", ADAPTER_RUNNER)
if _adapter_spec is None or _adapter_spec.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load sparse adapter: {ADAPTER_RUNNER}")
adapter = importlib.util.module_from_spec(_adapter_spec)
_adapter_spec.loader.exec_module(adapter)

_base_installed_runtime = base.installed_runtime

ROUND_ID = "R393"
QUESTION_ID = "Q-0110"
LINE_ID = "converter-vsg-pq-decoupling"
PLAN = ROOT / "memory/rounds/R393/plan.md"
QUESTION = ROOT / "memory/questions/Q-0110.md"
REHEARSAL = ROOT / "memory/rounds/R393/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R393/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R393/formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r393_ppvsm1_object_gate"


def source_manifest() -> dict[str, dict[str, str]]:
    """Hash every prospective implementation and authority input."""

    sources = {
        "runner": Path(__file__).resolve(),
        "lifecycle_base": BASE_RUNNER,
        "sparse_adapter_runner": ADAPTER_RUNNER,
        "model": ROOT / "src/andes_rl_kundur/env/andes/ppvsm1.py",
        "builder": ROOT / "src/andes_rl_kundur/env/andes/ppvsm1_static_kundur.py",
        "builder_base": ROOT
        / "src/andes_rl_kundur/env/andes/regcv1_static_kundur.py",
        "classifier": ROOT
        / "src/andes_rl_kundur/evaluation/ppvsm1_object_gate.py",
        "builder_tests": ROOT / "tests/test_ppvsm1_static_kundur.py",
        "classifier_tests": ROOT / "tests/test_ppvsm1_object_gate.py",
        "runner_tests": ROOT / "tests/test_r393_ppvsm1_object_gate.py",
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
    """Bind the immutable stopping evidence and its closures."""

    parents = {
        "clm1100": ROOT / "memory/claims/CLM-1100.md",
        "clm1105": ROOT / "memory/claims/CLM-1105.md",
        "r391_analysis": ROOT
        / "results/research_loop/r391_regf2_equilibrium_eig_correction_gate/formal_analysis.json",
        "r392_analysis": ROOT
        / "results/research_loop/r392_regf2_loop_perturbation_gate/formal_analysis.json",
        "r391_verdict": ROOT / "memory/rounds/R391/verdict.md",
        "r392_verdict": ROOT / "memory/rounds/R392/verdict.md",
        "r392_feed": ROOT / "paper/converter_vsg_pq_decoupling/reports/R392.md",
        "r391_feed": ROOT / "paper/converter_vsg_pq_decoupling/reports/R391.md",
    }
    return {
        name: {"path": base.relative(path), "sha256": base.sha256_file(path)}
        for name, path in parents.items()
    }


def installed_runtime() -> dict[str, Any]:
    """Bind the R393 runtime identity: case, model sources, EIG, numerics."""

    import inspect

    import scipy
    from andes.routines import eig as eig_module
    from andes.routines import tds as tds_module
    from andes.system import System
    from andes.variables import dae as dae_module

    runtime = _base_installed_runtime()
    model_path = ROOT / "src/andes_rl_kundur/env/andes/ppvsm1.py"
    runtime.update(
        {
            "ppvsm1_model_path": str(model_path),
            "ppvsm1_model_sha256": base.sha256_file(model_path),
            "eig_source_path": str(Path(eig_module.__file__).resolve()),
            "eig_source_sha256": base.sha256_file(Path(eig_module.__file__).resolve()),
            "numpy_version": str(np.__version__),
            "scipy_version": str(scipy.__version__),
            "system_source_path": str(
                Path(inspect.getsourcefile(System)).resolve()
            ),
            "system_source_sha256": base.sha256_file(
                Path(inspect.getsourcefile(System)).resolve()
            ),
            "tds_source_path": str(Path(tds_module.__file__).resolve()),
            "tds_source_sha256": base.sha256_file(Path(tds_module.__file__).resolve()),
            "dae_source_path": str(Path(dae_module.__file__).resolve()),
            "dae_source_sha256": base.sha256_file(Path(dae_module.__file__).resolve()),
        }
    )
    return runtime


def installed_runtime_matches_contract(
    runtime: Mapping[str, Any], contract: Mapping[str, Any]
) -> bool:
    expected = {
        "andes_version": contract["andes_version"],
        "xlsx_case_sha256": contract["xlsx_case_sha256"],
        "json_case_sha256": contract["json_case_sha256"],
        "ppvsm1_model_sha256": runtime["ppvsm1_model_sha256"],
        "eig_source_sha256": runtime["eig_source_sha256"],
        "numpy_version": runtime["numpy_version"],
        "scipy_version": runtime["scipy_version"],
        "system_source_sha256": runtime["system_source_sha256"],
        "tds_source_sha256": runtime["tds_source_sha256"],
        "dae_source_sha256": runtime["dae_source_sha256"],
    }
    return all(runtime.get(key) == value for key, value in expected.items())


def _card_rows(system: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    """Read back input (device-base) and runtime (system-base) cards."""

    card = contract["parameter_card"]
    runtime_card = contract["runtime_parameter_card"]
    input_rows: list[dict[str, Any]] = []
    runtime_rows: list[dict[str, Any]] = []
    for idx in ("PPVSM1_1", "PPVSM1_2"):
        input_row = {"idx": idx}
        runtime_row = {"idx": idx}
        for name in card:
            vin = system.PPVSM1.get(src=name, idx=idx, attr="vin")
            value = system.PPVSM1.get(src=name, idx=idx, attr="v")
            input_row[name] = float(vin if vin is not None else value)
            runtime_row[name] = float(value)
        input_rows.append(input_row)
        runtime_rows.append(runtime_row)
    input_match = all(
        all(row[name] == card[name] for name in card) for row in input_rows
    )
    runtime_match = all(
        all(row[name] == runtime_card[name] for name in card)
        for row in runtime_rows
    )
    return {
        "input_rows": input_rows,
        "runtime_rows": runtime_rows,
        "input_match": input_match,
        "runtime_match": runtime_match,
    }


def _inventory(system: Any, built: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    dynamic = _card_rows(system, contract)
    mapping = [
        {
            "idx": str(idx),
            "bus": int(system.PPVSM1.get(src="bus", idx=idx, attr="v")),
            "gen": int(system.PPVSM1.get(src="gen", idx=idx, attr="v")),
        }
        for idx in ("PPVSM1_1", "PPVSM1_2")
    ]
    return {
        "network": built.network_inventory,
        "forbidden_model_counts": base.forbidden_model_counts(
            system, contract["forbidden_models"]
        ),
        "forbidden_dae_names": base.forbidden_dae_names(
            system, contract["forbidden_models"]
        ),
        "ppvsm1_count": int(system.PPVSM1.n),
        "ppvsm1_buses": [row["bus"] for row in mapping],
        "ppvsm1_mapping_ok": mapping == [
            {"idx": row["idx"], "bus": row["bus"], "gen": row["gen"]}
            for row in contract["expected_mapping"]
        ],
        "input_parameter_cards_match": dynamic["input_match"],
        "runtime_parameter_cards_match": dynamic["runtime_match"],
    }


def _source_snapshot(system: Any, contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in contract["expected_mapping"]:
        idx = row["idx"]
        static_p = float(system.StaticGen.get(src="p", idx=row["gen"], attr="v"))
        static_q = float(system.StaticGen.get(src="q", idx=row["gen"], attr="v"))
        pref = float(system.PPVSM1.get(src="Pref", idx=idx, attr="v"))
        qref = float(system.PPVSM1.get(src="Qref", idx=idx, attr="v"))
        rows.append(
            {
                "idx": idx,
                "static_p": static_p,
                "static_q": static_q,
                "pref": pref,
                "qref": qref,
                "abs_deviation": max(abs(pref - static_p), abs(qref - static_q)),
            }
        )
    return rows


def _dense_state_matrix(system: Any) -> np.ndarray:
    matrix = adapter.dense_andes_matrix(system.EIG.As)
    if (
        matrix.ndim != 2
        or matrix.shape[0] != matrix.shape[1]
        or matrix.size == 0
        or not np.all(np.isfinite(matrix))
    ):
        raise RuntimeError("R393 reduced state matrix is not finite and square")
    return matrix


def _finite_status(system: Any, *, state_matrix_finite: bool) -> dict[str, bool]:
    dae_finite, _ = base.finite_guards(system)
    jacobian_finite = True
    for name in ("fx", "fy", "gx", "gy"):
        try:
            adapter.dense_andes_matrix(getattr(system.dae, name))
        except (AttributeError, TypeError, ValueError):
            jacobian_finite = False
    return {
        "checked": True,
        "dae_finite": dae_finite,
        "jacobian_finite": jacobian_finite,
        "state_matrix_finite": state_matrix_finite,
    }


def _matrix_by_identity(
    matrix: np.ndarray, addresses: list[int], labels: list[str], mask: np.ndarray
) -> dict[str, list[float]]:
    if matrix.ndim != 2 or matrix.shape[0] != len(mask):
        raise RuntimeError("R393 stored trajectory matrix is incomplete")
    if len(addresses) != len(labels):
        raise RuntimeError("R393 trajectory address/identity mismatch")
    return {
        label: [float(value) for value in matrix[mask, address]]
        for label, address in zip(labels, addresses, strict=True)
    }


def _capture_trace(system: Any, initial: Mapping[str, Any]) -> dict[str, Any]:
    system.dae.ts.unpack(attr="t", warn_empty=False)
    system.dae.ts.unpack(attr="x", warn_empty=False)
    system.dae.ts.unpack(attr="y", warn_empty=False)
    native_t = np.asarray(system.dae.ts.t, dtype=float)
    x_values = np.asarray(system.dae.ts.x, dtype=float)
    y_values = np.asarray(system.dae.ts.y, dtype=float)
    start = float(initial["time"])
    mask = native_t > start + 1.0e-12
    times = native_t[mask]
    if times.ndim != 1 or len(times) < 1 or not np.all(np.diff(times) > 0):
        raise RuntimeError("R393 stored post-start time grid is incomplete")

    bus_ids = [str(value) for value in system.Bus.idx.v]
    bus_native = _matrix_by_identity(
        y_values, [int(value) for value in system.Bus.v.a], bus_ids, mask
    )
    bus_samples = [dict(initial["bus_v"])]
    for position in range(len(times)):
        bus_samples.append(
            {bus: values[position] for bus, values in bus_native.items()}
        )

    device_ids = [str(value) for value in system.PPVSM1.idx.v]
    variables = {
        "Pe": system.PPVSM1.Pe,
        "Qe": system.PPVSM1.Qe,
        "Id": system.PPVSM1.Id,
        "Iq": system.PPVSM1.Iq,
        "virtual_frequency": system.PPVSM1.INTw_y,
    }
    devices = {device_id: {} for device_id in device_ids}
    for signal in TRACE_SIGNALS:
        variable = variables[signal]
        matrix = x_values if variable.v_code == "x" else y_values
        native = _matrix_by_identity(
            matrix, [int(value) for value in variable.a], device_ids, mask
        )
        for device_id in device_ids:
            devices[device_id][signal] = [
                float(initial["devices"][signal][device_id]),
                *native[device_id],
            ]
    return {
        "checked": True,
        "times": [start, *[float(value) for value in times]],
        "bus_v": bus_samples,
        "devices": devices,
    }


def _initial_trace_row(system: Any) -> dict[str, Any]:
    bus_v = {
        str(bus): float(system.Bus.get(src="v", idx=bus, attr="v"))
        for bus in system.Bus.idx.v
    }
    devices: dict[str, dict[str, float]] = {}
    for idx in ("PPVSM1_1", "PPVSM1_2"):
        devices[idx] = {
            "Pe": float(system.PPVSM1.get(src="Pe", idx=idx, attr="v")),
            "Qe": float(system.PPVSM1.get(src="Qe", idx=idx, attr="v")),
            "Id": float(system.PPVSM1.get(src="Id", idx=idx, attr="v")),
            "Iq": float(system.PPVSM1.get(src="Iq", idx=idx, attr="v")),
            "virtual_frequency": float(
                system.PPVSM1.get(src="INTw_y", idx=idx, attr="v")
            ),
        }
    return {"time": float(system.dae.t), "bus_v": bus_v, "devices": devices}


def _empty_record(contract_sha256: str) -> dict[str, Any]:
    contract = build_ppvsm1_object_contract()
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "contract_sha256": contract_sha256,
        "formal_input_complete": True,
        "execution_error": None,
        "scientific_error": None,
        "training_executed": False,
        "post_init_action_executed": False,
        "trajectory_attempted": False,
        "physical_trajectory_executed": False,
        "trajectory_count": 0,
        "source": {
            "andes_version": contract["andes_version"],
            "xlsx_case_sha256": None,
            "json_case_sha256": None,
            "derived_case_sha256": None,
            "ppvsm1_model_sha256": None,
            "eig_source_sha256": None,
        },
        "inventory": {
            "network": {},
            "forbidden_model_counts": {},
            "forbidden_dae_names": [],
            "ppvsm1_count": 0,
            "ppvsm1_buses": [],
            "ppvsm1_mapping_ok": False,
            "input_parameter_cards_match": False,
            "runtime_parameter_cards_match": False,
        },
        "references": {"checked": False, "phase": None, "rows": []},
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
            "tds_converged": False,
            "terminal_time_seconds": 0.0,
            "tds_tolerance": contract["tds_tolerance"],
            "time_before_eig": 0.0,
            "time_after_eig": 0.0,
            "state_max_abs_delta": 0.0,
        },
        "trace": {"checked": False, "times": [], "bus_v": [], "devices": {}},
        "finite_guard": {
            "checked": False,
            "dae_finite": False,
            "jacobian_finite": False,
            "state_matrix_finite": False,
        },
        "spectrum": {
            "captured": False,
            "state_count": 0,
            "eigenvalues": [],
        },
    }


def _run_arm(
    contract: Mapping[str, Any], runtime: Mapping[str, Any]
) -> dict[str, Any]:
    record = _empty_record(payload_sha256(contract))
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
        system.setup()
        record["solver"]["setup_completed"] = bool(system.is_setup)
        record["inventory"] = _inventory(system, built, contract)

        system.PFlow.run()
        record["solver"]["pflow_converged"] = system.PFlow.converged is True
        if not record["solver"]["pflow_converged"]:
            record["scientific_error"] = "PFlow did not converge"
            record["initialization_diagnostics"] = (
                base.capture_initialization_diagnostics(system)
            )
            return record

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
            "rows": _source_snapshot(system, contract),
        }
        if not (
            record["solver"]["tds_initialized"]
            and record["solver"]["tds_test_ok"]
        ):
            record["scientific_error"] = "TDS initialization failed"
            record["finite_guard"] = _finite_status(system, state_matrix_finite=False)
            return record

        models = system.exist.pflow_tds
        system.TDS.fg_update(models=models)
        system.j_update(models=models, info="R393 fixed equilibrium EIG snapshot")
        time_before = float(system.dae.t)
        eig_return = system.EIG.run()
        record["solver"]["eig_return"] = bool(eig_return)
        record["solver"]["time_before_eig"] = time_before
        record["solver"]["time_after_eig"] = float(system.dae.t)
        if not eig_return:
            record["scientific_error"] = "EIG calculation failed"
            record["finite_guard"] = _finite_status(system, state_matrix_finite=False)
            return record
        state_matrix = _dense_state_matrix(system)
        eigenvalues = np.asarray(system.EIG.mu, dtype=complex)
        if not np.all(np.isfinite(eigenvalues.real)) or not np.all(
            np.isfinite(eigenvalues.imag)
        ):
            raise RuntimeError("R393 spectrum is not finite")
        record["spectrum"] = {
            "captured": True,
            "state_count": int(state_matrix.shape[0]),
            "eigenvalues": [
                {"real": float(value.real), "imag": float(value.imag)}
                for value in eigenvalues
            ],
        }
        record["finite_guard"] = _finite_status(system, state_matrix_finite=True)

        initial = _initial_trace_row(system)
        system.TDS.run()
        record["trajectory_attempted"] = True
        record["physical_trajectory_executed"] = True
        record["trajectory_count"] = 1
        record["solver"]["tds_converged"] = system.TDS.converged is True
        record["solver"]["terminal_time_seconds"] = float(system.dae.t)
        record["trace"] = _capture_trace(system, initial)
        record["finite_guard"] = _finite_status(system, state_matrix_finite=True)
    except Exception as exc:
        record["execution_error"] = f"{type(exc).__name__}: {exc}"
        if system is not None:
            try:
                record["finite_guard"] = _finite_status(
                    system, state_matrix_finite=False
                )
            except Exception:
                pass
    return record


def run_formal_record(
    contract: Mapping[str, Any], runtime: Mapping[str, Any]
) -> dict[str, Any]:
    """Execute the exact single serial arm."""

    return _run_arm(contract, runtime)


def setup_only_canary(runtime: Mapping[str, Any]) -> dict[str, Any]:
    """Validate construction and APIs without PFlow, initialization, or EIG."""

    started = time.perf_counter()
    contract = build_ppvsm1_object_contract()
    audit = base.load_verified_static_case(
        xlsx_path=runtime["xlsx_case_path"],
        json_path=runtime["json_case_path"],
    )
    built = build_ppvsm1_static_kundur_object(
        full_case=audit.full_case, work_dir=Path.cwd()
    )
    system = built.system
    system.setup()
    inventory = _inventory(system, built, contract)
    eig_api_present = bool(
        callable(getattr(system.EIG, "run", None))
        and callable(getattr(system.EIG, "calc_As", None))
    )
    runtime_api_present = bool(
        callable(getattr(system.PFlow, "run", None))
        and hasattr(system.PFlow, "converged")
        and callable(getattr(system.TDS, "init", None))
        and callable(getattr(system.TDS, "fg_update", None))
        and hasattr(system.TDS.config, "tol")
        and callable(getattr(system, "j_update", None))
    )
    elapsed = time.perf_counter() - started
    return {
        "setup_completed": bool(system.is_setup),
        "derived_case_sha256": built.derived_case_sha256,
        "forbidden_model_counts": inventory["forbidden_model_counts"],
        "forbidden_dae_names": inventory["forbidden_dae_names"],
        "ppvsm1_count": inventory["ppvsm1_count"],
        "ppvsm1_buses": inventory["ppvsm1_buses"],
        "ppvsm1_mapping_ok": inventory["ppvsm1_mapping_ok"],
        "input_parameter_cards_match": inventory["input_parameter_cards_match"],
        "runtime_parameter_cards_match": inventory["runtime_parameter_cards_match"],
        "eig_api_present": eig_api_present,
        "runtime_api_present": runtime_api_present,
        "sparse_adapter_present": adapter.sparse_adapter_canary(),
        "physical_trajectory_executed": False,
        "setup_only_wall_seconds": elapsed,
    }


def rehearse() -> str:
    """Create setup-only resource/provenance evidence; no scientific seam."""

    base.assert_wsl_scratch()
    collisions = [
        path for path in (REHEARSAL, CAPACITY, SEAL, DEFAULT_OUT) if path.exists()
    ]
    if collisions:
        raise FileExistsError(f"R393 pre-attempt artifact exists: {collisions}")
    runtime = installed_runtime()
    contract = build_ppvsm1_object_contract()
    other = base.other_research_python_processes()
    logical, physical, available = base.memory_resources()
    capacity = base.build_capacity_payload(
        logical_processors=logical,
        physical_memory_bytes=physical,
        wsl_memory_available_bytes=available,
        disk_free_bytes=int(base.shutil.disk_usage(ROOT).free),
        competing_processes=other,
    )
    capacity["empirical_anchor"] = {
        "concurrent_workers": 1,
        "all_records_valid": True,
        "native_threads_per_worker": 1,
        "source": "r393_rehearsal_setup_only_canary",
    }
    capacity["capacity_canary"] = {"accepted": True, "accepted_worker_budget": 1}
    canary = setup_only_canary(runtime)
    sources = source_manifest()
    parents = parent_manifest()
    checks = {
        "source_hash": bool(sources),
        "parent_hash": bool(parents),
        "parent_stop_evidence": bool(
            parents["r391_analysis"]["sha256"]
            == "170658c967798aced2f4b62b614dd2863d2a8445ea4e92fbc2ac05968731619e"
            and parents["r392_analysis"]["sha256"]
            == "e05da2d17c19d8d02012e4b8b1fc9d48b2ccb26d1af195bf9c3799fb7cb3ec8b"
        ),
        "installed_runtime": installed_runtime_matches_contract(runtime, contract),
        "installed_cases": Path(runtime["xlsx_case_path"]).is_file()
        and Path(runtime["json_case_path"]).is_file(),
        "derived_case_determinism": canary["derived_case_sha256"]
        == "b33a134a368ee8e5829a956c35355370b2af66eb52bab5974ac83a965309e983",
        "structural_absence": all(
            value == 0 for value in canary["forbidden_model_counts"].values()
        )
        and canary["forbidden_dae_names"] == [],
        "setup_only_canary": canary["setup_completed"] is True
        and canary["ppvsm1_count"] == 2
        and canary["ppvsm1_buses"] == [1, 2]
        and canary["ppvsm1_mapping_ok"] is True
        and canary["input_parameter_cards_match"] is True
        and canary["runtime_parameter_cards_match"] is True
        and canary["eig_api_present"] is True
        and canary["sparse_adapter_present"] is True,
        "runtime_api_surface": canary["runtime_api_present"] is True,
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
        raise RuntimeError(f"R393 rehearsal/capacity gate did not pass: {checks}")

    capacity.update(
        {
            "installed_runtime": runtime,
            "sources": sources,
            "parents": parents,
            "setup_only_canary": canary,
            "setup_only_wall_seconds": canary["setup_only_wall_seconds"],
            "estimated_formal_wall_seconds_upper_bound": 4.0
            * float(canary["setup_only_wall_seconds"]),
            "formal_arm_count": 1,
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
        "contract_sha256": payload_sha256(contract),
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
    """Seal R393 after a fresh zero-competing-process measurement."""

    base.assert_posix_runtime()
    rehearsal = base.read_hashed_json(REHEARSAL)
    capacity = base.read_hashed_json(CAPACITY)
    if not base.rehearsal_checks(rehearsal):
        raise RuntimeError("R393 rehearsal did not pass")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R393 capacity gate is not RUN-READY")
    sources = source_manifest()
    parents = parent_manifest()
    runtime = installed_runtime()
    contract = build_ppvsm1_object_contract()
    if rehearsal["sources"] != sources or capacity["sources"] != sources:
        raise RuntimeError("R393 source drift before sealing")
    if rehearsal["parents"] != parents or capacity["parents"] != parents:
        raise RuntimeError("R393 parent drift before sealing")
    if (
        rehearsal["installed_runtime"] != runtime
        or capacity["installed_runtime"] != runtime
        or not installed_runtime_matches_contract(runtime, contract)
    ):
        raise RuntimeError("R393 installed runtime drift before sealing")
    if DEFAULT_OUT.exists() or SEAL.exists():
        raise FileExistsError("R393 seal/formal output collision")
    competing = base.other_research_python_processes()
    process_check = {
        "created_utc": datetime.now(UTC).isoformat(),
        "other_research_python_processes": competing,
        "other_reserved_processes": len(competing),
        "passed": not competing,
    }
    if competing:
        raise RuntimeError(
            "R393 HOLD: competing research processes found immediately before seal"
        )
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_sha256": payload_sha256(contract),
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
    base.build_clean_contract = build_ppvsm1_object_contract
    base.classify_regcv1_clean_init_record = classify_ppvsm1_object_record
    base.source_manifest = source_manifest
    base.parent_manifest = parent_manifest
    base.installed_runtime = installed_runtime
    base.run_formal_record = run_formal_record


_configure_lifecycle()


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
