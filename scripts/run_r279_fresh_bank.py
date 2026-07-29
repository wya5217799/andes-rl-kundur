#!/usr/bin/env python3
# ruff: noqa: E402
"""Prospectively generate and completion-screen the fresh R279 bank."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.active_power_authority import (  # noqa: E402
    run_active_power_scenario,
)
from andes_rl_kundur.evaluation.prospective_authority import (  # noqa: E402
    assess_screened_authority_bank,
    audit_zero_support_screen_record,
    build_stratified_authority_candidates,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    load_scenario_bank,
    sha256_bytes,
    sha256_file,
    write_scenario_bank,
)

ROUND_ID = "R279"
CANDIDATE_SEED = 2026072704
ENV_SEED = 42
STEPS = 300
SHARD_COUNT = 8
REFERENCE_BANK = ROOT / "results/r274_prospective_active_power_authority/formal_bank.json"
TRAINING_SUMMARY = ROOT / "results/r279_matched_training/training_matrix_summary.json"
CAUSAL_GUARD_SUMMARY = ROOT / "results/r279_causal_guard/causal_guard_summary.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R279/fresh_bank_screen_seal.json"
DEFAULT_OUT = ROOT / "results/r279_fresh_bank"
FORMAL_TRACE_DIR = ROOT / "results/r279_formal_evaluation/traces"


class _MessageCollector(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(self.format(record))


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
        raise ValueError(f"hash mismatch for {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R279/plan.md",
        "execution_amendment": ROOT
        / "memory/rounds/R279/execution_amendment_20260727.md",
        "script": Path(__file__).resolve(),
        "launcher": ROOT / "scripts/run_r279_fresh_bank.sh",
        "prospective_authority": ROOT
        / "src/andes_rl_kundur/evaluation/prospective_authority.py",
        "active_power_runner": ROOT
        / "src/andes_rl_kundur/evaluation/active_power_authority.py",
        "sealed_bank": ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py",
        "training_summary": TRAINING_SUMMARY,
        "causal_guard_summary": CAUSAL_GUARD_SUMMARY,
        "reference_bank": REFERENCE_BANK,
    }


def _delta_u_key(scenario: dict[str, Any]) -> str:
    return json.dumps(scenario["delta_u"], sort_keys=True, separators=(",", ":"))


def _assert_fresh(candidate: dict[str, Any], reference: dict[str, Any]) -> None:
    reference_keys = {_delta_u_key(row) for row in reference["scenarios"]}
    duplicated = [
        row["name"] for row in candidate["scenarios"] if _delta_u_key(row) in reference_keys
    ]
    if duplicated:
        raise ValueError(f"fresh bank duplicated reference delta_u: {duplicated}")


def _verify_upstream_artifacts(
    training: dict[str, Any], causal: dict[str, Any]
) -> None:
    if not training.get("all_completed") or training.get("observed_run_count") != 6:
        raise ValueError("fresh bank requires six completed matched training runs")
    if training.get("seed_selection_performed") is not False:
        raise ValueError("training summary reports forbidden seed selection")
    for path_text, digest in training.get("artifact_hashes", {}).items():
        if sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"training artifact drift: {path_text}")
    if not causal.get("decision", {}).get("pass", False):
        raise ValueError("fresh bank requires the frozen causal comparator to pass")
    for path_text, digest in causal.get("trace_hashes", {}).items():
        if sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"causal guard trace drift: {path_text}")


def prepare(manifest_path: Path, out_dir: Path) -> None:
    if manifest_path.exists() or (out_dir / "candidate_bank.json").exists():
        raise FileExistsError("fresh-bank candidate seal is immutable")
    if FORMAL_TRACE_DIR.exists() and any(FORMAL_TRACE_DIR.glob("*.json")):
        raise ValueError("fresh bank must be frozen before every formal trace")
    training = _load_json(TRAINING_SUMMARY)
    causal = _load_json(CAUSAL_GUARD_SUMMARY)
    _verify_upstream_artifacts(training, causal)
    reference, reference_hash = load_scenario_bank(REFERENCE_BANK)
    generator_path = _source_paths()["prospective_authority"]
    candidate = build_stratified_authority_candidates(
        seed=CANDIDATE_SEED,
        repository_head=_git_head(),
        generator_source_sha256=sha256_file(generator_path),
    )
    _assert_fresh(candidate, reference)
    candidate_path = out_dir / "candidate_bank.json"
    candidate_hash = write_scenario_bank(candidate_path, candidate)
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
        "phase": "fresh-bank-completion-screen",
        "repository_head": _git_head(),
        "candidate_bank": {
            "path": str(candidate_path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": candidate_hash,
            "scenario_count": 24,
            "generator_seed": CANDIDATE_SEED,
        },
        "reference_bank": {
            "path": str(REFERENCE_BANK.relative_to(ROOT)).replace("\\", "/"),
            "sha256": reference_hash,
            "exact_delta_u_overlap_count": 0,
        },
        "upstream": {
            "training_summary": {
                "path": str(TRAINING_SUMMARY.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(TRAINING_SUMMARY),
            },
            "causal_guard_summary": {
                "path": str(CAUSAL_GUARD_SUMMARY.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(CAUSAL_GUARD_SUMMARY),
            },
        },
        "execution": {
            "controller": "zero_support",
            "plant": "v4_plus_independent_esd1",
            "environment_seed": ENV_SEED,
            "steps": STEPS,
            "shard_count": SHARD_COUNT,
            "redraw_after_failure": False,
            "formal_controller_trace_count_at_freeze": 0,
        },
        "sources": sources,
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("andes", "numpy", "torch")
        }
        | {"python": sys.version},
    }
    digest = _write_new(manifest_path, payload)
    print(f"[sealed] {manifest_path} sha256={digest}", flush=True)


def _verify(manifest_path: Path, expected: str) -> dict[str, Any]:
    manifest = _load_json(manifest_path, expected)
    if manifest.get("round") != ROUND_ID or manifest.get("phase") != "fresh-bank-completion-screen":
        raise ValueError("not an R279 fresh-bank screen seal")
    for entry in manifest["sources"].values():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError(f"sealed source drift: {entry['path']}")
    training = _load_json(
        ROOT / manifest["upstream"]["training_summary"]["path"],
        manifest["upstream"]["training_summary"]["sha256"],
    )
    causal = _load_json(
        ROOT / manifest["upstream"]["causal_guard_summary"]["path"],
        manifest["upstream"]["causal_guard_summary"]["sha256"],
    )
    _verify_upstream_artifacts(training, causal)
    candidate, _ = load_scenario_bank(
        ROOT / manifest["candidate_bank"]["path"],
        expected_sha256=manifest["candidate_bank"]["sha256"],
    )
    reference, _ = load_scenario_bank(
        ROOT / manifest["reference_bank"]["path"],
        expected_sha256=manifest["reference_bank"]["sha256"],
    )
    _assert_fresh(candidate, reference)
    return manifest


def _trace_path(out_dir: Path, scenario: str) -> Path:
    return out_dir / "screen_traces" / f"{scenario}__zero_support.json"


def _validate_trace(
    path: Path, scenario: dict[str, Any], manifest: dict[str, Any], seal_hash: str
) -> dict[str, Any]:
    record = _load_json(path)
    expected = {
        "round": ROUND_ID,
        "phase": "fresh-bank-completion-screen",
        "controller": "zero_support",
        "scenario": scenario["name"],
        "delta_u": scenario["delta_u"],
        "fresh_bank_screen_seal_sha256": seal_hash,
        "candidate_bank_sha256": manifest["candidate_bank"]["sha256"],
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"screen trace provenance mismatch in {path}: {key}")
    return record


def _run_zero_support(scenario: dict[str, Any]) -> dict[str, Any]:
    collector = _MessageCollector()
    logger = logging.getLogger("andes.routines.tds")
    logger.addHandler(collector)
    try:
        try:
            record = run_active_power_scenario(
                scenario["name"],
                scenario["delta_u"],
                controller_name="zero_support",
                seed=ENV_SEED,
                steps=STEPS,
            )
        except Exception as exc:
            record = {
                "experiment": "r279_fresh_bank_screen",
                "controller": "zero_support",
                "scenario": scenario["name"],
                "delta_u": dict(scenario["delta_u"]),
                "requested_steps": STEPS,
                "n_steps": 0,
                "tds_failed": True,
                "completed": False,
                "traces": [],
                "setup_error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
                "seed": ENV_SEED,
            }
    finally:
        logger.removeHandler(collector)
    record["solver_messages"] = collector.messages
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
        raise ValueError("fresh-bank shard contract drift")
    bank, _ = load_scenario_bank(
        ROOT / manifest["candidate_bank"]["path"],
        expected_sha256=manifest["candidate_bank"]["sha256"],
    )
    selected = [
        row for index, row in enumerate(bank["scenarios"]) if index % shard_count == shard_index
    ]
    for index, scenario in enumerate(selected, start=1):
        path = _trace_path(out_dir, scenario["name"])
        if path.exists():
            _validate_trace(path, scenario, manifest, expected)
            print(f"[resume {index:02d}/{len(selected):02d}] {path.name}", flush=True)
            continue
        record = _run_zero_support(scenario)
        record.update(
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": "Q-0041",
                "phase": "fresh-bank-completion-screen",
                "location": scenario["location"],
                "sign": scenario["sign"],
                "severity": scenario["severity"],
                "fresh_bank_screen_seal_sha256": expected,
                "candidate_bank_sha256": manifest["candidate_bank"]["sha256"],
                "execution_shard_index": shard_index,
                "execution_shard_count": shard_count,
            }
        )
        digest = _write_new(path, record)
        print(
            f"[screen {index:02d}/{len(selected):02d}] {path.name} "
            f"completed={record['completed']} sha256={digest}",
            flush=True,
        )


def analyse(manifest_path: Path, expected: str, out_dir: Path) -> None:
    manifest = _verify(manifest_path, expected)
    bank, bank_hash = load_scenario_bank(
        ROOT / manifest["candidate_bank"]["path"],
        expected_sha256=manifest["candidate_bank"]["sha256"],
    )
    audits = []
    trace_hashes: dict[str, str] = {}
    solver_rows = []
    for scenario in bank["scenarios"]:
        path = _trace_path(out_dir, scenario["name"])
        record = _validate_trace(path, scenario, manifest, expected)
        digest = sha256_file(path)
        audits.append(audit_zero_support_screen_record(record, trace_sha256=digest))
        trace_hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = digest
        solver_rows.append(
            {
                "scenario": scenario["name"],
                "completed": bool(record["completed"]),
                "tds_failed": bool(record["tds_failed"]),
                "n_steps": int(record["n_steps"]),
                "requested_steps": int(record["requested_steps"]),
                "solver_messages": list(record.get("solver_messages", [])),
                "setup_error": record.get("setup_error"),
            }
        )
    evidence = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": "Q-0041",
        "phase": "fresh-bank-completion-screen",
        "candidate_bank_sha256": bank_hash,
        "fresh_bank_screen_seal_sha256": expected,
        "controller_performance_endpoints_inspected": False,
        "rows": audits,
        "solver_rows": solver_rows,
        "trace_hashes": dict(sorted(trace_hashes.items())),
    }
    evidence_hash = _write_new(out_dir / "screen_evidence.json", evidence)
    formal_count = (
        len(list(FORMAL_TRACE_DIR.glob("*.json"))) if FORMAL_TRACE_DIR.exists() else 0
    )
    assessment = assess_screened_authority_bank(
        bank,
        audits,
        generated_bank_sha256=bank_hash,
        completion_evidence_sha256=evidence_hash,
        controller_trace_count=formal_count,
    )
    formal_bank_hash = write_scenario_bank(
        out_dir / "formal_bank.json", assessment["formal_bank"]
    )
    screen_contract_hash = _write_new(
        out_dir / "feasibility_screen_contract.json",
        assessment["feasibility_contract"],
    )
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": "Q-0041",
        "phase": "fresh-bank-completion-screen",
        "decision": assessment["decision"],
        "generated_nontriviality": assessment["generated_nontriviality"],
        "included_nontriviality": assessment["included_nontriviality"],
        "row_decisions": assessment["row_decisions"],
        "candidate_bank_sha256": bank_hash,
        "fresh_bank_screen_seal_sha256": expected,
        "screen_evidence_sha256": evidence_hash,
        "screen_contract_sha256": screen_contract_hash,
        "formal_bank_sha256": formal_bank_hash,
        "controller_performance_endpoints_inspected": False,
        "controller_trace_count_at_freeze": formal_count,
        "redraw_performed": False,
    }
    summary_hash = _write_new(out_dir / "screen_summary.json", summary)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "repository_head": _git_head(),
        "fresh_bank_screen_seal_sha256": expected,
        "screen_summary_sha256": summary_hash,
        "screen_evidence_sha256": evidence_hash,
        "screen_contract_sha256": screen_contract_hash,
        "formal_bank_sha256": formal_bank_hash,
        "trace_hashes": dict(sorted(trace_hashes.items())),
        "paper_files_modified": False,
    }
    provenance_hash = _write_new(out_dir / "provenance.json", provenance)
    print(
        f"[analysed] classification={assessment['decision']['classification']} "
        f"included={assessment['formal_bank']['scenario_count']} "
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
