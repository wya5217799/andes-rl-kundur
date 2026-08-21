"""Windows-safe tests for the R410 message-contrast repair runner.

Binds the round identity, the single-factor arm factory, and the source
manifest without touching ANDES.  WSL measure-capacity/rehearse/prepare/
train/evaluate/classify are covered by the runner lifecycle itself.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

runner = importlib.import_module("run_r410_message_repair")


def test_round_identity_is_r410():
    assert runner.ROUND_ID == "R410"
    assert runner.OUT == ROOT / "results/research_loop/r410_message_repair"
    assert runner.SEAL == ROOT / "memory/rounds/R410/formal_seal.json"
    assert runner.PLAN == ROOT / "memory/rounds/R410/plan.md"
    assert runner.CAPACITY == ROOT / "memory/rounds/R410/capacity_evidence.json"
    assert runner.REHEARSAL == ROOT / "memory/rounds/R410/rehearsal.json"


def test_agent_factory_applies_mask_only_to_no_message_arm():
    from andes_rl_kundur.agents.cd_matd3 import CDMATD3, YangScalarTD3

    scalar = runner._agent_for("yang_scalar_td3", "cpu")
    no_message = runner._agent_for("cd_matd3_no_message", "cpu")
    message = runner._agent_for("cd_matd3_message", "cpu")
    assert isinstance(scalar, YangScalarTD3)
    assert isinstance(no_message, CDMATD3)
    assert isinstance(message, CDMATD3)
    assert scalar.actor_neighbour_mask is False
    assert no_message.actor_neighbour_mask is True
    assert message.actor_neighbour_mask is False


def test_source_manifest_includes_r410_runner_and_learner():
    sources = runner._source_manifest()
    assert "learner" in sources
    assert sources["runner"]["path"] == "scripts/run_r410_message_repair.py"
    assert sources["runner_tests"]["path"] == "tests/test_run_r410_message_repair.py"
