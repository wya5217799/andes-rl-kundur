"""Tests for reserve_claim.py — atomic CLM-NNNN minting."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from reserve_claim import (  # noqa: E402
    _max_existing_clm,
    reserve_next_claim,
)


def test_max_existing_clm_empty_dir_returns_zero(tmp_path: Path) -> None:
    assert _max_existing_clm(tmp_path) == 0


def test_max_existing_clm_finds_highest(tmp_path: Path) -> None:
    for name in ("CLM-0005.md", "CLM-0010.md", "CLM-0015.md"):
        (tmp_path / name).write_text("---\n---\n")
    assert _max_existing_clm(tmp_path) == 15


def test_max_existing_clm_ignores_non_claim_files(tmp_path: Path) -> None:
    (tmp_path / "CLM-0005.md").write_text("---\n---\n")
    (tmp_path / "_TEMPLATE.md").write_text("---\n---\n")
    (tmp_path / "README.md").write_text("---\n---\n")
    (tmp_path / "notes.txt").write_text("anything")
    assert _max_existing_clm(tmp_path) == 5


def test_reserve_first_claim_at_stride(tmp_path: Path) -> None:
    cid = reserve_next_claim(tmp_path, stride=5)
    assert cid == "CLM-0005"
    assert (tmp_path / "CLM-0005.md").exists()


def test_reserve_increments_by_stride(tmp_path: Path) -> None:
    (tmp_path / "CLM-0430.md").write_text("---\n---\n")
    cid = reserve_next_claim(tmp_path, stride=5)
    assert cid == "CLM-0435"


def test_reserve_snaps_to_stride_lattice(tmp_path: Path) -> None:
    """If a contiguous (stride=1) reservation interrupted the
    5-step lattice, a subsequent stride=5 call should snap back to
    the next multiple of 5, not just add 5."""
    (tmp_path / "CLM-0431.md").write_text("---\n---\n")  # off-grid
    cid = reserve_next_claim(tmp_path, stride=5)
    # max=431, +5=436, snap-to-5 -> 440 (preserves the lattice)
    assert cid == "CLM-0440"


def test_reserve_contiguous_stride_one(tmp_path: Path) -> None:
    (tmp_path / "CLM-0430.md").write_text("---\n---\n")
    cid = reserve_next_claim(tmp_path, stride=1)
    assert cid == "CLM-0431"


def test_reserve_writes_valid_frontmatter_stub(tmp_path: Path) -> None:
    cid = reserve_next_claim(tmp_path, stride=5, round_id="R251",
                             claim_type="correction")
    body = (tmp_path / f"{cid}.md").read_text(encoding="utf-8")
    # frontmatter present
    assert body.startswith("---\n")
    assert "\n---\n" in body
    # ID + round + type pre-filled
    assert f"id: {cid}" in body
    assert "round: R251" in body
    assert "type: correction" in body
    # correction defaults to trust V per validate.py rules
    assert "trust: V" in body


def test_reserve_rejects_bad_stride(tmp_path: Path) -> None:
    try:
        reserve_next_claim(tmp_path, stride=0)
    except ValueError as e:
        assert "stride" in str(e).lower()
    else:
        raise AssertionError("expected ValueError for stride=0")


def test_reserve_rejects_bad_claim_type(tmp_path: Path) -> None:
    try:
        reserve_next_claim(tmp_path, claim_type="bogus")
    except ValueError as e:
        assert "claim_type" in str(e)
    else:
        raise AssertionError("expected ValueError for bad claim_type")


def test_reserve_raises_on_missing_dir(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    try:
        reserve_next_claim(missing)
    except FileNotFoundError as e:
        assert "claims_dir" in str(e)
    else:
        raise AssertionError("expected FileNotFoundError")
