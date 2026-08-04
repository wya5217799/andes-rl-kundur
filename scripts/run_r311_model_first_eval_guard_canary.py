#!/usr/bin/env python3
"""Seal, run, and analyse the source-bound R311 EVAL guard canary."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from andes_rl_kundur.evaluation.model_first_stage1_eval_guards import (  # noqa: E402
    build_guarded_fresh_stage1_eval_view,
)

ROUND_ID = "R311"
QUESTION_ID = "Q-0067"
DEFAULT_SEAL = ROOT / "memory/rounds/R311/eval_guard_canary_seal.json"
DEFAULT_OUT = ROOT / "results/r311_model_first_eval_guard_canary"
EVAL_BOOTSTRAP_RESAMPLES = 1000
EVAL_BOOTSTRAP_SEED = 2026080311
PASS_CLASSIFICATION = "EVAL-GUARD-ADAPTER-CANARY-PASS"
INVALID_CLASSIFICATION = "INVALID-EVAL-GUARD-ADAPTER-CANARY"
EXPECTED_GUARDS = {
    "completed": True,
    "tds_test_ok": True,
    "system_exit_code": 0,
    "finite_telemetry": True,
}
SOURCE_PAIR = {
    "positive": {
        "path": "results/r310_model_first_stage1/records/edge_source/op0_edge_0__positive.json",
        "sha256": "db59415d00238cbd58339c52671e67a8926d517ca0a464a89f49fdffb3bba17d",
    },
    "negative": {
        "path": "results/r310_model_first_stage1/records/edge_source/op0_edge_0__negative.json",
        "sha256": "eae0611606d0bc543c7d038f0a91d589f9d0822cf119e1d2be4d42f3a061c7a1",
    },
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _payload_sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _write_new_json(path: Path, payload: object) -> str:
    path = path.resolve()
    sidecar = path.with_suffix(path.suffix + ".sha256")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"create-only artifact already exists: {path}")
    encoded = _canonical_bytes(payload)
    with path.open("xb") as handle:
        handle.write(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    with sidecar.open("x", encoding="ascii", newline="\n") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def _read_verified_json(
    path: Path,
    expected_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    path = path.resolve()
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not path.is_file() or not sidecar.is_file():
        raise RuntimeError(f"missing artifact or sidecar: {path}")
    digest = _sha256_file(path)
    recorded = sidecar.read_text(encoding="ascii").strip().split()[0]
    if digest != recorded:
        raise RuntimeError(f"sidecar mismatch for {path}")
    if expected_sha256 is not None and digest != expected_sha256:
        raise RuntimeError(f"expected hash mismatch for {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"artifact root must be an object: {path}")
    return payload, digest


def _path_text(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R311/plan.md",
        "question": ROOT / "memory/questions/Q-0067.md",
        "parent_claim": ROOT / "memory/claims/CLM-0760.md",
        "r310_analysis": ROOT / "results/r310_model_first_stage1/analysis.json",
        "r310_verdict": ROOT / "memory/rounds/R310/verdict.md",
        "adapter": Path(__file__).resolve(),
        "guard_synthesis": SRC
        / "andes_rl_kundur/evaluation/model_first_stage1_eval_guards.py",
        "paired_view": SRC
        / "andes_rl_kundur/evaluation/model_first_stage1_eval_view.py",
        "eval_v2": SRC / "andes_rl_kundur/evaluation/eval_v2.py",
        "guard_tests": ROOT / "tests/test_model_first_stage1_eval_guards.py",
        "adapter_tests": ROOT
        / "tests/test_r311_model_first_eval_guard_canary.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def build_contract() -> dict[str, Any]:
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "non-claim-bearing-eval-adapter-canary",
        "source_pair": SOURCE_PAIR,
        "synthesized_guards": EXPECTED_GUARDS,
        "eval": {
            "baseline": "positive",
            "execution_profile": "vector_power",
            "required_active_window_seconds": 1.0,
            "bootstrap_resamples": EVAL_BOOTSTRAP_RESAMPLES,
            "bootstrap_seed": EVAL_BOOTSTRAP_SEED,
            "evidence_status": "EXTERNAL_AUTHORITY_REQUIRED",
        },
        "classification": [PASS_CLASSIFICATION, INVALID_CLASSIFICATION],
        "physical_trace_rerun": False,
        "r310_amendment_authorized": False,
        "effect_interpretation_authorized": False,
        "predictor_fitting_authorized": False,
        "controller_development_authorized": False,
        "training_authorized": False,
    }


def prepare(seal_path: Path) -> str:
    for entry in SOURCE_PAIR.values():
        _read_verified_json(ROOT / entry["path"], entry["sha256"])
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "sources": _sources(),
    }
    digest = _write_new_json(seal_path, seal)
    print(f"seal_sha256={digest}", flush=True)
    return digest


def _load_seal(path: Path, expected: str) -> tuple[dict[str, Any], str]:
    seal, digest = _read_verified_json(path, expected)
    if seal.get("round") != ROUND_ID or seal.get("question") != QUESTION_ID:
        raise RuntimeError("R311 seal identity mismatch")
    if seal.get("contract_payload_sha256") != _payload_sha256(seal["contract"]):
        raise RuntimeError("R311 seal contract payload drift")
    if seal["contract"] != build_contract():
        raise RuntimeError("R311 in-code contract drift")
    for name, entry in seal["sources"].items():
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed source drift for {name}")
    return seal, digest


def classify_scorecard(scorecard: Mapping[str, object]) -> str:
    """Apply the binary, non-effect R311 classification rule."""

    try:
        validity = scorecard["validity"]
        evidence = scorecard["evidence_status"]
        if not isinstance(validity, Mapping) or not isinstance(evidence, Mapping):
            return INVALID_CLASSIFICATION
        input_integrity = validity["input_integrity"]
        execution = validity["execution_contract"]
        if not isinstance(input_integrity, Mapping) or not isinstance(
            execution, Mapping
        ):
            return INVALID_CLASSIFICATION
        passed = (
            validity.get("diagnostic_pass") is True
            and input_integrity.get("pass") is True
            and execution.get("pass") is True
            and execution.get("violation_count") == 0
            and execution.get("failed_check_counts") == {}
            and evidence.get("status") == "EXTERNAL_AUTHORITY_REQUIRED"
        )
        return PASS_CLASSIFICATION if passed else INVALID_CLASSIFICATION
    except KeyError:
        return INVALID_CLASSIFICATION


def run(seal_path: Path, expected: str, out_dir: Path) -> None:
    _seal, seal_digest = _load_seal(seal_path, expected)
    manifest_path = out_dir / "input_manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"R311 run already exists: {manifest_path}")

    entries: list[dict[str, object]] = []
    eval_input = out_dir.resolve() / "eval_input"
    for pulse_sign, source_entry in SOURCE_PAIR.items():
        source_path = ROOT / source_entry["path"]
        record, source_digest = _read_verified_json(
            source_path, source_entry["sha256"]
        )
        if (
            record.get("round") != "R310"
            or record.get("question") != "Q-0066"
            or record.get("controller") != pulse_sign
            or record.get("scenario") != "op0_edge_0"
        ):
            raise RuntimeError(f"R311 source identity mismatch for {pulse_sign}")
        view = build_guarded_fresh_stage1_eval_view(
            record,
            source_path=source_entry["path"],
            source_sha256=source_digest,
        )
        destination = eval_input / f"op0_edge_0__{pulse_sign}.json"
        view_digest = _write_new_json(destination, view)
        entries.append(
            {
                "controller": pulse_sign,
                "scenario": "op0_edge_0",
                "source_path": source_entry["path"],
                "source_sha256": source_digest,
                "view_path": _path_text(destination),
                "view_sha256": view_digest,
                "guards": EXPECTED_GUARDS,
            }
        )

    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "record_count": len(entries),
        "records": entries,
        "physical_trace_rerun": False,
        "r310_amendment": False,
        "effect_interpretation_authorized": False,
        "training_authorized": False,
    }
    manifest_digest = _write_new_json(manifest_path, manifest)

    from andes_rl_kundur.evaluation.eval_v2 import (
        evaluate_trace_directory,
        write_scorecard,
    )

    scorecard = evaluate_trace_directory(
        eval_input,
        baseline="positive",
        execution_profile="vector_power",
        required_active_window_seconds=1.0,
        bootstrap_resamples=EVAL_BOOTSTRAP_RESAMPLES,
        bootstrap_seed=EVAL_BOOTSTRAP_SEED,
    )
    outputs = write_scorecard(scorecard, out_dir / "eval", overwrite=False)
    print(f"input_manifest_sha256={manifest_digest}", flush=True)
    print(f"diagnostic_pass={scorecard['validity']['diagnostic_pass']}", flush=True)
    print(json.dumps(outputs, indent=2), flush=True)


def analyse(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    manifest, manifest_digest = _read_verified_json(out_dir / "input_manifest.json")
    if (
        manifest.get("seal_sha256") != seal_digest
        or manifest.get("record_count") != 2
        or manifest.get("physical_trace_rerun") is not False
        or manifest.get("r310_amendment") is not False
        or manifest.get("training_authorized") is not False
    ):
        raise RuntimeError("R311 input manifest contract mismatch")

    observed_sources: dict[str, str] = {}
    for entry in manifest["records"]:
        view, view_digest = _read_verified_json(
            ROOT / entry["view_path"], entry["view_sha256"]
        )
        if view_digest != entry["view_sha256"]:
            raise RuntimeError("R311 view digest mismatch")
        binding = view.get("source_record")
        if not isinstance(binding, Mapping):
            raise RuntimeError("R311 view source binding is missing")
        if (
            binding.get("path") != entry["source_path"]
            or binding.get("sha256") != entry["source_sha256"]
            or view.get("guards") != EXPECTED_GUARDS
        ):
            raise RuntimeError("R311 guarded-view contract mismatch")
        _read_verified_json(
            ROOT / entry["source_path"], entry["source_sha256"]
        )
        observed_sources[str(entry["controller"])] = str(entry["source_sha256"])
    expected_sources = {
        name: str(entry["sha256"]) for name, entry in SOURCE_PAIR.items()
    }
    if observed_sources != expected_sources:
        raise RuntimeError("R311 source-pair binding mismatch")

    scorecard_path = out_dir / "eval/scorecard.json"
    scorecard, scorecard_digest = _read_verified_json(scorecard_path)
    classification = classify_scorecard(scorecard)
    execution = scorecard["validity"]["execution_contract"]
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "classification": classification,
        "seal_sha256": seal_digest,
        "input_manifest_sha256": manifest_digest,
        "eval_scorecard_sha256": scorecard_digest,
        "source_bindings_verified": True,
        "eval_input_integrity_pass": scorecard["validity"]["input_integrity"][
            "pass"
        ],
        "eval_execution_contract_pass": execution["pass"],
        "eval_execution_violation_count": execution["violation_count"],
        "eval_failed_check_counts": execution["failed_check_counts"],
        "eval_diagnostic_pass": scorecard["validity"]["diagnostic_pass"],
        "evidence_status": scorecard["evidence_status"]["status"],
        "r310_amended": False,
        "physical_trace_rerun": False,
        "effect_interpretation_authorized": False,
        "fresh_stage1_design_review_eligible": classification
        == PASS_CLASSIFICATION,
        "training_authorized": False,
    }
    analysis_digest = _write_new_json(out_dir / "analysis.json", analysis)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal": {"path": _path_text(seal_path), "sha256": seal_digest},
        "input_manifest": {
            "path": _path_text(out_dir / "input_manifest.json"),
            "sha256": manifest_digest,
        },
        "eval_scorecard": {
            "path": _path_text(scorecard_path),
            "sha256": scorecard_digest,
        },
        "analysis": {
            "path": _path_text(out_dir / "analysis.json"),
            "sha256": analysis_digest,
        },
        "sources_verified": seal["sources"],
        "source_pair": SOURCE_PAIR,
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "r310_amended": False,
        "training_authorized": False,
    }
    provenance_digest = _write_new_json(out_dir / "provenance.json", provenance)
    print(f"classification={classification}", flush=True)
    print(f"analysis_sha256={analysis_digest}", flush=True)
    print(f"provenance_sha256={provenance_digest}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    for command in ("run", "analyse"):
        subparser = commands.add_parser(command)
        subparser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
        subparser.add_argument("--expected-seal-sha256", required=True)
        subparser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        prepare(args.seal)
    elif args.command == "run":
        run(args.seal, args.expected_seal_sha256, args.out_dir)
    else:
        analyse(args.seal, args.expected_seal_sha256, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
