"""R69 v3.0: Unit tests for 11-axis paper_grade_axes ranker.

Covers the 3 new axes added 2026-05-18:
- Axis 9: agent_min_activity (gate agent collapse)
- Axis 10: late_oscillation_inv (gate persistent oscillation)
- Axis 11: agent_P_balance (gate per-agent ΔP monopolization)

Each axis tested with synthetic edge cases plus a real R57-α trace
sanity check.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from andes_rl_kundur.evaluation.paper_grade_axes import (
    AGENT_MIN_ACTIVITY_THRESHOLD,
    LATE_OSCILLATION_STD_THRESHOLD,
    PAPER,
    _agent_min_activity,
    _agent_P_balance,
    _late_oscillation_inv,
    evaluate_trace,
)

# ─── Axis 9: agent_min_activity ──────────────────────────────────────────────

class TestAgentMinActivity:
    def test_all_agents_active_above_threshold_scores_1(self) -> None:
        # all 4 agents contribute well above threshold
        dH = np.tile([60.0, 60.0, 60.0, 60.0], (50, 1))
        dD = np.zeros_like(dH)
        score, min_act, _ = _agent_min_activity(dH, dD)
        assert score == 1.0
        assert min_act == 60.0

    def test_one_agent_dead_scores_0(self) -> None:
        # 3 agents active, 1 fully dead (collapse)
        dH = np.tile([60.0, 60.0, 0.0, 60.0], (50, 1))
        dD = np.zeros_like(dH)
        score, min_act, _ = _agent_min_activity(dH, dD)
        assert score == 0.0
        assert min_act == 0.0

    def test_partial_collapse_scales_linearly(self) -> None:
        # 1 agent at 25 (half threshold), others above
        dH = np.tile([60.0, 60.0, 25.0, 60.0], (50, 1))
        dD = np.zeros_like(dH)
        score, _, _ = _agent_min_activity(dH, dD)
        assert score == pytest.approx(25.0 / AGENT_MIN_ACTIVITY_THRESHOLD)

    def test_dH_and_dD_both_count(self) -> None:
        # weak dH (25) but strong dD (40) → activity = 65, above threshold
        dH = np.tile([25.0] * 4, (50, 1))
        dD = np.tile([40.0] * 4, (50, 1))
        score, min_act, _ = _agent_min_activity(dH, dD)
        assert min_act == 65.0
        assert score == 1.0


# ─── Axis 10: late_oscillation_inv ───────────────────────────────────────────

class TestLateOscillationInv:
    def test_flat_late_time_scores_1(self) -> None:
        t = np.linspace(0, 6, 60)
        df_flat = np.tile([0.04, 0.04, 0.04, 0.04], (60, 1))
        score, late_std = _late_oscillation_inv(t, df_flat)
        assert score == pytest.approx(1.0, abs=1e-9)
        assert late_std == pytest.approx(0.0, abs=1e-9)

    def test_oscillating_late_time_scores_low(self) -> None:
        t = np.linspace(0, 6, 60)
        df_osc = np.tile([0.04] * 4, (60, 1)).astype(float)
        # add 0.02 Hz amplitude sine oscillation in late window (t >= 3)
        late_mask = t >= 3.0
        df_osc[late_mask] += 0.02 * np.sin(20 * t[late_mask])[:, None]
        score, late_std = _late_oscillation_inv(t, df_osc)
        assert late_std > LATE_OSCILLATION_STD_THRESHOLD
        assert score == 0.0  # std >> threshold → clipped to 0

    def test_mild_oscillation_scores_partial(self) -> None:
        t = np.linspace(0, 6, 60)
        df_mild = np.tile([0.04] * 4, (60, 1)).astype(float)
        late_mask = t >= 3.0
        # amplitude 0.005 → std ≈ 0.0035, just above threshold 0.01 partially
        df_mild[late_mask] += 0.005 * np.sin(10 * t[late_mask])[:, None]
        score, late_std = _late_oscillation_inv(t, df_mild)
        assert 0.0 <= score <= 1.0
        # partial: not 0, not 1
        assert score > 0.0

    def test_too_short_trace_scores_1(self) -> None:
        t = np.linspace(0, 1, 5)
        df = np.tile([0.04] * 4, (5, 1))
        score, _ = _late_oscillation_inv(t, df)
        assert score == 1.0  # no late samples available → default safe


# ─── Axis 11: agent_P_balance ────────────────────────────────────────────────

class TestAgentPBalance:
    def test_perfectly_balanced_scores_1(self) -> None:
        P = np.tile([1.0, 1.0, 1.0, 1.0], (20, 1))
        score, P_final = _agent_P_balance(P)
        assert score == 1.0
        assert P_final == [1.0, 1.0, 1.0, 1.0]

    def test_monopolized_scores_low(self) -> None:
        # agent 0 absorbs 4 units, others 0
        P = np.tile([4.0, 0.0, 0.0, 0.0], (20, 1)).astype(float)
        score, _ = _agent_P_balance(P)
        # (max - min) / mean = (4 - 0) / 1 = 4 → 1 - 4 < 0 → clipped to 0
        assert score == 0.0

    def test_slightly_imbalanced_scores_partial(self) -> None:
        # agents 1.0, 1.2, 0.8, 1.0 — range 0.4, mean 1.0
        P = np.tile([1.0, 1.2, 0.8, 1.0], (20, 1))
        score, _ = _agent_P_balance(P)
        # (1.2 - 0.8) / 1.0 = 0.4 → score = 1 - 0.4 = 0.6
        assert score == pytest.approx(0.6, abs=0.01)

    def test_all_zero_scores_1_neutral(self) -> None:
        # all agents zero → mean < eps → return 1.0 (neutral; activity axis catches collapse)
        P = np.zeros((20, 4))
        score, _ = _agent_P_balance(P)
        assert score == 1.0

    def test_signed_P_uses_abs(self) -> None:
        # ΔP can be negative (absorbing vs injecting); balance uses |P|
        P = np.tile([+1.0, -1.0, +1.0, -1.0], (20, 1))
        score, _ = _agent_P_balance(P)
        # |P| = [1, 1, 1, 1] → balanced
        assert score == 1.0


# ─── Integration: evaluate_trace with v3 axes enabled vs disabled ─────────────

class TestIntegrationV3Toggle:
    @pytest.fixture
    def real_lstm_trace_path(self) -> Path:
        # Use an existing R68 LSTM trace if available; skip otherwise.
        root = Path(__file__).resolve().parents[1]
        p = (root / "results" / "research_loop" / "eval_v4_baseline"
             / "r68_w4l_lstm_warmup30_6axis_s51_load_step_1.json")
        if not p.exists():
            pytest.skip(f"trace fixture missing: {p}")
        return p

    def test_v3_adds_3_axes_for_ddic(self, real_lstm_trace_path: Path) -> None:
        ts_v2 = evaluate_trace(
            real_lstm_trace_path, PAPER["load_step_1"],
            is_ddic=True, label="lstm_test", enable_v3_axes=False,
        )
        ts_v3 = evaluate_trace(
            real_lstm_trace_path, PAPER["load_step_1"],
            is_ddic=True, label="lstm_test", enable_v3_axes=True,
        )
        # v3 should add exactly 3 axes (9, 10, 11) for DDIC
        assert len(ts_v3.axes) == len(ts_v2.axes) + 3

        # Names of new axes
        v3_names = [a.name for a in ts_v3.axes[-3:]]
        assert v3_names == ["agent_min_activity", "late_oscillation_inv", "agent_P_balance"]

    def test_v3_skipped_for_non_ddic(self, real_lstm_trace_path: Path) -> None:
        # No-control trace (is_ddic=False): v3 axes should NOT be added.
        ts_noctrl = evaluate_trace(
            real_lstm_trace_path, PAPER["load_step_1"],
            is_ddic=False, label="noctrl_test", enable_v3_axes=True,
        )
        # All axes that are present should NOT include v3-named axes
        names = [a.name for a in ts_noctrl.axes]
        assert "agent_min_activity" not in names
        assert "late_oscillation_inv" not in names
        assert "agent_P_balance" not in names

    def test_v3_overall_lower_when_collapse_detected(self, real_lstm_trace_path: Path) -> None:
        """If v3 axes detect issues, overall score should be lower than v2."""
        ts_v2 = evaluate_trace(
            real_lstm_trace_path, PAPER["load_step_1"],
            is_ddic=True, label="lstm_test", enable_v3_axes=False,
        )
        ts_v3 = evaluate_trace(
            real_lstm_trace_path, PAPER["load_step_1"],
            is_ddic=True, label="lstm_test", enable_v3_axes=True,
        )
        # v3 should not be strictly higher than v2 (new axes can only reduce
        # or maintain via geometric mean with values ≤ 1.0)
        assert ts_v3.overall <= ts_v2.overall + 1e-6
