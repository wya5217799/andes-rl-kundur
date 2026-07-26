#!/usr/bin/env python3
# ruff: noqa: E402
"""Seal, execute, and analyse the viewed-bank R278 single-seed pilot."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.fast_md_authority import (
    CANDIDATE_CONTROLLER as R275_CONTROLLER,
)
from andes_rl_kundur.evaluation.fast_md_authority import (
    summarise_fast_md_trace,
)
from andes_rl_kundur.evaluation.icems_residual import (
    CONTROLLER,
    FAST_GUARD_ENDPOINTS,
    PRIMARY_ENDPOINTS,
    SLOW_GUARD_ENDPOINTS,
    audit_icems_policy_action,
    classify_icems_pilot,
    run_icems_policy_scenario,
    summarise_icems_policy_trace,
)
from andes_rl_kundur.evaluation.sealed_bank import (
    canonical_json_bytes,
    empirical_upper_tail,
    load_scenario_bank,
    paired_binary_outcome_table,
    paired_bootstrap_contrasts,
    sha256_bytes,
    sha256_file,
)

ROUND_ID = "R278"
ENV_SEED = 42
STEPS = 300
FINAL_WINDOW_STEPS = 50
FAST_WINDOW_STEPS = 15
BOOTSTRAP_SEED = 2026072605
BOOTSTRAP_RESAMPLES = 10_000
SHARD_COUNT = 4
FORMAL_BANK_PATH = (
    ROOT / "results/r274_prospective_active_power_authority/formal_bank.json"
)
FORMAL_BANK_SHA256 = (
    "9d028e8a0e990fbea6585c674b471dba4d41ea27c1e0b7ecb5d8389092b31f44"
)
R275_PROVENANCE_PATH = ROOT / "results/r275_fast_md_authority/provenance.json"
R275_PROVENANCE_SHA256 = (
    "681ba69d959a1e943724468c66a20b51b9775d12a5733d13a744399351f8f99d"
)
DEFAULT_TRAIN_DIR = ROOT / "results/r278_shared_area_td3_s49"
DEFAULT_OUT_DIR = ROOT / "results/r278_icems_residual_pilot_s49"
BASELINE = R275_CONTROLLER
CANDIDATE = CONTROLLER
CONTINUOUS_ENDPOINTS = (
    *FAST_GUARD_ENDPOINTS,
    *PRIMARY_ENDPOINTS,
    *SLOW_GUARD_ENDPOINTS,
    "terminal_common_abs_hz",
    "bess_command_l1_device_s",
    "bess_command_total_variation",
    "bess_charge_energy_mwh_total",
    "bess_discharge_energy_mwh_total",
)
TAIL_THRESHOLDS = {
    **{endpoint: 5.0 for endpoint in FAST_GUARD_ENDPOINTS},
    **{endpoint: 5.0 for endpoint in PRIMARY_ENDPOINTS},
    **{endpoint: 2.0 for endpoint in SLOW_GUARD_ENDPOINTS},
}
STORAGE_RELATIVE_ENDPOINTS = (
    "bess_command_l1_device_s",
    "bess_command_total_variation",
    "bess_charge_energy_mwh_total",
    "bess_discharge_energy_mwh_total",
)


def _write_new_canonical(path: Path, payload: object) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(payload)
    path.write_bytes(data)
    digest = sha256_bytes(data)
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n",
        encoding="utf-8",
    )
    return digest


def _load_object(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    actual = sha256_file(path)
    if expected_sha256 is not None and actual != expected_sha256:
        raise ValueError(
            f"hash mismatch for {path}: expected {expected_sha256}, got {actual}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return payload


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def _candidate_path(out_dir: Path, scenario_name: str) -> Path:
    return out_dir / "pilot_traces" / f"{scenario_name}__{CANDIDATE}.json"


def _baseline_path(scenario_name: str) -> Path:
    return (
        ROOT
        / "results/r275_fast_md_authority/formal_traces"
        / f"{scenario_name}__common_M_pos.json"
    )


def _relative_percent(candidate: float, baseline: float) -> float:
    if np.isclose(baseline, 0.0, rtol=0.0, atol=1e-15):
        return 0.0 if np.isclose(candidate, 0.0, atol=1e-15) else float("inf")
    return 100.0 * (candidate / baseline - 1.0)


def _r275_baseline_hashes() -> dict[str, str]:
    provenance = _load_object(
        R275_PROVENANCE_PATH,
        R275_PROVENANCE_SHA256,
    )
    result = {
        path: digest
        for path, digest in provenance["trace_hashes"].items()
        if path.startswith("results/r275_fast_md_authority/formal_traces/")
        and path.endswith("__common_M_pos.json")
    }
    if len(result) != 24:
        raise ValueError(f"expected 24 immutable R275 traces, found {len(result)}")
    return dict(sorted(result.items()))


def _validate_baseline(
    path: Path,
    *,
    scenario: dict[str, Any],
    expected_sha256: str,
) -> dict[str, Any]:
    record = _load_object(path, expected_sha256)
    expected = {
        "round": "R275",
        "phase": "formal-candidate",
        "controller": BASELINE,
        "scenario": scenario["name"],
        "delta_u": scenario["delta_u"],
        "formal_bank_sha256": FORMAL_BANK_SHA256,
        "seed": ENV_SEED,
        "requested_steps": STEPS,
        "n_steps": STEPS,
        "completed": True,
        "tds_failed": False,
        "provenance_valid": True,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"R275 baseline mismatch in {path}: {key}")
    return record


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R278/plan.md",
        "pilot_runner": ROOT / "scripts/eval_icems_residual_pilot.py",
        "training_runner": ROOT / "scripts/train_icems_residual.py",
        "policy_evaluation": (
            ROOT / "src/andes_rl_kundur/evaluation/icems_residual.py"
        ),
        "policy": ROOT / "src/andes_rl_kundur/agents/shared_area_td3.py",
        "residual_contract": (
            ROOT / "src/andes_rl_kundur/control/area_inertia_residual.py"
        ),
        "residual_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/icems_residual_env.py"
        ),
        "sealed_bank": (
            ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py"
        ),
        "physical_endpoints": (
            ROOT / "src/andes_rl_kundur/evaluation/physical_endpoints.py"
        ),
        "r275_provenance": R275_PROVENANCE_PATH,
        "development_bank": FORMAL_BANK_PATH,
    }


def prepare_seal(
    *,
    manifest_path: Path,
    out_dir: Path,
    train_dir: Path,
) -> None:
    trace_dir = out_dir / "pilot_traces"
    if trace_dir.exists() and any(trace_dir.glob(f"*__{CANDIDATE}.json")):
        raise ValueError("pilot seal must precede every R278 candidate trace")
    bank, bank_sha256 = load_scenario_bank(
        FORMAL_BANK_PATH,
        expected_sha256=FORMAL_BANK_SHA256,
    )
    baseline_hashes = _r275_baseline_hashes()
    for scenario in bank["scenarios"]:
        path = _baseline_path(scenario["name"])
        relative = str(path.relative_to(ROOT)).replace("\\", "/")
        _validate_baseline(
            path,
            scenario=scenario,
            expected_sha256=baseline_hashes[relative],
        )

    contract_path = train_dir / "controller_contract.json"
    summary_path = train_dir / "training_summary.json"
    checkpoint_path = train_dir / "final.pt"
    contract = _load_object(contract_path)
    training_summary = _load_object(summary_path)
    if (
        contract.get("round") != ROUND_ID
        or contract["algorithm"].get("seed") != 49
        or contract["algorithm"].get("episodes") != 300
        or contract.get("smoke")
    ):
        raise ValueError("training contract is not the frozen R278 pilot")
    if (
        training_summary.get("round") != ROUND_ID
        or training_summary.get("seed") != 49
        or training_summary.get("episodes_completed") != 300
        or not training_summary.get("all_completed")
        or training_summary.get("failed")
    ):
        raise ValueError("R278 training did not complete the frozen pilot")
    checkpoint_sha256 = sha256_file(checkpoint_path)
    if checkpoint_sha256 != training_summary.get("checkpoint_sha256"):
        raise ValueError("checkpoint hash differs from training summary")
    if sha256_file(contract_path) != training_summary.get(
        "controller_contract_sha256"
    ):
        raise ValueError("controller contract hash differs from training summary")

    sources = {
        name: {
            "path": str(path),
            "sha256": sha256_file(path),
        }
        for name, path in _source_paths().items()
    }
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "phase": "viewed-development-pilot",
        "repository_head": _git_head(),
        "candidate_trace_count_at_freeze": 0,
        "development_bank": {
            "path": str(FORMAL_BANK_PATH),
            "sha256": bank_sha256,
            "scenario_count": bank["scenario_count"],
            "role": "viewed_development_only",
        },
        "r275_baseline": {
            "controller": BASELINE,
            "provenance_path": str(R275_PROVENANCE_PATH),
            "provenance_sha256": R275_PROVENANCE_SHA256,
            "trace_hashes": baseline_hashes,
        },
        "training": {
            "controller_contract_path": str(contract_path),
            "controller_contract_sha256": sha256_file(contract_path),
            "training_summary_path": str(summary_path),
            "training_summary_sha256": sha256_file(summary_path),
            "checkpoint_path": str(checkpoint_path),
            "checkpoint_sha256": checkpoint_sha256,
        },
        "execution": {
            "environment_seed": ENV_SEED,
            "steps": STEPS,
            "final_window_steps": FINAL_WINDOW_STEPS,
            "fast_window_steps": FAST_WINDOW_STEPS,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "shard_count": SHARD_COUNT,
        },
        "gate": {
            "primary_endpoints": list(PRIMARY_ENDPOINTS),
            "primary_material_improvement_percent": -2.0,
            "primary_ci_upper_below_percent": 0.0,
            "fast_mean_no_harm_percent": 5.0,
            "slow_mean_no_harm_percent": 2.0,
            "tail_cvar90_no_harm_percent": TAIL_THRESHOLDS,
            "storage_relative_no_harm_percent": 5.0,
        },
        "packages": {
            "python": sys.version,
            "andes": importlib.metadata.version("andes"),
            "numpy": importlib.metadata.version("numpy"),
            "torch": importlib.metadata.version("torch"),
        },
        "sources": sources,
    }
    digest = _write_new_canonical(manifest_path, manifest)
    print(f"[sealed] {manifest_path} sha256={digest}", flush=True)


def _verify_seal(
    manifest_path: Path,
    expected_sha256: str,
) -> dict[str, Any]:
    manifest = _load_object(manifest_path, expected_sha256)
    if (
        manifest.get("round") != ROUND_ID
        or manifest.get("phase") != "viewed-development-pilot"
        or manifest.get("candidate_trace_count_at_freeze") != 0
    ):
        raise ValueError("R278 pilot seal identity mismatch")
    if manifest["development_bank"]["sha256"] != FORMAL_BANK_SHA256:
        raise ValueError("R278 pilot bank mismatch")
    for name, entry in manifest["sources"].items():
        if sha256_file(Path(entry["path"])) != entry["sha256"]:
            raise ValueError(f"sealed source drift: {name}")
    training = manifest["training"]
    for key in (
        "controller_contract",
        "training_summary",
        "checkpoint",
    ):
        if sha256_file(Path(training[f"{key}_path"])) != training[f"{key}_sha256"]:
            raise ValueError(f"sealed training artifact drift: {key}")
    for path_text, expected in manifest["r275_baseline"]["trace_hashes"].items():
        if sha256_file(ROOT / path_text) != expected:
            raise ValueError(f"sealed R275 baseline drift: {path_text}")
    return manifest


def _validate_candidate(
    path: Path,
    *,
    scenario: dict[str, Any],
    seal_sha256: str,
    checkpoint_sha256: str,
) -> dict[str, Any]:
    record = _load_object(path)
    expected = {
        "round": ROUND_ID,
        "phase": "viewed-development-pilot",
        "controller": CANDIDATE,
        "scenario": scenario["name"],
        "delta_u": scenario["delta_u"],
        "formal_bank_sha256": FORMAL_BANK_SHA256,
        "pilot_seal_sha256": seal_sha256,
        "checkpoint_sha256": checkpoint_sha256,
        "provenance_valid": True,
        "seed": ENV_SEED,
        "requested_steps": STEPS,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"R278 candidate mismatch in {path}: {key}")
    return record


def evaluate(
    *,
    manifest_path: Path,
    expected_sha256: str,
    out_dir: Path,
    shard_index: int,
    shard_count: int,
    resume: bool,
) -> None:
    manifest = _verify_seal(manifest_path, expected_sha256)
    if shard_count != SHARD_COUNT or shard_index not in range(SHARD_COUNT):
        raise ValueError("R278 pilot execution is frozen to four shards, 0..3")
    if shard_count != manifest["execution"]["shard_count"]:
        raise ValueError("shard count differs from the R278 pilot seal")
    bank, _ = load_scenario_bank(
        Path(manifest["development_bank"]["path"]),
        expected_sha256=manifest["development_bank"]["sha256"],
    )
    assigned = [
        (index, scenario)
        for index, scenario in enumerate(bank["scenarios"])
        if index % shard_count == shard_index
    ]
    checkpoint = Path(manifest["training"]["checkpoint_path"])
    checkpoint_sha256 = manifest["training"]["checkpoint_sha256"]
    for local_index, (bank_index, scenario) in enumerate(assigned, start=1):
        path = _candidate_path(out_dir, scenario["name"])
        if path.exists():
            if not resume:
                raise FileExistsError(f"pilot trace exists: {path}")
            _validate_candidate(
                path,
                scenario=scenario,
                seal_sha256=expected_sha256,
                checkpoint_sha256=checkpoint_sha256,
            )
            print(f"[resume shard={shard_index}] {path.name}", flush=True)
            continue
        print(
            f"[pilot shard={shard_index} {local_index:02d}/{len(assigned):02d}] "
            f"bank_index={bank_index:02d} {scenario['name']}",
            flush=True,
        )
        record = run_icems_policy_scenario(
            checkpoint,
            scenario["name"],
            scenario["delta_u"],
            seed=ENV_SEED,
            steps=STEPS,
        )
        record.update(
            {
                "round": ROUND_ID,
                "phase": "viewed-development-pilot",
                "location": scenario["location"],
                "sign": scenario["sign"],
                "severity": scenario["severity"],
                "formal_bank_sha256": FORMAL_BANK_SHA256,
                "pilot_seal_sha256": expected_sha256,
                "checkpoint_sha256": checkpoint_sha256,
                "provenance_valid": True,
                "execution_shard_index": shard_index,
                "execution_shard_count": shard_count,
            }
        )
        digest = _write_new_canonical(path, record)
        print(
            f"[saved] {path.name} {record['n_steps']}/{STEPS} "
            f"completed={record['completed']} sha256={digest}",
            flush=True,
        )


def _controller_summary(
    records: list[dict[str, Any]],
    rows: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    means = {
        endpoint: (
            float(np.mean([row[endpoint] for _, row in rows]))
            if rows
            else None
        )
        for endpoint in CONTINUOUS_ENDPOINTS
    }
    tails = {
        endpoint: (
            empirical_upper_tail(
                {scenario: float(row[endpoint]) for scenario, row in rows}
            )
            if rows
            else None
        )
        for endpoint in TAIL_THRESHOLDS
    }
    violations = sum(
        len(step.get("bess_constraint_violations", []))
        for record in records
        for step in record.get("traces", [])
    )
    saturation_reasons = sum(
        bool(reasons)
        for record in records
        for step in record.get("traces", [])
        for reasons in step.get("bess_saturation_reasons", [])
    )
    commands = [
        abs(float(value))
        for record in records
        for step in record.get("traces", [])
        for value in step.get("bess_commanded_power_system_pu", [])
    ]
    actual = [
        abs(float(value))
        for record in records
        for step in record.get("traces", [])
        for value in step.get("bess_actual_power_system_pu", [])
    ]
    soc = [
        float(value)
        for record in records
        for step in record.get("traces", [])
        for value in step.get("bess_soc", [])
    ]
    return {
        "complete_count": sum(bool(record.get("completed")) for record in records),
        "failure_count": sum(bool(record.get("tds_failed")) for record in records),
        "paired_endpoint_count": len(rows),
        "constraint_violation_count": violations,
        "saturation_reason_count": saturation_reasons,
        "means": means,
        "tails": tails,
        "max_abs_commanded_power_system_pu": max(commands, default=None),
        "max_abs_actual_power_system_pu": max(actual, default=None),
        "min_soc": min(soc, default=None),
        "max_soc": max(soc, default=None),
    }


def _storage_audit(
    summaries: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    baseline = summaries[BASELINE]
    candidate = summaries[CANDIDATE]
    effects = {
        endpoint: _relative_percent(
            candidate["means"][endpoint],
            baseline["means"][endpoint],
        )
        for endpoint in STORAGE_RELATIVE_ENDPOINTS
    }
    checks = {
        "zero_constraint_violations": (
            baseline["constraint_violation_count"] == 0
            and candidate["constraint_violation_count"] == 0
        ),
        "zero_saturation_reasons": (
            baseline["saturation_reason_count"] == 0
            and candidate["saturation_reason_count"] == 0
        ),
        "command_within_contract": (
            candidate["max_abs_commanded_power_system_pu"] <= 0.36 + 1e-12
        ),
        "actual_within_contract": (
            candidate["max_abs_actual_power_system_pu"] <= 0.36 + 1e-12
        ),
        "soc_within_contract": (
            candidate["min_soc"] >= 0.20 - 1e-9
            and candidate["max_soc"] <= 0.80 + 1e-9
        ),
        "relative_action_energy_no_worse_5pct": all(
            value <= 5.0 for value in effects.values()
        ),
    }
    return {"checks": checks, "relative_effects_percent": effects}, all(
        checks.values()
    )


def _summary_markdown(summary: dict[str, Any]) -> str:
    decision = summary["decision"]
    lines = [
        "# R278 single-seed ICEMS residual pilot",
        "",
        f"**Classification:** `{decision['classification']}`",
        "",
        decision["reason"],
        "",
        "> Development evidence only: all 24 disturbances were viewed before R278.",
        "",
        "## Registered effects",
        "",
        "| Endpoint | Mean effect (%) | 95% interval (%) |",
        "|---|---:|---:|",
    ]
    contrast = summary["paired_bootstrap"]["contrasts"][
        "candidate_minus_baseline"
    ]
    for endpoint in (
        *PRIMARY_ENDPOINTS,
        *FAST_GUARD_ENDPOINTS,
        *SLOW_GUARD_ENDPOINTS,
    ):
        effect = contrast["endpoints"][endpoint]["ratio_of_means_percent"]
        interval = effect["percentile_95_interval"]
        lines.append(
            f"| `{endpoint}` | {effect['point']:.6g} | "
            f"[{interval[0]:.6g}, {interval[1]:.6g}] |"
        )
    lines.extend(["", "## Gates", ""])
    for name, passed in decision["guards"].items():
        lines.append(f"- `{name}`: {passed}")
    lines.append("")
    return "\n".join(lines)


def analyse(
    *,
    manifest_path: Path,
    expected_sha256: str,
    out_dir: Path,
) -> None:
    manifest = _verify_seal(manifest_path, expected_sha256)
    bank, _ = load_scenario_bank(
        Path(manifest["development_bank"]["path"]),
        expected_sha256=manifest["development_bank"]["sha256"],
    )
    records = {BASELINE: [], CANDIDATE: []}
    grid: dict[str, dict[str, dict[str, Any]]] = {}
    action_audits: dict[str, dict[str, bool]] = {}
    trace_hashes: dict[str, str] = {}
    checkpoint_sha256 = manifest["training"]["checkpoint_sha256"]

    for scenario in bank["scenarios"]:
        name = scenario["name"]
        baseline_path = _baseline_path(name)
        baseline_relative = str(baseline_path.relative_to(ROOT)).replace("\\", "/")
        baseline = _validate_baseline(
            baseline_path,
            scenario=scenario,
            expected_sha256=manifest["r275_baseline"]["trace_hashes"][
                baseline_relative
            ],
        )
        candidate_path = _candidate_path(out_dir, name)
        if not candidate_path.exists():
            raise FileNotFoundError(f"missing R278 pilot trace: {candidate_path}")
        candidate = _validate_candidate(
            candidate_path,
            scenario=scenario,
            seal_sha256=expected_sha256,
            checkpoint_sha256=checkpoint_sha256,
        )
        records[BASELINE].append(baseline)
        records[CANDIDATE].append(candidate)
        trace_hashes[baseline_relative] = sha256_file(baseline_path)
        trace_hashes[
            str(candidate_path.resolve().relative_to(ROOT)).replace("\\", "/")
        ] = sha256_file(candidate_path)
        grid[name] = {}
        if baseline["completed"] and candidate["completed"]:
            grid[name][BASELINE] = summarise_fast_md_trace(
                baseline,
                final_window_steps=FINAL_WINDOW_STEPS,
                fast_window_steps=FAST_WINDOW_STEPS,
            )
            candidate_summary = summarise_icems_policy_trace(
                candidate,
                final_window_steps=FINAL_WINDOW_STEPS,
                fast_window_steps=FAST_WINDOW_STEPS,
            )
            grid[name][CANDIDATE] = candidate_summary
            action_audits[name] = audit_icems_policy_action(candidate_summary)

    paired_names = [
        scenario["name"]
        for scenario in bank["scenarios"]
        if set(grid[scenario["name"]]) == {BASELINE, CANDIDATE}
    ]
    rows = {
        controller: [(name, grid[name][controller]) for name in paired_names]
        for controller in (BASELINE, CANDIDATE)
    }
    controller_summaries = {
        controller: _controller_summary(records[controller], rows[controller])
        for controller in (BASELINE, CANDIDATE)
    }
    paired = {
        "available": False,
        "paired_scenarios": [],
        "contrasts": {},
    }
    primary_contrast = None
    if paired_names:
        bootstrap_input = {
            controller: {
                endpoint: [
                    grid[name][controller][endpoint] for name in paired_names
                ]
                for endpoint in CONTINUOUS_ENDPOINTS
            }
            for controller in (BASELINE, CANDIDATE)
        }
        paired = paired_bootstrap_contrasts(
            bootstrap_input,
            contrasts=(("candidate_minus_baseline", CANDIDATE, BASELINE),),
            seed=BOOTSTRAP_SEED,
            n_resamples=BOOTSTRAP_RESAMPLES,
        )
        paired["available"] = True
        paired["paired_scenarios"] = paired_names
        primary_contrast = paired["contrasts"]["candidate_minus_baseline"]

    action_guard_pass = (
        len(action_audits) == bank["scenario_count"]
        and all(all(audit.values()) for audit in action_audits.values())
    )
    storage_audit, storage_guard_pass = _storage_audit(controller_summaries)
    tail_effects = {}
    if paired_names:
        for endpoint, threshold in TAIL_THRESHOLDS.items():
            baseline_tail = controller_summaries[BASELINE]["tails"][endpoint]
            candidate_tail = controller_summaries[CANDIDATE]["tails"][endpoint]
            tail_effects[endpoint] = {
                "effect_percent": _relative_percent(
                    candidate_tail["cvar_upper_tail"],
                    baseline_tail["cvar_upper_tail"],
                ),
                "threshold_percent": threshold,
                "baseline": baseline_tail,
                "candidate": candidate_tail,
            }
    tail_guard_pass = bool(tail_effects) and all(
        row["effect_percent"] <= row["threshold_percent"]
        for row in tail_effects.values()
    )
    complete_pairs = (
        len(paired_names) == bank["scenario_count"]
        and controller_summaries[BASELINE]["complete_count"]
        == bank["scenario_count"]
        and controller_summaries[CANDIDATE]["complete_count"]
        == bank["scenario_count"]
        and controller_summaries[CANDIDATE]["failure_count"] == 0
    )
    decision = classify_icems_pilot(
        primary_contrast=primary_contrast,
        provenance_valid=True,
        complete_pairs=complete_pairs,
        action_guard_pass=action_guard_pass,
        storage_guard_pass=storage_guard_pass,
        tail_guard_pass=tail_guard_pass,
    )
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "experiment": "r278_icems_residual_pilot",
        "evidence_role": "viewed_development_only",
        "decision": decision,
        "development_bank": manifest["development_bank"],
        "training": manifest["training"],
        "controllers": controller_summaries,
        "completion_pairing": paired_binary_outcome_table(
            [record["completed"] for record in records[CANDIDATE]],
            [record["completed"] for record in records[BASELINE]],
        ),
        "paired_bootstrap": paired,
        "tail_effects": tail_effects,
        "storage_audit": storage_audit,
        "action_guard_pass": action_guard_pass,
        "action_audits": action_audits,
        "pilot_seal": {"path": str(manifest_path), "sha256": expected_sha256},
        "trace_hashes": dict(sorted(trace_hashes.items())),
    }
    summary_path = out_dir / "icems_residual_pilot_summary.json"
    summary_digest = _write_new_canonical(summary_path, summary)
    markdown_path = out_dir / "icems_residual_pilot_summary.md"
    if markdown_path.exists():
        raise FileExistsError(f"refusing to overwrite {markdown_path}")
    markdown_path.write_text(_summary_markdown(summary), encoding="utf-8")
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "repository_head": _git_head(),
        "pilot_manifest": {
            "path": str(manifest_path),
            "sha256": expected_sha256,
            "payload": manifest,
        },
        "summary": {"path": str(summary_path), "sha256": summary_digest},
        "trace_hashes": dict(sorted(trace_hashes.items())),
        "packages": manifest["packages"],
        "sources": manifest["sources"],
        "analysis_command": " ".join(sys.argv),
    }
    provenance_digest = _write_new_canonical(
        out_dir / "provenance.json",
        provenance,
    )
    print(
        f"[analysed] classification={decision['classification']} "
        f"summary_sha256={summary_digest} provenance_sha256={provenance_digest}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    seal = subparsers.add_parser("prepare-seal")
    seal.add_argument("--manifest", type=Path, required=True)
    seal.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    seal.add_argument("--train-dir", type=Path, default=DEFAULT_TRAIN_DIR)

    run = subparsers.add_parser("evaluate")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--expected-manifest-sha256", required=True)
    run.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    run.add_argument("--shard-index", type=int, required=True)
    run.add_argument("--shard-count", type=int, required=True)
    run.add_argument("--resume", action="store_true")

    analysis = subparsers.add_parser("analyse")
    analysis.add_argument("--manifest", type=Path, required=True)
    analysis.add_argument("--expected-manifest-sha256", required=True)
    analysis.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    if args.command == "prepare-seal":
        prepare_seal(
            manifest_path=args.manifest,
            out_dir=args.out_dir,
            train_dir=args.train_dir,
        )
    elif args.command == "evaluate":
        evaluate(
            manifest_path=args.manifest,
            expected_sha256=args.expected_manifest_sha256,
            out_dir=args.out_dir,
            shard_index=args.shard_index,
            shard_count=args.shard_count,
            resume=args.resume,
        )
    else:
        analyse(
            manifest_path=args.manifest,
            expected_sha256=args.expected_manifest_sha256,
            out_dir=args.out_dir,
        )


if __name__ == "__main__":
    main()
