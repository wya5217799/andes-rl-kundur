#!/usr/bin/env python3
# ruff: noqa: E402
"""Freeze, run, and analyse the R279 full-horizon causal safety guard."""

from __future__ import annotations

import argparse
import importlib.metadata
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from run_r279_causal_development import (  # noqa: E402
    BANK_PATH,
    ENV_SEED,
    _git_head,
    _load_json,
    _r275_baseline_hashes,
    _write_new,
    _write_new_text,
)

from andes_rl_kundur.control.causal_area_feedback import (  # noqa: E402
    CausalAreaFeedbackController,
    r279_causal_contracts,
)
from andes_rl_kundur.evaluation.fast_md_authority import (  # noqa: E402
    summarise_fast_md_trace,
)
from andes_rl_kundur.evaluation.icems_residual import (  # noqa: E402
    audit_icems_policy_action,
    summarise_icems_policy_trace,
)
from andes_rl_kundur.evaluation.r279_controllers import (  # noqa: E402
    run_r279_controller_scenario,
)
from andes_rl_kundur.evaluation.sealed_bank import sha256_file  # noqa: E402

ROUND_ID = "R279"
STEPS = 300
SHARD_COUNT = 3
DEV_SUMMARY = ROOT / "results/r279_causal_development/causal_development_summary.json"
DEV_PROVENANCE = ROOT / "results/r279_causal_development/provenance.json"
DEV_SEAL = ROOT / "memory/rounds/R279/causal_development_seal.json"
R275_SUMMARY = ROOT / "results/r275_fast_md_authority/fast_md_authority_summary.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R279/causal_guard_seal.json"
DEFAULT_OUT = ROOT / "results/r279_causal_guard"


def _trace_path(out_dir: Path, scenario: str, candidate: str) -> Path:
    return out_dir / "guard_traces" / f"{scenario}__{candidate}.json"


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R279/plan.md",
        "guard_script": Path(__file__).resolve(),
        "development_script": ROOT / "scripts/run_r279_causal_development.py",
        "causal_controller": ROOT
        / "src/andes_rl_kundur/control/causal_area_feedback.py",
        "generic_runner": ROOT
        / "src/andes_rl_kundur/evaluation/r279_controllers.py",
        "policy_evaluation": ROOT
        / "src/andes_rl_kundur/evaluation/icems_residual.py",
        "development_summary": DEV_SUMMARY,
        "development_provenance": DEV_PROVENANCE,
        "development_bank": BANK_PATH,
        "r275_summary": R275_SUMMARY,
    }


def prepare(
    manifest_path: Path,
    out_dir: Path,
    expected_development_summary_sha256: str,
) -> None:
    trace_dir = out_dir / "guard_traces"
    if trace_dir.exists() and any(trace_dir.glob("*.json")):
        raise ValueError("guard seal must precede every full-horizon trace")
    summary = _load_json(DEV_SUMMARY, expected_development_summary_sha256)
    if not summary["completion"]["all_complete"]:
        raise ValueError("causal development did not complete 216 trajectories")
    selected = summary["selection"]["selected"]
    contract = next(
        row for row in r279_causal_contracts() if row.name == selected["candidate"]
    )
    if contract.k_frequency != selected["k_frequency"] or contract.k_rocof != selected["k_rocof"]:
        raise ValueError("selected causal contract drift")
    development_seal_sha256 = summary["causal_development_seal_sha256"]
    if sha256_file(DEV_SEAL) != development_seal_sha256:
        raise ValueError("causal development seal drift")
    r275 = _load_json(R275_SUMMARY)
    baseline_hashes = _r275_baseline_hashes(r275)
    for path_text, digest in baseline_hashes.items():
        if sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"R275 baseline drift: {path_text}")
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
        "question": "Q-0041",
        "phase": "viewed-bank-causal-full-guard",
        "repository_head": _git_head(),
        "selected_causal_contract": contract.telemetry(),
        "development_summary": {
            "path": str(DEV_SUMMARY.relative_to(ROOT)).replace("\\", "/"),
            "sha256": expected_development_summary_sha256,
        },
        "development_seal_sha256": development_seal_sha256,
        "development_bank": {
            "path": str(BANK_PATH.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(BANK_PATH),
            "scenario_count": 24,
            "role": "viewed_guard_only",
        },
        "r275_q0_baseline": {
            "summary_sha256": sha256_file(R275_SUMMARY),
            "trace_hashes": baseline_hashes,
        },
        "execution": {
            "steps": STEPS,
            "seed": ENV_SEED,
            "trajectory_budget": 24,
            "shard_count": SHARD_COUNT,
            "overwrite": False,
        },
        "guards": {
            "fast_mean_no_harm_percent": 5.0,
            "slow_mean_no_harm_percent": 2.0,
            "storage_relative_no_harm_percent": 5.0,
            "command_and_actual_abs_system_pu_max": 0.36,
            "soc_range": [0.20, 0.80],
            "zero_constraint_violations": True,
            "zero_saturation_reasons": True,
        },
        "sources": sources,
        "packages": {
            package: importlib.metadata.version(package)
            for package in ("andes", "numpy", "torch")
        }
        | {"python": sys.version},
        "candidate_trace_count_at_freeze": 0,
    }
    digest = _write_new(manifest_path, payload)
    print(f"[sealed] {manifest_path} sha256={digest}", flush=True)


def _verify(path: Path, expected: str) -> dict[str, Any]:
    manifest = _load_json(path, expected)
    if manifest.get("round") != ROUND_ID or manifest.get("phase") != "viewed-bank-causal-full-guard":
        raise ValueError("not an R279 causal guard seal")
    for entry in manifest["sources"].values():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError(f"guard source drift: {entry['path']}")
    if sha256_file(BANK_PATH) != manifest["development_bank"]["sha256"]:
        raise ValueError("guard bank drift")
    return manifest


def _validate_existing(
    path: Path,
    scenario: dict[str, Any],
    candidate: str,
    seal_sha256: str,
) -> dict[str, Any]:
    record = _load_json(path)
    expected = {
        "round": ROUND_ID,
        "phase": "viewed-bank-causal-full-guard",
        "controller": candidate,
        "scenario": scenario["name"],
        "requested_steps": STEPS,
        "n_steps": STEPS,
        "completed": True,
        "tds_failed": False,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"guard trace mismatch in {path}: {key}")
    if record["evidence_hashes"].get("causal_guard_seal") != seal_sha256:
        raise ValueError(f"guard trace seal mismatch: {path}")
    return record


def run_shard(
    manifest_path: Path,
    expected: str,
    out_dir: Path,
    shard_index: int,
    shard_count: int,
) -> None:
    manifest = _verify(manifest_path, expected)
    if shard_count != manifest["execution"]["shard_count"] or not 0 <= shard_index < shard_count:
        raise ValueError("guard shard contract drift")
    bank = _load_json(BANK_PATH, manifest["development_bank"]["sha256"])
    telemetry = manifest["selected_causal_contract"]
    contract = next(row for row in r279_causal_contracts() if row.name == telemetry["name"])
    controller = CausalAreaFeedbackController(contract)
    scenarios = [
        row for index, row in enumerate(bank["scenarios"]) if index % shard_count == shard_index
    ]
    for index, scenario in enumerate(scenarios, start=1):
        path = _trace_path(out_dir, scenario["name"], contract.name)
        if path.exists():
            _validate_existing(path, scenario, contract.name, expected)
            print(f"[resume {index:02d}/{len(scenarios):02d}] {path.name}", flush=True)
            continue
        record = run_r279_controller_scenario(
            controller,
            controller_name=contract.name,
            controller_config={"causal_feedback": contract.telemetry()},
            scenario_name=scenario["name"],
            delta_u=scenario["delta_u"],
            seed=ENV_SEED,
            steps=STEPS,
            phase="viewed-bank-causal-full-guard",
            evidence_hashes={
                "causal_guard_seal": expected,
                "development_bank": manifest["development_bank"]["sha256"],
            },
        )
        record.update(
            {
                "location": scenario["location"],
                "sign": scenario["sign"],
                "severity": scenario["severity"],
                "execution_shard_index": shard_index,
                "execution_shard_count": shard_count,
            }
        )
        digest = _write_new(path, record)
        print(f"[guard {index:02d}/{len(scenarios):02d}] {path.name} completed={record['completed']} sha256={digest}", flush=True)
        if not record["completed"]:
            raise RuntimeError(f"causal guard trajectory failed: {path}")


def _relative(candidate: float, baseline: float) -> float:
    if baseline <= 0.0:
        raise ValueError("guard baseline endpoint must be positive")
    return 100.0 * (candidate / baseline - 1.0)


def _storage_values(records: list[dict[str, Any]]) -> dict[str, float | int]:
    steps = [step for record in records for step in record["traces"]]
    command = [abs(float(value)) for step in steps for value in step["bess_commanded_power_system_pu"]]
    actual = [abs(float(value)) for step in steps for value in step["bess_actual_power_system_pu"]]
    soc = [float(value) for step in steps for value in step["bess_soc"]]
    return {
        "constraint_violation_count": sum(len(step["bess_constraint_violations"]) for step in steps),
        "saturation_reason_count": sum(bool(reason) for step in steps for reason in step["bess_saturation_reasons"]),
        "max_abs_commanded_power_system_pu": max(command),
        "max_abs_actual_power_system_pu": max(actual),
        "min_soc": min(soc),
        "max_soc": max(soc),
    }


def analyse(manifest_path: Path, expected: str, out_dir: Path) -> None:
    manifest = _verify(manifest_path, expected)
    bank = _load_json(BANK_PATH, manifest["development_bank"]["sha256"])
    candidate_name = manifest["selected_causal_contract"]["name"]
    baseline_metrics = []
    candidate_metrics = []
    records = []
    action_audits = {}
    trace_hashes = {}
    for scenario in bank["scenarios"]:
        baseline_path_text = next(
            path for path in manifest["r275_q0_baseline"]["trace_hashes"]
            if Path(path).name == f"{scenario['name']}__common_M_pos.json"
        )
        baseline_path = ROOT / baseline_path_text
        baseline = _load_json(
            baseline_path,
            manifest["r275_q0_baseline"]["trace_hashes"][baseline_path_text],
        )
        path = _trace_path(out_dir, scenario["name"], candidate_name)
        candidate = _validate_existing(path, scenario, candidate_name, expected)
        base_summary = summarise_fast_md_trace(
            baseline, final_window_steps=50, fast_window_steps=15
        )
        cand_summary = summarise_icems_policy_trace(
            candidate, final_window_steps=50, fast_window_steps=15
        )
        baseline_metrics.append(base_summary)
        candidate_metrics.append(cand_summary)
        records.append(candidate)
        action_audits[scenario["name"]] = audit_icems_policy_action(cand_summary)
        trace_hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = sha256_file(path)

    endpoints = (
        "normalized_sync_loss_hz2",
        "fast_inter_area_iae_hz_s",
        "max_abs_rocof_hz_s",
        "worst_bus_peak_abs_hz",
        "vsg_mean_iae_hz_s",
        "final_window_common_abs_mean_hz",
        "bess_command_l1_device_s",
        "bess_command_total_variation",
        "bess_charge_energy_mwh_total",
        "bess_discharge_energy_mwh_total",
    )
    effects = {}
    for endpoint in endpoints:
        baseline_mean = float(np.mean([row[endpoint] for row in baseline_metrics]))
        candidate_mean = float(np.mean([row[endpoint] for row in candidate_metrics]))
        effects[endpoint] = {
            "baseline_mean": baseline_mean,
            "candidate_mean": candidate_mean,
            "effect_percent": _relative(candidate_mean, baseline_mean),
        }
    storage = _storage_values(records)
    checks = {
        "complete_24": len(records) == 24 and all(row["completed"] for row in records),
        "action_contract": len(action_audits) == 24 and all(
            all(audit.values()) for audit in action_audits.values()
        ),
        "fast_mean_no_harm_5pct": all(
            effects[name]["effect_percent"] <= 5.0
            for name in ("max_abs_rocof_hz_s", "worst_bus_peak_abs_hz")
        ),
        "slow_mean_no_harm_2pct": all(
            effects[name]["effect_percent"] <= 2.0
            for name in ("vsg_mean_iae_hz_s", "final_window_common_abs_mean_hz")
        ),
        "storage_relative_no_harm_5pct": all(
            effects[name]["effect_percent"] <= 5.0
            for name in (
                "bess_command_l1_device_s",
                "bess_command_total_variation",
                "bess_charge_energy_mwh_total",
                "bess_discharge_energy_mwh_total",
            )
        ),
        "zero_constraint_violations": storage["constraint_violation_count"] == 0,
        "zero_saturation_reasons": storage["saturation_reason_count"] == 0,
        "power_within_contract": storage["max_abs_commanded_power_system_pu"] <= 0.36 + 1e-12
        and storage["max_abs_actual_power_system_pu"] <= 0.36 + 1e-12,
        "soc_within_contract": storage["min_soc"] >= 0.20 - 1e-9
        and storage["max_soc"] <= 0.80 + 1e-9,
    }
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": "Q-0041",
        "phase": "viewed-bank-causal-full-guard",
        "causal_guard_seal_sha256": expected,
        "selected_causal_contract": manifest["selected_causal_contract"],
        "decision": {
            "classification": "CAUSAL-GUARD-PASS" if all(checks.values()) else "CAUSAL-GUARD-FAIL",
            "pass": all(checks.values()),
            "checks": checks,
        },
        "effects_percent_vs_q0": effects,
        "storage_audit": storage,
        "action_audits": action_audits,
        "trace_hashes": dict(sorted(trace_hashes.items())),
    }
    summary_digest = _write_new(out_dir / "causal_guard_summary.json", summary)
    lines = [
        "# R279 causal full-horizon guard",
        "",
        f"**Classification:** `{summary['decision']['classification']}`",
        "",
        f"Selected comparator: `{candidate_name}`.",
        "",
    ] + [f"- `{name}`: {passed}" for name, passed in checks.items()] + [""]
    markdown_digest = _write_new_text(out_dir / "causal_guard_summary.md", "\n".join(lines))
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "repository_head": _git_head(),
        "causal_guard_seal_sha256": expected,
        "summary_sha256": summary_digest,
        "markdown_sha256": markdown_digest,
        "paper_files_modified": False,
    }
    provenance_digest = _write_new(out_dir / "provenance.json", provenance)
    print(
        f"[analysed] classification={summary['decision']['classification']} "
        f"summary_sha256={summary_digest} provenance_sha256={provenance_digest}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--manifest", type=Path, default=DEFAULT_SEAL)
    prepare_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    prepare_parser.add_argument("--expected-development-summary-sha256", required=True)
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
        prepare(
            args.manifest,
            args.out_dir,
            args.expected_development_summary_sha256,
        )
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
