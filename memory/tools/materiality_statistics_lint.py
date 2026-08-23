"""Materiality-statistics lint: gate claims that cite Holm/materiality wording.

Motivation (R473/R474, 2026-08-23): R473's headline claim said "Holm-rejected
at threshold 0.025, materially_supported=true" with p=0.015625, but that
p-value was a ZERO-null sign-flip test; the direct materiality test
(H0: effect <= log(1.10)) on the same six values gives p=2/64=0.03125, which
fails Holm at 0.025. The claim's "Holm-controlled materiality" wording was
therefore stronger than what the procedure actually established. The codified
rule (guardrails G.3) requires any claim worded "Holm-controlled materiality"
/ "materially supported" / "effect > threshold" to be backed by a direct
boundary test with Holm on the materiality p-values themselves, never a
zero-null test plus a separate bootstrap CI lower bound.

This tool scans a claim file (or all claims) for materiality wording and
reports:

- OK (exit 0): no materiality wording, or the wording is accompanied by
  evidence of a direct boundary test (materiality p-value at the threshold,
  "at log(1.10)", "boundary", "materiality p").
- HINT (exit 0): materiality wording present; the backing description is
  ambiguous (e.g. only "CI lower bound") — human review required.
- VIOLATION (exit 1): materiality wording present with no boundary-test
  evidence at all.

Usage::

    python memory/tools/materiality_statistics_lint.py CLM-1475
    python memory/tools/materiality_statistics_lint.py --all

Exit codes: 0 = pass (or not applicable); 1 = violation.  The tool only
reads; it never edits the ledger.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAIMS_DIR = ROOT / "memory" / "claims"

_MATERIALITY_WORDING = re.compile(
    r"Holm[- ]?controlled|materially supported|materiality|超过 ?10%|大于 ?10%"
    r"|effect > ?log\(1\.10\)|geometric (lower bound|improvement)",
    re.IGNORECASE,
)

_BOUNDARY_EVIDENCE = re.compile(
    r"at (the )?(materiality )?boundary|at log\(1\.10\)|materiality p|"
    r"H0: effect ?<=|H0 ?: ?effect|direct (materiality )?test|"
    r"sign[- ]?flip.*(materiality|boundary)|检验.*(边界|log\(1\.10\))",
    re.IGNORECASE,
)

_ZERO_NULL_ONLY = re.compile(
    r"zero[- ]?null|against zero|at null 0|零效应",
    re.IGNORECASE,
)


def _classify(text: str) -> tuple[str, list[str]]:
    if not _MATERIALITY_WORDING.search(text):
        return "OK", ["no materiality wording; not applicable"]
    notes: list[str] = []
    if _BOUNDARY_EVIDENCE.search(text):
        notes.append("boundary-test evidence present")
    if _ZERO_NULL_ONLY.search(text) and not _BOUNDARY_EVIDENCE.search(text):
        notes.append("zero-null wording WITHOUT boundary-test evidence")
    if not _BOUNDARY_EVIDENCE.search(text):
        return "VIOLATION", notes + [
            "materiality wording present but no direct boundary-test evidence "
            "(guardrails G.3: zero-null p + bootstrap CI lower bound is NOT a "
            "Holm-controlled materiality test)"
        ]
    if _ZERO_NULL_ONLY.search(text):
        return "HINT", notes + [
            "materiality wording accompanied by zero-null wording; confirm the "
            "materiality p-values themselves carry the Holm, not only the zero-null p"
        ]
    return "OK", notes + ["materiality wording backed by boundary-test evidence"]


def check_claim(claim_id: str) -> tuple[str, list[str]]:
    path = CLAIMS_DIR / f"{claim_id}.md"
    if not path.is_file():
        return "VIOLATION", [f"claim file not found: {path}"]
    text = path.read_text(encoding="utf-8")
    return _classify(text)


def check_all() -> tuple[str, list[tuple[str, str, list[str]]]]:
    worst = "OK"
    rows: list[tuple[str, str, list[str]]] = []
    for path in sorted(CLAIMS_DIR.glob("CLM-*.md")):
        code, notes = _classify(path.read_text(encoding="utf-8"))
        if code == "VIOLATION":
            worst = "VIOLATION"
        elif code == "HINT" and worst == "OK":
            worst = "HINT"
        if code != "OK":
            rows.append((path.stem, code, notes))
    return worst, rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("claim", nargs="?", help="claim id, e.g. CLM-1475")
    parser.add_argument("--all", action="store_true", help="scan every claim file")
    args = parser.parse_args()
    if args.all:
        code, rows = check_all()
        for claim_id, row_code, notes in rows:
            print(f"[{row_code}] {claim_id}: {'; '.join(notes)}")
        if code == "OK":
            print("[OK] no materiality-wording violations across all claims")
        return 1 if code == "VIOLATION" else 0
    if not args.claim:
        parser.error("claim id or --all required")
    code, notes = check_claim(args.claim)
    for note in notes:
        print(f"[{code}] {note}")
    return 1 if code == "VIOLATION" else 0


if __name__ == "__main__":
    sys.exit(main())
