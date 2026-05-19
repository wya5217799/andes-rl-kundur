"""One-shot: backfill `state` + `opened` fields into legacy round plans.

Ran once during R166 housekeeping sweep (2026-05-19). Kept in repo as audit
artifact — DO NOT re-run on already-backfilled plans.

For each `memory/rounds/RNNN/plan.md`:
- Parse existing frontmatter (if any); preserve all fields
- If `state` is already set, skip (idempotent)
- Otherwise inject:
  * `state: active`        (sweep phase B will flip zombies)
  * `opened: <date>`       (from `git log --diff-filter=A` first-touch,
                            falls back to file mtime)
  * `round: R<NNN>`        (if missing)
- Re-serialise frontmatter, preserve body verbatim
"""
from __future__ import annotations
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import yaml

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
ROUND_DIR_RE = re.compile(r"^R(\d+)$")


def _git_first_touch(repo_root: Path, file_path: Path) -> date | None:
    """Return the date of the commit that first added this file, or None."""
    try:
        out = subprocess.check_output(
            [
                "git", "log", "--diff-filter=A", "--follow",
                "--format=%ad", "--date=short", "--", str(file_path),
            ],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip().splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    if not out:
        return None
    # Take the LAST line (oldest commit in git log output)
    try:
        return date.fromisoformat(out[-1].strip())
    except ValueError:
        return None


def _file_mtime_date(path: Path) -> date:
    return datetime.fromtimestamp(path.stat().st_mtime).date()


def _backfill_plan(plan_path: Path, repo_root: Path, round_name: str) -> str:
    """Inject state/opened into one plan.md. Returns one-line status."""
    text = plan_path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if m:
        fm_raw, body = m.group(1), m.group(2)
        fm = yaml.safe_load(fm_raw) or {}
    else:
        fm = {}
        body = text

    if fm.get("state"):
        return f"SKIP  {round_name} — already has state={fm['state']}"

    opened = _git_first_touch(repo_root, plan_path) or _file_mtime_date(plan_path)

    new_fm: dict = {}
    new_fm["round"] = fm.get("round") or round_name
    new_fm["state"] = "active"
    new_fm["opened"] = opened.isoformat()
    new_fm["closed"] = None
    new_fm["supersedes_rounds"] = fm.get("supersedes_rounds") or []
    new_fm["superseded_by_round"] = fm.get("superseded_by_round")
    new_fm["abort_reason"] = fm.get("abort_reason")
    new_fm["superseded_note"] = fm.get("superseded_note")
    # Preserve any other pre-existing keys we didn't model
    for k, v in fm.items():
        if k not in new_fm:
            new_fm[k] = v

    fm_dump = yaml.safe_dump(new_fm, sort_keys=False, allow_unicode=True).strip()
    new_text = f"---\n{fm_dump}\n---\n{body.lstrip(chr(10))}"
    if not new_text.endswith("\n"):
        new_text += "\n"
    plan_path.write_text(new_text, encoding="utf-8")
    return f"WRITE {round_name} — state=active opened={opened.isoformat()}"


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    rounds_dir = repo_root / "memory" / "rounds"
    touched = 0
    skipped = 0
    for round_dir in sorted(rounds_dir.iterdir()):
        m = ROUND_DIR_RE.match(round_dir.name)
        if not (round_dir.is_dir() and m):
            continue
        plan = round_dir / "plan.md"
        if not plan.exists():
            print(f"NOPL  {round_dir.name} — no plan.md (reserved-empty)")
            continue
        msg = _backfill_plan(plan, repo_root, round_dir.name)
        print(msg)
        if msg.startswith("WRITE"):
            touched += 1
        elif msg.startswith("SKIP"):
            skipped += 1
    print(f"\nDone: {touched} written, {skipped} skipped (already had state)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
