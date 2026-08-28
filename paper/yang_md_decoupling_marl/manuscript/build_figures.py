"""Build corrected-card manuscript figures from frozen R481/R483/R484 analyses."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from matplotlib.ticker import PercentFormatter


ROOT = Path(__file__).resolve().parents[3]
R481_ANALYSIS = ROOT / "results/research_loop/r481_direct_md/formal_analysis.json"
R484_ANALYSIS = ROOT / "results/research_loop/r484_30s_tail_guard/formal_analysis.json"
OUT_DIR = Path(__file__).resolve().parent / "figures"

COLORS = {
    "blue": "#0072B2",
    "orange": "#D55E00",
    "green": "#009E73",
    "grey": "#777777",
    "light_grey": "#D9D9D9",
    "black": "#333333",
}


def _set_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 8,
            "axes.labelsize": 8,
            "axes.titlesize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _read_hashed_json(path: Path) -> dict:
    """Read a frozen JSON artifact only after its SHA-256 sidecar matches."""

    sidecar = path.with_name(path.name + ".sha256")
    expected = sidecar.read_text(encoding="utf-8").split()[0].lower()
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError(f"hash mismatch for {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_direct_md_horizon() -> None:
    """Show the selected deterministic law on the same fresh profiles at 6 and 30 s."""

    r481 = _read_hashed_json(R481_ANALYSIS)["phase1a_gate"]
    r484 = _read_hashed_json(R484_ANALYSIS)["deterministic_fresh_tail"]["gate"]
    if not r481["passed_4_of_4"] or not r484["passed_4_of_4"]:
        raise RuntimeError("the deterministic fresh-bank verdict changed")
    profiles = ["fresh_eva_a", "fresh_eva_b", "fresh_eva_c", "fresh_eva_d"]
    labels = ["Fresh A", "Fresh B", "Fresh C", "Fresh D"]
    metrics = [
        ("off_diagonal_ratio_to_zero", "Off-diagonal ratio to zero action"),
        ("differential_ratio_to_zero", "Differential ratio to zero action"),
    ]

    _set_style()
    fig, axes = plt.subplots(2, 1, figsize=(3.45, 2.75), constrained_layout=True)
    y = np.arange(len(profiles))[::-1]
    for panel, (ax, (metric, xlabel)) in enumerate(zip(axes, metrics)):
        six = np.asarray([r481["per_profile"][profile][metric] for profile in profiles])
        thirty = np.asarray([r484["per_profile"][profile][metric] for profile in profiles])
        for pos, left, right in zip(y, six, thirty):
            ax.plot([left, right], [pos, pos], color=COLORS["light_grey"], linewidth=1.0, zorder=1)
        ax.scatter(
            six,
            y,
            marker="o",
            s=28,
            facecolors="white",
            edgecolors=COLORS["blue"],
            linewidths=1.0,
            zorder=3,
            label="6 s primary window",
        )
        ax.scatter(
            thirty,
            y,
            marker="^",
            s=30,
            color=COLORS["orange"],
            linewidths=0.7,
            zorder=3,
            label="30 s tail",
        )
        ax.axvline(1.0, color=COLORS["black"], linestyle=":", linewidth=0.9)
        ax.set_yticks(y, labels)
        ax.set_xlim(0.25, 1.05)
        ax.set_xlabel(xlabel)
        ax.text(0.01, 0.94, f"({chr(97 + panel)})", transform=ax.transAxes, ha="left", va="top", fontsize=7.5)
        ax.grid(axis="x", color=COLORS["light_grey"], linewidth=0.45)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
    axes[0].legend(loc="lower right", frameon=True, borderpad=0.3, handletextpad=0.35)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / "direct_md_fresh_horizon.pdf", bbox_inches="tight")
    fig.savefig(OUT_DIR / "direct_md_fresh_horizon.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def build_policy_guard() -> None:
    """Show endpoint qualification and the guards that reverse that verdict."""

    data = _read_hashed_json(R484_ANALYSIS)["learned_guard"]
    decisions = data["policy_decisions"]
    blocks = data["per_profile_blocks"]
    if len(decisions) != 208 or len(blocks) != 832:
        raise RuntimeError("unexpected R484 roster size")

    endpoint_pass = np.asarray(
        [
            row["aggregate_joint_endpoint_target"]["off_diagonal_response_energy"]
            and row["aggregate_joint_endpoint_target"]["disturbance_differential_energy"]
            for row in decisions
        ],
        dtype=bool,
    )
    complete_pass = np.asarray([row["passed_complete_guard"] for row in decisions], dtype=bool)
    x = np.asarray(
        [row["aggregate_endpoint_ratios_to_deterministic"]["off_diagonal_response_energy"] for row in decisions]
    )
    y = np.asarray(
        [row["aggregate_endpoint_ratios_to_deterministic"]["disturbance_differential_energy"] for row in decisions]
    )

    failure_counts: Counter[str] = Counter()
    for row in blocks:
        failure_counts.update(row["failed_guards"])
    guard_keys = [
        "action_rms_no_harm",
        "action_variation_no_harm",
        "rocof_no_harm",
        "worst_peak_no_harm",
    ]
    counts = [failure_counts[key] for key in guard_keys]
    if endpoint_pass.sum() != 126 or complete_pass.sum() != 0:
        raise RuntimeError("R484 policy decision counts changed")
    if counts != [832, 832, 408, 45]:
        raise RuntimeError(f"R484 guard counts changed: {counts}")

    _set_style()
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(7.1, 2.55), constrained_layout=True)

    target_region = Rectangle(
        (0.3, 0.4),
        0.65,
        0.55,
        facecolor="none",
        edgecolor="#B8B8B8",
        hatch="////",
        linewidth=0.0,
        zorder=0,
    )
    ax0.add_patch(target_region)
    ax0.scatter(
        x[~endpoint_pass],
        y[~endpoint_pass],
        s=17,
        facecolors="none",
        edgecolors=COLORS["grey"],
        alpha=0.7,
        linewidths=0.65,
        label="Endpoint target not met",
    )
    ax0.scatter(
        x[endpoint_pass],
        y[endpoint_pass],
        s=15,
        color=COLORS["blue"],
        alpha=0.76,
        linewidths=0,
        label="Both endpoint targets met",
    )
    for value, style, colour in [(0.95, "--", COLORS["green"]), (1.0, ":", COLORS["black"])]:
        ax0.axvline(value, color=colour, linestyle=style, linewidth=0.85)
        ax0.axhline(value, color=colour, linestyle=style, linewidth=0.85)
    ax0.set_xscale("log")
    ax0.set_yscale("log")
    ax0.set_xlim(0.3, 10.5)
    ax0.set_ylim(0.4, 4.1)
    ax0.set_xlabel("Off-diagonal ratio to direct M/D")
    ax0.set_ylabel("Differential ratio to direct M/D")
    ax0.grid(color=COLORS["light_grey"], linewidth=0.4, which="both")
    ax0.text(
        0.02,
        0.97,
        "(a) Endpoint outcomes\n126/208 meet both targets; 0/208 complete",
        transform=ax0.transAxes,
        ha="left",
        va="top",
        fontsize=7.2,
        color=COLORS["black"],
    )
    ax0.legend(loc="lower right", frameon=True, borderpad=0.3, handletextpad=0.35)

    labels = ["Action RMS", "Action variation", "RoCoF", "Worst peak"]
    positions = np.arange(len(labels))
    rates = 100.0 * np.asarray(counts) / len(blocks)
    bars = ax1.barh(
        positions,
        rates,
        color=["#B8B8B8", "#B8B8B8", "white", "white"],
        edgecolor=COLORS["black"],
        linewidth=0.7,
        height=0.62,
    )
    for bar, hatch in zip(bars, ["////", "////", "..", ".."]):
        bar.set_hatch(hatch)
    for pos, count, rate in zip(positions, counts, rates):
        ax1.text(
            min(rate + 2.0, 98.0) if count else 1.5,
            pos,
            f"{count}/832",
            va="center",
            ha="right" if rate > 92 else "left",
            color=COLORS["black"],
            fontsize=7.2,
        )
    ax1.set_yticks(positions, labels)
    ax1.invert_yaxis()
    ax1.set_xlim(0, 105)
    ax1.xaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
    ax1.set_xlabel("Failed policy-profile blocks")
    ax1.set_title("(b) Complete-guard failures", loc="left", pad=3)
    ax1.grid(axis="x", color=COLORS["light_grey"], linewidth=0.45)
    ax1.spines[["top", "right", "left"]].set_visible(False)
    ax1.tick_params(axis="y", length=0)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / "learned_contract_tradeoff.pdf", bbox_inches="tight")
    fig.savefig(OUT_DIR / "learned_contract_tradeoff.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    build_direct_md_horizon()
    build_policy_guard()


if __name__ == "__main__":
    main()
