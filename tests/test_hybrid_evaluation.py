"""Unit tests for reusable hybrid controller action functions."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.hybrid import (  # noqa: E402
    bounded_droop_residual_action_fn,
    compose_bounded_droop_residual_actions,
    convex_blend_action_fn,
    interpolate_static_frontier_geo,
    mode_ratio_gated_blend_action_fn,
    proportional_damping_action_fn,
    slew_limited_mode_ratio_gated_blend_action_fn,
)
from andes_rl_kundur.evaluation.paper_path import deterministic_actor_action_fn  # noqa: E402


def test_proportional_damping_matches_r85_law():
    fn = proportional_damping_action_fn(10.0)
    obs = {
        0: np.array([0.0, -0.03, 0.0]),
        1: np.array([0.0, 0.20, 0.0]),
    }

    actions = fn(0, obs, 2)

    np.testing.assert_array_equal(actions[0], np.array([0.0, 0.3], dtype=np.float32))
    np.testing.assert_array_equal(actions[1], np.array([0.0, 1.0], dtype=np.float32))


def test_bounded_droop_residual_composition_is_exact_and_clipped():
    obs = {
        0: np.array([0.0, 0.02], dtype=np.float32),
        1: np.array([0.0, -0.20], dtype=np.float32),
    }
    residual = {
        0: np.array([1.0, -1.0], dtype=np.float32),
        1: np.array([-2.0, 0.5], dtype=np.float32),
    }

    actions = compose_bounded_droop_residual_actions(
        obs,
        residual,
        n_agents=2,
        k_droop=10.0,
        residual_scale=0.10,
    )

    np.testing.assert_allclose(actions[0], [0.10, 0.10], atol=1e-7)
    np.testing.assert_allclose(actions[1], [-0.10, 1.00], atol=1e-7)
    assert all(action.dtype == np.float32 for action in actions.values())


@pytest.mark.parametrize("scale", [-0.01, 1.01, float("nan")])
def test_bounded_droop_residual_rejects_invalid_scale(scale):
    with pytest.raises(ValueError, match="residual_scale"):
        bounded_droop_residual_action_fn(
            lambda step, obs, n_agents: {},
            k_droop=10.0,
            residual_scale=scale,
        )


def test_bounded_droop_residual_action_fn_matches_pure_composer():
    obs = {0: np.array([0.0, 0.03], dtype=np.float32)}
    residual = {0: np.array([0.4, -0.5], dtype=np.float32)}
    calls = []

    def residual_controller(step, current_obs, n_agents):
        calls.append((step, current_obs, n_agents))
        return residual

    action_fn = bounded_droop_residual_action_fn(
        residual_controller,
        k_droop=10.0,
        residual_scale=0.10,
    )
    actual = action_fn(7, obs, 1)
    expected = compose_bounded_droop_residual_actions(
        obs,
        residual,
        n_agents=1,
        k_droop=10.0,
        residual_scale=0.10,
    )

    np.testing.assert_array_equal(actual[0], expected[0])
    assert calls == [(7, obs, 1)]
    telemetry = action_fn.telemetry()
    assert telemetry["n_agent_steps"] == 1
    assert telemetry["residual_linf_max"] == pytest.approx(0.5)
    assert telemetry["executed_linf_max"] == pytest.approx(0.25)
    assert telemetry["executed_clipped_component_fraction"] == 0.0


@pytest.mark.parametrize("alpha", [-0.01, 1.01, float("nan")])
def test_convex_blend_rejects_invalid_alpha(alpha):
    with pytest.raises(ValueError, match="alpha"):
        convex_blend_action_fn(lambda *_: {}, lambda *_: {}, alpha=alpha)


def test_convex_blend_preserves_endpoints_and_clips():
    def primary(*_):
        return {0: np.array([-0.8, 2.0], dtype=np.float32)}

    def secondary(*_):
        return {0: np.array([0.4, -2.0], dtype=np.float32)}

    obs = {0: np.zeros(2, dtype=np.float32)}

    first = convex_blend_action_fn(primary, secondary, alpha=0.0)(0, obs, 1)
    second = convex_blend_action_fn(primary, secondary, alpha=1.0)(0, obs, 1)
    middle = convex_blend_action_fn(primary, secondary, alpha=0.25)(0, obs, 1)

    np.testing.assert_array_equal(first[0], np.array([-0.8, 1.0], dtype=np.float32))
    np.testing.assert_array_equal(second[0], np.array([0.4, -1.0], dtype=np.float32))
    np.testing.assert_allclose(middle[0], np.array([-0.5, 1.0], dtype=np.float32))


def test_blend_advances_and_resets_recurrent_primary():
    class RecurrentAgent:
        is_recurrent = True

        def __init__(self):
            self.hidden = 99
            self.reset_count = 0

        def begin_episode(self):
            self.hidden = 0
            self.reset_count += 1

        def select_action(self, obs, deterministic):
            del obs, deterministic
            self.hidden += 1
            return np.array([self.hidden, 0.0], dtype=np.float32)

    agent = RecurrentAgent()
    learned = deterministic_actor_action_fn([agent])

    def zero(*_):
        return {0: np.zeros(2, dtype=np.float32)}

    blend = convex_blend_action_fn(learned, zero, alpha=0.5)
    obs = {0: np.zeros(2, dtype=np.float32)}

    np.testing.assert_array_equal(blend(0, obs, 1)[0], np.array([0.5, 0.0]))
    np.testing.assert_array_equal(blend(1, obs, 1)[0], np.array([1.0, 0.0]))
    np.testing.assert_array_equal(blend(0, obs, 1)[0], np.array([0.5, 0.0]))
    assert agent.reset_count == 2


def test_blend_rejects_incomplete_agent_mapping():
    def primary(*_):
        return {0: np.zeros(2, dtype=np.float32)}

    def secondary(*_):
        return {}

    fn = convex_blend_action_fn(primary, secondary, alpha=0.5)

    with pytest.raises(ValueError, match="secondary"):
        fn(0, {0: np.zeros(2, dtype=np.float32)}, 1)


def test_mode_ratio_gate_matches_pre_registered_equation():
    def primary(*_):
        return {i: np.array([0.0, 0.0], dtype=np.float32) for i in range(4)}

    def secondary(*_):
        return {i: np.array([1.0, 1.0], dtype=np.float32) for i in range(4)}

    gate = mode_ratio_gated_blend_action_fn(
        primary,
        secondary,
        alpha_cap=0.5,
        ratio_full_scale=0.05,
    )
    obs = {
        0: np.array([0.0, 0.09]),
        1: np.array([0.0, 0.10]),
        2: np.array([0.0, 0.11]),
        3: np.array([0.0, 0.10]),
    }

    actions = gate(0, obs, 4)

    values = np.array([0.09, 0.10, 0.11, 0.10])
    ratio = np.std(values) / (abs(np.mean(values)) + np.std(values) + 1e-8)
    expected_alpha = 0.5 * np.clip(ratio / 0.05, 0.0, 1.0)
    for action in actions.values():
        np.testing.assert_allclose(action, [expected_alpha, expected_alpha])
    assert gate.alpha_history == pytest.approx([expected_alpha])
    assert gate.ratio_history == pytest.approx([ratio])


def test_mode_ratio_gate_saturates_on_pure_differential_mode_and_resets():
    calls = [0]

    def primary(step, obs, n_agents):
        if step == 0:
            calls[0] += 1
        return {i: np.zeros(2, dtype=np.float32) for i in range(n_agents)}

    def secondary(step, obs, n_agents):
        return {i: np.ones(2, dtype=np.float32) for i in range(n_agents)}

    gate = mode_ratio_gated_blend_action_fn(primary, secondary, alpha_cap=0.25)
    obs = {
        0: np.array([0.0, -0.1]),
        1: np.array([0.0, 0.1]),
    }

    first = gate(0, obs, 2)
    gate(1, obs, 2)
    second_scenario = gate(0, obs, 2)

    np.testing.assert_array_equal(first[0], np.array([0.25, 0.25]))
    np.testing.assert_array_equal(second_scenario[1], np.array([0.25, 0.25]))
    assert calls[0] == 2
    assert gate.telemetry()["n_steps"] == 1
    assert gate.telemetry()["saturated_fraction"] == 1.0


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"alpha_cap": 1.1}, "alpha_cap"),
        ({"alpha_cap": 0.5, "ratio_full_scale": 0.0}, "ratio_full_scale"),
        ({"alpha_cap": 0.5, "epsilon": 0.0}, "epsilon"),
    ],
)
def test_mode_ratio_gate_rejects_invalid_configuration(kwargs, match):
    with pytest.raises(ValueError, match=match):
        mode_ratio_gated_blend_action_fn(lambda *_: {}, lambda *_: {}, **kwargs)


def test_slew_limited_gate_bounds_executed_alpha_and_reports_telemetry():
    def primary(*_):
        return {i: np.zeros(2, dtype=np.float32) for i in range(2)}

    def secondary(*_):
        return {i: np.ones(2, dtype=np.float32) for i in range(2)}

    gate = slew_limited_mode_ratio_gated_blend_action_fn(
        primary,
        secondary,
        alpha_cap=0.25,
        delta_alpha_max=0.05,
    )
    common = {
        0: np.array([0.0, 0.1]),
        1: np.array([0.0, 0.1]),
    }
    differential = {
        0: np.array([0.0, -0.1]),
        1: np.array([0.0, 0.1]),
    }

    first = gate(0, common, 2)
    second = gate(1, differential, 2)
    third = gate(2, common, 2)

    np.testing.assert_allclose(first[0], [0.0, 0.0])
    np.testing.assert_allclose(second[0], [0.05, 0.05])
    np.testing.assert_allclose(third[0], [0.0, 0.0])
    assert gate.raw_alpha_history == pytest.approx([0.0, 0.25, 0.0])
    assert gate.alpha_history == pytest.approx([0.0, 0.05, 0.0])
    telemetry = gate.telemetry()
    assert telemetry["slew_limited_fraction"] == pytest.approx(1.0 / 3.0)
    assert telemetry["max_abs_executed_delta_alpha"] == pytest.approx(0.05)
    assert telemetry["delta_alpha_max"] == pytest.approx(0.05)


def test_slew_limited_gate_is_transparent_when_rate_is_inactive_and_resets():
    def primary(*_):
        return {i: np.zeros(2, dtype=np.float32) for i in range(2)}

    def secondary(*_):
        return {i: np.ones(2, dtype=np.float32) for i in range(2)}

    gate = slew_limited_mode_ratio_gated_blend_action_fn(
        primary,
        secondary,
        alpha_cap=0.25,
        delta_alpha_max=0.25,
    )
    differential = {
        0: np.array([0.0, -0.1]),
        1: np.array([0.0, 0.1]),
    }
    common = {
        0: np.array([0.0, 0.1]),
        1: np.array([0.0, 0.1]),
    }

    np.testing.assert_allclose(gate(0, differential, 2)[0], [0.25, 0.25])
    np.testing.assert_allclose(gate(1, common, 2)[0], [0.0, 0.0])
    np.testing.assert_allclose(gate(0, common, 2)[0], [0.0, 0.0])
    assert gate.telemetry()["n_steps"] == 1
    assert gate.telemetry()["slew_limited_fraction"] == 0.0


@pytest.mark.parametrize("delta", [0.0, -0.01, 0.26, float("nan")])
def test_slew_limited_gate_rejects_invalid_delta(delta):
    with pytest.raises(ValueError, match="delta_alpha_max"):
        slew_limited_mode_ratio_gated_blend_action_fn(
            lambda *_: {},
            lambda *_: {},
            alpha_cap=0.25,
            delta_alpha_max=delta,
        )


def test_static_frontier_interpolation_and_no_extrapolation():
    rows = [
        {"cum_rf": -0.07, "geo": 0.42},
        {"cum_rf": -0.05, "geo": 0.30},
        {"cum_rf": -0.03, "geo": 0.18},
    ]

    assert interpolate_static_frontier_geo(rows, cum_rf=-0.06) == pytest.approx(0.36)
    assert interpolate_static_frontier_geo(rows, cum_rf=-0.08) is None
    assert interpolate_static_frontier_geo(rows, cum_rf=-0.02) is None
