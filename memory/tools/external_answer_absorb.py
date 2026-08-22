"""Absorb an external answer package (GPT chat export) into the repo.

Motivation: the owner repeatedly hands back chat-export folders with external
math answers ("这是结果" / "全部吸收" / "彻底吸收"). Absorbing one by hand
repeats the same housekeeping every time — this exact pipeline ran three times
in the 2026-08-22 session (agent-results / complete-outputs / deep-solutions
packages), each time rediscovering the same gotchas: a nested same-name folder
hides the real root; Chinese filenames break the read tool and hash checks
(Unicode normalization); SHA256SUMS lines are easy to mis-parse by hand; and
the same four ledger files (ARTIFACTS.json, gpt_pro_manifest.json note,
gate_calibration_log, draft_update_queue) get hand-edited per package.
This CLI turns the pattern into a tool. Ledger edits stay agent-performed, but
the tool stages the package, verifies it, classifies duplicates, and emits
ready-to-insert registration snippets.

Usage:

    # stage + verify + duplicate-scan + emit registration snippets
    python memory/tools/external_answer_absorb.py --src <folder> \
        --line yang_md_decoupling_marl

    # custom staging name (default: basename of the real package root)
    python memory/tools/external_answer_absorb.py --src <folder> \
        --line yang_md_decoupling_marl --slug gpt_pro_math_pkgX_20260822

    # report only, copy nothing
    python memory/tools/external_answer_absorb.py --src <folder> \
        --line yang_md_decoupling_marl --dry-run

Stages:
    1. locate the real root (descend one nested directory that shares the
       basename of the given folder);
    2. stage every file under tmp/<line>/<slug>/ with ASCII-safe renames for
       non-ASCII path components (mapping recorded in NAME_MAP.json);
    3. verify SHA256SUMS if present (whitespace-tolerant parse; missing
       entries are matched by file hash instead of by path, which survives
       NFC/NFD filename mismatches);
    4. duplicate scan: hash each staged file against every file already under
       tmp/<line>/gpt_pro_* and classify NEW vs DUPLICATE(<existing path>);
    5. write intake_record.json plus REGISTER.md holding an ARTIFACTS.json
       entry, manifest note append lines (per matched problem id), and a
       gate-calibration-log row template.

Failure modes:
- Missing/unreadable src or empty package -> exit 2 with a message.
- Destination tmp/<line>/<slug> exists -> exit 2 (create-only; never merges
  into an already-staged package).
- SHA256SUMS entries that match no staged file hash -> recorded as unmatched
  and reported; the tool exits 1 so the caller sees the gap.
- Unknown line directory (paper/<line>/LINE.md missing) -> exit 2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

TOOL_NAME = "external_answer_absorb"
REPO_RELATIVE_FORBIDDEN = ("..",)


def repo_root() -> Path:
    """Repository root, independent of cwd (self-locating)."""
    return Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def locate_real_root(src: Path) -> Path:
    """Descend one nested dir that shares the src basename (chat exports often
    wrap the package in an outer folder of the same name)."""
    if not src.is_dir():
        raise ValueError(f"src folder not found: {src}")
    inner = src / src.name
    if inner.is_dir():
        return inner
    return src


def _ascii_component(name: str, counter: list[int]) -> str:
    """Deterministic ASCII-safe rename for a non-ASCII path component."""
    if all(ord(c) < 128 for c in name):
        return name
    suffix = Path(name).suffix
    stem = Path(name).stem
    prefix = re.sub(r"[^A-Za-z0-9_\-]", "", stem)[:24] or "file"
    counter[0] += 1
    return f"{prefix}_ascii{counter[0]}{suffix}"


def stage_package(src_root: Path, dst: Path) -> dict[str, str]:
    """Copy the package into dst with ASCII-safe names. Returns name map."""
    name_map: dict[str, str] = {}
    counter = [0]
    for f in sorted(src_root.rglob("*")):
        if not f.is_file():
            continue
        parts = list(f.relative_to(src_root).parts)
        new_parts = []
        for comp in parts:
            new_parts.append(_ascii_component(comp, counter))
        rel = Path(*new_parts)
        if rel.as_posix() != f.relative_to(src_root).as_posix():
            name_map[f.relative_to(src_root).as_posix()] = rel.as_posix()
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(f.read_bytes())
    return name_map


def parse_sums(sums_text: str) -> list[tuple[str, str]]:
    """Parse GNU-coreutils-style SHA256SUMS into (hash, relpath) pairs."""
    entries = []
    for line in sums_text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2 or len(parts[0]) != 64:
            continue
        rel = parts[1].lstrip("*")
        rel = rel.lstrip("./")
        entries.append((parts[0].lower(), rel.replace("/", "\\")))
    return entries


def verify_sums(staged: dict[str, Path], entries: list[tuple[str, str]]) -> dict:
    """Match sums entries to staged files. Exact path first, then by hash
    (survives NFC/NFD filename mismatches)."""
    hash_to_path: dict[str, list[str]] = {}
    for rel, p in staged.items():
        hash_to_path.setdefault(_sha256(p), []).append(rel)
    matched: list[dict] = []
    unmatched: list[dict] = []
    for expected, rel in entries:
        p = staged.get(rel)
        if p is not None and _sha256(p) == expected:
            matched.append({"expected_path": rel, "status": "path-match"})
            continue
        candidates = hash_to_path.get(expected, [])
        if candidates:
            matched.append({
                "expected_path": rel,
                "status": "hash-match",
                "matched_staged_path": candidates[0],
            })
        else:
            unmatched.append({"expected_path": rel, "expected_sha256": expected})
    return {"checked": len(entries), "matched": matched, "unmatched": unmatched}


def duplicate_scan(staged: dict[str, Path], line_dir: Path, self_dir: Path) -> dict[str, list[str]]:
    """Hash staged files against every already-staged file under tmp/<line>/gpt_pro_*."""
    existing: dict[str, list[str]] = {}
    root = line_dir.parent  # tmp/
    for cand in sorted((root / line_dir.name).glob("gpt_pro_*")):
        if cand == self_dir:
            continue
        for f in cand.rglob("*"):
            if f.is_file():
                existing.setdefault(_sha256(f), []).append(str(f))
    dups: dict[str, list[str]] = {}
    for rel, p in staged.items():
        for where in existing.get(_sha256(p), []):
            dups.setdefault(rel, []).append(where)
    return dups


def build_record(args, src_root: Path, dst: Path, name_map: dict, sums: dict,
                 dups: dict, staged: dict) -> dict:
    files = sorted(staged)
    return {
        "schema_version": 1,
        "tool": TOOL_NAME,
        "line": args.line,
        "src_root": str(src_root),
        "staged_root": str(dst),
        "ascii_name_map": name_map,
        "sha256sums": sums,
        "duplicates": dups,
        "files": [
            {"rel": rel, "bytes": staged[rel].stat().st_size,
             "sha256": _sha256(staged[rel]), "status": "DUPLICATE" if rel in dups else "NEW"}
            for rel in files
        ],
    }


def register_snippets(record: dict, dst: Path, args, root: Path) -> None:
    """Write REGISTER.md with ready-to-insert ledger snippets."""
    slug_id = re.sub(r"[^a-z0-9\-]", "-", dst.name.lower()).strip("-")
    staged_root = dst.relative_to(root).as_posix()
    inputs = []
    for name in ("README.md", "MASTER_SOLUTION.md", "VERIFICATION_REPORT.md",
                 "SHA256SUMS", "IMPORT_NOTE.md", "AUDITED_UPDATE_20260822.md",
                 "AUDIT_UPDATE_20260822.md", "INDEX.md"):
        if name in record["files"]:
            inputs.append(f"{staged_root}/{name}")
    if not inputs:
        inputs = [f"{staged_root}/{rel}" for rel in record["files"][:3]]
    artifact_entry = {
        "id": f"gpt-pro-{slug_id}",
        "purpose": "external-question",
        "path": staged_root,
        "status": "active",
        "canonical": False,
        "authoritative": False,
        "producer": "external-solver+project-governance",
        "inputs": inputs,
        "supersedes": [],
        "review_after": None,
    }
    lines = [
        "# Registration snippets for staged package",
        "",
        f"Staged root: `{staged_root}` (record: `{staged_root}/intake_record.json`)",
        "",
        "## 1. ARTIFACTS.json entry (insert into `paper/<line>/ARTIFACTS.json` `artifacts`)",
        "",
        "```json",
        json.dumps(artifact_entry, ensure_ascii=False, indent=1),
        "```",
        "",
        "## 2. gpt_pro_manifest.json note append (per matched problem id)",
        "",
        "Match staged solution files to canonical problem ids, then append one",
        "sentence per id to the problem's `note`, and update its `answer` pointer",
        "if the staged file is a stronger disposal than the current answer.",
        "",
        "## 3. gate_calibration_log.md row template",
        "",
        "| <date> intake | <package-name> absorption gate | right | <what the "
        "package's verifiers claim; what was replayed repo-side; what was "
        "quarantined or superseded> | Keep: <the one-line rule this intake "
        "codifies> |",
        "",
        "## 4. Duplicates (skip re-registering these)",
        "",
    ]
    for rel, wheres in sorted(record["duplicates"].items()):
        lines.append(f"- {rel} already at {', '.join(wheres)}")
    if not record["duplicates"]:
        lines.append("(none)")
    lines.append("")
    (dst / "REGISTER.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", type=Path, required=True, help="chat-export folder")
    ap.add_argument("--line", required=True, help="manuscript line dir name (e.g. yang_md_decoupling_marl)")
    ap.add_argument("--slug", default=None, help="staging dir name (default: real-root basename)")
    ap.add_argument("--root", type=Path, default=None,
                    help="repo root override (default: self-located); used by tests")
    ap.add_argument("--dry-run", action="store_true", help="report only, copy nothing")
    args = ap.parse_args(argv)

    root = (args.root or repo_root()).resolve()
    line_dir = root / "tmp" / args.line
    if not (root / "paper" / args.line / "LINE.md").is_file():
        print(f"ERROR: unknown line dir: {args.line}", file=sys.stderr)
        return 2

    try:
        src_root = locate_real_root(args.src.expanduser().resolve())
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if not any(src_root.rglob("*")):
        print(f"ERROR: package is empty: {src_root}", file=sys.stderr)
        return 2

    slug = args.slug or src_root.name
    dst = line_dir / slug
    if dst.exists():
        print(f"ERROR: staging dir exists (create-only): {dst}", file=sys.stderr)
        return 2

    files_before = [f for f in src_root.rglob("*") if f.is_file()]
    print(f"src: {src_root}")
    print(f"files: {len(files_before)}")
    if args.dry_run:
        print(f"would stage to: {dst}  (dry-run, nothing written)")
        return 0

    dst.mkdir(parents=True, exist_ok=False)
    name_map = stage_package(src_root, dst)
    staged = {rel: (dst / rel) for rel in sorted(
        p.relative_to(dst).as_posix() for p in dst.rglob("*") if p.is_file())}

    sums: dict = {"present": False, "checked": 0, "matched": [], "unmatched": []}
    sums_path = dst / "SHA256SUMS"
    if sums_path.is_file():
        sums["present"] = True
        entries = parse_sums(sums_path.read_text(encoding="utf-8", errors="replace"))
        sums = {**{"present": True}, **verify_sums(staged, entries)}

    dups = duplicate_scan(staged, line_dir, dst)
    record = build_record(args, src_root, dst, name_map, sums, dups, staged)
    (dst / "intake_record.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    register_snippets(record, dst, args, root)

    print(f"staged: {dst}")
    print(f"files: {len(staged)}  duplicates: {len(dups)}  "
          f"renamed: {len(name_map)}")
    if sums["present"]:
        print(f"SHA256SUMS: {len(sums['matched'])}/{sums['checked']} matched, "
              f"{len(sums['unmatched'])} unmatched")
    for u in sums["unmatched"]:
        print(f"  [UNMATCHED] {u['expected_path']}", file=sys.stderr)
    print(f"registration snippets: {dst / 'REGISTER.md'}")
    return 1 if sums["unmatched"] or (sums["present"] and not sums["matched"]) else 0


if __name__ == "__main__":
    sys.exit(main())
