"""R285 hybridization-zone map (Q-0044).

Frozen contracts (memory/rounds/R285/plan.md):
- plant/mapping identical to R281-R283; grid M0 in {100,125,150,175} x q in
  {-0.25,-0.125,0,+0.125,+0.25} (20 cells), frozen before the first
  eigenvalue.
- 14 cells newly computed; 6 cells (M0 in {100,150} x q in {-0.25,0,+0.25})
  reused read-only from results/r283_strength_sweep/summary.json; 3 flagged
  R283 cells re-computed with keep_modes=True solely for attribution
  recording and must reproduce R283 identified values within |dzeta| < 1e-6.
- Identification and branch-validity screen unchanged (R282/R283 rule);
  no new mode-tracking rule this round.

Writes results/r285_hybridization_map/{summary.json, provenance.json}.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path("/mnt/c/Users/27443/Desktop/andes-rl-kundur")
sys.path.insert(0, str(ROOT / "probes"))
OUT = ROOT / "results" / "r285_hybridization_map"
R283_SUMMARY = ROOT / "results" / "r283_strength_sweep" / "summary.json"

from eig_alloc_common import run_eig_at, sha256_file  # noqa: E402

M0_LEVELS = [100.0, 125.0, 150.0, 175.0]
Q_GRID = [-0.25, -0.125, 0.0, 0.125, 0.25]
R283_RO_M0 = (100.0, 150.0)
R283_RO_Q = (-0.25, 0.0, 0.25)
ATTR_RERUN = [(100.0, -0.25), (150.0, -0.25), (150.0, 0.25)]
RERUN_TOL = 1e-6


def r283_readonly():
    data = json.loads(R283_SUMMARY.read_text())
    cells = {}
    for e in data["axis_a"]:
        m0 = e["m0"]
        if m0 not in R283_RO_M0:
            continue
        for r in e["runs"]:
            q = r["q"]
            if q in R283_RO_Q:
                cells[(m0, q)] = r["identified"]
    if len(cells) != 6:
        raise KeyError(f"R283 read-only cells incomplete: {sorted(cells)}")
    return cells


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    contract = {
        "mapping": "M_i(q)=scale*(200+600*(0.25+q*[1,1,-1,-1])), scale=M0/200",
        "grid": {"m0": M0_LEVELS, "q": Q_GRID},
        "r283_readonly_cells": [[m0, q] for m0 in R283_RO_M0 for q in R283_RO_Q],
        "attribution_rerun_cells": ATTR_RERUN,
        "rerun_tol_abs_dzeta": RERUN_TOL,
        "mode_rule": "eig_alloc_common unchanged (R282/R283); no new mode-tracking rule",
        "branch_screen": "R283 amendment: endpoints vs q=0 (cos>=0.9, |df|<0.05 Hz); cross-level q=0 chain cos>=0.9",
    }
    contract_hash = hashlib.sha256(
        json.dumps(contract, sort_keys=True).encode()).hexdigest()

    ro = r283_readonly()

    cells = []
    for m0 in M0_LEVELS:
        for q in Q_GRID:
            if m0 in R283_RO_M0 and q in R283_RO_Q:
                cells.append({"m0": m0, "q": q, "source": "r283_readonly",
                              "identified": ro[(m0, q)]})
            else:
                r = run_eig_at(q, scale=m0 / 200.0, keep_modes=True)
                cells.append({"m0": m0, "q": q, "source": "new", "run": r})

    # attribution reruns (3 flagged R283 cells)
    reruns = []
    for m0, q in ATTR_RERUN:
        r = run_eig_at(q, scale=m0 / 200.0, keep_modes=True)
        ref = ro[(m0, q)]
        got = None if r["identified"] is None else r["identified"]["damping_ratio"]
        match = bool(got is not None
                     and abs(got - ref["damping_ratio"]) < RERUN_TOL)
        reruns.append({"m0": m0, "q": q, "run": r,
                       "r283_zeta": ref["damping_ratio"], "r285_zeta": got,
                       "match": match})

    summary = {
        "experiment": "r285_hybridization_map",
        "question": "Q-0044",
        "contract": contract,
        "contract_sha256": contract_hash,
        "cells": cells,
        "attribution_reruns": reruns,
        "rerun_checks_pass": all(x["match"] for x in reruns),
    }
    sp = OUT / "summary.json"
    sp.write_text(json.dumps(summary, indent=1))
    prov = {
        "summary_sha256": sha256_file(sp),
        "contract_sha256": contract_hash,
        "env": "AndesMultiVSGEnvV4._build_system() unmodified",
        "runner": "/home/wya/andes_venv/bin/python (WSL), ANDES 2.0.0",
        "r283_input_readonly": str(R283_SUMMARY),
        "r283_input_sha256": sha256_file(R283_SUMMARY),
        "shared_module": "probes/eig_alloc_common.py (keep_modes extension, backward-compatible)",
    }
    (OUT / "provenance.json").write_text(json.dumps(prov, indent=1))

    print("contract_sha256:", contract_hash[:16])
    print("rerun_checks_pass:", all(x["match"] for x in reruns))
    for c in cells:
        m = c["identified"] if c["source"] == "r283_readonly" else c["run"]["identified"]
        if m is None:
            print(f"M0={c['m0']:5.1f} q={c['q']:+.4f} [{c['source']}] identified=NONE")
        else:
            print(f"M0={c['m0']:5.1f} q={c['q']:+.4f} [{c['source']}] "
                  f"f={m['freq_hz']:.4f} zeta={m['damping_ratio']:.5f} "
                  f"contrast={m['area_contrast']:.4f}")


if __name__ == "__main__":
    main()
