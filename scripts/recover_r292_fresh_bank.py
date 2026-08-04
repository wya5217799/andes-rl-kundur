#!/usr/bin/env python3
"""Seal and execute the versioned R292 q0-screen re-audit.

This adapter never runs ANDES.  It verifies and reuses the immutable 24 q0
traces from the first implementation-invalid screen, applies the R292-specific
physical contract, and writes only versioned v2 artifacts.  Any source, trace,
bank, training, or provenance drift is a hard failure.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.prospective_authority import (  # noqa: E402
    assess_screened_authority_bank,
)
from andes_rl_kundur.evaluation.r292_screen import (  # noqa: E402
    audit_r292_q0_screen_record,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    load_scenario_bank,
    sha256_bytes,
    sha256_file,
    write_scenario_bank,
)

ROUND_ID = "R292"
QUESTION_ID = "Q-0049"
ORIGINAL_SEAL = ROOT / "memory/rounds/R292/fresh_bank_screen_seal.json"
ORIGINAL_OUT = ROOT / "results/r292_fresh_bank"
ORIGINAL_SUMMARY = ORIGINAL_OUT / "screen_summary.json"
ORIGINAL_EVIDENCE = ORIGINAL_OUT / "screen_evidence.json"
ORIGINAL_PROVENANCE = ORIGINAL_OUT / "provenance.json"
TRAINING_SUMMARY = ROOT / "results/r292_vector_training/training_matrix_summary.json"
AMENDMENT = ROOT / "memory/rounds/R292/execution_amendment_20260731.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R292/fresh_bank_screen_v2_seal.json"
DEFAULT_OUT = ROOT / "results/r292_fresh_bank_v2"
FORMAL_V2_TRACE_DIR = ROOT / "results/r292_formal_evaluation_v2/traces"


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


def _sidecar_digest(path: Path) -> str:
    sidecar = path.with_name(path.name + ".sha256")
    fields = sidecar.read_text(encoding="utf-8").strip().split()
    if len(fields) != 2 or fields[1] != path.name:
        raise ValueError(f"invalid sha256 sidecar: {sidecar}")
    if fields[0] != sha256_file(path):
        raise ValueError(f"sha256 sidecar mismatch: {path}")
    return fields[0]


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _source_paths() -> dict[str, Path]:
    return {
        "amendment": AMENDMENT,
        "recovery_script": Path(__file__).resolve(),
        "r292_screen_audit": ROOT
        / "src/andes_rl_kundur/evaluation/r292_screen.py",
        "prospective_authority": ROOT
        / "src/andes_rl_kundur/evaluation/prospective_authority.py",
        "sealed_bank": ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py",
        "original_seal": ORIGINAL_SEAL,
        "original_summary": ORIGINAL_SUMMARY,
        "original_evidence": ORIGINAL_EVIDENCE,
        "original_provenance": ORIGINAL_PROVENANCE,
        "training_summary": TRAINING_SUMMARY,
    }


def _verify_training(training: dict[str, Any]) -> None:
    if not training.get("all_completed") or training.get("observed_run_count") != 6:
        raise ValueError("R292 recovery requires six completed training runs")
    if training.get("seed_selection_performed") is not False:
        raise ValueError("R292 recovery forbids seed selection")
    for path_text, digest in training.get("artifact_hashes", {}).items():
        if sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"training artifact drift: {path_text}")


def _verify_original() -> dict[str, Any]:
    original_seal_hash = _sidecar_digest(ORIGINAL_SEAL)
    manifest = _load_json(ORIGINAL_SEAL, original_seal_hash)
    if manifest.get("round") != ROUND_ID:
        raise ValueError("original seal is not R292")
    if manifest.get("phase") != "fresh-bank-vector-q0-screen":
        raise ValueError("unexpected original fresh-bank phase")
    for entry in manifest["sources"].values():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError(f"original sealed source drift: {entry['path']}")
    training = _load_json(
        ROOT / manifest["upstream"]["training_summary"]["path"],
        manifest["upstream"]["training_summary"]["sha256"],
    )
    _verify_training(training)
    candidate_path = ROOT / manifest["candidate_bank"]["path"]
    candidate, candidate_hash = load_scenario_bank(
        candidate_path,
        expected_sha256=manifest["candidate_bank"]["sha256"],
    )
    if candidate["scenario_count"] != 24:
        raise ValueError("original candidate bank must contain 24 scenarios")
    summary = _load_json(ORIGINAL_SUMMARY, _sidecar_digest(ORIGINAL_SUMMARY))
    evidence = _load_json(ORIGINAL_EVIDENCE, _sidecar_digest(ORIGINAL_EVIDENCE))
    provenance = _load_json(
        ORIGINAL_PROVENANCE,
        _sidecar_digest(ORIGINAL_PROVENANCE),
    )
    if summary.get("decision", {}).get("classification") != "INVALID":
        raise ValueError("original screen is not the preserved invalid attempt")
    if summary.get("fresh_bank_screen_seal_sha256") != original_seal_hash:
        raise ValueError("original summary seal mismatch")
    if evidence.get("controller_performance_endpoints_inspected") is not False:
        raise ValueError("original screen inspected forbidden performance endpoints")
    if len(evidence.get("rows", [])) != 24:
        raise ValueError("original screen evidence must contain 24 rows")
    if not all(
        row.get("completed")
        and not row.get("tds_failed")
        and row.get("physical_valid") is False
        for row in evidence["rows"]
    ):
        raise ValueError("original screen failure shape drift")
    trace_hashes = dict(provenance.get("trace_hashes", {}))
    if len(trace_hashes) != 24:
        raise ValueError("original provenance must freeze 24 trace hashes")
    for path_text, digest in trace_hashes.items():
        if sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"original q0 trace drift: {path_text}")
    if FORMAL_V2_TRACE_DIR.exists() and any(FORMAL_V2_TRACE_DIR.glob("*.json")):
        raise ValueError("v2 screen seal must precede every v2 formal trace")
    return {
        "manifest": manifest,
        "seal_hash": original_seal_hash,
        "candidate": candidate,
        "candidate_path": candidate_path,
        "candidate_hash": candidate_hash,
        "summary_hash": sha256_file(ORIGINAL_SUMMARY),
        "evidence_hash": sha256_file(ORIGINAL_EVIDENCE),
        "provenance_hash": sha256_file(ORIGINAL_PROVENANCE),
        "trace_hashes": trace_hashes,
        "training_hash": sha256_file(TRAINING_SUMMARY),
    }


def prepare(manifest_path: Path, out_dir: Path) -> None:
    if manifest_path.exists():
        raise FileExistsError(f"v2 screen seal already exists: {manifest_path}")
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"v2 screen output already exists: {out_dir}")
    original = _verify_original()
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
        "phase": "fresh-bank-q0-contract-reaudit-v2",
        "repository_head": _git_head(),
        "candidate_bank": {
            "path": str(original["candidate_path"].relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "sha256": original["candidate_hash"],
            "scenario_count": 24,
            "generator_seed": original["manifest"]["candidate_bank"][
                "generator_seed"
            ],
        },
        "original_failed_attempt": {
            "seal_path": str(ORIGINAL_SEAL.relative_to(ROOT)).replace("\\", "/"),
            "seal_sha256": original["seal_hash"],
            "summary_sha256": original["summary_hash"],
            "evidence_sha256": original["evidence_hash"],
            "provenance_sha256": original["provenance_hash"],
            "classification": "INVALID",
            "preserved_byte_for_byte": True,
        },
        "training_summary_sha256": original["training_hash"],
        "execution": {
            "mode": "derived_reaudit_of_immutable_q0_traces",
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
    digest = _write_new(manifest_path, payload)
    print(f"[sealed] {manifest_path} sha256={digest}", flush=True)


def _verify(manifest_path: Path, expected: str) -> dict[str, Any]:
    manifest = _load_json(manifest_path, expected)
    if manifest.get("round") != ROUND_ID:
        raise ValueError("not an R292 v2 screen seal")
    if manifest.get("phase") != "fresh-bank-q0-contract-reaudit-v2":
        raise ValueError("unexpected R292 v2 screen phase")
    for entry in manifest["sources"].values():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError(f"v2 sealed source drift: {entry['path']}")
    original = _verify_original()
    expected_original = manifest["original_failed_attempt"]
    checks = {
        "seal_sha256": original["seal_hash"],
        "summary_sha256": original["summary_hash"],
        "evidence_sha256": original["evidence_hash"],
        "provenance_sha256": original["provenance_hash"],
    }
    for key, value in checks.items():
        if expected_original.get(key) != value:
            raise ValueError(f"original failed-attempt drift: {key}")
    if manifest["frozen_trace_hashes"] != original["trace_hashes"]:
        raise ValueError("v2 frozen trace hash set drift")
    return manifest


def _trace_path(scenario: str) -> Path:
    return ORIGINAL_OUT / "screen_traces" / f"{scenario}__q0.json"


def _validate_trace(
    path: Path,
    scenario: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    path_text = str(path.relative_to(ROOT)).replace("\\", "/")
    expected_hash = manifest["frozen_trace_hashes"].get(path_text)
    if expected_hash is None or sha256_file(path) != expected_hash:
        raise ValueError(f"v2 trace hash mismatch: {path}")
    record = _load_json(path, expected_hash)
    original_seal = manifest["original_failed_attempt"]["seal_sha256"]
    expected = {
        "round": ROUND_ID,
        "phase": "fresh-bank-vector-q0-screen",
        "controller": "q0",
        "scenario": scenario["name"],
        "delta_u": scenario["delta_u"],
        "fresh_bank_screen_seal_sha256": original_seal,
        "candidate_bank_sha256": manifest["candidate_bank"]["sha256"],
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"original trace provenance mismatch in {path}: {key}")
    return record


def analyse(manifest_path: Path, expected: str, out_dir: Path) -> None:
    manifest = _verify(manifest_path, expected)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite v2 screen output: {out_dir}")
    bank, bank_hash = load_scenario_bank(
        ROOT / manifest["candidate_bank"]["path"],
        expected_sha256=manifest["candidate_bank"]["sha256"],
    )
    audits = []
    trace_hashes: dict[str, str] = {}
    for scenario in bank["scenarios"]:
        path = _trace_path(scenario["name"])
        record = _validate_trace(path, scenario, manifest)
        digest = sha256_file(path)
        audit = audit_r292_q0_screen_record(record, trace_sha256=digest)
        audits.append(audit)
        trace_hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = digest
    evidence = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "fresh-bank-q0-contract-reaudit-v2",
        "candidate_bank_sha256": bank_hash,
        "v2_screen_seal_sha256": expected,
        "original_failed_screen_preserved": True,
        "controller_performance_endpoints_inspected": False,
        "andes_trajectory_count": 0,
        "rows": audits,
        "trace_hashes": dict(sorted(trace_hashes.items())),
    }
    evidence_hash = _write_new(out_dir / "screen_evidence.json", evidence)
    assessment = assess_screened_authority_bank(
        bank,
        audits,
        generated_bank_sha256=bank_hash,
        completion_evidence_sha256=evidence_hash,
        controller_trace_count=0,
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
        "question": QUESTION_ID,
        "phase": "fresh-bank-q0-contract-reaudit-v2",
        "decision": assessment["decision"],
        "generated_nontriviality": assessment["generated_nontriviality"],
        "included_nontriviality": assessment["included_nontriviality"],
        "row_decisions": assessment["row_decisions"],
        "candidate_bank_sha256": bank_hash,
        "v2_screen_seal_sha256": expected,
        "original_failed_screen_sha256": manifest["original_failed_attempt"][
            "summary_sha256"
        ],
        "screen_evidence_sha256": evidence_hash,
        "screen_contract_sha256": screen_contract_hash,
        "formal_bank_sha256": formal_bank_hash,
        "controller_performance_endpoints_inspected": False,
        "controller_trace_count_at_freeze": 0,
        "redraw_performed": False,
        "andes_trajectory_count": 0,
    }
    summary_hash = _write_new(out_dir / "screen_summary.json", summary)
    provenance_hash = _write_new(
        out_dir / "provenance.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "repository_head": _git_head(),
            "v2_screen_seal_sha256": expected,
            "original_failed_attempt": manifest["original_failed_attempt"],
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
        raise RuntimeError("R292 v2 screen did not pass; formal execution remains blocked")


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
