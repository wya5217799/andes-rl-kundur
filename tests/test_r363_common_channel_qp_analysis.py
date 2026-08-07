"""Adapter-level tests for the R363 common-channel gate adapter."""

from __future__ import annotations

from scripts.run_r363_common_channel_qp import (
    build_contract,
    parent_paths,
    source_paths,
)


def test_contract_freezes_four_channel_basis() -> None:
    contract = build_contract()
    common = contract["common_channel"]
    assert common["node_action_basis"] == "[ones(4), active_power_incidence()]"
    assert common["fleet_net_power_authority"] is True
    assert common["edge_channels_zero_sum"] is True
    assert common["tuning_executed"] is False
    assert contract["inventory"]["action_basis"] == "four-channel common-plus-three-edge"
    assert contract["inventory"]["r358_baseline_feasible_count"] == 10
    assert contract["authorization"]["training"] is False
    assert contract["authorization"]["simulation"] is False


def test_source_and_parent_closures_are_complete() -> None:
    sources = source_paths(include_rehearsal=False)
    assert "plan" in sources
    assert "question" in sources
    assert "capacity" in sources
    assert "adapter" in sources
    assert "probe" in sources
    assert "controller_src" in sources
    assert "r358_adapter" in sources
    assert "r358_probe" in sources
    parents = parent_paths()
    assert "r358_analysis" in parents
    assert "r358_claim" in parents
