from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.evaluation.reviewer_identifiability import (
    analyse_seed_policy_actions,
    analyse_signed_h1_pairs,
    hierarchical_seed_scenario_ratio_bootstrap,
)


def _record(
    scenario: str,
    differential: list[float],
    *,
    common: list[float] | None = None,
    q: list[float] | None = None,
    m_values: list[float] | None = None,
) -> dict:
    common_values = common or [0.01] * len(differential)
    inertia = m_values or [350.0, 350.0, 350.0, 350.0]
    traces = []
    for step, (common_value, diff_value) in enumerate(
        zip(common_values, differential, strict=True)
    ):
        frequency = np.asarray(
            [
                common_value + 0.5 * diff_value,
                common_value + 0.5 * diff_value,
                common_value - 0.5 * diff_value,
                common_value - 0.5 * diff_value,
            ]
        )
        traces.append(
            {
                "step": step,
                "t": 0.2 * (step + 1),
                "delta_f_physical_hz": frequency.tolist(),
                "M_es": inertia,
                "r278_q": 0.0 if q is None else q[step],
            }
        )
    return {
        "scenario": scenario,
        "completed": True,
        "tds_failed": False,
        "n_steps": len(traces),
        "traces": traces,
    }


def test_policy_diagnostic_aligns_actions_with_pre_action_signal() -> None:
    first = _record(
        "a",
        [0.1, 0.2, -0.1, 0.05],
        q=[-0.2, -0.1, -0.2, 0.1],
    )
    second = _record(
        "b",
        [0.05, 0.1, -0.05, 0.02],
        q=[-0.2, -0.05, -0.1, 0.05],
    )
    result = analyse_seed_policy_actions([first, second], active_steps=4)
    assert result["first_action"]["scenario_invariant_at_1e_7"] is True
    pooled = result["pooled_active_window"]
    assert pooled["correlation_q_with_available_inter_area_frequency"] < -0.5
    assert pooled["negative_feedback_sign_agreement_frequency"]["fraction"] == 1.0
    assert result["alignment"]["current_frequency"].startswith("post-action")


def test_signed_pair_decomposition_separates_common_leakage() -> None:
    baseline = {"s": _record("s", [0.02, 0.03, 0.02, 0.01])}
    perturbation = np.asarray([0.01, -0.02, 0.03, -0.01])
    base_diff = np.asarray([0.02, 0.03, 0.02, 0.01])
    base_common = np.asarray([0.01, 0.01, 0.01, 0.01])
    h1_pos = {
        "s": _record(
            "s",
            (base_diff + perturbation).tolist(),
            common=(base_common + 0.1 * perturbation).tolist(),
            m_values=[500.0, 500.0, 200.0, 200.0],
        )
    }
    h1_neg = {
        "s": _record(
            "s",
            (base_diff - perturbation).tolist(),
            common=(base_common - 0.1 * perturbation).tolist(),
            m_values=[200.0, 200.0, 500.0, 500.0],
        )
    }
    result = analyse_signed_h1_pairs(
        baseline,
        h1_pos,
        h1_neg,
        active_steps=4,
    )
    ratios = result["aggregate"]["leakage_ratios"]
    assert ratios["odd_common_to_odd_differential_iae"] == pytest.approx(0.1)
    assert ratios["even_common_to_odd_differential_iae"] == pytest.approx(0.0)
    assert result["maximum_abs_fleet_mean_m_shift_vs_q0"] == pytest.approx(0.0)
    assert result["aggregate"]["odd_differential_iae_hz_s"]["mean"] > 0.0


def test_signed_pair_rejects_mismatched_scenarios() -> None:
    baseline = {"s": _record("s", [0.01, 0.02])}
    with pytest.raises(ValueError, match="scenario sets"):
        analyse_signed_h1_pairs(
            baseline,
            {"other": _record("other", [0.01, 0.02])},
            baseline,
            active_steps=2,
        )

def test_hierarchical_bootstrap_is_paired_deterministic_and_lower_is_better():
    left = {
        17: {"a": 0.8, "b": 1.6, "c": 2.4},
        53: {"a": 0.9, "b": 1.8, "c": 2.7},
        89: {"a": 0.7, "b": 1.4, "c": 2.1},
    }
    right = {
        17: {"a": 1.0, "b": 2.0, "c": 3.0},
        53: {"a": 1.0, "b": 2.0, "c": 3.0},
        89: {"a": 1.0, "b": 2.0, "c": 3.0},
    }
    first = hierarchical_seed_scenario_ratio_bootstrap(
        left, right_by_seed=right, resamples=500, seed=123
    )
    second = hierarchical_seed_scenario_ratio_bootstrap(
        left, right_by_seed=right, resamples=500, seed=123
    )
    assert first == second
    assert first["ratio_of_means_percent"]["point"] == pytest.approx(-20.0)
    assert first["ratio_of_means_percent"]["percentile_95_interval"][1] < 0.0
    assert first["bootstrap_probability_left_improves"] == 1.0


def test_hierarchical_bootstrap_supports_deterministic_comparator():
    left = {
        17: {"a": 1.0, "b": 2.0},
        53: {"a": 1.0, "b": 2.0},
        89: {"a": 1.0, "b": 2.0},
    }
    result = hierarchical_seed_scenario_ratio_bootstrap(
        left,
        right_deterministic={"a": 1.0, "b": 2.0},
        resamples=200,
        seed=9,
    )
    assert result["ratio_of_means_percent"]["point"] == pytest.approx(0.0)
    assert result["ratio_of_means_percent"]["percentile_95_interval"] == pytest.approx([0.0, 0.0])
    assert result["right_has_seed_dimension"] is False


def test_hierarchical_bootstrap_rejects_mismatched_scenarios():
    with pytest.raises(ValueError, match="scenario set"):
        hierarchical_seed_scenario_ratio_bootstrap(
            {17: {"a": 1.0, "c": 2.0}, 53: {"a": 1.0, "c": 2.0}},
            right_deterministic={"b": 1.0, "c": 2.0},
            resamples=100,
        )
