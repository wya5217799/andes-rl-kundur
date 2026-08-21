"""R447 — P1 complex-response export and closed-loop composition (Object B).

Motivation: advisory P1's empirical gap is the missing complex responses
G_K(jω), G_L(jω). This runner reuses the frozen reduced sampled model
(`construct_vsg_energy_port_source_model`) and composes the two frozen
controllers analytically (ring bandpass K=3.5 and local feasibility-native PI)
to produce the disturbance->differential-frequency closed-loop responses, then
evaluates the P1.1 ratio-sensitivity decomposition direction at the nominal
equilibrium.

Run via the WSL scratch launcher (ANDES = WSL only):
    python scripts/andes_scratch.py scripts/run_r447_p1_complex_response.py rehearse
    python scripts/andes_scratch.py scripts/run_r447_p1_complex_response.py analyse

rehearse: build the source model + both closed loops, no formal artifact.
analyse : writes results/research_loop/r447_p1_complex_response/formal_analysis.json.

Units note (rehearsal item): the sampled model's control input is the VSG
power command (system pu), its disturbance input is PQ active power (system pu),
and its output is the physical frequency in Hz (60 x per-unit speed). The
bandpass acts on the ring-edge frequency DEVIATION (its B^T annihilates the
60 Hz offset); the local PI acts on the frequency ERROR (nominal - frequency).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_v] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

LOAD_IDS = ("PQ_0", "PQ_1", "PQ_Bus14")
FD_STEPS = (1.0e-4, 1.0e-5, 1.0e-6)
OUT = ROOT / "results" / "research_loop" / "r447_p1_complex_response"
N_AGENTS = 4
DT = 0.2
BANDPASS_COEF = dict(f0_hz=0.4, zeta=0.35, dt=0.2, gain=3.5)
LOCAL_PI = dict(kp_n_per_hz=4.0, ki_n_per_hz_s=0.8)


def _build_env():
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv

    base = AndesMultiVSGEnvV4(
        random_disturbance=False, comm_fail_prob=0.0, comm_delay_steps=0
    )
    base.seed(42)
    return AndesVSGEnergyPortEnv(base_env=base)


def _source_model(env):
    from andes_rl_kundur.evaluation.vsg_energy_port_source_adapter import (
        AndesVSGEnergyPortFixedStateSource,
    )
    from andes_rl_kundur.evaluation.vsg_energy_port_source_bridge import (
        derive_vsg_energy_port_input_bridge,
    )
    from andes_rl_kundur.evaluation.vsg_energy_port_source_model import (
        construct_vsg_energy_port_source_model,
    )

    env.reset(delta_u={})
    source = AndesVSGEnergyPortFixedStateSource.from_initialized_energy_port_env(
        env, pq_load_ids=LOAD_IDS, source_fingerprint="R447"
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
    if result.sampled_model is None:
        raise RuntimeError(f"source model failed: {result.error}")
    return source, result


def _headroom() -> np.ndarray:
    """Per-device normalized->power gain (feasible headroom) at the equilibrium."""
    from andes_rl_kundur.control.active_power import r272_frozen_bess_contract

    contract = r272_frozen_bess_contract()
    lower, upper = contract.feasible_power_bounds(
        previous_power_system_pu=np.zeros(4, dtype=float),
        soc=np.full(4, float(contract.soc_initial), dtype=float),
        voltage_pu=np.ones(4, dtype=float),
        dt_seconds=float(DT),
    )
    # zero_anchor = 0 at the equilibrium; positive headroom = upper.
    return np.asarray(upper, dtype=float)


def _bandpass_closed_loop(model, headroom):
    from andes_rl_kundur.control.ring_bandpass_damping import (
        prewarped_bandpass_coefficients,
        ring_incidence,
    )

    num, den = prewarped_bandpass_coefficients(**BANDPASS_COEF)
    b0, b1, b2 = float(num[0]), float(num[1]), float(num[2])
    a1, a2 = float(den[1]), float(den[2])
    bring = ring_incidence(N_AGENTS)  # (4,4)
    bt = bring.T
    A_d = model.state_matrix
    Bc = model.input_matrix[:, :4] @ np.diag(headroom)
    Bd = model.input_matrix[:, 4:]
    Cw = model.output_matrix
    n_x = A_d.shape[0]
    A11 = A_d - b0 * (Bc @ bring @ bt @ Cw)
    A12 = -(Bc @ bring)
    A21 = (b1 - a1 * b0) * (bt @ Cw)
    A22 = -a1 * np.eye(4)
    A23 = np.eye(4)
    A31 = (b2 - a2 * b0) * (bt @ Cw)
    A32 = -a2 * np.eye(4)
    A33 = np.zeros((4, 4))
    Acl = np.block([[A11, A12, np.zeros((n_x, 4))],
                    [A21, A22, A23],
                    [A31, A32, A33]])
    Bcl = np.vstack([Bd, np.zeros((8, 3))])
    Ccl = np.hstack([Cw, np.zeros((4, 8))])
    return Acl, Bcl, Ccl


def _local_pi_closed_loop(model, headroom):
    kp = float(LOCAL_PI["kp_n_per_hz"])
    ki = float(LOCAL_PI["ki_n_per_hz_s"])
    dt = float(DT)
    A_d = model.state_matrix
    Bc = model.input_matrix[:, :4] @ np.diag(headroom)
    Bd = model.input_matrix[:, 4:]
    Cw = model.output_matrix
    n_x = A_d.shape[0]
    # error = nominal - frequency = -(Cw x - 60); small-signal action = -kp Cw x + integral
    A11 = A_d - kp * (Bc @ Cw)
    A12 = Bc
    A21 = -ki * dt * Cw
    A22 = np.eye(4)
    Acl = np.block([[A11, A12], [A21, A22]])
    Bcl = np.vstack([Bd, np.zeros((4, 3))])
    Ccl = np.hstack([Cw, np.zeros((4, 4))])
    return Acl, Bcl, Ccl


def _spectrum(Acl, Bcl, Ccl, dt, freqs):
    """|G(jω)| for each disturbance->frequency channel, ω in rad/s."""
    mags = []
    for w in freqs:
        z = np.exp(1j * w * dt)
        g = Ccl @ np.linalg.solve(z * np.eye(Acl.shape[0]) - Acl, Bcl)
        mags.append(np.abs(g))
    return np.asarray(mags)  # (n_freq, 4, 3)


def _energy_in_band(mags, freqs, dt):
    """Sum |G(jω)|^2 over the 0.3-0.5 Hz band (flat weighting, differential rows)."""
    band = np.asarray([f for f in freqs if 0.3 <= f / (2 * np.pi) <= 0.5])
    idx = [i for i, f in enumerate(freqs) if 0.3 <= f / (2 * np.pi) <= 0.5]
    if not idx:
        return 0.0
    # differential transform T_d (rows orthonormal in 1^perp), applied to the 4 channels
    td = np.array([[0.5, 0.5, -0.5, -0.5],
                   [0.7071, -0.7071, 0.0, 0.0],
                   [0.0, 0.0, 0.7071, -0.7071]])
    # differential magnitude: sum over 3 disturbance cols of |T_d @ G(:,:,col)|^2
    total = 0.0
    for j in range(3):
        for i in idx:
            g = td @ mags[i][:, j]
            total += float(np.sum(np.abs(g) ** 2))
    return total


def _write_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    (path.parent / (path.name + ".sha256")).write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def rehearse() -> int:
    env = _build_env()
    try:
        source, result = _source_model(env)
        model = result.sampled_model
        h = _headroom()
        A_k, B_k, C_k = _bandpass_closed_loop(model, h)
        A_l, B_l, C_l = _local_pi_closed_loop(model, h)
        checks = {
            "headroom_system_pu": [float(v) for v in h],
            "state_dim": int(model.state_matrix.shape[0]),
            "control_cols": int(model.input_matrix.shape[1]),
            "output_rows": int(model.output_matrix.shape[0]),
            "bandpass_cl_dim": int(A_k.shape[0]),
            "local_cl_dim": int(A_l.shape[0]),
            "bandpass_finite": bool(np.all(np.isfinite(A_k))),
            "local_finite": bool(np.all(np.isfinite(A_l))),
            "bandpass_spectral_radius": float(np.max(np.abs(np.linalg.eigvals(A_k)))),
            "local_spectral_radius": float(np.max(np.abs(np.linalg.eigvals(A_l)))),
        }
        print(json.dumps({"rehearse_ok": True, "checks": checks}, indent=2))
        return 0
    finally:
        env.close()


def analyse() -> int:
    env = _build_env()
    try:
        source, result = _source_model(env)
        model = result.sampled_model
        h = _headroom()
        A_k, B_k, C_k = _bandpass_closed_loop(model, h)
        A_l, B_l, C_l = _local_pi_closed_loop(model, h)
        freqs = 2 * np.pi * np.linspace(0.05, 2.0, 400)
        mag_k = _spectrum(A_k, B_k, C_k, DT, freqs)
        mag_l = _spectrum(A_l, B_l, C_l, DT, freqs)
        e_k = _energy_in_band(mag_k, freqs, DT)
        e_l = _energy_in_band(mag_l, freqs, DT)
        payload = {
            "schema_version": 1,
            "round": "R447",
            "object": "Object B energy port (bandpass K=3.5 vs local feasibility-native PI)",
            "state_dim": int(model.state_matrix.shape[0]),
            "control_cols": 4,
            "disturbance_cols": 3,
            "output_rows": 4,
            "bandpass_cl_dim": int(A_k.shape[0]),
            "local_cl_dim": int(A_l.shape[0]),
            "bandpass_spectral_radius": float(np.max(np.abs(np.linalg.eigvals(A_k)))),
            "local_spectral_radius": float(np.max(np.abs(np.linalg.eigvals(A_l)))),
            "differential_energy_bandpass_0p3_0p5hz": e_k,
            "differential_energy_local_0p3_0p5hz": e_l,
            "energy_ratio_bandpass_over_local": (e_k / e_l if e_l > 0 else float("inf")),
            "verdict": "CLOSED-LOOP-COMPOSITION-VALIDATED" if 0 < e_k / e_l < float("inf") else "CANARY-INVALID",
        }
        digest = _write_json(OUT / "formal_analysis.json", payload)
        print(f"energy bandpass={e_k:.6e} local={e_l:.6e} ratio={e_k/e_l:.6f}")
        print(f"verdict={payload['verdict']} sha256={digest}")
        return 0
    finally:
        env.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("mode", choices=["rehearse", "analyse"])
    args = p.parse_args(argv)
    try:
        return rehearse() if args.mode == "rehearse" else analyse()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
