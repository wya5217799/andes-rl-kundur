"""Paper-path scenario evaluation (the trace-producing half of the paper path).

Centralises the V4 env construction, scenario loop, trace formatting, and
per-step metric accumulation that every eval script previously copied.
The policy is injected via ``action_fn`` so the same loop drives the
no-control baseline, single-actor DDIC, and weighted-ensemble eval.

This module deliberately stops at trace JSON. The 6-axis ranker
(``paper_grade_axes``) consumes those traces in a separate step — eval
produces evidence, ranker analyses it.

Trace JSON shape (one file per scenario):
    {
        "controller":   <label>,
        "scenario":     <scen_name>,
        "env_version":  "v4",
        "cum_rf_total": float,   # negative sum of step_rf
        "max_df":       float,   # max |Δf| in Hz over the run
        "osc":          float,   # accumulated cross-agent freq std
        "n_steps":      int,     # may be < steps if tds_failed
        "traces":       [        # one record per step
            {step, t, freq_hz, f_bar, step_rf, delta_P_es, delta_f_es,
             M_es, D_es, delta_M, delta_D},
            ...
        ],
    }
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

import numpy as np

from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4

if TYPE_CHECKING:
    from andes_rl_kundur.env.andes.v4_config import V4Config


# An ``action_fn`` receives the per-step observation dict and the agent
# count, and returns a dict mapping agent_idx -> 2-D action array.
ActionFn = Callable[[int, dict[int, np.ndarray], int], dict[int, np.ndarray]]


def zero_action_fn(step: int, obs: dict[int, np.ndarray], n_agents: int) -> dict[int, np.ndarray]:
    """No-control baseline: every agent emits zero action every step."""
    return {i: np.zeros(2, dtype=np.float32) for i in range(n_agents)}


def deterministic_actor_action_fn(agents: list) -> ActionFn:
    """Each agent runs its own ``select_action(obs[i], deterministic=True)``."""
    def _fn(step: int, obs: dict[int, np.ndarray], n_agents: int) -> dict[int, np.ndarray]:
        return {
            i: agents[i].select_action(obs[i], deterministic=True)
            for i in range(n_agents)
        }
    return _fn


def run_scenario(
    scen_name: str,
    delta_u: dict[str, Any],
    *,
    action_fn: ActionFn,
    label: str,
    seed: int = 42,
    steps: int = 150,
    extra_keys: dict[str, Any] | None = None,
    config: "V4Config | None" = None,
) -> dict[str, Any]:
    """Run one scenario on the V4 env and return the trace JSON dict.

    Args:
        scen_name: scenario label (e.g. "load_step_1").
        delta_u:   load-step input dict consumed by ``env.reset(delta_u=...)``.
        action_fn: per-step policy (see ``zero_action_fn`` /
                   ``deterministic_actor_action_fn``).
        label:     controller label written to the output dict's
                   ``"controller"`` field.
        seed:      env seed (default 42, matches paper).
        steps:     max episode length (default 150 = 30s @ DT=0.2).
        extra_keys: optional dict merged into the returned record
                    (e.g. ensemble eval adds ``ensemble_agg`` / ``n_actors``).
        config:     optional ``V4Config`` forwarded to the env constructor.
                    If ``None``, the env uses ``V4Config.paper_faithful()``
                    (bit-identical to the historic no-config path). Pass
                    a custom config for variants like ``zero_g4_inertia=False``
                    (R44-β) or ``lambda_smooth=-10.0`` (R50-α).

    Returns:
        Trace JSON dict (see module docstring for shape).
    """
    env = AndesMultiVSGEnvV4(
        random_disturbance=False, comm_fail_prob=0.0, config=config,
    )
    traces: list[dict[str, Any]] = []
    cum_rf = 0.0
    max_df = 0.0
    osc_accum = 0.0
    try:
        env.seed(seed)
        env.STEPS_PER_EPISODE = steps
        obs = env.reset(delta_u=delta_u)

        n_agents = env.N_AGENTS
        f_nom = env.FN

        for step in range(steps):
            actions = action_fn(step, obs, n_agents)
            obs, _rewards, done, info = env.step(actions)
            if info.get("tds_failed"):
                break

            freq_hz = info["freq_hz"].astype(float).tolist()
            delta_f = [(f - f_nom) for f in freq_hz]
            f_bar = float(np.mean(freq_hz))
            step_rf = float(np.mean([(d - (f_bar - f_nom)) ** 2 for d in delta_f]))
            cum_rf -= step_rf
            max_df = max(max_df, float(np.max(np.abs(delta_f))))
            osc_accum += float(np.std(delta_f))

            traces.append({
                "step":       step,
                "t":          float(info["time"]),
                "freq_hz":    freq_hz,
                "f_bar":      f_bar,
                "step_rf":    step_rf,
                "delta_P_es": info["P_es"].astype(float).tolist(),
                "delta_f_es": delta_f,
                "M_es":       info["M_es"].astype(float).tolist(),
                "D_es":       info["D_es"].astype(float).tolist(),
                "delta_M":    info["delta_M"].astype(float).tolist(),
                "delta_D":    info["delta_D"].astype(float).tolist(),
            })
            if done:
                break
    finally:
        # Always release the ANDES TDS session; single-session limit
        # on Windows (see docs/eng-notes/NOTES_ANDES.md) makes a leaked
        # env fatal for the next run.
        env.close()

    record: dict[str, Any] = {
        "controller":   label,
        "scenario":     scen_name,
        "env_version":  "v4",
        "cum_rf_total": cum_rf,
        "max_df":       max_df,
        "osc":          osc_accum,
        "n_steps":      len(traces),
        "traces":       traces,
    }
    if extra_keys:
        record.update(extra_keys)
    return record
