#!/usr/bin/env python3
"""Verify source hashes and every SEALED_JSON evidence-register entry.

This checker deliberately separates direct evidence verification from derived
reconstruction. Run rebuild_evidence.py for a full independent ledger rebuild.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, sys
from pathlib import Path
from typing import Any


def ptr_get(obj: Any, pointer: str) -> Any:
    if pointer in ("", "/"):
        return obj
    cur=obj
    for token in pointer.lstrip("/").split("/"):
        token=token.replace("~1", "/").replace("~0", "~")
        cur=cur[int(token)] if isinstance(cur, list) else cur[token]
    return cur


def encode(v: Any) -> str:
    if isinstance(v, (dict, list, bool)) or v is None:
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    return repr(v) if isinstance(v, float) else str(v)


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_hashes(root: Path) -> tuple[int,list[str]]:
    manifest=root/"SHA256SUMS"
    if not manifest.exists():
        return 0,[f"missing source manifest: {manifest}"]
    ok=0; errors=[]
    for lineno,line in enumerate(manifest.read_text(encoding="utf-8").splitlines(),1):
        line=line.strip()
        if not line: continue
        try:
            digest, rel=line.split(None,1)
        except ValueError:
            errors.append(f"SHA256SUMS:{lineno}: malformed line")
            continue
        rel=rel.lstrip("* ")
        p=root/rel
        if not p.exists():
            errors.append(f"missing: {rel}")
            continue
        got=sha256(p)
        if got.lower()!=digest.lower():
            errors.append(f"hash mismatch: {rel}: expected {digest}, got {got}")
        else:
            ok+=1
    return ok,errors


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-root",type=Path,required=True,help="Extracted gpt_pro_math_pack_20260820 directory")
    ap.add_argument("--advisory-root",type=Path,default=Path(__file__).resolve().parents[1])
    args=ap.parse_args()
    source=args.source_root.resolve(); advisory=args.advisory_root.resolve()
    register=advisory/"evidence/evidence_register.csv"
    rows=list(csv.DictReader(register.open(encoding="utf-8",newline="")))

    hash_ok,errors=verify_hashes(source)
    json_cache:dict[Path,Any]={}
    sealed_ok=0; source_ok=0; hypothetical=0; derived=0
    for row in rows:
        eid=row["evidence_id"]; status=row["status"]
        if status=="SEALED_JSON":
            p=source/row["source_path"]
            if not p.exists():
                errors.append(f"{eid}: missing JSON {row['source_path']}")
                continue
            if p not in json_cache:
                try: json_cache[p]=json.loads(p.read_text(encoding="utf-8"))
                except Exception as exc:
                    errors.append(f"{eid}: cannot parse {p}: {exc}"); continue
            try: got=encode(ptr_get(json_cache[p],row["json_pointer_or_range"]))
            except Exception as exc:
                errors.append(f"{eid}: pointer error {row['json_pointer_or_range']}: {exc}"); continue
            if got!=row["value"]:
                errors.append(f"{eid}: value mismatch expected={row['value']!r} got={got!r}")
            else: sealed_ok+=1
        elif status=="PACKAGE_SOURCE_CODE":
            p=source/row["source_path"]
            if not p.exists():
                errors.append(f"{eid}: missing source {row['source_path']}")
            else:
                # Exact check where the register stores a literal source token.
                text=p.read_text(encoding="utf-8",errors="replace")
                if eid=="C1-S01" and '"formal_dual_certificate": False' not in text:
                    errors.append(f"{eid}: literal source token not found")
                else: source_ok+=1
        elif status=="HYPOTHETICAL": hypothetical+=1
        elif status=="DERIVED_FROM_SEALED_JSON": derived+=1
        else: errors.append(f"{eid}: unknown status {status}")

    result={
        "source_hashes_verified":hash_ok,
        "sealed_json_entries_verified":sealed_ok,
        "package_source_entries_checked":source_ok,
        "derived_entries_pending_rebuild_check":derived,
        "hypothetical_entries_declared":hypothetical,
        "errors":errors,
    }
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 1 if errors else 0

if __name__=="__main__":
    raise SystemExit(main())
