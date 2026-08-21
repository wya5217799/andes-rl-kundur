"""R448 — P1.1 ratio-sensitivity two-term decomposition (Object B).

Reuses the R447 closed-loop composition (reduced sampled plant + analytical
bandpass/local-PI + headroom) and adds the d/drho sensitivity of the plant's
reduced discrete state matrix at M/D-perturbed equilibria, to split
d log r_d / d rho into a candidate term and a reference term (advisory P1.1).

Run via the WSL scratch launcher:
    python scripts/andes_scratch.py scripts/run_r448_p1_sensitivity.py rehearse
    python scripts/andes_scratch.py scripts/run_r448_p1_sensitivity.py analyse

Approximation (documented): only d A_d / d rho is folded through the loop;
the input/output matrix sensitivities (d B / d rho, d C / d rho) are second
order and omitted. rho is the log-perturbation (multiplicative) matching the
relaxed/stiff M/D blocks.
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
OUT = ROOT / "results" / "research_loop" / "r448_p1_sensitivity"
N_AGENTS = 4
DT = 0.2
BANDPASS_COEF = dict(f0_hz=0.4, zeta=0.35, dt=0.2, gain=3.5)
LOCAL_PI = dict(kp_n_per_hz=4.0, ki_n_per_hz_s=0.8)
DELTA = 0.01
T_D = np.array([[0.5, 0.5, -0.5, -0.5],
                [0.7071067811865475, -0.7071067811865475, 0.0, 0.0],
                [0.0, 0.0, 0.7071067811865475, -0.7071067811865475]])


def _build_env(m_scale=1.0, d_scale=1.0):
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.v4_config import V4Config
    from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv

    base = AndesMultiVSGEnvV4(
        random_disturbance=False, comm_fail_prob=0.0, comm_delay_steps=0,
        config=V4Config(
            vsg_m0=200.0 * m_scale,
            d0_per_agent=tuple(100.0 * d_scale for _ in range(4)),
        ),
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
        env, pq_load_ids=LOAD_IDS, source_fingerprint="R448"
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
    return result.sampled_model


def _headroom():
    from andes_rl_kundur.control.active_power import r272_frozen_bess_contract

    contract = r272_frozen_bess_contract()
    _lower, upper = contract.feasible_power_bounds(
        previous_power_system_pu=np.zeros(4), soc=np.full(4, float(contract.soc_initial)),
        voltage_pu=np.ones(4), dt_seconds=float(DT),
    )
    return np.asarray(upper, dtype=float)


def _bandpass_closed_loop(model, headroom):
    from andes_rl_kundur.control.ring_bandpass_damping import (
        prewarped_bandpass_coefficients,
        ring_incidence,
    )

    num, den = prewarped_bandpass_coefficients(**BANDPASS_COEF)
    b0, b1, b2 = float(num[0]), float(num[1]), float(num[2])
    a1, a2 = float(den[1]), float(den[2])
    bring = ring_incidence(N_AGENTS)
    bt = bring.T
    A_d = model.state_matrix
    Bc = model.input_matrix[:, :4] @ np.diag(headroom)
    Bd = model.input_matrix[:, 4:]
    Cw = model.output_matrix
    n_x = A_d.shape[0]
    A11 = A_d - b0 * (Bc @ bring @ bt @ Cw)
    A12 = -(Bc @ bring)
    A21 = (b1 - a1 * b0) * (bt @ Cw)
    A31 = (b2 - a2 * b0) * (bt @ Cw)
    Acl = np.block([[A11, A12, np.zeros((n_x, 4))],
                    [A21, -a1 * np.eye(4), np.eye(4)],
                    [A31, -a2 * np.eye(4), np.zeros((4, 4))]])
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
    A11 = A_d - kp * (Bc @ Cw)
    A12 = Bc
    A21 = -ki * dt * Cw
    Acl = np.block([[A11, A12], [A21, np.eye(4)]])
    Bcl = np.vstack([Bd, np.zeros((4, 3))])
    Ccl = np.hstack([Cw, np.zeros((4, 4))])
    return Acl, Bcl, Ccl


def _term(Acl, Bcl, Ccl, dA_plant, dt, freqs, band_idx):
    """2 Re <G, dG> / ||G||^2 over the band, with dG = C (zI-A)^-1 dA (zI-A)^-1 B."""
    n = Acl.shape[0]
    num = 0.0
    den = 0.0
    dA = np.zeros_like(Acl)
    dA[:dA_plant.shape[0], :dA_plant.shape[1]] = dA_plant
    for i in band_idx:
        w = freqs[i]
        z = np.exp(1j * w * DT)
        zi = np.linalg.solve(z * np.eye(n) - Acl, Bcl)          # (n, 3)
        g = Ccl @ zi                                            # (4, 3)
        dg = Ccl @ np.linalg.solve(z * np.eye(n) - Acl, dA @ zi)  # (4, 3)
        gd = T_D @ g                                            # (3, 3) differential
        dgd = T_D @ dg
        for j in range(3):
            den += float(np.real(np.vdot(gd[:, j], gd[:, j])))
            num += float(np.real(np.vdot(gd[:, j], dgd[:, j])))
    return num, den


def rehearse() -> int:
    env = _build_env()
    try:
        model = _source_model(env)
        h = _headroom()
        A_k, B_k, C_k = _bandpass_closed_loop(model, h)
        A_l, B_l, C_l = _local_pi_closed_loop(model, h)
        print(json.dumps({
            "rehearse_ok": True,
            "state_dim": int(model.state_matrix.shape[0]),
            "bandpass_cl_dim": int(A_k.shape[0]),
            "local_cl_dim": int(A_l.shape[0]),
            "headroom": [float(v) for v in h],
        }, indent=2))
        return 0
    finally:
        env.close()


def analyse() -> int:
    # nominal + M/D perturbed models
    model_n = _source_model(_build_env(1.0, 1.0))
    model_mp = _source_model(_build_env(1.0 + DELTA, 1.0))
    model_mm = _source_model(_build_env(1.0 - DELTA, 1.0))
    model_dp = _source_model(_build_env(1.0, 1.0 + DELTA))
    model_dm = _source_model(_build_env(1.0, 1.0 - DELTA))
    dA_dM = (model_mp.state_matrix - model_mm.state_matrix) / (2.0 * DELTA)
    dA_dD = (model_dp.state_matrix - model_dm.state_matrix) / (2.0 * DELTA)

    h = _headroom()
    A_k, B_k, C_k = _bandpass_closed_loop(model_n, h)
    A_l, B_l, C_l = _local_pi_closed_loop(model_n, h)
    freqs = 2 * np.pi * np.linspace(0.05, 2.0, 400)
    band_idx = [i for i, f in enumerate(freqs) if 0.3 <= f / (2 * np.pi) <= 0.5]

    results = {}
    for rho_name, dA in (("logM", dA_dM), ("logD", dA_dD)):
        num_k, den_k = _term(A_k, B_k, C_k, dA, DT, freqs, band_idx)
        num_l, den_l = _term(A_l, B_l, C_l, dA, DT, freqs, band_idx)
        cand = 2.0 * num_k / den_k if den_k > 0 else float("inf")
        ref = -2.0 * num_l / den_l if den_l > 0 else float("inf")
        results[rho_name] = {
            "candidate_term": float(cand),
            "reference_term": float(ref),
            "abs_ratio": float(abs(cand) / abs(ref)) if abs(ref) > 0 else float("inf"),
        }

    verdicts = {}
    for rho_name, r in results.items():
        ratio = r["abs_ratio"]
        if not np.isfinite(ratio):
            verdicts[rho_name] = "CANARY-INVALID"
        elif ratio > 3.0:
            verdicts[rho_name] = "CANDIDATE-DOMINANT" if abs(r["candidate_term"]) > abs(r["reference_term"]) else "REFERENCE-DOMINANT"
        else:
            verdicts[rho_name] = "MIXED"

    payload = {
        "schema_version": 1,
        "round": "R448",
        "delta": DELTA,
        "rho": "log-perturbation of M and D",
        "results": results,
        "verdicts": verdicts,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    (OUT / "formal_analysis.json").write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    (OUT / "formal_analysis.json.sha256").write_text(f"{digest}  formal_analysis.json\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"sha256={digest}")
    return 0


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
