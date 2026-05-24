"""Tests for ``algo_name`` introspection on agents + Monitor's
algo-aware log line (R50 optimization F).

Pre-R50 the monitor printed ``"SAC: mean critic_loss=..."`` for every
algorithm because the string was hardcoded. Confusing during the R48 /
R49 TD3 runs where the loss displayed was actually TD3's critic loss.

Behaviors under test:
1. TD3Agent exposes ``algo_name == 'td3'``.
2. SACAgent exposes ``algo_name == 'sac'``.
3. TrainingMonitor accepts an ``algo_name`` constructor kwarg and the
   print-loss line uses it (verified via capsys).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.sac import SACAgent  # noqa: E402
from andes_rl_kundur.agents.td3 import TD3Agent  # noqa: E402
from andes_rl_kundur.utils.monitor import TrainingMonitor  # noqa: E402


def test_td3_agent_algo_name():
    agent = TD3Agent(obs_dim=7, action_dim=2, hidden_sizes=(32, 32, 32, 32), device="cpu")
    assert agent.algo_name == "td3"


def test_sac_agent_algo_name():
    agent = SACAgent(obs_dim=7, action_dim=2, hidden_sizes=(32, 32, 32, 32), device="cpu")
    assert agent.algo_name == "sac"


def _seed_monitor(monitor: TrainingMonitor) -> None:
    """Populate the minimum data needed to drive _log_summary without
    going through log_and_check (which requires action arrays, etc.)."""
    monitor._episode_rewards.append(-7.0)
    monitor._reward_components.append({"r_f": -7.0})
    monitor._action_stats.append({
        "per_agent_mean": [0.0, 0.0, 0.0, 0.0],
        "per_agent_std": [0.5, 0.5, 0.5, 0.5],
    })
    monitor._env_health.append({"tds_failed": False, "max_freq_deviation_hz": 0.13})
    monitor._sac_losses.append([{"critic_loss": 0.5}])


def test_monitor_log_uses_algo_name_for_td3(capsys):
    """Monitor constructed with ``algo_name='td3'`` must print 'TD3:' not 'SAC:'
    when it emits the per-episode loss summary."""
    monitor = TrainingMonitor(
        calibration_episodes=1, log_interval=1, algo_name="td3",
    )
    _seed_monitor(monitor)
    monitor._log_summary(episode=0)
    out = capsys.readouterr().out
    assert "TD3:" in out, f"expected 'TD3:' in monitor output, got: {out!r}"
    assert "SAC:" not in out, f"unexpected 'SAC:' label for TD3 monitor: {out!r}"


def test_monitor_log_default_algo_name_is_sac(capsys):
    """Default (no algo_name kwarg) keeps the historic 'SAC:' string for
    backward compat with old training logs."""
    monitor = TrainingMonitor(calibration_episodes=1, log_interval=1)
    _seed_monitor(monitor)
    monitor._log_summary(episode=0)
    out = capsys.readouterr().out
    assert "SAC:" in out
