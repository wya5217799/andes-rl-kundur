"""Sealed WSL runner for R411 (soft-spot program A1): probe-amplitude ladder.

Owner-authorized by the soft-spot experiment program
(``paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md``,
item A1, creative mode): re-evaluate the R410 frozen checkpoints (nine
arm-seeds plus the deterministic reference) at five amplitude factors
{0.5, 0.7, 1.0, 1.3, 1.5} applied to the registered probe magnitudes.
The single changed scientific factor versus R410 is ``probe_magnitude`` per
record (``localized_magnitude`` stays registered); the R410 checkpoints,
learners, estimators, guards, and classifier are consumed read-only.

The amplitude-1.0 bank re-executes the exact R410 evaluation conditions and
serves as the drift anchor: bit-identical rows versus the R410 records are
expected and checked with exact array equality.

Lifecycle (WSL only, always through the scratch launcher):
  python scripts/andes_scratch.py scripts/run_r411_probe_amplitude_ladder.py measure-capacity
  python scripts/andes_scratch.py scripts/run_r411_probe_amplitude_ladder.py rehearse
  python scripts/andes_scratch.py scripts/run_r411_probe_amplitude_ladder.py prepare
  python scripts/andes_scratch.py scripts/run_r411_probe_amplitude_ladder.py shards
  python scripts/andes_scratch.py scripts/run_r411_probe_amplitude_ladder.py shard <shard_id> [--resume]
  python scripts/andes_scratch.py scripts/run_r411_probe_amplitude_ladder.py classify

All formal artifacts are create-only with sha256 sidecars under
results/research_loop/r411_probe_amplitude_ladder/.
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
    classify_canary,
    evaluation_record_count,
)
from andes_rl_kundur.evaluation.md_decoupling_headroom import (  # noqa: E402
    summarise_profile,
)
import run_r410_message_repair as r410  # noqa: E402
from run_r401_cd_matd3_canary_contract import (  # noqa: E402
    _memory_resources,
    _other_research_python_processes,
)

ROUND_ID = "R411"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
PLAN = ROOT / "memory/rounds/R411/plan.md"
REHEARSAL = ROOT / "memory/rounds/R411/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R411/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R411/formal_seal.json"
OUT = ROOT / "results/research_loop/r411_probe_amplitude_ladder"
R410_OUT = ROOT / "results/research_loop/r410_message_repair"

AMPLITUDE_FACTORS = (0.5, 0.7, 1.0, 1.3, 1.5)
CAPACITY_RUNGS = (1, 2, 4, 8, 12, 16)
CAPACITY_TASKS_PER_RUNG = 32
EVAL_WORKER_RSS_FLOOR_BYTES = 944214016
MARGINAL_GAIN_MIN = 1.05
MARGINAL_GAIN_CONFIRM_LOW = 1.03
MARGINAL_GAIN_CONFIRM_HIGH = 1.07
DRIFT_TOLERANCE_RELATIVE = 1.0e-6
AMPLITUDE_INVARIANCE_RELATIVE_SPREAD = 0.20
CAPACITY_TASK_ARM = "cd_matd3_message"
CAPACITY_TASK_SEED = 401
CAPACITY_TASK_FACTOR = 0.7
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


def amplitude_key(factor: float) -> str:
    return f"{float(factor):g}".replace(".", "p")


def factor_from_key(key: str) -> float:
    return float(key.replace("p", "."))


def shard_id(arm_id: str, seed: int | None, key: str) -> str:
    suffix = "det" if seed is None else f"s{int(seed)}"
    return f"{arm_id}|{suffix}|a{key}"


def parse_shard_id(sid: str) -> tuple[str, int | None, str]:
    parts = str(sid).split("|")
    if len(parts) != 3 or not parts[2].startswith("a"):
        raise ValueError(f"malformed shard id: {sid}")
    arm_id, seed_token, key_token = parts
    if seed_token == "det":
        seed = None
    elif seed_token.startswith("s"):
        seed = int(seed_token[1:])
    else:
        raise ValueError(f"malformed shard id: {sid}")
    return arm_id, seed, key_token[1:]


def shard_list() -> list[str]:
    """Expand the frozen protocol: (arm, seed) x amplitude + deterministic."""
    contract = _frozen_contract()
    identifiers: list[tuple[str, int | None]] = [
        (str(arm_id), int(seed))
        for arm_id in contract["learning_arm_ids"]
        for seed in contract["training_seeds"]
    ] + [(str(contract["deterministic_arm_id"]), None)]
    return [
        shard_id(arm_id, seed, amplitude_key(factor))
        for arm_id, seed in identifiers
        for factor in AMPLITUDE_FACTORS
    ]


def evaluation_profiles(contract: Mapping[str, Any] | None = None) -> list[str]:
    spec = contract if contract is not None else _frozen_contract()
    return [
        str(profile["profile_id"])
        for profile in spec["profiles"]
        if profile["split"] == "evaluation"
    ]


def scaled_profiles(factor: float) -> list[dict[str, Any]]:
    """Evaluation profiles with probe_magnitude x factor, localized frozen."""
    profiles = []
    for source in _frozen_contract()["profiles"]:
        if source["split"] != "evaluation":
            continue
        profile = copy.deepcopy(source)
        profile["probe_magnitude"] = float(factor) * float(
            source["probe_magnitude"]
        )
        profile["scenarios"] = _canary._signed_scenarios(profile)
        profile["amplitude_factor"] = float(factor)
        profiles.append(profile)
    return profiles


def scaled_contract(factor: float) -> dict[str, Any]:
    """Frozen contract copy with the four evaluation profiles re-scaled."""
    contract = copy.deepcopy(_frozen_contract())
    contract["profiles"] = [
        copy.deepcopy(profile)
        for profile in contract["profiles"]
        if profile["split"] != "evaluation"
    ] + scaled_profiles(factor)
    return contract


def _source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r411_probe_amplitude_ladder.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "shard_driver_tests": ROOT / "tests/test_soft_spot_shard_driver.py",
        "learner": ROOT / "src/andes_rl_kundur/agents/cd_matd3.py",
        "learner_tests": ROOT / "tests/test_cd_matd3_learner.py",
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
        "r410_formal_analysis": R410_OUT / "formal_analysis.json",
        "r410_formal_manifest": R410_OUT / "formal_manifest.json",
        "program": ROOT
        / "paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md",
        "owner_decision": ROOT
        / "paper/yang_md_decoupling_marl/working"
        / "route_owner_decision_soft_spot_program_2026-08-16.md",
        "r410_runner": ROOT / "scripts/run_r410_message_repair.py",
    }
    contract = _frozen_contract()
    for arm_id in contract["learning_arm_ids"]:
        for seed in contract["training_seeds"]:
            parents[f"checkpoint_{arm_id}_s{seed}"] = (
                R410_OUT / "train" / str(arm_id) / f"seed{seed}" / "final.pt"
            )
            parents[f"manifest_{arm_id}_s{seed}"] = (
                R410_OUT / "train" / str(arm_id) / f"seed{seed}" / "manifest.json"
            )
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
    checkpoints = [
        R410_OUT / "train" / str(arm_id) / f"seed{seed}" / "final.pt"
        for arm_id in contract["learning_arm_ids"]
        for seed in contract["training_seeds"]
    ]
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and "R411" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_closed": len(contract["profiles"]) == 8
        and evaluation_record_count(contract) == 240
        and list(contract["training_seeds"]) == [401, 402, 403],
        "checkpoints_present": all(
            path.is_file() and Path(f"{path}.sha256").is_file()
            for path in checkpoints
        ),
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
                "soft_spot_shard_driver.py",
            )
        ):
            continue
        matches.append(entry)
    return matches


def _load_agent_for_shard(
    arm_id: str, seed: int | None
) -> tuple[Any, str | None]:
    if seed is None:
        return None, None
    checkpoint = R410_OUT / "train" / str(arm_id) / f"seed{seed}" / "final.pt"
    agent = r410._agent_for(str(arm_id), "cpu")
    agent.load(checkpoint)
    return agent, _sha256_file(checkpoint)


def _evaluate_profile(
    arm_id: str,
    seed: int | None,
    factor: float,
    profile: Mapping[str, Any],
    *,
    agent: Any,
    checkpoint_sha: str | None,
    controller: Any,
    projector: Any,
) -> dict[str, Any]:
    contract = _frozen_contract()
    env = r410._build_env(dict(profile))
    records = []
    try:
        for scenario in profile["scenarios"]:
            observation = env.reset(delta_u=dict(scenario["delta_u"]))
            projector.reset()
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
                    joint = r410._joint_obs(observation)
                    actor_joint = r410._mask_actor_obs(arm_id, joint)
                    raw = agent.act(actor_joint, deterministic=True)
                    action = projector.project(raw)
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
                "arm_id": arm_id,
                "training_seed": seed,
                "checkpoint_sha256": checkpoint_sha,
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
                "amplitude_factor": float(factor),
                "probe_magnitude_executed": float(profile["probe_magnitude"]),
                "localized_magnitude_executed": float(
                    profile["localized_magnitude"]
                ),
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
    arm_id, seed, key = parse_shard_id(sid)
    factor = factor_from_key(key)
    profiles = scaled_profiles(factor)
    agent, checkpoint_sha = _load_agent_for_shard(arm_id, seed)
    controller = r410._deterministic_controller() if seed is None else None
    from andes_rl_kundur.control.per_vsg_md import PerVSGMDActionProjector

    projector = PerVSGMDActionProjector(
        action_slew_limit=float(_frozen_contract()["action_slew_limit"])
    )
    folder = OUT / "eval" / arm_id / (
        "deterministic" if seed is None else f"seed{seed}"
    ) / f"a{key}"
    for profile in profiles:
        path = folder / (str(profile["profile_id"]) + ".json")
        sidecar = Path(f"{path}.sha256")
        if path.exists() or sidecar.exists():
            if resume and path.is_file() and sidecar.is_file():
                _read_hashed_json(path)
                continue
            raise FileExistsError(f"create-only output exists: {path}")
        payload = _evaluate_profile(
            arm_id,
            seed,
            factor,
            profile,
            agent=agent,
            checkpoint_sha=checkpoint_sha,
            controller=controller,
            projector=projector,
        )
        _write_new_json(
            path,
            {"records": payload["records"], "amplitude_factor": float(factor)},
        )


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
            raise RuntimeError(f"source drifted from the R411 seal: {name}")
    return seal


# ── capacity ladder ────────────────────────────────────────────────────

def _capacity_task(_task_index: int) -> dict[str, Any]:
    import resource

    factor = float(CAPACITY_TASK_FACTOR)
    profile = next(
        row
        for row in scaled_profiles(factor)
        if row["profile_id"] == CAPACITY_TASK_PROFILE
    )
    scenario = next(
        row
        for row in profile["scenarios"]
        if row["pair_kind"] == CAPACITY_TASK_PAIR
        and row["sign"] == CAPACITY_TASK_SIGN
    )
    agent, _sha = _load_agent_for_shard(CAPACITY_TASK_ARM, CAPACITY_TASK_SEED)
    from andes_rl_kundur.control.per_vsg_md import PerVSGMDActionProjector

    projector = PerVSGMDActionProjector(
        action_slew_limit=float(_frozen_contract()["action_slew_limit"])
    )
    env = r410._build_env(dict(profile))
    completed = 0
    tds_failed = False
    failure: str | None = None
    try:
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        projector.reset()
        for _step_index in range(int(_frozen_contract()["steps"])):
            joint = r410._joint_obs(observation)
            actor_joint = r410._mask_actor_obs(CAPACITY_TASK_ARM, joint)
            raw = agent.act(actor_joint, deterministic=True)
            action = projector.project(raw)
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
            raise FileExistsError(f"R411 pre-attempt artifact exists: {candidate}")
    if OUT.exists():
        raise FileExistsError("R411 formal output exists before capacity")
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
            "stage": "representative_eval_capacity_ladder_rungs_1_2_4_8_12_16",
            "authorization": (
                "owner-authorized soft-spot A1 probe-amplitude ladder; "
                "R410 checkpoints and estimators consumed read-only"
            ),
            "contract_sha256": _canary.contract_sha256(_frozen_contract()),
            "representative_task": {
                "arm": CAPACITY_TASK_ARM,
                "seed": CAPACITY_TASK_SEED,
                "amplitude_factor": CAPACITY_TASK_FACTOR,
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
            raise FileExistsError(f"R411 pre-attempt artifact exists: {candidate}")
    if not CAPACITY.exists():
        raise FileExistsError("capacity evidence must exist before rehearse")
    checks = _authority_checks()
    required = {
        "active_plan",
        "active_line",
        "contract_closed",
        "checkpoints_present",
        "r410_root_present",
        "output_absence",
    }
    if not all(checks.get(key) is True for key in required):
        raise RuntimeError("R411 rehearsal checks failed: " + str(checks))
    runtime = _installed_runtime()
    sources = _source_manifest()
    parents = _parent_manifest()
    checks["source_hash"] = bool(sources)
    checks["parent_hash"] = bool(parents)
    checks["installed_package"] = runtime["andes_version"] != "unknown"
    checks["installed_case"] = Path(runtime["case_path"]).is_file()
    contract = _frozen_contract()
    profile = scaled_profiles(0.5)[0]
    scenario = next(
        row
        for row in profile["scenarios"]
        if row["pair_kind"] == "differential" and row["sign"] == "positive"
    )
    env = r410._build_env(dict(profile))
    from andes_rl_kundur.control.per_vsg_md import PerVSGMDActionProjector

    projector = PerVSGMDActionProjector(
        action_slew_limit=float(contract["action_slew_limit"])
    )
    rehearsal_dir = ROOT / "tmp" / "andes" / "r411_rehearsal_checkpoints"
    rehearsal_dir.mkdir(parents=True, exist_ok=True)
    try:
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        for arm_id in contract["learning_arm_ids"]:
            checkpoint = R410_OUT / "train" / str(arm_id) / "seed401" / "final.pt"
            agent = r410._agent_for(str(arm_id), "cpu")
            agent.load(checkpoint)
            projector.reset()
            joint = r410._joint_obs(observation)
            actor_joint = r410._mask_actor_obs(str(arm_id), joint)
            raw = agent.act(actor_joint, deterministic=False)
            if not np.all(np.isfinite(raw)):
                raise RuntimeError("nonfinite rehearsal actor output")
            action = projector.project(raw)
            action_dict = {
                actor: np.asarray(action[actor], dtype=np.float32)
                for actor in range(4)
            }
            observation, _reward, _done, info = env.step(action_dict)
            if info["tds_failed"]:
                raise RuntimeError("rehearsal TDS failure")
            probe = rehearsal_dir / f"{arm_id}.pt"
            if probe.exists():
                probe.unlink()
            agent.save(probe)
            restored = r410._agent_for(str(arm_id), "cpu")
            restored.load(probe)
        controller = r410._deterministic_controller()
        controller.reset()
        from andes_rl_kundur.control.per_vsg_md import (
            adapt_v4_observations_to_physical,
        )

        action = controller.act(adapt_v4_observations_to_physical(observation))
        if not np.all(np.isfinite(np.asarray(action, dtype=float))):
            raise RuntimeError("nonfinite deterministic rehearsal action")
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
        "checkpoints_present",
        "r410_root_present",
        "output_absence",
    }
    if not all(checks.get(key) is True for key in required):
        raise RuntimeError("R411 authority checks failed: " + str(checks))
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R411 capacity gate is not RUN-READY")
    if not _plan_process_budget_matches(capacity):
        raise RuntimeError("R411 plan does not freeze the measured process budget")
    for payload in (rehearsal, capacity):
        if payload["sources"] != snapshot_sources:
            raise RuntimeError("R411 source drift before seal")
        if payload["installed_runtime"] != snapshot_runtime:
            raise RuntimeError("R411 runtime drift before seal")
    if rehearsal["parents"] != snapshot_parents:
        raise RuntimeError("R411 parent drift before seal")
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R411 formal artifact exists before sealing")
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
            "amplitude_factors": [float(value) for value in AMPLITUDE_FACTORS],
            "sources": snapshot_sources,
            "parents": snapshot_parents,
            "installed_runtime": snapshot_runtime,
            "plan_sha256": _sha256_file(PLAN),
            "line_sha256": _sha256_file(LINE),
            "program_sha256": _sha256_file(
                ROOT
                / "paper/yang_md_decoupling_marl/working"
                / "soft_spot_experiment_program.md"
            ),
            "rehearsal_sha256": _sha256_file(REHEARSAL),
            "capacity_sha256": _sha256_file(CAPACITY),
            "single_factor_change": (
                "probe_magnitude scaled per record by one of "
                "{0.5,0.7,1.0,1.3,1.5}; localized_magnitude, baselines, "
                "steady loads, checkpoints, learners, estimators, guards, "
                "and classifier are the R410 assets read-only"
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

def _block_path(
    arm_id: str, seed: int | None, key: str, profile_id: str
) -> Path:
    suffix = "deterministic" if seed is None else f"seed{seed}"
    return OUT / "eval" / arm_id / suffix / f"a{key}" / f"{profile_id}.json"


def _arm_seed_pairs() -> list[tuple[str, int | None]]:
    contract = _frozen_contract()
    return [
        (str(arm_id), int(seed))
        for arm_id in contract["learning_arm_ids"]
        for seed in contract["training_seeds"]
    ] + [(str(contract["deterministic_arm_id"]), None)]


def _collect_blocks() -> dict[tuple[str, str, int | None, str], list[dict[str, Any]]]:
    blocks: dict[tuple[str, str, int | None, str], list[dict[str, Any]]] = {}
    for factor in AMPLITUDE_FACTORS:
        key = amplitude_key(factor)
        for arm_id, seed in _arm_seed_pairs():
            for profile_id in evaluation_profiles():
                path = _block_path(arm_id, seed, key, profile_id)
                payload = _read_hashed_json(path)
                blocks[(key, arm_id, seed, profile_id)] = payload["records"]
    return blocks


def _summaries_for_factor(
    blocks: Mapping[tuple[str, str, int | None, str], list[dict[str, Any]]],
    factor: float,
) -> tuple[list[dict[str, Any]], list[str]]:
    key = amplitude_key(factor)
    summaries = []
    errors = []
    for arm_id, seed in _arm_seed_pairs():
        for profile_id in evaluation_profiles():
            records = blocks[(key, arm_id, seed, profile_id)]
            try:
                summary = summarise_profile(records, contract=scaled_contract(factor))
            except Exception as exc:
                errors.append(
                    f"{key}|{arm_id}|{seed}|{profile_id}: "
                    f"{type(exc).__name__}: {exc}"
                )
                continue
            summary["profile_id"] = profile_id
            summary["arm_id"] = arm_id
            summary["training_seed"] = None if seed is None else int(seed)
            summaries.append(summary)
    return summaries, errors


_ENDPOINTS = (
    "off_diagonal_response_energy",
    "disturbance_differential_energy",
)


def _r410_block_summaries() -> dict[tuple[str, int | None, str], dict[str, Any]]:
    contract = _frozen_contract()
    summaries = {}
    for arm_id, seed in _arm_seed_pairs():
        suffix = "deterministic" if seed is None else f"seed{seed}"
        for profile_id in evaluation_profiles():
            path = R410_OUT / "eval" / arm_id / suffix / f"{profile_id}.json"
            payload = _read_hashed_json(path)
            summary = summarise_profile(payload["records"], contract=contract)
            summaries[(arm_id, seed, profile_id)] = summary
    return summaries


def _rows_identical(
    records_a: Sequence[Mapping[str, Any]],
    records_b: Sequence[Mapping[str, Any]],
) -> bool:
    if len(records_a) != len(records_b):
        return False
    for record_a, record_b in zip(records_a, records_b):
        if len(record_a.get("steps", [])) != len(record_b.get("steps", [])):
            return False
        for row_a, row_b in zip(record_a["steps"], record_b["steps"]):
            if not np.array_equal(
                np.asarray(row_a["freq_hz_physical"], dtype=float),
                np.asarray(row_b["freq_hz_physical"], dtype=float),
            ):
                return False
    return True


def _drift_anchor(
    blocks: Mapping[tuple[str, str, int | None, str], list[dict[str, Any]]],
) -> dict[str, Any]:
    key = amplitude_key(1.0)
    r410_summaries = _r410_block_summaries()
    per_block = []
    exact_row_mismatches = 0
    max_relative_deviation = 0.0
    for (block_key, arm_id, seed, profile_id), records in blocks.items():
        if block_key != key:
            continue
        summary = summarise_profile(records, contract=scaled_contract(1.0))
        reference = r410_summaries[(arm_id, seed, profile_id)]
        deviations = {}
        for endpoint in _ENDPOINTS:
            value = float(summary[endpoint])
            ref = float(reference[endpoint])
            denominator = max(abs(value), abs(ref), 1.0e-30)
            deviation = abs(value - ref) / denominator
            deviations[endpoint] = deviation
            max_relative_deviation = max(max_relative_deviation, deviation)
        rows_identical = True
        try:
            r411_payload = _read_hashed_json(
                _block_path(arm_id, seed, key, profile_id)
            )
            suffix = "deterministic" if seed is None else f"seed{seed}"
            r410_payload = _read_hashed_json(
                R410_OUT / "eval" / arm_id / suffix / f"{profile_id}.json"
            )
            rows_identical = _rows_identical(
                r411_payload["records"], r410_payload["records"]
            )
        except Exception:
            rows_identical = False
        if not rows_identical:
            exact_row_mismatches += 1
        per_block.append(
            {
                "block": f"{key}|{arm_id}|{seed}|{profile_id}",
                "relative_deviations": deviations,
                "rows_bit_identical": rows_identical,
            }
        )
    return {
        "anchor_amplitude": 1.0,
        "blocks": per_block,
        "max_relative_deviation": max_relative_deviation,
        "exact_row_mismatch_blocks": exact_row_mismatches,
        "tolerance_relative": DRIFT_TOLERANCE_RELATIVE,
        "verdict": (
            "ANCHOR-BIT-IDENTICAL"
            if exact_row_mismatches == 0
            and max_relative_deviation <= DRIFT_TOLERANCE_RELATIVE
            else "DRIFT"
        ),
    }


def _guard_lookup(classification: Mapping[str, Any]) -> dict[tuple[str, str, int | None], list[str]]:
    lookup: dict[tuple[str, str, int | None], list[str]] = {}
    for failure in classification.get("guard_failures", []):
        key = (
            str(failure.get("profile_id", "")),
            str(failure.get("arm_id", "")),
            None if failure.get("training_seed") is None else int(failure["training_seed"]),
        )
        lookup.setdefault(key, [])
        lookup[key].extend(list(failure.get("failed", [])))
    return lookup


def _amplitude_table(
    blocks: Mapping[tuple[str, str, int | None, str], list[dict[str, Any]]],
    per_amplitude: Mapping[str, Any],
) -> dict[str, Any]:
    deterministic_arm = str(_frozen_contract()["deterministic_arm_id"])
    block_rows: dict[str, Any] = {}
    arm_seed_rows: dict[str, Any] = {}
    for factor in AMPLITUDE_FACTORS:
        key = amplitude_key(factor)
        summaries = {
            (s["arm_id"], s["training_seed"], s["profile_id"]): s
            for s in per_amplitude[key]["summaries"]
        }
        guards = _guard_lookup(per_amplitude[key]["classification"])
        classification = per_amplitude[key]["classification"]["classification"]
        for arm_id, seed in _arm_seed_pairs():
            endpoints = {
                endpoint: sum(
                    float(summaries[(arm_id, seed, profile_id)][endpoint])
                    for profile_id in evaluation_profiles()
                )
                for endpoint in _ENDPOINTS
            }
            arm_seed_rows[f"{key}|{arm_id}|{seed}"] = {
                "endpoints": endpoints,
            }
            for profile_id in evaluation_profiles():
                block_key = (key, arm_id, seed, profile_id)
                failed = guards.get((arm_id, seed, profile_id), [])
                block_rows[f"{key}|{arm_id}|{seed}|{profile_id}"] = {
                    "endpoints": {
                        endpoint: float(
                            summaries[(arm_id, seed, profile_id)][endpoint]
                        )
                        for endpoint in _ENDPOINTS
                    },
                    "guard_pass": (
                        classification != "CANARY-INVALID" and not failed
                    ),
                    "failed_guards": failed,
                }
    learning_arms = [
        str(arm_id) for arm_id in _frozen_contract()["learning_arm_ids"]
    ]
    seeds = [int(seed) for seed in _frozen_contract()["training_seeds"]]
    invariance: dict[str, Any] = {}
    sensitive = 0
    for arm_id in learning_arms:
        for seed in seeds:
            for endpoint in _ENDPOINTS:
                ratios = []
                for factor in AMPLITUDE_FACTORS:
                    key = amplitude_key(factor)
                    learning = float(
                        arm_seed_rows[f"{key}|{arm_id}|{seed}"]["endpoints"][endpoint]
                    )
                    reference = float(
                        arm_seed_rows[f"{key}|{deterministic_arm}|None"][
                            "endpoints"
                        ][endpoint]
                    )
                    ratios.append(
                        learning / reference if reference > 0.0 else float("inf")
                    )
                median = float(np.median(ratios))
                spread = (
                    (max(ratios) - min(ratios)) / median
                    if median > 0.0
                    else float("inf")
                )
                robust = spread <= AMPLITUDE_INVARIANCE_RELATIVE_SPREAD
                if not robust:
                    sensitive += 1
                invariance[f"{arm_id}|{seed}|{endpoint}"] = {
                    "amplitude_ratios_vs_deterministic": ratios,
                    "median": median,
                    "relative_spread": spread,
                    "robust": robust,
                }
    classifications = {
        amplitude_key(factor): per_amplitude[amplitude_key(factor)][
            "classification"
        ]["classification"]
        for factor in AMPLITUDE_FACTORS
    }
    consistent = len(set(classifications.values())) == 1
    return {
        "block_rows": block_rows,
        "arm_seed_rows": arm_seed_rows,
        "invariance": invariance,
        "invariance_verdict": (
            "AMPLITUDE-ROBUST" if sensitive == 0 else "AMPLITUDE-SENSITIVE"
        ),
        "sensitive_count": sensitive,
        "classifications_per_amplitude": classifications,
        "classification_verdict": (
            "CLASSIFICATION-AMPLITUDE-INVARIANT"
            if consistent
            else "CLASSIFICATION-AMPLITUDE-DEPENDENT"
        ),
    }


def classify() -> str:
    r410._assert_wsl_scratch()
    load_seal()
    contract = _frozen_contract()
    blocks = _collect_blocks()
    manifests = [
        _read_hashed_json(
            R410_OUT / "train" / str(arm_id) / f"seed{seed}" / "manifest.json"
        )
        for arm_id in contract["learning_arm_ids"]
        for seed in contract["training_seeds"]
    ]
    per_amplitude: dict[str, Any] = {}
    for factor in AMPLITUDE_FACTORS:
        key = amplitude_key(factor)
        summaries, errors = _summaries_for_factor(blocks, factor)
        classification = classify_canary(manifests, summaries, contract=contract)
        per_amplitude[key] = {
            "amplitude_factor": float(factor),
            "classification": classification,
            "summaries": summaries,
            "summary_errors": errors,
        }
    table = _amplitude_table(blocks, per_amplitude)
    drift = _drift_anchor(blocks)
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "manuscript_line": str(contract["manuscript_line"]),
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": _canary.contract_sha256(contract),
        "seal_sha256": _sha256_file(SEAL),
        "amplitude_factors": [float(value) for value in AMPLITUDE_FACTORS],
        "per_amplitude": {
            key: {
                "amplitude_factor": payload["amplitude_factor"],
                "classification": payload["classification"],
                "summary_errors": payload["summary_errors"],
            }
            for key, payload in per_amplitude.items()
        },
        "amplitude_table": table,
        "drift_anchor": drift,
        "reward_used_for_gate": False,
        "training_executed": False,
    }
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
        "amplitude_factors": [float(value) for value in AMPLITUDE_FACTORS],
        "evaluation_block_count": len(blocks),
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
        safe_emit(f"R411 capacity evidence: {measure_capacity()}")
    elif args.command == "rehearse":
        safe_emit(f"R411 rehearsal artifact: {rehearse()}")
    elif args.command == "prepare":
        safe_emit(f"R411 formal seal: {prepare()}")
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
        safe_emit(f"R411 shard complete: {sid}")
    else:
        safe_emit(f"R411 formal analysis: {classify()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
