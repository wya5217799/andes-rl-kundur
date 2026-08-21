"""Exact ZOH fractional command-delay realization and pole tracking."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np
import scipy.linalg as la
from scipy.optimize import linear_sum_assignment

from andes_rl_kundur.evaluation.u5_total_sensitivity import _controller_realization

TS = 0.2
MEMORY_BLOCKS = 10
SCAN_TAUS = np.linspace(0.0, 2.0, 201)


def _zoh_input(a: np.ndarray, b: np.ndarray, duration: float) -> np.ndarray:
    if duration <= 0.0:
        return np.zeros_like(b)
    n, m = b.shape
    block = np.zeros((n + m, n + m))
    block[:n, :n], block[:n, n:] = a * duration, b * duration
    return la.expm(block)[:n, n:]


def delay_split(a: np.ndarray, b: np.ndarray, delta: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not 0.0 <= delta < TS + 1e-12:
        raise ValueError("delta outside one sample")
    ad = la.expm(a * TS)
    bd = _zoh_input(a, b, TS)
    b0 = _zoh_input(a, b, max(0.0, TS - delta))
    return ad, b0, bd - b0


def augmented_matrix(
    a_c: np.ndarray,
    b_c: np.ndarray,
    c: np.ndarray,
    tau: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Return fixed-dimension autonomous bandpass closed-loop matrix."""

    if tau < 0.0 or tau > MEMORY_BLOCKS * TS + 1e-12:
        raise ValueError("tau outside fixed memory")
    if abs(tau - MEMORY_BLOCKS * TS) <= 1e-12:
        integer, delta = MEMORY_BLOCKS, 0.0
    else:
        integer = int(np.floor(tau / TS + 1e-12))
        delta = tau - integer * TS
        if delta < 1e-12:
            delta = 0.0
    ad, b0, b1 = delay_split(a_c, b_c, delta)
    ak, bk, ck, dk = _controller_realization("bandpass")
    nx, nk, nu = a_c.shape[0], ak.shape[0], b_c.shape[1]
    total = nx + nk + MEMORY_BLOCKS * nu
    acl = np.zeros((total, total))
    sx = slice(0, nx)
    sk = slice(nx, nx + nk)
    memory = [slice(nx + nk + j * nu, nx + nk + (j + 1) * nu) for j in range(MEMORY_BLOCKS)]
    ux, uk = -dk @ c, -ck
    acl[sx, sx] = ad
    if integer == 0:
        acl[sx, sx] += b0 @ ux
        acl[sx, sk] += b0 @ uk
        if np.any(b1):
            acl[sx, memory[0]] += b1
    else:
        acl[sx, memory[integer - 1]] += b0
        if integer < MEMORY_BLOCKS and np.any(b1):
            acl[sx, memory[integer]] += b1
    acl[sk, sx], acl[sk, sk] = bk @ c, ak
    acl[memory[0], sx], acl[memory[0], sk] = ux, uk
    for index in range(1, MEMORY_BLOCKS):
        acl[memory[index], memory[index - 1]] = np.eye(nu)
    digest = hashlib.sha256(np.ascontiguousarray(acl).tobytes()).hexdigest()
    return acl, {
        "tau_s": float(tau), "integer_delay_samples": integer,
        "fractional_delta_s": float(delta), "B0": b0, "B1": b1,
        "augmented_matrix_sha256": digest, "dimension": total,
    }


@dataclass
class Spectrum:
    values: np.ndarray
    left: np.ndarray
    right: np.ndarray
    residuals: np.ndarray
    inverse_overlaps: np.ndarray


def spectrum(matrix: np.ndarray) -> Spectrum:
    values, left, right = la.eig(matrix, left=True, right=True)
    left = left / np.linalg.norm(left, axis=0, keepdims=True)
    right = right / np.linalg.norm(right, axis=0, keepdims=True)
    scale = max(1.0, float(la.norm(matrix, 2)))
    residuals = np.array([
        la.norm(matrix @ right[:, index] - values[index] * right[:, index]) / scale
        for index in range(values.size)
    ])
    overlaps = np.abs(np.sum(np.conj(left) * right, axis=0))
    inverse = 1.0 / np.maximum(overlaps, np.finfo(float).tiny)
    return Spectrum(values, left, right, residuals, inverse)


def _initial_order(values: np.ndarray) -> np.ndarray:
    return np.lexsort((np.imag(values), np.real(values), np.abs(values)))


def match_spectra(previous: Spectrum, current: Spectrum) -> tuple[np.ndarray, np.ndarray]:
    pv, cv = previous.values, current.values
    distance = np.abs(pv[:, None] - cv[None, :]) / (0.05 + np.abs(pv[:, None]))
    mac = np.abs(np.conj(previous.right).T @ current.right)
    cost = distance + 0.25 * (1.0 - np.minimum(mac, 1.0))
    rows, cols = linear_sum_assignment(cost)
    order = np.empty_like(cols)
    order[rows] = cols
    return order, cost[rows, cols]


def track_branches(a_c: np.ndarray, b_c: np.ndarray, c: np.ndarray) -> dict[str, Any]:
    matrices = []
    metadata = []
    spectra = []
    for tau in SCAN_TAUS:
        matrix, meta = augmented_matrix(a_c, b_c, c, float(tau))
        matrices.append(matrix)
        metadata.append(meta)
        spectra.append(spectrum(matrix))
    initial_order = _initial_order(spectra[0].values)
    first = spectra[0]
    first = Spectrum(first.values[initial_order], first.left[:, initial_order], first.right[:, initial_order], first.residuals[initial_order], first.inverse_overlaps[initial_order])
    tracked = [first]
    match_costs = [np.zeros(first.values.size)]
    for raw in spectra[1:]:
        order, cost = match_spectra(tracked[-1], raw)
        tracked.append(Spectrum(raw.values[order], raw.left[:, order], raw.right[:, order], raw.residuals[order], raw.inverse_overlaps[order]))
        match_costs.append(cost)
    values = np.stack([item.values for item in tracked])
    left = np.stack([item.left for item in tracked])
    right = np.stack([item.right for item in tracked])
    residuals = np.stack([item.residuals for item in tracked])
    conditions = np.stack([item.inverse_overlaps for item in tracked])
    costs = np.stack(match_costs)
    candidates = []
    for row in range(len(SCAN_TAUS) - 1):
        for branch in range(values.shape[1]):
            if abs(values[row, branch]) > 1e-8 and abs(values[row, branch]) < 1.0 <= abs(values[row + 1, branch]):
                candidates.append((float(SCAN_TAUS[row]), branch, row))
    crossing = min(candidates, default=None)
    refined = None
    if crossing is not None:
        refined = refine_crossing(a_c, b_c, c, tracked[crossing[2]], tracked[crossing[2] + 1], crossing[1], crossing[0], crossing[0] + 0.01)
    return {
        "taus": SCAN_TAUS, "values": values, "left": left, "right": right,
        "residuals": residuals,
        "conditions": conditions, "match_costs": costs, "metadata": metadata,
        "matrices": matrices, "crossing": refined,
    }


def _select_branch(reference_value: complex, reference_vector: np.ndarray, candidate: Spectrum) -> int:
    distance = np.abs(candidate.values - reference_value) / (0.05 + abs(reference_value))
    mac = np.abs(np.conj(reference_vector) @ candidate.right)
    return int(np.argmin(distance + 0.25 * (1.0 - np.minimum(mac, 1.0))))


def refine_crossing(
    a_c: np.ndarray, b_c: np.ndarray, c: np.ndarray,
    left_spectrum: Spectrum, right_spectrum: Spectrum, branch: int,
    tau_left: float, tau_right: float,
) -> dict[str, Any]:
    lv, lvec = left_spectrum.values[branch], left_spectrum.right[:, branch]
    rv, rvec = right_spectrum.values[branch], right_spectrum.right[:, branch]
    while tau_right - tau_left > 1e-5:
        midpoint = 0.5 * (tau_left + tau_right)
        matrix, _ = augmented_matrix(a_c, b_c, c, midpoint)
        mid = spectrum(matrix)
        target = 0.5 * (lv + rv)
        index = _select_branch(target, lvec + rvec, mid)
        mv, mvec = mid.values[index], mid.right[:, index]
        if abs(mv) >= 1.0:
            tau_right, rv, rvec, right_spectrum = midpoint, mv, mvec, mid
        else:
            tau_left, lv, lvec, left_spectrum = midpoint, mv, mvec, mid
    tau_star = 0.5 * (tau_left + tau_right)
    matrix, _ = augmented_matrix(a_c, b_c, c, tau_star)
    centre = spectrum(matrix)
    index = _select_branch(0.5 * (lv + rv), lvec + rvec, centre)
    value = centre.values[index]
    step = 1e-5
    slopes = []
    for tau in (max(0.0, tau_star - step), min(2.0, tau_star + step)):
        neighbour = spectrum(augmented_matrix(a_c, b_c, c, tau)[0])
        selected = _select_branch(value, centre.right[:, index], neighbour)
        slopes.append(np.log(abs(neighbour.values[selected])))
    transversality = (slopes[1] - slopes[0]) / (2.0 * step)
    return {
        "branch_id": int(branch), "tau_left_s": tau_left, "tau_right_s": tau_right,
        "tau_mid_s": tau_star, "eigenvalue_real": float(np.real(value)),
        "eigenvalue_imag": float(np.imag(value)), "modulus": float(abs(value)),
        "residual": float(centre.residuals[index]),
        "inverse_left_right_overlap": float(centre.inverse_overlaps[index]),
        "transversality_d_log_modulus_per_s": float(transversality),
    }


def classify_tracking(result: dict[str, Any]) -> tuple[str, dict[str, bool]]:
    residual_pass = bool(np.max(result["residuals"]) <= 1e-9)
    finite = bool(np.all(np.isfinite(result["values"])))
    crossing = result["crossing"]
    checks = {"finite_spectrum": finite, "residual_pass": residual_pass}
    if not finite or not residual_pass:
        return "POLE-TRACKING-INVALID", checks
    if crossing is None:
        return "NO-CROSSING-UP-TO-2S", checks
    simple = bool(
        crossing["inverse_left_right_overlap"] <= 1e8
        and abs(crossing["transversality_d_log_modulus_per_s"]) >= 1e-3
        and crossing["tau_right_s"] - crossing["tau_left_s"] <= 1e-5
    )
    checks["simple_crossing"] = simple
    return ("NOMINAL-LOCAL-CROSSING-VALID" if simple else "NEAR-DEFECTIVE-CROSSING"), checks


__all__ = [
    "MEMORY_BLOCKS", "SCAN_TAUS", "TS", "augmented_matrix", "classify_tracking",
    "delay_split", "spectrum", "track_branches",
]
