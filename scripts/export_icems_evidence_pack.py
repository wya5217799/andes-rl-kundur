#!/usr/bin/env python3
"""Build the paper-facing ICEMS evidence pack from immutable R274-R278 results."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT / "docs/research/evidence/icems2026_evidence_pack.json"
)
PAPER_TITLE = (
    "Decoupling-Oriented Coordination of Paralleled VSGs With "
    "Multi-Agent Reinforcement Learning"
)

SUMMARY_PATHS = {
    "R274": ROOT
    / "results/r274_prospective_active_power_authority/"
    "active_power_authority_summary.json",
    "R275": ROOT
    / "results/r275_fast_md_authority/fast_md_authority_summary.json",
    "R276": ROOT
    / "results/r276_fast_slow_factorial/fast_slow_factorial_summary.json",
    "R277": ROOT
    / "results/r277_learning_gap_oracle/learning_gap_oracle_summary.json",
    "R278_original": ROOT
    / "results/r278_icems_residual_pilot_s49/"
    "icems_residual_pilot_summary.json",
    "R278_repair": ROOT / "memory/rounds/R278/analysis_repair.json",
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _sidecar_digest(path: Path) -> str:
    sidecar = path.with_name(path.name + ".sha256")
    if not sidecar.is_file():
        raise FileNotFoundError(f"missing SHA-256 sidecar: {_relative(sidecar)}")
    fields = sidecar.read_text(encoding="utf-8").strip().split()
    if not fields:
        raise ValueError(f"empty SHA-256 sidecar: {_relative(sidecar)}")
    digest = fields[0].lower()
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError(f"invalid SHA-256 sidecar: {_relative(sidecar)}")
    return digest


def _verified_bytes(path: Path, expected_sha256: str | None = None) -> bytes:
    if not path.is_file():
        raise FileNotFoundError(f"missing evidence source: {_relative(path)}")
    expected = expected_sha256 or _sidecar_digest(path)
    data = path.read_bytes()
    actual = _sha256_bytes(data)
    if actual != expected:
        raise ValueError(
            f"hash mismatch for {_relative(path)}: expected {expected}, got {actual}"
        )
    return data


def _verified_json(
    path: Path,
    expected_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    data = _verified_bytes(path, expected_sha256)
    payload = json.loads(data.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {_relative(path)}")
    return payload, _sha256_bytes(data)


def _source(path: Path, digest: str) -> dict[str, str]:
    return {"path": _relative(path), "sha256": digest}


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def build_evidence_pack() -> dict[str, Any]:
    loaded: dict[str, dict[str, Any]] = {}
    sources: list[dict[str, str]] = []
    for name, path in SUMMARY_PATHS.items():
        payload, digest = _verified_json(path)
        loaded[name] = payload
        sources.append(_source(path, digest))

    r274 = loaded["R274"]
    r275 = loaded["R275"]
    r276 = loaded["R276"]
    r277 = loaded["R277"]
    r278_original = loaded["R278_original"]
    r278_repair = loaded["R278_repair"]

    expected_classes = {
        "R274": "AUTHORITY-POSITIVE",
        "R275": "FAST-LAYER-POSITIVE",
        "R276": "ADDITIVE-ONLY",
        "R277": "LEARNING-GAP-PRESENT",
    }
    for round_id, expected in expected_classes.items():
        actual = loaded[round_id]["decision"]["classification"]
        if actual != expected:
            raise ValueError(
                f"{round_id} classification drift: expected {expected}, got {actual}"
            )

    if r278_original["decision"]["classification"] != "INVALID":
        raise ValueError("R278 immutable summary is no longer the retained INVALID result")
    if r278_repair["decision"]["classification"] != "PILOT-NO-GO":
        raise ValueError("R278 repaired decision is no longer PILOT-NO-GO")
    if r278_repair["evidence_role"] != "viewed_development_only":
        raise ValueError("R278 evidence role drifted from viewed development only")
    if (
        r278_repair["repair"]["trajectory_or_bootstrap_changes"]
        or r278_repair["repair"]["retraining"]
    ):
        raise ValueError("R278 audit repair is no longer analysis-only")
    if r278_repair["decision"]["guards"]["both_primary_endpoints_clear"]:
        raise ValueError("R278 unexpectedly clears the registered two-endpoint gate")

    primary = r278_repair["decision"]["primary_endpoints"]
    if not primary["normalized_sync_loss_hz2"]["material_improvement"]:
        raise ValueError("R278 synchronization endpoint no longer clears")
    if primary["fast_inter_area_iae_hz_s"]["material_improvement"]:
        raise ValueError("R278 inter-area endpoint unexpectedly clears")

    training = r278_original["training"]
    training_summary_path = ROOT / training["training_summary_path"]
    training_summary, training_summary_digest = _verified_json(
        training_summary_path,
        training["training_summary_sha256"],
    )
    sources.append(_source(training_summary_path, training_summary_digest))
    if (
        training_summary["episodes_completed"] != 300
        or training_summary["total_steps"] != 4500
        or not training_summary["all_completed"]
        or training_summary["failed"]
    ):
        raise ValueError("R278 training completion contract is not satisfied")

    checkpoint_path = ROOT / training["checkpoint_path"]
    _verified_bytes(checkpoint_path, training["checkpoint_sha256"])
    sources.append(_source(checkpoint_path, training["checkpoint_sha256"]))

    controller_contract_path = ROOT / training["controller_contract_path"]
    controller_contract, controller_contract_digest = _verified_json(
        controller_contract_path,
        training["controller_contract_sha256"],
    )
    sources.append(_source(controller_contract_path, controller_contract_digest))

    return {
        "schema_version": 1,
        "evidence_cutoff": "2026-07-26",
        "paper_title": PAPER_TITLE,
        "manuscript_decision": {
            "readiness": "CONDITIONAL_HONEST_EVALUATION_ONLY",
            "marl_incremental_value": "NO-ADAPTIVE-MARL-VALUE",
            "positive_marl_superiority_supported": False,
            "three_seed_continuation_authorized": False,
            "fresh_formal_bank_authorized": False,
            "hawe_contribution_authorized": False,
        },
        "stages": {
            "R274": {
                "role": "slow_common_frequency_authority",
                "decision": r274["decision"],
                "completion_pairing": r274["completion_pairing"],
            },
            "R275": {
                "role": "fast_common_inertia_authority",
                "decision": r275["decision"],
                "completion_pairing": r275["completion_pairing"],
            },
            "R276": {
                "role": "fast_slow_factorial_interaction",
                "decision": r276["decision"],
                "completion_pairing": r276["completion_pairing"],
            },
            "R277": {
                "role": "outcome_seeing_attainability_upper_bound",
                "decision": r277["decision"],
                "completion_pairing": r277["completion_pairing"],
                "oracle_role": r277["oracle_selection"]["role"],
                "nonbaseline_selection_count": r277["oracle_selection"][
                    "nonbaseline_selection_count"
                ],
                "selection_counts": r277["oracle_selection"]["selection_counts"],
            },
            "R278": {
                "role": "single_seed_viewed_development_gate",
                "original_decision": r278_original["decision"],
                "repaired_decision": r278_repair["decision"],
                "completion_pairing": r278_original["completion_pairing"],
                "repair": r278_repair["repair"],
                "training": {
                    "seed": training_summary["seed"],
                    "episodes_completed": training_summary["episodes_completed"],
                    "total_steps": training_summary["total_steps"],
                    "all_completed": training_summary["all_completed"],
                    "failed": training_summary["failed"],
                    "checkpoint_path": training["checkpoint_path"],
                    "checkpoint_sha256": training["checkpoint_sha256"],
                    "controller_contract_path": training["controller_contract_path"],
                    "controller_contract_sha256": training[
                        "controller_contract_sha256"
                    ],
                    "algorithm": controller_contract["algorithm"],
                    "action_and_reward": controller_contract["action_and_reward"],
                },
            },
        },
        "claim_boundaries": {
            "supported": [
                "bounded_slow_active_power_has_common_frequency_authority",
                "frozen_fast_common_inertia_adds_transient_value",
                "fast_and_slow_benefits_are_largely_additive",
                "a_viewed_bank_differential_attainability_margin_exists",
                "seed49_improves_synchronization_with_paired_support",
                "seed49_respects_registered_action_storage_and_safety_guards",
            ],
            "unsupported": [
                "marl_reliably_improves_both_coprimary_endpoints",
                "marl_generalizes_across_training_seeds",
                "marl_generalizes_to_an_unseen_formal_bank",
                "hawe_adds_value_beyond_a_selected_seed",
                "the_actuator_is_a_unified_physical_gfm_bess",
                "topology_or_deployment_generalization",
            ],
        },
        "sources": sorted(sources, key=lambda item: item["path"]),
    }


def write_evidence_pack(output: Path) -> str:
    payload = build_evidence_pack()
    data = _canonical_bytes(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    digest = _sha256_bytes(data)
    output.with_name(output.name + ".sha256").write_text(
        f"{digest}  {output.name}\n",
        encoding="utf-8",
    )
    return digest


def check_evidence_pack(output: Path) -> str:
    expected_data = _canonical_bytes(build_evidence_pack())
    if not output.is_file():
        raise FileNotFoundError(f"missing generated evidence pack: {_relative(output)}")
    actual_data = output.read_bytes()
    if actual_data != expected_data:
        raise ValueError(
            f"stale generated evidence pack: {_relative(output)}; rerun with --write"
        )
    digest = _sha256_bytes(actual_data)
    if _sidecar_digest(output) != digest:
        raise ValueError(f"evidence-pack sidecar mismatch: {_relative(output)}")
    return digest


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    output = args.output.resolve()
    digest = (
        write_evidence_pack(output)
        if args.write
        else check_evidence_pack(output)
    )
    print(f"{_relative(output)} sha256={digest}")


if __name__ == "__main__":
    main()
