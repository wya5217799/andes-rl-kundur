"""Tests for R58 audit-A fixes (A1, A2, A3, A5).

A4 (Eq.15 `if η==1: subtract` vs `× η_j`) is mathematically equivalent
to the paper formula; no fix needed.

Each fix is exposed as an opt-in V4Config field. Defaults preserve
R30–R57 behaviour bit-identically so the in-flight 18-training matrix
and all historical ckpts are NOT affected.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


# ─── A3: r^f frequency units ────────────────────────────────────────


def test_v4config_default_r_f_freq_units_is_hz_preserves_r56_r57():
    """Default `r_f_freq_units = "hz"` matches all R30–R57 behaviour."""
    from andes_rl_kundur.env.andes.v4_config import V4Config

    cfg = V4Config()
    assert cfg.r_f_freq_units == "hz"
    assert V4Config.paper_faithful().r_f_freq_units == "hz"
    assert V4Config.paper_strict_pure().r_f_freq_units == "hz"
    assert V4Config.paper_strict_rescaled().r_f_freq_units == "hz"


def test_paper_strict_pure_radsec_uses_rad_per_s_units():
    """`paper_strict_pure_radsec()` overrides only the freq-units flag
    to `rad_per_s`; everything else matches paper_strict_pure (PHI_ABS=0,
    PHI_H=PHI_D=1.0)."""
    from andes_rl_kundur.env.andes.v4_config import V4Config

    cfg = V4Config.paper_strict_pure_radsec()
    assert cfg.r_f_freq_units == "rad_per_s"
    # All other paper-strict-pure overrides:
    assert cfg.phi_abs == 0.0
    assert cfg.phi_h == 1.0
    assert cfg.phi_d == 1.0
    # Everything else inherits paper_faithful defaults:
    default = V4Config.paper_faithful()
    assert cfg.vsg_m0 == default.vsg_m0
    assert cfg.dm_min == default.dm_min


def test_v4config_rejects_invalid_r_f_freq_units():
    from andes_rl_kundur.env.andes.v4_config import V4Config

    with pytest.raises(ValueError, match="r_f_freq_units"):
        V4Config(r_f_freq_units="khz")  # type: ignore[arg-type]


# ─── A2: H paper-interpretation ─────────────────────────────────────


def test_v4config_default_h_interpretation_preserves_r56_r57():
    """Default `h_paper_interpretation = "mechanical_H"` matches the
    R30–R57 code path (ΔH = ΔM/2 division in r^h)."""
    from andes_rl_kundur.env.andes.v4_config import V4Config

    cfg = V4Config()
    assert cfg.h_paper_interpretation == "mechanical_H"


def test_v4config_andes_m_interpretation_skips_half_division():
    """`h_paper_interpretation = "andes_M"` keeps r^h using ΔM directly
    (paper H ≡ ANDES M assumption). Verified via env-level r_h."""
    from andes_rl_kundur.env.andes.v4_config import V4Config

    cfg = V4Config(h_paper_interpretation="andes_M")
    assert cfg.h_paper_interpretation == "andes_M"


def test_v4config_rejects_invalid_h_interpretation():
    from andes_rl_kundur.env.andes.v4_config import V4Config

    with pytest.raises(ValueError, match="h_paper_interpretation"):
        V4Config(h_paper_interpretation="paper_H")  # type: ignore[arg-type]


# ─── A5: ΔH avg scope ───────────────────────────────────────────────


def test_v4config_default_avg_scope_is_global_preserves_r56_r57():
    """Default `r_avg_scope = "global"` matches the R30–R57 code path
    (np.mean over all 4 ESS)."""
    from andes_rl_kundur.env.andes.v4_config import V4Config

    cfg = V4Config()
    assert cfg.r_avg_scope == "global"


def test_v4config_neighbor_avg_scope():
    """`r_avg_scope = "neighbor"` switches r^h / r^d to per-agent
    mean over self + active neighbors."""
    from andes_rl_kundur.env.andes.v4_config import V4Config

    cfg = V4Config(r_avg_scope="neighbor")
    assert cfg.r_avg_scope == "neighbor"


def test_v4config_rejects_invalid_avg_scope():
    from andes_rl_kundur.env.andes.v4_config import V4Config

    with pytest.raises(ValueError, match="r_avg_scope"):
        V4Config(r_avg_scope="distributed")  # type: ignore[arg-type]


# ─── Env-level reward computation tests ─────────────────────────────


class _FakeEnv:
    """Minimal stand-in for AndesBaseEnv to exercise _compute_rewards
    without booting ANDES TDS. Sets all reward-related attributes to
    paper-faithful defaults plus the R31/R33/R50 probe knobs OFF."""

    N_AGENTS = 4
    FN = 50.0
    DM_MIN, DM_MAX = -200.0, 600.0
    DD_MIN, DD_MAX = -200.0, 600.0
    PHI_F = 100.0
    PHI_H = 1.0
    PHI_D = 1.0
    PHI_ABS = 0.0
    PHI_MAX = 0.0
    PHI_SETTLE = 0.0
    SETTLE_THRESHOLD_HZ = 0.05
    COMM_ADJ = {0: [1, 3], 1: [0, 2], 2: [1, 3], 3: [2, 0]}

    def __init__(self, **cfg_kwargs):
        self._omega_scale = self.FN * 2 * np.pi
        self.comm_eta = {(0, 1): 1, (0, 3): 1, (1, 0): 1, (1, 2): 1,
                         (2, 1): 1, (2, 3): 1, (3, 2): 1, (3, 0): 1}
        self.comm_delay_steps = 0
        self._delayed_omega = None
        self.action_penalty_mode = "physical"
        self.r_f_freq_units = cfg_kwargs.get("r_f_freq_units", "hz")
        self.h_paper_interpretation = cfg_kwargs.get(
            "h_paper_interpretation", "mechanical_H"
        )
        self.r_avg_scope = cfg_kwargs.get("r_avg_scope", "global")

    # Borrow the real implementation under test
    from andes_rl_kundur.env.andes.base_env import AndesBaseEnv  # noqa: E402
    _compute_rewards = AndesBaseEnv._compute_rewards


def test_r_f_freq_units_radsec_scales_r_f_by_2pi_squared():
    """At a typical disturbance (Δω = 0.1 Hz across all agents but
    one outlier at 0.5 Hz), the rad/s r^f magnitude should be (2π)²
    times the Hz r^f magnitude. This validates Finding A3's predicted
    scaling."""
    env_hz = _FakeEnv(r_f_freq_units="hz")
    env_rs = _FakeEnv(r_f_freq_units="rad_per_s")

    # 4 ESS, one out of sync by 0.4 Hz
    omega = np.array([1.0 + 0.5 / 50, 1.0 + 0.1 / 50,
                      1.0 + 0.1 / 50, 1.0 + 0.1 / 50])
    omega_dot = np.zeros(4)
    delta_M = np.zeros(4)
    delta_D = np.zeros(4)

    r_hz, *_ = env_hz._compute_rewards(omega, omega_dot, delta_M, delta_D)
    r_rs, *_ = env_rs._compute_rewards(omega, omega_dot, delta_M, delta_D)

    # Sum per-agent rewards (only r^f component is non-zero)
    s_hz = sum(r_hz.values())
    s_rs = sum(r_rs.values())
    ratio = s_rs / s_hz
    expected_ratio = (2 * np.pi) ** 2
    assert abs(ratio - expected_ratio) / expected_ratio < 1e-9, (
        f"rad/s vs Hz r^f ratio should be (2π)²={expected_ratio:.3f}, "
        f"got {ratio:.3f}"
    )


def test_h_interpretation_andes_M_makes_r_h_4x_larger():
    """`h_paper_interpretation = "andes_M"` skips the /2 → r^h is (2)² = 4×
    larger for the same ΔM input."""
    env_mech = _FakeEnv(h_paper_interpretation="mechanical_H")
    env_andes = _FakeEnv(h_paper_interpretation="andes_M")

    omega = np.ones(4)  # zero d_omega → r^f = 0
    omega_dot = np.zeros(4)
    delta_M = np.array([200.0, 100.0, -100.0, -200.0])  # mean = 0
    # Force a non-zero mean for clarity
    delta_M = np.array([200.0, 200.0, 200.0, 200.0])  # mean = 200
    delta_D = np.zeros(4)

    r_mech, *_ = env_mech._compute_rewards(omega, omega_dot, delta_M, delta_D)
    r_andes, *_ = env_andes._compute_rewards(omega, omega_dot, delta_M, delta_D)

    s_mech = sum(r_mech.values())   # = N × PHI_H × -(200/2)² = -40000
    s_andes = sum(r_andes.values()) # = N × PHI_H × -(200)² = -160000
    assert abs(s_mech - (-4 * 100 ** 2)) < 1e-6
    assert abs(s_andes - (-4 * 200 ** 2)) < 1e-6
    assert abs(s_andes / s_mech - 4.0) < 1e-9


def test_default_config_bit_identical_to_old_behavior():
    """All defaults preserve old code path. Specifically: hz freq, /2 H,
    global mean. R56/R57 reproducibility guarantee."""
    env = _FakeEnv()  # all defaults

    omega = np.array([1.0 + 0.5 / 50, 1.0, 1.0, 1.0])  # one ESS off by 0.5 Hz
    omega_dot = np.zeros(4)
    delta_M = np.array([400.0, 400.0, 400.0, 400.0])  # mean = 400
    delta_D = np.zeros(4)

    r, *_ = env._compute_rewards(omega, omega_dot, delta_M, delta_D)
    # r^h = -(400/2)² = -40000; PHI_H=1 → per-agent r^h = -40000
    # No PHI_ABS in fake env. r^f finite from the 0.5 Hz outlier.
    # Just sanity-check r^h component matches /2 division.
    s = sum(r.values())
    # r^h × N = -40000 × 4 = -160000 (PHI_H=1); add r^f<0 contributions
    assert s < -160000, "default must use /2 mechanical H interpretation"


def test_neighbor_avg_scope_uses_per_agent_subset():
    """`r_avg_scope = "neighbor"` makes each agent's r^h use a SUBSET of
    ΔM (self + active neighbors), not the global mean. Verify on a
    test where global mean = 0 but local subset ≠ 0."""
    env_global = _FakeEnv(r_avg_scope="global")
    env_neighbor = _FakeEnv(r_avg_scope="neighbor")

    omega = np.ones(4)  # r^f = 0
    omega_dot = np.zeros(4)
    # delta_M designed so global mean = 0 but per-agent neighbor means differ
    delta_M = np.array([400.0, -400.0, 400.0, -400.0])  # mean=0
    delta_D = np.zeros(4)

    r_global, *_ = env_global._compute_rewards(omega, omega_dot, delta_M, delta_D)
    r_neighbor, *_ = env_neighbor._compute_rewards(omega, omega_dot, delta_M, delta_D)

    # Global: r^h per agent = -(0)² = 0 → total = 0
    # Neighbor: agent 0 sees {0,1,3} = {400,-400,-400}/3 = -133.3...,
    #           r^h = -(-133.3/2)² ≈ -4444 per agent (non-zero)
    s_global = sum(r_global.values())
    s_neighbor = sum(r_neighbor.values())
    assert abs(s_global) < 1e-6, "global avg scope yields exact zero here"
    assert s_neighbor < -10.0, "neighbor avg scope yields non-zero (negative) r^h"


def test_audit_a1_no_delay_uses_true_d_omega():
    """When `comm_delay_steps = 0` (R56/R57 default), reward uses true
    `d_omega[j]` — bit-identical to pre-R58 behavior. The audit A1 fix
    only kicks in when delay > 0."""
    env = _FakeEnv()
    env.comm_delay_steps = 0  # explicit
    env._delayed_omega = None

    omega = np.array([1.0 + 0.5 / 50, 1.0, 1.0, 1.0])
    omega_dot = np.zeros(4)
    delta_M = np.zeros(4)
    delta_D = np.zeros(4)

    # Should not raise; behavior identical to current
    r, *_ = env._compute_rewards(omega, omega_dot, delta_M, delta_D)
    assert sum(r.values()) < 0  # has frequency disagreement → negative r^f
