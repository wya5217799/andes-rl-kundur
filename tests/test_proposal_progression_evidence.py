from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER = REPO_ROOT / "研究计划" / "proposal" / "figures" / "make_progression.py"


def test_proposal_progression_manifest_matches_its_claim_sources() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import runpy, sys; "
                "module = runpy.run_path(sys.argv[1]); "
                "module['load_evidence']()"
            ),
            str(BUILDER),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stdout + result.stderr
