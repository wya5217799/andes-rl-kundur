"""Directed tests for the R424 guard-aligned action-constraint learner.

Windows-safe: no ANDES import.  Pins the frozen multiplier constants, the
subclass wiring, the actor-objective terms, the dual-step semantics, the
checkpoint roundtrip of the new multipliers, and the byte-identity
boundary (the scalar learner keeps the sealed base path).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.agents.cd_matd3 import (  # noqa: E402
    SlewAwareCDMATD3,
    SlewAwareYangScalarTD3,
)
from andes_rl_kundur.agents.cd_matd3_guard_constraints import (  # noqa: E402
    GUARD_MULTIPLIER_MAX,
    GUARD_MULTIPLIER_STEP,
    GuardConstrainedSlewAwareCDMATD3,
)


def test_constants_frozen() -> None:
    assert GUARD_MULTIPLIER_STEP == 0.05
    assert GUARD_MULTIPLIER_MAX == 10.0


def test_subclass_wiring() -> None:
    assert issubclass(
        GuardConstrainedSlewAwareCDMATD3, SlewAwareCDMATD3
    )
    agent = GuardConstrainedSlewAwareCDMATD3(lagrange_initial=1.0)
    assert agent.out_dim == 2
    assert agent.mu_rms == 0.0 and agent.mu_tv == 0.0


def test_guard_multiplier_step_semantics() -> None:
    agent = GuardConstrainedSlewAwareCDMATD3(lagrange_initial=1.0)
    mu_rms, mu_tv = agent.guard_multiplier_step(0.5, -0.2)
    assert abs(mu_rms - 0.025) < 1e-12  # 0.05 * 0.5
    assert mu_tv == 0.0  # negative residual clips at 0
    # cap at the frozen ceiling
    for _index in range(1000):
        mu_rms, _ = agent.guard_multiplier_step(10.0, 0.0)
    assert mu_rms == GUARD_MULTIPLIER_MAX


def test_update_with_filled_buffer_finite() -> None:
    agent = GuardConstrainedSlewAwareCDMATD3(lagrange_initial=1.0)
    torch.manual_seed(0)
    np.random.seed(0)
    for _fill_index in range(agent.batch_size + 8):
        agent.store(
            np.random.randn(28).astype(np.float32),
            np.random.randn(8).astype(np.float32),
            np.random.randn(8).astype(np.float32),
            np.random.randn(2).astype(np.float32),
            np.random.randn(28).astype(np.float32),
            False,
        )
    diagnostics = agent.update()
    assert diagnostics is not None
    assert np.isfinite(diagnostics["critic_loss"])
    # the actor branch runs on the second update (policy_delay 2)
    diagnostics = agent.update()
    assert diagnostics is not None
    assert np.isfinite(diagnostics["actor_loss_mean"])
    assert np.isfinite(diagnostics["mu_rms"])
    assert np.isfinite(diagnostics["mu_tv"])


def test_checkpoint_roundtrip_preserves_multipliers() -> None:
    agent = GuardConstrainedSlewAwareCDMATD3(lagrange_initial=1.0)
    agent.guard_multiplier_step(0.5, 1.5)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "probe.pt"
        agent.save(probe)
        restored = GuardConstrainedSlewAwareCDMATD3(lagrange_initial=1.0)
        restored.load(probe)
    assert abs(restored.mu_rms - agent.mu_rms) < 1e-12
    assert abs(restored.mu_tv - agent.mu_tv) < 1e-12
    assert abs(restored.lagrange - agent.lagrange) < 1e-12


def test_scalar_learner_keeps_sealed_base_path() -> None:
    # The isolation control: the scalar arm must keep its sealed R419
    # update (no guard terms) so its bit-identity anchor holds.
    assert SlewAwareYangScalarTD3.update is not (  # type: ignore[attr-defined]
        GuardConstrainedSlewAwareCDMATD3.update
    )
    assert not hasattr(SlewAwareYangScalarTD3, "guard_multiplier_step")
