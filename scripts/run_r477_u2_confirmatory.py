"""R477 execution-completion successor of R476 (unchanged scientific design).

R476 aborted after its first training wave on the driver-result path bug
(now fixed and regression-locked). R477 prospectively reuses R476's 16
complete wave-1 training shards by hash-identical hardlink after per-shard
scientific-identity verification, trains the remaining 32 fresh cells in
two sealed waves, runs the unchanged 16 arm-stage evaluation jobs, and
aggregates all 48 manifests. Scientific execution delegates to the frozen
R476/R475 implementation; R477 owns paths, the 32-fresh/16-reused cell
split, the import phase, and the corrected orchestration.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from andes_rl_kundur.evaluation.u2_confirmatory import (
    ConfirmatoryAnalysisContext,
    build_confirmatory_analysis,
    check_artifact_budget,
    inventory_artifacts,
    recalibrate_eta,
    validate_review_coverage,
    verify_formal_seal,
)

_spec = importlib.util.spec_from_file_location(
    "_r477_r476_base", ROOT / "scripts/run_r476_u2_confirmatory.py"
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load isolated R476 execution base")
base = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = base
_spec.loader.exec_module(base)

ROUND_ID = "R477"
PLAN = ROOT / "memory/rounds/R477/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
POWER = ROOT / "memory/rounds/R477/power_analysis.json"
CAPACITY = ROOT / "memory/rounds/R477/capacity_evidence.json"
BASE_AUDIT = ROOT / "memory/rounds/R477/base_audit.json"
REHEARSAL = ROOT / "memory/rounds/R477/rehearsal.json"
SEAL = ROOT / "memory/rounds/R477/formal_seal.json"
OUT = ROOT / "results/research_loop/r477_u2_confirmatory"
R476_OUT = ROOT / "results/research_loop/r476_u2_confirmatory"
R473_OUT = ROOT / "results/research_loop/r473_u2_source_factorial"
R473_MANIFEST = R473_OUT / "formal_manifest.json"
TRAIN_SHARDS = ROOT / "tmp/andes/r477_train_shards.json"
EVAL_SHARDS = ROOT / "tmp/andes/r477_eval_shards.json"
TRAIN_WAVE_SHARDS = tuple(
    ROOT / f"tmp/andes/r477_train_wave{index}_shards.json"
    for index in range(1, 3)
)
ETA_RECALIBRATION = ROOT / "tmp/andes/r477_eta_recalibration.json"
PIPELINE_INVENTORY = ROOT / "tmp/andes/r477_pipeline_inventories"
TRAIN_LOG_ROOT = ROOT / "tmp/andes/r477_train_logs"
EVAL_LOG_ROOT = ROOT / "tmp/andes/r477_eval_logs"
ROUTING_GATE = ROOT / "memory/rounds/R477/routing_gate.json"
REVIEW_A = ROOT / "memory/rounds/R477/code_review_a.json"
REVIEW_B = ROOT / "memory/rounds/R477/code_review_b.json"
PIPELINE = ROOT / "scripts/run_r477_detached_pipeline.sh"
INTEGRITY_MODULE = ROOT / "src/andes_rl_kundur/evaluation/u2_confirmatory.py"
INTEGRITY_TESTS = ROOT / "tests/test_u2_confirmatory.py"
RUNNER_TESTS = ROOT / "tests/test_run_r477_u2_confirmatory.py"

RETRAIN_ARMS = base.RETRAIN_ARMS
REUSE_ARMS = base.REUSE_ARMS


def _cells(shard_ids: tuple[str, ...]) -> tuple[tuple[str, int], ...]:
    return tuple(
        (parts[1], int(parts[2]))
        for parts in (shard_id.split("|") for shard_id in shard_ids)
    )


# Prospective reuse declaration: exactly R476 wave-1 cells are carried over;
# the remaining 32 cells (R476 wave-2 + wave-3 lists) train fresh here.
REUSED_CELLS = _cells(base.TRAIN_WAVE_IDS[0])
RETRAIN_CELLS = _cells(base.TRAIN_WAVE_IDS[1] + base.TRAIN_WAVE_IDS[2])
TRAIN_SHARD_IDS = tuple(f"train|{arm}|{seed}" for arm, seed in RETRAIN_CELLS)
EVAL_SHARD_IDS = tuple(
    f"eval|{stage}|{arm}"
    for stage in ("half", "final")
    for arm in RETRAIN_ARMS
)
TRAIN_WAVE_IDS = tuple(
    TRAIN_SHARD_IDS[index : index + 16]
    for index in range(0, len(TRAIN_SHARD_IDS), 16)
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
    setattr(base.base, _name, _value)
    if hasattr(base.base.core, _name):
        setattr(base.base.core, _name, _value)


def build_contract() -> dict[str, Any]:
    contract = base.base._r470_build_contract()
    inherited = contract.pop("r470")
    inherited["successor_of"] = "R476"
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
    inherited["reused_cells"] = [
        f"train|{arm}|{seed}" for arm, seed in REUSED_CELLS
    ]
    inherited["reuse_source_round"] = "R476"
    inherited["engineering_correction"] = (
        "R476 wave-1 training shards imported by hash-identical hardlink "
        "after per-shard scientific-identity verification; identical review "
        "maps; executable terminal truth; fail-closed classification"
    )
    contract["r477"] = inherited
    return contract


def authority_checks() -> dict[str, bool]:
    plan = PLAN.read_text(encoding="utf-8")
    line = LINE.read_text(encoding="utf-8")
    return {
        "active_plan": "round: R477" in plan and "state: active" in plan,
        "active_line": (
            "line_id: yang-md-decoupling-marl" in line and "status: active" in line
        ),
        "contract_closed": (
            len(base.base.core.ARMS) == 18
            and len(base.base.core.TRAINING_SEEDS) == 6
            and len(RETRAIN_CELLS) == 32
            and len(REUSED_CELLS) == 16
            and len(REUSE_ARMS) == 0
            and set(REUSED_CELLS).isdisjoint(RETRAIN_CELLS)
        ),
        "output_absence": not OUT.exists(),
        "carryover_present": R476_OUT.joinpath(
            "train", "an_cn_r0", "seed401", "manifest.json"
        ).is_file(),
    }


def _reviewed_files() -> tuple[Path, ...]:
    return (
        Path(__file__).resolve(),
        RUNNER_TESTS,
        INTEGRITY_MODULE,
        INTEGRITY_TESTS,
        PIPELINE,
        ROOT / "scripts/run_r476_u2_confirmatory.py",
        ROOT / "scripts/soft_spot_shard_driver.py",
        ROOT / "memory/tools/detached_pipeline_lint.py",
        ROOT / "tests/test_detached_pipeline_lint.py",
        ROOT / "tests/test_soft_spot_shard_driver.py",
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
        contract_sha256=base.base.core.contract_sha256(),
        bound_files=_bound_files(),
        review_paths=(REVIEW_A, REVIEW_B),
        reviewed_files=_reviewed_files(),
        expected_shards={
            "train": TRAIN_SHARD_IDS,
            "train_wave_1": TRAIN_WAVE_IDS[0],
            "train_wave_2": TRAIN_WAVE_IDS[1],
            "eval": EVAL_SHARD_IDS,
        },
    )


_r476_rehearsal = base.rehearsal
_r476_train_arm_seed = base.train_arm_seed
_r476_evaluate_arm_stage = base.evaluate_arm_stage


def rehearsal() -> dict[str, Any]:
    # The R476 implementation already binds the rehearsed terminal
    # predicate through the injected R477 contract; no second guard layer.
    return _r476_rehearsal()


def train_arm_seed(arm_id: str, seed: int) -> str:
    return _r476_train_arm_seed(arm_id, seed)


def evaluate_arm_stage(arm_id: str, stage: str) -> None:
    _r476_evaluate_arm_stage(arm_id, stage)


def _write_shard_list(path: Path, values: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != list(values):
            raise RuntimeError(f"existing shard list drift: {path}")
        return
    path.write_text(json.dumps(list(values)) + "\n", encoding="utf-8")


def prepare() -> dict[str, Any]:
    if SEAL.exists():
        raise FileExistsError(f"R477 formal seal already exists: {SEAL}")
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed: {checks}")
    power = base.base.core._read_hashed_json(POWER)
    base_audit = base.base.core._read_hashed_json(BASE_AUDIT)
    routing = base.base.core._read_hashed_json(ROUTING_GATE)
    rehearsal_payload = base.base.core._read_hashed_json(REHEARSAL)
    capacity = base.base.core._read_hashed_json(CAPACITY)
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
    review = validate_review_coverage(
        (REVIEW_A, REVIEW_B),
        repo_root=ROOT,
        reviewed_files=_reviewed_files(),
    )
    _write_shard_list(TRAIN_SHARDS, TRAIN_SHARD_IDS)
    for path, values in zip(TRAIN_WAVE_SHARDS, TRAIN_WAVE_IDS, strict=True):
        _write_shard_list(path, values)
    _write_shard_list(EVAL_SHARDS, EVAL_SHARD_IDS)

    sources = {
        "successor_runner": Path(__file__).resolve(),
        "successor_tests": RUNNER_TESTS,
        "sealed_r476_parent": ROOT / "scripts/run_r476_u2_confirmatory.py",
        "sealed_r475_parent": ROOT / "scripts/run_r475_u2_confirmatory.py",
        "sealed_r474_parent": ROOT / "scripts/run_r474_u2_source_factorial.py",
        "sealed_r473_parent": ROOT / "scripts/run_r473_u2_source_factorial.py",
        "sealed_r472_parent": ROOT / "scripts/run_r472_u2_source_factorial.py",
        "sealed_r471_parent": ROOT / "scripts/run_r471_u2_source_factorial.py",
        "sealed_r470_parent": ROOT / "scripts/run_r470_u2_source_factorial.py",
        "r451_structural_parent": ROOT / "scripts/run_r451_m3_message_factorial.py",
        "r438_parent": ROOT / "scripts/run_r438_sac_message_channels.py",
        "r431_parent": ROOT / "scripts/run_r431_sac_slew.py",
        "confirmatory_integrity": INTEGRITY_MODULE,
        "confirmatory_integrity_tests": INTEGRITY_TESTS,
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
        "contract_sha256": base.base.core.contract_sha256(),
        **{field: base.base.core._sha256_file(path) for field, path in _bound_files().items()},
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
                "path": base.base.core._relative(path),
                "sha256": base.base.core._sha256_file(path),
            }
            for name, path in sources.items()
        },
        "shard_lists": {
            "train": {
                "path": base.base.core._relative(TRAIN_SHARDS),
                "sha256": base.base.core._sha256_file(TRAIN_SHARDS),
            },
            **{
                f"train_wave_{index}": {
                    "path": base.base.core._relative(path),
                    "sha256": base.base.core._sha256_file(path),
                }
                for index, path in enumerate(TRAIN_WAVE_SHARDS, start=1)
            },
            "eval": {
                "path": base.base.core._relative(EVAL_SHARDS),
                "sha256": base.base.core._sha256_file(EVAL_SHARDS),
            },
        },
        "reuse": {
            "source_round": "R476",
            "reused_cells": [f"{arm}|{seed}" for arm, seed in REUSED_CELLS],
            "reused_source_root": base.base.core._relative(R476_OUT),
        },
        "formal_authority": True,
        "training_executed": False,
    }
    seal_sha = base.base.core._write_new_json(SEAL, seal)
    load_seal()
    return {
        "seal_sha256": seal_sha,
        "selected_workers": 16,
        "fresh_training_shards": len(TRAIN_SHARD_IDS),
        "reused_training_shards": len(REUSED_CELLS),
        "fresh_eval_shards": len(EVAL_SHARD_IDS),
        "reviewed_file_count": len(review.reviewed_files),
        "reviewed_commit": review.reviewed_commit,
    }


def missing_shards() -> list[str]:
    missing: list[str] = []
    for arm, seed in (*REUSED_CELLS, *RETRAIN_CELLS):
        manifest = OUT / "train" / arm / f"seed{seed}" / "manifest.json"
        if not manifest.is_file():
            missing.append(f"train|{arm}|{seed}")
    for arm in RETRAIN_ARMS:
        for seed in base.base.core.TRAINING_SEEDS:
            for stage in ("half", "final"):
                if not (OUT / "eval" / stage / arm / f"seed{seed}").is_dir():
                    missing.append(f"eval|{stage}|{arm}|{seed}")
    return missing


def artifact_budget_check(*, max_bytes: int = 650 * 1024 * 1024) -> dict[str, int]:
    return check_artifact_budget(OUT, max_bytes=max_bytes)


def import_r476_training_shards() -> str:
    """Import R476 wave-1 training shards into the R477 output root.

    Every reused manifest must pass scientific-identity verification
    (valid, 43,200 steps, arm/seed match, factors, base-state hash,
    reward-function hash) before its files are hardlinked with their
    sidecars. Any mismatch stops the pipeline.
    """
    base.base.core._assert_wsl_scratch()
    entries: list[dict[str, Any]] = []
    for arm, seed in REUSED_CELLS:
        src_dir = R476_OUT / "train" / arm / f"seed{seed}"
        manifest = base.base.core._read_hashed_json(src_dir / "manifest.json")
        if manifest.get("round") != "R476":
            raise RuntimeError(f"not an R476 manifest: {arm}|{seed}")
        if not manifest.get("valid") or int(manifest.get("interaction_steps")) != 43_200:
            raise RuntimeError(f"R476 manifest not complete: {arm}|{seed}")
        if manifest.get("arm_id") != arm or int(manifest.get("training_seed")) != seed:
            raise RuntimeError(f"R476 manifest identity mismatch: {arm}|{seed}")
        if manifest.get("factors") != base.base.core.arm_factors(arm):
            raise RuntimeError(f"R476 manifest factors mismatch: {arm}|{seed}")
        donor_manifest = base.base.core._read_hashed_json(
            OUT / "donors" / f"seed{seed}" / "manifest.json"
        )
        if manifest.get("reward_function_sha256") != donor_manifest.get(
            "reward_function_sha256"
        ):
            raise RuntimeError(f"reward identity mismatch: {arm}|{seed}")
        base_sha = base.base.core._sha256_file(
            OUT / "donors" / f"seed{seed}" / "base_state.pt"
        )
        if manifest.get("base_state_sha256") != base_sha:
            raise RuntimeError(f"base-state identity mismatch: {arm}|{seed}")
        for name in ("manifest.json", "half.pt", "final.pt", "full_curves.npz"):
            source = src_dir / name
            target = OUT / "train" / arm / f"seed{seed}" / name
            if target.exists():
                raise FileExistsError(f"import target exists: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            os.link(source, target)
            if base.base.core._sha256_file(source) != base.base.core._sha256_file(target):
                raise RuntimeError(f"hardlink hash mismatch: {target}")
            src_stat, tgt_stat = os.stat(source), os.stat(target)
            if src_stat.st_dev != tgt_stat.st_dev or src_stat.st_ino != tgt_stat.st_ino:
                raise RuntimeError(f"not the same hardlink identity: {target}")
            entries.append(
                {
                    "source": base.base.core._relative(source),
                    "target": base.base.core._relative(target),
                    "sha256": base.base.core._sha256_file(target),
                    "bytes": target.stat().st_size,
                    "same_inode": True,
                }
            )
            src_side = Path(f"{source}.sha256")
            tgt_side = Path(f"{target}.sha256")
            if not src_side.is_file():
                raise RuntimeError(f"missing R476 sidecar: {src_side}")
            if tgt_side.exists():
                raise FileExistsError(f"import sidecar target exists: {tgt_side}")
            os.link(src_side, tgt_side)
            entries.append(
                {
                    "source": base.base.core._relative(src_side),
                    "target": base.base.core._relative(tgt_side),
                    "sha256": base.base.core._sha256_file(tgt_side),
                    "bytes": tgt_side.stat().st_size,
                    "same_inode": True,
                }
            )
    return base.base.core._write_new_json(
        OUT / "r476_shard_import.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "source_round": "R476",
            "imported_training_shards": [
                f"{arm}|{seed}" for arm, seed in REUSED_CELLS
            ],
            "verified": {
                "round": True,
                "valid_and_steps": True,
                "identity": True,
                "factors": True,
                "reward_function": True,
                "base_state": True,
            },
            "hardlink_entries": entries,
            "entry_count": len(entries),
            "logical_bytes": sum(row["bytes"] for row in entries),
            "all_same_inode": all(row["same_inode"] for row in entries),
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )


def import_parent_artifacts() -> str:
    """Donor import (inherited R476 implementation, R477 paths) then the
    R476 wave-1 training shard import."""
    donor_result = base.import_parent_artifacts()
    shard_result = import_r476_training_shards()
    return json.dumps(
        {"donor_import": donor_result, "shard_import": shard_result}, indent=2
    )


def aggregate() -> str:
    base.base.core._assert_wsl_scratch()
    load_seal()
    payload = build_confirmatory_analysis(
        ConfirmatoryAnalysisContext(
            round_id=ROUND_ID,
            contract_sha256=base.base.core.contract_sha256(),
            seal_sha256=base.base.core._sha256_file(SEAL),
            output_root=OUT,
            arms=tuple(RETRAIN_ARMS),
            seeds=tuple(base.base.core.TRAINING_SEEDS),
            primary_metric=base.base.PRIMARY,
            secondary_metric=base.base.SECONDARY,
            materiality_log=base.base.MATERIALITY_LOG,
            scope=(
                "six seeds; frozen R470 learner/bank/projector only; "
                "16 R476 wave-1 cells carried over by hash-identical "
                "hardlink; 32 all-fresh cells; row-permuted P"
            ),
            read_hashed_json=base.base.core._read_hashed_json,
            arm_factors=base.base.core.arm_factors,
            paired_main_effects=base.base._paired_main_effects,
            signflip_p_one_sided=base.base._signflip_p_one_sided,
            exact_bootstrap_ci=base.base._exact_bootstrap_ci,
            apply_holm_two=base.base._apply_holm_two,
            design_valid=base.base.routing_gate_passed,
            created_utc=datetime.now(UTC).isoformat(),
        ),
        missing_shards=missing_shards(),
    )
    return base.base.core._write_new_json(OUT / "formal_analysis.json", payload)


def write_eta_recalibration(driver_result: Path) -> str:
    load_seal()
    payload = json.loads(driver_result.read_text(encoding="utf-8"))
    if set(payload.get("results", {})) != set(TRAIN_WAVE_IDS[0]):
        raise RuntimeError("ETA input is not the exact first sealed training wave")
    eta = {
        **recalibrate_eta(
            payload,
            remaining_training_shards=16,
            evaluation_wave_count=1,
        ),
        "round": ROUND_ID,
        "driver_result": base.base.core._relative(driver_result),
        "driver_result_sha256": base.base.core._sha256_file(driver_result),
        "created_utc": datetime.now(UTC).isoformat(),
    }
    return base.base.core._write_new_json(ETA_RECALIBRATION, eta)


def write_pipeline_inventory() -> str:
    payload = inventory_artifacts(
        repo_root=ROOT,
        result_root=OUT,
        log_roots=(TRAIN_LOG_ROOT, EVAL_LOG_ROOT),
        phase=os.environ.get("R477_PIPELINE_PHASE", "unknown"),
        exit_code=int(os.environ.get("R477_PIPELINE_EXIT_CODE", "1")),
        created_utc=datetime.now(UTC).isoformat(),
    )
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    return base.base.core._write_new_json(PIPELINE_INVENTORY / f"inventory_{stamp}.json", payload)


def formal_manifest() -> str:
    """Finalize only a complete, budget-valid, hash-valid R477 execution."""

    load_seal()
    artifact_budget_check()
    missing = missing_shards()
    if missing:
        raise RuntimeError(f"cannot finalize with missing shards: {missing[:5]}")
    training_manifests = list(OUT.glob("train/*/seed*/manifest.json"))
    if len(training_manifests) != 48:
        raise RuntimeError(f"expected 48 training manifests, found {len(training_manifests)}")
    analysis = base.base.core._read_hashed_json(OUT / "formal_analysis.json")
    classification = analysis.get("classification", {})
    required = {
        "design": "VALID",
        "execution": "COMPLETE",
        "integrity": "PASS",
    }
    if any(classification.get(field) != value for field, value in required.items()):
        raise RuntimeError(f"formal analysis is not finalizable: {classification}")
    return base.formal_manifest()


source_rows = base.source_rows
routing_check = base.routing_check
routing_gate = base.routing_gate
base_audit = base.base_audit

for _name, _value in {
    "authority_checks": authority_checks,
    "build_contract": build_contract,
    "rehearsal": rehearsal,
    "prepare": prepare,
    "source_rows": source_rows,
    "load_seal": load_seal,
    "train_arm_seed": train_arm_seed,
    "evaluate_arm_stage": evaluate_arm_stage,
    "aggregate": aggregate,
    "missing_shards": missing_shards,
}.items():
    setattr(base, _name, _value)
    setattr(base.base, _name, _value)
    setattr(base.base.core, _name, _value)


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
            "eta",
            "inventory",
            "manifest",
        ),
    )
    parser.add_argument("shard_id", nargs="?")
    args = parser.parse_args()
    if args.command == "base":
        payload = base_audit()
        digest = base.base.core._write_new_json(BASE_AUDIT, payload)
        base.base.core.safe_emit(json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True))
    elif args.command == "import":
        base.base.core.safe_emit(import_parent_artifacts())
    elif args.command == "route":
        payload = routing_gate()
        digest = base.base.core._write_new_json(ROUTING_GATE, payload)
        base.base.core.safe_emit(json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True))
    elif args.command == "rehearse":
        payload = rehearsal()
        digest = base.base.core._write_new_json(REHEARSAL, payload)
        base.base.core.safe_emit(json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True))
    elif args.command == "prepare":
        base.base.core.safe_emit(json.dumps(prepare(), indent=2, sort_keys=True))
    elif args.command == "verify":
        base.base.core.safe_emit(json.dumps(load_seal(), indent=2, sort_keys=True))
    elif args.command == "aggregate":
        base.base.core.safe_emit(aggregate())
    elif args.command == "budget":
        load_seal()
        base.base.core.safe_emit(json.dumps(artifact_budget_check(), sort_keys=True))
    elif args.command == "eta":
        if args.shard_id is None:
            raise SystemExit("eta requires the first-wave driver result path")
        path = Path(args.shard_id)
        if not path.is_absolute():
            path = ROOT / path
        base.base.core.safe_emit(write_eta_recalibration(path.resolve()))
    elif args.command == "inventory":
        base.base.core.safe_emit(write_pipeline_inventory())
    elif args.command == "manifest":
        base.base.core.safe_emit(formal_manifest())
    else:
        if args.shard_id is None:
            raise SystemExit("shard requires a shard id")
        parts = args.shard_id.split("|")
        if parts[0] == "train" and len(parts) == 3:
            base.base.core.safe_emit(train_arm_seed(parts[1], int(parts[2])))
        elif parts[0] == "eval" and len(parts) == 3:
            evaluate_arm_stage(parts[2], parts[1])
        else:
            raise SystemExit(f"unsupported shard: {args.shard_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
