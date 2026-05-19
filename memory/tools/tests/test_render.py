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
    """Active-oracle STATE.md has the 6 mandated sections (plus optional
    Leaderboard from R50 opt H — that's tested separately)."""
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


# ── R50 opt H: STATE.md ``## Leaderboard`` section ─────────────────────────


def _build_metric_fixture(tmp_path, entries: list[tuple[str, float | None]]):
    """Make tmp_path/{claims, rounds, questions} with one claim per
    (cid, metric_value) pair. ``None`` value means no metric field."""
    claims_dir = tmp_path / "claims"
    claims_dir.mkdir()
    for cid, value in entries:
        metric_block = (
            f"metric:\n  name: 6_axis\n  value: {value}\n" if value is not None else ""
        )
        (claims_dir / f"{cid}.md").write_text(
            f"---\nid: {cid}\ntype: finding\ntrust: V\nstatus: current\n"
            f"statement: x\nround: R01\n{metric_block}---\n",
            encoding="utf-8",
        )
    rounds_dir = tmp_path / "rounds"
    rounds_dir.mkdir()
    (rounds_dir / "R01").mkdir()
    (rounds_dir / "R01" / "verdict.md").write_text(
        "# R01\n**Status**: COMPLETE\n## TL;DR\nx\n"
        "## Questions opened\n- none\n## Questions closed\n- none\n"
        "## Questions advanced\n- none\n",
        encoding="utf-8",
    )
    questions_dir = tmp_path / "questions"
    questions_dir.mkdir()
    return claims_dir, rounds_dir, questions_dir


def test_leaderboard_section_emitted_when_any_claim_has_metric(tmp_path):
    claims_dir, rounds_dir, questions_dir = _build_metric_fixture(
        tmp_path, [("CLM-0001", 0.334), ("CLM-0002", 0.275)],
    )
    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out)
    text = out.read_text(encoding="utf-8")

    assert "## Leaderboard" in text, "leaderboard section must be present"


def test_leaderboard_sorts_by_metric_value_descending(tmp_path):
    claims_dir, rounds_dir, questions_dir = _build_metric_fixture(
        tmp_path,
        [("CLM-0001", 0.275), ("CLM-0002", 0.334), ("CLM-0003", 0.117)],
    )
    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out)
    text = out.read_text(encoding="utf-8")

    lb = text.split("## Leaderboard")[1].split("## ")[0]
    pos_top = lb.find("CLM-0002")  # value 0.334 (highest)
    pos_mid = lb.find("CLM-0001")  # value 0.275
    pos_low = lb.find("CLM-0003")  # value 0.117 (lowest)
    assert 0 <= pos_top < pos_mid < pos_low, (
        f"expected descending sort by metric.value; got positions "
        f"top={pos_top}, mid={pos_mid}, low={pos_low}"
    )


def test_leaderboard_excludes_claims_without_metric(tmp_path):
    claims_dir, rounds_dir, questions_dir = _build_metric_fixture(
        tmp_path, [("CLM-0001", 0.334), ("CLM-0002", None)],
    )
    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out)
    text = out.read_text(encoding="utf-8")

    lb = text.split("## Leaderboard")[1].split("## ")[0]
    assert "CLM-0001" in lb
    assert "CLM-0002" not in lb


def test_leaderboard_shows_metric_value(tmp_path):
    """Each leaderboard row prints the metric value so a reader can scan."""
    claims_dir, rounds_dir, questions_dir = _build_metric_fixture(
        tmp_path, [("CLM-0001", 0.334)],
    )
    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out)
    text = out.read_text(encoding="utf-8")

    lb = text.split("## Leaderboard")[1].split("## ")[0]
    assert "0.334" in lb or "0.33" in lb, f"value should appear in leaderboard: {lb}"


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


# ── ADR-0003: PI briefing layer (R59+) ─────────────────────────────────────────


def _build_briefing_fixture(tmp_path, *, rounds: list[tuple[str, str | None]]):
    """Build a minimal valid (claims, rounds, questions) trio. Each (round_id,
    briefing_body) tuple either gets a briefing section or no briefing
    (body=None — verdict still has the 3 Q-sections so it's structurally
    valid for non-R59 cases)."""
    claims_dir = tmp_path / "claims"
    claims_dir.mkdir()
    questions_dir = tmp_path / "questions"
    questions_dir.mkdir()
    rounds_dir = tmp_path / "rounds"
    for round_id, body in rounds:
        d = rounds_dir / round_id
        d.mkdir(parents=True)
        briefing = (
            f"## 给 PI 的话\n\n{body}\n\n" if body else ""
        )
        (d / "verdict.md").write_text(
            f"# {round_id} verdict\n**Status**: COMPLETE\n"
            f"## TL;DR\n{round_id} TL;DR text.\n\n"
            "## Questions opened (this round)\n- none\n\n"
            "## Questions closed (this round)\n- none\n\n"
            "## Questions advanced (this round)\n- none\n\n"
            f"{briefing}",
            encoding="utf-8",
        )
    return claims_dir, rounds_dir, questions_dir


def test_pi_briefing_section_absent_when_no_r59_verdict(tmp_path):
    """STATE.md must NOT carry the briefing section header when no R≥59
    verdict has been written yet. Prevents an empty/awkward top section
    in the early phase before R59 closes."""
    claims_dir, rounds_dir, questions_dir = _build_briefing_fixture(
        tmp_path,
        rounds=[("R58", "**结果（一句话）**：pre-cutoff round.")],  # R58 < 59
    )
    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out)
    text = out.read_text(encoding="utf-8")
    assert "## 给 PI 的简报" not in text, \
        "briefing header must be absent until first R≥59 verdict exists"


def test_pi_briefing_section_extracted_from_r59(tmp_path):
    """A single R59 verdict with a briefing populates the top section."""
    body = (
        "**这周干了啥**：跑测试。\n"
        "**结果（一句话）**：通过了。\n"
        "**意外**：无。\n"
        "**我默认下一步做**：归档。\n"
        "**你想插一脚就说**：无需。"
    )
    claims_dir, rounds_dir, questions_dir = _build_briefing_fixture(
        tmp_path, rounds=[("R59", body)],
    )
    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out)
    text = out.read_text(encoding="utf-8")
    assert "## 给 PI 的简报（最新一轮 — R59）" in text
    # All five sub-segments must appear verbatim in the briefing
    briefing = text.split("## 给 PI 的简报")[1].split("## ")[0]
    for label in (
        "这周干了啥", "结果（一句话）", "意外",
        "我默认下一步做", "你想插一脚就说",
    ):
        assert label in briefing, f"missing sub-segment {label!r}"


def test_pi_briefing_picks_newest_round(tmp_path):
    """When multiple R≥59 verdicts have briefings, the newest one wins
    the top spot."""
    claims_dir, rounds_dir, questions_dir = _build_briefing_fixture(
        tmp_path,
        rounds=[
            ("R59", "**结果（一句话）**：older briefing."),
            ("R60", "**结果（一句话）**：newer briefing."),
        ],
    )
    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out)
    text = out.read_text(encoding="utf-8")
    assert "## 给 PI 的简报（最新一轮 — R60）" in text
    briefing = text.split("## 给 PI 的简报")[1].split("## ")[0]
    assert "newer briefing" in briefing
    assert "older briefing" not in briefing  # belongs in 历史简报 instead


def test_pi_briefing_historical_section_lists_past_rounds(tmp_path):
    """The 历史简报 section shows one-line headlines from older R≥59 rounds,
    newest first. The current latest round is excluded (it's at the top
    instead)."""
    claims_dir, rounds_dir, questions_dir = _build_briefing_fixture(
        tmp_path,
        rounds=[
            ("R59", "**结果（一句话）**：first briefing ever."),
            ("R60", "**结果（一句话）**：second briefing."),
            ("R61", "**结果（一句话）**：latest briefing."),
        ],
    )
    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out)
    text = out.read_text(encoding="utf-8")
    assert "## 历史简报" in text
    historical = text.split("## 历史简报")[1]
    # R59 and R60 appear as historical; R61 (latest) does not
    assert "R59" in historical and "first briefing ever" in historical
    assert "R60" in historical and "second briefing" in historical
    assert "R61" not in historical
    # Newest historical first
    pos_r60 = historical.find("R60")
    pos_r59 = historical.find("R59")
    assert 0 <= pos_r60 < pos_r59, "newer historical briefings must come first"


def test_pi_briefing_glossary_annotates_first_use_only(tmp_path):
    """Glossary auto-annotation appends `(definition)` to the FIRST
    occurrence of each term in the briefing; subsequent occurrences in
    the same briefing are bare."""
    glossary = tmp_path / "glossary.yml"
    glossary.write_text(
        "LSTM: 记前几步的网络\nHAWE: 加权融合集成\n",
        encoding="utf-8",
    )
    body = (
        "**这周干了啥**：跑 LSTM 实验，然后 HAWE 集成。\n"
        "**结果（一句话）**：LSTM 表现好。\n"  # second LSTM — must NOT annotate
        "**意外**：无。\n"
        "**我默认下一步做**：扩展。\n"
        "**你想插一脚就说**：无。"
    )
    claims_dir, rounds_dir, questions_dir = _build_briefing_fixture(
        tmp_path, rounds=[("R59", body)],
    )
    out = tmp_path / "STATE.md"
    render_state(
        claims_dir, rounds_dir, questions_dir, out,
        glossary_path=glossary,
    )
    text = out.read_text(encoding="utf-8")
    briefing = text.split("## 给 PI 的简报")[1].split("## ")[0]

    # First LSTM occurrence is annotated
    assert "LSTM(记前几步的网络)" in briefing
    # First HAWE occurrence is annotated
    assert "HAWE(加权融合集成)" in briefing
    # Second LSTM occurrence is bare — only ONE annotated form should appear
    assert briefing.count("LSTM(记前几步的网络)") == 1, \
        "subsequent LSTM occurrence should NOT be annotated"


def test_pi_briefing_glossary_handles_chinese_embedded_terms(tmp_path):
    """ASCII-word lookarounds — Chinese characters around a term don't
    break the boundary. `用LSTM时` still matches `LSTM`."""
    glossary = tmp_path / "glossary.yml"
    glossary.write_text("LSTM: 记前几步的网络\n", encoding="utf-8")
    body = (
        "**这周干了啥**：用LSTM时遇到问题。\n"
        "**结果（一句话）**：解决了。\n"
        "**意外**：无。\n"
        "**我默认下一步做**：归档。\n"
        "**你想插一脚就说**：无。"
    )
    claims_dir, rounds_dir, questions_dir = _build_briefing_fixture(
        tmp_path, rounds=[("R59", body)],
    )
    out = tmp_path / "STATE.md"
    render_state(
        claims_dir, rounds_dir, questions_dir, out,
        glossary_path=glossary,
    )
    text = out.read_text(encoding="utf-8")
    assert "LSTM(记前几步的网络)" in text


def test_pi_briefing_longer_term_matches_before_shorter_substring(tmp_path):
    """When glossary has both `6-axis geo` and `6-axis`, a verdict text
    containing `6-axis geo` must annotate as the longer phrase (not split
    `6-axis` + leftover `geo`)."""
    glossary = tmp_path / "glossary.yml"
    glossary.write_text(
        "6-axis: 6 项性能复合评分\n6-axis geo: 6 项性能几何平均\n",
        encoding="utf-8",
    )
    body = (
        "**这周干了啥**：算了 6-axis geo 分数。\n"
        "**结果（一句话）**：0.5。\n"
        "**意外**：无。\n"
        "**我默认下一步做**：归档。\n"
        "**你想插一脚就说**：无。"
    )
    claims_dir, rounds_dir, questions_dir = _build_briefing_fixture(
        tmp_path, rounds=[("R59", body)],
    )
    out = tmp_path / "STATE.md"
    render_state(
        claims_dir, rounds_dir, questions_dir, out,
        glossary_path=glossary,
    )
    text = out.read_text(encoding="utf-8")
    assert "6-axis geo(6 项性能几何平均)" in text
    # Shorter form must NOT also be annotated separately in this briefing
    assert "6-axis(6 项性能复合评分)" not in text


def test_pi_briefing_no_glossary_path_no_annotation(tmp_path):
    """When no glossary path is passed, briefing renders without annotation
    (backward-compatible with the old render_state signature)."""
    body = (
        "**这周干了啥**：用 LSTM。\n"
        "**结果（一句话）**：好。\n"
        "**意外**：无。\n"
        "**我默认下一步做**：归档。\n"
        "**你想插一脚就说**：无。"
    )
    claims_dir, rounds_dir, questions_dir = _build_briefing_fixture(
        tmp_path, rounds=[("R59", body)],
    )
    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out)  # no glossary_path
    text = out.read_text(encoding="utf-8")
    assert "## 给 PI 的简报" in text
    assert "LSTM(" not in text  # no annotation


# ── Task 6: Archive Index section (Note entity) ─────────────────────────────


def test_archive_index_section_emitted_when_notes_exist(tmp_path):
    """When notes/ dir has at least 1 note, STATE.md must contain
    `## Archive Index` section."""
    from render import render_state  # noqa: E402

    claims_dir = tmp_path / "claims"
    rounds_dir = tmp_path / "rounds"
    questions_dir = tmp_path / "questions"
    notes_dir = tmp_path / "notes"
    claims_dir.mkdir(); rounds_dir.mkdir(); questions_dir.mkdir(); notes_dir.mkdir()

    (notes_dir / "NOTE-0001.md").write_text("""---
id: NOTE-0001
source: handoff
source_path: dummy
date: 2026-05-17
related_rounds: [R58]
topics: [training-infra, lstm]
extracted_claims: []
status: ingested
---

## Summary
Demo note for the archive-index test.

## Key facts (claim candidates)
- foo

## Open threads
- bar
""", encoding="utf-8")

    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out, notes_dir=notes_dir)
    text = out.read_text(encoding="utf-8")
    assert "## Archive Index" in text
    assert "[training-infra]" in text
    assert "NOTE-0001" in text


def test_archive_index_appears_before_stats_section(tmp_path):
    """Archive Index (section 5c) must render before Stats (section 6)
    per the render.py docstring section order."""
    from render import render_state  # noqa: E402

    claims_dir = tmp_path / "claims"
    rounds_dir = tmp_path / "rounds"
    questions_dir = tmp_path / "questions"
    notes_dir = tmp_path / "notes"
    claims_dir.mkdir(); rounds_dir.mkdir(); questions_dir.mkdir(); notes_dir.mkdir()

    (notes_dir / "NOTE-0001.md").write_text("""---
id: NOTE-0001
source: handoff
source_path: dummy
date: 2026-05-17
related_rounds: [R58]
topics: [training-infra]
extracted_claims: []
status: ingested
---

## Summary
Order test note.
""", encoding="utf-8")

    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out, notes_dir=notes_dir)
    text = out.read_text(encoding="utf-8")
    assert text.index("## Archive Index") < text.index("## Stats")


def test_archive_index_section_omitted_when_no_notes(tmp_path):
    from render import render_state  # noqa: E402
    claims_dir = tmp_path / "claims"
    rounds_dir = tmp_path / "rounds"
    questions_dir = tmp_path / "questions"
    notes_dir = tmp_path / "notes"
    claims_dir.mkdir(); rounds_dir.mkdir(); questions_dir.mkdir(); notes_dir.mkdir()
    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out, notes_dir=notes_dir)
    text = out.read_text(encoding="utf-8")
    assert "## Archive Index" not in text


def test_archive_index_shows_extraction_count(tmp_path):
    from render import render_state  # noqa: E402
    claims_dir = tmp_path / "claims"
    rounds_dir = tmp_path / "rounds"
    questions_dir = tmp_path / "questions"
    notes_dir = tmp_path / "notes"
    claims_dir.mkdir(); rounds_dir.mkdir(); questions_dir.mkdir(); notes_dir.mkdir()

    # Two notes in training-infra; one has extracted_claims, one doesn't.
    (notes_dir / "NOTE-0001.md").write_text("""---
id: NOTE-0001
source: handoff
source_path: dummy
date: 2026-05-17
related_rounds: []
topics: [training-infra]
extracted_claims: [CLM-0001]
status: partially-extracted
---

## Summary
n1

## Key facts (claim candidates)
- a

## Open threads
- b
""", encoding="utf-8")
    (notes_dir / "NOTE-0002.md").write_text("""---
id: NOTE-0002
source: handoff
source_path: dummy
date: 2026-05-17
related_rounds: []
topics: [training-infra]
extracted_claims: []
status: ingested
---

## Summary
n2

## Key facts (claim candidates)
- a

## Open threads
- b
""", encoding="utf-8")

    out = tmp_path / "STATE.md"
    render_state(claims_dir, rounds_dir, questions_dir, out, notes_dir=notes_dir)
    text = out.read_text(encoding="utf-8")
    # Per spec §9 decision 1: bucket line shows "X notes · Y claims extracted"
    assert "2 notes" in text
    assert "1 claim" in text  # singular OK; bucket line is "N notes · M claim(s) extracted"
