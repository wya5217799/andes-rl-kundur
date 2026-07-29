"""R285 zone analysis (Q-0044) — reads the sealed map, applies the frozen
branch-validity screen, charts the valid/flag boundary, attributes flagged
cells, classifies the pre-registered verdict.

Criteria (plan.md / R283 amendment, unchanged):
- Within-row: q != 0 vs that row's q=0 anchor — cosine >= 0.9 AND
  |df| < 0.05 Hz.
- Cross-level q=0 chain (100 -> 125 -> 150 -> 175 -> 200, the R283 anchor
  row read-only): cosine >= 0.9 only.
- Attribution classifier (plan.md contract 4): picked mode and top-3
  contrast modes; class = non-area-contrasted (contrast < 0.3) /
  VSG-local-leaning (top-2 participation keys contain a vsg*) /
  GENROU-area-leaning (otherwise).

Runs anywhere (pure JSON + numpy): reads
results/r285_hybridization_map/summary.json, writes
results/r285_hybridization_map/zone_analysis.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "results" / "r285_hybridization_map" / "summary.json"
R283_SUMMARY = ROOT / "results" / "r283_strength_sweep" / "summary.json"
OUT = ROOT / "results" / "r285_hybridization_map" / "zone_analysis.json"

COS_MIN = 0.9
DF_MAX = 0.05
CONTRAST_LOW = 0.3
Q_ENDPOINTS = (-0.25, -0.125, 0.125, 0.25)


def cosine(a, b):
    a, b = np.asarray(a), np.asarray(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-30))


def mode_brief(m):
    top2 = sorted(m["p_machines"], key=m["p_machines"].get, reverse=True)[:2]
    return {"freq_hz": m["freq_hz"], "damping_ratio": m["damping_ratio"],
            "real": m["real"], "top2_machines": top2,
            "top2_share": [m["p_machines"][k] for k in top2]}


def contrast_of(m):
    p = m["p_machines"]
    a1 = sum(p.get(k, 0.0) for k in ("genrou1", "genrou2", "vsg12", "vsg16"))
    a2 = sum(p.get(k, 0.0) for k in ("genrou3", "genrou4", "vsg14", "vsg15"))
    return abs(a1 - a2)


def classify(m, contrast):
    if contrast < CONTRAST_LOW:
        return "non-area-contrasted"
    top2 = sorted(m["p_machines"], key=m["p_machines"].get, reverse=True)[:2]
    if any(k.startswith("vsg") for k in top2):
        return "VSG-local-leaning"
    return "GENROU-area-leaning"


def main():
    d = json.loads(SUMMARY.read_text())
    cells = {(c["m0"], c["q"]): c for c in d["cells"]}
    reruns = {(r["m0"], r["q"]): r for r in d["attribution_reruns"]}
    m0_levels = sorted({c["m0"] for c in d["cells"]})
    q_grid = sorted({c["q"] for c in d["cells"]})

    def identified_of(cell):
        return cell["identified"] if cell["source"] == "r283_readonly" \
            else cell["run"]["identified"]

    def modes_of(m0, q):
        cell = cells[(m0, q)]
        if cell["source"] == "new":
            return cell["run"].get("modes", [])
        rr = reruns.get((m0, q))
        return rr["run"].get("modes", []) if rr else []

    if not d["rerun_checks_pass"]:
        verdict = "INVALID"
        rows, chain, boundary, attributions = [], {}, {}, {}
    else:
        # within-row screen
        rows = []
        boundary = {}
        for m0 in m0_levels:
            anchor = identified_of(cells[(m0, 0.0)])
            row = {"m0": m0, "q0": {"freq_hz": anchor["freq_hz"],
                                    "zeta": anchor["damping_ratio"]},
                   "points": {}}
            for q in Q_ENDPOINTS:
                m = identified_of(cells[(m0, q)])
                c = cosine(anchor["p_vector"], m["p_vector"])
                df = abs(m["freq_hz"] - anchor["freq_hz"])
                ok = bool(c >= COS_MIN and df < DF_MAX)
                row["points"][str(q)] = {"status": "valid" if ok else "flagged",
                                         "cosine": c, "df_hz": df,
                                         "freq_hz": m["freq_hz"],
                                         "zeta": m["damping_ratio"],
                                         "contrast": m["area_contrast"]}
            rows.append(row)
            boundary[str(m0)] = {q: row["points"][str(q)]["status"]
                                 for q in Q_ENDPOINTS}

        # cross-level q=0 chain incl. R283 M0=200 anchor row
        r283 = json.loads(R283_SUMMARY.read_text())
        a200 = next(e for e in r283["axis_a"] if e["m0"] == 200.0)
        m200 = next(r["identified"] for r in a200["runs"] if abs(r["q"]) < 1e-9)
        chain_seq = [(m0, identified_of(cells[(m0, 0.0)])) for m0 in m0_levels]
        chain_seq.append((200.0, m200))
        chain = {"pass": True, "detail": []}
        prev = None
        for lvl, m in chain_seq:
            if prev is not None:
                c = cosine(prev[1]["p_vector"], m["p_vector"])
                ok = bool(c >= COS_MIN)
                chain["pass"] = chain["pass"] and ok
                chain["detail"].append({"level": lvl, "vs_level": prev[0],
                                        "cosine": c, "continuous": ok})
            prev = (lvl, m)

        # attribution for flagged cells
        attributions = {}
        for row in rows:
            m0 = row["m0"]
            for q in Q_ENDPOINTS:
                if row["points"][str(q)]["status"] != "flagged":
                    continue
                modes = modes_of(m0, q)
                if not modes:
                    attributions[f"{m0}/{q}"] = {"status": "unavailable"}
                    continue
                scored = sorted(modes, key=contrast_of, reverse=True)[:3]
                pick = identified_of(cells[(m0, q)])
                attributions[f"{m0}/{q}"] = {
                    "picked": {**mode_brief(pick_to_mode(pick, modes)),
                               "contrast": pick["area_contrast"],
                               "class": classify(pick_to_mode(pick, modes),
                                                 pick["area_contrast"])},
                    "top3_by_contrast": [
                        {**mode_brief(m), "contrast": contrast_of(m),
                         "class": classify(m, contrast_of(m))}
                        for m in scored],
                }

        # guard-invalid share across computed cells (plan: >25% -> INVALID)
        computed = [c for c in d["cells"] if c["source"] == "new"]
        n_bad = sum(1 for c in computed
                    if not (c["run"]["guards"]["g4_zeroed"]
                            and c["run"]["guards"]["zero_sum_pass"]
                            and c["run"]["guards"]["pflow_converged"]))
        guard_share = n_bad / max(len(computed), 1)
        attr_ok = all(a.get("status") != "unavailable"
                      for a in attributions.values())
        if not chain["pass"] or guard_share > 0.25:
            verdict = "INVALID"
        elif not attr_ok or n_bad > 0:
            verdict = "ZONE-PARTIAL"
        else:
            verdict = "ZONE-CHARTED"

    out = {
        "criteria": {"within_row": {"cosine_min": COS_MIN, "df_max_hz": DF_MAX},
                     "cross_level_q0": {"cosine_min": COS_MIN},
                     "contrast_low": CONTRAST_LOW},
        "rerun_checks_pass": d["rerun_checks_pass"],
        "rows": rows,
        "boundary": boundary,
        "cross_level_q0_chain": chain if d["rerun_checks_pass"] else {},
        "attributions": attributions if d["rerun_checks_pass"] else {},
        "verdict_class": verdict,
    }
    OUT.write_text(json.dumps(out, indent=1))

    print("verdict_class:", verdict)
    for row in rows:
        line = " ".join(f"q={q}:{row['points'][str(q)]['status'][0].upper()}"
                        for q in Q_ENDPOINTS)
        print(f"M0={row['m0']:5.1f} {line}")
    for k, a in attributions.items():
        if a.get("status") == "unavailable":
            print(f"attr {k}: UNAVAILABLE")
        else:
            p = a["picked"]
            print(f"attr {k}: picked f={p['freq_hz']:.4f} z={p['damping_ratio']:.4f} "
                  f"class={p['class']} top2={p['top2_machines']}")


def pick_to_mode(pick, modes):
    """Reconstruct a mode-shaped dict for the identified pick from modes."""
    for m in modes:
        if abs(m["freq_hz"] - pick["freq_hz"]) < 1e-9:
            return m
    # fallback: synthesize minimal fields
    return {"freq_hz": pick["freq_hz"], "damping_ratio": pick["damping_ratio"],
            "real": float("nan"),
            "p_machines": dict(zip(pick["p_keys"], pick["p_vector"]))}


if __name__ == "__main__":
    main()
