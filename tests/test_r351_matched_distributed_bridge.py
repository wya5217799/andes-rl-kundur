from __future__ import annotations

import numpy as np

import scripts.run_r351_matched_distributed_bridge as adapter
from andes_rl_kundur.env.andes.model_first_contract import active_power_incidence


def test_contract_freezes_only_matched_edge_execution_canaries() -> None:
    contract = adapter.build_contract()

    assert contract["round"] == "R351"
    assert contract["question"] == "Q-0092"
    assert contract["information_pattern"] == "endpoint-neighbour-only"
    assert contract["action_edges"] == [[0, 1], [1, 2], [2, 3]]
    assert contract["zero_record_count"] == 2
    assert contract["signed_record_count"] == 12
    assert contract["total_record_count"] == 14
    assert contract["training_executed"] is False
    assert contract["performance_comparison_executed"] is False


def test_signed_profile_is_generated_by_the_matched_governor() -> None:
    spec = adapter.build_signed_specs()[0]
    profile = adapter.governed_request_profile(spec)
    expected = np.zeros((25, 4))
    expected[:5] = active_power_incidence()[:, 0] * -0.05

    np.testing.assert_allclose(profile, expected, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(np.sum(profile, axis=1), np.zeros(25), atol=1e-12)


def test_canary_classifier_separates_contract_and_physical_failures() -> None:
    valid = [
        {
            "integrity_valid": True,
            "matched_governor_valid": True,
            "physical_guards_pass": True,
        }
        for _ in range(14)
    ]
    assert adapter.classify_canary_records(valid) == (
        "DISTRIBUTED-EDGE-EXECUTION-ELIGIBLE"
    )

    valid[0]["matched_governor_valid"] = False
    assert adapter.classify_canary_records(valid) == (
        "INVALID-DISTRIBUTED-EDGE-CONTRACT"
    )
    valid[0]["matched_governor_valid"] = True
    valid[0]["physical_guards_pass"] = False
    assert adapter.classify_canary_records(valid) == (
        "DISTRIBUTED-EDGE-PHYSICAL-GUARD-FAIL"
    )


def test_parser_exposes_no_training_or_performance_command() -> None:
    parser = adapter.build_parser()
    subparsers = next(action for action in parser._actions if action.dest == "command")
    commands = set(subparsers.choices)

    assert {"rehearse", "measure-capacity", "prepare", "execute-canaries"} <= commands
    assert not {"train", "training", "optimize", "formal-performance"} & commands


def test_rehearsal_gate_requires_no_physical_trajectory() -> None:
    rehearsal = {
        "checks": {
            "scratch_isolation": True,
            "inventory_count": True,
            "all_profiles_finite": True,
            "formal_output_absent": True,
            "physical_trajectory_executed": False,
        }
    }

    assert adapter.rehearsal_passed(rehearsal) is True
    rehearsal["checks"]["physical_trajectory_executed"] = True
    assert adapter.rehearsal_passed(rehearsal) is False
