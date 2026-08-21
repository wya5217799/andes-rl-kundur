"""Run the sealed R389 stock-REGF2 object and clean-initialization gate.

Motivation:
    R388 stops the exact REGCV1/card/port formulation. R389 begins a materially
    different stock REGF2 VSM route at the upstream object/init boundary while
    preserving ANDES 2.0.0 and the unchanged Kundur static network.

Usage:
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r389_regf2_object_init_gate.py rehearse
    /home/wya/andes_venv/bin/python \
        scripts/run_r389_regf2_object_init_gate.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r389_regf2_object_init_gate.py execute \
        --expected-seal-sha256 <sha256>

Failure modes:
    Provenance, source/card/inventory, diagnostic, trace, seal, runtime, or
    create-only defects are ANALYSIS-INVALID. A complete native solver,
    residual, finite, electrical, or drift failure is scientific STOP. There
    is no action, retry, tuning, controller, disturbance, or training command.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
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

from andes_rl_kundur.env.andes.regf2_static_kundur import (  # noqa: E402
    build_regf2_static_kundur_object,
)
from andes_rl_kundur.evaluation.regf2_object_init_gate import (  # noqa: E402
    TRACE_SIGNALS,
    build_regf2_object_init_contract,
    classify_regf2_object_init_record,
)


BASE_RUNNER = ROOT / "scripts/run_r385_regcv1_clean_init_gate.py"
_base_spec = importlib.util.spec_from_file_location("r389_r385_lifecycle", BASE_RUNNER)
if _base_spec is None or _base_spec.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load lifecycle base: {BASE_RUNNER}")
base = importlib.util.module_from_spec(_base_spec)
_base_spec.loader.exec_module(base)

ROUND_ID = "R389"
QUESTION_ID = "Q-0107"
LINE_ID = "converter-vsg-pq-decoupling"
PLAN = ROOT / "memory/rounds/R389/plan.md"
QUESTION = ROOT / "memory/questions/Q-0107.md"
REHEARSAL = ROOT / "memory/rounds/R389/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R389/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R389/formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r389_regf2_object_init_gate"


def source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "lifecycle_base": BASE_RUNNER,
        "builder": ROOT / "src/andes_rl_kundur/env/andes/regf2_static_kundur.py",
        "builder_base": ROOT / "src/andes_rl_kundur/env/andes/regcv1_static_kundur.py",
        "classifier": ROOT / "src/andes_rl_kundur/evaluation/regf2_object_init_gate.py",
        "builder_tests": ROOT / "tests/test_regf2_static_kundur.py",
        "classifier_tests": ROOT / "tests/test_regf2_object_init_gate.py",
        "runner_tests": ROOT / "tests/test_r389_regf2_object_init_gate.py",
        "plan": PLAN,
        "question": QUESTION,
        "programme": ROOT / "memory/RESEARCH_PROGRAM.md",
        "line": ROOT / "paper/converter_vsg_pq_decoupling/LINE.md",
        "route_contract": ROOT / "paper/converter_vsg_pq_decoupling/working/route_contract.md",
        "artifact_manifest": ROOT / "paper/converter_vsg_pq_decoupling/ARTIFACTS.json",
        "route_audit": ROOT / "paper/converter_vsg_pq_decoupling/working/REGF2_successor_route_audit.md",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": base.relative(path), "sha256": base.sha256_file(path)}
        for name, path in sources.items()
    }


def parent_manifest() -> dict[str, dict[str, str]]:
    parents = {
        "r388_claim": ROOT / "memory/claims/CLM-1085.md",
        "r388_feed": ROOT / "paper/converter_vsg_pq_decoupling/reports/R388.md",
        "r388_verdict": ROOT / "memory/rounds/R388/verdict.md",
        "r388_seal": ROOT / "memory/rounds/R388/formal_seal.json",
        "r388_analysis": ROOT / "results/research_loop/r388_regcv1_signed_authority_correction_gate/formal_analysis.json",
        "r388_manifest": ROOT / "results/research_loop/r388_regcv1_signed_authority_correction_gate/formal_manifest.json",
        "r386_execution": ROOT / "results/research_loop/r386_regcv1_reference_capture_gate/formal_execution.json",
    }
    return {
        name: {"path": base.relative(path), "sha256": base.sha256_file(path)}
        for name, path in parents.items()
    }


def installed_runtime() -> dict[str, Any]:
    import andes
    from andes.models.renewable import regf1, regf2

    xlsx_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    json_path = xlsx_path.with_suffix(".json")
    audit = base.load_verified_static_case(xlsx_path=xlsx_path, json_path=json_path)
    derived = base.render_static_case_bytes(audit.full_case)
    regf1_path = Path(regf1.__file__).resolve()
    regf2_path = Path(regf2.__file__).resolve()
    return {
        "python": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "andes_module": str(Path(andes.__file__).resolve()),
        "regf1_model_path": str(regf1_path),
        "regf1_model_sha256": base.sha256_file(regf1_path),
        "regf2_model_path": str(regf2_path),
        "regf2_model_sha256": base.sha256_file(regf2_path),
        "xlsx_case_path": str(xlsx_path),
        "xlsx_case_sha256": audit.xlsx_sha256,
        "json_case_path": str(json_path),
        "json_case_sha256": audit.json_sha256,
        "xlsx_json_static_equal": audit.xlsx_json_static_equal,
        "derived_case_sha256": base.hashlib.sha256(derived).hexdigest(),
    }


def installed_case_hashes_match(
    runtime: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> bool:
    return all(
        runtime.get(key) == contract.get(key)
        for key in (
            "xlsx_case_sha256",
            "json_case_sha256",
            "derived_case_sha256",
        )
    )


def regf2_and_pll_inventory(
    system: Any,
    *,
    bindings: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    contract = build_regf2_object_init_contract()
    model = system.REGF2
    link = getattr(model, "pllidx", model.pll)
    input_by_idx = {str(row["idx"]): row for row in bindings}
    regf2_rows: list[dict[str, Any]] = []
    for position, idx in enumerate(model.idx.v):
        runtime_card = {
            key: (
                None
                if key == "pll"
                else float(getattr(model, key).v[position])
            )
            for key in contract["parameter_card"]
        }
        binding = input_by_idx[str(idx)]
        input_card = {
            key: None if key == "pll" else float(binding[key])
            for key in contract["parameter_card"]
        }
        regf2_rows.append(
            {
                "idx": str(idx),
                "bus": int(model.bus.v[position]),
                "gen": int(model.gen.v[position]),
                "Sn": float(model.Sn.v[position]),
                "u": int(model.u.v[position]),
                "input_parameter_card": input_card,
                "runtime_parameter_card": runtime_card,
                "pll": str(link.v[position]),
            }
        )
    pll = system.PLL2
    pll_rows = [
        {
            "idx": str(idx),
            "bus": int(pll.bus.v[position]),
            "u": int(pll.u.v[position]),
        }
        for position, idx in enumerate(pll.idx.v)
    ]
    return {"regf2": regf2_rows, "pll2": pll_rows}


def finite_guards(system: Any) -> tuple[bool, bool]:
    dae_finite = True
    for name in ("x", "y", "z", "f", "g"):
        try:
            values = np.asarray(getattr(system.dae, name), dtype=float)
            dae_finite = dae_finite and bool(np.all(np.isfinite(values)))
        except (AttributeError, TypeError, ValueError):
            dae_finite = False
    model_finite = True
    for variable in system.REGF2.cache.all_vars.values():
        try:
            values = np.asarray(variable.v, dtype=float)
            model_finite = model_finite and bool(np.all(np.isfinite(values)))
        except (AttributeError, TypeError, ValueError):
            model_finite = False
    return dae_finite, model_finite


def capture_initialization_diagnostics(
    system: Any,
    *,
    residual_threshold: float,
) -> dict[str, Any]:
    """Capture all residuals at the registered R389 threshold."""

    result = {
        "captured": False,
        "equation_count": 0,
        "bad_combined_indices": [],
        "residual_count": 0,
        "residuals": [],
        "clamped_limits": [],
    }
    try:
        fg = np.asarray(system.dae.fg, dtype=float)
        bad = np.flatnonzero(
            (np.abs(fg) >= float(residual_threshold)) | ~np.isfinite(fg)
        )
        n_state = int(system.dae.n)
        rows: list[dict[str, Any]] = []
        for combined_index in bad:
            numeric_index = int(combined_index)
            is_state = numeric_index < n_state
            local_address = numeric_index if is_state else numeric_index - n_state
            mapping = system.dae.x_map if is_state else system.dae.y_map
            entry = mapping.get(local_address)
            variable = entry[1] if entry else None
            owner = getattr(variable, "owner", None)
            device_idx = None
            addresses = np.asarray(getattr(variable, "a", []), dtype=int)
            positions = np.flatnonzero(addresses == local_address)
            if owner is not None and len(positions) == 1 and hasattr(owner, "idx"):
                device_idx = base._json_value(owner.idx.v[int(positions[0])])
            rows.append(
                {
                    "combined_index": numeric_index,
                    "name": str(system.dae.xy_name[numeric_index]),
                    "residual": base._json_value(float(fg[numeric_index])),
                    "equation": str(getattr(variable, "e_str", "") or ""),
                    "model": str(getattr(owner, "class_name", "") or ""),
                    "idx": device_idx,
                }
            )
        limits: list[dict[str, Any]] = []
        for model in system.exist.pflow_tds.values():
            for discrete in model.discrete.values():
                limits.extend(base._json_value(discrete.get_limit_report()))
        result.update(
            captured=True,
            equation_count=int(fg.size),
            bad_combined_indices=[int(value) for value in bad],
            residual_count=len(rows),
            residuals=rows,
            clamped_limits=limits,
        )
    except Exception as exc:
        result["capture_error"] = f"{type(exc).__name__}: {exc}"
    return result


def _source_snapshot(system: Any, contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    idxes = [row["gen"] for row in contract["expected_mapping"]]
    static_p = system.StaticGen.get(src="p", idx=idxes, attr="v")
    static_q = system.StaticGen.get(src="q", idx=idxes, attr="v")
    return [
        {
            "idx": str(expected["idx"]),
            "static_p": float(static_p[position]),
            "static_q": float(static_q[position]),
        }
        for position, expected in enumerate(contract["expected_mapping"])
    ]


def post_init_references(
    system: Any,
    source_rows: list[dict[str, Any]],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    tolerance = float(contract["reference_abs_tolerance"])
    rows: list[dict[str, Any]] = []
    for position, source in enumerate(source_rows):
        pref = float(system.REGF2.Pref.v[position])
        qref = float(system.REGF2.Qref.v[position])
        static_p = float(source["static_p"])
        static_q = float(source["static_q"])
        rows.append(
            {
                **source,
                "pref": pref,
                "qref": qref,
                "pref_match": math.isclose(pref, static_p, rel_tol=0.0, abs_tol=tolerance),
                "qref_match": math.isclose(qref, static_q, rel_tol=0.0, abs_tol=tolerance),
            }
        )
    return {
        "phase": "post-pflow-pre-init-to-post-init",
        "checked": True,
        "absolute_tolerance": tolerance,
        "rows": rows,
    }


def _signal_values(system: Any) -> dict[str, dict[str, float]]:
    idxes = [str(value) for value in system.REGF2.idx.v]
    result: dict[str, dict[str, float]] = {}
    variables = {
        "Pe": system.REGF2.Pe,
        "Qe": system.REGF2.Qe,
        "Id": system.REGF2.Id,
        "Iq": system.REGF2.Iq,
        "virtual_frequency": system.REGF2.INTw_y,
    }
    for name, variable in variables.items():
        values = [float(value) for value in np.asarray(variable.v, dtype=float)]
        if len(values) != len(idxes):
            raise RuntimeError(f"R389 initial {name} identity/value mismatch")
        result[name] = dict(zip(idxes, values, strict=True))
    return result


def capture_initial_snapshot(system: Any) -> dict[str, Any]:
    buses = [str(value) for value in system.Bus.idx.v]
    bus_values = [float(value) for value in np.asarray(system.Bus.v.v, dtype=float)]
    if len(buses) != len(bus_values):
        raise RuntimeError("R389 initial bus identity/value mismatch")
    return {
        "time": float(system.dae.t),
        "bus_v": dict(zip(buses, bus_values, strict=True)),
        "devices": _signal_values(system),
    }


def _matrix_by_identity(
    matrix: np.ndarray,
    addresses: list[int],
    labels: list[str],
    mask: np.ndarray,
) -> dict[str, list[float]]:
    if matrix.ndim != 2 or matrix.shape[0] != len(mask):
        raise RuntimeError("R389 stored trajectory matrix is incomplete")
    if len(addresses) != len(labels):
        raise RuntimeError("R389 trajectory address/identity mismatch")
    return {
        label: [float(value) for value in matrix[mask, address]]
        for label, address in zip(labels, addresses, strict=True)
    }


def capture_trace(system: Any, initial: Mapping[str, Any]) -> dict[str, Any]:
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
        raise RuntimeError("R389 stored post-start time grid is incomplete")

    bus_ids = [str(value) for value in system.Bus.idx.v]
    bus_native = _matrix_by_identity(
        y_values,
        [int(value) for value in system.Bus.v.a],
        bus_ids,
        mask,
    )
    bus_samples = [dict(initial["bus_v"])]
    for position in range(len(times)):
        bus_samples.append({bus: values[position] for bus, values in bus_native.items()})

    device_ids = [str(value) for value in system.REGF2.idx.v]
    variables = {
        "Pe": system.REGF2.Pe,
        "Qe": system.REGF2.Qe,
        "Id": system.REGF2.Id,
        "Iq": system.REGF2.Iq,
        "virtual_frequency": system.REGF2.INTw_y,
    }
    devices = {device_id: {} for device_id in device_ids}
    for signal in TRACE_SIGNALS:
        variable = variables[signal]
        matrix = x_values if variable.v_code == "x" else y_values
        native = _matrix_by_identity(
            matrix,
            [int(value) for value in variable.a],
            device_ids,
            mask,
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


def _empty_record(contract_sha256: str) -> dict[str, Any]:
    contract = build_regf2_object_init_contract()
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
            "xlsx_json_static_equal": True,
            "derived_case_deterministic": True,
            "xlsx_case_sha256": None,
            "json_case_sha256": None,
            "derived_case_sha256": None,
            "regf1_source_sha256": None,
            "regf2_source_sha256": None,
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
            "absolute_tolerance": contract["reference_abs_tolerance"],
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
            "tds_converged": False,
            "terminal_time_seconds": 0.0,
            "tds_tolerance": contract["tds_tolerance"],
        },
        "trace": {"checked": False, "times": [], "bus_v": [], "devices": {}},
        "finite_guard": {
            "checked": False,
            "dae_finite": False,
            "regf2_finite": False,
        },
    }


def _full_inventory(system: Any, built: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    dynamic = regf2_and_pll_inventory(system, bindings=built.bindings)
    return {
        "network": built.network_inventory,
        "forbidden_model_counts": base.forbidden_model_counts(
            system, contract["forbidden_models"]
        ),
        "forbidden_dae_names": base.forbidden_dae_names(
            system, contract["forbidden_models"]
        ),
        **dynamic,
    }


def setup_only_canary(runtime: Mapping[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    contract = build_regf2_object_init_contract()
    audit = base.load_verified_static_case(
        xlsx_path=runtime["xlsx_case_path"],
        json_path=runtime["json_case_path"],
    )
    built = build_regf2_static_kundur_object(
        full_case=audit.full_case,
        work_dir=Path.cwd(),
    )
    built.system.setup()
    inventory = _full_inventory(built.system, built, contract)
    elapsed = time.perf_counter() - started
    expected_ids = [row["idx"] for row in contract["expected_mapping"]]
    return {
        "setup_completed": bool(built.system.is_setup),
        "derived_case_sha256": built.derived_case_sha256,
        "forbidden_model_counts": inventory["forbidden_model_counts"],
        "forbidden_dae_names": inventory["forbidden_dae_names"],
        "regf2_count": int(built.system.REGF2.n),
        "pll2_count": int(built.system.PLL2.n),
        "mapping_ids": [row["idx"] for row in inventory["regf2"]],
        "expected_mapping_ids": expected_ids,
        "input_parameter_cards_match": all(
            row["input_parameter_card"] == contract["parameter_card"]
            for row in inventory["regf2"]
        ),
        "runtime_parameter_cards_match": all(
            row["runtime_parameter_card"] == contract["runtime_parameter_card"]
            for row in inventory["regf2"]
        ),
        "pll_buses": [row["bus"] for row in inventory["pll2"]],
        "physical_trajectory_executed": False,
        "setup_only_wall_seconds": elapsed,
    }


def rehearse() -> str:
    base.assert_wsl_scratch()
    collisions = [path for path in (REHEARSAL, CAPACITY, SEAL, DEFAULT_OUT) if path.exists()]
    if collisions:
        raise FileExistsError(f"R389 pre-attempt artifact exists: {collisions}")
    runtime = installed_runtime()
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
    contract = build_regf2_object_init_contract()
    checks = {
        "source_hash": bool(sources),
        "parent_hash": bool(parents),
        "installed_package": runtime["andes_version"] == contract["andes_version"],
        "installed_model_sources": runtime["regf1_model_sha256"] == contract["regf1_source_sha256"]
        and runtime["regf2_model_sha256"] == contract["regf2_source_sha256"],
        "installed_cases": Path(runtime["xlsx_case_path"]).is_file()
        and Path(runtime["json_case_path"]).is_file(),
        "installed_case_hashes": installed_case_hashes_match(runtime, contract),
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
        and canary["pll_buses"] == [1, 2, 3, 4],
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
        "question_in_flight": "status: in-flight" in QUESTION.read_text(encoding="utf-8"),
        "active_plan": "state: active" in PLAN.read_text(encoding="utf-8")
        and f"manuscript_line: {LINE_ID}" in PLAN.read_text(encoding="utf-8"),
        "no_competing_research_process": not other,
        "physical_trajectory_executed": False,
    }
    if not base.rehearsal_checks({"checks": checks}) or capacity["readiness"] != "RUN-READY":
        raise RuntimeError(f"R389 rehearsal/capacity gate did not pass: {checks}")
    capacity.update(
        {
            "installed_runtime": runtime,
            "sources": sources,
            "parents": parents,
            "setup_only_canary": canary,
            "setup_only_wall_seconds": canary["setup_only_wall_seconds"],
            "prior_one_trajectory_wall_seconds": float(
                base.read_hashed_json(
                    ROOT / "results/research_loop/r386_regcv1_reference_capture_gate/formal_execution.json"
                )["wall_seconds"]
            ),
            "estimated_formal_wall_seconds": (
                canary["setup_only_wall_seconds"]
                + float(
                    base.read_hashed_json(
                        ROOT / "results/research_loop/r386_regcv1_reference_capture_gate/formal_execution.json"
                    )["wall_seconds"]
                )
            ),
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
    """Seal R389 only after a fresh zero-competing-process measurement."""

    base.assert_posix_runtime()
    rehearsal = base.read_hashed_json(REHEARSAL)
    capacity = base.read_hashed_json(CAPACITY)
    if not base.rehearsal_checks(rehearsal):
        raise RuntimeError("R389 rehearsal did not pass")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R389 capacity gate is not RUN-READY")
    sources = source_manifest()
    parents = parent_manifest()
    runtime = installed_runtime()
    if rehearsal["sources"] != sources or capacity["sources"] != sources:
        raise RuntimeError("R389 source drift before sealing")
    if rehearsal["parents"] != parents or capacity["parents"] != parents:
        raise RuntimeError("R389 parent drift before sealing")
    if rehearsal["installed_runtime"] != runtime or capacity["installed_runtime"] != runtime:
        raise RuntimeError("R389 installed runtime drift before sealing")
    if DEFAULT_OUT.exists() or SEAL.exists():
        raise FileExistsError("R389 seal/formal output collision")
    competing = base.other_research_python_processes()
    process_check = {
        "created_utc": datetime.now(UTC).isoformat(),
        "other_research_python_processes": competing,
        "other_reserved_processes": len(competing),
        "passed": not competing,
    }
    if competing:
        raise RuntimeError(
            "R389 HOLD: competing research processes found immediately before seal"
        )
    contract = build_regf2_object_init_contract()
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


def run_formal_record(
    contract: Mapping[str, Any], runtime: Mapping[str, Any]
) -> dict[str, Any]:
    record = _empty_record(base.payload_sha256(contract))
    system: Any | None = None
    built: Any | None = None
    trajectory_start: float | None = None
    initial: dict[str, Any] | None = None
    try:
        audit = base.load_verified_static_case(
            xlsx_path=runtime["xlsx_case_path"],
            json_path=runtime["json_case_path"],
        )
        built = build_regf2_static_kundur_object(
            full_case=audit.full_case,
            work_dir=Path.cwd(),
        )
        system = built.system
        record["source"] = {
            "andes_version": runtime["andes_version"],
            "xlsx_json_static_equal": audit.xlsx_json_static_equal,
            "derived_case_deterministic": built.derived_case_sha256
            == runtime["derived_case_sha256"],
            "xlsx_case_sha256": audit.xlsx_sha256,
            "json_case_sha256": audit.json_sha256,
            "derived_case_sha256": built.derived_case_sha256,
            "regf1_source_sha256": runtime["regf1_model_sha256"],
            "regf2_source_sha256": runtime["regf2_model_sha256"],
        }
        system.TDS.config.tol = float(contract["tds_tolerance"])
        system.TDS.config.tf = float(contract["tds_tf_seconds"])
        system.setup()
        record["solver"]["setup_completed"] = bool(system.is_setup)
        record["solver"]["tds_tolerance"] = float(system.TDS.config.tol)
        record["inventory"] = _full_inventory(system, built, contract)

        pflow_return = system.PFlow.run()
        record["solver"]["pflow_converged"] = bool(pflow_return)
        if not pflow_return:
            record["scientific_error"] = "PFlow did not converge"
            diagnostics = capture_initialization_diagnostics(
                system,
                residual_threshold=float(contract["residual_abs_threshold"]),
            )
            record["initialization_diagnostics"] = diagnostics
            if diagnostics["captured"] is not True:
                raise RuntimeError(
                    "R389 diagnostic capture failed after PFlow failure: "
                    f"{diagnostics.get('capture_error', 'unknown error')}"
                )
            dae_finite, model_finite = finite_guards(system)
            record["finite_guard"] = {
                "checked": True,
                "dae_finite": dae_finite,
                "regf2_finite": model_finite,
            }
            return record

        source_rows = _source_snapshot(system, contract)
        init_return = system.TDS.init()
        record["solver"]["tds_initialized"] = init_return is not False
        record["solver"]["tds_test_ok"] = system.TDS.test_ok is True
        record["inventory"] = _full_inventory(system, built, contract)
        diagnostics = capture_initialization_diagnostics(
            system,
            residual_threshold=float(contract["residual_abs_threshold"]),
        )
        record["initialization_diagnostics"] = diagnostics
        if diagnostics["captured"] is not True:
            raise RuntimeError(
                "R389 initialization diagnostic capture failed: "
                f"{diagnostics.get('capture_error', 'unknown error')}"
            )
        record["references"] = post_init_references(system, source_rows, contract)
        if not (
            record["solver"]["tds_initialized"]
            and record["solver"]["tds_test_ok"]
        ):
            record["scientific_error"] = "TDS initialization failed"
            dae_finite, model_finite = finite_guards(system)
            record["finite_guard"] = {
                "checked": True,
                "dae_finite": dae_finite,
                "regf2_finite": model_finite,
            }
            return record

        trajectory_start = float(system.dae.t)
        initial = capture_initial_snapshot(system)
        record["trajectory_attempted"] = True
        system.TDS.run()
        terminal_time = float(system.dae.t)
        record["solver"]["terminal_time_seconds"] = terminal_time
        record["solver"]["tds_converged"] = bool(system.TDS.converged)
        if terminal_time > trajectory_start:
            record["physical_trajectory_executed"] = True
            record["trajectory_count"] = 1
            record["trace"] = capture_trace(system, initial)
        dae_finite, model_finite = finite_guards(system)
        record["finite_guard"] = {
            "checked": True,
            "dae_finite": dae_finite,
            "regf2_finite": model_finite,
        }
        if terminal_time < float(contract["tds_tf_seconds"]) - float(contract["tds_tolerance"]):
            record["scientific_error"] = "TDS did not reach horizon"
        elif not record["solver"]["tds_converged"]:
            record["scientific_error"] = "TDS did not converge"
    except Exception as exc:
        record["execution_error"] = f"{type(exc).__name__}: {exc}"
        if system is not None and built is not None:
            try:
                record["inventory"] = _full_inventory(system, built, contract)
                diagnostics = capture_initialization_diagnostics(
                    system,
                    residual_threshold=float(contract["residual_abs_threshold"]),
                )
                if diagnostics["captured"] is True:
                    record["initialization_diagnostics"] = diagnostics
                terminal_time = float(system.dae.t)
                record["solver"]["terminal_time_seconds"] = terminal_time
                if (
                    record["trajectory_attempted"]
                    and trajectory_start is not None
                    and terminal_time > trajectory_start
                ):
                    record["physical_trajectory_executed"] = True
                    record["trajectory_count"] = 1
                    if initial is not None:
                        record["trace"] = capture_trace(system, initial)
                dae_finite, model_finite = finite_guards(system)
                record["finite_guard"] = {
                    "checked": True,
                    "dae_finite": dae_finite,
                    "regf2_finite": model_finite,
                }
            except Exception:
                pass
    return record


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
    base.build_clean_contract = build_regf2_object_init_contract
    base.classify_regcv1_clean_init_record = classify_regf2_object_init_record
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
