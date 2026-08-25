"""Prospective runner for a formally authorized adaptive-stop U2 successor.

This file cannot grant itself authority. A fresh, atomically reserved round
must bind its plan, owner approval, dual reviews over a committed snapshot,
preflight artifacts, source R482 artifacts, power artifact, probe bank, config,
and exact shard list through the repository's shared formal-seal verifier.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from andes_rl_kundur.evaluation.u2_confirmatory import verify_formal_seal
from andes_rl_kundur.training.adaptive_stop import AdaptiveStopConfig, AdaptiveStopMonitor
from andes_rl_kundur.training.adaptive_u2 import (
    config_sha256,
    create_probe_bank,
    sha256_file,
    train_cell,
)

SOURCE_ROUND = "R482"
SOURCE_PLAN = ROOT / "memory/rounds/R482/plan.md"
SOURCE_SEAL = ROOT / "memory/rounds/R482/formal_seal.json"
SOURCE_BASE_AUDIT = ROOT / "memory/rounds/R482/base_audit.json"
SOURCE_OUT = ROOT / "results/research_loop/r482_u2_confirmatory"
ALLOWED_ARMS = tuple(
    f"{actor}_{critic}_{reward}"
    for actor in ("an", "ap")
    for critic in ("cn", "cp")
    for reward in ("r0", "r1")
) + ("an_cn_r1_rms",)
RECOVERY_POLICY = "preserve_partial_new_attempt_reuse_completed"
TERMINAL_ROUND_STATES = {"completed", "aborted", "superseded"}
FACTORIAL_REWARD_SHA256 = "085ad375c203352d72e58847ca7b01297415b214adf41196dcb7783c7adb7bd9"


def _resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _repo_path(value: str | Path) -> Path:
    path = _resolve(value).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"configured path escapes repository: {value}") from exc
    return path


def _load_runtime() -> Any:
    spec = importlib.util.spec_from_file_location(
        "_adaptive_r482_runtime", ROOT / "scripts/run_r482_u2_confirmatory.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R482-compatible runtime")
    runtime = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runtime
    spec.loader.exec_module(runtime)
    return runtime


def load_config(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "round",
        "source_round",
        "out",
        "source_out",
        "seal",
        "power",
        "probe_bank",
        "probe_bank_sha256",
        "stop_config",
        "cells",
        "recovery_policy",
        "authority",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"adaptive config missing keys: {missing}")
    if payload["schema_version"] != 2:
        raise ValueError("unsupported adaptive config schema")
    round_id = payload["round"]
    if not isinstance(round_id, str) or re.fullmatch(r"R[0-9]+", round_id) is None:
        raise ValueError("invalid successor round id")
    if round_id == SOURCE_ROUND or payload["source_round"] != SOURCE_ROUND:
        raise ValueError("adaptive execution requires a fresh successor of R482")
    if _repo_path(payload["source_out"]) != SOURCE_OUT.resolve():
        raise ValueError("source_out must be the immutable R482 result root")
    if payload["recovery_policy"] != RECOVERY_POLICY:
        raise ValueError("unsupported or unsealed recovery policy")
    stop = AdaptiveStopConfig(**dict(payload["stop_config"]))
    if stop.min_steps <= stop.max_steps // 2:
        raise ValueError("min_steps must preserve the max-budget half checkpoint")
    cells = payload["cells"]
    if not isinstance(cells, list) or not cells:
        raise ValueError("cells must be a non-empty list")
    identities: list[tuple[str, int]] = []
    for row in cells:
        if not isinstance(row, dict) or set(row) != {"arm_id", "seed"}:
            raise ValueError("each cell must contain exactly arm_id and seed")
        identity = (str(row["arm_id"]), int(row["seed"]))
        if identity[0] not in ALLOWED_ARMS or identity[1] < 1:
            raise ValueError(f"invalid adaptive cell: {identity}")
        identities.append(identity)
    if len(set(identities)) != len(identities):
        raise ValueError("adaptive config contains duplicate cells")
    configured_arms = {arm for arm, _seed in identities}
    configured_seeds = {seed for _arm, seed in identities}
    rectangular_roster = {(arm, seed) for arm in configured_arms for seed in configured_seeds}
    if set(identities) != rectangular_roster:
        raise ValueError(
            "adaptive cells must form a balanced arm-by-seed roster; "
            "fixed-budget source cells cannot fill adaptive gaps"
        )
    authority = payload["authority"]
    authority_keys = {
        "plan",
        "owner_approval",
        "routing_gate",
        "rehearsal",
        "capacity",
        "review_a",
        "review_b",
        "train_shard_list",
        "eval_shard_list",
    }
    if not isinstance(authority, dict) or set(authority) != authority_keys:
        raise ValueError(f"authority must contain exactly {sorted(authority_keys)}")
    expected_plan = ROOT / f"memory/rounds/{round_id}/plan.md"
    if _repo_path(authority["plan"]) != expected_plan.resolve():
        raise ValueError("successor plan path does not match round id")
    for key, value in authority.items():
        authority[key] = _repo_path(value)
    for key in ("out", "source_out", "seal", "power", "probe_bank"):
        payload[f"_{key}"] = _repo_path(payload[key])
    payload["_path"] = path.resolve()
    payload["_stop"] = stop
    payload["_cells"] = tuple(identities)
    return payload


def _config_file_sha(config: dict[str, Any]) -> str:
    return sha256_file(config["_path"])


def _implementation_files() -> dict[str, Path]:
    files = {
        "runner": Path(__file__).resolve(),
        "training_package": ROOT / "src/andes_rl_kundur/training/__init__.py",
        "adaptive_stop": ROOT / "src/andes_rl_kundur/training/adaptive_stop.py",
        "adaptive_u2": ROOT / "src/andes_rl_kundur/training/adaptive_u2.py",
        "dynamic_driver": ROOT / "scripts/adaptive_shard_driver.py",
        "r482_runtime": ROOT / "scripts/run_r482_u2_confirmatory.py",
        "formal_seal_verifier": ROOT / "src/andes_rl_kundur/evaluation/u2_confirmatory.py",
        "source_r482_plan": SOURCE_PLAN,
        "source_r482_seal": SOURCE_SEAL,
        "source_r482_base_audit": SOURCE_BASE_AUDIT,
        "test_adaptive_stop": ROOT / "tests/test_adaptive_stop.py",
        "test_adaptive_u2": ROOT / "tests/test_adaptive_u2.py",
        "test_dynamic_driver": ROOT / "tests/test_adaptive_shard_driver.py",
        "test_successor_runner": ROOT / "tests/test_run_adaptive_u2_successor.py",
    }
    files.update(_source_sealed_files())
    return files


def _source_sealed_files() -> dict[str, Path]:
    sidecar = Path(f"{SOURCE_SEAL}.sha256")
    if sha256_file(SOURCE_SEAL) != sidecar.read_text(encoding="ascii").split()[0]:
        raise RuntimeError("R482 formal seal hash mismatch")
    seal = json.loads(SOURCE_SEAL.read_text(encoding="utf-8"))
    files: dict[str, Path] = {}
    for name, row in seal.get("sources", {}).items():
        if not isinstance(row, dict):
            raise RuntimeError(f"invalid R482 source entry: {name}")
        path = _repo_path(row.get("path", ""))
        if not path.is_file() or sha256_file(path) != row.get("sha256"):
            raise RuntimeError(f"R482 sealed source drift: {path}")
        files[f"r482_source_{name}"] = path
    if not files:
        raise RuntimeError("R482 formal seal has no source map")
    return files


def _source_base_inventory(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    seal_sidecar = Path(f"{SOURCE_SEAL}.sha256")
    if sha256_file(SOURCE_SEAL) != seal_sidecar.read_text(encoding="ascii").split()[0]:
        raise RuntimeError("R482 formal seal hash mismatch")
    source_seal = json.loads(SOURCE_SEAL.read_text(encoding="utf-8"))
    audit_sidecar = Path(f"{SOURCE_BASE_AUDIT}.sha256")
    audit_sha = sha256_file(SOURCE_BASE_AUDIT)
    if audit_sha != audit_sidecar.read_text(encoding="ascii").split()[0]:
        raise RuntimeError("R482 base audit hash mismatch")
    _verify_source_audit_anchor(source_seal, audit_sha)
    audit = json.loads(SOURCE_BASE_AUDIT.read_text(encoding="utf-8"))
    if audit.get("round") != SOURCE_ROUND or audit.get("passed") is not True:
        raise RuntimeError("R482 base audit is not authoritative")
    inventory: dict[str, dict[str, str]] = {}
    for seed in sorted({seed for _arm, seed in config["_cells"]}):
        manifest_path = config["_source_out"] / "donors" / f"seed{seed}" / "manifest.json"
        sidecar = Path(f"{manifest_path}.sha256")
        expected = sidecar.read_text(encoding="ascii").split()[0]
        manifest_sha = sha256_file(manifest_path)
        if manifest_sha != expected:
            raise RuntimeError(f"source manifest hash mismatch: seed{seed}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("round") != SOURCE_ROUND or int(manifest["training_seed"]) != seed:
            raise RuntimeError(f"source manifest identity mismatch: seed{seed}")
        base_path = _repo_path(manifest["base_state_path"])
        base_sha = sha256_file(base_path)
        if base_sha != manifest["base_state_sha256"]:
            raise RuntimeError(f"source base hash mismatch: seed{seed}")
        relative_base = base_path.relative_to(ROOT).as_posix()
        _verify_base_audit_entry(
            audit,
            seed=seed,
            base_path=relative_base,
            base_sha256=base_sha,
        )
        expected_manifest_fields = {
            "base_rng_seed": 200_000 + seed,
            "rng_set_before_environment": True,
            "base_state_path": relative_base,
            "base_state_sha256": base_sha,
            "reward_function_sha256": FACTORIAL_REWARD_SHA256,
            "matched_arm_slots": list(ALLOWED_ARMS),
        }
        for key, value in expected_manifest_fields.items():
            if manifest.get(key) != value:
                raise RuntimeError(f"source manifest field mismatch: seed{seed}|{key}")
        inventory[str(seed)] = {
            "manifest_path": manifest_path.relative_to(ROOT).as_posix(),
            "manifest_sha256": manifest_sha,
            "base_state_path": relative_base,
            "base_state_sha256": base_sha,
        }
    return inventory


def _verify_source_audit_anchor(source_seal: dict[str, Any], audit_sha256: str) -> None:
    if (
        source_seal.get("round") != SOURCE_ROUND
        or source_seal.get("formal_authority") is not True
        or source_seal.get("base_audit_sha256") != audit_sha256
    ):
        raise RuntimeError("R482 base audit is not anchored by its formal seal")


def _verify_base_audit_entry(
    audit: dict[str, Any], *, seed: int, base_path: str, base_sha256: str
) -> None:
    row = (audit.get("bases") or {}).get(str(seed))
    if not isinstance(row, dict):
        raise RuntimeError(f"R482 base audit lacks seed{seed}")
    if row.get("path") != base_path or row.get("sha256") != base_sha256:
        raise RuntimeError(f"source base contradicts R482 base audit: seed{seed}")


def seal_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Return a non-authoritative fragment for the round's prepare step."""

    _preseal_authority(config)
    return {
        "schema_version": 2,
        "seal_fragment_only": True,
        "round": config["round"],
        "source_round": SOURCE_ROUND,
        "adaptive_config_sha256": _config_file_sha(config),
        "stop_config_sha256": config_sha256(config["_stop"]),
        "probe_bank_sha256": config["probe_bank_sha256"],
        "source_base_inventory": _source_base_inventory(config),
        "implementation_sha256": {
            name: sha256_file(path) for name, path in _implementation_files().items()
        },
    }


def rehearsal(config: dict[str, Any]) -> str:
    """Run the inherited real-ANDES seam rehearsal plus adaptive semantics."""

    _preseal_authority(config)
    runtime = _load_runtime()
    bind_runtime(runtime, config)
    core = runtime.base.base.base.core
    core._assert_wsl_scratch()
    if config["_out"].exists():
        raise RuntimeError("adaptive formal output must be absent before rehearsal")
    if not config["_probe_bank"].is_file():
        raise RuntimeError("adaptive probe bank must precede rehearsal")
    if sha256_file(config["_probe_bank"]) != config["probe_bank_sha256"]:
        raise RuntimeError("adaptive probe bank hash mismatch before rehearsal")
    source_inventory = _source_base_inventory(config)
    runtime.authority_checks = lambda: {
        "active_successor_plan": _round_state(config["authority"]["plan"]) == "active",
        "source_round_terminal": _round_state(SOURCE_PLAN) in TERMINAL_ROUND_STATES,
        "balanced_roster": len(config["_cells"])
        == len({arm for arm, _seed in config["_cells"]})
        * len({seed for _arm, seed in config["_cells"]}),
        "output_absence": not config["_out"].exists(),
    }
    inherited = runtime.rehearsal()
    width = config["_stop"].window_updates
    flat = [1.0] * (2 * width)
    curves = {name: flat for name in AdaptiveStopMonitor.REQUIRED_CURVES}
    monitor = AdaptiveStopMonitor(config["_stop"])
    decisions = [
        monitor.observe(
            interaction_steps=step,
            curves=curves,
            action_probe_drift=0.0,
            tds_failures=0,
        )
        for step in (30_000, 32_000, 34_000)
    ]
    blocked = AdaptiveStopMonitor(config["_stop"]).observe(
        interaction_steps=30_000,
        curves=curves,
        action_probe_drift=config["_stop"].action_probe_drift_tolerance + 0.01,
        tds_failures=0,
    )
    adaptive_checks = {
        "earliest_stop_is_34000": decisions[-1].should_stop
        and decisions[-1].interaction_steps == 34_000,
        "three_consecutive_checks_required": [
            row.consecutive_passes for row in decisions
        ]
        == [1, 2, 3],
        "action_drift_fails_closed": not blocked.should_stop
        and blocked.consecutive_passes == 0,
        "source_base_count": len(source_inventory) == len(
            {seed for _arm, seed in config["_cells"]}
        ),
    }
    payload = {
        "schema_version": 1,
        "round": config["round"],
        "source_round": SOURCE_ROUND,
        "inherited_real_andes": inherited,
        "adaptive_checks": adaptive_checks,
        "passed": bool(inherited.get("passed") and all(adaptive_checks.values())),
    }
    if not payload["passed"]:
        raise RuntimeError(f"adaptive rehearsal failed: {payload}")
    return core._write_new_json(config["authority"]["rehearsal"], payload)


def _round_state(plan: Path) -> str | None:
    match = re.search(r"(?m)^state:\s*([^\s]+)\s*$", plan.read_text(encoding="utf-8"))
    return None if match is None else match.group(1)


def _preseal_authority(config: dict[str, Any]) -> dict[str, Any]:
    source_state = _round_state(SOURCE_PLAN)
    if source_state not in TERMINAL_ROUND_STATES:
        raise RuntimeError(f"R482 is not in a recognized terminal state: {source_state!r}")
    plan = config["authority"]["plan"]
    if _round_state(plan) != "active":
        raise RuntimeError("successor round plan is not active")
    owner_path = config["authority"]["owner_approval"]
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    if (
        owner.get("round") != config["round"]
        or owner.get("approved") is not True
        or not isinstance(owner.get("source"), str)
        or not owner["source"].strip()
    ):
        raise RuntimeError("successor owner approval is invalid")
    return owner


def _bound_files(config: dict[str, Any]) -> dict[str, Path]:
    authority = config["authority"]
    return {
        "plan_sha256": authority["plan"],
        "owner_approval_sha256": authority["owner_approval"],
        "routing_gate_sha256": authority["routing_gate"],
        "rehearsal_sha256": authority["rehearsal"],
        "capacity_sha256": authority["capacity"],
        "code_review_a_sha256": authority["review_a"],
        "code_review_b_sha256": authority["review_b"],
        "adaptive_config_sha256": config["_path"],
        "probe_bank_sha256": config["_probe_bank"],
        "power_sha256": config["_power"],
        "source_round_plan_sha256": SOURCE_PLAN,
        "source_round_seal_sha256": SOURCE_SEAL,
        "source_base_audit_sha256": SOURCE_BASE_AUDIT,
    }


def load_seal(config: dict[str, Any], runtime: Any) -> dict[str, Any]:
    _preseal_authority(config)
    seal = verify_formal_seal(
        repo_root=ROOT,
        seal_path=config["_seal"],
        round_id=config["round"],
        contract_sha256=runtime.base.base.base.core.contract_sha256(),
        bound_files=_bound_files(config),
        review_paths=(
            config["authority"]["review_a"],
            config["authority"]["review_b"],
        ),
        reviewed_files=tuple(_implementation_files().values()),
        expected_shards={
            "train": train_shard_ids(config),
            "eval": evaluation_shard_ids(config),
        },
    )
    expected = seal_inputs(config)
    for key in (
        "round",
        "source_round",
        "adaptive_config_sha256",
        "stop_config_sha256",
        "probe_bank_sha256",
        "source_base_inventory",
        "implementation_sha256",
    ):
        if seal.get(key) != expected[key]:
            raise RuntimeError(f"adaptive formal seal binding mismatch: {key}")
    if sha256_file(config["_probe_bank"]) != config["probe_bank_sha256"]:
        raise RuntimeError("adaptive probe bank differs from frozen config")
    for kind in ("train", "eval"):
        shard_row = seal["shard_lists"][kind]
        expected_path = config["authority"][f"{kind}_shard_list"]
        if _repo_path(shard_row["path"]) != expected_path:
            raise RuntimeError(f"sealed {kind} shard-list path differs from successor config")
    return seal


def bind_runtime(runtime: Any, config: dict[str, Any]) -> None:
    """Adapt the inherited runtime behind one successor-specific contract."""

    arms = tuple(dict.fromkeys(arm for arm, _seed in config["_cells"]))
    seeds = tuple(sorted({seed for _arm, seed in config["_cells"]}))
    cells = tuple(config["_cells"])
    train_shards = tuple(train_shard_ids(config))
    original_contract_builder = runtime.build_contract
    values = {
        "ROUND_ID": config["round"],
        "OUT": config["_out"],
        "POWER": config["_power"],
        "SEEDS": seeds,
        "TRAINING_SEEDS": seeds,
        "RETRAIN_ARMS": arms,
        "RETRAIN_CELLS": cells,
        "TRAIN_SHARD_IDS": train_shards,
        "REUSE_ARMS": (),
        "REUSED_CELLS": (),
    }
    modules = (runtime, runtime.base, runtime.base.base, runtime.base.base.base)
    core = runtime.base.base.base.core
    for name, value in values.items():
        for module in modules:
            setattr(module, name, value)
        if hasattr(core, name):
            setattr(core, name, value)

    def adaptive_contract() -> dict[str, Any]:
        contract = original_contract_builder()
        inherited = contract.pop("r482")
        inherited.update(
            {
                "successor_round": config["round"],
                "source_round": SOURCE_ROUND,
                "training_mode": "adaptive_stop_v1",
                "adaptive_stop": asdict(config["_stop"]),
                "adaptive_stop_sha256": config_sha256(config["_stop"]),
                "probe_bank_sha256": config["probe_bank_sha256"],
                "recovery_policy": config["recovery_policy"],
                "fixed_budget_cells_pooled_as_adaptive": False,
            }
        )
        contract["adaptive_u2"] = inherited
        return contract

    for module in (*modules, core):
        setattr(module, "build_contract", adaptive_contract)


def train_shard_ids(config: dict[str, Any]) -> list[str]:
    return [f"train|{arm}|{seed}" for arm, seed in config["_cells"]]


def evaluation_shard_ids(config: dict[str, Any]) -> list[str]:
    arms = tuple(dict.fromkeys(arm for arm, _seed in config["_cells"]))
    return [f"eval|{arm}|{stage}" for stage in ("half", "final") for arm in arms]


def _validate_completed(config: dict[str, Any], arm: str, seed: int) -> str | None:
    manifest = config["_out"] / "train" / arm / f"seed{seed}" / "manifest.json"
    sidecar = Path(f"{manifest}.sha256")
    if not manifest.exists() and not sidecar.exists():
        return None
    if not manifest.exists() or not sidecar.exists():
        raise RuntimeError(f"partial published cell requires review: {arm}|{seed}")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    if sha256_file(manifest) != expected:
        raise RuntimeError(f"existing cell manifest hash mismatch: {arm}|{seed}")
    row = json.loads(manifest.read_text(encoding="utf-8"))
    identity = {
        "round": config["round"],
        "source_round": SOURCE_ROUND,
        "arm_id": arm,
        "training_seed": seed,
        "training_mode": "adaptive_stop_v1",
        "valid": True,
        "stop_config_sha256": config_sha256(config["_stop"]),
        "probe_bank_sha256": config["probe_bank_sha256"],
    }
    for key, value in identity.items():
        if row.get(key) != value:
            raise RuntimeError(f"existing cell identity mismatch: {arm}|{seed}|{key}")
    steps = int(row.get("interaction_steps", -1))
    stop = config["_stop"]
    reason = row.get("stop_reason")
    if not stop.min_steps <= steps <= stop.max_steps:
        raise RuntimeError(f"existing cell has invalid step count: {arm}|{seed}")
    if reason == "max_steps" and steps != stop.max_steps:
        raise RuntimeError(f"existing cell has premature max stop: {arm}|{seed}")
    if reason == "converged" and row.get("converged") is not True:
        raise RuntimeError(f"existing cell lacks convergence verdict: {arm}|{seed}")
    if reason not in {"converged", "max_steps"}:
        raise RuntimeError(f"existing cell has invalid stop reason: {arm}|{seed}")
    folder = manifest.parent
    for filename, key in (
        ("half.pt", "half_checkpoint_sha256"),
        ("final.pt", "final_checkpoint_sha256"),
        ("full_curves.npz", "full_curves_sha256"),
        ("adaptive_trace.json", "adaptive_trace_sha256"),
    ):
        artifact = folder / filename
        if not artifact.exists() or sha256_file(artifact) != row.get(key):
            raise RuntimeError(f"existing cell artifact mismatch: {arm}|{seed}|{filename}")
    return expected


def _assert_recoverable_attempts(
    config: dict[str, Any], arm: str, seed: int, *, resume: bool
) -> None:
    root = config["_out"] / "recovery_attempts" / arm / f"seed{seed}"
    attempts = sorted(path for path in root.glob("*") if path.is_dir())
    if not attempts:
        return
    if not resume:
        raise RuntimeError(f"partial attempts require authorized resume: {arm}|{seed}")
    for attempt in attempts:
        if (attempt / "initialization_failure.json").exists():
            raise RuntimeError(
                f"retained initialization failure forbids retry: {arm}|{seed}|{attempt.name}"
            )
        manifest = attempt / "manifest.json"
        if manifest.exists():
            sidecar = Path(f"{manifest}.sha256")
            if (
                not sidecar.exists()
                or sha256_file(manifest) != sidecar.read_text(encoding="ascii").split()[0]
            ):
                raise RuntimeError(f"retained attempt manifest drift: {arm}|{seed}|{attempt.name}")
            row = json.loads(manifest.read_text(encoding="utf-8"))
            raise RuntimeError(
                "retained completed/invalid attempt requires review before retry: "
                f"{arm}|{seed}|{attempt.name}|valid={row.get('valid')}"
            )


def run_shard(config: dict[str, Any], shard_id: str, *, resume: bool = False) -> str:
    parts = shard_id.split("|")
    if len(parts) != 3 or parts[0] != "train":
        raise ValueError(f"unknown adaptive shard: {shard_id}")
    arm, seed = parts[1], int(parts[2])
    if (arm, seed) not in config["_cells"]:
        raise ValueError(f"unregistered adaptive cell: {arm}|{seed}")
    runtime = _load_runtime()
    bind_runtime(runtime, config)
    seal = load_seal(config, runtime)
    if resume:
        if config["recovery_policy"] != RECOVERY_POLICY:
            raise RuntimeError("resume was not prospectively authorized")
        completed = _validate_completed(config, arm, seed)
        if completed is not None:
            return completed
    _assert_recoverable_attempts(config, arm, seed, resume=resume)
    source = seal["source_base_inventory"][str(seed)]
    with runtime._terminal_guarded_environment():
        return train_cell(
            runtime,
            round_id=config["round"],
            out=config["_out"],
            source_out=config["_source_out"],
            arm_id=arm,
            seed=seed,
            stop_config=config["_stop"],
            probe_path=config["_probe_bank"],
            probe_sha256=config["probe_bank_sha256"],
            source_round=SOURCE_ROUND,
            source_manifest_sha256=source["manifest_sha256"],
            source_base_sha256=source["base_state_sha256"],
        )


def evaluate_shard(config: dict[str, Any], shard_id: str) -> dict[str, Any]:
    """Evaluate one arm-stage shard without copying R482 donor manifests."""

    parts = shard_id.split("|")
    if len(parts) != 3 or parts[0] != "eval" or parts[2] not in {"half", "final"}:
        raise ValueError(f"unknown adaptive evaluation shard: {shard_id}")
    arm, stage = parts[1], parts[2]
    cells = set(config["_cells"])
    seeds = tuple(sorted(seed for candidate, seed in cells if candidate == arm))
    if not seeds or shard_id not in evaluation_shard_ids(config):
        raise ValueError(f"unregistered adaptive evaluation shard: {shard_id}")
    runtime = _load_runtime()
    bind_runtime(runtime, config)
    seal = load_seal(config, runtime)
    core = runtime.base.base.base.core
    core._assert_wsl_scratch()
    contract = runtime.build_contract()
    factors = runtime.arm_factors(arm)
    profiles = [row for row in contract["profiles"] if row["split"] == "evaluation"]
    created = 0
    with runtime._terminal_guarded_environment():
        for seed in seeds:
            source = seal["source_base_inventory"][str(seed)]
            source_manifest = core._read_hashed_json(ROOT / source["manifest_path"])
            checkpoint = config["_out"] / "train" / arm / f"seed{seed}" / f"{stage}.pt"
            checkpoint_sha = sha256_file(checkpoint)
            wrapper = core.FactorialWrapper(arm)
            metadata = wrapper.load(checkpoint)
            if metadata["base_state_sha256"] != source_manifest["base_state_sha256"]:
                raise RuntimeError(f"eval checkpoint/base mismatch: {arm}|{seed}|{stage}")
            envs = {str(row["profile_id"]): core.r431._build_env(row) for row in profiles}
            try:
                for profile in profiles:
                    records = []
                    env = envs[str(profile["profile_id"])]
                    for scenario in profile["scenarios"]:
                        observation = env.reset(delta_u=dict(scenario["delta_u"]))
                        initial_frequency = (
                            runtime.np.asarray(env._get_vsg_omega(), dtype=float)
                            * float(contract["physical_nominal_frequency_hz"])
                        ).tolist()
                        previous = runtime.np.zeros((4, 2), dtype=runtime.np.float32)
                        identity = {
                            "n_agents": int(env.N_AGENTS),
                            "vsg_idx": [str(value) for value in env.vsg_idx],
                            "vsg_buses": [
                                int(env.ss.GENCLS.bus.v[position]) for position in env._vsg_pos
                            ],
                            "obs_dim": int(env.OBS_DIM),
                        }
                        rows = []
                        failure = None
                        for time_index in range(int(contract["steps"])):
                            joint = core.r431._joint_obs(observation)
                            actor_rows = runtime.base.base.source_rows(
                                joint, factors["actor_source"]
                            )
                            raw, executed = wrapper.act(actor_rows, previous, deterministic=True)
                            observation, _reward, done, info = env.step(
                                {index: executed[index] for index in range(4)}
                            )
                            rows.append(
                                {
                                    "step_index": time_index,
                                    "time": float(info["time"]),
                                    "raw_action_norm": raw.astype(float).tolist(),
                                    "action_norm": executed.astype(float).tolist(),
                                    "freq_hz_physical": runtime.np.asarray(
                                        info["freq_hz_physical"], dtype=float
                                    ).tolist(),
                                    "M_es": [
                                        float(env.ss.GENCLS.M.v[position])
                                        for position in env._vsg_pos
                                    ],
                                    "D_es": [
                                        float(env.ss.GENCLS.D.v[position])
                                        for position in env._vsg_pos
                                    ],
                                    "delta_M": runtime.np.asarray(
                                        info["delta_M"], dtype=float
                                    ).tolist(),
                                    "delta_D": runtime.np.asarray(
                                        info["delta_D"], dtype=float
                                    ).tolist(),
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
                                "scenario_id": str(scenario["scenario_id"]),
                                "pair_kind": str(scenario["pair_kind"]),
                                "sign": str(scenario["sign"]),
                                "magnitude": float(scenario["magnitude"]),
                                "delta_u": dict(scenario["delta_u"]),
                                "arm_id": arm,
                                "stage": stage,
                                "training_seed": seed,
                                "checkpoint_sha256": checkpoint_sha,
                                "identity": identity,
                                "initial_freq_hz_physical": initial_frequency,
                                "steps": rows,
                                "completed_steps": len(rows),
                                "completed": failure is None
                                and len(rows) == int(contract["steps"]),
                                "tds_failed": failure is not None,
                                "failure": failure,
                                "reward_used_for_gate": False,
                                "training_mode": "adaptive_stop_v1",
                            }
                        )
                    folder = config["_out"] / "eval" / stage / arm / f"seed{seed}"
                    core._write_new_json(
                        folder / f"{profile['profile_id']}.json", {"records": records}
                    )
                    created += 1
            finally:
                for env in envs.values():
                    try:
                        env.close()
                    except Exception:
                        pass
    return {"round": config["round"], "shard": shard_id, "profile_files": created}


def _profile_endpoint(
    runtime: Any, config: dict[str, Any], arm: str, seed: int, stage: str, profile: str
) -> float:
    core = runtime.base.base.base.core
    payload = core._read_hashed_json(
        config["_out"] / "eval" / stage / arm / f"seed{seed}" / f"{profile}.json"
    )
    if any(not row["completed"] or row["tds_failed"] for row in payload["records"]):
        raise RuntimeError(f"invalid eval record: {arm}|{seed}|{stage}|{profile}")
    return core.parent._arm_endpoints(payload["records"], runtime.build_contract())[
        runtime.PRIMARY
    ]


def aggregate(config: dict[str, Any]) -> str:
    """Run the registered four-effect analysis on adaptive cells only."""

    runtime = _load_runtime()
    bind_runtime(runtime, config)
    load_seal(config, runtime)
    core = runtime.base.base.base.core
    core._assert_wsl_scratch()
    arms = tuple(dict.fromkeys(arm for arm, _seed in config["_cells"]))
    seeds = tuple(sorted({seed for _arm, seed in config["_cells"]}))
    if set(arms) != set(runtime.FACTORIAL_ARMS):
        raise RuntimeError("adaptive analysis requires the complete eight-arm factorial")
    errors: list[str] = []
    base_hashes = {seed: set() for seed in seeds}
    stop_rows = []
    for arm, seed in config["_cells"]:
        try:
            _validate_completed(config, arm, seed)
            row = core._read_hashed_json(
                config["_out"] / "train" / arm / f"seed{seed}" / "manifest.json"
            )
            base_hashes[seed].add(str(row["base_state_sha256"]))
            if row.get("reward_function_sha256") != FACTORIAL_REWARD_SHA256:
                raise RuntimeError("factorial reward hash mismatch")
            stop_rows.append(
                {
                    "arm_id": arm,
                    "seed": seed,
                    "steps": int(row["interaction_steps"]),
                    "reason": row["stop_reason"],
                    "converged": bool(row["converged"]),
                }
            )
        except Exception as exc:
            errors.append(f"training {arm}|{seed}: {exc}")
    for seed, hashes in base_hashes.items():
        if len(hashes) != 1:
            errors.append(f"base state mismatch seed{seed}")
    profiles = tuple(runtime.PROFILES)
    factorial: dict[str, dict[int, float]] = {}
    stage_means: dict[str, dict[int, float]] = {}
    for stage in ("half", "final"):
        rows = []
        for arm in arms:
            factors = runtime.arm_factors(arm)
            for seed in seeds:
                for profile in profiles:
                    try:
                        endpoint = _profile_endpoint(
                            runtime, config, arm, seed, stage, profile
                        )
                    except Exception as exc:
                        errors.append(f"evaluation {arm}|{seed}|{stage}|{profile}: {exc}")
                        continue
                    rows.append(
                        {
                            "stage": stage,
                            "seed": seed,
                            "actor_source": factors["actor_source"],
                            "critic_source": factors["critic_source"],
                            "reward_access": int(factors["reward_access"]),
                            "profile": profile,
                            runtime.PRIMARY: endpoint,
                        }
                    )
        if errors:
            continue
        effects = runtime.sfd.seed_effects(
            rows,
            expected_seeds=seeds,
            expected_profiles=profiles,
            stage=stage,
            metric=runtime.PRIMARY,
        )
        if stage == "final":
            factorial = effects
        else:
            stage_means = effects
    test_rows = (
        runtime.r482_analysis.boundary_test_rows(factorial, runtime.MATERIALITY_LOG)
        if factorial and not errors
        else {}
    )
    classification = runtime.r482_analysis.classify_r482(
        design_valid=True,
        missing_shards=[] if not errors else errors,
        integrity_errors=errors,
        dynamics_stable=not errors,
        factorial_rows=test_rows,
        phase3_rows=None,
    )
    if classification["verdict"].startswith("MATERIAL-"):
        classification["verdict"] = "ADAPTIVE-" + classification["verdict"]
    payload = {
        "schema_version": 1,
        "round": config["round"],
        "training_mode": "adaptive_stop_v1",
        "fixed_budget_r482_cells_included": False,
        "contract_sha256": core.contract_sha256(),
        "seal_sha256": sha256_file(config["_seal"]),
        "integrity": {"valid": not errors, "errors": errors},
        "adaptive_stops": stop_rows,
        "factorial_materiality_tests": test_rows,
        "factorial_half_stage_means": {
            name: float(runtime.np.mean(list(by_seed.values())))
            for name, by_seed in stage_means.items()
        },
        "classification": classification,
        "created_utc": runtime.datetime.now(runtime.UTC).isoformat(),
    }
    return core._write_new_json(config["_out"] / "formal_analysis.json", payload)


def check_results(config: dict[str, Any]) -> dict[str, Any]:
    runtime = _load_runtime()
    bind_runtime(runtime, config)
    load_seal(config, runtime)
    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    for arm, seed in config["_cells"]:
        try:
            digest = _validate_completed(config, arm, seed)
            if digest is None:
                raise RuntimeError("missing completed cell")
            manifest = config["_out"] / "train" / arm / f"seed{seed}" / "manifest.json"
            row = json.loads(manifest.read_text(encoding="utf-8"))
            rows.append(
                {
                    "arm_id": arm,
                    "seed": seed,
                    "interaction_steps": row["interaction_steps"],
                    "stop_reason": row["stop_reason"],
                    "converged": row["converged"],
                }
            )
        except Exception as exc:
            errors.append(f"{arm}|{seed}: {exc}")
    return {
        "round": config["round"],
        "expected_cells": len(config["_cells"]),
        "valid_cells": len(rows),
        "errors": errors,
        "rows": rows,
    }


def formal_manifest(config: dict[str, Any]) -> str:
    """Finalize only a complete, hash-valid adaptive result tree."""

    runtime = _load_runtime()
    bind_runtime(runtime, config)
    load_seal(config, runtime)
    checked = check_results(config)
    if checked["errors"] or checked["valid_cells"] != len(config["_cells"]):
        raise RuntimeError("cannot finalize incomplete adaptive training")
    analysis_path = config["_out"] / "formal_analysis.json"
    analysis = runtime.base.base.base.core._read_hashed_json(analysis_path)
    required = {"design": "VALID", "execution": "COMPLETE", "integrity": "PASS"}
    classification = analysis.get("classification", {})
    if any(classification.get(key) != value for key, value in required.items()):
        raise RuntimeError(f"adaptive analysis is not finalizable: {classification}")
    core = runtime.base.base.base.core
    entries = []
    for path in sorted(config["_out"].rglob("*")):
        if (
            not path.is_file()
            or path.name == "formal_manifest.json"
            or path.name.endswith(".sha256")
            or "recovery_attempts" in path.relative_to(config["_out"]).parts
        ):
            continue
        sidecar = Path(f"{path}.sha256")
        digest = sha256_file(path)
        if not sidecar.is_file() or sidecar.read_text(encoding="ascii").split()[0] != digest:
            raise RuntimeError(f"missing/invalid result sidecar: {path}")
        entries.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": digest,
                "bytes": path.stat().st_size,
            }
        )
    return core._write_new_json(
        config["_out"] / "formal_manifest.json",
        {
            "schema_version": 1,
            "round": config["round"],
            "training_mode": "adaptive_stop_v1",
            "fixed_budget_r482_cells_included": False,
            "entry_count": len(entries),
            "total_bytes": sum(row["bytes"] for row in entries),
            "entries": entries,
            "created_utc": runtime.datetime.now(runtime.UTC).isoformat(),
        },
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument(
        "command",
        choices=(
            "seal-inputs",
            "probe",
            "rehearse",
            "train-shards",
            "eval-shards",
            "authority",
            "shard",
            "check",
            "aggregate",
            "manifest",
        ),
    )
    parser.add_argument("shard_id", nargs="?")
    parser.add_argument("--resume", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    config = load_config(config_path)
    if args.command == "seal-inputs":
        payload: Any = seal_inputs(config)
    elif args.command == "probe":
        _preseal_authority(config)
        runtime = _load_runtime()
        bind_runtime(runtime, config)
        runtime.base.base.base.core._assert_wsl_scratch()
        with runtime._terminal_guarded_environment():
            payload = {"probe_bank_sha256": create_probe_bank(runtime, config["_probe_bank"])}
    elif args.command == "rehearse":
        payload = {"rehearsal_sha256": rehearsal(config)}
    elif args.command == "train-shards":
        payload = train_shard_ids(config)
    elif args.command == "eval-shards":
        payload = evaluation_shard_ids(config)
    elif args.command == "authority":
        runtime = _load_runtime()
        bind_runtime(runtime, config)
        payload = load_seal(config, runtime)
    elif args.command == "shard":
        if args.shard_id is None:
            raise SystemExit("shard command requires a shard id")
        if args.shard_id.startswith("train|"):
            payload = {
                "manifest_sha256": run_shard(config, args.shard_id, resume=args.resume)
            }
        else:
            if args.resume:
                raise RuntimeError("evaluation resume must use create-only shard checks")
            payload = evaluate_shard(config, args.shard_id)
    elif args.command == "check":
        payload = check_results(config)
    elif args.command == "aggregate":
        payload = {"formal_analysis_sha256": aggregate(config)}
    else:
        payload = {"formal_manifest_sha256": formal_manifest(config)}
    print(json.dumps(payload, indent=2, sort_keys=True), flush=True)
    return 0 if not isinstance(payload, dict) or not payload.get("errors") else 1


if __name__ == "__main__":
    raise SystemExit(main())
