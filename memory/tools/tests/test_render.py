from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from render import render_state  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def _render(tmp_path) -> str:
    out = tmp_path / "STATE.md"
    render_state(
        claims_dir=FIXTURES / "claims",
        rounds_dir=FIXTURES / "rounds",
        questions_dir=FIXTURES / "questions",
        out_path=out,
    )
    return out.read_text(encoding="utf-8")


def test_render_state_has_six_sections(tmp_path):
    """Active-oracle STATE.md has exactly the 6 mandated sections."""
    text = _render(tmp_path)
    for section in (
        "## Headline Numbers",
        "## In-Flight",
        "## Open Questions",
        "## Recently Closed",
        "## Latest Round",
        "## Stats",
    ):
        assert section in text, f"missing section: {section}"


def test_render_state_has_no_legacy_sections(tmp_path):
    """The old 'Open Decisions' and 'Most Recent Handoff' sections are gone."""
    text = _render(tmp_path)
    assert "## Open Decisions" not in text
    assert "Most Recent Handoff" not in text


def test_render_state_headline_lists_tagged_claims(tmp_path):
    """Claims with tags=[headline] and status=current appear under Headlines."""
    text = _render(tmp_path)
    headlines = text.split("## Headline Numbers")[1].split("## ")[0]
    # CLM-0001 has tags: [test, headline], status: current
    assert "CLM-0001" in headlines
    # CLM-0002 is superseded — must not appear
    assert "- CLM-0002 " not in headlines
    # CLM-0004 is type=decision (not headline) — must not appear
    assert "- CLM-0004 " not in headlines


def test_render_state_open_questions_section(tmp_path):
    """Q files with status=open are listed; closed Qs are not."""
    text = _render(tmp_path)
    open_qs = text.split("## Open Questions")[1].split("## ")[0]
    assert "Q-0001" in open_qs
    assert "Test open question" in open_qs
    # closed Q should not appear in open section
    assert "Q-0002" not in open_qs


def test_render_state_recently_closed_questions(tmp_path):
    """Closed Q-0002 appears in Recently Closed with its closing round + claim."""
    text = _render(tmp_path)
    closed = text.split("## Recently Closed")[1].split("## ")[0]
    assert "Q-0002" in closed
    assert "closed-positive" in closed
    assert "R02" in closed
    assert "CLM-0003" in closed


def test_render_state_latest_round_extracts_tldr(tmp_path):
    """Latest Round section pulls a one-line TL;DR from the verdict."""
    text = _render(tmp_path)
    latest = text.split("## Latest Round")[1].split("## ")[0]
    assert "R02" in latest
    assert "Test round 2 produced" in latest


def test_render_state_in_flight_detects_plan_without_verdict(tmp_path):
    """A round dir with plan.md but no verdict.md surfaces as In-Flight."""
    # Build an isolated fixture with one in-flight round
    rounds_dir = tmp_path / "rounds"
    (rounds_dir / "R03").mkdir(parents=True)
    (rounds_dir / "R03" / "plan.md").write_text("# R03 plan", encoding="utf-8")
    out = tmp_path / "STATE.md"
    render_state(
        claims_dir=FIXTURES / "claims",
        rounds_dir=rounds_dir,
        questions_dir=FIXTURES / "questions",
        out_path=out,
    )
    text = out.read_text(encoding="utf-8")
    in_flight = text.split("## In-Flight")[1].split("## ")[0]
    assert "R03" in in_flight


def test_render_state_in_flight_says_none_when_clean(tmp_path):
    """If every round has a verdict.md, In-Flight reports (none)."""
    text = _render(tmp_path)
    in_flight = text.split("## In-Flight")[1].split("## ")[0]
    assert "(none)" in in_flight


def test_render_state_stats_includes_question_counts(tmp_path):
    """Stats line includes claim, round, and Q counts."""
    text = _render(tmp_path)
    stats = text.split("## Stats")[1]
    assert "4 claims" in stats
    assert "2 rounds" in stats
    # 2 questions total (1 open + 1 closed)
    assert "2 questions" in stats


# ---------- Hotfix regressions (R39 review punch list) ----------


def test_extract_tldr_skips_horizontal_rule(tmp_path):
    """H6: when TL;DR body is entirely blockquoted, the trailing `---` separator
    line must not be returned as the TL;DR text."""
    from render import _extract_tldr  # noqa: E402
    verdict = tmp_path / "v.md"
    verdict.write_text(
        "# Rxx\n**Status**: COMPLETE\n\n## TL;DR\n\n"
        "> body is all in a blockquote\n"
        "> spanning multiple lines\n"
        "\n"
        "---\n\n"
        "## Next section\nbody.\n",
        encoding="utf-8",
    )
    result = _extract_tldr(verdict)
    # `---` is a horizontal rule, not the TL;DR — function should return None
    # or the body of the blockquote, never the rule itself.
    assert result != "---", \
        f"_extract_tldr should not return the horizontal rule; got {result!r}"


def test_extract_tldr_returns_first_blockquote_text(tmp_path):
    """When the TL;DR body is a blockquote, the rendered TL;DR should pull
    the first line of blockquote text (with the leading `>` stripped),
    not return None."""
    from render import _extract_tldr  # noqa: E402
    verdict = tmp_path / "v.md"
    verdict.write_text(
        "# Rxx\n**Status**: COMPLETE\n\n## TL;DR\n\n"
        "> This is the actual summary.\n"
        "> Continues on the next line.\n"
        "\n## Next\n",
        encoding="utf-8",
    )
    result = _extract_tldr(verdict)
    assert result is not None and "actual summary" in result, \
        f"expected blockquote content; got {result!r}"


def test_recently_closed_sorts_by_round_number_not_lex(tmp_path):
    """H4: closed_qs sort must be numeric so R10 > R9, not lexicographic."""
    # Build a fixture with 4 closed Qs across R2, R9, R10, R11
    claims_dir = tmp_path / "claims"
    claims_dir.mkdir()
    for cid in ("CLM-0001", "CLM-0002", "CLM-0003", "CLM-0004"):
        (claims_dir / f"{cid}.md").write_text(
            f"---\nid: {cid}\ntype: finding\ntrust: V\nstatus: current\n"
            f"statement: x\n---\n", encoding="utf-8",
        )
    rounds_dir = tmp_path / "rounds"
    for r in ("R02", "R09", "R10", "R11"):
        (rounds_dir / r).mkdir(parents=True)
        (rounds_dir / r / "verdict.md").write_text(
            f"# {r}\n**Status**: COMPLETE\n## TL;DR\nx\n"
            "## Questions opened\n- none\n"
            "## Questions closed\n- none\n"
            "## Questions advanced\n- none\n",
            encoding="utf-8",
        )
    questions_dir = tmp_path / "questions"
    questions_dir.mkdir()
    for i, r in enumerate(("R02", "R09", "R10", "R11"), start=1):
        qid = f"Q-{i:04d}"
        cid = f"CLM-{i:04d}"
        (questions_dir / f"{qid}.md").write_text(
            f"---\nid: {qid}\nstatus: closed-positive\ntitle: q{i}\n"
            f"opened_round: R02\nclosed_round: {r}\nclosed_by: {cid}\n---\n",
            encoding="utf-8",
        )
    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out)
    text = out.read_text(encoding="utf-8")
    closed = text.split("## Recently Closed")[1].split("## ")[0]
    # Most-recent-3 should be R11, R10, R09 in that order (numerically newest first).
    # Lexicographic order would give R11, R10, R09 too coincidentally — but
    # also R02 would beat R09 if we had digits mixed. Stronger check: R02
    # (oldest) must NOT appear in the last-3 slice.
    assert "Q-0001" not in closed, \
        "Q-0001 (closed @ R02, oldest) should not appear in 'Recently Closed (last 3)'"
    # And the order should be R11 > R10 > R09 (numeric).
    pos_r11 = closed.find("R11")
    pos_r10 = closed.find("R10")
    pos_r09 = closed.find("R09")
    assert 0 <= pos_r11 < pos_r10 < pos_r09, \
        f"expected R11 < R10 < R09 in section text; got positions {pos_r11}, {pos_r10}, {pos_r09}"


def test_latest_round_picks_newest_completed_when_newest_is_in_flight(tmp_path):
    """H5: when the newest-numbered round is in-flight (plan only), `Latest Round`
    must point at the newest *completed* round so STATE.md doesn't double-list
    the in-flight round in two sections."""
    claims_dir = tmp_path / "claims"
    claims_dir.mkdir()
    questions_dir = tmp_path / "questions"
    questions_dir.mkdir()
    rounds_dir = tmp_path / "rounds"
    # R01 completed, R02 completed, R03 in-flight (plan only)
    for r in ("R01", "R02"):
        d = rounds_dir / r
        d.mkdir(parents=True)
        (d / "verdict.md").write_text(
            f"# {r} verdict\n**Status**: COMPLETE\n## TL;DR\n"
            f"{r} did stuff.\n## Questions opened\n- none\n"
            "## Questions closed\n- none\n## Questions advanced\n- none\n",
            encoding="utf-8",
        )
    (rounds_dir / "R03").mkdir(parents=True)
    (rounds_dir / "R03" / "plan.md").write_text("# R03 plan", encoding="utf-8")
    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out)
    text = out.read_text(encoding="utf-8")
    in_flight = text.split("## In-Flight")[1].split("## ")[0]
    latest = text.split("## Latest Round")[1].split("## ")[0]
    # R03 must be in In-Flight, NOT in Latest Round
    assert "R03" in in_flight, f"R03 should be In-Flight; got: {in_flight}"
    assert "R03" not in latest, \
        f"R03 (in-flight) must not also appear in Latest Round; got: {latest}"
    # R02 (newest completed) should be Latest Round
    assert "R02" in latest, f"R02 should be Latest Round; got: {latest}"
    assert "R02 did stuff" in latest, "TL;DR should be extracted for R02"
