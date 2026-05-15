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
    """A class with ``name`` + ``run(episode) -> CheckResult`` satisfies
    the ``Check`` Protocol structurally — no inheritance required."""
    from andes_rl_kundur.utils.checks import Check, CheckResult

    class MaxFreqGate:
        name = "max_freq_gate"

        def run(self, episode) -> CheckResult:
            return CheckResult(
                name=self.name,
                triggered=episode["max_freq_deviation_hz"] > 1.5,
                severity="warn",
                message="frequency excursion",
            )

    chk = MaxFreqGate()
    assert isinstance(chk, Check)
    out = chk.run({"max_freq_deviation_hz": 2.0})
    assert out.triggered
    assert out.severity == "warn"


def test_monitor_invokes_registered_check():
    """When a custom Check is registered, the monitor runs it on every
    log_and_check call and surfaces its result."""
    from andes_rl_kundur.utils.checks import CheckResult
    from andes_rl_kundur.utils.monitor import TrainingMonitor

    calls: list[dict] = []

    class Recorder:
        name = "recorder"

        def run(self, episode) -> CheckResult:
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

        def run(self, episode) -> CheckResult:
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
