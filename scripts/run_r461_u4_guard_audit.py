"""R461 U4 independent metric, constraint-ledger, and phase-I audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_name, "1")

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import numpy as np  # noqa: E402

from andes_rl_kundur.evaluation.cd_matd3_canary import build_contract as build_r431_contract  # noqa: E402
from andes_rl_kundur.evaluation.md_decoupling_headroom import summarise_profile  # noqa: E402
from andes_rl_kundur.evaluation.u4_guard_audit import (  # noqa: E402
    NUMERIC_KEYS,
    TRANSFORM,
    enumerate_phase_i,
    independent_profile_summary,
)


ROUND = "R461"
PLAN = ROOT / "memory/rounds/R461/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
CAPACITY = ROOT / "memory/rounds/R461/capacity_evidence.json"
REHEARSAL = ROOT / "memory/rounds/R461/rehearsal.json"
SEAL = ROOT / "memory/rounds/R461/formal_seal.json"
OUT = ROOT / "results/research_loop/r461_u4_guard_audit"
R460 = ROOT / "results/research_loop/r460_u3_execution_semantics"
R452 = ROOT / "results/research_loop/r452_m5_all_candidate_pareto"
R431 = ROOT / "results/research_loop/r431_sac_slew"
R456 = ROOT / "results/research_loop/r456_m1_dual_saturation"

SOURCE_PATHS = {
    "runner": Path(__file__).resolve(),
    "pure_audit": ROOT / "src/andes_rl_kundur/evaluation/u4_guard_audit.py",
    "audit_tests": ROOT / "tests/test_u4_guard_audit.py",
    "canonical_summary": ROOT / "src/andes_rl_kundur/evaluation/md_decoupling_headroom.py",
    "r431_contract": ROOT / "src/andes_rl_kundur/evaluation/cd_matd3_canary.py",
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
    sidecar = Path(f"{path}.sha256")
    if sidecar.exists():
        raise FileExistsError(sidecar)
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def _write_jsonl_new(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def _input_paths() -> list[Path]:
    paths = sorted((R460 / "trajectories").glob("*.json"))
    paths += sorted((R452 / "profiles").glob("*.json"))
    paths += sorted(R431.glob("train/*/seed*/manifest.json"))
    paths += [R431 / "formal_manifest.json", R431 / "formal_analysis.json"]
    paths += [R456 / "intervention_manifest.json", R456 / "formal_analysis.json"]
    paths += sorted((R456 / "intervention").glob("*/*/seed*.json"))
    if len(sorted((R460 / "trajectories").glob("*.json"))) != 24:
        raise RuntimeError("R460 trajectory bank is not 24 files")
    if len(sorted((R452 / "profiles").glob("*.json"))) != 4:
        raise RuntimeError("R452 profile bank is not four files")
    if len(sorted(R431.glob("train/*/seed*/manifest.json"))) != 15:
        raise RuntimeError("R431 training manifest bank is not 15 files")
    if len(sorted((R456 / "intervention").glob("*/*/seed*.json"))) != 30:
        raise RuntimeError("R456 intervention bank is not 30 files")
    if not all(path.is_file() for path in paths):
        raise RuntimeError("required input missing")
    return paths


def _manifest(paths: list[Path]) -> list[dict[str, Any]]:
    return [
        {"path": _relative(path), "bytes": path.stat().st_size, "sha256": _sha256(path)}
        for path in paths
    ]


def _authority(require_output_absent: bool) -> dict[str, bool]:
    plan = PLAN.read_text(encoding="utf-8")
    line = LINE.read_text(encoding="utf-8")
    checks = {
        "active_plan": "round: R461" in plan and "state: active" in plan,
        "active_line": "line_id: yang-md-decoupling-marl" in line and "status: active" in line,
        "r460_complete": (R460 / "checks/verification_report.json").is_file(),
        "r452_complete": (R452 / "formal_analysis.json").is_file(),
        "r431_complete": (R431 / "formal_manifest.json").is_file(),
        "r456_complete": (R456 / "formal_analysis.json").is_file(),
    }
    if require_output_absent:
        checks["formal_output_absent"] = not OUT.exists()
    return checks


def _profiles_and_records() -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    contract = _load(R460 / "contracts/formal_contract.json")
    profiles: dict[str, dict[str, Any]] = {}
    for job in contract["jobs"]:
        profiles[str(job["profile"]["profile_id"])] = job["profile"]
    records: dict[str, list[dict[str, Any]]] = {profile_id: [] for profile_id in profiles}
    for path in sorted((R460 / "trajectories").glob("*.json")):
        record = _load(path)
        records[str(record["profile_id"])].append(record)
    return [profiles[key] for key in sorted(profiles)], records


def _canonical_contract(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "steps": 30,
        "dt_seconds": 0.2,
        "physical_nominal_frequency_hz": 60.0,
        "differential_transform": TRANSFORM.tolist(),
        "action_bounds": [-1.0, 1.0],
        "action_slew_limit": 0.25,
        "decoder": {
            "delta_m_negative": -200.0,
            "delta_m_positive": 600.0,
            "delta_d_negative": -200.0,
            "delta_d_positive": 600.0,
            "m_lower_clamp": 20.0,
            "d_lower_clamp": 10.0,
            "mapping_atol": 3.0517578125e-5,
        },
        "profiles": profiles,
    }


def _canonical_record(record: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "profile_id": record["profile_id"],
        "arm_id": record["rows"][0]["arm_id"],
        "scenario_id": record["scenario_id"],
        "pair_kind": record["pair_kind"],
        "sign": record["sign"],
        "magnitude": record["magnitude"],
        "completed": record["completed"],
        "tds_failed": record["tds_failed"],
        "initial_freq_hz_physical": record["initial_frequency_hz"],
        "identity": {
            "baseline_m0": profile["baseline_m0"],
            "baseline_d0": profile["baseline_d0"],
        },
        "steps": [
            {
                "freq_hz_physical": row["freq_hz_physical"],
                "action_norm": row["executed_action"],
                "delta_M": row["physical_command"]["delta_M"],
                "delta_D": row["physical_command"]["delta_D"],
                "M_es": row["physical_command"]["M_es"],
                "D_es": row["physical_command"]["D_es"],
            }
            for row in record["rows"]
        ],
    }


def _metric_audit() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    profiles, records = _profiles_and_records()
    contract = _canonical_contract(profiles)
    summaries: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    numeric_max = 0.0
    boolean_match = True
    for profile in profiles:
        profile_id = str(profile["profile_id"])
        raw_records = records[profile_id]
        independent = independent_profile_summary(raw_records, profile)
        canonical = summarise_profile(
            [_canonical_record(record, profile) for record in raw_records], contract=contract
        )
        numeric_errors = {key: abs(float(independent[key]) - float(canonical[key])) for key in NUMERIC_KEYS}
        settling_errors = {
            key: abs(
                float(independent["differential_settling_seconds"][key])
                - float(canonical["differential_settling_seconds"][key])
            )
            for key in ("common", "differential", "localized")
        }
        booleans = {
            key: independent[key] == canonical[key]
            for key in (
                "valid",
                "action_bound_violation",
                "action_slew_violation",
                "actuator_mapping_pass",
            )
        }
        numeric_max = max(numeric_max, *numeric_errors.values(), *settling_errors.values())
        boolean_match = boolean_match and all(booleans.values())
        summaries.append(independent)
        comparisons.append(
            {
                "profile_id": profile_id,
                "canonical_summary": canonical,
                "numeric_abs_errors": numeric_errors,
                "settling_abs_errors": settling_errors,
                "boolean_matches": booleans,
            }
        )
    all_completion = [row for summary in summaries for row in summary["completion_rows"]]
    verification = {
        "profile_count": len(summaries),
        "trajectory_count": len(all_completion),
        "transition_count": sum(row["row_count"] for row in all_completion),
        "completed_trajectory_count": sum(row["completed"] for row in all_completion),
        "invalid_row_count": sum(row["invalid_row_count"] for row in all_completion),
        "tds_row_count": sum(row["tds_row_count"] for row in all_completion),
        "metric_max_abs_error": numeric_max,
        "boolean_match": boolean_match,
        "minimum_response_normalizer": min(
            value for summary in summaries for value in summary["normalizers"].values()
        ),
        "passed": bool(
            len(summaries) == 4
            and len(all_completion) == 24
            and sum(row["row_count"] for row in all_completion) == 720
            and numeric_max <= 1e-10
            and boolean_match
            and all(summary["valid"] for summary in summaries)
        ),
        "comparisons": comparisons,
    }
    return summaries, verification


def _phase_audit() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tables = [_load(path) for path in sorted((R452 / "profiles").glob("*.json"))]
    result = enumerate_phase_i(tables)
    rows = result.pop("rows")
    stored_guard_mismatches: list[dict[str, Any]] = []
    table_map = {str(table["profile_id"]): table for table in tables}
    for row in rows:
        for profile_id, residuals in row["profile_residuals"].items():
            source = next(
                item for item in table_map[profile_id]["candidate_rows"]
                if item["candidate_id"] == row["candidate_id"]
            )
            stored = source["guards"]
            pairs = {
                "disturbance_differential_energy": stored["endpoint"]["disturbance_eligible"],
                "off_diagonal_response_energy": stored["endpoint"]["off_diagonal_eligible"],
                "common_frequency_iae_hz_s": stored["common_no_harm"]["common_frequency_iae_no_harm"],
                "worst_unit_peak_hz": stored["common_no_harm"]["worst_peak_no_harm"],
                "worst_rocof_hz_s": stored["common_no_harm"]["rocof_no_harm"],
                "action_rms": stored["action_stress_no_harm"]["action_rms_no_harm"],
                "action_total_variation": stored["action_stress_no_harm"]["action_variation_no_harm"],
                "action_saturation_fraction": stored["saturation_pass"],
            }
            for guard, stored_value in pairs.items():
                direct = residuals[guard] <= 1e-12
                if direct != bool(stored_value):
                    stored_guard_mismatches.append(
                        {"candidate_id": row["candidate_id"], "profile_id": profile_id, "guard": guard}
                    )
    denominators = []
    for table in tables:
        static = table["static"]
        for key, factor in (
            ("disturbance_differential_energy", 0.95),
            ("off_diagonal_response_energy", 0.95),
            ("common_frequency_iae_hz_s", 1.03),
            ("worst_unit_peak_hz", 1.03),
            ("worst_rocof_hz_s", 1.03),
            ("action_rms", 1.10),
            ("action_total_variation", 1.10),
        ):
            denominators.append(
                {"profile_id": table["profile_id"], "guard": key, "value": factor * float(static[key])}
            )
    result.update(
        {
            "profile_count": len(tables),
            "guard_evaluation_count": len(rows) * 4 * 8,
            "minimum_denominator": min(row["value"] for row in denominators),
            "denominators": denominators,
            "stored_guard_mismatch_count": len(stored_guard_mismatches),
            "stored_guard_mismatches": stored_guard_mismatches,
            "passed": len(rows) == 350 and len(stored_guard_mismatches) == 0,
        }
    )
    return rows, result


def _r431_export() -> dict[str, Any]:
    contract = build_r431_contract()
    ledgers = []
    for path in sorted(R431.glob("train/*/seed*/manifest.json")):
        manifest = _load(path)
        available = bool(
            manifest["episode_common_costs"]
            or manifest["lagrange_trace"]
            or manifest["guard_multipliers"]
        )
        ledgers.append(
            {
                "arm_id": manifest["arm_id"],
                "training_seed": manifest["training_seed"],
                "source_path": _relative(path),
                "source_sha256": _sha256(path),
                "interaction_steps": manifest["interaction_steps"],
                "episodes_attempted": manifest["episodes_attempted"],
                "tds_failed_episodes": manifest["tds_failed_episodes"],
                "episode_common_costs": manifest["episode_common_costs"],
                "lagrange_trace": manifest["lagrange_trace"],
                "guard_multipliers": manifest["guard_multipliers"],
                "constraint_data_status": "recorded" if available else "not_recorded_in_original_training",
            }
        )
    return {
        "round": ROUND,
        "source_round": "R431",
        "ledger_count": len(ledgers),
        "ledger_unit": "arm_x_training_seed",
        "learner_discount_gamma": contract["learner_contract"]["gamma"],
        "original_learner_scope": "unconstrained SAC/TD3 arms; no dual update was executed",
        "reference_constraint_definition": contract["reward_contract"]["cd_matd3"],
        "reference_constraint_warning": "definition belongs to the CD-MATD3 contract and is not an executed R431 SAC/TD3 constraint ledger",
        "ledgers": ledgers,
        "missing_constraint_ledger_count": sum(
            row["constraint_data_status"] == "not_recorded_in_original_training" for row in ledgers
        ),
    }


def _r456_export() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    manifest = _load(R456 / "intervention_manifest.json")
    rows = []
    for path in sorted((R456 / "intervention").glob("*/*/seed*.json")):
        rows.append(
            {
                "source_path": _relative(path),
                "source_sha256": _sha256(path),
                "payload": _load(path),
            }
        )
    analysis = _load(R456 / "formal_analysis.json")
    metadata = {
        "round": ROUND,
        "source_round": "R456",
        "scope": "frozen-network fresh-Adam post-hoc diagnostic",
        "original_training_reproduction": False,
        "kkt_certificate": False,
        "global_feasibility_certificate": False,
        "cell_count": len(rows),
        "manifest": manifest,
        "formal_analysis_sha256": _sha256(R456 / "formal_analysis.json"),
        "formal_analysis": analysis,
    }
    return metadata, rows, analysis


def _compute() -> dict[str, Any]:
    summaries, metric = _metric_audit()
    phase_rows, phase = _phase_audit()
    r431 = _r431_export()
    r456_meta, r456_rows, _ = _r456_export()
    passed = bool(
        metric["passed"]
        and phase["passed"]
        and r431["ledger_count"] == 15
        and r456_meta["cell_count"] == 30
    )
    return {
        "summaries": summaries,
        "metric": metric,
        "phase_rows": phase_rows,
        "phase": phase,
        "r431": r431,
        "r456_meta": r456_meta,
        "r456_rows": r456_rows,
        "passed": passed,
    }


def _resources(start: float) -> dict[str, Any]:
    memory = None
    try:
        import psutil

        memory = {
            "available_bytes": psutil.virtual_memory().available,
            "total_bytes": psutil.virtual_memory().total,
            "process_rss_bytes": psutil.Process().memory_info().rss,
        }
    except ImportError:
        pass
    gpu = None
    try:
        query = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if query.returncode == 0:
            gpu = query.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return {
        "wall_seconds": time.perf_counter() - start,
        "cpu_logical": os.cpu_count(),
        "platform": platform.platform(),
        "memory": memory,
        "gpu_query": gpu,
        "selected_processes": 1,
        "native_threads_per_process": 1,
        "selection_reason": "single dependency-ordered JSON reduction; parallel parsing duplicates I/O and serialization",
    }


def rehearse() -> None:
    if REHEARSAL.exists() or CAPACITY.exists():
        raise FileExistsError("R461 rehearsal/capacity already exists")
    authority = _authority(require_output_absent=True)
    if not all(authority.values()):
        raise RuntimeError(f"authority failed: {authority}")
    paths = _input_paths()
    start = time.perf_counter()
    result = _compute()
    resources = _resources(start)
    capacity = {
        "round": ROUND,
        "created_utc": _utc(),
        "workload": "deterministic static reduction, no ANDES simulation",
        "input_file_count": len(paths),
        "input_bytes": sum(path.stat().st_size for path in paths),
        "physical_capacity_anchor": {
            "source_round": "R460",
            "selected_trajectory_workers": 15,
            "orchestrator_processes": 1,
            "throughput_gain_vs_8_workers_fraction": 0.5096,
        },
        "resources": resources,
        "selected_configuration": {"processes": 1, "native_threads_per_process": 1},
    }
    rehearsal = {
        "round": ROUND,
        "created_utc": _utc(),
        "authority": authority,
        "input_manifest": _manifest(paths),
        "checks": {
            "computed": True,
            "overall_pass": result["passed"],
            "metric_pass": result["metric"]["passed"],
            "phase_pass": result["phase"]["passed"],
            "r431_ledgers": result["r431"]["ledger_count"],
            "r456_cells": result["r456_meta"]["cell_count"],
        },
        "resources": resources,
    }
    _write_json_new(CAPACITY, capacity)
    _write_json_new(REHEARSAL, rehearsal)
    print(json.dumps(rehearsal["checks"], indent=2))


def prepare() -> None:
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R461 seal/output already exists")
    authority = _authority(require_output_absent=True)
    if not all(authority.values()):
        raise RuntimeError(f"authority failed: {authority}")
    rehearsal = _load(REHEARSAL)
    if rehearsal["checks"]["overall_pass"] is not True:
        raise RuntimeError("rehearsal did not pass")
    sources = {
        name: {"path": _relative(path), "sha256": _sha256(path)}
        for name, path in SOURCE_PATHS.items()
    }
    inputs = _manifest(_input_paths())
    seal = {
        "round": ROUND,
        "created_utc": _utc(),
        "authority": authority,
        "sources": sources,
        "inputs": inputs,
        "capacity_evidence": {"path": _relative(CAPACITY), "sha256": _sha256(CAPACITY)},
        "rehearsal": {"path": _relative(REHEARSAL), "sha256": _sha256(REHEARSAL)},
        "launch": {"processes": 1, "native_threads_per_process": 1, "retry_policy": "none"},
        "formal_output": _relative(OUT),
        "prospective_verdicts": ["U4-GUARD-AUDIT-VALID", "U4-GUARD-AUDIT-INVALID", "ENGINEERING-INVALID"],
    }
    digest = _write_json_new(SEAL, seal)
    print(digest)


def _verify_seal() -> dict[str, Any]:
    seal = _load(SEAL)
    if seal["round"] != ROUND:
        raise RuntimeError("wrong seal round")
    for group in ("sources",):
        for name, row in seal[group].items():
            path = ROOT / row["path"]
            if _sha256(path) != row["sha256"]:
                raise RuntimeError(f"sealed source drift: {name}")
    for row in seal["inputs"]:
        if _sha256(ROOT / row["path"]) != row["sha256"]:
            raise RuntimeError(f"sealed input drift: {row['path']}")
    return seal


def run() -> None:
    if OUT.exists():
        raise FileExistsError(OUT)
    seal = _verify_seal()
    start = time.perf_counter()
    result = _compute()
    if not result["passed"]:
        raise RuntimeError("formal scientific checker failed before output creation")
    OUT.mkdir(parents=True, exist_ok=False)
    _write_json_new(OUT / "contracts/input_manifest.json", seal["inputs"])
    _write_json_new(OUT / "metrics/independent_profile_summaries.json", result["summaries"])
    _write_json_new(OUT / "metrics/canonical_comparison.json", result["metric"])
    _write_jsonl_new(OUT / "phase_i/candidate_residuals.jsonl", result["phase_rows"])
    _write_json_new(OUT / "phase_i/exact_enumeration_result.json", result["phase"])
    _write_json_new(OUT / "constraints/r431_training_constraint_export.json", result["r431"])
    _write_json_new(OUT / "constraints/r456_intervention_export.json", result["r456_meta"])
    _write_jsonl_new(OUT / "constraints/r456_intervention_cells.jsonl", result["r456_rows"])
    runtime = _resources(start)
    _write_json_new(OUT / "provenance/runtime.json", runtime)
    verification = {
        "round": ROUND,
        "created_utc": _utc(),
        "formal_seal_sha256": _sha256(SEAL),
        "verdict": "U4-GUARD-AUDIT-VALID",
        "metric": {key: value for key, value in result["metric"].items() if key != "comparisons"},
        "phase_i": {key: value for key, value in result["phase"].items() if key not in ("denominators", "stored_guard_mismatches")},
        "r431_training_ledgers": result["r431"]["ledger_count"],
        "r431_missing_constraint_ledgers": result["r431"]["missing_constraint_ledger_count"],
        "r456_intervention_cells": result["r456_meta"]["cell_count"],
        "all_checks_pass": True,
    }
    _write_json_new(OUT / "checks/verification_report.json", verification)
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    sums = "".join(f"{_sha256(path)}  {path.relative_to(OUT).as_posix()}\n" for path in files)
    (OUT / "checks/SHA256SUMS").write_text(sums, encoding="utf-8", newline="\n")
    print(json.dumps(verification, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("rehearse", "prepare", "run"))
    args = parser.parse_args()
    if args.command == "rehearse":
        rehearse()
    elif args.command == "prepare":
        prepare()
    else:
        run()


if __name__ == "__main__":
    main()
