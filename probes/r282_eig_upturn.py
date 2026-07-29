"""R282 U-upturn densification check (R281 follow-up).

Frozen contracts (memory/rounds/R282/plan.md):
- plant/mapping/operating point identical to R281 (contract hash
  11a4800123f48a33); q densification grid {0.2000, 0.2125, 0.2250, 0.2375}
  between the R281-measured endpoints 0.1875 and 0.25.
- Process fix vs R281: conjugate-pair merging and inter-area mode
  identification run IN-SCRIPT (R281 did them offline ad hoc).
- Continuity metrics (pre-registered): participation-vector cosine >= 0.9
  and |df| < 0.05 Hz between adjacent q points (including the two R281
  endpoints read read-only from results/r281_eig_mechanism/summary.json).

Writes results/r282_eig_upturn/{summary.json, provenance.json}.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path("/mnt/c/Users/27443/Desktop/andes-rl-kundur")
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "results" / "r282_eig_upturn"
R281_SUMMARY = ROOT / "results" / "r281_eig_mechanism" / "summary.json"

from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402

Q_GRID = [0.2000, 0.2125, 0.2250, 0.2375]
PATTERN = np.asarray([1.0, 1.0, -1.0, -1.0])  # VSG_BUSES [12,16,14,15]
BASELINE_M = 200.0
DM_MAX = 600.0
COMMON = 0.25
F_BAND = (0.2, 1.5)
AREA1_KEYS = ("genrou1", "genrou2", "vsg12", "vsg16")
AREA2_KEYS = ("genrou3", "genrou4", "vsg14", "vsg15")
COS_MIN = 0.9
DF_MAX = 0.05


def build_frozen_plant():
    env = AndesMultiVSGEnvV4()
    ss = env._build_system()
    vsg_pos = [list(ss.GENCLS.idx.v).index(idx) for idx in env.vsg_idx]
    return env, ss, vsg_pos


def executed_m(q: float) -> np.ndarray:
    return BASELINE_M + DM_MAX * (COMMON + q * PATTERN)


def machine_state_indices(ss, vsg_pos, env):
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


def merge_conjugate_pairs(modes):
    """Merge entries identical in (f, real) within tolerance — amendment rule."""
    modes = sorted(modes, key=lambda m: (m["freq_hz"], m["real"]))
    merged = []
    for m in modes:
        if merged and abs(m["freq_hz"] - merged[-1]["freq_hz"]) < 1e-9 \
                and abs(m["real"] - merged[-1]["real"]) < 1e-9:
            prev = merged[-1]
            for k, v in m["p_machines"].items():
                prev["p_machines"][k] = (prev["p_machines"][k] + v) / 2.0
            prev["damping_ratio"] = (prev["damping_ratio"] + m["damping_ratio"]) / 2.0
        else:
            merged.append({**m, "p_machines": dict(m["p_machines"])})
    return merged


def identify_interarea(modes):
    """Rule v2 (R281 amendment): max |P_area1 - P_area2| on omega participation."""
    best, best_score = None, -1.0
    for m in modes:
        p = m["p_machines"]
        score = abs(sum(p.get(k, 0.0) for k in AREA1_KEYS)
                    - sum(p.get(k, 0.0) for k in AREA2_KEYS))
        if score > best_score:
            best, best_score = m, score
    if best is None:
        return None
    keys = sorted(best["p_machines"])
    return {
        "freq_hz": best["freq_hz"],
        "damping_ratio": best["damping_ratio"],
        "area_contrast": best_score,
        "p_vector": [best["p_machines"][k] for k in keys],
        "p_keys": keys,
    }


def run_eig_at(q: float):
    env, ss, vsg_pos = build_frozen_plant()
    m_vec = executed_m(q)
    for p, pos in enumerate(vsg_pos):
        ss.GENCLS.M.v[pos] = float(m_vec[p])
    g4_pos = list(ss.GENROU.idx.v).index(4)
    guards = {
        "g4_zeroed": bool(abs(ss.GENROU.M.v[g4_pos] - 0.1) < 1e-9
                          and abs(ss.GENROU.D.v[g4_pos]) < 1e-9),
        "zero_sum_pass": bool(abs(sum(m_vec) - 4 * (BASELINE_M + DM_MAX * COMMON)) < 1e-6),
        "m_vector": [float(x) for x in m_vec],
    }
    ok = ss.PFlow.run()
    guards["pflow_converged"] = bool(ok)
    if not ok:
        return {"q": q, "guards": guards, "identified": None, "n_modes_merged": 0}
    ss.EIG.run()
    ss.EIG.calc_pfactor()
    mu = np.asarray(ss.EIG.mu)
    pf = np.abs(np.asarray(ss.EIG.pfactors))
    mach = machine_state_indices(ss, vsg_pos, env)
    modes = []
    for j, lam in enumerate(mu):
        if lam.real >= 0:
            continue
        f = abs(lam.imag) / (2 * np.pi)
        if not (F_BAND[0] <= f <= F_BAND[1]):
            continue
        modes.append({
            "freq_hz": float(f),
            "damping_ratio": float(-lam.real / abs(lam)),
            "real": float(lam.real),
            "p_machines": {k: float(pf[a, j]) for k, a in mach.items()},
        })
    merged = merge_conjugate_pairs(modes)
    return {"q": q, "guards": guards,
            "identified": identify_interarea(merged),
            "n_modes_merged": len(merged)}


def r281_endpoint(q_target: float):
    """Read-only: re-identify the R281 grid point with this script's rule."""
    data = json.loads(R281_SUMMARY.read_text())
    for r in data["main_sweep"]:
        if abs(r["q"] - q_target) < 1e-9:
            merged = merge_conjugate_pairs(r["modes"])
            return identify_interarea(merged)
    raise KeyError(f"R281 grid point {q_target} not found")


def cosine(a, b) -> float:
    a, b = np.asarray(a), np.asarray(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-30))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    contract = {
        "mapping": "M_i(q)=200+600*(0.25+q*[1,1,-1,-1]) (identical to R281)",
        "r281_contract_sha256": "11a4800123f48a33 (cited, not recomputed)",
        "q_grid": Q_GRID,
        "mode_rule": "conjugate-pair merge then max |P_area1-P_area2|, in-script (process fix)",
        "continuity": {"cosine_min": COS_MIN, "df_max_hz": DF_MAX},
    }
    contract_hash = hashlib.sha256(
        json.dumps(contract, sort_keys=True).encode()).hexdigest()

    results = [run_eig_at(q) for q in Q_GRID]

    # continuity chain: R281 0.1875 -> new 4 -> R281 0.25
    chain = [("r281", 0.1875, r281_endpoint(0.1875))]
    chain += [("r282", r["q"], r["identified"]) for r in results]
    chain.append(("r281", 0.25, r281_endpoint(0.25)))
    continuity = []
    for (src0, q0, m0), (src1, q1, m1) in zip(chain, chain[1:]):
        if m0 is None or m1 is None:
            continuity.append({"q_pair": [q0, q1], "status": "identification_failed"})
            continue
        continuity.append({
            "q_pair": [q0, q1],
            "cosine": cosine(m0["p_vector"], m1["p_vector"]),
            "df_hz": abs(m1["freq_hz"] - m0["freq_hz"]),
            "zeta_pair": [m0["damping_ratio"], m1["damping_ratio"]],
            "continuous": bool(cosine(m0["p_vector"], m1["p_vector"]) >= COS_MIN
                               and abs(m1["freq_hz"] - m0["freq_hz"]) < DF_MAX),
        })

    summary = {
        "experiment": "r282_eig_upturn",
        "parent": "R281 (contract hash 11a4800123f48a33)",
        "contract": contract,
        "contract_sha256": contract_hash,
        "chain": [{"source": s, "q": q, "identified": m} for s, q, m in chain],
        "continuity": continuity,
        "runs": results,
    }
    sp = OUT / "summary.json"
    sp.write_text(json.dumps(summary, indent=1))
    prov = {
        "summary_sha256": sha256_file(sp),
        "contract_sha256": contract_hash,
        "env": "AndesMultiVSGEnvV4._build_system() unmodified",
        "runner": "/home/wya/andes_venv/bin/python (WSL), ANDES 2.0.0",
        "r281_input_readonly": str(R281_SUMMARY),
        "r281_input_sha256": sha256_file(R281_SUMMARY),
    }
    (OUT / "provenance.json").write_text(json.dumps(prov, indent=1))

    print("contract_sha256:", contract_hash[:16])
    for s, q, m in chain:
        if m is None:
            print(f"{s} q={q:+.4f} identified=NONE")
        else:
            print(f"{s} q={q:+.4f} f={m['freq_hz']:.4f} zeta={m['damping_ratio']:.5f}")
    for c in continuity:
        print("pair", c["q_pair"], "cont=", c.get("continuous"), c.get("status", ""))


if __name__ == "__main__":
    main()
