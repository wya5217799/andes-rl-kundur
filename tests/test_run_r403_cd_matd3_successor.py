"""Offline contract tests for the R403 WSL successor adapter."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r403_cd_matd3_successor.py"


def test_source_manifest_is_complete_and_hashed() -> None:
    code = (
        "import json,sys;"
        "sys.path[:0]=['scripts','src','.'];"
        "import run_r403_cd_matd3_successor as runner;"
        "print(json.dumps(runner._source_manifest()))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads(completed.stdout)
    assert "runner" in manifest
    assert "learner" in manifest
    assert "gate" in manifest
    assert all(len(row["sha256"]) == 64 for row in manifest.values())


def test_authority_checks_bind_round_line_parent_and_output_absence() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    for required in (
        '"active_plan"',
        '"active_line"',
        '"parent_hash"',
        '"output_absence"',
        '"state: active"',
        '"manuscript_line: yang-md-decoupling-marl"',
        '"R403"',
    ):
        assert required in source
