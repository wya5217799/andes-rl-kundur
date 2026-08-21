"""R458: development-selected guard-clean schedule, evaluation out-of-sample test.

Why this round exists
---------------------
R453 showed guard-clean joint headroom for the 350-candidate time-varying
family on three of four *evaluation* profiles, but the family had only ever
been executed on those same evaluation profiles, so the selected schedule is
outcome-seeing (selection-on-evaluation).  R458 closes that gap without
retraining: it re-runs the identical frozen family on the two frozen
development profiles, selects exactly one schedule by a pre-registered
development-only rule, then evaluates that single schedule once on the four
evaluation profiles and reports per-profile guard feasibility.

Everything scientific is reused unchanged from sealed parent rounds:

* candidate sequence .................... R452.candidates()
* piecewise trajectory + summary ........ R452 (-> R439/R441)
* guard definition ...................... R452.candidate_guard
* static reference ...................... km3_kd2 (R416 development-selected)

Formal entry is WSL-only through ``scripts/andes_scratch.py``.  Physical
commands:

    python scripts/andes_scratch.py scripts/run_r458_dev_select_eval_validate.py capacity
    python scripts/andes_scratch.py scripts/run_r458_dev_select_eval_validate.py rehearse
    python scripts/andes_scratch.py scripts/run_r458_dev_select_eval_validate.py prepare
    # phase 1 (development): soft_spot_shard_driver with tmp/andes/r458_dev_shards.json
    python scripts/andes_scratch.py scripts/run_r458_dev_select_eval_validate.py select
    # phase 2 (evaluation): soft_spot_shard_driver with tmp/andes/r458_eval_shards.json
    python scripts/andes_scratch.py scripts/run_r458_dev_select_eval_validate.py aggregate
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
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

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

R452_RUNNER = ROOT / "scripts/run_r452_m5_all_candidate_pareto.py"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


R452 = _load_module("_r458_r452_parent", R452_RUNNER)

ROUND_ID = "R458"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
PLAN = ROOT / "memory/rounds/R458/plan.md"
REHEARSAL = ROOT / "memory/rounds/R458/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R458/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R458/formal_seal.json"
DEV_SHARDS = ROOT / "tmp/andes/r458_dev_shards.json"
EVAL_SHARDS = ROOT / "tmp/andes/r458_eval_shards.json"
OUT = ROOT / "results/research_loop/r458_dev_select_eval_validate"
SELECTION = OUT / "selection.json"

DEV_PROFILE_IDS = ("dev_a", "dev_b")
EVAL_PROFILE_IDS = ("eval_a", "eval_b", "eval_c", "eval_d")
ALL_PROFILE_IDS = (*DEV_PROFILE_IDS, *EVAL_PROFILE_IDS)
CHUNKS_PER_PROFILE = 16

# Reuse sealed primitives from R452/R439/R441 verbatim.
_sha256_file = R452._sha256_file
_write_new_json = R452._write_new_json
_read_hashed_json = R452._read_hashed_json
_relative = R452._relative
candidates = R452.candidates
candidate_chunks = R452.candidate_chunks
candidate_guard = R452.candidate_guard
_run_trajectory = R452.R439._run_trajectory
_evaluation_scenarios = R452.R439._evaluation_scenarios
_summarise_profile = R452.R441.summarise_profile
STATIC_SELECTED = R452.STATIC_SELECTED


def _profile_by_id(profile_id: str) -> dict[str, Any]:
    return next(
        profile
        for profile in R452.build_contract()["profiles"]
        if str(profile["profile_id"]) == profile_id
    )


def build_contract() -> dict[str, Any]:
    import copy

    contract = copy.deepcopy(R452.build_contract())
    contract["round"] = ROUND_ID
    contract["r458"] = {
        "parent_rounds": ["R439", "R441", "R452", "R453"],
        "development_profile_ids": list(DEV_PROFILE_IDS),
        "evaluation_profile_ids": list(EVAL_PROFILE_IDS),
        "candidate_sequence_sha256": R452.candidate_sequence_sha256(),
        "chunks_per_profile": CHUNKS_PER_PROFILE,
        "selection_rule": {
            "priority_1": "joint_guard_feasible on both development profiles, "
            "maximize sum(improvement_d + improvement_x), tie -> smallest global_index",
            "priority_2": "joint_guard_feasible on one development profile, "
            "maximize feasible-profile count then improvement sum, tie -> smallest global_index",
            "priority_3": "minimize worst relative guard violation across all 7 guard "
            "dimensions on both development profiles, tie -> smallest global_index",
        },
        "plan_sha256": _sha256_file(PLAN),
    }
    return contract


def contract_sha256() -> str:
    return R452.contract_sha256(build_contract())


def authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    return {
        "active_plan": "round: R458" in plan_text and "state: active" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "candidate_contract": len(candidates()) == 350
        and R452.candidate_sequence_sha256() == R452.EXPECTED_CANDIDATE_SHA256,
        "output_absence": not OUT.exists(),
        "shard_contract": len(expected_dev_shard_ids()) == 34
        and len(expected_eval_shard_ids()) == 8,
    }


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R458 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R458 must run through scripts/andes_scratch.py")


def load_seal() -> dict[str, Any]:
    seal = _read_hashed_json(SEAL)
    if seal.get("round") != ROUND_ID:
        raise RuntimeError("seal belongs to another round")
    if seal.get("contract_sha256") != contract_sha256():
        raise RuntimeError("contract drifted from seal")
    for name, entry in (seal.get("sources") or {}).items():
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed source drift: {name}")
    if _sha256_file(CAPACITY) != seal.get("capacity_sha256"):
        raise RuntimeError("capacity evidence drifted from seal")
    if _sha256_file(REHEARSAL) != seal.get("rehearsal_sha256"):
        raise RuntimeError("rehearsal drifted from seal")
    return seal


def expected_dev_shard_ids() -> list[str]:
    ids = [f"dev|static|{profile_id}" for profile_id in DEV_PROFILE_IDS]
    ids += [
        f"dev|candidate|{profile_id}|{chunk_index:02d}"
        for profile_id in DEV_PROFILE_IDS
        for chunk_index in range(CHUNKS_PER_PROFILE)
    ]
    return ids


def expected_eval_shard_ids() -> list[str]:
    ids = [f"eval|static|{profile_id}" for profile_id in EVAL_PROFILE_IDS]
    ids += [f"eval|winner|{profile_id}" for profile_id in EVAL_PROFILE_IDS]
    return ids


def _shard_path(kind: str, phase: str, profile_id: str, chunk_text: str) -> Path:
    if kind == "static":
        return OUT / "shards" / phase / profile_id / "static.json"
    if kind == "candidate":
        return OUT / "shards" / phase / profile_id / f"candidate_{chunk_text}.json"
    return OUT / "shards" / phase / profile_id / "winner.json"


def _run_summary(
    profile: Mapping[str, Any],
    *,
    static: bool = False,
    schedule: Sequence[Sequence[float]] | None = None,
) -> tuple[dict[str, Any] | None, list[str], int]:
    scenarios = _evaluation_scenarios(profile)
    records = [
        _run_trajectory(
            profile,
            scenario,
            static_arm=STATIC_SELECTED if static else None,
            timevarying=None
            if static
            else tuple((float(pair[0]), float(pair[1])) for pair in (schedule or ())),
        )
        for scenario in scenarios
    ]
    errors: list[str] = []
    for record in records:
        if not record.get("completed") or record.get("tds_failed"):
            errors.append(
                f"{record.get('scenario_id')}: {record.get('failure') or 'incomplete'}"
            )
    if errors:
        return None, errors, len(records)
    try:
        summary = _summarise_profile(records, contract=build_contract())
    except Exception as exc:  # noqa: BLE001
        return None, [f"summary: {type(exc).__name__}: {exc}"], len(records)
    return summary, [], len(records)


def run_shard(shard_id: str) -> str:
    _assert_wsl_scratch()
    load_seal()
    parts = shard_id.split("|")
    if parts[0] == "dev" and len(parts) >= 3:
        _, kind, profile_id = parts[0], parts[1], parts[2]
        chunk_text = parts[3] if len(parts) > 3 else "00"
        phase = "dev"
    elif parts[0] == "eval" and len(parts) >= 3:
        _, kind, profile_id = parts[0], parts[1], parts[2]
        chunk_text = "00"
        phase = "eval"
    else:
        raise ValueError(f"unregistered shard: {shard_id}")
    if shard_id not in expected_dev_shard_ids() + expected_eval_shard_ids():
        raise ValueError(f"unregistered shard: {shard_id}")
    profile = _profile_by_id(profile_id)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "round": ROUND_ID,
        "shard_id": shard_id,
        "kind": kind,
        "phase": phase,
        "profile_id": profile_id,
        "contract_sha256": contract_sha256(),
        "created_utc": datetime.now(UTC).isoformat(),
    }
    if kind == "static":
        summary, errors, trajectory_count = _run_summary(profile, static=True)
        payload.update(
            {
                "trajectory_count": trajectory_count,
                "summary": summary,
                "errors": errors,
                "valid_execution": not errors and summary is not None,
            }
        )
    elif kind == "candidate":
        chunk = candidate_chunks()[int(chunk_text)]
        rows = []
        trajectory_count = 0
        for candidate in chunk:
            summary, errors, count = _run_summary(
                profile, schedule=candidate["schedule"]
            )
            trajectory_count += count
            rows.append(
                {
                    **candidate,
                    "summary": summary,
                    "errors": errors,
                }
            )
        payload.update(
            {
                "chunk_index": int(chunk_text),
                "candidate_count": len(rows),
                "trajectory_count": trajectory_count,
                "candidate_ids": [row["candidate_id"] for row in rows],
                "rows": rows,
                "errors": [
                    f"{row['candidate_id']}: {error}"
                    for row in rows
                    for error in row["errors"]
                ],
                "valid_execution": all(
                    not row["errors"] and row["summary"] is not None for row in rows
                ),
            }
        )
    else:  # winner (evaluation phase)
        selection = _read_hashed_json(SELECTION)
        schedule = [
            [float(pair[0]), float(pair[1])] for pair in selection["winner"]["schedule"]
        ]
        summary, errors, trajectory_count = _run_summary(profile, schedule=schedule)
        payload.update(
            {
                "winner_candidate_id": selection["winner"]["candidate_id"],
                "winner_schedule": schedule,
                "trajectory_count": trajectory_count,
                "summary": summary,
                "errors": errors,
                "valid_execution": not errors and summary is not None,
            }
        )
    return _write_new_json(
        _shard_path(kind, phase, profile_id, chunk_text), payload
    )


def _guard_margin(
    static: Mapping[str, Any], summary: Mapping[str, Any]
) -> dict[str, float]:
    # Excess over the frozen guard bound; negative/zero means satisfied.
    guard = candidate_guard(summary, static)
    static_r_d = float(static["disturbance_differential_energy"])
    static_r_x = float(static["off_diagonal_response_energy"])
    r_d = float(summary["disturbance_differential_energy"])
    r_x = float(summary["off_diagonal_response_energy"])
    improvements = {
        "endpoint_d": (static_r_d - r_d) / max(static_r_d, 1e-12),
        "endpoint_x": (static_r_x - r_x) / max(static_r_x, 1e-12),
    }
    return {
        "endpoint_d": R452.IMPROVEMENT_MIN - improvements["endpoint_d"],
        "endpoint_x": R452.IMPROVEMENT_MIN - improvements["endpoint_x"],
        "common_frequency": float(summary["common_frequency_iae_hz_s"])
        / max(float(static["common_frequency_iae_hz_s"]), 1e-12)
        - (1.0 + R452.COMMON_HARM_MAX),
        "worst_peak": float(summary["worst_unit_peak_hz"])
        / max(float(static["worst_unit_peak_hz"]), 1e-12)
        - (1.0 + R452.COMMON_HARM_MAX),
        "rocof": float(summary["worst_rocof_hz_s"])
        / max(float(static["worst_rocof_hz_s"]), 1e-12)
        - (1.0 + R452.COMMON_HARM_MAX),
        "action_rms": float(summary["action_rms"])
        / max(float(static["action_rms"]), 1e-12)
        - (1.0 + R452.ACTION_STRESS_HARM_MAX),
        "action_tv": float(summary["action_total_variation"])
        / max(float(static["action_total_variation"]), 1e-12)
        - (1.0 + R452.ACTION_STRESS_HARM_MAX),
        "saturation": float(summary["action_saturation_fraction"])
        - R452.SATURATION_MAX,
        "_improvements": improvements,
    }


def _load_dev_rows(profile_id: str) -> tuple[Mapping[str, Any], list[dict[str, Any]]]:
    static_payload = _read_hashed_json(
        OUT / "shards" / "dev" / profile_id / "static.json"
    )
    static = static_payload["summary"]
    rows: list[dict[str, Any]] = []
    for chunk_index in range(CHUNKS_PER_PROFILE):
        payload = _read_hashed_json(
            OUT / "shards" / "dev" / profile_id / f"candidate_{chunk_index:02d}.json"
        )
        for raw in payload["rows"]:
            if raw.get("errors") or raw.get("summary") is None:
                raise RuntimeError(f"{profile_id} invalid candidate row")
            guard = candidate_guard(raw["summary"], static)
            rows.append(
                {
                    "candidate_id": raw["candidate_id"],
                    "global_index": raw["global_index"],
                    "k": raw["k"],
                    "schedule": raw["schedule"],
                    "summary": raw["summary"],
                    "guards": guard,
                }
            )
    return static, rows


def select() -> str:
    _assert_wsl_scratch()
    load_seal()
    for profile_id in DEV_PROFILE_IDS:
        _load_dev_rows(profile_id)
    # Build a per-candidate view over both development profiles.
    by_id: dict[str, dict[str, Any]] = {}
    per_profile: dict[str, dict[str, Any]] = {}
    for profile_id in DEV_PROFILE_IDS:
        static, rows = _load_dev_rows(profile_id)
        per_profile[profile_id] = {
            "static": static,
            "feasible_ids": [row["candidate_id"] for row in rows if row["guards"]["joint_guard_feasible"]],
        }
        for row in rows:
            cid = row["candidate_id"]
            entry = by_id.setdefault(
                cid,
                {
                    "candidate_id": cid,
                    "global_index": row["global_index"],
                    "k": row["k"],
                    "schedule": row["schedule"],
                    "profiles": {},
                    "feasible_count": 0,
                    "improvement_sum": 0.0,
                    "worst_margin": float("-inf"),
                },
            )
            margin = _guard_margin(static, row["summary"])
            improvement_sum = (
                margin["_improvements"]["endpoint_d"]
                + margin["_improvements"]["endpoint_x"]
            )
            entry["profiles"][profile_id] = {
                "joint_guard_feasible": bool(row["guards"]["joint_guard_feasible"]),
                "improvement_sum": improvement_sum,
                "margins": {k: v for k, v in margin.items() if not k.startswith("_")},
            }
            if row["guards"]["joint_guard_feasible"]:
                entry["feasible_count"] += 1
                entry["improvement_sum"] += improvement_sum
            # worst_margin = max over all 7 relative-guard violations (more
            # negative = further satisfied; positive = violated).
            violations = [float(v) for k, v in margin.items() if not k.startswith("_")]
            entry["worst_margin"] = max(entry["worst_margin"], max(violations))

    rows = sorted(by_id.values(), key=lambda r: int(r["global_index"]))
    p1 = [r for r in rows if r["feasible_count"] == 2]
    p2 = [r for r in rows if r["feasible_count"] == 1]
    if p1:
        branch = 1
        pool = p1
        pool.sort(
            key=lambda r: (-float(r["improvement_sum"]), int(r["global_index"]))
        )
    elif p2:
        branch = 2
        pool = p2
        pool.sort(
            key=lambda r: (
                -int(r["feasible_count"]),
                -float(r["improvement_sum"]),
                int(r["global_index"]),
            )
        )
    else:
        branch = 3
        pool = rows
        pool.sort(
            key=lambda r: (float(r["worst_margin"]), int(r["global_index"]))
        )
    winner = pool[0]
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "contract_sha256": contract_sha256(),
        "selection_priority_branch": branch,
        "winner": {
            "candidate_id": winner["candidate_id"],
            "global_index": winner["global_index"],
            "k": winner["k"],
            "schedule": winner["schedule"],
        },
        "development": per_profile,
        "candidate_pool": {
            "total": len(rows),
            "feasible_on_both": len(p1),
            "feasible_on_one": len(p2),
            "feasible_on_none": len(rows) - len(p1) - len(p2),
        },
    }
    return _write_new_json(SELECTION, payload)


def _guard_payload(
    static: Mapping[str, Any], summary: Mapping[str, Any]
) -> dict[str, Any]:
    guard = candidate_guard(summary, static)
    return {
        "joint_guard_feasible": bool(guard["joint_guard_feasible"]),
        "valid": bool(guard["valid"]),
        "endpoint": dict(guard["endpoint"]),
        "common_no_harm": dict(guard["common_no_harm"]),
        "action_stress_no_harm": dict(guard["action_stress_no_harm"]),
        "saturation_pass": bool(guard["saturation_pass"]),
    }


def aggregate() -> str:
    _assert_wsl_scratch()
    seal = load_seal()
    selection = _read_hashed_json(SELECTION)
    integrity_errors: list[str] = []
    eval_outputs: dict[str, dict[str, Any]] = {}
    candidate_trajectory_count = 0
    static_trajectory_count = 0
    for profile_id in EVAL_PROFILE_IDS:
        static_payload = _read_hashed_json(
            OUT / "shards" / "eval" / profile_id / "static.json"
        )
        winner_payload = _read_hashed_json(
            OUT / "shards" / "eval" / profile_id / "winner.json"
        )
        static_trajectory_count += int(static_payload["trajectory_count"])
        candidate_trajectory_count += int(winner_payload["trajectory_count"])
        if not static_payload["valid_execution"] or not winner_payload["valid_execution"]:
            integrity_errors.append(f"{profile_id}: invalid execution")
            continue
        static = static_payload["summary"]
        winner = winner_payload["summary"]
        guards = _guard_payload(static, winner)
        eval_outputs[profile_id] = {
            "profile_id": profile_id,
            "static": static,
            "winner": winner,
            "winner_candidate_id": winner_payload["winner_candidate_id"],
            "winner_schedule": winner_payload["winner_schedule"],
            "guards": guards,
        }
        _write_new_json(OUT / "profiles" / f"{profile_id}.json", eval_outputs[profile_id])

    # Development-side integrity summary for the formal analysis record.
    dev_feasible: dict[str, list[str]] = {}
    dev_candidate_rows = 0
    for profile_id in DEV_PROFILE_IDS:
        _, rows = _load_dev_rows(profile_id)
        dev_candidate_rows += len(rows)
        dev_feasible[profile_id] = [row["candidate_id"] for row in rows if row["guards"]["joint_guard_feasible"]]

    transfer_profiles = [
        profile_id
        for profile_id, payload in eval_outputs.items()
        if payload["guards"]["joint_guard_feasible"]
    ]
    branch = int(selection["selection_priority_branch"])
    if integrity_errors:
        verdict = "CANARY-INVALID"
    elif branch == 3:
        verdict = "FALLBACK-NO-WITNESS"
    elif transfer_profiles:
        verdict = "GUARD-CLEAN-TRANSFER"
    else:
        verdict = "NO-GUARD-CLEAN-TRANSFER"

    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "contract_sha256": contract_sha256(),
        "seal_sha256": _sha256_file(SEAL),
        "selection_sha256": _sha256_file(SELECTION),
        "integrity": {
            "valid": not integrity_errors,
            "errors": integrity_errors,
            "dev_candidate_rows": dev_candidate_rows,
            "eval_candidate_trajectories": candidate_trajectory_count,
            "eval_static_trajectories": static_trajectory_count,
            "candidate_sequence_sha256": R452.candidate_sequence_sha256(),
        },
        "selection": {
            "priority_branch": branch,
            "winner": selection["winner"],
            "development_feasible_ids": dev_feasible,
            "candidate_pool": selection["candidate_pool"],
        },
        "evaluation": {
            profile_id: {
                "guards": payload["guards"],
                "winner_candidate_id": payload["winner_candidate_id"],
            }
            for profile_id, payload in eval_outputs.items()
        },
        "classification": {
            "profiles_with_guard_clean_transfer": transfer_profiles,
            "transfer_count": len(transfer_profiles),
            "verdict": verdict,
        },
        "formal_authority": bool(seal.get("formal_authority")),
        "training_executed": False,
    }
    return _write_new_json(OUT / "formal_analysis.json", analysis)


def classify() -> str:
    path = OUT / "formal_analysis.json"
    if not path.is_file():
        raise FileNotFoundError("missing formal_analysis.json")
    return json.dumps(
        _read_hashed_json(path)["classification"], indent=2, sort_keys=True
    )


def _capacity_job(_job_id: int) -> dict[str, Any]:
    profile = _profile_by_id("dev_a")
    scenario = _evaluation_scenarios(profile)[0]
    record = _run_trajectory(profile, scenario, static_arm=STATIC_SELECTED)
    return {
        "ok": bool(record.get("completed")) and not bool(record.get("tds_failed")),
        "completed_steps": int(record.get("completed_steps", 0)),
    }


def _meminfo() -> dict[str, int]:
    result: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].isdigit():
            result[parts[0].rstrip(":")] = int(parts[1]) * 1024
    return result


def measure_capacity() -> str:
    _assert_wsl_scratch()
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed before capacity: {checks}")
    mem = _meminfo()
    process_lines = subprocess.run(
        ["ps", "-eo", "pid=,args="], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    other = [
        line.strip()
        for line in process_lines
        if ("scripts/run_" in line or "soft_spot_shard_driver.py" in line)
        and "run_r458" not in line
        and "run_r439_timevarying_oracle.py" not in line
        and "run_r452" not in line
        and "run_r441" not in line
    ]
    rungs: list[dict[str, Any]] = []
    previous: float | None = None
    selected = 0
    accepting = True
    for workers in (1, 2, 4, 8, 12, 16):
        start = time.monotonic()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(_capacity_job, range(32)))
        wall = time.monotonic() - start
        throughput = len(rows) / max(wall, 1e-12)
        memory_safe = (
            workers * R452.WORKER_RSS_FLOOR_BYTES + R452.OS_FLOOR_BYTES
            <= int(mem["MemTotal"])
        )
        gain = None if previous is None else throughput / previous
        all_ok = all(row["ok"] for row in rows)
        accepted = bool(
            accepting
            and all_ok
            and memory_safe
            and (gain is None or gain >= 1.05)
        )
        if accepted:
            selected = workers
            previous = throughput
        else:
            accepting = False
        rungs.append(
            {
                "workers": workers,
                "jobs": len(rows),
                "wall_seconds": round(wall, 3),
                "throughput_jobs_per_second": round(throughput, 4),
                "marginal_gain": None if gain is None else round(gain, 4),
                "memory_safe": memory_safe,
                "all_ok": all_ok,
                "accepted": accepted,
            }
        )
    selected_row = next(
        (row for row in rungs if row["workers"] == selected),
        {"throughput_jobs_per_second": 0.0},
    )
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "authority": checks,
        "rungs": rungs,
        "jobs_per_rung": 32,
        "selected_workers": selected,
        "selected_throughput_jobs_per_second": selected_row[
            "throughput_jobs_per_second"
        ],
        "worker_rss_floor_bytes": R452.WORKER_RSS_FLOOR_BYTES,
        "os_floor_bytes": R452.OS_FLOOR_BYTES,
        "wsl_mem_total_bytes": int(mem["MemTotal"]),
        "wsl_mem_available_bytes": int(mem["MemAvailable"]),
        "other_python_processes": other,
        "other_reserved_processes": 0,
        "host_process_budget": selected + 1,
        "wsl_python_processes": selected + 1,
        "native_threads_per_process": 1,
        "estimated_formal_seconds": 4200
        / max(float(selected_row["throughput_jobs_per_second"]), 1e-12),
        "readiness": "RUN-READY" if selected > 0 and not other else "LOAD-CHECK-REVIEW",
    }
    digest = _write_new_json(CAPACITY, payload)
    return json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True)


def rehearse() -> str:
    _assert_wsl_scratch()
    checks = authority_checks()
    rows = candidates()
    static_fixture = {
        "disturbance_differential_energy": 1.0,
        "off_diagonal_response_energy": 1.0,
        "common_frequency_iae_hz_s": 1.0,
        "worst_unit_peak_hz": 1.0,
        "worst_rocof_hz_s": 1.0,
        "action_rms": 1.0,
        "action_total_variation": 1.0,
        "action_saturation_fraction": 0.0,
        "valid": True,
    }
    boundary_fixture = {
        **static_fixture,
        "disturbance_differential_energy": 0.95,
        "off_diagonal_response_energy": 0.95,
        "common_frequency_iae_hz_s": 1.03,
        "worst_unit_peak_hz": 1.03,
        "worst_rocof_hz_s": 1.03,
        "action_rms": 1.10,
        "action_total_variation": 1.10,
        "action_saturation_fraction": 0.05,
    }
    boundary_guard = candidate_guard(boundary_fixture, static_fixture)
    profile = _profile_by_id("dev_a")
    scenario = _evaluation_scenarios(profile)[0]
    static_record = _run_trajectory(profile, scenario, static_arm=STATIC_SELECTED)
    candidate_record = _run_trajectory(
        profile,
        scenario,
        timevarying=tuple(tuple(pair) for pair in rows[0]["schedule"]),
    )
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "formal_authority": False,
        "training_executed": False,
        "authority": checks,
        "runtime": R452.installed_runtime(),
        "generator": {
            "counts": {str(k): sum(1 for r in rows if r["k"] == k) for k in (2, 3, 5)},
            "total": len(rows),
            "sequence_sha256": R452.candidate_sequence_sha256(),
        },
        "guard_boundary": boundary_guard,
        "physical": {
            "static_completed": bool(static_record.get("completed")),
            "static_steps": int(static_record.get("completed_steps", 0)),
            "candidate_completed": bool(candidate_record.get("completed")),
            "candidate_steps": int(candidate_record.get("completed_steps", 0)),
            "static_identity": static_record.get("identity"),
            "candidate_identity": candidate_record.get("identity"),
        },
    }
    payload["passed"] = bool(
        all(checks.values())
        and payload["generator"]["counts"] == {"2": 25, "3": 125, "5": 200}
        and payload["generator"]["sequence_sha256"] == R452.EXPECTED_CANDIDATE_SHA256
        and boundary_guard["joint_guard_feasible"]
        and payload["physical"]["static_completed"]
        and payload["physical"]["candidate_completed"]
        and payload["physical"]["static_steps"] == int(build_contract()["steps"])
        and payload["physical"]["candidate_steps"] == int(build_contract()["steps"])
        and payload["physical"]["static_identity"]
        == payload["physical"]["candidate_identity"]
    )
    digest = _write_new_json(REHEARSAL, payload)
    return json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True)


def prepare() -> str:
    _assert_wsl_scratch()
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed: {checks}")
    rehearsal_payload = _read_hashed_json(REHEARSAL)
    if not rehearsal_payload.get("passed"):
        raise RuntimeError("rehearsal did not pass")
    capacity = _read_hashed_json(CAPACITY)
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError(f"capacity not RUN-READY: {capacity.get('readiness')}")
    selected = int(capacity["selected_workers"])
    sources = {
        "runner": Path(__file__).resolve(),
        "r452_runner": R452_RUNNER,
        "summary": ROOT / "src/andes_rl_kundur/evaluation/md_decoupling_headroom.py",
        "v4_environment": ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
    }
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(),
        "plan_sha256": _sha256_file(PLAN),
        "authority": checks,
        "runtime": rehearsal_payload["runtime"],
        "capacity_sha256": _sha256_file(CAPACITY),
        "rehearsal_sha256": _sha256_file(REHEARSAL),
        "launch": {
            "host_process_budget": selected + 1,
            "wsl_python_processes": selected + 1,
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
            "dev_shards": len(expected_dev_shard_ids()),
            "eval_shards": len(expected_eval_shard_ids()),
        },
        "sources": {
            name: {"path": _relative(path), "sha256": _sha256_file(path)}
            for name, path in sources.items()
        },
        "formal_authority": True,
        "training_executed": False,
    }
    digest = _write_new_json(SEAL, seal)
    DEV_SHARDS.parent.mkdir(parents=True, exist_ok=True)
    DEV_SHARDS.write_text(json.dumps(expected_dev_shard_ids()) + "\n", encoding="utf-8")
    EVAL_SHARDS.write_text(json.dumps(expected_eval_shard_ids()) + "\n", encoding="utf-8")
    return json.dumps(
        {
            "seal_sha256": digest,
            "selected_workers": selected,
            "dev_shards": len(expected_dev_shard_ids()),
            "eval_shards": len(expected_eval_shard_ids()),
            "estimated_formal_seconds": capacity["estimated_formal_seconds"],
        },
        indent=2,
        sort_keys=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("capacity", "rehearse", "prepare", "shard", "select", "aggregate", "classify"),
    )
    parser.add_argument("shard_id", nargs="?")
    args = parser.parse_args()
    if args.command == "capacity":
        print(measure_capacity(), flush=True)
    elif args.command == "rehearse":
        print(rehearse(), flush=True)
    elif args.command == "prepare":
        print(prepare(), flush=True)
    elif args.command == "shard":
        if args.shard_id is None:
            raise SystemExit("shard requires a shard id")
        print(run_shard(args.shard_id), flush=True)
    elif args.command == "select":
        print(select(), flush=True)
    elif args.command == "aggregate":
        print(aggregate(), flush=True)
    else:
        print(classify(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
