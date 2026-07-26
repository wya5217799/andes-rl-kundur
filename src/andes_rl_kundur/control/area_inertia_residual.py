"""R278 one-dimensional two-area inertia residual contract.

The learned policy emits one raw scalar per VSG.  A deterministic coordination
layer reduces those four values to the only executed learned coordinate,
``q * [1, 1, -1, -1]``.  Magnitude and slew are applied to ``q`` itself so the
zero-sum and within-area equality constraints cannot be broken by elementwise
clipping.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import torch

AREA_PATTERN = np.asarray([1.0, 1.0, -1.0, -1.0], dtype=np.float32)


@dataclass(frozen=True)
class AreaInertiaResidualContract:
    """Frozen R278 learned-action and reward contract."""

    agent_count: int = 4
    q_max: float = 0.25
    q_slew_max: float = 0.25
    common_amplitude: float = 0.25
    active_steps: int = 15
    control_dt_seconds: float = 0.2
    baseline_m: float = 200.0
    baseline_d: float = 100.0
    dm_max: float = 600.0
    sync_scale_hz: float = 0.05
    area_scale_hz: float = 0.05
    action_tv_weight: float = 0.01

    def __post_init__(self) -> None:
        if self.agent_count != 4:
            raise ValueError("R278 requires exactly four VSG agents")
        if self.q_max <= 0.0:
            raise ValueError("q_max must be positive")
        if not 0.0 < self.q_slew_max <= 2.0 * self.q_max:
            raise ValueError("q_slew_max must be in (0, 2*q_max]")
        if self.common_amplitude < self.q_max:
            raise ValueError(
                "common_amplitude must cover q_max so executed M stays non-negative"
            )
        if self.active_steps <= 0:
            raise ValueError("active_steps must be positive")

    @property
    def pattern(self) -> np.ndarray:
        return AREA_PATTERN.copy()

    def telemetry(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.update(
            {
                "schema_version": 1,
                "name": "r278_two_area_scalar_zero_sum",
                "area_pattern": AREA_PATTERN.astype(float).tolist(),
                "raw_to_q": (
                    "q_max*0.5*(mean(z[0:2])-mean(z[2:4]))"
                ),
                "executed_residual": "q*[1,1,-1,-1]",
                "d_action_norm": 0.0,
            }
        )
        return payload


def r278_area_inertia_contract() -> AreaInertiaResidualContract:
    """Return the immutable R278 contract."""
    return AreaInertiaResidualContract()


def _validate_raw_numpy(raw_z: np.ndarray) -> np.ndarray:
    raw = np.asarray(raw_z, dtype=np.float32)
    if raw.shape[-1:] != (4,):
        raise ValueError(f"raw_z must end in four agents, got shape {raw.shape}")
    if not np.all(np.isfinite(raw)):
        raise ValueError("raw_z must be finite")
    return raw


def project_raw_to_q_numpy(
    raw_z: np.ndarray,
    *,
    previous_q: float | np.ndarray = 0.0,
    active: bool | np.ndarray = True,
    contract: AreaInertiaResidualContract | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Project raw agent votes to scalar ``q`` and the zero-sum residual."""
    cfg = contract or r278_area_inertia_contract()
    raw = _validate_raw_numpy(raw_z)
    q_raw = cfg.q_max * 0.5 * (
        np.mean(raw[..., :2], axis=-1) - np.mean(raw[..., 2:], axis=-1)
    )
    prev = np.asarray(previous_q, dtype=np.float32)
    q = np.clip(
        q_raw,
        prev - cfg.q_slew_max,
        prev + cfg.q_slew_max,
    )
    q = np.clip(q, -cfg.q_max, cfg.q_max)
    q = np.where(np.asarray(active, dtype=bool), q, 0.0).astype(np.float32)
    residual = q[..., None] * AREA_PATTERN
    return q, residual.astype(np.float32)


def project_raw_to_q_torch(
    raw_z: torch.Tensor,
    *,
    previous_q: torch.Tensor | float = 0.0,
    active: torch.Tensor | bool = True,
    contract: AreaInertiaResidualContract | None = None,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Differentiable Torch equivalent of :func:`project_raw_to_q_numpy`."""
    cfg = contract or r278_area_inertia_contract()
    if raw_z.shape[-1:] != (4,):
        raise ValueError(
            f"raw_z must end in four agents, got shape {tuple(raw_z.shape)}"
        )
    if not torch.isfinite(raw_z).all():
        raise ValueError("raw_z must be finite")
    q_raw = cfg.q_max * 0.5 * (
        raw_z[..., :2].mean(dim=-1) - raw_z[..., 2:].mean(dim=-1)
    )
    prev = torch.as_tensor(
        previous_q,
        dtype=raw_z.dtype,
        device=raw_z.device,
    )
    q = torch.maximum(
        torch.minimum(q_raw, prev + cfg.q_slew_max),
        prev - cfg.q_slew_max,
    )
    q = q.clamp(-cfg.q_max, cfg.q_max)
    active_tensor = torch.as_tensor(
        active,
        dtype=torch.bool,
        device=raw_z.device,
    )
    q = torch.where(active_tensor, q, torch.zeros_like(q))
    pattern = torch.as_tensor(
        AREA_PATTERN,
        dtype=raw_z.dtype,
        device=raw_z.device,
    )
    return q, q.unsqueeze(-1) * pattern


def executed_md_actions_numpy(
    raw_z: np.ndarray,
    *,
    previous_q: float = 0.0,
    step: int,
    contract: AreaInertiaResidualContract | None = None,
) -> tuple[float, np.ndarray, np.ndarray]:
    """Return ``q``, residual vector and four normalized ``[M,D]`` actions."""
    cfg = contract or r278_area_inertia_contract()
    if step < 0:
        raise ValueError("step must be non-negative")
    active = step < cfg.active_steps
    q, residual = project_raw_to_q_numpy(
        raw_z,
        previous_q=previous_q,
        active=active,
        contract=cfg,
    )
    common = cfg.common_amplitude if active else 0.0
    m_action = common + residual
    actions = np.stack(
        [m_action, np.zeros(cfg.agent_count, dtype=np.float32)],
        axis=-1,
    ).astype(np.float32)
    return float(q), residual, actions


def q_from_signed_residual_observation(
    signed_residual_normalized: torch.Tensor,
) -> torch.Tensor:
    """Recover previous normalized ``q`` from four signed residual slots."""
    if signed_residual_normalized.shape[-1:] != (4,):
        raise ValueError("signed residual observation must end in four agents")
    pattern = torch.as_tensor(
        AREA_PATTERN,
        dtype=signed_residual_normalized.dtype,
        device=signed_residual_normalized.device,
    )
    return (signed_residual_normalized * pattern).mean(dim=-1)
