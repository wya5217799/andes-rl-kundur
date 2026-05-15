"""Reusable trace runners for ANDES Kundur 4-VSG forensic probes.

Pattern emerged across R10/R11/R13/R14/R15/R16/R17:
    1. Construct env (V2/V3/V4 + opt patches), seed, optionally override M0.
    2. reset(delta_u=LS1 or LS2).
    3. Step N times with zero action, accumulate freq + (optionally) Pm/Pgv.
    4. Compute max_df / final_df / settling, return dict.

Without these helpers each probe re-wrote the same 30 lines. Now use:

    from probes.andes_common import (
        run_zero_action_trace, run_h_scan, run_variant_ablation,
        LS1_DELTA_U, PAPER_FIG6,
    )

    out = run_zero_action_trace(
        env_cls=AndesMultiVSGEnvV3, scenario=LS1_DELTA_U,
        h_forced=6.5, n_steps=30,
    )
    print(out["max_df"], out["final_df"])
"""
from __future__ import annotations

from typing import Any, Callable, Iterable

import numpy as np

from andes_rl_kundur.probes.andes_common.paper_constants import (
    DEFAULT_PROBE_SEED,
    DEFAULT_PROBE_STEPS_SHORT,
    PAPER_BENCHMARKS,
)


# ─── Single-shot trace ────────────────────────────────────────────────────


def run_zero_action_trace(
    env_cls,
    scenario: dict,
    *,
    h_forced: float | None = None,
    n_steps: int = DEFAULT_PROBE_STEPS_SHORT,
    seed: int = DEFAULT_PROBE_SEED,
    env_patch: Callable | None = None,
    record_extras: tuple[str, ...] = ("freq_hz", "M_es", "D_es"),
) -> dict[str, Any]:
    """Run one zero-action episode. Returns dict with max_df, final_df, traj.

    Args:
        env_cls: env class (AndesMultiVSGEnvV2 / V3 / V4 / V3_G4Paper, ...).
        scenario: delta_u dict for env.reset (LS1_DELTA_U / LS2_DELTA_U).
        h_forced: if given, override env.M0 = full(2*h_forced) before reset.
        n_steps: how many control steps to take.
        seed: env seed (DEFAULT_PROBE_SEED for cross-probe alignment).
        env_patch: optional fn(env) called after construction, before reset.
            Use for per-instance tweaks (e.g. set GENROU.M[3]=111.15).
        record_extras: which info[] arrays to record in traj. Always records
            "freq_hz" + max_freq_deviation_hz; this list adds optional fields
            like "M_es", "D_es", "P_es", "delta_M", "delta_D".

    Returns:
        dict with:
          - "max_df", "final_df":  float, Hz
          - "traj":                 dict[str, list[list[float]]] per record_extras
          - "df_traj":              list[float] (max|Δf| per step)
          - "n_steps":              int (actual steps run, may be less if TDS failed)
          - "tds_failed":           bool
          - "delta_u":              echo of scenario
    """
    env = env_cls(random_disturbance=False, comm_fail_prob=0.0)
    env.seed(seed)
    if h_forced is not None:
        env.M0 = np.full(env.N_AGENTS, 2.0 * h_forced)
    if env_patch is not None:
        env_patch(env)
    if n_steps > getattr(env, "STEPS_PER_EPISODE", 50):
        env.STEPS_PER_EPISODE = n_steps

    env.reset(delta_u=scenario)
    df_traj: list[float] = []
    traj: dict[str, list] = {k: [] for k in record_extras}
    tds_failed = False
    for _ in range(n_steps):
        actions = {i: np.zeros(2, dtype=np.float32) for i in range(env.N_AGENTS)}
        try:
            _, _, done, info = env.step(actions)
        except Exception:
            tds_failed = True
            break
        if info.get("tds_failed"):
            tds_failed = True
            break
        df_traj.append(float(info["max_freq_deviation_hz"]))
        for k in record_extras:
            v = info.get(k)
            if v is None:
                continue
            arr = np.asarray(v).astype(float)
            traj[k].append(arr.tolist())
        if done:
            break
    try:
        env.close()
    except Exception:
        pass

    out: dict[str, Any] = {
        "delta_u": dict(scenario),
        "h_forced": h_forced,
        "n_steps": len(df_traj),
        "tds_failed": tds_failed,
        "df_traj": df_traj,
        "traj": traj,
    }
    if df_traj:
        out["max_df"] = float(np.max(df_traj))
        out["final_df"] = float(df_traj[-1])
    else:
        out["max_df"] = None
        out["final_df"] = None
    return out


# ─── Trained-policy single-shot trace (R20+ pattern) ─────────────────────


def run_trained_policy_trace(
    env_cls,
    scenario: dict,
    agents: list,
    *,
    h_forced: float | None = None,
    n_steps: int = DEFAULT_PROBE_STEPS_SHORT,
    seed: int = DEFAULT_PROBE_SEED,
    env_patch: Callable | None = None,
    deterministic: bool = True,
    record_extras: tuple[str, ...] = ("freq_hz", "M_es", "D_es"),
) -> dict[str, Any]:
    """Run one episode with trained SAC actors (deterministic by default).

    Mirrors ``run_zero_action_trace`` schema so downstream verdict code can
    treat the two interchangeably. Use this for R20 (reward paradox audit),
    R22 (action distribution), and any post-training behavioural probe.

    Args:
        agents: list of N_AGENTS objects with ``select_action(obs, deterministic)``.
        deterministic: pass-through to actor.select_action.
        Other args: same as ``run_zero_action_trace``.

    Returns:
        Same dict as ``run_zero_action_trace`` plus ``"actions"``: list of
        per-step ndarray-as-list (n_steps, N_AGENTS, action_dim).
    """
    env = env_cls(random_disturbance=False, comm_fail_prob=0.0)
    env.seed(seed)
    if h_forced is not None:
        env.M0 = np.full(env.N_AGENTS, 2.0 * h_forced)
    if env_patch is not None:
        env_patch(env)
    if n_steps > getattr(env, "STEPS_PER_EPISODE", 50):
        env.STEPS_PER_EPISODE = n_steps

    obs = env.reset(delta_u=scenario)
    df_traj: list[float] = []
    traj: dict[str, list] = {k: [] for k in record_extras}
    actions_log: list[list[list[float]]] = []
    tds_failed = False
    for _ in range(n_steps):
        actions = {
            i: agents[i].select_action(obs[i], deterministic=deterministic)
            for i in range(env.N_AGENTS)
        }
        try:
            obs, _, done, info = env.step(actions)
        except Exception:
            tds_failed = True
            break
        if info.get("tds_failed"):
            tds_failed = True
            break
        df_traj.append(float(info["max_freq_deviation_hz"]))
        for k in record_extras:
            v = info.get(k)
            if v is None:
                continue
            arr = np.asarray(v).astype(float)
            traj[k].append(arr.tolist())
        actions_log.append([
            np.asarray(actions[i]).astype(float).tolist()
            for i in range(env.N_AGENTS)
        ])
        if done:
            break
    try:
        env.close()
    except Exception:
        pass

    out: dict[str, Any] = {
        "delta_u": dict(scenario),
        "h_forced": h_forced,
        "n_steps": len(df_traj),
        "tds_failed": tds_failed,
        "df_traj": df_traj,
        "traj": traj,
        "actions": actions_log,
    }
    if df_traj:
        out["max_df"] = float(np.max(df_traj))
        out["final_df"] = float(df_traj[-1])
    else:
        out["max_df"] = None
        out["final_df"] = None
    return out


# ─── H scan (R08/R14 pattern) ─────────────────────────────────────────────


def run_h_scan(
    env_cls,
    scenario: dict,
    h_grid: Iterable[float],
    *,
    n_steps: int = DEFAULT_PROBE_STEPS_SHORT,
    seed: int = DEFAULT_PROBE_SEED,
    env_patch: Callable | None = None,
    paper_benchmark=None,
) -> list[dict]:
    """Run zero-action trace at multiple H values. Returns list of dicts.

    Each dict adds 'paper_ratio' field if paper_benchmark provided.
    """
    results = []
    for h in h_grid:
        r = run_zero_action_trace(
            env_cls, scenario, h_forced=h,
            n_steps=n_steps, seed=seed, env_patch=env_patch,
        )
        r["h"] = float(h)
        if paper_benchmark is not None and r.get("max_df"):
            r["paper_ratio_max_df"] = r["max_df"] / paper_benchmark.max_abs_df_Hz
            if r.get("final_df") is not None:
                r["paper_ratio_final_df"] = r["final_df"] / paper_benchmark.final_abs_df_Hz
        results.append(r)
    return results


# ─── Variant ablation (R15/R16 pattern) ───────────────────────────────────


def run_variant_ablation(
    variants: dict[str, dict],
    *,
    base_env_cls,
    scenario: dict,
    h_forced: float | None = None,
    n_steps: int = DEFAULT_PROBE_STEPS_SHORT,
    seed: int = DEFAULT_PROBE_SEED,
) -> dict[str, dict]:
    """Run variant ablation. Each variant key → {env_cls?, env_patch?}.

    Example::
        run_variant_ablation(
            {"V3_default":   {"env_cls": V3},
             "V3_G4_paper":  {"env_cls": V3, "env_patch": _restore_g4}},
            base_env_cls=V3,
            scenario=LS1_DELTA_U, h_forced=6.5,
        )
    """
    results: dict[str, dict] = {}
    for name, cfg in variants.items():
        env_cls = cfg.get("env_cls", base_env_cls)
        env_patch = cfg.get("env_patch")
        results[name] = run_zero_action_trace(
            env_cls, scenario,
            h_forced=h_forced, n_steps=n_steps, seed=seed,
            env_patch=env_patch,
        )
    return results


# ─── Settling-time helper (R13 pattern, fixed) ────────────────────────────


def compute_settling_time(
    df_traj: list[float] | np.ndarray,
    *,
    dt: float,
    final_df_target: float | None = None,
    band_hz: float = 0.02,
    window_s: float = 0.5,
) -> float:
    """Time after which |df - final_df_target| stays < band_hz over window.

    Args:
        final_df_target: if None, uses last value of df_traj as reference
            (paper Fig.6 convention: settling around droop steady-state).
            If 0.0 supplied, requires full recovery to nominal (rarely paper).

    Returns:
        Settling time in seconds. ``inf`` if never settles in trace window.
    """
    df = np.asarray(df_traj, dtype=float)
    if df.size == 0:
        return float("inf")
    target = final_df_target if final_df_target is not None else float(df[-1])
    deviation = np.abs(df - target)
    n_window = max(1, int(round(window_s / dt)))
    for i in range(len(df) - n_window):
        if np.all(deviation[i : i + n_window] < band_hz):
            return float(i * dt)
    return float("inf")


__all__ = [
    "run_zero_action_trace",
    "run_trained_policy_trace",
    "run_h_scan",
    "run_variant_ablation",
    "compute_settling_time",
]
