"""Adapter-level tests for the R360 flexible residual gate adapter."""

from __future__ import annotations

import numpy as np
import pytest
from scripts.run_r360_flexible_neighbour_residual import (
    build_contract,
    source_paths,
    parent_paths,
)

from andes_rl_kundur.control.flexible_neighbour_residual import (
    FLEXIBLE_CONTROLLER_FAMILY,
)


def test_contract_freezes_exactly_three_tuning_free_members() -> None:
    contract = build_contract()
    family = contract["controller_family"]
    assert family["members"] == sorted(FLEXIBLE_CONTROLLER_FAMILY)
    assert family["tuning_executed"] is False
    for member in family["members"]:
        assert family[member]["sweep"] is False
    assert family["selection_semantics"] == "pre-registered OR over all members"
    assert contract["authorization"]["training"] is False
    assert contract["authorization"]["simulation"] is False


def test_contract_matches_r359_information_and_physical_contract() -> None:
    contract = build_contract()
    information = contract["information"]
    assert information["continuous_fields_per_actor"] == 15
    assert information["startup_zero_steps"] == 2
    assert "achieved_power" in information["forbidden_fields"]
    assert "oracle_values" in information["forbidden_fields"]
    assert contract["inventory"]["development_pairs"] == 16
    assert contract["inventory"]["positive_development_targets"] == 10


def test_source_and_parent_closures_are_complete() -> None:
    sources = source_paths(include_rehearsal=False)
    assert "plan" in sources
    assert "question" in sources
    assert "capacity" in sources
    assert "adapter" in sources
    assert "probe" in sources
    assert "controller_src" in sources
    assert "r359_adapter" in sources
    assert "r353_adapter" in sources
    parents = parent_paths()
    assert "r358_analysis" in parents
    assert "r359_analysis" in parents
    assert "r359_claim" in parents
