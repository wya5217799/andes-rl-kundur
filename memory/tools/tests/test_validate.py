from pathlib import Path
from typing import Any
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from validate import load_claims  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "claims"


def test_load_claims_returns_dict_of_id_to_frontmatter():
    claims = load_claims(FIXTURES)
    assert set(claims.keys()) == {"CLM-0001", "CLM-0002", "CLM-0003", "CLM-0004"}
    assert claims["CLM-0001"]["type"] == "finding"
    assert claims["CLM-0001"]["status"] == "current"
    assert claims["CLM-0002"]["superseded_by"] == ["CLM-0003"]


from validate import validate_rules  # noqa: E402


def test_rule1_duplicate_id_fails():
    claims = {
        "CLM-0001": {"id": "CLM-0001", "status": "current",
                     "supersedes": [], "superseded_by": []},
        "CLM-0001b": {"id": "CLM-0001", "status": "current",
                      "supersedes": [], "superseded_by": []},
    }
    errors, _warnings = validate_rules(claims)
    assert any("duplicate id" in e.lower() for e in errors)


def test_rule2_supersedes_nonexistent_target_fails():
    claims = {
        "CLM-0001": {"id": "CLM-0001", "status": "current",
                     "supersedes": ["CLM-9999"], "superseded_by": []},
    }
    errors, _warnings = validate_rules(claims)
    assert any("CLM-9999" in e and "does not exist" in e for e in errors)


def test_rule3_current_with_nonempty_superseded_by_fails():
    claims = {
        "CLM-0001": {"id": "CLM-0001", "status": "current",
                     "supersedes": [], "superseded_by": ["CLM-0002"]},
        "CLM-0002": {"id": "CLM-0002", "status": "current",
                     "supersedes": ["CLM-0001"], "superseded_by": []},
    }
    errors, _warnings = validate_rules(claims)
    assert any("status: current" in e and "superseded_by" in e for e in errors)


def test_clean_fixtures_have_no_errors():
    claims = load_claims(FIXTURES)
    errors, warnings = validate_rules(claims)
    assert errors == [], f"Unexpected errors: {errors}"
    assert warnings == [], f"Unexpected warnings: {warnings}"


def test_rule4_decision_with_trust_V_fails():
    """A `type: decision` claim must be `trust: S` (Stated, not Verified).
    Decisions are choices, not measurable facts."""
    claims = {
        "CLM-0001": {"id": "CLM-0001", "type": "decision", "trust": "V",
                     "status": "current", "supersedes": [], "superseded_by": []},
    }
    errors, _ = validate_rules(claims)
    assert any("CLM-0001" in e and "decision" in e and "trust" in e for e in errors), \
        f"expected rule4 error, got: {errors}"


def test_rule4_decision_with_trust_S_passes():
    claims = {
        "CLM-0001": {"id": "CLM-0001", "type": "decision", "trust": "S",
                     "status": "current", "supersedes": [], "superseded_by": []},
    }
    errors, _ = validate_rules(claims)
    assert not any("CLM-0001" in e and "decision" in e and "trust" in e for e in errors), \
        f"unexpected rule4 error: {errors}"


def test_rule4_correction_with_trust_S_fails():
    """A `type: correction` claim must be `trust: V` (it replaces a verified
    prior number — the replacement itself must be verified)."""
    claims = {
        "CLM-0001": {"id": "CLM-0001", "type": "correction", "trust": "S",
                     "status": "current", "supersedes": [], "superseded_by": []},
    }
    errors, _ = validate_rules(claims)
    assert any("CLM-0001" in e and "correction" in e and "trust" in e for e in errors), \
        f"expected rule4 error, got: {errors}"


def test_rule4_finding_trust_V_or_S_both_pass():
    """Findings can be V, S, or T — different levels of evidence."""
    for trust in ("V", "S", "T"):
        claims = {
            "CLM-0001": {"id": "CLM-0001", "type": "finding", "trust": trust,
                         "status": "current", "supersedes": [], "superseded_by": []},
        }
        errors, _ = validate_rules(claims)
        assert not any("CLM-0001" in e and "finding" in e and "trust" in e for e in errors), \
            f"unexpected rule4 error for trust={trust}: {errors}"


def test_load_claims_raises_on_duplicate_id_on_disk(tmp_path):
    """Two files with the same id should error at load time."""
    (tmp_path / "CLM-0001.md").write_text(
        "---\nid: CLM-0001\ntype: finding\ntrust: V\n"
        "status: current\nstatement: foo\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "CLM-0001b.md").write_text(
        "---\nid: CLM-0001\ntype: finding\ntrust: V\n"
        "status: current\nstatement: bar\n---\n",
        encoding="utf-8",
    )
    import pytest
    with pytest.raises(ValueError, match="duplicate id CLM-0001"):
        load_claims(tmp_path)


import shutil
from validate import fix_back_edges  # noqa: E402


# ---------- Question entity tests (commit 2) ----------


def test_load_questions_returns_dict_keyed_by_id(tmp_path):
    """load_questions reads Q-*.md frontmatter into a dict keyed by id."""
    (tmp_path / "Q-0001.md").write_text(
        "---\nid: Q-0001\nstatus: open\ntitle: First Q\n"
        "opened_round: R37\n---\n## Candidates\n- a\n## Log\n- R37: opened\n",
        encoding="utf-8",
    )
    from validate import load_questions  # noqa: E402
    qs = load_questions(tmp_path)
    assert set(qs.keys()) == {"Q-0001"}
    assert qs["Q-0001"]["status"] == "open"
    assert qs["Q-0001"]["title"] == "First Q"
    assert qs["Q-0001"]["opened_round"] == "R37"


def test_validate_question_rules_status_enum(tmp_path):
    """Question status must be in the allowed enum."""
    from validate import validate_question_rules  # noqa: E402
    questions = {
        "Q-0001": {"id": "Q-0001", "status": "weird-status",
                   "title": "x", "opened_round": "R37"},
    }
    rounds_dir = tmp_path / "rounds"
    rounds_dir.mkdir()
    (rounds_dir / "R37").mkdir()
    errors = validate_question_rules(questions, claims={}, rounds_dir=rounds_dir)
    assert any("Q-0001" in e and "status" in e for e in errors)


def test_validate_question_rules_closed_must_have_closed_round_and_by(tmp_path):
    """Q with status=closed-* must have closed_round + closed_by."""
    from validate import validate_question_rules  # noqa: E402
    questions = {
        "Q-0001": {"id": "Q-0001", "status": "closed-positive",
                   "title": "x", "opened_round": "R37"},
    }
    rounds_dir = tmp_path / "rounds"
    rounds_dir.mkdir()
    (rounds_dir / "R37").mkdir()
    errors = validate_question_rules(questions, claims={}, rounds_dir=rounds_dir)
    assert any("Q-0001" in e and "closed" in e for e in errors)


def test_validate_question_rules_opened_round_must_exist(tmp_path):
    """opened_round must correspond to an existing round directory."""
    from validate import validate_question_rules  # noqa: E402
    questions = {
        "Q-0001": {"id": "Q-0001", "status": "open",
                   "title": "x", "opened_round": "R999"},
    }
    rounds_dir = tmp_path / "rounds"
    rounds_dir.mkdir()
    # no R999 dir
    errors = validate_question_rules(questions, claims={}, rounds_dir=rounds_dir)
    assert any("Q-0001" in e and "R999" in e for e in errors)


def test_validate_question_rules_clean_passes(tmp_path):
    """An open Q with valid opened_round and a closed Q with full closure produces no errors."""
    from validate import validate_question_rules  # noqa: E402
    questions = {
        "Q-0001": {"id": "Q-0001", "status": "open",
                   "title": "x", "opened_round": "R37"},
        "Q-0002": {"id": "Q-0002", "status": "closed-negative",
                   "title": "y", "opened_round": "R37",
                   "closed_round": "R38", "closed_by": "CLM-0099"},
    }
    rounds_dir = tmp_path / "rounds"
    rounds_dir.mkdir()
    for r in ("R37", "R38"):
        (rounds_dir / r).mkdir()
    errors = validate_question_rules(questions, claims={"CLM-0099": {}}, rounds_dir=rounds_dir)
    assert errors == []


def test_validate_verdict_structure_3_q_sections_pass(tmp_path):
    """A verdict with the 3 mandatory Q-sections passes (hard check)."""
    from validate import validate_verdict_structure  # noqa: E402
    verdict_path = tmp_path / "verdict.md"
    verdict_path.write_text(
        "# R99 verdict — example\n\n"
        "**Date**: 2026-01-01\n**Status**: **COMPLETE**.\n\n"
        "## TL;DR\nSomething happened.\n\n"
        "## Questions opened (this round)\n- none\n\n"
        "## Questions closed (this round)\n- none\n\n"
        "## Questions advanced (this round)\n- none\n",
        encoding="utf-8",
    )
    errors = validate_verdict_structure(verdict_path)
    assert errors == []


def test_validate_verdict_structure_missing_q_section_fails(tmp_path):
    """Missing one of the 3 Q-sections is a hard error."""
    from validate import validate_verdict_structure  # noqa: E402
    verdict_path = tmp_path / "verdict.md"
    verdict_path.write_text(
        "# R99 verdict\n\n**Status**: complete\n## TL;DR\nx\n"
        "## Questions opened (this round)\n- none\n",
        # missing Questions closed + advanced
        encoding="utf-8",
    )
    errors = validate_verdict_structure(verdict_path)
    assert any("Questions closed" in e for e in errors)
    assert any("Questions advanced" in e for e in errors)


def test_validate_verdict_status_header_accepts_varied_text(tmp_path):
    """`**Status**:` line is required but the text after is free
    (legacy verdicts use COMPLETE / DONE / INCONCLUSIVE / **PARTIAL** etc.)."""
    from validate import warn_verdict_recommended  # noqa: E402
    for tail in (
        "**COMPLETE**.",
        "DONE (8/8 exit 0)",
        "**INCONCLUSIVE**",
        "⚠ **PARTIAL** — see below",
        "in-progress",
    ):
        verdict_path = tmp_path / f"v_{hash(tail) & 0xFFFF}.md"
        verdict_path.write_text(
            f"# R99\n**Status**: {tail}\n## TL;DR\nx\n",
            encoding="utf-8",
        )
        warnings = warn_verdict_recommended(verdict_path)
        # No Status-related warning since header line is present
        assert not any("Status" in w for w in warnings), \
            f"unexpected Status warning for tail={tail!r}: {warnings}"


def test_warn_verdict_missing_tldr_emits_warning(tmp_path):
    from validate import warn_verdict_recommended  # noqa: E402
    verdict_path = tmp_path / "v.md"
    verdict_path.write_text(
        "# R99\n**Status**: COMPLETE\n## Questions opened\n- none\n"
        "## Questions closed\n- none\n## Questions advanced\n- none\n",
        encoding="utf-8",
    )
    warnings = warn_verdict_recommended(verdict_path)
    assert any("TL;DR" in w for w in warnings)


# ---------- Hotfix regressions (R39 review punch list) ----------


def test_iter_verdicts_ignores_non_round_directories(tmp_path):
    """H2: only directories matching ^R\\d+$ should be iterated as rounds.
    A `README` or `R-legacy` subdir under memory/rounds/ must be skipped."""
    from validate import _iter_verdicts  # noqa: E402
    rounds_dir = tmp_path / "rounds"
    # Real round
    (rounds_dir / "R01").mkdir(parents=True)
    (rounds_dir / "R01" / "verdict.md").write_text(
        "# R01\n## Questions opened\n## Questions closed\n## Questions advanced\n",
        encoding="utf-8",
    )
    # Decoy: directory starting with R but not a round
    (rounds_dir / "README").mkdir()
    (rounds_dir / "README" / "verdict.md").write_text(
        "# bogus\n", encoding="utf-8",
    )
    (rounds_dir / "R-legacy").mkdir()
    (rounds_dir / "R-legacy" / "verdict.md").write_text(
        "# bogus\n", encoding="utf-8",
    )
    found = list(_iter_verdicts(rounds_dir))
    assert len(found) == 1
    assert found[0].parent.name == "R01"


def test_load_claims_raises_value_error_on_missing_id(tmp_path):
    """M1: a CLM file with valid YAML frontmatter but no `id` key should raise
    a helpful ValueError naming the file, not a bare KeyError."""
    (tmp_path / "CLM-0099.md").write_text(
        "---\ntype: finding\ntrust: V\nstatus: current\nstatement: x\n---\n",
        encoding="utf-8",
    )
    import pytest
    with pytest.raises(ValueError, match="CLM-0099"):
        load_claims(tmp_path)


def test_load_questions_raises_value_error_on_missing_id(tmp_path):
    """M1: same guarantee for Q files."""
    from validate import load_questions  # noqa: E402
    (tmp_path / "Q-0099.md").write_text(
        "---\nstatus: open\ntitle: x\nopened_round: R01\n---\n",
        encoding="utf-8",
    )
    import pytest
    with pytest.raises(ValueError, match="Q-0099"):
        load_questions(tmp_path)


def test_validate_question_rules_closed_by_must_be_string(tmp_path):
    """M1: closed_by must be a single CLM id string, not a list. Per schema
    a Q is closed by exactly one claim. Catch the misuse as an error,
    don't let it propagate as TypeError into the dict lookup."""
    from validate import validate_question_rules  # noqa: E402
    questions = {
        "Q-0001": {
            "id": "Q-0001", "status": "closed-positive", "title": "x",
            "opened_round": "R01", "closed_round": "R02",
            "closed_by": ["CLM-0001", "CLM-0002"],  # invalid: list
        },
    }
    rounds_dir = tmp_path / "rounds"
    rounds_dir.mkdir()
    for r in ("R01", "R02"):
        (rounds_dir / r).mkdir()
    errors = validate_question_rules(
        questions, claims={"CLM-0001": {}, "CLM-0002": {}}, rounds_dir=rounds_dir,
    )
    assert any("Q-0001" in e and "closed_by" in e for e in errors), \
        f"expected closed_by-type error; got: {errors}"


def test_load_claims_tolerates_crlf_line_endings(tmp_path):
    """M2: a CLM file checked out with CRLF line endings (Windows
    autocrlf=true) must still be loadable. Without normalisation, the
    `^---\\n` regex misses the frontmatter delimiter and validate.py
    treats every claim as malformed."""
    text_lf = (
        "---\nid: CLM-0001\ntype: finding\ntrust: V\n"
        "status: current\nstatement: crlf-test\n---\n"
    )
    text_crlf = text_lf.replace("\n", "\r\n")
    (tmp_path / "CLM-0001.md").write_bytes(text_crlf.encode("utf-8"))
    claims = load_claims(tmp_path)
    assert claims["CLM-0001"]["statement"] == "crlf-test"


def test_fix_back_edges_writes_superseded_by_and_flips_status(tmp_path):
    src = FIXTURES
    dst = tmp_path / "claims"
    shutil.copytree(src, dst)

    # Wipe back edge + status from CLM-0002 to simulate forgotten metadata
    target = dst / "CLM-0002.md"
    content = target.read_text(encoding="utf-8")
    content = content.replace("status: superseded", "status: current")
    content = content.replace("superseded_by: [CLM-0003]", "superseded_by: []")
    target.write_text(content, encoding="utf-8")

    claims = load_claims(dst)
    assert claims["CLM-0002"]["status"] == "current"
    assert claims["CLM-0002"]["superseded_by"] == []

    fix_back_edges(claims, write=True)

    fixed = load_claims(dst)
    assert fixed["CLM-0002"]["status"] == "superseded"
    assert fixed["CLM-0002"]["superseded_by"] == ["CLM-0003"]


# ── R50 opt I: structured ``metric`` field ────────────────────────────────────


def _minimal_claim(cid: str, **extra) -> dict:
    base = {
        "id": cid,
        "type": "finding",
        "trust": "V",
        "status": "current",
        "supersedes": [],
        "superseded_by": [],
        "provenance": ["x"],
    }
    base.update(extra)
    return base


def test_metric_field_with_name_and_value_validates():
    """R50 opt I: claims may declare a structured metric for the
    STATE.md leaderboard (H). Valid block: name + numeric value."""
    claims = {
        "CLM-0001": _minimal_claim(
            "CLM-0001",
            metric={"name": "6_axis", "value": 0.334},
        ),
    }
    errors, _warnings = validate_rules(claims)
    assert errors == [], f"expected no errors, got {errors}"


def test_metric_field_missing_name_fails():
    claims = {
        "CLM-0001": _minimal_claim(
            "CLM-0001", metric={"value": 0.334},
        ),
    }
    errors, _warnings = validate_rules(claims)
    assert any("metric" in e and "name" in e for e in errors), errors


def test_metric_field_missing_value_fails():
    claims = {
        "CLM-0001": _minimal_claim(
            "CLM-0001", metric={"name": "6_axis"},
        ),
    }
    errors, _warnings = validate_rules(claims)
    assert any("metric" in e and "value" in e for e in errors), errors


def test_metric_field_non_numeric_value_fails():
    claims = {
        "CLM-0001": _minimal_claim(
            "CLM-0001",
            metric={"name": "6_axis", "value": "high"},
        ),
    }
    errors, _warnings = validate_rules(claims)
    assert any("metric" in e and ("numeric" in e or "value" in e) for e in errors), errors


def test_claim_without_metric_field_still_valid():
    """Backward compat: pre-R50 claims (CLM-0001 .. CLM-0057) don't
    carry a metric block. They must continue to validate."""
    claims = {
        "CLM-0001": _minimal_claim("CLM-0001"),  # no metric kwarg
    }
    errors, _warnings = validate_rules(claims)
    assert errors == [], f"backward compat broken: {errors}"


# ── R50 opt J: status: obsoleted ──────────────────────────────────────────────


def test_status_obsoleted_with_round_and_reason_validates():
    """R50 opt J: status='obsoleted' means the claim's number / decision
    became stale due to external change (ranker drift, env semantics
    shift) WITHOUT a successor claim to point at. Distinct from
    'superseded' (which always has a replacement). Both round + reason
    are mandatory so the obsoletion is auditable."""
    claims = {
        "CLM-0001": _minimal_claim(
            "CLM-0001",
            status="obsoleted",
            obsoleted_round="R44",
            obsoleted_reason="ranker drift post-R30 changed baseline",
        ),
    }
    errors, _warnings = validate_rules(claims)
    assert errors == [], f"expected no errors, got {errors}"


def test_status_obsoleted_missing_round_fails():
    claims = {
        "CLM-0001": _minimal_claim(
            "CLM-0001",
            status="obsoleted",
            obsoleted_reason="something",
        ),
    }
    errors, _warnings = validate_rules(claims)
    assert any("obsoleted" in e and "round" in e for e in errors), errors


def test_status_obsoleted_missing_reason_fails():
    claims = {
        "CLM-0001": _minimal_claim(
            "CLM-0001",
            status="obsoleted",
            obsoleted_round="R44",
        ),
    }
    errors, _warnings = validate_rules(claims)
    assert any("obsoleted" in e and "reason" in e for e in errors), errors


def test_status_current_still_validates_after_obsoleted_added():
    """The new status branch must NOT break existing 'current' claims."""
    claims = {
        "CLM-0001": _minimal_claim("CLM-0001"),  # status='current' by default
    }
    errors, _warnings = validate_rules(claims)
    assert errors == []


# ── R50 opt K: provenance soft path check ─────────────────────────────────────


def test_provenance_existing_path_no_warning(tmp_path):
    """Literal provenance paths that exist on disk produce no warning."""
    from validate import check_provenance_paths

    existing = tmp_path / "real_file.json"
    existing.write_text("{}", encoding="utf-8")

    claims = {
        "CLM-0001": _minimal_claim(
            "CLM-0001", provenance=[str(existing)],
        ),
    }
    warnings = check_provenance_paths(claims, repo_root=tmp_path)
    # Only warnings about THIS literal path; should be empty.
    relevant = [w for w in warnings if "real_file" in w]
    assert relevant == []


def test_provenance_missing_path_warns(tmp_path):
    """Literal provenance path that doesn't exist -> warning."""
    from validate import check_provenance_paths

    claims = {
        "CLM-0001": _minimal_claim(
            "CLM-0001", provenance=["does/not/exist.json"],
        ),
    }
    warnings = check_provenance_paths(claims, repo_root=tmp_path)
    assert any("does/not/exist.json" in w for w in warnings), warnings


def test_provenance_wildcard_path_skipped(tmp_path):
    """Glob / brace patterns are skipped — too expensive to expand and
    the brace form (``s{49,50,51}``) is shell syntax, not glob."""
    from validate import check_provenance_paths

    claims = {
        "CLM-0001": _minimal_claim(
            "CLM-0001",
            provenance=[
                "results/td3_norm_s{49,50,51}/agent_*_best.pt",
                "results/td3_norm_s49/agent_0_best.pt",  # literal, missing
            ],
        ),
    }
    warnings = check_provenance_paths(claims, repo_root=tmp_path)
    # Only the literal-but-missing path produces a warning.
    assert any("agent_0_best.pt" in w for w in warnings)
    assert not any("{49,50,51}" in w for w in warnings)
    assert not any("agent_*_best.pt" in w for w in warnings)


def test_provenance_check_is_warning_not_error(tmp_path):
    """Missing provenance never blocks validation — it only produces a
    warning. This honors the soft-check contract: results/ is gitignored,
    so cross-session provenance paths are routinely dangling."""
    from validate import check_provenance_paths

    claims = {
        "CLM-0001": _minimal_claim(
            "CLM-0001", provenance=["results/missing.json"],
        ),
    }
    # The function returns a list of warning strings (no exception).
    warnings = check_provenance_paths(claims, repo_root=tmp_path)
    assert isinstance(warnings, list)
    assert all(isinstance(w, str) for w in warnings)


# ── R53 patch A2: soft-warn for finding/correction without metric ────────────


def test_finding_with_decimal_statement_no_metric_warns():
    """R53 patch A2 (validates R50 opt I adoption): if a finding or
    correction's statement cites a benchmark-like decimal number but
    carries no metric block, emit a soft warning so future authors
    will fill it in. The warning is informational only (does not
    block validation)."""
    claims = {
        "CLM-0001": _minimal_claim(
            "CLM-0001",
            type="finding",
            statement="result is 0.334 6-axis",
        ),
    }
    _errors, warnings = validate_rules(claims)
    assert any(
        "CLM-0001" in w and "metric" in w for w in warnings
    ), f"expected soft-warn for missing metric, got: {warnings}"


def test_finding_with_decimal_and_metric_no_warn():
    """Same statement but with a metric block: no warning."""
    claims = {
        "CLM-0001": _minimal_claim(
            "CLM-0001",
            type="finding",
            statement="result is 0.334 6-axis",
            metric={"name": "6_axis", "value": 0.334},
        ),
    }
    _errors, warnings = validate_rules(claims)
    assert not any(
        "CLM-0001" in w and "metric" in w for w in warnings
    ), f"unexpected metric-soft-warn: {warnings}"


def test_decision_with_decimal_does_not_trigger_metric_warn():
    """Decision claims are choices, not measurements — the soft-warn
    only targets findings + corrections, even when a decision's
    statement happens to cite a decimal."""
    claims = {
        "CLM-0001": _minimal_claim(
            "CLM-0001",
            type="decision",
            trust="S",
            statement="picked weight 0.85 for the ensemble baseline",
        ),
    }
    _errors, warnings = validate_rules(claims)
    assert not any(
        "CLM-0001" in w and "metric" in w for w in warnings
    ), f"decision should not trigger metric soft-warn: {warnings}"


# ── ADR-0003: PI briefing layer (R59+) ─────────────────────────────────────────


def _verdict_with_q_sections(extra_body: str = "") -> str:
    """Helper: build a minimal-but-valid post-Q-sections verdict body. Extra
    content is inserted before the Q-sections to compose new section tests."""
    return (
        "# R99 verdict — test\n\n"
        "**Date**: 2026-05-17\n**Status**: COMPLETE\n\n"
        "## TL;DR\nx\n\n"
        f"{extra_body}"
        "## Questions opened (this round)\n- none\n\n"
        "## Questions closed (this round)\n- none\n\n"
        "## Questions advanced (this round)\n- none\n"
    )


def _briefing_section(body: str = "**结果（一句话）**：占位。") -> str:
    return f"## 给 PI 的话\n\n{body}\n\n"


def test_pre_r59_verdict_without_briefing_passes(tmp_path):
    """ADR-0003: cutoff is R59. A pre-cutoff verdict (R58) without
    `## 给 PI 的话` MUST continue to validate — legacy verdicts are not
    retrofit."""
    from validate import validate_verdict_structure  # noqa: E402
    rounds_dir = tmp_path / "rounds"
    r58 = rounds_dir / "R58"
    r58.mkdir(parents=True)
    verdict_path = r58 / "verdict.md"
    verdict_path.write_text(_verdict_with_q_sections(), encoding="utf-8")
    errors = validate_verdict_structure(verdict_path)
    assert errors == [], f"pre-R59 verdict must pass without briefing: {errors}"


def test_r59_verdict_without_briefing_fails(tmp_path):
    """ADR-0003: R≥59 verdict MUST have `## 给 PI 的话` (hard rule)."""
    from validate import validate_verdict_structure  # noqa: E402
    rounds_dir = tmp_path / "rounds"
    r59 = rounds_dir / "R59"
    r59.mkdir(parents=True)
    verdict_path = r59 / "verdict.md"
    verdict_path.write_text(_verdict_with_q_sections(), encoding="utf-8")
    errors = validate_verdict_structure(verdict_path)
    assert any("给 PI 的话" in e for e in errors), \
        f"expected briefing-missing error for R59, got: {errors}"


def test_r60_verdict_with_briefing_passes(tmp_path):
    """ADR-0003: a properly-formed R60 verdict with the briefing section
    validates clean."""
    from validate import validate_verdict_structure  # noqa: E402
    rounds_dir = tmp_path / "rounds"
    r60 = rounds_dir / "R60"
    r60.mkdir(parents=True)
    verdict_path = r60 / "verdict.md"
    verdict_path.write_text(
        _verdict_with_q_sections(extra_body=_briefing_section()),
        encoding="utf-8",
    )
    errors = validate_verdict_structure(verdict_path)
    assert errors == [], f"unexpected errors for valid R60 verdict: {errors}"


def test_pi_briefing_under_cap_no_warning(tmp_path):
    """A briefing with <= 30 non-blank lines produces no length warning."""
    from validate import warn_verdict_recommended  # noqa: E402
    r59 = tmp_path / "rounds" / "R59"
    r59.mkdir(parents=True)
    short_briefing = "\n".join([
        "**这周干了啥**：测试简短简报。",
        "**结果（一句话）**：通过。",
        "**意外**：无。",
        "**我默认下一步做**：归档。",
        "**你想插一脚就说**：无需。",
    ])
    verdict_path = r59 / "verdict.md"
    verdict_path.write_text(
        _verdict_with_q_sections(extra_body=_briefing_section(short_briefing)),
        encoding="utf-8",
    )
    warnings = warn_verdict_recommended(verdict_path)
    assert not any("给 PI 的话" in w for w in warnings), \
        f"unexpected briefing-length warning: {warnings}"


def test_pi_briefing_over_cap_emits_warning(tmp_path):
    """A briefing exceeding 30 non-blank lines emits a soft warning."""
    from validate import warn_verdict_recommended, PI_BRIEFING_LINE_CAP  # noqa: E402
    r59 = tmp_path / "rounds" / "R59"
    r59.mkdir(parents=True)
    bloated = "\n".join(
        f"line {i}: filler" for i in range(PI_BRIEFING_LINE_CAP + 5)
    )
    verdict_path = r59 / "verdict.md"
    verdict_path.write_text(
        _verdict_with_q_sections(extra_body=_briefing_section(bloated)),
        encoding="utf-8",
    )
    warnings = warn_verdict_recommended(verdict_path)
    assert any("给 PI 的话" in w and "lines" in w for w in warnings), \
        f"expected briefing-length warning, got: {warnings}"


def test_pre_r59_no_briefing_length_warning(tmp_path):
    """Length cap only applies to R≥59. A pre-cutoff round with no briefing
    section never triggers a length warning regardless of verdict length."""
    from validate import warn_verdict_recommended  # noqa: E402
    r58 = tmp_path / "rounds" / "R58"
    r58.mkdir(parents=True)
    verdict_path = r58 / "verdict.md"
    verdict_path.write_text(_verdict_with_q_sections(), encoding="utf-8")
    warnings = warn_verdict_recommended(verdict_path)
    assert not any("给 PI 的话" in w for w in warnings), \
        f"pre-R59 should not get briefing warnings: {warnings}"


def test_round_num_from_verdict_path(tmp_path):
    """Helper correctly extracts round number from R<N>/verdict.md."""
    from validate import _round_num_from_verdict_path  # noqa: E402
    assert _round_num_from_verdict_path(Path("/x/R59/verdict.md")) == 59
    assert _round_num_from_verdict_path(Path("/x/R01/verdict.md")) == 1
    assert _round_num_from_verdict_path(Path("/x/README/verdict.md")) is None


# ---------- Note entity rules (N1-N5) ----------
NOTE_FIXTURES = Path(__file__).parent / "fixtures" / "notes"
REPO_ROOT_FOR_TESTS = Path(__file__).parent.parent.parent.parent  # andes-rl-kundur/


def test_load_notes_returns_dict_of_id_to_frontmatter():
    from validate import load_notes  # noqa: E402
    notes = load_notes(NOTE_FIXTURES)
    assert set(notes.keys()) == {"NOTE-0001", "NOTE-0002", "NOTE-0003"}
    assert notes["NOTE-0001"]["source"] == "handoff"
    assert notes["NOTE-0002"]["topics"][0] == "pipeline"


def test_rule_N1_filename_must_match_id():
    from validate import validate_note_rules  # noqa: E402
    notes = {
        "NOTE-0001": {
            "id": "NOTE-0001", "source": "handoff",
            "source_path": "memory/tools/tests/fixtures/notes_handoff_src/2026-05-17_demo.md",
            "topics": ["training-infra"], "extracted_claims": [],
            "_path": Path("NOTE-0099.md"),
        },
    }
    errors = validate_note_rules(notes, claims={}, repo_root=REPO_ROOT_FOR_TESTS)
    assert any("filename" in e.lower() and "NOTE-0001" in e for e in errors)


def test_rule_N2_source_in_whitelist():
    from validate import validate_note_rules  # noqa: E402
    notes = {
        "NOTE-0001": {
            "id": "NOTE-0001", "source": "blog",
            "source_path": "memory/tools/tests/fixtures/notes_handoff_src/2026-05-17_demo.md",
            "topics": ["training-infra"], "extracted_claims": [],
            "_path": NOTE_FIXTURES / "NOTE-0001.md",
        },
    }
    errors = validate_note_rules(notes, claims={}, repo_root=REPO_ROOT_FOR_TESTS)
    assert any("source" in e and "blog" in e for e in errors)


def test_rule_N3_source_path_must_exist():
    from validate import validate_note_rules  # noqa: E402
    notes = {
        "NOTE-0001": {
            "id": "NOTE-0001", "source": "handoff",
            "source_path": "memory/this/file/does/not/exist.md",
            "topics": ["training-infra"], "extracted_claims": [],
            "_path": NOTE_FIXTURES / "NOTE-0001.md",
        },
    }
    errors = validate_note_rules(notes, claims={}, repo_root=REPO_ROOT_FOR_TESTS)
    assert any("source_path" in e and "exist" in e.lower() for e in errors)


def test_rule_N4_extracted_claims_must_exist():
    from validate import validate_note_rules  # noqa: E402
    notes = {
        "NOTE-0001": {
            "id": "NOTE-0001", "source": "handoff",
            "source_path": "memory/tools/tests/fixtures/notes_handoff_src/2026-05-17_demo.md",
            "topics": ["training-infra"], "extracted_claims": ["CLM-9999"],
            "_path": NOTE_FIXTURES / "NOTE-0001.md",
        },
    }
    errors = validate_note_rules(notes, claims={"CLM-0001": {}}, repo_root=REPO_ROOT_FOR_TESTS)
    assert any("CLM-9999" in e and "extracted" in e.lower() for e in errors)


def test_rule_N5_topic_top_level_in_whitelist():
    from validate import validate_note_rules  # noqa: E402
    notes = {
        "NOTE-0001": {
            "id": "NOTE-0001", "source": "handoff",
            "source_path": "memory/tools/tests/fixtures/notes_handoff_src/2026-05-17_demo.md",
            "topics": ["not-a-real-bucket", "lstm"],
            "extracted_claims": [],
            "_path": NOTE_FIXTURES / "NOTE-0001.md",
        },
    }
    errors = validate_note_rules(notes, claims={}, repo_root=REPO_ROOT_FOR_TESTS)
    assert any("topics[0]" in e or "top-level" in e for e in errors)


def test_clean_note_fixtures_have_no_errors():
    from validate import load_notes, validate_note_rules  # noqa: E402
    notes = load_notes(NOTE_FIXTURES)
    fake_claims = {"CLM-0001": {}}
    errors = validate_note_rules(notes, claims=fake_claims, repo_root=REPO_ROOT_FOR_TESTS)
    assert errors == [], f"unexpected errors on clean fixtures: {errors}"


# ---------- Cross-entity coverage warnings (X1, X2) ----------


def test_warning_X1_adr_without_note_warns(tmp_path):
    """X1: every docs/adr/*.md should have at least one note pointing to it."""
    from validate import warn_cross_entity_adr_coverage  # noqa: E402
    adr_dir = tmp_path / "adr"
    adr_dir.mkdir()
    (adr_dir / "0001-foo.md").write_text("# ADR placeholder\n")
    notes: dict[str, dict[str, Any]] = {}
    warnings = warn_cross_entity_adr_coverage(notes, adr_dir=adr_dir)
    assert any("0001-foo.md" in w for w in warnings)


def test_warning_X1_adr_with_note_silent(tmp_path):
    from validate import warn_cross_entity_adr_coverage  # noqa: E402
    adr_dir = tmp_path / "adr"
    adr_dir.mkdir()
    (adr_dir / "0001-foo.md").write_text("# ADR\n")
    notes = {
        "NOTE-0001": {
            "id": "NOTE-0001", "source": "adr-rationale",
            "source_path": str((adr_dir / "0001-foo.md").as_posix()),
        }
    }
    warnings = warn_cross_entity_adr_coverage(notes, adr_dir=adr_dir)
    assert warnings == []


def test_warning_X2_handoff_without_note_warns(tmp_path):
    from validate import warn_cross_entity_handoff_coverage  # noqa: E402
    handoffs_dir = tmp_path / "handoffs"
    handoffs_dir.mkdir()
    (handoffs_dir / "2026-05-17_demo.md").write_text("handoff body\n")
    (handoffs_dir / "README.md").write_text("intentionally excluded\n")
    (handoffs_dir / "_archive").mkdir()
    (handoffs_dir / "_archive" / "old.md").write_text("excluded\n")
    warnings = warn_cross_entity_handoff_coverage({}, handoffs_dir=handoffs_dir)
    # README.md and _archive/ excluded; only 2026-05-17_demo.md should warn.
    assert any("2026-05-17_demo.md" in w for w in warnings)
    assert not any("README.md" in w for w in warnings)
    assert not any("_archive" in w for w in warnings)
