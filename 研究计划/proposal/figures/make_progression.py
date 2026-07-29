"""Proposal progression figure — 11-axis performance across the 259-round programme.

Motivation
----------
The MRes proposal needs ONE figure that conveys, to a non-specialist
admissions committee, (a) the scale of the experimental programme,
(b) the systematic exploration of methods, and (c) the size of the
advantage over classical control -- without overclaiming a monotone
"improvement curve" that did not happen (the score plateaus).

Every plotted number is pinned to a claim in memory/claims/ and is the
CURRENT 11-axis (v3.1, gating axes 9-11) "geo" score:

  no_control floor ............ 0.094   CLM-0254
  best classical droop (K=2) .. 0.197   CLM-0186 (restated current CLM-0425)
  R72 TD3-LSTM SOTA base ...... 0.3908  CLM-0123
  R74 Pareto-dominant LSTM .... 0.410   CLM-0254
  R75 single-seed peak ........ 0.4301  CLM-0131 / CLM-0250
  R154 cross-algo ensemble .... 0.4119  CLM-0295
  R201/R249 autonomous SOTA ... 0.4152  CLM-0425
  RL / best-droop ratio ....... 2.1x    CLM-0425  (0.4152 / 0.197)
  R154 ablation spread (faint)  CLM-0295  (8-config study, shows volume)

Usage
-----
  python make_progression.py        # writes proposal_progression.{png,pdf}
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt

plt.switch_backend("Agg")

OUT = Path(__file__).resolve().parent
REPO_ROOT = OUT.parents[2]
EVIDENCE_PATH = OUT.parent / "proposal_progression_evidence.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_evidence() -> dict:
    """Load the reviewed projection and reject drift in its claim sources."""

    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    if evidence.get("version") != 1:
        raise ValueError("proposal progression evidence version must be 1")
    for source in evidence["source_files"]:
        path = REPO_ROOT / source["path"]
        if not path.is_file():
            raise FileNotFoundError(f"missing proposal evidence source: {path}")
        actual = _sha256(path)
        if actual != source["sha256"]:
            raise ValueError(
                f"proposal evidence source drift: {source['path']} "
                f"(expected {source['sha256']}, got {actual})"
            )
    return evidence


def main() -> None:
    evidence = load_evidence()
    reference_levels = evidence["reference_levels"]
    no_control = float(reference_levels["no_control"]["value"])
    droop_best = float(reference_levels["best_classical_droop"]["value"])
    milestones = [
        (
            int(row["round"]),
            float(row["value"]),
            str(row["plot_label"]),
            str(row["table_label"]),
        )
        for row in evidence["milestones"]
    ]
    spread = evidence["r154_ablation_spread"]
    spread_round = int(spread["round"])
    spread_values = [float(value) for value in spread["values"]]
    plateau = evidence["plateau_band"]
    programme = evidence["programme_scale"]

    plt.rcParams.update({
        "font.family": "serif", "font.size": 10,
        "axes.grid": True, "grid.alpha": 0.25,
    })
    fig, ax = plt.subplots(figsize=(8.0, 4.7))

    ax.axhspan(
        float(plateau["low"]),
        float(plateau["high"]),
        color="#1565c0",
        alpha=0.07,
        zorder=0,
    )
    ax.text(200, 0.396, f"RL plateau band ({plateau['trials']} trials)", fontsize=7.5,
            color="#1565c0", ha="center", va="center", style="italic")

    # classical reference lines
    ax.axhline(no_control, color="#888888", ls=":", lw=1.3)
    ax.text(31, no_control + 0.009, f"no control = {no_control:.3f}",
            fontsize=8, color="#555555")
    ax.axhline(droop_best, color="#e07b00", ls="--", lw=1.3)
    ax.text(31, droop_best - 0.026, f"best classical droop = {droop_best:.3f}",
            fontsize=8, color="#e07b00")

    # faint experiment cloud at R154 (shows volume of ablations)
    ax.scatter([spread_round] * len(spread_values), spread_values, s=12, color="#9e9e9e",
               alpha=0.5, zorder=2, label="individual experiments")

    # milestone markers + thin connector
    mx = [milestone[0] for milestone in milestones]
    my = [milestone[1] for milestone in milestones]
    ax.plot(mx, my, "-", color="#1565c0", lw=1.0, alpha=0.45, zorder=3)
    ax.scatter(mx, my, s=70, color="#1565c0", edgecolor="black",
               linewidth=0.8, zorder=4, label="milestone controllers")

    # milestone detail table (monospace, in the empty band 0.24-0.36)
    table = "\n".join(
        [
            "Milestone controllers (11-axis geo)",
            *[
                f"R{round_id:>3}   {table_label:<23} {value:.3f}"
                for round_id, value, _, table_label in milestones
            ],
        ]
    )
    ax.text(0.025, 0.69, table, transform=ax.transAxes, fontsize=7.6,
            family="monospace", va="top", ha="left",
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#1565c0", lw=0.9))

    # headline advantage callout (right, empty region)
    final_round, final_value, _, _ = milestones[-1]
    ratio = final_value / droop_best
    ax.annotate(rf"RL SOTA $\approx {ratio:.1f}\times$ best classical droop",
                xy=(final_round, final_value), xytext=(232, 0.30),
                arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
                fontsize=8.5, ha="right",
                bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow", ec="black"))

    # programme-scale box (top-left, above the cluster)
    ax.text(0.025, 0.975,
            f"{programme['rounds']} rounds  ·  "
            f"{programme['audited_findings']} audited findings\n"
            f"{programme['algorithm_variants']} RL algorithm variants  ·  "
            f"{programme['regression_tests_min']}+ regression tests",
            transform=ax.transAxes, fontsize=8.2, va="top", ha="left",
            bbox=dict(boxstyle="round,pad=0.4", fc="#f3f7fc", ec="#1565c0", lw=1.0))

    ax.set_xlabel(f"Experimental round (R1 – R{programme['rounds']})", fontsize=10)
    ax.set_ylabel("Eleven-axis paper-grade score", fontsize=10)
    ax.set_xlim(28, 262)
    ax.set_ylim(0, 0.50)
    ax.set_title(
        f"Multi-agent VSG control: 11-axis performance across the "
        f"{programme['rounds']}-round programme",
        fontsize=10.5,
        pad=10,
    )
    ax.legend(loc="lower right", fontsize=8, framealpha=0.95)

    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"proposal_progression.{ext}", dpi=200, bbox_inches="tight")
    print("saved proposal_progression.png/.pdf to", OUT)


if __name__ == "__main__":
    main()
