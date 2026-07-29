#!/usr/bin/env python3
# ruff: noqa: E402
"""Correct R279's float32 action audit without rerunning any trajectory."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_r279_formal import _classification

from andes_rl_kundur.evaluation.icems_residual import (
    audit_icems_policy_action,
    float32_limit_tolerance,
    summarise_icems_policy_trace,
)
from andes_rl_kundur.evaluation.sealed_bank import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)

ROUND_ID = "R280"
PARENT_ROUND = "R279"
PLAN = ROOT / "memory/rounds/R280/plan.md"
FORMAL_SEAL = ROOT / "memory/rounds/R279/formal_seal.json"
FORMAL_SUMMARY = ROOT / "results/r279_formal_evaluation/formal_summary.json"
FORMAL_PROVENANCE = ROOT / "results/r279_formal_evaluation/provenance.json"
ICEMS_SOURCE = (
    ROOT / "src/andes_rl_kundur/evaluation/icems_residual.py"
)
DEFAULT_OUT = ROOT / "results/r280_r279_action_audit_correction"
EXPECTED_FALSE_TO_TRUE = {
    (
        "centralized_s17",
        "cand_pq_1_neg_strong",
        "q_slew",
    ),
    (
        "centralized_s17",
        "cand_pq_bus14_neg_edge",
        "q_slew",
    ),
    (
        "centralized_s53",
        "cand_pq_0_pos_moderate",
        "q_slew",
    ),
    (
        "centralized_s89",
        "cand_pq_1_pos_strong",
        "q_slew",
    ),
    (
        "shared_s89",
        "cand_pq_bus15_neg_moderate",
        "q_slew",
    ),
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _write_new(path: Path, payload: object) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(payload)
    path.write_bytes(data)
    digest = sha256_bytes(data)
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n",
        encoding="utf-8",
    )
    return digest


def _write_new_text(path: Path, body: str) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.rstrip() + "\n", encoding="utf-8")
    digest = sha256_file(path)
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n",
        encoding="utf-8",
    )
    return digest


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def _verify_r279_sources(formal_seal: dict[str, Any]) -> dict[str, Any]:
    source_checks: dict[str, Any] = {}
    allowed_drift = {"icems_evaluation", "plan"}
    for name, row in formal_seal["sources"].items():
        path = ROOT / row["path"]
        observed = sha256_file(path)
        matches = observed == row["sha256"]
        if name not in allowed_drift and not matches:
            raise ValueError(f"unexpected R279 source drift: {name}: {path}")
        source_checks[name] = {
            "path": row["path"],
            "sealed_sha256": row["sha256"],
            "current_sha256": observed,
            "matches": matches,
        }
    icems = source_checks["icems_evaluation"]
    if icems["matches"]:
        raise ValueError("R280 correction source does not differ from R279 audit")
    plan_text = (ROOT / formal_seal["sources"]["plan"]["path"]).read_text(
        encoding="utf-8"
    )
    if (
        "state: completed" not in plan_text
        or "closed: '2026-07-27'" not in plan_text
        or not (ROOT / "memory/rounds/R279/verdict.md").exists()
    ):
        raise ValueError("R279 plan drift is not the expected closure lifecycle")
    source_checks["plan"]["expected_lifecycle_drift"] = True
    return source_checks


def _verify_r279_artifacts(
    formal_seal: dict[str, Any],
    formal_summary: dict[str, Any],
    formal_provenance: dict[str, Any],
) -> dict[str, str]:
    seal_hash = sha256_file(FORMAL_SEAL)
    summary_hash = sha256_file(FORMAL_SUMMARY)
    provenance_hash = sha256_file(FORMAL_PROVENANCE)
    if formal_summary["formal_seal_sha256"] != seal_hash:
        raise ValueError("R279 summary/formal-seal hash mismatch")
    if formal_provenance["formal_seal_sha256"] != seal_hash:
        raise ValueError("R279 provenance/formal-seal hash mismatch")
    if formal_provenance["summary_sha256"] != summary_hash:
        raise ValueError("R279 summary/provenance hash mismatch")
    if formal_summary["trace_hashes"] != formal_provenance["trace_hashes"]:
        raise ValueError("R279 summary/provenance trace ledger mismatch")
    if formal_seal["round"] != PARENT_ROUND:
        raise ValueError("unexpected parent formal seal")
    for path_text, expected in formal_provenance["trace_hashes"].items():
        observed = sha256_file(ROOT / path_text)
        if observed != expected:
            raise ValueError(f"R279 trace drift: {path_text}")
    return {
        "formal_seal_sha256": seal_hash,
        "formal_summary_sha256": summary_hash,
        "formal_provenance_sha256": provenance_hash,
    }


def _correct_action_audits(
    formal_summary: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], float]:
    corrected: dict[str, dict[str, dict[str, bool]]] = {}
    changes: list[dict[str, Any]] = []
    max_slew_excess = 0.0
    for path_text in sorted(formal_summary["trace_hashes"]):
        record = _load_json(ROOT / path_text)
        arm = str(record["controller"])
        scenario = str(record["scenario"])
        row = summarise_icems_policy_trace(
            record,
            final_window_steps=50,
            fast_window_steps=15,
        )
        audit = audit_icems_policy_action(row)
        corrected.setdefault(arm, {})[scenario] = audit
        old_audit = formal_summary["action_audits"][arm][scenario]
        for field, new_value in audit.items():
            old_value = bool(old_audit[field])
            if old_value != new_value:
                changes.append(
                    {
                        "arm": arm,
                        "scenario": scenario,
                        "field": field,
                        "old": old_value,
                        "new": new_value,
                        "r278_max_abs_q_slew": row[
                            "r278_max_abs_q_slew"
                        ],
                    }
                )
        max_slew_excess = max(
            max_slew_excess,
            float(row["r278_max_abs_q_slew"]) - 0.25,
        )
    return corrected, changes, max_slew_excess


def _all_action_audits_pass(audits: dict[str, Any]) -> bool:
    return all(
        all(all(fields.values()) for fields in scenarios.values())
        for scenarios in audits.values()
    )


def analyse(out_dir: Path = DEFAULT_OUT) -> dict[str, Any]:
    formal_seal = _load_json(FORMAL_SEAL)
    formal_summary = _load_json(FORMAL_SUMMARY)
    formal_provenance = _load_json(FORMAL_PROVENANCE)
    upstream_hashes = _verify_r279_artifacts(
        formal_seal,
        formal_summary,
        formal_provenance,
    )
    source_checks = _verify_r279_sources(formal_seal)

    old_decision = formal_summary["decision"]
    old_validity = dict(old_decision["validity_guards"])
    if old_decision["classification"] != "INVALID":
        raise ValueError("R279 correction requires the immutable INVALID result")
    old_false_guards = {
        name for name, value in old_validity.items() if not value
    }
    if old_false_guards != {"action_contract_all_rows"}:
        raise ValueError(f"unexpected old validity failures: {old_false_guards}")

    corrected_audits, changes, max_slew_excess = _correct_action_audits(
        formal_summary
    )
    observed_changes = {
        (row["arm"], row["scenario"], row["field"])
        for row in changes
        if row["old"] is False and row["new"] is True
    }
    if any(not (row["old"] is False and row["new"] is True) for row in changes):
        raise ValueError(f"unexpected action-audit direction: {changes}")
    if observed_changes != EXPECTED_FALSE_TO_TRUE:
        raise ValueError(
            "corrected action-audit set drift: "
            f"observed={sorted(observed_changes)}"
        )
    if not _all_action_audits_pass(corrected_audits):
        raise ValueError("one or more corrected action audits still fail")

    slew_tolerance = float32_limit_tolerance(0.25)
    if not 0.0 < max_slew_excess <= slew_tolerance:
        raise ValueError(
            "observed slew excess is outside the registered float32 bound"
        )

    corrected_validity = dict(old_validity)
    corrected_validity["action_contract_all_rows"] = True
    if not all(corrected_validity.values()):
        raise ValueError("corrected R279 validity remains false")
    corrected_decision = _classification(
        valid=True,
        causal_vs_q0=formal_summary["paired_bootstrap"]["causal_vs_q0"],
        hierarchical=formal_summary["hierarchical_bootstrap"],
        seed_effects=formal_summary["per_seed_primary_effects"],
    )
    corrected_decision["validity_guards"] = corrected_validity

    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "parent_round": PARENT_ROUND,
        "question": "Q-0041",
        "correction_gate": "AUDIT-CORRECTION-VALID",
        "old_decision": old_decision,
        "corrected_decision": corrected_decision,
        "float32_contract": {
            "q_limit": 0.25,
            "tolerance_rule": "spacing(float32(abs(limit)))",
            "one_ulp_tolerance": slew_tolerance,
            "maximum_observed_slew_excess": max_slew_excess,
        },
        "changed_action_audits": changes,
        "changed_action_audit_count": len(changes),
        "corrected_action_contract_all_rows": True,
        "trajectory_count": len(formal_summary["trace_hashes"]),
        "new_trajectory_count": 0,
        "efficacy_statistics_recomputed": False,
        "efficacy_statistics_source": upstream_hashes[
            "formal_summary_sha256"
        ],
        "upstream_hashes": upstream_hashes,
        "source_checks": source_checks,
    }
    summary_hash = _write_new(out_dir / "correction_summary.json", summary)
    markdown = "\n".join(
        [
            "# R280 correction of the R279 action audit",
            "",
            "**Correction gate:** `AUDIT-CORRECTION-VALID`",
            "",
            "**Corrected R279 decision:** "
            f"`{corrected_decision['classification']}`",
            "",
            f"- Immutable R279 trajectories verified: "
            f"{summary['trajectory_count']} / {summary['trajectory_count']}",
            "- New trajectories: 0",
            f"- False-to-true action audits: {len(changes)}",
            f"- Float32 one-ULP tolerance: `{slew_tolerance:.17g}`",
            f"- Maximum observed excess: `{max_slew_excess:.17g}`",
            "",
            corrected_decision["reason"],
            "",
        ]
    )
    markdown_hash = _write_new_text(out_dir / "correction_summary.md", markdown)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "repository_head": _git_head(),
        "summary_sha256": summary_hash,
        "markdown_sha256": markdown_hash,
        "plan_sha256": sha256_file(PLAN),
        "script_sha256": sha256_file(Path(__file__)),
        "corrected_icems_source_sha256": sha256_file(ICEMS_SOURCE),
        "upstream_hashes": upstream_hashes,
        "r279_trace_hashes": formal_provenance["trace_hashes"],
        "r279_artifacts_modified": False,
        "new_trajectory_count": 0,
    }
    provenance_hash = _write_new(out_dir / "provenance.json", provenance)
    print(
        "[corrected] "
        f"classification={corrected_decision['classification']} "
        f"summary_sha256={summary_hash} "
        f"provenance_sha256={provenance_hash}",
        flush=True,
    )
    return summary


if __name__ == "__main__":
    analyse()
