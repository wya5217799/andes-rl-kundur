"""Shared frozen-plant eigenvalue-allocation probe core (R281/R282/R283).

Motivation: the pattern "build V4 plant -> set executed VSG M (+ optional
tie-corridor scaling) -> guards -> PFlow -> EIG -> conjugate-pair merge ->
inter-area identification" was written three times (r281_eig_sweep.py,
r282_eig_upturn.py, r283_strength_sweep.py). Principle 1 (maintainability):
second-and-later occurrences become a shared module. Historical r281/r282
scripts are NOT retrofitted; new probes import from here.

Usage (WSL only — ANDES is WSL-only per CLAUDE.md):
    import sys
    sys.path.insert(0, "/mnt/c/Users/27443/Desktop/andes-rl-kundur/probes")
    from eig_alloc_common import run_eig_at, identify_interarea

Failure modes: importing andes under Windows python fails; run under
/home/wya/andes_venv/bin/python. PFlow non-convergence returns a run dict
with identified=None and guards["pflow_converged"]=False (no exception).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np

ROOT = Path("/mnt/c/Users/27443/Desktop/andes-rl-kundur")
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402

PATTERN = np.asarray([1.0, 1.0, -1.0, -1.0])  # VSG_BUSES [12,16,14,15]
BASELINE_M = 200.0
DM_MAX = 600.0
COMMON = 0.25
ZERO_SUM_BASE = 4 * (BASELINE_M + DM_MAX * COMMON)  # 1400 at scale=1
F_BAND = (0.2, 1.5)
AREA1_KEYS = ("genrou1", "genrou2", "vsg12", "vsg16")
AREA2_KEYS = ("genrou3", "genrou4", "vsg14", "vsg15")
# R283 SCR proxy: the 7<->8 triple-circuit long tie corridor (x ~ 0.22 each),
# dominant reactance of the inter-area path; 8<->9 pair (x ~ 0.02) untouched.
TIE_IDX = ("Line_4", "Line_5", "Line_6")


def build_frozen_plant():
    env = AndesMultiVSGEnvV4()
    ss = env._build_system()
    vsg_pos = [list(ss.GENCLS.idx.v).index(idx) for idx in env.vsg_idx]
    return env, ss, vsg_pos


def executed_m(q: float, scale: float = 1.0) -> np.ndarray:
    return scale * (BASELINE_M + DM_MAX * (COMMON + q * PATTERN))


def machine_state_indices(ss, vsg_pos, env):
    """Omega state indices per machine (R281 amendment, rule v2)."""
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


def run_eig_at(q: float, scale: float = 1.0, tie_k: float = 1.0,
               keep_modes: bool = False):
    """One frozen-plant EIG point.

    scale: multiplies the whole executed M vector (axis A, M0/200).
    tie_k: multiplies r and x of TIE_IDX lines (axis B, SCR proxy); PFlow is
           re-run afterwards, so linearization is at the new operating point.
    keep_modes: when True, also returns the merged mode list (R285
           attribution recording; default False keeps the R283/R284 return
           shape bit-identical).
    """
    env, ss, vsg_pos = build_frozen_plant()
    m_vec = executed_m(q, scale)
    for p, pos in enumerate(vsg_pos):
        ss.GENCLS.M.v[pos] = float(m_vec[p])
    tie_detail = None
    if abs(tie_k - 1.0) > 1e-12:
        line_idx = list(ss.Line.idx.v)
        tie_detail = {}
        for tidx in TIE_IDX:
            pos = line_idx.index(tidx)
            ss.Line.r.v[pos] = float(ss.Line.r.v[pos] * tie_k)
            ss.Line.x.v[pos] = float(ss.Line.x.v[pos] * tie_k)
            tie_detail[tidx] = {"r": float(ss.Line.r.v[pos]),
                                "x": float(ss.Line.x.v[pos])}
    g4_pos = list(ss.GENROU.idx.v).index(4)
    guards = {
        "g4_zeroed": bool(abs(ss.GENROU.M.v[g4_pos] - 0.1) < 1e-9
                          and abs(ss.GENROU.D.v[g4_pos]) < 1e-9),
        "zero_sum_pass": bool(abs(sum(m_vec) - ZERO_SUM_BASE * scale) < 1e-6),
        "m_vector": [float(x) for x in m_vec],
        "tie_k": float(tie_k),
        "tie_lines": tie_detail,
    }
    ok = ss.PFlow.run()
    guards["pflow_converged"] = bool(ok)
    if not ok:
        return {"q": q, "scale": scale, "tie_k": tie_k, "guards": guards,
                "identified": None, "n_modes_merged": 0,
                **({"modes": []} if keep_modes else {})}
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
    out = {"q": q, "scale": scale, "tie_k": tie_k, "guards": guards,
           "identified": identify_interarea(merged),
           "n_modes_merged": len(merged)}
    if keep_modes:
        out["modes"] = merged
    return out


def cosine(a, b) -> float:
    a, b = np.asarray(a), np.asarray(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-30))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
