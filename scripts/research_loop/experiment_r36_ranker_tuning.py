"""r36 — Ranker-tuning sensitivity experiment.

Per r30 audit and r35 verdict, two design choices in `paper_grade_axes.py`
are flagged as candidates for relaxation:

  T1. TOL["settling"] = 4.0  — too tight; project settle 6.8-7.7 s vs paper
       3 / 2.5 s = 4-5 s gap, score 0 across all controllers (settling axis
       structurally null on V4).
  T2. Action-range axes (dH/dD range_in_box) — score 1.0 across all DDIC
       controllers because project max ΔH ≤ 18.9 vs box 400 (DA-CRIT-3).

This experiment recomputes the principal-controller ranking under three
ranker variants:

  V1. Baseline (current post-fix)
  V2. Relax settling tol to 6.0 s (was 4.0)
  V3. Drop range_in_box axes (5-axis ranker for DDIC)
  V4. V2 + V3 combined

Goal: see whether the ranking ORDER changes, and how the R21-vs-no-control
multiplier responds. If V2/V3/V4 do not change the ordering, the current
ranker is fine and the structural-zero / structural-one observations
are merely *expected* given V4 env constraints. If the ordering does
change, we surface a paper-policy decision.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.paper_grade_axes import (  # noqa: E402
    PAPER, TOL, _action_range, _box_containment, _hf_std, _settling_time,
    _tol_score,
)

EVAL_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline"

PRINCIPAL = [
    ("ddic_v4_h50_s49", "R21"),
    ("ddic_v4_ens2_R21ws8_w9802", "HAWE 98/2"),
    ("ddic_v4_ens2_R21ws8_w9505", "HAWE 95/5"),
    ("ddic_v4_ens2_R21ws8_w8515", "HAWE 85/15"),
    ("ddic_v4_ens_R21_freshs50_w9802", "HAWE freshs50 98/2"),
    ("ddic_v4_swa_w98", "SWA 98/2"),
    ("ddic_v4_swa_w50", "SWA 50/50"),
    ("ddic_v4_8_R21_best", "ws8 single"),
    ("ddic_v4_h50_s50", "fresh s50 alone"),
    ("ddic_v4_paper_s42", "vanilla SAC"),
    ("no_control", "no-control"),
]


def evaluate_with_variant(
    label: str, scen: str, *, settling_tol: float = 4.0, drop_range: bool = False
) -> float:
    """Re-evaluate one trace JSON under a ranker variant. Returns overall."""
    p = EVAL_DIR / f"{label}_{scen}.json"
    if not p.exists():
        return float("nan")
    j = json.load(open(p))
    tr = j.get("traces") or []
    if not tr:
        return 0.0
    if j.get("tds_failed"):
        return 0.0

    is_ddic = "ddic" in label
    paper = PAPER[scen]

    t = np.array([s["t"] for s in tr])
    df_full = np.array([s["delta_f_es"] for s in tr])
    H_full = np.array([s["M_es"] for s in tr]) / 2.0
    D_full = np.array([s["D_es"] for s in tr])
    if (np.isnan(df_full).any() or np.isnan(H_full).any()
            or np.isnan(D_full).any()):
        return 0.0

    own_final_df = float(np.max(np.abs(df_full[-1])))
    proj_settling = _settling_time(
        t, df_full, residual_band_Hz=0.02, final_df_Hz=own_final_df
    )

    mask_6s = t <= t[0] + 6.0
    df = df_full[mask_6s]
    H = H_full[mask_6s]
    D = D_full[mask_6s]
    dH = H - H[0:1]
    dD = D - D[0:1]

    proj_max_df = float(np.max(np.abs(df)))
    proj_final_df = float(np.abs(df[-1]).max())
    proj_dH_std = _hf_std(dH) if is_ddic else 0.0
    proj_dD_std = _hf_std(dD) if is_ddic else 0.0
    proj_dH_min, proj_dH_max = _action_range(dH)
    proj_dD_min, proj_dD_max = _action_range(dD)

    settling_input = (
        proj_settling if proj_settling != float("inf") else 99.0
    )
    scores = [
        _tol_score(proj_max_df, paper.max_abs_df_Hz, TOL["max_df"]),
        _tol_score(proj_final_df, paper.final_abs_df_Hz, TOL["final_df"]),
        _tol_score(settling_input, paper.settling_to_residual_s, settling_tol),
    ]
    if is_ddic:
        scores += [
            max(0.0, 1.0 - proj_dH_std / TOL["dH_smooth"]),
            max(0.0, 1.0 - proj_dD_std / TOL["dD_smooth"]),
        ]
        if not drop_range:
            scores += [
                _box_containment(proj_dH_min, proj_dH_max,
                                 paper.dH_range[0], paper.dH_range[1]),
                _box_containment(proj_dD_min, proj_dD_max,
                                 paper.dD_range[0], paper.dD_range[1]),
            ]
    return math.exp(
        sum(math.log(max(s, 0.01)) for s in scores) / len(scores)
    )


def overall(label: str, *, settling_tol: float, drop_range: bool) -> float:
    scs = [
        evaluate_with_variant(label, "load_step_1",
                              settling_tol=settling_tol, drop_range=drop_range),
        evaluate_with_variant(label, "load_step_2",
                              settling_tol=settling_tol, drop_range=drop_range),
    ]
    if any(math.isnan(s) for s in scs):
        return float("nan")
    return math.exp(sum(math.log(max(s, 0.01)) for s in scs) / len(scs))


def main() -> int:
    variants = [
        ("V1 baseline (current)",     dict(settling_tol=4.0, drop_range=False)),
        ("V2 settling tol 6.0",       dict(settling_tol=6.0, drop_range=False)),
        ("V3 drop range axes",        dict(settling_tol=4.0, drop_range=True)),
        ("V4 V2+V3",                  dict(settling_tol=6.0, drop_range=True)),
    ]

    results: dict[str, dict[str, float]] = {}
    for label, name in PRINCIPAL:
        results[name] = {}
        for vname, kwargs in variants:
            results[name][vname] = overall(label, **kwargs)

    headers = [v[0] for v in variants]
    print(f"{'Controller':<22}", end="")
    for h in headers:
        print(f"  {h:>22}", end="")
    print()
    print("-" * (22 + 24 * len(headers)))
    for name, scores in results.items():
        print(f"{name:<22}", end="")
        for h in headers:
            v = scores[h]
            vs = f"{v:.3f}" if not math.isnan(v) else "n/a"
            print(f"  {vs:>22}", end="")
        print()

    # Multiplier R21 / no-control under each variant
    print()
    print("R21 / no-control multiplier under each variant:")
    for h in headers:
        r21 = results["R21"][h]
        nc = results["no-control"][h]
        ratio = r21 / nc if nc and not math.isnan(nc) else float("nan")
        print(f"  {h:<24}  R21={r21:.3f}  no-control={nc:.3f}  ratio={ratio:.2f}x")

    out = ROOT / "results" / "research_loop" / "r36_ranker_tuning_experiment.json"
    out.write_text(json.dumps(
        {"variants": [v[0] for v in variants], "results": results},
        indent=2,
    ))
    print(f"\nwrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
