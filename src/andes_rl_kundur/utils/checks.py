"""Check Protocol — the sole extension seam for ``TrainingMonitor`` diagnostics.

A Check is anything with a ``name: str`` attribute and a
``run(monitor, episode) -> CheckResult`` method. The monitor invokes
every registered check on each ``log_and_check`` call. The 12
ANDES-Kundur baked-in checks (reward_magnitude, action_collapse, etc.)
live in :mod:`andes_rl_kundur.scenarios.kundur.training_checks` and are
registered via :func:`register_kundur_default_checks` from ``train.py``.

The monitor passes ``self`` to ``Check.run`` so checks can query
accumulated state via the monitor's public read-only accessors:
``episode_rewards``, ``action_stats``, ``env_health``,
``reward_components``, ``per_agent_rewards``, ``sac_losses``,
``calibration_data``, ``is_calibrated``. This avoids defining a parallel
``MonitorView`` Protocol — the monitor *is* the view.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from andes_rl_kundur.utils.monitor import TrainingMonitor


Severity = Literal["info", "warn", "stop"]


@dataclass(frozen=True)
class CheckResult:
    name: str
    triggered: bool
    severity: Severity = "info"
    message: str = ""


@runtime_checkable
class Check(Protocol):
    name: str

    def run(
        self,
        monitor: TrainingMonitor,
        episode: dict[str, Any],
    ) -> CheckResult:
        ...
