"""Tests for the ensemble action-fn's recurrent-actor reset hook.

R57-β: ``build_ensemble_action_fn`` must call ``begin_episode`` on every
recurrent actor at scenario boundaries (``step == 0``). The analog hook
in ``paper_path.deterministic_actor_action_fn`` was added in R56, but
the parallel code path here was not — silent miscompile risk for
HAWE-LSTM ensembles.

R78: tests now import the library function directly. The previous
``scripts/eval_ensemble.py:_ensemble_action_fn`` alias was deleted along
with the ``sys.path`` hack into ``scripts/``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.ensemble import build_ensemble_action_fn  # noqa: E402


def test_ensemble_action_fn_resets_recurrent_at_scenario_boundary():
    """When ``build_ensemble_action_fn`` is reused across scenarios, the
    closure must call ``begin_episode()`` at ``step == 0`` on each
    recurrent agent across every ckpt set."""
    class StubLSTMAgent:
        is_recurrent = True

        def __init__(self):
            self.begin_called = 0

        def begin_episode(self):
            self.begin_called += 1

        def select_action(self, obs, deterministic=False):
            return np.zeros(2, dtype=np.float32)

    class StubMLPAgent:
        # No ``is_recurrent`` attribute.
        def __init__(self):
            self.calls = 0

        def select_action(self, obs, deterministic=False):
            self.calls += 1
            return np.zeros(2, dtype=np.float32)

    # 2 ckpt sets × 4 agents each (matching N_AGENTS=4)
    set_a = [StubLSTMAgent() for _ in range(4)]
    set_b = [StubMLPAgent() for _ in range(4)]
    all_actors = [set_a, set_b]
    weights = np.array([0.5, 0.5])
    fn = build_ensemble_action_fn(all_actors, agg="mean", weights=weights)

    obs = {i: np.zeros(7, dtype=np.float32) for i in range(4)}

    # Scenario 1: step 0, 1, 2
    fn(0, obs, 4)
    fn(1, obs, 4)
    fn(2, obs, 4)
    assert all(a.begin_called == 1 for a in set_a), (
        "All 4 LSTM agents in set A should have begin_episode called once"
    )

    # Scenario 2: step 0 again — each LSTM agent gets another reset
    fn(0, obs, 4)
    assert all(a.begin_called == 2 for a in set_a)

    # MLP set never gets begin_episode (no attribute); but select_action
    # was still called: 3 + 1 = 4 calls per agent.
    assert all(a.calls == 4 for a in set_b)


def test_ensemble_action_fn_handles_mixed_recurrent_and_mlp_sets():
    """Edge case: one ckpt set is LSTM, another is MLP — only the LSTM
    set should see begin_episode calls. The MLP set is silently skipped
    via the ``is_recurrent`` hasattr guard."""
    class StubLSTMAgent:
        is_recurrent = True

        def __init__(self):
            self.begin_called = 0

        def begin_episode(self):
            self.begin_called += 1

        def select_action(self, obs, deterministic=False):
            return np.full(2, 0.5, dtype=np.float32)

    class StubMLPAgent:
        is_recurrent = False  # explicitly False this time

        def select_action(self, obs, deterministic=False):
            return np.full(2, 0.3, dtype=np.float32)

    set_lstm = [StubLSTMAgent() for _ in range(4)]
    set_mlp = [StubMLPAgent() for _ in range(4)]
    all_actors = [set_lstm, set_mlp]
    weights = np.array([0.5, 0.5])
    fn = build_ensemble_action_fn(all_actors, agg="weighted", weights=weights)
    obs = {i: np.zeros(7, dtype=np.float32) for i in range(4)}

    fn(0, obs, 4)
    fn(0, obs, 4)
    fn(0, obs, 4)
    assert all(a.begin_called == 3 for a in set_lstm)
    # MLP path has no begin_episode method, but no crash either —
    # the ``getattr(ag, "is_recurrent", False)`` guard works for both
    # missing-attribute and explicit-False cases.


def test_ensemble_action_fn_does_not_reset_mid_scenario():
    """begin_episode must NOT be called at step > 0. Otherwise the
    hidden state resets every step, defeating the LSTM."""
    class StubLSTMAgent:
        is_recurrent = True

        def __init__(self):
            self.begin_called = 0

        def begin_episode(self):
            self.begin_called += 1

        def select_action(self, obs, deterministic=False):
            return np.zeros(2, dtype=np.float32)

    actors = [StubLSTMAgent() for _ in range(4)]
    fn = build_ensemble_action_fn([actors], agg="mean", weights=np.array([1.0]))
    obs = {i: np.zeros(7, dtype=np.float32) for i in range(4)}

    fn(0, obs, 4)
    for step in range(1, 100):
        fn(step, obs, 4)

    # Exactly one reset (at step 0), not 100
    assert all(a.begin_called == 1 for a in actors)
