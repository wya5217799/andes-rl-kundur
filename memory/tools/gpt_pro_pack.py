"""Pack GPT Pro math problems + related data into a self-contained zip.

Motivation: the owner repeatedly asks to "extract the math problems that need
GPT Pro + related data + zip". This was done by hand before (e.g. the 2026-08-19
brief + gpt_pro_data_*.zip). This CLI turns the housekeeping pattern into a
stable tool; the inventory lives in gpt_pro_manifest.json (single source of
truth for which problems exist, their status, and their related data).

Usage:

    # default: package problems with status open + partial
    python memory/tools/gpt_pro_pack.py

    # package everything (open + partial + answered + superseded)
    python memory/tools/gpt_pro_pack.py --all

    # explicit status filter
    python memory/tools/gpt_pro_pack.py --status open

    # one manuscript line only (combine with --all to include answered)
    python memory/tools/gpt_pro_pack.py --line yang_md_decoupling_marl --all

    # one or more specific problems
    python memory/tools/gpt_pro_pack.py --id residual-headroom --id icems2026-minimal-change

    # preview only (no zip written)
    python memory/tools/gpt_pro_pack.py --list
    python memory/tools/gpt_pro_pack.py --dry-run

    # override output zip / manifest
    python memory/tools/gpt_pro_pack.py --output tmp/out.zip
    python memory/tools/gpt_pro_pack.py --manifest other_manifest.json

Output zip layout: README.md (index grouped by problem), manifest.json
(provenance: status, per-file sha256, missing list), SHA256SUMS (GNU coreutils
style), then every included file at its repo-relative path.

Failure modes:
- Missing manifest -> exit 2 with a message.
- A problem/data file that no longer exists is recorded as missing and reported
  to stderr; the tool still writes the zip (graceful, never crashes on a stale
  pointer) but exits 1 so the caller can see something was absent.
- Absolute paths or ".." in a manifest path are rejected (escape guard).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import zipfile
from pathlib import Path

TOOL_NAME = "gpt_pro_pack"
VALID_STATUS = {"open", "partial", "answered", "superseded"}


def repo_root() -> Path:
    """Repository root, independent of cwd (self-locating)."""
    return Path(__file__).resolve().parents[2]


def load_manifest(manifest_path: Path) -> dict:
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "problems" not in raw:
        raise ValueError(f"manifest missing 'problems': {manifest_path}")
    for p in raw["problems"]:
        if p.get("status") not in VALID_STATUS:
            raise ValueError(
                f"problem {p.get('id')!r} has bad status {p.get('status')!r}; "
                f"expected one of {sorted(VALID_STATUS)}"
            )
    return raw


def _safe_repo_path(raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"path must be repo-relative, got {raw!r}")
    return p


def expand_paths(raw_paths: list[str], root: Path) -> tuple[list[Path], list[str]]:
    """Expand file/dir repo-relative paths to a sorted, deduped list of files.

    Returns (files, missing_raw) where missing_raw lists the raw strings that
    resolved to nothing (file absent / dir absent / dir empty).
    """
    files: set[Path] = set()
    missing: list[str] = []
    for raw in raw_paths:
        rel = _safe_repo_path(raw)
        path = root / rel
        if path.is_file():
            files.add(path)
        elif path.is_dir():
            found = [f for f in path.rglob("*") if f.is_file()]
            if not found:
                missing.append(raw)
            files.update(found)
        else:
            missing.append(raw)
    ordered = sorted(files, key=lambda f: f.as_posix())
    return ordered, missing


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def select_problems(
    manifest: dict,
    *,
    status_filter: list[str] | None,
    ids: list[str] | None,
    include_all: bool,
    line: str | None = None,
) -> list[dict]:
    if include_all:
        chosen = list(manifest["problems"])
    elif ids:
        by_id = {p["id"]: p for p in manifest["problems"]}
        chosen = []
        for i in ids:
            if i not in by_id:
                raise ValueError(f"unknown problem id {i!r}")
            chosen.append(by_id[i])
    else:
        statuses = set(status_filter or manifest.get("default_status_filter") or ["open"])
        chosen = [p for p in manifest["problems"] if p["status"] in statuses]
    if line:
        chosen = [p for p in chosen if p.get("manuscript_line") == line]
    return chosen


def build_package(
    problems: list[dict],
    *,
    root: Path,
    output: Path,
    status_label: str,
    now: dt.datetime,
) -> dict:
    """Write the zip. Returns a summary dict (never raises on missing files)."""
    # (arcname, local_path) pairs; arcname is the POSIX repo-relative path.
    included: list[tuple[str, Path]] = []
    seen: set[str] = set()
    missing: dict[str, list[str]] = {}

    for p in problems:
        pid = p["id"]
        raw_paths = list(p.get("problem", [])) + list(p.get("related_data", []))
        files, miss = expand_paths(raw_paths, root)
        if miss:
            missing[pid] = miss
        for f in files:
            arc = f.relative_to(root).as_posix()
            if arc in seen:
                continue
            seen.add(arc)
            included.append((arc, f))

    included.sort(key=lambda t: t[0])

    # Build provenance records before writing the zip.
    files_sha: dict[str, str] = {}
    for arc, f in included:
        files_sha[arc] = _sha256(f)

    per_problem: list[dict] = []
    for p in problems:
        own = []
        for raw in list(p.get("problem", [])) + list(p.get("related_data", [])):
            for arc, _ in included:
                if _arc_matches(raw, arc):
                    own.append(arc)
        per_problem.append({
            "id": p["id"],
            "title": p["title"],
            "status": p["status"],
            "manuscript_line": p.get("manuscript_line"),
            "answer": p.get("answer"),
            "note": p.get("note"),
            "files": sorted(set(own)),
            "missing": sorted(missing.get(p["id"], [])),
        })

    out_manifest = {
        "schema_version": 1,
        "tool": TOOL_NAME,
        "generated": now.isoformat(timespec="seconds"),
        "status_filter": status_label,
        "problems": per_problem,
        "files": {arc: files_sha[arc] for arc, _ in included},
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.md", _render_readme(per_problem, now))
        zf.writestr("manifest.json", json.dumps(out_manifest, indent=2, ensure_ascii=False))
        zf.writestr("SHA256SUMS", "".join(f"{files_sha[arc]}  {arc}\n" for arc, _ in included))
        for arc, f in included:
            zf.write(f, arcname=arc)

    return {
        "output": output,
        "included_count": len(included),
        "missing_count": sum(len(m) for m in missing.values()),
        "missing": missing,
        "problems": per_problem,
    }


def _arc_matches(raw: str, arc: str) -> bool:
    rel = Path(raw).as_posix()
    if rel == arc:
        return True
    return arc.startswith(rel.rstrip("/") + "/")


def _render_readme(per_problem: list[dict], now: dt.datetime) -> str:
    lines = [
        "# GPT Pro math problem package",
        "",
        f"Generated: {now.isoformat(timespec='seconds')}",
        "Tool: memory/tools/gpt_pro_pack.py (see manifest.json for sha256 provenance).",
        "",
        "Self-contained package of math/theory problems for an external solver",
        "(GPT Pro / theory audit). Hand the problem files + related data to the",
        "solver; every number is repository-sealed or a design input, never invented.",
        "",
        "## Problems in this package",
        "",
    ]
    for p in per_problem:
        lines.append(f"### {p['id']}  [{p['status']}]")
        lines.append(f"- title: {p['title']}")
        if p.get("manuscript_line"):
            lines.append(f"- manuscript_line: {p['manuscript_line']}")
        if p.get("note"):
            lines.append(f"- note: {p['note']}")
        if p.get("answer"):
            lines.append(f"- answer pointer (NOT included here): {p['answer']}")
        if p.get("files"):
            lines.append("- files:")
            for f in p["files"]:
                lines.append(f"  - {f}")
        if p.get("missing"):
            lines.append("- missing (NOT included, fix the manifest pointer):")
            for m in p["missing"]:
                lines.append(f"  - {m}")
        lines.append("")
    lines += [
        "## Intake contract",
        "",
        "Answers are design aids, not authority. Route them through the project",
        "external-theory intake (algebra / mechanism prediction / paper-grade",
        "proposition) before any feed or manuscript use; see",
        "skills/kundur-round/references/external-theory-intake.md.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path,
                        default=Path(__file__).resolve().parent / "gpt_pro_manifest.json")
    parser.add_argument("--output", type=Path, default=None,
                        help="zip path (default tmp/gpt_pro_math_pack_<date>.zip)")
    parser.add_argument("--status", default=None,
                        help="comma-separated status filter (open,partial,answered,superseded)")
    parser.add_argument("--id", action="append", dest="ids", default=None,
                        help="specific problem id (repeatable)")
    parser.add_argument("--line", default=None,
                        help="manuscript_line filter (e.g. yang_md_decoupling_marl)")
    parser.add_argument("--all", action="store_true", dest="include_all")
    parser.add_argument("--list", action="store_true", help="print selected problems only")
    parser.add_argument("--dry-run", action="store_true",
                        help="print full file list + missing, write no zip")
    args = parser.parse_args(argv)

    root = repo_root()
    try:
        manifest = load_manifest(args.manifest)
        status_filter = args.status.split(",") if args.status else None
        if status_filter:
            bad = set(status_filter) - VALID_STATUS
            if bad:
                raise ValueError(f"unknown status {sorted(bad)}; expected {sorted(VALID_STATUS)}")
        problems = select_problems(
            manifest,
            status_filter=status_filter,
            ids=args.ids,
            include_all=args.include_all,
            line=args.line,
        )
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if not problems:
        print("No problems match the filter.")
        return 0

    label = "ALL" if args.include_all else ",".join(
        status_filter or manifest.get("default_status_filter") or ["open"]
    )

    if args.list:
        for p in problems:
            print(f"{p['id']}\t{p['status']}\t{p['title']}")
        return 0

    if args.dry_run:
        for p in problems:
            files, miss = expand_paths(
                list(p.get("problem", [])) + list(p.get("related_data", [])), root
            )
            print(f"[{p['id']}] {p['title']}  ({p['status']})")
            for f in files:
                print(f"  + {f.relative_to(root).as_posix()}")
            for m in miss:
                print(f"  [MISSING] {m}")
        return 0

    now = dt.datetime.now()
    output = args.output or (root / "tmp" / f"gpt_pro_math_pack_{now:%Y%m%d}.zip")
    summary = build_package(problems, root=root, output=output,
                            status_label=label, now=now)

    print(f"zip: {summary['output']}")
    print(f"included: {summary['included_count']} files, "
          f"missing: {summary['missing_count']} pointers")
    for pid, miss in summary["missing"].items():
        for m in miss:
            print(f"  [MISSING] {pid}: {m}", file=sys.stderr)
    return 1 if summary["missing_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
