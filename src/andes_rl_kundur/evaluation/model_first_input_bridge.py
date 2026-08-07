"""Pure descriptor and sampled-data seams for the physical input bridge.

The functions in this module do not import ANDES or read project artifacts.
They make the two easy-to-hide modeling choices explicit: zero-time-constant
states are algebraic equations, and the R336 trace convention observes the
plant after each held input interval.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import cont2discrete

from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    StateSpaceRealization,
    fit_era_realization,
)


def _matrix(values: object, *, name: str) -> np.ndarray:
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2 or not np.all(np.isfinite(matrix)):
        raise ValueError(f"{name} must be a finite matrix")
    return matrix


def _positive_scales(values: object, *, name: str, size: int) -> np.ndarray:
    scales = np.asarray(values, dtype=float)
    if (
        scales.shape != (size,)
        or not np.all(np.isfinite(scales))
        or np.any(scales <= 0.0)
    ):
        raise ValueError(f"{name} must contain one positive scale per channel")
    return scales


@dataclass(frozen=True)
class FoldedDescriptor:
    """Descriptor blocks after zero-``Tf`` states become algebraic."""

    e_d: np.ndarray
    f_x: np.ndarray
    f_algebraic: np.ndarray
    g_x: np.ndarray
    g_algebraic: np.ndarray
    f_input: np.ndarray
    g_input: np.ndarray
    dynamic_state_indices: np.ndarray
    folded_state_indices: np.ndarray


@dataclass(frozen=True)
class ReducedInputModel:
    """Continuous input model after an index-1 Schur reduction."""

    state_matrix: np.ndarray
    input_matrix: np.ndarray
    algebraic_reciprocal_condition: float


@dataclass(frozen=True)
class SampledInputModel:
    """Discrete realization using end-of-hold output observations."""

    state_matrix: np.ndarray
    input_matrix: np.ndarray
    output_matrix: np.ndarray
    feedthrough_matrix: np.ndarray

    @property
    def spectral_radius(self) -> float:
        return float(np.max(np.abs(np.linalg.eigvals(self.state_matrix))))


def fold_zero_time_constant_states(
    *,
    time_constants: object,
    f_x: object,
    f_y: object,
    g_x: object,
    g_y: object,
    f_input: object,
    g_input: object,
) -> FoldedDescriptor:
    """Move exact zero-time-constant state equations into the DAE algebraic block.

    The augmented algebraic variable order is ``[original y, zero-Tf x]`` and
    the augmented algebraic equation order is ``[original g, zero-Tf f]``.
    No pseudoinverse, dead-row removal, or state-constraint deletion occurs in
    this pure seam; a live adapter must reconcile those cases by name against
    the installed simulator before calling the Schur reduction.
    """

    tf = np.asarray(time_constants, dtype=float)
    fx = _matrix(f_x, name="f_x")
    fy = _matrix(f_y, name="f_y")
    gx = _matrix(g_x, name="g_x")
    gy = _matrix(g_y, name="g_y")
    fu = _matrix(f_input, name="f_input")
    gu = _matrix(g_input, name="g_input")
    if tf.ndim != 1 or not np.all(np.isfinite(tf)):
        raise ValueError("time_constants must be a finite vector")
    state_count = tf.size
    algebraic_count = gy.shape[0]
    input_count = fu.shape[1]
    if (
        fx.shape != (state_count, state_count)
        or fy.shape != (state_count, algebraic_count)
        or gx.shape != (algebraic_count, state_count)
        or gy.shape != (algebraic_count, algebraic_count)
        or fu.shape != (state_count, input_count)
        or gu.shape != (algebraic_count, input_count)
    ):
        raise ValueError("descriptor and input Jacobian dimensions are inconsistent")

    folded_indices = np.flatnonzero(tf == 0.0)
    dynamic_indices = np.flatnonzero(tf != 0.0)
    if dynamic_indices.size == 0:
        raise ValueError("descriptor contains no nonzero-time-constant states")

    f_dynamic_x = fx[np.ix_(dynamic_indices, dynamic_indices)]
    f_dynamic_algebraic = np.hstack(
        [
            fy[dynamic_indices, :],
            fx[np.ix_(dynamic_indices, folded_indices)],
        ]
    )
    g_dynamic_x = np.vstack(
        [
            gx[:, dynamic_indices],
            fx[np.ix_(folded_indices, dynamic_indices)],
        ]
    )
    g_algebraic = np.block(
        [
            [gy, gx[:, folded_indices]],
            [fy[folded_indices, :], fx[np.ix_(folded_indices, folded_indices)]],
        ]
    )
    return FoldedDescriptor(
        e_d=np.diag(tf[dynamic_indices]),
        f_x=f_dynamic_x,
        f_algebraic=f_dynamic_algebraic,
        g_x=g_dynamic_x,
        g_algebraic=g_algebraic,
        f_input=fu[dynamic_indices, :],
        g_input=np.vstack([gu, fu[folded_indices, :]]),
        dynamic_state_indices=dynamic_indices,
        folded_state_indices=folded_indices,
    )


def reduce_folded_descriptor(
    descriptor: FoldedDescriptor,
    *,
    minimum_reciprocal_condition: float,
) -> ReducedInputModel:
    """Apply an index-1 Schur complement without a pseudoinverse."""

    minimum = float(minimum_reciprocal_condition)
    if not np.isfinite(minimum) or not 0.0 < minimum < 1.0:
        raise ValueError("minimum_reciprocal_condition must lie between zero and one")
    condition = float(np.linalg.cond(descriptor.g_algebraic, p=2))
    reciprocal = 0.0 if not np.isfinite(condition) else 1.0 / condition
    if reciprocal < minimum:
        raise np.linalg.LinAlgError(
            "augmented algebraic block is too ill-conditioned for Schur reduction"
        )
    eliminated_x = np.linalg.solve(descriptor.g_algebraic, descriptor.g_x)
    eliminated_input = np.linalg.solve(
        descriptor.g_algebraic, descriptor.g_input
    )
    state_rhs = descriptor.f_x - descriptor.f_algebraic @ eliminated_x
    input_rhs = descriptor.f_input - descriptor.f_algebraic @ eliminated_input
    return ReducedInputModel(
        state_matrix=np.linalg.solve(descriptor.e_d, state_rhs),
        input_matrix=np.linalg.solve(descriptor.e_d, input_rhs),
        algebraic_reciprocal_condition=reciprocal,
    )


def post_step_sampled_realization(
    *,
    state_matrix: object,
    input_matrix: object,
    output_matrix: object,
    feedthrough_matrix: object,
    sample_period_seconds: float,
) -> SampledInputModel:
    """Discretize a continuous model for observations at the end of each hold.

    ``scipy.signal.cont2discrete`` returns the usual pre-step output matrices.
    R336 instead associates ``u[k]`` with the response observed after the
    interval. For that convention, ``C_post = C Ad`` and
    ``D_post = C Bd + D``.
    """

    a = _matrix(state_matrix, name="state_matrix")
    b = _matrix(input_matrix, name="input_matrix")
    c = _matrix(output_matrix, name="output_matrix")
    d = _matrix(feedthrough_matrix, name="feedthrough_matrix")
    period = float(sample_period_seconds)
    if a.shape[0] != a.shape[1]:
        raise ValueError("state_matrix must be square")
    if (
        b.shape[0] != a.shape[0]
        or c.shape[1] != a.shape[0]
        or d.shape != (c.shape[0], b.shape[1])
    ):
        raise ValueError("continuous model dimensions are inconsistent")
    if not np.isfinite(period) or period <= 0.0:
        raise ValueError("sample_period_seconds must be positive and finite")

    ad, bd, cd, dd, _ = cont2discrete((a, b, c, d), period, method="zoh")
    return SampledInputModel(
        state_matrix=np.asarray(ad, dtype=float),
        input_matrix=np.asarray(bd, dtype=float),
        output_matrix=np.asarray(cd @ ad, dtype=float),
        feedthrough_matrix=np.asarray(cd @ bd + dd, dtype=float),
    )


def fit_normalized_era_realization(
    markov_parameters: object,
    *,
    input_scales: object,
    output_scales: object,
    order: int,
    block_rows: int,
    block_columns: int,
) -> StateSpaceRealization:
    """Fit ERA in declared normalized coordinates and return physical units.

    ``input_scales[j]`` is physical input per unit normalized input and
    ``output_scales[i]`` is physical output per unit normalized output. The
    returned realization accepts and emits the original physical coordinates.
    """

    markov = np.asarray(markov_parameters, dtype=float)
    if markov.ndim != 3 or not np.all(np.isfinite(markov)):
        raise ValueError(
            "markov_parameters must be a finite time-by-output-by-input tensor"
        )
    input_scale = _positive_scales(
        input_scales, name="input_scales", size=markov.shape[2]
    )
    output_scale = _positive_scales(
        output_scales, name="output_scales", size=markov.shape[1]
    )
    normalized = (
        markov
        * input_scale[np.newaxis, np.newaxis, :]
        / output_scale[np.newaxis, :, np.newaxis]
    )
    fitted = fit_era_realization(
        normalized,
        order=order,
        block_rows=block_rows,
        block_columns=block_columns,
    )
    inverse_input_scale = np.diag(1.0 / input_scale)
    output_scale_matrix = np.diag(output_scale)
    return StateSpaceRealization(
        state_matrix=fitted.state_matrix.copy(),
        input_matrix=fitted.input_matrix @ inverse_input_scale,
        output_matrix=output_scale_matrix @ fitted.output_matrix,
        feedthrough_matrix=(
            output_scale_matrix
            @ fitted.feedthrough_matrix
            @ inverse_input_scale
        ),
        retained_singular_values=fitted.retained_singular_values.copy(),
    )
