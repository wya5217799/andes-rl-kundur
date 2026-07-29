"""R283 grid-strength sweep (Q-0043).

Frozen contracts (memory/rounds/R283/plan.md):
- plant/mapping identical to R281/R282 (AndesMultiVSGEnvV4._build_system()
  as-is; M_i(q)=200+600*(0.25+q*[1,1,-1,-1])); no env code changes.
- Axis A (inertia strength): executed M scaled by s=M0/200,
  M0 in {100,150,200,250,300} x q in {0,-0.25,+0.25} (15 points).
- Axis B (electrical strength, declared SCR proxy): r and x of the 7<->8
  tie corridor (Line_4/5/6) scaled by k in {1.0,1.5,2.0} (constant r/x,
  charging b untouched) x q in {0,-0.25,+0.25} (9 points); PFlow re-run at
  each k (linearization at the new operating point).
- Identification: R282 in-script rule (merge conjugate pairs, then max
  |P_area1-P_area2|), no retuning; failures flagged, point excluded.
- Sensitivity per level: S = |zeta(+0.25)-zeta(-0.25)|/|zeta(0)| (R281 span).
- Anchors: M0=200 row and k=1.0 row must reproduce the R281 anchor
  (re-identified read-only from results/r281_eig_mechanism/summary.json)
  within |dzeta| < 1e-6, else contract drift -> INVALID.

Writes results/r283_strength_sweep/{summary.json, provenance.json}.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path("/mnt/c/Users/27443/Desktop/andes-rl-kundur")
sys.path.insert(0, str(ROOT / "probes"))
OUT = ROOT / "results" / "r283_strength_sweep"
R281_SUMMARY = ROOT / "results" / "r281_eig_mechanism" / "summary.json"

from eig_alloc_common import (  # noqa: E402
    TIE_IDX,
    identify_interarea,
    merge_conjugate_pairs,
    run_eig_at,
    sha256_file,
)

AXIS_A_M0 = [100.0, 150.0, 200.0, 250.0, 300.0]
AXIS_B_K = [1.0, 1.5, 2.0]
Q_SUBSET = [-0.25, 0.0, 0.25]
ANCHOR_TOL = 1e-6


def r281_anchor():
    """Read-only: re-identify R281 q in {0, +/-0.25} with this rule."""
    data = json.loads(R281_SUMMARY.read_text())
    out = {}
    for r in data["main_sweep"]:
        q = r["q"]
        if any(abs(q - t) < 1e-9 for t in Q_SUBSET):
            out[q] = identify_interarea(merge_conjugate_pairs(r["modes"]))
    if len(out) != 3:
        raise KeyError(f"R281 anchor points incomplete: {sorted(out)}")
    return out


def sensitivity(runs):
    """S = |zeta(+0.25)-zeta(-0.25)|/|zeta(0)|; None if any point missing."""
    zeta = {}
    for r in runs:
        if r["identified"] is None:
            return None
        zeta[r["q"]] = r["identified"]["damping_ratio"]
    return abs(zeta[0.25] - zeta[-0.25]) / abs(zeta[0.0])


def anchor_check(runs, anchor):
    """All three q points identified and within ANCHOR_TOL of R281."""
    detail = []
    ok = True
    for r in runs:
        a = anchor[r["q"]]
        got = None if r["identified"] is None else r["identified"]["damping_ratio"]
        match = bool(got is not None and abs(got - a["damping_ratio"]) < ANCHOR_TOL)
        ok = ok and match
        detail.append({"q": r["q"], "r283_zeta": got,
                       "r281_zeta": a["damping_ratio"], "match": match})
    return ok, detail


def guard_pass(r):
    g = r["guards"]
    return bool(g["g4_zeroed"] and g["zero_sum_pass"] and g["pflow_converged"])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    contract = {
        "mapping": "M_i(q)=scale*(200+600*(0.25+q*[1,1,-1,-1])) (R281 identical at scale=1)",
        "axis_a": {"name": "inertia strength", "m0": AXIS_A_M0, "scale": "M0/200",
                   "q": Q_SUBSET, "zero_sum_total_per_level": "1400*(M0/200)"},
        "axis_b": {"name": "electrical strength (declared SCR proxy)",
                   "tie_lines": list(TIE_IDX), "k": AXIS_B_K,
                   "scale_what": "r and x by k (constant r/x; charging b untouched)",
                   "q": Q_SUBSET, "operating_point": "PFlow re-run per k"},
        "mode_rule": "R282 in-script: conjugate-pair merge then max |P_area1-P_area2|",
        "sensitivity": "S = |zeta(+0.25)-zeta(-0.25)|/|zeta(0)| per level",
        "anchor": {"source": "results/r281_eig_mechanism/summary.json (read-only)",
                   "rows": ["axis A M0=200", "axis B k=1.0"], "tol_abs_dzeta": ANCHOR_TOL},
    }
    contract_hash = hashlib.sha256(
        json.dumps(contract, sort_keys=True).encode()).hexdigest()

    anchor = r281_anchor()

    axis_a, axis_b = [], []
    for m0 in AXIS_A_M0:
        runs = [run_eig_at(q, scale=m0 / 200.0) for q in Q_SUBSET]
        axis_a.append({"m0": m0, "runs": runs, "sensitivity": sensitivity(runs),
                       "guards_all_pass": all(guard_pass(r) for r in runs)})
    for k in AXIS_B_K:
        runs = [run_eig_at(q, tie_k=k) for q in Q_SUBSET]
        axis_b.append({"k": k, "runs": runs, "sensitivity": sensitivity(runs),
                       "guards_all_pass": all(guard_pass(r) for r in runs)})

    a200 = next(e for e in axis_a if e["m0"] == 200.0)
    b10 = next(e for e in axis_b if e["k"] == 1.0)
    a_ok, a_detail = anchor_check(a200["runs"], anchor)
    b_ok, b_detail = anchor_check(b10["runs"], anchor)

    summary = {
        "experiment": "r283_strength_sweep",
        "question": "Q-0043",
        "contract": contract,
        "contract_sha256": contract_hash,
        "r281_anchor": {str(q): m for q, m in sorted(anchor.items())},
        "anchor_checks": {"axis_a_m0_200": {"pass": a_ok, "detail": a_detail},
                          "axis_b_k_1.0": {"pass": b_ok, "detail": b_detail}},
        "axis_a": axis_a,
        "axis_b": axis_b,
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
        "shared_module": "probes/eig_alloc_common.py",
    }
    (OUT / "provenance.json").write_text(json.dumps(prov, indent=1))

    print("contract_sha256:", contract_hash[:16])
    print("anchor A(M0=200) pass:", a_ok, " anchor B(k=1.0) pass:", b_ok)
    for e in axis_a:
        zs = [None if r["identified"] is None else r["identified"]["damping_ratio"]
              for r in e["runs"]]
        print(f"A M0={e['m0']:5.1f} guards={e['guards_all_pass']} "
              f"zeta(-0.25,0,+0.25)={['None' if z is None else f'{z:.5f}' for z in zs]} "
              f"S={e['sensitivity'] if e['sensitivity'] is None else round(e['sensitivity'], 4)}")
    for e in axis_b:
        zs = [None if r["identified"] is None else r["identified"]["damping_ratio"]
              for r in e["runs"]]
        print(f"B k={e['k']:4.1f} guards={e['guards_all_pass']} "
              f"zeta(-0.25,0,+0.25)={['None' if z is None else f'{z:.5f}' for z in zs]} "
              f"S={e['sensitivity'] if e['sensitivity'] is None else round(e['sensitivity'], 4)}")


if __name__ == "__main__":
    main()
