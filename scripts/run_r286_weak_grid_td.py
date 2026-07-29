#!/usr/bin/env python3
# ruff: noqa: E402
"""R286 — weak-tie-corridor zero-training transfer evaluation (Q-0045).

Reruns the frozen R279 arms (q0 + centralized s17/s53/s89) on the sealed
24-scenario formal bank with the 7<->8 triple-circuit inter-area tie
corridor (Line_4/Line_5/Line_6) r/x scaled by k in {1.5, 2.0}. Mirrors
run_r279_formal.py discipline: seal-before-trace, immutable artifacts,
hash-verified upstreams, paired hierarchical bootstrap. Nominal k=1
reference effects come from the sealed R279 formal summary (read-only,
hash-verified); the disturbance-location read additionally summarises the
sealed R279 traces read-only.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from andes_rl_kundur.agents.central_scalar_td3 import CentralScalarTD3
from andes_rl_kundur.evaluation.icems_residual import (
    audit_icems_policy_action,
    summarise_icems_policy_trace,
)
from andes_rl_kundur.evaluation.r279_controllers import _trace_row
from andes_rl_kundur.evaluation.reviewer_identifiability import (
    hierarchical_seed_scenario_ratio_bootstrap,
)
from andes_rl_kundur.evaluation.sealed_bank import (
    canonical_json_bytes,
    load_scenario_bank,
    sha256_bytes,
    sha256_file,
)

ROUND_ID = "R286"
QUESTION = "Q-0045"
PHASE = "weak-tie-transfer"
ENV_SEED, STEPS, FAST_STEPS, FINAL_WINDOW_STEPS, SHARD_COUNT = 42, 300, 15, 50, 8
SEEDS = (17, 53, 89)
TIE_K_LEVELS = (1.5, 2.0)
BOOTSTRAP_RESAMPLES = 10_000
HIERARCHICAL_BOOTSTRAP_SEED = 2026072901
PRIMARY_ENDPOINTS = ("normalized_sync_loss_hz2", "fast_inter_area_iae_hz_s")
ARMS = ("q0", "centralized_s17", "centralized_s53", "centralized_s89")
FORMAL_BANK = ROOT / "results/r279_fresh_bank/formal_bank.json"
SCREEN_SUMMARY = ROOT / "results/r279_fresh_bank/screen_summary.json"
TRAINING_SUMMARY = ROOT / "results/r279_matched_training/training_matrix_summary.json"
R279_FORMAL_SUMMARY = ROOT / "results/r279_formal_evaluation/formal_summary.json"
R279_TRACE_DIR = ROOT / "results/r279_formal_evaluation/traces"
WEAK_TIE_SOURCE = ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4_weak_tie.py"
DEFAULT_SEAL = ROOT / "memory/rounds/R286/weak_tie_seal.json"
DEFAULT_OUT = ROOT / "results/r286_weak_grid_td"
MATERIALITY_PERCENT = -2.0
RETENTION_MIN = 0.5


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


def _checkpoint_path(seed: int) -> Path:
    return ROOT / f"results/r279_matched_training/centralized_s{seed}/final.pt"


def _contract_path(seed: int) -> Path:
    return ROOT / f"results/r279_matched_training/centralized_s{seed}/controller_contract.json"


def _arm_manifest(training: dict[str, Any]) -> dict[str, Any]:
    rows = {(row["architecture"], int(row["seed"])): row for row in training["rows"]}
    arms: dict[str, Any] = {"q0": {"kind": "deterministic", "controller": "q0"}}
    for seed in SEEDS:
        row = rows[("centralized", seed)]
        checkpoint, contract = _checkpoint_path(seed), _contract_path(seed)
        if sha256_file(checkpoint) != row["checkpoint_sha256"]:
            raise ValueError(f"checkpoint drift: {checkpoint}")
        arms[f"centralized_s{seed}"] = {
            "kind": "learned", "architecture": "centralized", "seed": seed,
            "checkpoint": str(checkpoint.relative_to(ROOT)).replace("\\", "/"),
            "checkpoint_sha256": row["checkpoint_sha256"],
            "controller_contract": str(contract.relative_to(ROOT)).replace("\\", "/"),
            "controller_contract_sha256": sha256_file(contract),
            "actor_parameter_count": row["actor_parameter_count"],
        }
    if tuple(arms) != ARMS:
        raise ValueError("R286 arm order drift")
    return arms


def _nominal_reference(formal: dict[str, Any]) -> dict[str, float]:
    contrast = formal["hierarchical_bootstrap"]["centralized_vs_q0"]
    return {
        endpoint: float(contrast[endpoint]["ratio_of_means_percent"]["point"])
        for endpoint in PRIMARY_ENDPOINTS
    }


def prepare(manifest_path: Path, out_dir: Path) -> None:
    trace_dir = out_dir / "traces"
    if trace_dir.exists() and any(trace_dir.glob("*.json")):
        raise ValueError("R286 seal must precede every controller trace")
    training = _load_json(TRAINING_SUMMARY)
    if not training.get("all_completed") or training.get("seed_selection_performed") is not False:
        raise ValueError("R286 requires the completed selection-free R279 training matrix")
    for path_text, digest in training.get("artifact_hashes", {}).items():
        if sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"training artifact drift: {path_text}")
    screen = _load_json(SCREEN_SUMMARY)
    if screen.get("decision", {}).get("classification") != "PASS":
        raise ValueError("R286 requires the passing fresh-bank screen")
    bank, bank_hash = load_scenario_bank(FORMAL_BANK, expected_sha256=screen["formal_bank_sha256"])
    formal = _load_json(R279_FORMAL_SUMMARY)
    if formal.get("round") != "R279" or "hierarchical_bootstrap" not in formal:
        raise ValueError("nominal reference is not the sealed R279 formal summary")
    nominal = _nominal_reference(formal)
    arms = _arm_manifest(training)
    sources = {
        name: {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256_file(path)}
        for name, path in {
            "plan": ROOT / "memory/rounds/R286/plan.md",
            "script": Path(__file__).resolve(),
            "weak_tie_env": WEAK_TIE_SOURCE,
            "generic_runner": ROOT / "src/andes_rl_kundur/evaluation/r279_controllers.py",
            "analysis": ROOT / "src/andes_rl_kundur/evaluation/reviewer_identifiability.py",
            "central_actor": ROOT / "src/andes_rl_kundur/agents/central_scalar_td3.py",
            "icems_evaluation": ROOT / "src/andes_rl_kundur/evaluation/icems_residual.py",
            "sealed_bank": ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py",
            "formal_bank": FORMAL_BANK,
        }.items()
    }
    payload = {
        "schema_version": 1, "round": ROUND_ID, "question": QUESTION, "phase": PHASE,
        "repository_head": _git_head(),
        "formal_bank": {"path": str(FORMAL_BANK.relative_to(ROOT)).replace("\\", "/"), "sha256": bank_hash, "scenario_count": bank["scenario_count"]},
        "training_summary_sha256": sha256_file(TRAINING_SUMMARY),
        "screen_summary_sha256": sha256_file(SCREEN_SUMMARY),
        "r279_formal_summary": {
            "path": str(R279_FORMAL_SUMMARY.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(R279_FORMAL_SUMMARY),
        },
        "nominal_reference_effects_percent": nominal,
        "arms": arms,
        "tie": {"tie_idx": ["Line_4", "Line_5", "Line_6"], "k_levels": list(TIE_K_LEVELS)},
        "execution": {"environment_seed": ENV_SEED, "steps": STEPS, "shard_count": SHARD_COUNT,
                      "arm_count": len(ARMS), "k_level_count": len(TIE_K_LEVELS),
                      "trajectory_budget": len(ARMS) * len(TIE_K_LEVELS) * bank["scenario_count"],
                      "resume_completed": True, "overwrite": False, "retry_failed_trajectory": False},
        "statistics": {"hierarchical_bootstrap_seed": HIERARCHICAL_BOOTSTRAP_SEED,
                       "resamples": BOOTSTRAP_RESAMPLES, "materiality_percent": MATERIALITY_PERCENT,
                       "retention_min": RETENTION_MIN, "confidence": 0.95,
                       "lower_is_better": True, "primary_endpoints": list(PRIMARY_ENDPOINTS)},
        "sources": sources,
        "packages": {name: importlib.metadata.version(name) for name in ("andes", "numpy", "torch")} | {"python": sys.version},
        "trace_count_at_freeze": 0,
    }
    digest = _write_new(manifest_path, payload)
    print(f"[sealed] {manifest_path} sha256={digest}", flush=True)


def _verify(manifest_path: Path, expected: str) -> dict[str, Any]:
    manifest = _load_json(manifest_path, expected)
    if manifest.get("round") != ROUND_ID or manifest.get("phase") != PHASE:
        raise ValueError("not an R286 weak-tie seal")
    for entry in manifest["sources"].values():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError(f"R286 source drift: {entry['path']}")
    _load_json(TRAINING_SUMMARY, manifest["training_summary_sha256"])
    load_scenario_bank(FORMAL_BANK, expected_sha256=manifest["formal_bank"]["sha256"])
    _load_json(R279_FORMAL_SUMMARY, manifest["r279_formal_summary"]["sha256"])
    for arm, config in manifest["arms"].items():
        if config["kind"] == "learned" and (
            sha256_file(ROOT / config["checkpoint"]) != config["checkpoint_sha256"]
            or sha256_file(ROOT / config["controller_contract"]) != config["controller_contract_sha256"]
        ):
            raise ValueError(f"R286 learned artifact drift: {arm}")
    return manifest


def _make_controller(arm: str, config: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    if arm == "q0":
        return ZeroResidualController(), {"name": "q0", "q": 0.0}
    controller = CentralScalarTD3(critic_hidden_sizes=[64, 64], actor_hidden_sizes=[55, 55], device="cpu")
    metadata = controller.load(ROOT / config["checkpoint"])
    expected = {"round": "R279", "question": "Q-0041", "architecture": "centralized",
                "seed": config["seed"], "episodes_completed": 300, "total_steps": 4500, "smoke": False}
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise ValueError(f"checkpoint metadata mismatch for {arm}: {key}")
    return controller, {
        "architecture": "centralized", "seed": config["seed"],
        "checkpoint": config["checkpoint"], "checkpoint_sha256": config["checkpoint_sha256"],
        "controller_contract_sha256": config["controller_contract_sha256"],
        "checkpoint_metadata": metadata,
    }


def _run_scenario(controller: Any, *, controller_name: str, controller_config: Mapping[str, Any],
                  scenario_name: str, delta_u: Mapping[str, float], tie_k: float,
                  evidence_hashes: Mapping[str, str]) -> dict[str, Any]:
    """One R286 trajectory: R279 runner discipline on the weak-tie plant."""
    from andes_rl_kundur.env.andes.icems_residual_env import ICEMSResidualEnv
    from andes_rl_kundur.env.andes.andes_vsg_env_v4_weak_tie import (
        AndesMultiVSGEnvV4WeakTie,
    )
    from andes_rl_kundur.control.area_inertia_residual import r278_area_inertia_contract

    env = ICEMSResidualEnv(
        AndesMultiVSGEnvV4WeakTie(random_disturbance=False, comm_fail_prob=0.0, tie_k=tie_k)
    )
    reset = getattr(controller, "reset", None)
    if callable(reset):
        reset()
    traces: list[dict[str, Any]] = []
    tds_failed = False
    nominal_hz = 60.0
    started = time.perf_counter()
    try:
        env.seed(ENV_SEED)
        env.STEPS_PER_EPISODE = STEPS
        observation = env.reset(delta_u=dict(delta_u))
        nominal_hz = float(env.base_env.andes_nominal_frequency_hz)
        for step in range(STEPS):
            raw = np.asarray(controller.select_raw_actions(observation, deterministic=True), dtype=np.float32)
            observation, _rewards, done, info = env.step(raw)
            if info.get("tds_failed"):
                tds_failed = True
                break
            traces.append(_trace_row(step, info, nominal_hz))
            if done:
                break
    finally:
        env.close()
    tie_detail = getattr(env.base_env, "tie_lines_applied", None)
    tie_nominal = (
        {idx: {"r": row["r"] / tie_k, "x": row["x"] / tie_k} for idx, row in tie_detail.items()}
        if tie_detail else None
    )
    return {
        "schema_version": 1, "round": ROUND_ID, "question": QUESTION,
        "experiment": "r286_weak_tie_transfer", "phase": PHASE,
        "controller": controller_name, "scenario": scenario_name,
        "delta_u": dict(delta_u), "tie_k": float(tie_k),
        "tie_lines": tie_detail, "tie_lines_nominal_derived": tie_nominal,
        "env_version": "v4_plus_independent_esd1_weak_tie",
        "control_nominal_frequency_hz": float(env.base_env.FN),
        "andes_nominal_frequency_hz": nominal_hz,
        "frequency_reporting_basis": "legacy_control_hz",
        "metric_frequency_basis": "andes_physical_hz",
        "requested_steps": STEPS, "n_steps": len(traces),
        "tds_failed": tds_failed,
        "completed": not tds_failed and len(traces) == STEPS,
        "wall_clock_s": time.perf_counter() - started,
        "traces": traces,
        "controller_config": {
            **dict(controller_config),
            "area_residual": r278_area_inertia_contract().telemetry(),
        },
        "evidence_hashes": dict(evidence_hashes),
        "seed": ENV_SEED,
    }


def _trace_path(out_dir: Path, scenario: str, arm: str, tie_k: float) -> Path:
    return out_dir / "traces" / f"{scenario}__{arm}__k{tie_k:.2f}.json"


def _validate_trace(path: Path, scenario: dict[str, Any], arm: str, tie_k: float,
                    manifest: dict[str, Any], seal_hash: str) -> dict[str, Any]:
    record = _load_json(path)
    expected = {"round": ROUND_ID, "phase": PHASE, "controller": arm,
                "scenario": scenario["name"], "delta_u": scenario["delta_u"],
                "tie_k": tie_k, "weak_tie_seal_sha256": seal_hash,
                "formal_bank_sha256": manifest["formal_bank"]["sha256"]}
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"R286 trace provenance mismatch in {path}: {key}")
    return record


def run_shard(manifest_path: Path, expected: str, out_dir: Path, shard_index: int, shard_count: int) -> None:
    manifest = _verify(manifest_path, expected)
    if shard_count != manifest["execution"]["shard_count"] or not 0 <= shard_index < shard_count:
        raise ValueError("R286 shard contract drift")
    bank, _ = load_scenario_bank(FORMAL_BANK, expected_sha256=manifest["formal_bank"]["sha256"])
    tasks = [(scenario, arm, tie_k) for scenario in bank["scenarios"] for arm in ARMS for tie_k in TIE_K_LEVELS]
    selected = [task for index, task in enumerate(tasks) if index % shard_count == shard_index]
    controllers: dict[str, tuple[Any, dict[str, Any]]] = {}
    for index, (scenario, arm, tie_k) in enumerate(selected, start=1):
        path = _trace_path(out_dir, scenario["name"], arm, tie_k)
        if path.exists():
            record = _validate_trace(path, scenario, arm, tie_k, manifest, expected)
            if not record.get("completed") or record.get("tds_failed"):
                raise RuntimeError(f"retained failed R286 trace forbids retry: {path}")
            print(f"[resume {index:03d}/{len(selected):03d}] {path.name}", flush=True)
            continue
        if arm not in controllers:
            controllers[arm] = _make_controller(arm, manifest["arms"][arm])
        controller, controller_config = controllers[arm]
        record = _run_scenario(
            controller, controller_name=arm, controller_config=controller_config,
            scenario_name=scenario["name"], delta_u=scenario["delta_u"], tie_k=tie_k,
            evidence_hashes={"weak_tie_seal": expected, "formal_bank": manifest["formal_bank"]["sha256"]},
        )
        record.update({
            "location": scenario["location"], "sign": scenario["sign"], "severity": scenario["severity"],
            "weak_tie_seal_sha256": expected, "formal_bank_sha256": manifest["formal_bank"]["sha256"],
            "execution_shard_index": shard_index, "execution_shard_count": shard_count,
        })
        digest = _write_new(path, record)
        print(f"[r286 {index:03d}/{len(selected):03d}] {path.name} completed={record['completed']} "
              f"wall={record['wall_clock_s']:.1f}s sha256={digest}", flush=True)
        if not record["completed"]:
            raise RuntimeError(f"R286 trajectory failed and is retained: {path}")


def _endpoint_row(record: dict[str, Any]) -> dict[str, Any]:
    row = summarise_icems_policy_trace(record, final_window_steps=FINAL_WINDOW_STEPS, fast_window_steps=FAST_STEPS)
    delta = np.asarray([step["delta_f_physical_hz"] for step in record["traces"]], dtype=float)
    row["first_3s_common_iae_hz_s"] = float(np.sum(np.abs(np.mean(delta, axis=1)[:FAST_STEPS])) * row["sample_interval_s"])
    return row


def _aggregate_storage(records: list[dict[str, Any]]) -> dict[str, Any]:
    steps = [step for record in records for step in record["traces"]]
    commanded = np.asarray([value for step in steps for value in step["bess_commanded_power_system_pu"]], dtype=float)
    actual = np.asarray([value for step in steps for value in step["bess_actual_power_system_pu"]], dtype=float)
    soc = np.asarray([value for step in steps for value in step["bess_soc"]], dtype=float)
    row = {"max_abs_commanded_power_system_pu": float(np.max(np.abs(commanded))),
           "max_abs_actual_power_system_pu": float(np.max(np.abs(actual))),
           "min_soc": float(np.min(soc)), "max_soc": float(np.max(soc)),
           "constraint_violation_count": sum(len(step["bess_constraint_violations"]) for step in steps),
           "saturation_reason_count": sum(bool(reason) for step in steps for reason in step["bess_saturation_reasons"])}
    row["pass"] = (row["constraint_violation_count"] == 0 and row["saturation_reason_count"] == 0
                   and row["max_abs_commanded_power_system_pu"] <= 0.36 + 1e-12
                   and row["max_abs_actual_power_system_pu"] <= 0.36 + 1e-12
                   and row["min_soc"] >= 0.20 - 1e-9 and row["max_soc"] <= 0.80 + 1e-9)
    return row


def _injection_consistent(records: list[dict[str, Any]]) -> dict[str, Any]:
    nominal: dict[str, dict[str, float]] | None = None
    ok = True
    for record in records:
        detail, derived, tie_k = record["tie_lines"], record["tie_lines_nominal_derived"], record["tie_k"]
        if detail is None or derived is None:
            ok = False
            continue
        if nominal is None:
            nominal = derived
        for idx in ("Line_4", "Line_5", "Line_6"):
            if abs(detail[idx]["r"] - derived[idx]["r"] * tie_k) > 1e-12 \
                    or abs(detail[idx]["x"] - derived[idx]["x"] * tie_k) > 1e-12 \
                    or abs(derived[idx]["x"] - nominal[idx]["x"]) > 1e-12 \
                    or abs(derived[idx]["r"] - nominal[idx]["r"]) > 1e-12:
                ok = False
    return {"pass": ok, "nominal": nominal}


def _contrast_at_k(grid: dict[str, dict[str, Any]], bank_names: list[str]) -> dict[str, Any]:
    result = {}
    for endpoint in PRIMARY_ENDPOINTS:
        left = {seed: {name: float(grid[name][f"centralized_s{seed}"][endpoint]) for name in bank_names} for seed in SEEDS}
        right = {name: float(grid[name]["q0"][endpoint]) for name in bank_names}
        result[endpoint] = hierarchical_seed_scenario_ratio_bootstrap(
            left, right_deterministic=right,
            resamples=BOOTSTRAP_RESAMPLES, seed=HIERARCHICAL_BOOTSTRAP_SEED)
    return result


def _material(effect: dict[str, Any]) -> bool:
    point = effect["ratio_of_means_percent"]["point"]
    upper = effect["ratio_of_means_percent"]["percentile_95_interval"][1]
    return bool(point <= MATERIALITY_PERCENT and upper < 0.0)


def _classify(per_k: dict[str, dict[str, Any]], nominal: dict[str, float]) -> dict[str, Any]:
    rows = {}
    for k_text, contrast in per_k.items():
        row = {}
        for endpoint in PRIMARY_ENDPOINTS:
            effect = contrast[endpoint]["ratio_of_means_percent"]
            row[endpoint] = {
                "point_percent": effect["point"],
                "ci95": effect["percentile_95_interval"],
                "material_improvement": _material(contrast[endpoint]),
                "direction_kept": bool(effect["point"] < 0.0),
                "retention_vs_nominal": effect["point"] / nominal[endpoint],
            }
        rows[k_text] = row
    reversal = any(not row[endpoint]["direction_kept"] for row in rows.values() for endpoint in PRIMARY_ENDPOINTS)
    gain_gone = any(
        all(not row[endpoint]["material_improvement"] for endpoint in PRIMARY_ENDPOINTS)
        for row in rows.values()
    )
    survives = all(
        row[endpoint]["material_improvement"] and row[endpoint]["retention_vs_nominal"] >= RETENTION_MIN
        for row in rows.values() for endpoint in PRIMARY_ENDPOINTS
    )
    if reversal or gain_gone:
        classification, reason = "COLLAPSES", "gain reversed or materially gone at at least one k level"
    elif survives:
        classification, reason = "SURVIVES", "both primary endpoints keep material improvement with >=50% retention at every k level"
    else:
        classification, reason = "DEGRADED", "direction kept but retention below 50% or improvement not material at some k level"
    return {"classification": classification, "reason": reason, "per_k": rows}


def _location_read(grids: dict[str, dict[str, dict[str, Any]]], bank: dict[str, Any]) -> dict[str, Any]:
    locations = sorted({row["location"] for row in bank["scenarios"]})
    names_by_location = {
        location: [row["name"] for row in bank["scenarios"] if row["location"] == location]
        for location in locations
    }
    out: dict[str, Any] = {}
    for k_text, grid in grids.items():
        per_location: dict[str, Any] = {}
        for location, names in names_by_location.items():
            row: dict[str, Any] = {"scenario_count": len(names), "endpoints": {}}
            for endpoint in PRIMARY_ENDPOINTS:
                central = [float(grid[name][f"centralized_s{seed}"][endpoint]) for name in names for seed in SEEDS]
                q0 = [float(grid[name]["q0"][endpoint]) for name in names for _ in SEEDS]
                q0_mean = float(np.mean([float(grid[name]["q0"][endpoint]) for name in names]))
                row["endpoints"][endpoint] = {
                    "centralized_mean": float(np.mean(central)),
                    "q0_mean": q0_mean,
                    "ratio_of_means_percent": 100.0 * (float(np.mean(central)) / float(np.mean(q0)) - 1.0) if float(np.mean(q0)) > 0 else None,
                }
            per_location[location] = row
        out[k_text] = per_location
    return out


def _nominal_grid(bank: dict[str, Any], formal: dict[str, Any]) -> dict[str, dict[str, Any]]:
    trace_hashes = formal.get("trace_hashes", {})
    grid: dict[str, dict[str, Any]] = {}
    for scenario in bank["scenarios"]:
        name = scenario["name"]
        grid[name] = {}
        for arm in ARMS:
            path = R279_TRACE_DIR / f"{name}__{arm}.json"
            rel = str(path.relative_to(ROOT)).replace("\\", "/")
            if rel in trace_hashes and sha256_file(path) != trace_hashes[rel]:
                raise ValueError(f"sealed R279 trace drift: {rel}")
            record = _load_json(path)
            if record.get("scenario") != name or record.get("controller") != arm:
                raise ValueError(f"R279 trace identity mismatch: {rel}")
            grid[name][arm] = _endpoint_row(record)
    return grid


def analyse(manifest_path: Path, expected: str, out_dir: Path) -> None:
    manifest = _verify(manifest_path, expected)
    bank, _ = load_scenario_bank(FORMAL_BANK, expected_sha256=manifest["formal_bank"]["sha256"])
    bank_names = [row["name"] for row in bank["scenarios"]]
    formal = _load_json(R279_FORMAL_SUMMARY, manifest["r279_formal_summary"]["sha256"])
    nominal = manifest["nominal_reference_effects_percent"]
    grids: dict[str, dict[str, dict[str, Any]]] = {}
    records_by_arm_k: dict[str, list[dict[str, Any]]] = {}
    action_ok = True
    failures = []
    trace_hashes: dict[str, str] = {}
    all_records: list[dict[str, Any]] = []
    for tie_k in TIE_K_LEVELS:
        k_text = f"{tie_k:.2f}"
        grid: dict[str, dict[str, Any]] = {name: {} for name in bank_names}
        for scenario in bank["scenarios"]:
            for arm in ARMS:
                path = _trace_path(out_dir, scenario["name"], arm, tie_k)
                record = _validate_trace(path, scenario, arm, tie_k, manifest, expected)
                digest = sha256_file(path)
                trace_hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = digest
                all_records.append(record)
                records_by_arm_k.setdefault(f"{arm}__k{k_text}", []).append(record)
                if not record.get("completed") or record.get("tds_failed"):
                    failures.append({"scenario": scenario["name"], "arm": arm, "tie_k": tie_k})
                    continue
                row = _endpoint_row(record)
                grid[scenario["name"]][arm] = row
                action_ok = action_ok and all(audit_icems_policy_action(row).values())
        grids[k_text] = grid
    complete = not failures and all(
        set(grids[k_text][name]) == set(ARMS) for k_text in grids for name in bank_names
    )
    storage = {key: _aggregate_storage(recs) for key, recs in records_by_arm_k.items()}
    injection = _injection_consistent(all_records)
    per_k_contrast = {k_text: _contrast_at_k(grids[k_text], bank_names) for k_text in grids} if complete else {}
    decision = _classify(per_k_contrast, nominal) if complete else {
        "classification": "INVALID", "reason": "incomplete trajectory matrix", "per_k": {}}
    if complete and (not action_ok or not all(row["pass"] for row in storage.values()) or not injection["pass"]):
        decision = {"classification": "INVALID",
                    "reason": "guard failure (action audit, storage, or injection consistency)",
                    "per_k": decision.get("per_k", {})}
    nominal_grid = _nominal_grid(bank, formal)
    location = _location_read({"1.00_nominal_r279": nominal_grid, **grids}, bank)
    summary = {
        "schema_version": 1, "round": ROUND_ID, "question": QUESTION, "phase": PHASE,
        "weak_tie_seal_sha256": expected, "formal_bank_sha256": manifest["formal_bank"]["sha256"],
        "nominal_reference_effects_percent": nominal,
        "decision": decision,
        "completion": {"expected": len(bank_names) * len(ARMS) * len(TIE_K_LEVELS),
                       "observed_complete": sum(len(grids[k][n]) for k in grids for n in bank_names),
                       "failures": failures},
        "contrasts": per_k_contrast,
        "location_read": location,
        "guards": {"complete_matrix": complete, "action_audits_pass": action_ok,
                   "absolute_storage": storage, "injection_consistency": injection},
        "trace_hashes": dict(sorted(trace_hashes.items())),
    }
    summary_hash = _write_new(out_dir / "weak_tie_summary.json", summary)
    markdown = "\n".join([
        "# R286 weak-tie zero-training transfer", "",
        f"**Classification:** `{decision['classification']}`", "",
        decision["reason"], "",
        f"Nominal reference (R279 sealed): {nominal}", "",
        f"Completed trajectories: {summary['completion']['observed_complete']} / {summary['completion']['expected']}.", "",
    ])
    markdown_hash = _write_new_text(out_dir / "weak_tie_summary.md", markdown)
    provenance = {
        "schema_version": 1, "round": ROUND_ID, "repository_head": _git_head(),
        "weak_tie_seal_sha256": expected, "formal_bank_sha256": manifest["formal_bank"]["sha256"],
        "summary_sha256": summary_hash, "markdown_sha256": markdown_hash,
        "source_sha256": {name: entry["sha256"] for name, entry in manifest["sources"].items()},
        "trace_hashes": dict(sorted(trace_hashes.items())),
        "paper_files_modified": False, "seed_selection_performed": False,
        "failed_trajectories_retained": True, "retraining_performed": False,
    }
    provenance_hash = _write_new(out_dir / "provenance.json", provenance)
    print(f"[analysed] classification={decision['classification']} "
          f"summary_sha256={summary_hash} provenance_sha256={provenance_hash}", flush=True)


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
