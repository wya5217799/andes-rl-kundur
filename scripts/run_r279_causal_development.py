#!/usr/bin/env python3
# ruff: noqa: E402
"""Seal, run, and analyse the R279 causal-comparator development grid."""

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

from andes_rl_kundur.control.causal_area_feedback import (
    CausalAreaFeedbackController,
    r279_causal_contracts,
)
from andes_rl_kundur.evaluation.fast_md_authority import summarise_fast_md_trace
from andes_rl_kundur.evaluation.icems_residual import (
    audit_icems_policy_action,
    summarise_icems_policy_trace,
)
from andes_rl_kundur.evaluation.r279_controllers import (
    run_r279_controller_scenario,
)
from andes_rl_kundur.evaluation.sealed_bank import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)

ROUND_ID = "R279"
ENV_SEED = 42
STEPS = 15
SHARD_COUNT = 3
BANK_PATH = ROOT / "results/r274_prospective_active_power_authority/formal_bank.json"
R275_SUMMARY = ROOT / "results/r275_fast_md_authority/fast_md_authority_summary.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R279/causal_development_seal.json"
DEFAULT_OUT = ROOT / "results/r279_causal_development"


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


def _write_new_text(path: Path, content: str) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact: {path}")
    data = content.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    digest = sha256_bytes(data)
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return digest


def _load_json(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    actual = sha256_file(path)
    if expected_sha256 is not None and actual != expected_sha256:
        raise ValueError(f"hash mismatch for {path}: expected {expected_sha256}, got {actual}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R279/plan.md",
        "script": Path(__file__).resolve(),
        "launcher": ROOT / "scripts/run_r279_causal_development.sh",
        "causal_controller": ROOT
        / "src/andes_rl_kundur/control/causal_area_feedback.py",
        "generic_runner": ROOT
        / "src/andes_rl_kundur/evaluation/r279_controllers.py",
        "policy_evaluation": ROOT
        / "src/andes_rl_kundur/evaluation/icems_residual.py",
        "residual_environment": ROOT
        / "src/andes_rl_kundur/env/andes/icems_residual_env.py",
        "residual_contract": ROOT
        / "src/andes_rl_kundur/control/area_inertia_residual.py",
        "development_bank": BANK_PATH,
        "r275_summary": R275_SUMMARY,
    }


def _r275_baseline_hashes(summary: dict[str, Any]) -> dict[str, str]:
    result = {
        path: digest
        for path, digest in summary["trace_hashes"].items()
        if path.endswith("__common_M_pos.json")
    }
    if len(result) != 24:
        raise ValueError(f"expected 24 q=0 baseline hashes, found {len(result)}")
    return dict(sorted(result.items()))


def _candidate_path(out_dir: Path, scenario: str, candidate: str) -> Path:
    return out_dir / "development_traces" / f"{scenario}__{candidate}.json"


def prepare_seal(manifest_path: Path, out_dir: Path) -> None:
    trace_dir = out_dir / "development_traces"
    if trace_dir.exists() and any(trace_dir.glob("*.json")):
        raise ValueError("causal development seal must precede all candidate traces")
    bank = _load_json(BANK_PATH)
    if len(bank.get("scenarios", [])) != 24:
        raise ValueError("development bank must contain exactly 24 scenarios")
    summary = _load_json(R275_SUMMARY)
    baseline_hashes = _r275_baseline_hashes(summary)
    for path_text, expected in baseline_hashes.items():
        if sha256_file(ROOT / path_text) != expected:
            raise ValueError(f"R275 baseline drift: {path_text}")
    contracts = [contract.telemetry() for contract in r279_causal_contracts()]
    if len(contracts) != 9 or len({row["name"] for row in contracts}) != 9:
        raise ValueError("causal gain grid must contain nine unique candidates")
    sources = {
        name: {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(path),
        }
        for name, path in _source_paths().items()
    }
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": "Q-0041",
        "phase": "viewed-bank-causal-development",
        "repository_head": _git_head(),
        "development_bank": {
            "path": str(BANK_PATH.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(BANK_PATH),
            "scenario_count": 24,
            "role": "viewed_development_only",
        },
        "r275_q0_baseline": {
            "summary_sha256": sha256_file(R275_SUMMARY),
            "trace_hashes": baseline_hashes,
            "reuse": "first 15 steps only; no baseline rerun",
        },
        "candidates": contracts,
        "selection": {
            "co_primary": [
                "normalized_sync_loss_hz2",
                "fast_inter_area_iae_hz_s",
            ],
            "score": "equal-weight mean candidate/q0 ratio",
            "ordering": [
                "minimum worst-location score",
                "minimum all-bank score",
                "minimum k_frequency^2+k_rocof^2",
                "frozen candidate order",
            ],
            "fast_guard_mean_no_harm_percent": 5.0,
            "effective_nonzero_candidate_is_always_frozen": True,
        },
        "execution": {
            "steps": STEPS,
            "seed": ENV_SEED,
            "trajectory_budget": 216,
            "shard_count": SHARD_COUNT,
            "overwrite": False,
        },
        "packages": {
            package: importlib.metadata.version(package)
            for package in ("andes", "numpy", "torch")
        }
        | {"python": sys.version},
        "sources": sources,
        "candidate_trace_count_at_freeze": 0,
    }
    digest = _write_new(manifest_path, manifest)
    print(f"[sealed] {manifest_path} sha256={digest}", flush=True)


def _verify_manifest(path: Path, expected_sha256: str) -> dict[str, Any]:
    manifest = _load_json(path, expected_sha256)
    if manifest.get("round") != ROUND_ID or manifest.get("phase") != "viewed-bank-causal-development":
        raise ValueError("manifest is not the R279 causal-development seal")
    for entry in manifest["sources"].values():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError(f"sealed source drift: {entry['path']}")
    if sha256_file(BANK_PATH) != manifest["development_bank"]["sha256"]:
        raise ValueError("development bank drift")
    return manifest


def _validate_existing(
    path: Path,
    *,
    scenario: dict[str, Any],
    candidate: dict[str, Any],
    seal_sha256: str,
) -> None:
    record = _load_json(path)
    expected = {
        "round": ROUND_ID,
        "phase": "viewed-bank-causal-development",
        "scenario": scenario["name"],
        "controller": candidate["name"],
        "requested_steps": STEPS,
        "n_steps": STEPS,
        "completed": True,
        "tds_failed": False,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"resume artifact mismatch in {path}: {key}")
    if record["evidence_hashes"].get("causal_development_seal") != seal_sha256:
        raise ValueError(f"resume artifact seal mismatch: {path}")


def run_shard(
    manifest_path: Path,
    expected_sha256: str,
    out_dir: Path,
    shard_index: int,
    shard_count: int,
) -> None:
    manifest = _verify_manifest(manifest_path, expected_sha256)
    if shard_count != manifest["execution"]["shard_count"] or not 0 <= shard_index < shard_count:
        raise ValueError("shard arguments differ from the frozen seal")
    bank = _load_json(BANK_PATH, manifest["development_bank"]["sha256"])
    candidates = manifest["candidates"]
    tasks = [
        (candidate_index, scenario_index, candidate, scenario)
        for candidate_index, candidate in enumerate(candidates)
        for scenario_index, scenario in enumerate(bank["scenarios"])
    ]
    selected = [task for index, task in enumerate(tasks) if index % shard_count == shard_index]
    for ordinal, (_ci, _si, candidate, scenario) in enumerate(selected, start=1):
        path = _candidate_path(out_dir, scenario["name"], candidate["name"])
        if path.exists():
            _validate_existing(
                path,
                scenario=scenario,
                candidate=candidate,
                seal_sha256=expected_sha256,
            )
            print(f"[resume {ordinal:03d}/{len(selected):03d}] {path.name}", flush=True)
            continue
        contract = next(
            row
            for row in r279_causal_contracts()
            if row.name == candidate["name"]
        )
        controller = CausalAreaFeedbackController(contract)
        record = run_r279_controller_scenario(
            controller,
            controller_name=contract.name,
            controller_config={"causal_feedback": contract.telemetry()},
            scenario_name=scenario["name"],
            delta_u=scenario["delta_u"],
            seed=ENV_SEED,
            steps=STEPS,
            phase="viewed-bank-causal-development",
            evidence_hashes={
                "causal_development_seal": expected_sha256,
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
        print(
            f"[run {ordinal:03d}/{len(selected):03d}] {path.name} "
            f"completed={record['completed']} sha256={digest}",
            flush=True,
        )
        if not record["completed"]:
            raise RuntimeError(f"real-ANDES trajectory failed: {path}")


def _truncated(record: dict[str, Any]) -> dict[str, Any]:
    result = dict(record)
    result["traces"] = list(record["traces"][:STEPS])
    result["n_steps"] = STEPS
    result["requested_steps"] = STEPS
    result["completed"] = True
    result["tds_failed"] = False
    return result


def _common_iae(record: dict[str, Any]) -> float:
    values = np.asarray(
        [row["delta_f_physical_hz"] for row in record["traces"][:STEPS]],
        dtype=float,
    )
    time = np.asarray([row["t"] for row in record["traces"][:STEPS]], dtype=float)
    dt = float(np.median(np.diff(time)))
    return float(np.sum(np.abs(np.mean(values, axis=1))) * dt)


def _summary_markdown(summary: dict[str, Any]) -> str:
    selected = summary["selection"]["selected"]
    return "\n".join(
        [
            "# R279 causal-comparator development summary",
            "",
            f"Selected: `{selected['candidate']}` (Kf={selected['k_frequency']}, Kr={selected['k_rocof']}).",
            "",
            f"- Worst-location score: `{selected['worst_location_score']:.6f}`.",
            f"- All-bank score: `{selected['all_bank_score']:.6f}`.",
            f"- Sync ratio of means: `{selected['sync_ratio_of_means']:.6f}`.",
            f"- Inter-area ratio of means: `{selected['inter_area_ratio_of_means']:.6f}`.",
            f"- Improves both co-primary means: `{selected['improves_both_primary_means']}`.",
            f"- Action and fast guards pass: `{selected['all_guards_pass']}`.",
            "",
            "This viewed-bank choice is frozen before any full-horizon guard or fresh-bank evaluation.",
            "",
        ]
    )


def analyse(
    manifest_path: Path,
    expected_sha256: str,
    out_dir: Path,
) -> None:
    manifest = _verify_manifest(manifest_path, expected_sha256)
    bank = _load_json(BANK_PATH, manifest["development_bank"]["sha256"])
    baseline_records: dict[str, dict[str, Any]] = {}
    baseline_metrics: dict[str, dict[str, float]] = {}
    for path_text, expected in manifest["r275_q0_baseline"]["trace_hashes"].items():
        record = _load_json(ROOT / path_text, expected)
        scenario = str(record["scenario"])
        truncated = _truncated(record)
        metrics = summarise_fast_md_trace(
            truncated, final_window_steps=5, fast_window_steps=STEPS
        )
        metrics["first_3s_common_iae_hz_s"] = _common_iae(truncated)
        baseline_records[scenario] = truncated
        baseline_metrics[scenario] = metrics
    scenario_meta = {row["name"]: row for row in bank["scenarios"]}

    rows: list[dict[str, Any]] = []
    trace_hashes: dict[str, str] = {}
    for order, candidate in enumerate(manifest["candidates"]):
        candidate_metrics: dict[str, dict[str, Any]] = {}
        action_pass = True
        for scenario in sorted(scenario_meta):
            path = _candidate_path(out_dir, scenario, candidate["name"])
            record = _load_json(path)
            _validate_existing(
                path,
                scenario=scenario_meta[scenario],
                candidate=candidate,
                seal_sha256=expected_sha256,
            )
            metrics = summarise_icems_policy_trace(
                record, final_window_steps=5, fast_window_steps=STEPS
            )
            metrics["first_3s_common_iae_hz_s"] = _common_iae(record)
            audit = audit_icems_policy_action(metrics)
            action_pass = action_pass and all(audit.values())
            metrics["action_audit"] = audit
            candidate_metrics[scenario] = metrics
            trace_hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = sha256_file(path)

        def ratio(endpoint: str, names: list[str] | None = None) -> float:
            selected_names = names or sorted(scenario_meta)
            left = np.mean([candidate_metrics[name][endpoint] for name in selected_names])
            right = np.mean([baseline_metrics[name][endpoint] for name in selected_names])
            return float(left / right)

        sync_ratio = ratio("normalized_sync_loss_hz2")
        inter_ratio = ratio("fast_inter_area_iae_hz_s")
        location_scores = {}
        for location in sorted({row["location"] for row in scenario_meta.values()}):
            names = [
                name
                for name, meta in scenario_meta.items()
                if meta["location"] == location
            ]
            location_scores[location] = 0.5 * (
                ratio("normalized_sync_loss_hz2", names)
                + ratio("fast_inter_area_iae_hz_s", names)
            )
        guard_ratios = {
            endpoint: ratio(endpoint)
            for endpoint in (
                "max_abs_rocof_hz_s",
                "worst_bus_peak_abs_hz",
                "first_3s_common_iae_hz_s",
            )
        }
        fast_guards_pass = all(value <= 1.05 for value in guard_ratios.values())
        rows.append(
            {
                "candidate": candidate["name"],
                "k_frequency": candidate["k_frequency"],
                "k_rocof": candidate["k_rocof"],
                "frozen_order": order,
                "gain_norm_squared": candidate["k_frequency"] ** 2
                + candidate["k_rocof"] ** 2,
                "sync_ratio_of_means": sync_ratio,
                "inter_area_ratio_of_means": inter_ratio,
                "all_bank_score": 0.5 * (sync_ratio + inter_ratio),
                "location_scores": location_scores,
                "worst_location_score": max(location_scores.values()),
                "guard_ratios": guard_ratios,
                "action_guard_pass": action_pass,
                "fast_guards_pass": fast_guards_pass,
                "all_guards_pass": action_pass and fast_guards_pass,
                "improves_both_primary_means": sync_ratio < 1.0 and inter_ratio < 1.0,
            }
        )
    eligible = [row for row in rows if row["all_guards_pass"]]
    if not eligible:
        raise ValueError("no causal candidate passes the frozen action/fast guards")
    selected = min(
        eligible,
        key=lambda row: (
            row["worst_location_score"],
            row["all_bank_score"],
            row["gain_norm_squared"],
            row["frozen_order"],
        ),
    )
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": "Q-0041",
        "phase": "viewed-bank-causal-development",
        "causal_development_seal_sha256": expected_sha256,
        "completion": {
            "expected": 216,
            "observed": len(trace_hashes),
            "all_complete": len(trace_hashes) == 216,
        },
        "selection": {
            "selected": selected,
            "ordered_candidates": sorted(
                rows,
                key=lambda row: (
                    row["worst_location_score"],
                    row["all_bank_score"],
                    row["gain_norm_squared"],
                    row["frozen_order"],
                ),
            ),
        },
        "trace_hashes": dict(sorted(trace_hashes.items())),
    }
    summary_path = out_dir / "causal_development_summary.json"
    digest = _write_new(summary_path, summary)
    markdown_digest = _write_new_text(
        out_dir / "causal_development_summary.md", _summary_markdown(summary)
    )
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "repository_head": _git_head(),
        "causal_development_seal_sha256": expected_sha256,
        "summary_sha256": digest,
        "markdown_sha256": markdown_digest,
        "source_sha256": {
            key: value["sha256"] for key, value in manifest["sources"].items()
        },
        "paper_files_modified": False,
    }
    provenance_digest = _write_new(out_dir / "provenance.json", provenance)
    print(
        f"[analysed] selected={selected['candidate']} "
        f"summary_sha256={digest} provenance_sha256={provenance_digest}",
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
        prepare_seal(args.manifest, args.out_dir)
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
