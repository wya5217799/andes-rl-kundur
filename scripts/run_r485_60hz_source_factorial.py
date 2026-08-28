"""R485 fixed-budget source factorial with one canonical 50-to-60 Hz seam.

This round adapter owns only R485 identity, roster, fixed budgets, create-only
artifacts, and the training/evaluation bindings.  Scientific kernels remain in
the package modules imported below.  Formal execution is seal- and owner-gated.

Usage: ``python scripts/run_r485_60hz_source_factorial.py <command>``.
``preflight`` exits 1 when any semantic authority gate or output-absence check
fails; execution commands raise without their required hashed authority files.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCIENTIFIC_ENVIRONMENT = {
    "N_SUBSTEPS": "5",
    "DISABLE_TOGGLER": "1",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
}
for _name, _value in SCIENTIFIC_ENVIRONMENT.items():
    os.environ[_name] = _value

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.source_factorial_sac import (  # noqa: E402
    SourceFactorialSACAgent,
)
from andes_rl_kundur.agents.networks import (  # noqa: E402
    LOG_STD_MAX,
    LOG_STD_MIN,
)
from andes_rl_kundur.control.per_vsg_md import (  # noqa: E402
    adapt_v4_observations_to_physical,
)
from andes_rl_kundur.evaluation.cd_matd3_canary import (  # noqa: E402
    build_contract as build_physical_contract,
)
from andes_rl_kundur.evaluation.r485_experiment import (  # noqa: E402
    analyse_result_root,
    attempt_output_root,
    build_canary_admissibility,
    build_rehearsal_evidence,
    evaluate_trajectory as _evaluate_trajectory,
    evaluation_contracts,
    learner_metrics as _learner_metrics,
    registered_shards,
    resolve_tds,
    run_objective_semantics_probe,
    verify_formal_authority,
)
from memory.tools.artifact_io import write_new_json  # noqa: E402

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


def source_rows(current: np.ndarray, source: str) -> np.ndarray:
    """Route the same-time authentic rows or their registered row permutation."""

    current_rows = np.asarray(current, dtype=np.float32).reshape(4, 7)
    if source == "N":
        return current_rows.copy()
    if source != "P":
        raise ValueError(f"unknown source: {source}")
    rows = current_rows.copy()
    for actor in range(4):
        rows[actor, 3:7] = current_rows[(actor + 1) % 4, 3:7]
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


def validate_parameter_card_against_member(
    card: Mapping[str, Any], member: SourceFactorialSACAgent
) -> dict[str, Any]:
    """Resolve the frozen learner contract from a live production member."""

    actor_hidden = [
        int(layer.out_features)
        for layer in member.actor.net
        if isinstance(layer, torch.nn.Linear)
    ]
    actor_activations = [
        type(layer).__name__
        for layer in member.actor.net
        if isinstance(layer, torch.nn.ReLU)
    ]
    q1_linears = [
        layer for layer in member.critic.q1.net if isinstance(layer, torch.nn.Linear)
    ]
    q2_linears = [
        layer for layer in member.critic.q2.net if isinstance(layer, torch.nn.Linear)
    ]
    actor_lr = float(member.actor_optimizer.param_groups[0]["lr"])
    critic_lr = float(member.critic_optimizer.param_groups[0]["lr"])
    alpha_lr = float(member.alpha_optimizer.param_groups[0]["lr"])
    if len({actor_lr, critic_lr, alpha_lr}) != 1:
        raise RuntimeError("live learner optimizers do not share the frozen learning rate")
    resolved = {
        "family": "four_independent_source_factorial_executed_action_sac_agents",
        "actor_state_dim": int(member.state_dim),
        "critic_state_dim": int(member.state_dim),
        "action_dim": int(member.action_dim),
        "hidden_sizes": actor_hidden,
        "activation": (
            "ReLU" if len(actor_activations) == len(actor_hidden) else actor_activations
        ),
        "actor": "Gaussian-tanh",
        "log_std_bounds": [float(LOG_STD_MIN), float(LOG_STD_MAX)],
        "twin_q": bool(
            member.critic.q1 is not member.critic.q2
            and [layer.in_features for layer in q1_linears]
            == [layer.in_features for layer in q2_linears]
            and [layer.out_features for layer in q1_linears]
            == [layer.out_features for layer in q2_linears]
        ),
        "lr": actor_lr,
        "gamma": float(member.gamma),
        "tau": float(member.tau),
        "replay_capacity": int(member.buffer.capacity),
        "batch_size": int(member.batch_size),
        "alpha_initial": float(member.alpha.detach().cpu()),
        "alpha_bounds": [
            float(np.exp(member._log_alpha_min)),
            float(np.exp(member._log_alpha_max)),
        ],
        "target_entropy": float(member.target_entropy),
        "max_grad_norm": float(member.max_grad_norm),
        "updates_per_environment_step_after_warmup": 1,
        "training_policy": "stochastic",
        "evaluation_policy": "deterministic_mean",
    }
    frozen = card.get("learner", {})

    def matches(left: Any, right: Any) -> bool:
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return bool(np.isclose(left, right, rtol=1.0e-12, atol=1.0e-12))
        if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
            return len(left) == len(right) and all(
                matches(a, b) for a, b in zip(left, right, strict=True)
            )
        return left == right

    mismatches = [
        f"learner.{name}"
        for name, value in resolved.items()
        if not matches(frozen.get(name), value)
    ]
    if mismatches:
        raise RuntimeError(
            "parameter card/live learner mismatch: " + ", ".join(mismatches)
        )
    return resolved


def objective_semantics_probe() -> dict[str, Any]:
    return run_objective_semantics_probe(
        new_member=_new_member,
        tensor_hash=_tensor_hash,
        canonicalize=canonical_rows,
        route_source=source_rows,
    )


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
    for group in ("sources", "parents"):
        rows = card.get(group)
        if not isinstance(rows, dict) or not rows:
            raise RuntimeError(f"{scope} authority failed: resolved {group} missing")
        for name, row in rows.items():
            source = ROOT / str(row.get("path", ""))
            if not source.is_file() or _sha256(source) != row.get("sha256"):
                raise RuntimeError(f"{scope} authority failed: resolved {group} drift: {name}")
    installed_case = card.get("installed_case") or {}
    case_path = Path(str(installed_case.get("path", "")))
    if not case_path.is_file() or _sha256(case_path) != installed_case.get("sha256"):
        raise RuntimeError(f"{scope} authority failed: installed case drift")
    if scope == "formal":
        verify_formal_authority(
            repo_root=ROOT,
            config=config,
            expected_shards=registered_shards(config, scope="formal"),
            reviewed_files=tuple(
                ROOT / str(row["path"]) for row in card["sources"].values()
            ),
        )


def build_parameter_card() -> dict[str, Any]:
    physical = build_physical_contract()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    card = copy.deepcopy(config["parameter_card"])
    card.update({
        "schema_version": 1,
        "round": ROUND_ID,
        "scientific_environment": dict(SCIENTIFIC_ENVIRONMENT),
        "design": {"arms": list(ARM_IDS), "formal_seeds": list(FORMAL_SEEDS), "canary_seed": CANARY_SEED, "interaction_steps": 43_200, "evaluation_steps": 150, "prefix_steps": 30, "dt_seconds": 0.2},
        "action": {"normalized_bounds": [-1.0, 1.0], "slew_limit": float(physical["action_slew_limit"]), "decoder": copy.deepcopy(physical["decoder"])},
        "profiles": copy.deepcopy(physical["profiles"]),
        "evaluation_contracts": evaluation_contracts(),
        "training_schedule": copy.deepcopy(physical["training_contract"]["development_scenario_order"]),
    })
    return card


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> str:
    return write_new_json(path, payload)


def resolve_parameter_card(config: Mapping[str, Any]) -> str:
    _assert_physical_runtime()
    import andes

    sources = {name: ROOT / path for name, path in config["source_files"].items()}
    parents = {name: ROOT / path for name, path in config["parent_files"].items()}
    sources.update(runner=Path(__file__).resolve(), config=Path(config["_path"]), plan=ROOT / str(config["paths"]["plan"]))
    probe = _new_member()
    optimizer = probe.actor_optimizer.param_groups[0]
    card = build_parameter_card()
    card["resolved_learner"] = validate_parameter_card_against_member(card, probe)
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
    card["parents"] = {
        name: {"path": path.relative_to(ROOT).as_posix(), "sha256": _sha256(path)}
        for name, path in sorted(parents.items())
    }
    card["objective_semantics_probe"] = objective_semantics_probe()
    card["created_utc"] = datetime.now(UTC).isoformat()
    if card["objective_semantics_probe"]["passed"] is not True:
        raise RuntimeError("R485 objective semantics probe failed")
    return _write_new_json(ROOT / str(config["paths"]["resolved_parameter_card"]), card)


def write_rosters(config: Mapping[str, Any]) -> dict[str, str]:
    shards = registered_shards(config, scope="formal")
    return {
        name: _write_new_json(
            ROOT / str(config["paths"][f"{name}_shards"]), list(values)
        )
        for name, values in shards.items()
    }


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
    drift = {
        name: os.environ.get(name)
        for name, expected in SCIENTIFIC_ENVIRONMENT.items()
        if os.environ.get(name) != expected
    }
    if drift:
        raise RuntimeError(f"R485 scientific environment drift: {drift}")
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
    env.seed(int(profile["environment_seed"]))
    env.STEPS_PER_EPISODE = steps
    return env


def _scope_root(config: Mapping[str, Any], scope: str) -> Path:
    return attempt_output_root(ROOT, config, scope=scope)


def generate_base(config: Mapping[str, Any], *, scope: str, seed: int) -> str:
    _assert_physical_runtime()
    require_authority(config, scope=scope)
    allowed = (CANARY_SEED,) if scope == "canary" else FORMAL_SEEDS
    if seed not in allowed:
        raise ValueError("unregistered base seed")
    root = _scope_root(config, scope)
    card_sha = _sha256(ROOT / str(config["paths"]["resolved_parameter_card"]))
    folder = root / "bases" / f"seed{seed}"
    if folder.exists():
        raise FileExistsError(f"base output exists: {folder}")
    folder.mkdir(parents=True)
    _seed_all(seed)
    base = FactorialPolicy(ARM_IDS[0]).export()
    base_path = folder / "base_state.pt"
    torch.save({"kind": "r485-common-base", "seed": seed, "members": base}, str(base_path))
    return _write_new_json(folder / "manifest.json", {"schema_version": 1, "round": ROUND_ID, "scope": scope, "seed": seed, "resolved_parameter_card_sha256": card_sha, "source_routing": {"authentic": "same_time_rows_unchanged", "placebo": "same_time_row_permutation_rho_i_plus_1", "exogenous_donor_bank": False}, "base_state": {"path": base_path.relative_to(ROOT).as_posix(), "sha256": _sha256(base_path)}})


def _base_manifest(config: Mapping[str, Any], scope: str, seed: int) -> dict[str, Any]:
    manifest_path = _scope_root(config, scope) / "bases" / f"seed{seed}" / "manifest.json"
    if not _hash_valid(manifest_path):
        raise RuntimeError("base manifest is missing or hash-invalid")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("round") != ROUND_ID or manifest.get("scope") != scope or int(manifest.get("seed", -1)) != seed:
        raise RuntimeError("base identity mismatch")
    card_path = ROOT / str(config["paths"]["resolved_parameter_card"])
    if manifest.get("resolved_parameter_card_sha256") != _sha256(card_path):
        raise RuntimeError("base parameter-card lineage mismatch")
    if manifest.get("source_routing", {}).get("exogenous_donor_bank") is not False:
        raise RuntimeError("base manifest permits an exogenous donor bank")
    base = manifest.get("base_state", {})
    path = ROOT / str(base.get("path", ""))
    if not path.is_file() or _sha256(path) != base.get("sha256"):
        raise RuntimeError("base-state hash mismatch")
    return manifest


def _save_policy(path: Path, policy: FactorialPolicy, *, scope: str, arm: str, seed: int, stage: str) -> str:
    if path.exists():
        raise FileExistsError(f"checkpoint exists: {path}")
    torch.save({"kind": "r485-source-factorial", "round": ROUND_ID, "scope": scope, "arm_id": arm, "seed": seed, "stage": stage, "members": policy.export()}, str(path))
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def train_cell(config: Mapping[str, Any], *, scope: str, arm: str, seed: int) -> str:
    _assert_physical_runtime()
    require_authority(config, scope=scope)
    factors = arm_factors(arm)
    base_manifest = _base_manifest(config, scope, seed)
    folder = _scope_root(config, scope) / "train" / arm / f"seed{seed}"
    if folder.exists():
        raise FileExistsError(f"training output exists: {folder}")
    folder.mkdir(parents=True)
    _seed_all(seed)
    policy = FactorialPolicy(arm)
    base = torch.load(str(ROOT / base_manifest["base_state"]["path"]), map_location="cpu", weights_only=True)
    for member, state in zip(policy.members, base["members"], strict=True):
        member.import_state(state)
    initial = [_tensor_hash(member) for member in policy.members]
    contract = evaluation_contracts()["same"]
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
            for time_index in range(30):
                current = canonical_rows(observation)
                actor_rows = source_rows(current, factors["actor_source"])
                critic_rows = source_rows(current, factors["critic_source"])
                raw, executed = policy.act(actor_rows, previous, deterministic=False)
                observation, _reward, done, info = envs[str(profile["profile_id"])].step({i: executed[i] for i in range(4)})
                steps += 1
                next_current = canonical_rows(observation)
                reward = step_rewards(current, info["delta_M"], info["delta_D"], reward_access=factors["reward_access"])
                policy.store(actor_rows, critic_rows, previous, raw, executed, reward, source_rows(next_current, factors["actor_source"]), source_rows(next_current, factors["critic_source"]), bool(done) or bool(info["tds_failed"]))
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
                if done and time_index != 29:
                    raise RuntimeError(
                        f"premature training terminal at step {time_index} of 30"
                    )
                if steps >= 43_200:
                    break
            episodes += 1
    finally:
        for env in envs.values():
            env.close()
    final_sha = _save_policy(folder / "final.pt", policy, scope=scope, arm=arm, seed=seed, stage="final")
    card_path = ROOT / str(config["paths"]["resolved_parameter_card"])
    card = json.loads(card_path.read_text(encoding="utf-8"))
    metrics = _learner_metrics(
        policy,
        initial,
        curves,
        rewards_seen,
        actions_seen,
        update_count,
        card.get("objective_semantics_probe", {}),
        _tensor_hash,
    )
    np.savez_compressed(folder / "curves.npz", **{key: np.asarray(value) for key, value in curves.items()})
    base_manifest_path = _scope_root(config, scope) / "bases" / f"seed{seed}" / "manifest.json"
    return _write_new_json(folder / "manifest.json", {"schema_version": 1, "round": ROUND_ID, "scope": scope, "arm_id": arm, "factors": factors, "seed": seed, "resolved_parameter_card_sha256": _sha256(card_path), "base_manifest_sha256": _sha256(base_manifest_path), "base_state_sha256": base_manifest["base_state"]["sha256"], "interaction_steps": steps, "episodes": episodes, "tds_failed_episodes": tds_failures, "half_checkpoint_sha256": half_sha, "final_checkpoint_sha256": final_sha, "curves_sha256": _sha256(folder / "curves.npz"), "learner_admissibility": metrics, "valid": steps == 43_200 and half_sha is not None and metrics["assessment"]["passed"]})


def _profiles(bank: str) -> list[dict[str, Any]]:
    if bank not in {"same", "fresh"}:
        raise ValueError("bank must be same or fresh")
    contract = evaluation_contracts()[bank]
    return [row for row in contract["profiles"] if row["split"] == "evaluation"]


def evaluate(config: Mapping[str, Any], *, scope: str, bank: str, arm: str, seed: int | None) -> list[str]:
    _assert_physical_runtime()
    require_authority(config, scope=scope)
    learned = arm in ARM_IDS
    if learned != (seed is not None) or learned and bank != "same":
        raise ValueError("learned evaluation requires a seed and the same bank")
    policy = FactorialPolicy(arm) if learned else None
    factors = None
    controller = None
    training_sha = checkpoint_sha = base_manifest_sha = None
    if learned:
        manifest_path = _scope_root(config, scope) / "train" / arm / f"seed{seed}" / "manifest.json"
        if not _hash_valid(manifest_path):
            raise RuntimeError("training manifest missing or hash-invalid")
        training = json.loads(manifest_path.read_text(encoding="utf-8"))
        if training.get("valid") is not True:
            raise RuntimeError("training cell is not learner-admissible")
        card_sha = _sha256(ROOT / str(config["paths"]["resolved_parameter_card"]))
        if training.get("resolved_parameter_card_sha256") != card_sha:
            raise RuntimeError("training parameter-card lineage mismatch")
        checkpoint = manifest_path.with_name("final.pt")
        checkpoint_sha = _sha256(checkpoint)
        if checkpoint_sha != training["final_checkpoint_sha256"]:
            raise RuntimeError("training checkpoint hash mismatch")
        policy.load(checkpoint)
        training_sha = _sha256(manifest_path)
        base_manifest = _base_manifest(config, scope, int(seed))
        base_manifest_path = _scope_root(config, scope) / "bases" / f"seed{seed}" / "manifest.json"
        base_manifest_sha = _sha256(base_manifest_path)
        if training.get("base_manifest_sha256") != base_manifest_sha:
            raise RuntimeError("training base-manifest lineage mismatch")
        if training.get("base_state_sha256") != base_manifest["base_state"]["sha256"]:
            raise RuntimeError("training base-state lineage mismatch")
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
    bank_contract = evaluation_contracts()[bank]
    transform = np.asarray(bank_contract["differential_transform"], dtype=float)
    for profile in _profiles(bank):
        env = _build_env(profile, steps=150)
        records: list[dict[str, Any]] = []
        try:
            for scenario in profile["scenarios"]:
                primary = _evaluate_trajectory(
                    env=env,
                    scenario=scenario,
                    transform=transform,
                    learned=learned,
                    policy=policy,
                    factors=factors,
                    controller=controller,
                    canonicalize=canonical_rows,
                    route_source=source_rows,
                    direct_action=direct_md_raw_actions,
                    reward_function=step_rewards,
                )
                reproduction = None
                if primary["tds_failed"]:
                    reproduction = _evaluate_trajectory(
                        env=env,
                        scenario=scenario,
                        transform=transform,
                        learned=learned,
                        policy=policy,
                        factors=factors,
                        controller=controller,
                        canonicalize=canonical_rows,
                        route_source=source_rows,
                        direct_action=direct_md_raw_actions,
                        reward_function=step_rewards,
                    )
                classification = resolve_tds(
                    primary_failed=bool(primary["tds_failed"]),
                    reproduction_failed=(
                        None if reproduction is None else bool(reproduction["tds_failed"])
                    ),
                )
                steps = primary["steps"]
                records.append({"round": ROUND_ID, "scope": scope, "bank": bank, "bank_contract_sha256": bank_contract["sha256"], "environment_seed": int(profile["environment_seed"]), "profile_id": str(profile["profile_id"]), "scenario_id": str(scenario["scenario_id"]), "pair_kind": str(scenario["pair_kind"]), "sign": str(scenario["sign"]), "magnitude": float(scenario["magnitude"]), "delta_u": dict(scenario["delta_u"]), "arm_id": arm, "training_seed": seed, "checkpoint_sha256": checkpoint_sha, "training_manifest_sha256": training_sha, "base_manifest_sha256": base_manifest_sha, "resolved_parameter_card_sha256": card_sha, "stage": "final", "identity": {**primary["identity"], "baseline_m0": [float(value) for value in profile["baseline_m0"]], "baseline_d0": [float(value) for value in profile["baseline_d0"]]}, "initial_freq_hz_physical": primary["initial_freq_hz_physical"], "steps": steps, "completed_steps": len(steps), "completed": classification == "COMPLETE" and len(steps) == 150, "tds_failed": bool(primary["tds_failed"]), "tds_classification": classification if primary["tds_failed"] else None, "tds_reproduction": None if reproduction is None else {"tds_failed": bool(reproduction["tds_failed"]), "completed_steps": len(reproduction["steps"]), "steps": reproduction["steps"]}, "failure": "TDS failed" if primary["tds_failed"] else None})
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
    card_sha = _sha256(ROOT / str(config["paths"]["resolved_parameter_card"]))
    payload = build_canary_admissibility(
        root=root,
        card_sha256=card_sha,
        arms=ARM_IDS,
        seed=CANARY_SEED,
        contracts=evaluation_contracts(),
    )
    return _write_new_json(ROOT / str(config["paths"]["canary_admissibility"]), payload)


def rehearse(config: Mapping[str, Any]) -> str:
    _assert_physical_runtime()
    require_authority(config, scope="canary")
    import andes

    payload = build_rehearsal_evidence(
        repo_root=ROOT,
        config=config,
        runtime={
            "python": sys.version,
            "python_executable": sys.executable,
            "andes_version": getattr(andes, "__version__", "unknown"),
            "andes_module": str(Path(andes.__file__).resolve()),
            "scientific_environment": dict(SCIENTIFIC_ENVIRONMENT),
        },
    )
    if not all(payload["checks"].values()):
        raise RuntimeError(f"R485 rehearsal failed: {payload['checks']}")
    payload["created_utc"] = datetime.now(UTC).isoformat()
    return _write_new_json(ROOT / str(config["paths"]["rehearsal"]), payload)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("show-card", "resolve-card", "write-rosters", "preflight", "assess-canary", "rehearse", "analyse-formal", "shard"),
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
    elif args.command == "write-rosters":
        payload = {"roster_sha256": write_rosters(config)}
    elif args.command == "preflight":
        try:
            require_authority(config, scope="formal")
        except RuntimeError as exc:
            errors = [str(exc)]
        else:
            errors = []
        try:
            formal_root = _scope_root(config, "formal")
        except (FileNotFoundError, RuntimeError):
            formal_root = config["_formal_out"]
        payload = {"round": ROUND_ID, "passed": not errors and not formal_root.exists(), "authority_errors": errors, "formal_output_absent": not formal_root.exists(), "formal_attempt_root": str(formal_root)}
    elif args.command == "assess-canary":
        payload = {"canary_admissibility_sha256": assess_canary(config)}
    elif args.command == "rehearse":
        payload = {"rehearsal_sha256": rehearse(config)}
    elif args.command == "analyse-formal":
        require_authority(config, scope="formal")
        result = analyse_result_root(
            repo_root=ROOT,
            config=config,
            root=_scope_root(config, "formal"),
            scope="formal",
        )
        if result["status"] in {"EXECUTION-INCOMPLETE", "INTEGRITY-INVALID"}:
            raise RuntimeError(f"R485 formal analysis blocked: {result['status']}")
        payload = {
            "formal_analysis_sha256": _write_new_json(
                _scope_root(config, "formal") / "formal_analysis.json", result
            )
        }
    else:
        if args.resume or not args.shard_id:
            raise RuntimeError("R485 forbids partial-cell resume and requires a shard id")
        parts = args.shard_id.split("|")
        allowed = {
            shard
            for scope in ("canary", "formal")
            for values in registered_shards(config, scope=scope).values()
            for shard in values
        }
        if args.shard_id not in allowed:
            raise ValueError(f"unregistered R485 shard: {args.shard_id}")
        if len(parts) == 3 and parts[0] == "base":
            payload = {"manifest_sha256": generate_base(config, scope=parts[1], seed=int(parts[2]))}
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
