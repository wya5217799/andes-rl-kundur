"""TDD slices for ``scenarios.kundur.training_checks`` (R42 / C4).

Each test feeds a synthetic accumulated state into a real ``TrainingMonitor``
via ``log_and_check`` and asserts the corresponding Check triggers as
expected. Tests use the public ``log_and_check`` API and the new public
read-only properties on the monitor — no private-state poking.

To keep the legacy 12 baked-in checks quiet during fixture build-up, every
test passes ``calibration_episodes`` larger than the number of synthetic
episodes fed: the legacy ``_run_all_checks`` only fires *after* calibration
completes, so the legacy checks stay silent and only the explicit
``check.run(monitor, ...)`` calls in each test are exercised.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _feed_episodes(
    monitor,
    n_episodes: int,
    *,
    actions_per_step: np.ndarray,
    rewards: float = -100.0,
    components: dict[str, float] | None = None,
    tds_failed: bool = False,
    max_freq_deviation_hz: float = 0.1,
    per_agent_rewards: dict[int, float] | None = None,
    max_power_swing: float | None = None,
    sac_losses: list[dict[str, float]] | None = None,
) -> None:
    """Helper: drive ``n_episodes`` of synthetic data into the monitor.

    ``actions_per_step`` shape = (steps, n_agents, action_dim).
    """
    info_base: dict = {
        "tds_failed": tds_failed,
        "max_freq_deviation_hz": max_freq_deviation_hz,
    }
    if max_power_swing is not None:
        info_base["max_power_swing"] = max_power_swing
    if components is None:
        components = {"r_f": rewards * 0.6, "r_h": rewards * 0.2, "r_d": rewards * 0.2}
    if per_agent_rewards is None:
        per_agent_rewards = {i: rewards / 4 for i in range(actions_per_step.shape[1])}
    for ep in range(n_episodes):
        monitor.log_and_check(
            episode=ep,
            rewards=rewards,
            reward_components=components,
            actions=actions_per_step,
            info=dict(info_base),
            per_agent_rewards=dict(per_agent_rewards),
            sac_losses=sac_losses,
        )


def test_action_collapse_check_triggers_when_window_std_stays_below_threshold():
    """Tracer: ActionCollapseCheck.run(monitor, episode) returns
    ``triggered=True`` when every agent's per-episode action std is below the
    configured threshold for the entire sliding window."""
    from andes_rl_kundur.scenarios.kundur.training_checks import ActionCollapseCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)  # silence legacy checks

    # 60 episodes, every step is a near-zero action for every agent.
    # The monitor records per-episode std via np.std(actions, axis=0).mean(-1).
    # With identical actions across steps, the std is exactly zero.
    flat_zero_actions = np.zeros((10, 4, 2), dtype=np.float32)
    _feed_episodes(monitor, 60, actions_per_step=flat_zero_actions)

    # Pin the threshold; do not let auto-calibration override (calibration
    # never completed because calibration_episodes=999).
    check = ActionCollapseCheck(std_threshold=0.01, window=50)
    result = check.run(monitor, episode={})

    assert result.triggered, f"expected trigger, got: {result}"
    assert result.name == "action_collapse"
    assert result.severity == "warn"
    assert "std" in result.message.lower() or "collapse" in result.message.lower()


def test_action_collapse_check_does_not_trigger_with_healthy_actions():
    """Negative: when actions vary step-to-step (healthy exploration), the
    per-episode std is high enough that the check stays quiet."""
    from andes_rl_kundur.scenarios.kundur.training_checks import ActionCollapseCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)

    rng = np.random.default_rng(0)
    varied_actions = rng.uniform(-0.5, 0.5, size=(10, 4, 2)).astype(np.float32)
    _feed_episodes(monitor, 60, actions_per_step=varied_actions)

    check = ActionCollapseCheck(std_threshold=0.01, window=50)
    result = check.run(monitor, episode={})
    assert not result.triggered, f"unexpected trigger: {result}"


def test_reward_component_ratio_check_triggers_when_dominant_below_threshold():
    """RewardComponentRatioCheck triggers when the configured dominant
    component (default 'r_f') is below the dominance fraction of total
    absolute reward components."""
    from andes_rl_kundur.scenarios.kundur.training_checks import RewardComponentRatioCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    # r_f is only 10% of total |r|; threshold is 0.5 -> should trigger.
    _feed_episodes(
        monitor, 1,
        actions_per_step=np.zeros((10, 4, 2), dtype=np.float32),
        components={"r_f": -10.0, "r_h": -45.0, "r_d": -45.0},
    )
    check = RewardComponentRatioCheck()
    result = check.run(monitor, episode={})
    assert result.triggered, f"expected trigger, got: {result}"
    assert result.name == "reward_component_ratio"
    assert "r_f" in result.message


def test_reward_component_ratio_check_quiet_when_dominant_above_threshold():
    from andes_rl_kundur.scenarios.kundur.training_checks import RewardComponentRatioCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    # r_f is 80% of total |r|; threshold is 0.5 -> should NOT trigger.
    _feed_episodes(
        monitor, 1,
        actions_per_step=np.zeros((10, 4, 2), dtype=np.float32),
        components={"r_f": -80.0, "r_h": -10.0, "r_d": -10.0},
    )
    check = RewardComponentRatioCheck()
    result = check.run(monitor, episode={})
    assert not result.triggered, f"unexpected trigger: {result}"


def test_action_saturation_check_triggers_when_most_actions_at_boundary():
    """ActionSaturationCheck triggers when the most recent episode's
    saturation ratio (fraction of |a| > 0.95) exceeds threshold."""
    from andes_rl_kundur.scenarios.kundur.training_checks import ActionSaturationCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    # All actions saturated near +1.0 -> saturation_ratio ≈ 1.0
    sat_actions = np.full((10, 4, 2), 0.99, dtype=np.float32)
    _feed_episodes(monitor, 1, actions_per_step=sat_actions)
    check = ActionSaturationCheck(threshold=0.8)
    result = check.run(monitor, episode={})
    assert result.triggered, f"expected trigger, got: {result}"
    assert result.name == "action_saturation"


def test_action_saturation_check_quiet_when_actions_in_interior():
    from andes_rl_kundur.scenarios.kundur.training_checks import ActionSaturationCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    mid_actions = np.full((10, 4, 2), 0.3, dtype=np.float32)
    _feed_episodes(monitor, 1, actions_per_step=mid_actions)
    check = ActionSaturationCheck(threshold=0.8)
    result = check.run(monitor, episode={})
    assert not result.triggered


def test_reward_plateau_check_triggers_when_no_improvement_over_window():
    """RewardPlateauCheck triggers when (max-min)/|min| over the window
    falls below improvement_threshold."""
    from andes_rl_kundur.scenarios.kundur.training_checks import RewardPlateauCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    flat_actions = np.zeros((10, 4, 2), dtype=np.float32)
    # 100 episodes all at reward = -100.0 -> improvement = 0% < 1% threshold.
    _feed_episodes(monitor, 100, actions_per_step=flat_actions, rewards=-100.0)
    check = RewardPlateauCheck(window=100, improvement_threshold=0.01)
    result = check.run(monitor, episode={})
    assert result.triggered
    assert result.name == "reward_plateau"


def test_reward_plateau_check_quiet_when_window_too_short():
    from andes_rl_kundur.scenarios.kundur.training_checks import RewardPlateauCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    flat_actions = np.zeros((10, 4, 2), dtype=np.float32)
    _feed_episodes(monitor, 50, actions_per_step=flat_actions, rewards=-100.0)
    check = RewardPlateauCheck(window=100, improvement_threshold=0.01)
    result = check.run(monitor, episode={})
    assert not result.triggered


def test_reward_divergence_check_triggers_on_sustained_decline():
    """RewardDivergenceCheck triggers when linear-fit slope is sufficiently
    negative with high R^2 over the window."""
    from andes_rl_kundur.scenarios.kundur.training_checks import RewardDivergenceCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    flat_actions = np.zeros((10, 4, 2), dtype=np.float32)
    # 60 episodes with reward decreasing linearly from -50 to -200
    for ep in range(60):
        r = -50.0 - 2.5 * ep
        _feed_episodes(
            monitor, 1, actions_per_step=flat_actions, rewards=r,
            per_agent_rewards={i: r / 4 for i in range(4)},
        )
    check = RewardDivergenceCheck(window=50)
    result = check.run(monitor, episode={})
    assert result.triggered, f"expected trigger on linear decline; got: {result}"


def test_reward_divergence_check_quiet_when_rewards_stable():
    from andes_rl_kundur.scenarios.kundur.training_checks import RewardDivergenceCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    flat_actions = np.zeros((10, 4, 2), dtype=np.float32)
    _feed_episodes(monitor, 60, actions_per_step=flat_actions, rewards=-100.0)
    check = RewardDivergenceCheck(window=50)
    result = check.run(monitor, episode={})
    assert not result.triggered


def test_tds_failure_rate_check_triggers_when_window_failure_rate_high():
    """TDSFailureRateCheck triggers when fraction of tds_failed=True
    episodes in window exceeds threshold."""
    from andes_rl_kundur.scenarios.kundur.training_checks import TDSFailureRateCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    flat_actions = np.zeros((10, 4, 2), dtype=np.float32)
    # 60 episodes, all tds_failed=True -> failure rate = 100%
    _feed_episodes(monitor, 60, actions_per_step=flat_actions, tds_failed=True)
    check = TDSFailureRateCheck(threshold=0.5, window=50)
    result = check.run(monitor, episode={})
    assert result.triggered
    assert result.name == "tds_failure_rate"


def test_tds_failure_rate_check_quiet_when_failure_rate_low():
    from andes_rl_kundur.scenarios.kundur.training_checks import TDSFailureRateCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    flat_actions = np.zeros((10, 4, 2), dtype=np.float32)
    _feed_episodes(monitor, 60, actions_per_step=flat_actions, tds_failed=False)
    check = TDSFailureRateCheck(threshold=0.5, window=50)
    result = check.run(monitor, episode={})
    assert not result.triggered


def test_freq_out_of_range_check_triggers_when_K_of_N_exceed_threshold():
    """FreqOutOfRangeCheck triggers when >=min_episodes of last `window`
    have max_freq_deviation_hz above threshold_hz."""
    from andes_rl_kundur.scenarios.kundur.training_checks import FreqOutOfRangeCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    flat_actions = np.zeros((10, 4, 2), dtype=np.float32)
    # 10 episodes all with high frequency deviation -> trigger
    _feed_episodes(
        monitor, 10, actions_per_step=flat_actions, max_freq_deviation_hz=3.0,
    )
    check = FreqOutOfRangeCheck(threshold_hz=2.0, window=10, min_episodes=3)
    result = check.run(monitor, episode={})
    assert result.triggered


def test_freq_out_of_range_check_quiet_when_below_min_episodes():
    from andes_rl_kundur.scenarios.kundur.training_checks import FreqOutOfRangeCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    flat_actions = np.zeros((10, 4, 2), dtype=np.float32)
    # Only 1 high-deviation episode in window of 10 -> below min_episodes=3
    for _ in range(9):
        _feed_episodes(monitor, 1, actions_per_step=flat_actions, max_freq_deviation_hz=0.1)
    _feed_episodes(monitor, 1, actions_per_step=flat_actions, max_freq_deviation_hz=3.0)
    check = FreqOutOfRangeCheck(threshold_hz=2.0, window=10, min_episodes=3)
    result = check.run(monitor, episode={})
    assert not result.triggered


def test_physics_frozen_check_triggers_when_power_swing_at_zero():
    """PhysicsFrozenCheck triggers when max_power_swing stays at ~0 across
    the window — electrical response not reaching the grid."""
    from andes_rl_kundur.scenarios.kundur.training_checks import PhysicsFrozenCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    flat_actions = np.zeros((10, 4, 2), dtype=np.float32)
    _feed_episodes(
        monitor, 20, actions_per_step=flat_actions, max_power_swing=0.0,
    )
    check = PhysicsFrozenCheck(window=10, epsilon=1e-9)
    result = check.run(monitor, episode={})
    assert result.triggered
    assert result.name == "physics_frozen"
    assert result.severity == "stop"


def test_physics_frozen_check_quiet_when_power_swing_nonzero():
    from andes_rl_kundur.scenarios.kundur.training_checks import PhysicsFrozenCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    flat_actions = np.zeros((10, 4, 2), dtype=np.float32)
    _feed_episodes(
        monitor, 20, actions_per_step=flat_actions, max_power_swing=0.05,
    )
    check = PhysicsFrozenCheck(window=10, epsilon=1e-9)
    result = check.run(monitor, episode={})
    assert not result.triggered


def test_agent_reward_disparity_check_triggers_when_one_agent_far_below():
    """AgentRewardDisparityCheck triggers when one agent's mean reward
    over the window is more than std_threshold std-devs below cross-agent
    mean."""
    from andes_rl_kundur.scenarios.kundur.training_checks import AgentRewardDisparityCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    flat_actions = np.zeros((10, 4, 2), dtype=np.float32)
    # Agent 3 punished hard, others normal -> disparity
    for _ in range(60):
        _feed_episodes(
            monitor, 1, actions_per_step=flat_actions, rewards=-100.0,
            per_agent_rewards={0: -25.0, 1: -25.0, 2: -25.0, 3: -1000.0},
        )
    check = AgentRewardDisparityCheck(window=50, std_threshold=1.0)
    result = check.run(monitor, episode={})
    assert result.triggered
    assert "Agent 3" in result.message


def test_agent_reward_disparity_check_quiet_when_agents_uniform():
    from andes_rl_kundur.scenarios.kundur.training_checks import AgentRewardDisparityCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    flat_actions = np.zeros((10, 4, 2), dtype=np.float32)
    for _ in range(60):
        _feed_episodes(
            monitor, 1, actions_per_step=flat_actions, rewards=-100.0,
            per_agent_rewards={i: -25.0 for i in range(4)},
        )
    check = AgentRewardDisparityCheck(window=50, std_threshold=2.0)
    result = check.run(monitor, episode={})
    assert not result.triggered


def test_loss_explosion_check_triggers_when_critic_loss_far_above_baseline():
    """LossExplosionCheck triggers when sliding-window mean critic_loss
    exceeds multiplier × calibration_data['critic_loss_baseline']."""
    from andes_rl_kundur.scenarios.kundur.training_checks import LossExplosionCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    # Real calibration: need 20 calibration episodes with low-loss baseline,
    # then 30 episodes with exploded loss.
    monitor = TrainingMonitor(calibration_episodes=20)
    flat_actions = np.zeros((10, 4, 2), dtype=np.float32)
    # Calibration phase: stable low losses
    low = [{"critic_loss": 1.0} for _ in range(4)]
    for _ in range(20):
        _feed_episodes(
            monitor, 1, actions_per_step=flat_actions, rewards=-100.0,
            sac_losses=low,
        )
    # Post-calibration: exploded losses (mean=100, baseline=1, ratio=100x >> 10x)
    high = [{"critic_loss": 100.0} for _ in range(4)]
    for _ in range(30):
        _feed_episodes(
            monitor, 1, actions_per_step=flat_actions, rewards=-100.0,
            sac_losses=high,
        )
    check = LossExplosionCheck(window=20, multiplier=10.0)
    result = check.run(monitor, episode={})
    assert result.triggered, f"expected explosion trigger; got: {result}"


def test_loss_explosion_check_quiet_before_calibration():
    """No trigger before calibration baseline exists."""
    from andes_rl_kundur.scenarios.kundur.training_checks import LossExplosionCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)  # never calibrates
    flat_actions = np.zeros((10, 4, 2), dtype=np.float32)
    high = [{"critic_loss": 100.0} for _ in range(4)]
    for _ in range(30):
        _feed_episodes(
            monitor, 1, actions_per_step=flat_actions, sac_losses=high,
        )
    check = LossExplosionCheck(window=20, multiplier=10.0)
    result = check.run(monitor, episode={})
    assert not result.triggered


def test_early_stopping_check_triggers_after_patience_without_improvement():
    """EarlyStoppingCheck is the only stateful Check — it tracks best reward
    + best episode across .run() calls. Triggers when (current ep - best ep)
    exceeds patience and improvement stayed below threshold."""
    from andes_rl_kundur.scenarios.kundur.training_checks import EarlyStoppingCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    flat_actions = np.zeros((10, 4, 2), dtype=np.float32)
    check = EarlyStoppingCheck(patience=20, min_improvement=0.10)

    # First episode sets the baseline best.
    _feed_episodes(monitor, 1, actions_per_step=flat_actions, rewards=-100.0)
    first = check.run(monitor, episode={})
    assert not first.triggered

    # 30 more episodes at the same reward → no improvement.
    # After 20 more episodes (cumulative idx 21 > 20 patience), should trigger.
    for _ in range(30):
        _feed_episodes(monitor, 1, actions_per_step=flat_actions, rewards=-100.0)
        result = check.run(monitor, episode={})
    assert result.triggered, f"expected trigger after 30 flat episodes; got: {result}"
    assert result.name == "early_stopping"


def test_reward_magnitude_check_triggers_in_manual_mode():
    """RewardMagnitudeCheck in manual mode (expected_range set) triggers
    when observed reward is outside the range."""
    from andes_rl_kundur.scenarios.kundur.training_checks import RewardMagnitudeCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    flat_actions = np.zeros((10, 4, 2), dtype=np.float32)
    _feed_episodes(monitor, 1, actions_per_step=flat_actions, rewards=-10000.0)
    check = RewardMagnitudeCheck(expected_range=(-200.0, 0.0))
    result = check.run(monitor, episode={})
    assert result.triggered
    assert result.name == "reward_magnitude"
    assert result.severity == "stop"


def test_register_kundur_default_checks_attaches_12_checks():
    """register_kundur_default_checks adds the full default suite."""
    from andes_rl_kundur.scenarios.kundur.training_checks import (
        kundur_default_checks,
        register_kundur_default_checks,
    )
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    assert len(monitor._plugin_checks) == 0
    register_kundur_default_checks(monitor)
    assert len(monitor._plugin_checks) == 12
    names = {chk.name for chk in monitor._plugin_checks}
    expected = {chk.name for chk in kundur_default_checks()}
    assert names == expected


def test_kundur_default_checks_returns_fresh_instances():
    """The factory must return new instances each call so that
    EarlyStoppingCheck's internal state does not leak across monitors."""
    from andes_rl_kundur.scenarios.kundur.training_checks import (
        EarlyStoppingCheck,
        kundur_default_checks,
    )

    a = kundur_default_checks()
    b = kundur_default_checks()
    es_a = next(c for c in a if isinstance(c, EarlyStoppingCheck))
    es_b = next(c for c in b if isinstance(c, EarlyStoppingCheck))
    assert es_a is not es_b


def test_early_stopping_check_resets_on_improvement():
    """When reward improves > min_improvement, the patience timer resets."""
    from andes_rl_kundur.scenarios.kundur.training_checks import EarlyStoppingCheck
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor(calibration_episodes=999)
    flat_actions = np.zeros((10, 4, 2), dtype=np.float32)
    check = EarlyStoppingCheck(patience=20, min_improvement=0.10)

    # 30 flat episodes, with one big improvement at ep 15 → timer resets,
    # no trigger should fire by ep 29.
    for ep in range(30):
        if ep == 15:
            r = -50.0  # big improvement: -50 vs -100 baseline -> +50%
        else:
            r = -100.0
        _feed_episodes(monitor, 1, actions_per_step=flat_actions, rewards=r)
        result = check.run(monitor, episode={})
    # 14 episodes since best (ep 15..29 - 1 = 14) < patience 20 -> no trigger
    assert not result.triggered, f"unexpected trigger; got: {result}"
