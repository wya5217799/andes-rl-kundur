#!/usr/bin/env python3
# ruff: noqa: E402
"""Freeze, execute, and analyse the eight-arm R279 formal comparison."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from andes_rl_kundur.agents.central_scalar_td3 import CentralScalarTD3
from andes_rl_kundur.agents.shared_area_td3 import SharedAreaTD3
from andes_rl_kundur.control.causal_area_feedback import (
    CausalAreaFeedbackController,
    r279_causal_contracts,
)
from andes_rl_kundur.evaluation.icems_residual import (
    audit_icems_policy_action,
    summarise_icems_policy_trace,
)
from andes_rl_kundur.evaluation.r279_controllers import run_r279_controller_scenario
from andes_rl_kundur.evaluation.reviewer_identifiability import (
    hierarchical_seed_scenario_ratio_bootstrap,
)
from andes_rl_kundur.evaluation.sealed_bank import (
    canonical_json_bytes,
    empirical_upper_tail,
    load_scenario_bank,
    paired_bootstrap_contrasts,
    sha256_bytes,
    sha256_file,
)

ROUND_ID = "R279"
ENV_SEED, STEPS, FAST_STEPS, FINAL_WINDOW_STEPS, SHARD_COUNT = 42, 300, 15, 50, 8
SEEDS = (17, 53, 89)
BOOTSTRAP_RESAMPLES = 10_000
PAIRED_BOOTSTRAP_SEED, HIERARCHICAL_BOOTSTRAP_SEED = 2026072705, 2026072706
PRIMARY_ENDPOINTS = ("normalized_sync_loss_hz2", "fast_inter_area_iae_hz_s")
FAST_COMMON_ENDPOINTS = ("max_abs_rocof_hz_s", "worst_bus_peak_abs_hz", "first_3s_common_iae_hz_s")
SLOW_COMMON_ENDPOINTS = ("vsg_mean_iae_hz_s", "final_window_common_abs_mean_hz")
STORAGE_ENDPOINTS = ("bess_command_l1_device_s", "bess_command_total_variation", "bess_charge_energy_mwh_total", "bess_discharge_energy_mwh_total")
CONTINUOUS_ENDPOINTS = (*PRIMARY_ENDPOINTS, *FAST_COMMON_ENDPOINTS, *SLOW_COMMON_ENDPOINTS, *STORAGE_ENDPOINTS)
STATISTICAL_ENDPOINTS = (*PRIMARY_ENDPOINTS, *FAST_COMMON_ENDPOINTS, *SLOW_COMMON_ENDPOINTS)
TAIL_ENDPOINTS = STATISTICAL_ENDPOINTS
ARMS = ("q0", "causal", "centralized_s17", "centralized_s53", "centralized_s89", "shared_s17", "shared_s53", "shared_s89")
FRESH_DIR = ROOT / "results/r279_fresh_bank"
FORMAL_BANK = FRESH_DIR / "formal_bank.json"
SCREEN_SUMMARY = FRESH_DIR / "screen_summary.json"
SCREEN_CONTRACT = FRESH_DIR / "feasibility_screen_contract.json"
SCREEN_PROVENANCE = FRESH_DIR / "provenance.json"
TRAINING_SUMMARY = ROOT / "results/r279_matched_training/training_matrix_summary.json"
CAUSAL_SUMMARY = ROOT / "results/r279_causal_guard/causal_guard_summary.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R279/formal_seal.json"
DEFAULT_OUT = ROOT / "results/r279_formal_evaluation"

class ZeroResidualController:
    def reset(self) -> None:
        pass
    def select_raw_actions(self, observations: Mapping[int, np.ndarray] | np.ndarray, *, deterministic: bool = True) -> np.ndarray:
        del observations
        if not deterministic:
            raise ValueError("q0 is deterministic")
        return np.zeros(4, dtype=np.float32)

def _write_new(path: Path, payload: object) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(payload)
    path.write_bytes(data)
    digest = sha256_bytes(data)
    path.with_name(path.name + ".sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest

def _write_new_text(path: Path, text: str) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    digest = sha256_file(path)
    path.with_name(path.name + ".sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest

def _load_json(path: Path, expected: str | None = None) -> dict[str, Any]:
    if expected is not None and sha256_file(path) != expected:
        raise ValueError(f"hash mismatch for {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload

def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R279/plan.md", "script": Path(__file__).resolve(),
        "execution_amendment": ROOT / "memory/rounds/R279/execution_amendment_20260727.md",
        "launcher": ROOT / "scripts/run_r279_formal.sh", "generic_runner": ROOT / "src/andes_rl_kundur/evaluation/r279_controllers.py",
        "analysis": ROOT / "src/andes_rl_kundur/evaluation/reviewer_identifiability.py", "shared_actor": ROOT / "src/andes_rl_kundur/agents/shared_area_td3.py",
        "central_actor": ROOT / "src/andes_rl_kundur/agents/central_scalar_td3.py", "causal_controller": ROOT / "src/andes_rl_kundur/control/causal_area_feedback.py",
        "icems_evaluation": ROOT / "src/andes_rl_kundur/evaluation/icems_residual.py", "sealed_bank": ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py",
        "formal_bank": FORMAL_BANK, "screen_summary": SCREEN_SUMMARY, "screen_contract": SCREEN_CONTRACT,
        "screen_provenance": SCREEN_PROVENANCE, "training_summary": TRAINING_SUMMARY, "causal_summary": CAUSAL_SUMMARY,
    }

def _checkpoint_path(architecture: str, seed: int) -> Path:
    return ROOT / f"results/r279_matched_training/{architecture}_s{seed}/final.pt"

def _contract_path(architecture: str, seed: int) -> Path:
    return ROOT / f"results/r279_matched_training/{architecture}_s{seed}/controller_contract.json"

def _verify_upstreams(training: dict[str, Any], causal: dict[str, Any], screen: dict[str, Any]) -> None:
    if not training.get("all_completed") or training.get("observed_run_count") != 6:
        raise ValueError("formal evaluation requires all six final checkpoints")
    if training.get("seed_selection_performed") is not False:
        raise ValueError("formal evaluation forbids seed selection")
    for path_text, digest in training.get("artifact_hashes", {}).items():
        if sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"training artifact drift: {path_text}")
    if not causal.get("decision", {}).get("pass", False):
        raise ValueError("formal evaluation requires a passing causal guard")
    if screen.get("decision", {}).get("classification") != "PASS" or screen.get("controller_trace_count_at_freeze") != 0:
        raise ValueError("formal evaluation requires a prospectively passing fresh-bank screen")
    if screen.get("redraw_performed") is not False:
        raise ValueError("fresh bank reports a forbidden redraw")

def _arm_manifest(training: dict[str, Any], causal: dict[str, Any]) -> dict[str, Any]:
    rows = {(row["architecture"], int(row["seed"])): row for row in training["rows"]}
    arms: dict[str, Any] = {
        "q0": {"kind": "deterministic", "controller": "q0"},
        "causal": {"kind": "deterministic", "controller": causal["selected_causal_contract"]["name"], "contract": causal["selected_causal_contract"], "causal_guard_summary_sha256": sha256_file(CAUSAL_SUMMARY)},
    }
    for architecture in ("centralized", "shared"):
        for seed in SEEDS:
            row = rows[(architecture, seed)]
            checkpoint, contract = _checkpoint_path(architecture, seed), _contract_path(architecture, seed)
            if sha256_file(checkpoint) != row["checkpoint_sha256"]:
                raise ValueError(f"checkpoint drift: {checkpoint}")
            arms[f"{architecture}_s{seed}"] = {
                "kind": "learned", "architecture": architecture, "seed": seed,
                "checkpoint": str(checkpoint.relative_to(ROOT)).replace("\\", "/"), "checkpoint_sha256": row["checkpoint_sha256"],
                "controller_contract": str(contract.relative_to(ROOT)).replace("\\", "/"), "controller_contract_sha256": sha256_file(contract),
                "actor_parameter_count": row["actor_parameter_count"],
            }
    if tuple(arms) != ARMS:
        raise ValueError("formal arm order drift")
    return arms

def prepare(manifest_path: Path, out_dir: Path) -> None:
    trace_dir = out_dir / "traces"
    if trace_dir.exists() and any(trace_dir.glob("*.json")):
        raise ValueError("formal seal must precede every controller trace")
    training, causal, screen = _load_json(TRAINING_SUMMARY), _load_json(CAUSAL_SUMMARY), _load_json(SCREEN_SUMMARY)
    _verify_upstreams(training, causal, screen)
    provenance = _load_json(SCREEN_PROVENANCE)
    for path_text, digest in provenance["trace_hashes"].items():
        if sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"fresh screen trace drift: {path_text}")
    bank, bank_hash = load_scenario_bank(FORMAL_BANK, expected_sha256=screen["formal_bank_sha256"])
    if bank["scenario_count"] < 20:
        raise ValueError("formal bank is below the registered minimum")
    arms = _arm_manifest(training, causal)
    sources = {name: {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256_file(path)} for name, path in _source_paths().items()}
    payload = {
        "schema_version": 1, "round": ROUND_ID, "question": "Q-0041", "phase": "fresh-bank-eight-arm-formal", "repository_head": _git_head(),
        "formal_bank": {"path": str(FORMAL_BANK.relative_to(ROOT)).replace("\\", "/"), "sha256": bank_hash, "scenario_count": bank["scenario_count"]},
        "screen": {"summary_sha256": sha256_file(SCREEN_SUMMARY), "contract_sha256": sha256_file(SCREEN_CONTRACT), "provenance_sha256": sha256_file(SCREEN_PROVENANCE), "frozen_trace_hashes": provenance["trace_hashes"]},
        "training_summary_sha256": sha256_file(TRAINING_SUMMARY), "causal_summary_sha256": sha256_file(CAUSAL_SUMMARY), "arms": arms,
        "execution": {"environment_seed": ENV_SEED, "steps": STEPS, "shard_count": SHARD_COUNT, "arm_count": len(ARMS), "trajectory_budget": len(ARMS) * bank["scenario_count"], "resume_completed": True, "overwrite": False, "retry_failed_trajectory": False},
        "statistics": {"paired_bootstrap_seed": PAIRED_BOOTSTRAP_SEED, "hierarchical_bootstrap_seed": HIERARCHICAL_BOOTSTRAP_SEED, "resamples": BOOTSTRAP_RESAMPLES, "materiality_percent": -2.0, "confidence": 0.95, "lower_is_better": True, "primary_endpoints": list(PRIMARY_ENDPOINTS)},
        "guards": {"fast_common_mean_and_cvar_no_harm_percent": 5.0, "slow_common_mean_and_cvar_no_harm_percent": 2.0, "storage_relative_no_harm_percent": 5.0, "command_and_actual_abs_system_pu_max": 0.36, "soc_range": [0.20, 0.80], "zero_constraint_violations": True, "zero_saturation_reasons": True, "shared_directional_seed_minimum": 2},
        "sources": sources, "packages": {name: importlib.metadata.version(name) for name in ("andes", "numpy", "torch")} | {"python": sys.version}, "formal_trace_count_at_freeze": 0,
    }
    digest = _write_new(manifest_path, payload)
    print(f"[sealed] {manifest_path} sha256={digest}", flush=True)

def _verify(manifest_path: Path, expected: str) -> dict[str, Any]:
    manifest = _load_json(manifest_path, expected)
    if manifest.get("round") != ROUND_ID or manifest.get("phase") != "fresh-bank-eight-arm-formal":
        raise ValueError("not an R279 formal seal")
    for entry in manifest["sources"].values():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError(f"formal source drift: {entry['path']}")
    training = _load_json(TRAINING_SUMMARY, manifest["training_summary_sha256"])
    causal = _load_json(CAUSAL_SUMMARY, manifest["causal_summary_sha256"])
    screen = _load_json(SCREEN_SUMMARY, manifest["screen"]["summary_sha256"])
    _verify_upstreams(training, causal, screen)
    load_scenario_bank(FORMAL_BANK, expected_sha256=manifest["formal_bank"]["sha256"])
    for path_text, digest in manifest["screen"]["frozen_trace_hashes"].items():
        if sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"screen trace drift: {path_text}")
    for arm, config in manifest["arms"].items():
        if config["kind"] == "learned" and (sha256_file(ROOT / config["checkpoint"]) != config["checkpoint_sha256"] or sha256_file(ROOT / config["controller_contract"]) != config["controller_contract_sha256"]):
            raise ValueError(f"formal learned artifact drift: {arm}")
    return manifest
def _make_controller(arm: str, config: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    if arm == "q0":
        return ZeroResidualController(), {"name": "q0", "q": 0.0}
    if arm == "causal":
        telemetry = config["contract"]
        contract = next(row for row in r279_causal_contracts() if row.name == telemetry["name"])
        if contract.telemetry() != telemetry:
            raise ValueError("causal contract drift")
        return CausalAreaFeedbackController(contract), {"causal_feedback": telemetry}
    architecture = config["architecture"]
    controller = (SharedAreaTD3(hidden_sizes=[64, 64], device="cpu") if architecture == "shared" else CentralScalarTD3(critic_hidden_sizes=[64, 64], actor_hidden_sizes=[55, 55], device="cpu"))
    metadata = controller.load(ROOT / config["checkpoint"])
    expected = {"round": ROUND_ID, "question": "Q-0041", "architecture": architecture, "seed": config["seed"], "episodes_completed": 300, "total_steps": 4500, "smoke": False}
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise ValueError(f"checkpoint metadata mismatch for {arm}: {key}")
    return controller, {"architecture": architecture, "seed": config["seed"], "checkpoint": config["checkpoint"], "checkpoint_sha256": config["checkpoint_sha256"], "controller_contract_sha256": config["controller_contract_sha256"], "checkpoint_metadata": metadata}

def _trace_path(out_dir: Path, scenario: str, arm: str) -> Path:
    return out_dir / "traces" / f"{scenario}__{arm}.json"

def _validate_trace(path: Path, scenario: dict[str, Any], arm: str, manifest: dict[str, Any], seal_hash: str) -> dict[str, Any]:
    record = _load_json(path)
    expected = {"round": ROUND_ID, "phase": "fresh-bank-eight-arm-formal", "controller": arm, "scenario": scenario["name"], "delta_u": scenario["delta_u"], "formal_seal_sha256": seal_hash, "formal_bank_sha256": manifest["formal_bank"]["sha256"]}
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"formal trace provenance mismatch in {path}: {key}")
    return record

def run_shard(manifest_path: Path, expected: str, out_dir: Path, shard_index: int, shard_count: int) -> None:
    manifest = _verify(manifest_path, expected)
    if shard_count != manifest["execution"]["shard_count"] or not 0 <= shard_index < shard_count:
        raise ValueError("formal shard contract drift")
    bank, _ = load_scenario_bank(FORMAL_BANK, expected_sha256=manifest["formal_bank"]["sha256"])
    tasks = [(scenario, arm) for scenario in bank["scenarios"] for arm in ARMS]
    selected = [task for index, task in enumerate(tasks) if index % shard_count == shard_index]
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
        record = run_r279_controller_scenario(controller, controller_name=arm, controller_config=controller_config, scenario_name=scenario["name"], delta_u=scenario["delta_u"], seed=ENV_SEED, steps=STEPS, phase="fresh-bank-eight-arm-formal", evidence_hashes={"formal_seal": expected, "formal_bank": manifest["formal_bank"]["sha256"]})
        record.update({"location": scenario["location"], "sign": scenario["sign"], "severity": scenario["severity"], "formal_seal_sha256": expected, "formal_bank_sha256": manifest["formal_bank"]["sha256"], "execution_shard_index": shard_index, "execution_shard_count": shard_count})
        digest = _write_new(path, record)
        print(f"[formal {index:03d}/{len(selected):03d}] {path.name} completed={record['completed']} sha256={digest}", flush=True)
        if not record["completed"]:
            raise RuntimeError(f"formal trajectory failed and is retained: {path}")

def _endpoint_row(record: dict[str, Any]) -> dict[str, Any]:
    row = summarise_icems_policy_trace(record, final_window_steps=FINAL_WINDOW_STEPS, fast_window_steps=FAST_STEPS)
    delta = np.asarray([step["delta_f_physical_hz"] for step in record["traces"]], dtype=float)
    row["first_3s_common_iae_hz_s"] = float(np.sum(np.abs(np.mean(delta, axis=1)[:FAST_STEPS])) * row["sample_interval_s"])
    return row

def _aggregate_storage(records: list[dict[str, Any]]) -> dict[str, float | int]:
    steps = [step for record in records for step in record["traces"]]
    commanded = np.asarray([value for step in steps for value in step["bess_commanded_power_system_pu"]], dtype=float)
    actual = np.asarray([value for step in steps for value in step["bess_actual_power_system_pu"]], dtype=float)
    soc = np.asarray([value for step in steps for value in step["bess_soc"]], dtype=float)
    return {"max_abs_commanded_power_system_pu": float(np.max(np.abs(commanded))), "max_abs_actual_power_system_pu": float(np.max(np.abs(actual))), "min_soc": float(np.min(soc)), "max_soc": float(np.max(soc)), "constraint_violation_count": sum(len(step["bess_constraint_violations"]) for step in steps), "saturation_reason_count": sum(bool(reason) for step in steps for reason in step["bess_saturation_reasons"])}

def _relative_percent(left: float, right: float) -> float:
    if right <= 0.0:
        raise ValueError("relative endpoint reference must be positive")
    return 100.0 * (left / right - 1.0)

def _guard_relative_percent(left: float, right: float) -> float:
    if right <= 1e-15:
        return 0.0 if left <= 1e-15 else float("inf")
    return 100.0 * (left / right - 1.0)

def _hierarchical_contrast(grid: dict[str, dict[str, dict[str, Any]]], bank_names: list[str], left_prefix: str, right_prefix: str) -> dict[str, Any]:
    result = {}
    for endpoint in STATISTICAL_ENDPOINTS:
        left = {seed: {name: float(grid[name][f"{left_prefix}_s{seed}"][endpoint]) for name in bank_names} for seed in SEEDS}
        kwargs = ({"right_by_seed": {seed: {name: float(grid[name][f"{right_prefix}_s{seed}"][endpoint]) for name in bank_names} for seed in SEEDS}} if right_prefix in {"shared", "centralized"} else {"right_deterministic": {name: float(grid[name][right_prefix][endpoint]) for name in bank_names}})
        result[endpoint] = hierarchical_seed_scenario_ratio_bootstrap(left, **kwargs, resamples=BOOTSTRAP_RESAMPLES, seed=HIERARCHICAL_BOOTSTRAP_SEED)
    return result

def _material_hierarchical(contrast: dict[str, Any], endpoint: str) -> bool:
    effect = contrast[endpoint]["ratio_of_means_percent"]
    return bool(effect["point"] <= -2.0 and effect["percentile_95_interval"][1] < 0.0)

def _material_paired(contrast: dict[str, Any], endpoint: str) -> bool:
    effect = contrast["endpoints"][endpoint]["ratio_of_means_percent"]
    return bool(effect["point"] <= -2.0 and effect["percentile_95_interval"][1] < 0.0)

def _seed_effects(grid: dict[str, dict[str, dict[str, Any]]], bank_names: list[str]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for comparator in ("causal", "centralized"):
        rows = []
        for seed in SEEDS:
            seed_row: dict[str, Any] = {"seed": seed, "endpoints": {}}
            for endpoint in PRIMARY_ENDPOINTS:
                left = float(np.mean([grid[name][f"shared_s{seed}"][endpoint] for name in bank_names]))
                right_arm = comparator if comparator == "causal" else f"centralized_s{seed}"
                right = float(np.mean([grid[name][right_arm][endpoint] for name in bank_names]))
                seed_row["endpoints"][endpoint] = {"effect_percent": _relative_percent(left, right), "directional_improvement": left < right}
            seed_row["both_endpoints_directional_improvement"] = all(row["directional_improvement"] for row in seed_row["endpoints"].values())
            rows.append(seed_row)
        output[f"shared_vs_{comparator}"] = {"rows": rows, "both_endpoint_improvement_count": sum(row["both_endpoints_directional_improvement"] for row in rows)}
    return output

def _classification(*, valid: bool, causal_vs_q0: dict[str, Any], hierarchical: dict[str, dict[str, Any]], seed_effects: dict[str, Any]) -> dict[str, Any]:
    if not valid:
        return {"classification": "INVALID", "reason": "one or more formal validity or guard contracts failed"}
    shared_q0 = all(_material_hierarchical(hierarchical["shared_vs_q0"], endpoint) for endpoint in PRIMARY_ENDPOINTS)
    shared_causal = all(_material_hierarchical(hierarchical["shared_vs_causal"], endpoint) for endpoint in PRIMARY_ENDPOINTS)
    shared_central = all(_material_hierarchical(hierarchical["shared_vs_centralized"], endpoint) for endpoint in PRIMARY_ENDPOINTS)
    causal_value = all(_material_paired(causal_vs_q0, endpoint) for endpoint in PRIMARY_ENDPOINTS)
    central_value = all(_material_hierarchical(hierarchical["centralized_vs_q0"], endpoint) for endpoint in PRIMARY_ENDPOINTS)
    directional = all(seed_effects[name]["both_endpoint_improvement_count"] >= 2 for name in ("shared_vs_causal", "shared_vs_centralized"))
    gates = {"shared_vs_q0_both_primary": shared_q0, "shared_vs_causal_both_primary": shared_causal, "shared_vs_centralized_both_primary": shared_central, "causal_vs_q0_both_primary": causal_value, "centralized_vs_q0_both_primary": central_value, "shared_directional_at_least_2_of_3": directional}
    if shared_q0 and shared_causal and shared_central and directional:
        classification, reason = "MARL-IDENTIFIABLE-POSITIVE", "shared actor clears both primary endpoints against all simpler comparators"
    elif causal_value and not shared_causal:
        classification, reason = "CAUSAL-EXPLANATION-SUFFICIENT", "causal feedback has guarded value and shared actor lacks incremental value"
    elif central_value and not shared_central:
        classification, reason = "CENTRALIZED-EXPLANATION-SUFFICIENT", "centralized actor has reproducible value and shared actor lacks incremental value"
    elif not shared_q0 and not central_value:
        classification, reason = "NO-REPRODUCIBLE-LEARNED-VALUE", "neither learned architecture clears both primary endpoints against q0"
    else:
        classification, reason = "LEARNED-VALUE-NOT-MARL-IDENTIFIABLE", "learned value exists but is not uniquely attributable to parameter sharing"
    return {"classification": classification, "reason": reason, "efficacy_gates": gates}
def analyse(manifest_path: Path, expected: str, out_dir: Path) -> None:
    manifest = _verify(manifest_path, expected)
    bank, _ = load_scenario_bank(FORMAL_BANK, expected_sha256=manifest["formal_bank"]["sha256"])
    bank_names = [row["name"] for row in bank["scenarios"]]
    grid: dict[str, dict[str, dict[str, Any]]] = {name: {} for name in bank_names}
    records: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    action_audits: dict[str, dict[str, dict[str, bool]]] = {arm: {} for arm in ARMS}
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
                failures.append({"scenario": scenario["name"], "arm": arm, "completed": bool(record.get("completed")), "tds_failed": bool(record.get("tds_failed")), "trace_sha256": digest})
                continue
            row = _endpoint_row(record)
            grid[scenario["name"]][arm] = row
            action_audits[arm][scenario["name"]] = audit_icems_policy_action(row)
    complete_matrix = not failures and all(set(grid[name]) == set(ARMS) for name in bank_names)
    if not complete_matrix:
        summary = {"schema_version": 1, "round": ROUND_ID, "question": "Q-0041", "phase": "fresh-bank-eight-arm-formal", "formal_seal_sha256": expected, "decision": {"classification": "INVALID", "reason": "formal trajectory matrix is incomplete"}, "completion": {"expected": len(bank_names) * len(ARMS), "observed_complete": sum(len(rows) for rows in grid.values()), "failures": failures}, "trace_hashes": dict(sorted(trace_hashes.items()))}
        summary_hash = _write_new(out_dir / "formal_summary.json", summary)
        _write_new(out_dir / "provenance.json", {"schema_version": 1, "round": ROUND_ID, "formal_seal_sha256": expected, "summary_sha256": summary_hash, "trace_hashes": dict(sorted(trace_hashes.items())), "paper_files_modified": False})
        print("[analysed] classification=INVALID incomplete formal matrix", flush=True)
        return
    arm_summaries: dict[str, Any] = {}
    for arm in ARMS:
        rows = [grid[name][arm] for name in bank_names]
        arm_summaries[arm] = {
            "scenario_count": len(rows),
            "means": {endpoint: float(np.mean([row[endpoint] for row in rows])) for endpoint in CONTINUOUS_ENDPOINTS},
            "medians": {endpoint: float(np.median([row[endpoint] for row in rows])) for endpoint in CONTINUOUS_ENDPOINTS},
            "cvar90": {endpoint: empirical_upper_tail({name: float(grid[name][arm][endpoint]) for name in bank_names}) for endpoint in TAIL_ENDPOINTS},
            "storage": _aggregate_storage(records[arm]),
        }
    paired_input = {arm: {endpoint: [grid[name][arm][endpoint] for name in bank_names] for endpoint in STATISTICAL_ENDPOINTS} for arm in ("causal", "q0")}
    causal_paired = paired_bootstrap_contrasts(paired_input, contrasts=(("causal_minus_q0", "causal", "q0"),), seed=PAIRED_BOOTSTRAP_SEED, n_resamples=BOOTSTRAP_RESAMPLES)["contrasts"]["causal_minus_q0"]
    hierarchical = {
        "shared_vs_q0": _hierarchical_contrast(grid, bank_names, "shared", "q0"),
        "shared_vs_causal": _hierarchical_contrast(grid, bank_names, "shared", "causal"),
        "shared_vs_centralized": _hierarchical_contrast(grid, bank_names, "shared", "centralized"),
        "centralized_vs_q0": _hierarchical_contrast(grid, bank_names, "centralized", "q0"),
    }
    per_seed = _seed_effects(grid, bank_names)
    q0_summary = arm_summaries["q0"]
    relative_guards: dict[str, Any] = {}
    for arm in ARMS[1:]:
        fast_mean = {endpoint: _relative_percent(arm_summaries[arm]["means"][endpoint], q0_summary["means"][endpoint]) for endpoint in FAST_COMMON_ENDPOINTS}
        slow_mean = {endpoint: _relative_percent(arm_summaries[arm]["means"][endpoint], q0_summary["means"][endpoint]) for endpoint in SLOW_COMMON_ENDPOINTS}
        storage_mean = {endpoint: _guard_relative_percent(arm_summaries[arm]["means"][endpoint], q0_summary["means"][endpoint]) for endpoint in STORAGE_ENDPOINTS}
        tail = {endpoint: _relative_percent(arm_summaries[arm]["cvar90"][endpoint]["cvar_upper_tail"], q0_summary["cvar90"][endpoint]["cvar_upper_tail"]) for endpoint in TAIL_ENDPOINTS}
        relative_guards[arm] = {"fast_common_mean_effect_percent": fast_mean, "slow_common_mean_effect_percent": slow_mean, "storage_mean_effect_percent": storage_mean, "tail_cvar90_effect_percent": tail, "pass": all(value <= 5.0 for value in fast_mean.values()) and all(value <= 2.0 for value in slow_mean.values()) and all(value <= 5.0 for value in storage_mean.values()) and all(value <= (2.0 if endpoint in SLOW_COMMON_ENDPOINTS else 5.0) for endpoint, value in tail.items())}
    absolute_storage = {}
    for arm in ARMS:
        row = arm_summaries[arm]["storage"]
        absolute_storage[arm] = {**row, "pass": row["constraint_violation_count"] == 0 and row["saturation_reason_count"] == 0 and row["max_abs_commanded_power_system_pu"] <= 0.36 + 1e-12 and row["max_abs_actual_power_system_pu"] <= 0.36 + 1e-12 and row["min_soc"] >= 0.20 - 1e-9 and row["max_soc"] <= 0.80 + 1e-9}
    action_pass = all(len(action_audits[arm]) == len(bank_names) and all(all(audit.values()) for audit in action_audits[arm].values()) for arm in ARMS)
    validity = {"complete_eight_arm_matrix": complete_matrix, "formal_bank_screen_pass": True, "action_contract_all_rows": action_pass, "absolute_storage_all_arms": all(row["pass"] for row in absolute_storage.values()), "relative_no_harm_all_candidate_arms": all(row["pass"] for row in relative_guards.values()), "bootstrap_contract_complete": True, "provenance_hashes_verified": True}
    decision = _classification(valid=all(validity.values()), causal_vs_q0=causal_paired, hierarchical=hierarchical, seed_effects=per_seed)
    decision["validity_guards"] = validity
    summary = {
        "schema_version": 1, "round": ROUND_ID, "question": "Q-0041", "phase": "fresh-bank-eight-arm-formal", "formal_seal_sha256": expected,
        "formal_bank_sha256": manifest["formal_bank"]["sha256"], "decision": decision,
        "completion": {"expected": len(bank_names) * len(ARMS), "observed_complete": len(bank_names) * len(ARMS), "failures": []},
        "arm_summaries": arm_summaries, "paired_bootstrap": {"causal_vs_q0": causal_paired}, "hierarchical_bootstrap": hierarchical,
        "per_seed_primary_effects": per_seed, "action_audits": action_audits, "absolute_storage_guards": absolute_storage,
        "relative_guards_vs_q0": relative_guards, "trace_hashes": dict(sorted(trace_hashes.items())),
    }
    summary_hash = _write_new(out_dir / "formal_summary.json", summary)
    markdown = "\n".join(["# R279 fresh-bank formal evaluation", "", f"**Classification:** `{decision['classification']}`", "", decision["reason"], "", f"Completed trajectories: {len(bank_names) * len(ARMS)} / {len(bank_names) * len(ARMS)}.", ""])
    markdown_hash = _write_new_text(out_dir / "formal_summary.md", markdown)
    provenance = {"schema_version": 1, "round": ROUND_ID, "repository_head": _git_head(), "formal_seal_sha256": expected, "formal_bank_sha256": manifest["formal_bank"]["sha256"], "summary_sha256": summary_hash, "markdown_sha256": markdown_hash, "source_sha256": {name: entry["sha256"] for name, entry in manifest["sources"].items()}, "trace_hashes": dict(sorted(trace_hashes.items())), "paper_files_modified": False, "seed_selection_performed": False, "failed_trajectories_retained": True}
    provenance_hash = _write_new(out_dir / "provenance.json", provenance)
    print(f"[analysed] classification={decision['classification']} summary_sha256={summary_hash} provenance_sha256={provenance_hash}", flush=True)

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
        run_shard(args.manifest, args.expected_manifest_sha256, args.out_dir, args.shard_index, args.shard_count)
    else:
        analyse(args.manifest, args.expected_manifest_sha256, args.out_dir)

if __name__ == "__main__":
    main()
