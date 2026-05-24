"""ANDES power-system simulation environments.

The simulator dependency is WSL-only, so importing this package should not
eagerly import environment implementations that require ``andes``.
"""
from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

__all__ = ["AndesBaseEnv", "AndesMultiVSGEnvV4"]

_LAZY_EXPORTS = {
    "AndesBaseEnv": ("andes_rl_kundur.env.andes.base_env", "AndesBaseEnv"),
    "AndesMultiVSGEnvV4": (
        "andes_rl_kundur.env.andes.andes_vsg_env_v4",
        "AndesMultiVSGEnvV4",
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
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.base_env import AndesBaseEnv
