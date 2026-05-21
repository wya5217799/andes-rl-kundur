"""Operations dashboard — what is training, what is queued, what just landed.

Replaces the ad-hoc ``wsl ps`` + ``ls results/`` polling pattern that
dominates an active autonomous-loop session. One command answers:

1. **In flight (WSL)**: which ``scripts/train.py`` processes are
   currently running (extracted via WSL ``ps``), plus their run-dir
   names + elapsed wall time.
2. **Active rounds without summary**: ``memory/rounds/R*/plan.md``
   with ``state: active`` but no ``results/<r*>/final_eval_summary.json``
   — these are either training in flight or zombies awaiting GC.
3. **Recently scored**: last N runs by ``final_eval_summary.json``
   mtime — useful for "is the autonomous loop still producing?".

This tool is **read-only**. It does not start or stop anything. It is
safe to call from anywhere (Bash, Python, autonomous-loop callback)
and always exits cleanly even if WSL is unavailable.

Usage (CLI)
-----------
::

    $ python memory/tools/status.py
    ── In flight (WSL) ──────────────────────────────────────────
      PID 1151  19:23  results/r245_w1_scalar_onlyphiabs_150ep_s54
      PID 1234  03:14  results/r252_w1_...
    ── Active rounds without summary ────────────────────────────
      R245  (training; matches running PID 1151)
      R252  (training; matches running PID 1234)
    ── Recently scored (last 5 by mtime) ────────────────────────
      r251_w1_scalar_full_v4_s50      geo=0.2662  cum_rf=-0.0878
      ...

    $ python memory/tools/status.py --json
    {"in_flight":[...], "active_rounds":[...], "recent_scored":[...]}
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Local imports (lazy in functions to avoid pyimport-time cost from
# baselines.py when status.py is used standalone)
_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class InflightTraining:
    pid: int
    etime: str            # HH:MM or H:MM:SS as ``ps -eo etime`` formats
    save_dir: str         # ``results/<run>/`` from --save-dir flag
    cmd_preview: str      # truncated command line for context


@dataclass(frozen=True)
class ActiveRound:
    round_id: str         # e.g. "R245"
    matched_pid: int | None
    has_summary: bool
    note: str             # "training", "zombie", "awaiting score"


@dataclass(frozen=True)
class RecentScored:
    run: str
    geo: float | None
    cum_rf: float | None
    mtime: float


_PS_PATTERN = re.compile(
    r"^\s*(\d+)\s+(\S+)\s+.*?--save-dir\s+(\S+)",
    re.MULTILINE,
)


def list_inflight_wsl(distro: str = "Ubuntu") -> list[InflightTraining]:
    """Run ``wsl -d <distro> ps -eo pid,etime,cmd`` and pull out python
    train.py processes. Returns ``[]`` if WSL is unavailable or no
    matching processes exist."""
    try:
        proc = subprocess.run(
            ["wsl", "-d", distro, "ps", "-eo", "pid,etime,cmd"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    out: list[InflightTraining] = []
    for line in proc.stdout.splitlines():
        if "scripts/train.py" not in line:
            continue
        if "grep" in line:  # the grep itself shouldn't match but defend
            continue
        # Pull out --save-dir argument
        save_match = re.search(r"--save-dir\s+(\S+)", line)
        if not save_match:
            continue
        save_dir = save_match.group(1)
        # First token = pid, second = etime
        toks = line.strip().split(None, 2)
        if len(toks) < 3:
            continue
        try:
            pid = int(toks[0])
        except ValueError:
            continue
        etime = toks[1]
        cmd_preview = toks[2][:120] + ("…" if len(toks[2]) > 120 else "")
        out.append(InflightTraining(pid=pid, etime=etime,
                                    save_dir=save_dir,
                                    cmd_preview=cmd_preview))
    return out


def list_active_rounds(rounds_dir: Path, results_dir: Path,
                       inflight: list[InflightTraining],
                       *,
                       suppress_closed_verdicts: bool = True,
                       ) -> list[ActiveRound]:
    """Walk ``rounds_dir`` for ``plan.md`` with ``state: active`` and
    classify each: training (matches an inflight PID's save-dir),
    scored-but-state-stale (verdict.md exists, state still active —
    needs ``close_round.py``), or awaiting-score / zombie.

    When ``suppress_closed_verdicts=True`` (default), rounds whose
    plan.md says ``state: active`` BUT have a ``verdict.md`` are
    silently filtered out — they're effectively closed and the
    inconsistency is a housekeeping issue for ``close_round.py``,
    not an operational concern. Pass ``False`` to surface them as a
    'state-stale' diagnostic.
    """
    import yaml
    out: list[ActiveRound] = []
    if not rounds_dir.is_dir():
        return out
    inflight_paths = {Path(t.save_dir).name.lower(): t.pid for t in inflight}
    for round_dir in sorted(rounds_dir.iterdir()):
        if not round_dir.is_dir() or not round_dir.name.startswith("R"):
            continue
        plan = round_dir / "plan.md"
        if not plan.exists():
            continue
        try:
            text = plan.read_text(encoding="utf-8")
        except OSError:
            continue
        fm_match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        if not fm_match:
            continue
        try:
            fm = yaml.safe_load(fm_match.group(1)) or {}
        except yaml.YAMLError:
            continue
        if fm.get("state") != "active":
            continue
        # Check for verdict — if present and we're suppressing, skip
        has_verdict = any(round_dir.glob("*verdict*.md"))
        if has_verdict and suppress_closed_verdicts:
            continue
        # Match any results/<r<round#>_*>/ directory
        round_num_match = re.match(r"^R(\d+)$", round_dir.name)
        if not round_num_match:
            continue
        n = round_num_match.group(1)
        matched_pid: int | None = None
        has_summary = False
        if results_dir.is_dir():
            for r_dir in results_dir.glob(f"r{n}_*"):
                if not r_dir.is_dir():
                    continue
                if (r_dir / "final_eval_summary.json").exists():
                    has_summary = True
                pid = inflight_paths.get(r_dir.name.lower())
                if pid is not None:
                    matched_pid = pid
                    break
        if matched_pid is not None:
            note = f"training (PID {matched_pid})"
        elif has_verdict:
            note = "state-stale (verdict written, run close_round.py)"
        elif has_summary:
            note = "scored — needs verdict.md"
        else:
            note = "awaiting score / zombie"
        out.append(ActiveRound(
            round_id=round_dir.name,
            matched_pid=matched_pid,
            has_summary=has_summary,
            note=note,
        ))
    return out


def list_recent_scored(results_dir: Path, *, limit: int = 5) -> list[RecentScored]:
    """Last ``limit`` runs by ``final_eval_summary.json`` mtime, newest
    first. Reads geo + cum_rf for dual-metric display."""
    if not results_dir.is_dir():
        return []
    rows: list[RecentScored] = []
    for run_dir in results_dir.iterdir():
        if not run_dir.is_dir():
            continue
        summary = run_dir / "final_eval_summary.json"
        if not summary.exists():
            continue
        try:
            j = json.loads(summary.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        rows.append(RecentScored(
            run=run_dir.name,
            geo=j.get("geo"), cum_rf=j.get("cum_rf"),
            mtime=summary.stat().st_mtime,
        ))
    rows.sort(key=lambda r: r.mtime, reverse=True)
    return rows[:limit]


def _print_human(inflight: list[InflightTraining],
                 active: list[ActiveRound],
                 recent: list[RecentScored]) -> None:
    # ASCII-only box drawing so Windows GBK terminals don't UnicodeEncodeError
    print("-- In flight (WSL) ------------------------------------------")
    if not inflight:
        print("  (none)")
    for t in inflight:
        print(f"  PID {t.pid:<5d}  etime={t.etime:<9s}  {t.save_dir}")

    print("-- Active rounds (state: active in plan.md) ----------------")
    if not active:
        print("  (none)")
    for r in active:
        flag = "x" if r.has_summary else " "
        print(f"  [{flag}] {r.round_id:<6s}  {r.note}")

    print("-- Recently scored (top by summary mtime) ------------------")
    if not recent:
        print("  (none)")
    for r in recent:
        geo_s = f"{r.geo:.4f}" if r.geo is not None else "n/a"
        cum_s = f"{r.cum_rf:+.4f}" if r.cum_rf is not None else "n/a"
        print(f"  {r.run:42s}  geo={geo_s:>8s}  cum_rf={cum_s:>9s}")


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--memory-dir", default=str(_ROOT / "memory"),
        help="Path to memory dir (default: <repo>/memory)",
    )
    parser.add_argument(
        "--results-dir", default=str(_ROOT / "results"),
        help="Path to results dir (default: <repo>/results)",
    )
    parser.add_argument(
        "--wsl-distro", default="Ubuntu",
        help="WSL distro name (default: Ubuntu)",
    )
    parser.add_argument(
        "--recent-limit", type=int, default=8,
        help="Number of recently-scored runs to show (default: 8)",
    )
    parser.add_argument(
        "--show-state-stale", action="store_true",
        help="Surface 'state: active in plan.md but verdict.md exists' "
             "rounds as diagnostic entries (default: suppress; these "
             "are housekeeping for close_round.py, not operational).",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Emit machine-readable JSON instead of human format",
    )
    args = parser.parse_args()

    inflight = list_inflight_wsl(distro=args.wsl_distro)
    active = list_active_rounds(
        Path(args.memory_dir) / "rounds",
        Path(args.results_dir),
        inflight,
        suppress_closed_verdicts=not args.show_state_stale,
    )
    recent = list_recent_scored(Path(args.results_dir),
                                limit=args.recent_limit)

    if args.json:
        json.dump({
            "in_flight": [asdict(t) for t in inflight],
            "active_rounds": [asdict(r) for r in active],
            "recent_scored": [asdict(r) for r in recent],
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return
    _print_human(inflight, active, recent)


if __name__ == "__main__":
    _main()
