"""Complete finite-difference total-sensitivity machinery for Object B.

The module deliberately keeps model reconstruction, fixed-coordinate gauge
reduction, feedback interconnection, and derivative verification separate so
the R465 execution adapter only owns lifecycle and persistence.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np
import scipy.linalg as la
from scipy.signal import cont2discrete

DT = 0.2
H_STEPS = (0.04, 0.02, 0.01)
FREQUENCIES_HZ = np.concatenate(([1.0e-8], np.linspace(2.5 / 1024.0, 2.5, 1024)))
LOAD_IDS = ("PQ_0", "PQ_1", "PQ_Bus14")
FD_STEPS = (1.0e-4, 1.0e-5, 1.0e-6)
T_D = np.array(
    [
        [0.5, 0.5, -0.5, -0.5],
        [2**-0.5, -(2**-0.5), 0.0, 0.0],
        [0.0, 0.0, 2**-0.5, -(2**-0.5)],
    ]
)


def _digest_array(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode())
    digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
    digest.update(array.tobytes())
    return digest.hexdigest()


def point_id(parameter: str, rho: float) -> str:
    if parameter == "nominal":
        return "nominal"
    sign = "p" if rho > 0 else "m"
    return f"{parameter}_{sign}{abs(rho):.3f}".replace(".", "")


def point_specs() -> list[tuple[str, float]]:
    return [("nominal", 0.0)] + [
        (parameter, sign * step)
        for parameter in ("logM", "logD")
        for step in H_STEPS
        for sign in (-1.0, 1.0)
    ]


def build_point(parameter: str, rho: float) -> dict[str, Any]:
    """Initialize ANDES and return one complete, in-memory Object-B point."""

    from andes_rl_kundur.control.active_power import r272_frozen_bess_contract
    from andes_rl_kundur.evaluation.model_first_input_bridge import (
        fold_zero_time_constant_states,
        reduce_folded_descriptor,
    )
    from andes_rl_kundur.evaluation.vsg_energy_port_source_adapter import (
        AndesVSGEnergyPortFixedStateSource,
    )
    from andes_rl_kundur.evaluation.vsg_energy_port_source_bridge import (
        derive_vsg_energy_port_input_bridge,
    )
    from andes_rl_kundur.evaluation.vsg_energy_port_source_model import (
        construct_vsg_energy_port_source_model,
    )
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.v4_config import V4Config
    from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv

    scale = float(np.exp(rho))
    m_scale = scale if parameter == "logM" else 1.0
    d_scale = scale if parameter == "logD" else 1.0
    base = AndesMultiVSGEnvV4(
        random_disturbance=False,
        comm_fail_prob=0.0,
        comm_delay_steps=0,
        config=V4Config(
            vsg_m0=200.0 * m_scale,
            d0_per_agent=tuple(100.0 * d_scale for _ in range(4)),
        ),
    )
    base.seed(42)
    env = AndesVSGEnergyPortEnv(base_env=base)
    try:
        env.reset(delta_u={})
        source = AndesVSGEnergyPortFixedStateSource.from_initialized_energy_port_env(
            env, pq_load_ids=LOAD_IDS, source_fingerprint=f"R465:{parameter}:{rho:+.8f}"
        )
        bridges = tuple(
            derive_vsg_energy_port_input_bridge(
                binding=source.binding, source=source, step_system_pu=step
            )
            for step in FD_STEPS
        )
        result = construct_vsg_energy_port_source_model(
            snapshot=source.descriptor_snapshot, bridges=bridges
        )
        if not result.passed or result.sampled_model is None:
            raise RuntimeError(f"Object B source gate failed: {result.error}")
        snap = source.descriptor_snapshot
        selected = bridges[-1]
        folded = fold_zero_time_constant_states(
            time_constants=snap.time_constants,
            f_x=snap.f_x,
            f_y=snap.f_y,
            g_x=snap.g_x,
            g_y=snap.g_y,
            f_input=selected.joint_f_input,
            g_input=selected.joint_g_input,
        )
        reduced = reduce_folded_descriptor(folded, minimum_reciprocal_condition=1.0e-12)
        c_cont = snap.frequency_output_map[:, folded.dynamic_state_indices]
        d_cont = np.zeros((4, 7))
        ad, bd, cd, dd, _ = cont2discrete(
            (reduced.state_matrix, reduced.input_matrix, c_cont, d_cont), DT, method="zoh"
        )
        sampled = result.sampled_model
        contract = r272_frozen_bess_contract()
        lower, upper = contract.feasible_power_bounds(
            previous_power_system_pu=np.zeros(4),
            soc=np.full(4, float(contract.soc_initial)),
            voltage_pu=np.ones(4),
            dt_seconds=DT,
        )
        arrays = {
            "time_constants": snap.time_constants.copy(),
            "f_x": snap.f_x.copy(), "f_y": snap.f_y.copy(),
            "g_x": snap.g_x.copy(), "g_y": snap.g_y.copy(),
            "equilibrium_x": snap.equilibrium_x.copy(),
            "equilibrium_y": snap.equilibrium_y.copy(),
            "equilibrium_z": snap.equilibrium_z.copy(),
            "equilibrium_f": snap.equilibrium_f.copy(),
            "equilibrium_g": snap.equilibrium_g.copy(),
            "F_input": folded.f_input.copy(), "G_input": folded.g_input.copy(),
            "dynamic_state_indices": folded.dynamic_state_indices.copy(),
            "folded_state_indices": folded.folded_state_indices.copy(),
            "A_continuous": reduced.state_matrix.copy(),
            "B_continuous": reduced.input_matrix.copy(),
            "C_continuous": c_cont.copy(), "D_continuous": d_cont.copy(),
            "A_sampled": np.asarray(ad), "B_sampled": np.asarray(bd),
            "C_sampled": np.asarray(cd), "D_sampled": np.asarray(dd),
            "A_post": sampled.state_matrix.copy(),
            "B_post": sampled.input_matrix.copy(),
            "C_post": sampled.output_matrix.copy(),
            "D_post": sampled.feedthrough_matrix.copy(),
            "headroom_lower": np.asarray(lower), "headroom_upper": np.asarray(upper),
        }
        names = {
            "state_names": list(snap.state_names),
            "algebraic_names": list(snap.algebraic_names),
            "dynamic_state_names": list(result.dynamic_state_names),
        }
        name_hash = hashlib.sha256(json.dumps(names, sort_keys=True).encode()).hexdigest()
        return {
            "parameter": parameter,
            "rho": rho,
            "point_id": point_id(parameter, rho),
            "M_values": [200.0 * m_scale] * 4,
            "D_values": [100.0 * d_scale] * 4,
            "arrays": arrays,
            "names": names,
            "name_hash": name_hash,
            "active_mode_hash": _digest_array(arrays["equilibrium_z"]),
            "equilibrium_max_abs_f": float(np.max(np.abs(arrays["equilibrium_f"]))),
            "equilibrium_max_abs_g": float(np.max(np.abs(arrays["equilibrium_g"]))),
            "algebraic_reciprocal_condition": float(reduced.algebraic_reciprocal_condition),
            "source_metrics": result.metrics,
        }
    finally:
        env.close()


def gauge_complement(nominal: dict[str, Any]) -> tuple[np.ndarray, dict[str, float]]:
    a = nominal["arrays"]["A_post"]
    c = nominal["arrays"]["C_post"]
    values, vectors = la.eig(a)
    index = int(np.argmin(np.abs(values - 1.0)))
    v = np.real(vectors[:, index])
    v /= np.linalg.norm(v)
    u = la.null_space(v.reshape(1, -1))
    return u, {
        "gauge_eigenvalue_real": float(np.real(values[index])),
        "gauge_eigenvalue_imag": float(np.imag(values[index])),
        "right_residual": float(np.linalg.norm(a @ v - values[index] * v)),
        "output_norm": float(np.linalg.norm(c @ v)),
    }


def reduce_point(point: dict[str, Any], u: np.ndarray) -> tuple[dict[str, np.ndarray], dict[str, float]]:
    arrays = point["arrays"]
    a, b, c, d = (arrays[key] for key in ("A_post", "B_post", "C_post", "D_post"))
    reduced = {"A": u.T @ a @ u, "B": u.T @ b, "C": c @ u, "D": d.copy()}
    # The unobservable gauge coordinate may receive a driven component from
    # the observable quotient without changing any transfer.  The required
    # direction is the converse: the gauge eigenvector must not drive the
    # retained quotient (lower-left block of T'AT).
    gauge_vector = la.null_space(u.T)[:, 0]
    gauge_leak = float(np.linalg.norm(u.T @ a @ gauge_vector))
    frequencies = (0.1, 0.4, 1.0, 2.5)
    errors = []
    for frequency in frequencies:
        z = np.exp(2j * np.pi * frequency * DT)
        full = c @ la.solve(z * np.eye(a.shape[0]) - a, b) + d
        red = reduced["C"] @ la.solve(z * np.eye(reduced["A"].shape[0]) - reduced["A"], reduced["B"]) + d
        errors.append(np.linalg.norm(full - red) / max(np.linalg.norm(full), 1e-12))
    return reduced, {
        "gauge_to_reduced_leakage": gauge_leak,
        "maximum_transfer_relative_error": float(max(errors)),
        "spectral_radius": float(np.max(np.abs(la.eigvals(reduced["A"])))),
    }


def _controller_realization(kind: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if kind == "bandpass":
        from andes_rl_kundur.control.ring_bandpass_damping import (
            prewarped_bandpass_coefficients,
            ring_incidence,
        )

        num, den = prewarped_bandpass_coefficients(f0_hz=0.4, zeta=0.35, dt=DT, gain=3.5)
        b0, b1, b2 = map(float, num)
        a1, a2 = float(den[1]), float(den[2])
        ring = ring_incidence(4)
        ak = np.block([[-a1 * np.eye(4), np.eye(4)], [-a2 * np.eye(4), np.zeros((4, 4))]])
        bk = np.vstack([(b1 - a1 * b0) * ring.T, (b2 - a2 * b0) * ring.T])
        ck = np.hstack([ring, np.zeros((4, 4))])
        dk = b0 * ring @ ring.T
        return ak, bk, ck, dk
    if kind == "local_pi":
        return np.eye(4), 0.8 * DT * np.eye(4), np.eye(4), 4.0 * np.eye(4)
    raise ValueError(kind)


def controller_transfer(kind: str, z: complex) -> np.ndarray:
    ak, bk, ck, dk = _controller_realization(kind)
    return ck @ la.solve(z * np.eye(ak.shape[0]) - ak, bk) + dk


def closed_loop_realization(model: dict[str, np.ndarray], headroom: np.ndarray, kind: str) -> tuple[np.ndarray, ...]:
    a, b, c, d = model["A"], model["B"], model["C"], model["D"]
    bc, bw = b[:, :4] @ np.diag(headroom), b[:, 4:]
    dc, dw = d[:, :4] @ np.diag(headroom), d[:, 4:]
    ak, bk, ck, dk = _controller_realization(kind)
    ret = np.eye(4) + dc @ dk
    yx = la.solve(ret, c)
    yc = la.solve(ret, -dc @ ck)
    yw = la.solve(ret, dw)
    ux, uc, uw = -dk @ yx, -ck - dk @ yc, -dk @ yw
    acl = np.block([[a + bc @ ux, bc @ uc], [bk @ yx, ak + bk @ yc]])
    bcl = np.vstack([bw + bc @ uw, bk @ yw])
    ccl = np.hstack([yx, yc])
    return acl, bcl, ccl, yw


def window_energy(model: dict[str, np.ndarray], headroom: np.ndarray, kind: str, steps: int = 30) -> float:
    a, b, c, d = closed_loop_realization(model, headroom, kind)
    energy = 0.0
    for channel in range(3):
        state = np.zeros(a.shape[0])
        for step in range(steps):
            w = np.zeros(3)
            if step == 0:
                w[channel] = 1.0
            y = c @ state + d @ w
            energy += float(np.linalg.norm(T_D @ y) ** 2)
            state = a @ state + b @ w
    return energy


def transfer_arrays(model: dict[str, np.ndarray], headroom: np.ndarray, kind: str) -> dict[str, np.ndarray]:
    a, b, c, d = model["A"], model["B"], model["C"], model["D"]
    bc, bw = b[:, :4] @ np.diag(headroom), b[:, 4:]
    dc, dw = d[:, :4] @ np.diag(headroom), d[:, 4:]
    shapes = {"Pc": (len(FREQUENCIES_HZ), 4, 4), "Pw": (len(FREQUENCIES_HZ), 4, 3),
              "K": (len(FREQUENCIES_HZ), 4, 4), "L": (len(FREQUENCIES_HZ), 4, 4),
              "S": (len(FREQUENCIES_HZ), 4, 4), "G": (len(FREQUENCIES_HZ), 4, 3)}
    out = {key: np.empty(shape, dtype=complex) for key, shape in shapes.items()}
    cond_a = np.empty(len(FREQUENCIES_HZ)); cond_return = np.empty(len(FREQUENCIES_HZ))
    for index, frequency in enumerate(FREQUENCIES_HZ):
        z = np.exp(2j * np.pi * frequency * DT)
        resolvent = z * np.eye(a.shape[0]) - a
        pc = c @ la.solve(resolvent, bc) + dc
        pw = c @ la.solve(resolvent, bw) + dw
        k = controller_transfer(kind, z)
        loop = pc @ k
        ret = np.eye(4) + loop
        sensitivity = la.solve(ret, np.eye(4))
        out["Pc"][index], out["Pw"][index], out["K"][index] = pc, pw, k
        out["L"][index], out["S"][index], out["G"][index] = loop, sensitivity, sensitivity @ pw
        cond_a[index], cond_return[index] = np.linalg.cond(resolvent), np.linalg.cond(ret)
    out["cond_zI_minus_A"] = cond_a
    out["cond_I_plus_L"] = cond_return
    return out


def centered(values: dict[float, np.ndarray | float], step: float) -> np.ndarray:
    return (np.asarray(values[step]) - np.asarray(values[-step])) / (2.0 * step)


def derivative_table(values: dict[float, np.ndarray | float]) -> dict[str, np.ndarray]:
    d1, d2, d3 = (centered(values, step) for step in H_STEPS)
    r1 = (4.0 * d2 - d1) / 3.0
    r2 = (4.0 * d3 - d2) / 3.0
    return {"D_h": d1, "D_h2": d2, "D_h4": d3, "R_h": r1, "R_h2": r2, "derivative": r2}


def discrepancy(actual: np.ndarray, expected: np.ndarray) -> dict[str, float | bool]:
    delta = np.asarray(actual) - np.asarray(expected)
    absolute = float(np.max(np.abs(delta)))
    relative = float(np.linalg.norm(delta.ravel()) / max(np.linalg.norm(np.asarray(expected).ravel()), 1e-12))
    return {"max_abs": absolute, "relative": relative, "passed": bool(relative <= 0.01 or absolute <= 1e-9)}


def zoh_frechet(a: np.ndarray, b: np.ndarray, a_rho: np.ndarray, b_rho: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n, m = b.shape
    block = np.zeros((n + m, n + m)); direction = np.zeros_like(block)
    block[:n, :n], block[:n, n:] = a * DT, b * DT
    direction[:n, :n], direction[:n, n:] = a_rho * DT, b_rho * DT
    derivative = la.expm_frechet(block, direction, compute_expm=False)
    return derivative[:n, :n], derivative[:n, n:]


def frequency_derivative(
    nominal: dict[str, np.ndarray], derivative: dict[str, np.ndarray], headroom: np.ndarray,
    headroom_rho: np.ndarray, kind: str,
) -> dict[str, np.ndarray]:
    a, b, c, d = (nominal[key] for key in ("A", "B", "C", "D"))
    ar, br, cr, dr = (derivative[key] for key in ("A", "B", "C", "D"))
    bc, bw = b[:, :4] @ np.diag(headroom), b[:, 4:]
    bcr = br[:, :4] @ np.diag(headroom) + b[:, :4] @ np.diag(headroom_rho)
    bwr = br[:, 4:]
    dc, dw = d[:, :4] @ np.diag(headroom), d[:, 4:]
    dcr = dr[:, :4] @ np.diag(headroom) + d[:, :4] @ np.diag(headroom_rho)
    dwr = dr[:, 4:]
    base = transfer_arrays(nominal, headroom, kind)
    derivatives = {key: np.empty_like(base[key]) for key in ("Pc", "Pw", "K", "L", "S", "G")}
    derivatives["K"].fill(0.0)
    for index, frequency in enumerate(FREQUENCIES_HZ):
        z = np.exp(2j * np.pi * frequency * DT)
        resolvent = z * np.eye(a.shape[0]) - a
        xc, xw = la.solve(resolvent, bc), la.solve(resolvent, bw)
        xcr = la.solve(resolvent, ar @ xc + bcr)
        xwr = la.solve(resolvent, ar @ xw + bwr)
        pcr = cr @ xc + c @ xcr + dcr
        pwr = cr @ xw + c @ xwr + dwr
        k, pc, pw, s, g = (base[key][index] for key in ("K", "Pc", "Pw", "S", "G"))
        lr = pcr @ k
        sr = -s @ lr @ s
        gr = s @ (pwr - lr @ g)
        derivatives["Pc"][index], derivatives["Pw"][index] = pcr, pwr
        derivatives["L"][index], derivatives["S"][index], derivatives["G"][index] = lr, sr, gr
    return derivatives


def band_energy(g: np.ndarray) -> float:
    mask = (FREQUENCIES_HZ >= 0.3) & (FREQUENCIES_HZ <= 0.5)
    projected = np.einsum("ab,fbc->fac", T_D, g[mask])
    density = np.sum(np.abs(projected) ** 2, axis=(1, 2))
    return float(np.trapezoid(density, FREQUENCIES_HZ[mask]))


def band_energy_derivative(g: np.ndarray, gr: np.ndarray) -> float:
    mask = (FREQUENCIES_HZ >= 0.3) & (FREQUENCIES_HZ <= 0.5)
    p = np.einsum("ab,fbc->fac", T_D, g[mask])
    pr = np.einsum("ab,fbc->fac", T_D, gr[mask])
    density = 2.0 * np.real(np.sum(np.conj(p) * pr, axis=(1, 2)))
    return float(np.trapezoid(density, FREQUENCIES_HZ[mask]))


__all__ = [
    "DT", "FREQUENCIES_HZ", "H_STEPS", "band_energy", "band_energy_derivative",
    "build_point", "centered", "derivative_table", "discrepancy", "frequency_derivative",
    "gauge_complement", "point_id", "point_specs", "reduce_point", "transfer_arrays",
    "window_energy", "zoh_frechet",
]
