"""External deep-review intake lint: gate rounds that absorb an external review package.

Motivation (R474/R475, 2026-08-23): an external deep review package
(gpt_pro_r474_placebo_review_deep_20260823) proved the sealed R474 design
invalid as written (guardrail relaxation unnecessary, batch mixing,
materiality test mismatch) and forced a same-day abort. The package was
absorbed manually: copied into working/, hash-verified by hand, registered
in ARTIFACTS.json by hand, findings triaged by hand. There was no machine
check that the intake was complete, so a future package could be partially
absorbed (e.g. findings fixed but no verdict written, or hashes never
verified) without any gate noticing.

The codified rule (guardrails G.5, 2026-08-23) requires any round that
absorbs an external review package to: hash-verify the package against its
source, register it in ARTIFACTS.json, classify findings (P0/P1/minor) with
per-finding disposition, write the verdict into the round feed, and run this
lint at close-out.

This tool reads the round's plan, feed, and ARTIFACTS.json and reports:

- OK (exit 0): no external-review citation in the round.
- HINT (exit 0): external-review citation present and the mandatory intake
  elements are all present (registered artifact, hash sidecar/record,
  per-finding dispositions, feed verdict).
- VIOLATION (exit 1): external-review citation present but any mandatory
  intake element is missing.

Usage::

    python memory/tools/external_review_intake_lint.py R<N>

Exit codes: 0 = pass (or not applicable); 1 = violation.  The tool only
reads; it never edits the ledger.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_REVIEW_HINT = re.compile(
    r"deep[-_ ]?review|external[-_ ]?review|review[-_ ]?(package|bundle)"
    r"|placebo[-_ ]?review|深审|深度审查|外部审查",
    re.IGNORECASE,
)

_FINDING_HINT = re.compile(
    r"P0|P1|finding|发现|阻断项|severity|disposition|处置",
    re.IGNORECASE,
)

_VERDICT_HINT = re.compile(
    r"verdict|裁决|判定|DISPROVED|CONFIRMED|supported|refuted|undecidable|不成立|成立",
    re.IGNORECASE,
)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _manuscript_line(plan: str) -> str:
    match = re.search(r"^manuscript_line:\s*(\S+)", plan, re.MULTILINE)
    return match.group(1) if match else ""


def _line_dir(plan: str) -> Path:
    """Manuscript line ids use hyphens (yang-md-decoupling-marl) but the
    paper/ directory uses underscores (paper/yang_md_decoupling_marl)."""
    line_id = _manuscript_line(plan) or "yang-md-decoupling-marl"
    return ROOT / "paper" / line_id.replace("-", "_")


def check(round_id: str) -> tuple[int, list[str]]:
    problems: list[str] = []
    round_dir = ROOT / "memory" / "rounds" / round_id
    plan = _read(round_dir / "plan.md")
    line_dir = _line_dir(plan)
    artifacts = _load_json(line_dir / "ARTIFACTS.json")

    # Feed location: follow the line's experiment-feeds artifact if present,
    # else fall back to the default reports dir of the manuscript line.
    feed_dirs: list[Path] = []
    for item in artifacts.get("artifacts", []):
        if str(item.get("purpose", "")) == "experiment-feeds":
            feed_dirs.append(ROOT / str(item.get("path", "")))
    if not feed_dirs:
        feed_dirs.append(line_dir / "reports")
    feed = ""
    for feed_dir in feed_dirs:
        candidates = sorted(feed_dir.glob(f"{round_id}.md"))
        if candidates:
            feed = _read(candidates[0])
            break

    if not _REVIEW_HINT.search(plan) and not _REVIEW_HINT.search(feed):
        return 0, ["no external-review citation; not applicable"]

    # 1. Registered artifact in ARTIFACTS.json (purpose external-review or
    #    external-question with a review bundle path).
    registered = False
    for item in artifacts.get("artifacts", []):
        purpose = str(item.get("purpose", ""))
        if "review" in purpose or "external" in purpose:
            path = str(item.get("path", ""))
            if "working" in path or "gpt_pro" in path:
                registered = True
                break
    if not registered:
        problems.append("external review package not registered in ARTIFACTS.json")

    # 2. Hash record: either a SHA256SUMS file inside the registered bundle
    #    path, or an ARTIFACTS entry carrying a hash, or per-file sidecars.
    hash_ok = False
    for item in artifacts.get("artifacts", []):
        path = str(item.get("path", ""))
        if "working" not in path:
            continue
        bundle = ROOT / path
        if (bundle / "SHA256SUMS").is_file():
            hash_ok = True
            break
        if item.get("input_hashes"):
            hash_ok = True
            break
    if not hash_ok:
        problems.append("no hash record for the external review package (SHA256SUMS or ARTIFACTS input_hashes)")

    # 3. Per-finding disposition in the feed (P0/P1 classification + verdict).
    if feed:
        if not _FINDING_HINT.search(feed):
            problems.append("feed lacks per-finding classification/disposition")
        if not _VERDICT_HINT.search(feed):
            problems.append("feed lacks an intake verdict")
    else:
        problems.append("no feed exists for the absorbing round")

    if problems:
        return 1, problems
    return 0, ["external review intake complete (registered, hashed, findings disposed, verdict written)"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("round", help="round id, e.g. R475")
    args = parser.parse_args()
    code, messages = check(args.round)
    for message in messages:
        print(f"[{'VIOLATION' if code else 'OK'}] {message}")
    return code


if __name__ == "__main__":
    sys.exit(main())
