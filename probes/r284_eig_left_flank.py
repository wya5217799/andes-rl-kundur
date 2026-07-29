"""R284 left-flank densification check (R282 symmetric completion).

Frozen contracts (memory/rounds/R284/plan.md):
- plant/mapping/operating point identical to R281/R282; q densification grid
  {-0.2000, -0.2125, -0.2250, -0.2375} between the R281-measured endpoints
  -0.1875 and -0.25.
- Identification in-script via probes/eig_alloc_common.py (R282 rule,
  no retuning).
- Continuity metrics (pre-registered, same as R282): participation cosine
  >= 0.9 and |df| < 0.05 Hz between adjacent q points (including the two
  R281 endpoints read read-only from results/r281_eig_mechanism/summary.json).

Writes results/r284_eig_left_flank/{summary.json, provenance.json}.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path("/mnt/c/Users/27443/Desktop/andes-rl-kundur")
sys.path.insert(0, str(ROOT / "probes"))
OUT = ROOT / "results" / "r284_eig_left_flank"
R281_SUMMARY = ROOT / "results" / "r281_eig_mechanism" / "summary.json"

from eig_alloc_common import (  # noqa: E402
    cosine,
    identify_interarea,
    merge_conjugate_pairs,
    run_eig_at,
    sha256_file,
)

Q_GRID = [-0.2375, -0.2250, -0.2125, -0.2000]
COS_MIN = 0.9
DF_MAX = 0.05


def r281_endpoint(q_target: float):
    """Read-only: re-identify the R281 grid point with this script's rule."""
    data = json.loads(R281_SUMMARY.read_text())
    for r in data["main_sweep"]:
        if abs(r["q"] - q_target) < 1e-9:
            return identify_interarea(merge_conjugate_pairs(r["modes"]))
    raise KeyError(f"R281 grid point {q_target} not found")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    contract = {
        "mapping": "M_i(q)=200+600*(0.25+q*[1,1,-1,-1]) (identical to R281)",
        "parent": "R281 contract 11a4800123f48a33 / R282 contract 6d0da4e1da39fc47 (cited)",
        "q_grid": Q_GRID,
        "mode_rule": "eig_alloc_common: conjugate-pair merge then max |P_area1-P_area2|",
        "continuity": {"cosine_min": COS_MIN, "df_max_hz": DF_MAX},
    }
    contract_hash = hashlib.sha256(
        json.dumps(contract, sort_keys=True).encode()).hexdigest()

    results = [run_eig_at(q) for q in Q_GRID]

    # continuity chain: R281 -0.25 -> new 4 (descending) -> R281 -0.1875
    chain = [("r281", -0.25, r281_endpoint(-0.25))]
    chain += [("r284", r["q"], r["identified"]) for r in results]
    chain.append(("r281", -0.1875, r281_endpoint(-0.1875)))
    continuity = []
    for (s0, q0, m0), (s1, q1, m1) in zip(chain, chain[1:]):
        if m0 is None or m1 is None:
            continuity.append({"q_pair": [q0, q1], "status": "identification_failed"})
            continue
        c = cosine(m0["p_vector"], m1["p_vector"])
        df = abs(m1["freq_hz"] - m0["freq_hz"])
        continuity.append({
            "q_pair": [q0, q1], "cosine": c, "df_hz": df,
            "zeta_pair": [m0["damping_ratio"], m1["damping_ratio"]],
            "continuous": bool(c >= COS_MIN and df < DF_MAX),
        })

    summary = {
        "experiment": "r284_eig_left_flank",
        "parent": "R281 (contract 11a4800123f48a33) / R282 (6d0da4e1da39fc47)",
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
        "shared_module": "probes/eig_alloc_common.py",
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
