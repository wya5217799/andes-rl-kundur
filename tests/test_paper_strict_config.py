"""Tests for R58 paper-strict V4Config classmethods.

Per ADR-0002, `V4Config` gets two new classmethods that produce
reward configurations matching the paper's Eq.14 more faithfully than
the default `paper_faithful()` (which adds a non-paper PHI_ABS term
and rescales PHI_H/D by 1/178).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_paper_strict_pure_returns_paper_eq14_nominal_weights():
    """`paper_strict_pure()` returns config with paper Eq.14 nominal:
    PHI_ABS=0 (no non-paper term), PHI_H=PHI_D=1.0 (paper nominal).
    All other fields equal `paper_faithful()` defaults."""
    from andes_rl_kundur.env.andes.v4_config import V4Config

    cfg = V4Config.paper_strict_pure()
    assert cfg.phi_abs == 0.0, "paper Eq.14 has no PHI_ABS term"
    assert cfg.phi_h == 1.0, "paper Eq.14 nominal PHI_H = 1.0"
    assert cfg.phi_d == 1.0, "paper Eq.14 nominal PHI_D = 1.0"
    # Frequency-component weight unchanged from paper Eq.14 nominal
    assert cfg.phi_f == 100.0
    # Action range, physics, smoothness — all paper-faithful defaults
    default = V4Config.paper_faithful()
    assert cfg.vsg_m0 == default.vsg_m0
    assert cfg.vsg_d0 == default.vsg_d0
    assert cfg.dm_min == default.dm_min
    assert cfg.dm_max == default.dm_max
    assert cfg.dd_min == default.dd_min
    assert cfg.dd_max == default.dd_max
    assert cfg.action_penalty_mode == default.action_penalty_mode
    assert cfg.lambda_smooth == default.lambda_smooth


def test_paper_strict_rescaled_zeros_phi_abs_keeps_phi_hd_rescale():
    """`paper_strict_rescaled()`: PHI_ABS=0 (no non-paper term) AND
    PHI_H=PHI_D=0.0056 (R18 rescale retained). Isolates the question
    of whether algorithm ranking depends on the non-paper PHI_ABS vs
    on the PHI_H/D rescale."""
    from andes_rl_kundur.env.andes.v4_config import V4Config

    cfg = V4Config.paper_strict_rescaled()
    assert cfg.phi_abs == 0.0, "no non-paper PHI_ABS term"
    assert cfg.phi_h == 0.0056, "R18 rescale retained"
    assert cfg.phi_d == 0.0056, "R18 rescale retained"
    assert cfg.phi_f == 100.0


def test_paper_strict_classmethods_dont_break_old_paper_faithful():
    """ADR-0002 guarantee: `V4Config.paper_faithful()` keeps original
    behaviour (PHI_ABS=50, PHI_H=PHI_D=0.0056) so R56/R57 ckpts and
    callers are not affected."""
    from andes_rl_kundur.env.andes.v4_config import V4Config

    cfg = V4Config.paper_faithful()
    assert cfg.phi_abs == 50.0, (
        "paper_faithful must keep PHI_ABS=50 (project-modified reward); "
        "do NOT silently change defaults — ADR-0002 promises stability"
    )
    assert cfg.phi_h == 0.0056
    assert cfg.phi_d == 0.0056


def test_paper_strict_configs_are_frozen_dataclasses():
    """`V4Config` is a frozen dataclass — paper_strict_pure() result
    cannot be mutated post-construction. Forces explicit replace() for
    overrides at call sites."""
    from andes_rl_kundur.env.andes.v4_config import V4Config
    import dataclasses
    import pytest

    cfg = V4Config.paper_strict_pure()
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.phi_abs = 99.0  # type: ignore[misc]
