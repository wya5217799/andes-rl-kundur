#!/usr/bin/env python3
"""V3 recovery for R292 after the v2 bank-aggregation implementation stop."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.r292_screen import (  # noqa: E402
    audit_r292_q0_screen_record,
)
from andes_rl_kundur.evaluation.r292_screen_bank import (  # noqa: E402
    assess_r292_screened_bank,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    load_scenario_bank,
    sha256_file,
    write_scenario_bank,
)

CORE_PATH = ROOT / "scripts/recover_r292_fresh_bank.py"
SPEC = importlib.util.spec_from_file_location("recover_r292_fresh_bank_v2_core", CORE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load R292 v2 recovery core: {CORE_PATH}")
CORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CORE)

ROUND_ID = "R292"
QUESTION_ID = "Q-0049"
AMENDMENT = ROOT / "memory/rounds/R292/execution_amendment_20260731_v3.json"
V2_SEAL = ROOT / "memory/rounds/R292/fresh_bank_screen_v2_seal.json"
V2_OUT = ROOT / "results/r292_fresh_bank_v2"
V2_STATUS = ROOT / "results/r292_recovery_unattended/status/failed"
V2_PREPARE_LOG = ROOT / "results/r292_recovery_unattended/logs/screen_v2_prepare.log"
V2_ANALYSE_LOG = ROOT / "results/r292_recovery_unattended/logs/screen_v2_analyse.log"
DEFAULT_SEAL = ROOT / "memory/rounds/R292/fresh_bank_screen_v3_seal.json"
DEFAULT_OUT = ROOT / "results/r292_fresh_bank_v3"
FORMAL_V3_TRACE_DIR = ROOT / "results/r292_formal_evaluation_v3/traces"


def _verify_v2_failed_attempt() -> dict[str, Any]:
    seal_hash = CORE._sidecar_digest(V2_SEAL)
    manifest = CORE._verify(V2_SEAL, seal_hash)
    if V2_STATUS.read_text(encoding="utf-8").strip() != "SCREEN_V2_ANALYSE_FAILED":
        raise ValueError("v2 recovery status is not the preserved aggregation failure")
    for path in (V2_PREPARE_LOG, V2_ANALYSE_LOG):
        if not path.is_file():
            raise ValueError(f"missing preserved v2 recovery log: {path}")
    evidence = V2_OUT / "screen_evidence.json"
    evidence_hash = CORE._sidecar_digest(evidence)
    payload = CORE._load_json(evidence, evidence_hash)
    if payload.get("controller_performance_endpoints_inspected") is not False:
        raise ValueError("v2 partial screen inspected performance endpoints")
    if payload.get("andes_trajectory_count") != 0 or len(payload.get("rows", [])) != 24:
        raise ValueError("v2 partial screen evidence shape drift")
    forbidden = (
        V2_OUT / "screen_summary.json",
        V2_OUT / "formal_bank.json",
        V2_OUT / "feasibility_screen_contract.json",
        V2_OUT / "provenance.json",
    )
    if any(path.exists() for path in forbidden):
        raise ValueError("v2 failed attempt unexpectedly produced downstream artifacts")
    if FORMAL_V3_TRACE_DIR.exists() and any(FORMAL_V3_TRACE_DIR.glob("*.json")):
        raise ValueError("v3 screen seal must precede every v3 formal trace")
    return {
        "seal_hash": seal_hash,
        "manifest": manifest,
        "evidence_hash": evidence_hash,
        "status_hash": sha256_file(V2_STATUS),
        "prepare_log_hash": sha256_file(V2_PREPARE_LOG),
        "analyse_log_hash": sha256_file(V2_ANALYSE_LOG),
    }


def _source_paths() -> dict[str, Path]:
    return {
        "amendment_v3": AMENDMENT,
        "recovery_v3": Path(__file__).resolve(),
        "recovery_v2_core": CORE_PATH,
        "r292_record_audit": ROOT / "src/andes_rl_kundur/evaluation/r292_screen.py",
        "r292_bank_audit": ROOT
        / "src/andes_rl_kundur/evaluation/r292_screen_bank.py",
        "feasibility_screen": ROOT
        / "src/andes_rl_kundur/evaluation/feasibility_screen.py",
        "prospective_guard_constants": ROOT
        / "src/andes_rl_kundur/evaluation/prospective_authority.py",
        "sealed_bank": ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py",
        "v2_seal": V2_SEAL,
        "v2_partial_evidence": V2_OUT / "screen_evidence.json",
        "v2_status": V2_STATUS,
        "v2_prepare_log": V2_PREPARE_LOG,
        "v2_analyse_log": V2_ANALYSE_LOG,
    }


def prepare(manifest_path: Path, out_dir: Path) -> None:
    if manifest_path.exists():
        raise FileExistsError(f"v3 screen seal already exists: {manifest_path}")
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"v3 screen output already exists: {out_dir}")
    original = CORE._verify_original()
    failed_v2 = _verify_v2_failed_attempt()
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
        "phase": "fresh-bank-q0-contract-reaudit-v3",
        "repository_head": CORE._git_head(),
        "candidate_bank": {
            "path": str(original["candidate_path"].relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "sha256": original["candidate_hash"],
            "scenario_count": 24,
            "generator_seed": original["manifest"]["candidate_bank"]["generator_seed"],
        },
        "original_failed_attempt": {
            "seal_path": str(CORE.ORIGINAL_SEAL.relative_to(ROOT)).replace("\\", "/"),
            "seal_sha256": original["seal_hash"],
            "summary_sha256": original["summary_hash"],
            "evidence_sha256": original["evidence_hash"],
            "provenance_sha256": original["provenance_hash"],
            "classification": "INVALID",
            "preserved_byte_for_byte": True,
        },
        "v2_failed_attempt": {
            "seal_sha256": failed_v2["seal_hash"],
            "partial_evidence_sha256": failed_v2["evidence_hash"],
            "status_sha256": failed_v2["status_hash"],
            "prepare_log_sha256": failed_v2["prepare_log_hash"],
            "analyse_log_sha256": failed_v2["analyse_log_hash"],
            "failure": "SCREEN_V2_ANALYSE_FAILED",
            "performance_endpoints_inspected": False,
            "andes_trajectory_count": 0,
            "preserved_byte_for_byte": True,
        },
        "training_summary_sha256": original["training_hash"],
        "execution": {
            "mode": "derived_reaudit_of_immutable_q0_traces_v3",
            "andes_trajectory_count": 0,
            "reused_immutable_trace_count": 24,
            "performance_endpoints_inspected": False,
            "scenario_redraw": False,
            "threshold_change": False,
            "formal_controller_trace_count_at_freeze": 0,
        },
        "frozen_trace_hashes": dict(sorted(original["trace_hashes"].items())),
        "sources": sources,
    }
    digest = CORE._write_new(manifest_path, payload)
    print(f"[sealed] {manifest_path} sha256={digest}", flush=True)


def _verify(manifest_path: Path, expected: str) -> dict[str, Any]:
    manifest = CORE._load_json(manifest_path, expected)
    if manifest.get("round") != ROUND_ID:
        raise ValueError("not an R292 v3 screen seal")
    if manifest.get("phase") != "fresh-bank-q0-contract-reaudit-v3":
        raise ValueError("unexpected R292 v3 screen phase")
    for entry in manifest["sources"].values():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError(f"v3 sealed source drift: {entry['path']}")
    original = CORE._verify_original()
    failed_v2 = _verify_v2_failed_attempt()
    for key, actual in {
        "seal_sha256": failed_v2["seal_hash"],
        "partial_evidence_sha256": failed_v2["evidence_hash"],
        "status_sha256": failed_v2["status_hash"],
        "prepare_log_sha256": failed_v2["prepare_log_hash"],
        "analyse_log_sha256": failed_v2["analyse_log_hash"],
    }.items():
        if manifest["v2_failed_attempt"].get(key) != actual:
            raise ValueError(f"v2 failed-attempt drift: {key}")
    if manifest["frozen_trace_hashes"] != original["trace_hashes"]:
        raise ValueError("v3 frozen trace hash set drift")
    return manifest


def analyse(manifest_path: Path, expected: str, out_dir: Path) -> None:
    manifest = _verify(manifest_path, expected)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite v3 screen output: {out_dir}")
    bank, bank_hash = load_scenario_bank(
        ROOT / manifest["candidate_bank"]["path"],
        expected_sha256=manifest["candidate_bank"]["sha256"],
    )
    audits = []
    trace_hashes: dict[str, str] = {}
    for scenario in bank["scenarios"]:
        path = CORE._trace_path(scenario["name"])
        record = CORE._validate_trace(path, scenario, manifest)
        digest = sha256_file(path)
        audits.append(audit_r292_q0_screen_record(record, trace_sha256=digest))
        trace_hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = digest
    evidence = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "fresh-bank-q0-contract-reaudit-v3",
        "candidate_bank_sha256": bank_hash,
        "v3_screen_seal_sha256": expected,
        "previous_failed_attempts_preserved": ["original", "v2"],
        "controller_performance_endpoints_inspected": False,
        "andes_trajectory_count": 0,
        "rows": audits,
        "trace_hashes": dict(sorted(trace_hashes.items())),
    }
    evidence_hash = CORE._write_new(out_dir / "screen_evidence.json", evidence)
    assessment = assess_r292_screened_bank(
        bank,
        audits,
        generated_bank_sha256=bank_hash,
        completion_evidence_sha256=evidence_hash,
        controller_trace_count=0,
    )
    formal_bank_hash = write_scenario_bank(
        out_dir / "formal_bank.json", assessment["formal_bank"]
    )
    screen_contract_hash = CORE._write_new(
        out_dir / "feasibility_screen_contract.json",
        assessment["feasibility_contract"],
    )
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "fresh-bank-q0-contract-reaudit-v3",
        "decision": assessment["decision"],
        "generated_nontriviality": assessment["generated_nontriviality"],
        "included_nontriviality": assessment["included_nontriviality"],
        "row_decisions": assessment["row_decisions"],
        "candidate_bank_sha256": bank_hash,
        "v3_screen_seal_sha256": expected,
        "original_failed_screen_sha256": manifest["original_failed_attempt"][
            "summary_sha256"
        ],
        "v2_failed_screen_evidence_sha256": manifest["v2_failed_attempt"][
            "partial_evidence_sha256"
        ],
        "screen_evidence_sha256": evidence_hash,
        "screen_contract_sha256": screen_contract_hash,
        "formal_bank_sha256": formal_bank_hash,
        "controller_performance_endpoints_inspected": False,
        "controller_trace_count_at_freeze": 0,
        "redraw_performed": False,
        "andes_trajectory_count": 0,
    }
    summary_hash = CORE._write_new(out_dir / "screen_summary.json", summary)
    provenance_hash = CORE._write_new(
        out_dir / "provenance.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "repository_head": CORE._git_head(),
            "v3_screen_seal_sha256": expected,
            "original_failed_attempt": manifest["original_failed_attempt"],
            "v2_failed_attempt": manifest["v2_failed_attempt"],
            "screen_summary_sha256": summary_hash,
            "screen_evidence_sha256": evidence_hash,
            "screen_contract_sha256": screen_contract_hash,
            "formal_bank_sha256": formal_bank_hash,
            "trace_hashes": dict(sorted(trace_hashes.items())),
            "paper_files_modified": False,
            "performance_endpoints_inspected": False,
            "andes_trajectory_count": 0,
        },
    )
    print(
        f"[analysed] classification={assessment['decision']['classification']} "
        f"included={assessment['formal_bank']['scenario_count']} "
        f"summary_sha256={summary_hash} provenance_sha256={provenance_hash}",
        flush=True,
    )
    if assessment["decision"]["classification"] != "PASS":
        raise RuntimeError("R292 v3 screen did not pass; formal execution remains blocked")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--manifest", type=Path, default=DEFAULT_SEAL)
    prepare_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--manifest", type=Path, default=DEFAULT_SEAL)
    analyse_parser.add_argument("--expected-manifest-sha256", required=True)
    analyse_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.manifest, args.out_dir)
    else:
        analyse(args.manifest, args.expected_manifest_sha256, args.out_dir)


if __name__ == "__main__":
    main()
