"""Unit tests for the future-round adaptive-stop module (no ANDES import)."""

from __future__ import annotations

import numpy as np

from andes_rl_kundur.training.adaptive_stop import (
    AdaptiveStopConfig,
    AdaptiveStopMonitor,
)


def _curves(*, drift: float = 0.0, size: int = 8_000) -> dict[str, np.ndarray]:
    split = size - 2_000
    actor = np.ones(size)
    critic = np.full(size, 2.0)
    if drift:
        actor[split:] *= 1.0 + drift
        critic[split:] *= 1.0 + drift
    return {
        "actor_loss": actor,
        "critic_loss": critic,
        "alpha": np.full(size, 0.005),
        "actor_grad_norm": np.full(size, 0.1),
    }


def test_three_checks_span_four_thousand_steps() -> None:
    config = AdaptiveStopConfig()
    assert config.confirmation_span_steps == 4_000
    monitor = AdaptiveStopMonitor(config)
    decisions = [
        monitor.observe(
            interaction_steps=step,
            curves=_curves(),
            action_probe_drift=0.01,
            tds_failures=0,
        )
        for step in (30_000, 32_000, 34_000)
    ]
    assert [item.should_stop for item in decisions] == [False, False, True]
    assert decisions[-1].converged is True
    assert decisions[-1].reason == "converged"


def test_drift_resets_patience() -> None:
    monitor = AdaptiveStopMonitor(AdaptiveStopConfig())
    first = monitor.observe(
        interaction_steps=30_000,
        curves=_curves(),
        action_probe_drift=0.01,
        tds_failures=0,
    )
    second = monitor.observe(
        interaction_steps=32_000,
        curves=_curves(drift=0.5),
        action_probe_drift=0.01,
        tds_failures=0,
    )
    assert first.consecutive_passes == 1
    assert second.consecutive_passes == 0
    assert second.reason == "gate_failed"


def test_action_probe_and_tds_fail_closed() -> None:
    monitor = AdaptiveStopMonitor(AdaptiveStopConfig())
    probe = monitor.observe(
        interaction_steps=30_000,
        curves=_curves(),
        action_probe_drift=0.03,
        tds_failures=0,
    )
    tds = monitor.observe(
        interaction_steps=32_000,
        curves=_curves(),
        action_probe_drift=0.01,
        tds_failures=1,
    )
    assert probe.consecutive_passes == 0
    assert tds.consecutive_passes == 0


def test_max_steps_stops_without_claiming_convergence() -> None:
    monitor = AdaptiveStopMonitor(AdaptiveStopConfig())
    decision = monitor.observe(
        interaction_steps=43_200,
        curves=_curves(drift=0.5),
        action_probe_drift=0.5,
        tds_failures=0,
    )
    assert decision.should_stop is True
    assert decision.converged is False
    assert decision.reason == "max_steps"


def test_monitor_state_round_trip_preserves_patience() -> None:
    monitor = AdaptiveStopMonitor(AdaptiveStopConfig())
    monitor.observe(
        interaction_steps=30_000,
        curves=_curves(),
        action_probe_drift=0.01,
        tds_failures=0,
    )
    restored = AdaptiveStopMonitor.from_state_dict(monitor.state_dict())
    decision = restored.observe(
        interaction_steps=32_000,
        curves=_curves(),
        action_probe_drift=0.01,
        tds_failures=0,
    )
    assert decision.consecutive_passes == 2
