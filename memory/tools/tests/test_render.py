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
    assert "2 questions" in stats or "2 Q" in stats
