from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

from andes_rl_kundur.agents.td3 import TD3Agent
from andes_rl_kundur.env.andes.residual_adapter import BoundedDroopResidualEnv
from andes_rl_kundur.evaluation.hybrid import bounded_droop_residual_action_fn
from andes_rl_kundur.evaluation.paper_path import deterministic_actor_action_fn


ROOT = Path(__file__).resolve().parents[1]


class _FakeEnv:
    N_AGENTS = 2
    STEPS_PER_EPISODE = 3

    def __init__(self) -> None:
        self.received = []
        self.closed = False
        self._reset_obs = {
            0: np.array([0.0, 0.02], dtype=np.float32),
            1: np.array([0.0, -0.04], dtype=np.float32),
        }
        self._next_obs = {
            0: np.array([0.0, 0.06], dtype=np.float32),
            1: np.array([0.0, -0.08], dtype=np.float32),
        }

    def reset(self):
        return self._reset_obs

    def step(self, actions):
        self.received.append(actions)
        return self._next_obs, {0: -1.0, 1: -2.0}, False, {"base": True}

    def close(self):
        self.closed = True


def _load_train_module():
    spec = importlib.util.spec_from_file_location(
        "train_residual_test",
        ROOT / "scripts" / "train.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_adapter_uses_current_observation_and_exposes_executed_telemetry():
    base = _FakeEnv()
    env = BoundedDroopResidualEnv(base, k_droop=10.0, residual_scale=0.10)
    obs = env.reset()
    residual = {
        0: np.array([0.5, -0.5], dtype=np.float32),
        1: np.array([-0.5, 0.5], dtype=np.float32),
    }

    next_obs, rewards, done, info = env.step(residual)

    assert obs is base._reset_obs
    assert next_obs is base._next_obs
    assert rewards == {0: -1.0, 1: -2.0}
    assert done is False
    np.testing.assert_allclose(base.received[0][0], [0.05, 0.15], atol=1e-7)
    np.testing.assert_allclose(base.received[0][1], [-0.05, 0.45], atol=1e-7)
    assert info["base"] is True
    assert info["controller_contract"]["mode"] == "bounded_droop_residual"
    assert info["residual_action_linf"] == pytest.approx(0.5)
    assert info["executed_action_linf"] == pytest.approx(0.45)

    # The next call must use the observation returned by the previous base step.
    zeros = {0: np.zeros(2, dtype=np.float32), 1: np.zeros(2, dtype=np.float32)}
    env.step(zeros)
    np.testing.assert_allclose(base.received[1][0], [0.0, 0.6], atol=1e-7)
    np.testing.assert_allclose(base.received[1][1], [0.0, 0.8], atol=1e-7)


def test_adapter_requires_reset_and_reset_clears_state():
    env = BoundedDroopResidualEnv(_FakeEnv(), k_droop=10.0, residual_scale=0.10)
    actions = {0: np.zeros(2), 1: np.zeros(2)}
    with pytest.raises(RuntimeError, match="reset"):
        env.step(actions)
    env.reset()
    env.step(actions)
    assert env.last_executed_actions is not None
    env.reset()
    assert env.last_executed_actions is None


def test_train_default_mode_is_identity_and_residual_mode_wraps():
    train = _load_train_module()
    base = _FakeEnv()
    absolute = argparse.Namespace(controller_mode="absolute")
    assert train.wrap_training_controller(base, absolute) is base

    residual = argparse.Namespace(
        controller_mode="bounded_droop_residual",
        droop_k=10.0,
        residual_scale=0.10,
    )
    wrapped = train.wrap_training_controller(base, residual)
    # Some full-suite import-contract tests deliberately reload package
    # modules, so class identity is not stable across the entire process.
    assert wrapped.__class__.__name__ == "BoundedDroopResidualEnv"
    assert wrapped.controller_contract["mode"] == "bounded_droop_residual"


def test_train_cli_exposes_safe_residual_defaults(monkeypatch):
    train = _load_train_module()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "train.py",
            "--algo",
            "td3",
            "--controller-mode",
            "bounded_droop_residual",
            "--no-final-eval",
        ],
    )
    args = train.parse_args()
    assert args.controller_mode == "bounded_droop_residual"
    assert args.droop_k == pytest.approx(10.0)
    assert args.residual_scale == pytest.approx(0.10)
    assert args.final_eval is False


def test_td3_checkpoint_reload_preserves_composed_deterministic_action(tmp_path):
    first = TD3Agent(
        obs_dim=7,
        action_dim=2,
        hidden_sizes=(8, 8, 8, 8),
        batch_size=2,
    )
    path = tmp_path / "agent.pt"
    first.save(str(path))
    second = TD3Agent(
        obs_dim=7,
        action_dim=2,
        hidden_sizes=(8, 8, 8, 8),
        batch_size=2,
    )
    second.load(str(path))
    obs = {0: np.array([0.1, -0.03, 0.0, 0.0, 0.0, 0.0, 0.0])}
    a = bounded_droop_residual_action_fn(
        deterministic_actor_action_fn([first]),
        k_droop=10.0,
        residual_scale=0.10,
    )(0, obs, 1)
    b = bounded_droop_residual_action_fn(
        deterministic_actor_action_fn([second]),
        k_droop=10.0,
        residual_scale=0.10,
    )(0, obs, 1)
    np.testing.assert_array_equal(a[0], b[0])
