"""Regression tests for ``src/andes_rl_kundur/evaluation/paper_path.py``.

These hit the public ``run_scenario`` interface with a fake env so we can
exercise failure modes (action_fn raising, env.step raising) without
booting a real ANDES TDS session — and assert that ``env.close()`` runs
even on the unhappy path.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class _FakeEnv:
    """Minimal stand-in for AndesMultiVSGEnvV4 — enough surface for
    ``paper_path.run_scenario`` to drive it one step."""

    N_AGENTS = 4
    FN = 50.0
    STEPS_PER_EPISODE = 0

    def __init__(self, *_, **__):
        self.closed = False

    def seed(self, _seed) -> None:
        pass

    def reset(self, *, delta_u=None):
        return {i: np.zeros(4, dtype=np.float32) for i in range(self.N_AGENTS)}

    def step(self, actions):
        info = {
            "tds_failed": False,
            "time": 0.2,
            "freq_hz": np.full(self.N_AGENTS, self.FN, dtype=np.float64),
            "P_es": np.zeros(self.N_AGENTS, dtype=np.float64),
            "M_es": np.zeros(self.N_AGENTS, dtype=np.float64),
            "D_es": np.zeros(self.N_AGENTS, dtype=np.float64),
            "delta_M": np.zeros(self.N_AGENTS, dtype=np.float64),
            "delta_D": np.zeros(self.N_AGENTS, dtype=np.float64),
        }
        rewards = {i: 0.0 for i in range(self.N_AGENTS)}
        obs = {i: np.zeros(4, dtype=np.float32) for i in range(self.N_AGENTS)}
        return obs, rewards, False, info

    def close(self) -> None:
        self.closed = True


def test_run_scenario_closes_env_on_action_fn_exception(monkeypatch):
    """B1 regression: if ``action_fn`` raises, ``env.close()`` must still run.

    Without ``try/finally`` around the eval loop, an exception leaves the
    ANDES TDS session open — fatal on a single-session Windows workstation
    (per docs/eng-notes/NOTES_ANDES.md).
    """
    from andes_rl_kundur.evaluation import paper_path

    fake_env = _FakeEnv()
    monkeypatch.setattr(
        paper_path, "AndesMultiVSGEnvV4", lambda *a, **k: fake_env,
    )

    def raising_action_fn(step, obs, n_agents):
        raise RuntimeError("simulated policy crash")

    with pytest.raises(RuntimeError, match="simulated policy crash"):
        paper_path.run_scenario(
            "load_step_1", {"line.Line_5.u": 0.0},
            action_fn=raising_action_fn,
            label="test",
            seed=42,
            steps=10,
        )

    assert fake_env.closed, "env.close() must run even when action_fn raises"


def test_run_scenario_closes_env_on_env_step_exception(monkeypatch):
    """Same guarantee when env.step itself raises mid-loop."""
    from andes_rl_kundur.evaluation import paper_path

    fake_env = _FakeEnv()

    call_count = [0]
    original_step = fake_env.step

    def flaky_step(actions):
        call_count[0] += 1
        if call_count[0] == 3:
            raise RuntimeError("simulated TDS crash")
        return original_step(actions)

    fake_env.step = flaky_step
    monkeypatch.setattr(
        paper_path, "AndesMultiVSGEnvV4", lambda *a, **k: fake_env,
    )

    def zero_action_fn(step, obs, n_agents):
        return {i: np.zeros(2, dtype=np.float32) for i in range(n_agents)}

    with pytest.raises(RuntimeError, match="simulated TDS crash"):
        paper_path.run_scenario(
            "load_step_1", {"line.Line_5.u": 0.0},
            action_fn=zero_action_fn,
            label="test",
            seed=42,
            steps=10,
        )

    assert fake_env.closed


def test_run_scenario_forwards_config_to_env(monkeypatch):
    """R50 opt C: run_scenario must accept a V4Config and forward it to
    AndesMultiVSGEnvV4 constructor — replaces the R44-β inline-script
    workaround for paper-faithful G4 / lambda_smooth / R03 obs experiments.
    """
    from andes_rl_kundur.evaluation import paper_path
    from andes_rl_kundur.env.andes.v4_config import V4Config

    captured: dict[str, object] = {}
    fake_env = _FakeEnv()

    def factory(*a, **k):
        captured.update(k)
        return fake_env

    monkeypatch.setattr(paper_path, "AndesMultiVSGEnvV4", factory)

    def zero_action_fn(step, obs, n_agents):
        return {i: np.zeros(2, dtype=np.float32) for i in range(n_agents)}

    custom_cfg = V4Config(zero_g4_inertia=False, lambda_smooth=-5.0)
    paper_path.run_scenario(
        "load_step_1", {"line.Line_5.u": 0.0},
        action_fn=zero_action_fn,
        label="test",
        seed=42,
        steps=1,
        config=custom_cfg,
    )

    assert "config" in captured, "AndesMultiVSGEnvV4 must receive a config kwarg"
    assert captured["config"] is custom_cfg, (
        f"forwarded config must be the same V4Config object; "
        f"got {captured['config']!r}"
    )
