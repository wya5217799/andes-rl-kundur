"""Claim ledger validator. Runs 3 hard rules + 2 warnings."""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def load_claims(claims_dir: Path) -> dict[str, dict[str, Any]]:
    """Load every CLM-*.md frontmatter into a dict keyed by id."""
    claims: dict[str, dict[str, Any]] = {}
    for path in sorted(claims_dir.glob("CLM-*.md")):
        text = path.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(text)
        if not match:
            raise ValueError(f"{path.name}: no YAML frontmatter")
        meta = yaml.safe_load(match.group(1)) or {}
        meta["_path"] = path
        meta.setdefault("superseded_by", [])
        meta.setdefault("supersedes", [])
        cid = meta["id"]
        if cid in claims:
            raise ValueError(
                f"duplicate id {cid} in {path.name} and "
                f"{claims[cid]['_path'].name}"
            )
        claims[cid] = meta
    return claims


def validate_rules(claims: dict[str, dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Hard rules go to errors; soft checks to warnings."""
    errors: list[str] = []
    warnings: list[str] = []

    # Rule 1: id uniqueness — guards against same id value appearing under different
    # dict keys (possible when validate_rules is called outside the main() flow).
    seen_ids: dict[str, str] = {}
    for key, claim in claims.items():
        cid = claim["id"]
        if cid in seen_ids and seen_ids[cid] != key:
            errors.append(f"duplicate id {cid} in key {key} and key {seen_ids[cid]}")
        seen_ids[cid] = key

    # Rule 2: supersedes target must exist
    for claim in claims.values():
        for target in claim.get("supersedes", []) or []:
            if target not in claims:
                errors.append(
                    f"{claim['id']}.supersedes references {target} which does not exist"
                )

    # Rule 3: status: current ↔ superseded_by must be empty
    for claim in claims.values():
        if claim.get("status") == "current" and claim.get("superseded_by"):
            errors.append(
                f"{claim['id']} has status: current but non-empty "
                f"superseded_by: {claim['superseded_by']}"
            )

    # Warning A: forward/back edge symmetry
    for claim in claims.values():
        for target in claim.get("supersedes", []) or []:
            if target not in claims:
                continue
            back = claims[target].get("superseded_by", []) or []
            if claim["id"] not in back:
                warnings.append(
                    f"asymmetric edge: {claim['id']}.supersedes lists {target}, "
                    f"but {target}.superseded_by missing {claim['id']}"
                )

    # Warning B: trust: V requires non-empty provenance
    for claim in claims.values():
        if claim.get("trust") == "V" and not claim.get("provenance"):
            warnings.append(f"{claim['id']} has trust: V but empty provenance")

    return errors, warnings


def _rewrite_frontmatter(path: Path, updates: dict[str, Any]) -> None:
    """Rewrite the YAML block of a claim file, preserving body and key order
    where possible."""
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"{path.name}: no frontmatter to rewrite")
    meta = yaml.safe_load(match.group(1)) or {}
    meta.update(updates)
    new_block = yaml.safe_dump(
        meta, sort_keys=False, allow_unicode=True, default_flow_style=False
    ).strip()
    body = text[match.end():]
    path.write_text(f"---\n{new_block}\n---\n{body}", encoding="utf-8")


def fix_back_edges(claims: dict[str, dict[str, Any]], *, write: bool) -> list[str]:
    """For every X with supersedes: [Y, ...], ensure Y.superseded_by includes X
    and Y.status == 'superseded'. Returns list of changes made."""
    changes: list[str] = []
    for claim in claims.values():
        for target_id in claim.get("supersedes", []) or []:
            target = claims.get(target_id)
            if target is None:
                continue
            back = list(target.get("superseded_by", []) or [])
            need_back = claim["id"] not in back
            need_status = target.get("status") != "superseded"
            if not (need_back or need_status):
                continue
            if need_back:
                back.append(claim["id"])
            updates = {"superseded_by": back, "status": "superseded"}
            changes.append(
                f"{target_id}: superseded_by += {claim['id']}, status -> superseded"
            )
            if write:
                _rewrite_frontmatter(target["_path"], updates)
                target.update(updates)
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Claim ledger validator")
    parser.add_argument(
        "--claims-dir", type=Path,
        default=Path(__file__).parent.parent / "claims",
        help="path to memory/claims/",
    )
    parser.add_argument("--fix", action="store_true",
                        help="auto-write missing back edges and flip status")
    args = parser.parse_args()

    claims = load_claims(args.claims_dir)
    if args.fix:
        changes = fix_back_edges(claims, write=True)
        for c in changes:
            print(f"FIX: {c}")
        # reload after writing
        claims = load_claims(args.claims_dir)

    errors, warnings = validate_rules(claims)
    for w in warnings:
        print(f"WARN: {w}")
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    if errors:
        return 1
    print(f"OK: {len(claims)} claims, {len(warnings)} warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
