"""Rank workflow-friction signals across DeepSeek Harness session history.

Motivation
----------
The research loop's most expensive failures are not scientific — they are
workflow friction that repeats across sessions: long commands colliding with
the harness wall-clock ceiling, memory-tool CLI misuse, edit-tool rejections,
duplicate file creation, and the owner repeatedly overriding over-strict rules
("说人话", "别管规则", "拉满硬件", "不要停"). Those lessons only become
preventable once they are measured, so this tool re-runs a bounded census over
the DSH session artifacts (zstd JSONL under ``~/.dsh/sessions/``) and prints a
ranked friction report. It is the self-optimization loop: run it after a batch
of rounds, read the top signals, codify the fix into a rule/tool, rerun.

Usage
-----
    python memory/tools/session_friction.py                    # current repo
    python memory/tools/session_friction.py --cwd <path>       # any workspace
    python memory/tools/session_friction.py --all              # every workspace
    python memory/tools/session_friction.py --json --limit 30
    python memory/tools/session_friction.py --artifact <file>  # one external
        session export: a .zip bundle, a plain .jsonl session, or a
        .zstd/.zst artifact (cwd filter disabled for artifacts)

Failure modes
-------------
- No ``zstandard`` module: exits 2 with an install hint (the analyzer is a
  convenience, never a gate — absence must not block a round).
- Torn final zstd frame (crash mid-write): the longest decodable prefix is
  used; the artifact is counted ``torn`` instead of silently dropped.
- Empty/unparsable header: artifact skipped and counted, not crashed on.

Output
------
Ranked, de-duplicated friction signals plus the top owner-correction quotes.
``--json`` emits the same structure machine-readably for downstream linting.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    import zstandard as zstd
except ImportError:  # graceful: analyzer is a convenience, not a gate
    print("session_friction.py: requires `zstandard` (pip install zstandard)", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[2]  # repo root, cwd-independent


# --------------------------------------------------------------------------- #
# Friction signatures (substring scans over tool-result / user text)
# --------------------------------------------------------------------------- #
TIMEOUT_RE = re.compile(
    r"wall-clock ceiling reached \((\d+)ms\)|timed out after (\d+)ms", re.I)
CLI_USAGE_RE = re.compile(
    r"usage: (reserve_round|reserve_claim|close_round|round_preflight|validate|"
    r"render|feed_check|technical_route_census|gpt_pro_pack)\.py")
EDIT_FAIL_RE = re.compile(
    r"old_string was not found|edit requires reading|requires reading .* first")
DUP_CREATE_RE = re.compile(r"cannot overwrite existing|refusing to materialize")
BIND_FAIL_RE = re.compile(
    r"binding arguments must be lossless JSON|missing required property|"
    r"invalid arguments|Unexpected token")
WIN32_RE = re.compile(r"unsupported on platform win32|terminal inspection is unsupported")
# Owner correction markers (Chinese; kept narrow to avoid false hits on
# subagent prompts / ritual boilerplate).
CORRECT_RE = re.compile(
    r"说人话|听不懂|不要一有问题就问我|干就完了|拉满硬件|别管规则|改规则|"
    r"别克隆|别乱改|不要放|不要停|一个一个地问|求求了|彻底修改规则|"
    r"限制少一点|自优化|重新实验|难道就|为什么不能|你就没有注意")


def _ms_to_iso(ms) -> str:
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return "?"


def _decompress(data: bytes) -> tuple[str, str]:
    """Decode concatenated zstd frames; tolerate a torn final frame."""
    dctx = zstd.ZstdDecompressor()
    try:
        with dctx.stream_reader(io.BytesIO(data)) as r:
            return r.read().decode("utf-8", "replace"), "ok"
    except Exception:
        pass
    out = b""
    d = zstd.ZstdDecompressor()
    try:
        dobj = d.decompressobj()
        out = dobj.decompress(data)
        remaining = dobj.unused_data
        while remaining:  # drain concatenated frames past the first
            try:
                dobj2 = d.decompressobj()
                out += dobj2.decompress(remaining)
                remaining = dobj2.unused_data
            except Exception:
                break
    except Exception:
        pass
    return (out.decode("utf-8", "replace"), "torn") if out else ("", "empty")


def _result_text(o: dict) -> str:
    d = o.get("data") or {}
    msg = d.get("message") or {}
    for c in msg.get("content") or []:
        if isinstance(c, dict) and c.get("type") == "tool-result":
            for inner in c.get("content") or []:
                if isinstance(inner, dict) and inner.get("type") == "text":
                    return inner.get("text", "")
    return ""


def _user_text(o: dict) -> str:
    d = o.get("data") or {}
    return "".join(c.get("text", "") for c in (d.get("content") or []) if isinstance(c, dict))


def _find_artifacts(sessions_root: Path):
    for proj in sessions_root.iterdir():
        if not proj.is_dir():
            continue
        for sdir in proj.iterdir():
            if not sdir.is_dir():
                continue
            for f in sdir.iterdir():
                if ".zstd" in f.name:
                    yield f


def _scan_text(text, cwd, all_ws, stats, sig, sig_examples, corrections,
               session_id=None):
    """Scan one decoded session text; shared by the archive walk and --artifact."""
    lines = text.split("\n")
    try:
        header = json.loads(lines[0])
    except Exception:
        header = {}
    if header.get("type") != "session":
        return
    if session_id is None:
        session_id = str(header.get("id"))
    if not all_ws and cwd:
        hcwd = (header.get("cwd") or "").replace("\\", "/").lower()
        if hcwd != (cwd.replace("\\", "/").lower()):
            return
    stats["sessions"] += 1
    for l in lines[1:]:
        if not l.strip():
            continue
        try:
            o = json.loads(l)
        except Exception:
            continue
        t = o.get("type")
        if t == "user/message":
            u = _user_text(o)
            if CORRECT_RE.search(u) and not u.startswith(("<", "You are", "Repository root:")):
                corrections.append((session_id, u))
        elif t == "tool/result":
            r = _result_text(o)
            if not r:
                continue
            for cls, rx, head in (
                ("timeout", TIMEOUT_RE, "wall-clock ceiling"),
                ("cli-usage", CLI_USAGE_RE, "usage:"),
                ("edit-fail", EDIT_FAIL_RE, "old_string not found"),
                ("dup-create", DUP_CREATE_RE, "cannot overwrite existing"),
                ("bind-fail", BIND_FAIL_RE, "binding arguments"),
                ("win32", WIN32_RE, "unsupported on platform"),
            ):
                if rx.search(r):
                    sig[cls] += 1
                    ex = r.split("\n")[0][:120] if r.split("\n") else r[:120]
                    sig_examples.setdefault(cls, [])
                    if ex not in sig_examples[cls] and len(sig_examples[cls]) < 6:
                        sig_examples[cls].append(ex)
                    break  # one dominant class per result


def _load_artifact(path: Path) -> tuple[str, str]:
    """Decode one external session artifact into scan text.

    Accepts a .zip bundle (looks for session.jsonl / *.zstd / *.zst members),
    a plain .jsonl session, or a .zstd/.zst artifact. Returns (text, status);
    empty text with a non-ok status means the caller reports and exits.
    """
    if path.suffix.lower() == ".zip":
        try:
            zf = zipfile.ZipFile(path)
        except Exception:
            return "", "bad-zip"
        cand = [n for n in zf.namelist()
                if n.lower().endswith((".jsonl", ".zstd", ".zst"))
                and "__MACOSX" not in n]
        if not cand:
            return "", "no-session"
        cand.sort(key=lambda n: (not n.lower().endswith("session.jsonl"), n))
        try:
            raw = zf.read(cand[0])
        except Exception:
            return "", "bad-zip"
        if cand[0].lower().endswith(".jsonl"):
            return raw.decode("utf-8", "replace"), "ok"
        return _decompress(raw)
    if path.suffix.lower() in (".zstd", ".zst"):
        try:
            raw = path.read_bytes()
        except OSError:
            return "", "missing"
        return _decompress(raw)
    try:
        return path.read_text(encoding="utf-8", errors="replace"), "ok"
    except OSError:
        return "", "missing"


def _scan(artifacts, cwd, all_ws):
    stats = Counter()
    sig = Counter()      # signal class -> count
    sig_examples = {}    # signal class -> list of short examples
    corrections = []     # (session id, user text)
    for path in artifacts:
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        text, status = _decompress(raw)
        stats[status] += 1
        if not text:
            continue
        _scan_text(text, cwd, all_ws, stats, sig, sig_examples, corrections)
    return stats, sig, sig_examples, corrections


def _render(stats, sig, sig_examples, corrections, limit):
    out = []
    out.append("== session-friction report ==")
    out.append(f"artifacts: ok={stats['ok']} torn={stats['torn']} empty={stats['empty']} "
               f"sessions={stats['sessions']}")
    out.append("")
    out.append("== ranked friction signals ==")
    if not sig:
        out.append("(none)")
    for cls, n in sig.most_common():
        out.append(f"{n:>4}  {cls}")
        for ex in sig_examples.get(cls, [])[:3]:
            out.append(f"        {ex}")
    out.append("")
    out.append(f"== owner-correction quotes ({len(corrections)}; top {limit}) ==")
    seen = set()
    shown = 0
    for sid, u in corrections:
        key = u[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(f"- [{sid[:8]}] {u[:240]}")
        shown += 1
        if shown >= limit:
            break
    return "\n".join(out)


def main(argv=None) -> int:
    # Windows consoles default to GBK; owner-correction quotes are Chinese, so
    # force UTF-8 output (Codex 2026-08-23 needed `-X utf8` to run this tool).
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Rank workflow friction across DSH session history")
    ap.add_argument("--cwd", default=str(ROOT), help="workspace path to filter (default: repo root)")
    ap.add_argument("--sessions-root",
                    default=str(Path(os.environ.get("USERPROFILE", "~")) / ".dsh" / "sessions"))
    ap.add_argument("--all", action="store_true", help="include every workspace, ignore --cwd")
    ap.add_argument("--artifact",
                    help="scan one external session artifact (.zip bundle, .jsonl session, or .zstd/.zst); cwd filter disabled")
    ap.add_argument("--limit", type=int, default=25, help="max correction quotes (default 25)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    if args.artifact:
        p = Path(args.artifact).expanduser()
        if not p.is_file():
            print(f"session_friction.py: artifact not found: {p}", file=sys.stderr)
            return 1
        stats = Counter()
        sig = Counter()
        sig_examples = {}
        corrections = []
        text, status = _load_artifact(p)
        stats[status] += 1
        if not text:
            print(f"session_friction.py: no session text in artifact: {p} "
                  f"(status={status})", file=sys.stderr)
            return 1
        _scan_text(text, None, True, stats, sig, sig_examples, corrections)
    else:
        root = Path(args.sessions_root).expanduser()
        if not root.is_dir():
            print(f"session_friction.py: sessions root not found: {root}", file=sys.stderr)
            return 1
        stats, sig, sig_examples, corrections = _scan(
            _find_artifacts(root), args.cwd, args.all)
    if args.json:
        print(json.dumps({
            "stats": dict(stats), "signals": dict(sig),
            "examples": sig_examples,
            "corrections": [{"session": s, "text": u[:400]} for s, u in corrections],
        }, ensure_ascii=False, indent=2))
    else:
        print(_render(stats, sig, sig_examples, corrections, args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
