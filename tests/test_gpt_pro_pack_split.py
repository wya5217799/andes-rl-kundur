"""Directed tests for gpt_pro_pack.py --max-size-mb (chat-upload split).

Session lesson: hand-made binary splits are unopenable (Windows + chat UI);
the split must be two standalone zips, each under the limit, built from
derived packaging manifests with related_data partitioned by size.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "memory" / "tools" / "gpt_pro_pack.py"
sys.path.insert(0, str(TOOL.parent))
import gpt_pro_pack as gpp  # noqa: E402

ROOT = gpp.repo_root()


def _write_random(path: Path, nbytes: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(os.urandom(nbytes))


def test_max_size_split_builds_two_standalone_zips():
    scratch = Path(tempfile.mkdtemp(prefix="gpt_pro_split_test_", dir=ROOT / "tmp"))
    try:
        big = scratch / "big"
        small = scratch / "small"
        _write_random(big / "payload.bin", 700_000)
        _write_random(small / "payload.bin", 400_000)
        manifest = {
            "schema_version": 1,
            "default_status_filter": ["open"],
            "problems": [
                {"id": "p1", "title": "one", "status": "open",
                 "problem": [], "related_data": [big.relative_to(ROOT).as_posix()]},
                {"id": "p2", "title": "two", "status": "open",
                 "problem": [], "related_data": [small.relative_to(ROOT).as_posix()]},
            ],
        }
        mp = scratch / "test_manifest.json"
        mp.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        out = scratch / "split_test.zip"

        rc = gpp.main(["--manifest", str(mp), "--all",
                       "--max-size-mb", "1", "--output", str(out)])
        assert rc == 0

        za = scratch / "split_test_a.zip"
        zb = scratch / "split_test_b.zip"
        assert za.is_file() and zb.is_file()
        for zpath in (za, zb):
            assert zpath.stat().st_size <= 1 * 1024 * 1024
            with zipfile.ZipFile(zpath) as zf:
                assert zf.testzip() is None  # each part is a valid archive
        # total payload preserved across the two parts
        total = 0
        for zpath in (za, zb):
            with zipfile.ZipFile(zpath) as zf:
                total += sum(i.file_size for i in zf.infolist() if i.filename.endswith("payload.bin"))
        assert total == 700_000 + 400_000
        # derived manifests were written next to the canonical tmp area
        assert (ROOT / "tmp" / "split_test_chat_a_manifest.json").is_file()
        assert (ROOT / "tmp" / "split_test_chat_b_manifest.json").is_file()
    finally:
        import shutil
        shutil.rmtree(scratch, ignore_errors=True)
        for suffix in ("_chat_a_manifest.json", "_chat_b_manifest.json"):
            p = ROOT / "tmp" / f"split_test{suffix}"
            if p.exists():
                p.unlink()
