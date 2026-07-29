"""R283 branch-validity analysis (Q-0043) — reads the sealed sweep, flags
identification failures, classifies the pre-registered verdict.

Declared criteria (memory/rounds/R283/execution_amendment_20260729.md):
- Within-level q-chain (-0.25 -> 0 -> +0.25): participation cosine >= 0.9 AND
  |df| < 0.05 Hz (same inertia/tie level, so frequency drift is small —
  R281/R282 measured |df| <= 0.003 across the whole q range).
- Cross-level q=0 chain: participation cosine >= 0.9 only; frequency drift
  across strength levels is physical (inertia/tie change shifts the mode).
- A point failing continuity is an identification-failure flag and is
  excluded from the gradient (plan.md contract item 4); a level whose S
  endpoints are not both valid has S=None.

Runs anywhere (pure JSON + numpy): reads
results/r283_strength_sweep/summary.json, writes
results/r283_strength_sweep/branch_analysis.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "results" / "r283_strength_sweep" / "summary.json"
OUT = ROOT / "results" / "r283_strength_sweep" / "branch_analysis.json"

COS_MIN = 0.9
DF_MAX = 0.05
CONFIRM_RATIO = 1.5
ABSENT_RATIO = 1.2


def cosine(a, b):
    a, b = np.asarray(a), np.asarray(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-30))


def chain_flags(runs):
    """Within-level branch check anchored at q=0 (cross-level-verified
    reference): each endpoint is compared against q=0 directly with
    cosine >= COS_MIN and |df| < DF_MAX."""
    status, detail = {}, []
    by_q = {r["q"]: r["identified"] for r in runs}
    m0 = by_q.get(0.0)
    if m0 is None:
        for q in by_q:
            status[q] = "flagged"
            detail.append({"q": q, "reason": "q=0 anchor not identified"})
        return status, detail
    status[0.0] = "valid"
    detail.append({"q": 0.0, "reason": "anchor (cross-level q=0 chain verified)"})
    for q in (-0.25, 0.25):
        m = by_q.get(q)
        if m is None:
            status[q] = "flagged"
            detail.append({"q": q, "reason": "identification returned None"})
            continue
        c = cosine(m0["p_vector"], m["p_vector"])
        df = abs(m["freq_hz"] - m0["freq_hz"])
        ok = bool(c >= COS_MIN and df < DF_MAX)
        status[q] = "valid" if ok else "flagged"
        detail.append({"q": q, "vs_q": 0.0, "cosine": c, "df_hz": df,
                       "continuous": ok,
                       "reason": "continuous" if ok else "branch swap vs q=0"})
    return status, detail


def cross_level(entries, key):
    """q=0 chain across levels: cosine only (frequency drift is physical)."""
    detail, prev = [], None
    ok_all = True
    for e in entries:
        r = next(x for x in e["runs"] if abs(x["q"]) < 1e-9)
        m = r["identified"]
        if m is None:
            detail.append({"level": e[key], "reason": "q=0 identified None"})
            ok_all = False
            prev = None
            continue
        if prev is not None:
            c = cosine(prev[1]["p_vector"], m["p_vector"])
            ok = bool(c >= COS_MIN)
            ok_all = ok_all and ok
            detail.append({"level": e[key], "vs_level": prev[0],
                           "cosine": c, "continuous": ok})
        prev = (e[key], m)
    return ok_all, detail


def valid_sensitivity(runs, status):
    z = {}
    for r in runs:
        q = r["q"]
        if status.get(q) != "valid":
            return None
        z[q] = r["identified"]["damping_ratio"]
    return abs(z[0.25] - z[-0.25]) / abs(z[0.0])


def axis_report(entries, key):
    out = []
    for e in entries:
        status, detail = chain_flags(e["runs"])
        s = valid_sensitivity(e["runs"], status)
        out.append({"level": e[key], "point_status": {str(k): v for k, v in status.items()},
                    "chain_detail": detail, "S_valid": s,
                    "guards_all_pass": e["guards_all_pass"]})
    cross_ok, cross_detail = cross_level(entries, key)
    s_vals = [(e[key], r["S_valid"]) for e, r in zip(entries, out)
              if r["S_valid"] is not None]
    ratio = None
    if len(s_vals) >= 2:
        ss = [s for _, s in s_vals]
        ratio = max(ss) / min(ss)
    all_valid = all(all(v == "valid" for v in r["point_status"].values()) for r in out)
    return {"levels": out, "cross_level_q0": {"pass": cross_ok, "detail": cross_detail},
            "valid_S": [{"level": l, "S": s} for l, s in s_vals],
            "S_ratio_max_min": ratio, "all_points_valid": all_valid}


def classify(a, b):
    """Pre-registered tree (plan.md Outcomes)."""
    def confirmed(rep):
        return (rep["all_points_valid"] and rep["S_ratio_max_min"] is not None
                and rep["S_ratio_max_min"] >= CONFIRM_RATIO)

    def measurable(rep):
        return rep["S_ratio_max_min"] is not None

    if not (a["levels"] and b["levels"]):
        return "INVALID"
    for rep in (a, b):
        if not all(l["guards_all_pass"] for l in rep["levels"]):
            return "INVALID"
        if not rep["cross_level_q0"]["pass"]:
            return "INVALID"
    if confirmed(a) or confirmed(b):
        return "STRENGTH-GRADIENT-CONFIRMED"
    if (measurable(a) and a["S_ratio_max_min"] >= ABSENT_RATIO) \
            or (measurable(b) and b["S_ratio_max_min"] >= ABSENT_RATIO) \
            or (measurable(a) and a["S_ratio_max_min"] >= CONFIRM_RATIO) \
            or (measurable(b) and b["S_ratio_max_min"] >= CONFIRM_RATIO):
        return "STRENGTH-GRADIENT-PARTIAL"
    if measurable(a) and measurable(b):
        return "STRENGTH-GRADIENT-ABSENT"
    return "INVALID"


def main():
    d = json.loads(SUMMARY.read_text())
    a = axis_report(d["axis_a"], "m0")
    b = axis_report(d["axis_b"], "k")
    verdict = classify(a, b)
    out = {
        "criteria": {"within_level": {"cosine_min": COS_MIN, "df_max_hz": DF_MAX},
                     "cross_level_q0": {"cosine_min": COS_MIN, "df": "drift allowed (physical)"}},
        "anchor_checks": d["anchor_checks"],
        "axis_a": a,
        "axis_b": b,
        "verdict_class": verdict,
    }
    OUT.write_text(json.dumps(out, indent=1))
    print("verdict_class:", verdict)
    for name, rep in (("A(inertia)", a), ("B(tie-k)", b)):
        print(f"axis {name}: all_valid={rep['all_points_valid']} "
              f"S_ratio={rep['S_ratio_max_min']} valid_S={rep['valid_S']}")
        for l in rep["levels"]:
            print(f"  level {l['level']}: {l['point_status']} S_valid={l['S_valid']}")


if __name__ == "__main__":
    main()
