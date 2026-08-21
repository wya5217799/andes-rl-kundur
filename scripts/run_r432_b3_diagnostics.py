"""R432 B3 diagnostics-instrumented rerun (log-only wrapper around the frozen R410 runner).

Registered soft-spot program item B3: the R410 family retains only final-20
cost/multiplier traces, so no failure mechanism can be identified.  This
round reruns the repaired no-message and message arms at seeds 401-403 with
the byte-unchanged R410 learner and persists per-step/per-episode training
diagnostics.  The logging seam consumes zero RNG: a rehearsal-scope bitcheck
runs the frozen loop and the wrapped copy on the same short budget and
requires byte-identical final checkpoints.

WSL lifecycle (always through ``scripts/andes_scratch.py``):

    python scripts/andes_scratch.py scripts/run_r432_b3_diagnostics.py reuse-capacity
    python scripts/andes_scratch.py scripts/run_r432_b3_diagnostics.py rehearse
    python scripts/andes_scratch.py scripts/run_r432_b3_diagnostics.py prepare
    python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py \
        --runner scripts/run_r432_b3_diagnostics.py \
        --shards tmp/andes/r432_train_shards.json --workers 4 --round R432

Formal outputs are create-only and hashed under
``results/research_loop/r432_b3_diagnostics``.  No evaluation and no
classifier run: this is a reporting-only diagnostics round.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import copy
import csv
import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import numpy as np
import torch

_base_spec = importlib.util.spec_from_file_location(
    "_r432_r410_base", ROOT / "scripts/run_r410_message_repair.py"
)
if _base_spec is None or _base_spec.loader is None:
    raise RuntimeError("cannot load the frozen R410 parent runner")
base = importlib.util.module_from_spec(_base_spec)
sys.modules[_base_spec.name] = base
_base_spec.loader.exec_module(base)

ROUND_ID = "R432"
PLAN = ROOT / "memory/rounds/R432/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
REHEARSAL = ROOT / "memory/rounds/R432/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R432/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R432/formal_seal.json"
OUT = ROOT / "results/research_loop/r432_b3_diagnostics"
R430_CAPACITY = ROOT / "memory/rounds/R430/capacity_evidence.json"

# Names the verbatim copy needs from the frozen R410 module.
for _name in (
    "PerVSGMDActionProjector",
    "_agent_for",
    "_build_env",
    "_joint_obs",
    "_mask_actor_obs",
    "_save_agent_snapshot",
    "_write_new_json",
    "contract_sha256",
    "_scalar_step_reward",
    "physical_costs",
    "safe_emit",
    "_assert_wsl_scratch",
    "load_seal",
    "_installed_runtime",
    "_relative",
    "_sha256_file",
    "_read_hashed_json",
    "random",
):
    globals()[_name] = getattr(base, _name)

# Capture the frozen R410 functions before _patch_base rebinds the names
# (avoids self-recursion and keeps the bitcheck's frozen side genuine).
_BASE_BUILD_CONTRACT = base.build_contract
_BASE_SOURCE_MANIFEST = base._source_manifest
_BASE_PARENT_MANIFEST = base._parent_manifest
_BASE_TRAIN_ARM_SEED = base.train_arm_seed


def load_seal() -> dict[str, Any]:
    """Verify the R432 seal with the shared-host budget semantics
    (wsl + other_reserved == host)."""
    seal = _read_hashed_json(SEAL)
    if seal.get("round") != ROUND_ID:
        raise RuntimeError("seal belongs to another round")
    if seal.get("contract") != build_contract():
        raise RuntimeError("sealed contract drifted from the frozen module")
    if seal.get("contract_sha256") != contract_sha256(build_contract()):
        raise RuntimeError("sealed contract hash mismatch")
    launch = seal.get("launch", {})
    if int(launch.get("wsl_python_processes", 0)) + int(
        launch.get("other_reserved_processes", 0)
    ) != int(launch.get("host_process_budget", -1)):
        raise RuntimeError("sealed launch budget is inconsistent")
    learner_sha = (seal.get("sources") or {}).get("learner", {}).get("sha256")
    if learner_sha != _sha256_file(ROOT / "src/andes_rl_kundur/agents/cd_matd3.py"):
        raise RuntimeError("learner source drifted from the R432 seal")
    return seal


def build_contract() -> dict[str, Any]:
    return _BASE_BUILD_CONTRACT()


def authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    contract = build_contract()
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and "R432" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_closed": len(contract["profiles"]) == 8
        and list(contract["training_seeds"]) == [401, 402, 403],
        "output_absence": not OUT.exists(),
    }


def source_manifest() -> dict[str, dict[str, str]]:
    sources = _BASE_SOURCE_MANIFEST()
    replacements = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r432_b3_diagnostics.py",
        "parent_r410_runner": ROOT / "scripts/run_r410_message_repair.py",
    }
    for name, path in replacements.items():
        sources[name] = {
            "path": _relative(path),
            "sha256": _sha256_file(path),
        }
    return sources


def parent_manifest() -> dict[str, dict[str, str]]:
    paths = {
        "r410_plan": ROOT / "memory/rounds/R410/plan.md",
        "r410_analysis": ROOT
        / "results/research_loop/r410_message_repair/formal_analysis.json",
        "r427_verdict": ROOT / "memory/rounds/R427/verdict.md",
        "r430_analysis": ROOT
        / "results/research_loop/r430_adapted_sac_successor/formal_analysis.json",
        "program_b3": ROOT
        / "paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md",
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in paths.items()
    }


def _plan_process_budget_matches(capacity: dict[str, Any]) -> bool:
    plan_text = PLAN.read_text(encoding="utf-8")
    expected = int(capacity["wsl_python_processes"])
    host = expected + int(capacity.get("other_reserved_processes", 0))
    return bool(
        f"host_process_budget: {host}" in plan_text
        and f"wsl_python_processes: {expected}" in plan_text
        and "native_threads_per_process: 1" in plan_text
        and f"other_reserved_processes: {capacity.get('other_reserved_processes', 0)}"
        in plan_text
    )


def write_new_json(path: Path, payload: dict[str, Any]) -> str:
    mutable = copy.deepcopy(payload)
    if path.resolve() == REHEARSAL.resolve():
        bit = _bitcheck()
        mutable.setdefault("checks", {})["bitcheck_byte_identity"] = bool(
            bit["passed"]
        )
        mutable["bitcheck"] = bit
    if path.resolve() == SEAL.resolve():
        mutable["single_factor_change"] = (
            "zero science change; log-only persistence of the frozen R410 "
            "training loop (no RNG consumed); R432 = reporting-only "
            "diagnostics rerun of the repaired no-message and message arms"
        )
        launch = mutable.get("launch", {})
        launch["host_process_budget"] = 21
        launch["other_reserved_processes"] = 16
        mutable["launch"] = launch
        mutable["decision_sha256"] = _sha256_file(
            ROOT
            / "paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md"
        )
    return _write_new_json(path, mutable)


def _bitcheck() -> dict[str, Any]:
    """Frozen R410 loop vs the R432 copy (project-free path) on the same
    short budget must yield byte-identical final checkpoints."""
    import tempfile

    result: dict[str, Any] = {"passed": False, "budget": 2100, "seed": 777}
    tmp_root = Path(tempfile.mkdtemp(prefix="r432_bitcheck_"))
    arm = "cd_matd3_no_message"
    seed = result["seed"]
    budget = result["budget"]
    build_contract_orig = globals()["build_contract"]

    frozen_out = tmp_root / "frozen"
    copy_out = tmp_root / "copy"
    saved = {
        "build_contract": (base.build_contract, build_contract),
        "out": (base.OUT, OUT),
        "seal": (base.load_seal, load_seal),
    }
    tmp_contract = build_contract()
    tmp_contract["training_contract"]["total_interaction_steps"] = budget

    def _tmp_build() -> dict[str, Any]:
        return copy.deepcopy(tmp_contract)

    def _noop_seal() -> dict[str, Any]:
        return {}

    try:
        base.build_contract = _tmp_build
        base.OUT = frozen_out
        base.load_seal = _noop_seal
        _BASE_TRAIN_ARM_SEED(arm, seed)
        frozen_sha = _sha256_file(
            frozen_out / "train" / arm / f"seed{seed}" / "final.pt"
        )
    finally:
        base.build_contract = saved["build_contract"][0]
        base.OUT = saved["out"][0]
        base.load_seal = saved["seal"][0]
    try:
        globals()["build_contract"] = _tmp_build
        globals()["OUT"] = copy_out
        globals()["load_seal"] = _noop_seal
        train_arm_seed(arm, seed)
        copy_sha = _sha256_file(
            copy_out / "train" / arm / f"seed{seed}" / "final.pt"
        )
    finally:
        globals()["build_contract"] = build_contract_orig
        globals()["OUT"] = OUT
        globals()["load_seal"] = base.load_seal
    result["frozen_final_sha256"] = frozen_sha
    result["copy_final_sha256"] = copy_sha
    result["passed"] = frozen_sha == copy_sha
    return result


def train_arm_seed(
    arm_id: str,
    seed: int,
    restart_count: int = 0,
    total_steps: int | None = None,
    out_root: Path | None = None,
    require_seal: bool = True,
) -> str:
    """R410 training loop — verbatim copy with R432-LOG persistence lines
    only (no RNG consumed).  ``total_steps``/``out_root``/``require_seal``
    are added for the rehearsal bitcheck and default to the frozen
    behavior.
    """
    _assert_wsl_scratch()
    if require_seal:  # R432-LOG
        load_seal()  # R432-LOG
    root = out_root if out_root is not None else OUT  # R432-LOG
    contract = build_contract()
    arm_root = root / "train" / arm_id  # R432-LOG
    run_dir = arm_root / f"seed{seed}"
    if run_dir.exists():
        raise FileExistsError(f"training output exists: {run_dir}")
    if restart_count:
        crash_dir = arm_root / f"seed{seed}-attempt{restart_count}-crash"
        if not crash_dir.is_dir():
            raise RuntimeError(
                "restart requires the preserved crash quarantine directory"
            )
    run_dir.mkdir(parents=True, exist_ok=True)
    snapshots_dir = run_dir / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    _write_new_json(
        run_dir / "started.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "arm_id": arm_id,
            "training_seed": int(seed),
            "restart_count": int(restart_count),
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_sha256": contract_sha256(contract),
            "torch_threads": torch.get_num_threads(),
        },
    )
    development = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "development"
    ]
    scenarios = {
        str(scenario["scenario_id"]): (profile, scenario)
        for profile in development
        for scenario in profile["scenarios"]
    }
    schedule = list(contract["training_contract"]["development_scenario_order"])
    torch.manual_seed(int(seed))
    np.random.seed(int(seed))
    random.seed(int(seed))
    device = "cpu"
    agent = _agent_for(arm_id, device)
    envs = {
        str(profile["profile_id"]): _build_env(profile)
        for profile in development
    }
    projector = PerVSGMDActionProjector(
        action_slew_limit=float(contract["action_slew_limit"])
    )
    total_steps = int(  # R432-LOG
        total_steps  # R432-LOG
        if total_steps is not None  # R432-LOG
        else contract["training_contract"]["total_interaction_steps"]  # R432-LOG
    )  # R432-LOG
    steps_per_episode = int(contract["steps"])
    executed_steps = 0
    episodes_attempted = 0
    tds_failed_episodes = 0
    episode_common_costs: list[float] = []
    episode_scalar_returns: list[float] = []
    invalid_reason: str | None = None
    lagrange_trace: list[float] = []
    reward = contract["reward_contract"]["cd_matd3"]
    budget = float(reward["common_budget_per_episode"])
    multiplier_step = float(reward["lagrange_step"])
    multiplier_max = float(reward["lagrange_maximum"])
    episode_index = 0
    any_tds_failure = False
    # R432-LOG: per-step diagnostics row buffer (persisted to CSV).
    log_rows: list[list[float]] = []  # R432-LOG
    buffer_capacity = float(agent.buffer.capacity)  # R432-LOG
    episode_log_rows: list[list[float]] = []  # R432-LOG
    while executed_steps < total_steps:
        scenario_id = schedule[episode_index % len(schedule)]
        episode_index += 1
        profile, scenario = scenarios[scenario_id]
        env = envs[str(profile["profile_id"])]
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        projector.reset()
        initial_frequency = (
            np.asarray(env._get_vsg_omega(), dtype=float)
            * float(contract["physical_nominal_frequency_hz"])
        )
        previous_frequency = initial_frequency.copy()
        episode_common = 0.0
        episode_scalar = 0.0
        for _step_index in range(steps_per_episode):
            joint = _joint_obs(observation)
            actor_joint = _mask_actor_obs(arm_id, joint)
            raw_action = agent.act(actor_joint, deterministic=False)
            if not np.all(np.isfinite(raw_action)):
                invalid_reason = "nonfinite actor output"
                break
            action = projector.project(raw_action)
            action_dict = {
                actor: np.asarray(action[actor], dtype=np.float32)
                for actor in range(4)
            }
            observation, rewards, done, info = env.step(action_dict)
            executed_steps += 1
            frequencies = np.asarray(info["freq_hz_physical"], dtype=float)
            rocof = (frequencies - previous_frequency) / float(
                contract["dt_seconds"]
            )
            previous_frequency = frequencies.copy()
            tds_failed = bool(info["tds_failed"])
            next_joint = _joint_obs(observation)
            terminal = bool(done) or tds_failed
            if arm_id == "yang_scalar_td3":
                scalar_reward = _scalar_step_reward(rewards)
                episode_scalar += scalar_reward
                agent.store(
                    joint,
                    action.reshape(-1),
                    np.array([scalar_reward], dtype=np.float32),
                    next_joint,
                    terminal,
                )
            else:
                if tds_failed:
                    differential_cost = 50.0
                    common_cost = 50.0
                else:
                    differential, common = physical_costs(
                        frequencies[None, :],
                        rocof[None, :],
                        np.asarray(info["P_es"], dtype=float)[None, :],
                        contract=contract,
                    )
                    differential_cost = float(differential[0])
                    common_cost = float(common[0])
                episode_common += common_cost
                agent.store(
                    joint,
                    action.reshape(-1),
                    np.array(
                        [-differential_cost, -common_cost], dtype=np.float32
                    ),
                    next_joint,
                    terminal,
                )
            diagnostics = agent.update()
            # R432-LOG: persist the frozen update() diagnostics + replay
            # fill fraction (pure reads; no RNG consumed).
            log_rows.append(  # R432-LOG
                [  # R432-LOG
                    float(executed_steps),  # R432-LOG
                    float(diagnostics["critic_loss"])  # R432-LOG
                    if diagnostics is not None  # R432-LOG
                    else float("nan"),  # R432-LOG
                    float(diagnostics.get("actor_loss_mean", float("nan")))  # R432-LOG
                    if diagnostics is not None  # R432-LOG
                    else float("nan"),  # R432-LOG
                    float(diagnostics.get("lagrange", float("nan")))  # R432-LOG
                    if diagnostics is not None  # R432-LOG
                    else float("nan"),  # R432-LOG
                    float(agent.buffer.size) / buffer_capacity,  # R432-LOG
                ]  # R432-LOG
            )  # R432-LOG
            if (
                diagnostics is not None
                and not np.isfinite(diagnostics["critic_loss"])
            ):
                invalid_reason = "nonfinite critic loss"
                break
            if tds_failed:
                tds_failed_episodes += 1
                any_tds_failure = True
                break
        if invalid_reason is not None:
            break
        episodes_attempted += 1
        if arm_id != "yang_scalar_td3":
            multiplier = agent.lagrange_step(
                episode_common,
                budget=budget,
                step=multiplier_step,
                maximum=multiplier_max,
            )
            lagrange_trace.append(multiplier)
            episode_common_costs.append(episode_common)
            # R432-LOG: per-episode cost + multiplier.
            episode_log_rows.append(  # R432-LOG
                [  # R432-LOG
                    float(episodes_attempted),  # R432-LOG
                    float(episode_common),  # R432-LOG
                    float(multiplier),  # R432-LOG
                ]  # R432-LOG
            )  # R432-LOG
        else:
            episode_scalar_returns.append(episode_scalar)
            episode_log_rows.append(  # R432-LOG
                [  # R432-LOG
                    float(episodes_attempted),  # R432-LOG
                    float(episode_scalar),  # R432-LOG
                    float("nan"),  # R432-LOG
                ]  # R432-LOG
            )  # R432-LOG
        if episodes_attempted % 240 == 0:
            _save_agent_snapshot(
                agent, snapshots_dir / f"episode{episodes_attempted}.pt"
            )
    for env in envs.values():
        try:
            env.close()
        except Exception:
            pass
    convergence_valid = invalid_reason is None and executed_steps == total_steps
    missing = invalid_reason is not None
    checkpoint_path = run_dir / "final.pt"
    checkpoint_sha = None
    if convergence_valid:
        checkpoint_sha = _save_agent_snapshot(agent, checkpoint_path)
    # R432-LOG: persist the diagnostic CSV + hashed summary JSON.
    csv_path = run_dir / "diagnostics.csv"  # R432-LOG
    with csv_path.open("w", encoding="utf-8", newline="") as handle:  # R432-LOG
        writer = csv.writer(handle)  # R432-LOG
        writer.writerow(  # R432-LOG
            [  # R432-LOG
                "step",  # R432-LOG
                "critic_loss",  # R432-LOG
                "actor_loss_mean",  # R432-LOG
                "lagrange",  # R432-LOG
                "buffer_fill",  # R432-LOG
            ]  # R432-LOG
        )  # R432-LOG
        writer.writerows(log_rows)  # R432-LOG
    csv_sha = _sha256_file(csv_path)  # R432-LOG
    csv_rel = (  # R432-LOG
        str(csv_path.relative_to(ROOT))  # R432-LOG
        if csv_path.is_relative_to(ROOT)  # R432-LOG
        else str(csv_path)  # R432-LOG
    )  # R432-LOG
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "arm_id": arm_id,
        "training_seed": int(seed),
        "interaction_steps": int(executed_steps),
        "episodes_attempted": int(episodes_attempted),
        "diagnostics_csv": csv_rel,  # R432-LOG
        "diagnostics_csv_sha256": csv_sha,
        "critic_loss_min": float(np.nanmin([r[1] for r in log_rows])),
        "critic_loss_median": float(np.nanmedian([r[1] for r in log_rows])),
        "critic_loss_q1": float(np.nanpercentile([r[1] for r in log_rows], 25)),
        "critic_loss_q4": float(np.nanpercentile([r[1] for r in log_rows], 75)),
        "actor_loss_mean_median": float(
            np.nanmedian([r[2] for r in log_rows])
        ),
        "lagrange_final": float(lagrange_trace[-1]) if lagrange_trace else None,
        "lagrange_median": float(np.median(lagrange_trace))
        if lagrange_trace
        else None,
        "buffer_fill_final": float(agent.buffer.size) / buffer_capacity,
        "episode_rows": episode_log_rows,
        "episode_common_costs": episode_common_costs[-20:],
        "episode_scalar_returns": episode_scalar_returns[-20:],
        "lagrange_trace": lagrange_trace[-20:],
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(contract),
    }
    summary_sha = _write_new_json(  # R432-LOG
        run_dir / "diagnostics_summary.json", summary  # R432-LOG
    )  # R432-LOG
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "arm_id": arm_id,
        "training_seed": int(seed),
        "interaction_steps": int(executed_steps),
        "episodes_attempted": int(episodes_attempted),
        "tds_failed_episodes": int(tds_failed_episodes),
        "convergence_diagnostics_valid": bool(convergence_valid),
        "missing": bool(missing),
        "invalid_reason": invalid_reason,
        "restart_count": int(restart_count),
        "final_checkpoint_sha256": checkpoint_sha,
        "episode_common_costs": episode_common_costs[-20:],
        "episode_scalar_returns": episode_scalar_returns[-20:],
        "lagrange_trace": lagrange_trace[-20:],
        "any_tds_failure": bool(any_tds_failure),
        "diagnostics_summary_sha256": summary_sha,
        "diagnostics_csv_sha256": csv_sha,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(contract),
    }
    return _write_new_json(run_dir / "manifest.json", manifest)


def shard(shard_id: str) -> None:
    """Parse ``train|<arm>|<seed>`` shard ids for the shared driver."""
    phase, _, rest = shard_id.partition("|")
    if phase != "train":
        raise SystemExit(f"R432 supports train shards only: {shard_id}")
    arm_id, _, seed_text = rest.partition("|")
    seed = int(seed_text)
    safe_emit(
        "R432 diagnostics manifest: "
        + train_arm_seed(arm_id, seed)
    )


def reuse_capacity() -> str:
    """Reuse the R430 (R429 v3) ladder rung-4 measurement after a fresh
    no-other-process host check."""
    _assert_wsl_scratch()
    if CAPACITY.exists() or REHEARSAL.exists() or SEAL.exists() or OUT.exists():
        raise FileExistsError("R432 pre-attempt artifact already exists")
    other = base._r410_other_research_processes()
    # Concurrent join per the owner's parallel order (R425+R426 precedent):
    # the sibling R431 wave (15 workers + 1 driver) is declared as
    # other_reserved_processes=16 in this plan; any OTHER research process
    # still blocks.
    unexpected = [
        proc
        for proc in other
        if "run_r431_sac_slew" not in str(proc.get("command", ""))
        and "r431_train_shards" not in str(proc.get("command", ""))
    ]
    if unexpected:
        raise RuntimeError(
            "unexpected research Python processes are active: " + str(unexpected)
        )
    logical, physical_memory, wsl_available = base._memory_resources()
    inherited = _read_hashed_json(R430_CAPACITY)
    if inherited.get("readiness") != "RUN-READY" or int(
        inherited.get("selected_workers", 0)
    ) != 16:
        raise RuntimeError("R430 capacity evidence is not the registered 16-worker anchor")
    payload = copy.deepcopy(inherited)
    payload.update(
        {
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "authorization": (
                "owner ordered parallel supplementary experiments; R429 v3 "
                "ladder rung 4 reused with the sibling R431 wave live and "
                "declared as other_reserved_processes=16 (R425+R426 "
                "concurrent-join precedent); total-memory accounting green"
            ),
            "contract_sha256": contract_sha256(build_contract()),
            "host": {
                "logical_processors": logical,
                "physical_memory_bytes": physical_memory,
            },
            "wsl": {"memory_available_bytes": wsl_available},
            "other_processes": other,
            "readiness": "RUN-READY",
            "selected_workers": 4,
            "wsl_python_processes": 5,
            "host_process_budget": 21,
            "other_reserved_processes": 16,
            "native_threads_per_process": 1,
            "whole_host_python_process_budget": 21,
            "sources": source_manifest(),
            "installed_runtime": _installed_runtime(),
            "inherited_capacity": {
                "path": _relative(R430_CAPACITY),
                "sha256": _sha256_file(R430_CAPACITY),
                "reuse_basis": "identical CD-family training task; log-only wrapper",
            },
            "scientific_classification_inspected": False,
            "formal_authority": False,
            "training_executed": False,
        }
    )
    payload["empirical_anchor"]["source"] = (
        "R429 v3 rung-4 measurement plus fresh R432 no-load host check"
    )
    payload["empirical_anchor"]["concurrent_workers"] = 5
    return _write_new_json(CAPACITY, payload)


def _patch_base() -> None:
    for name, value in {
        "ROUND_ID": ROUND_ID,
        "PLAN": PLAN,
        "LINE": LINE,
        "REHEARSAL": REHEARSAL,
        "CAPACITY": CAPACITY,
        "SEAL": SEAL,
        "OUT": OUT,
    }.items():
        setattr(base, name, value)
    base.build_contract = build_contract
    base._source_manifest = source_manifest
    base._parent_manifest = parent_manifest
    base._authority_checks = authority_checks
    base._write_new_json = write_new_json
    base.train_arm_seed = train_arm_seed
    base.load_seal = load_seal
    base.OTHER_RESERVED_PROCESSES = 16
    base._plan_process_budget_matches = _plan_process_budget_matches


_patch_base()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["reuse-capacity", "rehearse", "prepare", "shard", "train"],
    )
    parser.add_argument("shard_id", nargs="?")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "reuse-capacity":
        safe_emit(f"R432 capacity evidence: {reuse_capacity()}")
    elif args.command == "rehearse":
        safe_emit(f"R432 rehearsal artifact: {base.rehearse()}")
    elif args.command == "prepare":
        safe_emit(f"R432 formal seal: {base.prepare()}")
    elif args.command == "shard":
        if args.shard_id is None:
            raise SystemExit("shard requires a registered shard id")
        shard(args.shard_id)
    else:
        if args.shard_id is None:
            raise SystemExit("train requires a shard id train|<arm>|<seed>")
        shard(args.shard_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
