"""Reusable training-control modules.

This package holds execution policy that is independent of a particular
research round.  Round runners remain responsible for prospectively freezing
the configuration and for deciding whether adaptive stopping is scientific
evidence or development-only behaviour.
"""

from .adaptive_stop import (
    AdaptiveStopConfig,
    AdaptiveStopMonitor,
    StopDecision,
)

__all__ = [
    "AdaptiveStopConfig",
    "AdaptiveStopMonitor",
    "StopDecision",
]
