"""Package import contract for Windows-side tooling.

ANDES is WSL-only in this repo. Pure Python helpers, tests, and metadata
imports must remain usable on Windows without importing the simulator module.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _is_project_module(name: str) -> bool:
    return name == "andes" or name.startswith("andes_rl_kundur")


def _clear_project_modules() -> None:
    for name in list(sys.modules):
        if _is_project_module(name):
            del sys.modules[name]


@pytest.fixture(autouse=True)
def _restore_project_modules_after_test():
    """Keep these import-isolation checks from changing later test identities."""
    original_modules = {
        name: module for name, module in sys.modules.items() if _is_project_module(name)
    }
    try:
        yield
    finally:
        _clear_project_modules()
        sys.modules.update(original_modules)


def test_root_package_import_does_not_import_andes() -> None:
    _clear_project_modules()

    pkg = importlib.import_module("andes_rl_kundur")

    assert "andes" not in sys.modules
    assert "AndesMultiVSGEnvV4" in pkg.__all__


def test_v4_config_import_does_not_import_andes() -> None:
    _clear_project_modules()

    module = importlib.import_module("andes_rl_kundur.env.andes.v4_config")

    assert "andes" not in sys.modules
    assert module.V4Config.paper_faithful().zero_g4_inertia is True
