"""R281 eigenvalue mechanism sweep (Q-0042).

Frozen contracts (memory/rounds/R281/plan.md):
- plant: AndesMultiVSGEnvV4._build_system() as-is (R279/R280 frozen V4 build).
- M_i(q) = 200 + 600*(0.25 + q*pattern_i), pattern [1,1,-1,-1] over VSG
  buses [12,16] (area1) and [14,15] (area2); D frozen at build value.
- q grid: 9 points in [-0.25, +0.25]; inter-area mode = electromechanical
  mode in [0.2, 1.5] Hz maximizing |P_area1 - P_area2| via omega-state
  participation factors.
- development-only heterogeneity probe: scale executed M vector by s=M0/200,
  M0 in {100, 200, 300}, q in {0, +/-0.25}.

Writes results/r281_eig_mechanism/{summary.json, provenance.json}.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path("/mnt/c/Users/27443/Desktop/andes-rl-kundur")
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "results" / "r281_eig_mechanism"

from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402

Q_GRID = [-0.25, -0.1875, -0.125, -0.0625, 0.0, 0.0625, 0.125, 0.1875, 0.25]
PATTERN = np.asarray([1.0, 1.0, -1.0, -1.0])  # VSG_BUSES [12,16,14,15]
BASELINE_M = 200.0
DM_MAX = 600.0
COMMON = 0.25
F_BAND = (0.2, 1.5)


def build_frozen_plant():
    env = AndesMultiVSGEnvV4()
    ss = env._build_system()
    vsg_pos = [list(ss.GENCLS.idx.v).index(idx) for idx in env.vsg_idx]
    return env, ss, vsg_pos


def executed_m(q: float, scale: float = 1.0) -> np.ndarray:
    return scale * (BASELINE_M + DM_MAX * (COMMON + q * PATTERN))


def machine_state_indices(ss, vsg_pos, env):
    """Omega state indices per machine (amendment 2026-07-29, rule v2)."""
    out = {}
    g_omega_a = list(ss.GENROU.omega.a)
    for p, idx in enumerate(ss.GENROU.idx.v):
        out[f"genrou{int(idx)}"] = g_omega_a[p]
    c_omega_a = list(ss.GENCLS.omega.a)
    c_bus = list(ss.GENCLS.bus.v)
    for p, pos in enumerate(vsg_pos):
        out[f"vsg{int(c_bus[pos])}"] = c_omega_a[pos]
    vsg_set = set(vsg_pos)
    for p in range(len(ss.GENCLS.idx.v)):
        if p not in vsg_set:
            out[f"gencls_bus{int(c_bus[p])}"] = c_omega_a[p]
    return out


def run_eig_at(q: float, scale: float = 1.0):
    env, ss, vsg_pos = build_frozen_plant()
    m_vec = executed_m(q, scale)
    for p, pos in enumerate(vsg_pos):
        ss.GENCLS.M.v[pos] = float(m_vec[p])
    # contract guards (amendment 2026-07-29: G4 contract is M=0.1, D=0)
    g4_pos = list(ss.GENROU.idx.v).index(4)
    guards = {
        "g4_zeroed": bool(abs(ss.GENROU.M.v[g4_pos] - 0.1) < 1e-9
                          and abs(ss.GENROU.D.v[g4_pos]) < 1e-9),
        "zero_sum_total": float(sum(m_vec)),
        "zero_sum_pass": bool(abs(sum(m_vec) - 4 * (BASELINE_M + DM_MAX * COMMON)) < 1e-6),
        "vsg_buses": [int(b) for b in env.VSG_BUSES],
        "m_vector": [float(x) for x in m_vec],
        "d_vector": [float(ss.GENCLS.D.v[pos]) for pos in vsg_pos],
    }
    ok = ss.PFlow.run()
    guards["pflow_converged"] = bool(ok)
    if not ok:
        return {"q": q, "scale": scale, "guards": guards, "modes": [], "identified": None}
    ss.EIG.run()
    ss.EIG.calc_pfactor()
    mu = np.asarray(ss.EIG.mu)
    pf = np.abs(np.asarray(ss.EIG.pfactors))  # (n_states, n_eig)
    mach = machine_state_indices(ss, vsg_pos, env)
    modes = []
    for j, lam in enumerate(mu):
        if lam.real >= 0:
            continue
        f = abs(lam.imag) / (2 * np.pi)
        if not (F_BAND[0] <= f <= F_BAND[1]):
            continue
        zeta = -lam.real / abs(lam)
        modes.append({
            "eig_index": int(j),
            "freq_hz": float(f),
            "damping_ratio": float(zeta),
            "real": float(lam.real),
            "imag": float(lam.imag),
            "p_machines": {k: float(pf[a, j]) for k, a in mach.items()},
        })
    return {"q": q, "scale": scale, "guards": guards, "modes": modes}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    contract = {
        "mapping": "M_i(q)=scale*(200+600*(0.25+q*[1,1,-1,-1]))",
        "q_grid": Q_GRID,
        "f_band_hz": list(F_BAND),
        "mode_rule": "max |P_area1-P_area2| on omega states; area1=GENROU1,2+GENCLS@12,16; area2=GENROU3,4+GENCLS@14,15",
        "beneficial_direction_b": -1,
        "b_source": "mean executed r278_q in first 15 steps, results/r279_formal_evaluation learned arms (144 trajectories), all-negative",
    }
    contract_hash = hashlib.sha256(
        json.dumps(contract, sort_keys=True).encode()).hexdigest()

    results = [run_eig_at(q) for q in Q_GRID]
    dev = [run_eig_at(q, scale=m0 / 200.0)
           for m0 in (100.0, 300.0) for q in (0.0, -0.25, 0.25)]

    summary = {
        "experiment": "r281_eig_mechanism",
        "question": "Q-0042",
        "contract": contract,
        "contract_sha256": contract_hash,
        "main_sweep": results,
        "development_heterogeneity": dev,
    }
    sp = OUT / "summary.json"
    sp.write_text(json.dumps(summary, indent=1))
    prov = {
        "summary_sha256": sha256_file(sp),
        "contract_sha256": contract_hash,
        "env": "AndesMultiVSGEnvV4._build_system() unmodified",
        "runner": "/home/wya/andes_venv/bin/python (WSL), ANDES 2.0.0",
        "note": "env-side R274 slow droop+PI not in DAE (scope limit, plan.md)",
    }
    pp = OUT / "provenance.json"
    pp.write_text(json.dumps(prov, indent=1))

    # console digest (identification is offline, amendment 2026-07-29)
    print("contract_sha256:", contract_hash[:16])
    for r in results:
        g = r["guards"]
        print(f"q={r['q']:+.4f} pflow={g['pflow_converged']} g4z={g['g4_zeroed']} "
              f"zs={g['zero_sum_pass']} modes={len(r['modes'])}")


if __name__ == "__main__":
    main()
