"""R134 — Audit cum_rf vs 11-axis geo correlation across cached eval ckpts.

CLM-0238 (R130) found warm-h_0 has anti-correlated cum_rf (+54%) and
11-axis geo (-96%). Is this a unique outlier or systematic? If
systematic, the project may have HIDDEN SOTAs by cum_rf metric that
11-axis ranking missed.

Mines all `*_summary.json` in `results/research_loop/eval_v4_baseline/`
and `results/research_loop/eval_paper_strict/`. For each: extract
{geo, cum_rf} pair. Compute Pearson correlation. Highlight cum_rf-best
vs geo-best ckpts.

Output: results/r134_cumrf_vs_geo_audit/{summary.json, scatter.png}.
Zero ANDES.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "r134_cumrf_vs_geo_audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEARCH_DIRS = [
    ROOT / "results" / "research_loop" / "eval_v4_baseline",
    ROOT / "results" / "research_loop" / "eval_paper_strict",
]


def _compute_cum_rf_from_traces(label: str, summary_dir: Path) -> float | None:
    """research_loop summaries don't store cum_rf. Re-compute from sibling
    trace JSONs `{label}_load_step_{1,2}.json` if available."""
    import sys, types
    if "andes" not in sys.modules:
        sys.modules["andes"] = types.ModuleType("andes")
    sys.path.insert(0, str(ROOT / "src"))
    from andes_rl_kundur.evaluation.paper_strict_eval import compute_global_cum_rf

    total = 0.0
    found = 0
    # Match the seed-suffix pattern: {label}_s{seed}_load_step_N.json
    # OR plain {label}_load_step_N.json
    for scen in ("load_step_1", "load_step_2"):
        candidates = list(summary_dir.glob(f"{label}_*{scen}.json"))
        if not candidates:
            candidates = [summary_dir / f"{label}_{scen}.json"]
        for p in candidates:
            if p.exists():
                try:
                    tr = json.loads(p.read_text())
                    total += compute_global_cum_rf(tr)
                    found += 1
                    break
                except Exception:
                    pass
    return total if found > 0 else None


def _load_one(p: Path) -> dict[str, Any] | None:
    try:
        d = json.loads(p.read_text())
    except Exception:
        return None
    # Some summaries are lists (older format) — skip them
    if not isinstance(d, dict):
        return None
    geo = d.get("mean_geo") or d.get("geo")
    cum_rf = d.get("cum_rf")
    label = p.stem.replace("_summary", "")
    if geo is None:
        return None
    # If cum_rf missing, try to re-compute from sibling trace JSONs
    if cum_rf is None:
        cum_rf = _compute_cum_rf_from_traces(label, p.parent)
        if cum_rf is None:
            return None
    return {
        "label": label,
        "geo": float(geo),
        "cum_rf": float(cum_rf),
        "path": str(p.relative_to(ROOT)),
    }


def main() -> None:
    records: list[dict] = []
    for d in SEARCH_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.glob("*_summary.json")):
            rec = _load_one(p)
            if rec:
                records.append(rec)

    print(f"R134: loaded {len(records)} cached eval summaries")
    if len(records) < 5:
        print("not enough data — skipping correlation")
        return

    geos = np.array([r["geo"] for r in records])
    cum_rfs = np.array([r["cum_rf"] for r in records])

    # cum_rf is typically negative (closer to 0 = better). Use abs to
    # convert "less negative = better" → "lower abs = better".
    # For correlation: higher geo good; less negative cum_rf good
    # ⇒ POSITIVE corr expected if they agree.
    corr = float(np.corrcoef(geos, cum_rfs)[0, 1])
    print(f"\nN = {len(records)}")
    print(f"geo: med={np.median(geos):+.4f} p10={np.percentile(geos,10):+.4f} p90={np.percentile(geos,90):+.4f}")
    print(f"cum_rf: med={np.median(cum_rfs):+.4f} p10={np.percentile(cum_rfs,10):+.4f} p90={np.percentile(cum_rfs,90):+.4f}")
    print(f"Pearson corr(geo, cum_rf) = {corr:+.3f}")

    # Top 5 by geo vs top 5 by cum_rf
    by_geo = sorted(records, key=lambda r: -r["geo"])[:5]
    by_cumrf = sorted(records, key=lambda r: -r["cum_rf"])[:5]  # higher cum_rf = less negative = better
    print("\n--- Top 5 by geo ---")
    for r in by_geo:
        print(f"  {r['label']:50s} geo={r['geo']:.4f}  cum_rf={r['cum_rf']:+.4f}")
    print("\n--- Top 5 by cum_rf (less negative = better) ---")
    for r in by_cumrf:
        print(f"  {r['label']:50s} geo={r['geo']:.4f}  cum_rf={r['cum_rf']:+.4f}")

    # Disagreement metric: any ckpt in top-5-cumrf but bottom-50 geo?
    geo_rank = {r["label"]: i for i, r in enumerate(sorted(records, key=lambda x: -x["geo"]))}
    cumrf_rank = {r["label"]: i for i, r in enumerate(sorted(records, key=lambda x: -x["cum_rf"]))}
    print("\n--- Rank disagreement (top-10 cum_rf with > 20-rank geo gap) ---")
    for r in by_cumrf[:10]:
        delta = geo_rank[r["label"]] - cumrf_rank[r["label"]]
        if abs(delta) > 20:
            print(f"  {r['label']}: cum_rf rank #{cumrf_rank[r['label']]+1}, geo rank #{geo_rank[r['label']]+1}, Δ={delta:+d}")

    # Save artefacts
    (OUT_DIR / "summary.json").write_text(json.dumps({
        "n_records": len(records),
        "pearson_corr_geo_cumrf": corr,
        "geo_stats": {"median": float(np.median(geos)), "p10": float(np.percentile(geos,10)), "p90": float(np.percentile(geos,90))},
        "cum_rf_stats": {"median": float(np.median(cum_rfs)), "p10": float(np.percentile(cum_rfs,10)), "p90": float(np.percentile(cum_rfs,90))},
        "top_5_by_geo": [{"label": r["label"], "geo": r["geo"], "cum_rf": r["cum_rf"]} for r in by_geo],
        "top_5_by_cum_rf": [{"label": r["label"], "geo": r["geo"], "cum_rf": r["cum_rf"]} for r in by_cumrf],
        "all_records": records,
    }, indent=2))

    # Scatter plot
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 5.5))
    ax.scatter(cum_rfs, geos, s=20, alpha=0.55, edgecolor="black", linewidth=0.3,
               c="tab:gray", label=f"n={len(records)} cached ckpts")
    # Highlight top by each metric
    ax.scatter([r["cum_rf"] for r in by_geo], [r["geo"] for r in by_geo],
               s=80, c="tab:red", marker="*", edgecolor="black", linewidth=0.6,
               label="top-5 by geo")
    ax.scatter([r["cum_rf"] for r in by_cumrf], [r["geo"] for r in by_cumrf],
               s=50, c="tab:green", marker="o", edgecolor="black", linewidth=0.6,
               label="top-5 by cum_rf")
    ax.set_xlabel("cum_rf (less negative = better)")
    ax.set_ylabel("11-axis geo (higher = better)")
    ax.set_title(f"R134 — cum_rf vs 11-axis geo across {len(records)} cached ckpts\n"
                 f"Pearson r = {corr:+.3f}")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "scatter.png", dpi=180)
    fig.savefig(OUT_DIR / "scatter.pdf")
    print(f"\nWritten: {OUT_DIR / 'summary.json'}, scatter.png, .pdf")


if __name__ == "__main__":
    main()
