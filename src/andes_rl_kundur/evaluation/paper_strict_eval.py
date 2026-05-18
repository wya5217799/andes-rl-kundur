"""R58 / R61 paper-strict evaluation primitives.

Implements the **paper's actual evaluation protocol** from Yang et al.,
IEEE TPWRS 2023, Sec.IV-C:

> "the frequency reward used in the test set is *global*, rather than
> the sum of four locally available frequency rewards"
>
> (per-episode reward) = -Σ_t Σ_i (f_i,t - f̄_t)²,
>     f̄_t = Σ_i f_i,t / N

Plus a deterministic 20-scenario test set generator (R58 plan) that
includes the paper's named LS1/LS2 anchors plus 18 random disturbances
drawn to cover the paper's load-step magnitude range.

Used by ``scripts/_archive/round_scripts/_r58_paper_strict_eval.py``
(R58, archived) to re-score historical and paper-strict-trained ckpts
on a comparable footing.

See:
- `docs/paper/kd_4agent_paper_facts.md` §8.2 (paper formula)
- `docs/adr/0002-paper-strict-vs-paper-faithful.md` (terminology)
- `memory/rounds/R58/plan.md`
"""
from __future__ import annotations

from typing import Any

import numpy as np


def compute_global_cum_rf(trace: dict[str, Any]) -> float:
    """Paper Sec.IV-C cumulative global frequency reward.

    ``-Σ_t Σ_i (f_i,t - f̄_t)²`` over the trace's timesteps, where
    ``f̄_t`` is the mean frequency over the N ESS at step t.

    Notes:
        - **No outer ``1/M`` or ``1/N`` normalization** (paper §8.2).
          The ``1/N`` factor only appears INSIDE ``f̄_t``.
        - Equivalent to ``-Σ_t Σ_i (Δf_i,t - Δf̄_t)²`` since subtracting
          the mean kills the constant 50 Hz nominal offset.
        - Returns 0.0 for an empty trace (no steps to sum). Callers
          should also check ``trace.get('tds_failed')`` to distinguish
          "no oscillation" from "TDS aborted early".

    Args:
        trace: A trace dict in the layout produced by
            :func:`andes_rl_kundur.evaluation.paper_path.run_scenario`.
            The relevant key is ``trace["traces"]``, a list of
            per-step dicts where each step has ``"freq_hz"`` = N-element
            list of bus frequencies in Hz.

    Returns:
        Scalar cumulative reward (negative or zero for any non-trivial
        trace; zero only when all ESS frequencies are equal at every t).
    """
    steps = trace.get("traces", [])
    if not steps:
        return 0.0

    cum = 0.0
    for step in steps:
        freqs = np.asarray(step["freq_hz"], dtype=np.float64)
        f_bar = float(freqs.mean())
        # Σ_i (f_i - f̄)² for this step
        cum -= float(np.sum((freqs - f_bar) ** 2))
    return cum


# Paper Sec.IV-C named anchor scenarios.
_ANCHOR_LS1 = {"name": "load_step_1", "delta_u": {"PQ_Bus14": -2.48}}
_ANCHOR_LS2 = {"name": "load_step_2", "delta_u": {"PQ_Bus15": +1.88}}

# PQ bus candidates for random scenarios. AndesMultiVSGEnvV4 exposes
# 4 PQ buses: the two original Kundur loads (Area 1 at Bus 7 = PQ_0,
# Area 2 at Bus 9 = PQ_1) plus the V4-added loads at the ESS3/ES4
# buses (Bus14/Bus15). Earlier R58 draft used "PQ_Bus7..10" which are
# bus names without PQ-load instances → ValueError at reset.
_PQ_BUS_CANDIDATES = ["PQ_0", "PQ_1", "PQ_Bus14", "PQ_Bus15"]
# Magnitude bounds — ±3.0 p.u. on 100 MVA base covers paper LS1
# (-2.48) and LS2 (+1.88) plus surrounding ±300 MW range.
_MAG_MIN_PU = -3.0
_MAG_MAX_PU = 3.0
# Reject random draws below this magnitude (noise, not a meaningful
# disturbance — < 10 MW on 100 MVA base).
_MIN_MAG_PU = 0.1

# evaluate_agents_paper_metric sentinels
# ---------------------------------------
# Per-scenario penalty when TDS aborts before any logged step.
_TDS_FAILURE_PENALTY = -1.0
# Returned when *every* scenario fails — caller treats as "do not save
# eval-tracked best.pt".
_ALL_FAILED_SENTINEL = -1e6


def generate_test_scenarios(
    n: int = 20,
    seed: int = 2026,
    include_anchors: bool = True,
) -> list[dict[str, Any]]:
    """Deterministic R58 test-set generator.

    Args:
        n: Total scenarios to return. When ``include_anchors=True``,
            the first 2 are the paper LS1 + LS2 anchors and the
            remaining ``n - 2`` are random.
        seed: numpy RNG seed for the random subset; fixed across
            R58 evals so paper-strict-pure vs -rescaled vs historical
            ckpts compare on the same disturbance distribution.
        include_anchors: Whether to prepend paper LS1 + LS2 to the
            scenario list. Default True (matches R58 plan).

    Returns:
        List of length ``n``, each item a JSON-serializable dict with
        keys ``"name"`` and ``"delta_u"``. ``delta_u`` is a single-key
        dict mapping PQ bus id to magnitude in p.u. (100 MVA base).

    Raises:
        ValueError: if n is non-positive.
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")

    scenarios: list[dict[str, Any]] = []
    if include_anchors:
        scenarios.append(dict(_ANCHOR_LS1))
        scenarios.append(dict(_ANCHOR_LS2))

    n_random = n - len(scenarios)
    rng = np.random.default_rng(seed)
    for i in range(n_random):
        bus = str(rng.choice(_PQ_BUS_CANDIDATES))
        # Reject draws too close to zero (noise, not a meaningful
        # disturbance) — redraw until magnitude clears the floor.
        while True:
            mag = float(rng.uniform(_MAG_MIN_PU, _MAG_MAX_PU))
            if abs(mag) >= _MIN_MAG_PU:
                break
        # Round to 4 decimals for clean serialization
        mag = round(mag, 4)
        scenarios.append({
            "name": f"random_{i:02d}",
            "delta_u": {bus: mag},
        })

    return scenarios


# Paper-aligned anchor pair (LS1 + LS2). Used by Q-0007's in-training
# eval probe to score the current actors without running the full
# 20-scen test set (which would cost ~60 s per call → kill training).
ANCHOR_PAIR = [dict(_ANCHOR_LS1), dict(_ANCHOR_LS2)]


def evaluate_agents_paper_metric(
    agents: list,
    *,
    config: "V4Config | None" = None,
    scenarios: list[dict[str, Any]] | None = None,
    seed: int = 42,
    steps: int = 50,
) -> float:
    """R61 — in-training paper-metric eval helper for Q-0007.

    Runs deterministic actor rollouts on a small fixed scenario set
    (defaults to paper LS1 + LS2 anchors) and returns the **mean
    cum_rf** (less negative = better policy). Designed for cheap
    repeated calls from inside the training loop.

    Args:
        agents: Sequence of trained agent objects with a deterministic
            ``select_action`` interface.
        config: Optional ``V4Config`` (R58 paper-strict variants).
            When ``None`` the env uses ``V4Config.paper_faithful()``.
        scenarios: Override the default LS1+LS2 anchor pair. Each entry
            is a ``{"name": ..., "delta_u": ...}`` dict matching
            ``generate_test_scenarios`` output.
        seed: Env seed (default 42, matches paper).
        steps: Max steps per scenario (default 50, paper M=50).

    Returns:
        Mean ``cum_rf`` (negative or zero). On any scenario where TDS
        diverges, that scenario contributes the worst observed
        cum_rf so the average penalises instability. Returns a fixed
        sentinel ``-1e6`` if every scenario fails — caller can treat
        this as "do not save eval-tracked best.pt".

    Cost: ~5 s per LS1+LS2 pair on CPU. Designed to be called every
    N episodes (Q-0007's ``--eval-every-n-eps`` knob), where N is
    chosen so eval overhead is < 10 % of training wall.
    """
    from andes_rl_kundur.evaluation.paper_path import (
        deterministic_actor_action_fn,
        run_scenario,
    )

    if scenarios is None:
        scenarios = ANCHOR_PAIR

    action_fn = deterministic_actor_action_fn(agents)
    cum_rfs: list[float] = []
    any_ok = False
    for scen in scenarios:
        trace = run_scenario(
            scen_name=scen["name"],
            delta_u=scen["delta_u"],
            action_fn=action_fn,
            label="eval_probe",
            seed=seed,
            steps=steps,
            config=config,
        )
        if trace.get("traces"):
            cum_rfs.append(compute_global_cum_rf(trace))
            any_ok = True
        else:
            cum_rfs.append(_TDS_FAILURE_PENALTY)

    if not any_ok:
        return _ALL_FAILED_SENTINEL
    return float(np.mean(cum_rfs))
