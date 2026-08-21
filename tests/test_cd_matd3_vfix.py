"""Directed tests for the R423 repair learner module (cd_matd3_vfix).

Windows-safe: no ANDES import.  Pins the frozen clip constant, the
subclass wiring, the exact critic-update clip position, and the
byte-identity boundary (the scalar learner keeps the sealed base path).
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
    _SlewAwareJointTD3Base,
    SlewAwareCDMATD3,
    SlewAwareYangScalarTD3,
)
from andes_rl_kundur.agents.cd_matd3_vfix import (  # noqa: E402
    CRITIC_GRAD_CLIP_MAX_NORM,
    ClippedCriticSlewAwareCDMATD3,
)


def _synthetic_batch(batch_size: int = 8) -> dict[str, torch.Tensor]:
    return {
        "obs": torch.randn(batch_size, 28),
        "prev_actions": torch.randn(batch_size, 8),
        "actions": torch.randn(batch_size, 8),
        "rewards": torch.randn(batch_size, 2),
        "next_obs": torch.randn(batch_size, 28),
        "dones": torch.zeros(batch_size, 1),
    }


def test_clip_constant_frozen() -> None:
    assert CRITIC_GRAD_CLIP_MAX_NORM == 1.0


def test_subclass_wiring() -> None:
    assert issubclass(ClippedCriticSlewAwareCDMATD3, SlewAwareCDMATD3)
    agent = ClippedCriticSlewAwareCDMATD3(lagrange_initial=1.0)
    assert agent.out_dim == 2


def test_critic_update_applies_clip_exactly_once() -> None:
    agent = ClippedCriticSlewAwareCDMATD3(lagrange_initial=1.0)
    calls: list[tuple[object, float]] = []
    original = torch.nn.utils.clip_grad_norm_

    def recording_clip(parameters, max_norm, *args, **kwargs):
        calls.append((list(parameters), float(max_norm)))
        return original(parameters, max_norm, *args, **kwargs)

    monkeypatch_target = torch.nn.utils
    monkeypatch_target.clip_grad_norm_ = recording_clip
    try:
        loss = agent._critic_update(_synthetic_batch())
    finally:
        monkeypatch_target.clip_grad_norm_ = original
    assert torch.isfinite(loss)
    assert len(calls) == 1
    parameters, max_norm = calls[0]
    assert max_norm == CRITIC_GRAD_CLIP_MAX_NORM
    recorded = list(parameters)
    assert recorded == list(agent.critic.parameters())


def test_critic_update_loss_finite_on_synthetic_batch() -> None:
    agent = ClippedCriticSlewAwareCDMATD3(lagrange_initial=1.0)
    torch.manual_seed(0)
    loss = agent._critic_update(_synthetic_batch())
    assert torch.isfinite(loss)
    assert loss.item() > 0.0


def test_end_to_end_update_with_filled_buffer() -> None:
    agent = ClippedCriticSlewAwareCDMATD3(lagrange_initial=1.0)
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


def test_scalar_learner_keeps_sealed_base_critic_path() -> None:
    # The isolation control: the scalar arm must keep the sealed base
    # critic update (no clip) so its R422 bit-identity anchor holds.
    assert SlewAwareYangScalarTD3._critic_update is (  # type: ignore[attr-defined]
        _SlewAwareJointTD3Base._critic_update
    )
    assert SlewAwareCDMATD3._critic_update is (  # type: ignore[attr-defined]
        _SlewAwareJointTD3Base._critic_update
    )
    assert ClippedCriticSlewAwareCDMATD3._critic_update is not (  # type: ignore[attr-defined]
        _SlewAwareJointTD3Base._critic_update
    )
