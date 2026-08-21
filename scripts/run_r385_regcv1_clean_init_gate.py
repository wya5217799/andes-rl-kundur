"""Execute the sealed R385 structurally clean four-REGCV1 gate.

Motivation:
    Distinguish the R384 status-zero legacy-equation failure from REGCV1 by
    reconstructing the exact packaged Kundur static tables without any legacy
    dynamic/event records and running one zero-input initialization job.

Usage:
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r385_regcv1_clean_init_gate.py rehearse
    /home/wya/andes_venv/bin/python scripts/run_r385_regcv1_clean_init_gate.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r385_regcv1_clean_init_gate.py execute \
        --expected-seal-sha256 <sha256>

Failure modes:
    Provenance, source-equality, structural-absence, diagnostics-integrity, or
    create-only failures are ANALYSIS-INVALID. A complete clean object that
    fails native initialization/reference/finite/drift guards is a scientific
    STOP. There is no retry, tuning, controller, or training command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
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

from andes_rl_kundur.env.andes.regcv1_static_kundur import (  # noqa: E402
    build_regcv1_static_kundur_object,
    load_verified_static_case,
    render_static_case_bytes,
)
from andes_rl_kundur.evaluation.regcv1_clean_init_gate import (  # noqa: E402
    build_clean_contract,
    classify_regcv1_clean_init_record,
)

ROUND_ID = "R385"
QUESTION_ID = "Q-0105"
LINE_ID = "converter-vsg-pq-decoupling"
PLAN = ROOT / "memory/rounds/R385/plan.md"
QUESTION = ROOT / "memory/questions/Q-0105.md"
REHEARSAL = ROOT / "memory/rounds/R385/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R385/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R385/formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r385_regcv1_clean_init_gate"


def canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def payload_sha256(payload: object) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def write_new_json(path: Path, payload: object) -> str:
    """Create one canonical JSON artifact and matching SHA-256 sidecar."""

    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(payload)
    with path.open("xb") as handle:
        handle.write(data)
    digest = hashlib.sha256(data).hexdigest()
    sidecar = path.with_name(path.name + ".sha256")
    with sidecar.open("x", encoding="ascii", newline="\n") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def read_hashed_json(path: Path) -> dict[str, Any]:
    expected = path.with_name(path.name + ".sha256").read_text(
        encoding="ascii"
    ).split()[0]
    observed = sha256_file(path)
    if observed != expected:
        raise RuntimeError(f"hash mismatch for {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return payload


def source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "builder": ROOT / "src/andes_rl_kundur/env/andes/regcv1_static_kundur.py",
        "classifier": ROOT
        / "src/andes_rl_kundur/evaluation/regcv1_clean_init_gate.py",
        "builder_tests": ROOT / "tests/test_regcv1_static_kundur.py",
        "classifier_tests": ROOT / "tests/test_regcv1_clean_init_gate.py",
        "runner_tests": ROOT / "tests/test_r385_regcv1_clean_init_gate.py",
        "plan": PLAN,
        "question": QUESTION,
        "line": ROOT / "paper/converter_vsg_pq_decoupling/LINE.md",
        "route_contract": ROOT
        / "paper/converter_vsg_pq_decoupling/working/route_contract.md",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": relative(path), "sha256": sha256_file(path)}
        for name, path in sources.items()
    }


def parent_manifest() -> dict[str, dict[str, str]]:
    parents = {
        "r384_claim": ROOT / "memory/claims/CLM-1065.md",
        "r384_feed": ROOT / "paper/converter_vsg_pq_decoupling/reports/R384.md",
        "successor_adr": ROOT
        / "docs/adr/0017-structural-absence-regcv1-successor.md",
        "line_adr": ROOT / "docs/adr/0016-separate-converter-vsg-pq-decoupling-line.md",
    }
    return {
        name: {"path": relative(path), "sha256": sha256_file(path)}
        for name, path in parents.items()
    }


def installed_runtime() -> dict[str, Any]:
    import andes
    from andes.models.renewable import regcv1

    xlsx_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    json_path = xlsx_path.with_suffix(".json")
    audit = load_verified_static_case(xlsx_path=xlsx_path, json_path=json_path)
    model_path = Path(regcv1.__file__).resolve()
    derived = render_static_case_bytes(audit.full_case)
    return {
        "python": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "andes_module": str(Path(andes.__file__).resolve()),
        "regcv1_model_path": str(model_path),
        "regcv1_model_sha256": sha256_file(model_path),
        "xlsx_case_path": str(xlsx_path),
        "xlsx_case_sha256": audit.xlsx_sha256,
        "json_case_path": str(json_path),
        "json_case_sha256": audit.json_sha256,
        "xlsx_json_static_equal": audit.xlsx_json_static_equal,
        "derived_case_sha256": hashlib.sha256(derived).hexdigest(),
    }


def assert_posix_runtime() -> None:
    if os.name != "posix":
        raise RuntimeError("R385 research lifecycle commands are WSL/POSIX-only")


def assert_wsl_scratch() -> None:
    assert_posix_runtime()
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R385 rehearsal/execute must run through andes_scratch.py")


def other_research_python_processes() -> list[dict[str, Any]]:
    if os.name != "posix":
        return []
    own_pid = os.getpid()
    matches: list[dict[str, Any]] = []
    for path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            pid = int(path.parent.name)
            if pid == own_pid:
                continue
            command = path.read_bytes().replace(b"\x00", b" ").decode(
                "utf-8", errors="replace"
            )
        except (OSError, ValueError):
            continue
        lowered = command.lower()
        if "python" in lowered and "andes-rl-kundur" in lowered and (
            "run_r" in lowered or "train" in lowered or "eval" in lowered
        ):
            matches.append({"pid": pid, "command": command.strip()})
    return matches


def memory_resources() -> tuple[int, int, int]:
    logical_processors = int(os.cpu_count() or 1)
    meminfo: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition(":")
        if separator:
            meminfo[name] = int(value.strip().split()[0]) * 1024
    wsl_available = int(meminfo.get("MemAvailable", 0))
    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        physical_memory = int(completed.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        physical_memory = int(meminfo.get("MemTotal", 0))
    if min(logical_processors, physical_memory, wsl_available) <= 0:
        raise RuntimeError("failed to capture positive host/WSL resources")
    return logical_processors, physical_memory, wsl_available


def build_capacity_payload(
    *,
    logical_processors: int,
    physical_memory_bytes: int,
    wsl_memory_available_bytes: int,
    disk_free_bytes: int,
    competing_processes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    ready = (
        min(
            logical_processors,
            physical_memory_bytes,
            wsl_memory_available_bytes,
            disk_free_bytes,
        )
        > 0
        and not competing_processes
    )
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "readiness": "RUN-READY" if ready else "HOLD",
        "whole_host_python_process_budget": 1,
        "host_process_budget": 1,
        "wsl_python_processes": 1,
        "native_threads_per_process": 1,
        "other_reserved_processes": 0,
        "stage_cap_reason": "one independent quick formal job",
        "host": {
            "logical_processors": int(logical_processors),
            "physical_memory_bytes": int(physical_memory_bytes),
        },
        "wsl": {"memory_available_bytes": int(wsl_memory_available_bytes)},
        "disk_free_bytes": int(disk_free_bytes),
        "competing_processes": [dict(row) for row in competing_processes],
        "physical_trajectory_executed": False,
        "scientific_classification_inspected": False,
        "formal_authority": False,
        "training_executed": False,
    }


def rehearsal_checks(payload: Mapping[str, Any]) -> bool:
    checks = payload.get("checks")
    if not isinstance(checks, Mapping) or not checks:
        return False
    positive = {
        key: value
        for key, value in checks.items()
        if key != "physical_trajectory_executed"
    }
    return bool(positive) and all(value is True for value in positive.values()) and (
        checks.get("physical_trajectory_executed") is False
    )


def setup_only_canary(runtime: Mapping[str, Any]) -> dict[str, Any]:
    audit = load_verified_static_case(
        xlsx_path=runtime["xlsx_case_path"],
        json_path=runtime["json_case_path"],
    )
    built = build_regcv1_static_kundur_object(
        full_case=audit.full_case,
        work_dir=Path.cwd(),
    )
    built.system.setup()
    return {
        "setup_completed": bool(built.system.is_setup),
        "derived_case_sha256": built.derived_case_sha256,
        "forbidden_model_counts": built.forbidden_model_counts,
        "regcv1_count": int(built.system.REGCV1.n),
        "physical_trajectory_executed": False,
    }


def rehearse() -> str:
    assert_wsl_scratch()
    collisions = [
        path for path in (REHEARSAL, CAPACITY, SEAL, DEFAULT_OUT) if path.exists()
    ]
    if collisions:
        raise FileExistsError(f"R385 pre-attempt artifact exists: {collisions}")
    runtime = installed_runtime()
    other = other_research_python_processes()
    logical, physical, available = memory_resources()
    capacity = build_capacity_payload(
        logical_processors=logical,
        physical_memory_bytes=physical,
        wsl_memory_available_bytes=available,
        disk_free_bytes=int(shutil.disk_usage(ROOT).free),
        competing_processes=other,
    )
    canary = setup_only_canary(runtime)
    sources = source_manifest()
    parents = parent_manifest()
    checks = {
        "source_hash": bool(sources),
        "parent_hash": bool(parents),
        "installed_package": runtime["andes_version"] == "2.0.0",
        "installed_cases": Path(runtime["xlsx_case_path"]).is_file()
        and Path(runtime["json_case_path"]).is_file(),
        "static_table_identity": runtime["xlsx_json_static_equal"] is True,
        "derived_case_determinism": canary["derived_case_sha256"]
        == runtime["derived_case_sha256"],
        "structural_absence": all(
            value == 0 for value in canary["forbidden_model_counts"].values()
        ),
        "setup_only_canary": canary["setup_completed"] is True
        and canary["regcv1_count"] == 4,
        "output_absence": not DEFAULT_OUT.exists() and not SEAL.exists(),
        "question_in_flight": "status: in-flight"
        in QUESTION.read_text(encoding="utf-8"),
        "active_plan": "state: active" in PLAN.read_text(encoding="utf-8")
        and f"manuscript_line: {LINE_ID}" in PLAN.read_text(encoding="utf-8"),
        "no_competing_research_process": not other,
        "physical_trajectory_executed": False,
    }
    preview = {"checks": checks}
    if not rehearsal_checks(preview) or capacity["readiness"] != "RUN-READY":
        raise RuntimeError(f"R385 rehearsal/capacity gate did not pass: {checks}")
    capacity.update(
        {
            "installed_runtime": runtime,
            "sources": sources,
            "parents": parents,
            "setup_only_canary": canary,
        }
    )
    capacity_digest = write_new_json(CAPACITY, capacity)
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": payload_sha256(build_clean_contract()),
        "sources": sources,
        "parents": parents,
        "installed_runtime": runtime,
        "setup_only_canary": canary,
        "capacity_sha256": capacity_digest,
        "checks": checks,
        "formal_authority": False,
        "training_executed": False,
    }
    digest = write_new_json(REHEARSAL, payload)
    return digest


def prepare() -> str:
    assert_posix_runtime()
    rehearsal = read_hashed_json(REHEARSAL)
    capacity = read_hashed_json(CAPACITY)
    if not rehearsal_checks(rehearsal):
        raise RuntimeError("R385 rehearsal did not pass")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R385 capacity gate is not RUN-READY")
    sources = source_manifest()
    parents = parent_manifest()
    runtime = installed_runtime()
    if rehearsal["sources"] != sources or capacity["sources"] != sources:
        raise RuntimeError("R385 source drift before sealing")
    if rehearsal["parents"] != parents or capacity["parents"] != parents:
        raise RuntimeError("R385 parent drift before sealing")
    if rehearsal["installed_runtime"] != runtime or capacity["installed_runtime"] != runtime:
        raise RuntimeError("R385 installed runtime drift before sealing")
    if DEFAULT_OUT.exists() or SEAL.exists():
        raise FileExistsError("R385 seal/formal output collision")
    contract = build_clean_contract()
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
        "rehearsal_sha256": sha256_file(REHEARSAL),
        "capacity_sha256": sha256_file(CAPACITY),
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
    return write_new_json(SEAL, payload)


def load_seal(expected_sha256: str) -> tuple[dict[str, Any], str]:
    seal = read_hashed_json(SEAL)
    observed = sha256_file(SEAL)
    if observed != expected_sha256:
        raise RuntimeError("R385 seal digest mismatch")
    if seal.get("contract") != build_clean_contract():
        raise RuntimeError("R385 contract drift")
    if seal.get("sources") != source_manifest():
        raise RuntimeError("R385 sealed source drift")
    if seal.get("parents") != parent_manifest():
        raise RuntimeError("R385 sealed parent drift")
    if seal.get("installed_runtime") != installed_runtime():
        raise RuntimeError("R385 sealed runtime drift")
    if seal.get("rehearsal_sha256") != sha256_file(REHEARSAL):
        raise RuntimeError("R385 rehearsal drift")
    if seal.get("capacity_sha256") != sha256_file(CAPACITY):
        raise RuntimeError("R385 capacity drift")
    return seal, observed


def _json_value(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return [_json_value(item) for item in value.tolist()]
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def capture_initialization_diagnostics(system: Any) -> dict[str, Any]:
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
        tol = float(system.TDS.config.tol)
        bad = np.flatnonzero((np.abs(fg) >= tol) | np.isnan(fg))
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
                device_idx = _json_value(owner.idx.v[int(positions[0])])
            rows.append(
                {
                    "combined_index": numeric_index,
                    "name": str(system.dae.xy_name[numeric_index]),
                    "residual": _json_value(float(fg[numeric_index])),
                    "equation": str(getattr(variable, "e_str", "") or ""),
                    "model": str(getattr(owner, "class_name", "") or ""),
                    "idx": device_idx,
                }
            )
        limits: list[dict[str, Any]] = []
        for model in system.exist.pflow_tds.values():
            for discrete in model.discrete.values():
                limits.extend(_json_value(discrete.get_limit_report()))
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


def regcv1_inventory(system: Any) -> list[dict[str, Any]]:
    model = system.REGCV1
    return [
        {
            "idx": str(idx),
            "bus": int(model.bus.v[position]),
            "gen": int(model.gen.v[position]),
            "Sn": float(model.Sn.v[position]),
            "u": int(model.u.v[position]),
        }
        for position, idx in enumerate(model.idx.v)
    ]


def network_inventory(system: Any) -> dict[str, Any]:
    idxes = [1, 2, 3, 4]
    buses = system.StaticGen.get(src="bus", idx=idxes, attr="v")
    return {
        "bus_count": int(system.Bus.n),
        "line_count": int(system.Line.n),
        "pq_count": int(system.PQ.n),
        "static_gen_count": int(system.StaticGen.n),
        "static_generator_buses": [int(value) for value in buses],
    }


def forbidden_model_counts(system: Any, names: Sequence[str]) -> dict[str, int]:
    return {
        name: int(getattr(system, name).n) if hasattr(system, name) else 0
        for name in names
    }


def forbidden_dae_names(system: Any, names: Sequence[str]) -> list[str]:
    forbidden = set(names)
    matches: list[str] = []
    for raw_name in system.dae.xy_name:
        label = str(raw_name)
        tokens = set(filter(None, re.split(r"[\s.]+", label)))
        if tokens & forbidden:
            matches.append(label)
    return matches


def post_init_references(system: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    idxes = [row["gen"] for row in contract["expected_mapping"]]
    static_p = system.StaticGen.get(src="p", idx=idxes, attr="v")
    static_q = system.StaticGen.get(src="q", idx=idxes, attr="v")
    tol = float(contract["reference_abs_tolerance"])
    rows: list[dict[str, Any]] = []
    for position, expected in enumerate(contract["expected_mapping"]):
        pref = float(system.REGCV1.Pref.v[position])
        qref = float(system.REGCV1.Qref.v[position])
        p_value = float(static_p[position])
        q_value = float(static_q[position])
        rows.append(
            {
                "idx": str(expected["idx"]),
                "static_p": p_value,
                "static_q": q_value,
                "pref": pref,
                "qref": qref,
                "pref_match": math.isclose(pref, p_value, rel_tol=0.0, abs_tol=tol),
                "qref_match": math.isclose(qref, q_value, rel_tol=0.0, abs_tol=tol),
            }
        )
    return {"checked": True, "absolute_tolerance": tol, "rows": rows}


def signal_snapshot(system: Any, names: Sequence[str]) -> dict[str, np.ndarray]:
    return {
        name: np.asarray(getattr(system.REGCV1, name).v, dtype=float).copy()
        for name in names
    }


def finite_guards(system: Any) -> tuple[bool, bool]:
    dae_finite = True
    for name in ("x", "y", "z", "f", "g"):
        try:
            values = np.asarray(getattr(system.dae, name), dtype=float)
            dae_finite = dae_finite and bool(np.all(np.isfinite(values)))
        except (AttributeError, TypeError, ValueError):
            dae_finite = False
    model_finite = True
    for variable in system.REGCV1.cache.all_vars.values():
        try:
            values = np.asarray(variable.v, dtype=float)
            model_finite = model_finite and bool(np.all(np.isfinite(values)))
        except (AttributeError, TypeError, ValueError):
            model_finite = False
    return dae_finite, model_finite


def empty_record(contract_sha256: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "contract_sha256": contract_sha256,
        "formal_input_complete": True,
        "trajectory_attempted": False,
        "physical_trajectory_executed": False,
        "trajectory_count": 0,
        "execution_error": None,
        "scientific_error": None,
        "source": {
            "xlsx_json_static_equal": True,
            "xlsx_case_sha256": None,
            "json_case_sha256": None,
            "derived_case_sha256": None,
            "derived_case_deterministic": True,
        },
        "inventory": {
            "network": {},
            "forbidden_model_counts": {},
            "forbidden_dae_names": [],
            "regcv1": [],
        },
        "references": {"checked": False, "rows": []},
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
            "tds_tolerance": 1.0e-4,
        },
        "finite_guard": {
            "checked": False,
            "dae_finite": False,
            "regcv1_finite": False,
        },
        "drift": {
            "checked": False,
            "max_abs_by_signal": {
                name: None for name in build_clean_contract()["drift_signals"]
            },
        },
        "training_executed": False,
    }


def run_formal_record(
    contract: Mapping[str, Any], runtime: Mapping[str, Any]
) -> dict[str, Any]:
    record = empty_record(payload_sha256(contract))
    system: Any | None = None
    initial: dict[str, np.ndarray] | None = None
    trajectory_start_time: float | None = None
    try:
        audit = load_verified_static_case(
            xlsx_path=runtime["xlsx_case_path"],
            json_path=runtime["json_case_path"],
        )
        built = build_regcv1_static_kundur_object(
            full_case=audit.full_case,
            work_dir=Path.cwd(),
        )
        system = built.system
        record["source"] = {
            "xlsx_json_static_equal": audit.xlsx_json_static_equal,
            "xlsx_case_sha256": audit.xlsx_sha256,
            "json_case_sha256": audit.json_sha256,
            "derived_case_sha256": built.derived_case_sha256,
            "derived_case_deterministic": built.derived_case_sha256
            == runtime["derived_case_sha256"],
        }
        record["inventory"] = {
            "network": built.network_inventory,
            "forbidden_model_counts": built.forbidden_model_counts,
            "forbidden_dae_names": [],
            "regcv1": regcv1_inventory(system),
        }
        record["solver"]["tds_tolerance"] = float(system.TDS.config.tol)
        system.setup()
        record["solver"]["setup_completed"] = True
        record["inventory"]["regcv1"] = regcv1_inventory(system)
        record["inventory"]["forbidden_model_counts"] = forbidden_model_counts(
            system, contract["forbidden_models"]
        )

        pflow_return = system.PFlow.run()
        record["solver"]["pflow_converged"] = bool(pflow_return)
        if not pflow_return:
            record["scientific_error"] = "PFlow.run returned a non-success value"
            diagnostics = capture_initialization_diagnostics(system)
            record["initialization_diagnostics"] = diagnostics
            if diagnostics["captured"] is not True:
                raise RuntimeError(
                    "initialization diagnostic capture failed after PFlow failure: "
                    f"{diagnostics.get('capture_error', 'unknown error')}"
                )
            return record

        system.TDS.config.tf = float(contract["tds_tf_seconds"])
        init_return = system.TDS.init()
        record["solver"]["tds_initialized"] = init_return is not False
        record["solver"]["tds_test_ok"] = system.TDS.test_ok is True
        record["inventory"]["forbidden_dae_names"] = forbidden_dae_names(
            system, contract["forbidden_models"]
        )
        diagnostics = capture_initialization_diagnostics(system)
        record["initialization_diagnostics"] = diagnostics
        if diagnostics["captured"] is not True:
            raise RuntimeError(
                "initialization diagnostic capture failed: "
                f"{diagnostics.get('capture_error', 'unknown error')}"
            )
        record["references"] = post_init_references(system, contract)
        if not (
            record["solver"]["tds_initialized"]
            and record["solver"]["tds_test_ok"]
        ):
            record["scientific_error"] = "native TDS initialization guard failed"
            return record

        initial = signal_snapshot(system, contract["drift_signals"])
        trajectory_start_time = float(system.dae.t)
        record["trajectory_attempted"] = True
        system.TDS.run()
        terminal_time = float(system.dae.t)
        record["solver"]["terminal_time_seconds"] = terminal_time
        if terminal_time > trajectory_start_time:
            record["physical_trajectory_executed"] = True
            record["trajectory_count"] = 1
        record["solver"]["tds_converged"] = bool(system.TDS.converged)
        terminal = signal_snapshot(system, contract["drift_signals"])
        dae_finite, model_finite = finite_guards(system)
        record["finite_guard"] = {
            "checked": True,
            "dae_finite": dae_finite,
            "regcv1_finite": model_finite,
        }
        record["drift"] = {
            "checked": True,
            "max_abs_by_signal": {
                name: float(np.max(np.abs(terminal[name] - initial[name])))
                for name in contract["drift_signals"]
            },
        }
    except Exception as exc:
        record["execution_error"] = f"{type(exc).__name__}: {exc}"
        if system is not None:
            record["initialization_diagnostics"] = capture_initialization_diagnostics(system)
            try:
                record["inventory"]["forbidden_dae_names"] = forbidden_dae_names(
                    system, contract["forbidden_models"]
                )
                terminal_time = float(system.dae.t)
                record["solver"]["terminal_time_seconds"] = terminal_time
                if (
                    record["trajectory_attempted"] is True
                    and trajectory_start_time is not None
                    and terminal_time > trajectory_start_time
                ):
                    record["physical_trajectory_executed"] = True
                    record["trajectory_count"] = 1
                dae_finite, model_finite = finite_guards(system)
                record["finite_guard"] = {
                    "checked": True,
                    "dae_finite": dae_finite,
                    "regcv1_finite": model_finite,
                }
                if initial is not None:
                    terminal = signal_snapshot(system, contract["drift_signals"])
                    record["drift"] = {
                        "checked": True,
                        "max_abs_by_signal": {
                            name: float(np.max(np.abs(terminal[name] - initial[name])))
                            for name in contract["drift_signals"]
                        },
                    }
            except Exception:
                pass
    return record


def execute(*, expected_sha256: str, out_dir: Path = DEFAULT_OUT) -> str:
    assert_wsl_scratch()
    seal, seal_digest = load_seal(expected_sha256)
    other = other_research_python_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    if out_dir.exists():
        raise FileExistsError(f"R385 output collision: {out_dir}")
    attempt_digest = write_new_json(
        out_dir / "formal_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "retry_authorized": False,
            "training_authorized": False,
        },
    )
    started = time.perf_counter()
    try:
        record = run_formal_record(seal["contract"], seal["installed_runtime"])
        execution = {
            **record,
            "seal_sha256": seal_digest,
            "attempt_sha256": attempt_digest,
            "wall_seconds": time.perf_counter() - started,
        }
        execution_digest = write_new_json(
            out_dir / "formal_execution.json", execution
        )
        analysis = classify_regcv1_clean_init_record(
            record, contract=seal["contract"]
        )
        analysis.update(
            {
                "seal_sha256": seal_digest,
                "formal_execution_sha256": execution_digest,
                "training_authorized": False,
            }
        )
        analysis_digest = write_new_json(
            out_dir / "formal_analysis.json", analysis
        )
        manifest_digest = write_new_json(
            out_dir / "formal_manifest.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "entries": [
                    {
                        "path": relative(out_dir / "formal_attempt.json"),
                        "sha256": attempt_digest,
                    },
                    {
                        "path": relative(out_dir / "formal_execution.json"),
                        "sha256": execution_digest,
                    },
                    {
                        "path": relative(out_dir / "formal_analysis.json"),
                        "sha256": analysis_digest,
                    },
                ],
            },
        )
        print(f"classification={analysis['classification']}", flush=True)
        print(f"manifest_sha256={manifest_digest}", flush=True)
        return analysis_digest
    except Exception as exc:
        write_new_json(
            out_dir / "formal_failure.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "seal_sha256": seal_digest,
                "attempt_sha256": attempt_digest,
                "classification": "ANALYSIS-INVALID",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "wall_seconds": time.perf_counter() - started,
                "retry_authorized": False,
                "training_authorized": False,
            },
        )
        raise


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
