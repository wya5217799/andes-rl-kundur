"""Run repository-wide hygiene checks.

Motivation:
    Give humans, agents, pre-commit, and CI one deterministic repository-health
    interface instead of copying structural rules into each caller.

Usage:
    python scripts/repo_health.py check
    python scripts/repo_health.py check --format json --no-baseline
    python scripts/repo_health.py check --root C:\\path\\to\\checkout

Failure modes:
    Exit 1 means active policy findings or an invalid contract. Baselined debt
    remains visible but exits 0. The command never repairs or deletes files.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from andes_rl_kundur.repo_governance import (  # noqa: E402
    ValidationReport,
    repository_root,
    validate_repository,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="validate repository structure")
    check.add_argument(
        "--root",
        type=Path,
        default=repository_root(),
        help="repository root (defaults to the checkout containing this script)",
    )
    check.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="report format",
    )
    check.add_argument(
        "--no-baseline",
        action="store_true",
        help="treat existing debt as active findings",
    )
    return parser


def _text_report(report: ValidationReport) -> str:
    def ascii_safe(value: str) -> str:
        return value.encode("ascii", errors="backslashreplace").decode("ascii")

    lines: list[str] = []
    findings = report.findings
    for finding in findings:
        if finding.baselined:
            status = "BASELINED"
        elif finding.severity == "warning":
            status = "WARN"
        else:
            status = "ERROR"
        lines.append(
            f"{status} {finding.rule_id} {ascii_safe(finding.path)} :: "
            f"{ascii_safe(finding.message)} [{finding.fingerprint}]"
        )
    baselined_count = sum(item.baselined for item in findings)
    prefix = "OK" if report.exit_code == 0 else "FAIL"
    lines.append(
        f"{prefix}: {len(report.active_findings)} active finding(s), "
        f"{baselined_count} baselined"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = validate_repository(args.root, use_baseline=not args.no_baseline)
    if args.format == "json":
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    else:
        print(_text_report(report))
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
