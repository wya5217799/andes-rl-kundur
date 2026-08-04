"""Constraint-aware differential edge allocation for local BESS commands.

The module keeps a projected common-power baseline fixed, then allocates
antisymmetric neighbour-edge flows inside per-device power intervals.  Every
accepted edge flow adds power at one endpoint and removes the same amount at
the other, so the executed residual remains zero sum by construction.

``project_residual_to_zero_sum_box`` supplies a centralized deterministic
reference for the same action box.  It is an oracle comparator, not a claim
that the local two-endpoint schedule solves the global optimum.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from andes_rl_kundur.control.edge_relative_rocof_residual import (
    Edge,
    canonical_edge,
)


@dataclass(frozen=True)
class HeadroomAwareEdgeAllocation:
    """Executed power and edge flows from one frozen neighbour schedule."""

    commanded_power_system_pu: np.ndarray
    residual_power_system_pu: np.ndarray
    requested_edge_flows_system_pu: dict[Edge, float]
    allocated_edge_flows_system_pu: dict[Edge, float]


def _finite_vector(values: Sequence[float], *, name: str) -> np.ndarray:
    vector = np.asarray(values, dtype=float)
    if vector.ndim != 1 or vector.size < 2 or not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must be a finite one-dimensional device vector")
    return vector


def allocate_edge_flows_with_headroom(
    *,
    base_power_system_pu: Sequence[float],
    requested_edge_flows_system_pu: Mapping[Edge, float],
    edge_phases: Sequence[Sequence[Edge]],
    lower_power_system_pu: Sequence[float],
    upper_power_system_pu: Sequence[float],
    tolerance: float = 1e-12,
) -> HeadroomAwareEdgeAllocation:
    """Clip antisymmetric edge flows using only current endpoint headroom.

    Edges in one phase must be node-disjoint and may therefore negotiate in
    parallel.  Later phases see the endpoint power committed by earlier phases.
    The shared phase schedule is fixed offline; runtime constraint data never
    leave an edge's two endpoints.
    """

    base = _finite_vector(base_power_system_pu, name="base power")
    lower = _finite_vector(lower_power_system_pu, name="lower power")
    upper = _finite_vector(upper_power_system_pu, name="upper power")
    if lower.shape != base.shape or upper.shape != base.shape:
        raise ValueError("power vectors must have the same device count")
    if np.any(lower > upper + tolerance):
        raise ValueError("lower power exceeds upper power")
    if np.any(base < lower - tolerance) or np.any(base > upper + tolerance):
        raise ValueError("base power lies outside the feasible power box")

    requested: dict[Edge, float] = {}
    for raw_edge, raw_flow in requested_edge_flows_system_pu.items():
        edge = canonical_edge(*raw_edge)
        if edge != tuple(raw_edge):
            raise ValueError("edge-flow coordinates must use canonical orientation")
        flow = float(raw_flow)
        if edge[1] >= base.size or not math.isfinite(flow):
            raise ValueError("edge flow has an invalid endpoint or value")
        if edge in requested:
            raise ValueError("duplicate requested edge")
        requested[edge] = flow

    scheduled: list[Edge] = []
    normalized_phases: list[tuple[Edge, ...]] = []
    for phase in edge_phases:
        normalized: list[Edge] = []
        endpoints: set[int] = set()
        for raw_edge in phase:
            edge = canonical_edge(*raw_edge)
            if edge != tuple(raw_edge) or edge not in requested:
                raise ValueError("edge schedule must use every requested canonical edge")
            if edge[0] in endpoints or edge[1] in endpoints:
                raise ValueError("edges within one phase must be node-disjoint")
            endpoints.update(edge)
            normalized.append(edge)
            scheduled.append(edge)
        normalized_phases.append(tuple(normalized))
    if len(scheduled) != len(set(scheduled)) or set(scheduled) != set(requested):
        raise ValueError("edge schedule must contain every requested edge exactly once")

    command = base.copy()
    allocated: dict[Edge, float] = {}
    for phase in normalized_phases:
        phase_updates: list[tuple[Edge, float]] = []
        for source, target in phase:
            positive_capacity = max(
                0.0,
                min(
                    float(upper[source] - command[source]),
                    float(command[target] - lower[target]),
                ),
            )
            negative_capacity = max(
                0.0,
                min(
                    float(command[source] - lower[source]),
                    float(upper[target] - command[target]),
                ),
            )
            edge = (source, target)
            flow = float(
                np.clip(requested[edge], -negative_capacity, positive_capacity)
            )
            phase_updates.append((edge, flow))
        for (source, target), flow in phase_updates:
            command[source] += flow
            command[target] -= flow
            allocated[(source, target)] = flow

    residual = command - base
    if abs(float(np.sum(residual))) > tolerance:
        raise RuntimeError("allocated edge residual violated zero sum")
    if np.any(command < lower - tolerance) or np.any(command > upper + tolerance):
        raise RuntimeError("allocated command violated the feasible power box")
    return HeadroomAwareEdgeAllocation(
        commanded_power_system_pu=command,
        residual_power_system_pu=residual,
        requested_edge_flows_system_pu=requested,
        allocated_edge_flows_system_pu=allocated,
    )


def project_residual_to_zero_sum_box(
    *,
    target_residual_system_pu: Sequence[float],
    lower_residual_system_pu: Sequence[float],
    upper_residual_system_pu: Sequence[float],
    tolerance: float = 1e-12,
) -> np.ndarray:
    """Return the Euclidean projection onto a box intersected with ``sum=0``."""

    target = _finite_vector(target_residual_system_pu, name="target residual")
    lower = _finite_vector(lower_residual_system_pu, name="lower residual")
    upper = _finite_vector(upper_residual_system_pu, name="upper residual")
    if lower.shape != target.shape or upper.shape != target.shape:
        raise ValueError("residual vectors must have the same device count")
    if np.any(lower > upper + tolerance):
        raise ValueError("lower residual exceeds upper residual")
    if float(np.sum(lower)) > tolerance or float(np.sum(upper)) < -tolerance:
        raise ValueError("residual box contains no zero-sum point")

    lambda_low = float(np.min(target - upper))
    lambda_high = float(np.max(target - lower))
    projected = np.clip(target, lower, upper)
    for _ in range(200):
        multiplier = 0.5 * (lambda_low + lambda_high)
        projected = np.clip(target - multiplier, lower, upper)
        total = float(np.sum(projected))
        if abs(total) <= tolerance:
            break
        if total > 0.0:
            lambda_low = multiplier
        else:
            lambda_high = multiplier

    imbalance = float(np.sum(projected))
    if abs(imbalance) > tolerance:
        direction = -1.0 if imbalance > 0.0 else 1.0
        remaining = abs(imbalance)
        for index in range(projected.size):
            capacity = (
                projected[index] - lower[index]
                if direction < 0.0
                else upper[index] - projected[index]
            )
            adjustment = min(float(capacity), remaining)
            projected[index] += direction * adjustment
            remaining -= adjustment
            if remaining <= tolerance:
                break
    if abs(float(np.sum(projected))) > tolerance:
        raise RuntimeError("zero-sum box projection did not converge")
    return projected
