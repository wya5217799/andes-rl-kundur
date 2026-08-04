#!/usr/bin/env python3
"""Seal, execute, and analyse the R293 12-arm formal comparison."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from andes_rl_kundur.agents.classical_prior_td3 import (  # noqa: E402
    CentralPriorResidualTD3,
    DistributedPriorResidualTD3,
)
from andes_rl_kundur.control.classical_edge_residual import (  # noqa: E402
    ClassicalEdgeContract,
    ClassicalEdgeController,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    empirical_upper_tail,
    load_scenario_bank,
    sha256_bytes,
    sha256_file,
)
from andes_rl_kundur.evaluation.vector_residual import (  # noqa: E402
    audit_vector_action,
    run_vector_controller_scenario,
    summarise_vector_trace,
)
from probes.r293_comparison import (  # noqa: E402
    classify_r293,
    hierarchical_ratio_bootstrap,
    paired_ratio_bootstrap,
)

ROUND_ID = "R293"
QUESTION_ID = "Q-0050"
ENV_SEED = 42
STEPS = 300
FAST_STEPS = 15
FINAL_WINDOW_STEPS = 50
SHARD_COUNT = 3
SEEDS = (211, 257, 293, 331, 379)
BOOTSTRAP_RESAMPLES = 20_000
BOOTSTRAP_SEED = 2026080204
PRIMARY_ENDPOINTS = (
    "normalized_sync_loss_hz2",
    "fast_inter_area_iae_hz_s",
)
FAST_COMMON_ENDPOINTS = (
    "max_abs_rocof_hz_s",
    "worst_bus_peak_abs_hz",
    "first_3s_common_iae_hz_s",
)
SLOW_COMMON_ENDPOINTS = (
    "vsg_mean_iae_hz_s",
    "final_window_common_abs_mean_hz",
)
STORAGE_ENDPOINTS = (
    "bess_command_l1_device_s",
    "bess_command_total_variation",
    "bess_charge_energy_mwh_total",
    "bess_discharge_energy_mwh_total",
)
STATISTICAL_ENDPOINTS = (
    *PRIMARY_ENDPOINTS,
    *FAST_COMMON_ENDPOINTS,
    *SLOW_COMMON_ENDPOINTS,
)
CONTINUOUS_ENDPOINTS = (*STATISTICAL_ENDPOINTS, *STORAGE_ENDPOINTS)
TAIL_ENDPOINTS = STATISTICAL_ENDPOINTS
ARMS = (
    "q0",
    "classical_edge",
    *(f"central_prior_s{seed}" for seed in SEEDS),
    *(f"distributed_prior_s{seed}" for seed in SEEDS),
)
NEW_TRACE_ARMS = ARMS[1:]
FRESH_DIR = ROOT / "results/r293_fresh_bank"
FORMAL_BANK = FRESH_DIR / "formal_bank.json"
SCREEN_SUMMARY = FRESH_DIR / "screen_summary.json"
SCREEN_CONTRACT = FRESH_DIR / "feasibility_screen_contract.json"
SCREEN_PROVENANCE = FRESH_DIR / "provenance.json"
TRAINING_SUMMARY = ROOT / "results/r293_prior_residual_training/training_matrix_summary.json"
CLASSICAL_GUARD = ROOT / "results/r293_classical_guard/classical_guard_summary.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R293/formal_seal.json"
DEFAULT_OUT = ROOT / "results/r293_formal_evaluation"


def _write_new(path: Path, payload: object) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(payload)
    path.write_bytes(data)
    digest = sha256_bytes(data)
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return digest


def _load_json(path: Path, expected: str | None = None) -> dict[str, Any]:
    if expected is not None and sha256_file(path) != expected:
        raise ValueError(f"hash mismatch: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _checkpoint_path(architecture: str, seed: int) -> Path:
    return ROOT / (
        f"results/r293_prior_residual_training/{architecture}_s{seed}/final.pt"
    )


def _contract_path(architecture: str, seed: int) -> Path:
    return ROOT / (
        f"results/r293_prior_residual_training/{architecture}_s{seed}/"
        "controller_contract.json"
    )


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R293/plan.md",
        "script": Path(__file__).resolve(),
        "decision_probe": ROOT / "probes/r293_comparison.py",
        "vector_runner": ROOT / "src/andes_rl_kundur/evaluation/vector_residual.py",
        "sealed_bank": ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py",
        "prior_actor": ROOT / "src/andes_rl_kundur/agents/classical_prior_td3.py",
        "vector_actor": ROOT / "src/andes_rl_kundur/agents/vector_residual_td3.py",
        "classical_controller": ROOT
        / "src/andes_rl_kundur/control/classical_edge_residual.py",
        "vector_environment": ROOT
        / "src/andes_rl_kundur/env/andes/distributed_residual_env.py",
        "vector_contract": ROOT
        / "src/andes_rl_kundur/control/vector_inertia_residual.py",
        "formal_bank": FORMAL_BANK,
        "screen_summary": SCREEN_SUMMARY,
        "screen_contract": SCREEN_CONTRACT,
        "screen_provenance": SCREEN_PROVENANCE,
        "training_summary": TRAINING_SUMMARY,
        "classical_guard": CLASSICAL_GUARD,
    }


def _verify_upstreams(training: dict[str, Any], screen: dict[str, Any]) -> None:
    if not training.get("all_completed") or training.get("observed_run_count") != 10:
        raise ValueError("formal evaluation requires ten completed checkpoints")
    if training.get("seed_selection_performed") is not False:
        raise ValueError("formal evaluation forbids seed selection")
    for path_text, digest in training.get("artifact_hashes", {}).items():
        if sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"training artifact drift: {path_text}")
    if screen.get("decision", {}).get("classification") != "PASS":
        raise ValueError("formal evaluation requires a passing fresh-bank screen")
    if screen.get("controller_trace_count_at_freeze") != 0:
        raise ValueError("fresh bank was not frozen before controller traces")
    if screen.get("redraw_performed") is not False:
        raise ValueError("fresh bank reports a forbidden redraw")


def _classical_contract() -> ClassicalEdgeContract:
    guard = _load_json(CLASSICAL_GUARD)
    if guard.get("classification") != "CLASSICAL-GUARD-PASS":
        raise ValueError("classical comparator did not pass its development guard")
    row = guard["selected_classical_contract"]
    return ClassicalEdgeContract(
        family=row["family"],
        gain=float(row["gain"]),
        residual_scale=float(row["residual_scale"]),
    )


def _arm_manifest(training: dict[str, Any]) -> dict[str, Any]:
    rows = {(row["architecture"], int(row["seed"])): row for row in training["rows"]}
    classical = _classical_contract()
    arms: dict[str, Any] = {
        "q0": {"kind": "deterministic", "controller": "q0"},
        "classical_edge": {
            "kind": "deterministic",
            "controller": classical.name,
            "contract": classical.telemetry(),
            "classical_guard_sha256": sha256_file(CLASSICAL_GUARD),
        },
    }
    for architecture in ("central_prior", "distributed_prior"):
        for seed in SEEDS:
            row = rows[(architecture, seed)]
            checkpoint = _checkpoint_path(architecture, seed)
            contract = _contract_path(architecture, seed)
            if sha256_file(checkpoint) != row["checkpoint_sha256"]:
                raise ValueError(f"checkpoint drift: {checkpoint}")
            arms[f"{architecture}_s{seed}"] = {
                "kind": "learned",
                "architecture": architecture,
                "seed": seed,
                "checkpoint": str(checkpoint.relative_to(ROOT)).replace("\\", "/"),
                "checkpoint_sha256": row["checkpoint_sha256"],
                "controller_contract": str(contract.relative_to(ROOT)).replace("\\", "/"),
                "controller_contract_sha256": sha256_file(contract),
                "actor_parameter_count": row["actor_parameter_count"],
            }
    if tuple(arms) != ARMS:
        raise ValueError("R293 formal arm order drift")
    return arms


def prepare(manifest_path: Path, out_dir: Path) -> None:
    if manifest_path.exists():
        raise FileExistsError(f"formal seal already exists: {manifest_path}")
    trace_dir = out_dir / "traces"
    if trace_dir.exists() and any(trace_dir.glob("*.json")):
        raise ValueError("formal seal must precede every new formal trace")
    training = _load_json(TRAINING_SUMMARY)
    screen = _load_json(SCREEN_SUMMARY)
    _verify_upstreams(training, screen)
    screen_provenance = _load_json(SCREEN_PROVENANCE)
    for path_text, digest in screen_provenance["trace_hashes"].items():
        if sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"fresh-screen q0 trace drift: {path_text}")
    bank, bank_hash = load_scenario_bank(
        FORMAL_BANK, expected_sha256=screen["formal_bank_sha256"]
    )
    if bank["scenario_count"] != 24:
        raise ValueError("R293 formal bank must contain exactly 24 scenarios")
    arms = _arm_manifest(training)
    sources = {
        name: {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(path),
        }
        for name, path in _source_paths().items()
    }
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "fresh-bank-twelve-arm-prior-residual-formal",
        "repository_head": _git_head(),
        "formal_bank": {
            "path": str(FORMAL_BANK.relative_to(ROOT)).replace("\\", "/"),
            "sha256": bank_hash,
            "scenario_count": 24,
        },
        "screen": {
            "summary_sha256": sha256_file(SCREEN_SUMMARY),
            "contract_sha256": sha256_file(SCREEN_CONTRACT),
            "provenance_sha256": sha256_file(SCREEN_PROVENANCE),
            "frozen_q0_trace_hashes": screen_provenance["trace_hashes"],
            "q0_reuse_after_formal_seal": True,
        },
        "training_summary_sha256": sha256_file(TRAINING_SUMMARY),
        "arms": arms,
        "execution": {
            "environment_seed": ENV_SEED,
            "steps": STEPS,
            "shard_count": SHARD_COUNT,
            "arm_count": len(ARMS),
            "new_controller_trajectory_budget": len(NEW_TRACE_ARMS) * 24,
            "reused_q0_trajectory_count": 24,
            "total_matrix_count": len(ARMS) * 24,
            "overwrite": False,
            "retry_failed_controller_trajectory": False,
        },
        "statistics": {
            "hierarchical_bootstrap_seed": BOOTSTRAP_SEED,
            "resamples": BOOTSTRAP_RESAMPLES,
            "materiality_percent": -2.0,
            "confidence": 0.95,
            "noninferiority_margin_percent": 5.0,
            "noninferiority_bound": "one_sided_95_upper",
            "lower_is_better": True,
            "primary_endpoints": list(PRIMARY_ENDPOINTS),
        },
        "guards": {
            "fast_common_mean_and_cvar_no_harm_percent": 5.0,
            "slow_common_mean_and_cvar_no_harm_percent": 2.0,
            "storage_relative_no_harm_percent": 5.0,
            "command_and_actual_abs_system_pu_max": 0.36,
            "soc_range": [0.20, 0.80],
            "zero_constraint_violations": True,
            "zero_saturation_reasons": True,
            "distributed_directional_seed_minimum": 3,
            "distributed_noninferior_seed_minimum": 3,
            "controller_failure_is_outcome_not_integrity": True,
        },
        "sources": sources,
        "formal_trace_count_at_freeze": 0,
    }
    digest = _write_new(manifest_path, payload)
    print(f"[sealed] {manifest_path} sha256={digest}", flush=True)


def _verify(manifest_path: Path, expected: str) -> dict[str, Any]:
    manifest = _load_json(manifest_path, expected)
    if manifest.get("round") != ROUND_ID:
        raise ValueError("not an R293 formal seal")
    for entry in manifest["sources"].values():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError(f"formal source drift: {entry['path']}")
    training = _load_json(TRAINING_SUMMARY, manifest["training_summary_sha256"])
    screen = _load_json(SCREEN_SUMMARY, manifest["screen"]["summary_sha256"])
    _verify_upstreams(training, screen)
    load_scenario_bank(FORMAL_BANK, expected_sha256=manifest["formal_bank"]["sha256"])
    for path_text, digest in manifest["screen"]["frozen_q0_trace_hashes"].items():
        if sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"fresh-screen q0 trace drift: {path_text}")
    for arm, config in manifest["arms"].items():
        if config["kind"] == "learned":
            if sha256_file(ROOT / config["checkpoint"]) != config["checkpoint_sha256"]:
                raise ValueError(f"checkpoint drift: {arm}")
            if sha256_file(ROOT / config["controller_contract"]) != config["controller_contract_sha256"]:
                raise ValueError(f"controller contract drift: {arm}")
    return manifest


def _make_controller(arm: str, config: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    classical = _classical_contract()
    if arm == "classical_edge":
        return ClassicalEdgeController(classical), {
            "architecture": "classical_edge",
            "classical_contract": classical.telemetry(),
        }
    architecture = config["architecture"]
    if architecture == "central_prior":
        controller: Any = CentralPriorResidualTD3(
            classical_contract=classical,
            critic_hidden_sizes=[64, 64],
            actor_hidden_sizes=[59, 59],
            device="cpu",
        )
    else:
        controller = DistributedPriorResidualTD3(
            classical_contract=classical,
            hidden_sizes=[64, 64],
            device="cpu",
        )
    metadata = controller.load(ROOT / config["checkpoint"])
    expected_metadata = {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "architecture": architecture,
        "seed": config["seed"],
        "episodes_completed": 300,
        "total_steps": 4500,
        "smoke": False,
    }
    for key, value in expected_metadata.items():
        if metadata.get(key) != value:
            raise ValueError(f"checkpoint metadata mismatch for {arm}: {key}")
    return controller, {
        "architecture": architecture,
        "seed": config["seed"],
        "checkpoint": config["checkpoint"],
        "checkpoint_sha256": config["checkpoint_sha256"],
        "controller_contract_sha256": config["controller_contract_sha256"],
        "classical_contract": classical.telemetry(),
        "checkpoint_metadata": metadata,
    }


def _trace_path(out_dir: Path, scenario: str, arm: str) -> Path:
    return out_dir / "traces" / f"{scenario}__{arm}.json"


def _validate_new_trace(
    path: Path,
    scenario: dict[str, Any],
    arm: str,
    manifest: dict[str, Any],
    seal_hash: str,
) -> dict[str, Any]:
    record = _load_json(path)
    expected = {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "fresh-bank-twelve-arm-prior-residual-formal",
        "controller": arm,
        "scenario": scenario["name"],
        "delta_u": scenario["delta_u"],
        "formal_seal_sha256": seal_hash,
        "formal_bank_sha256": manifest["formal_bank"]["sha256"],
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"formal trace provenance mismatch in {path}: {key}")
    return record


def run_shard(
    manifest_path: Path,
    expected: str,
    out_dir: Path,
    shard_index: int,
    shard_count: int,
) -> None:
    manifest = _verify(manifest_path, expected)
    if shard_count != SHARD_COUNT or not 0 <= shard_index < shard_count:
        raise ValueError("formal shard contract drift")
    bank, _ = load_scenario_bank(FORMAL_BANK, expected_sha256=manifest["formal_bank"]["sha256"])
    tasks = [(scenario, arm) for scenario in bank["scenarios"] for arm in NEW_TRACE_ARMS]
    selected = [task for index, task in enumerate(tasks) if index % shard_count == shard_index]
    controllers: dict[str, tuple[Any, dict[str, Any]]] = {}
    for index, (scenario, arm) in enumerate(selected, start=1):
        path = _trace_path(out_dir, scenario["name"], arm)
        if path.exists():
            _validate_new_trace(path, scenario, arm, manifest, expected)
            print(f"[resume {index:03d}/{len(selected):03d}] {path.name}", flush=True)
            continue
        try:
            if arm not in controllers:
                controllers[arm] = _make_controller(arm, manifest["arms"][arm])
            controller, controller_config = controllers[arm]
            record = run_vector_controller_scenario(
                controller,
                controller_name=arm,
                controller_config=controller_config,
                scenario_name=scenario["name"],
                delta_u=scenario["delta_u"],
                seed=ENV_SEED,
                steps=STEPS,
                phase="fresh-bank-twelve-arm-prior-residual-formal",
                evidence_hashes={
                    "formal_seal": expected,
                    "formal_bank": manifest["formal_bank"]["sha256"],
                },
            )
        except Exception as exc:
            record = {
                "schema_version": 1,
                "controller": arm,
                "scenario": scenario["name"],
                "delta_u": dict(scenario["delta_u"]),
                "requested_steps": STEPS,
                "n_steps": 0,
                "tds_failed": True,
                "completed": False,
                "traces": [],
                "setup_error": {"type": type(exc).__name__, "message": str(exc)},
                "seed": ENV_SEED,
            }
        record.update(
            {
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "experiment": "r293_strong_classical_prior_comparison",
                "phase": "fresh-bank-twelve-arm-prior-residual-formal",
                "controller": arm,
                "location": scenario["location"],
                "sign": scenario["sign"],
                "severity": scenario["severity"],
                "formal_seal_sha256": expected,
                "formal_bank_sha256": manifest["formal_bank"]["sha256"],
                "execution_shard_index": shard_index,
                "execution_shard_count": shard_count,
            }
        )
        digest = _write_new(path, record)
        print(
            f"[formal {index:03d}/{len(selected):03d}] {path.name} "
            f"completed={record['completed']} sha256={digest}",
            flush=True,
        )


def _q0_records(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path_text, digest in manifest["screen"]["frozen_q0_trace_hashes"].items():
        record = _load_json(ROOT / path_text, digest)
        if record.get("controller") != "q0" or not record.get("completed"):
            raise ValueError(f"invalid frozen q0 screen record: {path_text}")
        records[record["scenario"]] = record
    if len(records) != 24:
        raise ValueError("formal matrix requires 24 frozen q0 records")
    return records


def _endpoint_row(record: dict[str, Any]) -> dict[str, Any]:
    row = summarise_vector_trace(
        record,
        final_window_steps=FINAL_WINDOW_STEPS,
        fast_window_steps=FAST_STEPS,
    )
    delta = np.asarray(
        [step["delta_f_physical_hz"] for step in record["traces"]], dtype=float
    )
    row["first_3s_common_iae_hz_s"] = float(
        np.sum(np.abs(np.mean(delta, axis=1)[:FAST_STEPS]))
        * row["sample_interval_s"]
    )
    return row


def _aggregate_storage(records: list[dict[str, Any]]) -> dict[str, float | int]:
    steps = [step for record in records for step in record["traces"]]
    commanded = np.asarray(
        [value for step in steps for value in step["bess_commanded_power_system_pu"]],
        dtype=float,
    )
    actual = np.asarray(
        [value for step in steps for value in step["bess_actual_power_system_pu"]],
        dtype=float,
    )
    soc = np.asarray([value for step in steps for value in step["bess_soc"]], dtype=float)
    return {
        "max_abs_commanded_power_system_pu": float(np.max(np.abs(commanded))),
        "max_abs_actual_power_system_pu": float(np.max(np.abs(actual))),
        "min_soc": float(np.min(soc)),
        "max_soc": float(np.max(soc)),
        "constraint_violation_count": sum(
            len(step["bess_constraint_violations"]) for step in steps
        ),
        "saturation_reason_count": sum(
            bool(reason)
            for step in steps
            for reason in step["bess_saturation_reasons"]
        ),
    }


def _summary(
    rows: list[dict[str, Any]], records: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "sample_count": len(rows),
        "means": {
            endpoint: float(np.mean([row[endpoint] for row in rows]))
            for endpoint in CONTINUOUS_ENDPOINTS
        },
        "medians": {
            endpoint: float(np.median([row[endpoint] for row in rows]))
            for endpoint in CONTINUOUS_ENDPOINTS
        },
        "cvar90": {
            endpoint: empirical_upper_tail(
                {f"row_{index:03d}": float(row[endpoint]) for index, row in enumerate(rows)}
            )
            for endpoint in TAIL_ENDPOINTS
        },
        "storage": _aggregate_storage(records),
    }


def _relative(left: float, right: float) -> float:
    if right <= 0.0:
        raise ValueError("relative endpoint reference must be positive")
    return 100.0 * (left / right - 1.0)


def _guard_relative(left: float, right: float) -> float:
    if right <= 1e-15:
        return 0.0 if left <= 1e-15 else float("inf")
    return 100.0 * (left / right - 1.0)


def _absolute_storage_pass(row: dict[str, Any]) -> bool:
    return bool(
        row["constraint_violation_count"] == 0
        and row["saturation_reason_count"] == 0
        and row["max_abs_commanded_power_system_pu"] <= 0.36 + 1e-12
        and row["max_abs_actual_power_system_pu"] <= 0.36 + 1e-12
        and row["min_soc"] >= 0.20 - 1e-9
        and row["max_soc"] <= 0.80 + 1e-9
    )


def _relative_guards(candidate: dict[str, Any], classical: dict[str, Any]) -> dict[str, Any]:
    fast_mean = {
        endpoint: _relative(candidate["means"][endpoint], classical["means"][endpoint])
        for endpoint in FAST_COMMON_ENDPOINTS
    }
    slow_mean = {
        endpoint: _relative(candidate["means"][endpoint], classical["means"][endpoint])
        for endpoint in SLOW_COMMON_ENDPOINTS
    }
    storage_mean = {
        endpoint: _guard_relative(
            candidate["means"][endpoint], classical["means"][endpoint]
        )
        for endpoint in STORAGE_ENDPOINTS
    }
    tail = {
        endpoint: _relative(
            candidate["cvar90"][endpoint]["cvar_upper_tail"],
            classical["cvar90"][endpoint]["cvar_upper_tail"],
        )
        for endpoint in TAIL_ENDPOINTS
    }
    result = {
        "fast_common_mean_effect_percent": fast_mean,
        "slow_common_mean_effect_percent": slow_mean,
        "storage_mean_effect_percent": storage_mean,
        "tail_cvar90_effect_percent": tail,
    }
    result["pass"] = (
        all(value <= 5.0 for value in fast_mean.values())
        and all(value <= 2.0 for value in slow_mean.values())
        and all(value <= 5.0 for value in storage_mean.values())
        and all(
            value <= (2.0 if endpoint in SLOW_COMMON_ENDPOINTS else 5.0)
            for endpoint, value in tail.items()
        )
    )
    return result


def _hierarchical(
    grid: dict[str, dict[str, dict[str, Any]]],
    bank_names: list[str],
    left_prefix: str,
    right_prefix: str,
) -> dict[str, Any]:
    result = {}
    for endpoint in STATISTICAL_ENDPOINTS:
        left = {
            seed: {
                name: float(grid[name][f"{left_prefix}_s{seed}"][endpoint])
                for name in bank_names
            }
            for seed in SEEDS
        }
        if right_prefix in {"q0", "classical_edge"}:
            kwargs = {
                "right_deterministic": {
                    name: float(grid[name][right_prefix][endpoint]) for name in bank_names
                }
            }
        else:
            kwargs = {
                "right_by_seed": {
                    seed: {
                        name: float(grid[name][f"{right_prefix}_s{seed}"][endpoint])
                        for name in bank_names
                    }
                    for seed in SEEDS
                }
            }
        result[endpoint] = hierarchical_ratio_bootstrap(
            left,
            **kwargs,
            resamples=BOOTSTRAP_RESAMPLES,
            seed=BOOTSTRAP_SEED,
        )
    return result


def _classical_contrast(
    grid: dict[str, dict[str, dict[str, Any]]], bank_names: list[str]
) -> dict[str, Any]:
    return {
        endpoint: paired_ratio_bootstrap(
            {name: float(grid[name]["classical_edge"][endpoint]) for name in bank_names},
            {name: float(grid[name]["q0"][endpoint]) for name in bank_names},
            resamples=BOOTSTRAP_RESAMPLES,
            seed=BOOTSTRAP_SEED,
        )
        for endpoint in STATISTICAL_ENDPOINTS
    }


def _seed_counts(
    grid: dict[str, dict[str, dict[str, Any]]], bank_names: list[str]
) -> tuple[int, int, list[dict[str, Any]]]:
    rows = []
    for seed in SEEDS:
        directions = {}
        noninferiority = {}
        for endpoint in PRIMARY_ENDPOINTS:
            distributed = float(
                np.mean([grid[name][f"distributed_prior_s{seed}"][endpoint] for name in bank_names])
            )
            central = float(
                np.mean([grid[name][f"central_prior_s{seed}"][endpoint] for name in bank_names])
            )
            classical = float(
                np.mean([grid[name]["classical_edge"][endpoint] for name in bank_names])
            )
            directions[endpoint] = {
                "effect_percent_vs_classical": _relative(distributed, classical),
                "directional_improvement": distributed < classical,
            }
            noninferiority[endpoint] = {
                "effect_percent_vs_central": _relative(distributed, central),
                "within_5_percent": _relative(distributed, central) <= 5.0,
            }
        rows.append(
            {
                "seed": seed,
                "distributed_vs_classical": directions,
                "distributed_vs_central": noninferiority,
                "both_primary_directional_improvement": all(
                    row["directional_improvement"] for row in directions.values()
                ),
                "both_primary_within_noninferiority_margin": all(
                    row["within_5_percent"] for row in noninferiority.values()
                ),
            }
        )
    return (
        sum(row["both_primary_directional_improvement"] for row in rows),
        sum(row["both_primary_within_noninferiority_margin"] for row in rows),
        rows,
    )


def analyse(manifest_path: Path, expected: str, out_dir: Path) -> None:
    manifest = _verify(manifest_path, expected)
    bank, _ = load_scenario_bank(FORMAL_BANK, expected_sha256=manifest["formal_bank"]["sha256"])
    bank_names = [row["name"] for row in bank["scenarios"]]
    q0_records = _q0_records(manifest)
    records: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    records["q0"] = [q0_records[name] for name in bank_names]
    trace_hashes = dict(manifest["screen"]["frozen_q0_trace_hashes"])
    failures: list[dict[str, Any]] = []
    for scenario in bank["scenarios"]:
        for arm in NEW_TRACE_ARMS:
            path = _trace_path(out_dir, scenario["name"], arm)
            record = _validate_new_trace(path, scenario, arm, manifest, expected)
            digest = sha256_file(path)
            trace_hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = digest
            records[arm].append(record)
            if not record.get("completed") or record.get("tds_failed"):
                failures.append(
                    {
                        "scenario": scenario["name"],
                        "arm": arm,
                        "completed": bool(record.get("completed")),
                        "tds_failed": bool(record.get("tds_failed")),
                        "setup_error": record.get("setup_error"),
                        "trace_sha256": digest,
                    }
                )
    if failures:
        summary = {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "phase": "fresh-bank-twelve-arm-prior-residual-formal",
            "formal_seal_sha256": expected,
            "formal_bank_sha256": manifest["formal_bank"]["sha256"],
            "decision": {
                "classification": "CONTROLLER-OUTCOME-FAILURE",
                "reason": "one or more controller trajectories failed or did not converge; this is valid negative outcome evidence, not an integrity failure",
                "integrity_valid": True,
            },
            "completion": {
                "expected_matrix": 288,
                "reused_q0": 24,
                "new_records_observed": sum(len(rows) for arm, rows in records.items() if arm != "q0"),
                "controller_outcome_failures": failures,
            },
            "trace_hashes": dict(sorted(trace_hashes.items())),
        }
        summary_digest = _write_new(out_dir / "formal_summary.json", summary)
        _write_new(
            out_dir / "provenance.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "formal_seal_sha256": expected,
                "summary_sha256": summary_digest,
                "trace_hashes": dict(sorted(trace_hashes.items())),
                "paper_files_modified": False,
            },
        )
        print("[analysed] classification=CONTROLLER-OUTCOME-FAILURE", flush=True)
        return

    grid: dict[str, dict[str, dict[str, Any]]] = {name: {} for name in bank_names}
    action_audits: dict[str, dict[str, Any]] = {arm: {} for arm in ARMS}
    for arm in ARMS:
        for record in records[arm]:
            row = _endpoint_row(record)
            grid[record["scenario"]][arm] = row
            action_audits[arm][record["scenario"]] = audit_vector_action(row)
    arm_summaries = {
        arm: _summary(
            [grid[name][arm] for name in bank_names],
            records[arm],
        )
        for arm in ARMS
    }
    grouped_summaries = {
        "central_prior": _summary(
            [grid[name][f"central_prior_s{seed}"] for seed in SEEDS for name in bank_names],
            [record for seed in SEEDS for record in records[f"central_prior_s{seed}"]],
        ),
        "distributed_prior": _summary(
            [grid[name][f"distributed_prior_s{seed}"] for seed in SEEDS for name in bank_names],
            [record for seed in SEEDS for record in records[f"distributed_prior_s{seed}"]],
        ),
    }
    contrasts = {
        "classical_vs_q0": _classical_contrast(grid, bank_names),
        "central_vs_classical": _hierarchical(
            grid, bank_names, "central_prior", "classical_edge"
        ),
        "distributed_vs_classical": _hierarchical(
            grid, bank_names, "distributed_prior", "classical_edge"
        ),
        "distributed_vs_central": _hierarchical(
            grid, bank_names, "distributed_prior", "central_prior"
        ),
    }
    directional_count, noninferior_count, seed_rows = _seed_counts(grid, bank_names)
    absolute_storage = {
        arm: {
            **arm_summaries[arm]["storage"],
            "pass": _absolute_storage_pass(arm_summaries[arm]["storage"]),
        }
        for arm in ARMS
    }
    action_pass_by_group = {
        "central_prior": all(
            all(audit.values())
            for seed in SEEDS
            for audit in action_audits[f"central_prior_s{seed}"].values()
        ),
        "distributed_prior": all(
            all(audit.values())
            for seed in SEEDS
            for audit in action_audits[f"distributed_prior_s{seed}"].values()
        ),
    }
    relative_guards = {
        architecture: _relative_guards(
            grouped_summaries[architecture], arm_summaries["classical_edge"]
        )
        for architecture in ("central_prior", "distributed_prior")
    }
    distributed_guards = {
        "action_contract": action_pass_by_group["distributed_prior"],
        "absolute_storage": all(
            absolute_storage[f"distributed_prior_s{seed}"]["pass"] for seed in SEEDS
        ),
        "relative_no_harm": relative_guards["distributed_prior"]["pass"],
        "controller_outcome_complete": True,
    }
    central_guards = {
        "action_contract": action_pass_by_group["central_prior"],
        "absolute_storage": all(
            absolute_storage[f"central_prior_s{seed}"]["pass"] for seed in SEEDS
        ),
        "relative_no_harm": relative_guards["central_prior"]["pass"],
        "controller_outcome_complete": True,
    }
    integrity = {
        "complete_288_matrix": all(set(grid[name]) == set(ARMS) for name in bank_names),
        "formal_bank_screen_pass": True,
        "all_action_execution_audits": all(
            all(audit.values())
            for arm in ARMS
            for audit in action_audits[arm].values()
        ),
        "training_budget_and_seed_set_verified": True,
        "bootstrap_contract_complete": True,
        "provenance_hashes_verified": True,
    }
    decision = classify_r293(
        integrity_valid=all(integrity.values()),
        distributed_vs_classical=contrasts["distributed_vs_classical"],
        central_vs_classical=contrasts["central_vs_classical"],
        distributed_vs_central=contrasts["distributed_vs_central"],
        distributed_directional_seed_count=directional_count,
        distributed_noninferior_seed_count=noninferior_count,
        distributed_positive_claim_guards=distributed_guards,
        central_positive_claim_guards=central_guards,
    )
    decision["integrity_guards"] = integrity
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "fresh-bank-twelve-arm-prior-residual-formal",
        "formal_seal_sha256": expected,
        "formal_bank_sha256": manifest["formal_bank"]["sha256"],
        "decision": decision,
        "completion": {
            "expected_matrix": 288,
            "reused_q0": 24,
            "new_records_observed": 264,
            "controller_outcome_failures": [],
        },
        "arm_summaries": arm_summaries,
        "grouped_summaries": grouped_summaries,
        "contrasts": contrasts,
        "seed_directionality_and_noninferiority": seed_rows,
        "relative_guards_vs_classical": relative_guards,
        "positive_claim_guards": {
            "distributed_prior": distributed_guards,
            "central_prior": central_guards,
        },
        "absolute_storage_guards": absolute_storage,
        "action_audits": action_audits,
        "trace_hashes": dict(sorted(trace_hashes.items())),
    }
    summary_digest = _write_new(out_dir / "formal_summary.json", summary)
    provenance_digest = _write_new(
        out_dir / "provenance.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "repository_head": _git_head(),
            "formal_seal_sha256": expected,
            "summary_sha256": summary_digest,
            "trace_hashes": dict(sorted(trace_hashes.items())),
            "paper_files_modified": False,
        },
    )
    print(
        f"[analysed] classification={decision['classification']} "
        f"summary_sha256={summary_digest} provenance_sha256={provenance_digest}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--manifest", type=Path, default=DEFAULT_SEAL)
    prepare_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--manifest", type=Path, default=DEFAULT_SEAL)
    run_parser.add_argument("--expected-manifest-sha256", required=True)
    run_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    run_parser.add_argument("--shard-index", type=int, required=True)
    run_parser.add_argument("--shard-count", type=int, default=SHARD_COUNT)
    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--manifest", type=Path, default=DEFAULT_SEAL)
    analyse_parser.add_argument("--expected-manifest-sha256", required=True)
    analyse_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.manifest, args.out_dir)
    elif args.command == "run":
        run_shard(
            args.manifest,
            args.expected_manifest_sha256,
            args.out_dir,
            args.shard_index,
            args.shard_count,
        )
    else:
        analyse(args.manifest, args.expected_manifest_sha256, args.out_dir)


if __name__ == "__main__":
    main()
