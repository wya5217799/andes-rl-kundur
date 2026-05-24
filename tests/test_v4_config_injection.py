"""V4Config injection — verify the explicit-config interface preserves
paper-faithful behaviour and prevents the silent-inheritance bug class
that produced CLM-0040 (G4 inertia).

Tracer behaviour 1 — bit-identical: ``V4(config=V4Config.paper_faithful())``
produces the same t=0 freq_hz as ``V4()`` (no config arg).

Subsequent behaviours added one at a time per /tdd vertical-slice rule.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _real_andes_available() -> bool:
    try:
        import andes
    except ModuleNotFoundError:
        return False
    return callable(getattr(andes, "get_case", None))


if not _real_andes_available():
    pytest.skip("real ANDES is WSL-only; run V4 env tests under WSL", allow_module_level=True)

from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from andes_rl_kundur.env.andes.v4_config import V4Config  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

SEED = 42
STEPS = 50


def _run(env: AndesMultiVSGEnvV4, scen: str) -> list[float]:
    env.seed(SEED)
    env.STEPS_PER_EPISODE = STEPS
    env.reset(delta_u=SCENARIOS[scen])
    actions = {i: np.zeros(2, dtype=np.float32) for i in range(env.N_AGENTS)}
    _, _, _, info = env.step(actions)
    env.close()
    return info["freq_hz"].astype(float).tolist()


def test_config_phi_h_flows_to_instance():
    """Tracer: V4Config(phi_h=X) makes the instance see X (not the class default).

    Forces a real implementation — a stub that accepts ``config=`` but
    ignores it would pass the bit-identical check below trivially
    (V4Config.paper_faithful() defaults to the same values), but fails
    here.
    """
    env = AndesMultiVSGEnvV4(
        random_disturbance=False, comm_fail_prob=0.0,
        config=V4Config(phi_h=999.0),
    )
    assert env.PHI_H == 999.0, (
        "V4 instance must read phi_h from the supplied config, "
        f"got {env.PHI_H}"
    )


def test_paper_faithful_config_matches_default():
    """V4Config.paper_faithful() reproduces the no-config V4 trajectory."""
    default_env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    configured_env = AndesMultiVSGEnvV4(
        random_disturbance=False, comm_fail_prob=0.0,
        config=V4Config.paper_faithful(),
    )
    f_default = _run(default_env, "load_step_1")
    f_configured = _run(configured_env, "load_step_1")
    np.testing.assert_allclose(f_configured, f_default, atol=1e-9, rtol=0)


def test_config_does_not_mutate_class_attribute():
    """Root-cause regression for CLM-0040: building a config-customised
    instance must NOT change the class-level default.

    Pre-2026-05-17 scripts/train.py used ``setattr(AndesMultiVSGEnvV4,
    ...)`` to override hyperparameters, leaking state across instances
    and across processes. The config-injection path replaces that.
    """
    class_default_before = AndesMultiVSGEnvV4.PHI_H
    AndesMultiVSGEnvV4(
        random_disturbance=False, comm_fail_prob=0.0,
        config=V4Config(phi_h=42.0),
    )
    class_default_after = AndesMultiVSGEnvV4.PHI_H
    assert class_default_after == class_default_before, (
        f"Class attribute PHI_H mutated by config injection: "
        f"{class_default_before} -> {class_default_after}"
    )


def test_two_envs_with_different_configs_are_isolated():
    """Behaviour: constructing env A with phi_h=1.0 must NOT affect env
    B's view of phi_h. The old monkey-patch pattern failed this."""
    a = AndesMultiVSGEnvV4(
        random_disturbance=False, comm_fail_prob=0.0,
        config=V4Config(phi_h=1.0),
    )
    b = AndesMultiVSGEnvV4(
        random_disturbance=False, comm_fail_prob=0.0,
        config=V4Config(phi_h=2.0),
    )
    assert a.PHI_H == 1.0
    assert b.PHI_H == 2.0


def test_v4_config_is_immutable():
    """V4Config is frozen — accidental in-flight mutation must fail loudly."""
    cfg = V4Config()
    with pytest.raises(Exception):  # FrozenInstanceError is dataclass-specific
        cfg.phi_h = 999.0  # type: ignore[misc]


def test_config_lambda_smooth_flows_to_instance():
    """R50 opt B: V4Config.lambda_smooth must reach env._lambda_smooth so
    train.py / eval scripts can enable anti-smoothness reward shaping via
    config instead of LAMBDA_SMOOTH env var."""
    env = AndesMultiVSGEnvV4(
        random_disturbance=False, comm_fail_prob=0.0,
        config=V4Config(lambda_smooth=-10.0),
    )
    assert env._lambda_smooth == -10.0


def test_config_include_own_action_obs_bumps_obs_dim():
    """R50 opt B: V4Config.include_own_action_obs=True must bump instance
    OBS_DIM by 2 (the R03 probe) — replaces the INCLUDE_OWN_ACTION_OBS env
    var workaround used in R49."""
    env = AndesMultiVSGEnvV4(
        random_disturbance=False, comm_fail_prob=0.0,
        config=V4Config(include_own_action_obs=True),
    )
    assert env.OBS_DIM == AndesMultiVSGEnvV4.OBS_DIM + 2
    assert env._include_own_action_obs is True


def test_config_lambda_smooth_default_is_zero_and_off():
    """Bit-identical paper-faithful guarantee: V4Config() with no override
    leaves the env reward path unchanged (lambda_smooth=0.0 disables the
    r_smooth term entirely)."""
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    assert env._lambda_smooth == 0.0
    assert env._include_own_action_obs is False
    assert env.OBS_DIM == AndesMultiVSGEnvV4.OBS_DIM


def test_deviation_summary_truthfully_reports_g4_state():
    """The introspection helper must report what ZERO_G4_INERTIA actually is.

    Pre-fix the dict always said ``"preserved (paper Kundur 4 SG)"`` even
    when ZERO_G4_INERTIA=True was zeroing G4 — that was the same class
    of silent-disagreement bug as CLM-0040.
    """
    summary = AndesMultiVSGEnvV4.deviation_summary()
    assert "zeroed" in summary["g4_inertia"], (
        f"Default V4 has ZERO_G4_INERTIA=True so deviation_summary "
        f"must say 'zeroed', got: {summary['g4_inertia']!r}"
    )
