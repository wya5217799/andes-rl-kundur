"""flag_suspect_claims.py — mark/unmark claim cards as suspect (evidence object invalid).

Motivation
----------
The 2026-08-24 M/D base-convention discovery invalidated the evidence object
(pre-R478 ANDES V4 env: device-base M/D written into system-base runtime
arrays, zero-action drift, halved action authority) for a large family of
claims. Future agents must see the marker on the claim card itself and in
STATE.md before citing numbers. The marker is non-terminal: status stays
``current`` until a correction/obsoletion flips the claim (ledger-writing.md).

Schema added to claim frontmatter:
    suspect: true
    suspect_round: RNNN        # round that established the suspicion
    suspect_reason: "..."      # non-empty; why the evidence object is invalid

Usage
-----
    python memory/tools/flag_suspect_claims.py list
    python memory/tools/flag_suspect_claims.py flag --ids CLM-0001,CLM-0002 \\
        --round R478 --reason "evidence object invalid (M/D base convention)"
    python memory/tools/flag_suspect_claims.py flag --ids-file <path> --round R478 --reason "..."
    python memory/tools/flag_suspect_claims.py clear --ids CLM-0001,CLM-0002

Failure modes
-------------
- Unknown claim id or missing frontmatter: reported, file untouched.
- Non-current claim: skipped with a warning (terminal states must use
  superseded/obsoleted, not suspect).
- YAML parse failure after edit: the edit is rolled back and reported.

The tool never rewrites the whole frontmatter: it inserts/removes only the
three suspect lines after the ``status:`` line, preserving formatting.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment without pyyaml
    yaml = None

ROOT = Path(__file__).resolve().parents[2]
CLAIMS_DIR = ROOT / "memory" / "claims"

_FRONT_RE = re.compile(r"^(---\n)(.*?)(\n---\n)", re.S)
_STATUS_RE = re.compile(r"^status:\s*(\S+)\s*$", re.M)


def _load_meta(front: str) -> dict | None:
    if yaml is None:
        return None
    try:
        meta = yaml.safe_load(front) or {}
    except Exception:
        return None
    return meta if isinstance(meta, dict) else None


def _claim_path(cid: str) -> Path:
    return CLAIMS_DIR / f"{cid}.md"


def _read_claim(cid: str) -> tuple[str, str, dict] | None:
    """Return (raw_text, frontmatter, meta) or None if unreadable/missing."""
    path = _claim_path(cid)
    if not path.is_file():
        print(f"  [skip] {cid}: no card at {path.relative_to(ROOT)}")
        return None
    text = path.read_text(encoding="utf-8")
    m = _FRONT_RE.match(text)
    if not m:
        print(f"  [skip] {cid}: no YAML frontmatter")
        return None
    meta = _load_meta(m.group(2))
    if meta is None:
        print(f"  [skip] {cid}: frontmatter not parseable")
        return None
    return text, m.group(2), meta


def _write_claim(cid: str, text: str) -> bool:
    try:
        _claim_path(cid).write_text(text, encoding="utf-8")
        return True
    except OSError as exc:  # pragma: no cover - IO failure path
        print(f"  [error] {cid}: cannot write: {exc}")
        return False


def _suspect_block(round_id: str, reason: str) -> str:
    # Double-quoted scalar: reason may contain colons/spaces safely.
    esc = reason.replace("\\", "\\\\").replace('"', '\\"')
    return (
        f"suspect: true\n"
        f"suspect_round: {round_id}\n"
        f'suspect_reason: "{esc}"\n'
    )


def _insert_after_status(front: str, block: str) -> str:
    """Insert block right after the ``status:`` line (inside frontmatter)."""
    m = _STATUS_RE.search(front)
    if not m:
        return front
    pos = m.end()
    return front[:pos] + "\n" + block.rstrip("\n") + front[pos:]


def _strip_suspect(front: str) -> str:
    lines = []
    drop = False
    for line in front.splitlines(keepends=True):
        if re.match(r"^suspect:\s*\S", line):
            drop = True
            continue
        if drop and re.match(r"^suspect_(round|reason):", line):
            continue
        drop = False
        lines.append(line)
    return "".join(lines)


def _flag_one(cid: str, round_id: str, reason: str, *, dry_run: bool) -> bool:
    got = _read_claim(cid)
    if got is None:
        return False
    text, front, meta = got
    if meta.get("status") != "current":
        print(f"  [skip] {cid}: status={meta.get('status')!r} (not current)")
        return False
    if meta.get("suspect"):
        print(f"  [skip] {cid}: already suspect")
        return True
    new_front = _insert_after_status(front, _suspect_block(round_id, reason))
    if new_front is front:
        print(f"  [skip] {cid}: no status: line found")
        return False
    if _load_meta(new_front) is None:
        print(f"  [error] {cid}: inserted block breaks frontmatter; rolled back")
        return False
    new_text = text.replace(front, new_front, 1)
    if dry_run:
        print(f"  [dry-run] {cid}: would flag")
        return True
    if _write_claim(cid, new_text):
        print(f"  [ok] {cid}")
        return True
    return False


def _clear_one(cid: str, *, dry_run: bool) -> bool:
    got = _read_claim(cid)
    if got is None:
        return False
    text, front, meta = got
    if not meta.get("suspect"):
        print(f"  [skip] {cid}: not suspect")
        return True
    new_front = _strip_suspect(front)
    new_text = text.replace(front, new_front, 1)
    if dry_run:
        print(f"  [dry-run] {cid}: would clear")
        return True
    if _write_claim(cid, new_text):
        print(f"  [ok] {cid}: cleared")
        return True
    return False


def _list_suspect() -> int:
    rows = []
    for path in sorted(CLAIMS_DIR.glob("CLM-*.md")):
        text = path.read_text(encoding="utf-8")
        m = _FRONT_RE.match(text)
        if not m:
            continue
        meta = _load_meta(m.group(2))
        if meta and meta.get("suspect"):
            reason = str(meta.get("suspect_reason") or "").strip().splitlines()[0]
            rows.append(
                f"{meta['id']} [{meta.get('suspect_round', '?')}] "
                f"[round {meta.get('round', '?')}] {reason}"
            )
    for row in rows:
        print(row)
    print(f"-- {len(rows)} suspect claim(s)")
    return 0


def _parse_ids(raw: str | None, ids_file: str | None) -> list[str]:
    ids: list[str] = []
    if raw:
        ids.extend(x.strip() for x in raw.split(",") if x.strip())
    if ids_file:
        p = Path(ids_file)
        if not p.is_file():
            raise SystemExit(f"ids-file not found: {p}")
        ids.extend(
            x.strip() for x in p.read_text(encoding="utf-8").split() if x.strip()
        )
    seen: set[str] = set()
    out = []
    for cid in ids:
        if cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list all suspect claims")
    p_list.set_defaults(func=lambda a: _list_suspect())

    p_flag = sub.add_parser("flag", help="mark claims as suspect")
    p_flag.add_argument("--ids", help="comma-separated claim ids")
    p_flag.add_argument("--ids-file", help="file with one claim id per line")
    p_flag.add_argument("--round", required=True, help="suspect_round (e.g. R478)")
    p_flag.add_argument("--reason", required=True, help="suspect_reason text")
    p_flag.add_argument("--dry-run", action="store_true")
    p_flag.set_defaults(func=_cmd_flag)

    p_clear = sub.add_parser("clear", help="remove suspect markers")
    p_clear.add_argument("--ids", help="comma-separated claim ids")
    p_clear.add_argument("--ids-file", help="file with one claim id per line")
    p_clear.add_argument("--dry-run", action="store_true")
    p_clear.set_defaults(func=_cmd_clear)

    args = parser.parse_args(argv)
    return args.func(args)


def _cmd_flag(args: argparse.Namespace) -> int:
    ids = _parse_ids(args.ids, args.ids_file)
    if not ids:
        raise SystemExit("no claim ids given (--ids or --ids-file)")
    ok = sum(1 for cid in ids if _flag_one(cid, args.round, args.reason, dry_run=args.dry_run))
    print(f"-- flagged {ok}/{len(ids)}")
    return 0


def _cmd_clear(args: argparse.Namespace) -> int:
    ids = _parse_ids(args.ids, args.ids_file)
    if not ids:
        raise SystemExit("no claim ids given (--ids or --ids-file)")
    ok = sum(1 for cid in ids if _clear_one(cid, dry_run=args.dry_run))
    print(f"-- cleared {ok}/{len(ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
