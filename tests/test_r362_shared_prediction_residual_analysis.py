"""Adapter-level tests for the R362 shared-prediction gate adapter."""

from __future__ import annotations

from scripts.run_r362_shared_prediction_residual import (
    build_contract,
    parent_paths,
    source_paths,
)

from andes_rl_kundur.control.neighbour_message_residual import (
    ONE_HOP_NEIGHBOUR_MESSAGES,
)
from andes_rl_kundur.control.shared_prediction_residual import (
    PREDICTION_STEPS,
    SHARED_PREDICTION_OBSERVATION_DIMENSION,
)
from probes.r362_shared_prediction_residual import SHARED_PREDICTION_FAMILY


def test_contract_freezes_exactly_four_tuning_free_members() -> None:
    contract = build_contract()
    family = contract["controller_family"]
    assert family["members"] == sorted(SHARED_PREDICTION_FAMILY)
    assert family["tuning_executed"] is False
    for member in family["members"]:
        assert family[member]["sweep"] is False
    assert family["selection_semantics"] == "pre-registered OR over all members"
    assert contract["authorization"]["training"] is False
    assert contract["authorization"]["simulation"] is False


def test_contract_freezes_shared_prediction_generator() -> None:
    contract = build_contract()
    information = contract["information"]
    assert information["own_fields"] == 15
    assert information["continuous_fields_per_actor"] == SHARED_PREDICTION_OBSERVATION_DIMENSION
    assert information["continuous_fields_per_actor"] == 23
    assert information["prediction_message_fields"] == PREDICTION_STEPS
    assert information["prediction_steps"] == PREDICTION_STEPS
    assert information["neighbours_per_edge"] == 2
    assert information["startup_zero_steps"] == 2
    assert "achieved_power" in information["forbidden_fields"]
    assert "oracle_values" in information["forbidden_fields"]
    assert "future_realized_values" in information["forbidden_fields"]
    assert "neighbour_commands" in information["forbidden_fields"]
    generator = contract["prediction_generator"]
    assert generator["model"].startswith("R341")
    assert generator["disturbance_scale"] == 0.05
    assert generator["measurement_fraction"] == 0.01
    assert generator["future_residual_control"] == "zero"
    assert generator["tuning_executed"] is False
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
    assert "r361_adapter" in sources
    assert "r360_adapter" in sources
    assert "r359_adapter" in sources
    assert "r353_adapter" in sources
    assert "r344_adapter" in sources
    parents = parent_paths()
    assert "r358_analysis" in parents
    assert "r359_analysis" in parents
    assert "r360_analysis" in parents
    assert "r361_analysis" in parents
    assert "r361_claim" in parents
