"""Tests for round_preflight.py — plan-launch checklist.

Each test instantiates a minimal plan.md (in tmp_path) plus a tiny
in-memory claim ledger to exercise one check at a time. The shared
preflight_check() integration test verifies they compose."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from round_preflight import (  # noqa: E402
    PreflightReport,
    _cited_clm_ids,
    _cited_run_names,
    _extract_methodology_flags,
    check_capacity_evidence,
    check_dual_metric_plan,
    check_formal_launch_contract,
    check_plan_structure,
    check_prior_art,
    check_superseded_citations,
)

# ── primitives ────────────────────────────────────────────────────────

def test_cited_clm_ids_pads_to_4_digits():
    assert _cited_clm_ids("see CLM-101 and CLM-0420") == {"CLM-0101", "CLM-0420"}


def test_cited_clm_ids_empty():
    assert _cited_clm_ids("no claims here") == set()


def test_cited_run_names_extracts():
    text = "compare to r251_w1_scalar_full_v4_s50 and r239_w1_scalar_onlyphiabs_s54"
    assert _cited_run_names(text) == {
        "r251_w1_scalar_full_v4_s50",
        "r239_w1_scalar_onlyphiabs_s54",
    }


def test_extract_methodology_flags_parses_cli():
    text = """
    LR=1e-4 python scripts/train.py --algo td3_lstm \\
        --episodes 75 --seed 51 --phi-h 0 --phi-d 0 --phi-f 0 \\
        --normalize-actions
    """
    flags = _extract_methodology_flags(text)
    assert flags["algo"] == "td3_lstm"
    assert flags["seed"] == "51"
    assert flags["phi-h"] == "0"
    assert flags["normalize-actions"] == ""


# ── check: superseded citations ───────────────────────────────────────

def test_supersede_chain_warns_on_superseded_citation(tmp_path: Path):
    claims = {
        "CLM-0001": {"id": "CLM-0001", "status": "superseded",
                     "superseded_by": ["CLM-0002"]},
        "CLM-0002": {"id": "CLM-0002", "status": "current"},
    }
    report = PreflightReport(round_id="R001",
                             plan_path=tmp_path / "plan.md")
    check_superseded_citations(report, "see CLM-0001 for context", claims)
    levels = [f.level for f in report.findings]
    checks = [f.check for f in report.findings]
    assert "WARN" in levels
    assert "supersede-chain" in checks


def test_supersede_chain_silent_when_current(tmp_path: Path):
    claims = {"CLM-0001": {"id": "CLM-0001", "status": "current"}}
    report = PreflightReport(round_id="R001",
                             plan_path=tmp_path / "plan.md")
    check_superseded_citations(report, "see CLM-0001", claims)
    assert report.findings == []


def test_supersede_chain_warns_on_missing(tmp_path: Path):
    claims = {}
    report = PreflightReport(round_id="R001",
                             plan_path=tmp_path / "plan.md")
    check_superseded_citations(report, "see CLM-9999", claims)
    assert any(f.check == "missing-clm" for f in report.findings)


# ── check: dual-metric ────────────────────────────────────────────────

def test_dual_metric_blocks_geo_only_in_reward_ablation(tmp_path: Path):
    plan = (
        "# R001 plan — paper Eq.14 phi_abs ablation\n"
        "## Outcomes\n"
        "- SOTA (geo > 0.40)\n"
        "- collapse (geo < 0.10)\n"
    )
    report = PreflightReport(round_id="R001", plan_path=tmp_path / "plan.md")
    check_dual_metric_plan(report, plan)
    assert any(f.check == "single-metric-plan" and f.level == "BLOCK"
               for f in report.findings)


def test_dual_metric_silent_when_both_metrics_present(tmp_path: Path):
    plan = (
        "# R001 plan — paper Eq.14 phi_abs ablation\n"
        "## Outcomes\n"
        "- SOTA (geo > 0.40, cum_rf > -0.07)\n"
        "- collapse (geo < 0.10, cum_rf < -0.15)\n"
    )
    report = PreflightReport(round_id="R001", plan_path=tmp_path / "plan.md")
    check_dual_metric_plan(report, plan)
    assert not any(f.check == "single-metric-plan" for f in report.findings)


def test_dual_metric_silent_when_not_reward_ablation(tmp_path: Path):
    plan = (
        "# R001 plan — LSTM hidden size ablation\n"
        "## Outcomes\n"
        "- baseline matches geo > 0.39\n"
    )
    report = PreflightReport(round_id="R001", plan_path=tmp_path / "plan.md")
    check_dual_metric_plan(report, plan)
    # No reward-ablation keyword present → check is not applicable
    assert report.findings == []


# ── check: plan structure ─────────────────────────────────────────────

def test_plan_structure_warns_on_missing_tldr(tmp_path: Path):
    plan = "# R001 plan — test\n\n## Methodology\n\nsome stuff\n"
    report = PreflightReport(round_id="R001", plan_path=tmp_path / "plan.md")
    check_plan_structure(report, plan)
    assert any(f.check == "plan-structure" and "TL;DR" in f.message
               for f in report.findings)


def test_plan_structure_warns_on_no_preregistration(tmp_path: Path):
    plan = (
        "# R001 plan — test\n"
        "## TL;DR\n\nsomething\n"
        "## Methodology\n\nrun training\n"
    )
    report = PreflightReport(round_id="R001", plan_path=tmp_path / "plan.md")
    check_plan_structure(report, plan)
    assert any(f.check == "no-preregistration" for f in report.findings)


def test_plan_structure_silent_with_outcomes_section(tmp_path: Path):
    plan = (
        "# R001 plan — test\n"
        "## TL;DR\n\nsomething\n"
        "## Methodology\n\nrun training\n"
        "## Outcomes\n\n- a\n- b\n"
    )
    report = PreflightReport(round_id="R001", plan_path=tmp_path / "plan.md")
    check_plan_structure(report, plan)
    # No no-preregistration warning expected
    assert not any(f.check == "no-preregistration" for f in report.findings)


# ── check: formal ANDES launch contract ───────────────────────────────

def test_formal_andes_plan_blocks_without_launch_contract(tmp_path: Path):
    plan = (
        "# R001 plan — formal run\n"
        "- Workload: `evidence`\n"
        "- Execute ANDES once in WSL after sealing.\n"
    )
    report = PreflightReport(round_id="R001", plan_path=tmp_path / "plan.md")
    check_formal_launch_contract(report, plan, adaptive_budget_required=False)
    assert any(
        f.check == "formal-launch-contract" and f.level == "BLOCK"
        for f in report.findings
    )


def test_formal_launch_contract_rejects_prefixed_tbd_placeholders(tmp_path: Path):
    plan = (
        "# R485 plan — formal run\n"
        "- Workload: `evidence`\n"
        "- Execute ANDES in WSL after sealing.\n"
        "## Formal launch contract\n"
        "- formal_entry: `TBD_R485_IMPLEMENTATION_BLOCKER`\n"
        "- rehearsal_command: `TBD_R485_REHEARSAL_BLOCKER`\n"
        "- rehearsal_scope: same-pre-attempt-path\n"
        "- rehearsal_checks: source_hash,parent_hash,installed_package,installed_case,output_absence\n"
        "- wsl_python_processes: 17\n"
        "- native_threads_per_process: 1\n"
        "- capacity_evidence: `TBD_R485_CAPACITY_BLOCKER`\n"
        "- host_process_budget: `TBD_R485_CAPACITY_BLOCKER`\n"
        "- other_reserved_processes: 0\n"
    )
    report = PreflightReport(round_id="R485", plan_path=tmp_path / "plan.md")

    check_formal_launch_contract(report, plan, adaptive_budget_required=True)

    finding = next(f for f in report.findings if f.check == "formal-launch-contract")
    assert finding.level == "BLOCK"
    assert "formal_entry" in finding.message
    assert "capacity_evidence" in finding.message


def test_formal_andes_plan_blocks_process_count_above_measured_host_budget(
        tmp_path: Path):
    plan = (
        "# R001 plan — formal run\n"
        "- Workload: `evidence`\n"
        "- Execute ANDES once in WSL after sealing.\n"
        "## Formal launch contract\n"
        "- formal_entry: scripts/run_formal.py --execute\n"
        "- rehearsal_command: scripts/run_formal.py --verify-runtime\n"
        "- rehearsal_scope: same-pre-attempt-path\n"
        "- rehearsal_checks: source_hash,parent_hash,installed_package,"
        "installed_case,output_absence\n"
        "- wsl_python_processes: 4\n"
        "- native_threads_per_process: 1\n"
        "- capacity_evidence: results/host_capacity.json#accepted\n"
        "- host_process_budget: 4\n"
        "- other_reserved_processes: 1\n"
    )
    report = PreflightReport(round_id="R001", plan_path=tmp_path / "plan.md")
    check_formal_launch_contract(report, plan, adaptive_budget_required=True)
    assert any(
        f.check == "host-process-budget" and f.level == "BLOCK"
        for f in report.findings
    )


def test_formal_andes_plan_accepts_more_than_three_with_measured_budget(
        tmp_path: Path):
    plan = (
        "# R001 plan — formal run\n"
        "- Workload: `evidence`\n"
        "- Execute ANDES once in WSL after sealing.\n"
        "## Formal launch contract\n"
        "- formal_entry: scripts/run_formal.py --execute\n"
        "- rehearsal_command: scripts/run_formal.py --verify-runtime\n"
        "- rehearsal_scope: same-pre-attempt-path\n"
        "- rehearsal_checks: source_hash,parent_hash,installed_package,"
        "installed_case,output_absence\n"
        "- wsl_python_processes: 4\n"
        "- native_threads_per_process: 1\n"
        "- capacity_evidence: results/host_capacity.json#accepted\n"
        "- host_process_budget: 6\n"
        "- other_reserved_processes: 1\n"
    )
    report = PreflightReport(round_id="R001", plan_path=tmp_path / "plan.md")
    check_formal_launch_contract(report, plan, adaptive_budget_required=True)
    assert not any(f.level == "BLOCK" for f in report.findings)


def test_future_formal_plan_blocks_without_adaptive_capacity_fields(
        tmp_path: Path):
    plan = (
        "# R339 plan — formal run\n"
        "- Workload: `evidence`\n"
        "- Execute ANDES once in WSL after sealing.\n"
        "## Formal launch contract\n"
        "- formal_entry: scripts/run_formal.py --execute\n"
        "- rehearsal_command: scripts/run_formal.py --verify-runtime\n"
        "- rehearsal_scope: same-pre-attempt-path\n"
        "- rehearsal_checks: source_hash,parent_hash,installed_package,"
        "installed_case,output_absence\n"
        "- wsl_python_processes: 4\n"
        "- native_threads_per_process: 1\n"
    )
    report = PreflightReport(round_id="R339", plan_path=tmp_path / "plan.md")

    check_formal_launch_contract(report, plan, adaptive_budget_required=True)

    assert any(
        f.check == "formal-launch-contract" and "capacity_evidence" in f.message
        for f in report.findings
    )


def test_capacity_evidence_binds_declared_budget_to_successful_anchor(
        tmp_path: Path):
    evidence = {
        "host": {"logical_processors": 32, "physical_memory_bytes": 32_000_000_000},
        "wsl": {"memory_available_bytes": 18_000_000_000},
        "empirical_anchor": {
            "concurrent_workers": 4,
            "native_threads_per_worker": 1,
            "all_records_valid": True,
        },
        "whole_host_python_process_budget": 4,
    }
    (tmp_path / "capacity.json").write_text(json.dumps(evidence), encoding="utf-8")
    plan = (
        "## Formal launch contract\n"
        "- capacity_evidence: capacity.json\n"
        "- host_process_budget: 4\n"
    )
    report = PreflightReport(round_id="R339", plan_path=tmp_path / "plan.md")

    check_capacity_evidence(report, plan, repo_root=tmp_path)

    assert report.findings == []


def test_capacity_evidence_blocks_unmeasured_budget_extrapolation(tmp_path: Path):
    evidence = {
        "host": {"logical_processors": 32, "physical_memory_bytes": 32_000_000_000},
        "wsl": {"memory_available_bytes": 18_000_000_000},
        "empirical_anchor": {
            "concurrent_workers": 4,
            "native_threads_per_worker": 1,
            "all_records_valid": True,
        },
        "whole_host_python_process_budget": 5,
    }
    (tmp_path / "capacity.json").write_text(json.dumps(evidence), encoding="utf-8")
    plan = (
        "## Formal launch contract\n"
        "- capacity_evidence: capacity.json\n"
        "- host_process_budget: 5\n"
    )
    report = PreflightReport(round_id="R339", plan_path=tmp_path / "plan.md")

    check_capacity_evidence(report, plan, repo_root=tmp_path)

    assert any(
        f.check == "capacity-evidence" and f.level == "BLOCK"
        for f in report.findings
    )


def test_capacity_evidence_blocks_missing_or_mismatched_snapshot(tmp_path: Path):
    report = PreflightReport(round_id="R339", plan_path=tmp_path / "plan.md")
    check_capacity_evidence(
        report,
        "## Formal launch contract\n"
        "- capacity_evidence: missing.json\n"
        "- host_process_budget: 4\n",
        repo_root=tmp_path,
    )
    assert any(f.check == "capacity-evidence" for f in report.findings)

    evidence = {
        "host": {"logical_processors": 32, "physical_memory_bytes": 32_000_000_000},
        "wsl": {"memory_available_bytes": 18_000_000_000},
        "empirical_anchor": {
            "concurrent_workers": 4,
            "native_threads_per_worker": 1,
            "all_records_valid": True,
        },
        "whole_host_python_process_budget": 4,
    }
    (tmp_path / "capacity.json").write_text(json.dumps(evidence), encoding="utf-8")
    mismatch = PreflightReport(round_id="R339", plan_path=tmp_path / "plan.md")
    check_capacity_evidence(
        mismatch,
        "## Formal launch contract\n"
        "- capacity_evidence: capacity.json\n"
        "- host_process_budget: 5\n",
        repo_root=tmp_path,
    )
    assert any(f.check == "capacity-evidence" for f in mismatch.findings)


def test_non_andes_plan_does_not_need_formal_launch_contract(tmp_path: Path):
    plan = "# R001 plan — offline proof\n- Workload: `evidence`\n"
    report = PreflightReport(round_id="R001", plan_path=tmp_path / "plan.md")
    check_formal_launch_contract(report, plan, adaptive_budget_required=True)
    assert report.findings == []


def test_offline_plan_ignores_negated_and_snapshot_andes_wsl_mentions(
        tmp_path: Path):
    plan = (
        "# R358 plan — offline proof\n"
        "- Workload: `evidence`\n"
        "## Snapshot at plan-time\n"
        "- legacy question: verify one unrelated case from WSL\n"
        "## Methodology\n"
        "- zero ANDES, zero WSL, zero simulation, and zero training\n"
        "## Offline formal execution contract\n"
        "- formal_entry: python scripts/run_offline.py analyse\n"
    )
    report = PreflightReport(round_id="R358", plan_path=tmp_path / "plan.md")

    check_formal_launch_contract(report, plan, adaptive_budget_required=True)

    assert not any(f.level == "BLOCK" for f in report.findings)


# ── check: prior-art ──────────────────────────────────────────────────

def test_prior_art_surfaces_unrelated_claim(tmp_path: Path):
    """Plan uses --algo sac; prior CLM-0007 is tagged with 'sac' and
    status=current. The check should surface it."""
    claims = {
        "CLM-0007": {
            "id": "CLM-0007", "status": "current",
            "tags": ["sac", "default-collapse"],
            "statement": "SAC at default hyper collapses",
        },
        "CLM-0008": {
            "id": "CLM-0008", "status": "current",
            "tags": ["unrelated"],
            "statement": "completely different topic",
        },
    }
    plan = "## Methodology\n\n--algo sac --seed 54\n"
    report = PreflightReport(round_id="R001", plan_path=tmp_path / "plan.md")
    check_prior_art(report, plan, claims)
    art = [f for f in report.findings if f.check == "prior-art"]
    assert len(art) == 1
    assert "CLM-0007" in art[0].message


def test_prior_art_skips_already_cited(tmp_path: Path):
    claims = {
        "CLM-0007": {
            "id": "CLM-0007", "status": "current",
            "tags": ["sac"], "statement": "SAC collapses",
        },
    }
    plan = "## Methodology\n\n--algo sac\n\nsee CLM-0007 for context.\n"
    report = PreflightReport(round_id="R001", plan_path=tmp_path / "plan.md")
    check_prior_art(report, plan, claims)
    # Already cited → not surfaced
    assert report.findings == []


# ── exit code semantics ──────────────────────────────────────────────

def test_exit_code_zero_for_no_findings(tmp_path: Path):
    r = PreflightReport(round_id="R001", plan_path=tmp_path / "plan.md")
    assert r.exit_code == 0


def test_exit_code_one_for_warn(tmp_path: Path):
    r = PreflightReport(round_id="R001", plan_path=tmp_path / "plan.md")
    r.add("WARN", "test", "msg")
    assert r.exit_code == 1


def test_exit_code_two_for_block(tmp_path: Path):
    r = PreflightReport(round_id="R001", plan_path=tmp_path / "plan.md")
    r.add("WARN", "test", "msg")
    r.add("BLOCK", "test2", "msg2")
    assert r.exit_code == 2  # BLOCK overrides WARN
