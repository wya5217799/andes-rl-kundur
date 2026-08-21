"""R471 output-isolated successor to R470 with a corrected donor terminal gate."""

# ruff: noqa: E402, I001

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import scripts.run_r470_u2_source_factorial as parent


ROUND_ID = "R471"
PLAN = ROOT / "memory/rounds/R471/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
POWER = ROOT / "memory/rounds/R471/power_analysis.json"
CAPACITY = ROOT / "memory/rounds/R471/capacity_evidence.json"
REHEARSAL = ROOT / "memory/rounds/R471/rehearsal.json"
SEAL = ROOT / "memory/rounds/R471/formal_seal.json"
OUT = ROOT / "results/research_loop/r471_u2_source_factorial"
DONOR_SHARDS = ROOT / "tmp/andes/r471_donor_shards.json"
TRAIN_SHARDS = ROOT / "tmp/andes/r471_train_shards.json"
EVAL_SHARDS = ROOT / "tmp/andes/r471_eval_shards.json"

for _name, _value in {
    "ROUND_ID": ROUND_ID,
    "PLAN": PLAN,
    "LINE": LINE,
    "POWER": POWER,
    "CAPACITY": CAPACITY,
    "REHEARSAL": REHEARSAL,
    "SEAL": SEAL,
    "OUT": OUT,
    "DONOR_SHARDS": DONOR_SHARDS,
    "TRAIN_SHARDS": TRAIN_SHARDS,
    "EVAL_SHARDS": EVAL_SHARDS,
}.items():
    setattr(parent, _name, _value)

_r470_build_contract = parent.build_contract
_r470_rehearsal = parent.rehearsal
_r470_measure_capacity = parent.measure_capacity


def build_contract() -> dict[str, Any]:
    contract = _r470_build_contract()
    inherited = contract.pop("r470")
    inherited["successor_of"] = "R470"
    inherited["only_semantic_change"] = (
        "accept done=True at final registered step; reject only TDS failure or premature done"
    )
    contract["r471"] = inherited
    return contract


def authority_checks() -> dict[str, bool]:
    plan = PLAN.read_text(encoding="utf-8")
    line = LINE.read_text(encoding="utf-8")
    return {
        "active_plan": "round: R471" in plan and "state: active" in plan,
        "active_line": "line_id: yang-md-decoupling-marl" in line and "status: active" in line,
        "contract_closed": len(parent.ARMS) == 18 and len(parent.TRAINING_SEEDS) == 6,
        "output_absence": not OUT.exists(),
    }


def donor_terminal_invalid(*, done: bool, tds_failed: bool, time_index: int, steps: int) -> bool:
    return bool(tds_failed) or (bool(done) and int(time_index) < int(steps) - 1)


def rehearsal() -> dict[str, Any]:
    checks = _r470_rehearsal()
    truth = {
        "normal_nonterminal_accepted": not donor_terminal_invalid(done=False, tds_failed=False, time_index=5, steps=30),
        "normal_horizon_done_accepted": not donor_terminal_invalid(done=True, tds_failed=False, time_index=29, steps=30),
        "premature_done_rejected": donor_terminal_invalid(done=True, tds_failed=False, time_index=28, steps=30),
        "tds_failure_rejected": donor_terminal_invalid(done=False, tds_failed=True, time_index=5, steps=30),
    }
    checks["terminal_truth_table"] = truth
    checks["passed"] = bool(checks["passed"] and all(truth.values()))
    return checks


def measure_capacity() -> dict[str, Any]:
    payload = _r470_measure_capacity()
    payload["other_python_processes"] = [
        row for row in payload["other_python_processes"]
        if "run_r471_u2_source_factorial.py capacity" not in row
    ]
    payload["readiness"] = (
        "RUN-READY"
        if int(payload["selected_workers"]) == 16 and not payload["other_python_processes"]
        else "LOAD-CHECK-REVIEW"
    )
    payload["self_process_excluded"] = True
    return payload


def generate_donor_and_base(seed: int) -> str:
    """R470 donor implementation with normal horizon completion accepted."""
    parent._assert_wsl_scratch()
    parent.load_seal()
    if seed not in parent.TRAINING_SEEDS:
        raise ValueError("unregistered donor seed")
    out_dir = OUT / "donors" / f"seed{seed}"
    if out_dir.exists():
        raise FileExistsError(f"donor output exists: {out_dir}")
    out_dir.mkdir(parents=True)
    contract = parent.build_contract()
    donor_seed = 100_000 + seed
    parent._seed_all(donor_seed)
    rng = np.random.default_rng(donor_seed)
    split_payload: dict[str, Any] = {}
    for split in ("development", "evaluation"):
        profiles = [p for p in contract["profiles"] if p["split"] == split]
        scenarios = [(p, s) for p in profiles for s in p["scenarios"]]
        trajectories = np.zeros(
            (len(scenarios), parent.DONOR_EPISODES, int(contract["steps"]) + 1, 4, parent.base.OBS_DIM),
            dtype=np.float32,
        )
        raw_actions = np.zeros((len(scenarios), parent.DONOR_EPISODES, int(contract["steps"]), 4, 2), dtype=np.float32)
        executed_actions = np.zeros_like(raw_actions)
        envs = {str(p["profile_id"]): parent.r431._build_env(p) for p in profiles}
        try:
            for scenario_index, (profile, scenario) in enumerate(scenarios):
                env = envs[str(profile["profile_id"])]
                for episode in range(parent.DONOR_EPISODES):
                    observation = env.reset(delta_u=dict(scenario["delta_u"]))
                    previous = np.zeros((4, 2), dtype=np.float32)
                    trajectories[scenario_index, episode, 0] = parent.r431._joint_obs(observation).reshape(4, parent.base.OBS_DIM)
                    for time_index in range(int(contract["steps"])):
                        raw = np.tanh(rng.normal(0.0, 0.35, size=(4, 2))).astype(np.float32)
                        executed = np.stack(
                            [parent.project_action_numpy(previous[i], raw[i], slew_limit=float(contract["action_slew_limit"])) for i in range(4)]
                        )
                        observation, _reward, done, info = env.step({i: executed[i] for i in range(4)})
                        raw_actions[scenario_index, episode, time_index] = raw
                        executed_actions[scenario_index, episode, time_index] = executed
                        trajectories[scenario_index, episode, time_index + 1] = parent.r431._joint_obs(observation).reshape(4, parent.base.OBS_DIM)
                        previous = executed.copy()
                        if donor_terminal_invalid(
                            done=bool(done), tds_failed=bool(info["tds_failed"]),
                            time_index=time_index, steps=int(contract["steps"]),
                        ):
                            raise RuntimeError(f"donor TDS/premature terminal: {split} {scenario['scenario_id']} e{episode} t{time_index}")
        finally:
            for env in envs.values():
                try:
                    env.close()
                except Exception:
                    pass
        audit = parent.donor_marginal_audit(trajectories)
        if not all(audit[key] for key in (
            "pi_fixed_point_free", "placebo_nodes_are_non_neighbours",
            "every_semantic_donor_changed", "slot_feature_scenario_time_pools_equal",
        )):
            raise RuntimeError(f"donor audit failed: {audit}")
        path = out_dir / f"{split}.npz"
        digest = parent._write_new_npz(
            path,
            trajectories=trajectories,
            raw_actions=raw_actions,
            executed_actions=executed_actions,
            scenario_ids=np.asarray([str(s["scenario_id"]) for _p, s in scenarios]),
        )
        split_payload[split] = {
            "path": parent._relative(path), "sha256": digest,
            "shape": list(trajectories.shape),
            "scenario_ids": [str(s["scenario_id"]) for _p, s in scenarios],
            "audit": audit,
        }
    parent._seed_all(seed)
    prototype = parent.FactorialWrapper(parent.ARMS[0])
    base_path = out_dir / "base_state.pt"
    base_sha = parent._write_new_torch(
        base_path,
        {
            "schema_version": 1, "kind": "r470-common-base-state",
            "training_seed": seed, "created_after_donor_freeze": True,
            "agents": prototype.export_states(),
        },
    )
    reward_source = parent.inspect.getsource(parent.legacy.step_rewards).encode("utf-8")
    return parent._write_new_json(
        out_dir / "manifest.json",
        {
            "schema_version": 1, "round": ROUND_ID, "training_seed": seed,
            "donor_seed": donor_seed, "rng_set_before_environment": True,
            "donor_frozen_before_base_network": True,
            "normal_horizon_done_accepted": True,
            "premature_done_rejected": True,
            "base_state_path": parent._relative(base_path),
            "base_state_sha256": base_sha,
            "reward_function_sha256": parent.hashlib.sha256(reward_source).hexdigest(),
            "splits": split_payload,
            "contract_sha256": parent.contract_sha256(),
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )


def prepare() -> dict[str, Any]:
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed: {checks}")
    power = parent._read_hashed_json(POWER)
    rehearsal = parent._read_hashed_json(REHEARSAL)
    capacity = parent._read_hashed_json(CAPACITY)
    if not power["adequate_by_normal_approximation"] or not rehearsal["passed"]:
        raise RuntimeError("power/rehearsal gate failed")
    if capacity["readiness"] != "RUN-READY" or int(capacity["selected_workers"]) != 16:
        raise RuntimeError("capacity gate failed")
    sources = {
        "successor_runner": Path(__file__).resolve(),
        "successor_tests": ROOT / "tests/test_run_r471_u2_source_factorial.py",
        "sealed_r470_parent": ROOT / "scripts/run_r470_u2_source_factorial.py",
        "source_agent": ROOT / "src/andes_rl_kundur/agents/source_factorial_sac.py",
        "source_agent_tests": ROOT / "tests/test_source_factorial_sac.py",
        "u3_agent": ROOT / "src/andes_rl_kundur/agents/executed_action_sac.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "environment": ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
    }
    seal = {
        "schema_version": 1, "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": parent.contract_sha256(),
        "plan_sha256": parent._sha256_file(PLAN),
        "power_sha256": parent._sha256_file(POWER),
        "rehearsal_sha256": parent._sha256_file(REHEARSAL),
        "capacity_sha256": parent._sha256_file(CAPACITY),
        "authority": checks,
        "launch": {"wsl_python_processes": 17, "other_reserved_processes": 0, "host_process_budget": 17, "native_threads_per_process": 1},
        "runtime": rehearsal["runtime"],
        "sources": {name: {"path": parent._relative(path), "sha256": parent._sha256_file(path)} for name, path in sources.items()},
        "formal_authority": True, "training_executed": False,
    }
    seal_sha = parent._write_new_json(SEAL, seal)
    DONOR_SHARDS.parent.mkdir(parents=True, exist_ok=True)
    DONOR_SHARDS.write_text(json.dumps([f"donor|{seed}" for seed in parent.TRAINING_SEEDS]) + "\n", encoding="utf-8")
    TRAIN_SHARDS.write_text(json.dumps([f"train|{arm}|{seed}" for arm in parent.ARMS for seed in parent.TRAINING_SEEDS]) + "\n", encoding="utf-8")
    EVAL_SHARDS.write_text(json.dumps([f"eval|{stage}|{arm}" for stage in ("half", "final") for arm in parent.ARMS]) + "\n", encoding="utf-8")
    return {"seal_sha256": seal_sha, "selected_workers": 16, "donor_shards": 6, "train_shards": 108, "eval_shards": 36}


parent.authority_checks = authority_checks
parent.build_contract = build_contract
parent.measure_capacity = measure_capacity
parent.rehearsal = rehearsal
parent.generate_donor_and_base = generate_donor_and_base
parent.prepare = prepare


if __name__ == "__main__":
    raise SystemExit(parent.main())
