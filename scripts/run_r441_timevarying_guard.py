"""R441 guard completion for the R439 time-varying headroom result.

R439 classified TIMEVARYING-HEADROOM by checking only ``valid`` (finite /
mapping / bound / no slew violation) plus a >5% endpoint improvement, and
stored only the r_d/r_cross summary.  The pre-registered no-harm guards —
common-mode no-harm (common_frequency_iae_hz_s, worst_unit_peak_hz,
worst_rocof_hz_s <= 1.03 x static) and action-stress no-harm (action_rms,
action_total_variation <= 1.10 x static) — were never checked, and the raw
frequency trajectories were discarded, so this cannot be answered offline.

This round re-runs the four R439 winning time-varying candidates plus the
static reference law on the same four evaluation profiles, keeps the full
``summarise_profile`` output for both arms, applies the no-harm guards
winner-vs-static, and classifies GUARD-CLEAN vs GUARD-VIOLATED.

It loads the R439 runner via ``importlib`` and reuses its sealed
``_run_trajectory``, ``_profiles``, ``_evaluation_scenarios``, and
``build_contract`` base (same object, seed 399, 0.2 s x 30 steps).  The
R439 winning candidates are read (read-only) from the hashed
``results/research_loop/r439_timevarying_oracle/profiles/eval_*.json``.

Usage (WSL, ANDES only):

    python scripts/andes_scratch.py scripts/run_r441_timevarying_guard.py capacity
    python scripts/andes_scratch.py scripts/run_r441_timevarying_guard.py rehearse
    python scripts/andes_scratch.py scripts/run_r441_timevarying_guard.py prepare
    python scripts/andes_scratch.py scripts/run_r441_timevarying_guard.py shard <profile_id>
    python scripts/andes_scratch.py scripts/run_r441_timevarying_guard.py aggregate
    python scripts/andes_scratch.py scripts/run_r441_timevarying_guard.py classify

Formal artifacts are create-only with sha256 sidecars under
results/research_loop/r441_timevarying_guard/.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

ROUND_ID = "R441"
PARENT_ROUND = "R439"
PLAN = ROOT / "memory/rounds/R441/plan.md"
REHEARSAL = ROOT / "memory/rounds/R441/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R441/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R441/formal_seal.json"
OUT = ROOT / "results/research_loop/r441_timevarying_guard"
R439_OUT = ROOT / "results/research_loop/r439_timevarying_oracle"
R439_RUNNER = ROOT / "scripts/run_r439_timevarying_oracle.py"

STATIC_SELECTED = "local_neighbour_md_km3_kd2"  # R416 development-selected law
IMPROVEMENT_MIN = 0.05  # >5% endpoint improvement (R439 pre-registered)
COMMON_HARM_MAX = 0.03  # R399 thresholds.maximum_common_harm
ACTION_STRESS_HARM_MAX = 0.10  # R399 thresholds.maximum_action_stress_harm
PROFILE_IDS = ("eval_a", "eval_b", "eval_c", "eval_d")

CAPACITY_RUNGS = (1, 2, 4, 8, 12, 16)


def _load_r439() -> Any:
    """Load the R439 runner module without importing it by name."""
    spec = importlib.util.spec_from_file_location(
        "r439_timevarying_oracle", R439_RUNNER
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R439 = _load_r439()

# Reused sealed execution / IO primitives (same object, seed, steps).
_run_trajectory = R439._run_trajectory
_profiles = R439._profiles
_evaluation_scenarios = R439._evaluation_scenarios
_sha256_file = R439._sha256_file
_relative = R439._relative
_write_new_json = R439._write_new_json
_read_hashed_json = R439._read_hashed_json
contract_sha256 = R439.contract_sha256
safe_emit = R439.safe_emit

from andes_rl_kundur.evaluation.md_decoupling_headroom import (  # noqa: E402
    summarise_profile,
)


def _r439_winner(profile_id: str) -> dict[str, Any]:
    """Read the sealed R439 winning candidate for one profile (read-only)."""
    entry = _read_hashed_json(R439_OUT / "profiles" / f"{profile_id}.json")
    best = entry["best_timevarying"]
    return {
        "candidate": [list(pair) for pair in best["candidate"]],
        "k": int(best["k"]),
    }


def _r439_winners() -> dict[str, dict[str, Any]]:
    return {profile_id: _r439_winner(profile_id) for profile_id in PROFILE_IDS}


def build_contract() -> dict[str, Any]:
    """R441 contract: R439 scientific base plus R441 guard metadata."""
    contract = R439.build_contract()
    contract["round"] = ROUND_ID
    contract["r441"] = {
        "round": ROUND_ID,
        "parent_round": PARENT_ROUND,
        "static_selected": STATIC_SELECTED,
        "improvement_min": IMPROVEMENT_MIN,
        "common_harm_max": COMMON_HARM_MAX,
        "action_stress_harm_max": ACTION_STRESS_HARM_MAX,
        "steps": 30,
        "profile_ids": list(PROFILE_IDS),
        "r439_results_dir": _relative(R439_OUT),
        "winning_candidates": _r439_winners(),
        "plan_sha256": _sha256_file(PLAN),
    }
    return contract


def _arm_summary(
    profile: Mapping[str, Any],
    *,
    static_arm: str | None = None,
    timevarying: Sequence[tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Full six-scenario ``summarise_profile`` for one arm on one profile."""
    scenarios = _evaluation_scenarios(profile)
    records = [
        _run_trajectory(
            profile, scenario, static_arm=static_arm, timevarying=timevarying
        )
        for scenario in scenarios
    ]
    return summarise_profile(records, contract=build_contract())


def _guard_report(
    static: Mapping[str, Any], winner: Mapping[str, Any]
) -> dict[str, Any]:
    """Winner-vs-static no-harm guards plus the improvement / validity gate."""
    static_r_d = float(static["disturbance_differential_energy"])
    static_r_cross = float(static["off_diagonal_response_energy"])
    winner_r_d = float(winner["disturbance_differential_energy"])
    winner_r_cross = float(winner["off_diagonal_response_energy"])
    r_d_improvement = (static_r_d - winner_r_d) / max(static_r_d, 1e-12)
    r_cross_improvement = (static_r_cross - winner_r_cross) / max(static_r_cross, 1e-12)
    improved = bool(
        r_d_improvement > IMPROVEMENT_MIN or r_cross_improvement > IMPROVEMENT_MIN
    )
    common_no_harm = {
        "common_frequency_iae_no_harm": bool(
            float(winner["common_frequency_iae_hz_s"])
            <= (1.0 + COMMON_HARM_MAX) * float(static["common_frequency_iae_hz_s"])
        ),
        "worst_peak_no_harm": bool(
            float(winner["worst_unit_peak_hz"])
            <= (1.0 + COMMON_HARM_MAX) * float(static["worst_unit_peak_hz"])
        ),
        "rocof_no_harm": bool(
            float(winner["worst_rocof_hz_s"])
            <= (1.0 + COMMON_HARM_MAX) * float(static["worst_rocof_hz_s"])
        ),
    }
    action_stress_no_harm = {
        "action_rms_no_harm": bool(
            float(winner["action_rms"])
            <= (1.0 + ACTION_STRESS_HARM_MAX) * float(static["action_rms"])
        ),
        "action_variation_no_harm": bool(
            float(winner["action_total_variation"])
            <= (1.0 + ACTION_STRESS_HARM_MAX) * float(static["action_total_variation"])
        ),
    }
    valid = bool(static.get("valid") is True and winner.get("valid") is True)
    no_harm = all(common_no_harm.values()) and all(action_stress_no_harm.values())
    guard_clean = bool(valid and improved and no_harm)
    violated: list[str] = [key for key, value in {**common_no_harm, **action_stress_no_harm}.items() if not value]
    if not valid:
        violated.append("valid")
    if not improved:
        violated.append("improvement")
    return {
        "valid": valid,
        "static_valid": bool(static.get("valid")),
        "winner_valid": bool(winner.get("valid")),
        "r_d_improvement": r_d_improvement,
        "r_cross_improvement": r_cross_improvement,
        "improved": improved,
        "improved_r_d": bool(r_d_improvement > IMPROVEMENT_MIN),
        "improved_r_cross": bool(r_cross_improvement > IMPROVEMENT_MIN),
        "common_no_harm": common_no_harm,
        "action_stress_no_harm": action_stress_no_harm,
        "no_harm": no_harm,
        "guard_clean": guard_clean,
        "violated_guards": violated,
    }


def _run_profile_shard(profile_id: str) -> str:
    profile = next(p for p in _profiles() if p["profile_id"] == profile_id)
    winner_info = _r439_winner(profile_id)
    static = _arm_summary(profile, static_arm=STATIC_SELECTED)
    winner = _arm_summary(
        profile,
        timevarying=tuple(tuple(pair) for pair in winner_info["candidate"]),
    )
    guards = _guard_report(static, winner)
    payload = {
        "profile_id": profile_id,
        "static": static,
        "winner": winner,
        "winner_candidate": winner_info["candidate"],
        "winner_k": winner_info["k"],
        "guards": guards,
    }
    return _write_new_json(OUT / "profiles" / f"{profile_id}.json", payload)


def _classify_profile(entry: Mapping[str, Any]) -> dict[str, Any]:
    guards = entry["guards"]
    static = entry["static"]
    winner = entry["winner"]
    return {
        "profile_id": entry["profile_id"],
        "guard_clean": bool(guards["guard_clean"]),
        "violated_guards": list(guards["violated_guards"]),
        "winner_k": entry["winner_k"],
        "winner_candidate": entry["winner_candidate"],
        "static_r_d": float(static["disturbance_differential_energy"]),
        "winner_r_d": float(winner["disturbance_differential_energy"]),
        "static_r_cross": float(static["off_diagonal_response_energy"]),
        "winner_r_cross": float(winner["off_diagonal_response_energy"]),
        "r_d_improvement": float(guards["r_d_improvement"]),
        "r_cross_improvement": float(guards["r_cross_improvement"]),
        "common_no_harm": dict(guards["common_no_harm"]),
        "action_stress_no_harm": dict(guards["action_stress_no_harm"]),
    }


def _aggregate() -> str:
    profiles_dir = OUT / "profiles"
    if not profiles_dir.is_dir():
        raise FileNotFoundError("missing profiles/ directory")
    per_profile = []
    for profile_id in PROFILE_IDS:
        path = profiles_dir / f"{profile_id}.json"
        entry = _read_hashed_json(path)
        per_profile.append(_classify_profile(entry))
    any_violated = any(not row["guard_clean"] for row in per_profile)
    classification = {
        "verdict": "GUARD-VIOLATED" if any_violated else "GUARD-CLEAN",
        "per_profile": per_profile,
    }
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "contract_sha256": contract_sha256(build_contract()),
        "seal_sha256": _sha256_file(SEAL),
        "classification": classification,
    }
    return _write_new_json(OUT / "formal_analysis.json", payload)


def classify() -> str:
    path = OUT / "formal_analysis.json"
    if not path.is_file():
        raise FileNotFoundError("missing formal_analysis.json")
    return json.dumps(_read_hashed_json(path)["classification"], indent=2, sort_keys=True)


def authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    contract = build_contract()
    return {
        "active_plan": "state: active" in plan_text and "R441" in plan_text,
        "contract_closed": (
            contract["r441"]["static_selected"] == STATIC_SELECTED
            and contract["r441"]["parent_round"] == PARENT_ROUND
            and list(contract["r441"]["profile_ids"]) == list(PROFILE_IDS)
        ),
        "output_absence": not OUT.exists(),
    }


def _capacity_job(_job_id: int) -> dict[str, Any]:
    profile = _profiles()[0]
    scenario = _evaluation_scenarios(profile)[0]
    record = _run_trajectory(profile, scenario, static_arm=STATIC_SELECTED)
    return {"ok": bool(record.get("completed_steps", 0) > 0)}


def measure_capacity() -> str:
    payload = {"rungs": []}
    for workers in CAPACITY_RUNGS:
        start = time.monotonic()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_capacity_job, range(workers * 4)))
        wall = time.monotonic() - start
        payload["rungs"].append(
            {
                "workers": workers,
                "jobs": len(results),
                "wall_seconds": round(wall, 3),
                "throughput_jobs_per_second": round(
                    len(results) / max(wall, 1e-9), 4
                ),
                "all_ok": all(r["ok"] for r in results),
            }
        )
    return json.dumps(payload, indent=2, sort_keys=True)


def rehearse() -> str:
    contract = build_contract()
    checks = {
        "authority": authority_checks(),
        "contract_sha256": contract_sha256(contract),
        "output_absence": not OUT.exists(),
    }
    profile = _profiles()[0]
    scenario = _evaluation_scenarios(profile)[0]
    record = _run_trajectory(profile, scenario, static_arm=STATIC_SELECTED)
    checks["static_reference"] = {
        "rows": int(record.get("completed_steps", 0)),
        "tds_failed": bool(record.get("tds_failed")),
        "identity_ok": bool(record.get("identity") is not None),
    }
    winner_info = _r439_winner(str(profile["profile_id"]))
    tv_record = _run_trajectory(
        profile,
        scenario,
        timevarying=tuple(tuple(pair) for pair in winner_info["candidate"]),
    )
    checks["winner_reference"] = {
        "rows": int(tv_record.get("completed_steps", 0)),
        "tds_failed": bool(tv_record.get("tds_failed")),
        "k": int(winner_info["k"]),
    }
    return json.dumps(checks, indent=2, sort_keys=True)


def prepare(other_reserved: int = 0) -> str:
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority checks failed: {checks}")
    rehearsal = _read_hashed_json(REHEARSAL)
    if not rehearsal.get("static_reference", {}).get("rows", 0) > 0:
        raise RuntimeError("rehearsal static reference failed")
    if not rehearsal.get("winner_reference", {}).get("rows", 0) > 0:
        raise RuntimeError("rehearsal winner reference failed")
    capacity = _read_hashed_json(CAPACITY)
    selected = int(capacity.get("selected_workers", 0))
    if selected <= 0:
        raise RuntimeError("capacity evidence has no selected rung")
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(build_contract()),
        "plan_sha256": _sha256_file(PLAN),
        "authority": checks,
        "launch": {
            "wsl_python_processes": selected + 1,
            "other_reserved_processes": other_reserved,
            "host_process_budget": selected + 1,
            "native_threads_per_process": 1,
        },
        "formal_authority": True,
        "training_executed": False,
        "sources": {
            "runner": {
                "path": _relative(Path(__file__).resolve()),
                "sha256": _sha256_file(Path(__file__).resolve()),
            },
            "r439_runner": {
                "path": _relative(R439_RUNNER),
                "sha256": _sha256_file(R439_RUNNER),
            },
        },
    }
    digest = _write_new_json(SEAL, seal)
    return json.dumps({"seal_sha256": digest}, indent=2, sort_keys=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["capacity", "rehearse", "prepare", "shard", "aggregate", "classify"],
    )
    parser.add_argument("shard_id", nargs="?")
    parser.add_argument("--other-reserved", type=int, default=0)
    args = parser.parse_args()
    if args.command == "capacity":
        payload = json.loads(measure_capacity())
        CAPACITY.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        safe_emit(json.dumps(payload, indent=2, sort_keys=True))
    elif args.command == "rehearse":
        payload = json.loads(rehearse())
        _write_new_json(REHEARSAL, payload)
        safe_emit(json.dumps(payload, indent=2, sort_keys=True))
    elif args.command == "prepare":
        safe_emit(prepare(args.other_reserved))
    elif args.command == "shard":
        if args.shard_id is None:
            raise SystemExit("shard requires a profile id")
        safe_emit("R441 guard: " + _run_profile_shard(args.shard_id))
    elif args.command == "aggregate":
        safe_emit(_aggregate())
    else:
        safe_emit(classify())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
