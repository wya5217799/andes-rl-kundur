"""ANDES Kundur 4-VSG RL training and evaluation toolkit.

ANDES itself is WSL-only in this repo, so the package root must stay
importable for pure Python tooling without importing simulator-backed envs.
Public exports are loaded lazily on first access.
"""
from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

__all__ = [
    "AndesMultiVSGEnvV4",
    "BaseAgent",
    "SACAgent",
    "SCENARIOS",
]

_LAZY_EXPORTS = {
    "AndesMultiVSGEnvV4": (
        "andes_rl_kundur.env.andes.andes_vsg_env_v4",
        "AndesMultiVSGEnvV4",
    ),
    "BaseAgent": ("andes_rl_kundur.agents.base_agent", "BaseAgent"),
    "SACAgent": ("andes_rl_kundur.agents.sac", "SACAgent"),
    "SCENARIOS": (
        "andes_rl_kundur.probes.andes_common.paper_constants",
        "SCENARIOS",
    ),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


if TYPE_CHECKING:
    from andes_rl_kundur.agents.base_agent import BaseAgent
    from andes_rl_kundur.agents.sac import SACAgent
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS
