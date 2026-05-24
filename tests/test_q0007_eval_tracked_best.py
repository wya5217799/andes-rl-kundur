"""R61 — Q-0007 eval-tracked best.pt tests.

Three pieces under test:
1. ``TrainingMonitor.update_eval_score`` (firing rule + persistence)
2. ``paper_strict_eval.evaluate_agents_paper_metric`` (helper output)
3. CLI ``--eval-every-n-eps`` flag wiring (presence + default)

The evaluate_agents_paper_metric tests skip if ANDES is unavailable
(Windows host). Monitor tests run everywhere.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.utils.monitor import TrainingMonitor  # noqa: E402

# ─── Monitor.update_eval_score ─────────────────────────────────────


def test_update_eval_score_first_call_always_fires():
    """First call (any finite score) > -inf → fires callback."""
    cb = MagicMock()
    monitor = TrainingMonitor(best_eval_callback=cb)
    fired = monitor.update_eval_score(episode=10, eval_score=-0.5)
    assert fired is True
    cb.assert_called_once_with(10, -0.5)
    assert monitor._best_eval_score == -0.5
    assert monitor._best_eval_episode == 10


def test_update_eval_score_strict_improvement_fires():
    """Worse → doesn't fire; better → fires."""
    cb = MagicMock()
    monitor = TrainingMonitor(best_eval_callback=cb)
    monitor.update_eval_score(0, -0.3)
    cb.reset_mock()
    # Worse score (more negative)
    assert monitor.update_eval_score(5, -0.5) is False
    cb.assert_not_called()
    # Better score (less negative)
    assert monitor.update_eval_score(10, -0.1) is True
    cb.assert_called_once_with(10, -0.1)
    assert monitor._best_eval_episode == 10


def test_update_eval_score_equal_does_not_fire():
    """Strict improvement only — equal score is not 'new best'."""
    cb = MagicMock()
    monitor = TrainingMonitor(best_eval_callback=cb)
    monitor.update_eval_score(0, -0.5)
    cb.reset_mock()
    assert monitor.update_eval_score(5, -0.5) is False
    cb.assert_not_called()


def test_update_eval_score_no_callback_still_tracks():
    """Without a callback, state still updates."""
    monitor = TrainingMonitor()  # no callback
    fired = monitor.update_eval_score(0, -0.3)
    assert fired is True
    assert monitor._best_eval_score == -0.3
    assert monitor._best_eval_episode == 0


def test_update_eval_score_persists_in_checkpoint(tmp_path):
    """save_checkpoint + load_checkpoint round-trip preserves eval state."""
    monitor = TrainingMonitor()
    monitor.update_eval_score(7, -0.123)
    path = tmp_path / "monitor.json"
    monitor.save_checkpoint(str(path))

    data = json.loads(path.read_text())
    assert data["_best_eval_score"] == -0.123
    assert data["_best_eval_episode"] == 7

    restored = TrainingMonitor.load_checkpoint(str(path))
    assert restored._best_eval_score == -0.123
    assert restored._best_eval_episode == 7


def test_update_eval_score_independent_from_best_reward():
    """Reward callback fires separately from eval callback."""
    reward_cb = MagicMock()
    eval_cb = MagicMock()
    monitor = TrainingMonitor(
        best_reward_callback=reward_cb,
        best_eval_callback=eval_cb,
    )
    # Trigger eval improvement without going through log_and_check
    monitor.update_eval_score(5, -0.4)
    eval_cb.assert_called_once_with(5, -0.4)
    reward_cb.assert_not_called()


# ─── CLI flag wiring ────────────────────────────────────────────────


def test_train_cli_has_eval_every_n_eps_flag():
    """--eval-every-n-eps must parse and default to 0 (disabled)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    # parse_args imports a lot; isolate by directly inspecting the
    # parser shape via argparse introspection on a fresh import.
    import importlib

    train_mod = importlib.import_module("train")

    # Build parser by calling parse_args with no-arg vector via patching
    import unittest.mock as mock
    with mock.patch.object(sys, "argv", ["train.py"]):
        ns = train_mod.parse_args()
    assert hasattr(ns, "eval_every_n_eps")
    assert ns.eval_every_n_eps == 0


# ─── evaluate_agents_paper_metric helper ────────────────────────────


def test_evaluate_agents_paper_metric_returns_float():
    """Helper returns a scalar cum_rf when called with mock actors.

    Bypasses ANDES by mocking ``run_scenario`` to return a synthetic
    trace.
    """
    import unittest.mock as mock

    fake_trace = {
        "traces": [
            {"freq_hz": [50.0, 50.05, 49.95, 50.0]},
            {"freq_hz": [50.0, 50.10, 49.90, 50.0]},
        ],
    }

    with mock.patch(
        "andes_rl_kundur.evaluation.paper_path.run_scenario",
        return_value=fake_trace,
    ):
        from andes_rl_kundur.evaluation.paper_strict_eval import (
            evaluate_agents_paper_metric,
        )

        # Mock agents — only need to exist; mocked run_scenario ignores them.
        mock_agents = [MagicMock() for _ in range(4)]
        for ag in mock_agents:
            ag.is_recurrent = False
        score = evaluate_agents_paper_metric(mock_agents)
    # Two scenarios (LS1 + LS2), both with same trace, cum_rf < 0
    assert isinstance(score, float)
    assert score < 0  # frequency disagreement → negative


def test_evaluate_agents_paper_metric_tds_failure_returns_sentinel():
    """If every scenario has no traces, returns -1e6 sentinel."""
    import unittest.mock as mock

    empty_trace = {"traces": []}

    with mock.patch(
        "andes_rl_kundur.evaluation.paper_path.run_scenario",
        return_value=empty_trace,
    ):
        from andes_rl_kundur.evaluation.paper_strict_eval import (
            evaluate_agents_paper_metric,
        )
        mock_agents = [MagicMock() for _ in range(4)]
        for ag in mock_agents:
            ag.is_recurrent = False
        score = evaluate_agents_paper_metric(mock_agents)
    assert score == -1e6


def test_evaluate_agents_paper_metric_uses_anchor_pair_by_default():
    """Default scenarios = paper LS1 + LS2 anchors (2 calls to run_scenario)."""
    import unittest.mock as mock

    fake_trace = {"traces": [{"freq_hz": [50.0, 50.0, 50.0, 50.0]}]}

    with mock.patch(
        "andes_rl_kundur.evaluation.paper_path.run_scenario",
        return_value=fake_trace,
    ) as mock_run:
        from andes_rl_kundur.evaluation.paper_strict_eval import (
            evaluate_agents_paper_metric,
        )
        mock_agents = [MagicMock() for _ in range(4)]
        for ag in mock_agents:
            ag.is_recurrent = False
        evaluate_agents_paper_metric(mock_agents)
    assert mock_run.call_count == 2  # LS1 + LS2
    call_names = [c.kwargs["scen_name"] for c in mock_run.call_args_list]
    assert "load_step_1" in call_names
    assert "load_step_2" in call_names
