"""End-to-end integration test for the R56 LSTM eval path.

Unit tests cover ``load_agents`` (checkpoint_loader), the recurrent
``deterministic_actor_action_fn`` (paper_path), and ``TD3LSTMAgent``
individually. This test wires them together — the way ``score_run.py``
does on the real path — without touching ANDES:

    save → load_agents → deterministic_actor_action_fn → action_fn(...)

Behaviors verified (public-interface only):
1. ``load_agents`` returns ``TD3LSTMAgent`` instances when ckpts carry
   ``algo='td3_lstm'``.
2. The closure resets hidden state at every ``step == 0`` call.
3. Within a scenario, identical obs at consecutive steps produces
   different actions (the defining R56 time-variance property must
   survive the load → eval-loop boundary).
4. Across scenarios (two ``step == 0`` calls separated by within-scenario
   steps), the first-step action of scenario 2 matches the first-step
   action of scenario 1 — proving the reset really happened.
5. Action values are valid float32 vectors in ``[-1, 1]``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _save_4_lstm_ckpts(ckpt_dir: Path, *, obs_dim: int = 7, hidden: int = 64) -> None:
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent

    ckpt_dir.mkdir(parents=True, exist_ok=True)
    for i in range(4):
        # Per-agent torch seed so the 4 agents have distinct LSTM weights
        # (matches the production train.py multi-agent setup).
        torch.manual_seed(100 + i)
        agent = TD3LSTMAgent(
            obs_dim=obs_dim, action_dim=2, hidden_sizes=(hidden,),
        )
        agent.save(str(ckpt_dir / f"agent_{i}_best.pt"))


def test_lstm_eval_path_loads_and_produces_time_varying_actions(tmp_path: Path):
    """Full integration: build ckpts → load_agents → action_fn → step.

    The score_run.py code path is:

        agents = load_agents(ckpt_dir, suffix='best')
        action_fn = deterministic_actor_action_fn(agents)
        for step in range(steps):
            actions = action_fn(step, obs, n_agents)

    This test replays that exact sequence end-to-end."""
    from andes_rl_kundur.agents.checkpoint_loader import load_agents
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent
    from andes_rl_kundur.evaluation.paper_path import (
        deterministic_actor_action_fn,
    )

    _save_4_lstm_ckpts(tmp_path)
    agents = load_agents(tmp_path, suffix="best")
    assert len(agents) == 4
    assert all(isinstance(a, TD3LSTMAgent) for a in agents)

    action_fn = deterministic_actor_action_fn(agents)
    obs = {i: np.zeros(7, dtype=np.float32) for i in range(4)}

    # Scenario 1: 5 steps with constant obs
    actions_scen1 = []
    for step in range(5):
        a = action_fn(step, obs, 4)
        assert set(a.keys()) == {0, 1, 2, 3}
        for i in range(4):
            assert a[i].dtype == np.float32
            assert a[i].shape == (2,)
            assert np.all(a[i] >= -1.0) and np.all(a[i] <= 1.0)
        actions_scen1.append({i: a[i].copy() for i in range(4)})

    # Time-varying property: at least one agent's actions must differ
    # between step 0 and step 4 of the same scenario despite identical
    # obs. Failure here would mean the LSTM hidden state was NOT being
    # carried across steps via the closure.
    deltas = [
        np.linalg.norm(actions_scen1[4][i] - actions_scen1[0][i])
        for i in range(4)
    ]
    assert max(deltas) > 1e-5, (
        f"All 4 agents produced identical step-0 and step-4 actions "
        f"under constant obs — LSTM hidden state not advancing. "
        f"deltas={deltas}"
    )

    # Scenario 2: same closure, step=0 must reset hidden state, so
    # first action of scenario 2 must equal first action of scenario 1.
    actions_scen2_first = action_fn(0, obs, 4)
    for i in range(4):
        np.testing.assert_allclose(
            actions_scen2_first[i], actions_scen1[0][i], atol=1e-6,
            err_msg=(
                f"Agent {i}: scenario-2 step-0 action differs from "
                f"scenario-1 step-0 action — hidden state not reset"
            ),
        )

    # Continue scenario 2 a few steps; must produce time-variance again
    actions_scen2_later = action_fn(3, obs, 4)
    deltas2 = [
        np.linalg.norm(actions_scen2_later[i] - actions_scen2_first[i])
        for i in range(4)
    ]
    assert max(deltas2) > 1e-5
