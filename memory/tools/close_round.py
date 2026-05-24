"""Reusable CLI to close a round (replaces ad-hoc sweep scripts).

R176 G6 — before this, every housekeeping pass wrote its own one-shot
script (`_r166_sweep.py`, `_r171_sweep.py`). Now there's a stable CLI:

    # Mark superseded by another round (no verdict required)
    python memory/tools/close_round.py R115 superseded --by R103 \
        --note "paper_strict_pure closed-negative by CLM-0203 (R103)"

    # Mark aborted (no verdict required)
    python memory/tools/close_round.py R119 aborted \
        --reason "wider action bound replaced by R132 α-sweep"

    # Mark completed (requires verdict.md already present in dir)
    python memory/tools/close_round.py R143 completed

Operates only on plan.md frontmatter; preserves body verbatim. Atomic
re-write (tempfile + rename) so partial writes do not corrupt files.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import tempfile
from pathlib import Path

import yaml

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
VALID_TERMINAL = {"completed", "superseded", "aborted"}
ROUND_DIR_RE = re.compile(r"^R\d+$")


def _atomic_write(path: Path, content: str) -> None:
    """Write via tempfile + rename so a crash mid-write cannot corrupt."""
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False,
        dir=path.parent, suffix=".tmp",
    ) as fh:
        fh.write(content)
        tmp_name = fh.name
    Path(tmp_name).replace(path)


def _load_plan(plan_path: Path) -> tuple[dict, str]:
    text = plan_path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm = yaml.safe_load(m.group(1)) or {}
    return fm, m.group(2)


def _dump(fm: dict, body: str) -> str:
    dump = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    out = f"---\n{dump}\n---\n{body.lstrip(chr(10))}"
    if not out.endswith("\n"):
        out += "\n"
    return out


def close_round(
    round_name: str,
    new_state: str,
    *,
    rounds_dir: Path,
    superseded_by: str | None = None,
    superseded_note: str | None = None,
    abort_reason: str | None = None,
    today: dt.date | None = None,
) -> str:
    """Flip a round's plan.md frontmatter to a terminal state.

    Returns a one-line status string. Raises ValueError on invalid input.
    """
    if not ROUND_DIR_RE.match(round_name):
        raise ValueError(
            f"round_name must match R<NNN>; got {round_name!r}"
        )
    if new_state not in VALID_TERMINAL:
        raise ValueError(
            f"new_state must be one of {sorted(VALID_TERMINAL)}; "
            f"got {new_state!r}"
        )
    round_dir = rounds_dir / round_name
    plan_path = round_dir / "plan.md"
    today = today or dt.date.today()

    if not round_dir.is_dir():
        raise FileNotFoundError(f"round dir does not exist: {round_dir}")

    if not plan_path.exists():
        # Stub a minimal plan.md (this is the case for reserved-empty
        # dirs we want to mark aborted).
        fm: dict = {
            "round": round_name,
            "state": "active",  # will be replaced below
            "opened": today.isoformat(),
            "closed": None,
            "supersedes_rounds": [],
            "superseded_by_round": None,
            "abort_reason": None,
            "superseded_note": None,
        }
        body = (
            f"# {round_name} plan — auto-stubbed by close_round CLI\n\n"
            f"This plan.md was created by `memory/tools/close_round.py` "
            f"when the round was closed without a pre-existing plan "
            f"(typically: reserved-empty parallel-session race).\n"
        )
    else:
        fm, body = _load_plan(plan_path)

    # State-specific validation
    if new_state == "superseded":
        if not superseded_by:
            raise ValueError(
                "state=superseded requires --by R<NNN> "
                "(superseded_by_round target)"
            )
        if not ROUND_DIR_RE.match(superseded_by):
            raise ValueError(
                f"--by must match R<NNN>; got {superseded_by!r}"
            )
        target_dir = rounds_dir / superseded_by
        if not target_dir.is_dir():
            raise FileNotFoundError(
                f"superseded_by target does not exist: {target_dir}"
            )
    if new_state == "aborted":
        if not abort_reason:
            raise ValueError(
                "state=aborted requires --reason"
            )
    if new_state == "completed":
        if not (round_dir / "verdict.md").exists():
            raise FileNotFoundError(
                f"state=completed requires {round_dir}/verdict.md; "
                f"either write one first or pick a different state"
            )

    # Apply state + audit fields
    fm["state"] = new_state
    fm["closed"] = today.isoformat()
    if new_state == "superseded":
        fm["superseded_by_round"] = superseded_by
        fm["superseded_note"] = superseded_note
        fm["abort_reason"] = None
    elif new_state == "aborted":
        fm["abort_reason"] = abort_reason
        fm["superseded_by_round"] = None
        fm["superseded_note"] = None
    elif new_state == "completed":
        fm["superseded_by_round"] = None
        fm["abort_reason"] = None

    _atomic_write(plan_path, _dump(fm, body))
    detail = (
        f"by {superseded_by}" if new_state == "superseded"
        else (abort_reason[:50] + "...") if new_state == "aborted" and abort_reason
        else ""
    )
    return f"{round_name}: state={new_state} {detail}".strip()


def main() -> int:
    base = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("round", help="Round name, e.g. R115")
    p.add_argument("state", choices=sorted(VALID_TERMINAL),
                   help="Terminal state to flip into")
    p.add_argument("--by", help="state=superseded target round (R<NNN>)")
    p.add_argument("--note", help="state=superseded one-line context",
                   default=None)
    p.add_argument("--reason", help="state=aborted one-line reason",
                   default=None)
    p.add_argument("--rounds-dir", type=Path,
                   default=base / "rounds",
                   help="path to memory/rounds/")
    args = p.parse_args()

    try:
        msg = close_round(
            args.round, args.state,
            rounds_dir=args.rounds_dir,
            superseded_by=args.by,
            superseded_note=args.note,
            abort_reason=args.reason,
        )
    except (ValueError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
