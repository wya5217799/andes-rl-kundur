"""Tests for memory/tools/reserve_round.py.

Two test surfaces:

1. **Atomic-mkdir contract (R50 original guarantee)**: ``reserve_next_round``
   returns ``max + 1``, side-effects an empty dir, and survives the
   FileExistsError retry path.
2. **Active-rounds detection (R256 followup, 2026-05-20)**: the
   ``_active_rounds_in_progress`` helper correctly identifies dirs whose
   plan.md declares ``state: active``, ignores other states, and the CLI
   ``--strict-no-active`` flag aborts with exit 1 when any active round
   is present.

The bug these tests pin: a context-compressed agent re-runs
``reserve_round.py`` without realising it already has an in-flight round
from a prior turn. Atomic mkdir does NOT prevent this (the prior dir may
have been swept by ``--gc`` between turns, or the prior turn may never
have committed). The state-based pre-flight is the second layer of
defence.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# Add the tools dir to sys.path so we can import the helper directly.
ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "memory" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import reserve_round  # noqa: E402


# ─── Atomic-mkdir contract (pins the R50 invariant) ──────────────────────


def test_max_existing_r_empty_dir(tmp_path: Path) -> None:
    assert reserve_round._max_existing_r(tmp_path) == 0


def test_max_existing_r_picks_max(tmp_path: Path) -> None:
    for n in (3, 7, 12, 1):
        (tmp_path / f"R{n}").mkdir()
    assert reserve_round._max_existing_r(tmp_path) == 12


def test_max_existing_r_ignores_non_round_dirs(tmp_path: Path) -> None:
    (tmp_path / "R5").mkdir()
    (tmp_path / "Rxyz").mkdir()            # non-numeric suffix
    (tmp_path / "_TEMPLATE_VERDICT.md").write_text("")  # file
    (tmp_path / "_SKIPPED.md").write_text("")
    (tmp_path / "Q-0001").mkdir()          # not R-prefixed
    assert reserve_round._max_existing_r(tmp_path) == 5


def test_reserve_next_round_fresh(tmp_path: Path) -> None:
    n = reserve_round.reserve_next_round(tmp_path)
    assert n == 1
    assert (tmp_path / "R1").is_dir()


def test_reserve_next_round_monotonic(tmp_path: Path) -> None:
    (tmp_path / "R10").mkdir()
    n = reserve_round.reserve_next_round(tmp_path)
    assert n == 11
    assert (tmp_path / "R11").is_dir()


def test_reserve_next_round_atomic_collision(tmp_path: Path) -> None:
    """Simulate the race: caller's `_max_existing_r` returns 4 but R5 was
    created between the scan and the mkdir attempt. The retry loop must
    pick R6, not raise.
    """
    (tmp_path / "R4").mkdir()
    # Pre-create R5 BEFORE calling reserve. The first iteration will see
    # max=5 and try R6 directly — which is fine, but to actually exercise
    # the retry path we monkey-patch _max_existing_r to return 4 once.
    real_max = reserve_round._max_existing_r
    calls = {"n": 0}

    def fake_max(rounds_dir: Path) -> int:
        calls["n"] += 1
        if calls["n"] == 1:
            return 4   # stale-cache scenario: tells caller "next is 5"
        return real_max(rounds_dir)
    reserve_round._max_existing_r = fake_max  # type: ignore[assignment]
    try:
        (tmp_path / "R5").mkdir()  # already exists, so mkdir(R5) will fail
        n = reserve_round.reserve_next_round(tmp_path)
    finally:
        reserve_round._max_existing_r = real_max  # type: ignore[assignment]
    assert n == 6
    assert (tmp_path / "R6").is_dir()
    assert calls["n"] >= 2   # at least one retry happened


def test_reserve_next_round_missing_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        reserve_round.reserve_next_round(tmp_path / "does-not-exist")


# ─── Frontmatter parser ──────────────────────────────────────────────────


def _write_plan(path: Path, state: str, opened: str = "2026-05-20",
                driver: str = "test plan") -> None:
    path.write_text(
        f"---\n"
        f"round: {path.parent.name}\n"
        f"state: {state}\n"
        f"opened: '{opened}'\n"
        f"closed: null\n"
        f"---\n"
        f"# {path.parent.name} plan\n\n"
        f"**Driver**: {driver}\n",
        encoding="utf-8",
    )


def test_parse_plan_frontmatter_missing(tmp_path: Path) -> None:
    assert reserve_round._parse_plan_frontmatter(tmp_path / "nope.md") == {}


def test_parse_plan_frontmatter_no_frontmatter(tmp_path: Path) -> None:
    p = tmp_path / "plan.md"
    p.write_text("# just a header, no yaml\n")
    assert reserve_round._parse_plan_frontmatter(p) == {}


def test_parse_plan_frontmatter_extracts_state(tmp_path: Path) -> None:
    (tmp_path / "R5").mkdir()
    plan_path = tmp_path / "R5" / "plan.md"
    _write_plan(plan_path, "active", opened="2026-05-20")
    fm = reserve_round._parse_plan_frontmatter(plan_path)
    assert fm["state"] == "active"
    assert fm["opened"] == "2026-05-20"
    assert fm["round"] == "R5"


# ─── Active-rounds detection (R256 followup) ─────────────────────────────


def test_active_rounds_empty_dir(tmp_path: Path) -> None:
    assert reserve_round._active_rounds_in_progress(tmp_path) == []


def test_active_rounds_detects_one(tmp_path: Path) -> None:
    (tmp_path / "R5").mkdir()
    _write_plan(tmp_path / "R5" / "plan.md", "active")
    result = reserve_round._active_rounds_in_progress(tmp_path)
    assert len(result) == 1
    assert result[0][0] == 5
    assert result[0][1]["state"] == "active"
    assert result[0][2] == "R5"


def test_active_rounds_ignores_completed(tmp_path: Path) -> None:
    (tmp_path / "R5").mkdir()
    (tmp_path / "R6").mkdir()
    (tmp_path / "R7").mkdir()
    _write_plan(tmp_path / "R5" / "plan.md", "completed")
    _write_plan(tmp_path / "R6" / "plan.md", "aborted")
    _write_plan(tmp_path / "R7" / "plan.md", "active")
    result = reserve_round._active_rounds_in_progress(tmp_path)
    assert [n for n, _, _ in result] == [7]


def test_active_rounds_ignores_missing_plan(tmp_path: Path) -> None:
    """Empty R<N>/ dir (reserved but never populated) is NOT active."""
    (tmp_path / "R5").mkdir()   # no plan.md at all
    assert reserve_round._active_rounds_in_progress(tmp_path) == []


def test_active_rounds_sorted_ascending(tmp_path: Path) -> None:
    for n in (10, 3, 7):
        (tmp_path / f"R{n}").mkdir()
        _write_plan(tmp_path / f"R{n}" / "plan.md", "active")
    result = reserve_round._active_rounds_in_progress(tmp_path)
    assert [n for n, _, _ in result] == [3, 7, 10]


def test_active_rounds_skips_stale_active_with_verdict(tmp_path: Path) -> None:
    """Legacy R01-R49 case: plan.md says state=active but verdict.md exists.
    Verdict is operational truth — exclude from active list by default."""
    (tmp_path / "R5").mkdir()
    _write_plan(tmp_path / "R5" / "plan.md", "active")
    (tmp_path / "R5" / "verdict.md").write_text("done", encoding="utf-8")
    result = reserve_round._active_rounds_in_progress(tmp_path)
    assert result == []


def test_active_rounds_include_stale_flag(tmp_path: Path) -> None:
    """include_stale=True returns the legacy stale-active case for
    ledger-hygiene audits."""
    (tmp_path / "R5").mkdir()
    _write_plan(tmp_path / "R5" / "plan.md", "active")
    (tmp_path / "R5" / "verdict.md").write_text("done", encoding="utf-8")
    result = reserve_round._active_rounds_in_progress(tmp_path, include_stale=True)
    assert [n for n, _, _ in result] == [5]


def test_active_rounds_preserves_zero_padded_dir_name(tmp_path: Path) -> None:
    """R01 in-progress should be displayable as R01, not R1."""
    (tmp_path / "R01").mkdir()
    _write_plan(tmp_path / "R01" / "plan.md", "active")
    result = reserve_round._active_rounds_in_progress(tmp_path)
    assert len(result) == 1
    n, _, dir_name = result[0]
    assert n == 1
    assert dir_name == "R01"


# ─── CLI integration ─────────────────────────────────────────────────────


def _run_cli(memory_dir: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    """Invoke reserve_round.py as a subprocess with the given memory dir."""
    cmd = [
        sys.executable,
        str(TOOLS_DIR / "reserve_round.py"),
        "--memory-dir", str(memory_dir),
        *extra_args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")


def _bootstrap_memory(tmp_path: Path) -> Path:
    """Build a minimal memory/ skeleton for CLI tests."""
    mem = tmp_path / "memory"
    (mem / "rounds").mkdir(parents=True)
    (mem / "claims").mkdir()
    return mem


def test_cli_basic_reserve(tmp_path: Path) -> None:
    mem = _bootstrap_memory(tmp_path)
    r = _run_cli(mem)
    assert r.returncode == 0
    assert r.stdout.strip() == "1"
    assert (mem / "rounds" / "R1").is_dir()


def test_cli_list_active_empty(tmp_path: Path) -> None:
    mem = _bootstrap_memory(tmp_path)
    r = _run_cli(mem, "--list-active")
    assert r.returncode == 0
    assert "no active" in r.stdout
    # --list-active must NOT reserve a round
    assert not (mem / "rounds" / "R1").exists()


def test_cli_list_active_finds_one(tmp_path: Path) -> None:
    mem = _bootstrap_memory(tmp_path)
    (mem / "rounds" / "R5").mkdir()
    _write_plan(mem / "rounds" / "R5" / "plan.md", "active",
                driver="probe action saturation")
    r = _run_cli(mem, "--list-active")
    assert r.returncode == 0
    assert "R5" in r.stdout
    assert "active" in r.stdout
    # Driver line shown
    assert "probe action saturation" in r.stdout
    # No reservation
    assert not (mem / "rounds" / "R6").exists()


def test_cli_strict_no_active_aborts(tmp_path: Path) -> None:
    """The R256-class bug fix: reserve refuses to spawn duplicate work."""
    mem = _bootstrap_memory(tmp_path)
    (mem / "rounds" / "R256").mkdir()
    _write_plan(mem / "rounds" / "R256" / "plan.md", "active",
                driver="Probe action-bound saturation as plateau mechanism")
    r = _run_cli(mem, "--strict-no-active")
    assert r.returncode == 1
    assert "ERROR" in r.stderr
    assert "R256" in r.stderr
    # No reservation happened
    assert not (mem / "rounds" / "R257").exists()


def test_cli_strict_no_active_passes_when_none(tmp_path: Path) -> None:
    mem = _bootstrap_memory(tmp_path)
    # Add a completed round — strict mode should still reserve.
    (mem / "rounds" / "R10").mkdir()
    _write_plan(mem / "rounds" / "R10" / "plan.md", "completed")
    r = _run_cli(mem, "--strict-no-active")
    assert r.returncode == 0
    assert r.stdout.strip() == "11"
    assert (mem / "rounds" / "R11").is_dir()


def test_cli_default_warn_active_but_proceed(tmp_path: Path) -> None:
    mem = _bootstrap_memory(tmp_path)
    (mem / "rounds" / "R5").mkdir()
    _write_plan(mem / "rounds" / "R5" / "plan.md", "active")
    r = _run_cli(mem)
    # Reserves anyway (R6) — warning is just informational
    assert r.returncode == 0
    assert r.stdout.strip() == "6"
    assert "WARNING" in r.stderr
    assert "R5" in r.stderr


def test_cli_no_warn_active_silent(tmp_path: Path) -> None:
    mem = _bootstrap_memory(tmp_path)
    (mem / "rounds" / "R5").mkdir()
    _write_plan(mem / "rounds" / "R5" / "plan.md", "active")
    r = _run_cli(mem, "--no-warn-active")
    assert r.returncode == 0
    assert r.stdout.strip() == "6"
    assert "WARNING" not in r.stderr


def test_cli_warning_goes_to_stderr_not_stdout(tmp_path: Path) -> None:
    """Scripts pipe `reserve_round.py | xargs ...` and parse stdout as
    the round number. The active-rounds warning must NOT contaminate
    stdout or the parse breaks."""
    mem = _bootstrap_memory(tmp_path)
    (mem / "rounds" / "R5").mkdir()
    _write_plan(mem / "rounds" / "R5" / "plan.md", "active")
    r = _run_cli(mem)
    # stdout must be a parseable integer
    assert r.stdout.strip().isdigit()
    assert int(r.stdout.strip()) == 6
    # warning content is only in stderr
    assert "WARNING" in r.stderr
    assert "WARNING" not in r.stdout


# ─── GC contract (regression-pin existing behaviour) ─────────────────────


def test_gc_skips_dir_with_plan(tmp_path: Path) -> None:
    (tmp_path / "R5").mkdir()
    _write_plan(tmp_path / "R5" / "plan.md", "active")
    swept = reserve_round.gc_empty_rounds(tmp_path, max_age_minutes=0)
    assert swept == []


def test_gc_skips_dir_with_verdict(tmp_path: Path) -> None:
    (tmp_path / "R5").mkdir()
    (tmp_path / "R5" / "verdict.md").write_text("done")
    swept = reserve_round.gc_empty_rounds(tmp_path, max_age_minutes=0)
    assert swept == []


def test_gc_sweeps_empty_old_dir(tmp_path: Path) -> None:
    import os
    (tmp_path / "R5").mkdir()
    # Backdate so it looks old
    old = 1000000.0
    os.utime(tmp_path / "R5", (old, old))
    swept = reserve_round.gc_empty_rounds(tmp_path, max_age_minutes=60)
    assert swept == ["R5"]
    # GC stubbed a plan.md with state=aborted. Read as utf-8 explicitly
    # because the stub contains em-dash and curly-quote which GBK
    # (Windows default locale on zh-CN) cannot decode.
    plan = (tmp_path / "R5" / "plan.md").read_text(encoding="utf-8")
    assert "state: aborted" in plan
    assert "reserved-empty" in plan


def test_gc_respects_results_orphan(tmp_path: Path) -> None:
    """If results/rNNN_*/ has final_eval_summary.json, the round is NOT
    a zombie even if plan.md is missing (R176 hotfix)."""
    import os
    (tmp_path / "R5").mkdir()
    old = 1000000.0
    os.utime(tmp_path / "R5", (old, old))
    # Build results sibling: rounds_dir.parent.parent / results
    results = tmp_path.parent / "results"
    results.mkdir(exist_ok=True)
    (results / "r5_some_run").mkdir()
    (results / "r5_some_run" / "final_eval_summary.json").write_text("{}")
    swept = reserve_round.gc_empty_rounds(tmp_path, max_age_minutes=60,
                                          results_dir=results)
    assert swept == []
