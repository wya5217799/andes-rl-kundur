"""``V4Config.action_penalty_mode = "normalized"`` — proper fix for
the CLM-0043 reward-landscape asymmetry surfaced by R38 and confirmed
by R40 with the extreme phi=0 ablation.

Under ``"physical"`` (default, paper-faithful, bit-identical), the
reward computes ``r_h = -(mean(ΔM)/2)² × PHI_H`` and  ``r_d =
-(mean(ΔD))² × PHI_D``. At V4 action range [-200, 600], that produces
500–1000× more action cost than frequency cost, trapping the actor
near zero.

Under ``"normalized"``, the reward uses ``a ∈ [-1, 1]`` (the
normalized action passed to step()) so action-cost is O(1) regardless
of action range — restoring the paper's intended PHI semantics.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.env.andes.v4_config import V4Config  # noqa: E402


def _skip_without_real_andes() -> None:
    try:
        import andes
    except ModuleNotFoundError:
        pytest.skip("real ANDES is WSL-only; run env-instantiation tests under WSL")
    if not callable(getattr(andes, "get_case", None)):
        pytest.skip("real ANDES is unavailable; only a test stub is installed")


def test_v4_config_action_penalty_mode_defaults_physical():
    """Backward-compatibility: paper-faithful bit-identical preserves
    the historic 'physical' penalty mode."""
    cfg = V4Config()
    assert cfg.action_penalty_mode == "physical"


def test_v4_config_accepts_normalized_mode():
    """The new mode is settable on the frozen dataclass."""
    cfg = V4Config(action_penalty_mode="normalized")
    assert cfg.action_penalty_mode == "normalized"


def test_v4_config_rejects_unknown_mode():
    """Catch typos at construction, not at first reward call."""
    with pytest.raises(ValueError):
        V4Config(action_penalty_mode="quadratic")


def test_action_penalty_magnitudes_under_normalized_mode():
    """Same physical ΔM = full action range yields O(1) penalty
    under normalized mode (vs O(1000) under physical mode).

    Direct probe: instantiate two envs, mock the reward computation
    inputs, and check the magnitude ratio is in the expected band.
    """
    _skip_without_real_andes()
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4

    env_phys = AndesMultiVSGEnvV4(
        random_disturbance=False, comm_fail_prob=0.0,
        config=V4Config(action_penalty_mode="physical"),
    )
    env_norm = AndesMultiVSGEnvV4(
        random_disturbance=False, comm_fail_prob=0.0,
        config=V4Config(action_penalty_mode="normalized"),
    )

    # Cheap probe: max-magnitude action vector.
    # Under physical: r_h = -(mean(ΔM)/2)^2 * PHI_H = -(600/2)^2 * 0.0056 = -504
    # Under normalized: r_h = -(mean(a_norm))^2 * PHI_H ≈ -(1.0)^2 * 0.0056 = -0.0056
    # Ratio: physical/normalized ≈ 90000×
    delta_M_max = np.full(env_phys.N_AGENTS, env_phys.DM_MAX)  # all at max
    delta_D_max = np.full(env_phys.N_AGENTS, env_phys.DD_MAX)
    omega = np.ones(env_phys.N_AGENTS)
    omega_dot = np.zeros(env_phys.N_AGENTS)

    # Set up minimal comm state so _compute_rewards doesn't KeyError
    env_phys.comm_eta = {(i, j): 0
                         for i in range(env_phys.N_AGENTS)
                         for j in env_phys.COMM_ADJ[i]}
    env_norm.comm_eta = env_phys.comm_eta

    _, _, r_h_phys, _ = env_phys._compute_rewards(omega, omega_dot, delta_M_max, delta_D_max)
    _, _, r_h_norm, _ = env_norm._compute_rewards(omega, omega_dot, delta_M_max, delta_D_max)

    # Physical mode: |r_h| ≈ 500 (= 600^2/4 * 0.0056 * 4 agents)
    # Normalized mode: |r_h| ≈ 0.02 (= 1^2 * 0.0056 * 4 agents)
    # Ratio physical/normalized should be ~10000×
    ratio = abs(r_h_phys) / max(abs(r_h_norm), 1e-9)
    assert 1000 < ratio < 1_000_000, (
        f"Normalized mode should be ~10000× smaller penalty, got ratio {ratio:.1e}"
    )
