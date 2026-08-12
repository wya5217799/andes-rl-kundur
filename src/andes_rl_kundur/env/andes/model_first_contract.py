"""Pure contracts for the model-first ANDES execution path.

This module deliberately has no ANDES import.  It owns the unit conversion,
coordinate, incidence, and descriptor-reduction seams that must be testable on
the Windows host before a live WSL canary is allowed to run.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

import numpy as np

ACTION_EDGES: Final[tuple[tuple[int, int], ...]] = ((0, 1), (1, 2), (2, 3))
STAGE1_PULSE_SYSTEM_PU: Final[float] = 0.05


def _finite_vector(values, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0:
        raise ValueError(f"{name} must be a non-empty vector")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be finite")
    return array


def device_to_system_base(
    values,
    *,
    device_mva: float,
    system_mva: float,
) -> np.ndarray:
    """Convert an ANDES ``power=True`` input from device to system base."""

    array = _finite_vector(values, name="values")
    if not np.isfinite(device_mva) or device_mva <= 0.0:
        raise ValueError("device_mva must be positive and finite")
    if not np.isfinite(system_mva) or system_mva <= 0.0:
        raise ValueError("system_mva must be positive and finite")
    return array * (float(device_mva) / float(system_mva))


def active_power_incidence(
    node_count: int = 4,
    edges: tuple[tuple[int, int], ...] = ACTION_EDGES,
) -> np.ndarray:
    """Return source-positive, target-negative edge-to-node incidence."""

    if node_count < 2:
        raise ValueError("node_count must be at least two")
    incidence = np.zeros((node_count, len(edges)), dtype=float)
    for column, (source, target) in enumerate(edges):
        if source == target:
            raise ValueError("self edges are not allowed")
        if not 0 <= source < node_count or not 0 <= target < node_count:
            raise ValueError(f"edge {(source, target)} is outside node range")
        incidence[source, column] = 1.0
        incidence[target, column] = -1.0
    return incidence


@dataclass(frozen=True)
class Stage1OperatingPoint:
    """One prospectively frozen Stage-1 development operating point."""

    name: str
    vsg_m_device: float
    vsg_d_device: float
    tie_rx_scale: float
    initial_soc: float

    @property
    def vsg_m_system(self) -> float:
        return self.vsg_m_device * 2.0

    @property
    def vsg_d_system(self) -> float:
        return self.vsg_d_device * 2.0


def stage1_operating_points() -> tuple[Stage1OperatingPoint, ...]:
    """Return the exact OP0--OP2 bank frozen by the manuscript contract."""

    return (
        Stage1OperatingPoint("OP0", 200.0, 100.0, 1.0, 0.50),
        Stage1OperatingPoint("OP1", 150.0, 75.0, 1.0, 0.30),
        Stage1OperatingPoint("OP2", 250.0, 125.0, 2.0, 0.70),
    )


def stage1_power_coordinates(
    pulse_amplitude_system_pu: float = STAGE1_PULSE_SYSTEM_PU,
) -> dict[str, np.ndarray]:
    """Return common and source-positive edge vectors at one pulse amplitude."""

    amplitude = float(pulse_amplitude_system_pu)
    if not np.isfinite(amplitude) or amplitude <= 0.0:
        raise ValueError("pulse amplitude must be positive and finite")
    incidence = active_power_incidence()
    coordinates = {"common": np.full(4, amplitude)}
    coordinates.update(
        {
            f"edge_{column}": amplitude * incidence[:, column]
            for column in range(incidence.shape[1])
        }
    )
    return coordinates


@dataclass(frozen=True)
class ModelFirstConfig:
    """Frozen plant choices for the separate model-first execution seam."""

    device_count: int = 4
    system_mva: float = 100.0
    vsg_device_mva: float = 200.0
    vsg_m_device: tuple[float, ...] = (200.0, 200.0, 200.0, 200.0)
    vsg_d_device: tuple[float, ...] = (100.0, 100.0, 100.0, 100.0)
    physical_nominal_frequency_hz: float = 60.0
    control_period_seconds: float = 0.2
    initialization_seconds: float = 0.5
    stage0_steps: int = 5
    tie_rx_scale: float = 1.0
    initial_soc: float = 0.5
    tds_convergence_tolerance: float | None = None
    tds_post_initialization_convergence_tolerance: float | None = None
    zero_g4_inertia: bool = False
    disable_default_toggler: bool = True
    random_disturbance: bool = False
    comm_fail_probability: float = 0.0

    def __post_init__(self) -> None:
        if self.device_count != 4:
            raise ValueError("the frozen model-first plant requires four devices")
        for name, values in (
            ("vsg_m_device", self.vsg_m_device),
            ("vsg_d_device", self.vsg_d_device),
        ):
            array = _finite_vector(values, name=name)
            if len(array) != self.device_count or np.any(array <= 0.0):
                raise ValueError(f"{name} must contain four positive values")
        if self.physical_nominal_frequency_hz != 60.0:
            raise ValueError("R306 freezes the physical nominal frequency at 60 Hz")
        if self.control_period_seconds != 0.2:
            raise ValueError("R306 freezes the controller period at 0.2 s")
        if self.initialization_seconds != 0.5 or self.stage0_steps != 5:
            raise ValueError("R306 freezes a 0.5 s initialization and five steps")
        if self.tie_rx_scale < 1.0 or not np.isfinite(self.tie_rx_scale):
            raise ValueError("tie_rx_scale must be finite and at least one")
        if not 0.2 < self.initial_soc < 0.8:
            raise ValueError("initial_soc must be strictly inside the ESD1 bounds")
        if self.tds_convergence_tolerance is not None and (
            not np.isfinite(self.tds_convergence_tolerance)
            or self.tds_convergence_tolerance <= 0.0
        ):
            raise ValueError(
                "tds_convergence_tolerance must be positive and finite"
            )
        if self.tds_post_initialization_convergence_tolerance is not None and (
            not np.isfinite(self.tds_post_initialization_convergence_tolerance)
            or self.tds_post_initialization_convergence_tolerance <= 0.0
        ):
            raise ValueError(
                "tds_post_initialization_convergence_tolerance must be "
                "positive and finite"
            )
        if (
            self.tds_convergence_tolerance is not None
            and self.tds_post_initialization_convergence_tolerance is not None
        ):
            raise ValueError(
                "tds_convergence_tolerance and "
                "tds_post_initialization_convergence_tolerance cannot both be set"
            )
        if self.zero_g4_inertia:
            raise ValueError("the model-first plant must retain original G4 inertia")
        if not self.disable_default_toggler:
            raise ValueError("the model-first plant must disable the default toggler")
        if self.random_disturbance or self.comm_fail_probability != 0.0:
            raise ValueError("R306 Stage-0 must be deterministic and disturbance-free")

    @classmethod
    def for_stage1_operating_point(
        cls,
        point: Stage1OperatingPoint,
    ) -> ModelFirstConfig:
        """Materialize the homogeneous plant settings for one Stage-1 point."""

        return cls(
            vsg_m_device=(point.vsg_m_device,) * 4,
            vsg_d_device=(point.vsg_d_device,) * 4,
            tie_rx_scale=point.tie_rx_scale,
            initial_soc=point.initial_soc,
        )

    @property
    def vsg_m_system(self) -> np.ndarray:
        return device_to_system_base(
            self.vsg_m_device,
            device_mva=self.vsg_device_mva,
            system_mva=self.system_mva,
        )

    @property
    def vsg_d_system(self) -> np.ndarray:
        return device_to_system_base(
            self.vsg_d_device,
            device_mva=self.vsg_device_mva,
            system_mva=self.system_mva,
        )

    @property
    def tds_tiny_correction_threshold(self) -> float | None:
        """Return ANDES' derived tiny-correction threshold when configured."""

        if self.tds_convergence_tolerance is None:
            return None
        return self.tds_convergence_tolerance / 1e6

    @property
    def tds_post_initialization_tiny_correction_threshold(self) -> float | None:
        """Return the derived tiny threshold for the post-init solver phase."""

        if self.tds_post_initialization_convergence_tolerance is None:
            return None
        return self.tds_post_initialization_convergence_tolerance / 1e6


@dataclass(frozen=True)
class WeightedCoordinateTransform:
    """Exact map ``xi = forward @ omega`` and its physical inverse."""

    inertia: np.ndarray
    q: np.ndarray
    forward: np.ndarray
    inverse: np.ndarray


def weighted_common_differential_transform(
    inertia,
) -> WeightedCoordinateTransform:
    """Build the frozen inertia-weighted common/differential coordinates."""

    matrix = np.asarray(inertia, dtype=float)
    if matrix.ndim == 1:
        diagonal = matrix.copy()
        matrix = np.diag(diagonal)
    elif matrix.ndim == 2 and matrix.shape[0] == matrix.shape[1]:
        diagonal = np.diag(matrix).copy()
        if not np.allclose(matrix, np.diag(diagonal), atol=1e-14):
            raise ValueError("inertia must be diagonal")
    else:
        raise ValueError("inertia must be a vector or square diagonal matrix")
    if diagonal.size < 2 or not np.all(np.isfinite(diagonal)):
        raise ValueError("inertia must contain at least two finite entries")
    if np.any(diagonal <= 0.0):
        raise ValueError("inertia must be strictly positive")

    sqrt_diagonal = np.sqrt(diagonal)
    sqrt_matrix = np.diag(sqrt_diagonal)
    inverse_sqrt_matrix = np.diag(1.0 / sqrt_diagonal)
    common = sqrt_diagonal / np.sqrt(float(np.sum(diagonal)))

    columns: list[np.ndarray] = [common]
    for basis_index in range(diagonal.size):
        candidate = np.eye(diagonal.size)[:, basis_index].copy()
        for column in columns:
            candidate -= float(column @ candidate) * column
        norm = float(np.linalg.norm(candidate))
        if norm > 1e-12:
            columns.append(candidate / norm)
        if len(columns) == diagonal.size:
            break
    if len(columns) != diagonal.size:
        raise RuntimeError("failed to construct a full differential complement")

    q = np.column_stack(columns)
    forward = q.T @ sqrt_matrix
    inverse = inverse_sqrt_matrix @ q
    return WeightedCoordinateTransform(
        inertia=matrix,
        q=q,
        forward=forward,
        inverse=inverse,
    )


@dataclass(frozen=True)
class TransformedLinearBlocks:
    transformed_state: np.ndarray
    transformed_input: np.ndarray
    a_cc: np.ndarray
    a_cd: np.ndarray
    a_dc: np.ndarray
    a_dd: np.ndarray
    b_cc: np.ndarray
    b_cd: np.ndarray
    b_dc: np.ndarray
    b_dd: np.ndarray
    reconstructed_state: np.ndarray
    reconstructed_input: np.ndarray


def transform_linear_blocks(
    state_matrix,
    input_matrix,
    *,
    state_forward,
    state_inverse,
    input_forward,
    input_inverse,
    common_dimension: int = 1,
) -> TransformedLinearBlocks:
    """Transform, partition, and reconstruct all linear blocks exactly."""

    a = np.asarray(state_matrix, dtype=float)
    b = np.asarray(input_matrix, dtype=float)
    tx = np.asarray(state_forward, dtype=float)
    tx_inv = np.asarray(state_inverse, dtype=float)
    tu = np.asarray(input_forward, dtype=float)
    tu_inv = np.asarray(input_inverse, dtype=float)
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise ValueError("state_matrix must be square")
    if b.ndim != 2 or b.shape[0] != a.shape[0]:
        raise ValueError("input_matrix row count must match state dimension")
    if tx.shape != a.shape or tx_inv.shape != a.shape:
        raise ValueError("state transforms must match state_matrix")
    if tu.shape[0] != tu.shape[1] or tu_inv.shape != tu.shape:
        raise ValueError("input transforms must be square and matched")
    if b.shape[1] != tu.shape[0]:
        raise ValueError("input transform must match input_matrix columns")
    if not 0 < common_dimension < a.shape[0]:
        raise ValueError("common_dimension must split the state coordinates")
    if common_dimension >= b.shape[1]:
        raise ValueError("common_dimension must split the input coordinates")

    transformed_a = tx @ a @ tx_inv
    transformed_b = tx @ b @ tu_inv
    split = common_dimension
    return TransformedLinearBlocks(
        transformed_state=transformed_a,
        transformed_input=transformed_b,
        a_cc=transformed_a[:split, :split],
        a_cd=transformed_a[:split, split:],
        a_dc=transformed_a[split:, :split],
        a_dd=transformed_a[split:, split:],
        b_cc=transformed_b[:split, :split],
        b_cd=transformed_b[:split, split:],
        b_dc=transformed_b[split:, :split],
        b_dd=transformed_b[split:, split:],
        reconstructed_state=tx_inv @ transformed_a @ tx,
        reconstructed_input=tx_inv @ transformed_b @ tu,
    )


@dataclass(frozen=True)
class DescriptorReduction:
    e_d: np.ndarray
    a: np.ndarray
    b_p: np.ndarray
    b_rho: np.ndarray


@dataclass(frozen=True)
class InputJacobians:
    f_input: np.ndarray
    g_input: np.ndarray
    midpoint_ratios: np.ndarray
    scheme: str
    step: float


def finite_difference_input_jacobians(
    residual: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]],
    *,
    equilibrium_input,
    step: float,
) -> InputJacobians:
    """Recover ``f_u`` and ``g_u`` from an executable residual callback.

    The callback must evaluate the DAE residual at fixed ``x`` and ``y``.  It
    is therefore an implementation seam, not a trajectory perturbation or a
    control-performance experiment.
    """

    centre = _finite_vector(equilibrium_input, name="equilibrium_input")
    if not np.isfinite(step) or step <= 0.0:
        raise ValueError("step must be positive and finite")
    base_f, base_g = residual(centre.copy())
    f0 = _finite_vector(base_f, name="f residual")
    g0 = _finite_vector(base_g, name="g residual")
    f_input = np.zeros((f0.size, centre.size), dtype=float)
    g_input = np.zeros((g0.size, centre.size), dtype=float)
    midpoint_ratios = np.zeros(centre.size, dtype=float)
    base = np.concatenate((f0, g0))
    for column in range(centre.size):
        positive = centre.copy()
        negative = centre.copy()
        positive[column] += step
        negative[column] -= step
        f_positive, g_positive = residual(positive)
        f_negative, g_negative = residual(negative)
        fp = _finite_vector(f_positive, name="positive f residual")
        fn = _finite_vector(f_negative, name="negative f residual")
        gp = _finite_vector(g_positive, name="positive g residual")
        gn = _finite_vector(g_negative, name="negative g residual")
        if fp.shape != f0.shape or fn.shape != f0.shape:
            raise ValueError("f residual shape changed during finite difference")
        if gp.shape != g0.shape or gn.shape != g0.shape:
            raise ValueError("g residual shape changed during finite difference")
        f_input[:, column] = (fp - fn) / (2.0 * step)
        g_input[:, column] = (gp - gn) / (2.0 * step)
        positive_residual = np.concatenate((fp, gp))
        negative_residual = np.concatenate((fn, gn))
        even = 0.5 * (positive_residual + negative_residual) - base
        odd = 0.5 * (positive_residual - negative_residual)
        midpoint_ratios[column] = np.linalg.norm(even) / max(
            np.linalg.norm(odd),
            1.0e-12,
        )
    return InputJacobians(
        f_input=f_input,
        g_input=g_input,
        midpoint_ratios=midpoint_ratios,
        scheme="central",
        step=float(step),
    )


def descriptor_schur_complement(
    *,
    e_d,
    f_x,
    f_y,
    g_x,
    g_y,
    f_p,
    g_p,
    f_rho,
    g_rho,
    e_d_rho,
    x_dot,
) -> DescriptorReduction:
    """Apply the frozen index-1 descriptor Schur-complement identities."""

    descriptor = np.asarray(e_d, dtype=float)
    fx = np.asarray(f_x, dtype=float)
    fy = np.asarray(f_y, dtype=float)
    gx = np.asarray(g_x, dtype=float)
    gy = np.asarray(g_y, dtype=float)
    fp = np.asarray(f_p, dtype=float)
    gp = np.asarray(g_p, dtype=float)
    frho = np.asarray(f_rho, dtype=float)
    grho = np.asarray(g_rho, dtype=float)
    descriptor_rho = np.asarray(e_d_rho, dtype=float)
    equilibrium_rate = np.asarray(x_dot, dtype=float)

    state_count = fx.shape[0]
    if fx.shape != (state_count, state_count):
        raise ValueError("f_x must be square")
    if descriptor.shape != fx.shape or descriptor_rho.shape != fx.shape:
        raise ValueError("descriptor matrices must match f_x")
    if fy.shape[0] != state_count or gx.shape[1] != state_count:
        raise ValueError("f_y/g_x state dimensions do not match f_x")
    if gy.shape != (gx.shape[0], fy.shape[1]):
        raise ValueError("g_y dimensions do not match f_y/g_x")
    if equilibrium_rate.shape != (state_count,):
        raise ValueError("x_dot must match the state dimension")
    if fp.shape[0] != state_count or gp.shape[0] != gy.shape[0]:
        raise ValueError("power-input Jacobian dimensions do not match")
    if frho.shape[0] != state_count or grho.shape[0] != gy.shape[0]:
        raise ValueError("parameter Jacobian dimensions do not match")
    if frho.shape[1] != 1:
        raise ValueError("this seam currently accepts one rho direction at a time")

    reduced_a = fx - fy @ np.linalg.solve(gy, gx)
    reduced_bp = fp - fy @ np.linalg.solve(gy, gp)
    reduced_brho = (
        frho
        - fy @ np.linalg.solve(gy, grho)
        - descriptor_rho @ equilibrium_rate[:, None]
    )
    return DescriptorReduction(
        e_d=descriptor.copy(),
        a=reduced_a,
        b_p=reduced_bp,
        b_rho=reduced_brho,
    )
