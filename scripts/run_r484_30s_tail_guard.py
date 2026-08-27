"""R484 evaluation-only 30-second tail guard for frozen R483 policies.

Physical commands are WSL-only and must be invoked through ``andes_scratch``::

    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r484_30s_tail_guard.py \
        --config memory/rounds/R484/config.json rehearse

The formal queue uses sixteen deterministic shards.  Each shard owns thirteen
R483 final-checkpoint policy cells and exactly one comparator-arm/profile
block.  This runner never trains, selects, or tunes a
policy.  Scientific outputs are create-only and SHA-256 sidecar protected.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from memory.tools.artifact_io import read_verified_json, sha256_file, write_new_json

from andes_rl_kundur.evaluation.u2_confirmatory import (
    terminal_invalid,
    verify_formal_seal,
)

ROUND_ID = "R484"
SOURCE_ROUND = "R483"
FRESH_PARENT_ROUND = "R481"
FACTORIAL_ARMS = (
    "an_cn_r0",
    "an_cn_r1",
    "an_cp_r0",
    "an_cp_r1",
    "ap_cn_r0",
    "ap_cn_r1",
    "ap_cp_r0",
    "ap_cp_r1",
)
SEEDS = tuple(range(501, 527))
CANARY_PROFILES = (
    "canary_eval_a",
    "canary_eval_b",
    "canary_eval_c",
    "canary_eval_d",
)
FRESH_PROFILES = ("fresh_eva_a", "fresh_eva_b", "fresh_eva_c", "fresh_eva_d")
COMPARATORS = ("zero", "local_neighbour_md_km2_kd2")
EXPECTED_STEPS = 150
WORKERS = 16
EXPECTED_TRAJECTORIES = 5_088
RECOVERY_POLICY = "preserve_partial_attempt_reuse_completed_only_with_resume"

R483_CONFIG = ROOT / "memory/rounds/R483/adaptive_config.json"
R483_PLAN = ROOT / "memory/rounds/R483/plan.md"
R481_PLAN = ROOT / "memory/rounds/R481/plan.md"

_R483_FORMAL_ENTRY_CACHE: dict[str, str] | None = None
_R481_PREFIX_CACHE: dict[tuple[str, str, str], dict[str, Any]] | None = None


def _resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _repo_path(value: str | Path) -> Path:
    path = _resolve(value).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as error:
        raise ValueError(f"configured path escapes repository: {value}") from error
    return path


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_r483_runner() -> Any:
    return _load_module("_r484_r483_runner", ROOT / "scripts/run_adaptive_u2_successor.py")


def _load_r481_runner() -> Any:
    return _load_module("_r484_r481_runner", ROOT / "scripts/run_r481_direct_md.py")


def _round_state(plan: Path) -> str | None:
    match = re.search(r"(?m)^state:\s*([^\s]+)\s*$", plan.read_text(encoding="utf-8"))
    return None if match is None else match.group(1)


def _validate_sidecar(path: Path, expected: str | None = None) -> str:
    if not path.is_file():
        raise RuntimeError(f"missing identity input: {path}")
    sidecar = Path(f"{path}.sha256")
    if not sidecar.is_file():
        raise RuntimeError(f"missing identity sidecar: {sidecar}")
    tokens = sidecar.read_text(encoding="ascii").split()
    actual = sha256_file(path)
    if not tokens or tokens[0] != actual:
        raise RuntimeError(f"identity sidecar mismatch: {path}")
    if expected is not None and actual != expected:
        raise RuntimeError(f"frozen identity hash mismatch: {path}")
    return actual


def load_config(path: Path) -> dict[str, Any]:
    path = _repo_path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "round",
        "out",
        "recovery_policy",
        "factorial_arms",
        "seeds",
        "contract",
        "execution",
        "identity_inputs",
        "authority",
    }
    if set(payload) != required:
        raise ValueError(f"R484 config keys differ: {sorted(set(payload) ^ required)}")
    if payload["schema_version"] != 1 or payload["round"] != ROUND_ID:
        raise ValueError("R484 config identity mismatch")
    if payload["recovery_policy"] != RECOVERY_POLICY:
        raise ValueError("R484 recovery policy drift")
    if tuple(payload["factorial_arms"]) != FACTORIAL_ARMS:
        raise ValueError("R484 factorial arm roster drift")
    if tuple(int(value) for value in payload["seeds"]) != SEEDS:
        raise ValueError("R484 seed roster drift")
    contract = payload["contract"]
    expected_contract = {
        "steps": EXPECTED_STEPS,
        "dt_seconds": 0.2,
        "canary_profiles": list(CANARY_PROFILES),
        "fresh_profiles": list(FRESH_PROFILES),
        "comparators": list(COMPARATORS),
        "training_authorized": False,
        "tuning_authorized": False,
    }
    if contract != expected_contract:
        raise ValueError("R484 execution contract drift")
    execution = payload["execution"]
    if set(execution) != {"workers", "eval_log_dir"} or int(execution["workers"]) != WORKERS:
        raise ValueError("R484 execution budget drift")
    authority_keys = {
        "plan",
        "owner_approval",
        "routing_gate",
        "rehearsal",
        "capacity",
        "review_a",
        "review_b",
        "seal",
        "shards",
    }
    if set(payload["authority"]) != authority_keys:
        raise ValueError("R484 authority path set drift")
    for key, value in payload["authority"].items():
        payload["authority"][key] = _repo_path(value)
    identities = payload["identity_inputs"]
    expected_identity_keys = {
        "r483_config",
        "r483_formal_seal",
        "r483_formal_manifest",
        "r481_contract",
        "r481_formal_seal",
        "r481_formal_analysis",
        "r481_formal_execution",
    }
    if set(identities) != expected_identity_keys:
        raise ValueError("R484 identity-input set drift")
    for key, row in identities.items():
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            raise ValueError(f"invalid identity input: {key}")
        row["_path"] = _repo_path(row["path"])
        if not re.fullmatch(r"[0-9a-f]{64}", str(row["sha256"])):
            raise ValueError(f"invalid identity hash: {key}")
    payload["_out"] = _repo_path(payload["out"])
    payload["_eval_log_dir"] = _repo_path(execution["eval_log_dir"])
    payload["_path"] = path
    return payload


def _identity_path(config: Mapping[str, Any], key: str) -> Path:
    return config["identity_inputs"][key]["_path"]


def _verify_identity_inputs(config: Mapping[str, Any]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name, row in config["identity_inputs"].items():
        hashes[name] = _validate_sidecar(row["_path"], str(row["sha256"]))
    r481_contract, _ = read_verified_json(_identity_path(config, "r481_contract"))
    r481_seal, _ = read_verified_json(_identity_path(config, "r481_formal_seal"))
    if r481_seal.get("round") != FRESH_PARENT_ROUND:
        raise RuntimeError("R481 seal round mismatch")
    if r481_seal.get("contract") != r481_contract:
        raise RuntimeError("R481 contract contradicts its formal seal")
    r481_analysis, _ = read_verified_json(_identity_path(config, "r481_formal_analysis"))
    if (
        r481_analysis.get("classification") != "DIRECT-MD-FORMAL-PASS"
        or r481_analysis.get("selected_deterministic_arm") != COMPARATORS[1]
    ):
        raise RuntimeError("R481 frozen deterministic winner identity mismatch")
    if r481_analysis.get("formal_execution_sha256") != config["identity_inputs"][
        "r481_formal_execution"
    ]["sha256"]:
        raise RuntimeError("R481 formal analysis/execution identity mismatch")
    r483_seal, _ = read_verified_json(_identity_path(config, "r483_formal_seal"))
    if r483_seal.get("round") != SOURCE_ROUND or r483_seal.get("formal_authority") is not True:
        raise RuntimeError("R483 formal seal is not authoritative")
    return hashes


def _checkpoint_inventory(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Verify and return all 208 final checkpoints against the R483 manifest."""

    _verify_identity_inputs(config)
    formal, _ = read_verified_json(_identity_path(config, "r483_formal_manifest"))
    if formal.get("round") != SOURCE_ROUND:
        raise RuntimeError("R483 formal manifest round mismatch")
    entries = formal.get("entries")
    if not isinstance(entries, list):
        raise RuntimeError("R483 formal manifest has no entries")
    by_path = {
        str(row.get("path")): row
        for row in entries
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    }
    inventory: dict[str, dict[str, Any]] = {}
    for arm in FACTORIAL_ARMS:
        for seed in SEEDS:
            manifest_path = (
                ROOT
                / "results/research_loop/r483_adaptive_u2/train"
                / arm
                / f"seed{seed}"
                / "manifest.json"
            )
            checkpoint_path = manifest_path.with_name("final.pt")
            manifest_rel = _relative(manifest_path)
            checkpoint_rel = _relative(checkpoint_path)
            manifest_entry = by_path.get(manifest_rel)
            checkpoint_entry = by_path.get(checkpoint_rel)
            if not isinstance(manifest_entry, dict) or not isinstance(checkpoint_entry, dict):
                raise RuntimeError(f"R483 formal manifest lacks cell: {arm}|{seed}")
            manifest_sha = _validate_sidecar(manifest_path, str(manifest_entry["sha256"]))
            checkpoint_sha = _validate_sidecar(
                checkpoint_path, str(checkpoint_entry["sha256"])
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            identity = {
                "round": SOURCE_ROUND,
                "arm_id": arm,
                "training_seed": seed,
                "training_mode": "adaptive_stop_v1",
                "valid": True,
                "final_checkpoint_sha256": checkpoint_sha,
            }
            for key, value in identity.items():
                if manifest.get(key) != value:
                    raise RuntimeError(f"R483 manifest identity mismatch: {arm}|{seed}|{key}")
            inventory[f"{arm}|{seed}"] = {
                "arm_id": arm,
                "seed": seed,
                "manifest_path": manifest_rel,
                "manifest_sha256": manifest_sha,
                "checkpoint_path": checkpoint_rel,
                "checkpoint_sha256": checkpoint_sha,
                "base_state_sha256": str(manifest["base_state_sha256"]),
            }
    if len(inventory) != 208:
        raise RuntimeError(f"R483 checkpoint inventory count mismatch: {len(inventory)}")
    return inventory


def _source_paths(config: Mapping[str, Any]) -> dict[str, Path]:
    paths = {
        "runner": Path(__file__).resolve(),
        "analysis": ROOT / "src/andes_rl_kundur/evaluation/r484_tail_guard.py",
        "runner_test": ROOT / "tests/test_run_r484_30s_tail_guard.py",
        "analysis_test": ROOT / "tests/test_r484_tail_guard.py",
        "dynamic_driver": ROOT / "scripts/adaptive_shard_driver.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "r483_runner": ROOT / "scripts/run_adaptive_u2_successor.py",
        "r481_runner": ROOT / "scripts/run_r481_direct_md.py",
        "canary_contract": ROOT / "src/andes_rl_kundur/evaluation/cd_matd3_canary.py",
        "fresh_contract": ROOT / "src/andes_rl_kundur/evaluation/r481_fresh_profiles.py",
        "headroom_summary": ROOT / "src/andes_rl_kundur/evaluation/md_decoupling_headroom.py",
        "source_factorial": ROOT / "src/andes_rl_kundur/evaluation/source_factorial_design.py",
        "formal_seal_verifier": ROOT / "src/andes_rl_kundur/evaluation/u2_confirmatory.py",
        "controller": ROOT / "src/andes_rl_kundur/control/per_vsg_md.py",
        "environment": ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "config": config["_path"],
        "shards": config["authority"]["shards"],
        "plan": config["authority"]["plan"],
        "r483_plan": R483_PLAN,
        "r481_plan": R481_PLAN,
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise RuntimeError(f"R484 source files missing: {missing}")
    return paths


def _reviewed_files(config: Mapping[str, Any]) -> tuple[Path, ...]:
    return tuple(dict.fromkeys(_source_paths(config).values()))


def _bound_files(config: Mapping[str, Any]) -> dict[str, Path]:
    authority = config["authority"]
    return {
        "plan_sha256": authority["plan"],
        "owner_approval_sha256": authority["owner_approval"],
        "routing_gate_sha256": authority["routing_gate"],
        "rehearsal_sha256": authority["rehearsal"],
        "capacity_sha256": authority["capacity"],
        "code_review_a_sha256": authority["review_a"],
        "code_review_b_sha256": authority["review_b"],
        "config_sha256": config["_path"],
        "r483_formal_manifest_sha256": _identity_path(config, "r483_formal_manifest"),
        "r483_formal_seal_sha256": _identity_path(config, "r483_formal_seal"),
        "r481_contract_sha256": _identity_path(config, "r481_contract"),
        "r481_formal_seal_sha256": _identity_path(config, "r481_formal_seal"),
        "r481_formal_analysis_sha256": _identity_path(config, "r481_formal_analysis"),
        "r481_formal_execution_sha256": _identity_path(
            config, "r481_formal_execution"
        ),
    }


def _preseal_authority(config: Mapping[str, Any]) -> dict[str, Any]:
    if _round_state(config["authority"]["plan"]) != "active":
        raise RuntimeError("R484 plan is not active")
    if _round_state(R483_PLAN) != "completed":
        raise RuntimeError("R483 parent is not completed")
    if _round_state(R481_PLAN) != "completed":
        raise RuntimeError("R481 parent is not completed")
    approval, _ = read_verified_json(config["authority"]["owner_approval"])
    if approval.get("round") != ROUND_ID or approval.get("approved") is not True:
        raise RuntimeError("R484 owner approval is invalid")
    _validate_sidecar(config["_path"])
    _validate_sidecar(config["authority"]["shards"])
    _verify_identity_inputs(config)
    return approval


def _canary_contract() -> dict[str, Any]:
    from andes_rl_kundur.evaluation.cd_matd3_canary import build_contract

    return build_contract()


def _fresh_contract(config: Mapping[str, Any]) -> dict[str, Any]:
    payload, _ = read_verified_json(_identity_path(config, "r481_contract"))
    return payload


def build_contract(config: Mapping[str, Any]) -> dict[str, Any]:
    canary = _canary_contract()
    fresh = _fresh_contract(config)
    canary_profiles = [
        copy.deepcopy(row)
        for row in canary["profiles"]
        if str(row["profile_id"]) in CANARY_PROFILES
    ]
    fresh_profiles = [
        copy.deepcopy(row)
        for row in fresh["profiles"]
        if str(row["profile_id"]) in FRESH_PROFILES
    ]
    if tuple(str(row["profile_id"]) for row in canary_profiles) != CANARY_PROFILES:
        raise RuntimeError("canary profile order/roster mismatch")
    if tuple(str(row["profile_id"]) for row in fresh_profiles) != FRESH_PROFILES:
        raise RuntimeError("fresh profile order/roster mismatch")
    shared_keys = (
        "decoder",
        "differential_transform",
        "action_bounds",
        "action_slew_limit",
    )
    for key in shared_keys:
        if canary.get(key) != fresh.get(key):
            raise RuntimeError(f"R481/R483 physical contract mismatch: {key}")
    for row in canary_profiles:
        row["bank"] = "canary"
        row["environment_seed"] = int(canary["bank_seed"])
    for row in fresh_profiles:
        row["bank"] = "fresh"
        row["environment_seed"] = int(fresh["seed"])
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "source_round": SOURCE_ROUND,
        "fresh_parent_round": FRESH_PARENT_ROUND,
        "steps": EXPECTED_STEPS,
        "dt_seconds": 0.2,
        "physical_nominal_frequency_hz": 60.0,
        "control_nominal_frequency_hz": 50.0,
        **{key: copy.deepcopy(canary[key]) for key in shared_keys},
        "factorial_arms": list(FACTORIAL_ARMS),
        "seeds": list(SEEDS),
        "learned_policy_count": 208,
        "comparators": list(COMPARATORS),
        "profiles": canary_profiles + fresh_profiles,
        "learned_profiles": list(CANARY_PROFILES),
        "fresh_comparator_profiles": list(FRESH_PROFILES),
        "expected_trajectories": EXPECTED_TRAJECTORIES,
        "thresholds": {
            "minimum_joint_improvement": 0.05,
            "maximum_common_harm": 0.03,
            "maximum_action_stress_harm": 0.10,
            "maximum_action_saturation_fraction": 0.05,
            "nonconstant_action_variation_floor": 1.0e-6,
            "independent_action_dispersion_floor": 1.0e-6,
        },
        "factorial_materiality_ratio": 1.10,
        "factorial_familywise_alpha": 0.05,
        "reward_used_for_gate": False,
        "training_authorized": False,
        "tuning_authorized": False,
        "claim_scope": "frozen R483 policies and registered R483/R481 profile banks only",
    }


def contract_sha256(config: Mapping[str, Any]) -> str:
    return _canonical_sha256(build_contract(config))


def evaluation_shard_ids(config: Mapping[str, Any]) -> list[str]:
    del config
    return [f"eval|{index:02d}" for index in range(WORKERS)]


def _all_cells() -> list[tuple[str, int]]:
    return [(arm, seed) for arm in FACTORIAL_ARMS for seed in SEEDS]


def _profiles_by_id(contract: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["profile_id"]): dict(row) for row in contract["profiles"]}


def assigned_work(config: Mapping[str, Any], shard_id: str) -> dict[str, Any]:
    parts = shard_id.split("|")
    if len(parts) != 2 or parts[0] != "eval" or not parts[1].isdigit():
        raise ValueError(f"unknown R484 shard: {shard_id}")
    index = int(parts[1])
    if index < 0 or index >= WORKERS or shard_id not in evaluation_shard_ids(config):
        raise ValueError(f"unregistered R484 shard: {shard_id}")
    cells = _all_cells()[index * 13 : (index + 1) * 13]
    if index < 8:
        comparator_blocks = [
            {
                "bank": "canary",
                "profile_id": CANARY_PROFILES[index // 2],
                "policy_id": COMPARATORS[index % 2],
            }
        ]
    else:
        comparator_index = index - 8
        comparator_blocks = [
            {
                "bank": "fresh",
                "profile_id": FRESH_PROFILES[comparator_index // 2],
                "policy_id": COMPARATORS[comparator_index % 2],
            }
        ]
    return {
        "shard_id": shard_id,
        "shard_index": index,
        "learned_cells": cells,
        "comparator_blocks": comparator_blocks,
        "expected_trajectories": 13 * len(CANARY_PROFILES) * 6
        + 6 * len(comparator_blocks),
        "expected_blocks": 13 * len(CANARY_PROFILES) + len(comparator_blocks),
    }


def _block_specs(config: Mapping[str, Any], shard_id: str) -> list[dict[str, Any]]:
    work = assigned_work(config, shard_id)
    specs = [
        {
            "kind": "learned",
            "bank": "canary",
            "arm_id": arm,
            "training_seed": seed,
            "policy_id": arm,
            "profile_id": profile_id,
        }
        for arm, seed in work["learned_cells"]
        for profile_id in CANARY_PROFILES
    ]
    specs.extend(
        {
            "kind": "comparator",
            "bank": block["bank"],
            "arm_id": block["policy_id"],
            "training_seed": None,
            "policy_id": block["policy_id"],
            "profile_id": block["profile_id"],
        }
        for block in work["comparator_blocks"]
    )
    if len(specs) != int(work["expected_blocks"]):
        raise RuntimeError(f"R484 block roster mismatch: {shard_id}")
    return specs


def _block_id(spec: Mapping[str, Any]) -> str:
    seed = "none" if spec["training_seed"] is None else f"seed{spec['training_seed']}"
    return "__".join(
        (
            str(spec["kind"]),
            str(spec["arm_id"]),
            seed,
            str(spec["profile_id"]),
        )
    )


def _block_path(
    config: Mapping[str, Any], shard_id: str, spec: Mapping[str, Any]
) -> Path:
    index = int(shard_id.split("|")[1])
    return config["_out"] / "blocks" / f"shard_{index:02d}" / f"{_block_id(spec)}.json"


def _seal_static_inputs(config: Mapping[str, Any]) -> dict[str, Any]:
    _preseal_authority(config)
    contract = build_contract(config)
    return {
        "schema_version": 2,
        "seal_fragment_only": True,
        "round": ROUND_ID,
        "contract_sha256": _canonical_sha256(contract),
        "config_sha256": sha256_file(config["_path"]),
        "sources": {
            name: {"path": _relative(path), "sha256": sha256_file(path)}
            for name, path in _source_paths(config).items()
        },
        "parents": {
            name: {"path": row["path"], "sha256": row["sha256"]}
            for name, row in config["identity_inputs"].items()
        },
        "shard_lists": {
            "eval": {
                "path": _relative(config["authority"]["shards"]),
                "sha256": sha256_file(config["authority"]["shards"]),
            }
        },
        "expected_trajectories": EXPECTED_TRAJECTORIES,
        "launch": {
            "workers": WORKERS,
            "launcher": 1,
            "wsl_python_processes": WORKERS + 2,
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
            "dynamic_immediate_refill": True,
        },
    }


def seal_inputs(config: Mapping[str, Any]) -> dict[str, Any]:
    """Return the full pre-seal fragment, including all 208 verified cells."""

    return {
        **_seal_static_inputs(config),
        "r483_checkpoint_inventory": _checkpoint_inventory(config),
    }


def _verified_routing_gate(config: Mapping[str, Any]) -> dict[str, Any]:
    routing, _ = read_verified_json(config["authority"]["routing_gate"])
    if (
        routing.get("round") != ROUND_ID
        or routing.get("passed") is not True
        or routing.get("checks", {}).get("independent_reviews_passed") is not True
    ):
        raise RuntimeError("R484 routing gate is not a passing launch authority")
    return routing


def _verify_live_runtime(config: Mapping[str, Any]) -> dict[str, Any]:
    rehearsal, _ = read_verified_json(config["authority"]["rehearsal"])
    expected = rehearsal.get("runtime")
    if not isinstance(expected, Mapping):
        raise RuntimeError("R484 rehearsal has no sealed runtime identity")
    current = _installed_runtime()
    for key in ("andes_version", "andes_module", "case_path", "case_sha256"):
        if current.get(key) != expected.get(key):
            raise RuntimeError(f"R484 installed runtime drift: {key}")
    return current


def load_seal(
    config: Mapping[str, Any], *, verify_checkpoint_inventory: bool = True,
    require_runtime: bool = False,
) -> dict[str, Any]:
    _preseal_authority(config)
    seal = verify_formal_seal(
        repo_root=ROOT,
        seal_path=config["authority"]["seal"],
        round_id=ROUND_ID,
        contract_sha256=contract_sha256(config),
        bound_files=_bound_files(config),
        review_paths=(config["authority"]["review_a"], config["authority"]["review_b"]),
        reviewed_files=_reviewed_files(config),
        expected_shards={"eval": evaluation_shard_ids(config)},
    )
    expected_fragment = _seal_static_inputs(config)
    for key in (
        "round",
        "contract_sha256",
        "config_sha256",
        "sources",
        "parents",
        "expected_trajectories",
        "launch",
    ):
        if seal.get(key) != expected_fragment[key]:
            raise RuntimeError(f"R484 formal seal binding mismatch: {key}")
    sealed_inventory = seal.get("r483_checkpoint_inventory")
    expected_keys = {f"{arm}|{seed}" for arm, seed in _all_cells()}
    if not isinstance(sealed_inventory, dict) or set(sealed_inventory) != expected_keys:
        raise RuntimeError("R484 formal seal checkpoint roster mismatch")
    if verify_checkpoint_inventory and sealed_inventory != _checkpoint_inventory(config):
        raise RuntimeError("R484 formal seal checkpoint inventory mismatch")
    _verified_routing_gate(config)
    if require_runtime:
        _verify_live_runtime(config)
    return seal


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R484 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R484 physical commands must run through scripts/andes_scratch.py")
    try:
        import torch

        torch.set_num_threads(1)
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass
    except ImportError:
        pass


def _installed_runtime() -> dict[str, Any]:
    import andes

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    return {
        "python": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "andes_module": str(Path(andes.__file__).resolve()),
        "case_path": str(case_path),
        "case_sha256": sha256_file(case_path),
    }


def _runtime_bundle() -> tuple[Any, Any, dict[str, Any]]:
    r483 = _load_r483_runner()
    r483_config = r483.load_config(R483_CONFIG)
    runtime = r483._load_runtime()
    r483.bind_runtime(runtime, r483_config)
    return r483, runtime, r483_config


def _controller_for(arm_id: str) -> Any:
    from andes_rl_kundur.control.per_vsg_md import (
        LocalNeighbourMDExecution,
        local_neighbour_md_candidates,
    )

    if arm_id == "zero":
        return None
    contracts = {row.name: row for row in local_neighbour_md_candidates()}
    if arm_id not in contracts:
        raise ValueError(f"unknown deterministic comparator: {arm_id}")
    return LocalNeighbourMDExecution(contracts[arm_id])


def _json_safe_finite(
    value: Any, *, path: str, nonfinite_paths: list[str]
) -> Any:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        if math.isfinite(float(value)):
            return value
        nonfinite_paths.append(path)
        return None
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe_finite(
                item,
                path=f"{path}.{key}" if path else str(key),
                nonfinite_paths=nonfinite_paths,
            )
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [
            _json_safe_finite(
                item,
                path=f"{path}[{index}]",
                nonfinite_paths=nonfinite_paths,
            )
            for index, item in enumerate(value)
        ]
    return value


def _sanitize_nonfinite_record(record: dict[str, Any]) -> dict[str, Any]:
    nonfinite_paths: list[str] = []
    safe = _json_safe_finite(
        record, path="record", nonfinite_paths=nonfinite_paths
    )
    if not isinstance(safe, dict):  # pragma: no cover - fixed caller shape
        raise TypeError("R484 record sanitizer changed the record shape")
    if nonfinite_paths:
        detail = "nonfinite numeric fields: " + ",".join(nonfinite_paths[:20])
        prior = safe.get("failure")
        safe["failure"] = f"{prior}; {detail}" if prior else detail
        safe["completed"] = False
        safe["nonfinite_fields"] = nonfinite_paths
    return safe


def _run_trajectory(
    runtime: Any,
    *,
    profile: Mapping[str, Any],
    scenario: Mapping[str, Any],
    policy_id: str,
    factorial_arm: str | None = None,
    seed: int | None = None,
    wrapper: Any | None = None,
    checkpoint_sha256: str | None = None,
    training_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Run one 150-step trajectory on the corrected device-base card."""

    import numpy as np

    try:
        import resource
    except ImportError:  # Windows-only unit-test seam; formal execution is WSL.
        resource = None

    from andes_rl_kundur.control.per_vsg_md import adapt_v4_observations_to_physical

    core = runtime.base.base.base.core
    env: Any | None = None
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] = {}
    initial_frequency: list[float] = []
    failure: str | None = None
    try:
        env = core.r431._build_env(profile)
        env.seed(int(profile["environment_seed"]))
        env.STEPS_PER_EPISODE = EXPECTED_STEPS
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
        initial_frequency = (
            np.asarray(env._get_vsg_omega(), dtype=float)
            * float(env.andes_nominal_frequency_hz)
        ).tolist()
        deterministic = _controller_for(policy_id) if factorial_arm is None else None
        if deterministic is not None:
            deterministic.reset()
        previous = np.zeros((4, 2), dtype=np.float32)
        factors = runtime.arm_factors(factorial_arm) if factorial_arm is not None else None
        for step_index in range(EXPECTED_STEPS):
            if factorial_arm is not None:
                joint = core.r431._joint_obs(observation)
                actor_rows = runtime.base.base.source_rows(joint, factors["actor_source"])
                raw, executed = wrapper.act(actor_rows, previous, deterministic=True)
                raw = np.asarray(raw, dtype=np.float32)
                executed = np.asarray(executed, dtype=np.float32)
            elif deterministic is None:
                executed = np.zeros((4, 2), dtype=np.float32)
                raw = executed.copy()
            else:
                executed = np.asarray(
                    deterministic.act(adapt_v4_observations_to_physical(observation)),
                    dtype=np.float32,
                )
                raw = executed.copy()
            observation, _reward, done, info = env.step(
                {index: executed[index] for index in range(4)}
            )
            # Device-base telemetry is mandatory.  Raw GENCLS.M/D are
            # system-base and would invalidate the actuator mapping guard.
            actual_m = np.asarray(info["M_es"], dtype=float)
            actual_d = np.asarray(info["D_es"], dtype=float)
            rows.append(
                {
                    "step_index": step_index,
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
            if terminal_invalid(
                done=bool(done),
                tds_failed=bool(info["tds_failed"]),
                time_index=step_index,
                steps=EXPECTED_STEPS,
            ):
                failure = "TDS failed" if info["tds_failed"] else "premature terminal"
                break
    except Exception as error:
        failure = f"{type(error).__name__}: {error}"
    finally:
        if env is not None:
            try:
                env.close()
            except Exception as close_error:
                close_failure = (
                    f"environment close failed: {type(close_error).__name__}: "
                    f"{close_error}"
                )
                failure = f"{failure}; {close_failure}" if failure else close_failure
    record = {
        "bank": str(profile["bank"]),
        "profile_id": str(profile["profile_id"]),
        "split": "evaluation",
        "scenario_id": str(scenario["scenario_id"]),
        "pair_kind": str(scenario["pair_kind"]),
        "sign": str(scenario["sign"]),
        "magnitude": float(scenario["magnitude"]),
        "delta_u": dict(scenario["delta_u"]),
        "arm_id": policy_id,
        "factorial_arm_id": factorial_arm,
        "training_seed": seed,
        "stage": "final",
        "checkpoint_sha256": checkpoint_sha256,
        "training_manifest_sha256": training_manifest_sha256,
        "identity": identity,
        "initial_freq_hz_physical": initial_frequency,
        "steps": rows,
        "completed_steps": len(rows),
        "completed": failure is None and len(rows) == EXPECTED_STEPS,
        "tds_failed": failure is not None
        or any(bool(row["tds_failed"]) for row in rows),
        "failure": failure,
        "worker_max_rss_kib": (
            0
            if resource is None
            else int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        ),
        "reward_used_for_gate": False,
        "training_executed": False,
    }
    return _sanitize_nonfinite_record(record)


def _run_capacity_job(job: dict[str, Any]) -> dict[str, Any]:
    _assert_wsl_scratch()
    _r483, runtime, _config = _runtime_bundle()
    if job["kind"] == "learned":
        source = job["source"]
        manifest_path = ROOT / source["manifest_path"]
        checkpoint_path = ROOT / source["checkpoint_path"]
        _validate_sidecar(manifest_path, str(source["manifest_sha256"]))
        _validate_sidecar(checkpoint_path, str(source["checkpoint_sha256"]))
        wrapper = runtime.base.base.base.core.FactorialWrapper(str(job["arm_id"]))
        metadata = wrapper.load(checkpoint_path)
        _validate_checkpoint_metadata(
            metadata,
            arm=str(job["arm_id"]),
            base_state_sha256=str(source["base_state_sha256"]),
        )
        record = _run_trajectory(
            runtime,
            profile=job["profile"],
            scenario=job["scenario"],
            policy_id=str(job["arm_id"]),
            factorial_arm=str(job["arm_id"]),
            seed=int(job["training_seed"]),
            wrapper=wrapper,
            checkpoint_sha256=str(source["checkpoint_sha256"]),
            training_manifest_sha256=str(source["manifest_sha256"]),
        )
    else:
        record = _run_trajectory(
            runtime,
            profile=job["profile"],
            scenario=job["scenario"],
            policy_id=str(job["policy_id"]),
        )
    capacity_config = load_config(Path(str(job["config_path"])))
    _attach_prefix_isolation(capacity_config, record)
    record["capacity_job_kind"] = str(job["kind"])
    record["capacity_job_id"] = str(job["job_id"])
    return record


def _validate_trajectory(record: Mapping[str, Any]) -> None:
    if record.get("completed") is not True or record.get("tds_failed") is not False:
        raise RuntimeError(
            f"invalid R484 trajectory: {record.get('arm_id')}|"
            f"{record.get('profile_id')}|{record.get('scenario_id')}|"
            f"{record.get('failure')}"
        )
    rows = record.get("steps")
    if not isinstance(rows, list) or len(rows) != EXPECTED_STEPS:
        raise RuntimeError("R484 trajectory step count mismatch")
    if [int(row.get("step_index", -1)) for row in rows] != list(range(EXPECTED_STEPS)):
        raise RuntimeError("R484 trajectory step-index mismatch")
    done_indices = [
        index for index, row in enumerate(rows) if bool(row.get("done", False))
    ]
    if done_indices != [EXPECTED_STEPS - 1]:
        raise RuntimeError("R484 trajectory terminal-index mismatch")


def _trajectory_id(record: Mapping[str, Any]) -> str:
    return "|".join(
        (
            str(record["bank"]),
            str(record["arm_id"]),
            "" if record.get("training_seed") is None else str(record["training_seed"]),
            str(record["profile_id"]),
            str(record["scenario_id"]),
        )
    )


def _r483_formal_entry_hashes(config: Mapping[str, Any]) -> dict[str, str]:
    global _R483_FORMAL_ENTRY_CACHE
    if _R483_FORMAL_ENTRY_CACHE is None:
        formal, _ = read_verified_json(_identity_path(config, "r483_formal_manifest"))
        entries = formal.get("entries")
        if not isinstance(entries, list):
            raise RuntimeError("R483 formal manifest has no entries")
        _R483_FORMAL_ENTRY_CACHE = {
            str(row["path"]): str(row["sha256"])
            for row in entries
            if isinstance(row, dict) and "path" in row and "sha256" in row
        }
    return _R483_FORMAL_ENTRY_CACHE


def _r483_prefix_reference(
    config: Mapping[str, Any], record: Mapping[str, Any]
) -> tuple[dict[str, Any], str, str]:
    arm = str(record["factorial_arm_id"])
    seed = int(record["training_seed"])
    profile_id = str(record["profile_id"])
    path = (
        ROOT
        / "results/research_loop/r483_adaptive_u2/eval/final"
        / arm
        / f"seed{seed}"
        / f"{profile_id}.json"
    )
    relative = _relative(path)
    expected = _r483_formal_entry_hashes(config).get(relative)
    if expected is None:
        raise RuntimeError(f"R483 formal manifest lacks prefix reference: {relative}")
    digest = _validate_sidecar(path, expected)
    payload = json.loads(path.read_text(encoding="utf-8"))
    matches = [
        row
        for row in payload.get("records", [])
        if row.get("scenario_id") == record.get("scenario_id")
    ]
    if len(matches) != 1:
        raise RuntimeError(f"R483 prefix reference roster mismatch: {relative}")
    return matches[0], relative, digest


def _r481_prefix_references(
    config: Mapping[str, Any],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    global _R481_PREFIX_CACHE
    if _R481_PREFIX_CACHE is None:
        execution, digest = read_verified_json(
            _identity_path(config, "r481_formal_execution")
        )
        if digest != config["identity_inputs"]["r481_formal_execution"]["sha256"]:
            raise RuntimeError("R481 prefix execution hash mismatch")
        cache: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in execution.get("records", []):
            if (
                row.get("arm_id") not in COMPARATORS
                or row.get("profile_id") not in FRESH_PROFILES
            ):
                continue
            key = (
                str(row["arm_id"]),
                str(row["profile_id"]),
                str(row["scenario_id"]),
            )
            if key in cache:
                raise RuntimeError(f"duplicate R481 prefix reference: {key}")
            cache[key] = row
        if len(cache) != 48:
            raise RuntimeError(f"R481 prefix reference count mismatch: {len(cache)}")
        _R481_PREFIX_CACHE = cache
    return _R481_PREFIX_CACHE


def _compare_prefix_rows(
    current: Mapping[str, Any], reference: Mapping[str, Any]
) -> dict[str, Any]:
    import numpy as np

    current_steps = current.get("steps")
    reference_steps = reference.get("steps")
    if (
        not isinstance(current_steps, list)
        or len(current_steps) < 30
        or not isinstance(reference_steps, list)
        or len(reference_steps) != 30
    ):
        return {
            "comparable": False,
            "passed": None,
            "integrity_drift": False,
            "reason": "prefix_not_comparable_after_engineering_failure",
        }
    fields = (
        "time",
        "freq_hz_physical",
        "raw_action_norm",
        "action_norm",
        "delta_M",
        "delta_D",
    )
    for index in range(30):
        left = current_steps[index]
        right = reference_steps[index]
        for field in fields:
            left_value = left.get(field)
            right_value = right.get(
                field,
                right.get("action_norm") if field == "raw_action_norm" else None,
            )
            try:
                equal = bool(
                    np.allclose(
                        np.asarray(left_value, dtype=float),
                        np.asarray(right_value, dtype=float),
                        rtol=0.0,
                        atol=1.0e-9,
                    )
                )
            except (TypeError, ValueError):
                equal = False
            if not equal:
                return {
                    "comparable": True,
                    "passed": False,
                    "integrity_drift": True,
                    "reason": "prefix_value_drift",
                    "first_mismatch": {"step_index": index, "field": field},
                    "tolerance": {"rtol": 0.0, "atol": 1.0e-9},
                }
    return {
        "comparable": True,
        "passed": True,
        "integrity_drift": False,
        "fields": list(fields),
        "steps_compared": 30,
        "done_excluded": True,
        "raw_system_base_m_d_excluded": True,
        "tolerance": {"rtol": 0.0, "atol": 1.0e-9},
    }


def _attach_prefix_isolation(
    config: Mapping[str, Any], record: dict[str, Any]
) -> None:
    required = record.get("factorial_arm_id") is not None or (
        record.get("bank") == "fresh" and record.get("arm_id") in COMPARATORS
    )
    if not required:
        record["prefix_isolation"] = {
            "required": False,
            "passed": True,
            "reason": "no_sealed_matching_prefix_registered",
        }
        return
    try:
        if record.get("factorial_arm_id") is not None:
            reference, reference_path, reference_sha = _r483_prefix_reference(
                config, record
            )
            reference_round = SOURCE_ROUND
        else:
            key = (
                str(record["arm_id"]),
                str(record["profile_id"]),
                str(record["scenario_id"]),
            )
            reference = _r481_prefix_references(config)[key]
            reference_path = _relative(_identity_path(config, "r481_formal_execution"))
            reference_sha = config["identity_inputs"]["r481_formal_execution"][
                "sha256"
            ]
            reference_round = FRESH_PARENT_ROUND
        compared = _compare_prefix_rows(record, reference)
        record["prefix_isolation"] = {
            "required": True,
            "reference_round": reference_round,
            "reference_path": reference_path,
            "reference_sha256": reference_sha,
            **compared,
        }
    except Exception as error:
        record["prefix_isolation"] = {
            "required": True,
            "comparable": False,
            "passed": False,
            "integrity_drift": True,
            "reason": f"reference_error:{type(error).__name__}:{error}",
        }


def _trajectory_status_errors(record: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    engineering: list[str] = []
    integrity: list[str] = []
    if record.get("completed") is not True:
        engineering.append("incomplete_trajectory")
    if record.get("tds_failed") is not False:
        engineering.append("tds_or_runtime_failure")
    if record.get("failure") not in (None, ""):
        engineering.append(f"explicit_failure:{record.get('failure')}")
    prefix = record.get("prefix_isolation")
    prefix_required = record.get("factorial_arm_id") is not None or (
        record.get("bank") == "fresh" and record.get("arm_id") in COMPARATORS
    )
    if prefix_required:
        if not isinstance(prefix, Mapping):
            integrity.append("prefix_isolation:missing_prefix_result")
        elif prefix.get("integrity_drift") is True:
            integrity.append(
                f"prefix_isolation:{prefix.get('reason', 'unknown_prefix_drift')}"
            )
        elif record.get("completed") is True and prefix.get("passed") is not True:
            integrity.append("prefix_isolation:completed_record_not_verified")
    return engineering, integrity


def _record_errors(
    records: Sequence[Mapping[str, Any]],
) -> tuple[list[str], list[str]]:
    engineering: list[str] = []
    integrity: list[str] = []
    for record in records:
        record_id = _trajectory_id(record)
        record_engineering, record_integrity = _trajectory_status_errors(record)
        engineering.extend(f"{record_id}:{error}" for error in record_engineering)
        integrity.extend(f"{record_id}:{error}" for error in record_integrity)
        if record.get("completed") is True:
            try:
                _validate_trajectory(record)
            except Exception as error:
                integrity.append(
                    f"{record_id}:completed_trajectory_structure:{type(error).__name__}:{error}"
                )
    return engineering, integrity


def _expected_block_trajectory_ids(
    contract: Mapping[str, Any], spec: Mapping[str, Any]
) -> set[str]:
    profiles = _profiles_by_id(contract)
    profile = profiles[str(spec["profile_id"])]
    seed = "" if spec.get("training_seed") is None else str(spec["training_seed"])
    return {
        "|".join(
            (
                str(spec["bank"]),
                str(spec["policy_id"]),
                seed,
                str(spec["profile_id"]),
                str(scenario["scenario_id"]),
            )
        )
        for scenario in profile["scenarios"]
    }


def _expected_trajectory_ids(config: Mapping[str, Any], shard_id: str) -> set[str]:
    contract = build_contract(config)
    profiles = _profiles_by_id(contract)
    work = assigned_work(config, shard_id)
    expected: set[str] = set()
    for arm, seed in work["learned_cells"]:
        for profile_id in CANARY_PROFILES:
            profile = profiles[profile_id]
            for scenario in profile["scenarios"]:
                expected.add(
                    f"canary|{arm}|{seed}|{profile_id}|{scenario['scenario_id']}"
                )
    for block in work["comparator_blocks"]:
        profile = profiles[block["profile_id"]]
        for scenario in profile["scenarios"]:
            expected.add(
                f"{block['bank']}|{block['policy_id']}||{block['profile_id']}|"
                f"{scenario['scenario_id']}"
            )
    if len(expected) != int(work["expected_trajectories"]):
        raise RuntimeError(f"R484 expected trajectory collision: {shard_id}")
    return expected


def _shard_path(config: Mapping[str, Any], shard_id: str) -> Path:
    return config["_out"] / "shards" / f"shard_{int(shard_id.split('|')[1]):02d}.json"


def _validate_block_file(
    config: Mapping[str, Any],
    shard_id: str,
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    path = _block_path(config, shard_id, spec)
    payload, digest = read_verified_json(path)
    expected_seal = sha256_file(config["authority"]["seal"])
    expected_identity = {
        "round": ROUND_ID,
        "shard_id": shard_id,
        "seal_sha256": expected_seal,
        "block_id": _block_id(spec),
        "block_spec": dict(spec),
        "trajectory_count": 6,
        "reward_used_for_gate": False,
        "training_executed": False,
    }
    for key, value in expected_identity.items():
        if payload.get(key) != value:
            raise RuntimeError(
                f"published R484 block identity mismatch: {shard_id}|"
                f"{_block_id(spec)}|{key}"
            )
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != 6:
        raise RuntimeError(
            f"published R484 block record count mismatch: {shard_id}|{_block_id(spec)}"
        )
    actual_ids = [_trajectory_id(record) for record in records]
    expected_ids = _expected_block_trajectory_ids(build_contract(config), spec)
    if len(actual_ids) != len(set(actual_ids)) or set(actual_ids) != expected_ids:
        raise RuntimeError(
            f"published R484 block roster mismatch: {shard_id}|{_block_id(spec)}"
        )
    for record in records:
        if (
            record.get("bank") != spec["bank"]
            or record.get("profile_id") != spec["profile_id"]
            or record.get("arm_id") != spec["policy_id"]
            or record.get("factorial_arm_id")
            != (spec["arm_id"] if spec["kind"] == "learned" else None)
            or record.get("training_seed") != spec["training_seed"]
            or record.get("reward_used_for_gate") is not False
            or record.get("training_executed") is not False
        ):
            raise RuntimeError(
                f"published R484 block record identity mismatch: "
                f"{shard_id}|{_block_id(spec)}"
            )
        if spec["kind"] == "learned" and (
            not re.fullmatch(r"[0-9a-f]{64}", str(record.get("checkpoint_sha256", "")))
            or not re.fullmatch(
                r"[0-9a-f]{64}", str(record.get("training_manifest_sha256", ""))
            )
            or record.get("stage") != "final"
        ):
            raise RuntimeError(
                f"published R484 learned identity mismatch: {shard_id}|{_block_id(spec)}"
            )
    engineering, integrity = _record_errors(records)
    if payload.get("engineering_errors") != engineering:
        raise RuntimeError(
            f"published R484 block engineering ledger mismatch: "
            f"{shard_id}|{_block_id(spec)}"
        )
    if payload.get("integrity_errors") != integrity:
        raise RuntimeError(
            f"published R484 block integrity ledger mismatch: "
            f"{shard_id}|{_block_id(spec)}"
        )
    return {
        "block_id": _block_id(spec),
        "path": _relative(path),
        "sha256": digest,
        "trajectory_count": len(records),
        "engineering_errors": engineering,
        "integrity_errors": integrity,
    }


def _existing_block(
    config: Mapping[str, Any],
    shard_id: str,
    spec: Mapping[str, Any],
    *,
    resume: bool,
) -> dict[str, Any] | None:
    path = _block_path(config, shard_id, spec)
    sidecar = Path(f"{path}.sha256")
    if not path.exists() and not sidecar.exists():
        return None
    if not resume:
        raise FileExistsError(
            f"R484 block already exists without authorized resume: "
            f"{shard_id}|{_block_id(spec)}"
        )
    if not path.is_file() or not sidecar.is_file():
        raise RuntimeError(
            f"retained R484 block is incomplete and cannot be overwritten: "
            f"{shard_id}|{_block_id(spec)}"
        )
    return {**_validate_block_file(config, shard_id, spec), "reused": True}


def _publish_block(
    config: Mapping[str, Any],
    shard_id: str,
    spec: Mapping[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    actual_ids = [_trajectory_id(record) for record in records]
    expected_ids = _expected_block_trajectory_ids(build_contract(config), spec)
    if (
        len(records) != 6
        or len(actual_ids) != len(set(actual_ids))
        or set(actual_ids) != expected_ids
    ):
        raise RuntimeError(
            f"R484 block trajectory roster mismatch before publish: "
            f"{shard_id}|{_block_id(spec)}"
        )
    engineering, integrity = _record_errors(records)
    path = _block_path(config, shard_id, spec)
    digest = write_new_json(
        path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "shard_id": shard_id,
            "seal_sha256": sha256_file(config["authority"]["seal"]),
            "block_id": _block_id(spec),
            "block_spec": dict(spec),
            "trajectory_count": len(records),
            "records": records,
            "engineering_errors": engineering,
            "integrity_errors": integrity,
            "reward_used_for_gate": False,
            "training_executed": False,
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )
    return {
        "block_id": _block_id(spec),
        "path": _relative(path),
        "sha256": digest,
        "trajectory_count": len(records),
        "engineering_errors": engineering,
        "integrity_errors": integrity,
        "reused": False,
    }


def _validate_published_shard(
    config: Mapping[str, Any], shard_id: str
) -> dict[str, Any]:
    path = _shard_path(config, shard_id)
    payload, digest = read_verified_json(path)
    if payload.get("round") != ROUND_ID or payload.get("shard_id") != shard_id:
        raise RuntimeError(f"published R484 shard identity mismatch: {shard_id}")
    if payload.get("seal_sha256") != sha256_file(config["authority"]["seal"]):
        raise RuntimeError(f"published R484 shard seal mismatch: {shard_id}")
    indexed_blocks = payload.get("blocks")
    specs = _block_specs(config, shard_id)
    if not isinstance(indexed_blocks, list) or len(indexed_blocks) != len(specs):
        raise RuntimeError(f"published R484 shard block count mismatch: {shard_id}")
    validated_blocks: list[dict[str, Any]] = []
    engineering: list[str] = []
    integrity: list[str] = []
    for index, spec in enumerate(specs):
        row = _validate_block_file(config, shard_id, spec)
        recorded = indexed_blocks[index]
        expected_index = {
            key: row[key]
            for key in (
                "block_id",
                "path",
                "sha256",
                "trajectory_count",
                "engineering_errors",
                "integrity_errors",
            )
        }
        if recorded != expected_index:
            raise RuntimeError(
                f"published R484 shard block index mismatch: "
                f"{shard_id}|{_block_id(spec)}"
            )
        validated_blocks.append(row)
        engineering.extend(row["engineering_errors"])
        integrity.extend(row["integrity_errors"])
    trajectory_count = sum(int(row["trajectory_count"]) for row in validated_blocks)
    expected_work = assigned_work(config, shard_id)
    if trajectory_count != int(expected_work["expected_trajectories"]):
        raise RuntimeError(f"published R484 shard trajectory count mismatch: {shard_id}")
    if payload.get("engineering_errors") != engineering:
        raise RuntimeError(f"published R484 shard engineering ledger mismatch: {shard_id}")
    if payload.get("integrity_errors") != integrity:
        raise RuntimeError(f"published R484 shard integrity ledger mismatch: {shard_id}")
    return {
        "shard_id": shard_id,
        "sha256": digest,
        "block_count": len(validated_blocks),
        "trajectory_count": trajectory_count,
        "engineering_errors": engineering,
        "integrity_errors": integrity,
    }


def _assert_recoverable_attempts(
    config: Mapping[str, Any], shard_id: str, *, resume: bool
) -> None:
    root = config["_out"] / "attempts" / f"shard_{int(shard_id.split('|')[1]):02d}"
    attempts = sorted(path for path in root.glob("*") if path.is_dir())
    if not attempts:
        return
    if not resume:
        raise RuntimeError(f"partial R484 attempt requires authorized resume: {shard_id}")
    for attempt in attempts:
        if (attempt / "failure.json").exists():
            raise RuntimeError(
                f"retained R484 explicit failure forbids retry: {shard_id}|{attempt.name}"
            )


def _validate_checkpoint_metadata(
    metadata: Mapping[str, Any], *, arm: str, base_state_sha256: str
) -> None:
    expected = {
        "round": SOURCE_ROUND,
        "stage": "final",
        "arm_id": arm,
        "base_state_sha256": base_state_sha256,
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise RuntimeError(f"R483 checkpoint metadata mismatch: {arm}|{key}")


def run_shard(
    config: Mapping[str, Any], shard_id: str, *, resume: bool = False
) -> dict[str, Any]:
    """Evaluate one seal-bound shard; no training or outcome-based selection.

    Every six-trajectory policy/profile block is published immediately.  A
    trajectory-level ANDES/TDS failure is data, not a shard exception: the
    environment has already been closed by ``_run_trajectory`` and the next
    registered trajectory is attempted with a newly built environment.  Only
    unrecoverable orchestration or storage failures leave the shard incomplete.
    Because launch-eval admits exactly sixteen shards into sixteen worker slots,
    no failed shard can prevent another registered shard from starting.
    """

    _assert_wsl_scratch()
    # The launcher verifies the complete 208-checkpoint inventory once before
    # starting all sixteen shards.  Each shard then revalidates its own thirteen
    # cells below, avoiding sixteen redundant full-inventory hash scans.
    seal = load_seal(
        config, verify_checkpoint_inventory=False, require_runtime=True
    )
    work = assigned_work(config, shard_id)
    final_path = _shard_path(config, shard_id)
    if final_path.exists() or Path(f"{final_path}.sha256").exists():
        if not resume:
            raise FileExistsError(f"R484 shard already published: {shard_id}")
        validated = _validate_published_shard(config, shard_id)
        return {**validated, "reused_completed": True}
    _assert_recoverable_attempts(config, shard_id, resume=resume)
    attempt_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ") + f"-{os.getpid()}"
    attempt = (
        config["_out"]
        / "attempts"
        / f"shard_{work['shard_index']:02d}"
        / attempt_id
    )
    attempt.mkdir(parents=True)
    block_rows: list[dict[str, Any]] = []
    try:
        _r483, runtime, _r483_config = _runtime_bundle()
        core = runtime.base.base.base.core
        contract = build_contract(config)
        profiles = _profiles_by_id(contract)
        inventory = seal["r483_checkpoint_inventory"]
        for arm, seed in work["learned_cells"]:
            cell_specs = [
                spec
                for spec in _block_specs(config, shard_id)
                if spec["kind"] == "learned"
                and spec["arm_id"] == arm
                and spec["training_seed"] == seed
            ]
            missing_specs: list[dict[str, Any]] = []
            for spec in cell_specs:
                reused = _existing_block(
                    config, shard_id, spec, resume=resume
                )
                if reused is None:
                    missing_specs.append(spec)
                else:
                    block_rows.append(reused)
            if not missing_specs:
                continue
            source = inventory[f"{arm}|{seed}"]
            manifest_path = ROOT / source["manifest_path"]
            checkpoint = ROOT / source["checkpoint_path"]
            if _validate_sidecar(manifest_path, source["manifest_sha256"]) != source[
                "manifest_sha256"
            ]:
                raise RuntimeError(f"R483 training manifest drift: {arm}|{seed}")
            if _validate_sidecar(checkpoint, source["checkpoint_sha256"]) != source[
                "checkpoint_sha256"
            ]:
                raise RuntimeError(f"R483 checkpoint drift: {arm}|{seed}")
            wrapper = core.FactorialWrapper(arm)
            metadata = wrapper.load(checkpoint)
            _validate_checkpoint_metadata(
                metadata,
                arm=arm,
                base_state_sha256=source["base_state_sha256"],
            )
            for spec in missing_specs:
                profile = profiles[str(spec["profile_id"])]
                records: list[dict[str, Any]] = []
                for scenario in profile["scenarios"]:
                    record = _run_trajectory(
                        runtime,
                        profile=profile,
                        scenario=scenario,
                        policy_id=arm,
                        factorial_arm=arm,
                        seed=seed,
                        wrapper=wrapper,
                        checkpoint_sha256=source["checkpoint_sha256"],
                        training_manifest_sha256=source["manifest_sha256"],
                    )
                    _attach_prefix_isolation(config, record)
                    records.append(record)
                block_rows.append(
                    _publish_block(config, shard_id, spec, records)
                )
                del records
            del wrapper
        comparator_specs = [
            spec
            for spec in _block_specs(config, shard_id)
            if spec["kind"] == "comparator"
        ]
        for spec in comparator_specs:
            reused = _existing_block(config, shard_id, spec, resume=resume)
            if reused is not None:
                block_rows.append(reused)
                continue
            profile = profiles[str(spec["profile_id"])]
            records = []
            for scenario in profile["scenarios"]:
                record = _run_trajectory(
                    runtime,
                    profile=profile,
                    scenario=scenario,
                    policy_id=str(spec["policy_id"]),
                )
                _attach_prefix_isolation(config, record)
                records.append(record)
            block_rows.append(_publish_block(config, shard_id, spec, records))
            del records
        by_block_id = {str(row["block_id"]): row for row in block_rows}
        specs = _block_specs(config, shard_id)
        if len(by_block_id) != len(specs):
            raise RuntimeError(f"R484 shard block roster mismatch: {shard_id}")
        ordered_rows = [by_block_id[_block_id(spec)] for spec in specs]
        trajectory_count = sum(int(row["trajectory_count"]) for row in ordered_rows)
        if trajectory_count != int(work["expected_trajectories"]):
            raise RuntimeError(f"R484 shard trajectory roster mismatch: {shard_id}")
        engineering = [
            error for row in ordered_rows for error in row["engineering_errors"]
        ]
        integrity = [
            error for row in ordered_rows for error in row["integrity_errors"]
        ]
        indexed_rows = [
            {
                key: row[key]
                for key in (
                    "block_id",
                    "path",
                    "sha256",
                    "trajectory_count",
                    "engineering_errors",
                    "integrity_errors",
                )
            }
            for row in ordered_rows
        ]
        digest = write_new_json(
            final_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "shard_id": shard_id,
                "seal_sha256": sha256_file(config["authority"]["seal"]),
                "work": work,
                "block_count": len(indexed_rows),
                "trajectory_count": trajectory_count,
                "blocks": indexed_rows,
                "engineering_errors": engineering,
                "integrity_errors": integrity,
                "reward_used_for_gate": False,
                "training_executed": False,
                "created_utc": datetime.now(UTC).isoformat(),
            },
        )
        write_new_json(
            attempt / "published.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "shard_id": shard_id,
                "final_path": _relative(final_path),
                "sha256": digest,
                "block_count": len(indexed_rows),
                "trajectory_count": trajectory_count,
                "engineering_error_count": len(engineering),
                "integrity_error_count": len(integrity),
                "created_utc": datetime.now(UTC).isoformat(),
            },
        )
        return {
            "round": ROUND_ID,
            "shard_id": shard_id,
            "sha256": digest,
            "block_count": len(indexed_rows),
            "trajectory_count": trajectory_count,
            "engineering_errors": engineering,
            "integrity_errors": integrity,
            "reused_completed": False,
        }
    except Exception as error:
        failure_path = attempt / "failure.json"
        if not failure_path.exists() and not Path(f"{failure_path}.sha256").exists():
            write_new_json(
                failure_path,
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "shard_id": shard_id,
                    "failure_type": type(error).__name__,
                    "failure": str(error)[:2000],
                    "completed_blocks_before_failure": len(block_rows),
                    "completed_trajectories_before_failure": sum(
                        int(row.get("trajectory_count", 0)) for row in block_rows
                    ),
                    "created_utc": datetime.now(UTC).isoformat(),
                },
            )
        raise


def _pre_attempt_checks(config: Mapping[str, Any]) -> dict[str, Any]:
    _preseal_authority(config)
    runtime = _installed_runtime()
    inventory = _checkpoint_inventory(config)
    checks = {
        "source_hash": bool(_source_paths(config)),
        "parent_hash": len(_verify_identity_inputs(config)) == 7,
        "checkpoint_inventory": len(inventory) == 208,
        "installed_package": runtime["andes_version"] != "unknown",
        "installed_case": Path(runtime["case_path"]).is_file(),
        "output_absence": not config["_out"].exists(),
        "active_plan": _round_state(config["authority"]["plan"]) == "active",
        "owner_approved": True,
        "shard_roster": evaluation_shard_ids(config)
        == json.loads(config["authority"]["shards"].read_text(encoding="utf-8")),
        "trajectory_count": sum(
            assigned_work(config, shard_id)["expected_trajectories"]
            for shard_id in evaluation_shard_ids(config)
        )
        == EXPECTED_TRAJECTORIES,
    }
    if not all(checks.values()):
        raise RuntimeError(f"R484 pre-attempt checks failed: {checks}")
    return {"checks": checks, "runtime": runtime}


def rehearse(config: Mapping[str, Any]) -> str:
    _assert_wsl_scratch()
    target = config["authority"]["rehearsal"]
    if target.exists() or Path(f"{target}.sha256").exists():
        raise FileExistsError(f"R484 rehearsal already exists: {target}")
    pre_attempt = _pre_attempt_checks(config)
    contract = build_contract(config)
    profile = _profiles_by_id(contract)[CANARY_PROFILES[0]]
    scenario = profile["scenarios"][0]
    _r483, runtime, _r483_config = _runtime_bundle()
    started = time.perf_counter()
    record = _run_trajectory(
        runtime,
        profile=profile,
        scenario=scenario,
        policy_id="zero",
    )
    _validate_trajectory(record)
    done_indices = [
        index
        for index, row in enumerate(record["steps"])
        if bool(row.get("done", False))
    ]
    return write_new_json(
        target,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "phase": "same-pre-attempt-path-rehearsal",
            **pre_attempt,
            "rehearsal_scope": "one canary zero-action trajectory at 150 steps",
            "representative": {
                "profile_id": record["profile_id"],
                "scenario_id": record["scenario_id"],
                "completed_steps": record["completed_steps"],
                "completed": record["completed"],
                "tds_failed": record["tds_failed"],
                "configured_steps_per_episode": EXPECTED_STEPS,
                "done_indices": done_indices,
                "done_only_at_step_149": done_indices == [EXPECTED_STEPS - 1],
            },
            "elapsed_seconds": time.perf_counter() - started,
            "formal_attempt_created": False,
            "formal_outputs_created": False,
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )


def _memory_snapshot() -> dict[str, Any]:
    values: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        key, raw = line.split(":", 1)
        token = raw.strip().split()[0]
        values[key] = int(token)
    return {
        "mem_total_kib": values["MemTotal"],
        "mem_available_kib": values["MemAvailable"],
        "mem_total_gib": values["MemTotal"] / (1024**2),
        "mem_available_gib": values["MemAvailable"] / (1024**2),
        "logical_cpus": int(os.cpu_count() or 0),
    }


def _capacity_jobs(
    contract: Mapping[str, Any],
    inventory: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    profiles = _profiles_by_id(contract)
    learned_cells = (
        (FACTORIAL_ARMS[0], SEEDS[0]),
        (FACTORIAL_ARMS[2], SEEDS[7]),
        (FACTORIAL_ARMS[5], SEEDS[16]),
        (FACTORIAL_ARMS[7], SEEDS[-1]),
    )
    jobs: list[dict[str, Any]] = []
    for index, (arm, seed) in enumerate(learned_cells):
        profile = profiles[CANARY_PROFILES[index]]
        jobs.append(
            {
                "kind": "learned",
                "job_id": f"learned|{arm}|{seed}|{profile['profile_id']}",
                "arm_id": arm,
                "training_seed": seed,
                "source": dict(inventory[f"{arm}|{seed}"]),
                "profile": profile,
                "scenario": profile["scenarios"][index],
            }
        )
    comparator_choices = (
        (CANARY_PROFILES[0], COMPARATORS[0], 0),
        (CANARY_PROFILES[1], COMPARATORS[1], 1),
        (FRESH_PROFILES[0], COMPARATORS[0], 2),
        (FRESH_PROFILES[1], COMPARATORS[1], 3),
    )
    for profile_id, policy_id, scenario_index in comparator_choices:
        profile = profiles[profile_id]
        jobs.append(
            {
                "kind": "comparator",
                "job_id": f"comparator|{policy_id}|{profile_id}",
                "policy_id": policy_id,
                "profile": profile,
                "scenario": profile["scenarios"][scenario_index],
            }
        )
    return jobs


def capacity(config: Mapping[str, Any]) -> str:
    _assert_wsl_scratch()
    target = config["authority"]["capacity"]
    if target.exists() or Path(f"{target}.sha256").exists():
        raise FileExistsError(f"R484 capacity evidence already exists: {target}")
    rehearsal_payload, _ = read_verified_json(config["authority"]["rehearsal"])
    if rehearsal_payload.get("representative", {}).get("completed") is not True:
        raise RuntimeError("R484 rehearsal did not pass")
    contract = build_contract(config)
    inventory = _checkpoint_inventory(config)
    jobs = _capacity_jobs(contract, inventory)
    for job in jobs:
        job["config_path"] = str(config["_path"])
    memory_before = _memory_snapshot()
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=WORKERS) as executor:
        records = list(executor.map(_run_capacity_job, jobs))
    wall = time.perf_counter() - started
    memory_after = _memory_snapshot()
    valid = all(
        record.get("completed") is True
        and record.get("tds_failed") is False
        and record.get("prefix_isolation", {}).get("passed") is True
        for record in records
    )
    rss_values = [int(record.get("worker_max_rss_kib", 0)) for record in records]
    output_bytes = len(
        json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    maximum_rss = max(rss_values, default=0)
    projected_worker_rss_gib = maximum_rss * WORKERS / (1024**2)
    required_available_gib = 2.0 + 1.25 * projected_worker_rss_gib
    memory_safe = (
        float(memory_before["mem_available_gib"]) >= required_available_gib
        and float(memory_after["mem_available_gib"]) >= 2.0
    )
    safe_for_formal_launch = bool(valid and memory_safe and len(records) == 8)
    return write_new_json(
        target,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "quick_confirm": {
                "workers": WORKERS,
                "jobs": len(records),
                "steps_per_job": EXPECTED_STEPS,
                "wall_seconds": wall,
                "all_records_valid": bool(valid),
                "job_mix": {
                    "learned_final": sum(
                        record.get("capacity_job_kind") == "learned"
                        for record in records
                    ),
                    "comparator": sum(
                        record.get("capacity_job_kind") == "comparator"
                        for record in records
                    ),
                },
                "job_ids": [str(record["capacity_job_id"]) for record in records],
                "failures": [
                    record.get("failure")
                    for record in records
                    if record.get("completed") is not True
                    or record.get("tds_failed") is not False
                ],
            },
            "memory": {
                "before": memory_before,
                "after": memory_after,
                "worker_max_rss_kib": rss_values,
                "maximum_worker_rss_kib": maximum_rss,
                "median_worker_rss_kib": statistics.median(rss_values),
                "projected_sixteen_worker_rss_gib": projected_worker_rss_gib,
                "required_available_gib_with_25pct_and_2gib_reserve": (
                    required_available_gib
                ),
                "memory_safe": memory_safe,
            },
            "output": {
                "estimated_json_bytes": output_bytes,
                "estimated_json_bytes_per_second": output_bytes / max(wall, 1.0e-9),
            },
            "selected": {
                "workers": WORKERS,
                "launcher_processes": 1,
                "native_threads_per_process": 1,
                "reason": (
                    "R452-R483 16-worker precedent plus this round's "
                    "16x8 150-step quick confirmation"
                ),
            },
            "whole_host_python_process_budget": WORKERS + 2,
            "other_reserved_processes": 0,
            "safe_for_formal_launch": safe_for_formal_launch,
            "capacity_trace_role": "non-claim-bearing quick confirmation",
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )


def _assert_capacity_safe(config: Mapping[str, Any]) -> None:
    payload, _ = read_verified_json(config["authority"]["capacity"])
    if payload.get("safe_for_formal_launch") is not True:
        raise RuntimeError("R484 capacity evidence does not authorize formal launch")


def _formal_attempt(config: Mapping[str, Any], *, resume: bool) -> str:
    path = config["_out"] / "formal_attempt.json"
    seal_sha = sha256_file(config["authority"]["seal"])
    if path.exists() or Path(f"{path}.sha256").exists():
        if not resume:
            raise FileExistsError("R484 formal attempt already exists")
        payload, digest = read_verified_json(path)
        expected = {
            "round": ROUND_ID,
            "seal_sha256": seal_sha,
            "shard_count": WORKERS,
            "expected_trajectories": EXPECTED_TRAJECTORIES,
        }
        if any(payload.get(key) != value for key, value in expected.items()):
            raise RuntimeError("R484 retained formal attempt identity mismatch")
        return digest
    if resume:
        raise RuntimeError("R484 resume requested without a retained formal attempt")
    return write_new_json(
        path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "started_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_sha,
            "shard_count": WORKERS,
            "expected_trajectories": EXPECTED_TRAJECTORIES,
            "workers": WORKERS,
            "scientific_outcomes_inspected": False,
            "reward_used_for_gate": False,
            "training_executed": False,
        },
    )


def launch_queue(config: Mapping[str, Any], *, resume: bool) -> dict[str, Any]:
    _assert_wsl_scratch()
    load_seal(config, require_runtime=True)
    _assert_capacity_safe(config)
    if not resume and config["_out"].exists():
        raise FileExistsError(f"R484 output root already exists: {config['_out']}")
    attempt_sha = _formal_attempt(config, resume=resume)
    command = [
        sys.executable,
        str(ROOT / "scripts/adaptive_shard_driver.py"),
        "--runner",
        str(Path(__file__).resolve()),
        "--runner-arg=--config",
        f"--runner-arg={config['_path'].relative_to(ROOT).as_posix()}",
        "--shards",
        str(config["authority"]["shards"]),
        "--workers",
        str(WORKERS),
        "--round",
        ROUND_ID,
        "--log-dir",
        str(config["_eval_log_dir"]),
    ]
    if resume:
        command.append("--resume")
    completed = subprocess.run(command, cwd=ROOT, check=False)
    return {
        "round": ROUND_ID,
        "kind": "eval",
        "resume": resume,
        "workers": WORKERS,
        "formal_attempt_sha256": attempt_sha,
        "exit_code": int(completed.returncode),
    }


def check_results(
    config: Mapping[str, Any], *, verify_seal: bool = True
) -> dict[str, Any]:
    if verify_seal:
        load_seal(config)
    valid: list[dict[str, Any]] = []
    errors: list[str] = []
    engineering_errors: list[str] = []
    integrity_errors: list[str] = []
    total = 0
    total_blocks = 0
    for shard_id in evaluation_shard_ids(config):
        try:
            row = _validate_published_shard(config, shard_id)
            valid.append(row)
            total += int(row["trajectory_count"])
            total_blocks += int(row["block_count"])
            engineering_errors.extend(
                f"{shard_id}:{error}" for error in row["engineering_errors"]
            )
            integrity_errors.extend(
                f"{shard_id}:{error}" for error in row["integrity_errors"]
            )
        except Exception as error:
            errors.append(f"{shard_id}: {type(error).__name__}: {error}")
    if total != EXPECTED_TRAJECTORIES:
        errors.append(f"trajectory_count: {total} != {EXPECTED_TRAJECTORIES}")
    expected_blocks = 208 * len(CANARY_PROFILES) + 16
    if total_blocks != expected_blocks:
        errors.append(f"block_count: {total_blocks} != {expected_blocks}")
    return {
        "round": ROUND_ID,
        "expected_shards": WORKERS,
        "valid_shards": len(valid),
        "expected_blocks": expected_blocks,
        "valid_blocks": total_blocks,
        "expected_trajectories": EXPECTED_TRAJECTORIES,
        "valid_trajectories": total,
        "errors": errors,
        "engineering_errors": engineering_errors,
        "integrity_errors": integrity_errors,
        "shards": valid,
    }


def _summaries(config: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    from andes_rl_kundur.evaluation.r484_tail_guard import summarise_30s_profile

    contract = build_contract(config)
    summaries: list[dict[str, Any]] = []
    errors: list[str] = []
    for shard_id in evaluation_shard_ids(config):
        for spec in _block_specs(config, shard_id):
            try:
                payload, _ = read_verified_json(_block_path(config, shard_id, spec))
                records = payload.get("records")
                if not isinstance(records, list):
                    raise RuntimeError("block has no records")
                summary = summarise_30s_profile(
                    records, contract=contract, expected_steps=EXPECTED_STEPS
                )
                summary["bank"] = str(spec["bank"])
                first = records[0]
                summary["factorial_arm_id"] = first.get("factorial_arm_id")
                summary["training_seed"] = first.get("training_seed")
                summary["checkpoint_sha256"] = first.get("checkpoint_sha256")
                summary["training_manifest_sha256"] = first.get(
                    "training_manifest_sha256"
                )
                summaries.append(summary)
                del records
            except Exception as error:
                errors.append(
                    f"{shard_id}|{_block_id(spec)}: {type(error).__name__}: {error}"
                )
    if len(summaries) != 848:
        errors.append(f"summary_count: {len(summaries)} != 848")
    return summaries, errors


def aggregate(config: Mapping[str, Any]) -> str:
    from andes_rl_kundur.evaluation.r484_tail_guard import (
        analyse_tail_factorial,
        classify_deterministic_tail,
        classify_learned_guard,
        classify_r484,
    )

    load_seal(config)
    checked = check_results(config, verify_seal=False)
    engineering_errors = [
        *checked.get("errors", []),
        *checked.get("engineering_errors", []),
    ]
    integrity_errors = list(checked.get("integrity_errors", []))
    if engineering_errors or integrity_errors:
        summaries: list[dict[str, Any]] = []
        summary_errors: list[str] = []
    else:
        summaries, summary_errors = _summaries(config)
        integrity_errors.extend(summary_errors)
    routing, _ = read_verified_json(config["authority"]["routing_gate"])
    valid_shard_ids = {str(row["shard_id"]) for row in checked["shards"]}
    missing_shards = [
        shard_id
        for shard_id in evaluation_shard_ids(config)
        if shard_id not in valid_shard_ids
    ]
    contract = build_contract(config)
    policy_roster = _all_cells()
    canary = [row for row in summaries if row.get("bank") == "canary"]
    fresh = [row for row in summaries if row.get("bank") == "fresh"]
    learned_guard: dict[str, Any] | None = None
    fresh_tail: dict[str, Any] | None = None
    canary_tail: dict[str, Any] | None = None
    factorial: dict[str, Any] | None = None
    classification: dict[str, Any]
    if not engineering_errors and not integrity_errors:
        fresh_contract = {
            **contract,
            "profiles": [
                row
                for row in contract["profiles"]
                if row["profile_id"] in FRESH_PROFILES
            ],
        }
        fresh_tail = classify_deterministic_tail(
            fresh,
            contract=fresh_contract,
            selected_arm=COMPARATORS[1],
            expected_profiles=list(FRESH_PROFILES),
            bank_name="fresh",
        )
        canary_comparators = [
            row for row in canary if row.get("arm_id") in set(COMPARATORS)
        ]
        canary_contract = {
            **contract,
            "profiles": [
                row
                for row in contract["profiles"]
                if row["profile_id"] in CANARY_PROFILES
            ],
        }
        canary_tail = classify_deterministic_tail(
            canary_comparators,
            contract=canary_contract,
            selected_arm=COMPARATORS[1],
            expected_profiles=list(CANARY_PROFILES),
            bank_name="canary",
        )
        learned_and_reference = [
            row
            for row in canary
            if row.get("training_seed") is not None
            or row.get("arm_id") == COMPARATORS[1]
        ]
        learned_guard = classify_learned_guard(
            learned_and_reference,
            policies=policy_roster,
            profiles=list(CANARY_PROFILES),
            deterministic_arm=COMPARATORS[1],
            thresholds=contract["thresholds"],
            deterministic_reference_gate=canary_tail,
        )
        factorial_rows: list[dict[str, Any]] = []
        for row in canary:
            if row.get("factorial_arm_id") is None:
                continue
            arm_id = str(row["factorial_arm_id"])
            factorial_row = dict(row)
            factorial_row.update(
                {
                    "arm_id": arm_id,
                    "seed": int(row["training_seed"]),
                    "actor_source": arm_id.split("_")[0][1:].upper(),
                    "critic_source": arm_id.split("_")[1][1:].upper(),
                    "reward_access": int(arm_id.endswith("r1")),
                    "profile": str(row["profile_id"]),
                }
            )
            factorial_rows.append(factorial_row)
        factorial = analyse_tail_factorial(
            factorial_rows,
            expected_seeds=list(SEEDS),
            expected_profiles=list(CANARY_PROFILES),
        )
        classification = classify_r484(
            design_valid=routing.get("passed") is True,
            missing_shards=missing_shards,
            engineering_errors=[],
            integrity_errors=[],
            learned_guard=learned_guard,
            fresh_tail=fresh_tail,
            canary_tail=canary_tail,
            tail_factorial=factorial,
        )
    else:
        classification = classify_r484(
            design_valid=routing.get("passed") is True,
            missing_shards=missing_shards,
            engineering_errors=engineering_errors,
            integrity_errors=integrity_errors,
            learned_guard=None,
            fresh_tail=None,
            canary_tail=None,
            tail_factorial=None,
        )
    return write_new_json(
        config["_out"] / "formal_analysis.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "seal_sha256": sha256_file(config["authority"]["seal"]),
            "formal_attempt_sha256": sha256_file(config["_out"] / "formal_attempt.json"),
            "contract_sha256": contract_sha256(config),
            "execution": checked,
            "summary_errors": summary_errors,
            "summary_count": len(summaries),
            "learned_guard": learned_guard,
            "deterministic_fresh_tail": fresh_tail,
            "deterministic_canary_tail_descriptive": canary_tail,
            "tail_factorial_sensitivity": factorial,
            "classification": classification,
            "reward_used_for_gate": False,
            "training_executed": False,
            "claim_scope": contract["claim_scope"],
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )


def formal_manifest(config: Mapping[str, Any]) -> str:
    load_seal(config)
    checked = check_results(config, verify_seal=False)
    if (
        checked["errors"]
        or checked["engineering_errors"]
        or checked["integrity_errors"]
        or checked["valid_shards"] != WORKERS
    ):
        raise RuntimeError("cannot finalize incomplete R484 evaluation")
    analysis, _ = read_verified_json(config["_out"] / "formal_analysis.json")
    overall = analysis.get("classification", {})
    if (
        analysis.get("execution", {}).get("errors")
        or analysis.get("summary_errors")
        or not isinstance(overall, Mapping)
        or overall.get("classification") != "R484-VALID"
        or overall.get("scientific_results_valid") is not True
    ):
        raise RuntimeError("cannot finalize invalid R484 analysis")
    entries: list[dict[str, Any]] = []
    for path in sorted(config["_out"].rglob("*")):
        if (
            not path.is_file()
            or path.name == "formal_manifest.json"
            or path.name.endswith(".sha256")
            or "attempts" in path.relative_to(config["_out"]).parts
        ):
            continue
        sidecar = Path(f"{path}.sha256")
        digest = sha256_file(path)
        if not sidecar.is_file() or sidecar.read_text(encoding="ascii").split()[0] != digest:
            raise RuntimeError(f"missing/invalid R484 result sidecar: {path}")
        entries.append(
            {
                "path": _relative(path),
                "sha256": digest,
                "bytes": path.stat().st_size,
            }
        )
    return write_new_json(
        config["_out"] / "formal_manifest.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "evaluation_only": True,
            "training_executed": False,
            "entry_count": len(entries),
            "total_bytes": sum(int(row["bytes"]) for row in entries),
            "entries": entries,
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument(
        "command",
        choices=(
            "contract",
            "seal-inputs",
            "shards",
            "rehearse",
            "capacity",
            "authority",
            "shard",
            "launch-eval",
            "check",
            "aggregate",
            "manifest",
        ),
    )
    parser.add_argument("shard_id", nargs="?")
    parser.add_argument("--resume", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    config = load_config(config_path)
    if args.command == "contract":
        payload: Any = build_contract(config)
    elif args.command == "seal-inputs":
        payload = seal_inputs(config)
    elif args.command == "shards":
        payload = evaluation_shard_ids(config)
    elif args.command == "rehearse":
        payload = {"rehearsal_sha256": rehearse(config)}
    elif args.command == "capacity":
        payload = {"capacity_sha256": capacity(config)}
    elif args.command == "authority":
        payload = load_seal(config)
    elif args.command == "shard":
        if args.shard_id is None:
            raise SystemExit("shard command requires a shard id")
        payload = run_shard(config, args.shard_id, resume=args.resume)
    elif args.command == "launch-eval":
        payload = launch_queue(config, resume=args.resume)
    elif args.command == "check":
        payload = check_results(config)
    elif args.command == "aggregate":
        payload = {"formal_analysis_sha256": aggregate(config)}
    else:
        payload = {"formal_manifest_sha256": formal_manifest(config)}
    print(json.dumps(payload, indent=2, sort_keys=True), flush=True)
    if isinstance(payload, dict) and payload.get("errors"):
        return 1
    if isinstance(payload, dict) and int(payload.get("exit_code", 0)) != 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
