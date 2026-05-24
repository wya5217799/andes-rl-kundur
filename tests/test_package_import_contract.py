"""Package import contract for Windows-side tooling.

ANDES is WSL-only in this repo. Pure Python helpers, tests, and metadata
imports must remain usable on Windows without importing the simulator module.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _clear_project_modules() -> None:
    for name in list(sys.modules):
        if name == "andes" or name.startswith("andes_rl_kundur"):
            del sys.modules[name]


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
