"""Tests for R58 `--reward-config` CLI wiring in scripts/train.py.

The wiring contract:
- New `--reward-config` flag selects which V4Config classmethod to
  use as the BASE config (paper_faithful default, or paper_strict_pure,
  or paper_strict_rescaled).
- Existing `--phi-h` / `--phi-d` / `--phi-f` per-field CLI overrides
  continue to win over the base config (programmer intent first).
- Default behaviour (no `--reward-config`) is bit-identical to the
  pre-R58 codepath (paper_faithful base).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))


def _mk_args(**overrides) -> argparse.Namespace:
    """Build an argparse Namespace mimicking scripts/train.py's parse_args
    output, with everything defaulted so only specified overrides differ."""
    base: dict = {
        "reward_config": None,
        "phi_f": None, "phi_h": None, "phi_d": None,
        "phi_abs": None, "phi_max": None, "phi_settle": None,
        "vsg_m0": None, "vsg_d0": None,
        "dm_min": None, "dm_max": None,
        "dd_min": None, "dd_max": None,
        "normalize_actions": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def test_build_v4_config_default_is_paper_faithful():
    """No `--reward-config` flag → bit-identical to V4Config.paper_faithful().
    R56/R57 ckpts and call sites that don't know about R58 still work."""
    import train

    args = _mk_args()
    cfg = train.build_v4_config(args)
    assert cfg.phi_abs == 50.0, "default base must remain paper_faithful"
    assert cfg.phi_h == 0.0056
    assert cfg.phi_d == 0.0056
    assert cfg.phi_f == 100.0


def test_build_v4_config_paper_strict_pure_flag():
    """`--reward-config paper_strict_pure` → returns config matching
    V4Config.paper_strict_pure() (PHI_ABS=0, PHI_H=PHI_D=1.0)."""
    import train

    args = _mk_args(reward_config="paper_strict_pure")
    cfg = train.build_v4_config(args)
    assert cfg.phi_abs == 0.0
    assert cfg.phi_h == 1.0
    assert cfg.phi_d == 1.0
    assert cfg.phi_f == 100.0


def test_build_v4_config_paper_strict_rescaled_flag():
    """`--reward-config paper_strict_rescaled` → returns config matching
    V4Config.paper_strict_rescaled() (PHI_ABS=0, PHI_H=PHI_D=0.0056)."""
    import train

    args = _mk_args(reward_config="paper_strict_rescaled")
    cfg = train.build_v4_config(args)
    assert cfg.phi_abs == 0.0
    assert cfg.phi_h == 0.0056
    assert cfg.phi_d == 0.0056


def test_explicit_cli_overrides_win_over_reward_config_base():
    """`--phi-h 0.5 --reward-config paper_strict_pure` → phi_h=0.5
    (explicit override wins). Documents programmer-intent precedence
    in case someone wants to mix-and-match."""
    import train

    args = _mk_args(reward_config="paper_strict_pure", phi_h=0.5)
    cfg = train.build_v4_config(args)
    # phi_h overridden, but phi_abs and phi_d inherited from
    # paper_strict_pure base.
    assert cfg.phi_h == 0.5
    assert cfg.phi_abs == 0.0
    assert cfg.phi_d == 1.0


def test_unknown_reward_config_raises():
    """Typo-resistant: unknown reward_config value must raise."""
    import pytest
    import train

    args = _mk_args(reward_config="paper_strict_typo")
    with pytest.raises((ValueError, AttributeError)):
        train.build_v4_config(args)
