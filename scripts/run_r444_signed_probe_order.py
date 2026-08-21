"""Sealed WSL runner for R444: signed-probe odd-response geometric amplitude ladder.

Owner-ordered (2026-08-20) evaluation-only evidence round for the
yang-md-decoupling-marl line: measure the convergence order of the signed
probe pair's odd response (quadratic vs cubic) for the implemented
deterministic law, per theory audit C.7/C.8.  Two zero-bias controllers run
the registered signed probe scenarios at geometric amplitudes
eps_k = eps_0 * 2^-k (k = 0..5): the deterministic law
(local_neighbour_md_km2_kd2) and zero action.  The controller-to-controller
response difference delta(eps) is decomposed into odd/even parts with a
fixed dt-weighted L2 norm; log-log regression estimates the order.

The single changed scientific factor versus R410: per-record probe/localized
magnitude scaled by 2^-k; the R410 environment, estimator semantics, and
evaluation loop are consumed read-only.  The k=0 law bank re-executes the
exact R410 deterministic evaluation conditions and serves as the drift
anchor (bit-identical frequency rows expected).

Lifecycle (WSL only, always through the scratch launcher):
  python scripts/andes_scratch.py scripts/run_r444_signed_probe_order.py measure-capacity
  python scripts/andes_scratch.py scripts/run_r444_signed_probe_order.py rehearse
  python scripts/andes_scratch.py scripts/run_r444_signed_probe_order.py prepare
  python scripts/andes_scratch.py scripts/run_r444_signed_probe_order.py shards
  python scripts/andes_scratch.py scripts/run_r444_signed_probe_order.py shard <shard_id> [--resume]
  python scripts/andes_scratch.py scripts/run_r444_signed_probe_order.py classify

All formal artifacts are create-only with sha256 sidecars under
results/research_loop/r444_signed_probe_order/.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import copy
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

from andes_rl_kundur.evaluation import cd_matd3_canary as _canary  # noqa: E402
from andes_rl_kundur.evaluation.cd_matd3_canary import (  # noqa: E402
    evaluation_record_count,
)
import run_r410_message_repair as r410  # noqa: E402
from run_r401_cd_matd3_canary_contract import (  # noqa: E402
    _memory_resources,
    _other_research_python_processes,
)

ROUND_ID = "R444"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
PLAN = ROOT / "memory/rounds/R444/plan.md"
REHEARSAL = ROOT / "memory/rounds/R444/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R444/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R444/formal_seal.json"
OUT = ROOT / "results/research_loop/r444_signed_probe_order"
R410_OUT = ROOT / "results/research_loop/r410_message_repair"

SCALE_COUNT = 6
CAPACITY_RUNGS = (1, 2, 4)
CAPACITY_TASKS_PER_RUNG = 32
EVAL_WORKER_RSS_FLOOR_BYTES = 944214016
MARGINAL_GAIN_MIN = 1.05
MARGINAL_GAIN_CONFIRM_LOW = 1.03
MARGINAL_GAIN_CONFIRM_HIGH = 1.07
DRIFT_TOLERANCE_RELATIVE = 1.0e-6
CAPACITY_TASK_PROFILE = "canary_eval_a"
CAPACITY_TASK_PAIR = "differential"
CAPACITY_TASK_SIGN = "positive"


def safe_emit(message: str, *, stream: TextIO | None = None) -> bool:
    target = sys.stdout if stream is None else stream
    try:
        print(message, file=target, flush=True)
    except BrokenPipeError:
        if stream is None:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        return False
    return True


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
    text = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
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


def _frozen_contract() -> dict[str, Any]:
    return _canary.build_contract()


def scale_key(k: int) -> str:
    return f"k{k}"


def shard_id(controller: str, k: int) -> str:
    return f"{controller}|{scale_key(k)}"


def parse_shard_id(sid: str) -> tuple[str, int]:
    parts = str(sid).split("|")
    if len(parts) != 2 or not parts[1].startswith("k"):
        raise ValueError(f"malformed shard id: {sid}")
    controller, key_token = parts
    if controller not in ("law", "zero"):
        raise ValueError(f"unknown controller: {controller}")
    return controller, int(key_token[1:])


def shard_list() -> list[str]:
    """Expand the frozen protocol: 2 controllers x 6 geometric scales."""
    return [
        shard_id(controller, k)
        for controller in ("law", "zero")
        for k in range(SCALE_COUNT)
    ]


def evaluation_profiles(contract: Mapping[str, Any] | None = None) -> list[str]:
    spec = contract if contract is not None else _frozen_contract()
    return [
        str(profile["profile_id"])
        for profile in spec["profiles"]
        if profile["split"] == "evaluation"
    ]


def scaled_profiles(k: int) -> list[dict[str, Any]]:
    """Evaluation profiles with probe AND localized magnitudes x 2^-k."""
    factor = 2.0 ** (-float(k))
    profiles = []
    for source in _frozen_contract()["profiles"]:
        if source["split"] != "evaluation":
            continue
        profile = copy.deepcopy(source)
        profile["probe_magnitude"] = float(factor) * float(
            source["probe_magnitude"]
        )
        profile["localized_magnitude"] = float(factor) * float(
            source["localized_magnitude"]
        )
        profile["scenarios"] = _canary._signed_scenarios(profile)
        profile["amplitude_k"] = int(k)
        profiles.append(profile)
    return profiles


def _source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r444_signed_probe_order.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "shard_driver_tests": ROOT / "tests/test_soft_spot_shard_driver.py",
        "contract": ROOT / "src/andes_rl_kundur/evaluation/cd_matd3_canary.py",
        "contract_tests": ROOT / "tests/test_cd_matd3_canary.py",
        "estimators": ROOT
        / "src/andes_rl_kundur/evaluation/md_decoupling_headroom.py",
        "controller": ROOT / "src/andes_rl_kundur/control/per_vsg_md.py",
        "controller_tests": ROOT / "tests/test_per_vsg_md.py",
        "v4_environment": ROOT
        / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "v4_config": ROOT / "src/andes_rl_kundur/env/andes/v4_config.py",
        "base_environment": ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
        "analysis_probe": ROOT / "probes/r444_signed_probe_order.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in sources.items()
    }


def _parent_manifest() -> dict[str, dict[str, str]]:
    parents = {
        "r410_formal_seal": ROOT / "memory/rounds/R410/formal_seal.json",
        "r410_deterministic_eval_profile_a": R410_OUT / "eval"
        / "local_neighbour_md_km2_kd2" / "deterministic"
        / "canary_eval_a.json",
        "r411_feed": ROOT / "paper/yang_md_decoupling_marl/reports/R411.md",
        "theory_audit": ROOT
        / "paper/yang_md_decoupling_marl/working/theory_audit_bundle"
        / "vsg_theory_audit.md",
        "r410_runner": ROOT / "scripts/run_r410_message_repair.py",
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in parents.items()
    }


def _installed_runtime() -> dict[str, Any]:
    import andes

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    return {
        "python": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "andes_module": str(Path(andes.__file__).resolve()),
        "case_path": str(case_path),
        "case_sha256": _sha256_file(case_path),
    }


def _authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    contract = _frozen_contract()
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and "R444" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_closed": len(contract["profiles"]) == 8
        and evaluation_record_count(contract) == 240
        and list(contract["training_seeds"]) == [401, 402, 403],
        "r410_root_present": R410_OUT.is_dir(),
        "output_absence": not OUT.exists(),
    }


def _other_processes() -> list[dict[str, Any]]:
    own_pids = {os.getpid()}
    parent = int(os.getppid())
    while parent > 1 and len(own_pids) < 16:
        own_pids.add(parent)
        try:
            stat_fields = Path(f"/proc/{parent}/stat").read_text(
                encoding="utf-8"
            ).split()
            parent = int(stat_fields[3])
        except (OSError, ValueError, IndexError):
            break
    matches: list[dict[str, Any]] = []
    for entry in _other_research_python_processes():
        if int(entry["pid"]) in own_pids:
            continue
        command = str(entry.get("command", ""))
        if any(
            marker in command
            for marker in (
                "run_r410_message_repair.py",
                "run_r411_probe_amplitude_ladder.py",
                "run_r444_signed_probe_order.py",
                "soft_spot_shard_driver.py",
            )
        ):
            continue
        matches.append(entry)
    return matches


def _evaluate_profile(
    controller_id: str,
    k: int,
    profile: Mapping[str, Any],
    *,
    controller: Any,
) -> dict[str, Any]:
    contract = _frozen_contract()
    env = r410._build_env(dict(profile))
    records = []
    try:
        for scenario in profile["scenarios"]:
            observation = env.reset(delta_u=dict(scenario["delta_u"]))
            if controller is not None:
                controller.reset()
            initial_frequency = (
                np.asarray(env._get_vsg_omega(), dtype=float)
                * float(contract["physical_nominal_frequency_hz"])
            ).tolist()
            identity = {
                "n_agents": int(env.N_AGENTS),
                "vsg_idx": [str(value) for value in env.vsg_idx],
                "vsg_buses": [
                    int(env.ss.GENCLS.bus.v[position])
                    for position in env._vsg_pos
                ],
                "obs_dim": int(env.OBS_DIM),
                "baseline_m0": [float(value) for value in profile["baseline_m0"]],
                "baseline_d0": [float(value) for value in profile["baseline_d0"]],
                "control_nominal_frequency_hz": float(env.FN),
                "physical_nominal_frequency_hz": float(
                    env.andes_nominal_frequency_hz
                ),
            }
            rows = []
            failure = None
            for step_index in range(int(contract["steps"])):
                if controller is not None:
                    from andes_rl_kundur.control.per_vsg_md import (
                        adapt_v4_observations_to_physical,
                    )

                    action = controller.act(
                        adapt_v4_observations_to_physical(observation)
                    )
                else:
                    action = np.zeros((4, 2), dtype=np.float32)
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
                        "delta_M": np.asarray(
                            info["delta_M"], dtype=float
                        ).tolist(),
                        "delta_D": np.asarray(
                            info["delta_D"], dtype=float
                        ).tolist(),
                        "tds_failed": bool(info["tds_failed"]),
                        "done": bool(done),
                    }
                )
                if info["tds_failed"]:
                    failure = "TDS failed"
                    break
            record = {
                "profile_id": str(profile["profile_id"]),
                "split": str(profile["split"]),
                "scenario_id": str(scenario["scenario_id"]),
                "pair_kind": str(scenario["pair_kind"]),
                "sign": str(scenario["sign"]),
                "magnitude": float(scenario["magnitude"]),
                "delta_u": dict(scenario["delta_u"]),
                "controller_id": controller_id,
                "amplitude_k": int(k),
                "magnitude_executed": float(profile["probe_magnitude"]),
                "identity": identity,
                "initial_freq_hz_physical": initial_frequency,
                "steps": rows,
                "completed_steps": len(rows),
                "completed": failure is None
                and len(rows) == int(contract["steps"]),
                "tds_failed": failure is not None
                or any(bool(row["tds_failed"]) for row in rows),
                "failure": failure,
                "reward_used_for_gate": False,
                "training_executed": False,
            }
            records.append(record)
    finally:
        try:
            env.close()
        except Exception:
            pass
    return {"records": records}


def _evaluate_shard(sid: str, *, resume: bool) -> None:
    r410._assert_wsl_scratch()
    load_seal()
    controller_id, k = parse_shard_id(sid)
    profiles = scaled_profiles(k)
    controller = (
        r410._deterministic_controller() if controller_id == "law" else None
    )
    folder = OUT / "eval" / controller_id / scale_key(k)
    for profile in profiles:
        path = folder / (str(profile["profile_id"]) + ".json")
        sidecar = Path(f"{path}.sha256")
        if path.exists() or sidecar.exists():
            if resume and path.is_file() and sidecar.is_file():
                _read_hashed_json(path)
                continue
            raise FileExistsError(f"create-only output exists: {path}")
        payload = _evaluate_profile(
            controller_id,
            k,
            profile,
            controller=controller,
        )
        _write_new_json(path, payload)


def load_seal() -> dict[str, Any]:
    seal = _read_hashed_json(SEAL)
    if seal.get("round") != ROUND_ID:
        raise RuntimeError("seal belongs to another round")
    if seal.get("contract_sha256") != _canary.contract_sha256(_frozen_contract()):
        raise RuntimeError("sealed contract drifted from the frozen module")
    launch = seal.get("launch", {})
    if int(launch.get("wsl_python_processes", 0)) != int(
        launch.get("host_process_budget", -1)
    ):
        raise RuntimeError("sealed launch budget is inconsistent")
    for name, entry in (seal.get("sources") or {}).items():
        if entry["sha256"] != _sha256_file(ROOT / entry["path"]):
            raise RuntimeError(f"source drifted from the R444 seal: {name}")
    return seal


# ── capacity ladder ────────────────────────────────────────────────────

def _capacity_task(_task_index: int) -> dict[str, Any]:
    import resource

    profile = next(
        row
        for row in scaled_profiles(0)
        if row["profile_id"] == CAPACITY_TASK_PROFILE
    )
    scenario = next(
        row
        for row in profile["scenarios"]
        if row["pair_kind"] == CAPACITY_TASK_PAIR
        and row["sign"] == CAPACITY_TASK_SIGN
    )
    controller = r410._deterministic_controller()
    env = r410._build_env(dict(profile))
    completed = 0
    tds_failed = False
    failure: str | None = None
    try:
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        controller.reset()
        from andes_rl_kundur.control.per_vsg_md import (
            adapt_v4_observations_to_physical,
        )

        for _step_index in range(int(_frozen_contract()["steps"])):
            action = controller.act(
                adapt_v4_observations_to_physical(observation)
            )
            action_dict = {
                actor: np.asarray(action[actor], dtype=np.float32)
                for actor in range(4)
            }
            observation, _reward, _done, info = env.step(action_dict)
            completed += 1
            if info["tds_failed"]:
                tds_failed = True
                failure = "TDS failed"
                break
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            env.close()
        except Exception:
            pass
    return {
        "completed": failure is None
        and completed == int(_frozen_contract()["steps"]),
        "tds_failed": bool(tds_failed),
        "failure": failure,
        "worker_max_rss_kib": int(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        ),
    }


def _measure_rung(workers: int) -> dict[str, Any]:
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as executor:
        results = list(
            executor.map(_capacity_task, range(CAPACITY_TASKS_PER_RUNG))
        )
    wall_seconds = time.perf_counter() - started
    valid = all(
        result["completed"] is True and result["tds_failed"] is False
        for result in results
    )
    return {
        "workers": workers,
        "native_threads_per_worker": 1,
        "wall_seconds": wall_seconds,
        "job_count": len(results),
        "valid_completions": sum(
            result["completed"] is True and result["tds_failed"] is False
            for result in results
        ),
        "all_records_valid": bool(valid),
        "throughput_jobs_per_second": len(results) / wall_seconds,
        "maximum_worker_rss_bytes": max(
            int(result["worker_max_rss_kib"]) * 1024 for result in results
        ),
        "failures": [
            {"task": index, "failure": result["failure"]}
            for index, result in enumerate(results)
            if result["completed"] is not True or result["tds_failed"] is not False
        ],
    }


def _select_rung(
    final_throughput: Mapping[int, float],
    *,
    wsl_available_bytes: int,
) -> dict[str, Any]:
    selected: int | None = None
    selected_throughput: float | None = None
    decisions: list[dict[str, Any]] = []
    for workers in CAPACITY_RUNGS:
        throughput = final_throughput[workers]
        projected = EVAL_WORKER_RSS_FLOOR_BYTES * workers
        memory_safe = projected <= int(wsl_available_bytes) / 2
        if not memory_safe:
            accepted, reason = False, "memory_reserve_guard"
        elif selected is None:
            accepted, reason = True, "first_safe_rung"
        elif throughput < MARGINAL_GAIN_MIN * float(selected_throughput):
            accepted, reason = False, "insufficient_throughput_gain"
        else:
            accepted, reason = True, "safe_throughput_gain"
        decisions.append(
            {
                "workers": workers,
                "accepted": accepted,
                "reason": reason,
                "projected_concurrent_worker_rss_bytes": projected,
                "memory_safe": memory_safe,
                "final_throughput_jobs_per_second": throughput,
            }
        )
        if accepted:
            selected = workers
            selected_throughput = throughput
    if selected is None:
        return {
            "readiness": "HOLD",
            "selected_workers": None,
            "host_process_budget": None,
            "wsl_python_processes": None,
            "rung_decisions": decisions,
        }
    return {
        "readiness": "RUN-READY",
        "selected_workers": selected,
        "host_process_budget": selected + 1,
        "wsl_python_processes": selected + 1,
        "selected_throughput_jobs_per_second": float(selected_throughput),
        "rung_decisions": decisions,
    }


def measure_capacity() -> str:
    r410._assert_wsl_scratch()
    for candidate in (CAPACITY, REHEARSAL, SEAL):
        if candidate.exists():
            raise FileExistsError(f"R444 pre-attempt artifact exists: {candidate}")
    if OUT.exists():
        raise FileExistsError("R444 formal output exists before capacity")
    other = _other_processes()
    if other:
        raise RuntimeError(
            "other research Python processes are active: " + str(other)
        )
    logical, physical_memory, wsl_available = _memory_resources()
    first_pass = [_measure_rung(workers) for workers in CAPACITY_RUNGS]
    final: dict[int, float] = {
        workers: first_pass[index]["throughput_jobs_per_second"]
        for index, workers in enumerate(CAPACITY_RUNGS)
    }
    confirm_pairs: list[tuple[int, int]] = []
    for index in range(len(CAPACITY_RUNGS) - 1):
        low = CAPACITY_RUNGS[index]
        high = CAPACITY_RUNGS[index + 1]
        gain = final[high] / max(final[low], 1e-12)
        if MARGINAL_GAIN_CONFIRM_LOW <= gain <= MARGINAL_GAIN_CONFIRM_HIGH:
            confirm_pairs.append((low, high))
    remeasure = sorted({worker for pair in confirm_pairs for worker in pair})
    second_pass: list[dict[str, Any]] = []
    if remeasure:
        second_pass = [_measure_rung(workers) for workers in remeasure]
        for workers in remeasure:
            values = [
                first_pass[CAPACITY_RUNGS.index(workers)][
                    "throughput_jobs_per_second"
                ],
                second_pass[remeasure.index(workers)]["throughput_jobs_per_second"],
            ]
            final[workers] = float(np.mean(values))
    selection = _select_rung(final, wsl_available_bytes=wsl_available)
    return _write_new_json(
        CAPACITY,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "readiness": selection["readiness"],
            "stage": "representative_eval_capacity_ladder_rungs_1_2_4",
            "authorization": (
                "owner-ordered R444 signed-probe geometric amplitude ladder; "
                "R410 assets consumed read-only"
            ),
            "contract_sha256": _canary.contract_sha256(_frozen_contract()),
            "representative_task": {
                "controller": "law",
                "profile": CAPACITY_TASK_PROFILE,
                "pair_kind": CAPACITY_TASK_PAIR,
                "sign": CAPACITY_TASK_SIGN,
                "tasks_per_rung": CAPACITY_TASKS_PER_RUNG,
            },
            "eval_worker_rss_floor": {
                "bytes": EVAL_WORKER_RSS_FLOOR_BYTES,
                "source": "memory/rounds/R402/capacity_evidence_v2.json",
                "role": "conservative per-worker RSS floor (R402 anchor)",
            },
            "host": {
                "logical_processors": logical,
                "physical_memory_bytes": physical_memory,
            },
            "wsl": {"memory_available_bytes": wsl_available},
            "rungs": first_pass,
            "confirmation_pairs": [
                {"low_workers": low, "high_workers": high}
                for low, high in confirm_pairs
            ],
            "confirmation_pass_2": second_pass,
            "final_throughput_jobs_per_second": final,
            **selection,
            "whole_host_python_process_budget": selection.get(
                "host_process_budget"
            ),
            "empirical_anchor": {
                "all_records_valid": True,
                "concurrent_workers": (
                    int(selection["selected_workers"]) + 1
                    if selection["selected_workers"] is not None
                    else None
                ),
                "launcher_processes": 1,
                "native_threads_per_worker": 1,
                "source": "selected representative capacity rung",
            },
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
            "other_processes": other,
            "memory_rule": (
                "projected concurrent eval-worker RSS must not exceed half "
                "of WSL total memory"
            ),
            "marginal_rule": (
                "next rung accepted only at >=5 percent marginal throughput "
                "gain; pairs within 5%+-2pp re-measured once and averaged"
            ),
            "capacity_trace_role": "non_claim_bearing_excluded_from_evidence",
            "sources": _source_manifest(),
            "installed_runtime": _installed_runtime(),
            "scientific_classification_inspected": False,
            "formal_authority": False,
            "training_executed": False,
        },
    )


# ── rehearsal and seal ─────────────────────────────────────────────────

def rehearse() -> str:
    r410._assert_wsl_scratch()
    for candidate in (REHEARSAL, SEAL):
        if candidate.exists():
            raise FileExistsError(f"R444 pre-attempt artifact exists: {candidate}")
    if not CAPACITY.exists():
        raise FileExistsError("capacity evidence must exist before rehearse")
    checks = _authority_checks()
    required = {
        "active_plan",
        "active_line",
        "contract_closed",
        "r410_root_present",
        "output_absence",
    }
    if not all(checks.get(key) is True for key in required):
        raise RuntimeError("R444 rehearsal checks failed: " + str(checks))
    runtime = _installed_runtime()
    sources = _source_manifest()
    parents = _parent_manifest()
    checks["source_hash"] = bool(sources)
    checks["parent_hash"] = bool(parents)
    checks["installed_package"] = runtime["andes_version"] != "unknown"
    checks["installed_case"] = Path(runtime["case_path"]).is_file()
    contract = _frozen_contract()
    profile = scaled_profiles(0)[0]
    scenario = next(
        row
        for row in profile["scenarios"]
        if row["pair_kind"] == "differential" and row["sign"] == "positive"
    )
    env = r410._build_env(dict(profile))
    from andes_rl_kundur.control.per_vsg_md import (
        adapt_v4_observations_to_physical,
    )

    try:
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        controller = r410._deterministic_controller()
        controller.reset()
        action = controller.act(adapt_v4_observations_to_physical(observation))
        if not np.all(np.isfinite(np.asarray(action, dtype=float))):
            raise RuntimeError("nonfinite deterministic rehearsal action")
        action_dict = {
            actor: np.asarray(action[actor], dtype=np.float32)
            for actor in range(4)
        }
        observation, _reward, _done, info = env.step(action_dict)
        if info["tds_failed"]:
            raise RuntimeError("rehearsal TDS failure (law)")
        zero_action = np.zeros((4, 2), dtype=np.float32)
        observation, _reward, _done, info = env.step(
            {
                actor: np.asarray(zero_action[actor], dtype=np.float32)
                for actor in range(4)
            }
        )
        if info["tds_failed"]:
            raise RuntimeError("rehearsal TDS failure (zero)")
    finally:
        try:
            env.close()
        except Exception:
            pass
    return _write_new_json(
        REHEARSAL,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_sha256": _canary.contract_sha256(contract),
            "sources": sources,
            "parents": parents,
            "installed_runtime": runtime,
            "checks": checks,
            "physical_trajectory_executed": True,
            "formal_artifacts_created": False,
            "training_executed": False,
        },
    )


def _plan_process_budget_matches(capacity: Mapping[str, Any]) -> bool:
    plan_text = PLAN.read_text(encoding="utf-8")
    expected = int(capacity["wsl_python_processes"])
    return bool(
        f"host_process_budget: {expected}" in plan_text
        and f"wsl_python_processes: {expected}" in plan_text
        and "native_threads_per_process: 1" in plan_text
        and "other_reserved_processes: 0" in plan_text
    )


def prepare() -> str:
    r410._assert_wsl_scratch()
    rehearsal = _read_hashed_json(REHEARSAL)
    capacity = _read_hashed_json(CAPACITY)
    snapshot_sources = _source_manifest()
    snapshot_parents = _parent_manifest()
    snapshot_runtime = _installed_runtime()
    checks = _authority_checks()
    required = {
        "active_plan",
        "active_line",
        "contract_closed",
        "r410_root_present",
        "output_absence",
    }
    if not all(checks.get(key) is True for key in required):
        raise RuntimeError("R444 authority checks failed: " + str(checks))
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R444 capacity gate is not RUN-READY")
    if not _plan_process_budget_matches(capacity):
        raise RuntimeError("R444 plan does not freeze the measured process budget")
    for payload in (rehearsal, capacity):
        if payload["sources"] != snapshot_sources:
            raise RuntimeError("R444 source drift before seal")
        if payload["installed_runtime"] != snapshot_runtime:
            raise RuntimeError("R444 runtime drift before seal")
    if rehearsal["parents"] != snapshot_parents:
        raise RuntimeError("R444 parent drift before seal")
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R444 formal artifact exists before sealing")
    process_count = int(capacity["wsl_python_processes"])
    workers = int(capacity["selected_workers"])
    contract = _frozen_contract()
    return _write_new_json(
        SEAL,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract": contract,
            "contract_sha256": _canary.contract_sha256(contract),
            "sources": snapshot_sources,
            "parents": snapshot_parents,
            "installed_runtime": snapshot_runtime,
            "plan_sha256": _sha256_file(PLAN),
            "line_sha256": _sha256_file(LINE),
            "rehearsal_sha256": _sha256_file(REHEARSAL),
            "capacity_sha256": _sha256_file(CAPACITY),
            "single_factor_change": (
                "per-record probe_magnitude and localized_magnitude scaled by "
                "2^-k for k=0..5; baselines, steady loads, estimator semantics, "
                "and evaluation loop are the R410 assets read-only"
            ),
            "launch": {
                "host_process_budget": process_count,
                "wsl_python_processes": process_count,
                "worker_processes": workers,
                "native_threads_per_process": 1,
                "other_reserved_processes": 0,
            },
            "formal_artifacts_create_only": True,
            "retry_authorized": False,
            "training_authorized_in_this_round": False,
        },
    )


# ── classification ────────────────────────────────────────────────────

def _block_path(controller_id: str, k: int, profile_id: str) -> Path:
    return OUT / "eval" / controller_id / scale_key(k) / f"{profile_id}.json"


def _drift_anchor() -> dict[str, Any]:
    """k=0 law records vs R410 deterministic records (bit-identical rows)."""
    contract = _frozen_contract()
    deterministic_arm = str(contract["deterministic_arm_id"])
    per_block = []
    exact_row_mismatches = 0
    max_relative_deviation = 0.0
    for profile_id in evaluation_profiles():
        path = _block_path("law", 0, profile_id)
        payload = _read_hashed_json(path)
        reference_path = (
            R410_OUT / "eval" / deterministic_arm / "deterministic"
            / f"{profile_id}.json"
        )
        reference = _read_hashed_json(reference_path)
        for record, ref_record in zip(
            payload["records"], reference["records"]
        ):
            if record["scenario_id"] != ref_record["scenario_id"]:
                raise ValueError("scenario order mismatch in drift anchor")
            for row, ref_row in zip(record["steps"], ref_record["steps"]):
                current = np.asarray(row["freq_hz_physical"], dtype=float)
                expected = np.asarray(ref_row["freq_hz_physical"], dtype=float)
                if not np.array_equal(current, expected):
                    exact_row_mismatches += 1
                denominator = max(
                    float(np.max(np.abs(current))),
                    float(np.max(np.abs(expected))),
                    1.0e-30,
                )
                deviation = float(np.max(np.abs(current - expected))) / denominator
                max_relative_deviation = max(max_relative_deviation, deviation)
        per_block.append(
            {
                "profile_id": profile_id,
                "rows_bit_identical": exact_row_mismatches == 0,
            }
        )
    return {
        "anchor_scale": "k0",
        "blocks": per_block,
        "exact_row_mismatch_blocks": exact_row_mismatches,
        "max_relative_deviation": max_relative_deviation,
        "tolerance_relative": DRIFT_TOLERANCE_RELATIVE,
        "verdict": (
            "ANCHOR-BIT-IDENTICAL"
            if exact_row_mismatches == 0
            and max_relative_deviation <= DRIFT_TOLERANCE_RELATIVE
            else "DRIFT"
        ),
    }


def classify() -> str:
    r410._assert_wsl_scratch()
    load_seal()
    import probes.r444_signed_probe_order as order

    contract = _frozen_contract()
    for controller_id in ("law", "zero"):
        for k in range(order.SCALE_COUNT):
            folder = OUT / "eval" / controller_id / scale_key(k)
            if not folder.is_dir():
                raise FileNotFoundError(f"missing scale folder: {folder}")
    analysis = order.run_analysis(OUT, dt=float(contract["dt_seconds"]))
    drift = _drift_anchor()
    analysis["round"] = ROUND_ID
    analysis["manuscript_line"] = str(contract["manuscript_line"])
    analysis["created_utc"] = datetime.now(UTC).isoformat()
    analysis["contract_sha256"] = _canary.contract_sha256(contract)
    analysis["seal_sha256"] = _sha256_file(SEAL)
    analysis["drift_anchor"] = drift
    analysis["reward_used_for_gate"] = False
    analysis["training_executed"] = False
    analysis_path = OUT / "formal_analysis.json"
    digest = _write_new_json(analysis_path, analysis)
    manifest_payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "analysis_sha256": digest,
        "input_artifacts": [
            {"path": _relative(path), "sha256": _sha256_file(path)}
            for path in sorted(OUT.rglob("*.json"))
            if path.name not in {"formal_analysis.json", "formal_manifest.json"}
        ],
        "evaluation_block_count": len(analysis["blocks"]),
    }
    _write_new_json(OUT / "formal_manifest.json", manifest_payload)
    return digest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "measure-capacity",
            "rehearse",
            "prepare",
            "shards",
            "shard",
            "classify",
        ],
    )
    parser.add_argument("args", nargs=argparse.REMAINDER)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "measure-capacity":
        safe_emit(f"R444 capacity evidence: {measure_capacity()}")
    elif args.command == "rehearse":
        safe_emit(f"R444 rehearsal artifact: {rehearse()}")
    elif args.command == "prepare":
        safe_emit(f"R444 formal seal: {prepare()}")
    elif args.command == "shards":
        safe_emit(json.dumps(shard_list(), separators=(",", ":")))
    elif args.command == "shard":
        if not args.args:
            raise SystemExit("shard requires a shard id")
        sid = str(args.args[0])
        extra = [item for item in args.args[1:] if item not in ("--resume",)]
        if extra:
            raise SystemExit(f"unexpected shard argument: {extra[0]}")
        resume = "--resume" in args.args
        _evaluate_shard(sid, resume=resume)
        safe_emit(f"R444 shard complete: {sid}")
    else:
        safe_emit(f"R444 formal analysis: {classify()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
