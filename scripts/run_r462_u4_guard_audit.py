"""R462 JSON-safe successor for the byte-frozen R461 U4 computations."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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

import run_r461_u4_guard_audit as parent  # noqa: E402


ROUND = "R462"
PLAN = ROOT / "memory/rounds/R462/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
CAPACITY = ROOT / "memory/rounds/R462/capacity_evidence.json"
REHEARSAL = ROOT / "memory/rounds/R462/rehearsal.json"
SEAL = ROOT / "memory/rounds/R462/formal_seal.json"
OUT = ROOT / "results/research_loop/r462_u4_guard_audit"
R461_OUT = ROOT / "results/research_loop/r461_u4_guard_audit"

SOURCE_PATHS = {
    "successor_runner": Path(__file__).resolve(),
    "parent_runner": ROOT / "scripts/run_r461_u4_guard_audit.py",
    "parent_pure_audit": ROOT / "src/andes_rl_kundur/evaluation/u4_guard_audit.py",
    "parent_audit_tests": ROOT / "tests/test_u4_guard_audit.py",
    "parent_plan": ROOT / "memory/rounds/R461/plan.md",
    "parent_seal": ROOT / "memory/rounds/R461/formal_seal.json",
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
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    path.write_text(text, encoding="utf-8")
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def _write_jsonl_new(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def _authority(require_output_absent: bool) -> dict[str, bool]:
    plan = PLAN.read_text(encoding="utf-8")
    line = LINE.read_text(encoding="utf-8")
    r461_plan = (ROOT / "memory/rounds/R461/plan.md").read_text(encoding="utf-8")
    checks = {
        "active_plan": "round: R462" in plan and "state: active" in plan,
        "active_line": "line_id: yang-md-decoupling-marl" in line and "status: active" in line,
        "r461_aborted": "state: aborted" in r461_plan,
        "r461_partial_preserved": R461_OUT.is_dir(),
        "r461_seal_present": (ROOT / "memory/rounds/R461/formal_seal.json").is_file(),
    }
    if require_output_absent:
        checks["formal_output_absent"] = not OUT.exists()
    return checks


def _safe_value(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _safe_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_value(item) for item in value]
    return value


def _safe_phase_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    encoded = []
    for source in rows:
        row = _safe_value(source)
        nonfinite: list[dict[str, str]] = []
        for profile_id, residuals in source["profile_residuals"].items():
            for guard, value in residuals.items():
                if isinstance(value, float) and not math.isfinite(value):
                    nonfinite.append({"profile_id": profile_id, "guard": guard, "status": "positive_infinity"})
        row["t_status"] = "positive_infinity" if not math.isfinite(float(source["t"])) else "finite"
        row["nonfinite_residuals"] = nonfinite
        for item, source_item in zip(row["active_guards"], source["active_guards"], strict=True):
            item["residual_status"] = (
                "positive_infinity"
                if not math.isfinite(float(source_item["residual"]))
                else "finite"
            )
        encoded.append(row)
    text = json.dumps(encoded, allow_nan=False)
    if "Infinity" in text or "NaN" in text:
        raise RuntimeError("non-standard JSON token survived encoding")
    return encoded


def _independent_phase_checker(rows: list[dict[str, Any]], result: dict[str, Any]) -> dict[str, Any]:
    reconstructed = []
    for row in rows:
        if row["t_status"] == "positive_infinity":
            t_value = float("inf")
        elif row["t_status"] == "finite" and row["t"] is not None:
            t_value = float(row["t"])
        else:
            raise ValueError("invalid t encoding")
        reconstructed.append((t_value, str(row["candidate_id"]), row))
    reconstructed.sort(key=lambda item: (item[0], item[1]))
    winner_t, winner_id, winner = reconstructed[0]
    runner_t = reconstructed[1][0]
    expected = result["winner"]
    active = sorted(
        (item["profile_id"], item["guard"])
        for item in winner["active_guards"]
        if item["residual_status"] == "finite"
    )
    expected_active = sorted((item["profile_id"], item["guard"]) for item in expected["active_guards"])
    checks = {
        "candidate_count_350": len(rows) == 350,
        "candidate_ids_unique": len({row["candidate_id"] for row in rows}) == 350,
        "winner_id_match": winner_id == expected["candidate_id"],
        "winner_t_match": abs(winner_t - float(expected["t"])) <= 1e-15,
        "runner_up_margin_match": abs((runner_t - winner_t) - float(result["runner_up_margin"])) <= 1e-15,
        "active_guards_match": active == expected_active,
        "strict_json_safe": True,
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "reconstructed_winner_id": winner_id,
        "reconstructed_winner_t": winner_t,
        "reconstructed_runner_up_margin": runner_t - winner_t,
        "positive_infinity_candidate_count": sum(row["t_status"] == "positive_infinity" for row in rows),
    }


def _compute_safe() -> dict[str, Any]:
    result = parent._compute()
    rows = _safe_phase_rows(result["phase_rows"])
    checker = _independent_phase_checker(rows, result["phase"])
    strict_payloads = [rows, _safe_value(result["phase"]), result["summaries"], result["r431"]]
    for payload in strict_payloads:
        json.dumps(payload, allow_nan=False)
    result["safe_phase_rows"] = rows
    result["phase_checker"] = checker
    result["passed"] = bool(result["passed"] and checker["passed"])
    return result


def rehearse() -> None:
    if REHEARSAL.exists() or CAPACITY.exists():
        raise FileExistsError("R462 rehearsal/capacity already exists")
    authority = _authority(True)
    if not all(authority.values()):
        raise RuntimeError(f"authority failed: {authority}")
    start = time.perf_counter()
    result = _compute_safe()
    elapsed = time.perf_counter() - start
    inputs = parent._input_paths()
    capacity = {
        "round": ROUND,
        "created_utc": _utc(),
        "workload": "strict-JSON static reduction, no ANDES simulation",
        "input_file_count": len(inputs),
        "input_bytes": sum(path.stat().st_size for path in inputs),
        "selected_configuration": {"processes": 1, "native_threads_per_process": 1},
        "wall_seconds": elapsed,
        "cpu_logical": os.cpu_count(),
        "physical_capacity_anchor": _load(ROOT / "memory/rounds/R461/capacity_evidence.json")["physical_capacity_anchor"],
    }
    rehearsal = {
        "round": ROUND,
        "created_utc": _utc(),
        "authority": authority,
        "checks": {
            "parent_science_pass": result["passed"],
            "strict_json_pass": True,
            "phase_checker_pass": result["phase_checker"]["passed"],
            "positive_infinity_candidate_count": result["phase_checker"]["positive_infinity_candidate_count"],
        },
        "wall_seconds": elapsed,
    }
    _write_json_new(CAPACITY, capacity)
    _write_json_new(REHEARSAL, rehearsal)
    print(json.dumps(rehearsal["checks"], indent=2))


def prepare() -> None:
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R462 seal/output exists")
    authority = _authority(True)
    if not all(authority.values()):
        raise RuntimeError(f"authority failed: {authority}")
    rehearsal = _load(REHEARSAL)
    if not all(value is True for key, value in rehearsal["checks"].items() if key.endswith("_pass")):
        raise RuntimeError("R462 rehearsal failed")
    seal = {
        "round": ROUND,
        "created_utc": _utc(),
        "authority": authority,
        "single_factor_change": "strict JSON encoding of positive infinity as null plus explicit status",
        "sources": {
            name: {"path": _relative(path), "sha256": _sha256(path)}
            for name, path in SOURCE_PATHS.items()
        },
        "inputs": parent._manifest(parent._input_paths()),
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
    result = _compute_safe()
    if not result["passed"]:
        raise RuntimeError("formal checker failed")
    OUT.mkdir(parents=True, exist_ok=False)
    _write_json_new(OUT / "contracts/input_manifest.json", seal["inputs"])
    _write_json_new(OUT / "metrics/independent_profile_summaries.json", result["summaries"])
    _write_json_new(OUT / "metrics/canonical_comparison.json", result["metric"])
    _write_jsonl_new(OUT / "phase_i/candidate_residuals.jsonl", result["safe_phase_rows"])
    _write_json_new(OUT / "phase_i/exact_enumeration_result.json", _safe_value(result["phase"]))
    _write_json_new(OUT / "phase_i/independent_reconstruction.json", result["phase_checker"])
    _write_json_new(OUT / "constraints/r431_training_constraint_export.json", result["r431"])
    _write_json_new(OUT / "constraints/r456_intervention_export.json", result["r456_meta"])
    _write_jsonl_new(OUT / "constraints/r456_intervention_cells.jsonl", result["r456_rows"])
    _write_json_new(
        OUT / "provenance/runtime.json",
        {
            "wall_seconds": time.perf_counter() - start,
            "processes": 1,
            "native_threads_per_process": 1,
            "formal_seal_sha256": _sha256(SEAL),
        },
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
