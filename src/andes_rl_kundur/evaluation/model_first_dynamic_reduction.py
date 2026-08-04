"""Offline dynamic-reduction primitives for the model-first research line.

These pure functions convert an already authorized finite rectangular-pulse
response into causal Markov parameters and apply the resulting FIR model to a
new input sequence.  They read no project artifact, run no simulator, and do
not turn development-data diagnostics into scientific evidence.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class StateSpaceRealization:
    """One discrete-time MIMO realization returned by ERA."""

    state_matrix: np.ndarray
    input_matrix: np.ndarray
    output_matrix: np.ndarray
    feedthrough_matrix: np.ndarray
    retained_singular_values: np.ndarray

    @property
    def spectral_radius(self) -> float:
        return float(np.max(np.abs(np.linalg.eigvals(self.state_matrix))))


def _finite_matrix(values: object, *, name: str) -> np.ndarray:
    matrix = np.asarray(values, dtype=float)
    if (
        matrix.ndim != 2
        or matrix.shape[0] < 1
        or matrix.shape[1] < 1
        or not np.all(np.isfinite(matrix))
    ):
        raise ValueError(f"{name} must be a non-empty finite matrix")
    return matrix


def recover_markov_parameters(
    pulse_response: object,
    *,
    pulse_width_steps: int,
    pulse_amplitude: float,
) -> np.ndarray:
    """Recover causal Markov parameters from one finite rectangular pulse.

    ``pulse_response[t]`` is the zero-baseline output increment produced by a
    constant input of ``pulse_amplitude`` for ``pulse_width_steps`` samples,
    followed by zero input.  The returned row ``k`` is the output response to
    one unit input at lag ``k``.
    """

    response = _finite_matrix(pulse_response, name="pulse_response")
    if (
        isinstance(pulse_width_steps, bool)
        or not isinstance(pulse_width_steps, int)
        or not 1 <= pulse_width_steps <= response.shape[0]
    ):
        raise ValueError("pulse_width_steps must be within the response horizon")
    amplitude = float(pulse_amplitude)
    if not np.isfinite(amplitude) or amplitude == 0.0:
        raise ValueError("pulse_amplitude must be finite and nonzero")

    markov = np.zeros_like(response)
    previous = np.zeros(response.shape[1], dtype=float)
    for step, output in enumerate(response):
        markov[step] = (output - previous) / amplitude
        if step >= pulse_width_steps:
            markov[step] += markov[step - pulse_width_steps]
        previous = output
    return markov


def simulate_fir_response(
    markov_parameters: object,
    input_sequence: Sequence[float] | np.ndarray,
) -> np.ndarray:
    """Apply a causal finite Markov sequence to one scalar input sequence."""

    markov = _finite_matrix(markov_parameters, name="markov_parameters")
    inputs = np.asarray(input_sequence, dtype=float)
    if inputs.ndim != 1 or inputs.size < 1 or not np.all(np.isfinite(inputs)):
        raise ValueError("input_sequence must be a non-empty finite vector")

    response = np.zeros((inputs.size, markov.shape[1]), dtype=float)
    for output_index in range(markov.shape[1]):
        response[:, output_index] = np.convolve(
            inputs,
            markov[:, output_index],
            mode="full",
        )[: inputs.size]
    return response


def simulate_mimo_fir_response(
    markov_parameters: object,
    input_sequence: object,
) -> np.ndarray:
    """Apply a causal time-by-output-by-input Markov tensor."""

    markov = np.asarray(markov_parameters, dtype=float)
    inputs = np.asarray(input_sequence, dtype=float)
    if markov.ndim != 3 or not np.all(np.isfinite(markov)):
        raise ValueError(
            "markov_parameters must be a finite time-by-output-by-input tensor"
        )
    if (
        inputs.ndim != 2
        or inputs.shape[0] < 1
        or inputs.shape[1] != markov.shape[2]
        or not np.all(np.isfinite(inputs))
    ):
        raise ValueError("input_sequence must be finite steps-by-inputs data")
    response = np.zeros((inputs.shape[0], markov.shape[1]), dtype=float)
    for input_index in range(markov.shape[2]):
        response += simulate_fir_response(
            markov[:, :, input_index], inputs[:, input_index]
        )
    return response


def fit_era_realization(
    markov_parameters: object,
    *,
    order: int,
    block_rows: int,
    block_columns: int,
) -> StateSpaceRealization:
    """Fit one reduced discrete-time realization by the eigensystem method."""

    markov = np.asarray(markov_parameters, dtype=float)
    if markov.ndim != 3 or not np.all(np.isfinite(markov)):
        raise ValueError("markov_parameters must be a finite time-by-output-by-input tensor")
    if markov.shape[0] <= block_rows + block_columns:
        raise ValueError("Markov horizon is too short for the requested block Hankel matrices")
    if block_rows < 1 or block_columns < 1:
        raise ValueError("block dimensions must be positive")
    maximum_order = min(block_rows * markov.shape[1], block_columns * markov.shape[2])
    if isinstance(order, bool) or not isinstance(order, int) or not 1 <= order <= maximum_order:
        raise ValueError("order is outside the block Hankel dimensions")

    hankel = np.block(
        [
            [markov[row + column + 1] for column in range(block_columns)]
            for row in range(block_rows)
        ]
    )
    shifted = np.block(
        [
            [markov[row + column + 2] for column in range(block_columns)]
            for row in range(block_rows)
        ]
    )
    left, singular_values, right_transpose = np.linalg.svd(
        hankel,
        full_matrices=False,
    )
    retained = singular_values[:order]
    if retained[-1] <= np.finfo(float).eps * retained[0]:
        raise ValueError("requested ERA order includes a numerically null direction")

    square_root = np.diag(np.sqrt(retained))
    inverse_square_root = np.diag(1.0 / np.sqrt(retained))
    observability = left[:, :order] @ square_root
    controllability = square_root @ right_transpose[:order, :]
    state_matrix = (
        inverse_square_root
        @ left[:, :order].T
        @ shifted
        @ right_transpose[:order, :].T
        @ inverse_square_root
    )
    input_count = markov.shape[2]
    output_count = markov.shape[1]
    return StateSpaceRealization(
        state_matrix=state_matrix,
        input_matrix=controllability[:, :input_count],
        output_matrix=observability[:output_count, :],
        feedthrough_matrix=markov[0].copy(),
        retained_singular_values=retained.copy(),
    )


def simulate_state_space(
    realization: StateSpaceRealization,
    input_sequence: object,
) -> np.ndarray:
    """Simulate one zero-state discrete-time MIMO realization."""

    inputs = np.asarray(input_sequence, dtype=float)
    if (
        inputs.ndim != 2
        or inputs.shape[0] < 1
        or inputs.shape[1] != realization.input_matrix.shape[1]
        or not np.all(np.isfinite(inputs))
    ):
        raise ValueError("input_sequence must be finite steps-by-inputs data")
    state = np.zeros(realization.state_matrix.shape[0], dtype=float)
    outputs = np.zeros(
        (inputs.shape[0], realization.output_matrix.shape[0]),
        dtype=float,
    )
    for step, control in enumerate(inputs):
        outputs[step] = (
            realization.output_matrix @ state
            + realization.feedthrough_matrix @ control
        )
        state = realization.state_matrix @ state + realization.input_matrix @ control
    return outputs


def enforce_spectral_radius(
    realization: StateSpaceRealization,
    *,
    maximum_radius: float,
) -> StateSpaceRealization:
    """Project only out-of-bound discrete poles onto a stable radius."""

    radius = float(maximum_radius)
    if not np.isfinite(radius) or not 0.0 < radius < 1.0:
        raise ValueError("maximum_radius must be finite and strictly between zero and one")
    eigenvalues, eigenvectors = np.linalg.eig(realization.state_matrix)
    if np.linalg.cond(eigenvectors) > 1.0e12:
        raise ValueError("state eigenvectors are too ill-conditioned for pole projection")
    projected = eigenvalues.copy()
    magnitudes = np.abs(projected)
    outside = magnitudes > radius
    projected[outside] *= radius / magnitudes[outside]
    state_matrix = eigenvectors @ np.diag(projected) @ np.linalg.inv(eigenvectors)
    state_matrix = np.real_if_close(state_matrix, tol=1000)
    if np.iscomplexobj(state_matrix):
        raise ValueError("pole projection did not preserve a real state matrix")
    return StateSpaceRealization(
        state_matrix=np.asarray(state_matrix, dtype=float),
        input_matrix=realization.input_matrix.copy(),
        output_matrix=realization.output_matrix.copy(),
        feedthrough_matrix=realization.feedthrough_matrix.copy(),
        retained_singular_values=realization.retained_singular_values.copy(),
    )


def realization_to_dict(realization: StateSpaceRealization) -> dict[str, object]:
    """Return one JSON-serializable representation with explicit matrices."""

    return {
        "state_matrix": np.asarray(realization.state_matrix, dtype=float).tolist(),
        "input_matrix": np.asarray(realization.input_matrix, dtype=float).tolist(),
        "output_matrix": np.asarray(realization.output_matrix, dtype=float).tolist(),
        "feedthrough_matrix": np.asarray(
            realization.feedthrough_matrix, dtype=float
        ).tolist(),
        "retained_singular_values": np.asarray(
            realization.retained_singular_values, dtype=float
        ).tolist(),
        "spectral_radius": realization.spectral_radius,
    }


def realization_from_dict(payload: object) -> StateSpaceRealization:
    """Restore and validate a realization produced by :func:`realization_to_dict`."""

    if not isinstance(payload, dict):
        raise ValueError("realization payload must be an object")
    try:
        state = _finite_matrix(payload["state_matrix"], name="state_matrix")
        inputs = _finite_matrix(payload["input_matrix"], name="input_matrix")
        outputs = _finite_matrix(payload["output_matrix"], name="output_matrix")
        feedthrough = _finite_matrix(
            payload["feedthrough_matrix"], name="feedthrough_matrix"
        )
        singular_values = np.asarray(
            payload["retained_singular_values"], dtype=float
        )
    except KeyError as exc:
        raise ValueError(f"realization payload is missing {exc.args[0]}") from exc
    order = state.shape[0]
    if (
        state.shape != (order, order)
        or inputs.shape[0] != order
        or outputs.shape[1] != order
        or feedthrough.shape != (outputs.shape[0], inputs.shape[1])
        or singular_values.shape != (order,)
        or not np.all(np.isfinite(singular_values))
        or np.any(singular_values <= 0.0)
    ):
        raise ValueError("realization matrix dimensions are inconsistent")
    realization = StateSpaceRealization(
        state_matrix=state,
        input_matrix=inputs,
        output_matrix=outputs,
        feedthrough_matrix=feedthrough,
        retained_singular_values=singular_values,
    )
    if "spectral_radius" in payload and not np.isclose(
        realization.spectral_radius,
        float(payload["spectral_radius"]),
        rtol=1e-12,
        atol=1e-12,
    ):
        raise ValueError("serialized spectral radius does not match the state matrix")
    return realization
