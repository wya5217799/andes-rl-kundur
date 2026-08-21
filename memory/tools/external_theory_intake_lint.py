"""External-theory intake lint: gate rounds that carry mechanism predictions.

Motivation (R422/R424/R432, 2026-08-19): external theory answers (GPT Pro,
theory-audit bundle, external solvers) were absorbed only halfway.  The
algebraic identities got repo-side numeric verification and entered the
feed/manuscript, but the mechanism predictions they carried never got their
required observables registered into a sealed protocol, so the predictions
were re-tested late or by accident — R422 mis-placed the effort channel,
R424 flipped the constraint sign, R432 added full telemetry four rounds
late.  The codified rule (CLAUDE.md "External theory intake") requires any
round that carries a mechanism prediction/hypothesis — whether sourced
from an external answer or an internal diagnostic feed (R435 lesson) — to
either register an observable list into the sealed protocol or record a
``not-pursued`` reason in the plan, and to write each prediction's verdict
(``supported``/``refuted``/``undecidable``) back into the feed.

This tool is the machine check for that rule.  It reads the round's plan
(and the feed when it exists) and reports:

- OK (exit 0): no mechanism prediction in the plan.
- HINT (exit 0): external-theory citation but algebra-only (no mechanism
  wording) — numeric verification is required by the publication gate,
  but this lint does not block on it.
- VIOLATION (exit 1): mechanism prediction with no ``## Theory intake``
  observable list and no ``not-pursued`` registration; or a feed exists
  but carries no verdict word.

Usage::

    python memory/tools/external_theory_intake_lint.py R<N>

Exit codes: 0 = pass (or not applicable); 1 = violation.  The tool only
reads; it never edits the ledger.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# External-theory provenance markers.  Keep in sync with
# skills/kundur-round/references/external-theory-intake.md.
_EXTERNAL_HINT = re.compile(
    r"gpt[-_ ]?pro|gpt[-_ ]?4|gptpro|theory[-_ ]?audit|vsg[-_ ]?audit"
    r"|external[-_ ]?(solver|answer|theory|math|consult)"
    r"|外部(解答|理论|数学|咨询|求解)",
    re.IGNORECASE,
)

# Mechanism / falsifiable-prediction markers.  A round that cites external
# theory AND carries these is on the observable-list hook, not the
# algebra-only path.
_MECHANISM_HINT = re.compile(
    r"mechanism|hypothes|预测|机制|假设|可证伪|prediction|falsifi",
    re.IGNORECASE,
)

# Absorption artifacts the plan must carry for a mechanism-bearing citation.
_THEORY_INTAKE_SECTION = re.compile(
    r"##\s*theory[-_ ]?intake|observable\s*:|可观测清单|可观测", re.IGNORECASE
)
_NOT_PURSUED = re.compile(r"not[-_ ]?pursued|不追", re.IGNORECASE)

# Verdict words the feed must write back per prediction.
_VERDICT = re.compile(
    r"\b(supported|refuted|undecidable)\b", re.IGNORECASE
)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _find_feed(round_id: str, plan_text: str | None) -> str | None:
    """Locate the round's feed by manuscript_line from the plan, falling
    back to a glob over the two canonical feed homes.

    Programme rounds (manuscript_line: null) write ``results/<run>/FEED.md``;
    the generic ``results/*/FEED.md`` glob is unordered, so a result
    directory named after this round is preferred before any fallback
    (2026-08-20: R445's lint once inspected an unrelated FEED.md).
    """
    line = None
    if plan_text:
        m = re.search(r"^manuscript_line:\s*(\S+)", plan_text, re.MULTILINE)
        if m:
            line = m.group(1).strip().strip("'\"")
    if line:
        direct = ROOT / "paper" / line / "reports" / f"{round_id}.md"
        if direct.exists():
            return str(direct)
    candidates: list[Path] = []
    for pattern in (
        f"paper/*/reports/{round_id}.md",
        f"results/*/{round_id}.md",
        "results/*/FEED.md",
    ):
        candidates.extend(ROOT.glob(pattern))
    for candidate in candidates:
        if candidate.parent.name.lower().startswith(round_id.lower()):
            return str(candidate)
    return str(candidates[0]) if candidates else None


def lint(round_id: str) -> int:
    plan_path = ROOT / "memory" / "rounds" / round_id / "plan.md"
    plan_text = _read_text(plan_path)
    if plan_text is None:
        print(f"[{round_id}] NO-PLAN: {plan_path} unreadable or missing")
        return 1

    has_mechanism = bool(_MECHANISM_HINT.search(plan_text))
    has_external = bool(_EXTERNAL_HINT.search(plan_text))

    # The observable-list gate fires on ANY mechanism prediction, whether the
    # hypothesis came from an external answer or an internal diagnostic feed
    # (R435 lesson: an R432-derived internal hypothesis also needs the list).
    if not has_mechanism:
        if has_external:
            print(
                f"[{round_id}] HINT: external-theory citation looks "
                f"algebra-only (no mechanism/prediction wording); numeric "
                f"verification is required before the feed/manuscript (see "
                f"references/external-theory-intake.md), but this lint does "
                f"not block"
            )
        else:
            print(f"[{round_id}] OK: no mechanism prediction; observable-list "
                  f"gate not applicable")
        return 0

    has_intake = bool(_THEORY_INTAKE_SECTION.search(plan_text))
    has_not_pursued = bool(_NOT_PURSUED.search(plan_text))
    if not has_intake and not has_not_pursued:
        print(
            f"[{round_id}] VIOLATION: plan carries a mechanism prediction/"
            f"hypothesis (external or internal) but no `## Theory intake` "
            f"observable list and no `not-pursued` registration; add one "
            f"(see references/external-theory-intake.md)"
        )
        return 1

    feed = _find_feed(round_id, plan_text)
    if feed is None:
        print(
            f"[{round_id}] PENDING: observable list/registration present but "
            f"no feed found yet — write the prediction verdicts "
            f"(supported/refuted/undecidable) into the feed before close-out"
        )
        return 1
    feed_text = _read_text(Path(feed))
    if feed_text is None:
        print(f"[{round_id}] PENDING: feed {feed} unreadable")
        return 1
    if not _VERDICT.search(feed_text):
        print(
            f"[{round_id}] VIOLATION: feed {feed} carries no prediction "
            f"verdict word (supported/refuted/undecidable); write each "
            f"prediction's verdict back explicitly"
        )
        return 1

    print(
        f"[{round_id}] OK: observable list/registration present and feed "
        f"writes prediction verdicts back"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("round_id", help="round id, e.g. R433")
    args = parser.parse_args()
    return lint(args.round_id)


if __name__ == "__main__":
    sys.exit(main())
