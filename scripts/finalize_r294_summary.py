#!/usr/bin/env python3
"""Create R294's derived round-level decision pointer from sealed stages."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results/r294_model_validation/round_summary.json"
SOURCES = {
    "stage_a": ROOT / "results/r294_model_validation/stage_a/stage_a_summary.json",
    "stage_b": ROOT / "results/r294_model_validation/stage_b/stage_b_summary.json",
    "stage_c": ROOT / "results/r294_model_validation/stage_c_fast_controller_development_v1/development_summary.json",
    "stage_d": ROOT / "results/r294_model_validation/stage_d_compact_controller_validation/formal_summary.json",
    "stage_e": ROOT / "results/r294_model_validation/stage_e_decentralized_execution/execution_summary.json",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sidecar(path: Path) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not path.is_file() or not sidecar.is_file():
        raise RuntimeError(f"missing artifact or sidecar: {path}")
    observed = sha256_file(path)
    expected = sidecar.read_text(encoding="ascii").split()[0]
    if observed != expected:
        raise RuntimeError(f"hash mismatch: {path}")
    return observed


def write_new(path: Path, payload: Any) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"create-only artifact exists: {path}")
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as handle:
        handle.write(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    with sidecar.open("x", encoding="ascii") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def main() -> None:
    documents = {}
    source_hashes = {}
    for name, path in SOURCES.items():
        source_hashes[name] = {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": verify_sidecar(path),
        }
        documents[name] = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "stage_a_model": "STAGE-A-NONLINEAR-OR-NARROWER-DOMAIN-REQUIRED",
        "stage_a_decoupling": "DECOUPLING-NO-GO",
        "stage_b": "VALID-BUDGET-NORMALIZED-AUTHORITY-MAP",
        "stage_c": "FAST-DEVELOPMENT-CANDIDATES-IDENTIFIED",
        "stage_d": "VALID-BOTH-VECTOR-CONTROLLERS-PASS",
        "stage_e": "DECENTRALIZED-EXECUTION-EQUIVALENT",
    }
    observed = {
        "stage_a_model": documents["stage_a"]["model_decision"],
        "stage_a_decoupling": documents["stage_a"]["decoupling_decision"],
        "stage_b": documents["stage_b"]["classification"],
        "stage_c": documents["stage_c"]["classification"],
        "stage_d": documents["stage_d"]["classification"],
        "stage_e": documents["stage_e"]["classification"],
    }
    if observed != expected:
        raise RuntimeError(f"unexpected R294 stage decisions: {observed}")
    payload = {
        "schema_version": 1,
        "round": "R294",
        "question": "Q-0051",
        "classification": "MODEL-FIRST-DISTRIBUTED-BASELINE-VALIDATED-PARTIAL",
        "stage_decisions": observed,
        "valid_record_counts": {
            "stage_a": documents["stage_a"]["record_count"],
            "stage_b": documents["stage_b"]["record_count"],
            "stage_c_development": documents["stage_c"]["record_count"],
            "stage_d_formal": documents["stage_d"]["guards"]["record_count"],
            "stage_e_execution": documents["stage_e"]["guards"]["record_count"],
        },
        "controller_result": {
            "central_vector_gate_pass": documents["stage_d"]["candidate_gates"]["central_vector__ks1"]["passed"],
            "distributed_dapi_gate_pass": documents["stage_d"]["candidate_gates"]["distributed_dapi__ks1"]["passed"],
            "executed_formulation_contrast": documents["stage_d"]["executed_formulation_contrast"],
            "explicit_local_agent_execution_equivalent": True,
        },
        "resolution": {
            "model": "full nonlinear DAE truth; coarse static LPV rejected; trajectory-local linearization remains eligible but predictive fidelity is unvalidated",
            "coupling": "hard decoupling rejected; control must retain or compensate cross-coupling",
            "actuator": "active power is the dominant budget-normalized common and inter-area channel under the tested contract",
            "deterministic_controller": "coupling-aware vector PI and explicit neighbour-local DAPI both pass versus scalar equal-sharing PI",
            "architecture": "no joint centralized-versus-distributed winner; pure architecture value is not identified",
            "neural": "not executed and not evidenced",
        },
        "question_disposition": "closed-partial",
        "claim_boundary": (
            "one fixed modified Kundur plant and the named deterministic controllers; "
            "no hard decoupling, validated LPV/MPC, pure architecture, MARL/neural, "
            "topology-generalization, stability, safety, or deployment claim"
        ),
        "sources": source_hashes,
    }
    digest = write_new(OUTPUT, payload)
    print(f"classification={payload['classification']}")
    print(f"summary_sha256={digest}")


if __name__ == "__main__":
    main()
