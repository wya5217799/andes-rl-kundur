"""Git attributes must preserve byte-stable research seals."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _eol_attribute(path: str) -> str:
    result = subprocess.run(
        ["git", "check-attr", "eol", "--", path],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def test_hash_bound_round_artifacts_are_forced_to_lf() -> None:
    assert _eol_attribute(
        "memory/rounds/R286/weak_tie_seal.json"
    ).endswith(": lf")
    assert _eol_attribute(
        "memory/rounds/R286/weak_tie_seal.json.sha256"
    ).endswith(": lf")
