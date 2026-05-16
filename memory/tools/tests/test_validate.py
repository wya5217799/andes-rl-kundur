from pathlib import Path
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
