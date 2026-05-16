"""``TrainingMonitor`` accepts plug-in checks via a Protocol.

The 12 baked-in checks (reward_magnitude / action_collapse / etc.)
stay inside ``utils/monitor.py`` — they each carry calibration state
that would be risky to refactor without behavioral regression. What
this test locks is the *extension seam*: a research script can write
a one-file Check that the monitor calls every episode, without
editing monitor.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_check_protocol_recognises_simple_callable_check():
    """A class with ``name`` + ``run(monitor, episode) -> CheckResult``
    satisfies the ``Check`` Protocol structurally — no inheritance required.

    Updated R42 hotfix: signature is now 2-arg (monitor, episode). The
    old 1-arg form would still satisfy ``isinstance(chk, Check)`` because
    ``@runtime_checkable`` only checks method presence, not arity — but
    the monitor would crash when it dispatches with 2 args."""
    from andes_rl_kundur.utils.checks import Check, CheckResult

    class MaxFreqGate:
        name = "max_freq_gate"

        def run(self, monitor, episode) -> CheckResult:
            return CheckResult(
                name=self.name,
                triggered=episode["max_freq_deviation_hz"] > 1.5,
                severity="warn",
                message="frequency excursion",
            )

    chk = MaxFreqGate()
    assert isinstance(chk, Check)
    out = chk.run(None, {"max_freq_deviation_hz": 2.0})
    assert out.triggered
    assert out.severity == "warn"


def test_summary_tolerates_legacy_trigger_history_schema():
    """B6 regression: pre-R42 _trigger_history entries used either
    ``{check, episode, action, message}`` (baked-in path) or
    ``{episode, name, severity, message, source}`` (plug-in path).
    Post-R42 only writes the first form, but ``load_checkpoint`` may
    hydrate either. ``summary()`` must read with a fallback so an old
    checkpoint with plug-in entries doesn't KeyError."""
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    monitor = TrainingMonitor()
    # Inject minimum state for summary() to render at all.
    monitor._episode_rewards = [-100.0]
    monitor._env_health = [{"tds_failed": False, "max_freq_deviation_hz": 0.1}]
    # Old plug-in schema (name / severity instead of check / action)
    monitor._trigger_history = [{
        "episode": 0,
        "name": "old_plugin_check",
        "severity": "warn",
        "message": "legacy entry",
        "source": "plugin",
    }]
    # Should not raise
    monitor.summary()


def test_monitor_dispatches_with_two_args_to_registered_check():
    """B2 regression: monitor.log_and_check must dispatch via
    ``check.run(monitor, episode)``; a Check written for the new 2-arg
    Protocol receives both args. This locks the seam against the silent
    1-arg drift the old MaxFreqGate hid."""
    from andes_rl_kundur.utils.checks import CheckResult
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    seen: list[tuple[object, dict]] = []

    class TwoArgCheck:
        name = "two_arg"

        def run(self, monitor, episode) -> CheckResult:
            seen.append((monitor, episode))
            return CheckResult(name=self.name, triggered=False)

    monitor = TrainingMonitor()
    monitor.register_check(TwoArgCheck())
    monitor.log_and_check(
        episode=0,
        rewards=-100.0,
        reward_components={"r_f": -60.0, "r_h": -20.0, "r_d": -20.0},
        actions=np.zeros((50, 4, 2)),
        info={"tds_failed": False, "max_freq_deviation_hz": 0.5},
        per_agent_rewards={i: -25.0 for i in range(4)},
    )

    assert len(seen) == 1
    received_monitor, received_episode = seen[0]
    assert received_monitor is monitor, \
        "monitor argument must be the same TrainingMonitor instance"
    assert received_episode["max_freq_deviation_hz"] == 0.5


def test_monitor_invokes_registered_check():
    """When a custom Check is registered, the monitor runs it on every
    log_and_check call and surfaces its result."""
    from andes_rl_kundur.utils.checks import CheckResult
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    calls: list[dict] = []

    class Recorder:
        name = "recorder"

        def run(self, monitor, episode) -> CheckResult:
            calls.append(episode)
            return CheckResult(name=self.name, triggered=False)

    monitor = TrainingMonitor()
    monitor.register_check(Recorder())
    monitor.log_and_check(
        episode=0,
        rewards=-100.0,
        reward_components={"r_f": -50.0, "r_h": -25.0, "r_d": -25.0},
        actions=np.zeros((50, 4, 2)),
        info={"tds_failed": False, "max_freq_deviation_hz": 0.1},
        per_agent_rewards={0: -25.0, 1: -25.0, 2: -25.0, 3: -25.0},
    )
    assert len(calls) == 1
    assert calls[0]["max_freq_deviation_hz"] == 0.1


def test_monitor_stops_when_registered_check_says_so():
    """A registered Check returning triggered=True severity='stop' must
    make log_and_check return True (the stop signal the train loop watches)."""
    from andes_rl_kundur.utils.checks import CheckResult
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    class HardStop:
        name = "hard_stop"

        def run(self, monitor, episode) -> CheckResult:
            return CheckResult(
                name=self.name, triggered=True, severity="stop",
                message="research-rule violation",
            )

    monitor = TrainingMonitor()
    monitor.register_check(HardStop())
    should_stop = monitor.log_and_check(
        episode=0,
        rewards=0.0,
        reward_components={"r_f": 0.0, "r_h": 0.0, "r_d": 0.0},
        actions=np.zeros((50, 4, 2)),
        info={"tds_failed": False, "max_freq_deviation_hz": 0.0},
        per_agent_rewards={0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0},
    )
    assert should_stop is True
