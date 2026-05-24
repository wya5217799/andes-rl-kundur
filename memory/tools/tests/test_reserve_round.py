"""Tests for ``memory/tools/reserve_round.py``.

R50 optimization G — atomically reserve the next R-number. Eliminates
the round-number race conditions encountered in R42 / R45 / R46 / R47
where my sessions had to rename rounds after the fact because Codex's
parallel session had claimed the same N.

Behaviors under test:
1. ``reserve_next_round`` returns ``max_existing_R + 1``.
2. ``reserve_next_round`` creates the directory atomically so the next
   call returns N+1 (the reservation is the side effect).
3. Concurrent callers never end up with the same N (mkdir-with-EEXIST
   retry loop).
4. Empty rounds dir yields 1 (first reservation).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from reserve_round import reserve_next_round  # noqa: E402


def test_reserve_next_round_returns_max_plus_one(tmp_path):
    rounds = tmp_path / "rounds"
    rounds.mkdir()
    (rounds / "R37").mkdir()
    (rounds / "R49").mkdir()

    n = reserve_next_round(rounds_dir=rounds)

    assert n == 50


def test_reserve_next_round_creates_the_dir(tmp_path):
    rounds = tmp_path / "rounds"
    rounds.mkdir()
    (rounds / "R10").mkdir()

    n = reserve_next_round(rounds_dir=rounds)

    assert (rounds / f"R{n}").exists()
    assert (rounds / f"R{n}").is_dir()


def test_reserve_next_round_sequential_calls_increment(tmp_path):
    """Two sequential calls in the same session return N then N+1, not
    N then N (the second call sees the dir created by the first)."""
    rounds = tmp_path / "rounds"
    rounds.mkdir()
    (rounds / "R01").mkdir()

    first = reserve_next_round(rounds_dir=rounds)
    second = reserve_next_round(rounds_dir=rounds)

    assert first == 2
    assert second == 3


def test_reserve_next_round_empty_dir_starts_at_one(tmp_path):
    rounds = tmp_path / "rounds"
    rounds.mkdir()

    n = reserve_next_round(rounds_dir=rounds)

    assert n == 1


def test_reserve_next_round_ignores_non_round_dirs(tmp_path):
    """A ``_TEMPLATE_VERDICT.md`` style sibling, or a ``Rxx-misc`` dir,
    must NOT be counted in the max."""
    rounds = tmp_path / "rounds"
    rounds.mkdir()
    (rounds / "R5").mkdir()
    (rounds / "_TEMPLATE_VERDICT.md").write_text("template", encoding="utf-8")
    (rounds / "_SKIPPED.md").write_text("skipped", encoding="utf-8")
    (rounds / "Rscratch").mkdir()

    n = reserve_next_round(rounds_dir=rounds)

    assert n == 6


def test_reserve_next_round_handles_race_via_eexist_retry(tmp_path, monkeypatch):
    """If another agent creates the same dir between the scan and the
    mkdir, the loop retries with the new max. Simulated by injecting a
    dir creation between the scan and the mkdir."""
    rounds = tmp_path / "rounds"
    rounds.mkdir()
    (rounds / "R5").mkdir()

    real_mkdir = Path.mkdir
    calls = {"n": 0}

    def racing_mkdir(self, *args, **kwargs):
        # Before the first attempt's mkdir, a competing agent creates R6.
        if calls["n"] == 0 and self.name == "R6":
            calls["n"] += 1
            (rounds / "R6").mkdir()
            real_mkdir(self, *args, **kwargs)  # this will raise FileExistsError
        else:
            real_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", racing_mkdir)

    n = reserve_next_round(rounds_dir=rounds)

    # First attempt aimed at R6, lost the race, retried and got R7.
    assert n == 7
