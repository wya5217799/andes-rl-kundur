"""R482 execution successor: corrected-card learning re-verification + all-fresh
26-seed source factorial (the final high-cost experiment of the corrected
plan; owner launch decision 2026-08-25).

Scientific execution delegates to the sealed R477/R476/R475/R470 chain. R482
owns: fresh seeds 501..526, the nine-arm roster (eight factorial arms plus the
Phase-3B RMS-penalty arm ``an_cn_r1_rms``), fresh base-state generation
(basegen replaces the R473 import), the four-test materiality aggregation and
Phase-3 trade-off pair (``andes_rl_kundur.evaluation.r482_analysis``), the
frozen power-plan artifact as the bound power evidence, and all R482 paths.

Zero carryover: no R470-R477 training or evaluation cell is reused.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from andes_rl_kundur.evaluation import source_factorial_design as sfd
from andes_rl_kundur.evaluation import r482_analysis
from andes_rl_kundur.evaluation.paper_strict_eval import compute_global_cum_rf
from andes_rl_kundur.evaluation.u2_confirmatory import (
    check_artifact_budget,
    guard_environment_builder,
    inventory_artifacts,
    recalibrate_eta,
    terminal_invalid,
    terminal_truth_table,
    validate_review_coverage,
    verify_formal_seal,
)

_spec = importlib.util.spec_from_file_location(
    "_r482_r477_base", ROOT / "scripts/run_r477_u2_confirmatory.py"
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load isolated R477 execution base")
base = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = base
_spec.loader.exec_module(base)

ROUND_ID = "R482"
PLAN = ROOT / "memory/rounds/R482/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
POWER = ROOT / "paper/yang_md_decoupling_marl/working/source_factorial_power_plan.json"
CAPACITY = ROOT / "memory/rounds/R482/capacity_evidence.json"
BASE_AUDIT = ROOT / "memory/rounds/R482/base_audit.json"
REHEARSAL = ROOT / "memory/rounds/R482/rehearsal.json"
SEAL = ROOT / "memory/rounds/R482/formal_seal.json"
OUT = ROOT / "results/research_loop/r482_u2_confirmatory"
TRAIN_SHARDS = ROOT / "tmp/andes/r482_train_shards.json"
EVAL_SHARDS = ROOT / "tmp/andes/r482_eval_shards.json"
DEV_SHARDS = ROOT / "tmp/andes/r482_dev_shards.json"
TRAIN_WAVE_SHARDS = tuple(
    ROOT / f"tmp/andes/r482_train_wave{index}_shards.json"
    for index in range(1, 16)
)
ETA_RECALIBRATION = ROOT / "tmp/andes/r482_eta_recalibration.json"
PIPELINE_INVENTORY = ROOT / "tmp/andes/r482_pipeline_inventories"
TRAIN_LOG_ROOT = ROOT / "tmp/andes/r482_train_logs"
EVAL_LOG_ROOT = ROOT / "tmp/andes/r482_eval_logs"
DEV_LOG_ROOT = ROOT / "tmp/andes/r482_dev_logs"
FORMAL_GO = ROOT / "tmp/andes/r482_formal_go.json"
OWNER_APPROVED = ROOT / "memory/rounds/R482/OWNER_APPROVED.json"
ROUTING_GATE = ROOT / "memory/rounds/R482/routing_gate.json"
REVIEW_A = ROOT / "memory/rounds/R482/code_review_a.json"
REVIEW_B = ROOT / "memory/rounds/R482/code_review_b.json"
PIPELINE = ROOT / "scripts/run_r482_detached_pipeline.sh"
RUNNER_TESTS = ROOT / "tests/test_run_r482_u2_confirmatory.py"
ANALYSIS_MODULE = ROOT / "src/andes_rl_kundur/evaluation/r482_analysis.py"
DESIGN_MODULE = ROOT / "src/andes_rl_kundur/evaluation/source_factorial_design.py"

SEEDS = tuple(range(501, 527))
DEV_SEEDS = tuple(range(601, 617))
DEV_ARMS = ("an_cn_r1", "an_cn_r1_rms")
DEV_CELLS = tuple(
    (arm, seed)
    for arm, index in ((DEV_ARMS[0], 0), (DEV_ARMS[1], 8))
    for seed in DEV_SEEDS[index : index + 8]
)
DEV_SHARD_IDS = tuple(f"dev|{arm}|{seed}" for arm, seed in DEV_CELLS)
FACTORIAL_ARMS = tuple(
    f"{actor}_{critic}_{reward}"
    for actor in ("an", "ap")
    for critic in ("cn", "cp")
    for reward in ("r0", "r1")
)
PHASE3B_ARM = "an_cn_r1_rms"
RETRAIN_ARMS = FACTORIAL_ARMS + (PHASE3B_ARM,)
REUSE_ARMS: tuple[str, ...] = ()
PHASE3B_CELLS = tuple((PHASE3B_ARM, seed) for seed in SEEDS)
FACTORIAL_CELLS = tuple(
    (arm, seed) for arm in FACTORIAL_ARMS for seed in SEEDS
)
RETRAIN_CELLS = PHASE3B_CELLS + FACTORIAL_CELLS
REUSED_CELLS: tuple[tuple[str, int], ...] = ()
TRAIN_SHARD_IDS = tuple(f"train|{arm}|{seed}" for arm, seed in RETRAIN_CELLS)
EVAL_SHARD_IDS = tuple(
    f"eval|{stage}|{arm}" for stage in ("half", "final") for arm in RETRAIN_ARMS
)
TRAIN_WAVE_IDS = tuple(
    TRAIN_SHARD_IDS[index : index + 16]
    for index in range(0, len(TRAIN_SHARD_IDS), 16)
)
PROFILES = ("canary_eval_a", "canary_eval_b", "canary_eval_c", "canary_eval_d")
PRIMARY = "disturbance_differential_energy"
MATERIALITY_LOG = math.log(1.10)
BASE_RNG_OFFSET = 200_000
LAMBDA_P = 10.0  # frozen R433 dev-lambda selection; no re-selection after results
FACTORIAL_REWARD_SHA = "085ad375c203352d72e58847ca7b01297415b214adf41196dcb7783c7adb7bd9"
ARTIFACT_BUDGET_BYTES = int(3.2 * 1024**3)


def _r482_penalized_step_rewards(
    joint_obs: np.ndarray,
    delta_m: np.ndarray,
    delta_d: np.ndarray,
    reward_access: bool,
    action: np.ndarray,
) -> np.ndarray:
    """R482-SEAM: factorial reward plus the frozen R433 action-RMS penalty.

    Single change vs the authentic-source cell: ``p_i = -mean_j(a_ij^2)`` over
    the projected executed action and ``r_i' = r_i + LAMBDA_P * p_i`` with the
    frozen coefficient 10.0. The base term is the sealed factorial reward
    (``legacy.step_rewards``).
    """
    rewards = base.base.base.core.legacy.step_rewards(
        joint_obs, delta_m, delta_d, reward_access=reward_access
    )
    executed = np.asarray(action, dtype=float)
    penalty = -np.mean(executed**2, axis=1)
    return rewards + LAMBDA_P * penalty


def _penalized_reward_sha() -> str:
    source = inspect.getsource(_r482_penalized_step_rewards).encode("utf-8")
    return hashlib.sha256(source).hexdigest()


def _factorial_reward_sha() -> str:
    source = inspect.getsource(base.base.base.core.legacy.step_rewards).encode("utf-8")
    return hashlib.sha256(source).hexdigest()


def _rewrite_chain() -> None:
    for name, value in {
        "ROUND_ID": ROUND_ID,
        "PLAN": PLAN,
        "LINE": LINE,
        "POWER": POWER,
        "CAPACITY": CAPACITY,
        "BASE_AUDIT": BASE_AUDIT,
        "REHEARSAL": REHEARSAL,
        "SEAL": SEAL,
        "OUT": OUT,
        "TRAIN_SHARDS": TRAIN_SHARDS,
        "EVAL_SHARDS": EVAL_SHARDS,
        "ROUTING_GATE": ROUTING_GATE,
        "REVIEW_A": REVIEW_A,
        "REVIEW_B": REVIEW_B,
        "RETRAIN_ARMS": RETRAIN_ARMS,
        "REUSE_ARMS": REUSE_ARMS,
        "RETRAIN_CELLS": RETRAIN_CELLS,
        "REUSE_CELLS": REUSED_CELLS,
        "TRAINING_SEEDS": SEEDS,
    }.items():
        setattr(base, name, value)
        setattr(base.base, name, value)
        setattr(base.base.base, name, value)
        if hasattr(base.base.base.core, name):
            setattr(base.base.base.core, name, value)
    setattr(base.base.base.core, "TRAINING_SEEDS", SEEDS)


_rewrite_chain()

# Capture the sealed parent entry before the compatibility rebinding below.
# Calling ``base.train_arm_seed`` afterwards would recurse into this module.
_PARENT_TRAIN_ARM_SEED = base.train_arm_seed


def arm_factors(arm_id: str) -> dict[str, Any]:
    if arm_id == PHASE3B_ARM:
        return {
            "actor_source": "N",
            "critic_source": "N",
            "reward_access": True,
            "penalty": "r433-action-rms",
        }
    if arm_id not in FACTORIAL_ARMS:
        raise ValueError(f"unknown arm: {arm_id}")
    actor, critic, reward = arm_id.split("_")
    return {
        "actor_source": actor[1:].upper(),
        "critic_source": critic[1:].upper(),
        "reward_access": reward == "r1",
    }


def build_contract() -> dict[str, Any]:
    parent_builder = getattr(base.base, "_r470_build_contract", None)
    if parent_builder is None:
        parent_builder = base.base.base._r470_build_contract
    contract = parent_builder()
    inherited = contract.pop("r470")
    inherited["successor_of"] = "R477"
    inherited["p_source_semantics"] = (
        "same-time row permutation rho(i)=(i+1) mod 4 of the authentic N "
        "neighbour 4-tuples (guardrails A.1/A.2); no exogenous donor bank"
    )
    for stale in (
        "placebo_left_node",
        "placebo_right_node",
        "donor_episodes",
        "donor_permutation",
    ):
        inherited.pop(stale, None)
    inherited["retrain_cells"] = list(TRAIN_SHARD_IDS)
    inherited["reused_cells"] = []
    inherited["fresh_seed_roster"] = list(SEEDS)
    inherited["carryover"] = "zero old training or evaluation cells"
    inherited["power_plan_sha256"] = base.base.base.core._sha256_file(POWER)
    inherited["phase3b"] = {
        "arm": PHASE3B_ARM,
        "factors": {"actor_source": "N", "critic_source": "N", "reward_access": True},
        "reward_change": "frozen R433 normalized action-RMS penalty seam",
        "penalty_form": "r_i' = r_i + lambda_p * p_i, p_i = -mean_j(a_ij^2) over projected executed action",
        "lambda_p": LAMBDA_P,
        "coefficient_frozen": True,
        "base_reward": "factorial legacy.step_rewards (unchanged)",
    }
    contract["r482"] = inherited
    return contract


def authority_checks() -> dict[str, bool]:
    plan = PLAN.read_text(encoding="utf-8")
    line = LINE.read_text(encoding="utf-8")
    return {
        "active_plan": "round: R482" in plan and "state: active" in plan,
        "active_line": (
            "line_id: yang-md-decoupling-marl" in line and "status: active" in line
        ),
        "contract_closed": (
            len(base.base.base.core.ARMS) == 18
            and len(SEEDS) == 26
            and len(RETRAIN_CELLS) == 234
            and len(REUSED_CELLS) == 0
        ),
        "output_absence": not OUT.exists(),
    }


def _reviewed_files() -> tuple[Path, ...]:
    # source_factorial_design.py is deliberately NOT in the review set: its
    # pre-existing CRLF working copy would break the byte-level review-coverage
    # check (git stores LF), and it is already double-bound by the power
    # artifact's embedded planner sha256 and the seal source map.
    return (
        Path(__file__).resolve(),
        RUNNER_TESTS,
        ANALYSIS_MODULE,
        ROOT / "scripts/run_r477_u2_confirmatory.py",
        ROOT / "scripts/run_r476_u2_confirmatory.py",
        ROOT / "src/andes_rl_kundur/evaluation/u2_confirmatory.py",
        ROOT / "tests/test_u2_confirmatory.py",
        ROOT / "scripts/soft_spot_shard_driver.py",
        ROOT / "tests/test_soft_spot_shard_driver.py",
        ROOT / "memory/tools/detached_pipeline_lint.py",
        ROOT / "tests/test_detached_pipeline_lint.py",
        PIPELINE,
    )


def _bound_files() -> dict[str, Path]:
    return {
        "plan_sha256": PLAN,
        "power_sha256": POWER,
        "base_audit_sha256": BASE_AUDIT,
        "routing_gate_sha256": ROUTING_GATE,
        "rehearsal_sha256": REHEARSAL,
        "capacity_sha256": CAPACITY,
        "code_review_a_sha256": REVIEW_A,
        "code_review_b_sha256": REVIEW_B,
    }


def load_seal() -> dict[str, Any]:
    return verify_formal_seal(
        repo_root=ROOT,
        seal_path=SEAL,
        round_id=ROUND_ID,
        contract_sha256=base.base.base.core.contract_sha256(),
        bound_files=_bound_files(),
        review_paths=(REVIEW_A, REVIEW_B),
        reviewed_files=_reviewed_files(),
        expected_shards={
            "train": TRAIN_SHARD_IDS,
            **{
                f"train_wave_{index}": TRAIN_WAVE_IDS[index - 1]
                for index in range(1, 16)
            },
            "eval": EVAL_SHARD_IDS,
            "dev": DEV_SHARD_IDS,
        },
    )


def basegen() -> str:
    """Generate the 26 fresh base states (one per seed) under the corrected card.

    Runs BEFORE seal (the base audit, rehearsal, and prepare consume the
    generated artifacts). No donor bank exists; each base state is the
    seed-initialized learner network export shared by all nine arm slots of
    that seed. RNG seed = 200,000 + seed (registered).
    """
    base.base.base.core._assert_wsl_scratch()
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed: {checks}")
    if OUT.exists():
        raise FileExistsError(f"R482 output exists: {OUT}")
    if _factorial_reward_sha() != FACTORIAL_REWARD_SHA:
        raise RuntimeError(
            "factorial reward source drifted from the sealed R470-R477 hash"
        )
    entries: list[dict[str, Any]] = []
    for seed in (*SEEDS, *DEV_SEEDS):
        out_dir = OUT / "donors" / f"seed{seed}"
        out_dir.mkdir(parents=True)
        base.base.base.core._seed_all(BASE_RNG_OFFSET + seed)
        prototype = base.base.base.core.FactorialWrapper(
            FACTORIAL_ARMS[0]
        )
        base_path = out_dir / "base_state.pt"
        base_sha = base.base.base.core._write_new_torch(
            base_path,
            {
                "schema_version": 1,
                "kind": "r470-common-base-state",
                "training_seed": seed,
                "agents": prototype.export_states(),
            },
        )
        digest = base.base.base.core._write_new_json(
            out_dir / "manifest.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "training_seed": seed,
                "base_rng_seed": BASE_RNG_OFFSET + seed,
                "rng_set_before_environment": True,
                "base_state_path": base.base.base.core._relative(base_path),
                "base_state_sha256": base_sha,
                "reward_function_sha256": FACTORIAL_REWARD_SHA,
                "matched_arm_slots": list(RETRAIN_ARMS),
                "contract_sha256": base.base.base.core.contract_sha256(),
                "created_utc": datetime.now(UTC).isoformat(),
            },
        )
        entries.append(
            {
                "seed": seed,
                "base_state_path": base.base.base.core._relative(base_path),
                "base_state_sha256": base_sha,
                "manifest_sha256": digest,
            }
        )
    formal_entries = [row for row in entries if int(row["seed"]) in SEEDS]
    development_entries = [row for row in entries if int(row["seed"]) in DEV_SEEDS]
    formal_digest = base.base.base.core._write_new_json(
        OUT / "formal_basegen_provenance.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "base_rng_offset": BASE_RNG_OFFSET,
            "base_count": len(formal_entries),
            "entries": formal_entries,
            "donor_bank_absent": True,
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )
    development_digest = base.base.base.core._write_new_json(
        OUT / "development_inputs" / "basegen_provenance.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "base_rng_offset": BASE_RNG_OFFSET,
            "base_count": len(development_entries),
            "entries": development_entries,
            "formal_bank": False,
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )
    return json.dumps(
        {
            "formal_basegen_provenance_sha256": formal_digest,
            "development_basegen_provenance_sha256": development_digest,
        },
        sort_keys=True,
    )


def base_audit() -> dict[str, Any]:
    base.base.base.core._assert_wsl_scratch()
    if REHEARSAL.exists() or SEAL.exists():
        raise FileExistsError("base audit must precede R482 rehearsal/formal artifacts")
    errors: list[str] = []
    rows: dict[int, dict[str, Any]] = {}
    for seed in (*SEEDS, *DEV_SEEDS):
        manifest_path = OUT / "donors" / f"seed{seed}" / "manifest.json"
        try:
            manifest = base.base.base.core._read_hashed_json(manifest_path)
        except RuntimeError as error:
            errors.append(str(error))
            continue
        base_path = OUT / "donors" / f"seed{seed}" / "base_state.pt"
        if base.base.base.core._sha256_file(base_path) != manifest.get("base_state_sha256"):
            errors.append(f"base hash drift seed{seed}")
        if manifest.get("reward_function_sha256") != FACTORIAL_REWARD_SHA:
            errors.append(f"reward identity drift seed{seed}")
        if int(manifest.get("base_rng_seed", -1)) != BASE_RNG_OFFSET + seed:
            errors.append(f"base rng drift seed{seed}")
        rows[seed] = {
            "path": manifest.get("base_state_path"),
            "sha256": manifest.get("base_state_sha256"),
        }
    if set(rows) != set((*SEEDS, *DEV_SEEDS)):
        errors.append("base seed set drift")
    if len(RETRAIN_CELLS) != 234 or REUSED_CELLS:
        errors.append("cell split drift (expect 234 fresh, 0 reused)")
    if len(DEV_CELLS) != 16:
        errors.append("dev cell split drift (expect 16 dev cells)")
    formal_count = len([seed for seed in rows if seed in SEEDS])
    dev_count = len([seed for seed in rows if seed in DEV_SEEDS])
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "constructed_networks_before_audit": False,
        "fresh_generation": True,
        "bases": {str(key): value for key, value in rows.items()},
        "base_count": formal_count,
        "dev_base_count": dev_count,
        "retrain_cell_count": len(RETRAIN_CELLS),
        "reuse_cell_count": len(REUSED_CELLS),
        "dev_cell_count": len(DEV_CELLS),
        "errors": errors,
        "passed": (
            not errors
            and formal_count == 26
            and dev_count == 16
        ),
    }


def routing_gate() -> dict[str, Any]:
    """Run the inherited routing proof after R482 base generation, before training."""
    if SEAL.exists() or any((OUT / phase).exists() for phase in ("train", "eval", "dev")):
        raise FileExistsError("routing gate must precede R482 execution artifacts")
    rng = np.random.default_rng(20260823)
    synthetic = rng.normal(size=(64, 4, 7)).astype(np.float32)
    synthetic[:, :, 0] = 0.0
    wide = base.base.base.routing_check(synthetic)
    rehearsal_payload = base.base.base.core._read_hashed_json(REHEARSAL)
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
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "synthetic_wide_sweep": wide,
        "real_three_step_from_rehearsal": real,
        "passed": passed,
        "failure_semantics": "any false flag = DESIGN-INVALID; no training starts",
    }


def _penalty_semantics_probe() -> dict[str, Any]:
    """R424 target-semantics gate for the R482 penalty seam (closed-form)."""
    probe = np.asarray([[0.25, -0.5], [0.0, 0.0], [1.0, 1.0], [-0.75, 0.25]], dtype=float)
    joint = np.zeros((4, 7), dtype=np.float32)
    delta_m = np.zeros(4, dtype=float)
    delta_d = np.zeros(4, dtype=float)
    base_rewards = base.base.base.core.legacy.step_rewards(
        joint, delta_m, delta_d, reward_access=True
    )
    penalized = _r482_penalized_step_rewards(joint, delta_m, delta_d, True, probe)
    expected_penalty = LAMBDA_P * (-np.mean(probe**2, axis=1))
    return {
        "penalty_equals_closed_form": bool(
            np.allclose(penalized - base_rewards, expected_penalty, atol=1e-9)
        ),
        "zero_action_penalty_zero": bool(
            np.allclose(penalized[1] - base_rewards[1], 0.0, atol=1e-9)
        ),
        "penalty_nonpositive": bool(np.all(expected_penalty <= 0.0)),
        "penalty_monotone_in_magnitude": bool(
            expected_penalty[2] < expected_penalty[0] < 0.0
            and expected_penalty[3] < expected_penalty[0]
        ),
        "lambda_p": LAMBDA_P,
    }


def rehearsal() -> dict[str, Any]:
    """Same-pre-attempt-path rehearsal adapted to the frozen n=26 design.

    Owns the real-ANDES three-step routing check, learner initialization
    parity, the U3 executed-action path probe, the objective-semantics probe
    (R424 gate), and the R482 reward identity + penalty-semantics probes.
    """
    core = base.base.base.core
    core._assert_wsl_scratch()
    if not POWER.exists() or not Path(f"{POWER}.sha256").exists():
        raise RuntimeError("power plan must exist before rehearsal")
    power = core._read_hashed_json(POWER)
    base_record = core._read_hashed_json(BASE_AUDIT)
    checks: dict[str, Any] = {
        "authority": authority_checks(),
        "runtime": core._installed_runtime(),
        "power_plan": {
            "n_star": int(power.get("n_star", -1)) == 26,
            "fresh_seed_roster": list(
                power.get("estimand", {}).get("fresh_seed_roster", [])
            ) == list(SEEDS),
            "profile_roster": list(
                power.get("estimand", {}).get("profile_roster", [])
            ) == list(PROFILES),
            "prospective_only": bool(power.get("prospective_only")),
        },
        "output_absence": not (OUT / "train").exists() and not (OUT / "eval").exists(),
        "contract_sha256": core.contract_sha256(),
    }
    rng = np.random.default_rng(20260825)
    synthetic = rng.normal(size=(16, 4, 7)).astype(np.float32)
    synthetic[:, :, 0] = 0.0
    checks["routing_check_synthetic"] = base.base.base.routing_check(synthetic)
    checks["terminal_truth_table"] = terminal_truth_table(terminal_invalid)
    checks["base_audit"] = {
        "passed": bool(base_record["passed"]),
        "base_count": int(base_record["base_count"]),
        "dev_base_count": int(base_record.get("dev_base_count", -1)),
        "retrain_cell_count": int(base_record["retrain_cell_count"]),
        "reuse_cell_count": int(base_record["reuse_cell_count"]),
    }
    checks["reward"] = {
        "factorial_sha_matches_frozen": _factorial_reward_sha() == FACTORIAL_REWARD_SHA,
        "penalized_sha": _penalized_reward_sha(),
        "penalty_semantics": _penalty_semantics_probe(),
    }
    checks["power_precedes_network"] = bool(
        power.get("prospective_only") and int(power.get("n_star", -1)) == 26
    )
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
        source = Path(folder) / "source.bin"
        target = Path(folder) / "target.bin"
        source.write_bytes(b"r482-hardlink-probe")
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
        "current_critic_executed": bool(
            torch.equal(paths["critic_current_action_input"], batch["executed_actions"])
        ),
        "target_critic_projected": bool(
            torch.equal(paths["critic_target_action_input"], paths["target_projected_action"])
        ),
        "actor_critic_projected": bool(
            torch.equal(paths["actor_critic_action_input"], paths["actor_projected_action"])
        ),
        "actor_critic_views_distinct": bool(
            not torch.equal(paths["actor_state"][:, :7], paths["critic_state"][:, :7])
        ),
    }
    checks["objective_semantics_probe"] = core.objective_semantics_probe()

    contract = build_contract()
    profile = next(p for p in contract["profiles"] if p["split"] == "development")
    scenario = profile["scenarios"][0]
    with _terminal_guarded_environment():
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
                    probe_member.store_source_transition(
                        aobs, cobs, previous, raw, executed, -0.1, aobs, cobs, False
                    )
                    previous = executed
            for _ in range(3):
                joint = core.r431._joint_obs(observation)
                joints.append(joint.reshape(4, core.base.OBS_DIM))
                actor_rows = base.base.base.source_rows(joint, "N")
                critic_rows = base.base.base.source_rows(joint, "P")
                raw, executed = wrapper.act(actor_rows, previous_joint, deterministic=False)
                observation, _reward, done, info = env.step(
                    {i: executed[i] for i in range(4)}
                )
                next_joint = core.r431._joint_obs(observation)
                joints.append(next_joint.reshape(4, core.base.OBS_DIM))
                rewards = core.legacy.step_rewards(
                    joint,
                    np.asarray(info["delta_M"]),
                    np.asarray(info["delta_D"]),
                    reward_access=False,
                )
                penalized = _r482_penalized_step_rewards(
                    joint,
                    np.asarray(info["delta_M"]),
                    np.asarray(info["delta_D"]),
                    True,
                    executed,
                )
                wrapper.store(
                    actor_rows, critic_rows, previous_joint, raw, executed, rewards,
                    base.base.base.source_rows(next_joint, "N"),
                    base.base.base.source_rows(next_joint, "P"),
                    bool(done) or bool(info["tds_failed"]),
                )
                update_result = wrapper.update_all()
                previous_joint = executed
                rows_completed += 1
                if rows_completed == 1:
                    checks["penalty_on_real_actions"] = {
                        "penalty_term_nonpositive": bool(
                            np.all(penalized <= rewards + 1e-9)
                        ),
                        "penalty_applied": bool(np.any(penalized < rewards)),
                    }
        finally:
            env.close()
    checks["routing_check"] = base.base.base.routing_check(
        np.stack(joints), realized_slots=True
    )
    checks["short_andes_path"] = {
        "rows": rows_completed,
        "update_finite": bool(
            update_result is not None
            and all(np.isfinite(list(update_result.values())))
        ),
    }
    routing_synthetic = checks["routing_check_synthetic"]
    routing_real = checks["routing_check"]
    checks["passed"] = bool(
        all(checks["authority"].values())
        and checks["power_precedes_network"]
        and all(checks["power_plan"].values())
        and checks["reward"]["factorial_sha_matches_frozen"]
        and all(checks["reward"]["penalty_semantics"].values())
        and checks["base_audit"]["passed"]
        and checks["base_audit"]["base_count"] == 26
        and checks["base_audit"]["dev_base_count"] == 16
        and checks["base_audit"]["retrain_cell_count"] == 234
        and checks["base_audit"]["reuse_cell_count"] == 0
        and checks["terminal_truth_table"]["normal_horizon_done_accepted"]
        and checks["terminal_truth_table"]["premature_done_rejected"]
        and checks["terminal_truth_table"]["tds_failure_rejected"]
        and routing_synthetic["per_slot_value_pools_equal"]
        and routing_synthetic["tuple_multiset_equal"]
        and routing_synthetic["every_source_tuple_changed"]
        and routing_synthetic["no_p_source_is_true_neighbour"]
        and routing_synthetic["no_within_tuple_source_collapse"]
        and routing_synthetic["actual_row_value_collapse_absent"]
        and routing_synthetic["own_columns_unchanged"]
        and routing_synthetic["actual_p_rows_match_declared_row_perm"]
        and routing_real["per_slot_value_pools_equal"]
        and routing_real["tuple_multiset_equal"]
        and routing_real["every_source_tuple_changed"]
        and routing_real["no_p_source_is_true_neighbour"]
        and routing_real["no_within_tuple_source_collapse"]
        and routing_real["actual_row_value_collapse_absent"]
        and routing_real["own_columns_unchanged"]
        and routing_real["actual_p_rows_match_declared_row_perm"]
        and routing_real["same_contemporaneous_pool"]
        and routing_real["realized_slot_identity_ok"]
        and routing_real["realized_slots_checked"]
        and checks["initialization"]["same_seed_all_cell_tensor_hash_equal"]
        and all(checks["u3_paths"].values())
        and all(checks["objective_semantics_probe"].values())
        and checks["penalty_on_real_actions"]["penalty_term_nonpositive"]
        and checks["penalty_on_real_actions"]["penalty_applied"]
        and all(checks["hardlink_probe"].values())
        and checks["short_andes_path"]["rows"] == 3
        and checks["short_andes_path"]["update_finite"]
    )
    return checks


def prepare() -> dict[str, Any]:
    if SEAL.exists():
        raise FileExistsError(f"R482 formal seal already exists: {SEAL}")
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed: {checks}")
    power = base.base.base.core._read_hashed_json(POWER)
    base_record = base.base.base.core._read_hashed_json(BASE_AUDIT)
    routing = base.base.base.core._read_hashed_json(ROUTING_GATE)
    rehearsal_payload = base.base.base.core._read_hashed_json(REHEARSAL)
    capacity = base.base.base.core._read_hashed_json(CAPACITY)
    if (
        int(power.get("n_star", -1)) != 26
        or list(power.get("estimand", {}).get("fresh_seed_roster", [])) != list(SEEDS)
    ):
        raise RuntimeError("power plan does not match the frozen 26-seed design")
    if not base_record.get("passed") or not routing.get("passed"):
        raise RuntimeError("base/routing gate failed")
    if not rehearsal_payload.get("passed"):
        raise RuntimeError("rehearsal gate failed")
    if (
        capacity.get("readiness") != "RUN-READY"
        or int(capacity.get("selected_workers", -1)) != 16
        or int(capacity.get("whole_host_python_process_budget", -1)) != 17
    ):
        raise RuntimeError("capacity gate failed")
    review = validate_review_coverage(
        (REVIEW_A, REVIEW_B),
        repo_root=ROOT,
        reviewed_files=_reviewed_files(),
    )
    for path, values in [
        (TRAIN_SHARDS, TRAIN_SHARD_IDS),
        *zip(TRAIN_WAVE_SHARDS, TRAIN_WAVE_IDS, strict=True),
        (EVAL_SHARDS, EVAL_SHARD_IDS),
        (DEV_SHARDS, DEV_SHARD_IDS),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if json.loads(path.read_text(encoding="utf-8")) != list(values):
                raise RuntimeError(f"existing shard list drift: {path}")
            continue
        path.write_text(json.dumps(list(values)) + "\n", encoding="utf-8")
    sources = {
        "successor_runner": Path(__file__).resolve(),
        "successor_tests": RUNNER_TESTS,
        "r482_analysis": ANALYSIS_MODULE,
        "source_factorial_design": DESIGN_MODULE,
        "sealed_r477_parent": ROOT / "scripts/run_r477_u2_confirmatory.py",
        "sealed_r476_parent": ROOT / "scripts/run_r476_u2_confirmatory.py",
        "sealed_r475_parent": ROOT / "scripts/run_r475_u2_confirmatory.py",
        "sealed_r470_parent": ROOT / "scripts/run_r470_u2_source_factorial.py",
        "r451_structural_parent": ROOT / "scripts/run_r451_m3_message_factorial.py",
        "r438_parent": ROOT / "scripts/run_r438_sac_message_channels.py",
        "r431_parent": ROOT / "scripts/run_r431_sac_slew.py",
        "r433_parent": ROOT / "scripts/run_r433_sac_stress_penalty.py",
        "source_agent": ROOT / "src/andes_rl_kundur/agents/source_factorial_sac.py",
        "source_agent_tests": ROOT / "tests/test_source_factorial_sac.py",
        "u3_agent": ROOT / "src/andes_rl_kundur/agents/executed_action_sac.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "pipeline_lint": ROOT / "memory/tools/detached_pipeline_lint.py",
        "pipeline_lint_tests": ROOT / "tests/test_detached_pipeline_lint.py",
        "driver_tests": ROOT / "tests/test_soft_spot_shard_driver.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "detached_pipeline": PIPELINE,
        "environment": ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "base_env": ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
        "v4_config": ROOT / "src/andes_rl_kundur/env/andes/v4_config.py",
    }
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": base.base.base.core.contract_sha256(),
        **{
            field: base.base.base.core._sha256_file(path)
            for field, path in _bound_files().items()
        },
        "authority": checks,
        "launch": {
            "wsl_python_processes": 17,
            "other_reserved_processes": 0,
            "host_process_budget": 17,
            "native_threads_per_process": 1,
            "detached_from_unified_exec": True,
        },
        "runtime": rehearsal_payload["runtime"],
        "reviewed_commit": review.reviewed_commit,
        "reviewer_ids": list(review.reviewer_ids),
        "reviewed_files": review.reviewed_files,
        "sources": {
            name: {
                "path": base.base.base.core._relative(path),
                "sha256": base.base.base.core._sha256_file(path),
            }
            for name, path in sources.items()
        },
        "shard_lists": {
            "train": {
                "path": base.base.base.core._relative(TRAIN_SHARDS),
                "sha256": base.base.base.core._sha256_file(TRAIN_SHARDS),
            },
            **{
                f"train_wave_{index}": {
                    "path": base.base.base.core._relative(path),
                    "sha256": base.base.base.core._sha256_file(path),
                }
                for index, path in enumerate(TRAIN_WAVE_SHARDS, start=1)
            },
            "eval": {
                "path": base.base.base.core._relative(EVAL_SHARDS),
                "sha256": base.base.base.core._sha256_file(EVAL_SHARDS),
            },
            "dev": {
                "path": base.base.base.core._relative(DEV_SHARDS),
                "sha256": base.base.base.core._sha256_file(DEV_SHARDS),
            },
        },
        "reuse": {
            "source_round": None,
            "reused_cells": [],
        },
        "formal_authority": True,
        "training_executed": False,
    }
    seal_sha = base.base.base.core._write_new_json(SEAL, seal)
    load_seal()
    return {
        "seal_sha256": seal_sha,
        "selected_workers": 16,
        "fresh_training_shards": len(TRAIN_SHARD_IDS),
        "reused_training_shards": 0,
        "fresh_eval_shards": len(EVAL_SHARD_IDS),
        "reviewed_file_count": len(review.reviewed_files),
        "reviewed_commit": review.reviewed_commit,
    }


@contextmanager
def _terminal_guarded_environment():
    """Bind the rehearsed terminal predicate to every formal environment step."""
    core = base.base.base.core
    guarded = guard_environment_builder(
        core.r431._build_env,
        steps=int(build_contract()["steps"]),
        predicate=terminal_invalid,
    )
    original = core.r431._build_env
    core.r431._build_env = guarded
    try:
        yield
    finally:
        core.r431._build_env = original


def _train_arm_seed_phase3b(seed: int) -> str:
    with _terminal_guarded_environment():
        return _train_arm_seed_phase3b_body(seed)


def _train_arm_seed_phase3b_body(seed: int) -> str:
    """Train one RMS-penalty cell (R482 penalty seam; single change vs an_cn_r1)."""
    base.base.base.core._assert_wsl_scratch()
    load_seal()
    run_dir = OUT / "train" / PHASE3B_ARM / f"seed{seed}"
    if run_dir.exists():
        raise FileExistsError(f"training output exists: {run_dir}")
    run_dir.mkdir(parents=True)
    contract = build_contract()
    factors = arm_factors(PHASE3B_ARM)
    base_manifest = base.base.base.core._read_hashed_json(
        OUT / "donors" / f"seed{seed}" / "manifest.json"
    )
    base.base.base.core._seed_all(seed)
    development = [p for p in contract["profiles"] if p["split"] == "development"]
    envs = {str(p["profile_id"]): base.base.base.core.r431._build_env(p) for p in development}
    wrapper = base.base.base.core.FactorialWrapper(PHASE3B_ARM)
    base_path, base_sha = base.base.base.core._load_base(wrapper, seed)
    scenarios = {
        str(s["scenario_id"]): (profile, s)
        for profile in development
        for s in profile["scenarios"]
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
                joint = base.base.base.core.r431._joint_obs(observation)
                actor_rows = base.base.base.source_rows(joint, "N")
                critic_rows = base.base.base.source_rows(joint, "N")
                raw, executed = wrapper.act(actor_rows, previous, deterministic=False)
                if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(executed)):
                    invalid_reason = "nonfinite action"
                    break
                observation, _reward, done, info = env.step(
                    {i: executed[i] for i in range(4)}
                )
                executed_steps += 1
                next_joint = base.base.base.core.r431._joint_obs(observation)
                next_actor_rows = base.base.base.source_rows(next_joint, "N")
                next_critic_rows = base.base.base.source_rows(next_joint, "N")
                terminal = bool(done) or bool(info["tds_failed"])
                rewards = _r482_penalized_step_rewards(
                    joint,
                    np.asarray(info["delta_M"], dtype=float),
                    np.asarray(info["delta_D"], dtype=float),
                    True,
                    executed,
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
                    half_sha = wrapper.save(
                        run_dir / "half.pt", stage="half", base_sha256=base_sha
                    )
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
    valid = (
        invalid_reason is None
        and executed_steps == total_steps
        and half_sha is not None
    )
    final_sha = (
        wrapper.save(run_dir / "final.pt", stage="final", base_sha256=base_sha)
        if valid
        else None
    )
    curve_sha = base.base.base.core._write_new_npz(
        run_dir / "full_curves.npz",
        **{key: np.asarray(value, dtype=np.float64) for key, value in curves.items()},
    )
    stability = {
        key: base.base.base.core._curve_stability(np.asarray(curves[key]))
        for key in ("critic_loss", "actor_loss")
    }
    return base.base.base.core._write_new_json(
        run_dir / "manifest.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "arm_id": PHASE3B_ARM,
            "factors": factors,
            "training_seed": seed,
            "rng_set_before_environment_network_optimizer_replay": True,
            "base_state_path": base_path,
            "base_state_sha256": base_sha,
            "donor_manifest_sha256": base.base.base.core._sha256_file(
                OUT / "donors" / f"seed{seed}" / "manifest.json"
            ),
            "reward_function_sha256": _penalized_reward_sha(),
            "p_source_semantics": (
                "same-time row permutation rho(i)=(i+1) mod 4 of the authentic "
                "N neighbour 4-tuples (guardrails A.1/A.2); no exogenous donor bank"
            ),
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
            "contract_sha256": base.base.base.core.contract_sha256(),
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )


def train_arm_seed(arm_id: str, seed: int) -> str:
    if arm_id == PHASE3B_ARM:
        if seed not in SEEDS:
            raise ValueError(f"unregistered seed: {seed}")
        return _train_arm_seed_phase3b(seed)
    return _PARENT_TRAIN_ARM_SEED(arm_id, seed)


def _train_dev_cell_body(arm_id: str, seed: int) -> str:
    """Train one development diagnostic cell (burned; never formal evidence)."""
    core = base.base.base.core
    core._assert_wsl_scratch()
    load_seal()
    if (arm_id, seed) not in DEV_CELLS:
        raise ValueError(f"unregistered dev cell: {arm_id}|{seed}")
    run_dir = OUT / "dev" / arm_id / f"seed{seed}"
    if run_dir.exists():
        raise FileExistsError(f"dev output exists: {run_dir}")
    run_dir.mkdir(parents=True)
    contract = build_contract()
    factors = arm_factors(arm_id)
    penalized = arm_id == PHASE3B_ARM
    base_manifest = core._read_hashed_json(
        OUT / "donors" / f"seed{seed}" / "manifest.json"
    )
    core._seed_all(seed)
    development = [p for p in contract["profiles"] if p["split"] == "development"]
    envs = {
        str(p["profile_id"]): core.r431._build_env(p) for p in development
    }
    wrapper = core.FactorialWrapper(arm_id)
    base_path, base_sha = core._load_base(wrapper, seed)
    scenarios = {
        str(s["scenario_id"]): (profile, s)
        for profile in development
        for s in profile["scenarios"]
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
                actor_rows = base.base.base.source_rows(joint, "N")
                critic_rows = base.base.base.source_rows(joint, "N")
                raw, executed = wrapper.act(actor_rows, previous, deterministic=False)
                if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(executed)):
                    invalid_reason = "nonfinite action"
                    break
                observation, _reward, done, info = env.step(
                    {i: executed[i] for i in range(4)}
                )
                executed_steps += 1
                next_joint = core.r431._joint_obs(observation)
                next_actor_rows = base.base.base.source_rows(next_joint, "N")
                next_critic_rows = base.base.base.source_rows(next_joint, "N")
                terminal = bool(done) or bool(info["tds_failed"])
                if penalized:
                    rewards = _r482_penalized_step_rewards(
                        joint,
                        np.asarray(info["delta_M"], dtype=float),
                        np.asarray(info["delta_D"], dtype=float),
                        True,
                        executed,
                    )
                else:
                    rewards = core.legacy.step_rewards(
                        joint,
                        np.asarray(info["delta_M"], dtype=float),
                        np.asarray(info["delta_D"], dtype=float),
                        reward_access=True,
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
                    half_sha = wrapper.save(
                        run_dir / "half.pt", stage="half", base_sha256=base_sha
                    )
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
    valid = (
        invalid_reason is None
        and executed_steps == total_steps
        and half_sha is not None
    )
    final_sha = (
        wrapper.save(run_dir / "final.pt", stage="final", base_sha256=base_sha)
        if valid
        else None
    )
    curve_sha = core._write_new_npz(
        run_dir / "full_curves.npz",
        **{key: np.asarray(value, dtype=np.float64) for key, value in curves.items()},
    )
    stability = {
        key: core._curve_stability(np.asarray(curves[key]))
        for key in ("critic_loss", "actor_loss")
    }
    manifest_sha = core._write_new_json(
        run_dir / "manifest.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "development": True,
            "formal_bank": False,
            "arm_id": arm_id,
            "factors": factors,
            "training_seed": seed,
            "rng_set_before_environment_network_optimizer_replay": True,
            "base_state_path": base_path,
            "base_state_sha256": base_sha,
            "donor_manifest_sha256": core._sha256_file(
                OUT / "donors" / f"seed{seed}" / "manifest.json"
            ),
            "reward_function_sha256": (
                _penalized_reward_sha()
                if penalized
                else FACTORIAL_REWARD_SHA
            ),
            "p_source_semantics": (
                "same-time row permutation rho(i)=(i+1) mod 4 of the authentic "
                "N neighbour 4-tuples (guardrails A.1/A.2); no exogenous donor bank"
            ),
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
    if not valid:
        raise RuntimeError(
            f"development cell invalid after preserving manifest: {arm_id}|{seed}"
        )
    return manifest_sha


def development_check() -> dict[str, Any]:
    """Validate the complete burned development wave without formal pooling."""
    core = base.base.base.core
    load_seal()
    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    for arm_id, seed in DEV_CELLS:
        run_dir = OUT / "dev" / arm_id / f"seed{seed}"
        manifest_path = run_dir / "manifest.json"
        try:
            manifest = core._read_hashed_json(manifest_path)
        except Exception as exc:
            errors.append(f"{arm_id}|{seed}: manifest {exc}")
            continue
        expected = {
            "round": ROUND_ID,
            "development": True,
            "formal_bank": False,
            "arm_id": arm_id,
            "training_seed": seed,
            "valid": True,
            "interaction_steps": 43_200,
            "tds_failed_episodes": 0,
            "contract_sha256": core.contract_sha256(),
        }
        for field, value in expected.items():
            if manifest.get(field) != value:
                errors.append(
                    f"{arm_id}|{seed}: {field}={manifest.get(field)!r}, expected {value!r}"
                )
        for filename, field in (
            ("half.pt", "half_checkpoint_sha256"),
            ("final.pt", "final_checkpoint_sha256"),
            ("full_curves.npz", "full_curves_sha256"),
        ):
            artifact = run_dir / filename
            if not artifact.is_file() or core._sha256_file(artifact) != manifest.get(field):
                errors.append(f"{arm_id}|{seed}: invalid {filename}")
            sidecar = Path(f"{artifact}.sha256")
            if not sidecar.is_file():
                errors.append(f"{arm_id}|{seed}: missing {filename}.sha256")
        rows.append(
            {
                "arm_id": arm_id,
                "seed": seed,
                "manifest_sha256": core._sha256_file(manifest_path),
                "interaction_steps": manifest.get("interaction_steps"),
                "tds_failed_episodes": manifest.get("tds_failed_episodes"),
                "curve_count": manifest.get("curve_count"),
                "stability": manifest.get("stability"),
                "created_utc": manifest.get("created_utc"),
            }
        )
    if errors:
        raise RuntimeError(f"development wave incomplete/invalid: {errors[:5]}")
    manifest_set_sha256 = hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "round": ROUND_ID,
        "development_cell_count": len(DEV_CELLS),
        "formal_cells_included": 0,
        "manifest_set_sha256": manifest_set_sha256,
        "cells": rows,
        "passed": True,
    }


def write_development_report() -> str:
    """Persist the owner-visible development diagnostics exactly once."""
    core = base.base.base.core
    payload = {
        "schema_version": 1,
        **development_check(),
        "scientific_evidence": False,
        "formal_inference_included": False,
        "created_utc": datetime.now(UTC).isoformat(),
    }
    return core._write_new_json(OUT / "dev" / "diagnostic_report.json", payload)


def development_report_check() -> dict[str, Any]:
    """Verify that the visible report matches the immutable dev manifests."""
    core = base.base.base.core
    report = core._read_hashed_json(OUT / "dev" / "diagnostic_report.json")
    current = development_check()
    if (
        report.get("passed") is not True
        or report.get("scientific_evidence") is not False
        or report.get("formal_inference_included") is not False
        or report.get("manifest_set_sha256") != current["manifest_set_sha256"]
    ):
        raise RuntimeError("R482 development diagnostic report drift")
    return report


def owner_approval_check() -> dict[str, Any]:
    """Require the owner approval record immediately before any execution."""
    payload = json.loads(OWNER_APPROVED.read_text(encoding="utf-8"))
    if (
        payload.get("round") != ROUND_ID
        or payload.get("approved") is not True
        or not isinstance(payload.get("source"), str)
        or not payload["source"].strip()
    ):
        raise RuntimeError("R482 owner approval record is invalid")
    return payload


def measure_capacity() -> str:
    """Run the registered 16-worker x 8-job corrected-family confirmation."""
    core = base.base.base.core
    core._assert_wsl_scratch()
    if CAPACITY.exists() or SEAL.exists():
        raise FileExistsError("R482 capacity/seal artifact already exists")
    rehearsal_payload = core._read_hashed_json(REHEARSAL)
    if rehearsal_payload.get("passed") is not True:
        raise RuntimeError("R482 rehearsal did not pass")
    ps_lines = subprocess.run(
        ["ps", "-eo", "pid=,args="], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    other = [
        line.strip()
        for line in ps_lines
        if ("scripts/run_" in line or "soft_spot_shard_driver.py" in line)
        and "run_r482_u2_confirmatory.py capacity" not in line
    ]
    if other:
        raise RuntimeError(f"other research processes are active: {other}")
    meminfo = Path("/proc/meminfo").read_text(encoding="ascii")
    memory = {
        line.split(":", 1)[0]: int(line.split()[1]) * 1024
        for line in meminfo.splitlines()
        if ":" in line and len(line.split()) >= 2 and line.split()[1].isdigit()
    }
    anchor_path = ROOT / "memory/rounds/R438/capacity_evidence.json"
    anchor_payload = core._read_hashed_json(anchor_path)
    worker_anchor = int(anchor_payload["training_worker_rss_anchor"]["bytes"])
    memory_safe = 16 * worker_anchor + 3 * 1024**3 <= int(memory["MemTotal"])

    import run_r481_direct_md as capacity_base

    jobs = capacity_base._capacity_jobs(capacity_base.build_contract())
    if len(jobs) != 8:
        raise RuntimeError(f"capacity roster drift: expected 8 jobs, found {len(jobs)}")
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=16) as executor:
        records = list(executor.map(capacity_base._run_job, jobs))
    wall_seconds = time.perf_counter() - started
    failures = [
        record.get("failure")
        for record in records
        if record.get("completed") is not True or record.get("tds_failed") is not False
    ]
    run_ready = memory_safe and not failures and not other
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "readiness": "RUN-READY" if run_ready else "LOAD-CHECK-REVIEW",
        "selected_workers": 16 if run_ready else 0,
        "quick_confirm": {
            "requested_workers": 16,
            "jobs": len(records),
            "wall_seconds": wall_seconds,
            "all_records_valid": not failures,
            "failures": failures,
        },
        "empirical_anchor": {
            "path": core._relative(anchor_path),
            "sha256": core._sha256_file(anchor_path),
            "training_worker_rss_anchor_bytes": worker_anchor,
            "history_ladder_r452_r477": (
                "16 workers selected in every round R452-R477 on this host"
            ),
        },
        "wsl_mem_total_bytes": int(memory["MemTotal"]),
        "wsl_mem_available_bytes": int(memory["MemAvailable"]),
        "memory_safe": memory_safe,
        "whole_host_python_process_budget": 17,
        "wsl_python_processes": 17,
        "native_threads_per_process": 1,
        "other_reserved_processes": 0,
        "other_research_processes": other,
        "capacity_trace_role": "non_claim_bearing_quick_confirmation",
    }
    return core._write_new_json(CAPACITY, payload)


def formal_go_check() -> dict[str, Any]:
    """Validate the post-development owner continuation authorization."""
    report = development_report_check()
    payload = json.loads(FORMAL_GO.read_text(encoding="utf-8"))
    if (
        payload.get("round") != ROUND_ID
        or payload.get("approved") is not True
        or payload.get("development_reviewed") is not True
        or payload.get("development_report_sha256")
        != base.base.base.core._sha256_file(OUT / "dev" / "diagnostic_report.json")
        or not isinstance(payload.get("source"), str)
        or not payload["source"].strip()
    ):
        raise RuntimeError("R482 formal go-file is invalid")
    approved_utc = datetime.fromisoformat(str(payload.get("approved_utc")))
    report_utc = datetime.fromisoformat(str(report.get("created_utc")))
    if approved_utc <= report_utc:
        raise RuntimeError("R482 formal go-file predates the development report")
    return payload


def evaluate_arm_stage(arm_id: str, stage: str) -> None:
    with _terminal_guarded_environment():
        _evaluate_arm_stage_body(arm_id, stage)


def _evaluate_arm_stage_body(arm_id: str, stage: str) -> None:
    """R482 evaluation (reward-free path; the inherited R475 loop, R482 roster)."""
    base.base.base.core._assert_wsl_scratch()
    load_seal()
    if arm_id not in RETRAIN_ARMS or stage not in ("half", "final"):
        raise ValueError("unknown eval arm/stage")
    contract = build_contract()
    factors = arm_factors(arm_id)
    evaluation = [p for p in contract["profiles"] if p["split"] == "evaluation"]
    for seed in SEEDS:
        base_manifest = base.base.base.core._read_hashed_json(
            OUT / "donors" / f"seed{seed}" / "manifest.json"
        )
        checkpoint = OUT / "train" / arm_id / f"seed{seed}" / f"{stage}.pt"
        checkpoint_sha = base.base.base.core._sha256_file(checkpoint)
        wrapper = base.base.base.core.FactorialWrapper(arm_id)
        metadata = wrapper.load(checkpoint)
        if metadata["base_state_sha256"] != base_manifest["base_state_sha256"]:
            raise RuntimeError("eval checkpoint/base identity mismatch")
        envs = {
            str(p["profile_id"]): base.base.base.core.r431._build_env(p)
            for p in evaluation
        }
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
                        "vsg_buses": [
                            int(env.ss.GENCLS.bus.v[position])
                            for position in env._vsg_pos
                        ],
                        "obs_dim": int(env.OBS_DIM),
                    }
                    rows = []
                    failure = None
                    for time_index in range(int(contract["steps"])):
                        joint = base.base.base.core.r431._joint_obs(observation)
                        actor_rows = base.base.base.source_rows(joint, factors["actor_source"])
                        raw, executed = wrapper.act(actor_rows, previous, deterministic=True)
                        observation, _reward, done, info = env.step(
                            {i: executed[i] for i in range(4)}
                        )
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
                                "step_index": time_index,
                                "time": float(info["time"]),
                                "raw_action_norm": raw.astype(float).tolist(),
                                "action_norm": executed.astype(float).tolist(),
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
                            "tds_failed": failure is not None
                            or any(bool(row["tds_failed"]) for row in rows),
                            "failure": failure,
                            "reward_used_for_gate": False,
                            "training_executed": True,
                        }
                    )
                folder = OUT / "eval" / stage / arm_id / f"seed{seed}"
                base.base.base.core._write_new_json(
                    folder / f"{profile['profile_id']}.json", {"records": records}
                )
        finally:
            for env in envs.values():
                try:
                    env.close()
                except Exception:
                    pass


def _profile_endpoint(arm: str, seed: int, stage: str, profile_id: str) -> float:
    payload = base.base.base.core._read_hashed_json(
        OUT / "eval" / stage / arm / f"seed{seed}" / f"{profile_id}.json"
    )
    if any(not row["completed"] or row["tds_failed"] for row in payload["records"]):
        raise RuntimeError(
            f"invalid eval record {stage} {arm} seed{seed} profile {profile_id}"
        )
    contract = build_contract()
    return base.base.base.core.parent._arm_endpoints(payload["records"], contract)[PRIMARY]


def _profile_stress(arm: str, seed: int, stage: str, profile_id: str) -> float:
    payload = base.base.base.core._read_hashed_json(
        OUT / "eval" / stage / arm / f"seed{seed}" / f"{profile_id}.json"
    )
    per_record = []
    for record in payload["records"]:
        step_rms = [
            float(
                math.sqrt(
                    np.mean(np.asarray(row["action_norm"], dtype=float) ** 2)
                )
            )
            for row in record["steps"]
        ]
        per_record.append(float(np.mean(step_rms)))
    return float(np.mean(per_record))


def _factorial_rows(stage: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for arm in FACTORIAL_ARMS:
        factors = arm_factors(arm)
        for seed in SEEDS:
            for profile_id in PROFILES:
                rows.append(
                    {
                        "stage": stage,
                        "seed": seed,
                        "actor_source": factors["actor_source"],
                        "critic_source": factors["critic_source"],
                        "reward_access": int(factors["reward_access"]),
                        "profile": profile_id,
                        PRIMARY: _profile_endpoint(arm, seed, stage, profile_id),
                    }
                )
    return rows


def _profile_cum_rf(arm: str, seed: int, stage: str, profile_id: str) -> float:
    """Paper Sec.IV-C cumulative global frequency reward from sealed records."""
    payload = base.base.base.core._read_hashed_json(
        OUT / "eval" / stage / arm / f"seed{seed}" / f"{profile_id}.json"
    )
    per_record = []
    for record in payload["records"]:
        trace = {
            "traces": [{"freq_hz": row["freq_hz_physical"]} for row in record["steps"]],
            "tds_failed": record["tds_failed"],
        }
        per_record.append(float(compute_global_cum_rf(trace)))
    return float(np.mean(per_record))


def _phase3_inputs() -> tuple[list[float], list[float], list[float]]:
    endpoint_log_ratios: list[float] = []
    stress_diffs: list[float] = []
    cum_rf_diffs: list[float] = []
    for seed in SEEDS:
        rms_values = [
            _profile_endpoint(PHASE3B_ARM, seed, "final", profile_id)
            for profile_id in PROFILES
        ]
        sac_values = [
            _profile_endpoint("an_cn_r1", seed, "final", profile_id)
            for profile_id in PROFILES
        ]
        endpoint_log_ratios.append(
            float(
                np.mean(
                    [
                        math.log(r / s)
                        for r, s in zip(rms_values, sac_values, strict=True)
                    ]
                )
            )
        )
        rms_stress = float(
            np.mean(
                [
                    _profile_stress(PHASE3B_ARM, seed, "final", profile_id)
                    for profile_id in PROFILES
                ]
            )
        )
        sac_stress = float(
            np.mean(
                [
                    _profile_stress("an_cn_r1", seed, "final", profile_id)
                    for profile_id in PROFILES
                ]
            )
        )
        stress_diffs.append(sac_stress - rms_stress)
        rms_cum_rf = float(
            np.mean(
                [
                    _profile_cum_rf(PHASE3B_ARM, seed, "final", profile_id)
                    for profile_id in PROFILES
                ]
            )
        )
        sac_cum_rf = float(
            np.mean(
                [
                    _profile_cum_rf("an_cn_r1", seed, "final", profile_id)
                    for profile_id in PROFILES
                ]
            )
        )
        cum_rf_diffs.append(sac_cum_rf - rms_cum_rf)
    return endpoint_log_ratios, stress_diffs, cum_rf_diffs


def missing_shards() -> list[str]:
    missing: list[str] = []
    for arm, seed in RETRAIN_CELLS:
        manifest = OUT / "train" / arm / f"seed{seed}" / "manifest.json"
        if not manifest.is_file():
            missing.append(f"train|{arm}|{seed}")
    for arm in RETRAIN_ARMS:
        for seed in SEEDS:
            for stage in ("half", "final"):
                if not (OUT / "eval" / stage / arm / f"seed{seed}").is_dir():
                    missing.append(f"eval|{stage}|{arm}|{seed}")
    return missing


def aggregate() -> str:
    base.base.base.core._assert_wsl_scratch()
    load_seal()
    integrity_errors: list[str] = []
    base_hashes: dict[int, set[str]] = {seed: set() for seed in SEEDS}
    reward_hashes: dict[str, set[str]] = {"factorial": set(), "penalty": set()}
    stability_rows: dict[str, list[dict[str, Any]]] = {}
    for arm in RETRAIN_ARMS:
        stability_rows[arm] = []
        for seed in SEEDS:
            manifest = base.base.base.core._read_hashed_json(
                OUT / "train" / arm / f"seed{seed}" / "manifest.json"
            )
            if not manifest["valid"] or int(manifest["interaction_steps"]) != 43_200:
                integrity_errors.append(f"invalid training {arm} seed{seed}")
            base_hashes[seed].add(str(manifest["base_state_sha256"]))
            reward_hashes[
                "penalty" if arm == PHASE3B_ARM else "factorial"
            ].add(str(manifest["reward_function_sha256"]))
            stability_rows[arm].append(manifest["stability"])
    for seed, hashes in base_hashes.items():
        if len(hashes) != 1:
            integrity_errors.append(f"base state mismatch seed{seed}")
    if len(reward_hashes["factorial"]) != 1 or reward_hashes["factorial"] != {
        FACTORIAL_REWARD_SHA
    }:
        integrity_errors.append("factorial reward hash mismatch")
    if len(reward_hashes["penalty"]) != 1 or reward_hashes["penalty"] != {
        _penalized_reward_sha()
    }:
        integrity_errors.append("penalty reward hash mismatch")

    factorial_final = sfd.seed_effects(
        _factorial_rows("final"),
        expected_seeds=SEEDS,
        expected_profiles=PROFILES,
        stage="final",
        metric=PRIMARY,
    )
    factorial_half = sfd.seed_effects(
        _factorial_rows("half"),
        expected_seeds=SEEDS,
        expected_profiles=PROFILES,
        stage="half",
        metric=PRIMARY,
    )
    factorial_rows = r482_analysis.boundary_test_rows(factorial_final, MATERIALITY_LOG)
    endpoint_log_ratios, stress_diffs, cum_rf_diffs = _phase3_inputs()
    phase3_rows = r482_analysis.phase3_analysis(endpoint_log_ratios, stress_diffs)
    phase3_rows["cum_rf_dual_row"] = {
        "paired_diffs": cum_rf_diffs,
        "mean_diff": float(np.mean(cum_rf_diffs)),
        "one_sided_p_at_zero": (
            r482_analysis.signflip_p_one_sided_mc(
                cum_rf_diffs, 0.0,
                r482_analysis.SIGNFLIP_DRAWS, r482_analysis.SIGNFLIP_RNG_SEED,
            )[0]
        ),
        "direction": "sac_minus_rms_positive_expected (penalty regresses cum_rf)",
        "registered_role": "CLM-0430 dual-metric report line; descriptive, not part of the Holm family",
    }

    direction_flips = {}
    for name in r482_analysis.REGISTERED_EFFECTS:
        half = float(
            np.mean([factorial_half[name][seed] for seed in sorted(factorial_half[name])])
        )
        final = float(
            np.mean([factorial_final[name][seed] for seed in sorted(factorial_final[name])])
        )
        direction_flips[name] = {
            "half_mean": half,
            "final_mean": final,
            "flipped": bool(np.sign(half) != np.sign(final)),
        }
    no_plateau = [
        f"{arm}|{seed}|{kind}"
        for arm in RETRAIN_ARMS
        for seed, row in zip(SEEDS, stability_rows[arm], strict=True)
        for kind in ("critic_loss", "actor_loss")
        if not row[kind]["stable"]
    ]
    dynamics_stable = not any(
        row["flipped"] for row in direction_flips.values()
    ) and not no_plateau
    classification = r482_analysis.classify_r482(
        design_valid=bool(
            base.base.base.core._read_hashed_json(ROUTING_GATE).get("passed")
        ),
        missing_shards=missing_shards(),
        integrity_errors=integrity_errors,
        dynamics_stable=dynamics_stable,
        factorial_rows=factorial_rows,
        phase3_rows=phase3_rows,
    )
    holm = sfd.holm_decisions(
        {name: row["p_one_sided"] for name, row in factorial_rows.items()}
    )
    for name, row in factorial_rows.items():
        row["holm_threshold"] = holm[name]["holm_threshold"]
        row["holm_adjusted_p"] = holm[name]["adjusted_p"]
        row["holm_reject"] = holm[name]["reject"]
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "contract_sha256": base.base.base.core.contract_sha256(),
        "seal_sha256": base.base.base.core._sha256_file(SEAL),
        "integrity": {
            "valid": not integrity_errors,
            "errors": integrity_errors,
            "base_hashes": {
                str(seed): sorted(values) for seed, values in base_hashes.items()
            },
            "reward_hashes": {
                key: sorted(values) for key, values in reward_hashes.items()
            },
        },
        "factorial_materiality_tests": factorial_rows,
        "factorial_half_stage_means": {
            name: float(
                np.mean([factorial_half[name][seed] for seed in sorted(factorial_half[name])])
            )
            for name in r482_analysis.REGISTERED_EFFECTS
        },
        "phase3": phase3_rows,
        "optimization": {
            "direction_flips": direction_flips,
            "nonplateau_rows": no_plateau,
            "unresolved": not dynamics_stable,
        },
        "classification": {
            **classification,
            "scope": (
                "26 fresh seeds; frozen R470 learner/bank/projector only; "
                "corrected card; zero carryover; row-permuted P; four "
                "registered materiality tests"
            ),
            "universal_intrinsic_claim_authorized": False,
        },
        "created_utc": datetime.now(UTC).isoformat(),
    }
    return base.base.base.core._write_new_json(OUT / "formal_analysis.json", payload)


def artifact_budget_check() -> dict[str, int]:
    return check_artifact_budget(OUT, max_bytes=ARTIFACT_BUDGET_BYTES)


def formal_manifest() -> str:
    load_seal()
    artifact_budget_check()
    missing = missing_shards()
    if missing:
        raise RuntimeError(f"cannot finalize with missing shards: {missing[:5]}")
    training_manifests = list(OUT.glob("train/*/seed*/manifest.json"))
    if len(training_manifests) != 234:
        raise RuntimeError(
            f"expected 234 training manifests, found {len(training_manifests)}"
        )
    analysis = base.base.base.core._read_hashed_json(OUT / "formal_analysis.json")
    classification = analysis.get("classification", {})
    required = {"design": "VALID", "execution": "COMPLETE", "integrity": "PASS"}
    if any(classification.get(field) != value for field, value in required.items()):
        raise RuntimeError(f"formal analysis is not finalizable: {classification}")
    core = base.base.base.core
    entries = []
    for path in sorted(OUT.rglob("*")):
        if (
            not path.is_file()
            or path.name == "formal_manifest.json"
            or path.name.endswith(".sha256")
            or "dev" in path.relative_to(OUT).parts
            or "development_inputs" in path.relative_to(OUT).parts
            or (
                len(path.relative_to(OUT).parts) >= 2
                and path.relative_to(OUT).parts[0] == "donors"
                and path.relative_to(OUT).parts[1]
                in {f"seed{seed}" for seed in DEV_SEEDS}
            )
        ):
            continue
        sidecar = Path(f"{path}.sha256")
        if (
            not sidecar.is_file()
            or sidecar.read_text(encoding="ascii").split()[0]
            != core._sha256_file(path)
        ):
            raise RuntimeError(f"missing/invalid sidecar: {path}")
        entries.append(
            {
                "path": core._relative(path),
                "sha256": core._sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    return core._write_new_json(
        OUT / "formal_manifest.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "entries": entries,
            "entry_count": len(entries),
            "total_bytes": sum(row["bytes"] for row in entries),
            "development_artifacts_excluded": True,
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )


def write_eta_recalibration(driver_result: Path) -> str:
    load_seal()
    payload = json.loads(driver_result.read_text(encoding="utf-8"))
    if set(payload.get("results", {})) != set(TRAIN_WAVE_IDS[0]):
        raise RuntimeError("ETA input is not the exact first sealed training wave")
    eta = {
        **recalibrate_eta(
            payload,
            remaining_training_shards=218,
            evaluation_wave_count=1,
        ),
        "round": ROUND_ID,
        "driver_result": base.base.base.core._relative(driver_result),
        "driver_result_sha256": base.base.base.core._sha256_file(driver_result),
        "created_utc": datetime.now(UTC).isoformat(),
    }
    return base.base.base.core._write_new_json(ETA_RECALIBRATION, eta)


def write_pipeline_inventory() -> str:
    payload = inventory_artifacts(
        repo_root=ROOT,
        result_root=OUT,
        log_roots=(TRAIN_LOG_ROOT, EVAL_LOG_ROOT),
        phase=os.environ.get("R482_PIPELINE_PHASE", "unknown"),
        exit_code=int(os.environ.get("R482_PIPELINE_EXIT_CODE", "1")),
        created_utc=datetime.now(UTC).isoformat(),
    )
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    return base.base.base.core._write_new_json(
        PIPELINE_INVENTORY / f"inventory_{stamp}.json", payload
    )


for _name, _value in {
    "authority_checks": authority_checks,
    "build_contract": build_contract,
    "arm_factors": arm_factors,
    "load_seal": load_seal,
    "rehearsal": rehearsal,
    "routing_gate": routing_gate,
    "prepare": prepare,
    "train_arm_seed": train_arm_seed,
    "evaluate_arm_stage": evaluate_arm_stage,
    "aggregate": aggregate,
    "missing_shards": missing_shards,
    "formal_manifest": formal_manifest,
}.items():
    setattr(base, _name, _value)
    setattr(base.base, _name, _value)
    setattr(base.base.base, _name, _value)
    setattr(base.base.base.core, _name, _value)


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "base",
            "basegen",
            "route",
            "rehearse",
            "prepare",
            "verify",
            "shard",
            "aggregate",
            "budget",
            "eta",
            "inventory",
            "manifest",
            "dev-check",
            "owner-check",
            "capacity",
            "formal-go-check",
            "dev-report",
            "dev-report-check",
        ),
    )
    parser.add_argument("shard_id", nargs="?")
    args = parser.parse_args()
    if args.command == "base":
        payload = base_audit()
        digest = base.base.base.core._write_new_json(BASE_AUDIT, payload)
        base.base.base.core.safe_emit(
            json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True)
        )
    elif args.command == "basegen":
        base.base.base.core.safe_emit(basegen())
    elif args.command == "route":
        base.base.base.core._assert_wsl_scratch()
        payload = routing_gate()
        digest = base.base.base.core._write_new_json(ROUTING_GATE, payload)
        base.base.base.core.safe_emit(
            json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True)
        )
    elif args.command == "rehearse":
        payload = rehearsal()
        digest = base.base.base.core._write_new_json(REHEARSAL, payload)
        base.base.base.core.safe_emit(
            json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True)
        )
    elif args.command == "prepare":
        base.base.base.core.safe_emit(json.dumps(prepare(), indent=2, sort_keys=True))
    elif args.command == "verify":
        base.base.base.core.safe_emit(
            json.dumps(load_seal(), indent=2, sort_keys=True)
        )
    elif args.command == "aggregate":
        base.base.base.core.safe_emit(aggregate())
    elif args.command == "budget":
        load_seal()
        base.base.base.core.safe_emit(json.dumps(artifact_budget_check(), sort_keys=True))
    elif args.command == "eta":
        if args.shard_id is None:
            raise SystemExit("eta requires the first-wave driver result path")
        path = Path(args.shard_id)
        if not path.is_absolute():
            path = ROOT / path
        base.base.base.core.safe_emit(write_eta_recalibration(path.resolve()))
    elif args.command == "inventory":
        base.base.base.core.safe_emit(write_pipeline_inventory())
    elif args.command == "manifest":
        base.base.base.core.safe_emit(formal_manifest())
    elif args.command == "dev-check":
        base.base.base.core.safe_emit(
            json.dumps(development_check(), indent=2, sort_keys=True)
        )
    elif args.command == "owner-check":
        base.base.base.core.safe_emit(
            json.dumps(owner_approval_check(), indent=2, sort_keys=True)
        )
    elif args.command == "capacity":
        base.base.base.core.safe_emit(measure_capacity())
    elif args.command == "formal-go-check":
        base.base.base.core.safe_emit(
            json.dumps(formal_go_check(), indent=2, sort_keys=True)
        )
    elif args.command == "dev-report":
        base.base.base.core.safe_emit(write_development_report())
    elif args.command == "dev-report-check":
        base.base.base.core.safe_emit(
            json.dumps(development_report_check(), indent=2, sort_keys=True)
        )
    else:
        if args.shard_id is None:
            raise SystemExit("shard requires a shard id")
        parts = args.shard_id.split("|")
        if parts[0] == "train" and len(parts) == 3:
            arm_id, seed = parts[1], int(parts[2])
            digest = train_arm_seed(arm_id, seed)
            manifest = base.base.base.core._read_hashed_json(
                OUT / "train" / arm_id / f"seed{seed}" / "manifest.json"
            )
            if manifest.get("valid") is not True or int(
                manifest.get("interaction_steps", -1)
            ) != 43_200:
                raise RuntimeError(
                    f"formal training cell invalid after preserving manifest: {arm_id}|{seed}"
                )
            base.base.base.core.safe_emit(digest)
        elif parts[0] == "dev" and len(parts) == 3:
            with _terminal_guarded_environment():
                base.base.base.core.safe_emit(
                    _train_dev_cell_body(parts[1], int(parts[2]))
                )
        elif parts[0] == "eval" and len(parts) == 3:
            evaluate_arm_stage(parts[2], parts[1])
        else:
            raise SystemExit(f"unsupported shard: {args.shard_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
