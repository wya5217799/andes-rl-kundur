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

from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
from andes_rl_kundur.env.andes.v4_config import V4Config
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS

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
