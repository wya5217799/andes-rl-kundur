#!/usr/bin/env python3
"""Seal, execute, and analyse the seven-arm R292 vector comparison."""

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

from andes_rl_kundur.agents.vector_residual_td3 import (  # noqa: E402
    CentralVectorTD3,
    DistributedEdgeTD3,
)
from andes_rl_kundur.evaluation.reviewer_identifiability import (  # noqa: E402
    hierarchical_seed_scenario_ratio_bootstrap,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    empirical_upper_tail,
    load_scenario_bank,
    sha256_bytes,
    sha256_file,
)
from andes_rl_kundur.evaluation.vector_residual import (  # noqa: E402
    ZeroVectorController,
    audit_vector_action,
    run_vector_controller_scenario,
    summarise_vector_trace,
)

ROUND_ID = "R292"
QUESTION_ID = "Q-0049"
ENV_SEED = 42
STEPS = 300
FAST_STEPS = 15
FINAL_WINDOW_STEPS = 50
SHARD_COUNT = 3
SEEDS = (101, 137, 173)
BOOTSTRAP_RESAMPLES = 20_000
BOOTSTRAP_SEED = 2026073102
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
    "central_vector_s101",
    "central_vector_s137",
    "central_vector_s173",
    "distributed_edge_s101",
    "distributed_edge_s137",
    "distributed_edge_s173",
)
FRESH_DIR = ROOT / "results/r292_fresh_bank"
FORMAL_BANK = FRESH_DIR / "formal_bank.json"
SCREEN_SUMMARY = FRESH_DIR / "screen_summary.json"
SCREEN_CONTRACT = FRESH_DIR / "feasibility_screen_contract.json"
SCREEN_PROVENANCE = FRESH_DIR / "provenance.json"
TRAINING_SUMMARY = ROOT / "results/r292_vector_training/training_matrix_summary.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R292/formal_seal.json"
DEFAULT_OUT = ROOT / "results/r292_formal_evaluation"


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


def _write_new_text(path: Path, value: str) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")
    digest = sha256_file(path)
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return digest


def _load_json(path: Path, expected: str | None = None) -> dict[str, Any]:
    if expected is not None and sha256_file(path) != expected:
        raise ValueError(f"hash mismatch for {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _checkpoint_path(architecture: str, seed: int) -> Path:
    return ROOT / f"results/r292_vector_training/{architecture}_s{seed}/final.pt"


def _contract_path(architecture: str, seed: int) -> Path:
    return ROOT / (
        f"results/r292_vector_training/{architecture}_s{seed}/"
        "controller_contract.json"
    )


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R292/plan.md",
        "script": Path(__file__).resolve(),
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
        "formal_bank": FORMAL_BANK,
        "screen_summary": SCREEN_SUMMARY,
        "screen_contract": SCREEN_CONTRACT,
        "screen_provenance": SCREEN_PROVENANCE,
        "training_summary": TRAINING_SUMMARY,
    }


def _verify_upstreams(training: dict[str, Any], screen: dict[str, Any]) -> None:
    if not training.get("all_completed") or training.get("observed_run_count") != 6:
        raise ValueError("formal evaluation requires all six final checkpoints")
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


def _arm_manifest(training: dict[str, Any]) -> dict[str, Any]:
    rows = {
        (row["architecture"], int(row["seed"])): row
        for row in training["rows"]
    }
    arms: dict[str, Any] = {
        "q0": {"kind": "deterministic", "controller": "q0"}
    }
    for architecture in ("central_vector", "distributed_edge"):
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
                "controller_contract": str(contract.relative_to(ROOT)).replace(
                    "\\", "/"
                ),
                "controller_contract_sha256": sha256_file(contract),
                "actor_parameter_count": row["actor_parameter_count"],
            }
    if tuple(arms) != ARMS:
        raise ValueError("formal arm order drift")
    return arms


def prepare(manifest_path: Path, out_dir: Path) -> None:
    trace_dir = out_dir / "traces"
    if trace_dir.exists() and any(trace_dir.glob("*.json")):
        raise ValueError("formal seal must precede every controller trace")
    training = _load_json(TRAINING_SUMMARY)
    screen = _load_json(SCREEN_SUMMARY)
    _verify_upstreams(training, screen)
    provenance = _load_json(SCREEN_PROVENANCE)
    for path_text, digest in provenance["trace_hashes"].items():
        if sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"fresh-screen trace drift: {path_text}")
    bank, bank_hash = load_scenario_bank(
        FORMAL_BANK,
        expected_sha256=screen["formal_bank_sha256"],
    )
    if bank["scenario_count"] != 24:
        raise ValueError("R292 formal bank must contain exactly 24 scenarios")
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
        "phase": "fresh-bank-seven-arm-vector-formal",
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
            "frozen_trace_hashes": provenance["trace_hashes"],
        },
        "training_summary_sha256": sha256_file(TRAINING_SUMMARY),
        "arms": arms,
        "execution": {
            "environment_seed": ENV_SEED,
            "steps": STEPS,
            "shard_count": SHARD_COUNT,
            "arm_count": len(ARMS),
            "trajectory_budget": len(ARMS) * 24,
            "resume_completed": True,
            "overwrite": False,
            "retry_failed_trajectory": False,
        },
        "statistics": {
            "hierarchical_bootstrap_seed": BOOTSTRAP_SEED,
            "resamples": BOOTSTRAP_RESAMPLES,
            "materiality_percent": -2.0,
            "confidence": 0.95,
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
            "distributed_directional_seed_minimum": 2,
        },
        "sources": sources,
        "formal_trace_count_at_freeze": 0,
    }
    digest = _write_new(manifest_path, payload)
    print(f"[sealed] {manifest_path} sha256={digest}", flush=True)


def _verify(manifest_path: Path, expected: str) -> dict[str, Any]:
    manifest = _load_json(manifest_path, expected)
    if manifest.get("round") != ROUND_ID:
        raise ValueError("not an R292 formal seal")
    for entry in manifest["sources"].values():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError(f"formal source drift: {entry['path']}")
    training = _load_json(TRAINING_SUMMARY, manifest["training_summary_sha256"])
    screen = _load_json(SCREEN_SUMMARY, manifest["screen"]["summary_sha256"])
    _verify_upstreams(training, screen)
    load_scenario_bank(
        FORMAL_BANK,
        expected_sha256=manifest["formal_bank"]["sha256"],
    )
    for path_text, digest in manifest["screen"]["frozen_trace_hashes"].items():
        if sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"fresh-screen trace drift: {path_text}")
    for arm, config in manifest["arms"].items():
        if config["kind"] == "learned":
            if sha256_file(ROOT / config["checkpoint"]) != config["checkpoint_sha256"]:
                raise ValueError(f"formal checkpoint drift: {arm}")
            if sha256_file(ROOT / config["controller_contract"]) != config[
                "controller_contract_sha256"
            ]:
                raise ValueError(f"formal controller contract drift: {arm}")
    return manifest


def _make_controller(arm: str, config: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    if arm == "q0":
        return ZeroVectorController(), {"name": "q0", "edge": [0.0, 0.0, 0.0]}
    architecture = config["architecture"]
    if architecture == "central_vector":
        controller: Any = CentralVectorTD3(
            critic_hidden_sizes=[64, 64],
            actor_hidden_sizes=[59, 59],
            device="cpu",
        )
    else:
        controller = DistributedEdgeTD3(hidden_sizes=[64, 64], device="cpu")
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
        "checkpoint_metadata": metadata,
    }


def _trace_path(out_dir: Path, scenario: str, arm: str) -> Path:
    return out_dir / "traces" / f"{scenario}__{arm}.json"


def _validate_trace(
    path: Path,
    scenario: dict[str, Any],
    arm: str,
    manifest: dict[str, Any],
    seal_hash: str,
) -> dict[str, Any]:
    record = _load_json(path)
    expected = {
        "round": ROUND_ID,
        "phase": "fresh-bank-seven-arm-vector-formal",
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
    if shard_count != manifest["execution"]["shard_count"]:
        raise ValueError("formal shard contract drift")
    if not 0 <= shard_index < shard_count:
        raise ValueError("invalid shard index")
    bank, _ = load_scenario_bank(
        FORMAL_BANK,
        expected_sha256=manifest["formal_bank"]["sha256"],
    )
    tasks = [(scenario, arm) for scenario in bank["scenarios"] for arm in ARMS]
    selected = [
        task for index, task in enumerate(tasks) if index % shard_count == shard_index
    ]
    controllers: dict[str, tuple[Any, dict[str, Any]]] = {}
    for index, (scenario, arm) in enumerate(selected, start=1):
        path = _trace_path(out_dir, scenario["name"], arm)
        if path.exists():
            record = _validate_trace(path, scenario, arm, manifest, expected)
            if not record.get("completed") or record.get("tds_failed"):
                raise RuntimeError(f"retained failed formal trace forbids retry: {path}")
            print(f"[resume {index:03d}/{len(selected):03d}] {path.name}", flush=True)
            continue
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
            phase="fresh-bank-seven-arm-vector-formal",
            evidence_hashes={
                "formal_seal": expected,
                "formal_bank": manifest["formal_bank"]["sha256"],
            },
        )
        record.update(
            {
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
        if not record["completed"]:
            raise RuntimeError(f"formal trajectory failed and is retained: {path}")


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
    soc = np.asarray(
        [value for step in steps for value in step["bess_soc"]], dtype=float
    )
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


def _relative_percent(left: float, right: float) -> float:
    if right <= 0.0:
        raise ValueError("relative endpoint reference must be positive")
    return 100.0 * (left / right - 1.0)


def _guard_relative_percent(left: float, right: float) -> float:
    if right <= 1e-15:
        return 0.0 if left <= 1e-15 else float("inf")
    return 100.0 * (left / right - 1.0)


def _hierarchical_contrast(
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
        if right_prefix == "q0":
            kwargs = {
                "right_deterministic": {
                    name: float(grid[name]["q0"][endpoint]) for name in bank_names
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
        result[endpoint] = hierarchical_seed_scenario_ratio_bootstrap(
            left,
            **kwargs,
            resamples=BOOTSTRAP_RESAMPLES,
            seed=BOOTSTRAP_SEED,
        )
    return result


def _material(contrast: dict[str, Any], endpoint: str) -> bool:
    effect = contrast[endpoint]["ratio_of_means_percent"]
    return bool(
        effect["point"] <= -2.0
        and effect["percentile_95_interval"][1] < 0.0
    )


def _material_worsening(contrast: dict[str, Any], endpoint: str) -> bool:
    effect = contrast[endpoint]["ratio_of_means_percent"]
    return bool(
        effect["point"] >= 2.0
        and effect["percentile_95_interval"][0] > 0.0
    )


def _classification(
    *,
    valid: bool,
    distributed_vs_q0: dict[str, Any],
    central_vs_q0: dict[str, Any],
    distributed_vs_central: dict[str, Any],
    distributed_directional_seed_count: int,
) -> dict[str, Any]:
    if not valid:
        return {
            "classification": "INVALID",
            "reason": "one or more formal completion, action, storage, tail, or provenance guards failed",
        }
    distributed_effective = all(
        _material(distributed_vs_q0, endpoint) for endpoint in PRIMARY_ENDPOINTS
    ) and distributed_directional_seed_count >= 2
    central_effective = all(
        _material(central_vs_q0, endpoint) for endpoint in PRIMARY_ENDPOINTS
    )
    distributed_superior = all(
        _material(distributed_vs_central, endpoint)
        for endpoint in PRIMARY_ENDPOINTS
    )
    no_material_worsening = not any(
        _material_worsening(distributed_vs_central, endpoint)
        for endpoint in PRIMARY_ENDPOINTS
    )
    gates = {
        "distributed_vs_q0_both_primary": distributed_effective,
        "central_vs_q0_both_primary": central_effective,
        "distributed_vs_central_both_primary": distributed_superior,
        "distributed_directional_seed_count": distributed_directional_seed_count,
        "distributed_vs_central_no_material_worsening": no_material_worsening,
    }
    if distributed_effective and distributed_superior:
        classification = "DISTRIBUTED-SUPERIOR"
        reason = "distributed execution materially improves both primary endpoints versus q0 and central vector control"
    elif distributed_effective and no_material_worsening:
        classification = "DISTRIBUTED-EFFECTIVE-NOT-SEPARATED"
        reason = "distributed execution is reproducibly effective versus q0 but not separated from central vector control"
    elif distributed_effective:
        classification = "DISTRIBUTED-EFFECTIVE-INFERIOR"
        reason = "distributed execution is reproducibly effective versus q0 but materially worse than central vector control"
    elif central_effective:
        classification = "CENTRAL-VECTOR-ONLY"
        reason = "only the centralized vector actor clears both q0 primary gates"
    else:
        classification = "NO-REPRODUCIBLE-VECTOR-VALUE"
        reason = "neither learned vector architecture clears both primary q0 gates"
    return {"classification": classification, "reason": reason, "efficacy_gates": gates}


def _directional_seed_count(
    grid: dict[str, dict[str, dict[str, Any]]], bank_names: list[str]
) -> tuple[int, list[dict[str, Any]]]:
    rows = []
    for seed in SEEDS:
        endpoints: dict[str, Any] = {}
        for endpoint in PRIMARY_ENDPOINTS:
            learned = float(
                np.mean(
                    [grid[name][f"distributed_edge_s{seed}"][endpoint] for name in bank_names]
                )
            )
            q0 = float(np.mean([grid[name]["q0"][endpoint] for name in bank_names]))
            endpoints[endpoint] = {
                "effect_percent": _relative_percent(learned, q0),
                "directional_improvement": learned < q0,
            }
        rows.append(
            {
                "seed": seed,
                "endpoints": endpoints,
                "both_endpoints_directional_improvement": all(
                    row["directional_improvement"] for row in endpoints.values()
                ),
            }
        )
    return (
        sum(row["both_endpoints_directional_improvement"] for row in rows),
        rows,
    )


def analyse(manifest_path: Path, expected: str, out_dir: Path) -> None:
    manifest = _verify(manifest_path, expected)
    bank, _ = load_scenario_bank(
        FORMAL_BANK,
        expected_sha256=manifest["formal_bank"]["sha256"],
    )
    bank_names = [row["name"] for row in bank["scenarios"]]
    grid: dict[str, dict[str, dict[str, Any]]] = {name: {} for name in bank_names}
    records: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    action_audits: dict[str, dict[str, dict[str, bool]]] = {
        arm: {} for arm in ARMS
    }
    trace_hashes: dict[str, str] = {}
    failures = []
    for scenario in bank["scenarios"]:
        for arm in ARMS:
            path = _trace_path(out_dir, scenario["name"], arm)
            record = _validate_trace(path, scenario, arm, manifest, expected)
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
                        "trace_sha256": digest,
                    }
                )
                continue
            row = _endpoint_row(record)
            grid[scenario["name"]][arm] = row
            action_audits[arm][scenario["name"]] = audit_vector_action(row)
    complete = not failures and all(
        set(grid[name]) == set(ARMS) for name in bank_names
    )
    if not complete:
        summary = {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "phase": "fresh-bank-seven-arm-vector-formal",
            "formal_seal_sha256": expected,
            "decision": {
                "classification": "INVALID",
                "reason": "formal trajectory matrix is incomplete",
            },
            "completion": {
                "expected": len(bank_names) * len(ARMS),
                "observed_complete": sum(len(rows) for rows in grid.values()),
                "failures": failures,
            },
            "trace_hashes": dict(sorted(trace_hashes.items())),
        }
        summary_hash = _write_new(out_dir / "formal_summary.json", summary)
        _write_new(
            out_dir / "provenance.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "formal_seal_sha256": expected,
                "summary_sha256": summary_hash,
                "trace_hashes": dict(sorted(trace_hashes.items())),
                "paper_files_modified": False,
            },
        )
        print("[analysed] classification=INVALID incomplete formal matrix", flush=True)
        return

    arm_summaries: dict[str, Any] = {}
    for arm in ARMS:
        rows = [grid[name][arm] for name in bank_names]
        arm_summaries[arm] = {
            "scenario_count": len(rows),
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
                    {
                        name: float(grid[name][arm][endpoint])
                        for name in bank_names
                    }
                )
                for endpoint in TAIL_ENDPOINTS
            },
            "storage": _aggregate_storage(records[arm]),
        }
    hierarchical = {
        "distributed_vs_q0": _hierarchical_contrast(
            grid, bank_names, "distributed_edge", "q0"
        ),
        "central_vs_q0": _hierarchical_contrast(
            grid, bank_names, "central_vector", "q0"
        ),
        "distributed_vs_central": _hierarchical_contrast(
            grid, bank_names, "distributed_edge", "central_vector"
        ),
    }
    directional_count, directional_rows = _directional_seed_count(grid, bank_names)
    q0_summary = arm_summaries["q0"]
    relative_guards: dict[str, Any] = {}
    for arm in ARMS[1:]:
        fast_mean = {
            endpoint: _relative_percent(
                arm_summaries[arm]["means"][endpoint],
                q0_summary["means"][endpoint],
            )
            for endpoint in FAST_COMMON_ENDPOINTS
        }
        slow_mean = {
            endpoint: _relative_percent(
                arm_summaries[arm]["means"][endpoint],
                q0_summary["means"][endpoint],
            )
            for endpoint in SLOW_COMMON_ENDPOINTS
        }
        storage_mean = {
            endpoint: _guard_relative_percent(
                arm_summaries[arm]["means"][endpoint],
                q0_summary["means"][endpoint],
            )
            for endpoint in STORAGE_ENDPOINTS
        }
        tail = {
            endpoint: _relative_percent(
                arm_summaries[arm]["cvar90"][endpoint]["cvar_upper_tail"],
                q0_summary["cvar90"][endpoint]["cvar_upper_tail"],
            )
            for endpoint in TAIL_ENDPOINTS
        }
        relative_guards[arm] = {
            "fast_common_mean_effect_percent": fast_mean,
            "slow_common_mean_effect_percent": slow_mean,
            "storage_mean_effect_percent": storage_mean,
            "tail_cvar90_effect_percent": tail,
            "pass": all(value <= 5.0 for value in fast_mean.values())
            and all(value <= 2.0 for value in slow_mean.values())
            and all(value <= 5.0 for value in storage_mean.values())
            and all(
                value <= (2.0 if endpoint in SLOW_COMMON_ENDPOINTS else 5.0)
                for endpoint, value in tail.items()
            ),
        }
    absolute_storage = {}
    for arm in ARMS:
        row = arm_summaries[arm]["storage"]
        absolute_storage[arm] = {
            **row,
            "pass": row["constraint_violation_count"] == 0
            and row["saturation_reason_count"] == 0
            and row["max_abs_commanded_power_system_pu"] <= 0.36 + 1e-12
            and row["max_abs_actual_power_system_pu"] <= 0.36 + 1e-12
            and row["min_soc"] >= 0.20 - 1e-9
            and row["max_soc"] <= 0.80 + 1e-9,
        }
    action_pass = all(
        len(action_audits[arm]) == len(bank_names)
        and all(all(audit.values()) for audit in action_audits[arm].values())
        for arm in ARMS
    )
    validity = {
        "complete_seven_arm_matrix": complete,
        "formal_bank_screen_pass": True,
        "action_contract_all_rows": action_pass,
        "absolute_storage_all_arms": all(
            row["pass"] for row in absolute_storage.values()
        ),
        "relative_no_harm_all_candidate_arms": all(
            row["pass"] for row in relative_guards.values()
        ),
        "bootstrap_contract_complete": True,
        "provenance_hashes_verified": True,
    }
    decision = _classification(
        valid=all(validity.values()),
        distributed_vs_q0=hierarchical["distributed_vs_q0"],
        central_vs_q0=hierarchical["central_vs_q0"],
        distributed_vs_central=hierarchical["distributed_vs_central"],
        distributed_directional_seed_count=directional_count,
    )
    decision["validity_guards"] = validity
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "fresh-bank-seven-arm-vector-formal",
        "formal_seal_sha256": expected,
        "formal_bank_sha256": manifest["formal_bank"]["sha256"],
        "decision": decision,
        "completion": {
            "expected": len(bank_names) * len(ARMS),
            "observed_complete": len(bank_names) * len(ARMS),
            "failures": [],
        },
        "arm_summaries": arm_summaries,
        "hierarchical_bootstrap": hierarchical,
        "distributed_seed_directionality": {
            "both_endpoint_improvement_count": directional_count,
            "rows": directional_rows,
        },
        "action_audits": action_audits,
        "absolute_storage_guards": absolute_storage,
        "relative_guards_vs_q0": relative_guards,
        "trace_hashes": dict(sorted(trace_hashes.items())),
    }
    summary_hash = _write_new(out_dir / "formal_summary.json", summary)
    markdown_hash = _write_new_text(
        out_dir / "formal_summary.md",
        "\n".join(
            [
                "# R292 true distributed vector comparison",
                "",
                f"**Classification:** `{decision['classification']}`",
                "",
                decision["reason"],
                "",
                f"Completed trajectories: {len(bank_names) * len(ARMS)} / {len(bank_names) * len(ARMS)}.",
                "",
            ]
        ),
    )
    provenance_hash = _write_new(
        out_dir / "provenance.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "repository_head": _git_head(),
            "formal_seal_sha256": expected,
            "formal_bank_sha256": manifest["formal_bank"]["sha256"],
            "summary_sha256": summary_hash,
            "markdown_sha256": markdown_hash,
            "source_sha256": {
                name: entry["sha256"] for name, entry in manifest["sources"].items()
            },
            "trace_hashes": dict(sorted(trace_hashes.items())),
            "paper_files_modified": False,
            "seed_selection_performed": False,
            "failed_trajectories_retained": True,
        },
    )
    print(
        f"[analysed] classification={decision['classification']} "
        f"summary_sha256={summary_hash} provenance_sha256={provenance_hash}",
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
