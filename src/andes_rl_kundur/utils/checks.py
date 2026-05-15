"""Extension seam for ``TrainingMonitor``: structural Check Protocol.

Any class with a ``name: str`` attribute and a ``run(episode_dict) ->
CheckResult`` method satisfies the Protocol and can be registered with
:py:meth:`TrainingMonitor.register_check`. The monitor invokes
registered checks each ``log_and_check`` cycle alongside its 12 baked-in
diagnostics.

The baked-in checks are not refactored to use this seam — they carry
calibration state machines that would be risky to rewrite without
regression. New checks added during continuing research should be
written against this Protocol; over time, the baked-in set can migrate
one check at a time.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol, runtime_checkable


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

    def run(self, episode: dict[str, Any]) -> CheckResult:
        ...
