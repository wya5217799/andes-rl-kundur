#!/usr/bin/env python3
"""R292 formal adapter consuming the passing versioned v3 q0 screen."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "scripts/run_r292_formal.py"
SPEC = importlib.util.spec_from_file_location("run_r292_formal_v3_core", CORE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load R292 formal core: {CORE_PATH}")
FORMAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FORMAL)

AMENDMENT = ROOT / "memory/rounds/R292/execution_amendment_20260731_v3.json"
FORMAL.FRESH_DIR = ROOT / "results/r292_fresh_bank_v3"
FORMAL.FORMAL_BANK = FORMAL.FRESH_DIR / "formal_bank.json"
FORMAL.SCREEN_SUMMARY = FORMAL.FRESH_DIR / "screen_summary.json"
FORMAL.SCREEN_CONTRACT = FORMAL.FRESH_DIR / "feasibility_screen_contract.json"
FORMAL.SCREEN_PROVENANCE = FORMAL.FRESH_DIR / "provenance.json"
FORMAL.DEFAULT_SEAL = ROOT / "memory/rounds/R292/formal_v3_seal.json"
FORMAL.DEFAULT_OUT = ROOT / "results/r292_formal_evaluation_v3"


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R292/plan.md",
        "execution_amendment_v3": AMENDMENT,
        "formal_core": CORE_PATH,
        "formal_v3_adapter": Path(__file__).resolve(),
        "recovery_v3": ROOT / "scripts/recover_r292_fresh_bank_v3.py",
        "recovery_v3_launcher": ROOT / "scripts/run_r292_recovery_v3_unattended.sh",
        "vector_runner": ROOT
        / "src/andes_rl_kundur/evaluation/vector_residual.py",
        "statistics": ROOT
        / "src/andes_rl_kundur/evaluation/reviewer_identifiability.py",
        "sealed_bank": ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py",
        "vector_actor": ROOT / "src/andes_rl_kundur/agents/vector_residual_td3.py",
        "vector_environment": ROOT
        / "src/andes_rl_kundur/env/andes/distributed_residual_env.py",
        "vector_contract": ROOT
        / "src/andes_rl_kundur/control/vector_inertia_residual.py",
        "r292_screen_audit": ROOT
        / "src/andes_rl_kundur/evaluation/r292_screen.py",
        "r292_screen_bank": ROOT
        / "src/andes_rl_kundur/evaluation/r292_screen_bank.py",
        "formal_bank": FORMAL.FORMAL_BANK,
        "screen_summary": FORMAL.SCREEN_SUMMARY,
        "screen_contract": FORMAL.SCREEN_CONTRACT,
        "screen_provenance": FORMAL.SCREEN_PROVENANCE,
        "training_summary": FORMAL.TRAINING_SUMMARY,
    }


def prepare(manifest_path: Path, out_dir: Path) -> None:
    trace_dir = out_dir / "traces"
    if manifest_path.exists():
        raise FileExistsError(f"v3 formal seal already exists: {manifest_path}")
    if trace_dir.exists() and any(trace_dir.glob("*.json")):
        raise ValueError("v3 formal seal must precede every v3 controller trace")
    training = FORMAL._load_json(FORMAL.TRAINING_SUMMARY)
    screen = FORMAL._load_json(FORMAL.SCREEN_SUMMARY)
    FORMAL._verify_upstreams(training, screen)
    provenance = FORMAL._load_json(FORMAL.SCREEN_PROVENANCE)
    if provenance.get("performance_endpoints_inspected") is not False:
        raise ValueError("v3 screen inspected forbidden performance endpoints")
    if provenance.get("andes_trajectory_count") != 0:
        raise ValueError("v3 screen unexpectedly ran new ANDES trajectories")
    for path_text, digest in provenance["trace_hashes"].items():
        if FORMAL.sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"v3 screen trace drift: {path_text}")
    bank, bank_hash = FORMAL.load_scenario_bank(
        FORMAL.FORMAL_BANK,
        expected_sha256=screen["formal_bank_sha256"],
    )
    if bank["scenario_count"] != 24:
        raise ValueError("R292 v3 formal bank must contain exactly 24 scenarios")
    arms = FORMAL._arm_manifest(training)
    sources = {
        name: {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": FORMAL.sha256_file(path),
        }
        for name, path in _source_paths().items()
    }
    payload: dict[str, Any] = {
        "schema_version": 1,
        "round": FORMAL.ROUND_ID,
        "question": FORMAL.QUESTION_ID,
        "phase": "fresh-bank-seven-arm-vector-formal",
        "repository_head": FORMAL._git_head(),
        "recovery": {
            "version": 3,
            "execution_amendment": str(AMENDMENT.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "failed_screen_attempts_preserved": ["original", "v2"],
            "screen_reused_immutable_q0_traces": 24,
            "screen_andes_trajectory_count": 0,
            "performance_endpoints_inspected_before_formal_seal": False,
        },
        "formal_bank": {
            "path": str(FORMAL.FORMAL_BANK.relative_to(ROOT)).replace("\\", "/"),
            "sha256": bank_hash,
            "scenario_count": 24,
        },
        "screen": {
            "summary_sha256": FORMAL.sha256_file(FORMAL.SCREEN_SUMMARY),
            "contract_sha256": FORMAL.sha256_file(FORMAL.SCREEN_CONTRACT),
            "provenance_sha256": FORMAL.sha256_file(FORMAL.SCREEN_PROVENANCE),
            "frozen_trace_hashes": provenance["trace_hashes"],
        },
        "training_summary_sha256": FORMAL.sha256_file(FORMAL.TRAINING_SUMMARY),
        "arms": arms,
        "execution": {
            "environment_seed": FORMAL.ENV_SEED,
            "steps": FORMAL.STEPS,
            "shard_count": FORMAL.SHARD_COUNT,
            "arm_count": len(FORMAL.ARMS),
            "trajectory_budget": len(FORMAL.ARMS) * 24,
            "resume_completed": True,
            "overwrite": False,
            "retry_failed_trajectory": False,
        },
        "statistics": {
            "hierarchical_bootstrap_seed": FORMAL.BOOTSTRAP_SEED,
            "resamples": FORMAL.BOOTSTRAP_RESAMPLES,
            "materiality_percent": -2.0,
            "confidence": 0.95,
            "lower_is_better": True,
            "primary_endpoints": list(FORMAL.PRIMARY_ENDPOINTS),
        },
        "guards": {
            "fast_common_mean_and_cvar_no_harm_percent": 5.0,
            "slow_common_mean_and_cvar_no_harm_percent": 2.0,
            "storage_relative_no_harm_percent": 5.0,
            "command_and_actual_abs_system_pu_max": 0.36,
            "soc_range": [0.20, 0.80],
            "zero_constraint_violations": True,
            "zero_saturation_reasons": True,
            "distributed_directional_seed_minimum": 2,
        },
        "sources": sources,
        "formal_trace_count_at_freeze": 0,
    }
    digest = FORMAL._write_new(manifest_path, payload)
    print(f"[sealed] {manifest_path} sha256={digest}", flush=True)


FORMAL._source_paths = _source_paths
FORMAL.prepare = prepare


def main() -> None:
    FORMAL.main()


if __name__ == "__main__":
    main()
