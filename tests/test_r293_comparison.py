from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.agents.classical_prior_td3 import (
    CentralPriorResidualTD3,
    DistributedPriorResidualTD3,
)
from andes_rl_kundur.control.classical_edge_residual import ClassicalEdgeContract
from andes_rl_kundur.env.andes.prior_residual_env import PriorResidualEnv
from tests.test_vector_residual_control import _FakeStorageEnv
from probes.r293_comparison import classify_r293, hierarchical_ratio_bootstrap


def test_r293_reward_adds_frozen_rocof_penalty_without_changing_physics() -> None:
    base = _FakeStorageEnv()
    env = PriorResidualEnv(base)
    env.reset(delta_u={"demo": 1.0})

    _obs, rewards, _done, info = env.step(np.zeros(3, dtype=np.float32))

    assert info["r293_reward_terms"]["max_rocof"] > 0.0
    assert info["r293_team_reward"] < info["r292_team_reward"]
    assert sum(rewards.values()) == pytest.approx(info["r293_team_reward"])
    assert info["r293_rocof_reward_weight"] == 0.25
    assert info["r292_contract"]["central_action_aggregation"] is False


def test_both_prior_residual_architectures_complete_finite_updates() -> None:
    rng = np.random.default_rng(293)
    contract = ClassicalEdgeContract(family="full", gain=0.5)
    for agent_class in (DistributedPriorResidualTD3, CentralPriorResidualTD3):
        agent = agent_class(
            classical_contract=contract,
            batch_size=4,
            buffer_size=32,
            policy_delay=2,
        )
        for index in range(8):
            observation = rng.normal(size=20).astype(np.float32)
            next_observation = rng.normal(size=20).astype(np.float32)
            agent.store(
                observation,
                rng.uniform(-1.0, 1.0, size=3).astype(np.float32),
                reward=-float(index),
                next_observation=next_observation,
                done=index == 7,
            )

        first = agent.update()
        second = agent.update()

        assert first is not None and np.isfinite(first["critic_loss"])
        assert second is not None and np.isfinite(second["critic_loss"])
        assert np.isfinite(second["actor_loss"])


def _contrast(point: float, low: float, high: float, one_sided: float) -> dict:
    return {
        endpoint: {
            "ratio_of_means_percent": {
                "point": point,
                "percentile_95_interval": [low, high],
                "one_sided_95_upper": one_sided,
            }
        }
        for endpoint in ("normalized_sync_loss_hz2", "fast_inter_area_iae_hz_s")
    }


def test_r293_noninferiority_is_a_positive_bounded_architecture_result() -> None:
    decision = classify_r293(
        integrity_valid=True,
        distributed_vs_classical=_contrast(-6.0, -9.0, -2.5, -3.0),
        central_vs_classical=_contrast(-7.0, -10.0, -3.0, -3.5),
        distributed_vs_central=_contrast(1.0, -2.0, 4.0, 3.5),
        distributed_directional_seed_count=4,
        distributed_noninferior_seed_count=4,
        distributed_positive_claim_guards={"tail": True, "storage": True},
        central_positive_claim_guards={"tail": True, "storage": True},
    )

    assert decision["classification"] == "DISTRIBUTED-NONINFERIOR-LOCAL"


def test_controller_guard_failure_is_valid_negative_not_integrity_invalid() -> None:
    decision = classify_r293(
        integrity_valid=True,
        distributed_vs_classical=_contrast(-6.0, -9.0, -2.5, -3.0),
        central_vs_classical=_contrast(-7.0, -10.0, -3.0, -3.5),
        distributed_vs_central=_contrast(1.0, -2.0, 4.0, 3.5),
        distributed_directional_seed_count=4,
        distributed_noninferior_seed_count=4,
        distributed_positive_claim_guards={"tail": False, "storage": True},
        central_positive_claim_guards={"tail": True, "storage": True},
    )

    assert decision["classification"] == "DISTRIBUTED-EFFECTIVE-GUARD-FAIL"


def test_hierarchical_bootstrap_exposes_one_sided_upper_bound() -> None:
    left = {
        seed: {"a": 0.90 + seed * 0.001, "b": 1.00 + seed * 0.001}
        for seed in range(5)
    }
    right = {
        seed: {"a": 1.0 + seed * 0.001, "b": 1.1 + seed * 0.001}
        for seed in range(5)
    }

    result = hierarchical_ratio_bootstrap(
        left,
        right_by_seed=right,
        resamples=500,
        seed=293,
    )

    effect = result["ratio_of_means_percent"]
    assert effect["one_sided_95_upper"] < 0.0
    assert effect["percentile_95_interval"][1] < 0.0


def test_only_explicit_integrity_failure_can_return_integrity_invalid() -> None:
    decision = classify_r293(
        integrity_valid=False,
        distributed_vs_classical=_contrast(-6.0, -9.0, -2.5, -3.0),
        central_vs_classical=_contrast(-7.0, -10.0, -3.0, -3.5),
        distributed_vs_central=_contrast(1.0, -2.0, 4.0, 3.5),
        distributed_directional_seed_count=4,
        distributed_noninferior_seed_count=4,
        distributed_positive_claim_guards={"tail": False},
        central_positive_claim_guards={"tail": False},
    )

    assert decision["classification"] == "INTEGRITY-INVALID"
