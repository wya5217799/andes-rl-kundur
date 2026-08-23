"""R476 governance-correct adapter for the frozen R475 U2 design.

Scientific execution delegates to the frozen R475 implementation. R476 owns
new paths plus the corrected seal, review, terminal, and classification
interfaces required after R475's governance abort.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from andes_rl_kundur.evaluation.u2_confirmatory import (
    classify_confirmatory,
    terminal_invalid,
    terminal_truth_table,
    validate_review_coverage,
    verify_formal_seal,
)

_spec = importlib.util.spec_from_file_location(
    "_r476_r475_base", ROOT / "scripts/run_r475_u2_confirmatory.py"
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load isolated R475 scientific implementation")
base = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = base
_spec.loader.exec_module(base)

ROUND_ID = "R476"
PLAN = ROOT / "memory/rounds/R476/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
POWER = ROOT / "memory/rounds/R476/power_analysis.json"
CAPACITY = ROOT / "memory/rounds/R476/capacity_evidence.json"
BASE_AUDIT = ROOT / "memory/rounds/R476/base_audit.json"
REHEARSAL = ROOT / "memory/rounds/R476/rehearsal.json"
SEAL = ROOT / "memory/rounds/R476/formal_seal.json"
OUT = ROOT / "results/research_loop/r476_u2_confirmatory"
R473_OUT = ROOT / "results/research_loop/r473_u2_source_factorial"
R473_MANIFEST = R473_OUT / "formal_manifest.json"
TRAIN_SHARDS = ROOT / "tmp/andes/r476_train_shards.json"
EVAL_SHARDS = ROOT / "tmp/andes/r476_eval_shards.json"
ROUTING_GATE = ROOT / "memory/rounds/R476/routing_gate.json"
REVIEW_A = ROOT / "memory/rounds/R476/code_review_a.json"
REVIEW_B = ROOT / "memory/rounds/R476/code_review_b.json"
PIPELINE = ROOT / "scripts/run_r476_detached_pipeline.sh"
INTEGRITY_MODULE = ROOT / "src/andes_rl_kundur/evaluation/u2_confirmatory.py"
INTEGRITY_TESTS = ROOT / "tests/test_u2_confirmatory.py"
RUNNER_TESTS = ROOT / "tests/test_run_r476_u2_confirmatory.py"

RETRAIN_ARMS = base.RETRAIN_ARMS
REUSE_ARMS = base.REUSE_ARMS
RETRAIN_CELLS = base.RETRAIN_CELLS
REUSE_CELLS = base.REUSE_CELLS
TRAIN_SHARD_IDS = tuple(f"train|{arm}|{seed}" for arm, seed in RETRAIN_CELLS)
EVAL_SHARD_IDS = tuple(
    f"eval|{stage}|{arm}"
    for stage in ("half", "final")
    for arm in RETRAIN_ARMS
)

for _name, _value in {
    "ROUND_ID": ROUND_ID,
    "PLAN": PLAN,
    "LINE": LINE,
    "POWER": POWER,
    "CAPACITY": CAPACITY,
    "BASE_AUDIT": BASE_AUDIT,
    "REHEARSAL": REHEARSAL,
    "SEAL": SEAL,
    "OUT": OUT,
    "R473_OUT": R473_OUT,
    "R473_MANIFEST": R473_MANIFEST,
    "TRAIN_SHARDS": TRAIN_SHARDS,
    "EVAL_SHARDS": EVAL_SHARDS,
    "ROUTING_GATE": ROUTING_GATE,
    "REVIEW_A": REVIEW_A,
    "REVIEW_B": REVIEW_B,
}.items():
    setattr(base, _name, _value)
    if hasattr(base.core, _name):
        setattr(base.core, _name, _value)


def build_contract() -> dict[str, Any]:
    contract = base._r470_build_contract()
    inherited = contract.pop("r470")
    inherited["successor_of"] = "R475"
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
    inherited["engineering_correction"] = (
        "full current-round seal verification; identical review maps; "
        "executable terminal truth; fail-closed classification"
    )
    contract["r476"] = inherited
    return contract


def authority_checks() -> dict[str, bool]:
    plan = PLAN.read_text(encoding="utf-8")
    line = LINE.read_text(encoding="utf-8")
    return {
        "active_plan": "round: R476" in plan and "state: active" in plan,
        "active_line": (
            "line_id: yang-md-decoupling-marl" in line and "status: active" in line
        ),
        "contract_closed": (
            len(base.core.ARMS) == 18
            and len(base.core.TRAINING_SEEDS) == 6
            and len(RETRAIN_CELLS) == 48
            and not REUSE_CELLS
        ),
        "output_absence": not OUT.exists(),
    }


def _reviewed_files() -> tuple[Path, ...]:
    return (
        Path(__file__).resolve(),
        RUNNER_TESTS,
        INTEGRITY_MODULE,
        INTEGRITY_TESTS,
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
        contract_sha256=base.core.contract_sha256(),
        bound_files=_bound_files(),
        review_paths=(REVIEW_A, REVIEW_B),
        reviewed_files=_reviewed_files(),
        expected_shards={"train": TRAIN_SHARD_IDS, "eval": EVAL_SHARD_IDS},
    )


_r475_rehearsal = base.rehearsal


def rehearsal() -> dict[str, Any]:
    checks = _r475_rehearsal()
    truth = terminal_truth_table(terminal_invalid)
    checks["terminal_truth_table"] = truth
    checks["passed"] = bool(checks.get("passed") and all(truth.values()))
    return checks


def _write_shard_list(path: Path, values: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != list(values):
            raise RuntimeError(f"existing shard list drift: {path}")
        return
    path.write_text(json.dumps(list(values)) + "\n", encoding="utf-8")


def prepare() -> dict[str, Any]:
    if SEAL.exists():
        raise FileExistsError(f"R476 formal seal already exists: {SEAL}")
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed: {checks}")
    power = base.core._read_hashed_json(POWER)
    base_audit = base.core._read_hashed_json(BASE_AUDIT)
    routing = base.core._read_hashed_json(ROUTING_GATE)
    rehearsal_payload = base.core._read_hashed_json(REHEARSAL)
    capacity = base.core._read_hashed_json(CAPACITY)
    if not power.get("targets_materiality"):
        raise RuntimeError("power analysis does not target materiality")
    if not base_audit.get("passed") or not routing.get("passed"):
        raise RuntimeError("base/routing gate failed")
    if not rehearsal_payload.get("passed"):
        raise RuntimeError("rehearsal gate failed")
    if (
        capacity.get("readiness") != "RUN-READY"
        or int(capacity.get("whole_host_python_process_budget", -1)) != 17
    ):
        raise RuntimeError("capacity gate failed")
    reviewed_map = validate_review_coverage(
        (REVIEW_A, REVIEW_B),
        repo_root=ROOT,
        reviewed_files=_reviewed_files(),
    )
    _write_shard_list(TRAIN_SHARDS, TRAIN_SHARD_IDS)
    _write_shard_list(EVAL_SHARDS, EVAL_SHARD_IDS)

    sources = {
        "successor_runner": Path(__file__).resolve(),
        "successor_tests": RUNNER_TESTS,
        "confirmatory_integrity": INTEGRITY_MODULE,
        "confirmatory_integrity_tests": INTEGRITY_TESTS,
        "detached_pipeline": PIPELINE,
        "sealed_r475_parent": ROOT / "scripts/run_r475_u2_confirmatory.py",
        "sealed_r474_parent": ROOT / "scripts/run_r474_u2_source_factorial.py",
        "sealed_r473_parent": ROOT / "scripts/run_r473_u2_source_factorial.py",
        "sealed_r472_parent": ROOT / "scripts/run_r472_u2_source_factorial.py",
        "sealed_r471_parent": ROOT / "scripts/run_r471_u2_source_factorial.py",
        "sealed_r470_parent": ROOT / "scripts/run_r470_u2_source_factorial.py",
        "r451_structural_parent": ROOT / "scripts/run_r451_m3_message_factorial.py",
        "r438_parent": ROOT / "scripts/run_r438_sac_message_channels.py",
        "r431_parent": ROOT / "scripts/run_r431_sac_slew.py",
        "source_agent": ROOT / "src/andes_rl_kundur/agents/source_factorial_sac.py",
        "source_agent_tests": ROOT / "tests/test_source_factorial_sac.py",
        "u3_agent": ROOT / "src/andes_rl_kundur/agents/executed_action_sac.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "environment": ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "base_env": ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
        "v4_config": ROOT / "src/andes_rl_kundur/env/andes/v4_config.py",
    }
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": base.core.contract_sha256(),
        **{field: base.core._sha256_file(path) for field, path in _bound_files().items()},
        "authority": checks,
        "launch": {
            "wsl_python_processes": 17,
            "other_reserved_processes": 0,
            "host_process_budget": 17,
            "native_threads_per_process": 1,
            "detached_from_unified_exec": True,
        },
        "runtime": rehearsal_payload["runtime"],
        "reviewed_files": reviewed_map,
        "sources": {
            name: {
                "path": base.core._relative(path),
                "sha256": base.core._sha256_file(path),
            }
            for name, path in sources.items()
        },
        "shard_lists": {
            "train": {
                "path": base.core._relative(TRAIN_SHARDS),
                "sha256": base.core._sha256_file(TRAIN_SHARDS),
            },
            "eval": {
                "path": base.core._relative(EVAL_SHARDS),
                "sha256": base.core._sha256_file(EVAL_SHARDS),
            },
        },
        "formal_authority": True,
        "training_executed": False,
    }
    seal_sha = base.core._write_new_json(SEAL, seal)
    load_seal()
    return {
        "seal_sha256": seal_sha,
        "selected_workers": 16,
        "fresh_training_shards": len(TRAIN_SHARD_IDS),
        "fresh_eval_shards": len(EVAL_SHARD_IDS),
        "reviewed_file_count": len(reviewed_map),
    }


def missing_shards() -> list[str]:
    return base.missing_shards()


def artifact_budget_check(*, max_bytes: int = 650 * 1024 * 1024) -> dict[str, int]:
    total_bytes = sum(
        path.stat().st_size for path in OUT.rglob("*") if path.is_file()
    ) if OUT.exists() else 0
    if total_bytes > max_bytes:
        raise RuntimeError(
            f"R476 artifact budget exceeded: {total_bytes} > {max_bytes} bytes"
        )
    return {"total_bytes": total_bytes, "max_bytes": max_bytes}


def aggregate() -> str:
    base.core._assert_wsl_scratch()
    load_seal()
    missing = missing_shards()
    if missing:
        classification = classify_confirmatory(
            design_valid=base.routing_gate_passed(),
            missing_shards=missing,
            integrity_errors=[],
            dynamics_stable=False,
            established_factors=[],
        )
        return base.core._write_new_json(
            OUT / "formal_analysis.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "contract_sha256": base.core.contract_sha256(),
                "seal_sha256": base.core._sha256_file(SEAL),
                "integrity": {"valid": True, "errors": []},
                "missing_shards": missing,
                "main_effects": {},
                "primary_materiality_tests": {},
                "classification": classification,
                "created_utc": datetime.now(UTC).isoformat(),
            },
        )

    integrity_errors: list[str] = []
    base_hashes: dict[int, set[str]] = {
        seed: set() for seed in base.core.TRAINING_SEEDS
    }
    reward_hashes: dict[bool, set[str]] = {False: set(), True: set()}
    stability_rows: dict[str, list[dict[str, Any]]] = {}
    for arm in RETRAIN_ARMS:
        stability_rows[arm] = []
        for seed in base.core.TRAINING_SEEDS:
            manifest = base.core._read_hashed_json(
                OUT / "train" / arm / f"seed{seed}" / "manifest.json"
            )
            if not manifest["valid"] or int(manifest["interaction_steps"]) != 43_200:
                integrity_errors.append(f"invalid training {arm} seed{seed}")
            base_hashes[seed].add(str(manifest["base_state_sha256"]))
            reward = bool(base.core.arm_factors(arm)["reward_access"])
            reward_hashes[reward].add(str(manifest["reward_function_sha256"]))
            stability_rows[arm].append(manifest["stability"])
    for seed, hashes in base_hashes.items():
        if len(hashes) != 1:
            integrity_errors.append(f"base state mismatch seed{seed}")
    if (
        any(len(hashes) != 1 for hashes in reward_hashes.values())
        or reward_hashes[False] != reward_hashes[True]
    ):
        integrity_errors.append("reward implementation hash mismatch")

    stage_effects = {
        stage: {
            metric: base._paired_main_effects(stage, metric)
            for metric in (base.PRIMARY, base.SECONDARY)
        }
        for stage in ("half", "final")
    }
    final_primary = stage_effects["final"][base.PRIMARY]
    primary_tests: dict[str, dict[str, Any]] = {}
    for factor in ("actor", "critic"):
        values = final_primary[factor]
        p_value = base._signflip_p_one_sided(values, base.MATERIALITY_LOG)
        ci_low, ci_high = base._exact_bootstrap_ci(values)
        primary_tests[factor] = {
            "paired_log_effects": values,
            "mean_log_effect": float(np.mean(values)),
            "geometric_improvement": float(math.exp(float(np.mean(values))) - 1.0),
            "materiality_log": base.MATERIALITY_LOG,
            "materiality_p_one_sided": p_value,
            "bootstrap_ci95_descriptive": [ci_low, ci_high],
            "holm_reject": False,
            "direction_count_positive": int(sum(value > 0 for value in values)),
            "seed_min": float(np.min(values)),
            "seed_median": float(np.median(values)),
            "leave_one_out_means": [
                float(np.mean([value for j, value in enumerate(values) if j != i]))
                for i in range(len(values))
            ],
        }
    base._apply_holm_two(primary_tests)

    direction_flips = {}
    for factor in ("actor", "critic"):
        half = float(np.mean(stage_effects["half"][base.PRIMARY][factor]))
        final = float(np.mean(stage_effects["final"][base.PRIMARY][factor]))
        direction_flips[factor] = {
            "half_mean": half,
            "final_mean": final,
            "flipped": bool(np.sign(half) != np.sign(final)),
        }
    no_plateau = [
        f"{arm}|{seed}|{kind}"
        for arm in RETRAIN_ARMS
        for seed, row in zip(
            base.core.TRAINING_SEEDS, stability_rows[arm], strict=True
        )
        for kind in ("critic_loss", "actor_loss")
        if not row[kind]["stable"]
    ]
    dynamics_stable = not any(
        row["flipped"] for row in direction_flips.values()
    ) and not no_plateau
    established = [
        factor for factor, row in primary_tests.items() if row["holm_reject"]
    ]
    classification = classify_confirmatory(
        design_valid=base.routing_gate_passed(),
        missing_shards=[],
        integrity_errors=integrity_errors,
        dynamics_stable=dynamics_stable,
        established_factors=established,
    )
    for row in primary_tests.values():
        row["material_effect"] = (
            "NOT_TESTED"
            if classification["material_effect"] == "NOT_TESTED"
            else ("ESTABLISHED" if row["holm_reject"] else "NOT_ESTABLISHED")
        )
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "contract_sha256": base.core.contract_sha256(),
        "seal_sha256": base.core._sha256_file(SEAL),
        "integrity": {
            "valid": not integrity_errors,
            "errors": integrity_errors,
            "six_seed_base_hashes": {
                str(seed): sorted(values) for seed, values in base_hashes.items()
            },
            "reward_hashes": {
                str(key): sorted(values) for key, values in reward_hashes.items()
            },
        },
        "missing_shards": [],
        "main_effects": stage_effects,
        "primary_materiality_tests": primary_tests,
        "optimization": {
            "direction_flips": direction_flips,
            "nonplateau_rows": no_plateau,
            "unresolved": not dynamics_stable,
        },
        "classification": {
            **classification,
            "scope": (
                "six seeds; frozen R470 learner/bank/projector only; "
                "all-fresh 2x2; row-permuted P"
            ),
            "universal_intrinsic_claim_authorized": False,
        },
        "created_utc": datetime.now(UTC).isoformat(),
    }
    return base.core._write_new_json(OUT / "formal_analysis.json", payload)


source_rows = base.source_rows
routing_check = base.routing_check
routing_gate = base.routing_gate
base_audit = base.base_audit
import_parent_artifacts = base.import_parent_artifacts
train_arm_seed = base.train_arm_seed
evaluate_arm_stage = base.evaluate_arm_stage

for _name, _value in {
    "authority_checks": authority_checks,
    "build_contract": build_contract,
    "rehearsal": rehearsal,
    "prepare": prepare,
    "source_rows": source_rows,
    "load_seal": load_seal,
    "aggregate": aggregate,
}.items():
    setattr(base, _name, _value)
    setattr(base.core, _name, _value)


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "base",
            "import",
            "route",
            "rehearse",
            "prepare",
            "verify",
            "shard",
            "aggregate",
            "budget",
            "manifest",
        ),
    )
    parser.add_argument("shard_id", nargs="?")
    args = parser.parse_args()
    if args.command == "base":
        payload = base_audit()
        digest = base.core._write_new_json(BASE_AUDIT, payload)
        base.core.safe_emit(json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True))
    elif args.command == "import":
        base.core.safe_emit(import_parent_artifacts())
    elif args.command == "route":
        payload = routing_gate()
        digest = base.core._write_new_json(ROUTING_GATE, payload)
        base.core.safe_emit(json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True))
    elif args.command == "rehearse":
        payload = rehearsal()
        digest = base.core._write_new_json(REHEARSAL, payload)
        base.core.safe_emit(json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True))
    elif args.command == "prepare":
        base.core.safe_emit(json.dumps(prepare(), indent=2, sort_keys=True))
    elif args.command == "verify":
        base.core.safe_emit(json.dumps(load_seal(), indent=2, sort_keys=True))
    elif args.command == "aggregate":
        base.core.safe_emit(aggregate())
    elif args.command == "budget":
        base.core.safe_emit(json.dumps(artifact_budget_check(), sort_keys=True))
    elif args.command == "manifest":
        base.core.safe_emit(base.core.formal_manifest())
    else:
        if args.shard_id is None:
            raise SystemExit("shard requires a shard id")
        parts = args.shard_id.split("|")
        if parts[0] == "train" and len(parts) == 3:
            base.core.safe_emit(train_arm_seed(parts[1], int(parts[2])))
        elif parts[0] == "eval" and len(parts) == 3:
            evaluate_arm_stage(parts[2], parts[1])
        else:
            raise SystemExit(f"unsupported shard: {args.shard_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
