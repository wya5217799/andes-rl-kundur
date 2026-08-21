from __future__ import annotations

import numpy as np
import pytest
import scripts.run_r457_m2_head_causality as R457
import torch

from andes_rl_kundur.agents.cd_matd3 import JOINT_OBS_DIM


def test_contract_and_shard_inventory() -> None:
    contract = R457.build_contract()
    assert contract["replay"]["transitions_per_dataset"] == 720
    assert contract["replay"]["phase1_updates"] == 512
    assert contract["replay"]["phase2_updates"] == 256
    assert len(R457.replay_ids()) == 10
    assert len(R457.learn_ids()) == 40
    assert len(R457.eval_ids()) == 40
    assert len(R457.calibration_ids()) == 40
    assert len(set(R457.replay_ids() + R457.learn_ids() + R457.eval_ids() + R457.calibration_ids())) == 130


def test_four_cells_have_identical_initial_networks() -> None:
    hashes = []
    for cell in R457.CELLS:
        R457._seed_everything(401)
        hashes.append(R457._network_hashes(R457._agent("cd_matd3_message", cell)))
    assert all(value == hashes[0] for value in hashes)


def test_helmert_directions_are_orthonormal_by_action_channel() -> None:
    directions = R457._helmert_directions()
    assert len(directions) == 8
    for label, action_index in (("M", 0), ("D", 1)):
        rows = np.stack(
            [directions[f"differential_{label}_{index}"][:, action_index] for index in (1, 2, 3)]
        )
        assert np.allclose(rows @ rows.T, np.eye(3), atol=1e-12)
        common = directions[f"common_{label}"][:, action_index]
        assert np.allclose(rows @ common, 0.0, atol=1e-12)
        assert np.linalg.norm(common) == pytest.approx(1.0)


def test_legacy_r427_stats_update_is_not_output_preserving() -> None:
    probe = R457._legacy_nonpreservation_probe()
    assert probe["max_abs_original_output_delta_after_stats_only"] > 2e-5
    assert probe["output_preserved"] is False


def test_directional_gradient_is_finite() -> None:
    R457._seed_everything(402)
    agent = R457._agent("cd_matd3_no_message", "common_only")
    gradients, derivative = R457._critic_directional_gradients(
        agent,
        np.zeros(JOINT_OBS_DIM, dtype=np.float32),
        np.zeros((4, 2), dtype=np.float32),
        R457._helmert_directions()["common_M"],
    )
    assert np.all(np.isfinite(gradients))
    assert np.isfinite(derivative)


def test_batch_from_preserves_registered_shapes() -> None:
    data = {
        "obs": np.zeros((12, 28), dtype=np.float32),
        "prev_actions": np.zeros((12, 8), dtype=np.float32),
        "actions": np.zeros((12, 8), dtype=np.float32),
        "rewards": np.zeros((12, 2), dtype=np.float32),
        "next_obs": np.zeros((12, 28), dtype=np.float32),
        "dones": np.zeros((12, 1), dtype=np.float32),
    }
    batch = R457._batch_from(data, np.array([1, 3, 5]))
    assert batch["obs"].shape == (3, 28)
    assert batch["actions"].shape == (3, 8)
    assert batch["rewards"].shape == (3, 2)
    assert all(value.dtype == torch.float32 for value in batch.values())


def test_objective_semantics_probe_has_required_signs() -> None:
    generator = np.random.default_rng(11)
    data = {
        "obs": generator.standard_normal((64, 28)).astype(np.float32),
        "prev_actions": np.zeros((64, 8), dtype=np.float32),
        "actions": generator.uniform(-1, 1, (64, 8)).astype(np.float32),
        "rewards": -np.abs(generator.standard_normal((64, 2))).astype(np.float32),
        "next_obs": generator.standard_normal((64, 28)).astype(np.float32),
        "dones": np.zeros((64, 1), dtype=np.float32),
    }
    probe = R457._objective_semantics_probe(data)
    assert probe["output_correction_identity"]["ok"]
    assert probe["common_target_untouched"]["ok"]
    assert probe["stats_convergence"]["ok"]
    assert probe["differential_gradient_dot"] > 0.0
    assert probe["differential_gradient_decomposition_ok"]
