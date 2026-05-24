"""ANDES-Kundur training diagnostics — :class:`Check` implementations.

R42 / C4 moved the per-paper tolerance checks out of ``utils/monitor.py``
to this domain module. New Check classes added by future research live
here; the monitor's ``register_check`` seam is the only entry point.

Tracer: only ``ActionCollapseCheck`` so far. Subsequent commits will
incrementally add the remaining 11 checks (one per TDD vertical slice).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from andes_rl_kundur.utils.checks import CheckResult, Severity

if TYPE_CHECKING:
    from andes_rl_kundur.utils.checks import Check
    from andes_rl_kundur.utils.monitor import TrainingMonitor


def _no_trigger(name: str) -> CheckResult:
    return CheckResult(name=name, triggered=False)


@dataclass
class RewardComponentRatioCheck:
    """Dominant reward component below expected dominance fraction.

    The Kundur paper's reward formulation is dominated by the frequency
    component (``r_f``); when that share falls below
    ``dominance_threshold`` (default 0.5) of total absolute components,
    reward shaping has likely been disturbed (action-cost too large, etc.)
    and training will drift.
    """
    name: str = "reward_component_ratio"
    severity: Severity = "warn"
    dominant: str = "r_f"
    dominance_threshold: float = 0.5

    def run(self, monitor: TrainingMonitor, episode: dict[str, Any]) -> CheckResult:
        if not monitor.reward_components:
            return _no_trigger(self.name)
        components = monitor.reward_components[-1]
        if self.dominant not in components:
            return _no_trigger(self.name)
        total_abs = sum(abs(v) for v in components.values())
        if total_abs < 1e-8:
            return _no_trigger(self.name)
        dom_ratio = abs(components[self.dominant]) / total_abs
        if dom_ratio < self.dominance_threshold:
            breakdown = ", ".join(
                f"{k}: {abs(v) / total_abs * 100:.1f}%" for k, v in components.items()
            )
            return CheckResult(
                name=self.name,
                triggered=True,
                severity=self.severity,
                message=(
                    f"'{self.dominant}' is only {dom_ratio * 100:.1f}% of total reward "
                    f"(threshold: {self.dominance_threshold * 100:.0f}%). "
                    f"Breakdown: {breakdown}"
                ),
            )
        return _no_trigger(self.name)


@dataclass
class RewardPlateauCheck:
    """No reward improvement over a sliding window."""
    name: str = "reward_plateau"
    severity: Severity = "warn"
    window: int = 100
    improvement_threshold: float = 0.01

    def run(self, monitor: TrainingMonitor, episode: dict[str, Any]) -> CheckResult:
        if len(monitor.episode_rewards) < self.window:
            return _no_trigger(self.name)
        recent = monitor.episode_rewards[-self.window:]
        min_r, max_r = min(recent), max(recent)
        if abs(min_r) < 1e-8:
            if max_r - min_r < 1e-6:
                return CheckResult(
                    name=self.name, triggered=True, severity=self.severity,
                    message=f"Reward stuck near zero for {self.window} episodes.",
                )
            return _no_trigger(self.name)
        improvement = (max_r - min_r) / max(abs(min_r), 1e-8)
        if improvement < self.improvement_threshold:
            return CheckResult(
                name=self.name, triggered=True, severity=self.severity,
                message=(
                    f"Reward range [{min_r:.1f}, {max_r:.1f}] over last "
                    f"{self.window} episodes. Improvement: "
                    f"{improvement * 100:.2f}% (threshold: "
                    f"{self.improvement_threshold * 100:.1f}%). "
                    f"Training may be stuck in a local optimum."
                ),
            )
        return _no_trigger(self.name)


@dataclass
class RewardDivergenceCheck:
    """Sustained downward trend in reward (linear-fit slope + R^2 test)."""
    name: str = "reward_divergence"
    severity: Severity = "warn"  # R27 2026-05-07: downgraded from stop
    window: int = 50

    def run(self, monitor: TrainingMonitor, episode: dict[str, Any]) -> CheckResult:
        if len(monitor.episode_rewards) < self.window:
            return _no_trigger(self.name)
        recent = np.array(monitor.episode_rewards[-self.window:])
        x = np.arange(self.window)
        coeffs = np.polyfit(x, recent, 1)
        slope = coeffs[0]
        if slope >= 0:
            return _no_trigger(self.name)
        predicted = np.polyval(coeffs, x)
        ss_res = float(np.sum((recent - predicted) ** 2))
        ss_tot = float(np.sum((recent - np.mean(recent)) ** 2))
        r_squared = 1.0 - ss_res / max(ss_tot, 1e-8)
        if r_squared < 0.3:
            return _no_trigger(self.name)
        mean_r = float(np.abs(np.mean(recent)))
        if mean_r < 1e-8:
            return _no_trigger(self.name)
        normalised = abs(slope * self.window) / mean_r
        if normalised > 0.1:
            return CheckResult(
                name=self.name, triggered=True, severity=self.severity,
                message=(
                    f"Reward declining over last {self.window} episodes. "
                    f"Slope: {slope:.1f}/ep, R^2={r_squared:.2f}, "
                    f"total change: {abs(slope * self.window):.0f} "
                    f"({normalised * 100:.0f}% of mean). "
                    f"Training may be diverging."
                ),
            )
        return _no_trigger(self.name)


@dataclass
class TDSFailureRateCheck:
    """Sliding-window TDS divergence rate too high."""
    name: str = "tds_failure_rate"
    severity: Severity = "warn"
    threshold: float | None = 0.2
    window: int = 50

    def run(self, monitor: TrainingMonitor, episode: dict[str, Any]) -> CheckResult:
        if len(monitor.env_health) < self.window:
            return _no_trigger(self.name)
        threshold = self.threshold
        if threshold is None:
            if not monitor.is_calibrated:
                return _no_trigger(self.name)
            baseline = monitor.calibration_data.get("tds_failure_baseline", 0.0)
            threshold = max(baseline * 2, 0.3)
        recent = monitor.env_health[-self.window:]
        fails = sum(1 for h in recent if h["tds_failed"])
        rate = fails / self.window
        if rate > threshold:
            return CheckResult(
                name=self.name, triggered=True, severity=self.severity,
                message=(
                    f"TDS failure rate: {fails}/{self.window} = "
                    f"{rate * 100:.1f}% (threshold: {threshold * 100:.0f}%). "
                    f"Simulation may be numerically unstable."
                ),
            )
        return _no_trigger(self.name)


@dataclass
class FreqOutOfRangeCheck:
    """Frequency deviation exceeds threshold_hz in K of last N episodes."""
    name: str = "freq_out_of_range"
    severity: Severity = "warn"
    threshold_hz: float = 2.0
    window: int = 10
    min_episodes: int = 3

    def run(self, monitor: TrainingMonitor, episode: dict[str, Any]) -> CheckResult:
        if len(monitor.env_health) < self.window:
            return _no_trigger(self.name)
        recent = monitor.env_health[-self.window:]
        violations = sum(
            1 for h in recent if h["max_freq_deviation_hz"] > self.threshold_hz
        )
        if violations >= self.min_episodes:
            return CheckResult(
                name=self.name, triggered=True, severity=self.severity,
                message=(
                    f"Frequency exceeded ±{self.threshold_hz} Hz in "
                    f"{violations}/{self.window} recent episodes "
                    f"(threshold: {self.min_episodes} episodes). "
                    f"VSG parameters may be causing system instability."
                ),
            )
        return _no_trigger(self.name)


@dataclass
class PhysicsFrozenCheck:
    """Max power swing stuck at ~0 over window — electrical response not
    reaching the grid. Severity stop because this implies the M/D actions
    are not driving anything physical."""
    name: str = "physics_frozen"
    severity: Severity = "stop"
    window: int = 10
    epsilon: float = 1e-9

    def run(self, monitor: TrainingMonitor, episode: dict[str, Any]) -> CheckResult:
        if len(monitor.env_health) < self.window:
            return _no_trigger(self.name)
        recent = monitor.env_health[-self.window:]
        swings = [h.get("max_power_swing") for h in recent]
        if any(s is None for s in swings):
            return _no_trigger(self.name)
        if all(abs(float(s)) <= self.epsilon for s in swings):
            return CheckResult(
                name=self.name, triggered=True, severity=self.severity,
                message=(
                    f"max_power_swing <= {self.epsilon:g} for the last "
                    f"{self.window} episodes. Electrical power response "
                    f"appears frozen; M/D changes may not reach the grid."
                ),
            )
        return _no_trigger(self.name)


@dataclass
class AgentRewardDisparityCheck:
    """One agent's mean reward >K std-devs below cross-agent mean."""
    name: str = "agent_reward_disparity"
    severity: Severity = "warn"
    window: int = 50
    std_threshold: float = 2.0

    def run(self, monitor: TrainingMonitor, episode: dict[str, Any]) -> CheckResult:
        if len(monitor.per_agent_rewards) < self.window:
            return _no_trigger(self.name)
        recent = monitor.per_agent_rewards[-self.window:]
        agent_ids = sorted(recent[0].keys())
        if len(agent_ids) < 2:
            return _no_trigger(self.name)
        agent_means = {
            aid: float(np.mean([r[aid] for r in recent])) for aid in agent_ids
        }
        values = np.array(list(agent_means.values()))
        mean_v = float(np.mean(values))
        std_v = float(np.std(values))
        if std_v < 1e-8:
            return _no_trigger(self.name)
        for aid in agent_ids:
            if agent_means[aid] < mean_v - self.std_threshold * std_v:
                return CheckResult(
                    name=self.name, triggered=True, severity=self.severity,
                    message=(
                        f"Agent {aid} mean reward = {agent_means[aid]:.1f} "
                        f"over last {self.window} episodes. Cross-agent mean = "
                        f"{mean_v:.1f}, std = {std_v:.1f}. "
                        f"Agent is >{self.std_threshold:.1f} std devs below mean."
                    ),
                )
        return _no_trigger(self.name)


@dataclass
class LossExplosionCheck:
    """Per-agent critic loss >K× calibration baseline."""
    name: str = "loss_explosion"
    severity: Severity = "warn"
    window: int = 20
    multiplier: float = 10.0

    def run(self, monitor: TrainingMonitor, episode: dict[str, Any]) -> CheckResult:
        if len(monitor.sac_losses) < self.window:
            return _no_trigger(self.name)
        if not monitor.is_calibrated:
            return _no_trigger(self.name)
        baseline = monitor.calibration_data.get("critic_loss_baseline")
        if baseline is None or baseline < 1e-8:
            return _no_trigger(self.name)
        recent = monitor.sac_losses[-self.window:]
        if not recent or not recent[0]:
            return _no_trigger(self.name)
        for aidx in range(len(recent[0])):
            agent_losses = [
                ep[aidx]["critic_loss"]
                for ep in recent
                if aidx < len(ep) and "critic_loss" in ep[aidx]
            ]
            if not agent_losses:
                continue
            mean_loss = float(np.mean(agent_losses))
            if mean_loss > self.multiplier * baseline:
                return CheckResult(
                    name=self.name, triggered=True, severity=self.severity,
                    message=(
                        f"Agent {aidx} critic_loss = {mean_loss:.2f} over last "
                        f"{self.window} episodes. Baseline: {baseline:.2f}, "
                        f"ratio: {mean_loss / baseline:.1f}x "
                        f"(threshold: {self.multiplier:.0f}x)."
                    ),
                )
        return _no_trigger(self.name)


@dataclass
class EarlyStoppingCheck:
    """No improvement >min_improvement for `patience` episodes.

    The only Check that carries its own state across calls — tracks the
    best reward seen so far and the episode index it was seen at. The
    fresh-instance discipline in :func:`kundur_default_checks` (returns
    a new list per call) ensures different monitors don't accidentally
    share this state.
    """
    name: str = "early_stopping"
    severity: Severity = "warn"
    patience: int = 500
    min_improvement: float = 0.02
    _best_reward: float = field(default=float('-inf'), init=False, repr=False)
    _best_ep_idx: int = field(default=0, init=False, repr=False)

    def run(self, monitor: TrainingMonitor, episode: dict[str, Any]) -> CheckResult:
        if not monitor.episode_rewards:
            return _no_trigger(self.name)
        current = monitor.episode_rewards[-1]
        ep_idx = len(monitor.episode_rewards) - 1

        if self._best_reward < -1e30:
            self._best_reward = current
            self._best_ep_idx = ep_idx
            return _no_trigger(self.name)

        if abs(self._best_reward) > 1e-8:
            improvement = (current - self._best_reward) / abs(self._best_reward)
        else:
            improvement = current - self._best_reward

        if improvement > self.min_improvement:
            self._best_reward = current
            self._best_ep_idx = ep_idx
            return _no_trigger(self.name)

        eps_since = ep_idx - self._best_ep_idx
        if eps_since >= self.patience:
            return CheckResult(
                name=self.name, triggered=True, severity=self.severity,
                message=(
                    f"No improvement >{self.min_improvement * 100:.1f}% for "
                    f"{eps_since} episodes (patience: {self.patience}). "
                    f"Best reward: {self._best_reward:.1f} @ ep "
                    f"{self._best_ep_idx}. Current: {current:.1f}."
                ),
            )
        return _no_trigger(self.name)


@dataclass
class ActionSaturationCheck:
    """Most actions are clipping at ±0.95. The action space is too small.

    Reads only the most recent episode's saturation ratio (precomputed
    by ``TrainingMonitor`` as ``np.mean(|actions| > 0.95)``).
    """
    name: str = "action_saturation"
    severity: Severity = "warn"
    threshold: float = 0.8

    def run(self, monitor: TrainingMonitor, episode: dict[str, Any]) -> CheckResult:
        if not monitor.action_stats:
            return _no_trigger(self.name)
        sat_ratio = monitor.action_stats[-1]["saturation_ratio"]
        if sat_ratio > self.threshold:
            return CheckResult(
                name=self.name,
                triggered=True,
                severity=self.severity,
                message=(
                    f"Action saturation = {sat_ratio * 100:.1f}% "
                    f"(threshold: {self.threshold * 100:.0f}%). "
                    f"Most actions are at boundary ±0.95; action space may be too small."
                ),
            )
        return _no_trigger(self.name)


@dataclass
class RewardMagnitudeCheck:
    """Reward grossly outside expected envelope (auto-calibrated or manual)."""
    name: str = "reward_magnitude"
    severity: Severity = "stop"
    expected_range: tuple[float, float] | None = None  # manual mode
    auto_ratio_threshold: float = 100.0  # auto mode

    def run(self, monitor: TrainingMonitor, episode: dict[str, Any]) -> CheckResult:
        if not monitor.episode_rewards:
            return _no_trigger(self.name)
        current = monitor.episode_rewards[-1]
        if self.expected_range is not None:
            lo, hi = self.expected_range
            if current < lo or current > hi:
                deviation = abs(current / max(min(abs(lo), abs(hi)), 1e-8))
                return CheckResult(
                    name=self.name, triggered=True, severity=self.severity,
                    message=(
                        f"Observed reward = {current:.0f}, expected range "
                        f"({lo}, {hi}). Deviation: {deviation:.0f}x."
                    ),
                )
            return _no_trigger(self.name)
        if not monitor.is_calibrated:
            return _no_trigger(self.name)
        mu = monitor.calibration_data["reward_mean"]
        if abs(mu) < 1e-8:
            return _no_trigger(self.name)
        ratio = abs(current / mu)
        if ratio >= self.auto_ratio_threshold:
            return CheckResult(
                name=self.name, triggered=True, severity=self.severity,
                message=f"Reward {current:.0f} is {ratio:.0f}x baseline ({mu:.0f}).",
            )
        return _no_trigger(self.name)


@dataclass
class ActionCollapseCheck:
    """Per-agent action std stuck near zero over a sliding window.

    Triggers when every agent's per-episode action std is below the
    threshold for the entire window of the most-recent ``window``
    episodes — interpreted as the policy collapsing to a near-zero
    "do nothing" output.

    If ``std_threshold`` is None and the monitor is calibrated, an
    auto-threshold of ``0.1 * calibration_data['action_std_baseline']``
    is used. Otherwise the literal ``std_threshold`` is used.
    """
    name: str = "action_collapse"
    severity: Severity = "warn"
    std_threshold: float | None = 0.05
    window: int = 50

    def run(self, monitor: TrainingMonitor, episode: dict[str, Any]) -> CheckResult:
        if len(monitor.action_stats) < self.window:
            return _no_trigger(self.name)

        threshold = self.std_threshold
        if threshold is None:
            if not monitor.is_calibrated:
                return _no_trigger(self.name)
            baseline = monitor.calibration_data.get("action_std_baseline", 0.5)
            threshold = baseline * 0.1

        recent = monitor.action_stats[-self.window:]
        n_agents = len(recent[0]["per_agent_std"])
        for aidx in range(n_agents):
            agent_stds = [s["per_agent_std"][aidx] for s in recent]
            if all(s < threshold for s in agent_stds):
                avg_std = float(np.mean(agent_stds))
                return CheckResult(
                    name=self.name,
                    triggered=True,
                    severity=self.severity,
                    message=(
                        f"Agent {aidx} action std = {avg_std:.4f} "
                        f"(threshold: {threshold:.4f}) over last {self.window} episodes. "
                        f"Interpretation: policy may have collapsed to near-zero output."
                    ),
                )
        return _no_trigger(self.name)


# ──────────────────────────────────────────────────────────────────────
# Registration helpers — declared last so all Check classes are in scope.
# ──────────────────────────────────────────────────────────────────────


def kundur_default_checks() -> list[Check]:
    """Return a **fresh** list of the 12 default Check instances (Kundur
    paper tolerances).

    Fresh-list discipline is important: :class:`EarlyStoppingCheck`
    carries per-monitor state and must not be shared across monitors.
    """
    return [
        RewardMagnitudeCheck(),
        RewardComponentRatioCheck(),
        ActionCollapseCheck(),
        ActionSaturationCheck(),
        RewardPlateauCheck(),
        RewardDivergenceCheck(),
        TDSFailureRateCheck(),
        FreqOutOfRangeCheck(),
        PhysicsFrozenCheck(),
        AgentRewardDisparityCheck(),
        LossExplosionCheck(),
        EarlyStoppingCheck(),
    ]


def register_kundur_default_checks(monitor: TrainingMonitor) -> None:
    """Register the 12 default Kundur Check instances on a TrainingMonitor.

    Use in ``train.py`` after constructing the monitor::

        monitor = TrainingMonitor(best_reward_callback=on_best_reward)
        register_kundur_default_checks(monitor)
    """
    for chk in kundur_default_checks():
        monitor.register_check(chk)
