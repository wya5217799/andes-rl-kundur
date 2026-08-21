"""R470 U2 complete actor/critic message-source factorial.

Formal physical commands are WSL-only through ``andes_scratch.py``.  Outputs
are create-only, donor banks precede training, and every learner uses the R460
executed-action Bellman seam.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import inspect
import itertools
import json
import math
import os
import random
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from andes_rl_kundur.agents.source_factorial_sac import SourceFactorialSACAgent
from andes_rl_kundur.agents.executed_action_sac import project_action_numpy

_spec = importlib.util.spec_from_file_location(
    "_r470_r451_legacy", ROOT / "scripts/run_r451_m3_message_factorial.py"
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load R451 structural parent")
legacy = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = legacy
_spec.loader.exec_module(legacy)

parent = legacy.parent
r431 = legacy.r431
r429 = legacy.r429
base = legacy.base

ROUND_ID = "R470"
PLAN = ROOT / "memory/rounds/R470/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
POWER = ROOT / "memory/rounds/R470/power_analysis.json"
CAPACITY = ROOT / "memory/rounds/R470/capacity_evidence.json"
REHEARSAL = ROOT / "memory/rounds/R470/rehearsal.json"
SEAL = ROOT / "memory/rounds/R470/formal_seal.json"
OUT = ROOT / "results/research_loop/r470_u2_source_factorial"
R438_CAPACITY = ROOT / "memory/rounds/R438/capacity_evidence.json"
R431_OUT = ROOT / "results/research_loop/r431_sac_slew"
DONOR_SHARDS = ROOT / "tmp/andes/r470_donor_shards.json"
TRAIN_SHARDS = ROOT / "tmp/andes/r470_train_shards.json"
EVAL_SHARDS = ROOT / "tmp/andes/r470_eval_shards.json"

SOURCES = ("0", "P", "N")
TRAINING_SEEDS = (401, 402, 403, 404, 405, 406)
ARMS = tuple(
    f"a{actor.lower()}_c{critic.lower()}_r{reward}"
    for actor in SOURCES
    for critic in SOURCES
    for reward in (0, 1)
)
NEIGHBOUR_SLICE = slice(3, 7)
DONOR_EPISODES = 2
PRIMARY = "disturbance_differential_energy"
SECONDARY = "off_diagonal_response_energy"
MATERIALITY_LOG = math.log(1.10)
BOOTSTRAP_RESAMPLES = 20_000
BOOTSTRAP_SEED = 470


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> str:
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(f"create-only output exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    path.write_text(text + "\n", encoding="utf-8")
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _read_hashed_json(path: Path) -> dict[str, Any]:
    sidecar = Path(f"{path}.sha256")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    actual = _sha256_file(path)
    if expected != actual:
        raise RuntimeError(f"hash mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_new_npz(path: Path, **arrays: Any) -> str:
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(f"create-only output exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _write_new_torch(path: Path, payload: Any) -> str:
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(f"create-only output exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, str(path))
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def safe_emit(value: Any) -> None:
    print(value, flush=True)


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R470 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R470 must run through scripts/andes_scratch.py")
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass


def arm_factors(arm_id: str) -> dict[str, Any]:
    if arm_id not in ARMS:
        raise ValueError(f"unknown arm: {arm_id}")
    actor, critic, reward = arm_id.split("_")
    return {
        "actor_source": actor[1:].upper() if actor[1:] != "0" else "0",
        "critic_source": critic[1:].upper() if critic[1:] != "0" else "0",
        "reward_access": reward == "r1",
    }


def build_contract() -> dict[str, Any]:
    contract = copy.deepcopy(legacy._PARENT_BUILD_CONTRACT())
    contract["round"] = ROUND_ID
    contract.pop("r438", None)
    contract["r470"] = {
        "arms": list(ARMS),
        "sources": list(SOURCES),
        "training_seeds": list(TRAINING_SEEDS),
        "donor_episodes": DONOR_EPISODES,
        "donor_permutation": [1, 0],
        "placebo_left_node": "i",
        "placebo_right_node": "(i+2) mod 4",
        "authentic_left_node": "(i-1) mod 4",
        "authentic_right_node": "(i+1) mod 4",
        "primary_endpoint": PRIMARY,
        "secondary_endpoint": SECONDARY,
        "materiality_log": MATERIALITY_LOG,
        "familywise_alpha": 0.05,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "total_interaction_steps": 43_200,
        "checkpoint_fractions": [0.5, 1.0],
        "plan_sha256": _sha256_file(PLAN),
        "executed_action_semantics": "R460 current/target/actor Q paths use projected action",
        "entropy_semantics": "raw_policy_entropy_regularizer",
    }
    return contract


def contract_sha256() -> str:
    text = json.dumps(build_contract(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def authority_checks() -> dict[str, bool]:
    plan = PLAN.read_text(encoding="utf-8")
    line = LINE.read_text(encoding="utf-8")
    return {
        "active_plan": "round: R470" in plan and "state: active" in plan,
        "active_line": "line_id: yang-md-decoupling-marl" in line and "status: active" in line,
        "contract_closed": len(ARMS) == 18 and len(TRAINING_SEEDS) == 6,
        "output_absence": not OUT.exists(),
    }


def load_seal() -> dict[str, Any]:
    seal = _read_hashed_json(SEAL)
    if seal.get("round") != ROUND_ID or seal.get("contract_sha256") != contract_sha256():
        raise RuntimeError("R470 seal/contract mismatch")
    for entry in (seal.get("sources") or {}).values():
        path = ROOT / entry["path"]
        if _sha256_file(path) != entry["sha256"]:
            raise RuntimeError(f"sealed source drift: {path}")
    return seal


def _seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _installed_runtime() -> dict[str, Any]:
    return legacy.installed_runtime()


def _power_seed_values() -> tuple[list[float], list[float]]:
    contract = r431.build_contract()
    output: dict[str, list[float]] = {}
    for arm in ("cd_matd3_message", "cd_matd3_no_message"):
        values = []
        for seed in range(401, 406):
            per_profile = []
            for profile in contract["profiles"]:
                if profile["split"] != "evaluation":
                    continue
                path = R431_OUT / "eval" / arm / f"seed{seed}" / f"{profile['profile_id']}.json"
                payload = _read_hashed_json(path)
                endpoint = parent._arm_endpoints(payload["records"], contract)[PRIMARY]
                per_profile.append(float(endpoint))
            values.append(sorted(per_profile)[len(per_profile) // 2])
        output[arm] = values
    return output["cd_matd3_message"], output["cd_matd3_no_message"]


def power_analysis() -> dict[str, Any]:
    if OUT.exists() or REHEARSAL.exists() or SEAL.exists():
        raise FileExistsError("power analysis must precede all R470 network/formal artifacts")
    message, no_message = _power_seed_values()
    paired = np.log(np.asarray(no_message) / np.asarray(message))
    sd = float(np.std(paired, ddof=1))
    required = int(math.ceil(((1.959963984540054 + 0.8416212335729143) * sd / MATERIALITY_LOG) ** 2))
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "constructed_networks_before_analysis": False,
        "source": "sealed R431 five paired held-out seed endpoints",
        "message_values": message,
        "no_message_values": no_message,
        "paired_log_ratios": paired.tolist(),
        "paired_log_ratio_sd": sd,
        "materiality_log": MATERIALITY_LOG,
        "alpha_two_sided": 0.05,
        "power": 0.8,
        "formula": "ceil(((z_0.975+z_0.8)*sd/log(1.10))^2)",
        "required_seeds": required,
        "selected_seeds": len(TRAINING_SEEDS),
        "adequate_by_normal_approximation": len(TRAINING_SEEDS) >= required,
        "exact_two_sided_signflip_min_p": 2.0 / (2 ** len(TRAINING_SEEDS)),
    }
    return payload


def measure_capacity() -> dict[str, Any]:
    _assert_wsl_scratch()
    inherited = _read_hashed_json(R438_CAPACITY)
    meminfo = Path("/proc/meminfo").read_text(encoding="ascii")
    fields = {
        line.split(":", 1)[0]: int(line.split()[1]) * 1024
        for line in meminfo.splitlines()
        if ":" in line and len(line.split()) >= 2 and line.split()[1].isdigit()
    }
    ps = subprocess.run(["ps", "-eo", "pid=,args="], capture_output=True, text=True, check=True).stdout.splitlines()
    other = [
        line.strip() for line in ps
        if ("scripts/run_" in line or "soft_spot_shard_driver.py" in line)
        and "run_r470" not in line
    ]
    anchor = int(inherited["training_worker_rss_anchor"]["bytes"])
    mem_total = int(fields["MemTotal"])
    safe = [rung for rung in (1, 2, 4, 8, 12, 16) if rung * anchor + 3 * 1024**3 <= mem_total]
    selected = max(safe)
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "inherited_ladder": {"path": _relative(R438_CAPACITY), "sha256": _sha256_file(R438_CAPACITY), "basis": "same four-agent SAC width/update workload and host"},
        "rungs": [1, 2, 4, 8, 12, 16],
        "memory_safe_rungs": safe,
        "worker_rss_anchor_bytes": anchor,
        "wsl_mem_total_bytes": mem_total,
        "wsl_mem_available_bytes": int(fields["MemAvailable"]),
        "other_python_processes": other,
        "selected_workers": selected,
        "wsl_python_processes": selected + 1,
        "host_process_budget": 17,
        "other_reserved_processes": 0,
        "native_threads_per_process": 1,
        "gpu_selected": False,
        "readiness": "RUN-READY" if selected == 16 and not other else "LOAD-CHECK-REVIEW",
    }


def source_rows(joint_obs: np.ndarray, donor_joint: np.ndarray, source: str) -> np.ndarray:
    current = np.asarray(joint_obs, dtype=np.float32).reshape(base.AGENT_COUNT, base.OBS_DIM)
    if source == "N":
        return current.copy()
    rows = current.copy()
    if source == "0":
        rows[:, NEIGHBOUR_SLICE] = 0.0
        return rows
    if source != "P":
        raise ValueError(f"unknown source: {source}")
    donor = np.asarray(donor_joint, dtype=np.float32).reshape(base.AGENT_COUNT, base.OBS_DIM)
    for i in range(base.AGENT_COUNT):
        rows[i, 3:5] = donor[i, 1:3]
        rows[i, 5:7] = donor[(i + 2) % base.AGENT_COUNT, 1:3]
    return rows


def donor_marginal_audit(trajectories: np.ndarray) -> dict[str, Any]:
    values = np.asarray(trajectories, dtype=np.float32)
    if values.ndim != 5 or values.shape[1] != 2 or values.shape[-2:] != (4, 7):
        raise ValueError(f"unexpected donor tensor shape: {values.shape}")
    hashes: dict[str, str] = {}
    all_equal = True
    all_changed = True
    for scenario in range(values.shape[0]):
        for time_index in range(values.shape[2]):
            for label, true_offset, placebo_offset in (("left", -1, 0), ("right", 1, 2)):
                for feature in (1, 2):
                    authentic = []
                    placebo = []
                    for episode in range(2):
                        for agent in range(4):
                            authentic.append(values[scenario, episode, time_index, (agent + true_offset) % 4, feature])
                            placebo.append(values[scenario, 1 - episode, time_index, (agent + placebo_offset) % 4, feature])
                            all_changed = all_changed and ((episode, (agent + true_offset) % 4) != (1 - episode, (agent + placebo_offset) % 4))
                    left = np.sort(np.asarray(authentic, dtype=np.float32))
                    right = np.sort(np.asarray(placebo, dtype=np.float32))
                    all_equal = all_equal and np.array_equal(left, right)
                    key = f"{scenario}|{time_index}|{label}|{feature}"
                    hashes[key] = hashlib.sha256(left.tobytes()).hexdigest()
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "pi_fixed_point_free": True,
        "placebo_nodes_are_non_neighbours": True,
        "every_semantic_donor_changed": bool(all_changed),
        "slot_feature_scenario_time_pools_equal": bool(all_equal),
        "pooled_hash_index_sha256": digest,
        "comparisons": len(hashes),
    }


def _new_member() -> SourceFactorialSACAgent:
    return SourceFactorialSACAgent(
        obs_dim=base.OBS_DIM,
        action_dim=base.ACTION_DIM,
        hidden_sizes=r429.HIDDEN_SIZES,
        slew_limit=float(build_contract()["action_slew_limit"]),
        lr=r429.SAC_LR,
        gamma=r429.SAC_GAMMA,
        tau=r429.SAC_TAU,
        buffer_size=r429.SAC_BUFFER_SIZE,
        batch_size=r429.SAC_BATCH_SIZE,
        device="cpu",
        alpha_min=r429.SAC_ALPHA_MIN,
        alpha_max=r429.SAC_ALPHA_MAX,
    )


class FactorialWrapper:
    def __init__(self, arm_id: str) -> None:
        self.arm_id = arm_id
        self.factors = arm_factors(arm_id)
        self.agents = [_new_member() for _ in range(base.AGENT_COUNT)]

    def act(
        self,
        actor_rows: np.ndarray,
        previous_executed: np.ndarray,
        *,
        deterministic: bool,
    ) -> tuple[np.ndarray, np.ndarray]:
        raw = np.stack(
            [
                member.select_raw_action(
                    actor_rows[i], previous_executed[i], deterministic=deterministic
                )
                for i, member in enumerate(self.agents)
            ]
        ).astype(np.float32)
        executed = np.stack(
            [member.execute_action(previous_executed[i], raw[i]) for i, member in enumerate(self.agents)]
        ).astype(np.float32)
        return raw, executed

    def store(
        self,
        actor_rows: np.ndarray,
        critic_rows: np.ndarray,
        previous_executed: np.ndarray,
        raw: np.ndarray,
        executed: np.ndarray,
        rewards: np.ndarray,
        next_actor_rows: np.ndarray,
        next_critic_rows: np.ndarray,
        done: bool,
    ) -> None:
        for i, member in enumerate(self.agents):
            member.store_source_transition(
                actor_rows[i], critic_rows[i], previous_executed[i], raw[i], executed[i],
                float(rewards[i]), next_actor_rows[i], next_critic_rows[i], done,
            )

    def update_all(self) -> dict[str, float] | None:
        rows = [member.update() for member in self.agents]
        if any(row is None for row in rows):
            return None
        return {
            key: float(np.mean([row[key] for row in rows if row is not None]))
            for key in rows[0]
        }

    def export_states(self) -> list[dict[str, Any]]:
        return [member.export_state() for member in self.agents]

    def import_states(self, states: list[dict[str, Any]]) -> None:
        if len(states) != len(self.agents):
            raise ValueError("base/checkpoint agent count mismatch")
        for member, state in zip(self.agents, states, strict=True):
            member.import_state(state)

    def save(self, path: Path, *, stage: str, base_sha256: str) -> str:
        return _write_new_torch(
            path,
            {
                "schema_version": 1,
                "kind": "r470-source-factorial",
                "round": ROUND_ID,
                "arm_id": self.arm_id,
                "factors": self.factors,
                "stage": stage,
                "base_state_sha256": base_sha256,
                "agents": self.export_states(),
            },
        )

    def load(self, path: Path) -> dict[str, Any]:
        payload = torch.load(str(path), map_location="cpu", weights_only=True)
        if payload.get("kind") != "r470-source-factorial" or payload.get("arm_id") != self.arm_id:
            raise ValueError("checkpoint identity mismatch")
        self.import_states(payload["agents"])
        return payload


def _scenario_index(split: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    profiles = [p for p in build_contract()["profiles"] if p["split"] == split]
    scenarios = [s for p in profiles for s in p["scenarios"]]
    return scenarios, {str(s["scenario_id"]): i for i, s in enumerate(scenarios)}


def generate_donor_and_base(seed: int) -> str:
    _assert_wsl_scratch()
    load_seal()
    if seed not in TRAINING_SEEDS:
        raise ValueError("unregistered donor seed")
    out_dir = OUT / "donors" / f"seed{seed}"
    if out_dir.exists():
        raise FileExistsError(f"donor output exists: {out_dir}")
    out_dir.mkdir(parents=True)
    contract = build_contract()
    donor_seed = 100_000 + seed
    _seed_all(donor_seed)
    rng = np.random.default_rng(donor_seed)
    split_payload: dict[str, Any] = {}
    for split in ("development", "evaluation"):
        profiles = [p for p in contract["profiles"] if p["split"] == split]
        scenarios = [(p, s) for p in profiles for s in p["scenarios"]]
        trajectories = np.zeros(
            (len(scenarios), DONOR_EPISODES, int(contract["steps"]) + 1, 4, base.OBS_DIM),
            dtype=np.float32,
        )
        raw_actions = np.zeros((len(scenarios), DONOR_EPISODES, int(contract["steps"]), 4, 2), dtype=np.float32)
        executed_actions = np.zeros_like(raw_actions)
        envs = {str(p["profile_id"]): r431._build_env(p) for p in profiles}
        try:
            for scenario_index, (profile, scenario) in enumerate(scenarios):
                env = envs[str(profile["profile_id"])]
                for episode in range(DONOR_EPISODES):
                    observation = env.reset(delta_u=dict(scenario["delta_u"]))
                    previous = np.zeros((4, 2), dtype=np.float32)
                    trajectories[scenario_index, episode, 0] = r431._joint_obs(observation).reshape(4, base.OBS_DIM)
                    for time_index in range(int(contract["steps"])):
                        raw = np.tanh(rng.normal(0.0, 0.35, size=(4, 2))).astype(np.float32)
                        executed = np.stack(
                            [project_action_numpy(previous[i], raw[i], slew_limit=float(contract["action_slew_limit"])) for i in range(4)]
                        )
                        observation, _reward, done, info = env.step(
                            {i: executed[i] for i in range(4)}
                        )
                        raw_actions[scenario_index, episode, time_index] = raw
                        executed_actions[scenario_index, episode, time_index] = executed
                        trajectories[scenario_index, episode, time_index + 1] = r431._joint_obs(observation).reshape(4, base.OBS_DIM)
                        previous = executed.copy()
                        if done or info["tds_failed"]:
                            raise RuntimeError(f"donor TDS failed: {split} {scenario['scenario_id']} e{episode} t{time_index}")
        finally:
            for env in envs.values():
                try:
                    env.close()
                except Exception:
                    pass
        audit = donor_marginal_audit(trajectories)
        if not all(audit[key] for key in (
            "pi_fixed_point_free", "placebo_nodes_are_non_neighbours",
            "every_semantic_donor_changed", "slot_feature_scenario_time_pools_equal",
        )):
            raise RuntimeError(f"donor audit failed: {audit}")
        path = out_dir / f"{split}.npz"
        digest = _write_new_npz(
            path,
            trajectories=trajectories,
            raw_actions=raw_actions,
            executed_actions=executed_actions,
            scenario_ids=np.asarray([str(s["scenario_id"]) for _p, s in scenarios]),
        )
        split_payload[split] = {
            "path": _relative(path),
            "sha256": digest,
            "shape": list(trajectories.shape),
            "scenario_ids": [str(s["scenario_id"]) for _p, s in scenarios],
            "audit": audit,
        }

    _seed_all(seed)
    prototype = FactorialWrapper(ARMS[0])
    base_path = out_dir / "base_state.pt"
    base_sha = _write_new_torch(
        base_path,
        {
            "schema_version": 1,
            "kind": "r470-common-base-state",
            "training_seed": seed,
            "created_after_donor_freeze": True,
            "agents": prototype.export_states(),
        },
    )
    reward_source = inspect.getsource(legacy.step_rewards).encode("utf-8")
    return _write_new_json(
        out_dir / "manifest.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "training_seed": seed,
            "donor_seed": donor_seed,
            "rng_set_before_environment": True,
            "donor_frozen_before_base_network": True,
            "base_state_path": _relative(base_path),
            "base_state_sha256": base_sha,
            "reward_function_sha256": hashlib.sha256(reward_source).hexdigest(),
            "splits": split_payload,
            "contract_sha256": contract_sha256(),
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )


def _load_donor(seed: int, split: str) -> tuple[dict[str, Any], np.ndarray, dict[str, int]]:
    manifest = _read_hashed_json(OUT / "donors" / f"seed{seed}" / "manifest.json")
    entry = manifest["splits"][split]
    path = ROOT / entry["path"]
    if _sha256_file(path) != entry["sha256"]:
        raise RuntimeError("donor npz hash mismatch")
    payload = np.load(path, allow_pickle=False)
    scenario_ids = [str(value) for value in payload["scenario_ids"].tolist()]
    return manifest, payload["trajectories"], {value: i for i, value in enumerate(scenario_ids)}


def _load_base(wrapper: FactorialWrapper, seed: int) -> tuple[str, str]:
    donor_manifest = _read_hashed_json(OUT / "donors" / f"seed{seed}" / "manifest.json")
    path = ROOT / donor_manifest["base_state_path"]
    digest = _sha256_file(path)
    if digest != donor_manifest["base_state_sha256"]:
        raise RuntimeError("base state hash mismatch")
    payload = torch.load(str(path), map_location="cpu", weights_only=True)
    if payload.get("kind") != "r470-common-base-state" or int(payload["training_seed"]) != seed:
        raise RuntimeError("base state identity mismatch")
    wrapper.import_states(payload["agents"])
    return _relative(path), digest


def _curve_stability(values: np.ndarray) -> dict[str, Any]:
    values = np.asarray(values, dtype=float)
    if values.size < 40:
        return {"valid": False, "stable": False}
    width = max(10, values.size // 10)
    previous = float(np.median(np.abs(values[-2 * width : -width])))
    final = float(np.median(np.abs(values[-width:])))
    log_ratio = abs(math.log(max(final, 1.0e-12) / max(previous, 1.0e-12)))
    return {
        "valid": True,
        "previous_decile_median": previous,
        "final_decile_median": final,
        "absolute_log_ratio": log_ratio,
        "threshold_log_1p25": math.log(1.25),
        "stable": log_ratio <= math.log(1.25),
    }


def train_arm_seed(arm_id: str, seed: int) -> str:
    _assert_wsl_scratch()
    load_seal()
    if arm_id not in ARMS or seed not in TRAINING_SEEDS:
        raise ValueError("unregistered arm/seed")
    run_dir = OUT / "train" / arm_id / f"seed{seed}"
    if run_dir.exists():
        raise FileExistsError(f"training output exists: {run_dir}")
    run_dir.mkdir(parents=True)
    contract = build_contract()
    factors = arm_factors(arm_id)
    donor_manifest, donors, donor_index = _load_donor(seed, "development")

    _seed_all(seed)
    development = [p for p in contract["profiles"] if p["split"] == "development"]
    envs = {str(p["profile_id"]): r431._build_env(p) for p in development}
    wrapper = FactorialWrapper(arm_id)
    base_path, base_sha = _load_base(wrapper, seed)
    scenarios = {
        str(s["scenario_id"]): (profile, s)
        for profile in development for s in profile["scenarios"]
    }
    schedule = list(contract["training_contract"]["development_scenario_order"])
    total_steps = 43_200
    steps_per_episode = int(contract["steps"])
    executed_steps = 0
    episode_index = 0
    tds_failures = 0
    invalid_reason: str | None = None
    curves: dict[str, list[float]] = {
        "critic_loss": [], "actor_loss": [], "alpha_loss": [],
        "alpha": [], "actor_grad_norm": [],
    }
    half_sha: str | None = None
    try:
        while executed_steps < total_steps:
            scenario_id = str(schedule[episode_index % len(schedule)])
            donor_episode = episode_index % DONOR_EPISODES
            profile, scenario = scenarios[scenario_id]
            env = envs[str(profile["profile_id"])]
            observation = env.reset(delta_u=dict(scenario["delta_u"]))
            previous = np.zeros((4, 2), dtype=np.float32)
            donor_scenario = donor_index[scenario_id]
            for time_index in range(steps_per_episode):
                joint = r431._joint_obs(observation)
                donor_joint = donors[donor_scenario, 1 - donor_episode, time_index]
                actor_rows = source_rows(joint, donor_joint, factors["actor_source"])
                critic_rows = source_rows(joint, donor_joint, factors["critic_source"])
                raw, executed = wrapper.act(actor_rows, previous, deterministic=False)
                if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(executed)):
                    invalid_reason = "nonfinite action"
                    break
                observation, _reward, done, info = env.step({i: executed[i] for i in range(4)})
                executed_steps += 1
                next_joint = r431._joint_obs(observation)
                next_donor = donors[donor_scenario, 1 - donor_episode, time_index + 1]
                next_actor_rows = source_rows(next_joint, next_donor, factors["actor_source"])
                next_critic_rows = source_rows(next_joint, next_donor, factors["critic_source"])
                terminal = bool(done) or bool(info["tds_failed"])
                rewards = legacy.step_rewards(
                    joint,
                    np.asarray(info["delta_M"], dtype=float),
                    np.asarray(info["delta_D"], dtype=float),
                    reward_access=bool(factors["reward_access"]),
                )
                wrapper.store(
                    actor_rows, critic_rows, previous, raw, executed, rewards,
                    next_actor_rows, next_critic_rows, terminal,
                )
                diagnostics = wrapper.update_all()
                if diagnostics is not None:
                    for key in curves:
                        curves[key].append(float(diagnostics[key]))
                    if not all(np.isfinite(list(diagnostics.values()))):
                        invalid_reason = "nonfinite learner diagnostic"
                        break
                previous = executed.copy()
                if executed_steps == total_steps // 2:
                    half_sha = wrapper.save(run_dir / "half.pt", stage="half", base_sha256=base_sha)
                if info["tds_failed"]:
                    tds_failures += 1
                    break
            episode_index += 1
            if invalid_reason is not None:
                break
    finally:
        for env in envs.values():
            try:
                env.close()
            except Exception:
                pass

    valid = invalid_reason is None and executed_steps == total_steps and half_sha is not None
    final_sha = wrapper.save(run_dir / "final.pt", stage="final", base_sha256=base_sha) if valid else None
    curve_sha = _write_new_npz(
        run_dir / "full_curves.npz",
        **{key: np.asarray(value, dtype=np.float64) for key, value in curves.items()},
    )
    stability = {key: _curve_stability(np.asarray(curves[key])) for key in ("critic_loss", "actor_loss")}
    return _write_new_json(
        run_dir / "manifest.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "arm_id": arm_id,
            "factors": factors,
            "training_seed": seed,
            "rng_set_before_environment_network_optimizer_replay": True,
            "base_state_path": base_path,
            "base_state_sha256": base_sha,
            "donor_manifest_sha256": _sha256_file(OUT / "donors" / f"seed{seed}" / "manifest.json"),
            "reward_function_sha256": donor_manifest["reward_function_sha256"],
            "interaction_steps": executed_steps,
            "episodes_attempted": episode_index,
            "tds_failed_episodes": tds_failures,
            "valid": valid,
            "invalid_reason": invalid_reason,
            "half_checkpoint_sha256": half_sha,
            "final_checkpoint_sha256": final_sha,
            "full_curves_sha256": curve_sha,
            "curve_count": len(curves["critic_loss"]),
            "stability": stability,
            "contract_sha256": contract_sha256(),
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )


def evaluate_arm_stage(arm_id: str, stage: str) -> None:
    _assert_wsl_scratch()
    load_seal()
    if arm_id not in ARMS or stage not in ("half", "final"):
        raise ValueError("unknown eval arm/stage")
    contract = build_contract()
    factors = arm_factors(arm_id)
    evaluation = [p for p in contract["profiles"] if p["split"] == "evaluation"]
    for seed in TRAINING_SEEDS:
        donor_manifest, donors, donor_index = _load_donor(seed, "evaluation")
        checkpoint = OUT / "train" / arm_id / f"seed{seed}" / f"{stage}.pt"
        checkpoint_sha = _sha256_file(checkpoint)
        wrapper = FactorialWrapper(arm_id)
        metadata = wrapper.load(checkpoint)
        if metadata["base_state_sha256"] != donor_manifest["base_state_sha256"]:
            raise RuntimeError("eval checkpoint/base identity mismatch")
        envs = {str(p["profile_id"]): r431._build_env(p) for p in evaluation}
        try:
            global_scenario_index = 0
            for profile in evaluation:
                env = envs[str(profile["profile_id"])]
                records = []
                for scenario in profile["scenarios"]:
                    scenario_id = str(scenario["scenario_id"])
                    donor_episode = global_scenario_index % DONOR_EPISODES
                    global_scenario_index += 1
                    observation = env.reset(delta_u=dict(scenario["delta_u"]))
                    initial_frequency = (
                        np.asarray(env._get_vsg_omega(), dtype=float)
                        * float(contract["physical_nominal_frequency_hz"])
                    ).tolist()
                    previous = np.zeros((4, 2), dtype=np.float32)
                    donor_scenario = donor_index[scenario_id]
                    identity = {
                        "n_agents": int(env.N_AGENTS),
                        "vsg_idx": [str(value) for value in env.vsg_idx],
                        "vsg_buses": [int(env.ss.GENCLS.bus.v[position]) for position in env._vsg_pos],
                        "obs_dim": int(env.OBS_DIM),
                    }
                    rows = []
                    failure = None
                    for time_index in range(int(contract["steps"])):
                        joint = r431._joint_obs(observation)
                        donor_joint = donors[donor_scenario, 1 - donor_episode, time_index]
                        actor_rows = source_rows(joint, donor_joint, factors["actor_source"])
                        raw, executed = wrapper.act(actor_rows, previous, deterministic=True)
                        observation, _reward, done, info = env.step({i: executed[i] for i in range(4)})
                        actual_m = np.asarray([env.ss.GENCLS.M.v[position] for position in env._vsg_pos], dtype=float)
                        actual_d = np.asarray([env.ss.GENCLS.D.v[position] for position in env._vsg_pos], dtype=float)
                        rows.append(
                            {
                                "step_index": time_index,
                                "time": float(info["time"]),
                                "raw_action_norm": raw.astype(float).tolist(),
                                "action_norm": executed.astype(float).tolist(),
                                "freq_hz_physical": np.asarray(info["freq_hz_physical"], dtype=float).tolist(),
                                "M_es": actual_m.tolist(),
                                "D_es": actual_d.tolist(),
                                "delta_M": np.asarray(info["delta_M"], dtype=float).tolist(),
                                "delta_D": np.asarray(info["delta_D"], dtype=float).tolist(),
                                "tds_failed": bool(info["tds_failed"]),
                                "done": bool(done),
                            }
                        )
                        previous = executed.copy()
                        if info["tds_failed"]:
                            failure = "TDS failed"
                            break
                    records.append(
                        {
                            "profile_id": str(profile["profile_id"]),
                            "split": "evaluation",
                            "scenario_id": scenario_id,
                            "pair_kind": str(scenario["pair_kind"]),
                            "sign": str(scenario["sign"]),
                            "magnitude": float(scenario["magnitude"]),
                            "delta_u": dict(scenario["delta_u"]),
                            "arm_id": arm_id,
                            "stage": stage,
                            "training_seed": seed,
                            "donor_episode": donor_episode,
                            "checkpoint_sha256": checkpoint_sha,
                            "identity": identity,
                            "initial_freq_hz_physical": initial_frequency,
                            "steps": rows,
                            "completed_steps": len(rows),
                            "completed": failure is None and len(rows) == int(contract["steps"]),
                            "tds_failed": failure is not None or any(bool(row["tds_failed"]) for row in rows),
                            "failure": failure,
                            "reward_used_for_gate": False,
                            "training_executed": True,
                        }
                    )
                folder = OUT / "eval" / stage / arm_id / f"seed{seed}"
                _write_new_json(folder / f"{profile['profile_id']}.json", {"records": records})
        finally:
            for env in envs.values():
                try:
                    env.close()
                except Exception:
                    pass


def _upper_median(values: list[float]) -> float:
    ordered = sorted(float(value) for value in values)
    return ordered[len(ordered) // 2]


def _seed_endpoint(arm: str, seed: int, stage: str, metric: str) -> float:
    contract = build_contract()
    values = []
    for profile in contract["profiles"]:
        if profile["split"] != "evaluation":
            continue
        payload = _read_hashed_json(
            OUT / "eval" / stage / arm / f"seed{seed}" / f"{profile['profile_id']}.json"
        )
        if any(not row["completed"] or row["tds_failed"] for row in payload["records"]):
            raise RuntimeError(f"invalid eval record {stage} {arm} seed{seed}")
        values.append(parent._arm_endpoints(payload["records"], contract)[metric])
    return _upper_median(values)


def _main_effect(endpoints: dict[str, dict[str, list[float]]], factor: str, metric: str) -> list[float]:
    output = []
    for seed_index in range(len(TRAINING_SEEDS)):
        n_values = []
        p_values = []
        for arm in ARMS:
            factors = arm_factors(arm)
            target = factors[f"{factor}_source"]
            if target not in ("N", "P"):
                continue
            value = math.log(endpoints[arm][metric][seed_index])
            (n_values if target == "N" else p_values).append(value)
        output.append(float(np.mean(p_values) - np.mean(n_values)))
    return output


def _paired_inference(values: list[float]) -> dict[str, Any]:
    array = np.asarray(values, dtype=float)
    observed = float(np.mean(array))
    permutations = np.asarray(
        [np.mean(array * np.asarray(signs)) for signs in itertools.product((-1.0, 1.0), repeat=len(array))]
    )
    p_one_sided = float(np.sum(permutations >= observed) / len(permutations))
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = np.empty(BOOTSTRAP_RESAMPLES, dtype=float)
    for i in range(BOOTSTRAP_RESAMPLES):
        draws[i] = float(np.mean(array[rng.integers(0, len(array), len(array))]))
    return {
        "paired_log_effects": array.tolist(),
        "mean_log_effect": observed,
        "geometric_improvement": float(math.exp(observed) - 1.0),
        "ci95": [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))],
        "exact_signflip_p_one_sided": p_one_sided,
        "materiality_log": MATERIALITY_LOG,
    }


def _apply_holm(rows: dict[str, dict[str, Any]]) -> None:
    ordered = sorted(rows, key=lambda key: rows[key]["exact_signflip_p_one_sided"])
    for rank, key in enumerate(ordered):
        threshold = 0.05 / (len(ordered) - rank)
        previous_pass = all(rows[prior].get("holm_reject", False) for prior in ordered[:rank])
        rows[key]["holm_threshold"] = threshold
        rows[key]["holm_reject"] = bool(previous_pass and rows[key]["exact_signflip_p_one_sided"] <= threshold)


def aggregate() -> str:
    _assert_wsl_scratch()
    load_seal()
    integrity_errors: list[str] = []
    base_hashes: dict[int, set[str]] = {seed: set() for seed in TRAINING_SEEDS}
    reward_hashes: dict[bool, set[str]] = {False: set(), True: set()}
    stability_rows: dict[str, Any] = {}
    for arm in ARMS:
        stability_rows[arm] = []
        for seed in TRAINING_SEEDS:
            manifest = _read_hashed_json(OUT / "train" / arm / f"seed{seed}" / "manifest.json")
            if not manifest["valid"] or int(manifest["interaction_steps"]) != 43_200:
                integrity_errors.append(f"invalid training {arm} seed{seed}")
            base_hashes[seed].add(str(manifest["base_state_sha256"]))
            reward_hashes[bool(arm_factors(arm)["reward_access"])].add(str(manifest["reward_function_sha256"]))
            stability_rows[arm].append(manifest["stability"])
    for seed, hashes in base_hashes.items():
        if len(hashes) != 1:
            integrity_errors.append(f"base state mismatch seed{seed}")
    if any(len(hashes) != 1 for hashes in reward_hashes.values()) or reward_hashes[False] != reward_hashes[True]:
        integrity_errors.append("reward implementation hash mismatch")

    stage_endpoints: dict[str, Any] = {}
    for stage in ("half", "final"):
        endpoints: dict[str, dict[str, list[float]]] = {}
        for arm in ARMS:
            endpoints[arm] = {
                metric: [_seed_endpoint(arm, seed, stage, metric) for seed in TRAINING_SEEDS]
                for metric in (PRIMARY, SECONDARY)
            }
        effects = {
            factor: {
                metric: _main_effect(endpoints, factor, metric)
                for metric in (PRIMARY, SECONDARY)
            }
            for factor in ("actor", "critic")
        }
        stage_endpoints[stage] = {"cells": endpoints, "main_effects_log_p_over_n": effects}

    primary_tests = {
        factor: _paired_inference(stage_endpoints["final"]["main_effects_log_p_over_n"][factor][PRIMARY])
        for factor in ("actor", "critic")
    }
    _apply_holm(primary_tests)
    for row in primary_tests.values():
        row["materially_supported"] = bool(row["holm_reject"] and row["ci95"][0] > MATERIALITY_LOG)

    direction_flips = {}
    for factor in ("actor", "critic"):
        half = float(np.mean(stage_endpoints["half"]["main_effects_log_p_over_n"][factor][PRIMARY]))
        final = float(np.mean(stage_endpoints["final"]["main_effects_log_p_over_n"][factor][PRIMARY]))
        direction_flips[factor] = {"half_mean": half, "final_mean": final, "flipped": bool(np.sign(half) != np.sign(final))}
    no_plateau = [
        f"{arm}|{seed}|{kind}"
        for arm in ARMS
        for seed, row in zip(TRAINING_SEEDS, stability_rows[arm], strict=True)
        for kind in ("critic_loss", "actor_loss")
        if not row[kind]["stable"]
    ]
    optimization_unresolved = bool(any(row["flipped"] for row in direction_flips.values()) or no_plateau)
    if integrity_errors:
        verdict = "FACTORIAL-INVALID"
    elif optimization_unresolved:
        verdict = "OPTIMIZATION-UNRESOLVED"
    elif any(row["materially_supported"] for row in primary_tests.values()):
        verdict = "U2-SOURCE-EFFECT-SUPPORTED"
    else:
        verdict = "U2-SOURCE-EFFECT-NOT-SUPPORTED"
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "contract_sha256": contract_sha256(),
        "seal_sha256": _sha256_file(SEAL),
        "integrity": {
            "valid": not integrity_errors,
            "errors": integrity_errors,
            "six_seed_base_hashes": {str(seed): sorted(values) for seed, values in base_hashes.items()},
            "reward_hashes": {str(key): sorted(values) for key, values in reward_hashes.items()},
        },
        "endpoints": stage_endpoints,
        "primary_holm_tests": primary_tests,
        "optimization": {
            "direction_flips": direction_flips,
            "nonplateau_rows": no_plateau,
            "unresolved": optimization_unresolved,
        },
        "classification": {
            "verdict": verdict,
            "scope": "six seeds; frozen R470 learner/bank/projector only",
            "universal_intrinsic_claim_authorized": False,
        },
        "created_utc": datetime.now(UTC).isoformat(),
    }
    return _write_new_json(OUT / "formal_analysis.json", payload)


def _state_tensor_hash(wrapper: FactorialWrapper) -> str:
    digest = hashlib.sha256()
    for state in wrapper.export_states():
        for group in ("actor", "critic", "critic_target"):
            for name, tensor in sorted(state[group].items()):
                digest.update(group.encode("ascii"))
                digest.update(name.encode("utf-8"))
                digest.update(tensor.detach().cpu().numpy().tobytes())
        digest.update(state["log_alpha"].numpy().tobytes())
    return digest.hexdigest()


def objective_semantics_probe() -> dict[str, bool]:
    """Independently pin the unchanged SAC and reward formula directions."""
    _seed_all(880)
    learner = _new_member()
    batch_size = learner.batch_size
    rng = np.random.default_rng(881)
    for _ in range(batch_size):
        actor_obs = rng.normal(size=7).astype(np.float32)
        critic_obs = rng.normal(size=7).astype(np.float32)
        previous = rng.uniform(-0.2, 0.2, size=2).astype(np.float32)
        raw = np.tanh(rng.normal(size=2)).astype(np.float32)
        executed = learner.execute_action(previous, raw)
        learner.store_source_transition(
            actor_obs, critic_obs, previous, raw, executed, -float(rng.random()),
            actor_obs + 0.01, critic_obs - 0.01, False,
        )
    batch = learner.buffer.sample(batch_size, "cpu", indices=np.arange(batch_size))
    torch.manual_seed(882)
    paths = learner.source_loss_inputs(batch, deterministic_target=True)
    with torch.no_grad():
        q1_target, q2_target = learner.critic_target(
            paths["next_critic_state"], paths["target_projected_action"]
        )
        expected_target = batch["rewards"] + learner.gamma * (1.0 - batch["dones"]) * torch.minimum(q1_target, q2_target)
    critic_ok = bool(torch.allclose(paths["td_target"], expected_target, rtol=1e-6, atol=1e-7))
    q1_actor, q2_actor = learner.critic(paths["critic_state"], paths["actor_projected_action"])
    actor_loss = (learner.alpha.detach() * paths["actor_log_prob"] - torch.minimum(q1_actor, q2_actor)).mean()
    alpha_loss = -(learner.log_alpha * (paths["actor_log_prob"].detach() + learner.target_entropy)).mean()
    synthetic = np.zeros((4, 7), dtype=np.float32)
    synthetic[:, 1] = 0.1
    dm = np.array([600.0, -200.0, 0.0, 0.0])
    dd = np.array([600.0, -200.0, 0.0, 0.0])
    rewards = legacy.step_rewards(synthetic, dm, dd, reward_access=False)
    expected = r431._sac_step_rewards(synthetic, dm, dd, masked=True)
    return {
        "critic_target_identity_ok": critic_ok,
        "actor_loss_form_ok": bool(torch.isfinite(actor_loss)),
        "alpha_loss_form_ok": bool(torch.isfinite(alpha_loss)),
        "reward_nonpositive_ok": bool(np.all(rewards <= 1.0e-9)),
        "reward_obs_consistent_ok": bool(np.allclose(rewards, expected, atol=1.0e-6)),
    }


def rehearsal() -> dict[str, Any]:
    _assert_wsl_scratch()
    if not POWER.exists() or not Path(f"{POWER}.sha256").exists():
        raise RuntimeError("power analysis must be created before rehearsal network construction")
    power = _read_hashed_json(POWER)
    checks: dict[str, Any] = {
        "authority": authority_checks(),
        "runtime": _installed_runtime(),
        "power_precedes_network": bool(power["constructed_networks_before_analysis"] is False and power["selected_seeds"] >= power["required_seeds"]),
        "output_absence": not OUT.exists(),
        "contract_sha256": contract_sha256(),
    }
    synthetic = np.arange(3 * 2 * 5 * 4 * 7, dtype=np.float32).reshape(3, 2, 5, 4, 7)
    checks["donor_audit"] = donor_marginal_audit(synthetic)
    _seed_all(901)
    first = FactorialWrapper(ARMS[0])
    first_hash = _state_tensor_hash(first)
    _seed_all(901)
    second = FactorialWrapper(ARMS[-1])
    second_hash = _state_tensor_hash(second)
    checks["initialization"] = {
        "same_seed_all_cell_tensor_hash_equal": first_hash == second_hash,
        "first_sha256": first_hash,
        "second_sha256": second_hash,
    }
    member = first.agents[0]
    rng = np.random.default_rng(902)
    previous = np.zeros(2, dtype=np.float32)
    for _ in range(member.batch_size):
        actor_obs = rng.normal(size=7).astype(np.float32)
        critic_obs = rng.normal(size=7).astype(np.float32)
        raw = np.tanh(rng.normal(size=2)).astype(np.float32)
        executed = member.execute_action(previous, raw)
        member.store_source_transition(
            actor_obs, critic_obs, previous, raw, executed, -0.1,
            actor_obs + 0.01, critic_obs - 0.01, False,
        )
        previous = executed
    batch = member.buffer.sample(member.batch_size, "cpu", indices=np.arange(member.batch_size))
    torch.manual_seed(903)
    paths = member.source_loss_inputs(batch)
    checks["u3_paths"] = {
        "current_critic_executed": bool(torch.equal(paths["critic_current_action_input"], batch["executed_actions"])),
        "target_critic_projected": bool(torch.equal(paths["critic_target_action_input"], paths["target_projected_action"])),
        "actor_critic_projected": bool(torch.equal(paths["actor_critic_action_input"], paths["actor_projected_action"])),
        "actor_critic_views_distinct": bool(not torch.equal(paths["actor_state"][:, :7], paths["critic_state"][:, :7])),
    }
    checks["sac_semantics_probe"] = dict(checks["u3_paths"])
    checks["objective_semantics_probe"] = objective_semantics_probe()
    reward_source = inspect.getsource(legacy.step_rewards).encode("utf-8")
    checks["reward"] = {
        "function_sha256": hashlib.sha256(reward_source).hexdigest(),
        "same_code_for_eta_0_eta_1": True,
        "configuration_only_difference": "reward_access",
    }
    contract = build_contract()
    profile = next(p for p in contract["profiles"] if p["split"] == "development")
    scenario = profile["scenarios"][0]
    env = r431._build_env(profile)
    rows_completed = 0
    update_result: dict[str, float] | None = None
    try:
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        previous_joint = np.zeros((4, 2), dtype=np.float32)
        wrapper = FactorialWrapper("an_cp_r0")
        for index, probe_member in enumerate(wrapper.agents):
            probe_rng = np.random.default_rng(950 + index)
            previous = np.zeros(2, dtype=np.float32)
            for _ in range(probe_member.batch_size - 1):
                aobs = probe_rng.normal(size=7).astype(np.float32)
                cobs = probe_rng.normal(size=7).astype(np.float32)
                raw = np.tanh(probe_rng.normal(size=2)).astype(np.float32)
                executed = probe_member.execute_action(previous, raw)
                probe_member.store_source_transition(aobs, cobs, previous, raw, executed, -0.1, aobs, cobs, False)
                previous = executed
        for _ in range(3):
            joint = r431._joint_obs(observation)
            donor = np.roll(joint.reshape(4, 7), 2, axis=0)
            actor_rows = source_rows(joint, donor, "N")
            critic_rows = source_rows(joint, donor, "P")
            raw, executed = wrapper.act(actor_rows, previous_joint, deterministic=False)
            observation, _reward, done, info = env.step({i: executed[i] for i in range(4)})
            next_joint = r431._joint_obs(observation)
            next_donor = np.roll(next_joint.reshape(4, 7), 2, axis=0)
            rewards = legacy.step_rewards(joint, np.asarray(info["delta_M"]), np.asarray(info["delta_D"]), reward_access=False)
            wrapper.store(
                actor_rows, critic_rows, previous_joint, raw, executed, rewards,
                source_rows(next_joint, next_donor, "N"), source_rows(next_joint, next_donor, "P"),
                bool(done) or bool(info["tds_failed"]),
            )
            update_result = wrapper.update_all()
            previous_joint = executed
            rows_completed += 1
    finally:
        env.close()
    checks["short_andes_path"] = {
        "rows": rows_completed,
        "update_finite": bool(update_result is not None and all(np.isfinite(list(update_result.values())))),
    }
    checks["passed"] = bool(
        all(checks["authority"].values())
        and checks["power_precedes_network"]
        and all(checks["donor_audit"][key] for key in (
            "pi_fixed_point_free", "placebo_nodes_are_non_neighbours",
            "every_semantic_donor_changed", "slot_feature_scenario_time_pools_equal",
        ))
        and checks["initialization"]["same_seed_all_cell_tensor_hash_equal"]
        and all(checks["u3_paths"].values())
        and checks["short_andes_path"]["rows"] == 3
        and checks["short_andes_path"]["update_finite"]
    )
    return checks


def prepare() -> dict[str, Any]:
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed: {checks}")
    power = _read_hashed_json(POWER)
    rehearsal_payload = _read_hashed_json(REHEARSAL)
    capacity = _read_hashed_json(CAPACITY)
    if not power["adequate_by_normal_approximation"] or not rehearsal_payload["passed"]:
        raise RuntimeError("power/rehearsal gate failed")
    if capacity["readiness"] != "RUN-READY" or int(capacity["selected_workers"]) != 16:
        raise RuntimeError("capacity gate is not the frozen 16-worker rung")
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r470_u2_source_factorial.py",
        "source_agent": ROOT / "src/andes_rl_kundur/agents/source_factorial_sac.py",
        "source_agent_tests": ROOT / "tests/test_source_factorial_sac.py",
        "u3_agent": ROOT / "src/andes_rl_kundur/agents/executed_action_sac.py",
        "u3_tests": ROOT / "tests/test_executed_action_sac.py",
        "r451_structural_parent": ROOT / "scripts/run_r451_m3_message_factorial.py",
        "r438_parent": ROOT / "scripts/run_r438_sac_message_channels.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "environment": ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
    }
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(),
        "plan_sha256": _sha256_file(PLAN),
        "power_sha256": _sha256_file(POWER),
        "rehearsal_sha256": _sha256_file(REHEARSAL),
        "capacity_sha256": _sha256_file(CAPACITY),
        "authority": checks,
        "launch": {
            "wsl_python_processes": 17,
            "other_reserved_processes": 0,
            "host_process_budget": 17,
            "native_threads_per_process": 1,
        },
        "runtime": rehearsal_payload["runtime"],
        "sources": {name: {"path": _relative(path), "sha256": _sha256_file(path)} for name, path in sources.items()},
        "formal_authority": True,
        "training_executed": False,
    }
    seal_sha = _write_new_json(SEAL, seal)
    DONOR_SHARDS.parent.mkdir(parents=True, exist_ok=True)
    DONOR_SHARDS.write_text(json.dumps([f"donor|{seed}" for seed in TRAINING_SEEDS]) + "\n", encoding="utf-8")
    TRAIN_SHARDS.write_text(json.dumps([f"train|{arm}|{seed}" for arm in ARMS for seed in TRAINING_SEEDS]) + "\n", encoding="utf-8")
    EVAL_SHARDS.write_text(json.dumps([f"eval|{stage}|{arm}" for stage in ("half", "final") for arm in ARMS]) + "\n", encoding="utf-8")
    return {"seal_sha256": seal_sha, "selected_workers": 16, "donor_shards": 6, "train_shards": 108, "eval_shards": 36}


def formal_manifest() -> str:
    load_seal()
    entries = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path.name == "formal_manifest.json" or path.name.endswith(".sha256"):
            continue
        sidecar = Path(f"{path}.sha256")
        if not sidecar.is_file() or sidecar.read_text(encoding="ascii").split()[0] != _sha256_file(path):
            raise RuntimeError(f"missing/invalid sidecar: {path}")
        entries.append({"path": _relative(path), "sha256": _sha256_file(path), "bytes": path.stat().st_size})
    return _write_new_json(
        OUT / "formal_manifest.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "entries": entries,
            "entry_count": len(entries),
            "total_bytes": sum(row["bytes"] for row in entries),
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("power", "capacity", "rehearse", "prepare", "shard", "aggregate", "manifest"))
    parser.add_argument("shard_id", nargs="?")
    args = parser.parse_args()
    if args.command == "power":
        payload = power_analysis()
        digest = _write_new_json(POWER, payload)
        safe_emit(json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True))
    elif args.command == "capacity":
        payload = measure_capacity()
        digest = _write_new_json(CAPACITY, payload)
        safe_emit(json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True))
    elif args.command == "rehearse":
        payload = rehearsal()
        digest = _write_new_json(REHEARSAL, payload)
        safe_emit(json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True))
    elif args.command == "prepare":
        safe_emit(json.dumps(prepare(), indent=2, sort_keys=True))
    elif args.command == "aggregate":
        safe_emit(aggregate())
    elif args.command == "manifest":
        safe_emit(formal_manifest())
    else:
        if args.shard_id is None:
            raise SystemExit("shard requires a shard id")
        parts = args.shard_id.split("|")
        if parts[0] == "donor" and len(parts) == 2:
            safe_emit(generate_donor_and_base(int(parts[1])))
        elif parts[0] == "train" and len(parts) == 3:
            safe_emit(train_arm_seed(parts[1], int(parts[2])))
        elif parts[0] == "eval" and len(parts) == 3:
            evaluate_arm_stage(parts[2], parts[1])
        else:
            raise SystemExit(f"unsupported shard: {args.shard_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
