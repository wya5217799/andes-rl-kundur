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

**R256 follow-up (2026-05-20)** — atomic mkdir prevents *concurrent*
duplicate reservation, but does NOT prevent *re-entry* duplicate work
within a single conversation that has been context-compressed:

1. Turn N: agent reserves R<M>, writes plan + verdict + CLM.
2. Conversation summary truncates the work record.
3. Turn N+k: post-compression agent has no memory of R<M>, calls
   ``reserve_round.py``, gets a *fresh* dir (R<M+1> or, if R<M>
   was for any reason swept / never persisted on disk, R<M> again).
4. The agent repeats the work; the prior-turn verdict.md still on
   disk is silently overwritten or duplicated.

The fix is a state-based pre-flight: scan all R<N>/ dirs for
``state: active`` in plan.md frontmatter, print a warning listing
them, and either WARN-only (default), ABORT (``--strict-no-active``),
or LIST-only (``--list-active``). The warning gives the post-
compression agent a chance to notice "ah, R<M> is already in flight"
before spawning a duplicate round. Atomic mkdir is preserved
unchanged; this is an additional layer on top.

Usage (CLI):
    $ python memory/tools/reserve_round.py
    50

    $ python memory/tools/reserve_round.py --list-active
    Active rounds (state=active in plan.md):
      R256  opened=2026-05-20  driver=Probe action-bound saturation...

    $ python memory/tools/reserve_round.py --strict-no-active
    ERROR: 1 active round(s) in progress. Refuse to reserve.
    (exit code 1)

    $ python memory/tools/reserve_round.py --strict-no-active \
        --line decoupling-marl-model-first --write-plan-stub
    339

Usage (library):
    >>> from memory.tools.reserve_round import reserve_next_round
    >>> n = reserve_next_round(Path("memory/rounds"))
"""
from __future__ import annotations

import argparse
import atexit
import datetime as dt
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from andes_rl_kundur.round_scope import (  # noqa: E402
    RoundScopeError,
    lines_conflict,
    resolve_line_selector,
    resolve_round_line,
)


def _release_reservation_lock(lock_path: Path) -> None:
    """Release only the reservation mutex acquired by this process."""

    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass


def _acquire_reservation_lock(
    rounds_dir: Path,
    *,
    timeout_seconds: float = 15.0,
) -> Path:
    """Serialize the short scan/reserve/stub transaction across processes.

    The mutex does not serialize experiments. It only prevents two sessions
    from both observing the same line as idle before either plan becomes
    visible. Exclusive file creation works for Windows and WSL callers sharing
    the checkout.
    """

    lock_path = rounds_dir / ".reservation.lock"
    deadline = time.monotonic() + timeout_seconds
    payload = f"pid={os.getpid()} started={dt.datetime.now().isoformat()}\n"
    while True:
        try:
            descriptor = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"round reservation is busy or stale at {lock_path}; "
                    "confirm no reservation command is running before removing it"
                )
            time.sleep(0.05)
            continue
        try:
            os.write(descriptor, payload.encode("utf-8"))
        finally:
            os.close(descriptor)
        return lock_path


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


def _write_plan_stub(
    round_dir: Path,
    n: int,
    oracle_snapshot: str,
    manuscript_line: str | None = None,
) -> None:
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
        # R291+: do not duplicate canonical state in a body Status line.
        f"---\n"
        f"round: R{n}\n"
        f"state: active\n"
        f"manuscript_line: {manuscript_line or 'null'}\n"
        f"opened: '{now}'\n"
        f"closed: null\n"
        f"supersedes_rounds: []\n"
        f"superseded_by_round: null\n"
        f"abort_reason: null\n"
        f"superseded_note: null\n"
        f"---\n"
        f"# R{n} plan — (rename me)\n\n"
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
    results_dir: Path | None = None,
) -> list[str]:
    """R176 G8: scan ``rounds_dir`` for ``RNNN/`` directories that are
    older than ``max_age_minutes``, contain no ``plan.md``, no
    ``*verdict*.md``, AND have no matching ``results/rNNN_*/`` with
    a ``final_eval_summary.json`` (R176 hotfix — earlier version
    wrongly swept R174 which had real eval results from a parallel
    session that hadn't yet written plan.md).

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
    # Default results_dir: sibling of rounds_dir's parent (repo_root/results)
    if results_dir is None:
        results_dir = rounds_dir.parent.parent / "results"
    now = time.time()
    cutoff = now - max_age_minutes * 60
    today = today or dt.date.today()

    # Build set of round numbers that have results/ dirs with eval output
    rounds_with_results: set[int] = set()
    if results_dir.is_dir():
        for r_entry in results_dir.iterdir():
            if not r_entry.is_dir():
                continue
            m = re.match(r"^r(\d+)_", r_entry.name, re.IGNORECASE)
            if not m:
                continue
            if (r_entry / "final_eval_summary.json").exists():
                rounds_with_results.add(int(m.group(1)))

    for entry in sorted(rounds_dir.iterdir()):
        if not entry.is_dir():
            continue
        m = re.match(r"^R(\d+)$", entry.name)
        if not m:
            continue
        if (entry / "plan.md").exists():
            continue
        if any(entry.glob("*verdict*.md")):
            continue
        if int(m.group(1)) in rounds_with_results:
            # Parallel session produced results but didn't write plan.md
            # yet — do NOT abort, this is the kind of orphan that should
            # become state=completed once someone writes it up.
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
            f"# {entry.name} plan -- auto-gc'd by reserve_round.py",
            "",
            "Dir created via `reserve_round.py` but never populated with",
            "plan.md within the GC window. Most likely a parallel-session",
            "race or crashed session. Closed as aborted by `--gc`.",
            "",
        ]
        plan_path.write_text("\n".join(fm_lines), encoding="utf-8")
        swept.append(entry.name)
    return swept


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
# R281 introduced the current feed-era close contract.  Earlier rounds contain
# many retrofit ``state: active`` values despite durable verdicts; from R281
# onward the lifecycle frontmatter must itself reach a terminal state.
EXPLICIT_LIFECYCLE_ROUND = 281


def _parse_plan_frontmatter(plan_path: Path) -> dict[str, str]:
    """Parse the YAML-style frontmatter at the top of a plan.md.

    Returns an empty dict if plan.md is missing, has no frontmatter, or
    fails to parse. We do a minimal line-based parse rather than pulling
    in PyYAML so this stays a zero-dependency helper.
    """
    if not plan_path.is_file():
        return {}
    try:
        text = plan_path.read_text(encoding="utf-8")
    except OSError:
        return {}
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip().strip("'\"")
    return out


def _active_rounds_in_progress(
    rounds_dir: Path,
    *,
    include_stale: bool = False,
) -> list[tuple[int, dict[str, str], str]]:
    """Find R<N>/ dirs that are *genuinely* in-flight (state=active and no
    verdict yet).

    Returns a list of ``(n, frontmatter_dict, dir_name)`` sorted by N
    ascending. ``dir_name`` preserves the on-disk spelling
    (``R01`` vs ``R1``) so callers can re-construct the path.

    A feed-era round is in-flight whenever ``plan.md`` declares
    ``state: active``.  A verdict does not silently close R281+ because the
    canonical lifecycle requires ``close_round.py`` to make that transition.

    Before R281, many historical rounds retain retrofit ``state: active``
    frontmatter despite durable verdicts.  Those legacy inconsistencies remain
    hidden by default so they do not flood every cold start.

    Pass ``include_stale=True`` to disable the verdict.md gate (useful
    for ledger-hygiene audits that want to see frontmatter-vs-verdict
    inconsistencies).

    Used by ``--list-active`` and ``--strict-no-active`` to prevent the
    context-compression duplicate-work failure mode: an agent that has
    forgotten its in-flight round can be reminded before it spawns a
    duplicate. See module docstring for the R256 case study.
    """
    out: list[tuple[int, dict[str, str], str]] = []
    if not rounds_dir.is_dir():
        return out
    for entry in rounds_dir.iterdir():
        if not entry.is_dir():
            continue
        m = re.match(r"^R(\d+)$", entry.name)
        if not m:
            continue
        plan = entry / "plan.md"
        fm = _parse_plan_frontmatter(plan)
        if fm.get("state") != "active":
            continue
        round_number = int(m.group(1))
        if (
            not include_stale
            and round_number < EXPLICIT_LIFECYCLE_ROUND
            and any(entry.glob("*verdict*.md"))
        ):
            # Historical compatibility only. Feed-era rounds must transition
            # their lifecycle state explicitly even when a verdict exists.
            continue
        out.append((round_number, fm, entry.name))
    # Sort numerically (so R10 > R3, not the str-order opposite).
    out.sort(key=lambda t: t[0])
    return out


def _active_rounds_in_scope(
    active: list[tuple[int, dict[str, str], str]],
    *,
    repo_root: Path,
    rounds_dir: Path,
    manuscript_line: str | None,
) -> list[tuple[int, dict[str, str], str]]:
    """Return active rounds that conflict with the requested line scope."""

    if manuscript_line is None:
        return active
    return [
        item
        for item in active
        if lines_conflict(
            resolve_round_line(
                repo_root,
                rounds_dir / item[2] / "plan.md",
                item[1],
            ),
            manuscript_line,
        )
    ]


def _format_active_list(
    active: list[tuple[int, dict[str, str], str]],
    rounds_dir: Path,
    *,
    repo_root: Path | None = None,
) -> str:
    """Pretty-print active rounds for CLI output."""
    if not active:
        return ""
    lines = ["Active rounds (state=active in plan.md; explicit close required):"]
    for n, fm, dir_name in active:
        opened = fm.get("opened", "?")
        line = ""
        if repo_root is not None:
            owner = resolve_round_line(
                repo_root,
                rounds_dir / dir_name / "plan.md",
                fm,
            )
            line = f"  line={owner or 'GLOBAL'}"
        # Extract Driver line from plan body if present
        driver = ""
        plan_path = rounds_dir / dir_name / "plan.md"
        try:
            body = plan_path.read_text(encoding="utf-8")
            mdrv = re.search(r"^\*\*Driver\*\*:\s*(.+)$", body, re.MULTILINE)
            if mdrv:
                drv = mdrv.group(1).strip()
                # Truncate for readable single-line display
                driver = "  driver=" + (drv[:60] + "..." if len(drv) > 60 else drv)
        except OSError:
            pass
        lines.append(f"  {dir_name}  opened={opened}{line}{driver}")
    return "\n".join(lines)


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
    # Windows GBK terminals choke on non-ASCII driver lines copied from
    # plan.md (em-dash, CJK). Reconfigure stdio to utf-8 with replace
    # fallback so we never raise UnicodeEncodeError. Per CLAUDE.md
    # "Windows GBK terminal" cross-platform rule.
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, OSError):
                pass

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--memory-dir",
        default="memory",
        help="Path to the memory root (default: memory)",
    )
    parser.add_argument(
        "--line",
        help=(
            "Own the new round by one active manuscript line. Active rounds "
            "on other lines do not conflict; unowned rounds remain global locks."
        ),
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
    parser.add_argument(
        "--list-active",
        action="store_true",
        help=(
            "List all R<N>/ dirs whose plan.md declares state=active, "
            "then exit without reserving. R256-followup safeguard against "
            "the context-compression duplicate-work failure mode (see "
            "module docstring)."
        ),
    )
    parser.add_argument(
        "--strict-no-active",
        action="store_true",
        help=(
            "Refuse to reserve a new round if any R<N>/ has state=active "
            "in plan.md. Exits 1 with an error listing the active rounds. "
            "Use this in autonomous-loop scripts to prevent the agent from "
            "spawning a duplicate of its own in-flight round after context "
            "compression. Default behaviour is WARN-only."
        ),
    )
    parser.add_argument(
        "--no-warn-active",
        action="store_true",
        help=(
            "Suppress the WARN-active default. Useful when the active "
            "round is the one the caller is intentionally about to close, "
            "or in pure scripted use where the noise is unwanted."
        ),
    )
    args = parser.parse_args()
    memory_dir = Path(args.memory_dir)
    rounds_dir = memory_dir / "rounds"
    repo_root = memory_dir.resolve().parent
    manuscript_line: str | None = None
    if args.line is not None:
        try:
            manuscript_line = resolve_line_selector(
                repo_root,
                args.line,
                require_active=True,
            )
        except RoundScopeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(4)

    # --list-active short-circuit: report and exit without reserving.
    if args.list_active:
        active = _active_rounds_in_progress(rounds_dir)
        active = _active_rounds_in_scope(
            active,
            repo_root=repo_root,
            rounds_dir=rounds_dir,
            manuscript_line=manuscript_line,
        )
        if not active:
            print("(no active rounds)")
        else:
            print(_format_active_list(active, rounds_dir, repo_root=repo_root))
        return

    if args.gc:
        swept = gc_empty_rounds(rounds_dir, max_age_minutes=args.gc_minutes)
        if swept:
            for name in swept:
                print(f"GC {name}: aborted (reserved-empty >{args.gc_minutes}min)")
        else:
            print("GC: no zombies found")
        return

    try:
        reservation_lock = _acquire_reservation_lock(rounds_dir)
    except TimeoutError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(5)
    atexit.register(_release_reservation_lock, reservation_lock)

    # Active-rounds preflight (R256 followup, 2026-05-20).
    active = _active_rounds_in_progress(rounds_dir)
    active = _active_rounds_in_scope(
        active,
        repo_root=repo_root,
        rounds_dir=rounds_dir,
        manuscript_line=manuscript_line,
    )
    if active:
        if args.strict_no_active:
            print(
                f"ERROR: {len(active)} active round(s) in progress. "
                f"Refuse to reserve.",
                file=sys.stderr,
            )
            print(
                _format_active_list(active, rounds_dir, repo_root=repo_root),
                file=sys.stderr,
            )
            print(
                "Resolve the active round(s) first (close to "
                "state=completed/aborted/superseded) or use a non-strict "
                "invocation.",
                file=sys.stderr,
            )
            sys.exit(1)
        elif not args.no_warn_active:
            # Default WARN-only: print to stderr so it doesn't poison the
            # stdout `N` capture in scripts that pipe the round number.
            print(
                f"WARNING: {len(active)} active round(s) in progress. "
                f"Proceeding anyway.",
                file=sys.stderr,
            )
            print(
                _format_active_list(active, rounds_dir, repo_root=repo_root),
                file=sys.stderr,
            )
            print(
                "If this is unintentional (e.g. you forgot you already "
                "have an in-flight round from a prior turn), abort with "
                "Ctrl-C and resume the existing round instead. Pass "
                "--no-warn-active to suppress, or --strict-no-active to "
                "make this fatal.",
                file=sys.stderr,
            )

    if args.write_plan_stub:
        _refresh_oracle(memory_dir)
    n = reserve_next_round(rounds_dir)
    if args.write_plan_stub or manuscript_line is not None:
        snapshot = (
            _extract_oracle_snapshot(memory_dir / "STATE.md")
            if args.write_plan_stub
            else ""
        )
        _write_plan_stub(
            rounds_dir / f"R{n}",
            n,
            snapshot,
            manuscript_line=manuscript_line,
        )
    _release_reservation_lock(reservation_lock)
    atexit.unregister(_release_reservation_lock)
    print(n)


if __name__ == "__main__":
    _main()
