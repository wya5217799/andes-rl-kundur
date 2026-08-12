"""Outcome-blind R369 reanalysis of the immutable R368 physical bank.

Only the actuator-mapping absolute tolerance changes.  Its value is derived
from the half-ULP error bound for binary32 multiplication at the frozen decoder
full scale.  The probe executes no simulator and exposes no training surface.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.evaluation.deterministic_headroom import (  # noqa: E402
    build_contract,
    classify_summaries,
    summarise_record,
)


ROUND_ID = "R369"
QUESTION_ID = "Q-0103"
PARENT_SEAL = ROOT / "memory/rounds/R368/formal_seal.json"
PARENT_EXECUTION = (
    ROOT
    / "results/research_loop/r368_deterministic_headroom/formal_execution.json"
)
PARENT_ANALYSIS = (
    ROOT / "results/research_loop/r368_deterministic_headroom/formal_analysis.json"
)
DEFAULT_OUTPUT = (
    ROOT / "results/research_loop/r369_actuator_mapping_reanalysis/analysis.json"
)
EXPECTED_INPUT_HASHES = {
    "parent_seal": "59163fc1b706af389351a817b678cf34744052baba881154b1c97bb8ce5d129e",
    "parent_execution": "6c75a4bd2bc0b6648ba09d2146a17d8aec1dcf2004307fcd6a568e1c6a143164",
    "parent_analysis": "4b25f418f0c3b3fadf032d58cb0232f7ac69f5ea3a943a0e1dfbb99fb3264f6c",
}
EXPECTED_SOURCE_HASHES = {
    "classifier": "c5dbe98b0b996a947f4a6ec7ba47b3d43495774c2c543501c9a6d30e3b86ed46",
    "base_environment": "1797c658aa52a788a5e26782fc2c7fa71b7dccfac3c2dc5de7d6ce6e4432fe34",
    "controller": "801ee600e54e82f14def5c0c1a59f419a961f0aa7abee1ec0a23f2e375866667",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _read_verified_json(path: Path, expected_sha256: str) -> dict[str, Any]:
    observed = _sha256(path)
    if observed != expected_sha256:
        raise ValueError(f"hash mismatch for {path}: {observed}")
    sidecar = path.with_name(path.name + ".sha256")
    if sidecar.read_text(encoding="ascii").split()[0] != expected_sha256:
        raise ValueError(f"sidecar mismatch for {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return payload


def binary32_half_ulp_bound(decoder_full_scale: float) -> float:
    """Return the round-to-nearest half-ULP bound at one positive scale."""

    scale = float(decoder_full_scale)
    if not np.isfinite(scale) or scale <= 0.0:
        raise ValueError("decoder full scale must be finite and positive")
    scale32 = np.float32(scale)
    if float(scale32) != scale:
        raise ValueError("decoder full scale must be exactly representable in binary32")
    return float(np.spacing(scale32) / np.float32(2.0))


def contract_diff_paths(left: object, right: object, prefix: str = "") -> list[str]:
    """Return stable JSON-pointer-like paths whose values differ."""

    if isinstance(left, Mapping) and isinstance(right, Mapping):
        paths: list[str] = []
        for key in sorted(set(left) | set(right)):
            child = f"{prefix}/{key}"
            if key not in left or key not in right:
                paths.append(child)
            else:
                paths.extend(contract_diff_paths(left[key], right[key], child))
        return paths
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return [prefix]
        paths = []
        for index, (left_value, right_value) in enumerate(zip(left, right, strict=True)):
            paths.extend(
                contract_diff_paths(left_value, right_value, f"{prefix}/{index}")
            )
        return paths
    return [] if left == right else [prefix]


def build_corrected_contract(parent_contract: Mapping[str, Any]) -> dict[str, Any]:
    """Change only the mapping tolerance using the registered arithmetic bound."""

    corrected = deepcopy(dict(parent_contract))
    decoder = corrected.get("decoder")
    if not isinstance(decoder, dict):
        raise ValueError("parent contract has no decoder mapping")
    maximum_scale = max(
        abs(float(decoder["delta_m_negative"])),
        abs(float(decoder["delta_m_positive"])),
        abs(float(decoder["delta_d_negative"])),
        abs(float(decoder["delta_d_positive"])),
    )
    decoder["mapping_atol"] = binary32_half_ulp_bound(maximum_scale)
    differences = contract_diff_paths(parent_contract, corrected)
    if differences != ["/decoder/mapping_atol"]:
        raise ValueError(f"unexpected corrected-contract differences: {differences}")
    return corrected


def validate_parent_headers(
    parent_analysis: Mapping[str, Any],
    execution: Mapping[str, Any],
) -> None:
    """Fail closed unless the input is exactly the registered invalid complete bank."""

    checks = parent_analysis.get("checks")
    if parent_analysis.get("classification") != "ANALYSIS-INVALID":
        raise ValueError("parent analysis is not the registered invalid result")
    if not isinstance(checks, Mapping) or checks != {
        "all_rows_valid": False,
        "complete_bank": True,
        "reward_unused": True,
        "training_forbidden": True,
    }:
        raise ValueError("parent invalidity checks do not match the registered gate")
    if parent_analysis.get("training_authorized") is not False:
        raise ValueError("parent analysis training flag must be false")
    summaries = parent_analysis.get("summaries")
    records = execution.get("records")
    if not isinstance(summaries, list) or len(summaries) != 80:
        raise ValueError("parent analysis must contain 80 summaries")
    if (
        not isinstance(records, list)
        or len(records) != 80
        or int(execution.get("record_count", -1)) != 80
    ):
        raise ValueError("execution must contain the complete 80-record bank")
    if execution.get("training_executed") is not False:
        raise ValueError("execution training flag must be false")
    if any(
        record.get("completed") is not True
        or record.get("tds_failed") is not False
        or record.get("training_executed") is not False
        for record in records
    ):
        raise ValueError("every execution record must be complete and nonfailed")


def _verify_sources() -> dict[str, dict[str, str]]:
    paths = {
        "classifier": ROOT
        / "src/andes_rl_kundur/evaluation/deterministic_headroom.py",
        "base_environment": ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
        "controller": ROOT / "src/andes_rl_kundur/control/per_vsg_md.py",
    }
    result: dict[str, dict[str, str]] = {}
    for name, path in paths.items():
        observed = _sha256(path)
        if observed != EXPECTED_SOURCE_HASHES[name]:
            raise ValueError(f"source hash mismatch for {name}: {observed}")
        result[name] = {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": observed,
        }
    return result


def build_reanalysis() -> dict[str, Any]:
    """Verify inputs and return the single R369 corrected classification."""

    source_manifest = _verify_sources()
    parent_seal = _read_verified_json(PARENT_SEAL, EXPECTED_INPUT_HASHES["parent_seal"])
    execution = _read_verified_json(
        PARENT_EXECUTION, EXPECTED_INPUT_HASHES["parent_execution"]
    )
    parent_analysis = _read_verified_json(
        PARENT_ANALYSIS, EXPECTED_INPUT_HASHES["parent_analysis"]
    )
    validate_parent_headers(parent_analysis, execution)
    parent_contract = parent_seal.get("contract")
    if not isinstance(parent_contract, dict) or parent_contract != build_contract():
        raise ValueError("sealed parent contract differs from preserved classifier contract")
    corrected_contract = build_corrected_contract(parent_contract)
    records = execution["records"]
    summaries = [
        summarise_record(record, contract=corrected_contract) for record in records
    ]
    decision = classify_summaries(summaries, contract=corrected_contract)
    mapping_pass_count = sum(
        summary["actuator_mapping_pass"] is True for summary in summaries
    )
    if mapping_pass_count != len(summaries):
        decision = {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "classification": "ANALYSIS-INVALID",
            "checks": {"all_corrected_mapping_guards_pass": False},
            "training_authorized": False,
        }
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "classification": decision["classification"],
        "source_manifest": source_manifest,
        "input_manifest": {
            "parent_seal": {
                "path": PARENT_SEAL.relative_to(ROOT).as_posix(),
                "sha256": EXPECTED_INPUT_HASHES["parent_seal"],
            },
            "parent_execution": {
                "path": PARENT_EXECUTION.relative_to(ROOT).as_posix(),
                "sha256": EXPECTED_INPUT_HASHES["parent_execution"],
            },
            "parent_analysis": {
                "path": PARENT_ANALYSIS.relative_to(ROOT).as_posix(),
                "sha256": EXPECTED_INPUT_HASHES["parent_analysis"],
            },
        },
        "tolerance_derivation": {
            "arithmetic": "IEEE-754 binary32 round-to-nearest multiplication",
            "maximum_decoder_scale": 600.0,
            "largest_relevant_binade": "[512,1024)",
            "half_ulp_expression": "2^(9-24)=2^-15",
            "parent_mapping_atol": float(parent_contract["decoder"]["mapping_atol"]),
            "corrected_mapping_atol": float(
                corrected_contract["decoder"]["mapping_atol"]
            ),
            "relative_tolerance": 0.0,
            "performance_endpoints_used": False,
        },
        "contract_diff_paths": contract_diff_paths(parent_contract, corrected_contract),
        "corrected_contract": corrected_contract,
        "corrected_contract_sha256": hashlib.sha256(
            _canonical_bytes(corrected_contract)
        ).hexdigest(),
        "parent_invalidity": {
            "classification": parent_analysis["classification"],
            "checks": parent_analysis["checks"],
        },
        "corrected_mapping_pass_count": mapping_pass_count,
        "corrected_summary_count": len(summaries),
        "decision": decision,
        "summaries": summaries,
        "physical_rerun_executed": False,
        "reward_used_for_gate": False,
        "training_authorized": False,
        "claim_scope": "finite R368 development bank only",
    }


def write_reanalysis(output: Path) -> str:
    if output.exists() or output.with_name(output.name + ".sha256").exists():
        raise FileExistsError(f"refusing to overwrite R369 analysis: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical_bytes(build_reanalysis())
    with output.open("xb") as handle:
        handle.write(data)
    digest = hashlib.sha256(data).hexdigest()
    with output.with_name(output.name + ".sha256").open(
        "x", encoding="ascii", newline="\n"
    ) as handle:
        handle.write(f"{digest}  {output.name}\n")
    return digest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    digest = write_reanalysis(args.output.resolve())
    print(f"analysis_sha256={digest}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
