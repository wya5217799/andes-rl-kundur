"""Complete local physical-parameter tensors and finite-horizon lifts for U7."""

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
PARAMETER_NAMES = tuple([f"M_{i}" for i in range(1, 5)] + [f"D_{i}" for i in range(1, 5)])
BASE_STEPS = np.asarray([4.0] * 4 + [1.0] * 4, dtype=float)
LEVELS = (1.0, 0.5, 0.25)


def _digest_array(value: np.ndarray) -> str:
    value = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode())
    digest.update(np.asarray(value.shape, dtype=np.int64).tobytes())
    digest.update(value.tobytes())
    return digest.hexdigest()


def point_specs() -> list[tuple[int, float]]:
    return [(-1, 0.0)] + [
        (parameter, sign * float(BASE_STEPS[parameter]) * level)
        for parameter in range(8)
        for level in LEVELS
        for sign in (-1.0, 1.0)
    ]


def point_id(parameter: int, delta: float) -> str:
    if parameter < 0:
        return "nominal"
    sign = "p" if delta > 0 else "m"
    return f"{PARAMETER_NAMES[parameter]}_{sign}{abs(delta):.6f}".replace(".", "p")


def build_point(parameter: int, delta: float) -> dict[str, Any]:
    """Build one complete Object-A equilibrium and joint-input linear model."""

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

    base = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0, comm_delay_steps=0)
    base.seed(42)
    env = AndesVSGEnergyPortEnv(base_env=base)
    try:
        env.reset(delta_u={})
        ss = base.ss
        positions = list(base._vsg_pos)
        ids = list(base.vsg_idx)
        m_values = np.asarray([ss.GENCLS.M.v[pos] for pos in positions], dtype=float)
        d_values = np.asarray([ss.GENCLS.D.v[pos] for pos in positions], dtype=float)
        if parameter >= 0:
            if parameter < 4:
                m_values[parameter] += float(delta)
            else:
                d_values[parameter - 4] += float(delta)
        for index, device_id in enumerate(ids):
            ss.GENCLS.set("M", device_id, float(m_values[index]), attr="v")
            ss.GENCLS.set("D", device_id, float(d_values[index]), attr="v")
        models = ss.exist.pflow_tds
        ss.TDS.fg_update(models=models)
        ss.j_update(models=models, info=f"R468 {point_id(parameter, delta)}")

        source = AndesVSGEnergyPortFixedStateSource.from_initialized_energy_port_env(
            env, pq_load_ids=LOAD_IDS, source_fingerprint=f"R468:{point_id(parameter, delta)}"
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
            "dynamic_state_indices": np.asarray(folded.dynamic_state_indices),
            "equilibrium_z": np.asarray(snap.equilibrium_z),
            "equilibrium_f": np.asarray(snap.equilibrium_f),
            "equilibrium_g": np.asarray(snap.equilibrium_g),
            "omega_state_addresses": np.asarray(snap.omega_state_addresses),
        }
        names = {
            "state_names": list(snap.state_names),
            "algebraic_names": list(snap.algebraic_names),
            "dynamic_state_names": list(result.dynamic_state_names),
        }
        return {
            "parameter": int(parameter),
            "parameter_name": "nominal" if parameter < 0 else PARAMETER_NAMES[parameter],
            "delta": float(delta),
            "point_id": point_id(parameter, delta),
            "M_values": m_values,
            "D_values": d_values,
            "arrays": arrays,
            "names": names,
            "name_hash": hashlib.sha256(json.dumps(names, sort_keys=True).encode()).hexdigest(),
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
    vector = np.real(vectors[:, index])
    vector /= np.linalg.norm(vector)
    complement = la.null_space(vector.reshape(1, -1))
    return complement, {
        "gauge_eigenvalue_real": float(np.real(values[index])),
        "gauge_eigenvalue_imag": float(np.imag(values[index])),
        "right_residual": float(np.linalg.norm(a @ vector - values[index] * vector)),
        "output_norm": float(np.linalg.norm(c @ vector)),
    }


def quotient_arrays(point: dict[str, Any], complement: np.ndarray) -> dict[str, np.ndarray]:
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


def derivative_levels(
    points: dict[tuple[int, float], dict[str, np.ndarray]], key: str
) -> np.ndarray:
    rows = []
    for parameter in range(8):
        estimates = []
        for level in LEVELS:
            h = float(BASE_STEPS[parameter] * level)
            estimates.append(
                (points[(parameter, h)][key] - points[(parameter, -h)][key]) / (2.0 * h)
            )
        rows.append(np.stack(estimates))
    return np.stack(rows)


def convergence(levels: np.ndarray) -> list[dict[str, float | bool]]:
    rows: list[dict[str, float | bool]] = []
    for parameter in range(levels.shape[0]):
        fine = levels[parameter, 2]
        middle = levels[parameter, 1]
        absolute = float(np.max(np.abs(fine - middle)))
        relative = float(np.linalg.norm(fine - middle) / max(np.linalg.norm(fine), 1.0e-15))
        rows.append(
            {
                "max_abs_h2_minus_h4": absolute,
                "relative_h2_minus_h4": relative,
                "near_zero": bool(np.linalg.norm(fine) <= 1.0e-9),
                "passed": bool(relative <= 0.01 or absolute <= 1.0e-9),
            }
        )
    return rows


def additive_lift(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray) -> np.ndarray:
    """Map 30 held differential commands to 30 end-of-interval outputs."""

    q = la.null_space(np.ones((1, 4)))
    bd = b[:, :4] @ q
    dd = d[:, :4] @ q
    yd = q.T
    blocks = np.zeros((HORIZON * 3, HORIZON * 3), dtype=float)
    powers = [np.eye(a.shape[0])]
    for _ in range(HORIZON):
        powers.append(powers[-1] @ a)
    for row in range(HORIZON):
        for column in range(row + 1):
            if row == column:
                block = yd @ dd
            else:
                block = yd @ c @ powers[row - column - 1] @ bd
            blocks[row * 3 : (row + 1) * 3, column * 3 : (column + 1) * 3] = block
    return blocks


def bilinear_lift(
    a: np.ndarray,
    c: np.ndarray,
    n_tensor: np.ndarray,
    e_tensor: np.ndarray,
    r_tensor: np.ndarray,
    s_tensor: np.ndarray,
) -> np.ndarray:
    """Map independent products [q_j*x, q_j*r] at each step to output."""

    drive = np.concatenate([n_tensor.reshape(8, a.shape[0], -1), e_tensor], axis=2)
    direct = np.concatenate([r_tensor.reshape(8, c.shape[0], -1), s_tensor], axis=2)
    drive = np.transpose(drive, (1, 0, 2)).reshape(a.shape[0], -1)
    direct = np.transpose(direct, (1, 0, 2)).reshape(c.shape[0], -1)
    width = drive.shape[1]
    result = np.zeros((HORIZON * c.shape[0], HORIZON * width), dtype=float)
    powers = [np.eye(a.shape[0])]
    for _ in range(HORIZON):
        powers.append(powers[-1] @ a)
    for row in range(HORIZON):
        for column in range(row + 1):
            block = direct if row == column else c @ powers[row - column - 1] @ drive
            result[
                row * c.shape[0] : (row + 1) * c.shape[0], column * width : (column + 1) * width
            ] = block
    return result


__all__ = [
    "BASE_STEPS",
    "DT",
    "HORIZON",
    "LEVELS",
    "PARAMETER_NAMES",
    "additive_lift",
    "bilinear_lift",
    "build_point",
    "convergence",
    "derivative_levels",
    "gauge_complement",
    "point_id",
    "point_specs",
    "quotient_arrays",
]
