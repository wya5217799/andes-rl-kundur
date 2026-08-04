#!/usr/bin/env python3
"""Seal, execute, and analyse the R293 classical edge-controller grid.

The 3 x 3 family is selected only on the declared R274 development bank.  A
separate full-horizon R292-bank guard is required before learned training; this
adapter never treats development endpoints as formal evidence.
"""

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

from andes_rl_kundur.control.classical_edge_residual import (  # noqa: E402
    ClassicalEdgeController,
    classical_edge_candidates,
)
from andes_rl_kundur.evaluation.fast_md_authority import (  # noqa: E402
    summarise_fast_md_trace,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from andes_rl_kundur.evaluation.vector_residual import (  # noqa: E402
    ZeroVectorController,
    audit_vector_action,
    run_vector_controller_scenario,
    summarise_vector_trace,
)

ROUND_ID = "R293"
QUESTION_ID = "Q-0050"
ENV_SEED = 42
STEPS = 15
SHARD_COUNT = 3
BANK_PATH = ROOT / "results/r274_prospective_active_power_authority/formal_bank.json"
R275_SUMMARY = ROOT / "results/r275_fast_md_authority/fast_md_authority_summary.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R293/classical_development_seal.json"
DEFAULT_OUT = ROOT / "results/r293_classical_development"
PRIMARY_ENDPOINTS = ("normalized_sync_loss_hz2", "fast_inter_area_iae_hz_s")
GUARD_ENDPOINTS = (*PRIMARY_ENDPOINTS, "max_abs_rocof_hz_s", "worst_bus_peak_abs_hz")


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
        "plan": ROOT / "memory/rounds/R293/plan.md",
        "script": Path(__file__).resolve(),
        "classical_controller": ROOT
        / "src/andes_rl_kundur/control/classical_edge_residual.py",
        "vector_runner": ROOT
        / "src/andes_rl_kundur/evaluation/vector_residual.py",
        "vector_environment": ROOT
        / "src/andes_rl_kundur/env/andes/distributed_residual_env.py",
        "vector_contract": ROOT
        / "src/andes_rl_kundur/control/vector_inertia_residual.py",
        "development_bank": BANK_PATH,
        "q0_summary": R275_SUMMARY,
    }


def _baseline_hashes(summary: dict[str, Any]) -> dict[str, str]:
    result = {
        path: digest
        for path, digest in summary["trace_hashes"].items()
        if path.endswith("__common_M_pos.json")
    }
    if len(result) != 24:
        raise ValueError(f"expected 24 q0 baseline traces, found {len(result)}")
    return dict(sorted(result.items()))


def _trace_path(out_dir: Path, scenario: str, candidate: str) -> Path:
    return out_dir / "traces" / f"{scenario}__{candidate}.json"


def smoke() -> None:
    """Run two non-persisted engineering trajectories without reading endpoints."""

    scenario = _load_json(BANK_PATH)["scenarios"][0]
    controllers = (
        ("q0", ZeroVectorController(), {"role": "engineering_q0"}),
        (
            "classical_smoke",
            ClassicalEdgeController(classical_edge_candidates()[4]),
            {"role": "engineering_classical"},
        ),
    )
    outcome: dict[str, dict[str, Any]] = {}
    for name, controller, config in controllers:
        record = run_vector_controller_scenario(
            controller,
            controller_name=name,
            controller_config=config,
            scenario_name=scenario["name"],
            delta_u=scenario["delta_u"],
            seed=ENV_SEED,
            steps=3,
            phase="engineering-smoke",
            evidence_hashes={},
        )
        finite = all(
            np.all(np.isfinite(np.asarray(row["M_es"], dtype=float)))
            and np.all(np.isfinite(np.asarray(row["freq_hz_physical"], dtype=float)))
            for row in record["traces"]
        )
        outcome[name] = {
            "completed": record["completed"],
            "n_steps": record["n_steps"],
            "tds_failed": record["tds_failed"],
            "finite": bool(finite),
        }
        if not record["completed"] or not finite:
            raise RuntimeError(f"R293 engineering smoke failed: {name}")
    print(json.dumps(outcome, sort_keys=True), flush=True)


def prepare(manifest_path: Path, out_dir: Path) -> None:
    trace_dir = out_dir / "traces"
    if trace_dir.exists() and any(trace_dir.glob("*.json")):
        raise ValueError("development seal must precede all R293 traces")
    bank = _load_json(BANK_PATH)
    if len(bank.get("scenarios", [])) != 24:
        raise ValueError("development bank must contain exactly 24 scenarios")
    q0_summary = _load_json(R275_SUMMARY)
    q0_hashes = _baseline_hashes(q0_summary)
    for path_text, expected in q0_hashes.items():
        if sha256_file(ROOT / path_text) != expected:
            raise ValueError(f"q0 baseline drift: {path_text}")
    candidates = [contract.telemetry() for contract in classical_edge_candidates()]
    if len(candidates) != 9 or len({row["name"] for row in candidates}) != 9:
        raise ValueError("R293 requires nine unique classical candidates")
    sources = {
        name: {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(path),
        }
        for name, path in _source_paths().items()
    }
    packages: dict[str, str] = {"python": sys.version}
    for package in ("andes", "numpy", "torch"):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = "not-installed"
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "viewed-bank-classical-edge-development",
        "repository_head": _git_head(),
        "development_bank": {
            "path": str(BANK_PATH.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(BANK_PATH),
            "scenario_count": 24,
            "role": "viewed_development_only",
        },
        "q0_baseline": {
            "summary_sha256": sha256_file(R275_SUMMARY),
            "trace_hashes": q0_hashes,
            "reuse": "first 15 steps only; no baseline rerun",
        },
        "candidates": candidates,
        "selection": {
            "co_primary": list(PRIMARY_ENDPOINTS),
            "score": "equal-weight mean candidate/q0 ratio",
            "ordering": [
                "minimum worst-location primary score",
                "minimum all-bank primary score",
                "minimum edge total variation",
                "frozen candidate order",
            ],
            "mean_no_harm_percent": 5.0,
            "nontrivial_edge_total_variation_min": 1e-6,
        },
        "execution": {
            "steps": STEPS,
            "seed": ENV_SEED,
            "trajectory_budget": 216,
            "shard_count": SHARD_COUNT,
            "overwrite": False,
        },
        "packages": packages,
        "sources": sources,
        "trace_count_at_freeze": 0,
    }
    digest = _write_new(manifest_path, payload)
    print(f"[sealed] {manifest_path} sha256={digest}", flush=True)


def _verify_manifest(path: Path, expected_sha256: str) -> dict[str, Any]:
    manifest = _load_json(path, expected_sha256)
    if manifest.get("round") != ROUND_ID:
        raise ValueError("manifest is not R293")
    if manifest.get("phase") != "viewed-bank-classical-edge-development":
        raise ValueError("unexpected R293 development phase")
    for entry in manifest["sources"].values():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError(f"sealed source drift: {entry['path']}")
    return manifest


def _validate_trace(
    path: Path,
    *,
    scenario: dict[str, Any],
    candidate: dict[str, Any],
    seal_sha256: str,
) -> dict[str, Any]:
    record = _load_json(path)
    expected = {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "viewed-bank-classical-edge-development",
        "scenario": scenario["name"],
        "controller": candidate["name"],
        "requested_steps": STEPS,
        "n_steps": STEPS,
        "completed": True,
        "tds_failed": False,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"trace mismatch in {path}: {key}")
    if record["evidence_hashes"].get("r293_development_seal") != seal_sha256:
        raise ValueError(f"trace seal mismatch: {path}")
    return record


def run_shard(
    manifest_path: Path,
    expected_sha256: str,
    out_dir: Path,
    shard_index: int,
    shard_count: int,
) -> None:
    manifest = _verify_manifest(manifest_path, expected_sha256)
    if shard_count != SHARD_COUNT or not 0 <= shard_index < shard_count:
        raise ValueError("shard arguments differ from the frozen contract")
    bank = _load_json(BANK_PATH, manifest["development_bank"]["sha256"])
    contracts = {row.name: row for row in classical_edge_candidates()}
    tasks = [
        (candidate, scenario)
        for candidate in manifest["candidates"]
        for scenario in bank["scenarios"]
    ]
    selected = [task for index, task in enumerate(tasks) if index % shard_count == shard_index]
    for ordinal, (candidate, scenario) in enumerate(selected, start=1):
        path = _trace_path(out_dir, scenario["name"], candidate["name"])
        if path.exists():
            _validate_trace(
                path,
                scenario=scenario,
                candidate=candidate,
                seal_sha256=expected_sha256,
            )
            print(f"[resume {ordinal:03d}/{len(selected):03d}] {path.name}", flush=True)
            continue
        contract = contracts[candidate["name"]]
        record = run_vector_controller_scenario(
            ClassicalEdgeController(contract),
            controller_name=contract.name,
            controller_config={"classical_edge": contract.telemetry()},
            scenario_name=scenario["name"],
            delta_u=scenario["delta_u"],
            seed=ENV_SEED,
            steps=STEPS,
            phase="viewed-bank-classical-edge-development",
            evidence_hashes={
                "r293_development_seal": expected_sha256,
                "development_bank": manifest["development_bank"]["sha256"],
            },
        )
        record.update(
            {
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "experiment": "r293_classical_edge_development",
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
            raise RuntimeError(f"real-ANDES development trajectory failed: {path}")


def _truncated(record: dict[str, Any]) -> dict[str, Any]:
    result = dict(record)
    result["traces"] = list(record["traces"][:STEPS])
    result["n_steps"] = STEPS
    result["requested_steps"] = STEPS
    result["completed"] = True
    result["tds_failed"] = False
    return result


def analyse(manifest_path: Path, expected_sha256: str, out_dir: Path) -> None:
    manifest = _verify_manifest(manifest_path, expected_sha256)
    bank = _load_json(BANK_PATH, manifest["development_bank"]["sha256"])
    scenario_meta = {row["name"]: row for row in bank["scenarios"]}
    baseline: dict[str, dict[str, Any]] = {}
    for path_text, expected in manifest["q0_baseline"]["trace_hashes"].items():
        record = _load_json(ROOT / path_text, expected)
        baseline[str(record["scenario"])] = summarise_fast_md_trace(
            _truncated(record), final_window_steps=5, fast_window_steps=STEPS
        )

    rows: list[dict[str, Any]] = []
    trace_hashes: dict[str, str] = {}
    for order, candidate in enumerate(manifest["candidates"]):
        metrics: dict[str, dict[str, Any]] = {}
        action_pass = True
        for scenario in sorted(scenario_meta):
            path = _trace_path(out_dir, scenario, candidate["name"])
            record = _validate_trace(
                path,
                scenario=scenario_meta[scenario],
                candidate=candidate,
                seal_sha256=expected_sha256,
            )
            row_metrics = summarise_vector_trace(
                record, final_window_steps=5, fast_window_steps=STEPS
            )
            action_pass = action_pass and all(audit_vector_action(row_metrics).values())
            metrics[scenario] = row_metrics
            trace_hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = sha256_file(path)

        def ratio(endpoint: str, names: list[str] | None = None) -> float:
            chosen = names or sorted(scenario_meta)
            left = float(np.mean([metrics[name][endpoint] for name in chosen]))
            right = float(np.mean([baseline[name][endpoint] for name in chosen]))
            return left / right

        endpoint_ratios = {endpoint: ratio(endpoint) for endpoint in GUARD_ENDPOINTS}
        location_scores = {}
        for location in sorted({row["location"] for row in scenario_meta.values()}):
            names = [
                name for name, meta in scenario_meta.items() if meta["location"] == location
            ]
            location_scores[location] = 0.5 * sum(ratio(endpoint, names) for endpoint in PRIMARY_ENDPOINTS)
        total_variation = float(
            sum(metrics[name]["r292_edge_total_variation"] for name in metrics)
        )
        mean_guard_pass = all(endpoint_ratios[name] <= 1.05 for name in GUARD_ENDPOINTS)
        nontrivial = total_variation > 1e-6
        rows.append(
            {
                "candidate": candidate["name"],
                "family": candidate["family"],
                "gain": candidate["gain"],
                "frozen_order": order,
                "endpoint_ratios": endpoint_ratios,
                "all_bank_score": 0.5 * sum(endpoint_ratios[name] for name in PRIMARY_ENDPOINTS),
                "location_scores": location_scores,
                "worst_location_score": max(location_scores.values()),
                "edge_total_variation": total_variation,
                "action_guard_pass": action_pass,
                "mean_guard_pass": mean_guard_pass,
                "nontrivial_action": nontrivial,
                "credible_development": action_pass and mean_guard_pass and nontrivial,
            }
        )
    eligible = [row for row in rows if row["credible_development"]]
    selected = (
        min(
            eligible,
            key=lambda row: (
                row["worst_location_score"],
                row["all_bank_score"],
                row["edge_total_variation"],
                row["frozen_order"],
            ),
        )
        if eligible
        else None
    )
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "viewed-bank-classical-edge-development",
        "development_seal_sha256": expected_sha256,
        "completion": {
            "expected": 216,
            "observed": len(trace_hashes),
            "all_complete": len(trace_hashes) == 216,
        },
        "classification": "CLASSICAL-DEVELOPMENT-CANDIDATE" if selected else "CLASSICAL-FAMILY-NO-GO",
        "selected": selected,
        "ordered_candidates": sorted(
            rows,
            key=lambda row: (
                not row["credible_development"],
                row["worst_location_score"],
                row["all_bank_score"],
                row["edge_total_variation"],
                row["frozen_order"],
            ),
        ),
        "trace_hashes": dict(sorted(trace_hashes.items())),
    }
    summary_digest = _write_new(out_dir / "classical_development_summary.json", summary)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "repository_head": _git_head(),
        "development_seal_sha256": expected_sha256,
        "summary_sha256": summary_digest,
        "source_sha256": {
            name: entry["sha256"] for name, entry in manifest["sources"].items()
        },
        "paper_files_modified": False,
        "performance_role": "viewed_development_only",
    }
    provenance_digest = _write_new(out_dir / "provenance.json", provenance)
    selected_name = selected["candidate"] if selected else "none"
    print(
        f"[analysed] selected={selected_name} summary_sha256={summary_digest} "
        f"provenance_sha256={provenance_digest}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("smoke")
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
    if args.command == "smoke":
        smoke()
    elif args.command == "prepare":
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
