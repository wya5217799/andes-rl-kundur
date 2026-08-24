"""Build manuscript figures from authoritative frozen analysis artifacts."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter


ROOT = Path(__file__).resolve().parents[3]
ANALYSIS = ROOT / "results/research_loop/r477_u2_confirmatory/formal_analysis.json"
OUT_DIR = Path(__file__).resolve().parent / "figures"
R431_EVAL = ROOT / "results/research_loop/r431_sac_slew/eval"
R433_EVAL = ROOT / "results/research_loop/r433_sac_stress_penalty/eval"
TRACE_PROFILE = "canary_eval_a"
TRACE_SCENARIO = "canary_eval_a_common_positive"


def pct(log_effect: float) -> float:
    """Convert a log-ratio effect to a signed fractional geometric effect."""

    return math.exp(log_effect) - 1.0


def build_source_effect() -> None:
    data = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    rows = data["primary_materiality_tests"]
    labels = ["Actor source", "Critic source"]
    keys = ["actor", "critic"]
    means = [pct(rows[key]["mean_log_effect"]) for key in keys]
    lows = [pct(rows[key]["bootstrap_ci95_descriptive"][0]) for key in keys]
    highs = [pct(rows[key]["bootstrap_ci95_descriptive"][1]) for key in keys]
    errors = [
        [means[i] - lows[i] for i in range(len(keys))],
        [highs[i] - means[i] for i in range(len(keys))],
    ]

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 8,
            "axes.labelsize": 8,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 8,
            "legend.fontsize": 7.5,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    fig, ax = plt.subplots(figsize=(3.45, 1.75), constrained_layout=True)
    colors = ["#0072B2", "#D55E00"]
    markers = ["o", "s"]
    y = [1, 0]
    for i in range(2):
        ax.errorbar(
            means[i],
            y[i],
            xerr=[[errors[0][i]], [errors[1][i]]],
            fmt=markers[i],
            color=colors[i],
            markerfacecolor="white",
            markeredgewidth=1.2,
            markersize=5,
            elinewidth=1.2,
            capsize=3,
            zorder=3,
        )
        ax.text(
            means[i],
            y[i] + 0.22,
            f"{100 * means[i]:+.2f}%",
            color=colors[i],
            ha="center",
            va="bottom",
            fontsize=7.5,
        )

    ax.axvline(0.0, color="#555555", linewidth=0.8, linestyle="-")
    ax.axvline(0.10, color="#009E73", linewidth=1.1, linestyle="--")
    ax.text(
        0.096,
        1.36,
        "10% materiality",
        color="#00734f",
        ha="right",
        va="bottom",
        fontsize=7.2,
    )
    ax.set_yticks(y, labels)
    ax.set_ylim(-0.45, 1.55)
    ax.set_xlim(-0.115, 0.13)
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    ax.set_xlabel("Signed source effect (geometric)")
    ax.grid(axis="x", color="#d9d9d9", linewidth=0.5)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / "source_effect.pdf", bbox_inches="tight")
    fig.savefig(OUT_DIR / "source_effect.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def _read_hashed_json(path: Path) -> dict:
    """Read one sealed evaluation file after checking its SHA-256 sidecar."""

    sidecar = path.with_name(path.name + ".sha256")
    expected = sidecar.read_text(encoding="utf-8").split()[0]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError(f"hash mismatch for {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _trace(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    data = _read_hashed_json(path)
    record = next(
        row for row in data["records"] if row["scenario_id"] == TRACE_SCENARIO
    )
    if not record["completed"] or record["tds_failed"]:
        raise RuntimeError(f"incomplete physical trace in {path}")
    steps = record["steps"]
    if len(steps) != 30:
        raise RuntimeError(f"unexpected trace length in {path}: {len(steps)}")
    time = np.asarray([row["time"] for row in steps], dtype=float)
    frequency = np.asarray([row["freq_hz_physical"] for row in steps], dtype=float)
    action = np.asarray([row["action_norm"] for row in steps], dtype=float)
    common_deviation_mhz = 1000.0 * (60.0 - frequency.mean(axis=1))
    executed_action_rms = np.sqrt(np.mean(np.square(action), axis=(1, 2)))
    return time, common_deviation_mhz, executed_action_rms


def _seed_traces(root: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    traces = [
        _trace(
            root
            / "cd_matd3_message"
            / f"seed{seed}"
            / f"{TRACE_PROFILE}.json"
        )
        for seed in range(401, 406)
    ]
    time = traces[0][0]
    if any(not np.array_equal(time, row[0]) for row in traces[1:]):
        raise RuntimeError("seed traces do not share the registered time grid")
    return time, np.stack([row[1] for row in traces]), np.stack(
        [row[2] for row in traces]
    )


def build_repair_tradeoff() -> None:
    """Plot a non-data-selected physical trace from the repair ladder."""

    deterministic = _trace(
        R431_EVAL
        / "local_neighbour_md_km2_kd2"
        / "deterministic"
        / f"{TRACE_PROFILE}.json"
    )
    projected = _seed_traces(R431_EVAL)
    penalized = _seed_traces(R433_EVAL)

    fig, axes = plt.subplots(2, 1, figsize=(3.45, 3.05), sharex=True)
    colors = {"projected": "#0072B2", "penalized": "#D55E00"}
    line_styles = {"projected": "-", "penalized": "--"}
    markers = {"projected": "o", "penalized": "s"}
    labels = {
        "projected": "Projected SAC",
        "penalized": "SAC + RMS penalty",
    }
    for axis, trace_index in zip(axes, (1, 2), strict=True):
        axis.plot(
            deterministic[0],
            deterministic[trace_index],
            color="#222222",
            linewidth=1.15,
            label="Deterministic",
            zorder=4,
        )
        for name, traces in (("projected", projected), ("penalized", penalized)):
            values = traces[trace_index]
            axis.fill_between(
                traces[0],
                values.min(axis=0),
                values.max(axis=0),
                color=colors[name],
                alpha=0.13,
                linewidth=0,
            )
            axis.plot(
                traces[0],
                np.median(values, axis=0),
                color=colors[name],
                linewidth=1.15,
                linestyle=line_styles[name],
                marker=markers[name],
                markevery=5,
                markersize=2.8,
                label=labels[name],
                zorder=3,
            )
        axis.grid(color="#dddddd", linewidth=0.45)
        axis.spines[["top", "right"]].set_visible(False)
        axis.margins(x=0)

    axes[0].set_ylabel("Common deviation\n(mHz)")
    axes[1].set_ylabel("Executed action\nRMS")
    axes[1].set_xlabel("Time (s)")
    axes[0].text(0.02, 0.92, "(a)", transform=axes[0].transAxes, fontweight="bold")
    axes[1].text(0.02, 0.92, "(b)", transform=axes[1].transAxes, fontweight="bold")
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        legend_labels,
        loc="upper center",
        ncol=3,
        frameon=False,
        fontsize=6.8,
        handlelength=1.25,
        handletextpad=0.35,
        columnspacing=0.8,
        borderaxespad=0.0,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93), pad=0.45, h_pad=0.25)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / "repair_tradeoff.pdf", bbox_inches="tight")
    fig.savefig(OUT_DIR / "repair_tradeoff.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    build_source_effect()
    build_repair_tradeoff()
