"""R71 v3.1 — Unit tests for multiplicative-gating aggregation.

v3.1 changes the overall score from:
    geo_mean(all 11 axes)             [v3.0]
to:
    geo_mean(axes 1-8) × min(axes 9, 10, 11)   [v3.1]

Motivation (CLM-0119): v3.0 allowed strong axes 1-8 to dilute gating axes 9-11.
v3.1 ensures any single gating axis with score N caps overall at
N × geo_mean(continuous), matching paper-figure-quality intuition.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from andes_rl_kundur.evaluation.paper_grade_axes import PAPER, evaluate_trace


@pytest.fixture
def real_lstm_trace_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    p = (root / "results" / "research_loop" / "eval_v4_baseline"
         / "r68_w2_lstm_tau001_6axis_s51_load_step_1.json")
    if not p.exists():
        pytest.skip(f"trace fixture missing: {p}")
    return p


@pytest.fixture
def collapsed_td3_trace_path() -> Path:
    """R67 TD3 SOTA trace with agent collapse (min_act=0.07)."""
    root = Path(__file__).resolve().parents[1]
    p = (root / "results" / "research_loop" / "eval_v4_baseline"
         / "r67_w2a_td3_combo_tau001_6axis_s50_load_step_1.json")
    if not p.exists():
        pytest.skip(f"trace fixture missing: {p}")
    return p


class TestV31MultiplicativeGating:
    def test_v31_overall_lower_than_v3_when_gating_axis_low(
        self, real_lstm_trace_path: Path
    ) -> None:
        """v3.1 should produce overall score ≤ v3.0 geo_mean equivalent for
        any controller with non-perfect gating axes."""
        # Compute under v3.1 (current default)
        ts_v31 = evaluate_trace(
            real_lstm_trace_path, PAPER["load_step_1"],
            is_ddic=True, label="lstm_test", enable_v3_axes=True,
        )
        # Compute v2.x equivalent (no v3 axes)
        ts_v2 = evaluate_trace(
            real_lstm_trace_path, PAPER["load_step_1"],
            is_ddic=True, label="lstm_test", enable_v3_axes=False,
        )
        # v3.1 overall ≤ v2.x overall (gating can only reduce)
        # Specifically: v3.1 = geo(1..8) × min(9,10,11) ≤ geo(1..8) = v2
        assert ts_v31.overall <= ts_v2.overall + 1e-6

    def test_v31_gates_agent_collapse(self, collapsed_td3_trace_path: Path) -> None:
        """TD3 R67 has min_act ≈ 0.07 → v3.1 overall must be heavily penalized."""
        ts = evaluate_trace(
            collapsed_td3_trace_path, PAPER["load_step_1"],
            is_ddic=True, label="td3_collapse", enable_v3_axes=True,
        )
        # min_act is in axis 9
        axes_by_name = {a.name: a for a in ts.axes}
        assert "agent_min_activity" in axes_by_name
        min_act_score = axes_by_name["agent_min_activity"].score
        # LS1 has min_act ≈ 0.32 (vs LS2's 0.07 — matrix shows min across LS1+LS2)
        # Either way: TD3 R67 is far from "all 4 agents active" (1.0)
        assert min_act_score < 0.5, f"TD3 collapse axis score should be < 0.5, got {min_act_score}"
        # v3.1 overall should be at most min_act × continuous_geo
        # (cannot exceed min_act × 1.0 = min_act since geo_mean ≤ 1)
        assert ts.overall <= min_act_score + 0.01, (
            f"v3.1 overall {ts.overall:.3f} should be capped by min_act {min_act_score:.3f}"
        )

    def test_v31_aggregation_formula(self, real_lstm_trace_path: Path) -> None:
        """Verify v3.1 overall = geo_mean(continuous) × min(gating) exactly."""
        ts = evaluate_trace(
            real_lstm_trace_path, PAPER["load_step_1"],
            is_ddic=True, label="lstm_test", enable_v3_axes=True,
        )
        gating_names = {"agent_min_activity", "late_oscillation_inv", "agent_P_balance"}
        continuous = [a.score for a in ts.axes if a.name not in gating_names]
        gating = [a.score for a in ts.axes if a.name in gating_names]
        if continuous and gating:
            expected = math.exp(
                sum(math.log(max(s, 0.01)) for s in continuous) / len(continuous)
            ) * min(gating)
            assert abs(ts.overall - expected) < 1e-6

    def test_v31_disabled_falls_back_to_v2_geo(self, real_lstm_trace_path: Path) -> None:
        """enable_v3_axes=False should use plain geo_mean over all included axes."""
        ts_disabled = evaluate_trace(
            real_lstm_trace_path, PAPER["load_step_1"],
            is_ddic=True, label="lstm_test", enable_v3_axes=False,
        )
        # No gating axes in disabled mode → plain geo_mean
        expected = math.exp(
            sum(math.log(max(a.score, 0.01)) for a in ts_disabled.axes) / len(ts_disabled.axes)
        )
        assert abs(ts_disabled.overall - expected) < 1e-6

    def test_v31_with_zero_p_balance_drives_overall_low(self) -> None:
        """Synthetic case: P_balance=0 should drive overall to near-0 regardless
        of how strong axes 1-8 are."""
        # Build a trace that has high axes 1-8 but P_balance=0
        # We need to construct a JSON with the right structure
        import tempfile

        import numpy as np

        T = 60
        t_arr = np.linspace(0, 6, T)
        # Perfect frequency control: Δf ≈ 0 everywhere
        df = np.zeros((T, 4))
        # But all the ΔP absorbed by agent 0 only (monopolization)
        P = np.zeros((T, 4))
        P[10:, 0] = 1.0  # only agent 0 has output
        # Modest H and D dynamics (avoids axis 9 collapse)
        M = np.tile([100.0, 100.0, 100.0, 100.0], (T, 1))
        M[10:, :] += 60.0  # all agents move 60 units
        D = np.tile([40.0, 40.0, 40.0, 40.0], (T, 1))

        traces_list = []
        for i in range(T):
            traces_list.append({
                "t": float(t_arr[i]),
                "delta_f_es": df[i].tolist(),
                "M_es": M[i].tolist(),
                "D_es": D[i].tolist(),
                "delta_P_es": P[i].tolist(),
                "delta_M": [60.0] * 4,
                "delta_D": [0.0] * 4,
            })
        trace_json = {
            "scenario": "load_step_1",
            "traces": traces_list,
            "tds_failed": False,
            "n_steps": T,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
            json.dump(trace_json, tf)
            tmp_path = Path(tf.name)

        try:
            ts = evaluate_trace(
                tmp_path, PAPER["load_step_1"],
                is_ddic=True, label="synthetic_monopoly", enable_v3_axes=True,
            )
            axes_by_name = {a.name: a for a in ts.axes}
            # P_balance should be near 0
            assert axes_by_name["agent_P_balance"].score < 0.2
            # And overall should be capped by it (v3.1 gating)
            assert ts.overall < 0.2, (
                f"v3.1 overall {ts.overall:.3f} should be capped by P_balance penalty"
            )
        finally:
            tmp_path.unlink(missing_ok=True)
