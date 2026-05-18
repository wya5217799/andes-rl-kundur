"""Heterogeneous Actor Weighted Ensemble (HAWE) action helpers.

Used by ``scripts/eval_ensemble.py`` (live) and
``scripts/_archive/round_scripts/_r75_ensemble_eval.py`` (R75, archived).
Before R75 each script kept its own private copy of these two functions
(and ``_r75`` further needed a ``sys.path`` hack into ``scripts/`` to
import the copy in ``eval_ensemble.py``). The logic is identical across
all call sites; this module is the single source of truth.

See CONTEXT.md → "HAWE" for the design rationale.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np


def ensemble_action(
    all_actors_per_agent: list[list[Any]],
    agent_idx: int,
    obs_i: np.ndarray,
    agg: str,
    weights: np.ndarray,
) -> np.ndarray:
    """Combine N actors' deterministic actions for one agent.

    Returns a 2-D action array (per-agent action shape).
    """
    acts = np.array([
        actors[agent_idx].select_action(obs_i, deterministic=True)
        for actors in all_actors_per_agent
    ])  # shape (N_actors, 2)
    if agg == "mean":
        return acts.mean(axis=0)
    if agg == "median":
        return np.median(acts, axis=0)
    if agg == "weighted":
        return (weights[:, None] * acts).sum(axis=0)
    raise ValueError(f"unknown agg: {agg}")


def build_ensemble_action_fn(
    all_actors_per_agent: list[list[Any]],
    agg: str,
    weights: np.ndarray,
) -> Callable[[int, dict[int, np.ndarray], int], dict[int, np.ndarray]]:
    """Build an ``action_fn`` (per ``paper_path.ActionFn``) that returns
    the per-step ensembled action for every agent.

    R57-β: at scenario boundaries (``step == 0``), call ``begin_episode``
    on every recurrent actor across every ckpt set so the LSTM hidden
    states reset. Without this, recurrent ckpts evaluated through this
    closure would silently carry hidden state from a prior scenario,
    corrupting the eval. No-op for MLP actors (no ``is_recurrent``).
    """
    def _fn(step: int, obs: dict[int, np.ndarray], n_agents: int) -> dict[int, np.ndarray]:
        if step == 0:
            for actors in all_actors_per_agent:
                for ag in actors:
                    if getattr(ag, "is_recurrent", False):
                        ag.begin_episode()
        return {
            i: ensemble_action(all_actors_per_agent, i, obs[i], agg, weights)
            for i in range(n_agents)
        }
    return _fn
