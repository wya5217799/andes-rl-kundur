"""R293 causal neighbour-edge classical inertia-allocation prior.

The controller ranks transient severity from absolute local measurements and
moves the bounded zero-sum inertia residual toward the more severe endpoint.
It is sign-symmetric for positive and negative disturbances and requires only
one-hop endpoint information.  The frozen nine-candidate family is a fair
classical distributed comparator, not a stability certificate.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from andes_rl_kundur.control.vector_inertia_residual import EDGE_ENDPOINTS

FEATURE_WEIGHTS: dict[str, tuple[float, float, float]] = {
    "rocof": (0.0, 1.0, 0.0),
    "freq_rocof": (0.5, 0.5, 0.0),
    "full": (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0),
}
GAINS = (0.25, 0.5, 1.0)


@dataclass(frozen=True)
class ClassicalEdgeContract:
    """One member of the frozen R293 classical development family."""

    family: str
    gain: float
    residual_scale: float = 0.5

    def __post_init__(self) -> None:
        if self.family not in FEATURE_WEIGHTS:
            raise ValueError(f"unknown severity family: {self.family}")
        if self.gain <= 0.0:
            raise ValueError("gain must be positive")
        if not 0.0 < self.residual_scale <= 1.0:
            raise ValueError("residual_scale must lie in (0, 1]")

    @property
    def weights(self) -> tuple[float, float, float]:
        return FEATURE_WEIGHTS[self.family]

    @property
    def name(self) -> str:
        return f"classical_edge_{self.family}_k{self.gain:g}".replace(".", "p")

    def telemetry(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.update(
            {
                "schema_version": 1,
                "name": self.name,
                "feature_order": [
                    "abs_normalized_delta_f",
                    "abs_normalized_rocof",
                    "abs_normalized_delta_p",
                ],
                "feature_weights": list(self.weights),
                "law": "raw_edge=tanh(gain*(severity_target-severity_source))",
                "positive_flow": "moves inertia from source to target",
                "information": "current observations of the two edge endpoints only",
                "central_action_aggregation": False,
                "stability_certificate": False,
            }
        )
        return payload


def classical_edge_candidates() -> tuple[ClassicalEdgeContract, ...]:
    """Return the prospectively fixed three-family by three-gain grid."""

    return tuple(
        ClassicalEdgeContract(family=family, gain=gain)
        for family in ("rocof", "freq_rocof", "full")
        for gain in GAINS
    )


def _stack_observations(
    observations: Mapping[int, np.ndarray] | np.ndarray,
) -> np.ndarray:
    if isinstance(observations, Mapping):
        if set(observations) != set(range(4)):
            raise ValueError("observations must contain exactly agents 0..3")
        obs = np.stack(
            [np.asarray(observations[index], dtype=np.float32) for index in range(4)]
        )
    else:
        obs = np.asarray(observations, dtype=np.float32)
    if obs.shape != (4, 5):
        raise ValueError(f"observations must have shape (4, 5), got {obs.shape}")
    if not np.all(np.isfinite(obs)):
        raise ValueError("observations must be finite")
    return obs


def node_severity(
    observations: Mapping[int, np.ndarray] | np.ndarray,
    contract: ClassicalEdgeContract,
) -> np.ndarray:
    """Return non-negative local transient severity for the four devices."""

    obs = _stack_observations(observations)
    features = np.abs(obs[:, [0, 1, 3]].astype(np.float64))
    weights = np.asarray(contract.weights, dtype=np.float64)
    return np.asarray(features @ weights, dtype=np.float32)


def edge_severity_delta(
    observations: Mapping[int, np.ndarray] | np.ndarray,
    contract: ClassicalEdgeContract,
) -> np.ndarray:
    """Return target-minus-source severity independently on each path edge."""

    severity = node_severity(observations, contract)
    return np.asarray(
        [severity[target] - severity[source] for source, target in EDGE_ENDPOINTS],
        dtype=np.float32,
    )


def classical_raw_edge(
    observations: Mapping[int, np.ndarray] | np.ndarray,
    contract: ClassicalEdgeContract,
) -> np.ndarray:
    """Return normalized raw edge commands in the R292 three-edge coordinates."""

    delta = edge_severity_delta(observations, contract)
    return np.tanh(np.float32(contract.gain) * delta).astype(np.float32)


class ClassicalEdgeController:
    """Deterministic controller adapter for the vector-evaluation interface."""

    def __init__(self, contract: ClassicalEdgeContract) -> None:
        self.contract = contract

    def reset(self) -> None:
        return None

    def select_edge_actions(
        self,
        observations: Mapping[int, np.ndarray] | np.ndarray,
        *,
        deterministic: bool = True,
    ) -> np.ndarray:
        if not deterministic:
            raise ValueError("classical edge controller is deterministic")
        return classical_raw_edge(observations, self.contract)


def compose_prior_residual_numpy(
    prior_raw: np.ndarray,
    actor_residual: np.ndarray,
    severity_delta: np.ndarray,
    *,
    residual_scale: float = 0.5,
) -> np.ndarray:
    """Change prior magnitude without allowing flow against severity gradient."""

    prior = np.asarray(prior_raw, dtype=np.float32).reshape(-1)
    residual = np.asarray(actor_residual, dtype=np.float32).reshape(-1)
    delta = np.asarray(severity_delta, dtype=np.float32).reshape(-1)
    if prior.shape != (3,) or residual.shape != (3,) or delta.shape != (3,):
        raise ValueError("prior, residual, and severity_delta must have shape (3,)")
    if not all(np.all(np.isfinite(value)) for value in (prior, residual, delta)):
        raise ValueError("prior, residual, and severity_delta must be finite")
    if not 0.0 < residual_scale <= 1.0:
        raise ValueError("residual_scale must lie in (0, 1]")
    magnitude = np.clip(
        np.abs(prior) + np.float32(residual_scale) * np.clip(residual, -1.0, 1.0),
        0.0,
        1.0,
    )
    return (np.sign(delta) * magnitude).astype(np.float32)
