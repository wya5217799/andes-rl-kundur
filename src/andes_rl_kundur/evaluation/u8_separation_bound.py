"""Input/output separation and effective-stiffness bounds for U8."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np
import scipy.linalg as la
from scipy.signal import cont2discrete

DT = 0.2
HORIZON = 30
LOAD_IDS = ("PQ_0", "PQ_1", "PQ_Bus14")
ALPHAS = (0.0, 0.25, 0.5, 1.0)
FREQUENCIES_HZ = np.linspace(0.0, 1.0 / (2.0 * DT), 1025)
Q_C = np.ones(4, dtype=float) / 2.0
T_D = np.asarray(
    [
        [0.5, 0.5, -0.5, -0.5],
        [2**-0.5, -(2**-0.5), 0.0, 0.0],
        [0.0, 0.0, 2**-0.5, -(2**-0.5)],
    ],
    dtype=float,
)


def _digest_array(value: np.ndarray) -> str:
    value = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode())
    digest.update(np.asarray(value.shape, dtype=np.int64).tobytes())
    digest.update(value.tobytes())
    return digest.hexdigest()


def scaled_values(values: np.ndarray, alpha: float) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    return np.full_like(values, np.mean(values)) + float(alpha) * (values - np.mean(values))


def point_id(profile_id: str, alpha: float) -> str:
    return f"{profile_id}_alpha_{alpha:.2f}".replace(".", "p")


def build_point(
    profile_id: str, m_values: np.ndarray, d_values: np.ndarray, alpha: float
) -> dict[str, Any]:
    """Build one complete joint-input model for a scaled R405 M/D profile."""

    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv
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

    m_scaled = scaled_values(m_values, alpha)
    d_scaled = scaled_values(d_values, alpha)
    base = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0, comm_delay_steps=0)
    base.seed(42)
    env = AndesVSGEnergyPortEnv(base_env=base)
    try:
        env.reset(delta_u={})
        ss = base.ss
        ids = list(base.vsg_idx)
        for index, device_id in enumerate(ids):
            ss.GENCLS.set("M", device_id, float(m_scaled[index]), attr="v")
            ss.GENCLS.set("D", device_id, float(d_scaled[index]), attr="v")
        models = ss.exist.pflow_tds
        ss.TDS.fg_update(models=models)
        ss.j_update(models=models, info=f"R469 {point_id(profile_id, alpha)}")
        source = AndesVSGEnergyPortFixedStateSource.from_initialized_energy_port_env(
            env, pq_load_ids=LOAD_IDS, source_fingerprint=f"R469:{point_id(profile_id, alpha)}"
        )
        bridges = tuple(
            derive_vsg_energy_port_input_bridge(
                binding=source.binding, source=source, step_system_pu=step
            )
            for step in (1.0e-4, 1.0e-5, 1.0e-6)
        )
        result = construct_vsg_energy_port_source_model(
            snapshot=source.descriptor_snapshot, bridges=bridges
        )
        if not result.passed or result.sampled_model is None:
            raise RuntimeError(f"joint input model failed: {result.error}")
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
        d_cont = np.zeros((4, 7), dtype=float)
        ad, bd, cd, dd, _ = cont2discrete(
            (reduced.state_matrix, reduced.input_matrix, c_cont, d_cont), DT, method="zoh"
        )
        sampled = result.sampled_model
        arrays = {
            "A_continuous": np.asarray(reduced.state_matrix),
            "B_continuous": np.asarray(reduced.input_matrix),
            "C_continuous": np.asarray(c_cont),
            "D_continuous": np.asarray(d_cont),
            "A_pre": np.asarray(ad),
            "B_pre": np.asarray(bd),
            "C_pre": np.asarray(cd),
            "D_pre": np.asarray(dd),
            "A_post": np.asarray(sampled.state_matrix),
            "B_post": np.asarray(sampled.input_matrix),
            "C_post": np.asarray(sampled.output_matrix),
            "D_post": np.asarray(sampled.feedthrough_matrix),
            "equilibrium_z": np.asarray(snap.equilibrium_z),
            "equilibrium_f": np.asarray(snap.equilibrium_f),
            "equilibrium_g": np.asarray(snap.equilibrium_g),
        }
        names = {
            "state_names": list(snap.state_names),
            "algebraic_names": list(snap.algebraic_names),
            "dynamic_state_names": list(result.dynamic_state_names),
        }
        return {
            "profile_id": profile_id,
            "alpha": float(alpha),
            "point_id": point_id(profile_id, alpha),
            "M_values": m_scaled,
            "D_values": d_scaled,
            "arrays": arrays,
            "names": names,
            "name_hash": hashlib.sha256(json.dumps(names, sort_keys=True).encode()).hexdigest(),
            "active_mode_hash": _digest_array(arrays["equilibrium_z"]),
            "equilibrium_max_abs_f": float(np.max(np.abs(arrays["equilibrium_f"]))),
            "equilibrium_max_abs_g": float(np.max(np.abs(arrays["equilibrium_g"]))),
            "algebraic_reciprocal_condition": float(reduced.algebraic_reciprocal_condition),
        }
    finally:
        env.close()


def gauge_complement(point: dict[str, Any]) -> tuple[np.ndarray, dict[str, float]]:
    a = point["arrays"]["A_post"]
    c = point["arrays"]["C_post"]
    values, vectors = la.eig(a)
    index = int(np.argmin(np.abs(values - 1.0)))
    vector = np.real(vectors[:, index])
    vector /= np.linalg.norm(vector)
    complement = la.null_space(vector.reshape(1, -1))
    return complement, {
        "eigenvalue_real": float(np.real(values[index])),
        "eigenvalue_imag": float(np.imag(values[index])),
        "right_residual": float(np.linalg.norm(a @ vector - values[index] * vector)),
        "output_norm": float(np.linalg.norm(c @ vector)),
    }


def quotient(point: dict[str, Any], complement: np.ndarray) -> dict[str, np.ndarray]:
    arrays = point["arrays"]
    return {
        "A_continuous": complement.T @ arrays["A_continuous"] @ complement,
        "B_continuous": complement.T @ arrays["B_continuous"],
        "C_continuous": arrays["C_continuous"] @ complement,
        "D_continuous": arrays["D_continuous"].copy(),
        "A_post": complement.T @ arrays["A_post"] @ complement,
        "B_post": complement.T @ arrays["B_post"],
        "C_post": arrays["C_post"] @ complement,
        "D_post": arrays["D_post"].copy(),
    }


def projectors() -> dict[str, np.ndarray]:
    p = np.outer(Q_C, Q_C)
    return {"P_u": p, "Q_u": np.eye(4) - p, "P_y": p.copy(), "Q_y": np.eye(4) - p}


def projector_checks(values: dict[str, np.ndarray]) -> dict[str, Any]:
    rows = {}
    for name, value in values.items():
        rows[name] = {
            "idempotence": float(np.linalg.norm(value @ value - value)),
            "symmetry": float(np.linalg.norm(value.T - value)),
            "rank": int(np.linalg.matrix_rank(value)),
        }
    rows["basis"] = {
        "qc_norm_error": float(abs(np.linalg.norm(Q_C) - 1.0)),
        "Td_orthonormal_error": float(np.linalg.norm(T_D @ T_D.T - np.eye(3))),
        "common_differential_orthogonality": float(np.linalg.norm(T_D @ Q_C)),
        "completeness": float(np.linalg.norm(np.outer(Q_C, Q_C) + T_D.T @ T_D - np.eye(4))),
    }
    rows["passed"] = bool(
        max(
            item[key]
            for item in rows.values()
            if isinstance(item, dict)
            for key in item
            if key in ("idempotence", "symmetry")
        )
        <= 1.0e-12
        and max(rows["basis"].values()) <= 1.0e-12
        and rows["P_u"]["rank"] == rows["P_y"]["rank"] == 1
        and rows["Q_u"]["rank"] == rows["Q_y"]["rank"] == 3
    )
    return rows


def toeplitz_lift(model: dict[str, np.ndarray]) -> np.ndarray:
    a, b, c, d = (model[key] for key in ("A_post", "B_post", "C_post", "D_post"))
    bc = b[:, :4] @ Q_C.reshape(-1, 1)
    dc = d[:, :4] @ Q_C.reshape(-1, 1)
    result = np.zeros((HORIZON * 3, HORIZON), dtype=float)
    powers = [np.eye(a.shape[0])]
    for _ in range(HORIZON):
        powers.append(powers[-1] @ a)
    for row in range(HORIZON):
        for column in range(row + 1):
            block = T_D @ (dc if row == column else c @ powers[row - column - 1] @ bc)
            result[row * 3 : (row + 1) * 3, column] = block[:, 0]
    return result


def direct_impulse_lift(model: dict[str, np.ndarray]) -> np.ndarray:
    """Independent basis simulation of the held-input observation convention."""

    a, b, c, d = (model[key] for key in ("A_post", "B_post", "C_post", "D_post"))
    result = np.zeros((HORIZON * 3, HORIZON), dtype=float)
    for source_step in range(HORIZON):
        state = np.zeros(a.shape[0], dtype=float)
        for step in range(HORIZON):
            scalar = 1.0 if step == source_step else 0.0
            command = Q_C * scalar
            output = c @ state + d[:, :4] @ command
            result[step * 3 : (step + 1) * 3, source_step] = T_D @ output
            state = a @ state + b[:, :4] @ command
    return result


def frequency_table(model: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    a, b, c, d = (model[key] for key in ("A_post", "B_post", "C_post", "D_post"))
    bc = b[:, :4]
    dc = d[:, :4]
    values = np.empty((len(FREQUENCIES_HZ), 3), dtype=complex)
    conditions = np.empty(len(FREQUENCIES_HZ), dtype=float)
    for index, frequency in enumerate(FREQUENCIES_HZ):
        z = np.exp(2j * np.pi * frequency * DT)
        matrix = z * np.eye(a.shape[0]) - a
        conditions[index] = np.linalg.cond(matrix)
        transfer = c @ la.solve(matrix, bc) + dc
        values[index] = T_D @ transfer @ Q_C
    return {
        "frequency_hz": FREQUENCIES_HZ.copy(),
        "G_dc": values,
        "cross_norm": np.linalg.norm(values, axis=1),
        "resolvent_condition": conditions,
        "epsilon_D": np.full(len(FREQUENCIES_HZ), np.linalg.norm(T_D @ dc @ Q_C)),
    }


def stiffness_table(model: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    a, b, c, d = (
        model[key] for key in ("A_continuous", "B_continuous", "C_continuous", "D_continuous")
    )
    bc = b[:, :4]
    dc = d[:, :4]
    frequencies = FREQUENCIES_HZ[1:]
    count = len(frequencies)
    z_dd = np.empty((count, 3, 3), dtype=complex)
    z_dc = np.empty((count, 3), dtype=complex)
    s_c = np.empty(count, dtype=complex)
    actual = np.empty(count, dtype=float)
    reconstructed = np.empty(count, dtype=float)
    lower = np.empty(count, dtype=float)
    upper = np.empty(count, dtype=float)
    sigma_min_zdd = np.empty(count, dtype=float)
    condition_g = np.empty(count, dtype=float)
    condition_zdd = np.empty(count, dtype=float)
    valid = np.ones(count, dtype=bool)
    transform = np.column_stack([Q_C, T_D.T])
    for index, frequency in enumerate(frequencies):
        s = 2j * np.pi * frequency
        transfer = c @ la.solve(s * np.eye(a.shape[0]) - a, bc) + dc
        condition_g[index] = np.linalg.cond(transfer)
        if not np.isfinite(condition_g[index]) or condition_g[index] > 1.0e12:
            valid[index] = False
            z_dd[index] = np.nan
            z_dc[index] = np.nan
            s_c[index] = np.nan
            actual[index] = np.linalg.norm(T_D @ transfer @ Q_C)
            reconstructed[index] = lower[index] = upper[index] = np.nan
            sigma_min_zdd[index] = condition_zdd[index] = np.nan
            continue
        z = s * la.inv(transfer)
        transformed = transform.T @ z @ transform
        zcc = transformed[0, 0]
        zcd = transformed[0, 1:]
        zdc_value = transformed[1:, 0]
        zdd_value = transformed[1:, 1:]
        condition_zdd[index] = np.linalg.cond(zdd_value)
        sigma_min_zdd[index] = la.svdvals(zdd_value)[-1]
        if not np.isfinite(condition_zdd[index]) or condition_zdd[index] > 1.0e12:
            valid[index] = False
            z_dd[index], z_dc[index] = zdd_value, zdc_value
            s_c[index] = np.nan
            actual[index] = np.linalg.norm(T_D @ transfer @ Q_C)
            reconstructed[index] = lower[index] = upper[index] = np.nan
            continue
        schur = zcc - zcd @ la.solve(zdd_value, zdc_value)
        predicted = -s * la.solve(zdd_value, zdc_value) / schur
        actual_value = T_D @ transfer @ Q_C
        z_dd[index], z_dc[index], s_c[index] = zdd_value, zdc_value, schur
        actual[index] = np.linalg.norm(actual_value)
        reconstructed[index] = np.linalg.norm(predicted - actual_value)
        numerator = abs(s) * np.linalg.norm(zdc_value)
        lower[index] = numerator / (np.linalg.norm(zdd_value) * abs(schur))
        upper[index] = numerator * np.linalg.norm(la.inv(zdd_value)) / abs(schur)
    return {
        "frequency_hz": frequencies,
        "Z_dd": z_dd,
        "z_dc": z_dc,
        "S_c": s_c,
        "b_c": np.ones(count),
        "actual_cross_norm": actual,
        "reconstruction_error": reconstructed,
        "lower_bound": lower,
        "upper_bound": upper,
        "sigma_min_Zdd": sigma_min_zdd,
        "abs_Sc": np.abs(s_c),
        "condition_G": condition_g,
        "condition_Zdd": condition_zdd,
        "valid": valid,
    }


__all__ = [
    "ALPHAS",
    "DT",
    "FREQUENCIES_HZ",
    "HORIZON",
    "Q_C",
    "T_D",
    "build_point",
    "direct_impulse_lift",
    "frequency_table",
    "gauge_complement",
    "point_id",
    "projector_checks",
    "projectors",
    "quotient",
    "scaled_values",
    "stiffness_table",
    "toeplitz_lift",
]
