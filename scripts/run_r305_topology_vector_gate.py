#!/usr/bin/env python3
"""Seal, canary, run, and analyse the R305 3x7 topology-information gate.

ANDES-facing commands (``prepare``, ``run-canary``, and ``run-shard``) must be launched with
the WSL interpreter through ``scripts/andes_scratch.py``.  ``eval-check`` and
``analyse`` are import-safe under Windows Python.  Every formal artifact is
create-only and accompanied by a SHA-256 sidecar.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import math
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for import_root in (ROOT / "src", ROOT / "probes"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

GATE_PATH = ROOT / "probes/r304_topology_vector_gate.py"
GATE_SPEC = importlib.util.spec_from_file_location("r304_topology_vector_gate", GATE_PATH)
if GATE_SPEC is None or GATE_SPEC.loader is None:
    raise RuntimeError(f"cannot load R304 gate: {GATE_PATH}")
gate: ModuleType = importlib.util.module_from_spec(GATE_SPEC)
GATE_SPEC.loader.exec_module(gate)

ROUND_ID = "R305"
QUESTION_ID = "Q-0061"
SHARD_COUNT = 3
CANARY_CELL = ("nominal", "q0")
POSITIVE_REAL_TOLERANCE = 1e-7
FREQUENCY_BAND_HZ = (0.2, 1.5)
AREA1_KEYS = ("genrou1", "genrou2", "vsg12", "vsg16")
AREA2_KEYS = ("genrou3", "genrou4", "vsg14", "vsg15")
PLAN = ROOT / "memory/rounds/R305/plan.md"
QUESTION = ROOT / "memory/questions/Q-0061.md"
DEFAULT_SEAL = ROOT / "memory/rounds/R305/topology_vector_gate_seal.json"
DEFAULT_OUT = ROOT / "results/r305_topology_vector_gate"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _payload_sha256(payload: object) -> str:
    compact = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(compact).hexdigest()


def _write_new_json(path: Path, payload: object) -> str:
    sidecar = path.with_name(path.name + ".sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"formal artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical_bytes(payload)
    digest = hashlib.sha256(data).hexdigest()
    with path.open("xb") as handle:
        handle.write(data)
    with sidecar.open("x", encoding="ascii", newline="\n") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def _read_verified_json(
    path: Path,
    expected_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    sidecar = path.with_name(path.name + ".sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"artifact or sidecar missing: {path}")
    digest = _sha256_file(path)
    recorded = sidecar.read_text(encoding="ascii").split()[0].lower()
    if digest != recorded:
        raise RuntimeError(f"sidecar mismatch for {path}")
    if expected_sha256 is not None and digest != expected_sha256.lower():
        raise RuntimeError(f"unexpected SHA-256 for {path}: {digest}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object: {path}")
    return payload, digest


def _path_text(path: Path) -> str:
    try:
        selected = path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        selected = path.resolve()
    return selected.as_posix()


def _runtime_record() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "andes": importlib.metadata.version("andes")
        if importlib.util.find_spec("andes") is not None
        else "not-installed",
    }


def _source_paths() -> dict[str, Path]:
    return {
        "plan": PLAN,
        "question": QUESTION,
        "adapter": Path(__file__).resolve(),
        "pure_gate": GATE_PATH,
        "vector_contract": ROOT
        / "src/andes_rl_kundur/control/vector_inertia_residual.py",
        "topology_status": ROOT
        / "src/andes_rl_kundur/evaluation/topology_status.py",
        "eval_v2": ROOT / "src/andes_rl_kundur/evaluation/eval_v2.py",
        "vector_environment": ROOT
        / "src/andes_rl_kundur/env/andes/distributed_residual_env.py",
        "vector_runner": ROOT
        / "src/andes_rl_kundur/evaluation/vector_residual.py",
        "v4_environment": ROOT
        / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "eval_tests": ROOT / "tests/test_eval_v2.py",
        "vector_control_tests": ROOT / "tests/test_vector_residual_control.py",
        "vector_evaluation_tests": ROOT
        / "tests/test_vector_residual_evaluation.py",
        "gate_tests": ROOT / "tests/test_r304_topology_vector_gate.py",
        "adapter_tests": ROOT / "tests/test_r305_topology_vector_adapter.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    missing = [path for path in _source_paths().values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing sealed sources: {missing}")
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _verify_sources(seal: dict[str, Any]) -> None:
    for name, entry in seal["sources"].items():
        path = ROOT / entry["path"]
        observed = _sha256_file(path)
        if observed != entry["sha256"]:
            raise RuntimeError(
                f"sealed source drift for {name}: {entry['sha256']} != {observed}"
            )


def _line_rows(system: Any) -> list[dict[str, Any]]:
    indices = [str(value) for value in system.Line.idx.v]
    rows: list[dict[str, Any]] = []
    for position, idx in enumerate(indices):
        row: dict[str, Any] = {
            "idx": idx,
            "position": position,
            "bus1": int(system.Line.bus1.v[position]),
            "bus2": int(system.Line.bus2.v[position]),
            "u": float(system.Line.u.v[position]),
        }
        for field in ("r", "x", "b", "b1", "b2"):
            owner = getattr(system.Line, field, None)
            values = getattr(owner, "v", None)
            row[field] = None if values is None else float(values[position])
        rows.append(row)
    return rows


def _g4_zeroed(system: Any) -> bool:
    position = list(system.GENROU.idx.v).index(4)
    return bool(
        abs(float(system.GENROU.M.v[position]) - 0.1) < 1e-9
        and abs(float(system.GENROU.D.v[position])) < 1e-9
    )


def _plant_counts(system: Any, vsg_positions: list[int]) -> dict[str, int]:
    return {
        "bus_count": len(system.Bus.idx.v),
        "line_count": len(system.Line.idx.v),
        "vsg_count": len(vsg_positions),
    }


def _return_summary(value: Any) -> dict[str, Any]:
    """Serialize only the type and shape of an opaque ANDES return value."""

    return {
        "python_type": type(value).__name__,
        "shape": list(np.shape(value)),
    }


def _scalar_truth(value: Any) -> bool:
    array = np.asarray(value)
    if array.shape != ():
        return False
    return bool(array.item())


def _return_explicitly_failed(value: Any) -> bool:
    if value is None:
        return False
    array = np.asarray(value)
    return bool(array.shape == () and not bool(array.item()))


def _run_pflow(system: Any) -> tuple[bool, dict[str, Any]]:
    """Run PFlow and read convergence only from its authoritative model state."""

    raw_return = system.PFlow.run()
    return _scalar_truth(system.PFlow.converged), _return_summary(raw_return)


def _build_system() -> tuple[Any, Any, list[int]]:
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4

    env = AndesMultiVSGEnvV4()
    system = env._build_system()
    positions = [list(system.GENCLS.idx.v).index(idx) for idx in env.vsg_idx]
    return env, system, positions


def _machine_state_indices(
    system: Any,
    vsg_positions: list[int],
) -> dict[str, int]:
    result: dict[str, int] = {}
    for position, idx in enumerate(system.GENROU.idx.v):
        result[f"genrou{int(idx)}"] = int(system.GENROU.omega.a[position])
    gencls_buses = list(system.GENCLS.bus.v)
    for position in vsg_positions:
        result[f"vsg{int(gencls_buses[position])}"] = int(
            system.GENCLS.omega.a[position]
        )
    vsg_set = set(vsg_positions)
    for position in range(len(system.GENCLS.idx.v)):
        if position not in vsg_set:
            result[f"gencls_bus{int(gencls_buses[position])}"] = int(
                system.GENCLS.omega.a[position]
            )
    return result


def _assigned_cells(shard_index: int, shard_count: int) -> list[tuple[str, str]]:
    if shard_count != SHARD_COUNT:
        raise ValueError(f"R305 requires exactly {SHARD_COUNT} shards")
    if not 0 <= shard_index < shard_count:
        raise ValueError("shard_index must lie in [0, shard_count)")
    cells = [
        (topology, action)
        for topology in gate.TOPOLOGY_ORDER
        for action in gate.ACTION_LIBRARY
        if (topology, action) != CANARY_CELL
    ]
    return cells[shard_index::shard_count]


def _contract() -> dict[str, Any]:
    return {
        "topologies": [
            {"name": topology, "opened_line": gate.OPENED_LINES[topology]}
            for topology in gate.TOPOLOGY_ORDER
        ],
        "actions": {
            "order": list(gate.ACTION_LIBRARY),
            "values": {
                name: list(values) for name, values in gate.ACTION_LIBRARY.items()
            },
            "coordinate": "R292 path-edge single-edge basis",
            "total_m_model_units": 1400.0,
            "common_m_model_units": 350.0,
        },
        "thresholds": dict(gate.DEFAULT_THRESHOLDS),
        "positive_real_tolerance": POSITIVE_REAL_TOLERANCE,
        "required_cell_guards": list(gate.REQUIRED_CELL_GUARDS),
        "mode_rule": {
            "frequency_band_hz": list(FREQUENCY_BAND_HZ),
            "conjugate_merge": True,
            "pick": "max abs(P_area1-P_area2) on machine omega participation",
        },
        "matrix_shape": [3, 7],
        "shard_count": SHARD_COUNT,
        "execution_staging": {
            "canary_cell": list(CANARY_CELL),
            "remaining_cells": 20,
            "expand_only_after_canary_pass": True,
        },
        "eval_profile": "vector_inertia",
    }


def prepare(seal_path: Path, out_dir: Path) -> None:
    seal_path = seal_path.resolve()
    out_dir = out_dir.resolve()
    inventory_path = out_dir / "topology_inventory.json"
    if seal_path.exists() or inventory_path.exists():
        raise FileExistsError("R305 prepare artifacts already exist")

    _env, system, vsg_positions = _build_system()
    lines = _line_rows(system)
    by_id = {row["idx"]: row for row in lines}
    selected = [gate.OPENED_LINES[name] for name in gate.TOPOLOGY_ORDER[1:]]
    failures: list[str] = []
    for line_idx in selected:
        if line_idx not in by_id:
            failures.append(f"missing selected line {line_idx}")
        elif by_id[line_idx]["u"] != 1.0:
            failures.append(f"selected line is inactive: {line_idx}")
    if "Line_2" in selected:
        failures.append("Line_2 must remain excluded after its positive-mode finding")
    counts = _plant_counts(system, vsg_positions)
    if counts["vsg_count"] != 4:
        failures.append("R305 requires exactly four VSGs")
    if not _g4_zeroed(system):
        failures.append("G4 inertia/damping guard failed")
    if failures:
        raise RuntimeError(f"R305 topology inventory invalid: {failures}")
    sources = _sources()

    inventory = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "base_plant_counts": counts,
        "vsg_indices": [str(system.GENCLS.idx.v[position]) for position in vsg_positions],
        "vsg_buses": [int(system.GENCLS.bus.v[position]) for position in vsg_positions],
        "selected_lines": selected,
        "selected_line_records": {line_idx: by_id[line_idx] for line_idx in selected},
        "line_status_inventory": {row["idx"]: row["u"] for row in lines},
        "strict_local_discovery_supported": False,
        "execution_runtime": _runtime_record(),
        "reason": (
            "Line_0 and Line_9 are remote from all four VSG attachment buses; "
            "R305 studies configuration-conditioned action value only"
        ),
    }
    inventory_digest = _write_new_json(inventory_path, inventory)
    contract = _contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "topology_inventory": {
            "path": _path_text(inventory_path),
            "sha256": inventory_digest,
        },
        "sources": sources,
        "asset_protection": {
            "current_icems_line_read_only": True,
            "no_time_domain_performance": True,
            "no_training": True,
            "no_topology_generalization_claim": True,
            "formal_artifacts_create_only": True,
        },
    }
    seal_digest = _write_new_json(seal_path, seal)
    print(f"inventory_sha256={inventory_digest}", flush=True)
    print(f"seal_sha256={seal_digest}", flush=True)


def _load_seal(seal_path: Path, expected: str) -> tuple[dict[str, Any], str]:
    seal, digest = _read_verified_json(seal_path.resolve(), expected)
    if seal.get("round") != ROUND_ID or seal.get("question") != QUESTION_ID:
        raise RuntimeError("R305 seal identity mismatch")
    if _payload_sha256(seal["contract"]) != seal["contract_payload_sha256"]:
        raise RuntimeError("R305 sealed contract payload drift")
    if seal["contract"] != _contract():
        raise RuntimeError("R305 runtime contract does not match sealed contract")
    _verify_sources(seal)
    _read_verified_json(
        ROOT / seal["topology_inventory"]["path"],
        seal["topology_inventory"]["sha256"],
    )
    return seal, digest


def _cell_path(out_dir: Path, topology: str, action: str) -> Path:
    return out_dir / "cells" / f"{topology}__{action}.json"


def _run_cell(
    *,
    topology: str,
    action: str,
    expected_counts: dict[str, int],
) -> dict[str, Any]:
    from andes_rl_kundur.evaluation.topology_status import (
        apply_line_outage,
        eig_validity_guard,
    )

    _env, system, vsg_positions = _build_system()
    m_vector = gate.ACTION_LIBRARY[action]
    for position, value in zip(vsg_positions, m_vector, strict=True):
        system.GENCLS.set(
            "M",
            system.GENCLS.idx.v[position],
            float(value),
            attr="v",
        )
    indices = [str(value) for value in system.Line.idx.v]
    before = [float(value) for value in system.Line.u.v]
    opened_line = gate.OPENED_LINES[topology]
    if opened_line != "none":
        apply_line_outage(system, opened_line)
    after = [float(value) for value in system.Line.u.v]
    changed = [
        idx
        for idx, old, new in zip(indices, before, after, strict=True)
        if abs(old - new) > 1e-12
    ]
    expected_changed = [] if opened_line == "none" else [opened_line]
    counts = _plant_counts(system, vsg_positions)
    readback_m = [float(system.GENCLS.M.v[position]) for position in vsg_positions]
    guards: dict[str, bool] = {
        "pflow_converged": False,
        "g4_zeroed": _g4_zeroed(system),
        "total_m_pass": abs(sum(readback_m) - 1400.0) < 1e-6,
        "action_value_pass": bool(
            np.allclose(readback_m, m_vector, rtol=0.0, atol=1e-9)
        ),
        "opened_line_pass": changed == expected_changed,
        "bus_count_pass": counts["bus_count"] == expected_counts["bus_count"],
        "vsg_count_pass": counts["vsg_count"] == expected_counts["vsg_count"],
        "initialization_pass": False,
        "tds_test_ok": False,
        "system_exit_zero": False,
        "residual_pass": False,
        "eig_run_pass": False,
        "spectrum_finite": False,
        "spectrum_pass": False,
    }
    pflow_converged, pflow_return_summary = _run_pflow(system)
    guards["pflow_converged"] = pflow_converged
    tds_init_return: Any = False
    eig_return: Any = False
    topology_status: dict[str, Any] = {}
    identified = None
    modes: list[dict[str, Any]] = []
    if guards["pflow_converged"]:
        tds_init_return = system.TDS.init()
        if _scalar_truth(getattr(system.TDS, "initialized", False)):
            eig_return = system.EIG.run()
            eigenvalues = np.asarray(system.EIG.mu)
            guards["eig_run_pass"] = bool(
                not _return_explicitly_failed(eig_return) and eigenvalues.size > 0
            )
            if guards["eig_run_pass"]:
                topology_status = eig_validity_guard(
                    system,
                    positive_real_tolerance=POSITIVE_REAL_TOLERANCE,
                )
                guards.update(
                    {
                        "initialization_pass": bool(
                            topology_status["initialization_pass"]
                        ),
                        "tds_test_ok": bool(topology_status["tds_test_ok"]),
                        "system_exit_zero": topology_status["system_exit_code"] == 0,
                        "residual_pass": bool(topology_status["residual_pass"]),
                        "spectrum_finite": bool(topology_status["spectrum_finite"]),
                        "spectrum_pass": bool(topology_status["spectrum_pass"]),
                    }
                )
            if guards["eig_run_pass"] and topology_status["spectrum_finite"]:
                system.EIG.calc_pfactor()
                eigenvalues = np.asarray(system.EIG.mu)
                pfactors = np.abs(np.asarray(system.EIG.pfactors))
                machine_states = _machine_state_indices(system, vsg_positions)
                for mode_index, eigenvalue in enumerate(eigenvalues):
                    if eigenvalue.real >= 0.0:
                        continue
                    frequency = abs(eigenvalue.imag) / (2.0 * math.pi)
                    if not FREQUENCY_BAND_HZ[0] <= frequency <= FREQUENCY_BAND_HZ[1]:
                        continue
                    modes.append(
                        {
                            "freq_hz": float(frequency),
                            "damping_ratio": float(-eigenvalue.real / abs(eigenvalue)),
                            "real": float(eigenvalue.real),
                            "p_machines": {
                                key: float(pfactors[state_index, mode_index])
                                for key, state_index in machine_states.items()
                            },
                        }
                    )
                modes = gate.merge_conjugate_pairs(modes)
                identified = gate.identify_interarea(
                    modes,
                    area1_keys=AREA1_KEYS,
                    area2_keys=AREA2_KEYS,
                )
    status_detail = {
        **topology_status,
        "topology": topology,
        "opened_line": opened_line,
        "changed_lines": changed,
        "pflow_return": pflow_return_summary,
        "tds_init_return": _return_summary(tds_init_return),
        "eig_return": _return_summary(eig_return),
    }
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "topology": topology,
        "opened_line": opened_line,
        "action": action,
        "m_vector": list(m_vector),
        "actual_m_readback": readback_m,
        "guards": guards,
        "topology_status": status_detail,
        "identified": identified,
        "n_modes_merged": len(modes),
        "execution_runtime": _runtime_record(),
    }


def _canary_manifest_path(out_dir: Path) -> Path:
    return out_dir / "canary.json"


def _canary_analysis_path(out_dir: Path) -> Path:
    return out_dir / "canary_analysis.json"


def _identified_mode_failures(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["identified"]
    failures: list[str] = []
    try:
        if not isinstance(value["p_vector"], list) or not isinstance(
            value["p_keys"], list
        ):
            return ["identified_malformed"]
        frequency = float(value["freq_hz"])
        damping = float(value["damping_ratio"])
        vector = tuple(float(item) for item in value["p_vector"])
        keys = tuple(value["p_keys"])
    except (KeyError, TypeError, ValueError):
        return ["identified_malformed"]
    if not (
        math.isfinite(frequency)
        and FREQUENCY_BAND_HZ[0] <= frequency <= FREQUENCY_BAND_HZ[1]
    ):
        failures.append("identified_frequency")
    if not math.isfinite(damping) or damping <= 0.0:
        failures.append("identified_damping")
    if not vector or not all(math.isfinite(item) for item in vector):
        failures.append("identified_p_vector")
    if (
        not keys
        or len(keys) != len(vector)
        or len(set(keys)) != len(keys)
        or any(not isinstance(key, str) or not key for key in keys)
        or keys != tuple(sorted(keys))
    ):
        failures.append("identified_p_keys")
    return failures


def _runtime_failures(value: Any) -> list[str]:
    expected = {"python", "platform", "andes"}
    if not isinstance(value, dict) or set(value) != expected:
        return ["execution_runtime"]
    if any(not isinstance(value[key], str) or not value[key] for key in expected):
        return ["execution_runtime"]
    return []


def _canary_cell_failures(cell: dict[str, Any]) -> list[str]:
    topology, action = CANARY_CELL
    failures: list[str] = []
    expected_identity = {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "topology": topology,
        "opened_line": gate.OPENED_LINES[topology],
        "action": action,
    }
    for key, expected in expected_identity.items():
        if cell.get(key) != expected:
            failures.append(key)
    if cell.get("m_vector") != list(gate.ACTION_LIBRARY[action]):
        failures.append("m_vector")
    guards = cell.get("guards")
    expected_guards = set(gate.REQUIRED_CELL_GUARDS)
    if not isinstance(guards, dict) or set(guards) != expected_guards:
        failures.append("guard_keys")
    if not isinstance(guards, dict) or not all(
        guards.get(guard) is True for guard in gate.REQUIRED_CELL_GUARDS
    ):
        failures.append("guards_pass")
    failures.extend(_identified_mode_failures(cell.get("identified")))
    failures.extend(_runtime_failures(cell.get("execution_runtime")))
    if "execution_error" in cell:
        failures.append("execution_error")
    return failures


def _canary_decision(cell: dict[str, Any]) -> dict[str, Any]:
    failures = _canary_cell_failures(cell)
    passed = not failures
    return {
        "classification": (
            "CANARY-PASS-MATRIX-AUTHORIZED" if passed else "INVALID-CANARY"
        ),
        "canary_failures": failures,
        "matrix_expansion_authorized": passed,
        "training_gate": {
            "authorized": False,
            "training_executed": False,
            "next_step": "MATRIX" if passed else "STOP",
        },
    }


def _failed_cell(topology: str, action: str, exc: Exception) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "topology": topology,
        "opened_line": gate.OPENED_LINES[topology],
        "action": action,
        "m_vector": list(gate.ACTION_LIBRARY[action]),
        "guards": {guard: False for guard in gate.REQUIRED_CELL_GUARDS},
        "identified": None,
        "execution_error": f"{type(exc).__name__}: {exc}",
        "execution_runtime": _runtime_record(),
    }


def _verify_canary(
    out_dir: Path,
    seal_digest: str,
    inventory_digest: str,
) -> tuple[dict[str, Any], str, str, str]:
    manifest_path = _canary_manifest_path(out_dir)
    manifest, manifest_digest = _read_verified_json(manifest_path)
    analysis_path = _canary_analysis_path(out_dir)
    analysis, analysis_digest = _read_verified_json(analysis_path)
    topology, action = CANARY_CELL
    cell_path = _cell_path(out_dir, topology, action)
    cell, cell_digest = _read_verified_json(cell_path)
    if manifest.get("round") != ROUND_ID or manifest.get("question") != QUESTION_ID:
        raise RuntimeError("R305 canary identity mismatch")
    if manifest.get("seal_sha256") != seal_digest:
        raise RuntimeError("R305 canary seal mismatch")
    if manifest.get("topology_inventory_sha256") != inventory_digest:
        raise RuntimeError("R305 canary topology inventory mismatch")
    if manifest.get("cell") != list(CANARY_CELL):
        raise RuntimeError("R305 canary cell mismatch")
    if manifest.get("cell_path") != _path_text(cell_path):
        raise RuntimeError("R305 canary cell path mismatch")
    if manifest.get("analysis_path") != _path_text(analysis_path):
        raise RuntimeError("R305 canary analysis path mismatch")
    if manifest.get("cell_sha256") != cell_digest:
        raise RuntimeError("R305 canary cell hash mismatch")
    if manifest.get("analysis_sha256") != analysis_digest:
        raise RuntimeError("R305 canary analysis hash mismatch")
    if cell.get("seal_sha256") != seal_digest:
        raise RuntimeError("R305 canary cell seal mismatch")
    if cell.get("topology_inventory_sha256") != inventory_digest:
        raise RuntimeError("R305 canary cell topology inventory mismatch")
    failures = _canary_cell_failures(cell)
    if analysis.get("cell_sha256") != cell_digest:
        raise RuntimeError("R305 canary decision cell hash mismatch")
    if analysis.get("round") != ROUND_ID or analysis.get("question") != QUESTION_ID:
        raise RuntimeError("R305 canary decision identity mismatch")
    if analysis.get("seal_sha256") != seal_digest:
        raise RuntimeError("R305 canary decision seal mismatch")
    if analysis.get("topology_inventory_sha256") != inventory_digest:
        raise RuntimeError("R305 canary decision topology inventory mismatch")
    if analysis.get("classification") != "CANARY-PASS-MATRIX-AUTHORIZED":
        raise RuntimeError("R305 canary decision prohibits matrix expansion")
    if analysis.get("matrix_expansion_authorized") is not True:
        raise RuntimeError("R305 canary decision does not authorize matrix expansion")
    if analysis.get("canary_failures") != []:
        raise RuntimeError("R305 canary decision retains failures")
    if analysis.get("training_gate") != {
        "authorized": False,
        "training_executed": False,
        "next_step": "MATRIX",
    }:
        raise RuntimeError("R305 canary decision training gate mismatch")
    if manifest.get("passed") is not True or failures:
        raise RuntimeError("R305 canary did not pass; matrix expansion is prohibited")
    return cell, cell_digest, manifest_digest, analysis_digest


def run_canary(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    out_dir = out_dir.resolve()
    inventory, inventory_digest = _read_verified_json(
        ROOT / seal["topology_inventory"]["path"],
        seal["topology_inventory"]["sha256"],
    )
    topology, action = CANARY_CELL
    cell_path = _cell_path(out_dir, topology, action)
    manifest_path = _canary_manifest_path(out_dir)
    analysis_path = _canary_analysis_path(out_dir)
    if (
        cell_path.exists()
        or cell_path.with_name(cell_path.name + ".sha256").exists()
        or manifest_path.exists()
        or manifest_path.with_name(manifest_path.name + ".sha256").exists()
        or analysis_path.exists()
        or analysis_path.with_name(analysis_path.name + ".sha256").exists()
    ):
        raise FileExistsError("R305 canary artifacts already exist")
    try:
        cell = _run_cell(
            topology=topology,
            action=action,
            expected_counts=inventory["base_plant_counts"],
        )
    except Exception as exc:  # retained fail-closed formal canary
        cell = _failed_cell(topology, action, exc)
    cell.update(
        {
            "seal_sha256": seal_digest,
            "topology_inventory_sha256": inventory_digest,
            "created_utc": datetime.now(UTC).isoformat(),
        }
    )
    cell_digest = _write_new_json(cell_path, cell)
    decision = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "topology_inventory_sha256": inventory_digest,
        "cell_path": _path_text(cell_path),
        "cell_sha256": cell_digest,
        "execution_runtime": _runtime_record(),
        **_canary_decision(cell),
    }
    decision_digest = _write_new_json(analysis_path, decision)
    passed = decision["matrix_expansion_authorized"] is True
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "topology_inventory_sha256": inventory_digest,
        "cell": list(CANARY_CELL),
        "cell_path": _path_text(cell_path),
        "cell_sha256": cell_digest,
        "analysis_path": _path_text(analysis_path),
        "analysis_sha256": decision_digest,
        "passed": passed,
        "execution_runtime": _runtime_record(),
    }
    manifest_digest = _write_new_json(manifest_path, manifest)
    print(f"canary_pass={passed}", flush=True)
    print(f"canary_classification={decision['classification']}", flush=True)
    print(f"canary_analysis_sha256={decision_digest}", flush=True)
    print(f"canary_sha256={manifest_digest}", flush=True)
    if not passed:
        raise RuntimeError("R305 canary failed; matrix expansion is prohibited")


def run_shard(
    seal_path: Path,
    expected: str,
    out_dir: Path,
    shard_index: int,
    shard_count: int,
) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    out_dir = out_dir.resolve()
    inventory, inventory_digest = _read_verified_json(
        ROOT / seal["topology_inventory"]["path"],
        seal["topology_inventory"]["sha256"],
    )
    _verify_canary(out_dir, seal_digest, inventory_digest)
    assigned = _assigned_cells(shard_index, shard_count)
    targets = [_cell_path(out_dir, topology, action) for topology, action in assigned]
    shard_path = out_dir / "shards" / f"shard_{shard_index}_of_{shard_count}.json"
    if shard_path.exists() or any(
        path.exists() or path.with_name(path.name + ".sha256").exists()
        for path in targets
    ):
        raise FileExistsError(f"R305 shard {shard_index} has existing artifacts")

    cell_hashes: dict[str, str] = {}
    for topology, action in assigned:
        try:
            cell = _run_cell(
                topology=topology,
                action=action,
                expected_counts=inventory["base_plant_counts"],
            )
        except Exception as exc:  # retained fail-closed formal cell
            cell = _failed_cell(topology, action, exc)
        cell.update(
            {
                "seal_sha256": seal_digest,
                "topology_inventory_sha256": inventory_digest,
                "created_utc": datetime.now(UTC).isoformat(),
            }
        )
        path = _cell_path(out_dir, topology, action)
        digest = _write_new_json(path, cell)
        cell_hashes[_path_text(path)] = digest
        print(
            f"{topology}/{action}: "
            f"guards={all(cell['guards'].values())} "
            f"identified={cell.get('identified') is not None}",
            flush=True,
        )
    shard = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "topology_inventory_sha256": inventory_digest,
        "shard_index": shard_index,
        "shard_count": shard_count,
        "assigned_cells": [list(item) for item in assigned],
        "cell_hashes": cell_hashes,
        "execution_runtime": _runtime_record(),
    }
    digest = _write_new_json(shard_path, shard)
    print(f"shard_sha256={digest}", flush=True)


def eval_check(seal_path: Path, expected: str, out_dir: Path) -> None:
    _seal, seal_digest = _load_seal(seal_path, expected)
    output = out_dir.resolve() / "eval_readiness.json"
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_eval_v2.py",
        "tests/test_vector_residual_control.py",
        "tests/test_vector_residual_evaluation.py",
        "-q",
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    from andes_rl_kundur.evaluation.eval_v2 import (
        EXECUTION_PROFILE_SPECS,
        VECTOR_INERTIA_EXECUTION_PROFILE,
    )

    profile_present = (
        VECTOR_INERTIA_EXECUTION_PROFILE == "vector_inertia"
        and VECTOR_INERTIA_EXECUTION_PROFILE in EXECUTION_PROFILE_SPECS
    )
    result = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "check_scope": "execution-contract tests only; no performance endpoint",
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "profile_present": profile_present,
        "passed": completed.returncode == 0 and profile_present,
        "evidence_status": "EXTERNAL_AUTHORITY_REQUIRED",
    }
    digest = _write_new_json(output, result)
    print(f"eval_ready={result['passed']}", flush=True)
    print(f"eval_readiness_sha256={digest}", flush=True)
    if not result["passed"]:
        raise RuntimeError("R305 vector_inertia EVAL readiness failed")


def analyse(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    out_dir = out_dir.resolve()
    inventory, inventory_digest = _read_verified_json(
        ROOT / seal["topology_inventory"]["path"],
        seal["topology_inventory"]["sha256"],
    )
    eval_readiness, eval_digest = _read_verified_json(out_dir / "eval_readiness.json")
    if eval_readiness.get("seal_sha256") != seal_digest:
        raise RuntimeError("EVAL readiness does not belong to the R305 seal")
    (
        canary_cell,
        canary_cell_digest,
        canary_manifest_digest,
        canary_analysis_digest,
    ) = _verify_canary(out_dir, seal_digest, inventory_digest)
    cells: list[dict[str, Any]] = []
    cell_hashes: dict[str, str] = {}
    for topology in gate.TOPOLOGY_ORDER:
        for action in gate.ACTION_LIBRARY:
            path = _cell_path(out_dir, topology, action)
            if (topology, action) == CANARY_CELL:
                cell, digest = canary_cell, canary_cell_digest
            else:
                cell, digest = _read_verified_json(path)
            if cell.get("seal_sha256") != seal_digest:
                raise RuntimeError(f"cell seal mismatch: {path}")
            if cell.get("topology_inventory_sha256") != inventory_digest:
                raise RuntimeError(f"cell topology inventory mismatch: {path}")
            if _runtime_failures(cell.get("execution_runtime")):
                raise RuntimeError(f"cell execution runtime missing: {path}")
            cells.append(cell)
            cell_hashes[_path_text(path)] = digest
    shard_hashes: dict[str, str] = {}
    observed_assignments: list[tuple[str, str]] = []
    for shard_index in range(SHARD_COUNT):
        shard_path = (
            out_dir / "shards" / f"shard_{shard_index}_of_{SHARD_COUNT}.json"
        )
        shard, shard_digest = _read_verified_json(shard_path)
        expected_assignment = _assigned_cells(shard_index, SHARD_COUNT)
        if shard.get("seal_sha256") != seal_digest:
            raise RuntimeError(f"shard seal mismatch: {shard_path}")
        if shard.get("topology_inventory_sha256") != inventory_digest:
            raise RuntimeError(f"shard topology inventory mismatch: {shard_path}")
        if shard.get("shard_index") != shard_index or shard.get("shard_count") != SHARD_COUNT:
            raise RuntimeError(f"shard identity mismatch: {shard_path}")
        if shard.get("assigned_cells") != [list(item) for item in expected_assignment]:
            raise RuntimeError(f"shard assignment mismatch: {shard_path}")
        expected_hashes = {
            _path_text(_cell_path(out_dir, topology, action)): cell_hashes[
                _path_text(_cell_path(out_dir, topology, action))
            ]
            for topology, action in expected_assignment
        }
        if shard.get("cell_hashes") != expected_hashes:
            raise RuntimeError(f"shard cell hash manifest mismatch: {shard_path}")
        if _runtime_failures(shard.get("execution_runtime")):
            raise RuntimeError(f"shard execution runtime missing: {shard_path}")
        observed_assignments.extend(expected_assignment)
        shard_hashes[_path_text(shard_path)] = shard_digest
    expected_all = [
        (topology, action)
        for topology in gate.TOPOLOGY_ORDER
        for action in gate.ACTION_LIBRARY
        if (topology, action) != CANARY_CELL
    ]
    if sorted(observed_assignments) != sorted(expected_all):
        raise RuntimeError("three shard manifests do not cover the exact 20 post-canary cells")
    matrix = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "topology_inventory_sha256": inventory_digest,
        "topologies": list(gate.TOPOLOGY_ORDER),
        "actions": list(gate.ACTION_LIBRARY),
        "cells": cells,
        "cell_hashes": cell_hashes,
        "shard_hashes": shard_hashes,
        "runtime": {
            "analysis": _runtime_record(),
            "execution": {
                json.dumps(cell["execution_runtime"], sort_keys=True): cell[
                    "execution_runtime"
                ]
                for cell in cells
            },
        },
    }
    matrix_path = out_dir / "eig_matrix.json"
    matrix_digest = _write_new_json(matrix_path, matrix)
    decision = gate.analyze_topology_vector_gate(
        matrix,
        eval_ready=eval_readiness.get("passed") is True,
        thresholds=seal["contract"]["thresholds"],
    )
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "topology_inventory_sha256": inventory_digest,
        "matrix_sha256": matrix_digest,
        "eval_readiness_sha256": eval_digest,
        **decision,
    }
    analysis_path = out_dir / "analysis.json"
    analysis_digest = _write_new_json(analysis_path, analysis)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal": {"path": _path_text(seal_path), "sha256": seal_digest},
        "topology_inventory": {
            "path": seal["topology_inventory"]["path"],
            "sha256": inventory_digest,
        },
        "matrix": {"path": _path_text(matrix_path), "sha256": matrix_digest},
        "canary": {
            "path": _path_text(_canary_manifest_path(out_dir)),
            "sha256": canary_manifest_digest,
            "analysis_path": _path_text(_canary_analysis_path(out_dir)),
            "analysis_sha256": canary_analysis_digest,
        },
        "shards": shard_hashes,
        "eval_readiness": {
            "path": _path_text(out_dir / "eval_readiness.json"),
            "sha256": eval_digest,
        },
        "analysis": {"path": _path_text(analysis_path), "sha256": analysis_digest},
        "sources_verified": seal["sources"],
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "topology_inventory_summary": {
            "selected_lines": inventory["selected_lines"],
            "strict_local_discovery_supported": inventory[
                "strict_local_discovery_supported"
            ],
        },
    }
    provenance_digest = _write_new_json(out_dir / "provenance.json", provenance)
    print(f"classification={analysis['classification']}", flush=True)
    print(f"analysis_sha256={analysis_digest}", flush=True)
    print(f"provenance_sha256={provenance_digest}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    prepare_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    canary_parser = commands.add_parser("run-canary")
    canary_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    canary_parser.add_argument("--expected-seal-sha256", required=True)
    canary_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    shard_parser = commands.add_parser("run-shard")
    shard_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    shard_parser.add_argument("--expected-seal-sha256", required=True)
    shard_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    shard_parser.add_argument("--shard-index", type=int, required=True)
    shard_parser.add_argument("--shard-count", type=int, default=SHARD_COUNT)
    eval_parser = commands.add_parser("eval-check")
    eval_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    eval_parser.add_argument("--expected-seal-sha256", required=True)
    eval_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    analyse_parser = commands.add_parser("analyse")
    analyse_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse_parser.add_argument("--expected-seal-sha256", required=True)
    analyse_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        prepare(args.seal, args.out_dir)
    elif args.command == "run-canary":
        run_canary(args.seal, args.expected_seal_sha256, args.out_dir)
    elif args.command == "run-shard":
        run_shard(
            args.seal,
            args.expected_seal_sha256,
            args.out_dir,
            args.shard_index,
            args.shard_count,
        )
    elif args.command == "eval-check":
        eval_check(args.seal, args.expected_seal_sha256, args.out_dir)
    else:
        analyse(args.seal, args.expected_seal_sha256, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
