#!/usr/bin/env python3
"""Run the R279 no-new-trajectory reviewer identifiability audit."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.reviewer_identifiability import (  # noqa: E402
    ACTIVE_STEPS,
    analyse_seed_policy_actions,
    analyse_signed_h1_pairs,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)

R275_SUMMARY = ROOT / "results/r275_fast_md_authority/fast_md_authority_summary.json"
R277_SUMMARY = ROOT / "results/r277_learning_gap_oracle/learning_gap_oracle_summary.json"
R278_SUMMARY = (
    ROOT / "results/r278_icems_residual_pilot_s49/icems_residual_pilot_summary.json"
)
R278_REPAIR = ROOT / "memory/rounds/R278/analysis_repair.json"
DEFAULT_OUTPUT = ROOT / "results/r279_reviewer_identifiability"


def _verified_json(path: Path) -> dict[str, Any]:
    sidecar = path.with_name(path.name + ".sha256")
    if not sidecar.exists():
        raise FileNotFoundError(f"missing sha256 sidecar for {path}")
    expected = sidecar.read_text(encoding="utf-8").split()[0]
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"hash mismatch for {path}: expected {expected}, got {actual}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def _plain_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def _load_trace_group(
    summary: dict[str, Any],
    *,
    suffix: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    records: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    for path_text, expected in sorted(summary["trace_hashes"].items()):
        path = ROOT / path_text
        if not path.name.endswith(suffix):
            continue
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"sealed trace hash drift: {path_text}")
        record = _plain_json(path)
        scenario = str(record["scenario"])
        if scenario in records:
            raise ValueError(f"duplicate scenario {scenario} for {suffix}")
        if record.get("completed") is not True or record.get("tds_failed") is not False:
            raise ValueError(f"incomplete trace cannot enter audit: {path_text}")
        records[scenario] = record
        hashes[path_text] = actual
    if len(records) != 24:
        raise ValueError(f"expected 24 records for {suffix}, got {len(records)}")
    return records, hashes


def _write_new(path: Path, payload: object) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite R279 artifact: {path}")
    data = canonical_json_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    digest = sha256_bytes(data)
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return digest


def _write_new_text(path: Path, text: str) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite R279 artifact: {path}")
    data = text.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    digest = sha256_bytes(data)
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return digest


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _markdown(audit: dict[str, Any]) -> str:
    policy = audit["seed49_policy_diagnostic"]
    pooled = policy["pooled_active_window"]
    signed = audit["signed_h1_dynamic_decomposition"]
    pos = signed["h1_pos_minus_q0"]
    neg = signed["h1_neg_minus_q0"]
    leakage = signed["aggregate"]["leakage_ratios"]
    return "\n".join(
        [
            "# R279 reviewer identifiability mechanism audit",
            "",
            "This is a read-only diagnostic over sealed R275/R277/R278 traces. It does not relabel R278.",
            "",
            "## Seed-49 policy diagnostic",
            "",
            f"- Step-0 q scenario invariant: `{policy['first_action']['scenario_invariant_at_1e_7']}`; q={policy['first_action']['minimum']:.9f}.",
            f"- Causal correlation with available inter-area frequency: `{pooled['correlation_q_with_available_inter_area_frequency']}`.",
            f"- Causal correlation with available inter-area RoCoF: `{pooled['correlation_q_with_available_inter_area_rocof']}`.",
            f"- Negative-q fraction: `{100.0 * pooled['negative_q_fraction']:.2f}%`; q at >=95% bound: `{100.0 * pooled['q_fraction_at_or_above_95_percent_bound']:.2f}%`; raw-vote saturation: `{100.0 * pooled['raw_vote_saturation_fraction']:.2f}%`.",
            "",
            "## Constant signed h1 effects versus q=0",
            "",
            f"- h1_pos sync-loss ratio of means: `{pos['normalized_sync_loss_hz2']['ratio_of_means_percent']:.3f}%`.",
            f"- h1_pos inter-area IAE ratio of means: `{pos['fast_inter_area_iae_hz_s']['ratio_of_means_percent']:.3f}%`.",
            f"- h1_neg sync-loss ratio of means: `{neg['normalized_sync_loss_hz2']['ratio_of_means_percent']:.3f}%`.",
            f"- h1_neg inter-area IAE ratio of means: `{neg['fast_inter_area_iae_hz_s']['ratio_of_means_percent']:.3f}%`.",
            "",
            "## Dynamic coupling audit",
            "",
            f"- Maximum fleet-mean M shift versus q=0: `{signed['maximum_abs_fleet_mean_m_shift_vs_q0']:.9g}`.",
            f"- Odd common / odd differential IAE: `{leakage['odd_common_to_odd_differential_iae']:.6f}`.",
            f"- Even common / odd differential IAE: `{leakage['even_common_to_odd_differential_iae']:.6f}`.",
            "- Therefore the zero-sum action is an exact budget constraint, not by itself a dynamic-decoupling proof.",
            "",
            "## Consequence for R279",
            "",
            "The historical seed-49 checkpoint is diagnostic only. A causal feedback comparator, a size-matched centralized actor, three new shared-policy seeds, and a fresh disturbance bank remain necessary.",
            "",
        ]
    )


def run(output_dir: Path) -> None:
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    r275 = _verified_json(R275_SUMMARY)
    r277 = _verified_json(R277_SUMMARY)
    r278 = _verified_json(R278_SUMMARY)
    repair = _plain_json(R278_REPAIR)
    if repair["decision"]["classification"] != "PILOT-NO-GO":
        raise ValueError("R278 analysis repair no longer reports PILOT-NO-GO")

    baseline, baseline_hashes = _load_trace_group(r275, suffix="__common_M_pos.json")
    h1_pos, pos_hashes = _load_trace_group(r277, suffix="__h1_pos.json")
    h1_neg, neg_hashes = _load_trace_group(r277, suffix="__h1_neg.json")
    seed49, seed49_hashes = _load_trace_group(
        r278, suffix="__r278_shared_area_td3.json"
    )
    if not (set(baseline) == set(h1_pos) == set(h1_neg) == set(seed49)):
        raise ValueError("historical scenario sets do not match")

    sample = next(iter(seed49.values()))
    area_contract = sample["controller_config"]["area_residual"]
    q_max = float(area_contract["q_max"])
    dm_max = float(area_contract["dm_max"])
    baseline_m = float(area_contract["baseline_m"])
    baseline_d = float(area_contract["baseline_d"])
    source_hashes = baseline_hashes | pos_hashes | neg_hashes | seed49_hashes

    audit = {
        "schema_version": 1,
        "round": "R279",
        "question": "Q-0041",
        "evidence_role": "historical_read_only_mechanism_diagnostic",
        "historical_decision_unchanged": {
            "round": "R278",
            "classification": "PILOT-NO-GO",
            "analysis_repair_path": str(R278_REPAIR.relative_to(ROOT)),
            "analysis_repair_sha256": sha256_file(R278_REPAIR),
        },
        "seed49_policy_diagnostic": analyse_seed_policy_actions(
            list(seed49.values()), active_steps=ACTIVE_STEPS, q_max=q_max
        ),
        "signed_h1_dynamic_decomposition": analyse_signed_h1_pairs(
            baseline,
            h1_pos,
            h1_neg,
            active_steps=ACTIVE_STEPS,
        ),
        "physical_mapping": {
            "simulator_fields": {"inertia": "M_es", "damping": "D_es"},
            "definition": "M=2H",
            "baseline_m": baseline_m,
            "baseline_h_seconds": baseline_m / 2.0,
            "baseline_d": baseline_d,
            "normalized_m_action_decode": f"delta_M={dm_max:g}*a_M",
            "scalar_residual": "q*[+1,+1,-1,-1]",
            "q_max": q_max,
            "maximum_abs_delta_m_per_device": dm_max * q_max,
            "fleet_mean_delta_m_identity": "mean(delta_M)=0 up to trace precision",
            "warning": "input zero-sum does not imply zero common-mode output",
        },
        "source_artifacts": {
            "summaries": {
                str(R275_SUMMARY.relative_to(ROOT)): sha256_file(R275_SUMMARY),
                str(R277_SUMMARY.relative_to(ROOT)): sha256_file(R277_SUMMARY),
                str(R278_SUMMARY.relative_to(ROOT)): sha256_file(R278_SUMMARY),
            },
            "trace_count": len(source_hashes),
            "trace_hashes": source_hashes,
        },
    }
    audit_path = output_dir / "mechanism_audit.json"
    markdown_path = output_dir / "mechanism_audit.md"
    audit_digest = _write_new(audit_path, audit)
    markdown_digest = _write_new_text(markdown_path, _markdown(audit))
    status = subprocess.check_output(
        ["git", "status", "--short"], cwd=ROOT, text=True
    )
    provenance = {
        "schema_version": 1,
        "round": "R279",
        "repository_head": _git_head(),
        "repository_dirty": bool(status.strip()),
        "command": " ".join(sys.argv),
        "source": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "outputs": {
            str(audit_path.relative_to(ROOT)): audit_digest,
            str(markdown_path.relative_to(ROOT)): markdown_digest,
        },
        "new_trajectories_generated": False,
        "paper_files_modified": False,
    }
    provenance_digest = _write_new(output_dir / "provenance.json", provenance)
    print(
        f"[R279 mechanism audit] scenarios=24 traces={len(source_hashes)} "
        f"audit_sha256={audit_digest} provenance_sha256={provenance_digest}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
