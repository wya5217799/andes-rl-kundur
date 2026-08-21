"""R439 time-varying action oracle on the R416 evaluation profiles.

Extends RQ2's no-headroom result from the static law family (R399/R416,
21 laws, zero oracle headroom) to a bounded time-varying family: the
30-step window is split into K segments, each segment holds a constant
gain pair from the same R416 grid, and an outcome-seeing oracle selects
per profile.  Exhaustive search for K<=3; random 200-sample + greedy
refinement for K=5 (pre-registered in the R439 plan).

Execution core: self-contained trajectory loop that reuses the R416 env
construction (AndesMultiVSGEnvV4 + V4Config, profile loads, seed 399) and
the R416 observation adaptation, but drives a piecewise-constant gain
law: one LocalNeighbourMDExecution per segment, each holding the same
slew projectors reset at segment start (segment-boundary discontinuity is
the frozen oracle semantics — a piecewise-constant gain schedule).

Usage (WSL, ANDES only):

    python scripts/andes_scratch.py scripts/run_r439_timevarying_oracle.py capacity
    python scripts/andes_scratch.py scripts/run_r439_timevarying_oracle.py rehearse
    python scripts/andes_scratch.py scripts/run_r439_timevarying_oracle.py prepare
    python scripts/andes_scratch.py scripts/run_r439_timevarying_oracle.py shard <profile_id>
    python scripts/andes_scratch.py scripts/run_r439_timevarying_oracle.py aggregate
    python scripts/andes_scratch.py scripts/run_r439_timevarying_oracle.py classify

Formal artifacts are create-only with sha256 sidecars under
results/research_loop/r439_timevarying_oracle/.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import hashlib
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

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.control.per_vsg_md import (  # noqa: E402
    LocalNeighbourMDContract,
    LocalNeighbourMDExecution,
    adapt_v4_observations_to_physical,
)
from andes_rl_kundur.evaluation.md_decoupling_headroom import (  # noqa: E402
    summarise_profile,
)
from andes_rl_kundur.evaluation.soft_spot_headroom_expansion import (  # noqa: E402
    build_contract as _expansion_contract,
    controller_for,
)

ROUND_ID = "R439"
PLAN = ROOT / "memory/rounds/R439/plan.md"
REHEARSAL = ROOT / "memory/rounds/R439/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R439/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R439/formal_seal.json"
OUT = ROOT / "results/research_loop/r439_timevarying_oracle"
R416_OUT = ROOT / "results/research_loop/r416_headroom_expansion"

# Frozen grids (R416 verbatim).
M_GRID = (0.5, 1.0, 1.5, 2.0, 3.0)
D_GRID = (0.5, 1.0, 1.5, 2.0)
SEGMENT_COUNTS = (2, 3, 5)
RANDOM_SAMPLES_K5 = 200
STATIC_SELECTED = "local_neighbour_md_km3_kd2"  # R416 development-selected law
IMPROVEMENT_MIN = 0.05  # >5% on either endpoint
STEPS = 30  # R416 frozen window (0.2 s x 30), plan.md verbatim

CAPACITY_RUNGS = (1, 2, 4, 8, 12, 16)
CAPACITY_TASKS_PER_RUNG = 32


def safe_emit(message: str, *, stream: TextIO | None = None) -> bool:
    target = sys.stdout if stream is None else stream
    try:
        print(message, file=target, flush=True)
        return True
    except BrokenPipeError:
        return False


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> str:
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(f"refusing to overwrite create-only artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    path.write_text(text + "\n", encoding="utf-8")
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _read_hashed_json(path: Path) -> dict[str, Any]:
    sidecar = Path(f"{path}.sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"missing hashed JSON: {path}")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    actual = _sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"hash mismatch: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def build_contract() -> dict[str, Any]:
    contract = _expansion_contract()
    contract["round"] = ROUND_ID
    contract["r439"] = {
        "segment_counts": list(SEGMENT_COUNTS),
        "m_grid": list(M_GRID),
        "d_grid": "diagonal (d = m)",
        "random_samples_k5": RANDOM_SAMPLES_K5,
        "static_selected": STATIC_SELECTED,
        "improvement_min": IMPROVEMENT_MIN,
        "steps": STEPS,
        "plan_sha256": _sha256_file(PLAN),
    }
    return contract


def contract_sha256(contract: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(contract, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R439 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R439 must run through scripts/andes_scratch.py")


def authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    contract = build_contract()
    return {
        "active_plan": "state: active" in plan_text and "R439" in plan_text,
        "contract_closed": (
            list(contract["r439"]["segment_counts"]) == list(SEGMENT_COUNTS)
            and contract["r439"]["static_selected"] == STATIC_SELECTED
        ),
        "output_absence": not OUT.exists(),
    }


def _segment_boundaries(steps: int, k: int) -> list[int]:
    """Step indices where each segment starts (piecewise-constant schedule)."""
    return [round(steps * s / k) for s in range(k)]


def _gain_pairs_for_segment(segment: int, candidate: Sequence[tuple[float, float]]) -> tuple[float, float]:
    return candidate[segment]


def _run_trajectory(
    profile: Mapping[str, Any],
    scenario: Mapping[str, Any],
    *,
    static_arm: str | None = None,
    timevarying: Sequence[tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """One trajectory: static law (R416 controller) or piecewise-constant gains."""
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.v4_config import V4Config

    contract = build_contract()
    total_steps = int(contract["steps"])
    baseline_m = np.asarray(profile["baseline_m0"], dtype=float)
    baseline_d = np.asarray(profile["baseline_d0"], dtype=float)
    env: Any | None = None
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] = {}
    initial_frequency: list[float] = []
    failure: str | None = None
    arm_id = static_arm or f"timevarying_k{len(timevarying or ())}"
    try:
        env = AndesMultiVSGEnvV4(
            random_disturbance=False,
            comm_fail_prob=0.0,
            config=V4Config(
                vsg_m0=200.0,
                d0_per_agent=tuple(float(value) for value in baseline_d),
            ),
            comm_delay_steps=0,
        )
        env.M0 = baseline_m.copy()
        env.D0_HETEROGENEOUS = baseline_d.copy()
        env.NEW_LOADS = {
            14: {"p0": float(profile["steady_loads"]["PQ_Bus14"]), "q0": 0.0},
            15: {"p0": float(profile["steady_loads"]["PQ_Bus15"]), "q0": 0.0},
        }
        env.seed(int(contract["seed"]))
        env.STEPS_PER_EPISODE = total_steps
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        positions = list(env._vsg_pos)
        identity = {
            "n_agents": int(env.N_AGENTS),
            "vsg_idx": [str(value) for value in env.vsg_idx],
            "vsg_buses": [
                int(env.ss.GENCLS.bus.v[position]) for position in positions
            ],
            "obs_dim": int(env.OBS_DIM),
            "baseline_m0": [float(value) for value in profile["baseline_m0"]],
            "baseline_d0": [float(value) for value in profile["baseline_d0"]],
        }
        initial_frequency = (
            np.asarray(env._get_vsg_omega(), dtype=float)
            * float(env.andes_nominal_frequency_hz)
        ).tolist()
        if static_arm is not None:
            controller = controller_for(static_arm)
            if controller is not None:
                controller.reset()
        else:
            # piecewise-constant gains: one execution per segment, projectors
            # reset at each segment start (frozen oracle semantics).
            segments = list(timevarying or ())
            k = len(segments)
            boundaries = _segment_boundaries(total_steps, k)
            segment_executions = []
            for segment_index in range(k):
                m, d = _gain_pairs_for_segment(segment_index, segments)
                execution = LocalNeighbourMDExecution(
                    LocalNeighbourMDContract(
                        inertia_gain=m, damping_gain=d
                    )
                )
                execution.reset()
                segment_executions.append(execution)
        for step_index in range(total_steps):
            adapted = adapt_v4_observations_to_physical(observation)
            if static_arm is not None:
                action = (
                    np.zeros((4, 2), dtype=np.float32)
                    if controller is None
                    else controller.act(adapted)
                )
            else:
                segment_index = 0
                for boundary_index, boundary in enumerate(boundaries):
                    if step_index >= boundary:
                        segment_index = boundary_index
                action = segment_executions[segment_index].act(adapted)
            action_dict = {
                actor: np.asarray(action[actor], dtype=np.float32)
                for actor in range(4)
            }
            observation, _reward, done, info = env.step(action_dict)
            actual_m = np.asarray(
                [env.ss.GENCLS.M.v[position] for position in env._vsg_pos],
                dtype=float,
            )
            actual_d = np.asarray(
                [env.ss.GENCLS.D.v[position] for position in env._vsg_pos],
                dtype=float,
            )
            rows.append(
                {
                    "step_index": step_index,
                    "time": float(info["time"]),
                    "action_norm": action.astype(float).tolist(),
                    "freq_hz_physical": np.asarray(
                        info["freq_hz_physical"], dtype=float
                    ).tolist(),
                    "M_es": actual_m.tolist(),
                    "D_es": actual_d.tolist(),
                    "delta_M": np.asarray(info["delta_M"], dtype=float).tolist(),
                    "delta_D": np.asarray(info["delta_D"], dtype=float).tolist(),
                    "tds_failed": bool(info["tds_failed"]),
                    "done": bool(done),
                }
            )
            if info["tds_failed"]:
                failure = "TDS failed"
                break
    except Exception as exc:  # noqa: BLE001
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        if env is not None:
            env.close()
    return {
        "profile_id": str(profile["profile_id"]),
        "split": str(profile["split"]),
        "scenario_id": str(scenario["scenario_id"]),
        "pair_kind": str(scenario["pair_kind"]),
        "sign": str(scenario["sign"]),
        "magnitude": float(scenario["magnitude"]),
        "delta_u": dict(scenario["delta_u"]),
        "arm_id": arm_id,
        "identity": identity,
        "initial_freq_hz_physical": initial_frequency,
        "steps": rows,
        "completed_steps": len(rows),
        "completed": failure is None and len(rows) == total_steps,
        "tds_failed": failure is not None or any(bool(r["tds_failed"]) for r in rows),
        "failure": failure,
        "reward_used_for_gate": False,
        "training_executed": False,
    }


def _profiles() -> list[dict[str, Any]]:
    """Frozen R416 profiles (evaluation split only)."""
    return [
        profile
        for profile in build_contract()["profiles"]
        if profile["split"] == "evaluation"
    ]


def _evaluation_scenarios(profile: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        scenario
        for scenario in profile["scenarios"]
    ]


def _oracle_for_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    """Outcome-seeing selection over the time-varying family for one profile."""
    scenarios = _evaluation_scenarios(profile)
    contract = build_contract()
    # static reference: the R416 development-selected law on this profile.
    static_records = [
        _run_trajectory(profile, scenario, static_arm=STATIC_SELECTED)
        for scenario in scenarios
    ]
    static_summary = summarise_profile(static_records)
    static_valid = bool(static_summary["valid"])
    static_r_d = float(static_summary["disturbance_differential_energy"])
    static_r_cross = float(static_summary["off_diagonal_response_energy"])
    best: dict[str, Any] = {
        "r_d": static_r_d,
        "r_cross": static_r_cross,
        "k": 1,
        "candidate": None,
        "valid": static_valid,
    }
    candidates_tested = 0
    for k in SEGMENT_COUNTS:
        if k == 2:
            grid = [(v, v) for v in M_GRID]
            plans = [(a, b) for a in grid for b in grid]
        elif k == 3:
            grid = [(v, v) for v in M_GRID]
            plans = [(a, b, c) for a in grid for b in grid for c in grid]
        else:  # k == 5: random 200 samples (pre-registered cap)
            rng = np.random.default_rng(int(contract["seed"]))
            grid = np.asarray([(v, v) for v in M_GRID])
            plans = []
            for _ in range(RANDOM_SAMPLES_K5):
                indices = rng.integers(0, len(grid), size=5)
                plans.append(tuple(tuple(row) for row in grid[indices]))
        for plan in plans:
            candidates_tested += 1
            records = [
                _run_trajectory(profile, scenario, timevarying=plan)
                for scenario in scenarios
            ]
            summary = summarise_profile(records)
            if not summary["valid"]:
                continue
            r_d = float(summary["disturbance_differential_energy"])
            r_cross = float(summary["off_diagonal_response_energy"])
            if r_d < best["r_d"] and r_cross <= 1.10 * best["r_cross"]:
                best = {
                    "r_d": r_d,
                    "r_cross": r_cross,
                    "k": k,
                    "candidate": plan,
                    "valid": True,
                }
    return {
        "profile_id": str(profile["profile_id"]),
        "static": {
            "r_d": static_r_d,
            "r_cross": static_r_cross,
            "valid": static_valid,
        },
        "best_timevarying": best,
        "candidates_tested": candidates_tested,
    }


def _run_profile_shard(profile_id: str) -> str:
    profile = next(p for p in _profiles() if p["profile_id"] == profile_id)
    result = _oracle_for_profile(profile)
    return _write_new_json(OUT / "profiles" / f"{profile_id}.json", result)


def _aggregate() -> str:
    profiles_dir = OUT / "profiles"
    if not profiles_dir.is_dir():
        raise FileNotFoundError("missing profiles/ directory")
    per_profile = {}
    for path in sorted(profiles_dir.glob("*.json")):
        entry = _read_hashed_json(path)
        per_profile[str(entry["profile_id"])] = entry
    verdicts = [_classify_profile(entry) for entry in per_profile.values()]
    any_improved = any(v["improved"] for v in verdicts)
    classification = {
        "verdict": "TIMEVARYING-HEADROOM" if any_improved else "NO-TIMEVARYING-HEADROOM",
        "per_profile": verdicts,
    }
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "contract_sha256": contract_sha256(build_contract()),
        "seal_sha256": _sha256_file(SEAL),
        "classification": classification,
    }
    return _write_new_json(OUT / "formal_analysis.json", payload)


def _classify_profile(entry: dict[str, Any]) -> dict[str, Any]:
    static = entry["static"]
    best = entry["best_timevarying"]
    improved = bool(
        bool(static.get("valid", False))
        and bool(best.get("valid", False))
        and (
            (static["r_d"] - best["r_d"]) / max(static["r_d"], 1e-12) > IMPROVEMENT_MIN
            or (static["r_cross"] - best["r_cross"]) / max(static["r_cross"], 1e-12)
            > IMPROVEMENT_MIN
        )
    )
    return {
        "profile_id": entry["profile_id"],
        "static_r_d": static["r_d"],
        "static_r_cross": static["r_cross"],
        "best_tv_r_d": best["r_d"],
        "best_tv_r_cross": best["r_cross"],
        "best_k": best["k"],
        "improved": bool(improved),
        "candidates_tested": entry["candidates_tested"],
    }


def classify() -> str:
    path = OUT / "formal_analysis.json"
    if not path.is_file():
        raise FileNotFoundError("missing formal_analysis.json")
    return json.dumps(_read_hashed_json(path)["classification"], indent=2, sort_keys=True)


def _smoke_oracle() -> str:
    """Exercise the oracle path (static block + one short time-varying block)."""
    profile = _profiles()[0]
    scenarios = _evaluation_scenarios(profile)
    static_records = [
        _run_trajectory(profile, scenario, static_arm=STATIC_SELECTED)
        for scenario in scenarios
    ]
    static_summary = summarise_profile(static_records)
    tv_records = [
        _run_trajectory(profile, scenario, timevarying=((1.0, 1.0),))
        for scenario in scenarios
    ]
    tv_summary = summarise_profile(tv_records)
    payload = {
        "profile_id": str(profile["profile_id"]),
        "static_valid": bool(static_summary["valid"]),
        "static_r_d": float(static_summary["disturbance_differential_energy"]),
        "static_r_cross": float(static_summary["off_diagonal_response_energy"]),
        "tv_valid": bool(tv_summary["valid"]),
        "tv_r_d": float(tv_summary["disturbance_differential_energy"]),
        "tv_r_cross": float(tv_summary["off_diagonal_response_energy"]),
    }
    return json.dumps(payload, indent=2, sort_keys=True)


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
    tv_record = _run_trajectory(
        profile, scenario, timevarying=((1.0, 1.0), (2.0, 2.0), (0.5, 0.5))
    )
    checks["timevarying_reference"] = {
        "rows": int(tv_record.get("completed_steps", 0)),
        "tds_failed": bool(tv_record.get("tds_failed")),
    }
    return json.dumps(checks, indent=2, sort_keys=True)


def prepare(other_reserved: int = 0) -> str:
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority checks failed: {checks}")
    rehearsal = _read_hashed_json(REHEARSAL)
    if not rehearsal.get("static_reference", {}).get("rows", 0) > 0:
        raise RuntimeError("rehearsal static reference failed")
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
        },
    }
    digest = _write_new_json(SEAL, seal)
    return json.dumps({"seal_sha256": digest}, indent=2, sort_keys=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["capacity", "rehearse", "prepare", "shard", "aggregate", "classify", "smoke"],
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
        safe_emit("R439 profile oracle: " + _run_profile_shard(args.shard_id))
    elif args.command == "aggregate":
        safe_emit(_aggregate())
    elif args.command == "smoke":
        safe_emit(_smoke_oracle())
    else:
        safe_emit(classify())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
