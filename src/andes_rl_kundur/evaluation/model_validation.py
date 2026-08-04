"""Pure R294 model-validation calculations.

The functions in this module do not import ANDES.  They compare frozen state
matrices, identify the registered inter-area branch, and quantify the response
coupling exposed by common/differential VSG-frequency coordinates.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
from scipy.linalg import eig
from scipy.sparse.linalg import expm_multiply


def helmert_coordinates(device_count: int = 4) -> np.ndarray:
    """Return an orthonormal common-plus-differential coordinate matrix."""

    if device_count < 2:
        raise ValueError("device_count must be at least two")
    transform = np.zeros((device_count, device_count), dtype=float)
    transform[0, :] = 1.0 / np.sqrt(device_count)
    for row in range(1, device_count):
        scale = np.sqrt(row * (row + 1.0))
        transform[row, :row] = 1.0 / scale
        transform[row, row] = -row / scale
    return transform


def multilinear_weights(
    point: Mapping[str, float],
    bounds: Mapping[str, Sequence[float]],
    axis_order: Sequence[str],
) -> dict[tuple[float, ...], float]:
    """Return corner weights for a point inside a rectangular LPV domain."""

    weights: dict[tuple[float, ...], float] = {(): 1.0}
    tolerance = 1e-12
    for axis in axis_order:
        low, high = (float(value) for value in bounds[axis])
        value = float(point[axis])
        if not low < high:
            raise ValueError(f"invalid bounds for {axis}: {(low, high)}")
        if value < low - tolerance or value > high + tolerance:
            raise ValueError(f"{axis}={value} outside {(low, high)}")
        alpha = min(1.0, max(0.0, (value - low) / (high - low)))
        expanded: dict[tuple[float, ...], float] = {}
        for prefix, weight in weights.items():
            expanded[(*prefix, low)] = weight * (1.0 - alpha)
            expanded[(*prefix, high)] = weight * alpha
        weights = expanded
    return weights


def multilinear_interpolate(
    corner_matrices: Mapping[tuple[float, ...], np.ndarray],
    point: Mapping[str, float],
    bounds: Mapping[str, Sequence[float]],
    axis_order: Sequence[str],
) -> np.ndarray:
    """Interpolate a state matrix from all rectangular-domain corners."""

    weights = multilinear_weights(point, bounds, axis_order)
    missing = sorted(set(weights) - set(corner_matrices))
    if missing:
        raise KeyError(f"missing interpolation corners: {missing}")
    shapes = {np.asarray(corner_matrices[key]).shape for key in weights}
    if len(shapes) != 1:
        raise ValueError(f"corner matrix shapes differ: {sorted(shapes)}")
    result = np.zeros(next(iter(shapes)), dtype=float)
    for key, weight in weights.items():
        result += weight * np.asarray(corner_matrices[key], dtype=float)
    return result


def participation_mode(
    state_matrix: np.ndarray,
    machine_state_indices: Mapping[str, int],
    area_1_keys: Sequence[str],
    area_2_keys: Sequence[str],
    *,
    frequency_band_hz: tuple[float, float] = (0.2, 1.5),
) -> dict[str, object] | None:
    """Identify the inter-area mode by normalized state participation.

    Only the positive-imaginary member of each conjugate pair is considered.
    The participation definition is ``|v_ij w_ji|`` with rows of ``W=V^-1``.
    """

    matrix = np.asarray(state_matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("state_matrix must be square")
    eigenvalues, left, right = eig(matrix, left=True, right=True)
    keys = list(machine_state_indices)
    candidates: list[dict[str, object]] = []
    for mode_index, eigenvalue in enumerate(eigenvalues):
        if eigenvalue.imag <= 0.0:
            continue
        frequency_hz = float(eigenvalue.imag / (2.0 * np.pi))
        if not frequency_band_hz[0] <= frequency_hz <= frequency_band_hz[1]:
            continue
        biorthogonal_product = np.vdot(left[:, mode_index], right[:, mode_index])
        condition_number = float(
            np.linalg.norm(left[:, mode_index])
            * np.linalg.norm(right[:, mode_index])
            / max(abs(biorthogonal_product), 1e-30)
        )
        raw = np.abs(
            right[:, mode_index] * np.conjugate(left[:, mode_index])
        )
        total = float(np.sum(raw))
        if not np.isfinite(total) or total <= 0.0:
            continue
        normalized = raw / total
        machine = {
            key: float(normalized[int(machine_state_indices[key])]) for key in keys
        }
        contrast = abs(
            sum(machine[key] for key in area_1_keys)
            - sum(machine[key] for key in area_2_keys)
        )
        candidates.append(
            {
                "eigenvalue_real": float(eigenvalue.real),
                "eigenvalue_imag": float(eigenvalue.imag),
                "frequency_hz": frequency_hz,
                "damping_ratio": float(-eigenvalue.real / abs(eigenvalue)),
                "area_contrast": float(contrast),
                "participation_keys": keys,
                "participation_vector": [machine[key] for key in keys],
                "eigenvector_condition_number": condition_number,
            }
        )
    if not candidates:
        return None
    return max(candidates, key=lambda item: float(item["area_contrast"]))


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Return cosine similarity with a zero-vector guard."""

    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denominator <= 1e-30:
        return 0.0
    return float(np.dot(a, b) / denominator)


def compare_modes(
    truth: dict[str, object] | None,
    prediction: dict[str, object] | None,
) -> dict[str, float | bool | str | None]:
    """Compare frequency, damping, and participation for one mode branch."""

    if truth is None or prediction is None:
        return {
            "branch_present": False,
            "frequency_relative_error": None,
            "damping_absolute_error": None,
            "participation_cosine": None,
            "reason": "truth_or_prediction_branch_missing",
        }
    truth_frequency = float(truth["frequency_hz"])
    prediction_frequency = float(prediction["frequency_hz"])
    return {
        "branch_present": True,
        "frequency_relative_error": abs(prediction_frequency - truth_frequency)
        / max(abs(truth_frequency), 1e-12),
        "damping_absolute_error": abs(
            float(prediction["damping_ratio"]) - float(truth["damping_ratio"])
        ),
        "participation_cosine": cosine_similarity(
            truth["participation_vector"], prediction["participation_vector"]
        ),
        "reason": None,
    }


def coordinate_response(
    state_matrix: np.ndarray,
    vsg_omega_indices: Sequence[int],
    *,
    horizon_seconds: float = 10.0,
    sample_count: int = 201,
) -> np.ndarray:
    """Return common/differential outputs to coordinate initial conditions."""

    matrix = np.asarray(state_matrix, dtype=float)
    indices = [int(value) for value in vsg_omega_indices]
    transform = helmert_coordinates(len(indices))
    physical_input = np.zeros((matrix.shape[0], len(indices)), dtype=float)
    physical_output = np.zeros((len(indices), matrix.shape[0]), dtype=float)
    for column, state_index in enumerate(indices):
        physical_input[state_index, column] = 1.0
        physical_output[column, state_index] = 1.0
    coordinate_input = physical_input @ transform.T
    coordinate_output = transform @ physical_output
    state_response = expm_multiply(
        matrix,
        coordinate_input,
        start=0.0,
        stop=float(horizon_seconds),
        num=int(sample_count),
        endpoint=True,
    )
    return np.einsum("ij,tjk->tik", coordinate_output, state_response)


def coupling_ratios(response: np.ndarray) -> dict[str, float]:
    """Return amplitude cross/self ratios in both coordinate directions."""

    values = np.asarray(response, dtype=float)
    if values.ndim != 3 or values.shape[1] != values.shape[2]:
        raise ValueError("response must have shape (time, coordinates, inputs)")
    if values.shape[1] < 2:
        raise ValueError("response needs common and differential coordinates")
    dynamic = values[1:, :, :]
    common_self = float(np.linalg.norm(dynamic[:, 0, 0]))
    common_to_diff = float(np.linalg.norm(dynamic[:, 1:, 0]))
    differential_self = float(np.linalg.norm(dynamic[:, 1:, 1:]))
    differential_to_common = float(np.linalg.norm(dynamic[:, 0, 1:]))
    if common_self <= 1e-30 or differential_self <= 1e-30:
        raise ValueError("zero self-response prevents coupling normalization")
    return {
        "differential_from_common": common_to_diff / common_self,
        "common_from_differential": differential_to_common / differential_self,
    }


def compare_coordinate_responses(
    truth: np.ndarray, prediction: np.ndarray
) -> dict[str, object]:
    """Compare full coordinate response and its two cross-coupling ratios."""

    truth_values = np.asarray(truth, dtype=float)
    prediction_values = np.asarray(prediction, dtype=float)
    if truth_values.shape != prediction_values.shape:
        raise ValueError("truth and prediction response shapes differ")
    truth_norm = float(np.linalg.norm(truth_values))
    nrmse = float(np.linalg.norm(prediction_values - truth_values)) / max(
        truth_norm, 1e-30
    )
    truth_coupling = coupling_ratios(truth_values)
    prediction_coupling = coupling_ratios(prediction_values)
    coupling_error = {
        key: abs(prediction_coupling[key] - truth_coupling[key])
        for key in truth_coupling
    }
    return {
        "response_nrmse": nrmse,
        "truth_coupling": truth_coupling,
        "prediction_coupling": prediction_coupling,
        "coupling_absolute_error": coupling_error,
    }


def model_point_passes(
    mode: Mapping[str, object],
    response: Mapping[str, object],
    thresholds: Mapping[str, float],
) -> bool:
    """Apply the prospectively frozen Stage-A pointwise fidelity gate."""

    if mode.get("branch_present") is not True:
        return False
    coupling_errors = response["coupling_absolute_error"]
    return bool(
        float(mode["frequency_relative_error"])
        <= thresholds["mode_frequency_relative_error_max"]
        and float(mode["damping_absolute_error"])
        <= thresholds["mode_damping_absolute_error_max"]
        and float(mode["participation_cosine"])
        >= thresholds["participation_cosine_min"]
        and float(response["response_nrmse"])
        <= thresholds["coordinate_response_nrmse_max"]
        and max(float(value) for value in coupling_errors.values())
        <= thresholds["coupling_ratio_absolute_error_max"]
    )
