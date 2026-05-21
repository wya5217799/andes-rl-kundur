"""R135 — Re-score N=90 ckpts with fresh evaluate_trace, fix R134.

R134 found Pearson r(geo, cum_rf) = +0.415 with rank disagreement
indicating r67_w2a as "hidden cum_rf SOTA" (geo=0.251 from cache,
cum_rf=-0.031). R135 discovered the cached geo values are STALE
(from older paper_grade_axes scoring); fresh evaluate_trace gives
r67_w2a geo=0.014-0.056 (similar to warm-h_0 catastrophic).

R135 re-scores all 90 ckpts with current evaluate_trace + recomputes
correlation. This is the integrity check the R134 verdict's
follow-up flagged.

Output: results/r135_freshscore/{summary.json, scatter.png}.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

if "andes" not in sys.modules:
    sys.modules["andes"] = types.ModuleType("andes")

from andes_rl_kundur.evaluation.paper_grade_axes import evaluate_trace, PAPER  # noqa: E402
from andes_rl_kundur.evaluation.paper_strict_eval import compute_global_cum_rf  # noqa: E402


SEARCH_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline"
OUT_DIR = ROOT / "results" / "r135_freshscore"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _find_traces(label: str, summary_dir: Path) -> tuple[Path | None, Path | None]:
    """Match `{label}_*load_step_{1,2}.json` for current label."""
    ls1 = sorted(summary_dir.glob(f"{label}_*load_step_1.json"))
    ls2 = sorted(summary_dir.glob(f"{label}_*load_step_2.json"))
    return (ls1[0] if ls1 else None, ls2[0] if ls2 else None)


def _score_one(label: str, summary_dir: Path) -> dict | None:
    p1, p2 = _find_traces(label, summary_dir)
    if p1 is None or p2 is None:
        return None
    try:
        ts1 = evaluate_trace(p1, PAPER["load_step_1"], is_ddic=True, label=label)
        ts2 = evaluate_trace(p2, PAPER["load_step_2"], is_ddic=True, label=label)
        # Geo = geometric mean of LS1 + LS2 overalls (floor at 0.01 per
        # summary.py convention; matches score_trace_files's `floor_geo_mean`)
        import math
        vals = [max(ts1.overall, 0.01), max(ts2.overall, 0.01)]
        geo = math.exp(sum(math.log(v) for v in vals) / len(vals))

        # cum_rf
        cum_rf = 0.0
        for p in (p1, p2):
            tr = json.loads(p.read_text())
            cum_rf += compute_global_cum_rf(tr)

        return {
            "label": label,
            "LS1_geo": ts1.overall,
            "LS2_geo": ts2.overall,
            "geo": geo,
            "cum_rf": cum_rf,
        }
    except Exception as e:
        print(f"  ERR {label}: {e}")
        return None


def main():
    files = sorted([p for p in SEARCH_DIR.glob("*_summary.json")])
    print(f"R135: re-scoring {len(files)} ckpts with current evaluate_trace\n")
    records: list[dict] = []
    for sp in files:
        label = sp.stem.replace("_summary", "")
        rec = _score_one(label, SEARCH_DIR)
        if rec:
            records.append(rec)

    print(f"\n  Successfully scored: {len(records)} / {len(files)}")
    if len(records) < 5:
        return

    geos = np.array([r["geo"] for r in records])
    cum_rfs = np.array([r["cum_rf"] for r in records])
    corr = float(np.corrcoef(geos, cum_rfs)[0, 1])
    print(f"\n  Pearson r(geo, cum_rf) = {corr:+.3f}")
    print(f"  geo: med={np.median(geos):.4f}  p10={np.percentile(geos,10):.4f}  p90={np.percentile(geos,90):.4f}")
    print(f"  cum_rf: med={np.median(cum_rfs):.4f}  p10={np.percentile(cum_rfs,10):.4f}  p90={np.percentile(cum_rfs,90):.4f}")

    # Top 5 by geo / cum_rf
    by_geo = sorted(records, key=lambda r: -r["geo"])[:5]
    by_cumrf = sorted(records, key=lambda r: -r["cum_rf"])[:5]
    print("\n--- Top 5 by FRESH geo ---")
    for r in by_geo:
        print(f"  {r['label']:50s} geo={r['geo']:.4f}  cum_rf={r['cum_rf']:+.4f}")
    print("\n--- Top 5 by cum_rf ---")
    for r in by_cumrf:
        print(f"  {r['label']:50s} geo={r['geo']:.4f}  cum_rf={r['cum_rf']:+.4f}")

    # Cross-tab disagreement
    geo_rank = {r["label"]: i for i, r in enumerate(sorted(records, key=lambda x: -x["geo"]))}
    cumrf_rank = {r["label"]: i for i, r in enumerate(sorted(records, key=lambda x: -x["cum_rf"]))}
    print("\n--- Best-of-both candidates (both ranks in top 30) ---")
    for r in records:
        gr = geo_rank[r["label"]]
        cr = cumrf_rank[r["label"]]
        if gr < 30 and cr < 30:
            print(f"  {r['label']:50s} geo#{gr+1:2d} cum_rf#{cr+1:2d}  geo={r['geo']:.4f} cum_rf={r['cum_rf']:+.4f}")

    summary = {
        "round": "R135",
        "n_records": len(records),
        "pearson_corr_geo_cumrf": corr,
        "top_5_by_geo": [{"label": r["label"], "geo": r["geo"], "cum_rf": r["cum_rf"]} for r in by_geo],
        "top_5_by_cum_rf": [{"label": r["label"], "geo": r["geo"], "cum_rf": r["cum_rf"]} for r in by_cumrf],
        "all_records": records,
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nWritten: {OUT_DIR / 'summary.json'}")

    # Scatter
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 5.5))
    ax.scatter(cum_rfs, geos, s=22, alpha=0.55, edgecolor="black", linewidth=0.3, c="gray",
               label=f"n={len(records)} (fresh)")
    # Highlight
    bg = [r for r in by_geo[:5]]
    bc = [r for r in by_cumrf[:5]]
    ax.scatter([r["cum_rf"] for r in bg], [r["geo"] for r in bg],
               s=90, c="tab:red", marker="*", edgecolor="black", linewidth=0.6,
               label="top-5 geo")
    ax.scatter([r["cum_rf"] for r in bc], [r["geo"] for r in bc],
               s=55, c="tab:green", marker="o", edgecolor="black", linewidth=0.6,
               label="top-5 cum_rf")
    ax.set_xlabel("cum_rf (less negative = better)")
    ax.set_ylabel("FRESH 11-axis geo (current paper_grade_axes)")
    ax.set_title(f"R135 — FRESH re-score across N={len(records)} ckpts\n"
                 f"Pearson r = {corr:+.3f}  (R134 stale-geo value was +0.415)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "scatter.png", dpi=180)
    fig.savefig(OUT_DIR / "scatter.pdf")
    print(f"saved: scatter.png + .pdf")


if __name__ == "__main__":
    main()
