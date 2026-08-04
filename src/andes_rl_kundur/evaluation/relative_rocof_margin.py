"""Small-signal diagnostics for the sampled relative-RoCoF graph residual.

The implemented controller is a sampled, filtered derivative feedback on a
row-normalized communication Laplacian.  This module makes three boundaries
explicit:

* ``L @ 1 == 0`` is a controller-interface common-mode property, not plant
  decoupling;
* the exact digital differentiator/filter can be audited without ANDES; and
* an augmented equilibrium matrix is a local diagnostic, not a nonlinear or
  robust stability certificate.

All functions are pure and read no repository state.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import cmath
import math

import numpy as np
from scipy.linalg import eig, expm

from andes_rl_kundur.control.coupling_aware_power import (
    row_normalized_laplacian,
)


def sampled_rocof_transfer(
    frequency_hz: float,
    *,
    sample_period_s: float,
    filter_time_constant_s: float,
) -> complex:
    """Return the exact implemented transfer from frequency to filtered RoCoF.

    The implementation is
    ``r[k] = alpha*r[k-1] + (1-alpha)*(f[k]-f[k-1])/T`` with
    ``alpha = exp(-T/tau)``.
    """

    frequency = float(frequency_hz)
    sample_period = float(sample_period_s)
    time_constant = float(filter_time_constant_s)
    if frequency < 0.0 or not math.isfinite(frequency):
        raise ValueError("frequency_hz must be finite and non-negative")
    if sample_period <= 0.0 or not math.isfinite(sample_period):
        raise ValueError("sample_period_s must be finite and positive")
    if time_constant <= 0.0 or not math.isfinite(time_constant):
        raise ValueError("filter_time_constant_s must be finite and positive")
    alpha = math.exp(-sample_period / time_constant)
    z_inverse = cmath.exp(-1j * 2.0 * math.pi * frequency * sample_period)
    return (1.0 - alpha) * (1.0 - z_inverse) / (
        sample_period * (1.0 - alpha * z_inverse)
    )


def continuous_rocof_transfer(
    frequency_hz: float,
    *,
    filter_time_constant_s: float,
) -> complex:
    """Return ``s/(tau*s+1)`` at one frequency."""

    frequency = float(frequency_hz)
    time_constant = float(filter_time_constant_s)
    if frequency < 0.0 or not math.isfinite(frequency):
        raise ValueError("frequency_hz must be finite and non-negative")
    if time_constant <= 0.0 or not math.isfinite(time_constant):
        raise ValueError("filter_time_constant_s must be finite and positive")
    omega = 2.0 * math.pi * frequency
    return 1j * omega / (1.0 + 1j * omega * time_constant)


def held_path_transfer(
    frequency_hz: float,
    *,
    sample_period_s: float,
    filter_time_constant_s: float,
    actuator_time_constant_s: float,
) -> complex:
    """Return filter times ZOH times one first-order active-current lag."""

    frequency = float(frequency_hz)
    sample_period = float(sample_period_s)
    actuator_time_constant = float(actuator_time_constant_s)
    if actuator_time_constant <= 0.0 or not math.isfinite(actuator_time_constant):
        raise ValueError("actuator_time_constant_s must be finite and positive")
    omega = 2.0 * math.pi * frequency
    omega_sample = omega * sample_period
    if abs(omega_sample) <= 1e-15:
        zero_order_hold = 1.0 + 0.0j
    else:
        zero_order_hold = (
            cmath.exp(-0.5j * omega_sample)
            * math.sin(0.5 * omega_sample)
            / (0.5 * omega_sample)
        )
    actuator = 1.0 / (1.0 + 1j * omega * actuator_time_constant)
    return sampled_rocof_transfer(
        frequency,
        sample_period_s=sample_period,
        filter_time_constant_s=filter_time_constant_s,
    ) * zero_order_hold * actuator


def graph_coordinate_audit(
    adjacency: Mapping[int, Sequence[int]],
    *,
    device_count: int,
) -> dict[str, object]:
    """Audit the common kernel and differential spectrum of the graph law."""

    laplacian = row_normalized_laplacian(adjacency, device_count=device_count)
    symmetry_error = float(np.max(np.abs(laplacian - laplacian.T)))
    common_residual = laplacian @ np.ones(device_count, dtype=float)
    eigenvalues = np.linalg.eigvalsh(0.5 * (laplacian + laplacian.T))
    return {
        "laplacian": laplacian.tolist(),
        "symmetry_max_abs": symmetry_error,
        "common_kernel_max_abs": float(np.max(np.abs(common_residual))),
        "eigenvalues": [float(value) for value in eigenvalues],
        "differential_eigenvalues": [
            float(value) for value in eigenvalues if value > 1e-12
        ],
    }


def ideal_swing_routh_margin(
    *,
    inertia: float,
    damping: float,
    synchronizing_stiffness: float,
    filter_time_constant_s: float,
    graph_eigenvalue: float,
    residual_gain: float,
) -> dict[str, object]:
    """Return the cubic coefficients and Routh margin for one ideal mode.

    For ``M*w_dot = -D*w - K_s*theta - K_v*lambda*r`` and
    ``tau*r_dot = w_dot-r``, the characteristic polynomial is

    ``tau*M*s^3 + (M+tau*D+K_v*lambda)*s^2``
    ``+ (D+tau*K_s)*s + K_s``.

    Positive physical parameters and non-negative gain make the Routh margin
    strictly positive.  This proves no finite ideal-model gain ceiling; it does
    not cover sampling, delay, projection, saturation, or the full DAE.
    """

    values = {
        "inertia": float(inertia),
        "damping": float(damping),
        "synchronizing_stiffness": float(synchronizing_stiffness),
        "filter_time_constant_s": float(filter_time_constant_s),
        "graph_eigenvalue": float(graph_eigenvalue),
        "residual_gain": float(residual_gain),
    }
    if any(not math.isfinite(value) for value in values.values()):
        raise ValueError("ideal swing parameters must be finite")
    if min(
        values["inertia"],
        values["damping"],
        values["synchronizing_stiffness"],
        values["filter_time_constant_s"],
        values["graph_eigenvalue"],
    ) <= 0.0 or values["residual_gain"] < 0.0:
        raise ValueError("physical parameters must be positive and gain non-negative")
    inertia_value = values["inertia"]
    damping_value = values["damping"]
    stiffness = values["synchronizing_stiffness"]
    tau = values["filter_time_constant_s"]
    graph_value = values["graph_eigenvalue"]
    gain = values["residual_gain"]
    coefficients = [
        tau * inertia_value,
        inertia_value + tau * damping_value + gain * graph_value,
        damping_value + tau * stiffness,
        stiffness,
    ]
    margin = coefficients[1] * coefficients[2] - coefficients[0] * coefficients[3]
    slope = graph_value * (damping_value + tau * stiffness)
    return {
        "characteristic_coefficients_descending": coefficients,
        "routh_margin": float(margin),
        "routh_margin_gain_slope": float(slope),
        "stable": bool(all(value > 0.0 for value in coefficients) and margin > 0.0),
    }


def esd_active_power_input_matrix(
    state_names: Sequence[str],
    *,
    device_count: int,
    active_current_lag_seconds: float,
    sensed_voltage_pu: float | Sequence[float],
) -> np.ndarray:
    """Construct the local equilibrium input map to ESD1 ``Ipout_y`` states.

    ANDES ESD1 uses ``tip * d(Ipout_y)/dt = Pext/vp - Ipout_y`` around the
    unsaturated zero-power equilibrium. ``Pext`` is documented by ANDES as
    system-base per unit.  A voltage vector permits an explicit uncertainty
    envelope when algebraic equilibrium voltages were not retained.
    """

    lag = float(active_current_lag_seconds)
    if lag <= 0.0 or not math.isfinite(lag):
        raise ValueError("active_current_lag_seconds must be finite and positive")
    voltages = np.broadcast_to(np.asarray(sensed_voltage_pu, dtype=float), (device_count,))
    if not np.all(np.isfinite(voltages)) or np.any(voltages <= 0.0):
        raise ValueError("sensed voltages must be finite and positive")
    indices = [
        index
        for index, name in enumerate(state_names)
        if str(name).startswith("Ipout_y ESD1")
    ]
    if len(indices) != device_count:
        raise ValueError(
            f"expected {device_count} ESD1 Ipout states, found {len(indices)}"
        )
    matrix = np.zeros((len(state_names), device_count), dtype=float)
    for device, state_index in enumerate(indices):
        matrix[state_index, device] = 1.0 / (lag * voltages[device])
    return matrix


def frequency_output_matrix(
    state_count: int,
    frequency_state_indices: Sequence[int],
    *,
    nominal_frequency_hz: float,
) -> np.ndarray:
    """Map per-unit VSG speed states to physical-Hz deviations."""

    indices = [int(value) for value in frequency_state_indices]
    output = np.zeros((len(indices), int(state_count)), dtype=float)
    for row, state_index in enumerate(indices):
        output[row, state_index] = float(nominal_frequency_hz)
    return output


def sampled_closed_loop_matrix(
    plant_state_matrix: np.ndarray,
    plant_input_matrix: np.ndarray,
    frequency_output: np.ndarray,
    graph_laplacian: np.ndarray,
    *,
    sample_period_s: float,
    filter_time_constant_s: float,
    kp_system_pu_per_hz: float,
    ki_system_pu_per_hz_s: float,
    sync_gain_system_pu_per_hz: float,
    consensus_gain_per_s: float,
    relative_rocof_gain_system_pu_s_per_hz: float,
) -> np.ndarray:
    """Build the exact ZOH plant plus implemented sampled local-controller map.

    The augmented state is ``[x[k], z[k-1], r[k-1], y[k-1]]``. Projection and
    anti-windup are inactive in this equilibrium diagnostic.
    """

    a = np.asarray(plant_state_matrix, dtype=float)
    b = np.asarray(plant_input_matrix, dtype=float)
    c = np.asarray(frequency_output, dtype=float)
    laplacian = np.asarray(graph_laplacian, dtype=float)
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise ValueError("plant_state_matrix must be square")
    state_count = a.shape[0]
    device_count = c.shape[0]
    if b.shape != (state_count, device_count):
        raise ValueError("plant_input_matrix shape mismatch")
    if c.shape[1] != state_count or laplacian.shape != (device_count, device_count):
        raise ValueError("frequency or graph matrix shape mismatch")
    sample_period = float(sample_period_s)
    time_constant = float(filter_time_constant_s)
    if sample_period <= 0.0 or time_constant <= 0.0:
        raise ValueError("sample period and filter time constant must be positive")

    augmented_plant = np.zeros(
        (state_count + device_count, state_count + device_count), dtype=float
    )
    augmented_plant[:state_count, :state_count] = a
    augmented_plant[:state_count, state_count:] = b
    transition = expm(augmented_plant * sample_period)
    ad = transition[:state_count, :state_count]
    bd = transition[:state_count, state_count:]

    identity = np.eye(device_count, dtype=float)
    alpha = math.exp(-sample_period / time_constant)
    beta = (1.0 - alpha) / sample_period
    integral_from_integral = identity - sample_period * float(
        consensus_gain_per_s
    ) * laplacian
    integral_from_plant = -sample_period * float(ki_system_pu_per_hz_s) * c
    rocof_from_plant = beta * c

    static_frequency = (
        float(kp_system_pu_per_hz) * identity
        + float(sync_gain_system_pu_per_hz) * laplacian
    )
    gain_laplacian = float(
        relative_rocof_gain_system_pu_s_per_hz
    ) * laplacian
    input_from_plant = (
        -static_frequency @ c
        + integral_from_plant
        - gain_laplacian @ rocof_from_plant
    )
    input_from_integral = integral_from_integral
    input_from_rocof = -alpha * gain_laplacian
    input_from_previous_frequency = beta * gain_laplacian

    total = state_count + 3 * device_count
    closed_loop = np.zeros((total, total), dtype=float)
    x_slice = slice(0, state_count)
    integral_slice = slice(state_count, state_count + device_count)
    rocof_slice = slice(state_count + device_count, state_count + 2 * device_count)
    previous_frequency_slice = slice(
        state_count + 2 * device_count, state_count + 3 * device_count
    )

    closed_loop[x_slice, x_slice] = ad + bd @ input_from_plant
    closed_loop[x_slice, integral_slice] = bd @ input_from_integral
    closed_loop[x_slice, rocof_slice] = bd @ input_from_rocof
    closed_loop[x_slice, previous_frequency_slice] = (
        bd @ input_from_previous_frequency
    )
    closed_loop[integral_slice, x_slice] = integral_from_plant
    closed_loop[integral_slice, integral_slice] = integral_from_integral
    closed_loop[rocof_slice, x_slice] = rocof_from_plant
    closed_loop[rocof_slice, rocof_slice] = alpha * identity
    closed_loop[rocof_slice, previous_frequency_slice] = -beta * identity
    closed_loop[previous_frequency_slice, x_slice] = c
    return closed_loop


def sampled_mode_summary(
    closed_loop_matrix: np.ndarray,
    *,
    sample_period_s: float,
    machine_state_indices: Mapping[str, int],
    area_1_keys: Sequence[str],
    area_2_keys: Sequence[str],
    frequency_band_hz: tuple[float, float] = (0.2, 1.5),
    unstable_tolerance: float = 1e-7,
) -> dict[str, object]:
    """Summarize unit-circle validity and the registered inter-area branch."""

    matrix = np.asarray(closed_loop_matrix, dtype=float)
    eigenvalues, left, right = eig(matrix, left=True, right=True)
    magnitudes = np.abs(eigenvalues)
    unstable = magnitudes > 1.0 + float(unstable_tolerance)
    candidates: list[dict[str, float]] = []
    for mode_index, discrete_value in enumerate(eigenvalues):
        if abs(discrete_value) <= 1e-14:
            continue
        continuous_value = cmath.log(complex(discrete_value)) / float(sample_period_s)
        if continuous_value.imag <= 0.0:
            continue
        frequency_hz = continuous_value.imag / (2.0 * math.pi)
        if not frequency_band_hz[0] <= frequency_hz <= frequency_band_hz[1]:
            continue
        raw = np.abs(
            right[:, mode_index] * np.conjugate(left[:, mode_index])
        )
        total = float(np.sum(raw))
        if not math.isfinite(total) or total <= 0.0:
            continue
        normalized = raw / total
        machine = {
            key: float(normalized[int(machine_state_indices[key])])
            for key in machine_state_indices
        }
        contrast = abs(
            sum(machine[key] for key in area_1_keys)
            - sum(machine[key] for key in area_2_keys)
        )
        damping_ratio = -continuous_value.real / max(abs(continuous_value), 1e-30)
        candidates.append(
            {
                "discrete_magnitude": float(abs(discrete_value)),
                "continuous_real_per_s": float(continuous_value.real),
                "continuous_imag_per_s": float(continuous_value.imag),
                "frequency_hz": float(frequency_hz),
                "damping_ratio": float(damping_ratio),
                "area_contrast": float(contrast),
            }
        )
    mode = None if not candidates else max(candidates, key=lambda item: item["area_contrast"])
    return {
        "spectral_radius": float(np.max(magnitudes)),
        "unstable_count": int(np.count_nonzero(unstable)),
        "neutral_count": int(
            np.count_nonzero(np.abs(magnitudes - 1.0) <= unstable_tolerance)
        ),
        "interarea_mode": mode,
    }
