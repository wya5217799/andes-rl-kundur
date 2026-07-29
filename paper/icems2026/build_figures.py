"""Regenerate ICEMS 2026 result macros and vector figures from frozen evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

PAPER_DIR = Path(__file__).resolve().parent
REPO_ROOT = PAPER_DIR.parents[1]
FIGURE_DIR = PAPER_DIR / "figures"
WORKING_DIR = PAPER_DIR / "working"


def load_json(relative_path: str) -> dict:
    with (REPO_ROOT / relative_path).open(encoding="utf-8") as stream:
        return json.load(stream)


def contrast_endpoint(summary: dict, endpoint: str) -> tuple[float, float, float]:
    contrasts = summary["paired_bootstrap"]["contrasts"]
    contrast = next(iter(contrasts.values()))
    estimate = contrast["endpoints"][endpoint]["ratio_of_means_percent"]
    low, high = estimate["percentile_95_interval"]
    return float(estimate["point"]), float(low), float(high)


def formal_endpoint(summary: dict, comparison: str, endpoint: str) -> tuple[float, float, float]:
    estimate = summary["hierarchical_bootstrap"][comparison][endpoint]["ratio_of_means_percent"]
    low, high = estimate["percentile_95_interval"]
    return float(estimate["point"]), float(low), float(high)


def paired_endpoint(summary: dict, comparison: str, endpoint: str) -> tuple[float, float, float]:
    estimate = summary["paired_bootstrap"][comparison]["endpoints"][endpoint][
        "ratio_of_means_percent"
    ]
    low, high = estimate["percentile_95_interval"]
    return float(estimate["point"]), float(low), float(high)


def format_signed(value: float, digits: int = 2) -> str:
    return f"{value:+.{digits}f}"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def physical_frequency_matrix(record: dict) -> np.ndarray:
    values = np.asarray(
        [step["delta_f_physical_hz"] for step in record["traces"]],
        dtype=float,
    )
    if values.ndim != 2 or values.shape[1] != 4:
        raise ValueError("physical frequency trace must have shape [time, 4]")
    if not np.all(np.isfinite(values)):
        raise ValueError("physical frequency trace contains non-finite values")
    return values


def select_fixed_formal_scenario(formal_bank: dict) -> tuple[str, dict]:
    """Select a trace by manifest order without consulting controller outcomes."""

    selected = next(row for row in formal_bank["scenarios"] if row["severity"] == "moderate")
    scenario = selected["name"]
    trace_paths = {
        arm: (REPO_ROOT / "results/r279_formal_evaluation/traces" / f"{scenario}__{arm}.json")
        for arm in (
            "q0",
            "centralized_s17",
            "centralized_s53",
            "centralized_s89",
            "shared_s17",
            "shared_s53",
            "shared_s89",
        )
    }
    if not all(path.exists() for path in trace_paths.values()):
        missing = [str(path) for path in trace_paths.values() if not path.exists()]
        raise FileNotFoundError(f"missing formal traces: {missing}")
    selection = {
        "schema_version": 2,
        "selection_rule": (
            "Select the first moderate-severity scenario in the immutable "
            "formal-bank manifest order; do not inspect controller outcomes."
        ),
        "formal_bank_sha256": file_sha256(REPO_ROOT / "results/r279_fresh_bank/formal_bank.json"),
        "selected": selected,
        "trace_sha256": {arm: file_sha256(path) for arm, path in trace_paths.items()},
    }
    WORKING_DIR.mkdir(parents=True, exist_ok=True)
    (WORKING_DIR / "dynamic_response_selection.json").write_text(
        json.dumps(selection, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return scenario, selection


def write_result_macros(
    r274: dict,
    r275: dict,
    r277: dict,
    formal: dict,
    correction: dict,
) -> None:
    rows = {
        "SlowIae": contrast_endpoint(r274, "vsg_mean_iae_hz_s"),
        "SlowFinal": contrast_endpoint(r274, "final_window_common_abs_mean_hz"),
        "FastRocof": contrast_endpoint(r275, "max_abs_rocof_hz_s"),
        "FastPeak": contrast_endpoint(r275, "worst_bus_peak_abs_hz"),
        "FastSync": contrast_endpoint(r275, "normalized_sync_loss_hz2"),
        "FastArea": contrast_endpoint(r275, "fast_inter_area_iae_hz_s"),
        "OracleSync": contrast_endpoint(r277, "normalized_sync_loss_hz2"),
        "OracleArea": contrast_endpoint(r277, "fast_inter_area_iae_hz_s"),
        "CausalSync": paired_endpoint(formal, "causal_vs_q0", "normalized_sync_loss_hz2"),
        "CausalArea": paired_endpoint(formal, "causal_vs_q0", "fast_inter_area_iae_hz_s"),
        "CentralSync": formal_endpoint(formal, "centralized_vs_q0", "normalized_sync_loss_hz2"),
        "CentralArea": formal_endpoint(formal, "centralized_vs_q0", "fast_inter_area_iae_hz_s"),
        "SharedSync": formal_endpoint(formal, "shared_vs_q0", "normalized_sync_loss_hz2"),
        "SharedArea": formal_endpoint(formal, "shared_vs_q0", "fast_inter_area_iae_hz_s"),
        "SharedCentralSync": formal_endpoint(
            formal, "shared_vs_centralized", "normalized_sync_loss_hz2"
        ),
        "SharedCentralArea": formal_endpoint(
            formal, "shared_vs_centralized", "fast_inter_area_iae_hz_s"
        ),
    }

    macro_lines = [
        "% Generated by build_figures.py from frozen R274--R280 evidence.",
    ]
    for name, (point, low, high) in rows.items():
        macro_lines.append(rf"\newcommand{{\{name}Effect}}{{{format_signed(point)}}}")
        macro_lines.append(
            rf"\newcommand{{\{name}CI}}{{[{format_signed(low)}, "
            rf"{format_signed(high)}]}}"
        )
    macro_lines.extend(
        [
            (
                r"\newcommand{\FormalMaxCommand}{"
                + f"{max(row['max_abs_commanded_power_system_pu'] for row in formal['absolute_storage_guards'].values()):.6f}"
                + "}"
            ),
            (
                r"\newcommand{\FormalMinSoc}{"
                + f"{min(row['min_soc'] for row in formal['absolute_storage_guards'].values()):.6f}"
                + "}"
            ),
            (
                r"\newcommand{\FormalMaxSoc}{"
                + f"{max(row['max_soc'] for row in formal['absolute_storage_guards'].values()):.6f}"
                + "}"
            ),
            (
                r"\newcommand{\AuditOneUlp}{"
                + f"{correction['float32_contract']['one_ulp_tolerance']:.6e}"
                + "}"
            ),
            (
                r"\newcommand{\AuditMaxExcess}{"
                + f"{correction['float32_contract']['maximum_observed_slew_excess']:.6e}"
                + "}"
            ),
            "",
        ]
    )
    (PAPER_DIR / "generated_results.tex").write_text("\n".join(macro_lines), encoding="utf-8")


def draw_forest_panel(
    axis: plt.Axes,
    rows: list[tuple[str, float, float, float, str]],
    xlim: tuple[float, float],
    title: str,
) -> None:
    palette = {
        "slow": "#009E73",
        "fast": "#CC79A7",
        "oracle": "#7A7A7A",
        "central": "#0072B2",
        "shared": "#D55E00",
    }
    markers = {
        "slow": "o",
        "fast": "s",
        "oracle": "D",
        "central": "s",
        "shared": "o",
    }
    y_values = list(range(len(rows)))[::-1]
    for y, (label, point, low, high, group) in zip(y_values, rows, strict=True):
        axis.errorbar(
            point,
            y,
            xerr=[[point - low], [high - point]],
            fmt=markers[group],
            markersize=5.2,
            markerfacecolor=palette[group],
            markeredgecolor=palette[group],
            markeredgewidth=1.1,
            ecolor=palette[group],
            elinewidth=1.1,
            capsize=2.2,
            zorder=3,
        )
    axis.axvline(0, color="#333333", linewidth=0.9)
    axis.set_yticks(y_values, [row[0] for row in rows])
    axis.set_xlim(*xlim)
    axis.set_title(title, loc="left", fontweight="bold", pad=4)
    axis.grid(axis="x", color="#D9D9D9", linewidth=0.5)
    axis.set_axisbelow(True)
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.tick_params(axis="y", length=0, pad=3)
    axis.set_xlabel("Effect relative to matched reference (%)")


def write_paired_effect_figure(r274: dict, r275: dict, r277: dict, formal: dict) -> None:
    classical = [
        ("Mean-frequency IAE", *contrast_endpoint(r274, "vsg_mean_iae_hz_s"), "slow"),
        (
            "Final-window common error",
            *contrast_endpoint(r274, "final_window_common_abs_mean_hz"),
            "slow",
        ),
        ("Maximum RoCoF", *contrast_endpoint(r275, "max_abs_rocof_hz_s"), "fast"),
        (
            "Worst-bus peak",
            *contrast_endpoint(r275, "worst_bus_peak_abs_hz"),
            "fast",
        ),
        (
            "Synchronization loss",
            *contrast_endpoint(r275, "normalized_sync_loss_hz2"),
            "fast",
        ),
        (
            "Early inter-area IAE",
            *contrast_endpoint(r275, "fast_inter_area_iae_hz_s"),
            "fast",
        ),
    ]
    learned = [
        (
            r"Central vs $q=0$: sync",
            *formal_endpoint(formal, "centralized_vs_q0", "normalized_sync_loss_hz2"),
            "central",
        ),
        (
            r"Central vs $q=0$: area IAE",
            *formal_endpoint(formal, "centralized_vs_q0", "fast_inter_area_iae_hz_s"),
            "central",
        ),
        (
            r"Shared vs $q=0$: sync",
            *formal_endpoint(formal, "shared_vs_q0", "normalized_sync_loss_hz2"),
            "shared",
        ),
        (
            r"Shared vs $q=0$: area IAE",
            *formal_endpoint(formal, "shared_vs_q0", "fast_inter_area_iae_hz_s"),
            "shared",
        ),
        (
            "Shared vs central: sync",
            *formal_endpoint(formal, "shared_vs_centralized", "normalized_sync_loss_hz2"),
            "shared",
        ),
        (
            "Shared vs central: area IAE",
            *formal_endpoint(
                formal,
                "shared_vs_centralized",
                "fast_inter_area_iae_hz_s",
            ),
            "shared",
        ),
    ]

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": 8.0,
            "axes.titlesize": 8.4,
            "axes.labelsize": 8.0,
            "xtick.labelsize": 8.0,
            "ytick.labelsize": 8.0,
            "legend.fontsize": 8.0,
            "mathtext.fontset": "stix",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    figure, axes = plt.subplots(
        1,
        2,
        figsize=(7.15, 2.90),
        gridspec_kw={"width_ratios": [1.05, 1.15], "wspace": 0.58},
    )
    draw_forest_panel(
        axes[0],
        classical,
        (-82, 5),
        "(a) Classical mechanism checks",
    )
    draw_forest_panel(
        axes[1],
        learned,
        (-36, 32),
        "(b) Architecture comparison",
    )
    legend = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="#009E73",
            markeredgecolor="#009E73",
            label="Slow restoration",
        ),
        Line2D(
            [0],
            [0],
            marker="s",
            color="none",
            markerfacecolor="#CC79A7",
            markeredgecolor="#CC79A7",
            label="Fast common pulse",
        ),
        Line2D(
            [0],
            [0],
            marker="s",
            color="none",
            markerfacecolor="#0072B2",
            markeredgecolor="#0072B2",
            label="Centralized TD3",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="#D55E00",
            markeredgecolor="#D55E00",
            label="Shared MARL",
        ),
    ]
    figure.legend(
        handles=legend,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.01),
        ncol=4,
        frameon=False,
        handletextpad=0.4,
        columnspacing=1.0,
    )
    figure.subplots_adjust(left=0.20, right=0.985, top=0.88, bottom=0.23)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    figure.savefig(FIGURE_DIR / "paired_effects.pdf", bbox_inches="tight")
    plt.close(figure)


def style_time_axis(axis: plt.Axes) -> None:
    axis.axvline(
        3.0,
        color="#777777",
        linewidth=0.75,
        linestyle=(0, (2, 2)),
        zorder=1,
    )
    axis.grid(color="#E1E1E1", linewidth=0.45)
    axis.set_axisbelow(True)
    axis.spines[["top", "right"]].set_visible(False)
    axis.set_xlabel("Time (s)")


def response_series(record: dict) -> dict[str, np.ndarray]:
    steps = record["traces"]
    frequency = physical_frequency_matrix(record)
    inertia = np.asarray([step["M_es"] for step in steps], dtype=float)
    return {
        "time": np.asarray([step["t"] for step in steps], dtype=float),
        "common": np.mean(frequency, axis=1),
        "area": np.mean(frequency[:, :2], axis=1) - np.mean(frequency[:, 2:], axis=1),
        "q": np.asarray([step["r278_q"] for step in steps], dtype=float),
        "m_area_a": np.mean(inertia[:, :2], axis=1),
        "m_area_b": np.mean(inertia[:, 2:], axis=1),
        "power": np.sum(
            np.asarray(
                [step["bess_actual_power_system_pu"] for step in steps],
                dtype=float,
            ),
            axis=1,
        ),
    }


def seed_band(records: list[dict], key: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = np.stack([response_series(record)[key] for record in records])
    return np.mean(values, axis=0), np.min(values, axis=0), np.max(values, axis=0)


def plot_seed_band(
    axis: plt.Axes,
    time: np.ndarray,
    records: list[dict],
    key: str,
    *,
    color: str,
    linestyle: str | tuple,
    drawstyle: str = "default",
    linewidth: float = 1.15,
    band_alpha: float = 0.12,
) -> None:
    mean, low, high = seed_band(records, key)
    step = "post" if drawstyle == "steps-post" else None
    axis.fill_between(
        time,
        low,
        high,
        color=color,
        alpha=band_alpha,
        linewidth=0,
        step=step,
    )
    axis.plot(
        time,
        mean,
        color=color,
        linewidth=linewidth,
        linestyle=linestyle,
        drawstyle=drawstyle,
    )


def write_dynamic_response_figure(scenario: str, selection: dict) -> None:
    trace_dir = REPO_ROOT / "results/r279_formal_evaluation/traces"

    def trace(arm: str) -> dict:
        return load_json(str((trace_dir / f"{scenario}__{arm}.json").relative_to(REPO_ROOT)))

    reference = trace("q0")
    centralized = [trace(f"centralized_s{seed}") for seed in (17, 53, 89)]
    shared = [trace(f"shared_s{seed}") for seed in (17, 53, 89)]
    reference_series = response_series(reference)
    time_absolute = reference_series["time"]
    for record in centralized + shared:
        candidate_time = response_series(record)["time"]
        if candidate_time.shape != time_absolute.shape or not np.allclose(
            candidate_time, time_absolute, atol=1e-12, rtol=0.0
        ):
            raise ValueError("formal trace time grids differ")
    time = time_absolute - time_absolute[0]

    central_color = "#0072B2"
    shared_color = "#D55E00"
    reference_color = "#333333"
    figure = plt.figure(figsize=(7.15, 3.70))
    grid = figure.add_gridspec(
        2,
        6,
        height_ratios=[1.0, 0.92],
        hspace=0.64,
        wspace=1.0,
    )
    axes = [
        figure.add_subplot(grid[0, :3]),
        figure.add_subplot(grid[0, 3:]),
        figure.add_subplot(grid[1, :2]),
        figure.add_subplot(grid[1, 2:4]),
        figure.add_subplot(grid[1, 4:]),
    ]
    common_axis, area_axis, q_axis, inertia_axis, power_axis = axes

    for axis, key in ((common_axis, "common"), (area_axis, "area")):
        plot_seed_band(
            axis,
            time,
            centralized,
            key,
            color=central_color,
            linestyle="-",
        )
        plot_seed_band(
            axis,
            time,
            shared,
            key,
            color=shared_color,
            linestyle="-.",
        )
        axis.plot(
            time,
            reference_series[key],
            color=reference_color,
            linewidth=1.0,
            linestyle="--",
        )

    common_axis.set_ylabel(r"Common $\Delta f$ (Hz)")
    common_axis.set_title("(a) Common frequency", loc="left", fontweight="bold")
    area_axis.set_ylabel(r"$\Delta f_{\mathrm{AB}}$ (Hz)")
    area_axis.set_title(
        "(b) Inter-area frequency",
        loc="left",
        fontweight="bold",
    )

    plot_seed_band(
        q_axis,
        time,
        centralized,
        "q",
        color=central_color,
        linestyle="-",
        drawstyle="steps-post",
        linewidth=1.0,
        band_alpha=0.08,
    )
    plot_seed_band(
        q_axis,
        time,
        shared,
        "q",
        color=shared_color,
        linestyle="-.",
        drawstyle="steps-post",
        linewidth=1.0,
        band_alpha=0.08,
    )
    for bound in (-0.25, 0.25):
        q_axis.axhline(
            bound,
            color="#A5A5A5",
            linewidth=0.65,
            linestyle=(0, (1.5, 1.5)),
            zorder=1,
        )
    q_axis.axhline(0.0, color=reference_color, linewidth=0.9, linestyle="--")
    q_axis.set_ylabel(r"Residual $q_k$")
    q_axis.set_title("(c) Differential action", loc="left", fontweight="bold")
    q_axis.set_xlim(0, 4)
    q_axis.set_ylim(-0.29, 0.29)

    for records, color, area_a_style, area_b_style in (
        (centralized, central_color, "-", (0, (1.5, 1.5))),
        (shared, shared_color, "-.", (0, (4, 1, 1, 1, 1, 1))),
    ):
        mean_a, _, _ = seed_band(records, "m_area_a")
        mean_b, _, _ = seed_band(records, "m_area_b")
        inertia_axis.plot(
            time,
            mean_a,
            color=color,
            linewidth=1.0,
            linestyle=area_a_style,
            drawstyle="steps-post",
        )
        inertia_axis.plot(
            time,
            mean_b,
            color=color,
            linewidth=0.75,
            linestyle=area_b_style,
            drawstyle="steps-post",
        )
    inertia_axis.plot(
        time,
        reference_series["m_area_a"],
        color=reference_color,
        linewidth=0.9,
        linestyle="--",
        drawstyle="steps-post",
    )
    inertia_axis.set_ylabel(r"Executed $M_A,M_B$ (s)")
    inertia_axis.set_title(
        "(d) Inertia setpoints",
        loc="left",
        fontweight="bold",
    )
    inertia_axis.set_xlim(0, 4)

    plot_seed_band(
        power_axis,
        time,
        centralized,
        "power",
        color=central_color,
        linestyle="-",
    )
    plot_seed_band(
        power_axis,
        time,
        shared,
        "power",
        color=shared_color,
        linestyle="-.",
    )
    power_axis.plot(
        time,
        reference_series["power"],
        color=reference_color,
        linewidth=1.0,
        linestyle="--",
    )
    power_axis.set_ylabel(r"Fleet $P_{\mathrm{BESS}}$ (pu)")
    power_axis.set_title("(e) Storage output", loc="left", fontweight="bold")

    for axis in axes:
        style_time_axis(axis)
    common_axis.set_xlim(0, float(time[-1]))
    area_axis.set_xlim(0, float(time[-1]))
    power_axis.set_xlim(0, float(time[-1]))

    global_legend = [
        Line2D(
            [0],
            [0],
            color=central_color,
            linewidth=1.3,
            label="Centralized TD3 mean",
        ),
        Line2D(
            [0],
            [0],
            color=shared_color,
            linewidth=1.3,
            linestyle="-.",
            label="Shared MARL mean",
        ),
        Line2D(
            [0],
            [0],
            color=reference_color,
            linewidth=1.1,
            linestyle="--",
            label="q=0 reference",
        ),
        Line2D(
            [0],
            [0],
            color="#777777",
            linewidth=0.9,
            linestyle=(0, (2, 2)),
            label="Scheduled end of 3-s window",
        ),
    ]
    figure.legend(
        handles=global_legend,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.01),
        ncol=4,
        frameon=False,
        handlelength=2.1,
        columnspacing=1.0,
    )
    figure.subplots_adjust(
        left=0.09,
        right=0.985,
        top=0.88,
        bottom=0.12,
    )
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    figure.savefig(FIGURE_DIR / "dynamic_response.pdf", bbox_inches="tight")
    plt.close(figure)

    print(
        "dynamic response: "
        f"{selection['selected']['name']} "
        "(first moderate scenario in formal-bank manifest order)"
    )


def main() -> None:
    r274 = load_json(
        "results/r274_prospective_active_power_authority/active_power_authority_summary.json"
    )
    r275 = load_json("results/r275_fast_md_authority/fast_md_authority_summary.json")
    r277 = load_json("results/r277_learning_gap_oracle/learning_gap_oracle_summary.json")
    formal_bank = load_json("results/r279_fresh_bank/formal_bank.json")
    formal = load_json("results/r279_formal_evaluation/formal_summary.json")
    correction = load_json("results/r280_r279_action_audit_correction/correction_summary.json")
    write_result_macros(r274, r275, r277, formal, correction)
    write_paired_effect_figure(r274, r275, r277, formal)
    scenario, selection = select_fixed_formal_scenario(formal_bank)
    write_dynamic_response_figure(scenario, selection)


if __name__ == "__main__":
    main()
