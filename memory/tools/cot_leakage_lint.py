"""CoT / design-session leakage lint: recall battery for ledger prose.

Motivation (2026-08-27): feed, claim, and verdict are AI-written.  The round
contract already bans duplication (single-source allocation table) and
narration ("写陈述不写叙述"), but nothing catches prose whose vantage is the
authoring session rather than the repository - dead design-session citations,
change narration, review choreography, or hedged planning residue.  The
dsh-trim-cot-leakage / dsh-prose-standard taxonomy was absorbed into
``skills/kundur-round/references/prose-leakage.md``; this tool is the recall
battery that surfaces candidate lines.

It is advisory by design: leakage is semantic, so regexes are probes that both
miss cases and can false-positive; the semantic judgement stays with the
agent/auditor - exactly how ``feed_check.py`` leaves "the same fact lives in
two homes" to the evidence audit.  Findings print as HINT and never block.

It reads a round's plan, feed, bound claims, and verdict, scans each line
against the battery, and prints ``HINT <class> <file>:<line>``.  Exit 0 even
when hints are found; exit 1 only when the round's plan is missing/unreadable.

Usage::

    python memory/tools/cot_leakage_lint.py R<N>

Exit codes: 0 = clean or hints printed (advisory); 1 = required input missing.
The tool only reads; it never edits the ledger.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# (class, pattern) recall battery.  Keep in sync with
# skills/kundur-round/references/prose-leakage.md.  High-precision markers
# only; the taxonomy doc owns the definition.  The bare noun phrase
# "this round" is deliberately absent: it names the round's own contract
# (plan subject, verdict "Questions ... (this round)" headers) and is not
# narration by itself - only "this round <change-verb>" is.
_BATTERY: list[tuple[str, re.Pattern[str]]] = [
    (
        "dead_citation",
        re.compile(
            r"\(decision\s+\d+\)|\(audit\s+[A-Z0-9_-]+\)|design\s*§\s*\d"
            r"|plan\s*§\s*\d",
            re.IGNORECASE,
        ),
    ),
    (
        "change_narration",
        re.compile(
            r"\bused to\b|\bno longer\b|\bthe old\b|\bpreviously\b|\bformerly\b"
            r"|\bthe previous (?:round|commit|PR)\b"
            r"|\b(?:a later|the next) (?:round|PR|commit)\b"
            r"|\bthis (?:round|PR|commit) "
            r"(?:adds|changes|introduces|removes|fixes|replaces|moves)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "review_choreography",
        re.compile(
            r"\brejected in review\b|\bthe reviewer\b|\breviewer "
            r"(?:confirmed|said|requested)\b|\baddressed (?:in|per) review\b"
            r"|\bv\d+ of this\b",
            re.IGNORECASE,
        ),
    ),
    (
        "self_justification",
        re.compile(
            r"\bthis is correct because\b|\bit is (?:safe|correct) because\b"
            r"|\bthe cast is safe\b",
            re.IGNORECASE,
        ),
    ),
    (
        "control_flow",
        re.compile(
            r"\bfirst we\b|\bthen we\b|\bwe first\b|\bnow we\b",
            re.IGNORECASE,
        ),
    ),
    (
        "hedge",
        re.compile(
            r"\bprobably fine\b|\bshould be (?:enough|fine|ok|okay)\b"
            r"|\bhopefully\b",
            re.IGNORECASE,
        ),
    ),
]

# Feed and claim are English surfaces by policy (SKILL.md §3 / CLAUDE.md 语言).
# A CJK run in either is an authoring-language slip (taxonomy class 8).
_CJK = re.compile(r"[\u4e00-\u9fff]")

# Keep rules that legitimately reuse these words: a round/claim id resolves at
# HEAD and is never flagged as leakage.  Line-level scanning already avoids
# bare id tokens, but skip whole lines that are only a backticked repo pointer
# to keep noise down.
_POINTER_LINE = re.compile(r"^\s*[-*]?\s*`[^`]+`\s*$")


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _find_feed(round_id: str, plan_text: str | None) -> Path | None:
    """Locate the round's feed, mirroring external_theory_intake_lint._find_feed.

    Prefer the manuscript-line report named after the round, then a results
    directory named after the round, then any FEED.md fallback.
    """
    line = None
    if plan_text:
        m = re.search(r"^manuscript_line:\s*(\S+)", plan_text, re.MULTILINE)
        if m:
            line = m.group(1).strip().strip("'\"")
    if line:
        direct = ROOT / "paper" / line / "reports" / f"{round_id}.md"
        if direct.exists():
            return direct
    candidates: list[Path] = []
    for pattern in (
        f"paper/*/reports/{round_id}.md",
        f"results/*/{round_id}.md",
        "results/*/FEED.md",
    ):
        candidates.extend(ROOT.glob(pattern))
    for candidate in candidates:
        if candidate.parent.name.lower().startswith(round_id.lower()):
            return candidate
    return candidates[0] if candidates else None


def _bound_claims(round_id: str) -> list[Path]:
    """Claims whose frontmatter ``round:`` matches this round."""
    out: list[Path] = []
    for p in sorted(ROOT.glob("memory/claims/CLM-*.md")):
        try:
            body = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if re.search(rf"(?m)^round:\s*{re.escape(round_id)}\s*$", body):
            out.append(p)
    return out


def _ascii(snippet: str) -> str:
    # Windows GBK terminals garble non-ASCII; echo an ASCII-safe snippet only.
    return snippet.encode("ascii", "replace").decode("ascii")


def _scan(name: str, text: str, *, check_cjk: bool) -> list[str]:
    hits: list[str] = []
    for index, line in enumerate(text.splitlines(), 1):
        if _POINTER_LINE.match(line):
            continue
        for cls, pattern in _BATTERY:
            if pattern.search(line):
                hits.append(
                    f"HINT {cls}: {name}:{index}: {_ascii(line.strip()[:120])}"
                )
                break
        if check_cjk and _CJK.search(line):
            hits.append(
                f"HINT language_slip: {name}:{index}: {_ascii(line.strip()[:120])}"
            )
    return hits


def lint(round_id: str) -> int:
    plan_path = ROOT / "memory" / "rounds" / round_id / "plan.md"
    plan_text = _read_text(plan_path)
    if plan_text is None:
        print(f"[{round_id}] NO-PLAN: {plan_path} unreadable or missing")
        return 1

    printed = 0

    # plan is a Chinese surface and the round's own contract: English leakage
    # markers only, no CJK probe.
    for hit in _scan("plan.md", plan_text, check_cjk=False):
        print(f"[{round_id}] {hit}")
        printed += 1

    feed = _find_feed(round_id, plan_text)
    if feed is not None:
        feed_text = _read_text(feed)
        if feed_text is not None:
            for hit in _scan(feed.name, feed_text, check_cjk=True):
                print(f"[{round_id}] {hit}")
                printed += 1

    for claim in _bound_claims(round_id):
        claim_text = _read_text(claim)
        if claim_text is None:
            continue
        for hit in _scan(claim.name, claim_text, check_cjk=True):
            print(f"[{round_id}] {hit}")
            printed += 1

    verdict_path = ROOT / "memory" / "rounds" / round_id / "verdict.md"
    verdict_text = _read_text(verdict_path)
    if verdict_text is not None:
        # verdict technical skeleton is Chinese; 给 PI 的话 is Chinese by policy.
        for hit in _scan("verdict.md", verdict_text, check_cjk=False):
            print(f"[{round_id}] {hit}")
            printed += 1

    if printed == 0:
        print(f"[{round_id}] OK: no leakage markers surfaced")
    else:
        print(
            f"[{round_id}] {printed} hint(s) above; advisory - judge each "
            f"semantically against references/prose-leakage.md, then fix or keep"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("round_id", help="round id, e.g. R433")
    args = parser.parse_args()
    return lint(args.round_id)


if __name__ == "__main__":
    sys.exit(main())
