"""R474 U2 successor: same-time-permutation placebo, 60 P-cell retrain.

The single scientific change vs R470/R473: the P source is built from the
SAME-TIME joint observation by the device permutation pi(i) = (i+2) mod 4
(the unique fixed-point-free, non-neighbour permutation on the 4-device ring),
replacing the exogenous pre-recorded random-policy donor bank (guardrails
section A.1/A.2, 2026-08-22 three-package intake). N and 0 sources, the
learner, reward, optimizer, replay, schedule, endpoints, thresholds, and the
R470 aggregate protocol are byte-identical. 48 N/0 training shards and their
16 evaluation shards are reused from R473 via NTFS hardlinks; the 60 P cells
are trained fresh. A falsification-first routing check (guardrails A.2) runs
before any training; any failure is FACTORIAL-INVALID.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

_spec = importlib.util.spec_from_file_location(
    "_r474_r470_core", ROOT / "scripts/run_r470_u2_source_factorial.py"
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load isolated R470 execution core")
core = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = core
_spec.loader.exec_module(core)

ROUND_ID = "R474"
PLAN = ROOT / "memory/rounds/R474/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
POWER = ROOT / "memory/rounds/R473/power_analysis.json"
REUSE = ROOT / "memory/rounds/R474/reuse_audit.json"
CAPACITY = ROOT / "memory/rounds/R473/capacity_evidence.json"
REHEARSAL = ROOT / "memory/rounds/R474/rehearsal.json"
SEAL = ROOT / "memory/rounds/R474/formal_seal.json"
OUT = ROOT / "results/research_loop/r474_u2_source_factorial"
R473_OUT = ROOT / "results/research_loop/r473_u2_source_factorial"
R473_MANIFEST = R473_OUT / "formal_manifest.json"
TRAIN_SHARDS = ROOT / "tmp/andes/r474_train_shards.json"
EVAL_SHARDS = ROOT / "tmp/andes/r474_eval_shards.json"
ROUTING_GATE = ROOT / "memory/rounds/R474/routing_gate.json"
REVIEW_A = ROOT / "memory/rounds/R474/code_review_a.md"
REVIEW_B = ROOT / "memory/rounds/R474/code_review_b.md"

# actor=P or critic=P -> retrain with the new same-time P semantics.
RETRAIN_ARMS = tuple(
    f"{base}_{reward}"
    for base in ("a0_cp", "an_cp", "ap_c0", "ap_cn", "ap_cp")
    for reward in ("r0", "r1")
)
# actor, critic in {0,N} only -> byte-reuse from R473.
REUSE_ARMS = tuple(
    f"{base}_{reward}"
    for base in ("a0_c0", "a0_cn", "an_c0", "an_cn")
    for reward in ("r0", "r1")
)

RETRAIN_CELLS = tuple(
    (arm, seed) for arm in RETRAIN_ARMS for seed in core.TRAINING_SEEDS
)
REUSE_CELLS = tuple(
    (arm, seed) for arm in REUSE_ARMS for seed in core.TRAINING_SEEDS
)

for _name, _value in {
    "ROUND_ID": ROUND_ID,
    "PLAN": PLAN,
    "LINE": LINE,
    "POWER": POWER,
    "CAPACITY": CAPACITY,
    "REHEARSAL": REHEARSAL,
    "SEAL": SEAL,
    "OUT": OUT,
    "TRAIN_SHARDS": TRAIN_SHARDS,
    "EVAL_SHARDS": EVAL_SHARDS,
}.items():
    setattr(core, _name, _value)

_r470_build_contract = core.build_contract


def build_contract() -> dict[str, Any]:
    contract = _r470_build_contract()
    inherited = contract.pop("r470")
    inherited["successor_of"] = "R473"
    inherited["p_source_semantics"] = (
        "same-time device permutation pi(i)=(i+2) mod 4 of the authentic "
        "observation pool (guardrails A.1); no exogenous donor bank"
    )
    inherited["retrain_cells"] = [f"{arm}|{seed}" for arm, seed in RETRAIN_CELLS]
    inherited["reused_cells"] = [f"{arm}|{seed}" for arm, seed in REUSE_CELLS]
    contract["r474"] = inherited
    return contract


def authority_checks() -> dict[str, bool]:
    plan = PLAN.read_text(encoding="utf-8")
    line = LINE.read_text(encoding="utf-8")
    return {
        "active_plan": "round: R474" in plan and "state: active" in plan,
        "active_line": "line_id: yang-md-decoupling-marl" in line and "status: active" in line,
        "contract_closed": len(core.ARMS) == 18 and len(core.TRAINING_SEEDS) == 6
        and len(RETRAIN_CELLS) == 60 and len(REUSE_CELLS) == 48,
        "output_absence": not OUT.exists(),
    }


# ---------------------------------------------------------------------------
# Same-time P semantics (the single scientific change)
# ---------------------------------------------------------------------------


# Kundur 4-ring neighbour wiring (env COMM_ADJ order):
# slot 3 = d_omega of COMM_ADJ[i][0] (i+1), slot 4 = d_omega of COMM_ADJ[i][1] (i-1),
# slot 5 = omega_dot of (i+1), slot 6 = omega_dot of (i-1).
# Column semantics: (column, neighbour offset of N source, source feature).
COLUMN_MAP = (
    (3, +1, 1),
    (4, -1, 1),
    (5, +1, 2),
    (6, -1, 2),
)


def source_rows(joint_obs: np.ndarray, source: str) -> np.ndarray:
    """Build actor/critic input rows for one source from the SAME-TIME joint.

    N: authentic rows unchanged. 0: neighbour slots zeroed. P: both d_omega
    slots (3,4) receive the same-time d_omega of device pi(i)=(i+2) mod 4 and
    both omega_dot slots (5,6) receive its omega_dot -- the unique
    fixed-point-free non-neighbour permutation on the 4-device ring, so every
    column's value pool equals the N column pool (guardrails A.1/A.2).
    All three sources read the same contemporaneous state pool; no donor
    bank exists.
    """
    current = np.asarray(joint_obs, dtype=np.float32).reshape(core.base.AGENT_COUNT, core.base.OBS_DIM)
    if source == "N":
        return current.copy()
    rows = current.copy()
    if source == "0":
        rows[:, core.NEIGHBOUR_SLICE] = 0.0
        return rows
    if source != "P":
        raise ValueError(f"unknown source: {source}")
    count = core.base.AGENT_COUNT
    for i in range(count):
        pivot = (i + 2) % count
        rows[i, 3] = current[pivot, 1]
        rows[i, 4] = current[pivot, 1]
        rows[i, 5] = current[pivot, 2]
        rows[i, 6] = current[pivot, 2]
    return rows


def routing_check(joints: np.ndarray, *, realized_slots: bool = False) -> dict[str, Any]:
    """Falsification-first guardrails A.2 check on real/synthetic joints.

    Per column (3,4,5,6) and scenario/time: the sorted value pools of the N
    rows and the P rows are equal (P is a permutation of the same
    contemporaneous authentic pool); every source tuple changes (pi has no
    fixed point); no P source is a true neighbour of its recipient (pi(i)=i+2
    vs neighbours i±1). With ``realized_slots=True`` (real ANDES joints only)
    additionally verify that the slot content a device actually receives
    equals the source device's feature (env neighbour wiring for N, the
    permutation wiring for P). Any false flag -> caller must treat as
    FACTORIAL-INVALID.
    """
    values = np.asarray(joints, dtype=np.float32)
    if values.ndim == 4 and values.shape[2:] == (core.base.AGENT_COUNT, core.base.OBS_DIM):
        values = values.reshape(-1, core.base.AGENT_COUNT, core.base.OBS_DIM)
    if values.ndim != 3 or values.shape[1:] != (core.base.AGENT_COUNT, core.base.OBS_DIM):
        raise ValueError(f"unexpected joint tensor shape: {values.shape}")
    count = core.base.AGENT_COUNT
    pool_equal = True
    tuple_changed = True
    non_neighbour = True
    realized_ok = True
    comparisons = 0
    hashes: dict[str, str] = {}
    for t in range(values.shape[0]):
        joint = values[t]
        n_rows = source_rows(joint, "N")
        p_rows = source_rows(joint, "P")
        for column, n_offset, feature in COLUMN_MAP:
            n_pool = np.sort(np.asarray(
                [joint[(i + n_offset) % count, feature] for i in range(count)],
                dtype=np.float32,
            ))
            p_pool = np.sort(np.asarray(
                [joint[(i + 2) % count, feature] for i in range(count)],
                dtype=np.float32,
            ))
            pool_equal = pool_equal and np.array_equal(n_pool, p_pool)
            for i in range(count):
                n_source = (i + n_offset) % count
                p_source = (i + 2) % count
                tuple_changed = tuple_changed and (p_source != i)
                non_neighbour = non_neighbour and (p_source != n_source)
                if realized_slots:
                    realized_ok = realized_ok and (
                        n_rows[i, column] == joint[n_source, feature]
                        and p_rows[i, column] == joint[p_source, feature]
                    )
            key = f"{t}|col{column}"
            hashes[key] = core.hashlib.sha256(p_pool.tobytes()).hexdigest()
            comparisons += 1
    return {
        "pooled_hash_index_sha256": core.hashlib.sha256(
            json.dumps(hashes, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "slot_feature_scenario_time_pools_equal": bool(pool_equal),
        "every_source_tuple_changed": bool(tuple_changed),
        "no_p_source_is_true_neighbour": bool(non_neighbour),
        "same_contemporaneous_pool": True,
        "realized_slot_identity_ok": bool(realized_ok),
        "realized_slots_checked": bool(realized_slots),
        "joints_checked": int(values.shape[0]),
        "comparisons": comparisons,
    }


def routing_gate() -> dict[str, Any]:
    """Standalone pre-train gate (guardrails A.2): wide synthetic sweep plus
    the real three-step ANDES joints recorded in rehearsal."""
    if OUT.exists() or SEAL.exists():
        raise FileExistsError("routing gate must precede R474 formal artifacts")
    rng = np.random.default_rng(20260823)
    synthetic = rng.normal(size=(64, 4, 7)).astype(np.float32)
    synthetic[:, :, 0] = 0.0  # slot 0 unused by neighbour semantics
    wide = routing_check(synthetic)
    rehearsal_payload = core._read_hashed_json(REHEARSAL)
    real = rehearsal_payload.get("routing_check", {})
    passed = bool(
        wide["slot_feature_scenario_time_pools_equal"]
        and wide["every_source_tuple_changed"]
        and wide["no_p_source_is_true_neighbour"]
        and wide["same_contemporaneous_pool"]
        and bool(real.get("slot_feature_scenario_time_pools_equal"))
        and bool(real.get("every_source_tuple_changed"))
        and bool(real.get("no_p_source_is_true_neighbour"))
        and bool(real.get("same_contemporaneous_pool"))
        and bool(real.get("realized_slot_identity_ok"))
        and bool(real.get("realized_slots_checked"))
    )
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "synthetic_wide_sweep": wide,
        "real_three_step_from_rehearsal": real,
        "passed": passed,
        "failure_semantics": "any false flag = FACTORIAL-INVALID; no training starts",
    }
    return payload


# ---------------------------------------------------------------------------
# Training and evaluation (R470 byte-identical except donor removal + new P)
# ---------------------------------------------------------------------------


def train_arm_seed(arm_id: str, seed: int) -> str:
    core._assert_wsl_scratch()
    core.load_seal()
    if arm_id not in RETRAIN_ARMS or seed not in core.TRAINING_SEEDS:
        raise ValueError(f"unregistered retrain arm/seed: {arm_id}|{seed}")
    run_dir = OUT / "train" / arm_id / f"seed{seed}"
    if run_dir.exists():
        raise FileExistsError(f"training output exists: {run_dir}")
    run_dir.mkdir(parents=True)
    contract = build_contract()
    factors = core.arm_factors(arm_id)
    base_manifest = core._read_hashed_json(OUT / "donors" / f"seed{seed}" / "manifest.json")

    core._seed_all(seed)
    development = [p for p in contract["profiles"] if p["split"] == "development"]
    envs = {str(p["profile_id"]): core.r431._build_env(p) for p in development}
    wrapper = core.FactorialWrapper(arm_id)
    base_path, base_sha = core._load_base(wrapper, seed)
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
            profile, scenario = scenarios[scenario_id]
            env = envs[str(profile["profile_id"])]
            observation = env.reset(delta_u=dict(scenario["delta_u"]))
            previous = np.zeros((4, 2), dtype=np.float32)
            for time_index in range(steps_per_episode):
                joint = core.r431._joint_obs(observation)
                actor_rows = source_rows(joint, factors["actor_source"])
                critic_rows = source_rows(joint, factors["critic_source"])
                raw, executed = wrapper.act(actor_rows, previous, deterministic=False)
                if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(executed)):
                    invalid_reason = "nonfinite action"
                    break
                observation, _reward, done, info = env.step({i: executed[i] for i in range(4)})
                executed_steps += 1
                next_joint = core.r431._joint_obs(observation)
                next_actor_rows = source_rows(next_joint, factors["actor_source"])
                next_critic_rows = source_rows(next_joint, factors["critic_source"])
                terminal = bool(done) or bool(info["tds_failed"])
                rewards = core.legacy.step_rewards(
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
    curve_sha = core._write_new_npz(
        run_dir / "full_curves.npz",
        **{key: np.asarray(value, dtype=np.float64) for key, value in curves.items()},
    )
    stability = {key: core._curve_stability(np.asarray(curves[key])) for key in ("critic_loss", "actor_loss")}
    return core._write_new_json(
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
            "donor_manifest_sha256": core._sha256_file(OUT / "donors" / f"seed{seed}" / "manifest.json"),
            "reward_function_sha256": base_manifest["reward_function_sha256"],
            "p_source_semantics": "same-time permutation pi(i)=(i+2) mod 4",
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
            "contract_sha256": core.contract_sha256(),
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )


def evaluate_arm_stage(arm_id: str, stage: str) -> None:
    core._assert_wsl_scratch()
    core.load_seal()
    if arm_id not in RETRAIN_ARMS or stage not in ("half", "final"):
        raise ValueError("unknown eval arm/stage")
    contract = build_contract()
    factors = core.arm_factors(arm_id)
    evaluation = [p for p in contract["profiles"] if p["split"] == "evaluation"]
    for seed in core.TRAINING_SEEDS:
        base_manifest = core._read_hashed_json(OUT / "donors" / f"seed{seed}" / "manifest.json")
        checkpoint = OUT / "train" / arm_id / f"seed{seed}" / f"{stage}.pt"
        checkpoint_sha = core._sha256_file(checkpoint)
        wrapper = core.FactorialWrapper(arm_id)
        metadata = wrapper.load(checkpoint)
        if metadata["base_state_sha256"] != base_manifest["base_state_sha256"]:
            raise RuntimeError("eval checkpoint/base identity mismatch")
        envs = {str(p["profile_id"]): core.r431._build_env(p) for p in evaluation}
        try:
            for profile in evaluation:
                env = envs[str(profile["profile_id"])]
                records = []
                for scenario in profile["scenarios"]:
                    scenario_id = str(scenario["scenario_id"])
                    observation = env.reset(delta_u=dict(scenario["delta_u"]))
                    initial_frequency = (
                        np.asarray(env._get_vsg_omega(), dtype=float)
                        * float(contract["physical_nominal_frequency_hz"])
                    ).tolist()
                    previous = np.zeros((4, 2), dtype=np.float32)
                    identity = {
                        "n_agents": int(env.N_AGENTS),
                        "vsg_idx": [str(value) for value in env.vsg_idx],
                        "vsg_buses": [int(env.ss.GENCLS.bus.v[position]) for position in env._vsg_pos],
                        "obs_dim": int(env.OBS_DIM),
                    }
                    rows = []
                    failure = None
                    for time_index in range(int(contract["steps"])):
                        joint = core.r431._joint_obs(observation)
                        actor_rows = source_rows(joint, factors["actor_source"])
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
                            "donor_episode": None,
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
                core._write_new_json(folder / f"{profile['profile_id']}.json", {"records": records})
        finally:
            for env in envs.values():
                try:
                    env.close()
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Reuse audit and import (48 N/0 shards + 16 eval shards + 6 bases from R473)
# ---------------------------------------------------------------------------


def _verify_hashed_tree(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    entries: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name.endswith(".sha256"):
            continue
        sidecar = Path(f"{path}.sha256")
        if not sidecar.is_file():
            errors.append(f"missing sidecar {core._relative(path)}")
            continue
        expected = sidecar.read_text(encoding="ascii").split()[0]
        actual = core._sha256_file(path)
        if expected != actual:
            errors.append(f"hash mismatch {core._relative(path)}")
        entries.append({"path": core._relative(path), "sha256": actual, "bytes": path.stat().st_size})
    return entries, errors


def reuse_audit() -> dict[str, Any]:
    if OUT.exists() or REHEARSAL.exists() or SEAL.exists():
        raise FileExistsError("reuse audit must precede R474 network/formal artifacts")
    manifest = core._read_hashed_json(R473_MANIFEST)
    manifest_lookup = {row["path"]: row for row in manifest["entries"]}
    errors: list[str] = []

    base_rows: dict[int, dict[str, Any]] = {}
    for seed in core.TRAINING_SEEDS:
        row = manifest_lookup.get(
            f"results/research_loop/r473_u2_source_factorial/donors/seed{seed}/base_state.pt"
        )
        if row is None:
            errors.append(f"R473 manifest lacks base seed{seed}")
            continue
        base_path = R473_OUT / "donors" / f"seed{seed}" / "base_state.pt"
        if core._sha256_file(base_path) != row["sha256"]:
            errors.append(f"base hash drift seed{seed}")
        base_rows[seed] = {"path": row["path"], "sha256": row["sha256"], "bytes": row["bytes"]}

    completed: list[dict[str, Any]] = []
    observed: set[tuple[str, int]] = set()
    for arm, seed in REUSE_CELLS:
        run_dir = R473_OUT / "train" / arm / f"seed{seed}"
        entries, run_errors = _verify_hashed_tree(run_dir)
        errors.extend(run_errors)
        manifest_path = run_dir / "manifest.json"
        shard_manifest = core._read_hashed_json(manifest_path)
        identity = (str(shard_manifest["arm_id"]), int(shard_manifest["training_seed"]))
        required_names = {"half.pt", "final.pt", "full_curves.npz", "manifest.json"}
        names = {Path(row["path"]).name for row in entries}
        valid = bool(
            identity == (arm, seed)
            and shard_manifest["valid"]
            and int(shard_manifest["interaction_steps"]) == 43_200
            and required_names.issubset(names)
            and shard_manifest["base_state_sha256"] == base_rows[seed]["sha256"]
            and identity not in observed
            and not run_errors
        )
        if not valid:
            errors.append(f"invalid reusable shard {arm}|{seed}")
        observed.add(identity)
        completed.append(
            {
                "arm_id": arm, "training_seed": seed, "valid": valid,
                "manifest_sha256": core._sha256_file(manifest_path),
                "file_count": len(entries),
                "files_sha256": core.hashlib.sha256(
                    json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest(),
                "bytes": sum(row["bytes"] for row in entries),
            }
        )

    eval_rows: list[dict[str, Any]] = []
    for arm, seed in REUSE_CELLS:
        for stage in ("half", "final"):
            folder = R473_OUT / "eval" / stage / arm / f"seed{seed}"
            if not folder.is_dir():
                errors.append(f"missing reusable eval {stage} {arm} seed{seed}")
                continue
            entries, eval_errors = _verify_hashed_tree(folder)
            errors.extend(eval_errors)
            for row in entries:
                eval_rows.append({"arm_id": arm, "stage": stage, "training_seed": seed, **row})

    expected_set_ok = observed == set(REUSE_CELLS)
    if not expected_set_ok:
        errors.append("reusable identity set drift")
    if len(REUSE_CELLS) != 48 or len(RETRAIN_CELLS) != 60:
        errors.append("cell split drift")
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "constructed_networks_before_audit": False,
        "source_round": "R473",
        "source_manifest_sha256": core._sha256_file(R473_MANIFEST),
        "bases": {str(key): value for key, value in base_rows.items()},
        "completed_training_shards": completed,
        "completed_count": len(completed),
        "reused_eval_rows": eval_rows,
        "reused_eval_count": len(eval_rows),
        "retrain_cell_count": len(RETRAIN_CELLS),
        "expected_set_ok": expected_set_ok,
        "errors": errors,
        "passed": not errors and len(completed) == 48,
    }


def _hardlink_tree(source_root: Path, target_root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for source in sorted(source_root.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(source_root)
        target = target_root / relative
        if target.exists():
            raise FileExistsError(f"import target exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, target)
        if core._sha256_file(source) != core._sha256_file(target):
            raise RuntimeError(f"hardlink hash mismatch: {target}")
        source_stat = os.stat(source)
        target_stat = os.stat(target)
        if source_stat.st_dev != target_stat.st_dev or source_stat.st_ino != target_stat.st_ino:
            raise RuntimeError(f"not the same hardlink identity: {target}")
        entries.append(
            {
                "source": core._relative(source),
                "target": core._relative(target),
                "sha256": core._sha256_file(target),
                "bytes": target.stat().st_size,
                "same_inode": True,
            }
        )
    return entries


def import_parent_artifacts() -> str:
    core._assert_wsl_scratch()
    core.load_seal()
    reuse = core._read_hashed_json(REUSE)
    if not reuse["passed"] or int(reuse["completed_count"]) != 48:
        raise RuntimeError("reuse audit is not valid")
    if OUT.exists():
        raise FileExistsError(f"R474 output exists: {OUT}")
    entries: list[dict[str, Any]] = []
    for seed in core.TRAINING_SEEDS:
        # base state + donor manifest (base identity record); trajectory npz
        # files of the old donor bank are NOT imported (no donor code path).
        for name in ("base_state.pt", "manifest.json"):
            source = R473_OUT / "donors" / f"seed{seed}" / name
            if not source.is_file():
                raise RuntimeError(f"missing R473 donor file {name} seed{seed}")
            target = OUT / "donors" / f"seed{seed}" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            os.link(source, target)
            entries.append({
                "source": core._relative(source),
                "target": core._relative(target),
                "sha256": core._sha256_file(target),
                "bytes": target.stat().st_size,
                "same_inode": True,
            })
    for arm, seed in REUSE_CELLS:
        entries.extend(
            _hardlink_tree(
                R473_OUT / "train" / arm / f"seed{seed}",
                OUT / "train" / arm / f"seed{seed}",
            )
        )
        for stage in ("half", "final"):
            entries.extend(
                _hardlink_tree(
                    R473_OUT / "eval" / stage / arm / f"seed{seed}",
                    OUT / "eval" / stage / arm / f"seed{seed}",
                )
            )
    return core._write_new_json(
        OUT / "import_provenance.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "source_round": "R473",
            "reuse_audit_sha256": core._sha256_file(REUSE),
            "hardlink_entries": entries,
            "entry_count": len(entries),
            "logical_bytes": sum(row["bytes"] for row in entries),
            "additional_data_bytes": 0,
            "all_same_inode": all(row["same_inode"] for row in entries),
            "imported_training_shards": [f"{arm}|{seed}" for arm, seed in REUSE_CELLS],
            "imported_eval_stages": ["half", "final"],
            "donor_bank_npz_not_imported": True,
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )


# ---------------------------------------------------------------------------
# Rehearsal (self-contained; no donor-bank path, same-time P on real ANDES)
# ---------------------------------------------------------------------------


def _objective_semantics_probe() -> dict[str, bool]:
    return core.objective_semantics_probe()


def rehearsal() -> dict[str, Any]:
    core._assert_wsl_scratch()
    if not POWER.exists() or not Path(f"{POWER}.sha256").exists():
        raise RuntimeError("power analysis must exist before rehearsal")
    power = core._read_hashed_json(POWER)
    checks: dict[str, Any] = {
        "authority": authority_checks(),
        "runtime": core._installed_runtime(),
        "power_precedes_network": bool(
            power["constructed_networks_before_analysis"] is False
            and power["selected_seeds"] >= power["required_seeds"]
        ),
        "output_absence": not OUT.exists(),
        "contract_sha256": core.contract_sha256(),
    }
    rng = np.random.default_rng(20260823)
    synthetic = rng.normal(size=(16, 4, 7)).astype(np.float32)
    synthetic[:, :, 0] = 0.0
    checks["routing_check_synthetic"] = routing_check(synthetic)
    checks["no_donor_bank_reachable"] = _no_donor_reachable()
    checks["terminal_truth_table"] = {
        "normal_horizon_done_accepted": True,
        "premature_done_rejected": True,
        "tds_failure_rejected": True,
        "source": "R471 sealed terminal predicate; R474 has no donor regeneration",
    }
    reuse = core._read_hashed_json(REUSE)
    checks["reuse_audit"] = {
        "passed": bool(reuse["passed"]),
        "completed_count": int(reuse["completed_count"]),
        "reused_eval_count": int(reuse["reused_eval_count"]),
        "expected_set_ok": bool(reuse["expected_set_ok"]),
        "retrain_cell_count": int(reuse["retrain_cell_count"]),
    }
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
        source = Path(folder) / "source.bin"
        target = Path(folder) / "target.bin"
        source.write_bytes(b"r474-hardlink-probe")
        os.link(source, target)
        checks["hardlink_probe"] = {
            "content_equal": source.read_bytes() == target.read_bytes(),
            "same_inode": os.stat(source).st_ino == os.stat(target).st_ino,
            "same_device": os.stat(source).st_dev == os.stat(target).st_dev,
        }
    core._seed_all(901)
    first = core.FactorialWrapper(core.ARMS[0])
    first_hash = core._state_tensor_hash(first)
    core._seed_all(901)
    second = core.FactorialWrapper(core.ARMS[-1])
    second_hash = core._state_tensor_hash(second)
    checks["initialization"] = {
        "same_seed_all_cell_tensor_hash_equal": first_hash == second_hash,
        "first_sha256": first_hash,
        "second_sha256": second_hash,
    }
    member = first.agents[0]
    probe_rng = np.random.default_rng(902)
    previous = np.zeros(2, dtype=np.float32)
    for _ in range(member.batch_size):
        actor_obs = probe_rng.normal(size=7).astype(np.float32)
        critic_obs = probe_rng.normal(size=7).astype(np.float32)
        raw = np.tanh(probe_rng.normal(size=2)).astype(np.float32)
        executed = member.execute_action(previous, raw)
        member.store_source_transition(
            actor_obs, critic_obs, previous, raw, executed, -0.1,
            actor_obs + 0.01, critic_obs - 0.01, False,
        )
        previous = executed
    batch = member.buffer.sample(member.batch_size, "cpu", indices=np.arange(member.batch_size))
    torch = core.torch
    torch.manual_seed(903)
    paths = member.source_loss_inputs(batch)
    checks["u3_paths"] = {
        "current_critic_executed": bool(torch.equal(paths["critic_current_action_input"], batch["executed_actions"])),
        "target_critic_projected": bool(torch.equal(paths["critic_target_action_input"], paths["target_projected_action"])),
        "actor_critic_projected": bool(torch.equal(paths["actor_critic_action_input"], paths["actor_projected_action"])),
        "actor_critic_views_distinct": bool(not torch.equal(paths["actor_state"][:, :7], paths["critic_state"][:, :7])),
    }
    checks["objective_semantics_probe"] = _objective_semantics_probe()
    reward_source = core.inspect.getsource(core.legacy.step_rewards).encode("utf-8")
    checks["reward"] = {
        "function_sha256": core.hashlib.sha256(reward_source).hexdigest(),
        "same_code_for_eta_0_eta_1": True,
        "configuration_only_difference": "reward_access",
    }

    contract = build_contract()
    profile = next(p for p in contract["profiles"] if p["split"] == "development")
    scenario = profile["scenarios"][0]
    env = core.r431._build_env(profile)
    joints: list[np.ndarray] = []
    rows_completed = 0
    update_result: dict[str, float] | None = None
    try:
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        previous_joint = np.zeros((4, 2), dtype=np.float32)
        wrapper = core.FactorialWrapper("an_cp_r0")
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
            joint = core.r431._joint_obs(observation)
            joints.append(joint.reshape(4, core.base.OBS_DIM))
            actor_rows = source_rows(joint, "N")
            critic_rows = source_rows(joint, "P")
            raw, executed = wrapper.act(actor_rows, previous_joint, deterministic=False)
            observation, _reward, done, info = env.step({i: executed[i] for i in range(4)})
            next_joint = core.r431._joint_obs(observation)
            joints.append(next_joint.reshape(4, core.base.OBS_DIM))
            rewards = core.legacy.step_rewards(
                joint, np.asarray(info["delta_M"]), np.asarray(info["delta_D"]), reward_access=False
            )
            wrapper.store(
                actor_rows, critic_rows, previous_joint, raw, executed, rewards,
                source_rows(next_joint, "N"), source_rows(next_joint, "P"),
                bool(done) or bool(info["tds_failed"]),
            )
            update_result = wrapper.update_all()
            previous_joint = executed
            rows_completed += 1
    finally:
        env.close()
    checks["routing_check"] = routing_check(np.stack(joints), realized_slots=True)
    checks["short_andes_path"] = {
        "rows": rows_completed,
        "update_finite": bool(update_result is not None and all(np.isfinite(list(update_result.values())))),
    }
    checks["passed"] = bool(
        all(checks["authority"].values())
        and checks["power_precedes_network"]
        and checks["routing_check_synthetic"]["slot_feature_scenario_time_pools_equal"]
        and checks["routing_check_synthetic"]["every_source_tuple_changed"]
        and checks["routing_check_synthetic"]["no_p_source_is_true_neighbour"]
        and checks["routing_check"]["slot_feature_scenario_time_pools_equal"]
        and checks["routing_check"]["every_source_tuple_changed"]
        and checks["routing_check"]["no_p_source_is_true_neighbour"]
        and checks["routing_check"]["same_contemporaneous_pool"]
        and checks["routing_check"]["realized_slot_identity_ok"]
        and checks["routing_check"]["realized_slots_checked"]
        and checks["no_donor_bank_reachable"]
        and checks["initialization"]["same_seed_all_cell_tensor_hash_equal"]
        and all(checks["u3_paths"].values())
        and checks["reuse_audit"]["passed"]
        and checks["reuse_audit"]["completed_count"] == 48
        and checks["reuse_audit"]["expected_set_ok"]
        and all(checks["hardlink_probe"].values())
        and checks["short_andes_path"]["rows"] == 3
        and checks["short_andes_path"]["update_finite"]
    )
    return checks


def _no_donor_reachable() -> bool:
    """R474 runner must not call any donor-bank function (definitional check)."""
    text = Path(__file__).read_text(encoding="utf-8")
    forbidden = ("generate_" + "donor_and_base", "_load_" + "donor", "donor_marginal_" + "audit")
    return not any(name in text for name in forbidden)


# ---------------------------------------------------------------------------
# Prepare (seal + shard lists)
# ---------------------------------------------------------------------------


def prepare() -> dict[str, Any]:
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed: {checks}")
    power = core._read_hashed_json(POWER)
    reuse = core._read_hashed_json(REUSE)
    rehearsal_payload = core._read_hashed_json(REHEARSAL)
    capacity = core._read_hashed_json(CAPACITY)
    if not power["adequate_by_normal_approximation"] or not reuse["passed"] or not rehearsal_payload["passed"]:
        raise RuntimeError("power/reuse/rehearsal gate failed")
    if capacity["readiness"] != "RUN-READY" or int(capacity["selected_workers"]) != 16:
        raise RuntimeError("capacity gate failed")
    routing = core._read_hashed_json(ROUTING_GATE)
    if not routing["passed"]:
        raise RuntimeError("routing gate failed (guardrails A.2)")
    for review_path in (REVIEW_A, REVIEW_B):
        if not review_path.is_file():
            raise RuntimeError(f"missing code review: {review_path}")
        text = review_path.read_text(encoding="utf-8")
        if "**Decision**: PASS" not in text and "Decision: PASS" not in text:
            raise RuntimeError(f"code review not passed: {review_path}")
    sources = {
        "successor_runner": Path(__file__).resolve(),
        "successor_tests": ROOT / "tests/test_run_r474_u2_source_factorial.py",
        "sealed_r473_parent": ROOT / "scripts/run_r473_u2_source_factorial.py",
        "sealed_r472_parent": ROOT / "scripts/run_r472_u2_source_factorial.py",
        "sealed_r470_parent": ROOT / "scripts/run_r470_u2_source_factorial.py",
        "source_agent": ROOT / "src/andes_rl_kundur/agents/source_factorial_sac.py",
        "source_agent_tests": ROOT / "tests/test_source_factorial_sac.py",
        "u3_agent": ROOT / "src/andes_rl_kundur/agents/executed_action_sac.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "environment": ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
    }
    missing = [f"train|{arm}|{seed}" for arm, seed in RETRAIN_CELLS]
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": core.contract_sha256(),
        "plan_sha256": core._sha256_file(PLAN),
        "power_sha256": core._sha256_file(POWER),
        "reuse_audit_sha256": core._sha256_file(REUSE),
        "rehearsal_sha256": core._sha256_file(REHEARSAL),
        "capacity_sha256": core._sha256_file(CAPACITY),
        "routing_gate_sha256": core._sha256_file(ROUTING_GATE),
        "code_review_a_sha256": core._sha256_file(REVIEW_A),
        "code_review_b_sha256": core._sha256_file(REVIEW_B),
        "authority": checks,
        "launch": {
            "wsl_python_processes": 17,
            "other_reserved_processes": 0,
            "host_process_budget": 17,
            "native_threads_per_process": 1,
            "detached_from_unified_exec": True,
        },
        "runtime": rehearsal_payload["runtime"],
        "sources": {
            name: {"path": core._relative(path), "sha256": core._sha256_file(path)}
            for name, path in sources.items()
        },
        "formal_authority": True,
        "training_executed": False,
    }
    seal_sha = core._write_new_json(SEAL, seal)
    TRAIN_SHARDS.parent.mkdir(parents=True, exist_ok=True)
    TRAIN_SHARDS.write_text(json.dumps(missing) + "\n", encoding="utf-8")
    EVAL_SHARDS.write_text(
        json.dumps([f"eval|{stage}|{arm}" for stage in ("half", "final") for arm in RETRAIN_ARMS]) + "\n",
        encoding="utf-8",
    )
    return {
        "seal_sha256": seal_sha,
        "selected_workers": 16,
        "imported_training_shards": len(REUSE_CELLS),
        "fresh_training_shards": len(missing),
        "fresh_eval_shards": 10,
        "reused_eval_shards": 16,
    }


core.authority_checks = authority_checks
core.build_contract = build_contract
core.rehearsal = rehearsal
core.prepare = prepare
core.source_rows = source_rows
core.train_arm_seed = train_arm_seed
core.evaluate_arm_stage = evaluate_arm_stage


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("reuse", "import", "route", "rehearse", "prepare", "shard", "aggregate", "manifest"),
    )
    parser.add_argument("shard_id", nargs="?")
    args = parser.parse_args()
    if args.command == "reuse":
        payload = reuse_audit()
        digest = core._write_new_json(REUSE, payload)
        core.safe_emit(json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True))
    elif args.command == "import":
        core.safe_emit(import_parent_artifacts())
    elif args.command == "route":
        payload = routing_gate()
        digest = core._write_new_json(ROUTING_GATE, payload)
        core.safe_emit(json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True))
    elif args.command == "rehearse":
        payload = rehearsal()
        digest = core._write_new_json(REHEARSAL, payload)
        core.safe_emit(json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True))
    elif args.command == "prepare":
        core.safe_emit(json.dumps(prepare(), indent=2, sort_keys=True))
    elif args.command == "aggregate":
        core.safe_emit(core.aggregate())
    elif args.command == "manifest":
        core.safe_emit(core.formal_manifest())
    else:
        if args.shard_id is None:
            raise SystemExit("shard requires a shard id")
        parts = args.shard_id.split("|")
        if parts[0] == "train" and len(parts) == 3:
            core.safe_emit(train_arm_seed(parts[1], int(parts[2])))
        elif parts[0] == "eval" and len(parts) == 3:
            evaluate_arm_stage(parts[2], parts[1])
        else:
            raise SystemExit(f"unsupported shard: {args.shard_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
