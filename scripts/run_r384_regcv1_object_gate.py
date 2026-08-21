"""Execute the sealed R384 four-REGCV1 object/initialization gate.

Motivation:
    Establish whether converter-level VSG objects exist, initialize, expose
    independent Pref/Qref software interfaces, and remain at a zero-input
    operating point before any controller or learning experiment is allowed.

Usage:
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r384_regcv1_object_gate.py rehearse
    /home/wya/andes_venv/bin/python scripts/run_r384_regcv1_object_gate.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r384_regcv1_object_gate.py execute \
        --expected-seal-sha256 <sha256>

Failure modes:
    Provenance, seal, source, output-collision, or runner-integrity failures
    produce ANALYSIS-INVALID evidence and never retry.  Complete physical
    object, setup, solver, interface, finite-value, or drift failures produce
    the registered scientific STOP.  Every artifact is create-only and the
    runner exposes no training or tuning command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
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

from andes_rl_kundur.env.andes.regcv1_kundur import (  # noqa: E402
    build_regcv1_kundur_object,
)
from andes_rl_kundur.evaluation.regcv1_object_gate import (  # noqa: E402
    build_contract,
    classify_regcv1_object_record,
)

ROUND_ID = "R384"
QUESTION_ID = "Q-0104"
LINE_ID = "converter-vsg-pq-decoupling"
PLAN = ROOT / "memory/rounds/R384/plan.md"
QUESTION = ROOT / "memory/questions/Q-0104.md"
REHEARSAL = ROOT / "memory/rounds/R384/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R384/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R384/formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r384_regcv1_object_gate"


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_new_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical_bytes(payload)
    with path.open("xb") as handle:
        handle.write(data)
    digest = hashlib.sha256(data).hexdigest()
    sidecar = path.with_name(path.name + ".sha256")
    with sidecar.open("x", encoding="ascii", newline="\n") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def _read_hashed_json(path: Path) -> dict[str, Any]:
    expected = path.with_name(path.name + ".sha256").read_text(
        encoding="ascii"
    ).split()[0]
    observed = _sha256_file(path)
    if observed != expected:
        raise RuntimeError(f"hash mismatch for {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return payload


def _source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "builder": ROOT / "src/andes_rl_kundur/env/andes/regcv1_kundur.py",
        "classifier": ROOT
        / "src/andes_rl_kundur/evaluation/regcv1_object_gate.py",
        "builder_tests": ROOT / "tests/test_regcv1_kundur.py",
        "classifier_tests": ROOT / "tests/test_regcv1_object_gate.py",
        "runner_tests": ROOT / "tests/test_r384_regcv1_object_gate.py",
        "plan": PLAN,
        "question": QUESTION,
        "line": ROOT / "paper/converter_vsg_pq_decoupling/LINE.md",
        "route_contract": ROOT
        / "paper/converter_vsg_pq_decoupling/working/route_contract.md",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in sources.items()
    }


def _parent_manifest() -> dict[str, dict[str, str]]:
    parents = {
        "line_decision_claim": ROOT / "memory/claims/CLM-1060.md",
        "line_decision_feed": ROOT
        / "paper/converter_vsg_pq_decoupling/reports/R383.md",
        "line_decision_adr": ROOT
        / "docs/adr/0016-separate-converter-vsg-pq-decoupling-line.md",
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in parents.items()
    }


def _installed_runtime() -> dict[str, Any]:
    import andes
    from andes.models.renewable import regcv1

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    model_path = Path(regcv1.__file__).resolve()
    return {
        "python": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "andes_module": str(Path(andes.__file__).resolve()),
        "regcv1_model_path": str(model_path),
        "regcv1_model_sha256": _sha256_file(model_path),
        "case_path": str(case_path),
        "case_sha256": _sha256_file(case_path),
    }


def _assert_posix_runtime() -> None:
    if os.name != "posix":
        raise RuntimeError("R384 research lifecycle commands are WSL/POSIX-only")


def _assert_wsl_scratch() -> None:
    _assert_posix_runtime()
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R384 rehearsal/execute must run through andes_scratch.py")


def _other_research_python_processes() -> list[dict[str, Any]]:
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
        if "python" not in lowered:
            continue
        if "andes-rl-kundur" in lowered and (
            "run_r" in lowered or "train" in lowered or "eval" in lowered
        ):
            matches.append({"pid": pid, "command": command.strip()})
    return matches


def _memory_resources() -> tuple[int, int, int]:
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


def _build_capacity_payload(
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
        "stage_cap_reason": "one independent formal job",
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


def _rehearsal_checks(payload: Mapping[str, Any]) -> bool:
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


def rehearse() -> str:
    _assert_wsl_scratch()
    collisions = [
        path for path in (REHEARSAL, CAPACITY, SEAL, DEFAULT_OUT) if path.exists()
    ]
    if collisions:
        raise FileExistsError(f"R384 pre-attempt artifact exists: {collisions}")
    runtime = _installed_runtime()
    other = _other_research_python_processes()
    logical, physical, available = _memory_resources()
    capacity = _build_capacity_payload(
        logical_processors=logical,
        physical_memory_bytes=physical,
        wsl_memory_available_bytes=available,
        disk_free_bytes=int(shutil.disk_usage(ROOT).free),
        competing_processes=other,
    )
    capacity.update(
        {
            "installed_runtime": runtime,
            "sources": _source_manifest(),
            "parents": _parent_manifest(),
        }
    )
    capacity_digest = _write_new_json(CAPACITY, capacity)
    plan_text = PLAN.read_text(encoding="utf-8")
    question_text = QUESTION.read_text(encoding="utf-8")
    checks = {
        "source_hash": bool(_source_manifest()),
        "parent_hash": bool(_parent_manifest()),
        "installed_package": runtime["andes_version"] == "2.0.0",
        "installed_case": Path(runtime["case_path"]).is_file(),
        "output_absence": not DEFAULT_OUT.exists() and not SEAL.exists(),
        "question_in_flight": "status: in-flight" in question_text,
        "active_plan": "state: active" in plan_text
        and f"manuscript_line: {LINE_ID}" in plan_text,
        "no_competing_research_process": not other,
        "physical_trajectory_executed": False,
    }
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": _payload_sha256(build_contract()),
        "sources": _source_manifest(),
        "parents": _parent_manifest(),
        "installed_runtime": runtime,
        "capacity_sha256": capacity_digest,
        "checks": checks,
        "formal_authority": False,
        "training_executed": False,
    }
    digest = _write_new_json(REHEARSAL, payload)
    if not _rehearsal_checks(payload) or capacity["readiness"] != "RUN-READY":
        raise RuntimeError("R384 rehearsal/capacity gate did not pass")
    return digest


def prepare() -> str:
    _assert_posix_runtime()
    rehearsal = _read_hashed_json(REHEARSAL)
    capacity = _read_hashed_json(CAPACITY)
    if not _rehearsal_checks(rehearsal):
        raise RuntimeError("R384 rehearsal did not pass")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R384 capacity gate is not RUN-READY")
    sources = _source_manifest()
    parents = _parent_manifest()
    runtime = _installed_runtime()
    if rehearsal["sources"] != sources or capacity["sources"] != sources:
        raise RuntimeError("R384 source drift before sealing")
    if rehearsal["parents"] != parents or capacity["parents"] != parents:
        raise RuntimeError("R384 parent drift before sealing")
    if rehearsal["installed_runtime"] != runtime or capacity["installed_runtime"] != runtime:
        raise RuntimeError("R384 installed runtime drift before sealing")
    if DEFAULT_OUT.exists() or SEAL.exists():
        raise FileExistsError("R384 seal/formal output collision")
    contract = build_contract()
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_sha256": _payload_sha256(contract),
        "sources": sources,
        "parents": parents,
        "installed_runtime": runtime,
        "rehearsal_sha256": _sha256_file(REHEARSAL),
        "capacity_sha256": _sha256_file(CAPACITY),
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
    return _write_new_json(SEAL, payload)


def _load_seal(expected_sha256: str) -> tuple[dict[str, Any], str]:
    seal = _read_hashed_json(SEAL)
    observed = _sha256_file(SEAL)
    if observed != expected_sha256:
        raise RuntimeError("R384 seal digest mismatch")
    if seal.get("contract") != build_contract():
        raise RuntimeError("R384 contract drift")
    if seal.get("sources") != _source_manifest():
        raise RuntimeError("R384 sealed source drift")
    if seal.get("parents") != _parent_manifest():
        raise RuntimeError("R384 sealed parent drift")
    if seal.get("installed_runtime") != _installed_runtime():
        raise RuntimeError("R384 sealed runtime drift")
    if seal.get("rehearsal_sha256") != _sha256_file(REHEARSAL):
        raise RuntimeError("R384 rehearsal drift")
    if seal.get("capacity_sha256") != _sha256_file(CAPACITY):
        raise RuntimeError("R384 capacity drift")
    return seal, observed


def _probe_setpoint_identity(system: Any, idxes: Sequence[str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "attempted": True,
        "completed": False,
        "pref": [],
        "qref": [],
        "error": None,
    }
    baselines: dict[str, dict[str, float]] = {}
    try:
        for channel in ("pref", "qref"):
            getter = getattr(system.RenGen, f"get_{channel}")
            setter = getattr(system.RenGen, f"set_{channel}")
            baseline = {idx: float(getter(system, idx)) for idx in idxes}
            baselines[channel] = baseline
            rows: list[dict[str, Any]] = []
            for target in idxes:
                probe = math.nextafter(baseline[target], math.inf)
                setter(system, target, probe)
                observed = {idx: float(getter(system, idx)) for idx in idxes}
                setter(system, target, baseline[target])
                restored = float(getter(system, target))
                rows.append(
                    {
                        "idx": target,
                        "baseline": baseline[target],
                        "probe": probe,
                        "readback": observed[target],
                        "restored": restored,
                        "non_target_unchanged": all(
                            observed[idx] == baseline[idx]
                            for idx in idxes
                            if idx != target
                        ),
                    }
                )
            result[channel] = rows
        result["completed"] = True
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        for channel, values in baselines.items():
            setter = getattr(system.RenGen, f"set_{channel}")
            for idx, value in values.items():
                try:
                    setter(system, idx, value)
                except Exception:
                    result["completed"] = False
    return result


def _regcv1_inventory(system: Any) -> list[dict[str, Any]]:
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


def _disabled_inventory(system: Any, names: Sequence[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in names:
        model = getattr(system, name)
        for position, idx in enumerate(model.idx.v):
            numeric_idx = int(idx)
            rows.append(
                {
                    "model": name,
                    "idx": numeric_idx,
                    "syn": numeric_idx
                    if name == "GENROU"
                    else int(model.syn.v[position]),
                    "u": int(model.u.v[position]),
                }
            )
    return rows


def _signal_snapshot(system: Any, names: Sequence[str]) -> dict[str, np.ndarray]:
    return {
        name: np.asarray(getattr(system.REGCV1, name).v, dtype=float).copy()
        for name in names
    }


def _finite_guards(system: Any) -> tuple[bool, bool]:
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


def _empty_record(contract_sha256: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "contract_sha256": contract_sha256,
        "formal_input_complete": True,
        "physical_trajectory_executed": False,
        "trajectory_count": 0,
        "execution_error": None,
        "scientific_error": None,
        "inventory": {
            "regcv1": [],
            "disabled_dynamic_chain": [],
            "network": {},
        },
        "interface_identity": {
            "attempted": False,
            "completed": False,
            "pref": [],
            "qref": [],
            "error": None,
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
                name: None for name in build_contract()["drift_signals"]
            },
        },
        "training_executed": False,
    }


def _run_formal_record(contract: Mapping[str, Any]) -> dict[str, Any]:
    record = _empty_record(_payload_sha256(contract))
    system: Any | None = None
    initial: dict[str, np.ndarray] | None = None
    try:
        built = build_regcv1_kundur_object()
        system = built.system
        record["inventory"] = {
            "regcv1": _regcv1_inventory(system),
            "disabled_dynamic_chain": _disabled_inventory(
                system, contract["disabled_chain_models"]
            ),
            "network": built.network_inventory,
        }
        record["solver"]["tds_tolerance"] = float(system.TDS.config.tol)
        system.setup()
        record["solver"]["setup_completed"] = True
        record["inventory"]["regcv1"] = _regcv1_inventory(system)
        record["inventory"]["disabled_dynamic_chain"] = _disabled_inventory(
            system, contract["disabled_chain_models"]
        )

        pflow_return = system.PFlow.run()
        record["solver"]["pflow_converged"] = bool(pflow_return)
        if not pflow_return:
            record["scientific_error"] = "PFlow.run returned a non-success value"
            return record

        idxes = [row["idx"] for row in contract["expected_mapping"]]
        record["interface_identity"] = _probe_setpoint_identity(system, idxes)
        if record["interface_identity"]["completed"] is not True:
            record["scientific_error"] = record["interface_identity"]["error"]
            return record

        system.TDS.config.tf = float(contract["tds_tf_seconds"])
        init_return = system.TDS.init()
        record["solver"]["tds_initialized"] = init_return is not False
        record["solver"]["tds_test_ok"] = system.TDS.test_ok is True
        if not (
            record["solver"]["tds_initialized"]
            and record["solver"]["tds_test_ok"]
        ):
            record["scientific_error"] = "native TDS initialization guard failed"
            return record

        initial = _signal_snapshot(system, contract["drift_signals"])
        record["physical_trajectory_executed"] = True
        record["trajectory_count"] = 1
        system.TDS.run()
        record["solver"]["tds_converged"] = bool(system.TDS.converged)
        record["solver"]["terminal_time_seconds"] = float(system.dae.t)
        terminal = _signal_snapshot(system, contract["drift_signals"])
        dae_finite, model_finite = _finite_guards(system)
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
        record["scientific_error"] = f"{type(exc).__name__}: {exc}"
        if system is not None:
            try:
                record["solver"]["terminal_time_seconds"] = float(system.dae.t)
                dae_finite, model_finite = _finite_guards(system)
                record["finite_guard"] = {
                    "checked": True,
                    "dae_finite": dae_finite,
                    "regcv1_finite": model_finite,
                }
                if initial is not None:
                    terminal = _signal_snapshot(system, contract["drift_signals"])
                    record["drift"] = {
                        "checked": True,
                        "max_abs_by_signal": {
                            name: float(
                                np.max(np.abs(terminal[name] - initial[name]))
                            )
                            for name in contract["drift_signals"]
                        },
                    }
            except Exception:
                pass
    return record


def execute(*, expected_sha256: str, out_dir: Path = DEFAULT_OUT) -> str:
    _assert_wsl_scratch()
    seal, seal_digest = _load_seal(expected_sha256)
    other = _other_research_python_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    if out_dir.exists():
        raise FileExistsError(f"R384 output collision: {out_dir}")
    attempt_digest = _write_new_json(
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
        record = _run_formal_record(seal["contract"])
        execution = {
            **record,
            "seal_sha256": seal_digest,
            "attempt_sha256": attempt_digest,
            "wall_seconds": time.perf_counter() - started,
        }
        execution_digest = _write_new_json(
            out_dir / "formal_execution.json", execution
        )
        analysis = classify_regcv1_object_record(
            record, contract=seal["contract"]
        )
        analysis.update(
            {
                "seal_sha256": seal_digest,
                "formal_execution_sha256": execution_digest,
                "training_authorized": False,
            }
        )
        analysis_digest = _write_new_json(
            out_dir / "formal_analysis.json", analysis
        )
        manifest_digest = _write_new_json(
            out_dir / "formal_manifest.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "entries": [
                    {
                        "path": _relative(out_dir / "formal_attempt.json"),
                        "sha256": attempt_digest,
                    },
                    {
                        "path": _relative(out_dir / "formal_execution.json"),
                        "sha256": execution_digest,
                    },
                    {
                        "path": _relative(out_dir / "formal_analysis.json"),
                        "sha256": analysis_digest,
                    },
                ],
            },
        )
        print(f"classification={analysis['classification']}", flush=True)
        print(f"manifest_sha256={manifest_digest}", flush=True)
        return analysis_digest
    except Exception as exc:
        _write_new_json(
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
        print(
            "analysis_sha256="
            f"{execute(expected_sha256=args.expected_seal_sha256)}"
        )
    else:  # pragma: no cover
        raise RuntimeError(f"unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
