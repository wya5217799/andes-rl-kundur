"""Adapter-level tests for the R361 message-extended gate adapter."""

from __future__ import annotations

from scripts.run_r361_neighbour_message_residual import (
    build_contract,
    parent_paths,
    source_paths,
)

from andes_rl_kundur.control.neighbour_message_residual import (
    MESSAGE_CONTROLLER_FAMILY,
    MESSAGE_EXTENDED_OBSERVATION_DIMENSION,
    ONE_HOP_NEIGHBOUR_MESSAGES,
)


def test_contract_freezes_exactly_four_tuning_free_members() -> None:
    contract = build_contract()
    family = contract["controller_family"]
    assert family["members"] == sorted(MESSAGE_CONTROLLER_FAMILY)
    assert family["tuning_executed"] is False
    for member in family["members"]:
        assert family[member]["sweep"] is False
    assert family["selection_semantics"] == "pre-registered OR over all members"
    assert contract["authorization"]["training"] is False
    assert contract["authorization"]["simulation"] is False


def test_contract_matches_r360_information_and_physical_contract() -> None:
    contract = build_contract()
    information = contract["information"]
    assert information["own_fields"] == 15
    assert information["continuous_fields_per_actor"] == MESSAGE_EXTENDED_OBSERVATION_DIMENSION
    assert information["continuous_fields_per_actor"] == 23
    assert information["neighbour_message_fields"] == 4
    assert information["neighbours_per_edge"] == 2
    assert information["startup_zero_steps"] == 2
    assert "achieved_power" in information["forbidden_fields"]
    assert "oracle_values" in information["forbidden_fields"]
    assert "other_edge_actions" in information["forbidden_fields"]
    assert "neighbour_commands" in information["forbidden_fields"]
    assert "neighbour_edge_flows" in information["forbidden_fields"]
    assert contract["inventory"]["development_pairs"] == 16
    assert contract["inventory"]["positive_development_targets"] == 10


def test_contract_freezes_one_hop_neighbour_table() -> None:
    contract = build_contract()
    table = contract["information"]["one_hop_neighbour_table"]
    assert table == {
        str(edge): list(message) for edge, message in ONE_HOP_NEIGHBOUR_MESSAGES.items()
    }


def test_source_and_parent_closures_are_complete() -> None:
    sources = source_paths(include_rehearsal=False)
    assert "plan" in sources
    assert "question" in sources
    assert "capacity" in sources
    assert "adapter" in sources
    assert "probe" in sources
    assert "controller_src" in sources
    assert "r360_adapter" in sources
    assert "r359_adapter" in sources
    assert "r353_adapter" in sources
    parents = parent_paths()
    assert "r358_analysis" in parents
    assert "r359_analysis" in parents
    assert "r360_analysis" in parents
    assert "r360_claim" in parents
