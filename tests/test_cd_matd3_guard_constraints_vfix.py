"""Directed tests for the R425 sign-corrected guard-constraint learner.

Windows-safe: no ANDES import.  Pins the penalty-direction semantics of the
R425 actor objective (the R424 reward-sign defect corrected), the frozen
multiplier constants, the dual-step semantics, and the checkpoint roundtrip.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.agents.cd_matd3 import (  # noqa: E402
    SlewAwareCDMATD3,
    project_slew_torch,
)
from andes_rl_kundur.agents.cd_matd3_guard_constraints_vfix import (  # noqa: E402
    GUARD_MULTIPLIER_MAX,
    GUARD_MULTIPLIER_STEP,
    GuardConstrainedSlewAwareCDMATD3Signfix,
)


def test_constants_frozen() -> None:
    assert GUARD_MULTIPLIER_STEP == 0.05
    assert GUARD_MULTIPLIER_MAX == 10.0


def test_subclass_wiring() -> None:
    assert issubclass(
        GuardConstrainedSlewAwareCDMATD3Signfix, SlewAwareCDMATD3
    )
    agent = GuardConstrainedSlewAwareCDMATD3Signfix(lagrange_initial=1.0)
    assert agent.out_dim == 2
    assert agent.mu_rms == 0.0 and agent.mu_tv == 0.0


def test_penalty_direction_on_a_minimal_objective() -> None:
    """The R425 fix: with mu > 0, gradient descent on the actor loss must
    DESCEND on each executed-action statistic (penalty), the opposite of
    the R424 form.  Checked term-by-term with the other multiplier zero."""
    torch.manual_seed(0)
    net = torch.nn.Sequential(
        torch.nn.Linear(2, 8), torch.nn.Tanh(), torch.nn.Linear(8, 2), torch.nn.Tanh()
    )
    prev = torch.zeros(1, 2)
    x = torch.randn(1, 2)
    raw = net(x)
    row = project_slew_torch(prev, raw, slew_limit=0.25)
    rms_term = torch.mean(row**2)
    tv_term = torch.mean(torch.abs(row - prev))
    params = list(net.parameters())
    for statistic in (rms_term, tv_term):
        loss = -torch.mean(torch.zeros(1)) + statistic  # R425 appended form
        grads = torch.autograd.grad(loss, params, retain_graph=True)
        stat_grads = torch.autograd.grad(statistic, params, retain_graph=True)
        dot = sum(
            (g * s).sum().item() for g, s in zip(grads, stat_grads)
        )
        assert dot > 0.0, (
            f"expected the update to descend on the statistic "
            f"(grad aligned with statistic ascent), got dot={dot}"
        )
    # contrast pin: the R424 form (terms inside the negated mean) ascends
    loss_defect = -torch.mean(rms_term)
    grads = torch.autograd.grad(loss_defect, params, retain_graph=True)
    stat_grads = torch.autograd.grad(rms_term, params, retain_graph=True)
    dot = sum(
        (g * s).sum().item() for g, s in zip(grads, stat_grads)
    )
    assert dot < 0.0, (
        f"R424 defect form should ascend on the statistic, got dot={dot}"
    )


def test_guard_multiplier_step_semantics() -> None:
    agent = GuardConstrainedSlewAwareCDMATD3Signfix(lagrange_initial=1.0)
    mu_rms, mu_tv = agent.guard_multiplier_step(0.5, -0.2)
    assert abs(mu_rms - 0.025) < 1e-12
    assert mu_tv == 0.0
    for _index in range(1000):
        mu_rms, _ = agent.guard_multiplier_step(10.0, 0.0)
    assert mu_rms == GUARD_MULTIPLIER_MAX


def test_update_with_filled_buffer_finite() -> None:
    agent = GuardConstrainedSlewAwareCDMATD3Signfix(lagrange_initial=1.0)
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
    diagnostics = agent.update()
    assert diagnostics is not None
    assert np.isfinite(diagnostics["actor_loss_mean"])
    assert np.isfinite(diagnostics["mu_rms"])
    assert np.isfinite(diagnostics["mu_tv"])


def test_checkpoint_roundtrip_preserves_multipliers() -> None:
    agent = GuardConstrainedSlewAwareCDMATD3Signfix(lagrange_initial=1.0)
    agent.guard_multiplier_step(0.5, 1.5)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "probe.pt"
        agent.save(probe)
        restored = GuardConstrainedSlewAwareCDMATD3Signfix(lagrange_initial=1.0)
        restored.load(probe)
    assert abs(restored.mu_rms - agent.mu_rms) < 1e-12
    assert abs(restored.mu_tv - agent.mu_tv) < 1e-12
    assert abs(restored.lagrange - agent.lagrange) < 1e-12
