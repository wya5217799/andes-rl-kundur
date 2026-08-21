from __future__ import annotations

import numpy as np
import scripts.run_r470_u2_source_factorial as R470


def test_factorial_is_complete_and_balanced() -> None:
    assert len(R470.ARMS) == 18
    cells = [R470.arm_factors(arm) for arm in R470.ARMS]
    assert {row["actor_source"] for row in cells} == {"0", "P", "N"}
    assert {row["critic_source"] for row in cells} == {"0", "P", "N"}
    assert {row["reward_access"] for row in cells} == {False, True}
    assert len({(row["actor_source"], row["critic_source"], row["reward_access"]) for row in cells}) == 18


def test_placebo_rows_use_only_non_neighbour_donor_nodes() -> None:
    current = np.arange(28, dtype=np.float32).reshape(4, 7)
    donor = (1000 + np.arange(28, dtype=np.float32)).reshape(4, 7)
    rows = R470.source_rows(current, donor, "P")
    for i in range(4):
        assert np.array_equal(rows[i, :3], current[i, :3])
        assert np.array_equal(rows[i, 3:5], donor[i, 1:3])
        assert np.array_equal(rows[i, 5:7], donor[(i + 2) % 4, 1:3])
        assert i not in ((i - 1) % 4, (i + 1) % 4)
        assert (i + 2) % 4 not in ((i - 1) % 4, (i + 1) % 4)


def test_zero_and_neighbour_sources_change_only_registered_slots() -> None:
    current = np.arange(28, dtype=np.float32).reshape(4, 7)
    zero = R470.source_rows(current, np.zeros_like(current), "0")
    neighbour = R470.source_rows(current, np.zeros_like(current), "N")
    assert np.array_equal(zero[:, :3], current[:, :3])
    assert np.count_nonzero(zero[:, 3:7]) == 0
    assert np.array_equal(neighbour, current)


def test_fixed_point_free_placebo_preserves_every_pooled_marginal() -> None:
    tensor = np.arange(4 * 2 * 9 * 4 * 7, dtype=np.float32).reshape(4, 2, 9, 4, 7)
    audit = R470.donor_marginal_audit(tensor)
    assert audit["pi_fixed_point_free"]
    assert audit["placebo_nodes_are_non_neighbours"]
    assert audit["every_semantic_donor_changed"]
    assert audit["slot_feature_scenario_time_pools_equal"]
    assert audit["comparisons"] == 4 * 9 * 2 * 2


def test_main_effect_is_seed_paired_log_p_over_n() -> None:
    endpoints = {
        arm: {R470.PRIMARY: [2.0] * 6, R470.SECONDARY: [1.0] * 6}
        for arm in R470.ARMS
    }
    for arm in R470.ARMS:
        if R470.arm_factors(arm)["actor_source"] == "N":
            endpoints[arm][R470.PRIMARY] = [1.0] * 6
    values = R470._main_effect(endpoints, "actor", R470.PRIMARY)
    assert np.allclose(values, np.log(2.0))
