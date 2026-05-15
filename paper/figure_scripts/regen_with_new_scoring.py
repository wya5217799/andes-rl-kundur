"""Regenerate dissertation figures with NEW 8-axis scoring (utilization + improvement axes).

Replaces hardcoded post-N1c scores with new evaluator output. Produces:
  - paper/figures/v4_progression_chart_NEW.{png,pdf}
  - paper/figures/v4_overlay_compare/score_bar_summary_NEW.{png,pdf}
  - paper/figures/v4_per_agent_contribution_bars_NEW.{png,pdf}
  - paper/figures/v4_gini_vs_score_NEW.{png,pdf}

New scoring per evaluation/paper_grade_axes.py v2 (2026-05-09):
  - _action_utilization replaces _box_containment (was trivially 1.0)
  - smoothness applies to ALL traces (not DDIC-only)
  - improvement_vs_noctrl axis added (uses no_control trace as reference)

Run:  python paper/figure_scripts/regen_with_new_scoring.py
"""
from __future__ import annotations
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from evaluation.paper_grade_axes import (  # noqa: E402
    evaluate_trace, PAPER, _load_no_ctrl_max_df,
)
from plotting.paper_style import apply_ieee_style, save_fig  # noqa: E402

EVAL = ROOT / "results" / "research_loop" / "eval_v4_baseline"
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)


# ─── Compute new scores for all stages ────────────────────────────────────────

# Stage definition: (display_label, ckpt_label, color, is_ddic, is_aggregate)
STAGES = [
    ("no_control",   "no_control",                 "#888888", False, False),
    ("vanilla SAC",  ["ddic_v4_paper_s42", "ddic_v4_paper_s43", "ddic_v4_paper_s44"],
                                                   "#9e9e9e", True,  True),
    ("ws8",          "ddic_v4_8_R21_best",         "#2e7d32", True,  False),
    ("Ens 85/15",    "ddic_v4_ens2_R21ws8_w8515",  "#ff9800", True,  False),
    ("Ens 98/2",     "ddic_v4_ens2_R21ws8_w9802",  "#d32f2f", True,  False),
    ("R21 BEST",     "ddic_v4_h50_s49",            "#1565c0", True,  False),
]


def score_one(label: str, is_ddic: bool, no_ctrl_refs: dict) -> tuple[float, list]:
    """Return (geo_mean across LS1+LS2, list of TraceScore objects)."""
    per = []
    for scen in ["load_step_1", "load_step_2"]:
        p = EVAL / f"{label}_{scen}.json"
        if not p.exists():
            return 0.0, []
        ts = evaluate_trace(p, PAPER[scen], is_ddic=is_ddic, label=label,
                            no_ctrl_max_df=no_ctrl_refs[scen])
        per.append(ts)
    if not per:
        return 0.0, []
    geo = math.exp(sum(math.log(max(t.overall, 0.01)) for t in per) / len(per))
    return geo, per


def compute_all_scores() -> list[dict]:
    no_ctrl_refs = {s: _load_no_ctrl_max_df(EVAL, s)
                    for s in ["load_step_1", "load_step_2"]}
    print(f"no_ctrl refs: {no_ctrl_refs}")

    out = []
    for display, ckpt, color, is_ddic, is_agg in STAGES:
        if is_agg:
            # Average of multiple ckpts
            scores = []
            for c in ckpt:
                s, _ = score_one(c, is_ddic, no_ctrl_refs)
                if s > 0:
                    scores.append(s)
            score = float(np.mean(scores)) if scores else 0.0
            ckpt_repr = f"avg({len(scores)})"
        else:
            score, _ = score_one(ckpt, is_ddic, no_ctrl_refs)
            ckpt_repr = ckpt
        out.append({"display": display, "ckpt": ckpt_repr, "color": color,
                    "score": score, "is_ddic": is_ddic})
        print(f"  {display:14s} ({ckpt_repr:35s}) → score = {score:.4f}")
    return out


# ─── Figure 1: Progression chart ──────────────────────────────────────────────

def plot_progression(scores: list[dict]):
    apply_ieee_style()
    fig, ax = plt.subplots(figsize=(8.5, 4.8))

    # Add paper benchmark as last bar
    bars_data = scores + [{"display": "Paper\nbenchmark", "score": 1.0,
                            "color": "#000000", "ckpt": "target"}]
    x = np.arange(len(bars_data))
    vals = [b["score"] for b in bars_data]
    colors = [b["color"] for b in bars_data]
    labels = [b["display"] for b in bars_data]

    bars = ax.bar(x, vals, color=colors, edgecolor="black", linewidth=0.9, width=0.7)

    base = vals[0]   # no_control reference
    for i, (bar, v) in enumerate(zip(bars, vals)):
        # Score on top of bar
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.02,
                f"{v:.3f}", ha="center", fontsize=9, fontweight="bold")
        # Improvement annotation under top
        if i > 0 and base > 0:
            mult = v / base
            annot = f"{mult:+.2f}×" if mult >= 1.0 else f"({(mult-1)*100:+.0f}%)"
            ax.text(bar.get_x() + bar.get_width() / 2,
                    max(v - 0.05, 0.02), annot,
                    ha="center", fontsize=7.5, color="black",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray", alpha=0.8))

    # Paper benchmark dashed line
    ax.axhline(1.0, color="black", ls=":", lw=0.8, alpha=0.5)

    # Connector arrows (only between project stages, not into paper benchmark)
    for i in range(1, len(scores)):
        arrow = FancyArrowPatch(
            (x[i - 1] + 0.35, vals[i - 1] + 0.005),
            (x[i] - 0.35, vals[i] + 0.005),
            arrowstyle='->,head_length=4,head_width=3',
            color='gray', alpha=0.5, lw=0.8,
            connectionstyle='arc3,rad=-0.15')
        ax.add_patch(arrow)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("8-axis paper-grade score (NEW)", fontsize=10)
    ax.set_title("Stage 2 ANDES progression — recomputed with utilization + improvement axes",
                 fontsize=10.5, pad=12)
    ax.set_ylim(0, 1.18)
    ax.grid(True, axis="y", alpha=0.3)

    # Best ckpt callout
    best_idx = int(np.argmax([s["score"] for s in scores]))
    best = scores[best_idx]
    ax.annotate(
        f"{best['score'] / base:.2f}× over no_control\n(best={best['display']})",
        xy=(best_idx, best["score"]), xytext=(best_idx + 0.3, 0.85),
        arrowprops=dict(arrowstyle="->", color="black", lw=0.7),
        fontsize=8.5, ha="left",
        bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow", ec="black"))

    # Footnote about scoring change
    fig.text(0.5, 0.02,
             "Note: 8-axis evaluator (paper_grade_axes.py v2, 2026-05-09) — fixes Axis-6 degeneracy "
             "+ adds improvement axis.\nOld scores 0.110/0.137/0.255/0.413/0.439/0.444 superseded.",
             ha="center", fontsize=7, style="italic", color="dimgray")

    plt.subplots_adjust(bottom=0.22)
    save_fig(fig, OUT, "v4_progression_chart_NEW")
    plt.close(fig)
    print("  saved v4_progression_chart_NEW.{png,pdf}")


# ─── Figure 2: Score bar summary (overlay subdir) ─────────────────────────────

def plot_score_bar_summary(scores: list[dict]):
    apply_ieee_style()
    fig, ax = plt.subplots(figsize=(7.0, 3.4))

    # Skip vanilla SAC for parity with old fig (it had only 5 bars)
    use = [s for s in scores if s["display"] not in ("vanilla SAC",)]
    labels = [s["display"] for s in use]
    vals = [s["score"] for s in use]
    colors = [s["color"] for s in use]

    bars = ax.bar(labels, vals, color=colors, edgecolor="black", linewidth=0.8)
    base = use[0]["score"]   # no_control
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.015,
                f"{v:.3f}\n({v / base:.2f}x)", ha="center", fontsize=8.5)

    ax.axhline(1.0, color="black", ls="--", lw=0.8, label="Paper (target)")
    ax.set_ylabel("8-axis score (mean LS1+LS2, NEW)", fontsize=10)
    ax.set_title("Controller comparison — paper-grade alignment scores (recomputed)",
                 fontsize=10)
    ax.set_ylim(0, max(max(vals), 0.2) * 1.4)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)
    plt.xticks(rotation=15, ha="right", fontsize=9)

    fig.text(0.5, 0.02,
             "8-axis evaluator (paper_grade_axes.py v2). Old scores "
             "0.110/0.419/0.554/0.607/0.613 superseded.",
             ha="center", fontsize=6.5, style="italic", color="dimgray")

    plt.subplots_adjust(bottom=0.30)

    sub_out = OUT / "v4_overlay_compare"
    sub_out.mkdir(parents=True, exist_ok=True)
    save_fig(fig, sub_out, "score_bar_summary_NEW")
    plt.close(fig)
    print(f"  saved v4_overlay_compare/score_bar_summary_NEW.{{png,pdf}}")


# ─── Figure 3: Gini vs score scatter ──────────────────────────────────────────

def get_dH_range(label: str, scen: str) -> np.ndarray | None:
    p = EVAL / f"{label}_{scen}.json"
    if not p.exists():
        return None
    j = json.load(open(p))
    tr = j["traces"]
    dM = np.array([s["delta_M"] for s in tr])
    dH = dM / 2.0
    return dH.max(axis=0) - dH.min(axis=0)


def gini(values: np.ndarray) -> float:
    if values.sum() == 0:
        return 0.0
    v = np.sort(values)
    n = len(v)
    cum = np.cumsum(v)
    return float((n + 1 - 2 * np.sum(cum) / cum[-1]) / n)


def plot_gini_vs_score(scores: list[dict]):
    apply_ieee_style()
    fig, ax = plt.subplots(figsize=(6.0, 3.8))

    # Skip vanilla SAC + no_control (latter has gini=0 trivially)
    use = [s for s in scores if s["display"] not in ("vanilla SAC",)]

    plotted_legend = set()
    for scen, marker, scen_lbl in [("load_step_1", "o", "LS1"),
                                    ("load_step_2", "s", "LS2")]:
        for s in use:
            ckpt = s["ckpt"]
            r = get_dH_range(ckpt, scen)
            if r is None:
                continue
            g = gini(r)
            lbl_key = (s["display"], scen_lbl)
            ax.scatter(g, s["score"], s=80, color=s["color"], marker=marker,
                       edgecolor="black", linewidth=0.7, alpha=0.85,
                       label=f"{s['display']} ({scen_lbl})"
                             if lbl_key not in plotted_legend else None)
            plotted_legend.add(lbl_key)
            ax.annotate(s["display"],
                        (g, s["score"]), xytext=(5, 3),
                        textcoords="offset points", fontsize=7,
                        color=s["color"])

    ax.set_xlabel(r"Gini coefficient of per-agent $\Delta H$ range  (0=equal, 1=monopoly)",
                  fontsize=9)
    ax.set_ylabel("8-axis score (mean LS1+LS2, NEW)", fontsize=9)
    ax.set_title("Action distribution inequality vs paper-grade score (recomputed)",
                 fontsize=9.5)

    score_max = max(s["score"] for s in use) * 1.4
    ax.set_xlim(-0.02, 0.65)
    ax.set_ylim(0.0, max(score_max, 0.15))
    ax.grid(True, alpha=0.3)

    fig.text(0.5, 0.02,
             "Y-axis: 8-axis evaluator v2 (utilization + improvement axes added).",
             ha="center", fontsize=6.5, style="italic", color="dimgray")
    plt.subplots_adjust(bottom=0.16)

    save_fig(fig, OUT, "v4_gini_vs_score_NEW")
    plt.close(fig)
    print("  saved v4_gini_vs_score_NEW.{png,pdf}")


# ─── Figure 4: Per-agent ΔH range bars (with new score in legend) ─────────────

def plot_per_agent_bars(scores: list[dict]):
    apply_ieee_style()
    es_names = ["ES1\n(Bus12)", "ES2\n(Bus16)", "ES3\n(Bus14)", "ES4\n(Bus15)"]

    use = [s for s in scores if s["display"] not in ("vanilla SAC",)]

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))

    for ax_idx, scen in enumerate(["load_step_1", "load_step_2"]):
        ax = axes[ax_idx]
        scen_lbl = ("LS1: Bus 14 −2.48 p.u." if scen == "load_step_1"
                    else "LS2: Bus 15 +1.88 p.u.")

        data, labels, colors = [], [], []
        for s in use:
            r = get_dH_range(s["ckpt"], scen)
            if r is None:
                continue
            data.append(r)
            labels.append(f"{s['display']}\n({s['score']:.3f})")
            colors.append(s["color"])

        data = np.array(data)
        n_ctrl, n_agents = data.shape
        x = np.arange(n_agents)
        width = 0.8 / n_ctrl

        for i in range(n_ctrl):
            offset = (i - (n_ctrl - 1) / 2) * width
            ax.bar(x + offset, data[i], width, color=colors[i],
                   edgecolor="black", linewidth=0.5, label=labels[i])

        ax.set_xticks(x)
        ax.set_xticklabels(es_names, fontsize=8.5)
        ax.set_ylabel(r"$\Delta H$ range (s) over episode", fontsize=9)
        ax.set_title(f"{scen_lbl}", fontsize=9.5)
        ax.set_yscale("log")
        ax.set_ylim(0.05, 100)
        ax.grid(True, axis="y", which="both", alpha=0.3)
        if ax_idx == 0:
            ax.legend(loc="upper left", fontsize=7, ncol=1, framealpha=0.92)

    fig.suptitle("Per-agent ΔH range with NEW 8-axis scores in legend",
                 fontsize=10, y=1.02)
    fig.tight_layout()

    save_fig(fig, OUT, "v4_per_agent_contribution_bars_NEW")
    plt.close(fig)
    print("  saved v4_per_agent_contribution_bars_NEW.{png,pdf}")


def main():
    print("[regen_with_new_scoring] Computing new scores...")
    scores = compute_all_scores()
    print()
    print("[regen_with_new_scoring] Generating figures...")
    plot_progression(scores)
    plot_score_bar_summary(scores)
    plot_gini_vs_score(scores)
    plot_per_agent_bars(scores)
    print()
    print(f"[regen_with_new_scoring] All figures written to {OUT}")
    print("Old figures preserved (suffix _NEW for new versions). To replace:")
    print("  cp v4_progression_chart_NEW.png v4_progression_chart.png")
    print("  cp v4_overlay_compare/score_bar_summary_NEW.png v4_overlay_compare/score_bar_summary.png")
    print("  cp v4_gini_vs_score_NEW.png v4_gini_vs_score.png")
    print("  cp v4_per_agent_contribution_bars_NEW.png v4_per_agent_contribution_bars.png")


if __name__ == "__main__":
    main()
