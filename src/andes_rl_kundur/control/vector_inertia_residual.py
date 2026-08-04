"""R292 neighbour-edge inertia residual execution contract.

Three oriented communication-edge flows span the four-device zero-sum
subspace.  Each device executes only the signed sum of flows on its incident
edges; there is no scalar vote aggregation or joint-observation action seam.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

EDGE_ENDPOINTS = ((0, 1), (1, 2), (2, 3))
INCIDENCE = np.asarray(
    [
        [-1.0, 0.0, 0.0],
        [1.0, -1.0, 0.0],
        [0.0, 1.0, -1.0],
        [0.0, 0.0, 1.0],
    ],
    dtype=np.float32,
)


@dataclass(frozen=True)
class VectorInertiaResidualContract:
    """Frozen R292 communication graph and physical action limits."""

    agent_count: int = 4
    edge_count: int = 3
    edge_flow_max: float = 0.125
    edge_slew_max: float = 0.125
    node_residual_max: float = 0.25
    node_slew_max: float = 0.25
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
        if self.agent_count != 4 or self.edge_count != 3:
            raise ValueError("R292 requires four nodes and three path edges")
        if self.edge_flow_max <= 0.0:
            raise ValueError("edge_flow_max must be positive")
        if not 0.0 < self.edge_slew_max <= 2.0 * self.edge_flow_max:
            raise ValueError("edge_slew_max must lie in (0, 2*edge_flow_max]")
        if self.node_residual_max != 2.0 * self.edge_flow_max:
            raise ValueError("path interior-node limit must equal two edge flows")
        if self.node_slew_max != 2.0 * self.edge_slew_max:
            raise ValueError("path interior-node slew must equal two edge slews")
        if self.common_amplitude < self.node_residual_max:
            raise ValueError("common action must keep executed inertia non-negative")

    def telemetry(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.update(
            {
                "schema_version": 1,
                "name": "r292_path_edge_zero_sum_vector",
                "edge_endpoints": [list(edge) for edge in EDGE_ENDPOINTS],
                "edge_orientation": "lower_index_to_higher_index",
                "node_residual": "incidence@edge_flow",
                "central_action_aggregation": False,
                "d_action_norm": 0.0,
            }
        )
        return payload


def r292_vector_residual_contract() -> VectorInertiaResidualContract:
    """Return the immutable R292 vector-action contract."""

    return VectorInertiaResidualContract()


def execute_edge_residual_numpy(
    raw_edge: np.ndarray,
    *,
    previous_edge: np.ndarray,
    step: int,
    contract: VectorInertiaResidualContract | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Execute normalized edge commands as local zero-sum node actions."""

    cfg = contract or r292_vector_residual_contract()
    if step < 0:
        raise ValueError("step must be non-negative")
    raw = np.asarray(raw_edge, dtype=np.float32).reshape(-1)
    previous = np.asarray(previous_edge, dtype=np.float32).reshape(-1)
    if raw.shape != (cfg.edge_count,) or previous.shape != (cfg.edge_count,):
        raise ValueError("raw_edge and previous_edge must each have shape (3,)")
    if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(previous)):
        raise ValueError("edge actions must be finite")

    target = np.clip(raw, -1.0, 1.0) * np.float32(cfg.edge_flow_max)
    edge = np.clip(
        target,
        previous - np.float32(cfg.edge_slew_max),
        previous + np.float32(cfg.edge_slew_max),
    )
    edge = np.clip(edge, -cfg.edge_flow_max, cfg.edge_flow_max)
    if step >= cfg.active_steps:
        edge = np.zeros(cfg.edge_count, dtype=np.float32)
    edge = np.asarray(edge, dtype=np.float32)
    node = np.asarray(INCIDENCE @ edge, dtype=np.float32)
    common = cfg.common_amplitude if step < cfg.active_steps else 0.0
    actions = np.stack(
        [common + node, np.zeros(cfg.agent_count, dtype=np.float32)],
        axis=-1,
    ).astype(np.float32)
    return edge, node, actions
