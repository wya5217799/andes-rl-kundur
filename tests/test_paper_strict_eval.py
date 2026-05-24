"""Tests for R58 paper-strict eval primitives.

Two new functions live in
``src/andes_rl_kundur/evaluation/paper_strict_eval.py``:

1. ``compute_global_cum_rf(trace)`` — paper Sec.IV-C formula:
   ``-Σ_t Σ_i (f_i,t - f̄_t)²``. Returns a single scalar per scenario.
2. ``generate_test_scenarios(n, seed, include_anchors)`` — deterministic
   20-scenario test set: 18 random PQ bus disturbances + 2 anchors
   (paper LS1 / LS2).

These tests cover the metric formula via hand-computed cross-checks
and the generator via determinism + structure checks.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


# ─── compute_global_cum_rf — hand-computed cross-checks ─────────────


def _make_trace(freq_hz_per_step: list[list[float]]) -> dict:
    """Build a minimal trace dict in the shape that run_scenario writes
    out (``paper_path.run_scenario`` JSON layout).

    Each step's frequencies are a list of N freq values per ESS.
    Other fields not used by ``compute_global_cum_rf`` are stubbed.
    """
    traces = []
    for step, freqs in enumerate(freq_hz_per_step):
        traces.append({
            "step": step,
            "t": 0.2 * (step + 1),
            "freq_hz": list(freqs),
            # other fields the run_scenario writes but we don't need:
            "f_bar": float(np.mean(freqs)),
            "step_rf": 0.0,
            "delta_P_es": [0.0] * len(freqs),
            "delta_f_es": [f - 50.0 for f in freqs],
            "M_es": [200.0] * len(freqs),
            "D_es": [100.0] * len(freqs),
            "delta_M": [0.0] * len(freqs),
            "delta_D": [0.0] * len(freqs),
        })
    return {
        "controller": "test",
        "scenario": "test_scen",
        "env_version": "v4",
        "cum_rf_total": 0.0,
        "max_df": 0.0,
        "osc": 0.0,
        "n_steps": len(traces),
        "traces": traces,
    }


def test_compute_global_cum_rf_returns_zero_when_all_synchronized():
    """Paper §2.4.2: when all nodes share the same frequency offset,
    `(f_i - f̄)² = 0` for every i → reward is exactly 0."""
    from andes_rl_kundur.evaluation.paper_strict_eval import compute_global_cum_rf

    trace = _make_trace([[50.0, 50.0, 50.0, 50.0]] * 5)
    assert compute_global_cum_rf(trace) == 0.0

    # Even when offset is non-zero, as long as nodes are equal → 0
    trace_offset = _make_trace([[50.5, 50.5, 50.5, 50.5]] * 5)
    assert compute_global_cum_rf(trace_offset) == 0.0


def test_compute_global_cum_rf_hand_computed_two_step_case():
    """Concrete hand-computed cross-check:
    Step 1: freqs = [50.1, 50.1, 49.9, 49.9]
            mean = 50.0; diffs = [+0.1, +0.1, -0.1, -0.1]
            (f_i - f̄)² = [0.01, 0.01, 0.01, 0.01]; sum = 0.04
    Step 2: freqs = [50.05, 50.0, 49.95, 50.0]
            mean = 50.0; diffs = [+0.05, 0, -0.05, 0]
            (f_i - f̄)² = [0.0025, 0, 0.0025, 0]; sum = 0.005

    Total cum_rf = -(0.04 + 0.005) = -0.045
    """
    from andes_rl_kundur.evaluation.paper_strict_eval import compute_global_cum_rf

    trace = _make_trace([
        [50.1, 50.1, 49.9, 49.9],
        [50.05, 50.0, 49.95, 50.0],
    ])
    cum_rf = compute_global_cum_rf(trace)
    assert abs(cum_rf - (-0.045)) < 1e-12, (
        f"Hand-computed cum_rf=-0.045 mismatch: got {cum_rf}"
    )


def test_compute_global_cum_rf_uses_sum_not_mean():
    """Paper Sec.IV-C: outer sum has NO 1/M or 1/N normalization
    (see §8.2: "no `1/M` or `1/N` — only f̄_t internal uses 1/N").
    Our `paper_path.py:128` step_rf divides by N — we MUST NOT
    inherit that here."""
    from andes_rl_kundur.evaluation.paper_strict_eval import compute_global_cum_rf

    # Single step: freqs = [50.2, 49.8, 50.0, 50.0]
    # mean = 50.0; (f_i - f̄)² = [0.04, 0.04, 0, 0]; sum = 0.08
    # → cum_rf = -0.08 (no /4 factor)
    trace = _make_trace([[50.2, 49.8, 50.0, 50.0]])
    cum_rf = compute_global_cum_rf(trace)
    assert abs(cum_rf - (-0.08)) < 1e-12


def test_compute_global_cum_rf_negative_under_oscillation():
    """Oscillating frequencies (Bus i above mean alternating with Bus j
    below mean) produces strictly negative cum_rf."""
    from andes_rl_kundur.evaluation.paper_strict_eval import compute_global_cum_rf

    trace = _make_trace([
        [50.5, 49.5, 50.5, 49.5],
        [49.5, 50.5, 49.5, 50.5],
        [50.5, 49.5, 50.5, 49.5],
    ])
    cum_rf = compute_global_cum_rf(trace)
    assert cum_rf < 0
    # Each step: (±0.5)² × 4 = 1.0; 3 steps → -3.0
    assert abs(cum_rf - (-3.0)) < 1e-12


def test_compute_global_cum_rf_handles_empty_trace():
    """Empty trace (tds_failed before any step) → returns 0.0 (no
    steps to sum). Caller should also check ``trace['n_steps']==0`` or
    ``trace.get('tds_failed')`` to distinguish "no oscillation" from
    "failed scenario"."""
    from andes_rl_kundur.evaluation.paper_strict_eval import compute_global_cum_rf

    empty_trace = _make_trace([])
    assert compute_global_cum_rf(empty_trace) == 0.0


# ─── generate_test_scenarios — determinism + structure checks ────────


def test_generate_test_scenarios_default_returns_20_with_anchors():
    """Default `n=20, include_anchors=True` returns exactly 20
    scenarios: 18 random + 2 anchors (paper LS1 + LS2). Anchors are
    placed first (indices 0 and 1) to make their identification trivial."""
    from andes_rl_kundur.evaluation.paper_strict_eval import generate_test_scenarios

    scens = generate_test_scenarios(n=20, seed=2026, include_anchors=True)
    assert len(scens) == 20
    # Anchors: paper Sec.IV-C
    assert scens[0]["name"] == "load_step_1"
    assert scens[0]["delta_u"] == {"PQ_Bus14": -2.48}
    assert scens[1]["name"] == "load_step_2"
    assert scens[1]["delta_u"] == {"PQ_Bus15": +1.88}


def test_generate_test_scenarios_is_deterministic_under_fixed_seed():
    """Same seed → bit-identical scenario list. Required for
    reproducible cross-config comparison (paper-strict-pure ckpt
    evaluated on same 20 scenarios as paper-strict-rescaled ckpt)."""
    from andes_rl_kundur.evaluation.paper_strict_eval import generate_test_scenarios

    a = generate_test_scenarios(n=20, seed=2026, include_anchors=True)
    b = generate_test_scenarios(n=20, seed=2026, include_anchors=True)
    assert a == b


def test_generate_test_scenarios_random_scens_cover_paper_magnitudes():
    """Random scenarios should cover the paper LS1 magnitude range
    (-248 MW) and LS2 (+188 MW). Drawing from [-300, +300] MW gives
    both signs and the paper magnitudes within range."""
    from andes_rl_kundur.evaluation.paper_strict_eval import generate_test_scenarios

    scens = generate_test_scenarios(n=20, seed=2026, include_anchors=True)
    random_scens = scens[2:]  # skip the 2 anchors
    assert len(random_scens) == 18
    magnitudes = []
    for s in random_scens:
        # Each delta_u dict has exactly one key (one PQ bus, one Δu)
        magnitudes.extend(s["delta_u"].values())
    # On 100 MVA base, ±3.0 p.u. = ±300 MW. R58 covers paper LS1/LS2
    # in [-3.0, +3.0]. None should exceed.
    assert all(abs(m) <= 3.0 + 1e-12 for m in magnitudes)
    # And we want at least one positive AND one negative (random sign)
    assert any(m > 0 for m in magnitudes)
    assert any(m < 0 for m in magnitudes)


def test_generate_test_scenarios_no_anchors_when_flag_off():
    """With ``include_anchors=False``, all n scenarios are random
    (no paper LS1/LS2 special-case). Used for ablation: how much do
    the named anchors contribute to the headline cum_rf number?"""
    from andes_rl_kundur.evaluation.paper_strict_eval import generate_test_scenarios

    scens = generate_test_scenarios(n=20, seed=2026, include_anchors=False)
    assert len(scens) == 20
    # None should equal the named anchors literally
    anchor_uses = {"load_step_1", "load_step_2"}
    assert not any(s.get("name") in anchor_uses for s in scens)


def test_generate_test_scenarios_returns_jsonable_dicts():
    """Each scenario is a JSON-serializable dict — required so the
    test set can be saved to disk via ``json.dump`` for reproducibility."""
    import json

    from andes_rl_kundur.evaluation.paper_strict_eval import generate_test_scenarios

    scens = generate_test_scenarios(n=20, seed=2026, include_anchors=True)
    # Round-trip
    serialized = json.dumps(scens)
    re_parsed = json.loads(serialized)
    assert re_parsed == scens


def test_generate_test_scenarios_rejects_invalid_n():
    """Negative or zero n is a programmer error."""
    from andes_rl_kundur.evaluation.paper_strict_eval import generate_test_scenarios

    with pytest.raises(ValueError):
        generate_test_scenarios(n=0, seed=2026)
    with pytest.raises(ValueError):
        generate_test_scenarios(n=-5, seed=2026)


def test_generate_test_scenarios_uses_only_buses_that_exist_in_v4_env():
    """Regression for the R58 first-eval failure: the generator's
    ``_PQ_BUS_CANDIDATES`` listed bus IDs (``PQ_Bus7..10``) that
    AndesMultiVSGEnvV4 doesn't expose, causing run-time ValueError on
    eval. AndesMultiVSGEnvV4 has exactly 4 PQ-load instances:
    ``PQ_0`` (Area 1 Bus 7), ``PQ_1`` (Area 2 Bus 9), and the V4-added
    ``PQ_Bus14`` / ``PQ_Bus15`` (ES3/ES4 loads).
    """
    from andes_rl_kundur.evaluation.paper_strict_eval import (
        _PQ_BUS_CANDIDATES,
        generate_test_scenarios,
    )

    valid_pq_ids = {"PQ_0", "PQ_1", "PQ_Bus14", "PQ_Bus15"}
    assert set(_PQ_BUS_CANDIDATES).issubset(valid_pq_ids), (
        f"Generator pulls from {set(_PQ_BUS_CANDIDATES)}, but only "
        f"{valid_pq_ids} actually exist in AndesMultiVSGEnvV4"
    )

    # And the actual generated random scenarios should only ever
    # reference those valid buses (across many seeds for confidence)
    for seed in [2026, 42, 0, 12345]:
        scens = generate_test_scenarios(n=20, seed=seed, include_anchors=True)
        for s in scens:
            for bus in s["delta_u"]:
                assert bus in valid_pq_ids, (
                    f"seed={seed}, scen={s['name']!r}, bus={bus!r} "
                    f"not in valid set {valid_pq_ids}"
                )
