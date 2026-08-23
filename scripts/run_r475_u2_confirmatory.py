"""R475 U2 confirmatory successor: row-permuted same-time placebo, all-fresh 2x2.

Owner decision A after R474 abort (external deep review 2026-08-23): the P
source is the pre-registered row permutation rho(i)=(i+1) mod 4 of the
authentic same-time N neighbour 4-tuples, P[i,0:3]=joint[i,0:3],
P[i,3:7]=joint[(i+1)%4,3:7] (guardrails A.1/A.2 per-slot pool equality).
The confirmatory factorial is all-fresh 8 arms (an_cn, an_cp, ap_cn, ap_cp x
r0/r1) x seeds 401..406 = 48 training shards; zero reuse of R473/R474
training or eval artifacts (no batch mixing). The aggregate computes
profile-paired log(P/N) main effects per seed, tests the materiality null
H0: effect <= log(1.10) directly by full 2^6 sign-flip enumeration with Holm
over actor/critic, and demotes bootstrap to descriptive sensitivity.
Classification separates design/execution/integrity/dynamics/effect fields.
Wording boundary: total algorithm effect of authentic neighbour source vs
pre-registered same-time row-permuted placebo; never pure semantic value.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import math
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
    "_r475_r470_core", ROOT / "scripts/run_r470_u2_source_factorial.py"
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load isolated R470 execution core")
core = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = core
_spec.loader.exec_module(core)

ROUND_ID = "R475"
PLAN = ROOT / "memory/rounds/R475/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
POWER = ROOT / "memory/rounds/R475/power_analysis.json"
CAPACITY = ROOT / "memory/rounds/R473/capacity_evidence.json"
BASE_AUDIT = ROOT / "memory/rounds/R475/base_audit.json"
REHEARSAL = ROOT / "memory/rounds/R475/rehearsal.json"
SEAL = ROOT / "memory/rounds/R475/formal_seal.json"
OUT = ROOT / "results/research_loop/r475_u2_confirmatory"
R473_OUT = ROOT / "results/research_loop/r473_u2_source_factorial"
R473_MANIFEST = R473_OUT / "formal_manifest.json"
TRAIN_SHARDS = ROOT / "tmp/andes/r475_train_shards.json"
EVAL_SHARDS = ROOT / "tmp/andes/r475_eval_shards.json"
ROUTING_GATE = ROOT / "memory/rounds/R475/routing_gate.json"
REVIEW_A = ROOT / "memory/rounds/R475/code_review_a.json"
REVIEW_B = ROOT / "memory/rounds/R475/code_review_b.json"

# All-fresh confirmatory 2x2: actor/critic source in {N,P}, reward in {0,1}.
RETRAIN_ARMS = tuple(
    f"{base}_{reward}"
    for base in ("an_cn", "an_cp", "ap_cn", "ap_cp")
    for reward in ("r0", "r1")
)
# No reuse: the 0-source cells stay out of the confirmatory analysis.
REUSE_ARMS: tuple[str, ...] = ()

RETRAIN_CELLS = tuple(
    (arm, seed) for arm in RETRAIN_ARMS for seed in core.TRAINING_SEEDS
)
REUSE_CELLS: tuple[tuple[str, int], ...] = ()

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
        "same-time row permutation rho(i)=(i+1) mod 4 of the authentic N "
        "neighbour 4-tuples (guardrails A.1/A.2); no exogenous donor bank"
    )
    # The inherited R470 donor-bank fields describe the aborted exogenous
    # donor design; R475 has no donor bank and no (i+2) pivot, so they are
    # removed from the sealed record rather than carried as stale text.
    for stale in ("placebo_left_node", "placebo_right_node", "donor_episodes", "donor_permutation"):
        inherited.pop(stale, None)
    inherited["retrain_cells"] = [f"{arm}|{seed}" for arm, seed in RETRAIN_CELLS]
    inherited["reused_cells"] = [f"{arm}|{seed}" for arm, seed in REUSE_CELLS]
    contract["r475"] = inherited
    return contract


def authority_checks() -> dict[str, bool]:
    plan = PLAN.read_text(encoding="utf-8")
    line = LINE.read_text(encoding="utf-8")
    return {
        "active_plan": "round: R475" in plan and "state: active" in plan,
        "active_line": "line_id: yang-md-decoupling-marl" in line and "status: active" in line,
        "contract_closed": len(core.ARMS) == 18 and len(core.TRAINING_SEEDS) == 6
        and len(RETRAIN_CELLS) == 48 and len(REUSE_CELLS) == 0,
        "output_absence": not OUT.exists(),
    }


# ---------------------------------------------------------------------------
# Same-time P semantics (the single scientific change vs R474)
# ---------------------------------------------------------------------------


# Kundur 4-ring neighbour wiring (env COMM_ADJ, andes_vsg_env_v4.py:107):
#   {0:[1,3], 1:[0,2], 2:[1,3], 3:[2,0]}  -- the neighbour ORDER is asymmetric
#   (device 0 lists [i+1, i-1]; devices 1..3 list [i-1, i+1]).
# Observed slot layout per device: col 3 = d_omega of COMM_ADJ[i][0],
# col 4 = d_omega of COMM_ADJ[i][1], col 5 = omega_dot of COMM_ADJ[i][0],
# col 6 = omega_dot of COMM_ADJ[i][1].
COMM_ADJ: dict[int, tuple[int, int]] = {0: (1, 3), 1: (0, 2), 2: (1, 3), 3: (2, 0)}

# Pre-registered main direction (external redesign section 2): P is the row
# permutation rho(i) = (i+1) mod 4 of the authentic N neighbour 4-tuples.
# P[i,0:3] = joint[i,0:3]; P[i,3:7] = joint[(i+1)%4,3:7]. Because rho is a
# row permutation of the N block, every column 3..6 keeps its value multiset
# exactly, the full ordered 2-source tuple multiset is preserved, every
# recipient receives a tuple different from its own N tuple, and the two P
# sources of recipient i are the neighbours of i+1 = {i, i+2} -- the
# recipient itself (not a true neighbour) and the diagonal device (not a
# true neighbour) -- so no P source is a true neighbour of its recipient.
# The reverse direction rho(i)=(i-1) mod 4 is registered as sensitivity and
# is NOT executed in this round.
ROW_PERM = (1, 2, 3, 0)
REVERSE_ROW_PERM = (3, 0, 1, 2)


def source_rows(joint_obs: np.ndarray, source: str) -> np.ndarray:
    """Build actor/critic input rows for one source from the SAME-TIME joint.

    N: authentic rows unchanged. 0: neighbour slots zeroed. P: the authentic
    N neighbour 4-tuples row-permuted by rho(i)=(i+1) mod 4 -- P[i,0:3] keeps
    the recipient's own features and P[i,3:7] = N[(i+1)%4,3:7]. This is a
    permutation of the authentic same-time source pool: per-slot value pools
    and the full tuple multiset are preserved exactly (guardrails A.1/A.2),
    every recipient's source tuple changes, and no P source is a true
    neighbour of its recipient. All three sources read the same
    contemporaneous state pool; no donor bank exists.
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
    rows[:, 3:7] = current[list(ROW_PERM), 3:7]
    return rows


def _source_ids(joint: np.ndarray, source: str) -> tuple[tuple[int, int], ...]:
    """Return the ordered 2-source device-ID tuple of every recipient row."""
    count = core.base.AGENT_COUNT
    if source == "N":
        return tuple(COMM_ADJ[i] for i in range(count))
    if source == "P":
        return tuple(COMM_ADJ[(i + 1) % count] for i in range(count))
    raise ValueError(f"source-id mapping undefined for {source}")


def routing_check(joints: np.ndarray, *, realized_slots: bool = False) -> dict[str, Any]:
    """Falsification-first guardrails A.2 check on real/synthetic joints.

    Source-ID structure proof (integer IDs, not float equality):
      - rho is a permutation of 0..3 and fixed-point-free;
      - for every i, neither P source is a true neighbour of i;
      - per-slot source-ID multisets of N and P are equal;
      - full ordered 2-source tuple multisets of N and P are equal;
      - every P tuple differs from the recipient's N tuple;
      - the two P sources of every recipient differ (no slot collapse).
    Actual-output value gate on the REAL function outputs (n_rows/p_rows),
    never rebuilt from an expected formula: per column 3..6 the sorted value
    pools are equal; the row 4-tuple multiset is equal; own columns 0:2 are
    unchanged. With ``realized_slots=True`` (real ANDES joints only)
    additionally verify slot content equals the source device's feature for
    N (COMM_ADJ wiring) and P (row-permuted wiring). Any false flag -> caller
    must treat as DESIGN-INVALID; no training starts.
    """
    values = np.asarray(joints, dtype=np.float32)
    if values.ndim == 4 and values.shape[2:] == (core.base.AGENT_COUNT, core.base.OBS_DIM):
        values = values.reshape(-1, core.base.AGENT_COUNT, core.base.OBS_DIM)
    if values.ndim != 3 or values.shape[1:] != (core.base.AGENT_COUNT, core.base.OBS_DIM):
        raise ValueError(f"unexpected joint tensor shape: {values.shape}")
    count = core.base.AGENT_COUNT
    pool_equal = True
    tuple_multiset_equal = True
    tuple_changed = True
    non_neighbour = True
    no_slot_collapse = True
    actual_no_collapse = True
    own_unchanged = True
    declared_wiring_match = True
    realized_ok = True
    comparisons = 0
    hashes: dict[str, str] = {}
    for t in range(values.shape[0]):
        joint = values[t]
        n_rows = source_rows(joint, "N")
        p_rows = source_rows(joint, "P")
        n_ids = _source_ids(joint, "N")
        p_ids = _source_ids(joint, "P")
        # Structure: permutation, fixed-point-free, non-neighbour, changed.
        for i in range(count):
            tuple_changed = tuple_changed and (p_ids[i] != n_ids[i])
            for p_source in p_ids[i]:
                non_neighbour = non_neighbour and (p_source not in COMM_ADJ[i])
        no_slot_collapse = no_slot_collapse and all(
            p_ids[i][0] != p_ids[i][1] for i in range(count)
        )
        # Structure: per-slot and full-tuple multisets over source IDs.
        for col in (0, 1):
            n_col = sorted(n_ids[i][col] for i in range(count))
            p_col = sorted(p_ids[i][col] for i in range(count))
            pool_equal = pool_equal and (n_col == p_col)
        tuple_multiset_equal = tuple_multiset_equal and (
            sorted(n_ids) == sorted(p_ids)
        )
        # Actual-output value gate on the real rows (per column 3..6).
        for col in range(3, 7):
            pool_equal = pool_equal and bool(
                np.array_equal(np.sort(n_rows[:, col]), np.sort(p_rows[:, col]))
            )
        # Row 4-tuple value multiset on the actual outputs.
        tuple_multiset_equal = tuple_multiset_equal and (
            sorted(map(tuple, n_rows[:, 3:7].tolist()))
            == sorted(map(tuple, p_rows[:, 3:7].tolist()))
        )
        own_unchanged = own_unchanged and bool(
            np.array_equal(n_rows[:, :3], p_rows[:, :3])
        )
        # Implementation drift gate: the actual P rows must equal the
        # declared row-permuted wiring (catches fixed-point or otherwise
        # drifted implementations even when pools/multisets are preserved).
        declared_wiring_match = declared_wiring_match and bool(
            np.array_equal(p_rows[:, 3:7], joint[list(ROW_PERM), 3:7])
        )
        # Every recipient's ACTUAL P tuple must differ from its ACTUAL N
        # tuple (catches fixed-point implementations at the value level).
        for i in range(count):
            tuple_changed = tuple_changed and bool(
                not np.array_equal(p_rows[i, 3:7], n_rows[i, 3:7])
            )
        # Actual-row slot-collapse gate: the two d_omega slots (3,4) and the
        # two omega_dot slots (5,6) of every P row must not be identical
        # (the aborted diagonal-copy design forces slot3==slot4 and
        # slot5==slot6, a detectable rank collapse; the row permutation
        # never does). The authoritative proof is the source-ID structure
        # check (no_within_tuple_source_collapse); this value-level check is
        # an additional signal that can false-FAIL on degenerate joints, so
        # it is reported separately and combined via AND only for the
        # value-gate summary.
        for i in range(count):
            actual_no_collapse = actual_no_collapse and bool(
                p_rows[i, 3] != p_rows[i, 4] or p_rows[i, 5] != p_rows[i, 6]
            )
        if realized_slots:
            for i in range(count):
                adj0, adj1 = COMM_ADJ[i]
                p_i = (i + 1) % count
                realized_ok = realized_ok and (
                    n_rows[i, 3] == joint[adj0, 1]
                    and n_rows[i, 4] == joint[adj1, 1]
                    and n_rows[i, 5] == joint[adj0, 2]
                    and n_rows[i, 6] == joint[adj1, 2]
                    and p_rows[i, 3] == joint[COMM_ADJ[p_i][0], 1]
                    and p_rows[i, 4] == joint[COMM_ADJ[p_i][1], 1]
                    and p_rows[i, 5] == joint[COMM_ADJ[p_i][0], 2]
                    and p_rows[i, 6] == joint[COMM_ADJ[p_i][1], 2]
                )
        key = f"{t}|pool"
        hashes[key] = core.hashlib.sha256(
            json.dumps({"n_ids": n_ids, "p_ids": p_ids}, sort_keys=True).encode("utf-8")
        ).hexdigest()
        comparisons += 1
    # same_contemporaneous_pool derived from the data flow, not hardcoded:
    # every source row must be a pure function of THIS joint (N == joint,
    # P == joint with the neighbour block row-permuted, own columns intact,
    # 0 == joint with neighbour slots zeroed), so no source can read any
    # other time step or an exogenous bank. Checked on the first joint (the
    # identity holds by construction for all).
    first_joint = values[0]
    first_n = source_rows(first_joint, "N")
    first_p = source_rows(first_joint, "P")
    first_zero = source_rows(first_joint, "0")
    expected_p = first_joint.copy()
    expected_p[:, 3:7] = first_joint[list(ROW_PERM), 3:7]
    same_pool = bool(
        np.array_equal(first_n, first_joint)
        and np.array_equal(first_p, expected_p)
        and np.array_equal(first_zero[:, :3], first_joint[:, :3])
        and np.all(first_zero[:, 3:7] == 0.0)
    )
    return {
        "pooled_hash_index_sha256": core.hashlib.sha256(
            json.dumps(hashes, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "per_slot_value_pools_equal": bool(pool_equal),
        "tuple_multiset_equal": bool(tuple_multiset_equal),
        "every_source_tuple_changed": bool(tuple_changed),
        "no_p_source_is_true_neighbour": bool(non_neighbour),
        "no_within_tuple_source_collapse": bool(no_slot_collapse),
        "actual_row_value_collapse_absent": bool(actual_no_collapse),
        "own_columns_unchanged": bool(own_unchanged),
        "actual_p_rows_match_declared_row_perm": bool(declared_wiring_match),
        "row_perm_is_permutation": sorted(ROW_PERM) == list(range(count)),
        "row_perm_fixed_point_free": all(ROW_PERM[i] != i for i in range(count)),
        "same_contemporaneous_pool": bool(same_pool),
        "realized_slot_identity_ok": bool(realized_ok),
        "realized_slots_checked": bool(realized_slots),
        "pool_equality_scope": "per column 3..6 on actual source_rows outputs; row permutation of the authentic N neighbour 4-tuples",
        "joints_checked": int(values.shape[0]),
        "comparisons": comparisons,
    }


def routing_gate() -> dict[str, Any]:
    """Standalone pre-train gate (guardrails A.2): wide synthetic sweep plus
    the real three-step ANDES joints recorded in rehearsal."""
    if OUT.exists() or SEAL.exists():
        raise FileExistsError("routing gate must precede R475 formal artifacts")
    rng = np.random.default_rng(20260823)
    synthetic = rng.normal(size=(64, 4, 7)).astype(np.float32)
    synthetic[:, :, 0] = 0.0  # slot 0 unused by neighbour semantics
    wide = routing_check(synthetic)
    rehearsal_payload = core._read_hashed_json(REHEARSAL)
    real = rehearsal_payload.get("routing_check", {})
    required_flags = (
        "per_slot_value_pools_equal",
        "tuple_multiset_equal",
        "every_source_tuple_changed",
        "no_p_source_is_true_neighbour",
        "no_within_tuple_source_collapse",
        "actual_row_value_collapse_absent",
        "own_columns_unchanged",
        "actual_p_rows_match_declared_row_perm",
        "row_perm_is_permutation",
        "row_perm_fixed_point_free",
        "same_contemporaneous_pool",
    )
    passed = bool(
        all(wide[flag] for flag in required_flags)
        and all(real.get(flag) for flag in required_flags)
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
        "failure_semantics": "any false flag = DESIGN-INVALID; no training starts",
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
            "p_source_semantics": "same-time row permutation rho(i)=(i+1) mod 4 of the authentic N neighbour 4-tuples (guardrails A.1/A.2); no exogenous donor bank",
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
# Base import (6 R473 base states by hardlink; NO training/eval reuse)
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


def base_audit() -> dict[str, Any]:
    """Audit the six R473 base states against the R473 formal manifest.

    Initialization parity only: R475 retrains every confirmatory cell fresh,
    so the bases are the sole reused artifact and enter by NTFS hardlink with
    R473-manifest hash identity. No training/eval shard of R473/R474 is read.
    """
    if OUT.exists() or REHEARSAL.exists() or SEAL.exists():
        raise FileExistsError("base audit must precede R475 network/formal artifacts")
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
    expected = set(core.TRAINING_SEEDS)
    if set(base_rows) != expected:
        errors.append("base seed set drift")
    if len(RETRAIN_CELLS) != 48 or REUSE_CELLS:
        errors.append("cell split drift (expect 48 fresh, 0 reused)")
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "constructed_networks_before_audit": False,
        "source_round": "R473",
        "source_manifest_sha256": core._sha256_file(R473_MANIFEST),
        "bases": {str(key): value for key, value in base_rows.items()},
        "base_count": len(base_rows),
        "retrain_cell_count": len(RETRAIN_CELLS),
        "reuse_cell_count": len(REUSE_CELLS),
        "errors": errors,
        "passed": not errors and len(base_rows) == 6,
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
    audit = core._read_hashed_json(BASE_AUDIT)
    if not audit["passed"] or int(audit["base_count"]) != 6:
        raise RuntimeError("base audit is not valid")
    if OUT.exists():
        raise FileExistsError(f"R475 output exists: {OUT}")
    entries: list[dict[str, Any]] = []
    for seed in core.TRAINING_SEEDS:
        # base state + donor manifest (base identity record) + their SHA-256
        # sidecars (every later _read_hashed_json requires the sidecar);
        # trajectory npz files of the old donor bank are NOT imported (no
        # donor code path). No training/eval shard is imported.
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
            src_side = Path(f"{source}.sha256")
            tgt_side = Path(f"{target}.sha256")
            if not src_side.is_file():
                raise RuntimeError(f"missing R473 donor sidecar {name}.sha256 seed{seed}")
            if tgt_side.exists():
                raise FileExistsError(f"import sidecar target exists: {tgt_side}")
            os.link(src_side, tgt_side)
            entries.append({
                "source": core._relative(src_side),
                "target": core._relative(tgt_side),
                "sha256": core._sha256_file(tgt_side),
                "bytes": tgt_side.stat().st_size,
                "same_inode": True,
            })
    return core._write_new_json(
        OUT / "import_provenance.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "source_round": "R473",
            "base_audit_sha256": core._sha256_file(BASE_AUDIT),
            "hardlink_entries": entries,
            "entry_count": len(entries),
            "logical_bytes": sum(row["bytes"] for row in entries),
            "additional_data_bytes": 0,
            "all_same_inode": all(row["same_inode"] for row in entries),
            "imported_training_shards": [],
            "imported_eval_stages": [],
            "imported_base_states": [f"seed{seed}" for seed in core.TRAINING_SEEDS],
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
            and power["targets_materiality"]
            and int(power["selected_seeds"]) == len(core.TRAINING_SEEDS)
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
        "source": "R471 sealed terminal predicate; R475 has no donor regeneration",
    }
    base = core._read_hashed_json(BASE_AUDIT)
    checks["base_audit"] = {
        "passed": bool(base["passed"]),
        "base_count": int(base["base_count"]),
        "retrain_cell_count": int(base["retrain_cell_count"]),
        "reuse_cell_count": int(base["reuse_cell_count"]),
    }
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
        source = Path(folder) / "source.bin"
        target = Path(folder) / "target.bin"
        source.write_bytes(b"r475-hardlink-probe")
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
    reward_sha = core.hashlib.sha256(reward_source).hexdigest()
    base_manifest0 = core._read_hashed_json(R473_OUT / "donors" / f"seed{core.TRAINING_SEEDS[0]}" / "manifest.json")
    checks["reward"] = {
        "function_sha256": reward_sha,
        "matches_sealed_r473_reward_hash": bool(
            base_manifest0["reward_function_sha256"] == reward_sha
        ),
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
        and checks["routing_check_synthetic"]["per_slot_value_pools_equal"]
        and checks["routing_check_synthetic"]["tuple_multiset_equal"]
        and checks["routing_check_synthetic"]["every_source_tuple_changed"]
        and checks["routing_check_synthetic"]["no_p_source_is_true_neighbour"]
        and checks["routing_check_synthetic"]["no_within_tuple_source_collapse"]
        and checks["routing_check_synthetic"]["actual_row_value_collapse_absent"]
        and checks["routing_check_synthetic"]["own_columns_unchanged"]
        and checks["routing_check_synthetic"]["actual_p_rows_match_declared_row_perm"]
        and checks["routing_check_synthetic"]["row_perm_is_permutation"]
        and checks["routing_check_synthetic"]["row_perm_fixed_point_free"]
        and checks["routing_check"]["per_slot_value_pools_equal"]
        and checks["routing_check"]["tuple_multiset_equal"]
        and checks["routing_check"]["every_source_tuple_changed"]
        and checks["routing_check"]["no_p_source_is_true_neighbour"]
        and checks["routing_check"]["no_within_tuple_source_collapse"]
        and checks["routing_check"]["actual_row_value_collapse_absent"]
        and checks["routing_check"]["own_columns_unchanged"]
        and checks["routing_check"]["actual_p_rows_match_declared_row_perm"]
        and checks["routing_check"]["same_contemporaneous_pool"]
        and checks["routing_check"]["realized_slot_identity_ok"]
        and checks["routing_check"]["realized_slots_checked"]
        and checks["no_donor_bank_reachable"]
        and checks["initialization"]["same_seed_all_cell_tensor_hash_equal"]
        and all(checks["u3_paths"].values())
        and all(checks["objective_semantics_probe"].values())
        and checks["reward"]["matches_sealed_r473_reward_hash"]
        and checks["terminal_truth_table"]["normal_horizon_done_accepted"]
        and checks["terminal_truth_table"]["premature_done_rejected"]
        and checks["terminal_truth_table"]["tds_failure_rejected"]
        and checks["base_audit"]["passed"]
        and checks["base_audit"]["base_count"] == 6
        and checks["base_audit"]["retrain_cell_count"] == 48
        and checks["base_audit"]["reuse_cell_count"] == 0
        and all(checks["hardlink_probe"].values())
        and checks["short_andes_path"]["rows"] == 3
        and checks["short_andes_path"]["update_finite"]
    )
    return checks


def _no_donor_reachable() -> bool:
    """R475 runner must not call any donor-bank function (definitional check)."""
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
    base = core._read_hashed_json(BASE_AUDIT)
    rehearsal_payload = core._read_hashed_json(REHEARSAL)
    capacity = core._read_hashed_json(CAPACITY)
    if not power["targets_materiality"] or not base["passed"] or not rehearsal_payload["passed"]:
        raise RuntimeError("power/base/rehearsal gate failed")
    if capacity["readiness"] != "RUN-READY" or int(capacity["selected_workers"]) != 16:
        raise RuntimeError("capacity gate failed")
    routing = core._read_hashed_json(ROUTING_GATE)
    if not routing["passed"]:
        raise RuntimeError("routing gate failed (guardrails A.2)")
    for review_path in (REVIEW_A, REVIEW_B):
        if not review_path.is_file():
            raise RuntimeError(f"missing code review: {review_path}")
        review = core._read_hashed_json(review_path)
        if review.get("decision") != "PASS":
            raise RuntimeError(f"code review not passed: {review_path}")
        if int(review.get("open_p0_count", -1)) != 0 or int(review.get("open_p1_count", -1)) != 0:
            raise RuntimeError(f"code review has open findings: {review_path}")
    sources = {
        "successor_runner": Path(__file__).resolve(),
        "successor_tests": ROOT / "tests/test_run_r475_u2_confirmatory.py",
        "sealed_r474_parent": ROOT / "scripts/run_r474_u2_source_factorial.py",
        "sealed_r473_parent": ROOT / "scripts/run_r473_u2_source_factorial.py",
        "sealed_r472_parent": ROOT / "scripts/run_r472_u2_source_factorial.py",
        "sealed_r470_parent": ROOT / "scripts/run_r470_u2_source_factorial.py",
        "r451_structural_parent": ROOT / "scripts/run_r451_m3_message_factorial.py",
        "r438_parent": ROOT / "scripts/run_r438_sac_message_channels.py",
        "r431_parent": ROOT / "scripts/run_r431_sac_slew.py",
        "r430_parent": ROOT / "scripts/run_r430_adapted_sac_successor.py",
        "r429_parent": ROOT / "scripts/run_r429_adapted_sac.py",
        "r428_parent": ROOT / "scripts/run_r428_c1_sac.py",
        "source_agent": ROOT / "src/andes_rl_kundur/agents/source_factorial_sac.py",
        "source_agent_tests": ROOT / "tests/test_source_factorial_sac.py",
        "u3_agent": ROOT / "src/andes_rl_kundur/agents/executed_action_sac.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "environment": ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "base_env": ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
        "v4_config": ROOT / "src/andes_rl_kundur/env/andes/v4_config.py",
    }
    missing = [f"train|{arm}|{seed}" for arm, seed in RETRAIN_CELLS]
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": core.contract_sha256(),
        "plan_sha256": core._sha256_file(PLAN),
        "power_sha256": core._sha256_file(POWER),
        "base_audit_sha256": core._sha256_file(BASE_AUDIT),
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
        "fresh_eval_shards": 16,
        "reused_eval_shards": 0,
    }


# ---------------------------------------------------------------------------
# Aggregate: profile-paired main effects + direct materiality Holm
# ---------------------------------------------------------------------------

# Symbols inherited from the R470 core module (frozen protocol definitions).
PRIMARY = core.PRIMARY
SECONDARY = core.SECONDARY
MATERIALITY_LOG = core.MATERIALITY_LOG


def _profile_endpoint(arm: str, seed: int, stage: str, metric: str, profile_id: str) -> float:
    """Endpoint of one arm/seed/stage on ONE evaluation profile (not merged)."""
    payload = core._read_hashed_json(
        OUT / "eval" / stage / arm / f"seed{seed}" / f"{profile_id}.json"
    )
    if any(not row["completed"] or row["tds_failed"] for row in payload["records"]):
        raise RuntimeError(f"invalid eval record {stage} {arm} seed{seed} profile {profile_id}")
    contract = build_contract()
    return core.parent._arm_endpoints(payload["records"], contract)[metric]

def _paired_main_effects(stage: str, metric: str) -> dict[str, list[float]]:
    """Per-seed profile-paired log(P/N) main effects (equal-weight).

    actor:  D_s = mean over critic in {N,P}, reward in {0,1}, profile of
            log(L(ap_*)/L(an_*)) computed on the SAME profile.
    critic: D_s = mean over actor in {N,P}, reward in {0,1}, profile of
            log(L(*_cp)/L(*_cn)) computed on the SAME profile.
    """
    contract = build_contract()
    profiles = [p for p in contract["profiles"] if p["split"] == "evaluation"]
    profile_ids = [str(p["profile_id"]) for p in profiles]
    effects: dict[str, list[float]] = {"actor": [], "critic": []}
    for seed in core.TRAINING_SEEDS:
        actor_diffs: list[float] = []
        critic_diffs: list[float] = []
        for reward in ("r0", "r1"):
            for profile_id in profile_ids:
                # actor effect: N-side arm an_*_<reward>, P-side ap_*_<reward>
                # with critic factor matched cell-by-cell (cn pairs with cn,
                # cp pairs with cp).
                for critic in ("cn", "cp"):
                    n_arm = f"an_{critic}_{reward}"
                    p_arm = f"ap_{critic}_{reward}"
                    n_val = _profile_endpoint(n_arm, seed, stage, metric, profile_id)
                    p_val = _profile_endpoint(p_arm, seed, stage, metric, profile_id)
                    actor_diffs.append(math.log(p_val / n_val))
                # critic effect: N-side arm a*_cn_<reward>, P-side a*_cp_<reward>
                # with actor factor matched cell-by-cell.
                for actor in ("an", "ap"):
                    n_arm = f"{actor}_cn_{reward}"
                    p_arm = f"{actor}_cp_{reward}"
                    n_val = _profile_endpoint(n_arm, seed, stage, metric, profile_id)
                    p_val = _profile_endpoint(p_arm, seed, stage, metric, profile_id)
                    critic_diffs.append(math.log(p_val / n_val))
        effects["actor"].append(float(np.mean(actor_diffs)))
        effects["critic"].append(float(np.mean(critic_diffs)))
    return effects


def _signflip_p_one_sided(values: list[float], null: float) -> float:
    """Full 2^n sign-flip enumeration at the given null; one-sided p."""
    array = np.asarray(values, dtype=float) - float(null)
    observed = float(np.mean(array))
    permutations = np.asarray(
        [np.mean(array * np.asarray(signs)) for signs in itertools.product((-1.0, 1.0), repeat=len(array))]
    )
    return float(np.sum(permutations >= observed) / len(permutations))


def _apply_holm_two(rows: dict[str, dict[str, Any]]) -> None:
    ordered = sorted(rows, key=lambda key: rows[key]["materiality_p_one_sided"])
    for rank, key in enumerate(ordered):
        threshold = 0.05 / (len(ordered) - rank)
        previous_pass = all(rows[prior].get("holm_reject", False) for prior in ordered[:rank])
        rows[key]["holm_threshold"] = threshold
        rows[key]["holm_reject"] = bool(previous_pass and rows[key]["materiality_p_one_sided"] <= threshold)


def _exact_bootstrap_ci(values: list[float]) -> tuple[float, float]:
    """Exact 6^6 ordered resample enumeration; percentile CI (descriptive)."""
    array = np.asarray(values, dtype=float)
    n = len(array)
    means = []
    for index in itertools.product(range(n), repeat=n):
        means.append(float(np.mean(array[list(index)])))
    means = np.asarray(means)
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def aggregate() -> str:
    core._assert_wsl_scratch()
    core.load_seal()
    integrity_errors: list[str] = []
    base_hashes: dict[int, set[str]] = {seed: set() for seed in core.TRAINING_SEEDS}
    reward_hashes: dict[bool, set[str]] = {False: set(), True: set()}
    stability_rows: dict[str, Any] = {}
    for arm in RETRAIN_ARMS:
        stability_rows[arm] = []
        for seed in core.TRAINING_SEEDS:
            manifest = core._read_hashed_json(OUT / "train" / arm / f"seed{seed}" / "manifest.json")
            if not manifest["valid"] or int(manifest["interaction_steps"]) != 43_200:
                integrity_errors.append(f"invalid training {arm} seed{seed}")
            base_hashes[seed].add(str(manifest["base_state_sha256"]))
            reward_hashes[bool(core.arm_factors(arm)["reward_access"])].add(str(manifest["reward_function_sha256"]))
            stability_rows[arm].append(manifest["stability"])
    for seed, hashes in base_hashes.items():
        if len(hashes) != 1:
            integrity_errors.append(f"base state mismatch seed{seed}")
    if any(len(hashes) != 1 for hashes in reward_hashes.values()) or reward_hashes[False] != reward_hashes[True]:
        integrity_errors.append("reward implementation hash mismatch")

    stage_effects: dict[str, Any] = {}
    for stage in ("half", "final"):
        stage_effects[stage] = {
            metric: _paired_main_effects(stage, metric) for metric in (PRIMARY, SECONDARY)
        }

    final_primary = stage_effects["final"][PRIMARY]
    primary_tests: dict[str, dict[str, Any]] = {}
    for factor in ("actor", "critic"):
        values = final_primary[factor]
        p = _signflip_p_one_sided(values, MATERIALITY_LOG)
        ci_low, ci_high = _exact_bootstrap_ci(values)
        primary_tests[factor] = {
            "paired_log_effects": values,
            "mean_log_effect": float(np.mean(values)),
            "geometric_improvement": float(math.exp(float(np.mean(values))) - 1.0),
            "materiality_log": MATERIALITY_LOG,
            "materiality_p_one_sided": p,
            "bootstrap_ci95_descriptive": [ci_low, ci_high],
            "holm_reject": False,
            "direction_count_positive": int(sum(v > 0 for v in values)),
            "seed_min": float(np.min(values)),
            "seed_median": float(np.median(values)),
            "leave_one_out_means": [
                float(np.mean([value for j, value in enumerate(values) if j != i]))
                for i in range(len(values))
            ],
        }
    _apply_holm_two(primary_tests)
    for row in primary_tests.values():
        row["material_effect"] = "ESTABLISHED" if row["holm_reject"] else "NOT_ESTABLISHED"

    direction_flips = {}
    for factor in ("actor", "critic"):
        half = float(np.mean(stage_effects["half"][PRIMARY][factor]))
        final = float(np.mean(stage_effects["final"][PRIMARY][factor]))
        direction_flips[factor] = {"half_mean": half, "final_mean": final, "flipped": bool(np.sign(half) != np.sign(final))}
    no_plateau = [
        f"{arm}|{seed}|{kind}"
        for arm in RETRAIN_ARMS
        for seed, row in zip(core.TRAINING_SEEDS, stability_rows[arm], strict=True)
        for kind in ("critic_loss", "actor_loss")
        if not row[kind]["stable"]
    ]

    design_valid = routing_gate_passed()
    execution_complete = not integrity_errors and not missing_shards()
    integrity_pass = not integrity_errors
    dynamics_stable = not any(row["flipped"] for row in direction_flips.values()) and not no_plateau

    if not design_valid:
        verdict = "DESIGN-INVALID"
    elif not execution_complete:
        verdict = "EXECUTION-INCOMPLETE"
    elif not integrity_pass:
        verdict = "INTEGRITY-INVALID"
    elif any(row["material_effect"] == "ESTABLISHED" for row in primary_tests.values()):
        verdict = "MATERIAL-EFFECT-ESTABLISHED"
    else:
        verdict = "MATERIAL-EFFECT-NOT-ESTABLISHED"
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "contract_sha256": core.contract_sha256(),
        "seal_sha256": core._sha256_file(SEAL),
        "integrity": {
            "valid": integrity_pass,
            "errors": integrity_errors,
            "six_seed_base_hashes": {str(seed): sorted(values) for seed, values in base_hashes.items()},
            "reward_hashes": {str(key): sorted(values) for key, values in reward_hashes.items()},
        },
        "main_effects": stage_effects,
        "primary_materiality_tests": primary_tests,
        "optimization": {
            "direction_flips": direction_flips,
            "nonplateau_rows": no_plateau,
            "unresolved": not dynamics_stable,
        },
        "classification": {
            "design": "VALID" if design_valid else "INVALID",
            "execution": "COMPLETE" if execution_complete else "INCOMPLETE",
            "integrity": "PASS" if integrity_pass else "FAIL",
            "training_dynamics": "STABLE" if dynamics_stable else "UNSTABLE",
            "material_effect": ("ESTABLISHED" if any(row["material_effect"] == "ESTABLISHED" for row in primary_tests.values())
                                else "NOT_ESTABLISHED"),
            "verdict": verdict,
            "scope": "six seeds; frozen R470 learner/bank/projector only; all-fresh 2x2; row-permuted P",
            "universal_intrinsic_claim_authorized": False,
        },
        "created_utc": datetime.now(UTC).isoformat(),
    }
    return core._write_new_json(OUT / "formal_analysis.json", payload)


def routing_gate_passed() -> bool:
    payload = core._read_hashed_json(ROUTING_GATE)
    return bool(payload.get("passed"))


def missing_shards() -> list[str]:
    missing = []
    for arm in RETRAIN_ARMS:
        for seed in core.TRAINING_SEEDS:
            manifest = OUT / "train" / arm / f"seed{seed}" / "manifest.json"
            if not manifest.is_file():
                missing.append(f"train|{arm}|{seed}")
            for stage in ("half", "final"):
                if not (OUT / "eval" / stage / arm / f"seed{seed}").is_dir():
                    missing.append(f"eval|{stage}|{arm}|{seed}")
    return missing


core.authority_checks = authority_checks
core.build_contract = build_contract
core.rehearsal = rehearsal
core.prepare = prepare
core.source_rows = source_rows
core.train_arm_seed = train_arm_seed
core.evaluate_arm_stage = evaluate_arm_stage
core.aggregate = aggregate


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("base", "import", "route", "rehearse", "prepare", "shard", "aggregate", "manifest"),
    )
    parser.add_argument("shard_id", nargs="?")
    args = parser.parse_args()
    if args.command == "base":
        payload = base_audit()
        digest = core._write_new_json(BASE_AUDIT, payload)
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
