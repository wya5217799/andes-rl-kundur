#!/usr/bin/env python3
"""Recompute the arithmetic and unit-of-analysis checks for the R402 causal audit.

This script uses only the values transcribed into ``r402_audit_input.json``.
It does not claim to verify the repository hashes or regenerate simulator outputs.

Outputs
-------
- r402_audit_recomputed.json
- endpoint_ratios.csv
- message_contrasts.csv
- guard_checks.csv
- action_diagnostics_derived.csv
- frequency_cost_reconstruction_derived.csv
- multiplier_tail_derived.csv

Usage
-----
python r402_recompute.py --input r402_audit_input.json --outdir generated
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ABS_TOL = 5e-7
REL_TOL = 5e-5


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Input file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def is_close(actual: float, expected: float) -> bool:
    return math.isclose(actual, expected, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def records_json_safe(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame to strict-JSON records, mapping missing values to null."""

    safe = df.astype(object).where(pd.notna(df), None)
    return safe.to_dict(orient="records")


def calculate_counts(data: dict[str, Any]) -> dict[str, int]:
    d = data["design"]
    n_arms = len(d["arms"])
    n_seeds = len(d["seeds"])
    n_profiles = int(d["evaluation_profiles"])
    n_traj = int(d["trajectories_per_profile"])
    n_det = int(d["deterministic_controllers"])

    learning_files = n_arms * n_seeds * n_profiles
    deterministic_files = n_det * n_profiles
    learning_trajectories = learning_files * n_traj
    deterministic_trajectories = deterministic_files * n_traj
    total_trajectories = learning_trajectories + deterministic_trajectories
    total_files = learning_files + deterministic_files
    arm_seed_profile_blocks = n_arms * n_seeds * n_profiles

    action_component_samples_per_arm_seed = (
        n_profiles
        * n_traj
        * int(d["steps_per_trajectory"])
        * int(d["actors"])
        * int(d["action_components_per_actor"])
    )

    total_interaction_steps = int(d["number_of_runs"]) * int(
        d["interaction_steps_per_run"]
    )
    total_attempted_episodes = int(d["number_of_runs"]) * int(
        d["attempted_episodes_per_run"]
    )

    require(
        int(d["attempted_episodes_per_run"]) * int(d["steps_per_trajectory"])
        == int(d["interaction_steps_per_run"]),
        "Per-run episode and interaction-step counts are inconsistent.",
    )

    return {
        "learning_files": learning_files,
        "deterministic_files": deterministic_files,
        "total_files": total_files,
        "learning_trajectories": learning_trajectories,
        "deterministic_trajectories": deterministic_trajectories,
        "total_trajectories": total_trajectories,
        "arm_seed_profile_blocks": arm_seed_profile_blocks,
        "action_component_samples_per_arm_seed": action_component_samples_per_arm_seed,
        "total_interaction_steps": total_interaction_steps,
        "total_attempted_episodes": total_attempted_episodes,
    }


def calculate_endpoint_tables(data: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    det = data["deterministic_endpoints"]
    det_cross = float(det["off_diagonal_response_energy"])
    det_diff = float(det["disturbance_differential_energy"])

    df = pd.DataFrame(data["learning_endpoints"]).copy()
    df["cross_ratio_vs_det"] = df["off_diagonal_response_energy"] / det_cross
    df["differential_ratio_vs_det"] = (
        df["disturbance_differential_energy"] / det_diff
    )
    df["cross_degradation_pct"] = 100.0 * (df["cross_ratio_vs_det"] - 1.0)
    df["differential_degradation_pct"] = 100.0 * (
        df["differential_ratio_vs_det"] - 1.0
    )

    medians = (
        df.groupby("arm", sort=False)[
            ["off_diagonal_response_energy", "disturbance_differential_energy"]
        ]
        .median()
        .reset_index()
    )
    medians["cross_ratio_vs_det"] = (
        medians["off_diagonal_response_energy"] / det_cross
    )
    medians["differential_ratio_vs_det"] = (
        medians["disturbance_differential_energy"] / det_diff
    )

    expected = {
        "scalar TD3": (4.1153, 2.9155),
        "CD-MATD3, no message": (4.1621, 3.1263),
        "CD-MATD3, message": (5.0917, 3.2992),
    }
    for _, row in medians.iterrows():
        exp_cross, exp_diff = expected[row["arm"]]
        require(
            is_close(float(row["cross_ratio_vs_det"]), exp_cross),
            f"Cross ratio mismatch for {row['arm']}",
        )
        require(
            is_close(float(row["differential_ratio_vs_det"]), exp_diff),
            f"Differential ratio mismatch for {row['arm']}",
        )

    msg = medians.set_index("arm").loc["CD-MATD3, message"]
    contrasts: list[dict[str, Any]] = []
    for comparator in ("CD-MATD3, no message", "scalar TD3"):
        comp = medians.set_index("arm").loc[comparator]
        for label, col in (
            ("cross", "off_diagonal_response_energy"),
            ("differential", "disturbance_differential_energy"),
        ):
            increment = 100.0 * (float(comp[col]) - float(msg[col])) / float(comp[col])
            contrasts.append(
                {
                    "contrast": f"message vs {comparator}",
                    "metric": label,
                    "positive_means_message_improves_pct": increment,
                    "aggregation": "difference of three-seed arm medians divided by comparator median",
                }
            )

    # Seedwise matched signs are informative descriptively but are not population inference.
    pivot = df.pivot(index="seed", columns="arm")
    for seed in sorted(df["seed"].unique()):
        for label, col in (
            ("cross", "off_diagonal_response_energy"),
            ("differential", "disturbance_differential_energy"),
        ):
            no_msg = float(pivot.loc[seed, (col, "CD-MATD3, no message")])
            msg_value = float(pivot.loc[seed, (col, "CD-MATD3, message")])
            contrasts.append(
                {
                    "contrast": "message vs CD-MATD3, no message",
                    "metric": label,
                    "seed": int(seed),
                    "positive_means_message_improves_pct": 100.0
                    * (no_msg - msg_value)
                    / no_msg,
                    "aggregation": "seedwise matched descriptive contrast",
                }
            )

    contrast_df = pd.DataFrame(contrasts)
    contrast_df["seed"] = contrast_df["seed"].astype("Int64")

    expected_contrasts = {
        ("message vs CD-MATD3, no message", "cross"): -22.3354579787,
        ("message vs CD-MATD3, no message", "differential"): -5.5327468757,
        ("message vs scalar TD3", "cross"): -23.7258816508,
        ("message vs scalar TD3", "differential"): -13.1623237582,
    }
    median_rows = contrast_df[
        contrast_df["aggregation"].str.startswith("difference")
    ]
    for _, row in median_rows.iterrows():
        key = (str(row["contrast"]), str(row["metric"]))
        require(
            is_close(
                float(row["positive_means_message_improves_pct"]),
                expected_contrasts[key],
            ),
            f"Message contrast mismatch for {key}",
        )

    return df, contrast_df


def calculate_guard_checks(data: dict[str, Any]) -> pd.DataFrame:
    thresholds = data["registered_thresholds"]
    df = pd.DataFrame(data["guard_ratios"]).copy()
    mapping = {
        "common_iae_ratio": thresholds["common_iae_ratio"],
        "worst_peak_ratio": thresholds["worst_peak_ratio"],
        "rocof_ratio": thresholds["rocof_ratio"],
        "action_rms_ratio": thresholds["action_rms_ratio"],
        "action_tv_ratio": thresholds["action_tv_ratio"],
    }
    for col, ceiling in mapping.items():
        df[f"{col}_passes"] = df[col] <= float(ceiling)
        df[f"{col}_multiple_of_ceiling"] = df[col] / float(ceiling)
        require(
            bool((df[col] > float(ceiling)).all()),
            f"At least one per-run worst {col} does not exceed its ceiling.",
        )
    df["all_displayed_worst_guards_pass"] = df[
        [f"{col}_passes" for col in mapping]
    ].all(axis=1)
    return df


def calculate_action_diagnostics(data: dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame(data["action_diagnostics"]).copy()
    det = df.loc[df["arm"] == "deterministic"].iloc[0]
    df["mean_abs_action_ratio_vs_det"] = (
        df["mean_abs_action"] / float(det["mean_abs_action"])
    )
    df["slew_limit_fraction_ratio_vs_det"] = (
        df["fraction_at_slew_limit"] / float(det["fraction_at_slew_limit"])
    )
    return df


def calculate_frequency_cost_diagnostics(data: dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame(data["frequency_cost_reconstruction"]).copy()
    det = df.loc[df["arm"] == "deterministic"].iloc[0]
    df["common_cost_ratio_vs_det"] = (
        df["total_common_cost"] / float(det["total_common_cost"])
    )
    df["frequency_only_diff_ratio_vs_det"] = (
        df["frequency_only_differential_total"]
        / float(det["frequency_only_differential_total"])
    )
    learning = df[df["arm"] != "deterministic"]
    require(
        bool((learning["common_cost_ratio_vs_det"] > 1.0).all()),
        "A learning run is not worse than deterministic in reconstructed common cost.",
    )
    require(
        bool((learning["frequency_only_diff_ratio_vs_det"] > 1.0).all()),
        "A learning run is not worse than deterministic in frequency-only differential cost.",
    )
    return df


def calculate_multiplier_tail(data: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    m = data["multiplier_tail"]
    budget = float(m["budget"])
    eta = float(m["step_size"])
    df = pd.DataFrame(m["runs"]).copy()
    df["min_unprojected_delta_lambda"] = eta * (df["cc_min"] - budget)
    df["median_unprojected_delta_lambda"] = eta * (df["cc_median"] - budget)
    df["max_unprojected_delta_lambda"] = eta * (df["cc_max"] - budget)
    df["tail_lambda_below_initial"] = df["lambda_max"] < float(m["initial_lambda"])
    df["tail_touches_zero"] = df["lambda_min"] == 0.0
    df["final_lambda_positive"] = df["lambda_final"] > 0.0
    df["median_cost_below_budget"] = df["cc_median"] < budget

    require(bool(df["tail_lambda_below_initial"].all()), "A tail lambda reaches the initial value.")
    require(bool(df["tail_touches_zero"].all()), "A tail trace does not touch zero.")
    require(bool(df["final_lambda_positive"].all()), "A final lambda is not positive.")
    require(bool(df["median_cost_below_budget"].all()), "A tail median common cost is not below budget.")

    aggregate = m["aggregate_common_cost"]
    derived = {
        "aggregate_unprojected_delta_lambda_at_min_cost": eta
        * (float(aggregate["minimum"]) - budget),
        "aggregate_unprojected_delta_lambda_at_median_cost": eta
        * (float(aggregate["median"]) - budget),
        "aggregate_unprojected_delta_lambda_at_max_cost": eta
        * (float(aggregate["maximum"]) - budget),
        "largest_tail_lambda_observed": float(df["lambda_max"].max()),
        "largest_final_lambda": float(df["lambda_final"].max()),
        "smallest_final_lambda": float(df["lambda_final"].min()),
        "minimum_number_of_below_budget_cost_samples_per_run_implied_by_median": 10,
        "minimum_number_across_six_runs": 60,
        "important_limit": (
            "Only marginal final-20 summaries are available; the full chronological path, "
            "cost/lambda pairing semantics, and actor-update alignment are unavailable."
        ),
    }
    return df, derived


def calculate_energy_port(data: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for round_name, values in data["energy_port"].items():
        output[round_name] = {
            **values,
            "differential_improvement_pct": 100.0
            * (1.0 - float(values["differential_ratio"])),
            "cross_improvement_pct": 100.0 * (1.0 - float(values["cross_ratio"])),
        }
    return output


def write_outputs(input_path: Path, outdir: Path) -> dict[str, Any]:
    data = load_json(input_path)
    outdir.mkdir(parents=True, exist_ok=True)

    counts = calculate_counts(data)
    endpoint_df, contrast_df = calculate_endpoint_tables(data)
    guard_df = calculate_guard_checks(data)
    action_df = calculate_action_diagnostics(data)
    cost_df = calculate_frequency_cost_diagnostics(data)
    multiplier_df, multiplier_derived = calculate_multiplier_tail(data)
    energy_port = calculate_energy_port(data)

    # Recompute arm medians separately for a clean export.
    det_cross = float(data["deterministic_endpoints"]["off_diagonal_response_energy"])
    det_diff = float(data["deterministic_endpoints"]["disturbance_differential_energy"])
    arm_medians = (
        endpoint_df.groupby("arm", sort=False)[
            ["off_diagonal_response_energy", "disturbance_differential_energy"]
        ]
        .median()
        .reset_index()
    )
    arm_medians["cross_ratio_vs_det"] = arm_medians["off_diagonal_response_energy"] / det_cross
    arm_medians["differential_ratio_vs_det"] = arm_medians["disturbance_differential_energy"] / det_diff

    # Mechanical consistency checks requested by the audit.
    require(counts["total_files"] == 40, "Expected 40 evaluation JSON files.")
    require(counts["learning_trajectories"] == 216, "Expected 216 learning trajectories.")
    require(counts["deterministic_trajectories"] == 24, "Expected 24 deterministic trajectories.")
    require(counts["total_trajectories"] == 240, "Expected 240 total trajectories.")
    require(counts["arm_seed_profile_blocks"] == 36, "Expected 36 learning blocks.")
    require(counts["action_component_samples_per_arm_seed"] == 5760, "Expected 5,760 action-component samples.")
    require(counts["total_interaction_steps"] == 388800, "Total interaction-step count mismatch.")
    require(counts["total_attempted_episodes"] == 12960, "Total attempted-episode count mismatch.")

    endpoint_df.to_csv(outdir / "endpoint_ratios.csv", index=False)
    arm_medians.to_csv(outdir / "endpoint_arm_medians.csv", index=False)
    contrast_df.to_csv(outdir / "message_contrasts.csv", index=False)
    guard_df.to_csv(outdir / "guard_checks.csv", index=False)
    action_df.to_csv(outdir / "action_diagnostics_derived.csv", index=False)
    cost_df.to_csv(outdir / "frequency_cost_reconstruction_derived.csv", index=False)
    multiplier_df.to_csv(outdir / "multiplier_tail_derived.csv", index=False)

    output = {
        "source_boundary": data["metadata"]["source_scope_note"],
        "all_assertions_passed": True,
        "counts": counts,
        "arm_seed_median_endpoints": records_json_safe(arm_medians),
        "message_contrasts": records_json_safe(contrast_df),
        "guard_summary": {
            "all_nine_per_run_worst_rows_exceed_every_displayed_ceiling": bool(
                (~guard_df["all_displayed_worst_guards_pass"]).all()
            ),
            "minimum_observed_ratio_by_guard": {
                col: float(guard_df[col].min())
                for col in (
                    "common_iae_ratio",
                    "worst_peak_ratio",
                    "rocof_ratio",
                    "action_rms_ratio",
                    "action_tv_ratio",
                )
            },
        },
        "multiplier_tail": multiplier_derived,
        "energy_port": energy_port,
        "unit_of_analysis_warnings": [
            "The seed median has n=3 seeds per arm; trajectories are not independent seeds.",
            "The 36 arm-seed-profile blocks are repeated conditions nested within nine trained policies.",
            "The 5,760 action-component samples per arm-seed are serially and cross-sectionally dependent.",
            "The 120 retained tail episodes are nested within six runs and are not 120 independent runs.",
            "R408/R409 are separate fixed-controller objects and must not be pooled numerically with R402.",
        ],
        "interpretive_limits": [
            "The post-hoc differential reconstruction omits the T_d P_es term and is not the complete training objective.",
            "A small multiplier does not imply a small lambda times Q_c value or action-gradient contribution.",
            "The arithmetic checks do not verify repository hashes, simulator execution, or missing provenance files.",
        ],
    }
    (outdir / "r402_audit_recomputed.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).with_name("r402_audit_input.json"),
        help="Path to the transcribed audit input JSON.",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path(__file__).with_name("generated"),
        help="Directory for generated JSON/CSV files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = write_outputs(args.input, args.outdir)
    print(json.dumps(output["counts"], ensure_ascii=False, indent=2))
    print(f"All assertions passed. Outputs written to: {args.outdir.resolve()}")


if __name__ == "__main__":
    main()
