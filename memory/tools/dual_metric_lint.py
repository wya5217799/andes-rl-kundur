"""Lint claims for single-metric framing that should be dual-metric.

Motivation (CLM-0430, 2026-05-20)
---------------------------------
Every ``final_eval_summary.json`` carries both ``geo`` (project 11-axis
v3.1 ranker) and ``cum_rf`` (paper Yang2023 §IV-C metric). Through
this whole session, however, claims about reward ablations cited only
``geo``, leading to the "paper Eq.14 vestigial" framing being
substantially over-stated; once cum_rf was audited it showed a
consistent 3-6% degradation under only-phi_abs. CLM-0430 wrote up
the methodological correction; this linter exists to prevent
recurrence by failing CI / pre-commit when a paper-reward-ablation
claim is single-metric.

What "should be dual-metric" means
----------------------------------
Triggered when ALL three are true:

1. The claim's tags include ANY of the paper-integrity tags
   (``paper-sec-iv-d-*``, ``paper-eq14-*``, ``gauge-invariance``,
   ``paper-strict-*``, ``reward-reproducibility-gap``). These
   characterise reward-ablation claims, which are the ones for which
   the cum_rf vs geo divergence matters most.
2. The statement cites ``geo`` (any form: ``geo=``, ``geo `` X, etc.).
3. The statement does NOT mention ``cum_rf``.

The linter reports each violator and exits 1 (so it composes with
``validate.py`` in pre-commit / CI). When run with ``--fix`` it does
not auto-edit (statement bodies are author prose) but prints the
suggested addition (a one-line dual-metric note pointing at the
relevant final_eval_summary.json).

Usage
-----
::

    # Lint
    $ python memory/tools/dual_metric_lint.py
    DUAL-METRIC GAP: CLM-0410 cites geo without cum_rf
      tags include: paper-eq14-partial-inertness-confirmed
      add: "cum_rf=-0.0917 (paper §IV-C)"

    # Lint a single claim
    $ python memory/tools/dual_metric_lint.py --claim CLM-0410
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Reuse validate's loader so frontmatter parsing stays consistent
sys.path.insert(0, str(Path(__file__).parent))
from validate import load_claims  # noqa: E402

# Tags that mark a claim as paper-reward-ablation territory.
# Substring match, case-insensitive. Add new tags here as the
# paper-integrity surface grows.
_DUAL_METRIC_TAGS = (
    "paper-sec-iv-d",
    "paper-eq14",
    "paper-strict",
    "gauge-invariance",
    "reward-reproducibility",
    "scalar-onlyphiabs",
    "hreg-onlyphiabs",
    "onlyphiabs",      # generic "only phi_abs" comparison
    "phi_h",           # paper-term decomposition (e.g. CLM-0420)
    "phi_d",
    "phi_f",
    "paper-faithful",
)

# Patterns indicating the body cites the project 11-axis metric.
_GEO_CITATION = re.compile(
    r"\bgeo\b\s*[=≈:](\s*\d|\s*[-+])"  # geo=0.39 / geo: 0.39 / geo≈ 0.4
    r"|\bgeo\b\s*\d+\.\d+",            # geo 0.39
    re.IGNORECASE,
)

# Patterns indicating the body cites the paper metric. Required when
# a geo citation is present and tag is paper-integrity.
_CUM_RF_CITATION = re.compile(
    r"\bcum_rf\b|\bpaper.metric\b|"
    r"§\s*IV-C|sec.iv-c|Yang2023.*§|paper.cited.metric",
    re.IGNORECASE,
)


def _has_dual_metric_tag(tags: list[str]) -> tuple[bool, list[str]]:
    """Return (matched_any, list_of_matched_tag_strings)."""
    matched: list[str] = []
    for t in tags or []:
        if not isinstance(t, str):
            continue
        tl = t.lower()
        for marker in _DUAL_METRIC_TAGS:
            if marker in tl:
                matched.append(t)
                break
    return bool(matched), matched


def _statement_text(claim: dict) -> str:
    """Return claim['statement'] as a single string regardless of YAML
    encoding (literal | block, folded, plain). Empty string when
    missing — caller decides what to do with it."""
    s = claim.get("statement")
    if isinstance(s, str):
        return s
    if isinstance(s, list):
        return "\n".join(str(x) for x in s)
    return "" if s is None else str(s)


def lint_claims(claims: dict) -> list[tuple[str, list[str]]]:
    """Return list of (claim_id, matched_tags) for every claim that
    triggers the dual-metric gap rule."""
    violators: list[tuple[str, list[str]]] = []
    for cid in sorted(claims):
        c = claims[cid]
        # Skip already-superseded claims — they're frozen history;
        # the new (current) claim is what should pass lint.
        if c.get("status") in {"superseded", "obsoleted"}:
            continue
        tags = c.get("tags") or []
        triggered, matched_tags = _has_dual_metric_tag(tags)
        if not triggered:
            continue
        body = _statement_text(c)
        if not _GEO_CITATION.search(body):
            # Doesn't cite a number — could be a process/decision
            # claim. Don't false-positive on those.
            continue
        if _CUM_RF_CITATION.search(body):
            continue  # already dual-metric ✓
        violators.append((cid, matched_tags))
    return violators


def _format_violation(cid: str, matched_tags: list[str]) -> str:
    tag_preview = ", ".join(matched_tags[:3])
    if len(matched_tags) > 3:
        tag_preview += f", … ({len(matched_tags)} total)"
    return (
        f"DUAL-METRIC GAP: {cid} cites geo without cum_rf\n"
        f"  trigger tags: {tag_preview}\n"
        f"  fix: add cum_rf=… (paper §IV-C) alongside the geo number,\n"
        f"       and link the source final_eval_summary.json in provenance."
    )


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--claims-dir", default="memory/claims",
        help="Path to claims dir (default: memory/claims)",
    )
    parser.add_argument(
        "--claim", default=None,
        help="Lint a single claim id (e.g. CLM-0410)",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-violation detail; just exit with 0/1",
    )
    args = parser.parse_args()

    claims = load_claims(Path(args.claims_dir))
    if args.claim:
        claims = {args.claim: claims[args.claim]} if args.claim in claims else {}
        if not claims:
            print(f"# Claim {args.claim} not found", file=sys.stderr)
            sys.exit(2)

    violators = lint_claims(claims)
    if not violators:
        if not args.quiet:
            print(f"OK: {len(claims)} claims pass dual-metric lint")
        sys.exit(0)
    if not args.quiet:
        for cid, tags in violators:
            print(_format_violation(cid, tags))
        print()
        print(f"# {len(violators)} violator(s) — see CLM-0430 for context")
    sys.exit(1)


if __name__ == "__main__":
    _main()
