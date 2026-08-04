#!/usr/bin/env python3
"""Seal and run the R293 selected classical controller on a viewed guard bank.

This full-horizon guard reuses only hash-verified R292 q0 records and runs 24
new selected-controller trajectories.  It is development evidence and cannot
be used as the R293 formal comparison bank.
"""

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

from andes_rl_kundur.control.classical_edge_residual import (  # noqa: E402
    ClassicalEdgeController,
    classical_edge_candidates,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    empirical_upper_tail,
    sha256_bytes,
    sha256_file,
)
from andes_rl_kundur.evaluation.vector_residual import (  # noqa: E402
    audit_vector_action,
    run_vector_controller_scenario,
    summarise_vector_trace,
)

ROUND_ID = "R293"
QUESTION_ID = "Q-0050"
ENV_SEED = 42
STEPS = 300
FAST_STEPS = 15
FINAL_WINDOW_STEPS = 50
SHARD_COUNT = 3
DEV_SUMMARY = ROOT / "results/r293_classical_development/classical_development_summary.json"
DEV_PROVENANCE = ROOT / "results/r293_classical_development/provenance.json"
DEV_SEAL = ROOT / "memory/rounds/R293/classical_development_seal.json"
GUARD_BANK = ROOT / "results/r292_fresh_bank_v3/formal_bank.json"
R292_FORMAL_SUMMARY = ROOT / "results/r292_formal_evaluation_v3/formal_summary.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R293/classical_guard_seal.json"
DEFAULT_OUT = ROOT / "results/r293_classical_guard"
PRIMARY_AND_FAST = (
    "normalized_sync_loss_hz2",
    "fast_inter_area_iae_hz_s",
    "max_abs_rocof_hz_s",
    "worst_bus_peak_abs_hz",
)
ALL_ENDPOINTS = (
    *PRIMARY_AND_FAST,
    "first_3s_common_iae_hz_s",
    "vsg_mean_iae_hz_s",
    "final_window_common_abs_mean_hz",
)


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


def _sources() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R293/plan.md",
        "script": Path(__file__).resolve(),
        "classical_controller": ROOT
        / "src/andes_rl_kundur/control/classical_edge_residual.py",
        "vector_runner": ROOT / "src/andes_rl_kundur/evaluation/vector_residual.py",
        "development_summary": DEV_SUMMARY,
        "development_provenance": DEV_PROVENANCE,
        "development_seal": DEV_SEAL,
        "guard_bank": GUARD_BANK,
        "r292_formal_summary": R292_FORMAL_SUMMARY,
    }


def _q0_hashes(formal_summary: dict[str, Any]) -> dict[str, str]:
    rows = {
        path: digest
        for path, digest in formal_summary["trace_hashes"].items()
        if path.endswith("__q0.json")
    }
    if len(rows) != 24:
        raise ValueError(f"expected 24 R292 q0 guard records, found {len(rows)}")
    return dict(sorted(rows.items()))


def _trace_path(out_dir: Path, scenario: str, controller: str) -> Path:
    return out_dir / "traces" / f"{scenario}__{controller}.json"


def prepare(manifest_path: Path, out_dir: Path) -> None:
    if manifest_path.exists():
        raise FileExistsError(f"guard seal already exists: {manifest_path}")
    if (out_dir / "traces").exists() and any((out_dir / "traces").glob("*.json")):
        raise ValueError("guard seal must precede every guard trace")
    development = _load_json(DEV_SUMMARY)
    if development.get("classification") != "CLASSICAL-DEVELOPMENT-CANDIDATE":
        raise ValueError("classical development did not select a credible candidate")
    selected = development.get("selected")
    contracts = {row.name: row for row in classical_edge_candidates()}
    if not isinstance(selected, dict) or selected.get("candidate") not in contracts:
        raise ValueError("selected classical contract drift")
    bank = _load_json(GUARD_BANK)
    if bank.get("scenario_count") != 24:
        raise ValueError("guard bank must contain 24 cases")
    r292 = _load_json(R292_FORMAL_SUMMARY)
    q0_hashes = _q0_hashes(r292)
    for path_text, digest in q0_hashes.items():
        if sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"R292 q0 trace drift: {path_text}")
    source_entries = {
        name: {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(path),
        }
        for name, path in _sources().items()
    }
    contract = contracts[selected["candidate"]]
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "viewed-bank-classical-edge-full-guard",
        "repository_head": _git_head(),
        "selected_classical_contract": contract.telemetry(),
        "development_selection": selected,
        "guard_bank": {
            "path": str(GUARD_BANK.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(GUARD_BANK),
            "scenario_count": 24,
            "role": "viewed_guard_only",
        },
        "q0_guard_records": {
            "source_summary_sha256": sha256_file(R292_FORMAL_SUMMARY),
            "trace_hashes": q0_hashes,
            "role": "hash_verified_reuse_no_rerun",
        },
        "execution": {
            "steps": STEPS,
            "seed": ENV_SEED,
            "trajectory_budget": 24,
            "shard_count": SHARD_COUNT,
            "overwrite": False,
        },
        "gate": {
            "mean_and_cvar90_no_harm_percent": 5.0,
            "endpoints": list(PRIMARY_AND_FAST),
            "absolute_storage": {
                "command_and_actual_abs_system_pu_max": 0.36,
                "soc_range": [0.2, 0.8],
                "zero_constraint_violations": True,
                "zero_saturation_reasons": True,
            },
            "all_action_audits": True,
            "nontrivial_edge_total_variation_min": 1e-6,
        },
        "sources": source_entries,
        "trace_count_at_freeze": 0,
    }
    digest = _write_new(manifest_path, payload)
    print(f"[sealed] {manifest_path} sha256={digest}", flush=True)


def _verify(path: Path, expected: str) -> dict[str, Any]:
    manifest = _load_json(path, expected)
    if manifest.get("round") != ROUND_ID or manifest.get("phase") != "viewed-bank-classical-edge-full-guard":
        raise ValueError("not an R293 classical guard seal")
    for entry in manifest["sources"].values():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError(f"sealed source drift: {entry['path']}")
    return manifest


def _validate_trace(
    path: Path,
    *,
    scenario: dict[str, Any],
    controller: str,
    seal_sha256: str,
) -> dict[str, Any]:
    record = _load_json(path)
    expected = {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "viewed-bank-classical-edge-full-guard",
        "scenario": scenario["name"],
        "controller": controller,
        "requested_steps": STEPS,
        "n_steps": STEPS,
        "completed": True,
        "tds_failed": False,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"guard trace mismatch in {path}: {key}")
    if record["evidence_hashes"].get("r293_guard_seal") != seal_sha256:
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
    if shard_count != SHARD_COUNT or not 0 <= shard_index < shard_count:
        raise ValueError("shard arguments differ from the guard seal")
    bank = _load_json(GUARD_BANK, manifest["guard_bank"]["sha256"])
    contract = next(
        row
        for row in classical_edge_candidates()
        if row.name == manifest["selected_classical_contract"]["name"]
    )
    selected = [
        scenario
        for index, scenario in enumerate(bank["scenarios"])
        if index % shard_count == shard_index
    ]
    for ordinal, scenario in enumerate(selected, start=1):
        path = _trace_path(out_dir, scenario["name"], contract.name)
        if path.exists():
            _validate_trace(
                path,
                scenario=scenario,
                controller=contract.name,
                seal_sha256=expected,
            )
            print(f"[resume {ordinal:02d}/{len(selected):02d}] {path.name}", flush=True)
            continue
        record = run_vector_controller_scenario(
            ClassicalEdgeController(contract),
            controller_name=contract.name,
            controller_config={"classical_edge": contract.telemetry()},
            scenario_name=scenario["name"],
            delta_u=scenario["delta_u"],
            seed=ENV_SEED,
            steps=STEPS,
            phase="viewed-bank-classical-edge-full-guard",
            evidence_hashes={
                "r293_guard_seal": expected,
                "guard_bank": manifest["guard_bank"]["sha256"],
            },
        )
        record.update(
            {
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "experiment": "r293_classical_edge_guard",
                "location": scenario["location"],
                "sign": scenario["sign"],
                "severity": scenario["severity"],
                "execution_shard_index": shard_index,
                "execution_shard_count": shard_count,
            }
        )
        digest = _write_new(path, record)
        print(
            f"[guard {ordinal:02d}/{len(selected):02d}] {path.name} "
            f"completed={record['completed']} sha256={digest}",
            flush=True,
        )
        if not record["completed"]:
            raise RuntimeError(f"R293 classical guard failed: {path}")


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


def _relative(left: float, right: float) -> float:
    if right <= 0.0:
        raise ValueError("guard reference must be positive")
    return 100.0 * (left / right - 1.0)


def analyse(manifest_path: Path, expected: str, out_dir: Path) -> None:
    manifest = _verify(manifest_path, expected)
    bank = _load_json(GUARD_BANK, manifest["guard_bank"]["sha256"])
    scenarios = {row["name"]: row for row in bank["scenarios"]}
    controller = manifest["selected_classical_contract"]["name"]
    q0_records: dict[str, dict[str, Any]] = {}
    for path_text, digest in manifest["q0_guard_records"]["trace_hashes"].items():
        record = _load_json(ROOT / path_text, digest)
        q0_records[record["scenario"]] = record
    candidate_records: dict[str, dict[str, Any]] = {}
    trace_hashes: dict[str, str] = {}
    action_audits: dict[str, Any] = {}
    for name, scenario in scenarios.items():
        path = _trace_path(out_dir, name, controller)
        record = _validate_trace(
            path,
            scenario=scenario,
            controller=controller,
            seal_sha256=expected,
        )
        candidate_records[name] = record
        trace_hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = sha256_file(path)

    metrics = {
        "q0": {name: _endpoint_row(record) for name, record in q0_records.items()},
        "classical": {
            name: _endpoint_row(record) for name, record in candidate_records.items()
        },
    }
    for name, row in metrics["classical"].items():
        action_audits[name] = audit_vector_action(row)
    summaries: dict[str, Any] = {}
    for arm, rows in metrics.items():
        summaries[arm] = {
            "means": {
                endpoint: float(np.mean([row[endpoint] for row in rows.values()]))
                for endpoint in ALL_ENDPOINTS
            },
            "cvar90": {
                endpoint: empirical_upper_tail(
                    {name: float(row[endpoint]) for name, row in rows.items()}
                )
                for endpoint in ALL_ENDPOINTS
            },
            "storage": _aggregate_storage(
                list(q0_records.values()) if arm == "q0" else list(candidate_records.values())
            ),
        }
    mean_effects = {
        endpoint: _relative(
            summaries["classical"]["means"][endpoint],
            summaries["q0"]["means"][endpoint],
        )
        for endpoint in ALL_ENDPOINTS
    }
    cvar_effects = {
        endpoint: _relative(
            summaries["classical"]["cvar90"][endpoint]["cvar_upper_tail"],
            summaries["q0"]["cvar90"][endpoint]["cvar_upper_tail"],
        )
        for endpoint in ALL_ENDPOINTS
    }
    storage = summaries["classical"]["storage"]
    storage_pass = (
        storage["constraint_violation_count"] == 0
        and storage["saturation_reason_count"] == 0
        and storage["max_abs_commanded_power_system_pu"] <= 0.36 + 1e-12
        and storage["max_abs_actual_power_system_pu"] <= 0.36 + 1e-12
        and storage["min_soc"] >= 0.20 - 1e-9
        and storage["max_soc"] <= 0.80 + 1e-9
    )
    action_pass = len(action_audits) == 24 and all(
        all(row.values()) for row in action_audits.values()
    )
    nontrivial = sum(
        metrics["classical"][name]["r292_edge_total_variation"]
        for name in scenarios
    ) > 1e-6
    gate = {
        "complete_24": len(candidate_records) == 24,
        "action_all_rows": action_pass,
        "absolute_storage": storage_pass,
        "nontrivial_action": nontrivial,
        "registered_mean_no_harm": all(
            mean_effects[endpoint] <= 5.0 for endpoint in PRIMARY_AND_FAST
        ),
        "registered_cvar90_no_harm": all(
            cvar_effects[endpoint] <= 5.0 for endpoint in PRIMARY_AND_FAST
        ),
        "provenance_hashes_verified": True,
    }
    classification = "CLASSICAL-GUARD-PASS" if all(gate.values()) else "CLASSICAL-FAMILY-NO-GO"
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "viewed-bank-classical-edge-full-guard",
        "guard_seal_sha256": expected,
        "guard_bank_sha256": manifest["guard_bank"]["sha256"],
        "selected_classical_contract": manifest["selected_classical_contract"],
        "classification": classification,
        "gate": gate,
        "mean_effect_percent_vs_q0": mean_effects,
        "cvar90_effect_percent_vs_q0": cvar_effects,
        "arm_summaries": summaries,
        "action_audits": action_audits,
        "trace_hashes": dict(sorted(trace_hashes.items())),
    }
    summary_digest = _write_new(out_dir / "classical_guard_summary.json", summary)
    provenance_digest = _write_new(
        out_dir / "provenance.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "repository_head": _git_head(),
            "guard_seal_sha256": expected,
            "summary_sha256": summary_digest,
            "trace_hashes": dict(sorted(trace_hashes.items())),
            "source_sha256": {
                name: entry["sha256"] for name, entry in manifest["sources"].items()
            },
            "performance_role": "viewed_guard_only",
            "paper_files_modified": False,
        },
    )
    print(
        f"[analysed] classification={classification} summary_sha256={summary_digest} "
        f"provenance_sha256={provenance_digest}",
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
