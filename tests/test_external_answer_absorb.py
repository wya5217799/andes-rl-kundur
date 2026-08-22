"""Directed tests for memory/tools/external_answer_absorb.py.

Covers the three session lessons the tool codifies:
- nested same-name folder hides the real package root;
- non-ASCII filenames break the read tool / hash checks (ASCII rename + map);
- SHA256SUMS entries are matched by hash when the path does not resolve
  (NFC/NFD filename mismatch), and duplicates against already-staged
  packages are classified instead of re-registered.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "memory" / "tools" / "external_answer_absorb.py"
sys.path.insert(0, str(TOOL.parent))
import external_answer_absorb as eaa  # noqa: E402


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_package(tmp_path: Path) -> tuple[Path, Path, bytes]:
    """Synthetic chat export: outer dir wraps a nested same-name root."""
    outer = tmp_path / "chat_export"
    inner = outer / "chat_export"
    inner.mkdir(parents=True)
    (inner / "README.md").write_text("# hello\n", encoding="utf-8")
    # Chinese filename (the read tool + hash checks broke on these in-session)
    zh = "U1_U9_数学审计.md"
    zh_bytes = "数学审计内容".encode("utf-8")
    (inner / zh).write_bytes(zh_bytes)
    sub = inner / "sub"
    sub.mkdir()
    dup_bytes = b"same-content-payload-123"
    (sub / "data.bin").write_bytes(dup_bytes)
    return outer, inner, dup_bytes


def _make_repo(tmp_path: Path, line: str = "yang_md_decoupling_marl") -> Path:
    root = tmp_path / "repo"
    (root / "paper" / line).mkdir(parents=True)
    (root / "paper" / line / "LINE.md").write_text("---\nline_id: x\n---\n", encoding="utf-8")
    (root / "tmp" / line).mkdir(parents=True)
    return root


def test_nested_root_ascii_rename_and_sums(tmp_path):
    outer, inner, _dup = _make_package(tmp_path)
    root = _make_repo(tmp_path)
    # Sums with a path that will not resolve (name differs) -> must hash-match.
    sums = f"{_sha('数学审计内容'.encode('utf-8'))}  ./U1_U9_OTHER_NAME.md\n"
    (inner / "SHA256SUMS").write_text(sums, encoding="utf-8")

    rc = eaa.main(["--src", str(outer), "--line", "yang_md_decoupling_marl",
                   "--root", str(root), "--slug", "pkg_test"])
    assert rc == 0
    staged = root / "tmp" / "yang_md_decoupling_marl" / "pkg_test"
    record = json.loads((staged / "intake_record.json").read_text(encoding="utf-8"))
    assert record["ascii_name_map"]  # the Chinese file was renamed
    assert "U1_U9_OTHER_NAME.md" not in [f["rel"] for f in record["files"]]
    assert record["sha256sums"]["present"] is True
    assert record["sha256sums"]["unmatched"] == []
    assert any(m["status"] == "hash-match" for m in record["sha256sums"]["matched"])
    assert (staged / "REGISTER.md").is_file()
    # nested root resolved: staged files carry no doubled basename
    assert not (staged / "chat_export").exists()


def test_duplicate_scan_and_create_only(tmp_path):
    outer, inner, dup_bytes = _make_package(tmp_path)
    root = _make_repo(tmp_path)
    # Pre-stage an earlier package containing one identical payload file.
    prior = root / "tmp" / "yang_md_decoupling_marl" / "gpt_pro_prior_test"
    (prior / "sub").mkdir(parents=True)
    (prior / "sub" / "data.bin").write_bytes(dup_bytes)

    rc = eaa.main(["--src", str(outer), "--line", "yang_md_decoupling_marl",
                   "--root", str(root), "--slug", "pkg_dup"])
    assert rc == 0
    record = json.loads(
        (root / "tmp" / "yang_md_decoupling_marl" / "pkg_dup" / "intake_record.json")
        .read_text(encoding="utf-8"))
    dup_rel = next(r for r in record["duplicates"])
    assert dup_rel.endswith("data.bin")
    assert "gpt_pro_prior_test" in record["duplicates"][dup_rel][0]
    # create-only: staging the same slug again must fail
    rc2 = eaa.main(["--src", str(outer), "--line", "yang_md_decoupling_marl",
                    "--root", str(root), "--slug", "pkg_dup"])
    assert rc2 == 2


def test_dry_run_and_unknown_line(tmp_path):
    outer, _inner, _dup = _make_package(tmp_path)
    root = _make_repo(tmp_path)
    rc = eaa.main(["--src", str(outer), "--line", "yang_md_decoupling_marl",
                   "--root", str(root), "--dry-run"])
    assert rc == 0
    assert not (root / "tmp" / "yang_md_decoupling_marl" / "chat_export").exists()
    rc2 = eaa.main(["--src", str(outer), "--line", "no_such_line", "--root", str(root)])
    assert rc2 == 2
