"""Tests for close_round.py's post-close git commit contract (workflow 2026-08-22).

close_round.py commits the whole working tree by default after a close so
each round ends with one atomic commit and the workspace stays clean. These
tests exercise the commit / skip / clean-tree paths against a throwaway git
repo, so the real ledger and history are never touched.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_TOOL = ROOT / "memory" / "tools" / "close_round.py"

_PLAN = """---
round: {round}
state: active
manuscript_line: null
opened: '2026-08-22'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# {round} plan — close_round commit test fixture
"""


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def _make_repo(tmp_path: Path, round_name: str = "R999") -> Path:
    repo = tmp_path / "repo"
    (repo / "memory" / "rounds" / round_name).mkdir(parents=True)
    (repo / "memory" / "rounds" / round_name / "plan.md").write_text(
        _PLAN.format(round=round_name), encoding="utf-8"
    )
    assert _git(repo, "init", "-q").returncode == 0
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "close-round test")
    _git(repo, "config", "commit.gpgsign", "false")
    return repo


def _close(repo: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable, str(_TOOL), "R999", "aborted",
            "--reason", "test fixture",
            "--rounds-dir", str(repo / "memory" / "rounds"),
            *extra,
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def test_close_commits_by_default(tmp_path):
    repo = _make_repo(tmp_path)
    proc = _close(repo)
    assert proc.returncode == 0, proc.stderr
    assert "round R999: close aborted" in _git(repo, "log", "--oneline").stdout
    plan = (repo / "memory" / "rounds" / "R999" / "plan.md").read_text(encoding="utf-8")
    assert "state: aborted" in plan
    assert _git(repo, "status", "--porcelain").stdout.strip() == ""


def test_no_commit_flag_skips_commit(tmp_path):
    repo = _make_repo(tmp_path)
    proc = _close(repo, "--no-commit")
    assert proc.returncode == 0, proc.stderr
    assert _git(repo, "log", "--oneline").stdout.strip() == ""
    assert _git(repo, "status", "--porcelain").stdout.strip() != ""


def test_clean_tree_reports_nothing_to_commit(tmp_path):
    repo = _make_repo(tmp_path)
    assert _close(repo).returncode == 0
    proc = _close(repo)  # second close: no file change left in the tree
    assert proc.returncode == 0, proc.stderr
    assert "nothing to commit" in proc.stdout


def test_custom_commit_message(tmp_path):
    repo = _make_repo(tmp_path)
    proc = _close(repo, "--commit-message", "round RA1: close aborted (fixture)")
    assert proc.returncode == 0, proc.stderr
    assert "round RA1: close aborted (fixture)" in _git(repo, "log", "--oneline").stdout
