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


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--memory-dir",
        default="memory",
        help="Path to the memory root (default: memory)",
    )
    args = parser.parse_args()
    rounds_dir = Path(args.memory_dir) / "rounds"
    n = reserve_next_round(rounds_dir)
    print(n)


if __name__ == "__main__":
    _main()
