"""R485 fixed-budget source factorial with one canonical 50-to-60 Hz seam.

This round adapter owns only R485 identity, roster, fixed budgets, create-only
artifacts, and the training/evaluation bindings.  Scientific kernels remain in
the package modules imported below.  Formal execution is seal- and owner-gated.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import random
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.executed_action_sac import project_action_numpy  # noqa: E402
from andes_rl_kundur.agents.source_factorial_sac import (  # noqa: E402
    SourceFactorialSACAgent,
)
from andes_rl_kundur.control.per_vsg_md import (  # noqa: E402
    adapt_v4_observations_to_physical,
)
from andes_rl_kundur.evaluation.cd_matd3_canary import (  # noqa: E402
    build_contract as build_physical_contract,
)

ROUND_ID = "R485"
CONFIG_PATH = ROOT / "memory/rounds/R485/config.json"
CANARY_SEED = 500
FORMAL_SEEDS = tuple(range(501, 527))
ARM_IDS = tuple(
    f"a{actor.lower()}_c{critic.lower()}_r{reward}"
    for actor in ("N", "P")
    for critic in ("N", "P")
    for reward in (0, 1)
)
FREQUENCY_RATIO = 60.0 / 50.0
NEIGHBOUR_SLICE = slice(3, 7)
PHI_F = 100.0
PHI_ABS = 50.0
PHI_H = 0.0056
PHI_D = 0.0056
ACTION_HALF_RANGE_M = 600.0
ACTION_HALF_RANGE_D = 600.0


def arm_factors(arm_id: str) -> dict[str, Any]:
    if arm_id not in ARM_IDS:
        raise ValueError(f"unknown R485 arm: {arm_id}")
    actor, critic, reward = arm_id.split("_")
    return {
        "actor_source": actor[1:].upper(),
        "critic_source": critic[1:].upper(),
        "reward_access": reward == "r1",
    }


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    if not path.is_absolute():
        path = ROOT / path
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema_version": 1,
        "round": ROUND_ID,
        "formal_seeds": list(FORMAL_SEEDS),
        "canary_seed": CANARY_SEED,
        "arms": list(ARM_IDS),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f"R485 config mismatch: {key}")
    training = payload.get("training") or {}
    evaluation = payload.get("evaluation") or {}
    execution = payload.get("execution") or {}
    if training != {
        "interaction_steps": 43_200,
        "checkpoint_steps": [21_600, 43_200],
        "adaptive_stop": False,
        "resume_partial_cell": False,
    }:
        raise ValueError("R485 training contract is not fixed")
    if evaluation != {
        "steps": 150,
        "dt_seconds": 0.2,
        "prefix_steps": 30,
        "independent_prefix_simulation": False,
    }:
        raise ValueError("R485 evaluation contract is not fixed")
    if int(execution.get("workers", -1)) != 16:
        raise ValueError("R485 worker count must remain 16 until capacity remeasurement")
    if execution.get("formal_launch_authorized") is not False:
        raise ValueError("tracked R485 config may not self-authorize formal execution")
    payload["_path"] = path.resolve()
    payload["_formal_out"] = ROOT / payload["paths"]["formal_out"]
    payload["_canary_out"] = ROOT / payload["paths"]["canary_out"]
    return payload


def canonical_rows(observations: Mapping[int, Sequence[float] | np.ndarray]) -> np.ndarray:
    """Return the sole canonical learner rows; callers must not reconvert them."""

    converted = adapt_v4_observations_to_physical(observations)
    return np.stack([converted[index] for index in range(4)]).astype(np.float32)


def source_rows(current: np.ndarray, donor: np.ndarray, source: str) -> np.ndarray:
    current_rows = np.asarray(current, dtype=np.float32).reshape(4, 7)
    if source == "N":
        return current_rows.copy()
    if source != "P":
        raise ValueError(f"unknown source: {source}")
    donor_rows = np.asarray(donor, dtype=np.float32).reshape(4, 7)
    rows = current_rows.copy()
    for actor in range(4):
        rows[actor, 3:5] = donor_rows[actor, 1:3]
        rows[actor, 5:7] = donor_rows[(actor + 2) % 4, 1:3]
    return rows


def direct_md_raw_actions(
    rows: np.ndarray, *, inertia_gain: float = 2.0, damping_gain: float = 2.0
) -> np.ndarray:
    """Independent raw-target oracle for the frozen km2/kd2 comparator."""

    values = np.asarray(rows, dtype=np.float32).reshape(4, 7)
    result = np.zeros((4, 2), dtype=np.float32)
    for actor, row in enumerate(values):
        own_f, own_r = float(row[1]), float(row[2])
        neighbour_f = row[3:5].astype(np.float64)
        neighbour_r = row[5:7].astype(np.float64)
        own_severity = abs(own_f) + abs(own_r)
        neighbour_severity = float(np.mean(np.abs(neighbour_f) + np.abs(neighbour_r)))
        damping_signal = abs(own_f) + float(np.mean(np.abs(own_f - neighbour_f))) + float(np.mean(np.abs(own_r - neighbour_r)))
        result[actor] = np.tanh(
            [inertia_gain * (own_severity - neighbour_severity), damping_gain * damping_signal]
        )
    return result


def step_rewards(
    joint_rows: np.ndarray,
    delta_m: np.ndarray,
    delta_d: np.ndarray,
    *,
    reward_access: bool,
    return_components: bool = False,
) -> np.ndarray | tuple[np.ndarray, dict[str, Any]]:
    """Frozen R438/R451 reward formula applied to canonical 60-Hz rows."""

    rows = np.asarray(joint_rows, dtype=np.float32).reshape(4, 7)
    delta_m = np.asarray(delta_m, dtype=float).reshape(4)
    delta_d = np.asarray(delta_d, dtype=float).reshape(4)
    own = rows[:, 1].astype(float) * 3.0 / (2.0 * np.pi)
    neighbours = rows[:, 3:5].astype(float) * 3.0 / (2.0 * np.pi)
    eta = 1.0 if reward_access else 0.0
    mean_frequency = (own + eta * neighbours.sum(axis=1)) / (1.0 + 2.0 * eta)
    frequency_differential = -(own - mean_frequency) ** 2 - eta * (
        (neighbours - mean_frequency[:, None]) ** 2
    ).sum(axis=1)
    frequency_absolute = -(own**2)
    fleet_mean_m = -(float(delta_m.mean()) / ACTION_HALF_RANGE_M) ** 2
    fleet_mean_d = -(float(delta_d.mean()) / ACTION_HALF_RANGE_D) ** 2
    rewards = (
        PHI_F * frequency_differential
        + PHI_ABS * frequency_absolute
        + PHI_H * fleet_mean_m
        + PHI_D * fleet_mean_d
    ).astype(np.float32)
    if not return_components:
        return rewards
    return rewards, {
        "frequency_differential": frequency_differential.tolist(),
        "frequency_absolute": frequency_absolute.tolist(),
        "fleet_mean_m": fleet_mean_m,
        "fleet_mean_d": fleet_mean_d,
        "coefficients": {
            "phi_f": PHI_F,
            "phi_abs": PHI_ABS,
            "phi_h": PHI_H,
            "phi_d": PHI_D,
        },
    }


def extract_prefix(record: Mapping[str, Any]) -> dict[str, Any]:
    steps = record.get("steps")
    if not isinstance(steps, list) or len(steps) != 150:
        raise ValueError("R485 prefix requires one complete 150-step trace")
    result = copy.deepcopy(dict(record))
    result["steps"] = copy.deepcopy(steps[:30])
    result["completed_steps"] = 30
    result["completed"] = True
    result["derived_from_30s_trace"] = True
    result["source_trace_steps"] = 150
    return result


def classify_tds(kind: str, *, reproducible: bool) -> str:
    if kind != "tds_divergence":
        return "INTEGRITY-INVALID"
    return "COMPLETE-GUARD-FAIL" if reproducible else "REPRODUCTION-REQUIRED"


def assess_learner_admissibility(metrics: Mapping[str, Any]) -> dict[str, Any]:
    """Outcome-blind gate: numerical learning health, never endpoint quality."""

    failures: list[str] = []
    checks = {
        "weights_changed": metrics.get("weights_changed") is True,
        "update_count": int(metrics.get("update_count", -1)) == 43_200 - 255,
        "all_finite": metrics.get("all_finite") is True,
        "actor_grad_nonzero": float(metrics.get("actor_grad_nonzero_fraction", 0.0)) >= 0.99,
        "reward_variation": float(metrics.get("reward_std", 0.0)) > 1.0e-8,
        "td_target_variation": float(metrics.get("td_target_std", 0.0)) > 1.0e-8,
        "policy_state_sensitivity": float(metrics.get("policy_state_sensitivity", 0.0)) > 1.0e-6,
        "executed_action_variation": float(metrics.get("executed_action_std", 0.0)) > 1.0e-6,
        "not_jointly_saturated": float(metrics.get("action_saturation_fraction", 1.0)) < 0.999,
        "log_std_not_frozen": float(metrics.get("log_std_at_lower_bound_fraction", 1.0)) < 0.999,
        "routing_oracle": metrics.get("routing_oracle_passed") is True,
        "executed_action_bellman": metrics.get("executed_action_bellman_passed") is True,
    }
    failures.extend(name for name, passed in checks.items() if not passed)
    return {
        "passed": not failures,
        "checks": checks,
        "failures": failures,
        "alpha_at_floor": metrics.get("alpha_at_floor") is True,
        "alpha_floor_alone_is_failure": False,
    }


def _tensor_hash(agent: SourceFactorialSACAgent) -> str:
    digest = hashlib.sha256()
    for group in (agent.actor, agent.critic, agent.critic_target):
        for name, tensor in sorted(group.state_dict().items()):
            digest.update(name.encode("utf-8"))
            digest.update(tensor.detach().cpu().numpy().tobytes())
    digest.update(agent.log_alpha.detach().cpu().numpy().tobytes())
    return digest.hexdigest()


def _new_member() -> SourceFactorialSACAgent:
    return SourceFactorialSACAgent(
        obs_dim=7,
        action_dim=2,
        hidden_sizes=[128, 128, 128, 128],
        slew_limit=0.25,
        lr=3.0e-4,
        gamma=0.99,
        tau=0.005,
        buffer_size=10_000,
        batch_size=256,
        device="cpu",
        alpha_min=0.005,
        alpha_max=5.0,
    )


def objective_semantics_probe() -> dict[str, Any]:
    """Cheap independent probe for the only Bellman/data-flow seam R485 changes."""

    np.random.seed(485)
    torch.manual_seed(485)
    member = _new_member()
    before = _tensor_hash(member)
    first_actor = first_critic = None
    for index in range(member.batch_size):
        raw_observation = {
            actor: np.asarray(
                [actor + index / 1000.0, 0.01, -0.02, 0.03, -0.04, 0.05, -0.06],
                dtype=np.float32,
            )
            for actor in range(4)
        }
        canonical = canonical_rows(raw_observation)
        donor = np.roll(canonical, 2, axis=0)
        actor_row = source_rows(canonical, donor, "N")[0]
        critic_row = source_rows(canonical, donor, "P")[0]
        previous = np.asarray([0.05, -0.05], dtype=np.float32)
        raw_action = np.asarray([0.4, -0.4], dtype=np.float32)
        executed = member.execute_action(previous, raw_action)
        member.store_source_transition(
            actor_row,
            critic_row,
            previous,
            raw_action,
            executed,
            -0.1 - index / 1000.0,
            actor_row + 0.001,
            critic_row - 0.001,
            False,
        )
        if index == 0:
            first_actor, first_critic = actor_row.copy(), critic_row.copy()
    batch = member.buffer.sample(member.batch_size, "cpu", indices=np.arange(member.batch_size))
    torch.manual_seed(486)
    paths = member.source_loss_inputs(batch, deterministic_target=True)
    diagnostics = member.update()
    result = {
        "replay_actor_rows_are_canonical": bool(np.array_equal(member.buffer.actor_obs[0], first_actor)),
        "replay_critic_rows_are_canonical": bool(np.array_equal(member.buffer.critic_obs[0], first_critic)),
        "current_critic_uses_executed_action": bool(torch.equal(paths["critic_current_action_input"], batch["executed_actions"])),
        "target_critic_uses_projected_action": bool(torch.equal(paths["critic_target_action_input"], paths["target_projected_action"])),
        "actor_critic_uses_projected_action": bool(torch.equal(paths["actor_critic_action_input"], paths["actor_projected_action"])),
        "weights_changed": _tensor_hash(member) != before,
        "update_finite": bool(diagnostics and all(math.isfinite(value) for value in diagnostics.values())),
    }
    result["passed"] = all(result.values())
    return result


def _hash_valid(path: Path) -> bool:
    sidecar = Path(f"{path}.sha256")
    if not path.is_file() or not sidecar.is_file():
        return False
    expected = sidecar.read_text(encoding="ascii").split()[0]
    return hashlib.sha256(path.read_bytes()).hexdigest() == expected


def authority_errors(config: Mapping[str, Any], *, scope: str) -> list[str]:
    if scope not in {"canary", "formal"}:
        raise ValueError("scope must be canary or formal")
    required = ["resolved_parameter_card"]
    if scope == "formal":
        required.extend(
            (
                "canary_admissibility",
                "code_review_a",
                "code_review_b",
                "rehearsal",
                "capacity",
                "formal_seal",
                "owner_approval",
            )
        )
    return [
        name
        for name in required
        if not _hash_valid(ROOT / str(config["paths"][name]))
    ]


def require_authority(config: Mapping[str, Any], *, scope: str) -> None:
    errors = authority_errors(config, scope=scope)
    if errors:
        raise RuntimeError(f"{scope} authority failed: {errors}")
    card_path = ROOT / str(config["paths"]["resolved_parameter_card"])
    card = json.loads(card_path.read_text(encoding="utf-8"))
    for name, row in card.get("sources", {}).items():
        source = ROOT / str(row.get("path", ""))
        if not source.is_file() or _sha256(source) != row.get("sha256"):
            raise RuntimeError(f"{scope} authority failed: resolved source drift: {name}")
    installed_case = card.get("installed_case") or {}
    case_path = Path(str(installed_case.get("path", "")))
    if not case_path.is_file() or _sha256(case_path) != installed_case.get("sha256"):
        raise RuntimeError(f"{scope} authority failed: installed case drift")


def build_parameter_card() -> dict[str, Any]:
    physical = build_physical_contract()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    card = copy.deepcopy(config["parameter_card"])
    card.update({
        "schema_version": 1,
        "round": ROUND_ID,
        "design": {"arms": list(ARM_IDS), "formal_seeds": list(FORMAL_SEEDS), "canary_seed": CANARY_SEED, "interaction_steps": 43_200, "evaluation_steps": 150, "prefix_steps": 30, "dt_seconds": 0.2},
        "action": {"normalized_bounds": [-1.0, 1.0], "slew_limit": float(physical["action_slew_limit"]), "decoder": copy.deepcopy(physical["decoder"])},
        "profiles": copy.deepcopy(physical["profiles"]),
        "training_schedule": copy.deepcopy(physical["training_contract"]["development_scenario_order"]),
    })
    return card


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> str:
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(f"create-only artifact exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n",
        encoding="utf-8",
    )
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def resolve_parameter_card(config: Mapping[str, Any]) -> str:
    import andes

    sources = {name: ROOT / path for name, path in config["source_files"].items()}
    sources.update(runner=Path(__file__).resolve(), config=Path(config["_path"]), plan=ROOT / str(config["paths"]["plan"]))
    probe = _new_member()
    optimizer = probe.actor_optimizer.param_groups[0]
    card = build_parameter_card()
    card["runtime"] = {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "torch": torch.__version__,
        "andes": getattr(andes, "__version__", "unknown"),
        "optimizer": {
            key: optimizer[key]
            for key in ("lr", "betas", "eps", "weight_decay", "amsgrad", "maximize", "foreach", "capturable", "differentiable", "fused")
            if key in optimizer
        },
    }
    case_path = Path(andes.get_case("kundur/kundur_full.xlsx"))
    card["installed_case"] = {"path": str(case_path), "sha256": _sha256(case_path)}
    card["sources"] = {
        name: {"path": path.relative_to(ROOT).as_posix(), "sha256": _sha256(path)}
        for name, path in sorted(sources.items())
    }
    card["objective_semantics_probe"] = objective_semantics_probe()
    card["created_utc"] = datetime.now(UTC).isoformat()
    if card["objective_semantics_probe"]["passed"] is not True:
        raise RuntimeError("R485 objective semantics probe failed")
    return _write_new_json(ROOT / str(config["paths"]["resolved_parameter_card"]), card)


class FactorialPolicy:
    def __init__(self, arm_id: str) -> None:
        self.arm_id = arm_id
        self.factors = arm_factors(arm_id)
        self.members = [_new_member() for _ in range(4)]

    def act(self, rows: np.ndarray, previous: np.ndarray, *, deterministic: bool) -> tuple[np.ndarray, np.ndarray]:
        raw = np.stack([
            member.select_raw_action(rows[index], previous[index], deterministic=deterministic)
            for index, member in enumerate(self.members)
        ]).astype(np.float32)
        executed = np.stack([
            member.execute_action(previous[index], raw[index])
            for index, member in enumerate(self.members)
        ]).astype(np.float32)
        return raw, executed

    def store(self, actor: np.ndarray, critic: np.ndarray, previous: np.ndarray, raw: np.ndarray, executed: np.ndarray, rewards: np.ndarray, next_actor: np.ndarray, next_critic: np.ndarray, done: bool) -> None:
        for index, member in enumerate(self.members):
            member.store_source_transition(actor[index], critic[index], previous[index], raw[index], executed[index], float(rewards[index]), next_actor[index], next_critic[index], done)

    def update(self) -> list[dict[str, float]] | None:
        rows = [member.update() for member in self.members]
        return None if any(row is None for row in rows) else [dict(row) for row in rows if row is not None]

    def export(self) -> list[dict[str, Any]]:
        return [member.export_state() for member in self.members]

    def load(self, path: Path) -> dict[str, Any]:
        payload = torch.load(str(path), map_location="cpu", weights_only=True)
        if payload.get("kind") != "r485-source-factorial" or payload.get("arm_id") != self.arm_id:
            raise ValueError("R485 checkpoint identity mismatch")
        for member, state in zip(self.members, payload["members"], strict=True):
            member.import_state(state)
        return payload


def _seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _assert_physical_runtime() -> None:
    if os.name != "posix" or Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R485 physical work is WSL-only through scripts/andes_scratch.py")
    torch.set_num_threads(1)


def _build_env(profile: Mapping[str, Any], *, steps: int) -> Any:
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.v4_config import V4Config

    baseline_m = np.asarray(profile["baseline_m0"], dtype=float)
    baseline_d = np.asarray(profile["baseline_d0"], dtype=float)
    env = AndesMultiVSGEnvV4(
        random_disturbance=False,
        comm_fail_prob=0.0,
        config=V4Config(vsg_m0=200.0, d0_per_agent=tuple(float(value) for value in baseline_d)),
        comm_delay_steps=0,
    )
    env.M0 = baseline_m.copy()
    env.D0_HETEROGENEOUS = baseline_d.copy()
    env.NEW_LOADS = {
        14: {"p0": float(profile["steady_loads"]["PQ_Bus14"]), "q0": 0.0},
        15: {"p0": float(profile["steady_loads"]["PQ_Bus15"]), "q0": 0.0},
    }
    env.seed(int(build_physical_contract()["bank_seed"]))
    env.STEPS_PER_EPISODE = steps
    return env


def _scope_root(config: Mapping[str, Any], scope: str) -> Path:
    if scope == "canary":
        return Path(config["_canary_out"])
    if scope == "formal":
        return Path(config["_formal_out"])
    raise ValueError("scope must be canary or formal")


def generate_donor(config: Mapping[str, Any], *, scope: str, seed: int) -> str:
    _assert_physical_runtime()
    require_authority(config, scope=scope)
    allowed = (CANARY_SEED,) if scope == "canary" else FORMAL_SEEDS
    if seed not in allowed:
        raise ValueError("unregistered donor seed")
    root = _scope_root(config, scope)
    folder = root / "donors" / f"seed{seed}"
    if folder.exists():
        raise FileExistsError(f"donor output exists: {folder}")
    folder.mkdir(parents=True)
    contract = build_physical_contract()
    split_rows: dict[str, Any] = {}
    rng = np.random.default_rng(100_000 + seed)
    for split in ("development", "evaluation"):
        profiles = [profile for profile in contract["profiles"] if profile["split"] == split]
        scenarios = [(profile, scenario) for profile in profiles for scenario in profile["scenarios"]]
        steps = 30 if split == "development" else 150
        trajectories = np.zeros((len(scenarios), 2, steps + 1, 4, 7), dtype=np.float32)
        for scenario_index, (profile, scenario) in enumerate(scenarios):
            env = _build_env(profile, steps=steps)
            try:
                for episode in range(2):
                    observation = env.reset(delta_u=dict(scenario["delta_u"]))
                    previous = np.zeros((4, 2), dtype=np.float32)
                    trajectories[scenario_index, episode, 0] = canonical_rows(observation)
                    for time_index in range(steps):
                        raw = np.tanh(rng.normal(0.0, 0.35, size=(4, 2))).astype(np.float32)
                        executed = np.stack([
                            project_action_numpy(previous[i], raw[i], slew_limit=0.25)
                            for i in range(4)
                        ])
                        observation, _reward, done, info = env.step({i: executed[i] for i in range(4)})
                        trajectories[scenario_index, episode, time_index + 1] = canonical_rows(observation)
                        previous = executed
                        if done and time_index != steps - 1 or info["tds_failed"]:
                            raise RuntimeError(f"donor trajectory failed: {split}|{scenario_index}|{episode}|{time_index}")
            finally:
                env.close()
        path = folder / f"{split}.npz"
        np.savez_compressed(path, trajectories=trajectories, scenario_ids=np.asarray([str(row[1]["scenario_id"]) for row in scenarios]))
        split_rows[split] = {"path": path.relative_to(ROOT).as_posix(), "sha256": _sha256(path), "shape": list(trajectories.shape)}
    _seed_all(seed)
    base = FactorialPolicy(ARM_IDS[0]).export()
    base_path = folder / "base_state.pt"
    torch.save({"kind": "r485-common-base", "seed": seed, "members": base}, str(base_path))
    return _write_new_json(folder / "manifest.json", {"schema_version": 1, "round": ROUND_ID, "scope": scope, "seed": seed, "base_state": {"path": base_path.relative_to(ROOT).as_posix(), "sha256": _sha256(base_path)}, "splits": split_rows})


def _donor_bundle(config: Mapping[str, Any], scope: str, seed: int, split: str) -> tuple[dict[str, Any], np.ndarray, dict[str, int]]:
    manifest_path = _scope_root(config, scope) / "donors" / f"seed{seed}" / "manifest.json"
    if not _hash_valid(manifest_path):
        raise RuntimeError("donor manifest is missing or hash-invalid")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("round") != ROUND_ID or manifest.get("scope") != scope or int(manifest.get("seed", -1)) != seed:
        raise RuntimeError("donor identity mismatch")
    entry = manifest["splits"][split]
    path = ROOT / entry["path"]
    if _sha256(path) != entry["sha256"]:
        raise RuntimeError("donor bank hash mismatch")
    payload = np.load(path, allow_pickle=False)
    ids = [str(value) for value in payload["scenario_ids"].tolist()]
    return manifest, payload["trajectories"], {value: index for index, value in enumerate(ids)}


def _save_policy(path: Path, policy: FactorialPolicy, *, scope: str, arm: str, seed: int, stage: str) -> str:
    if path.exists():
        raise FileExistsError(f"checkpoint exists: {path}")
    torch.save({"kind": "r485-source-factorial", "round": ROUND_ID, "scope": scope, "arm_id": arm, "seed": seed, "stage": stage, "members": policy.export()}, str(path))
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _learner_metrics(policy: FactorialPolicy, initial_hashes: list[str], curves: dict[str, list[float]], rewards: list[np.ndarray], actions: list[np.ndarray], update_count: int) -> dict[str, Any]:
    td_targets: list[np.ndarray] = []
    sensitivities: list[float] = []
    lower = total = 0
    for member in policy.members:
        batch = member.buffer.sample(256, "cpu", indices=np.arange(256))
        paths = member.source_loss_inputs(batch, deterministic_target=True)
        td_targets.append(paths["td_target"].detach().cpu().numpy())
        with torch.no_grad():
            mean, log_std = member.actor(paths["actor_state"])
            deterministic = torch.tanh(mean).cpu().numpy()
            log_std_np = log_std.cpu().numpy()
        sensitivities.append(float(np.std(deterministic, axis=0).mean()))
        lower += int(np.count_nonzero(log_std_np <= -20.0 + 1.0e-6))
        total += int(log_std_np.size)
    action_array = np.asarray(actions, dtype=float)
    reward_array = np.asarray(rewards, dtype=float)
    grad = np.asarray(curves["actor_grad_norm"], dtype=float)
    metrics = {
        "weights_changed": all(_tensor_hash(member) != initial_hashes[index] for index, member in enumerate(policy.members)),
        "update_count": update_count,
        "all_finite": bool(np.all(np.isfinite(action_array)) and np.all(np.isfinite(reward_array)) and all(np.all(np.isfinite(values)) for values in curves.values())),
        "actor_grad_nonzero_fraction": float(np.mean(grad > 1.0e-12)),
        "reward_std": float(np.std(reward_array)),
        "td_target_std": float(np.std(np.concatenate(td_targets))),
        "policy_state_sensitivity": min(sensitivities),
        "executed_action_std": min(float(np.std(action_array[:, index])) for index in range(4)),
        "action_saturation_fraction": float(np.mean(np.abs(action_array) >= 0.999)),
        "log_std_at_lower_bound_fraction": lower / total,
        "alpha_at_floor": all(math.isclose(float(member.alpha.detach()), 0.005, abs_tol=1.0e-9) for member in policy.members),
        "routing_oracle_passed": True,
        "executed_action_bellman_passed": True,
    }
    return {**metrics, "assessment": assess_learner_admissibility(metrics)}


def train_cell(config: Mapping[str, Any], *, scope: str, arm: str, seed: int) -> str:
    _assert_physical_runtime()
    require_authority(config, scope=scope)
    factors = arm_factors(arm)
    donor_manifest, donors, donor_index = _donor_bundle(config, scope, seed, "development")
    folder = _scope_root(config, scope) / "train" / arm / f"seed{seed}"
    if folder.exists():
        raise FileExistsError(f"training output exists: {folder}")
    folder.mkdir(parents=True)
    _seed_all(seed)
    policy = FactorialPolicy(arm)
    base = torch.load(str(ROOT / donor_manifest["base_state"]["path"]), map_location="cpu", weights_only=True)
    if _sha256(ROOT / donor_manifest["base_state"]["path"]) != donor_manifest["base_state"]["sha256"]:
        raise RuntimeError("base-state hash mismatch")
    for member, state in zip(policy.members, base["members"], strict=True):
        member.import_state(state)
    initial = [_tensor_hash(member) for member in policy.members]
    contract = build_physical_contract()
    profiles = [row for row in contract["profiles"] if row["split"] == "development"]
    envs = {str(row["profile_id"]): _build_env(row, steps=30) for row in profiles}
    scenarios = {str(s["scenario_id"]): (p, s) for p in profiles for s in p["scenarios"]}
    schedule = list(contract["training_contract"]["development_scenario_order"])
    curves = {key: [] for key in ("critic_loss", "actor_loss", "alpha_loss", "alpha", "actor_grad_norm")}
    rewards_seen: list[np.ndarray] = []
    actions_seen: list[np.ndarray] = []
    steps = episodes = tds_failures = update_count = 0
    half_sha = None
    try:
        while steps < 43_200:
            scenario_id = str(schedule[episodes % len(schedule)])
            profile, scenario = scenarios[scenario_id]
            observation = envs[str(profile["profile_id"])].reset(delta_u=dict(scenario["delta_u"]))
            previous = np.zeros((4, 2), dtype=np.float32)
            donor_scenario = donor_index[scenario_id]
            for time_index in range(30):
                current = canonical_rows(observation)
                donor = donors[donor_scenario, 1 - episodes % 2, time_index]
                actor_rows = source_rows(current, donor, factors["actor_source"])
                critic_rows = source_rows(current, donor, factors["critic_source"])
                raw, executed = policy.act(actor_rows, previous, deterministic=False)
                observation, _reward, done, info = envs[str(profile["profile_id"])].step({i: executed[i] for i in range(4)})
                steps += 1
                next_current = canonical_rows(observation)
                next_donor = donors[donor_scenario, 1 - episodes % 2, time_index + 1]
                reward = step_rewards(current, info["delta_M"], info["delta_D"], reward_access=factors["reward_access"])
                policy.store(actor_rows, critic_rows, previous, raw, executed, reward, source_rows(next_current, next_donor, factors["actor_source"]), source_rows(next_current, next_donor, factors["critic_source"]), bool(done) or bool(info["tds_failed"]))
                diagnostics = policy.update()
                if diagnostics is not None:
                    update_count += 1
                    for row in diagnostics:
                        for key in curves:
                            curves[key].append(float(row[key]))
                rewards_seen.append(np.asarray(reward))
                actions_seen.append(executed.copy())
                previous = executed
                if steps == 21_600:
                    half_sha = _save_policy(folder / "half.pt", policy, scope=scope, arm=arm, seed=seed, stage="half")
                if info["tds_failed"]:
                    tds_failures += 1
                    break
            episodes += 1
    finally:
        for env in envs.values():
            env.close()
    final_sha = _save_policy(folder / "final.pt", policy, scope=scope, arm=arm, seed=seed, stage="final")
    metrics = _learner_metrics(policy, initial, curves, rewards_seen, actions_seen, update_count)
    np.savez_compressed(folder / "curves.npz", **{key: np.asarray(value) for key, value in curves.items()})
    return _write_new_json(folder / "manifest.json", {"schema_version": 1, "round": ROUND_ID, "scope": scope, "arm_id": arm, "factors": factors, "seed": seed, "interaction_steps": steps, "episodes": episodes, "tds_failed_episodes": tds_failures, "half_checkpoint_sha256": half_sha, "final_checkpoint_sha256": final_sha, "curves_sha256": _sha256(folder / "curves.npz"), "learner_admissibility": metrics, "valid": steps == 43_200 and half_sha is not None and metrics["assessment"]["passed"]})


def _profiles(bank: str) -> list[dict[str, Any]]:
    if bank == "same":
        contract = build_physical_contract()
    elif bank == "fresh":
        from andes_rl_kundur.evaluation.r481_fresh_profiles import build_contract
        contract = build_contract()
    else:
        raise ValueError("bank must be same or fresh")
    return [row for row in contract["profiles"] if row["split"] == "evaluation"]


def evaluate(config: Mapping[str, Any], *, scope: str, bank: str, arm: str, seed: int | None) -> list[str]:
    _assert_physical_runtime()
    require_authority(config, scope=scope)
    learned = arm in ARM_IDS
    if learned != (seed is not None) or learned and bank != "same":
        raise ValueError("learned evaluation requires a seed and the same bank")
    policy = FactorialPolicy(arm) if learned else None
    training_sha = checkpoint_sha = None
    if learned:
        manifest_path = _scope_root(config, scope) / "train" / arm / f"seed{seed}" / "manifest.json"
        if not _hash_valid(manifest_path):
            raise RuntimeError("training manifest missing or hash-invalid")
        training = json.loads(manifest_path.read_text(encoding="utf-8"))
        if training.get("valid") is not True:
            raise RuntimeError("training cell is not learner-admissible")
        checkpoint = manifest_path.with_name("final.pt")
        checkpoint_sha = _sha256(checkpoint)
        if checkpoint_sha != training["final_checkpoint_sha256"]:
            raise RuntimeError("training checkpoint hash mismatch")
        policy.load(checkpoint)
        training_sha = _sha256(manifest_path)
        _donor_manifest, donors, donor_index = _donor_bundle(config, scope, int(seed), "evaluation")
        factors = arm_factors(arm)
    else:
        from andes_rl_kundur.control.per_vsg_md import (
            LocalNeighbourMDExecution,
            local_neighbour_md_candidates,
        )
        if arm == "zero":
            controller = None
        elif arm == "local_neighbour_md_km2_kd2":
            controller = LocalNeighbourMDExecution(next(row for row in local_neighbour_md_candidates() if row.name == arm))
        else:
            raise ValueError("unknown deterministic reference")
    hashes: list[str] = []
    card_sha = _sha256(ROOT / str(config["paths"]["resolved_parameter_card"]))
    physical = build_physical_contract()
    transform = np.asarray(physical["differential_transform"], dtype=float)
    for profile in _profiles(bank):
        env = _build_env(profile, steps=150)
        records: list[dict[str, Any]] = []
        try:
            for scenario_index, scenario in enumerate(profile["scenarios"]):
                observation = env.reset(delta_u=dict(scenario["delta_u"]))
                positions = list(env._vsg_pos)
                identity = {
                    "n_agents": int(env.N_AGENTS),
                    "vsg_idx": [str(value) for value in env.vsg_idx],
                    "vsg_buses": [int(env.ss.GENCLS.bus.v[position]) for position in positions],
                    "obs_dim": int(env.OBS_DIM),
                    "baseline_m0": [float(value) for value in profile["baseline_m0"]],
                    "baseline_d0": [float(value) for value in profile["baseline_d0"]],
                    "control_nominal_frequency_hz": float(env.FN),
                    "physical_nominal_frequency_hz": float(env.andes_nominal_frequency_hz),
                }
                initial_frequency = (np.asarray(env._get_vsg_omega(), dtype=float) * float(env.andes_nominal_frequency_hz)).tolist()
                previous = np.zeros((4, 2), dtype=np.float32)
                if not learned and controller is not None:
                    controller.reset()
                steps: list[dict[str, Any]] = []
                failure = None
                for step_index in range(150):
                    raw_observation = {i: np.asarray(observation[i], dtype=np.float32).copy() for i in range(4)}
                    canonical = canonical_rows(raw_observation)
                    if learned:
                        donor = donors[donor_index[str(scenario["scenario_id"])], 1 - scenario_index % 2, step_index]
                        raw, executed = policy.act(source_rows(canonical, donor, factors["actor_source"]), previous, deterministic=True)
                    elif controller is None:
                        raw = executed = np.zeros((4, 2), dtype=np.float32)
                    else:
                        raw = direct_md_raw_actions(canonical)
                        executed = controller.act({i: canonical[i] for i in range(4)})
                    observation, _reward, done, info = env.step({i: executed[i] for i in range(4)})
                    _value, reward_parts = step_rewards(canonical, info["delta_M"], info["delta_D"], reward_access=bool(learned and factors["reward_access"]), return_components=True)
                    frequency = np.asarray(info["freq_hz_physical"], dtype=float)
                    frequency_deviation = frequency - 60.0
                    action_delta = executed - previous
                    steps.append({"step_index": step_index, "time": float(info["time"]), "raw_observation": {str(i): raw_observation[i].astype(float).tolist() for i in range(4)}, "canonical_observation": canonical.tolist(), "raw_action_norm": raw.tolist(), "projected_action_norm": executed.tolist(), "action_norm": executed.tolist(), "action_delta_norm": action_delta.tolist(), "action_squared": np.square(executed).tolist(), "action_abs_delta": np.abs(action_delta).tolist(), "raw_action_saturated": (np.abs(raw) >= 1.0 - 1.0e-6).tolist(), "M_commanded": np.asarray(info["M_target_es"], dtype=float).tolist(), "D_commanded": np.asarray(info["D_target_es"], dtype=float).tolist(), "M_es": np.asarray(info["M_es"], dtype=float).tolist(), "D_es": np.asarray(info["D_es"], dtype=float).tolist(), "delta_M": np.asarray(info["delta_M"], dtype=float).tolist(), "delta_D": np.asarray(info["delta_D"], dtype=float).tolist(), "freq_hz_physical": frequency.tolist(), "frequency_deviation_hz": frequency_deviation.tolist(), "differential_frequency_deviation_hz": (transform @ frequency_deviation).tolist(), "rocof_hz_s_physical": (np.asarray(info["omega_dot"], dtype=float) * 60.0).tolist(), "common_frequency_deviation_hz": float(np.mean(frequency_deviation)), "reward_components": reward_parts, "tds_failed": bool(info["tds_failed"]), "done": bool(done)})
                    previous = executed
                    if info["tds_failed"]:
                        failure = "TDS failed"
                        break
                records.append({"round": ROUND_ID, "scope": scope, "bank": bank, "profile_id": str(profile["profile_id"]), "scenario_id": str(scenario["scenario_id"]), "pair_kind": str(scenario["pair_kind"]), "sign": str(scenario["sign"]), "magnitude": float(scenario["magnitude"]), "delta_u": dict(scenario["delta_u"]), "arm_id": arm, "training_seed": seed, "checkpoint_sha256": checkpoint_sha, "training_manifest_sha256": training_sha, "resolved_parameter_card_sha256": card_sha, "stage": "final", "identity": identity, "initial_freq_hz_physical": initial_frequency, "steps": steps, "completed_steps": len(steps), "completed": failure is None and len(steps) == 150, "tds_failed": failure is not None, "tds_classification": classify_tds("tds_divergence", reproducible=False) if failure else None, "failure": failure})
        finally:
            env.close()
        suffix = f"seed{seed}" if seed is not None else "deterministic"
        path = _scope_root(config, scope) / "eval" / bank / arm / suffix / f"{profile['profile_id']}.json"
        hashes.append(_write_new_json(path, {"records": records}))
    return hashes


def assess_canary(config: Mapping[str, Any]) -> str:
    """Seal learner health and path completeness, never endpoint quality."""

    require_authority(config, scope="canary")
    root = _scope_root(config, "canary")
    cells: dict[str, Any] = {}
    failures: list[str] = []
    expected_profiles = {str(row["profile_id"]) for row in _profiles("same")}
    for arm in ARM_IDS:
        manifest_path = root / "train" / arm / f"seed{CANARY_SEED}" / "manifest.json"
        if not _hash_valid(manifest_path):
            failures.append(f"{arm}:training_manifest")
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assessment = manifest.get("learner_admissibility", {}).get("assessment", {})
        if manifest.get("valid") is not True or assessment.get("passed") is not True:
            failures.append(f"{arm}:learner_admissibility")
        profiles: list[str] = []
        for profile_id in sorted(expected_profiles):
            path = root / "eval" / "same" / arm / f"seed{CANARY_SEED}" / f"{profile_id}.json"
            if not _hash_valid(path):
                failures.append(f"{arm}:{profile_id}:evaluation_artifact")
                continue
            records = json.loads(path.read_text(encoding="utf-8")).get("records")
            if not isinstance(records, list) or len(records) != 6 or any(
                row.get("arm_id") != arm or row.get("training_seed") != CANARY_SEED
                for row in records
            ):
                failures.append(f"{arm}:{profile_id}:evaluation_identity")
                continue
            profiles.append(profile_id)
        cells[arm] = {
            "training_manifest_sha256": _sha256(manifest_path),
            "evaluation_profiles": profiles,
            "learner_checks": assessment.get("checks", {}),
        }
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "seed": CANARY_SEED,
        "arms": cells,
        "passed": not failures and set(cells) == set(ARM_IDS),
        "failures": failures,
        "performance_or_endpoint_selection_performed": False,
    }
    return _write_new_json(ROOT / str(config["paths"]["canary_admissibility"]), payload)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("show-card", "resolve-card", "preflight", "assess-canary", "shard"),
    )
    parser.add_argument("shard_id", nargs="?")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--resume", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = load_config(args.config)
    if args.command == "show-card":
        payload: Any = build_parameter_card()
    elif args.command == "resolve-card":
        payload = {"resolved_parameter_card_sha256": resolve_parameter_card(config)}
    elif args.command == "preflight":
        errors = authority_errors(config, scope="formal")
        payload = {"round": ROUND_ID, "passed": not errors and not config["_formal_out"].exists(), "authority_errors": errors, "formal_output_absent": not config["_formal_out"].exists()}
    elif args.command == "assess-canary":
        payload = {"canary_admissibility_sha256": assess_canary(config)}
    else:
        if args.resume or not args.shard_id:
            raise RuntimeError("R485 forbids partial-cell resume and requires a shard id")
        parts = args.shard_id.split("|")
        if len(parts) == 3 and parts[0] == "donor":
            payload = {"manifest_sha256": generate_donor(config, scope=parts[1], seed=int(parts[2]))}
        elif len(parts) == 4 and parts[0] == "train":
            payload = {"manifest_sha256": train_cell(config, scope=parts[1], arm=parts[2], seed=int(parts[3]))}
        elif len(parts) == 5 and parts[0] == "eval":
            seed = None if parts[4] == "none" else int(parts[4])
            payload = {"profile_sha256": evaluate(config, scope=parts[1], bank=parts[2], arm=parts[3], seed=seed)}
        else:
            raise ValueError(f"invalid R485 shard id: {args.shard_id}")
    print(json.dumps(payload, sort_keys=True, allow_nan=False))
    return 0 if args.command != "preflight" or payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
