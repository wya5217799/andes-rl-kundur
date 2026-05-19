"""Atomically reserve the next R-number under ``memory/rounds/``.

R50 optimization G — eliminates round-number races between parallel
agent sessions. The pre-R50 workflow was:

1. Decide "I'll do R<N>" based on the highest committed round.
2. Write claims with ``round: R<N>``.
3. Discover a parallel session also picked R<N> — rename everything.

The R42/R45/R46/R47 series in the project history shows this rename
dance three times. The fix is to make the choice of N a side-effect
of creating the dir: ``mkdir`` is atomic on POSIX, so two callers
racing to claim the same N have exactly one winner; the loser sees
``FileExistsError`` and retries with the new max.

Usage (CLI):
    $ python memory/tools/reserve_round.py
    50

Usage (library):
    >>> from memory.tools.reserve_round import reserve_next_round
    >>> n = reserve_next_round(Path("memory/rounds"))
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path


def _max_existing_r(rounds_dir: Path) -> int:
    """Highest R-number in ``rounds_dir``. Returns 0 when empty so that
    ``max + 1 == 1`` for a fresh memory tree."""
    numbers = []
    for entry in rounds_dir.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name
        if len(name) < 2 or not name.startswith("R"):
            continue
        suffix = name[1:]
        if not suffix.isdigit():
            continue
        numbers.append(int(suffix))
    return max(numbers) if numbers else 0


def reserve_next_round(rounds_dir: Path) -> int:
    """Reserve and return the next R-number.

    Atomically creates ``rounds_dir / R{N}`` and returns ``N``. ``N`` is
    always ``max(existing R-numbers) + 1`` so reservations are monotonic
    over project time (matches the project's pre-R50 round-numbering
    convention; gaps from skipped rounds are NOT filled).

    On concurrent races (two agents reserving simultaneously), the loser
    catches ``FileExistsError`` and retries against the updated max —
    so each caller is guaranteed a unique N.

    Args:
        rounds_dir: typically ``Path("memory/rounds")``. Must exist.

    Returns:
        The reserved integer N. ``rounds_dir / f"R{N}"`` is now an empty
        directory awaiting plan.md / verdict.md.
    """
    if not rounds_dir.is_dir():
        raise FileNotFoundError(f"rounds_dir does not exist: {rounds_dir}")

    while True:
        next_n = _max_existing_r(rounds_dir) + 1
        target = rounds_dir / f"R{next_n}"
        try:
            target.mkdir(exist_ok=False)
            return next_n
        except FileExistsError:
            # Race: another agent grabbed N. Rescan and retry.
            continue


def _extract_oracle_snapshot(state_md: Path) -> str:
    """Pull the Open Questions + Recently Closed sections out of STATE.md.

    Used by ``--write-plan-stub`` to inline a freshly-rendered oracle view
    into the new round's plan.md. Returns an empty string when STATE.md
    is missing or has neither section (e.g. fresh memory tree).
    """
    if not state_md.exists():
        return ""
    text = state_md.read_text(encoding="utf-8")
    sections: list[str] = []
    for heading in ("## Open Questions", "## Recently Closed"):
        m = re.search(
            rf"^{re.escape(heading)}\b.*?(?=\n##\s|\Z)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        if m:
            sections.append(m.group(0).rstrip())
    return "\n\n".join(sections)


def _write_plan_stub(round_dir: Path, n: int, oracle_snapshot: str) -> None:
    """Drop a plan.md skeleton with the oracle snapshot inlined.

    The snapshot freezes the open Q / recently-closed list at plan-write
    time so a parallel session writing the verdict cannot blame "stale
    STATE.md" for an out-of-date plan (F4 from 2026-05-19 audit). The
    author can overwrite the rest of the plan freely; the snapshot
    section is informational and should be preserved through edits.
    """
    plan_path = round_dir / "plan.md"
    if plan_path.exists():
        return  # do not clobber an existing plan
    now = dt.date.today().isoformat()
    snapshot_block = (
        oracle_snapshot if oracle_snapshot else "(STATE.md had no oracle sections)"
    )
    plan_path.write_text(
        # R166: machine-readable lifecycle state in YAML frontmatter.
        # Body markdown keeps the human-readable Status/Opened lines.
        f"---\n"
        f"round: R{n}\n"
        f"state: active\n"
        f"opened: '{now}'\n"
        f"closed: null\n"
        f"supersedes_rounds: []\n"
        f"superseded_by_round: null\n"
        f"abort_reason: null\n"
        f"superseded_note: null\n"
        f"---\n"
        f"# R{n} plan — (rename me)\n\n"
        f"**Status**: ACTIVE\n"
        f"**Opened**: {now}\n"
        f"**Driver**: (one-sentence motivation)\n"
        f"**Parent**: (CLM-NNNN refs)\n\n"
        f"## TL;DR\n\n"
        f"(fill in after methodology drafted)\n\n"
        f"## Snapshot at plan-time (oracle as of {now})\n\n"
        f"<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->\n"
        f"<!-- Do not delete — re-render-render.py STATE.md if you want to -->\n"
        f"<!-- refresh, but keep this block as the plan-time snapshot. -->\n\n"
        f"{snapshot_block}\n\n"
        f"## Methodology\n\n"
        f"(fill in)\n\n"
        f"## Gate\n\n"
        f"(decision rule)\n\n"
        f"## 资产保护契约\n\n"
        f"(what stays unchanged, what's added)\n\n"
        f"## Cross-references\n\n"
        f"(CLM-NNNN parent claims)\n",
        encoding="utf-8",
    )


def gc_empty_rounds(
    rounds_dir: Path,
    *,
    max_age_minutes: int = 60,
    today: dt.date | None = None,
) -> list[str]:
    """R176 G8: scan ``rounds_dir`` for ``RNNN/`` directories that are
    older than ``max_age_minutes``, contain no ``plan.md`` and no
    ``*verdict*.md``, and convert them to ``state=aborted`` stubs.

    Catches the parallel-session race: ``reserve_round.py`` atomically
    creates a dir, but if the session crashes or never writes the plan,
    the dir persists as a zombie. The garbage collector finds these
    and writes a minimal aborted plan via the canonical close path.

    Returns a list of round names that were swept. Empty list means
    no zombies found (the happy steady state).
    """
    import time
    swept: list[str] = []
    if not rounds_dir.is_dir():
        return swept
    now = time.time()
    cutoff = now - max_age_minutes * 60
    today = today or dt.date.today()
    for entry in sorted(rounds_dir.iterdir()):
        if not entry.is_dir():
            continue
        if not re.match(r"^R\d+$", entry.name):
            continue
        if (entry / "plan.md").exists():
            continue
        if any(entry.glob("*verdict*.md")):
            continue
        if entry.stat().st_mtime > cutoff:
            continue  # too young; could still be in-progress
        # Stub a minimal aborted plan via the close_round helper.
        plan_path = entry / "plan.md"
        fm_lines = [
            "---",
            f"round: {entry.name}",
            "state: aborted",
            f"opened: '{today.isoformat()}'",
            f"closed: '{today.isoformat()}'",
            "supersedes_rounds: []",
            "superseded_by_round: null",
            "abort_reason: reserved-empty for >60min (auto-gc by reserve_round.py)",
            "superseded_note: null",
            "---",
            f"# {entry.name} plan — auto-gc'd by reserve_round.py",
            "",
            "Dir created via `reserve_round.py` but never populated with",
            "plan.md within the GC window. Most likely a parallel-session",
            "race or crashed session. Closed as aborted by `--gc`.",
            "",
        ]
        plan_path.write_text("\n".join(fm_lines), encoding="utf-8")
        swept.append(entry.name)
    return swept


def _refresh_oracle(memory_dir: Path) -> None:
    """Run validate.py + render.py to refresh STATE.md before snapshotting.

    Failures are non-fatal: if validate hits a hard error we still want
    to allow round reservation (the caller may be in the middle of fixing
    that error). The snapshot just won't reflect the in-flight fix.
    """
    validate = memory_dir / "tools" / "validate.py"
    render = memory_dir / "tools" / "render.py"
    for script in (validate, render):
        if not script.exists():
            continue
        subprocess.run(
            [sys.executable, str(script)],
            cwd=str(memory_dir.parent),
            capture_output=True,
            timeout=30,
        )


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--memory-dir",
        default="memory",
        help="Path to the memory root (default: memory)",
    )
    parser.add_argument(
        "--write-plan-stub",
        action="store_true",
        help=(
            "After reserving the round, refresh STATE.md (validate + render) "
            "and write a plan.md skeleton with the open-Q / recently-closed "
            "snapshot inlined. F4 from 2026-05-19 audit — prevents stale-"
            "oracle race conditions like R114."
        ),
    )
    parser.add_argument(
        "--gc",
        action="store_true",
        help=(
            "R176 G8: sweep zombie empty round dirs (created by "
            "reserve_round.py but never populated with plan.md). "
            "Default cutoff = 60 minutes; older empties are stubbed as "
            "aborted. Does not reserve a new round when --gc is set."
        ),
    )
    parser.add_argument(
        "--gc-minutes",
        type=int,
        default=60,
        help="Minimum age (minutes) before --gc treats a dir as zombie",
    )
    args = parser.parse_args()
    memory_dir = Path(args.memory_dir)
    rounds_dir = memory_dir / "rounds"
    if args.gc:
        swept = gc_empty_rounds(rounds_dir, max_age_minutes=args.gc_minutes)
        if swept:
            for name in swept:
                print(f"GC {name}: aborted (reserved-empty >{args.gc_minutes}min)")
        else:
            print("GC: no zombies found")
        return
    if args.write_plan_stub:
        _refresh_oracle(memory_dir)
    n = reserve_next_round(rounds_dir)
    if args.write_plan_stub:
        snapshot = _extract_oracle_snapshot(memory_dir / "STATE.md")
        _write_plan_stub(rounds_dir / f"R{n}", n, snapshot)
    print(n)


if __name__ == "__main__":
    _main()
