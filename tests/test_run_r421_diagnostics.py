"""Directed tests for the R421 diagnostics runner.

Windows-safe: agent factory, diagnostic field set, contract shape, and the
shard-id parsing.  The WSL-only lifecycle runs through the scratch launcher
in the sealed round itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import run_r421_diagnostics as runner  # noqa: E402
from andes_rl_kundur.agents.cd_matd3_diagnostics import (  # noqa: E402
    DiagnosticCDMATD3,
)


def test_agent_factory() -> None:
    message = runner._agent_for("cd_matd3_message", "cpu")
    assert isinstance(message, DiagnosticCDMATD3)
    assert message.actor_neighbour_mask is False
    no_message = runner._agent_for("cd_matd3_no_message", "cpu")
    assert isinstance(no_message, DiagnosticCDMATD3)
    assert no_message.actor_neighbour_mask is True
    with pytest.raises(ValueError):
        runner._agent_for("yang_scalar_td3", "cpu")
    with pytest.raises(ValueError):
        runner._agent_for("unknown", "cpu")


def test_diagnostic_fields_registered() -> None:
    assert runner.DIAGNOSTIC_FIELDS[0] == "update_count"
    for field in (
        "critic_loss",
        "bellman_residual_mean",
        "critic_grad_norm_mean",
        "actor_grad_norm_mean",
        "td_error_std",
        "sampled_state_variance_mean",
    ):
        assert field in runner.DIAGNOSTIC_FIELDS


def test_contract_shape() -> None:
    contract = runner.build_contract()
    assert list(contract["training_seeds"]) == [401, 402, 403]
    assert contract["training_contract"]["total_interaction_steps"] == 43200
    assert list(runner.DIAGNOSTIC_ARMS) == [
        "cd_matd3_no_message",
        "cd_matd3_message",
    ]
