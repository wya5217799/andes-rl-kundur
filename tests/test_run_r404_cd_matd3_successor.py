"""Offline checks for the science-identical R404 correction wrapper."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_probe(expression: str) -> object:
    code = (
        "import json,sys;"
        "sys.path[:0]=['scripts','src','.'];"
        "import run_r404_cd_matd3_successor as runner;"
        f"print(json.dumps({expression}, allow_nan=False))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_parent_contract_is_byte_identical_and_bound() -> None:
    result = _run_probe(
        "{'parent_valid': runner._parent_valid(), "
        "'contract_hash': runner.contract_sha256("
        "runner.base.build_successor_contract())}"
    )
    assert result == {
        "parent_valid": True,
        "contract_hash": "dad9b0e5775982c67c478acb178ccfc1befc05ea081c3aed5aea95309b5bae02",
    }


def test_deep_rehearsal_crosses_both_update_states_with_finite_json() -> None:
    result = _run_probe("runner.deep_diagnostic_rehearsal()")
    assert result["critic_only"]["policy_updated"] == 0.0
    assert result["actor_update"]["policy_updated"] == 1.0
    assert result["batch_size"] == 256


def test_wrapper_binds_new_round_paths_without_changing_science() -> None:
    source = (ROOT / "scripts/run_r404_cd_matd3_successor.py").read_text(
        encoding="utf-8"
    )
    for required in (
        'ROUND_ID = "R404"',
        'memory/rounds/R404/plan.md',
        'tmp/r404_cd_matd3_successor',
        'PARENT_CONTRACT_SHA256',
        'base.build_successor_contract()',
    ):
        assert required in source
