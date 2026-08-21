"""R463 recursive empty-ledger correction for the U4 evidence export."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_name, "1")

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_r462_u4_guard_audit as parent  # noqa: E402


ROUND = "R463"
PLAN = ROOT / "memory/rounds/R463/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
CAPACITY = ROOT / "memory/rounds/R463/capacity_evidence.json"
REHEARSAL = ROOT / "memory/rounds/R463/rehearsal.json"
SEAL = ROOT / "memory/rounds/R463/formal_seal.json"
OUT = ROOT / "results/research_loop/r463_u4_guard_audit"
R462_OUT = ROOT / "results/research_loop/r462_u4_guard_audit"
SOURCE_PATHS = {
    "successor_runner": Path(__file__).resolve(),
    "parent_r462_runner": ROOT / "scripts/run_r462_u4_guard_audit.py",
    "parent_r461_runner": ROOT / "scripts/run_r461_u4_guard_audit.py",
    "pure_audit": ROOT / "src/andes_rl_kundur/evaluation/u4_guard_audit.py",
    "r462_plan": ROOT / "memory/rounds/R462/plan.md",
    "r462_seal": ROOT / "memory/rounds/R462/formal_seal.json",
    "plan": PLAN,
}


def _utc() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_new(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def _write_jsonl_new(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) for row in rows) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def _has_leaf_data(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, dict):
        return any(_has_leaf_data(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_leaf_data(item) for item in value)
    return True


def _correct_r431_export(source: dict[str, Any]) -> dict[str, Any]:
    export = copy.deepcopy(source)
    fields = ("episode_common_costs", "lagrange_trace", "guard_multipliers")
    for ledger in export["ledgers"]:
        availability = {
            field: "recorded" if _has_leaf_data(ledger[field]) else "not_recorded_in_original_training"
            for field in fields
        }
        ledger["field_availability"] = availability
        ledger["constraint_data_status"] = (
            "recorded" if any(value == "recorded" for value in availability.values())
            else "not_recorded_in_original_training"
        )
    export["presence_semantics"] = "recorded only if recursive traversal finds at least one non-container, non-null leaf datum"
    export["missing_constraint_ledger_count"] = sum(
        row["constraint_data_status"] == "not_recorded_in_original_training"
        for row in export["ledgers"]
    )
    export["recorded_constraint_ledger_count"] = len(export["ledgers"]) - export["missing_constraint_ledger_count"]
    return export


def _independent_ledger_check(export: dict[str, Any]) -> dict[str, Any]:
    mismatches = []
    source_files = sorted(parent.parent.R431.glob("train/*/seed*/manifest.json"))
    expected = {}
    for path in source_files:
        manifest = _load(path)
        key = (manifest["arm_id"], int(manifest["training_seed"]))
        expected[key] = {
            field: "recorded" if _has_leaf_data(manifest[field]) else "not_recorded_in_original_training"
            for field in ("episode_common_costs", "lagrange_trace", "guard_multipliers")
        }
    for ledger in export["ledgers"]:
        key = (ledger["arm_id"], int(ledger["training_seed"]))
        if ledger["field_availability"] != expected[key]:
            mismatches.append({"arm_id": key[0], "training_seed": key[1]})
    return {
        "source_manifest_count": len(source_files),
        "export_ledger_count": len(export["ledgers"]),
        "missing_ledger_count": export["missing_constraint_ledger_count"],
        "recorded_ledger_count": export["recorded_constraint_ledger_count"],
        "mismatches": mismatches,
        "passed": len(source_files) == len(export["ledgers"]) == 15 and not mismatches,
    }


def _compute() -> dict[str, Any]:
    result = parent._compute_safe()
    result["r431"] = _correct_r431_export(result["r431"])
    result["ledger_checker"] = _independent_ledger_check(result["r431"])
    result["passed"] = bool(result["passed"] and result["ledger_checker"]["passed"])
    return result


def _authority(require_output_absent: bool) -> dict[str, bool]:
    plan = PLAN.read_text(encoding="utf-8")
    line = LINE.read_text(encoding="utf-8")
    r462_plan = (ROOT / "memory/rounds/R462/plan.md").read_text(encoding="utf-8")
    checks = {
        "active_plan": "round: R463" in plan and "state: active" in plan,
        "active_line": "line_id: yang-md-decoupling-marl" in line and "status: active" in line,
        "r462_aborted": "state: aborted" in r462_plan,
        "r462_output_preserved": R462_OUT.is_dir(),
        "r462_seal_present": (ROOT / "memory/rounds/R462/formal_seal.json").is_file(),
    }
    if require_output_absent:
        checks["formal_output_absent"] = not OUT.exists()
    return checks


def rehearse() -> None:
    if CAPACITY.exists() or REHEARSAL.exists():
        raise FileExistsError("R463 rehearsal/capacity exists")
    authority = _authority(True)
    if not all(authority.values()):
        raise RuntimeError(f"authority failed: {authority}")
    start = time.perf_counter()
    result = _compute()
    elapsed = time.perf_counter() - start
    checks = {
        "all_parent_checks_pass": result["passed"],
        "ledger_checker_pass": result["ledger_checker"]["passed"],
        "all_15_ledgers_truthfully_missing": result["ledger_checker"]["missing_ledger_count"] == 15,
        "zero_recorded_ledgers": result["ledger_checker"]["recorded_ledger_count"] == 0,
    }
    _write_json_new(
        CAPACITY,
        {
            "round": ROUND,
            "created_utc": _utc(),
            "workload": "recursive-ledger plus static U4 reduction; no ANDES simulation",
            "selected_configuration": {"processes": 1, "native_threads_per_process": 1},
            "cpu_logical": os.cpu_count(),
            "wall_seconds": elapsed,
            "physical_capacity_anchor": _load(ROOT / "memory/rounds/R461/capacity_evidence.json")["physical_capacity_anchor"],
        },
    )
    _write_json_new(REHEARSAL, {"round": ROUND, "created_utc": _utc(), "authority": authority, "checks": checks})
    print(json.dumps(checks, indent=2))


def prepare() -> None:
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R463 seal/output exists")
    authority = _authority(True)
    if not all(authority.values()):
        raise RuntimeError(f"authority failed: {authority}")
    if not all(_load(REHEARSAL)["checks"].values()):
        raise RuntimeError("rehearsal failed")
    seal = {
        "round": ROUND,
        "created_utc": _utc(),
        "authority": authority,
        "single_factor_change": "recursive leaf-data presence predicate for R431 constraint ledgers",
        "sources": {name: {"path": _relative(path), "sha256": _sha256(path)} for name, path in SOURCE_PATHS.items()},
        "inputs": parent.parent._manifest(parent.parent._input_paths()),
        "capacity_evidence": {"path": _relative(CAPACITY), "sha256": _sha256(CAPACITY)},
        "rehearsal": {"path": _relative(REHEARSAL), "sha256": _sha256(REHEARSAL)},
        "formal_output": _relative(OUT),
        "launch": {"processes": 1, "native_threads_per_process": 1, "retry_policy": "none"},
    }
    print(_write_json_new(SEAL, seal))


def _verify_seal() -> dict[str, Any]:
    seal = _load(SEAL)
    for name, row in seal["sources"].items():
        if _sha256(ROOT / row["path"]) != row["sha256"]:
            raise RuntimeError(f"source drift: {name}")
    for row in seal["inputs"]:
        if _sha256(ROOT / row["path"]) != row["sha256"]:
            raise RuntimeError(f"input drift: {row['path']}")
    return seal


def run() -> None:
    if OUT.exists():
        raise FileExistsError(OUT)
    seal = _verify_seal()
    start = time.perf_counter()
    result = _compute()
    if not result["passed"]:
        raise RuntimeError("formal checker failed")
    OUT.mkdir(parents=True, exist_ok=False)
    _write_json_new(OUT / "contracts/input_manifest.json", seal["inputs"])
    _write_json_new(OUT / "metrics/independent_profile_summaries.json", result["summaries"])
    _write_json_new(OUT / "metrics/canonical_comparison.json", result["metric"])
    _write_jsonl_new(OUT / "phase_i/candidate_residuals.jsonl", result["safe_phase_rows"])
    _write_json_new(OUT / "phase_i/exact_enumeration_result.json", parent._safe_value(result["phase"]))
    _write_json_new(OUT / "phase_i/independent_reconstruction.json", result["phase_checker"])
    _write_json_new(OUT / "constraints/r431_training_constraint_export.json", result["r431"])
    _write_json_new(OUT / "constraints/r431_independent_availability_check.json", result["ledger_checker"])
    _write_json_new(OUT / "constraints/r456_intervention_export.json", result["r456_meta"])
    _write_jsonl_new(OUT / "constraints/r456_intervention_cells.jsonl", result["r456_rows"])
    _write_json_new(
        OUT / "provenance/runtime.json",
        {"wall_seconds": time.perf_counter() - start, "processes": 1, "native_threads_per_process": 1, "formal_seal_sha256": _sha256(SEAL)},
    )
    verification = {
        "round": ROUND,
        "created_utc": _utc(),
        "verdict": "U4-GUARD-AUDIT-VALID",
        "formal_seal_sha256": _sha256(SEAL),
        "metric_profile_count": result["metric"]["profile_count"],
        "metric_trajectory_count": result["metric"]["trajectory_count"],
        "metric_transition_count": result["metric"]["transition_count"],
        "metric_max_abs_error": result["metric"]["metric_max_abs_error"],
        "invalid_row_count": result["metric"]["invalid_row_count"],
        "tds_row_count": result["metric"]["tds_row_count"],
        "phase_i_classification": result["phase"]["classification"],
        "phase_i_winner": result["phase"]["winner"],
        "phase_i_runner_up_margin": result["phase"]["runner_up_margin"],
        "phase_i_guard_evaluation_count": result["phase"]["guard_evaluation_count"],
        "phase_i_positive_infinity_candidate_count": result["phase_checker"]["positive_infinity_candidate_count"],
        "phase_i_independent_reconstruction_pass": result["phase_checker"]["passed"],
        "r431_training_ledgers": result["r431"]["ledger_count"],
        "r431_missing_constraint_ledgers": result["r431"]["missing_constraint_ledger_count"],
        "r431_recorded_constraint_ledgers": result["r431"]["recorded_constraint_ledger_count"],
        "r431_independent_availability_check_pass": result["ledger_checker"]["passed"],
        "r456_intervention_cells": result["r456_meta"]["cell_count"],
        "all_checks_pass": True,
    }
    _write_json_new(OUT / "checks/verification_report.json", verification)
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (OUT / "checks/SHA256SUMS").write_text(
        "".join(f"{_sha256(path)}  {path.relative_to(OUT).as_posix()}\n" for path in files),
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(verification, ensure_ascii=False, indent=2, allow_nan=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("rehearse", "prepare", "run"))
    args = parser.parse_args()
    {"rehearse": rehearse, "prepare": prepare, "run": run}[args.command]()


if __name__ == "__main__":
    main()
