"""Pure tests for the R403 disclosed-profile development gate."""

from __future__ import annotations

from andes_rl_kundur.evaluation.cd_matd3_successor import (
    DETERMINISTIC_BASELINE,
    R402_BASELINE,
    REPAIRED_ARMS,
    build_successor_contract,
    classify_development_gate,
)


def _block(
    *,
    action: float,
    slew: float,
    common: float,
    differential: float,
) -> dict[str, object]:
    return {
        "mean_abs_action": action,
        "slew_bound_hit_fraction": slew,
        "mean_per_record_common": common,
        "mean_per_record_differential": differential,
        "diagnostics_complete": True,
        "tds_failed_episodes": 0,
    }


def test_contract_uses_only_disclosed_development_profiles() -> None:
    contract = build_successor_contract()
    assert contract["total_interaction_steps"] == 1200
    assert contract["scratch_seed"] == 4030
    assert contract["fixed_common_weight"] == 1.0
    assert contract["action_effort_weight"] == 1.0
    assert len(contract["profiles"]) == 4
    assert all(profile["split"] == "development" for profile in contract["profiles"])
    assert set(contract["excluded_profile_ids"]) == {
        "canary_eval_a",
        "canary_eval_b",
        "canary_eval_c",
        "canary_eval_d",
    }


def test_gate_passes_only_when_both_repaired_arms_pass_every_guard() -> None:
    metrics = {
        DETERMINISTIC_BASELINE: _block(
            action=0.01, slew=0.001, common=10.0, differential=1.0
        ),
        R402_BASELINE: _block(
            action=0.20, slew=0.10, common=50.0, differential=5.0
        ),
    }
    for arm_id in REPAIRED_ARMS:
        metrics[arm_id] = _block(
            action=0.10, slew=0.049, common=15.0, differential=5.0
        )

    outcome = classify_development_gate(metrics)

    assert outcome["classification"] == "SCRATCH-PASS"
    assert all(value["passed"] for value in outcome["arm_decisions"].values())


def test_gate_fails_without_tuning_when_one_guard_misses() -> None:
    metrics = {
        DETERMINISTIC_BASELINE: _block(
            action=0.01, slew=0.001, common=10.0, differential=1.0
        ),
        R402_BASELINE: _block(
            action=0.20, slew=0.10, common=50.0, differential=5.0
        ),
        REPAIRED_ARMS[0]: _block(
            action=0.10, slew=0.049, common=15.0, differential=5.0
        ),
        REPAIRED_ARMS[1]: _block(
            action=0.10, slew=0.05, common=15.0, differential=5.0
        ),
    }

    outcome = classify_development_gate(metrics)

    assert outcome["classification"] == "SCRATCH-FAIL"
    assert not outcome["arm_decisions"][REPAIRED_ARMS[1]]["guards"]["slew_ok"]
