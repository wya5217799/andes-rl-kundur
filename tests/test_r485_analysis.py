"""Outcome-blind statistical and learner-admissibility tests for R485."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r485_60hz_source_factorial.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("r485_analysis_test", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_learner_gate_accepts_floor_alpha_only_when_other_signals_are_live() -> None:
    runner = _load_runner()
    live = {
        "weights_changed": True,
        "update_count": 42_945,
        "all_finite": True,
        "actor_grad_nonzero_fraction": 1.0,
        "reward_std": 0.1,
        "td_target_std": 0.2,
        "policy_state_sensitivity": 1.0e-3,
        "executed_action_std": 2.0e-3,
        "action_saturation_fraction": 0.2,
        "log_std_at_lower_bound_fraction": 0.0,
        "alpha_at_floor": True,
        "routing_oracle_passed": True,
        "executed_action_bellman_passed": True,
    }
    collapsed = {**live, "policy_state_sensitivity": 0.0, "executed_action_std": 0.0}

    assert runner.assess_learner_admissibility(live)["passed"] is True
    result = runner.assess_learner_admissibility(collapsed)
    assert result["passed"] is False
    assert "policy_state_sensitivity" in result["failures"]
    assert "executed_action_variation" in result["failures"]


def test_tds_ontology_separates_integrity_from_controller_failure() -> None:
    runner = _load_runner()

    assert runner.classify_tds("hash_mismatch", reproducible=False) == "INTEGRITY-INVALID"
    assert runner.classify_tds("tds_divergence", reproducible=True) == "COMPLETE-GUARD-FAIL"
    assert runner.classify_tds("tds_divergence", reproducible=False) == "REPRODUCTION-REQUIRED"


def test_statistics_contract_has_no_data_dependent_fallback() -> None:
    runner = _load_runner()
    contract = runner.build_parameter_card()["statistics"]

    assert contract["estimand"] == "seed_level_hodges_lehmann_location_pseudomedian"
    assert contract["null_boundary"] == "theta_HL <= log(1.10)"
    assert contract["test"] == "exact_one_sided_wilcoxon_signed_rank"
    assert contract["multiplicity"] == "Holm_family_of_four"
    assert contract["ties_zeros_or_symmetry_failure"] == "ASSUMPTION-LIMITED"
    assert contract["fallback"] is None


def test_threshold_and_claim_contracts_are_frozen_before_results() -> None:
    runner = _load_runner()
    card = runner.build_parameter_card()

    assert card["threshold_sensitivity"]["frequency_multipliers"] == [1.0, 1.03, 1.05, 1.1]
    assert card["threshold_sensitivity"]["action_multipliers"] == [1.1, 1.2, 1.5, 2.0]
    assert card["threshold_sensitivity"]["primary"] == {"frequency": 1.03, "action": 1.1}
    assert card["threshold_sensitivity"]["post_result_threshold_additions"] is False
    assert set(card["outcome_to_claim"]) == {
        "VALID-POSITIVE",
        "VALID-MIXED",
        "VALID-NEGATIVE",
        "ASSUMPTION-LIMITED",
        "INTEGRITY-INVALID",
    }
