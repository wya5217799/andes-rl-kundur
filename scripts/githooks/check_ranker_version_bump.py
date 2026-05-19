"""Reject a commit that modifies paper_grade_axes.py without bumping RANKER_VERSION.

Background: paper_grade_axes was silently rewritten three times (R69, R71)
without any in-code version stamp. Result: numbers from different rounds
became silently incomparable. CLM-0005/0006/0007 (v2 7-axis) ended up in
STATE.md headlines alongside CLM-0094 (v3.1 11-axis) until the 2026-05-19
audit caught it. F6 from that audit installs this gate.

Rule: if the commit's staged diff for
``src/andes_rl_kundur/evaluation/paper_grade_axes.py`` touches any of:
- the axis-function bodies (``_max_abs_df_score``, ``_action_utilization``,
  ``_late_oscillation_inv``, ``_agent_min_activity``, ``_agent_P_balance``,
  etc.)
- the ``PAPER`` benchmark constants
- the aggregation formula
…then the same diff MUST also change the ``RANKER_VERSION = "..."`` literal.
If it doesn't, the commit is rejected with a helpful error.

The check is intentionally conservative: any diff to the listed functions
or constants triggers the requirement, even if the diff is a pure comment.
The author can either (a) bump RANKER_VERSION and update the version-history
docstring or (b) rephrase the diff to avoid touching guarded regions.

Bypass: ``git commit --no-verify`` (not recommended; circumvents the gate).

Install:
    git config core.hooksPath scripts/githooks
or (preferred symlink approach on POSIX):
    ln -sf ../../scripts/githooks/pre-commit .git/hooks/pre-commit
"""
from __future__ import annotations

import re
import subprocess
import sys

RANKER_FILE = "src/andes_rl_kundur/evaluation/paper_grade_axes.py"
RANKER_VERSION_RE = re.compile(r'^RANKER_VERSION\s*=\s*["\'](.+?)["\']', re.MULTILINE)

# Lines in the staged file whose change requires a RANKER_VERSION bump.
# Pattern list — matched substring-anywhere; tighten if false-positive rate
# proves too high in practice.
GUARDED_PATTERNS = (
    "def _max_abs_df_score",
    "def _final_abs_df_score",
    "def _settling_score",
    "def _smoothness_score",
    "def _action_utilization",
    "def _improvement_vs_no_ctrl",
    "def _agent_min_activity",
    "def _late_oscillation_inv",
    "def _agent_p_balance",
    "def score_trace",
    "PaperBenchmark(",
    "PAPER = {",
    "max_abs_df_Hz=",
    "final_abs_df_Hz=",
    "settling_to_residual_s=",
    "dH_range=",
    "dD_range=",
    "geo_mean(axes",
    "enable_v3_axes",
    "AGENT_MIN_ACTIVITY_THRESHOLD",
    "LATE_OSCILLATION_STD_THRESHOLD",
)


def _staged_diff() -> str:
    """Return the staged diff for ``RANKER_FILE`` (empty if unchanged).

    Force UTF-8 + errors=replace so Windows GBK consoles don't choke on
    the non-ASCII characters in the docstring / Chinese comments.
    """
    result = subprocess.run(
        ["git", "diff", "--cached", "--unified=0", "--", RANKER_FILE],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.stdout or ""


def _is_ranker_modified(diff: str) -> bool:
    """True iff ``diff`` contains additions / removals to the ranker file."""
    for line in diff.splitlines():
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
            stripped = line[1:].strip()
            if stripped:
                return True
    return False


def _diff_touches_guarded_lines(diff: str) -> list[str]:
    """Return the guarded patterns that show up in added/removed lines."""
    hits: list[str] = []
    for pattern in GUARDED_PATTERNS:
        for line in diff.splitlines():
            if not line.startswith(("+", "-")) or line.startswith(("+++", "---")):
                continue
            payload = line[1:]
            if pattern in payload:
                hits.append(pattern)
                break
    return hits


def _ranker_version_changed(diff: str) -> bool:
    """True iff RANKER_VERSION literal differs between staged and HEAD."""
    head_version = _file_version_at("HEAD")
    staged_version = _file_version_at(":")  # ":" = staged index
    return head_version != staged_version


def _file_version_at(ref: str) -> str | None:
    """Read RANKER_VERSION from ``git show {ref}:{RANKER_FILE}``."""
    result = subprocess.run(
        ["git", "show", f"{ref}:{RANKER_FILE}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0 or not result.stdout:
        return None
    m = RANKER_VERSION_RE.search(result.stdout)
    return m.group(1) if m else None


def main() -> int:
    diff = _staged_diff()
    if not _is_ranker_modified(diff):
        return 0  # ranker file not in the commit — nothing to check

    guarded_hits = _diff_touches_guarded_lines(diff)
    if not guarded_hits:
        return 0  # only docstrings / whitespace / non-guarded edits

    if _ranker_version_changed(diff):
        return 0  # author bumped RANKER_VERSION — good

    sys.stderr.write(
        "\n"
        "ERROR: commit modifies paper_grade_axes.py guarded regions but does\n"
        "NOT bump RANKER_VERSION. F6 audit (2026-05-19) blocks silent ranker\n"
        "drift — this is the class of error that orphaned CLM-0005's 0.444 vs\n"
        f"CLM-0094's 0.391 across versions v2 → v3.1.\n\n"
        f"Guarded patterns detected in diff: {sorted(set(guarded_hits))}\n\n"
        "Fix:\n"
        "  1. Edit src/andes_rl_kundur/evaluation/paper_grade_axes.py and\n"
        "     bump the RANKER_VERSION string to a new value (e.g. v3.2).\n"
        "  2. Add a version-history line in the module docstring describing\n"
        "     what changed.\n"
        "  3. git add the file and retry the commit.\n\n"
        "Bypass (NOT recommended — silently breaks ledger comparability):\n"
        "  git commit --no-verify\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
