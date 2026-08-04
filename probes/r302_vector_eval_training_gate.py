#!/usr/bin/env python3
"""Decide vector-EVAL readiness and whether neural training is justified.

This probe binds the architecture-aware EVAL-v2 replay to the current formal
decision chain.  It does not recalculate controller efficacy and cannot grant
paper-evidence status.  It only answers the prospective engineering/research
gate: is there both a valid evaluator and a named adaptive mechanism worth one
neural smoke run?

Usage::

    python probes/r302_vector_eval_training_gate.py

The output is create-only and receives a sibling ``.sha256`` sidecar.  Missing
or mismatched input sidecars, malformed decision fields, or a pre-existing
output fail closed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVAL = ROOT / "results/r302_vector_eval_training_gate/eval_v2_r300_scorecard.json"
DEFAULT_R292 = ROOT / "results/r292_formal_evaluation_v3/formal_summary.json"
DEFAULT_R299 = ROOT / "results/r299_edge_information_probe/development_summary.json"
DEFAULT_R300 = ROOT / "results/r300_fixed_2kv_formal/formal_summary.json"
DEFAULT_R301 = ROOT / "results/r301_relative_rocof_margin/analysis_summary.json"
DEFAULT_OUTPUT = ROOT / "results/r302_vector_eval_training_gate/analysis_summary.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_verified(path: Path) -> tuple[dict[str, Any], str]:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not path.is_file() or not sidecar.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"missing input or sidecar: {path}")
    observed = _sha256(path)
    expected = sidecar.read_text(encoding="ascii").strip().split()[0]
    if observed != expected:
        raise RuntimeError(f"input hash mismatch: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"input root must be an object: {path}")
    return payload, observed


def _source(path: Path, digest: str) -> dict[str, str]:
    try:
        display = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        display = str(path.resolve())
    return {"path": display, "sha256": digest}


def build_summary(
    *,
    eval_path: Path,
    r292_path: Path,
    r299_path: Path,
    r300_path: Path,
    r301_path: Path,
) -> dict[str, Any]:
    loaded = {
        "eval_v2_r300": _load_verified(eval_path),
        "r292_neural_formal": _load_verified(r292_path),
        "r299_adaptive_headroom": _load_verified(r299_path),
        "r300_fixed_2kv_formal": _load_verified(r300_path),
        "r301_model_margin": _load_verified(r301_path),
    }
    eval_score = loaded["eval_v2_r300"][0]
    r292 = loaded["r292_neural_formal"][0]
    r299 = loaded["r299_adaptive_headroom"][0]
    r300 = loaded["r300_fixed_2kv_formal"][0]
    r301 = loaded["r301_model_margin"][0]

    eval_pass = bool(
        eval_score.get("contract", {}).get("execution_profile") == "vector_power"
        and eval_score.get("validity", {}).get("diagnostic_pass") is True
        and eval_score.get("validity", {})
        .get("input_integrity", {})
        .get("sidecar_sha256", {})
        .get("verified_count")
        == eval_score.get("source", {}).get("trace_count")
        and eval_score.get("validity", {})
        .get("execution_contract", {})
        .get("violation_count")
        == 0
        and eval_score.get("evidence_status", {}).get("status")
        == "EXTERNAL_AUTHORITY_REQUIRED"
    )

    relative_guards = r292.get("relative_guards_vs_q0", {})
    distributed_rows = {
        name: row
        for name, row in relative_guards.items()
        if str(name).startswith("distributed_edge_s") and isinstance(row, dict)
    }
    distributed_no_harm_seed_count = sum(
        row.get("pass") is True for row in distributed_rows.values()
    )

    analysis = r299.get("analysis", {})
    oracle = analysis.get("oracle_over_best_fixed", {})
    thresholds = r299.get("thresholds", {})
    adaptive_fast_limit = float(thresholds.get("adaptive_fast_ratio_max", 0.99))
    adaptive_sync_limit = float(thresholds.get("adaptive_sync_ratio_max", 0.99))
    fast_ratio = float(oracle.get("fast_inter_area_iae_hz_s", math.inf))
    sync_ratio = float(oracle.get("normalized_sync_loss_hz2", math.inf))
    adaptive_headroom = bool(
        fast_ratio <= adaptive_fast_limit and sync_ratio <= adaptive_sync_limit
    )
    local_signal = analysis.get("local_information_signal", {})
    pooled_spearman = float(local_signal.get("pooled_spearman", math.nan))
    local_signal_limit = float(thresholds.get("local_spearman_min", 0.5))
    local_information_signal = bool(
        math.isfinite(pooled_spearman) and pooled_spearman >= local_signal_limit
    )

    baseline_valid = r300.get("classification") == "VALID-2KV-PASS"
    blind_gain_closed = bool(
        r301.get("classification") == "2KV-SUFFICIENT-NO-BLIND-ESCALATION"
        and r301.get("next_action", {}).get("nonlinear_higher_gain_probe_authorized")
        is False
    )
    prior_neural_invalid = bool(
        r292.get("decision", {}).get("classification") == "INVALID"
        and r292.get("decision", {})
        .get("validity_guards", {})
        .get("relative_no_harm_all_candidate_arms")
        is False
    )
    training_prerequisites = {
        "reproducible_2kv_failure_axis": False,
        "local_information_necessity_demonstrated": False,
        "matched_classical_comparator_frozen": baseline_valid,
        "neural_action_authority_frozen": False,
        "pretraining_kill_probe_passed": False,
    }
    missing_prerequisites = [
        name for name, passed in training_prerequisites.items() if not passed
    ]
    # R302 can diagnose current readiness but cannot manufacture the prospective
    # mechanism evidence that a later round must supply.
    training_authorized = False
    if not eval_pass:
        classification = "VECTOR-EVAL-INVALID"
    elif not baseline_valid:
        classification = "FIXED-2KV-BASELINE-NOT-VALID"
    else:
        classification = "EVAL-READY-TRAINING-BLOCKED"

    return {
        "schema_version": 1,
        "round": "R302",
        "question": "Q-0059",
        "classification": classification,
        "evaluator_gate": {
            "passed": eval_pass,
            "execution_profile": eval_score.get("contract", {}).get("execution_profile"),
            "trace_count": eval_score.get("source", {}).get("trace_count"),
            "verified_sidecar_count": eval_score.get("validity", {})
            .get("input_integrity", {})
            .get("sidecar_sha256", {})
            .get("verified_count"),
            "execution_violation_count": eval_score.get("validity", {})
            .get("execution_contract", {})
            .get("violation_count"),
            "evidence_status": eval_score.get("evidence_status", {}).get("status"),
        },
        "prior_result_chain": {
            "r292_neural_formal_classification": r292.get("decision", {}).get(
                "classification"
            ),
            "r292_relative_no_harm_all_candidate_arms": r292.get("decision", {})
            .get("validity_guards", {})
            .get("relative_no_harm_all_candidate_arms"),
            "r299_classification": r299.get("classification"),
            "r299_oracle_over_best_fixed_registered_ratios": {
                "fast_inter_area_iae_hz_s": fast_ratio,
                "normalized_sync_loss_hz2": sync_ratio,
            },
            "r299_pooled_local_spearman": pooled_spearman,
            "r300_classification": r300.get("classification"),
            "r301_classification": r301.get("classification"),
        },
        "training_gate": {
            "authorized": training_authorized,
            "valid_fixed_2kv_baseline": baseline_valid,
            "adaptive_headroom_identified": adaptive_headroom,
            "local_information_association_pass": local_information_signal,
            "prior_neural_formal_invalid": prior_neural_invalid,
            "prior_distributed_no_harm_seed_count": distributed_no_harm_seed_count,
            "prior_distributed_seed_count": len(distributed_rows),
            "blind_gain_escalation_closed": blind_gain_closed,
            "prospective_prerequisites": training_prerequisites,
            "missing_prerequisites": missing_prerequisites,
            "reason": (
                "No registered adaptive margin over fixed 2Kv and no sufficient "
                "local-information necessity are established; the neural action "
                "authority and pre-training kill probe are also not frozen, and "
                "prior distributed TD3 failed the formal relative no-harm gate."
            ),
        },
        "next_probe": {
            "train_neural_agent": training_authorized,
            "objective": (
                "Test whether heterogeneous per-device power/SOC headroom makes "
                "independent projection break the executed differential zero-sum "
                "seam, then test a deterministic headroom-aware edge allocator."
            ),
            "neural_condition": (
                "Only a deterministic probe showing a reproducible 2Kv failure and "
                "local-information value may authorize one separately sealed smoke."
            ),
        },
        "claim_boundary": (
            "Infrastructure and training-readiness decision only; R300 formal summary "
            "remains performance authority. No neural, MARL, pure-architecture, hard-"
            "decoupling, stability, topology, safety, or deployment claim."
        ),
        "sources": {
            name: _source(path, loaded[name][1])
            for name, path in (
                ("eval_v2_r300", eval_path),
                ("r292_neural_formal", r292_path),
                ("r299_adaptive_headroom", r299_path),
                ("r300_fixed_2kv_formal", r300_path),
                ("r301_model_margin", r301_path),
            )
        },
    }


def _write_new(path: Path, payload: dict[str, Any]) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"create-only output exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval", type=Path, default=DEFAULT_EVAL)
    parser.add_argument("--r292", type=Path, default=DEFAULT_R292)
    parser.add_argument("--r299", type=Path, default=DEFAULT_R299)
    parser.add_argument("--r300", type=Path, default=DEFAULT_R300)
    parser.add_argument("--r301", type=Path, default=DEFAULT_R301)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = _parser().parse_args()
    summary = build_summary(
        eval_path=args.eval,
        r292_path=args.r292,
        r299_path=args.r299,
        r300_path=args.r300,
        r301_path=args.r301,
    )
    digest = _write_new(args.output, summary)
    print(
        json.dumps(
            {
                "classification": summary["classification"],
                "training_authorized": summary["training_gate"]["authorized"],
                "output": str(args.output.resolve()),
                "sha256": digest,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
