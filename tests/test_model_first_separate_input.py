"""Behavior tests for the separate control/disturbance model seam."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from andes_rl_kundur.control.model_first_separate_input import (
    SeparateInputHorizonController,
    SeparateInputRealization,
    advance_separate_input_estimate,
    fallback_separate_input_node_power,
    synthesize_separate_input_estimator,
)
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    StateSpaceRealization,
)

ROOT = Path(__file__).resolve().parents[1]


def test_joint_model_can_be_split_without_static_input_equivalence() -> None:
    joint = StateSpaceRealization(
        state_matrix=np.diag([0.7, 0.8]),
        input_matrix=np.arange(16.0).reshape(2, 8),
        output_matrix=np.arange(8.0).reshape(4, 2),
        feedthrough_matrix=np.arange(32.0).reshape(4, 8) / 10.0,
        retained_singular_values=np.array([3.0, 1.0]),
    )

    split = SeparateInputRealization.from_joint(joint)

    np.testing.assert_array_equal(split.control_input_matrix, joint.input_matrix[:, :4])
    np.testing.assert_array_equal(split.disturbance_input_matrix, joint.input_matrix[:, 4:])
    np.testing.assert_array_equal(
        split.control_feedthrough_matrix,
        joint.feedthrough_matrix[:, :4],
    )
    np.testing.assert_array_equal(
        split.disturbance_feedthrough_matrix,
        joint.feedthrough_matrix[:, 4:],
    )
    np.testing.assert_array_equal(split.as_joint_realization().input_matrix, joint.input_matrix)
    np.testing.assert_array_equal(
        split.as_control_realization().input_matrix,
        joint.input_matrix[:, :4],
    )


def test_estimator_keeps_control_and_disturbance_dynamics_separate() -> None:
    model = SeparateInputRealization(
        state_matrix=np.diag([0.2, 0.3, 0.4, 0.5]),
        control_input_matrix=0.1 * np.eye(4),
        disturbance_input_matrix=np.eye(4),
        output_matrix=np.eye(4),
        control_feedthrough_matrix=0.05 * np.eye(4),
        disturbance_feedthrough_matrix=np.zeros((4, 4)),
        retained_singular_values=np.ones(4),
    )

    design = synthesize_separate_input_estimator(
        model,
        output_scales=np.ones(4),
    )

    np.testing.assert_array_equal(
        design.transition_matrix,
        np.block(
            [
                [model.state_matrix, model.disturbance_input_matrix],
                [np.zeros((4, 4)), np.eye(4)],
            ]
        ),
    )
    np.testing.assert_array_equal(
        design.control_matrix,
        np.vstack((model.control_input_matrix, np.zeros((4, 4)))),
    )
    np.testing.assert_array_equal(
        design.measurement_matrix,
        np.hstack((model.output_matrix, model.disturbance_feedthrough_matrix)),
    )
    np.testing.assert_array_equal(
        design.control_feedthrough_matrix,
        model.control_feedthrough_matrix,
    )
    assert design.observability_rank == 8
    assert design.error_pole_radius < 1.0


def test_estimator_step_subtracts_only_the_executed_control_feedthrough() -> None:
    model = SeparateInputRealization(
        state_matrix=0.4 * np.eye(4),
        control_input_matrix=0.2 * np.eye(4),
        disturbance_input_matrix=np.eye(4),
        output_matrix=np.eye(4),
        control_feedthrough_matrix=0.5 * np.eye(4),
        disturbance_feedthrough_matrix=np.zeros((4, 4)),
        retained_singular_values=np.ones(4),
    )
    design = synthesize_separate_input_estimator(model, output_scales=np.ones(4))
    control = np.array([0.10, -0.20, 0.30, -0.40])

    step = advance_separate_input_estimate(
        design,
        prior_estimate=np.zeros(8),
        previous_delivered_output=0.5 * control,
        previous_executed_control=control,
    )

    np.testing.assert_allclose(step.innovation, np.zeros(4), atol=1.0e-15)
    np.testing.assert_allclose(
        step.predicted_estimate,
        np.concatenate((0.2 * control, np.zeros(4))),
        atol=1.0e-15,
    )


def test_horizon_controller_uses_achieved_node_power_in_estimator() -> None:
    model = SeparateInputRealization(
        state_matrix=0.4 * np.eye(4),
        control_input_matrix=0.2 * np.eye(4),
        disturbance_input_matrix=np.eye(4),
        output_matrix=np.eye(4),
        control_feedthrough_matrix=0.5 * np.eye(4),
        disturbance_feedthrough_matrix=np.zeros((4, 4)),
        retained_singular_values=np.ones(4),
    )
    controller = SeparateInputHorizonController(
        model,
        output_scales=np.ones(4),
        action_scales=np.ones(4),
        horizon_steps=2,
    )
    assert controller.identity.information_pattern == "full-output-centralized"
    assert controller.identity.input_contract == "separate-control-and-disturbance"
    assert controller.identity.request_semantics == "node-power-before-physical-projection"
    assert controller.identity.achieved_semantics == "measured-node-power"
    assert controller.identity.solver == "osqp-direct"
    assert controller.identity.fallback == "bounded-ramp-toward-zero"
    assert controller.identity.horizon_steps == 2
    achieved_node_power = np.full(4, 0.1)

    step = controller.step(
        prior_estimate=np.zeros(8),
        previous_delivered_output=np.array([0.05, 0.0, 0.0, 0.0]),
        previous_achieved_node_power=achieved_node_power,
        previous_commanded_node_power=np.zeros(4),
        soc=np.full(4, 0.5),
    )

    np.testing.assert_allclose(
        step.achieved_control_coordinates,
        np.array([0.1, 0.0, 0.0, 0.0]),
        atol=1.0e-15,
    )
    np.testing.assert_allclose(step.estimate.innovation, np.zeros(4), atol=1.0e-15)
    assert step.solver.solution.feasible
    assert not step.used_fallback
    assert np.all(np.abs(step.requested_node_power) <= 0.36 + 1.0e-12)


def test_fallback_moves_toward_zero_inside_the_frozen_ramp() -> None:
    fallback = fallback_separate_input_node_power(
        previous_commanded_node_power=np.array([0.20, -0.20, 0.05, -0.05]),
        soc=np.full(4, 0.5),
    )

    np.testing.assert_allclose(fallback, np.array([0.128, -0.128, 0.0, 0.0]))


def test_r341_candidates_support_the_frozen_horizon_controller() -> None:
    candidate_path = (
        ROOT
        / "results"
        / "r341_staged_fresh_model_validation"
        / "candidate_models.json"
    )
    payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    assert hashlib.sha256(candidate_path.read_bytes()).hexdigest() == (
        "7a74cb78dca8c5e30f32a344ca43704079a1549c966ff21de492eba7a3f1e32e"
    )
    point_digests = {
        "FV0": "c858441f0fd48c7f69da98f569bca4a88f3547324af6a301ebf42de60c055cf5",
        "FV1": "c65ead6face6015ed951b7d55b13b90847fb557462ab946d730392666cf9200c",
    }
    initial_soc = {"FV0": 0.435, "FV1": 0.535}
    output_scales = {
        "FV0": np.array(
            [
                0.0005208588784582888,
                0.00020891280532014673,
                0.0002641363410614004,
                0.0004599914624251534,
            ]
        ),
        "FV1": np.array(
            [
                0.0005014001877174584,
                0.0002058568956880255,
                0.00024780152784620513,
                0.00043006662398575727,
            ]
        ),
    }

    for point, expected_digest in point_digests.items():
        raw = payload["points"][point]["order12"]
        digest = hashlib.sha256(
            json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        assert digest == expected_digest
        realization = StateSpaceRealization(
            state_matrix=np.asarray(raw["state_matrix"], dtype=float),
            input_matrix=np.asarray(raw["input_matrix"], dtype=float),
            output_matrix=np.asarray(raw["output_matrix"], dtype=float),
            feedthrough_matrix=np.asarray(raw["feedthrough_matrix"], dtype=float),
            retained_singular_values=np.asarray(
                raw["retained_singular_values"], dtype=float
            ),
        )
        controller = SeparateInputHorizonController(
            SeparateInputRealization.from_joint(realization),
            output_scales=output_scales[point],
            action_scales=np.full(4, 0.36),
            horizon_steps=25,
        )
        zero = controller.step(
            prior_estimate=np.zeros(16),
            previous_delivered_output=np.zeros(4),
            previous_achieved_node_power=np.zeros(4),
            previous_commanded_node_power=np.zeros(4),
            soc=np.full(4, initial_soc[point]),
        )
        assert controller.estimator.observability_rank == 16
        assert controller.estimator.error_pole_radius < 1.0
        assert zero.solver.solution.feasible
        assert not zero.used_fallback
        np.testing.assert_allclose(zero.requested_node_power, np.zeros(4))

        for sign in (-1.0, 1.0):
            controller.reset()
            signed = controller.step(
                prior_estimate=np.zeros(16),
                previous_delivered_output=sign
                * output_scales[point]
                * np.array([1.0, 0.0, 0.0, 0.0]),
                previous_achieved_node_power=np.zeros(4),
                previous_commanded_node_power=np.zeros(4),
                soc=np.full(4, initial_soc[point]),
            )
            assert signed.solver.solution.feasible
            assert not signed.used_fallback
            assert sign * signed.requested_control_coordinates[0] < 0.0
            assert np.max(np.abs(signed.requested_node_power)) <= 0.072 + 1.0e-8
