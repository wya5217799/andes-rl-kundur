"""Extend the sealed R485 post-run audit without changing formal evidence.

Motivation
----------
The registered R485 analysis reports the frozen factorial decisions and the
combined action guard.  Manuscript close-out also needs three read-only views:

1. confidence bounds for the registered Hodges-Lehmann seed estimands;
2. separate M/D command-activity metrics across raw, projected, executed, and
   decoded commands; and
3. an endpoint/command/frequency failure map.

Usage
-----
``python tmp/yang-md-decoupling-marl/r485_offline_extension.py``

Failure modes
-------------
The script fails closed on a missing/hash-invalid trace, unexpected roster,
shape mismatch, mismatch with the earlier full post-run replay, or a failed
exact-interval inversion check.  It writes only under ``tmp/`` and never edits
the seal, plan, formal result, manuscript, claim, or round ledger.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tmp"))

import r485_postrun_data_audit as base  # noqa: E402
from andes_rl_kundur.evaluation import r485_experiment as exp  # noqa: E402


RESULT_ROOT = (
    REPO
    / "results/research_loop/r485_60hz_source_factorial/r485-formal-20260829-a"
)
CONFIG_PATH = REPO / "memory/rounds/R485/config.json"
SEAL_PATH = REPO / "memory/rounds/R485/formal_seal.json"
FORMAL_ANALYSIS_PATH = RESULT_ROOT / "formal_analysis.json"
PRIOR_AUDIT_PATH = REPO / "tmp/r485_postrun_data_audit.json"
OUTPUT_ROOT = REPO / "tmp/yang-md-decoupling-marl/r485_offline_extension"
REFERENCE_ARM = "local_neighbour_md_km2_kd2"
MATERIALITY_RATIO = 1.10
FAMILY_SIZE = 4


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def exact_signed_rank_counts(n: int) -> list[int]:
    counts = [1]
    for rank in range(1, n + 1):
        updated = [0] * (len(counts) + rank)
        for total, count in enumerate(counts):
            updated[total] += count
            updated[total + rank] += count
        counts = updated
    return counts


def exact_signed_rank_p(
    values: Sequence[float], theta: float
) -> dict[str, float | int]:
    """Return exact lower, upper, and central two-sided signed-rank p-values."""

    centered = np.asarray(values, dtype=float) - float(theta)
    absolute = np.abs(centered)
    if centered.ndim != 1 or centered.size == 0 or not np.all(np.isfinite(centered)):
        raise ValueError("values must be one-dimensional and finite")
    if np.any(absolute == 0.0) or len(np.unique(absolute)) != len(absolute):
        raise ValueError("interval probe landed on a zero or tied absolute rank")
    order = np.argsort(absolute)
    ranks = np.empty_like(order)
    ranks[order] = np.arange(1, len(centered) + 1)
    statistic = int(np.sum(ranks[centered > 0.0]))
    counts = exact_signed_rank_counts(len(centered))
    denominator = 2 ** len(centered)
    lower = float(sum(counts[: statistic + 1]) / denominator)
    upper = float(sum(counts[statistic:]) / denominator)
    return {
        "w_plus": statistic,
        "lower_tail": lower,
        "upper_tail": upper,
        "two_sided_central": min(1.0, 2.0 * min(lower, upper)),
    }


def _probe_intervals(walsh: Sequence[float]) -> list[float]:
    unique = sorted(set(float(value) for value in walsh))
    scale = max(1.0, abs(unique[0]), abs(unique[-1]))
    return [unique[0] - scale] + [
        (left + right) / 2.0 for left, right in zip(unique, unique[1:])
    ] + [unique[-1] + scale]


def invert_signed_rank(
    values: Sequence[float], *, alpha: float, p_field: str
) -> dict[str, Any]:
    """Invert the exact signed-rank test over Walsh-average change points."""

    samples = [float(value) for value in values]
    walsh = sorted(
        (samples[left] + samples[right]) / 2.0
        for left in range(len(samples))
        for right in range(left, len(samples))
    )
    unique = sorted(set(walsh))
    probes = _probe_intervals(walsh)
    accepted: list[int] = []
    p_values: list[float] = []
    for index, probe in enumerate(probes):
        p_value = float(exact_signed_rank_p(samples, probe)[p_field])
        p_values.append(p_value)
        if p_value > alpha:
            accepted.append(index)
    if not accepted:
        raise RuntimeError("exact signed-rank inversion produced an empty confidence set")
    first = min(accepted)
    last = max(accepted)
    if accepted != list(range(first, last + 1)):
        raise RuntimeError("exact signed-rank confidence set is not contiguous")
    lower = -math.inf if first == 0 else unique[first - 1]
    upper = math.inf if last == len(probes) - 1 else unique[last]
    result: dict[str, Any] = {
        "alpha": alpha,
        "p_field": p_field,
        "lower": lower,
        "upper": upper,
        "accepted_interval_count": len(accepted),
    }
    if math.isfinite(lower):
        result["inside_lower_p"] = p_values[first]
        result["outside_lower_p"] = p_values[first - 1]
        if not (result["inside_lower_p"] > alpha >= result["outside_lower_p"]):
            raise RuntimeError("lower confidence boundary inversion check failed")
    if math.isfinite(upper):
        result["inside_upper_p"] = p_values[last]
        result["outside_upper_p"] = p_values[last + 1]
        if not (result["inside_upper_p"] > alpha >= result["outside_upper_p"]):
            raise RuntimeError("upper confidence boundary inversion check failed")
    return result


def ratio_or_none(value: float) -> float | None:
    if not math.isfinite(value):
        return None
    return math.exp(value)


def source_bounds(formal: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for horizon, key in (("6s_primary", "primary_inference"), ("30s_tail", "tail_inference")):
        for effect, test in formal[key]["tests"].items():
            values = [float(value) for value in test["seed_effects"]]
            ci95 = invert_signed_rank(
                values, alpha=0.05, p_field="two_sided_central"
            )
            ci_sim = invert_signed_rank(
                values,
                alpha=0.05 / FAMILY_SIZE,
                p_field="two_sided_central",
            )
            upper95 = invert_signed_rank(
                values, alpha=0.05, p_field="lower_tail"
            )
            upper_fwer = invert_signed_rank(
                values, alpha=0.05 / FAMILY_SIZE, p_field="lower_tail"
            )
            estimate = float(test["hodges_lehmann"])
            row = {
                "horizon": horizon,
                "effect": effect,
                "n_seeds": len(values),
                "estimand": "seed-level Hodges-Lehmann pseudomedian of log contrast",
                "ratio_estimate": math.exp(estimate),
                "ci95_ratio_lower": ratio_or_none(float(ci95["lower"])),
                "ci95_ratio_upper": ratio_or_none(float(ci95["upper"])),
                "simultaneous_98_75_ratio_lower": ratio_or_none(float(ci_sim["lower"])),
                "simultaneous_98_75_ratio_upper": ratio_or_none(float(ci_sim["upper"])),
                "one_sided_95_ratio_upper": ratio_or_none(float(upper95["upper"])),
                "familywise_95_ratio_upper": ratio_or_none(float(upper_fwer["upper"])),
                "materiality_ratio": MATERIALITY_RATIO,
                "individual_upper_excludes_1_10": float(upper95["upper"])
                < math.log(MATERIALITY_RATIO),
                "familywise_upper_excludes_1_10": float(upper_fwer["upper"])
                < math.log(MATERIALITY_RATIO),
                "registered_p_one_sided_for_gain_gt_1_10": test["p_one_sided"],
                "registered_holm_reject_gain_gt_1_10": test["holm"]["reject"],
                "post_completion_status": "descriptive precision diagnostic; not preregistered equivalence",
                "inversion_checks": {
                    "ci95": ci95,
                    "simultaneous_98_75": ci_sim,
                    "upper95": upper95,
                    "upper_familywise95": upper_fwer,
                },
            }
            rows.append(row)
    return rows


def _channel_metrics(block: np.ndarray) -> dict[str, float]:
    """Return RMS and registered-style TV for a [record, step, agent, channel] block."""

    values = np.asarray(block, dtype=float)
    if values.ndim != 4 or values.shape[2:] != (4, 2):
        raise RuntimeError(f"unexpected action block shape: {values.shape}")
    differences = np.diff(
        np.concatenate(
            [np.zeros((values.shape[0], 1, 4, 2), dtype=float), values], axis=1
        ),
        axis=1,
    )
    result: dict[str, float] = {
        "combined_rms": float(np.sqrt(np.mean(values**2))),
        "combined_tv": float(np.sum(np.mean(np.abs(differences), axis=(2, 3)))),
    }
    for index, channel in enumerate(("M", "D")):
        result[f"{channel}_rms"] = float(np.sqrt(np.mean(values[..., index] ** 2)))
        result[f"{channel}_tv"] = float(
            np.sum(np.mean(np.abs(differences[..., index]), axis=2))
        )
    if not math.isclose(
        result["combined_rms"] ** 2,
        0.5 * (result["M_rms"] ** 2 + result["D_rms"] ** 2),
        rel_tol=1.0e-12,
        abs_tol=1.0e-12,
    ):
        raise RuntimeError("combined RMS does not reconstruct from M/D channels")
    if not math.isclose(
        result["combined_tv"],
        0.5 * (result["M_tv"] + result["D_tv"]),
        rel_tol=1.0e-12,
        abs_tol=1.0e-12,
    ):
        raise RuntimeError("combined TV does not reconstruct from M/D channels")
    return result


def _decoded_metrics(block: np.ndarray) -> dict[str, float]:
    values = np.asarray(block, dtype=float)
    if values.ndim != 3 or values.shape[2] != 4:
        raise RuntimeError(f"unexpected decoded command block shape: {values.shape}")
    differences = np.diff(
        np.concatenate(
            [np.zeros((values.shape[0], 1, 4), dtype=float), values], axis=1
        ),
        axis=1,
    )
    return {
        "rms": float(np.sqrt(np.mean(values**2))),
        "tv": float(np.sum(np.mean(np.abs(differences), axis=2))),
    }


def trace_metrics(payload: Mapping[str, Any]) -> dict[str, Any]:
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != 6:
        raise RuntimeError("trace block must contain six records")
    stage_blocks: dict[str, list[np.ndarray]] = {
        "raw": [],
        "projected": [],
        "executed": [],
    }
    delta_m: list[np.ndarray] = []
    delta_d: list[np.ndarray] = []
    raw_projection_max = 0.0
    projected_executed_max = 0.0
    for record in records:
        steps = record.get("steps")
        if not isinstance(steps, list) or len(steps) != 150:
            raise RuntimeError("each trace record must contain 150 steps")
        raw = np.asarray([step["raw_action_norm"] for step in steps], dtype=float)
        projected = np.asarray(
            [step["projected_action_norm"] for step in steps], dtype=float
        )
        executed = np.asarray([step["action_norm"] for step in steps], dtype=float)
        if raw.shape != (150, 4, 2) or projected.shape != raw.shape or executed.shape != raw.shape:
            raise RuntimeError("unexpected raw/projected/executed action shape")
        raw_projection_max = max(
            raw_projection_max, float(np.max(np.abs(raw - projected)))
        )
        projected_executed_max = max(
            projected_executed_max, float(np.max(np.abs(projected - executed)))
        )
        stage_blocks["raw"].append(raw)
        stage_blocks["projected"].append(projected)
        stage_blocks["executed"].append(executed)
        delta_m.append(np.asarray([step["delta_M"] for step in steps], dtype=float))
        delta_d.append(np.asarray([step["delta_D"] for step in steps], dtype=float))
    result: dict[str, Any] = {
        "raw_projection_max_abs": raw_projection_max,
        "projected_executed_max_abs": projected_executed_max,
        "decoded_M": _decoded_metrics(np.stack(delta_m)),
        "decoded_D": _decoded_metrics(np.stack(delta_d)),
    }
    for stage, blocks in stage_blocks.items():
        result[stage] = _channel_metrics(np.stack(blocks))
    return result


def flatten_metrics(prefix: str, metrics: Mapping[str, Any], row: dict[str, Any]) -> None:
    for name, value in metrics.items():
        if isinstance(value, Mapping):
            flatten_metrics(f"{prefix}{name}_", value, row)
        else:
            row[f"{prefix}{name}"] = value


def _ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0.0:
        raise RuntimeError("non-positive comparator command metric")
    return float(numerator / denominator)


def load_command_rows(
    config: Mapping[str, Any], formal: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    artifacts = exp.expected_artifacts(config, root=RESULT_ROOT, scope="formal")
    learned_payloads: dict[tuple[str, int, str], Mapping[str, Any]] = {}
    reference_payloads: dict[str, Mapping[str, Any]] = {}
    verified_hashes: list[str] = []
    for identity, path in artifacts["eval"].items():
        _kind, _scope, bank, arm, seed_text, profile = identity.split("|")
        if bank != "same":
            continue
        if arm != REFERENCE_ARM and seed_text == "none":
            continue
        if arm == REFERENCE_ARM and seed_text == "none":
            payload, digest = base.read_verified_json(path)
            reference_payloads[profile] = payload
            verified_hashes.append(digest)
        elif seed_text != "none":
            payload, digest = base.read_verified_json(path)
            learned_payloads[(arm, int(seed_text), profile)] = payload
            verified_hashes.append(digest)
    if len(learned_payloads) != 832 or len(reference_payloads) != 4:
        raise RuntimeError(
            f"unexpected same-bank roster: learned={len(learned_payloads)} "
            f"reference={len(reference_payloads)}"
        )

    decisions = {
        (str(row["arm_id"]), int(row["training_seed"])): row
        for row in formal["threshold_sensitivity"]["primary"]["policy_decisions"]
    }
    blocks = {
        (str(row["arm_id"]), int(row["training_seed"]), str(row["profile_id"])): row
        for row in formal["threshold_sensitivity"]["primary"]["per_profile_blocks"]
    }
    break_even = {
        (str(row["arm_id"]), int(row["training_seed"])): row
        for row in formal["threshold_sensitivity"]["break_even"]
    }
    reference_metrics = {
        profile: trace_metrics(payload) for profile, payload in reference_payloads.items()
    }
    rows: list[dict[str, Any]] = []
    for (arm, seed, profile), payload in sorted(learned_payloads.items()):
        metrics = trace_metrics(payload)
        reference = reference_metrics[profile]
        decision = decisions[(arm, seed)]
        block = blocks[(arm, seed, profile)]
        row: dict[str, Any] = {
            "arm_id": arm,
            "training_seed": seed,
            "profile_id": profile,
            "endpoint_qualified": all(
                bool(value) for value in decision["aggregate_joint_endpoint_target"].values()
            ),
            "all_non_action_guards_and_endpoints_pass": bool(
                break_even[(arm, seed)]["all_non_action_guards_pass"]
            ),
            "off_diagonal_ratio": float(
                decision["aggregate_endpoint_ratios_to_deterministic"][
                    "off_diagonal_response_energy"
                ]
            ),
            "differential_ratio": float(
                decision["aggregate_endpoint_ratios_to_deterministic"][
                    "disturbance_differential_energy"
                ]
            ),
            "rocof_pass": bool(block["guard"]["rocof_no_harm"]),
            "worst_peak_pass": bool(block["guard"]["worst_peak_no_harm"]),
            "common_frequency_pass": bool(
                block["guard"]["common_frequency_no_harm"]
            ),
            "failed_guard_count": len(block["failed_guards"]),
            "failed_guards": "+".join(block["failed_guards"]),
        }
        flatten_metrics("candidate_", metrics, row)
        flatten_metrics("reference_", reference, row)
        for stage in ("raw", "projected", "executed"):
            for metric in ("combined_rms", "combined_tv", "M_rms", "M_tv", "D_rms", "D_tv"):
                row[f"ratio_{stage}_{metric}"] = _ratio(
                    float(metrics[stage][metric]), float(reference[stage][metric])
                )
        for channel in ("M", "D"):
            for metric in ("rms", "tv"):
                row[f"ratio_decoded_{channel}_{metric}"] = _ratio(
                    float(metrics[f"decoded_{channel}"][metric]),
                    float(reference[f"decoded_{channel}"][metric]),
                )
        rows.append(row)

    return rows, {
        "verified_trace_files": len(verified_hashes),
        "verified_trace_sha256_set": hashlib.sha256(
            "\n".join(sorted(verified_hashes)).encode("ascii")
        ).hexdigest(),
        "reference_profiles": sorted(reference_metrics),
    }


def quantiles(values: Iterable[float]) -> dict[str, float | int | None]:
    return base.quantiles(values)


def aggregate_command_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    numeric_keys = sorted(
        key
        for key, value in rows[0].items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    )
    summary = {
        key: quantiles(float(row[key]) for row in rows) for key in numeric_keys
    }
    failures = Counter()
    for row in rows:
        for name in str(row["failed_guards"]).split("+"):
            if name:
                failures[name] += 1
    summary["profile_block_failure_counts"] = dict(failures)
    summary["endpoint_qualified_policy_count"] = len(
        {
            (str(row["arm_id"]), int(row["training_seed"]))
            for row in rows
            if bool(row["endpoint_qualified"])
        }
    )
    summary["endpoint_and_non_action_clean_policy_count"] = len(
        {
            (str(row["arm_id"]), int(row["training_seed"]))
            for row in rows
            if bool(row["all_non_action_guards_and_endpoints_pass"])
        }
    )
    summary["projected_executed_max_abs"] = max(
        float(row["candidate_projected_executed_max_abs"]) for row in rows
    )
    summary["raw_projection_max_abs"] = max(
        float(row["candidate_raw_projection_max_abs"]) for row in rows
    )
    return summary


def policy_rows(profile_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[Mapping[str, Any]]] = {}
    for row in profile_rows:
        grouped.setdefault((str(row["arm_id"]), int(row["training_seed"])), []).append(row)
    result: list[dict[str, Any]] = []
    for (arm, seed), rows in sorted(grouped.items()):
        first = rows[0]
        frequency_fail_profiles = sum(
            not (bool(row["rocof_pass"]) and bool(row["worst_peak_pass"]))
            for row in rows
        )
        row = {
            "arm_id": arm,
            "training_seed": seed,
            "endpoint_qualified": bool(first["endpoint_qualified"]),
            "all_non_action_guards_and_endpoints_pass": bool(
                first["all_non_action_guards_and_endpoints_pass"]
            ),
            "off_diagonal_ratio": float(first["off_diagonal_ratio"]),
            "differential_ratio": float(first["differential_ratio"]),
            "endpoint_worst_ratio": max(
                float(first["off_diagonal_ratio"]), float(first["differential_ratio"])
            ),
            "action_rms_max_ratio": max(
                float(value["ratio_executed_combined_rms"]) for value in rows
            ),
            "action_tv_max_ratio": max(
                float(value["ratio_executed_combined_tv"]) for value in rows
            ),
            "frequency_fail_profiles": frequency_fail_profiles,
            "rocof_fail_profiles": sum(not bool(value["rocof_pass"]) for value in rows),
            "peak_fail_profiles": sum(not bool(value["worst_peak_pass"]) for value in rows),
        }
        row["action_worst_ratio"] = max(
            float(row["action_rms_max_ratio"]), float(row["action_tv_max_ratio"])
        )
        result.append(row)
    return result


def nondominated(rows: Sequence[Mapping[str, Any]]) -> set[tuple[str, int]]:
    result: set[tuple[str, int]] = set()
    for index, row in enumerate(rows):
        vector = np.asarray(
            [float(row["endpoint_worst_ratio"]), float(row["action_worst_ratio"])]
        )
        dominated = False
        for other_index, other in enumerate(rows):
            if index == other_index:
                continue
            other_vector = np.asarray(
                [float(other["endpoint_worst_ratio"]), float(other["action_worst_ratio"])]
            )
            if np.all(other_vector <= vector) and np.any(other_vector < vector):
                dominated = True
                break
        if not dominated:
            result.add((str(row["arm_id"]), int(row["training_seed"])))
    return result


def cross_check_prior_audit(
    rows: Sequence[Mapping[str, Any]], prior: Mapping[str, Any]
) -> dict[str, Any]:
    if prior["integrity"]["passed"] is not True:
        raise RuntimeError("prior full post-run audit did not pass")
    expected = prior["continuous_ratios"]["all_policy_profile_blocks"]
    checks: dict[str, Any] = {}
    for current_key, prior_key in (
        ("ratio_executed_combined_rms", "action_rms"),
        ("ratio_executed_combined_tv", "action_total_variation"),
    ):
        actual = quantiles(float(row[current_key]) for row in rows)
        target = expected[prior_key]
        max_error = max(
            abs(float(actual[name]) - float(target[name]))
            for name in ("min", "q05", "q25", "median", "q75", "q95", "max")
        )
        checks[prior_key] = {
            "max_quantile_abs_error": max_error,
            "match": max_error <= 1.0e-12,
        }
        if not checks[prior_key]["match"]:
            raise RuntimeError(f"registered {prior_key} ratio distribution drift")
    return checks


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def source_figure(rows: Sequence[Mapping[str, Any]], path: Path) -> None:
    effects = ["actor_main", "critic_main", "actor_x_critic", "critic_x_reward"]
    labels = ["Actor main", "Critic main", "Actor x critic", "Critic x reward"]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), sharey=True)
    for axis, horizon, title in zip(
        axes, ("6s_primary", "30s_tail"), ("6 s primary", "30 s sensitivity")
    ):
        selected = {str(row["effect"]): row for row in rows if row["horizon"] == horizon}
        y = np.arange(len(effects))
        estimates = np.asarray([selected[name]["ratio_estimate"] for name in effects])
        low = np.asarray([selected[name]["ci95_ratio_lower"] for name in effects])
        high = np.asarray([selected[name]["ci95_ratio_upper"] for name in effects])
        sim_low = np.asarray(
            [selected[name]["simultaneous_98_75_ratio_lower"] for name in effects]
        )
        sim_high = np.asarray(
            [selected[name]["simultaneous_98_75_ratio_upper"] for name in effects]
        )
        axis.errorbar(
            estimates,
            y,
            xerr=np.vstack([estimates - sim_low, sim_high - estimates]),
            fmt="none",
            ecolor="#9aa0a6",
            elinewidth=5,
            capsize=0,
            label="98.75% simultaneous CI",
        )
        axis.errorbar(
            estimates,
            y,
            xerr=np.vstack([estimates - low, high - estimates]),
            fmt="o",
            color="#1f77b4",
            ecolor="#1f77b4",
            elinewidth=1.8,
            capsize=4,
            label="95% exact CI",
        )
        axis.axvline(1.0, color="black", linestyle=":", linewidth=1)
        axis.axvline(MATERIALITY_RATIO, color="#d62728", linestyle="--", linewidth=1)
        axis.set_title(title)
        axis.set_xlabel("Registered contrast ratio (>1 favors authentic source)")
        axis.grid(axis="x", alpha=0.25)
        axis.set_yticks(y, labels)
        axis.invert_yaxis()
    axes[0].legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def pareto_figure(rows: Sequence[Mapping[str, Any]], path: Path) -> None:
    front = nondominated(rows)
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 5.0), sharex=True)
    for axis, y_key, title in zip(
        axes,
        ("action_rms_max_ratio", "action_tv_max_ratio"),
        ("RMS guard ratio", "Total-variation guard ratio"),
    ):
        for row in rows:
            if bool(row["all_non_action_guards_and_endpoints_pass"]):
                color, marker, size = "#2ca02c", "D", 48
            elif bool(row["endpoint_qualified"]):
                color, marker, size = "#ff7f0e", "o", 30
            else:
                color, marker, size = "#b0b0b0", "o", 18
            edge = "black" if (str(row["arm_id"]), int(row["training_seed"])) in front else "none"
            axis.scatter(
                float(row["endpoint_worst_ratio"]),
                float(row[y_key]),
                c=color,
                marker=marker,
                s=size,
                edgecolors=edge,
                linewidths=0.8,
                alpha=0.82,
            )
        axis.axvline(0.95, color="#2ca02c", linestyle="--", linewidth=1)
        axis.axhline(1.10, color="#d62728", linestyle="--", linewidth=1)
        axis.set_yscale("log")
        axis.set_title(title)
        axis.set_xlabel("Worst aggregate endpoint ratio (lower is better)")
        axis.grid(alpha=0.22, which="both")
    axes[0].set_ylabel("Worst profile command-activity ratio to direct M/D")
    axes[0].scatter([], [], c="#b0b0b0", s=18, label="Endpoint not qualified")
    axes[0].scatter([], [], c="#ff7f0e", s=30, label="Endpoint-qualified; frequency guard fails")
    axes[0].scatter([], [], c="#2ca02c", marker="D", s=48, label="Endpoint + non-action guards pass")
    axes[0].legend(loc="upper right", fontsize=7.5)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def command_figure(rows: Sequence[Mapping[str, Any]], path: Path) -> None:
    fields = [
        "ratio_executed_M_rms",
        "ratio_executed_D_rms",
        "ratio_executed_M_tv",
        "ratio_executed_D_tv",
        "ratio_decoded_M_rms",
        "ratio_decoded_D_rms",
        "ratio_decoded_M_tv",
        "ratio_decoded_D_tv",
    ]
    labels = [
        "Norm M RMS",
        "Norm D RMS",
        "Norm M TV",
        "Norm D TV",
        "Decoded M RMS",
        "Decoded D RMS",
        "Decoded M TV",
        "Decoded D TV",
    ]
    values = [np.asarray([float(row[field]) for row in rows]) for field in fields]
    fig, axis = plt.subplots(figsize=(12.0, 5.2))
    axis.boxplot(values, tick_labels=labels, showfliers=False, whis=(5, 95))
    axis.axhline(1.10, color="#d62728", linestyle="--", linewidth=1)
    axis.set_yscale("log")
    axis.set_ylabel("Candidate / direct-M/D comparator ratio")
    axis.set_title("R485 command activity by M/D channel (832 policy-profile blocks)")
    axis.grid(axis="y", alpha=0.25, which="both")
    axis.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def render_markdown(result: Mapping[str, Any]) -> str:
    bounds = result["source_contrast_bounds"]
    action = result["command_activity_summary"]
    lines = [
        "# R485 offline extension: precision, M/D command activity, and Pareto map",
        "",
        "> Scratch sealed-data analysis. It does not alter the registered R485 verdict.",
        "",
        "## Conclusion",
        "",
        f"- Verified trace files: {result['inputs']['verified_trace_files']} (832 learned + 4 direct-M/D reference blocks).",
        f"- Endpoint-qualified policies: {action['endpoint_qualified_policy_count']}/208.",
        f"- Endpoint-qualified policies also passing every non-action guard: {action['endpoint_and_non_action_clean_policy_count']}/208.",
        f"- Projected and executed normalized actions are identical to max absolute error {action['projected_executed_max_abs']:.3g}; there is no recorded downstream actuator state in R485.",
        "- The exact confidence bounds are a post-completion precision diagnostic, not a preregistered equivalence analysis.",
        "",
        "## Source-contrast confidence bounds",
        "",
        "| Horizon | Effect | HL ratio | 95% exact CI | 95% familywise upper bound | Excludes 1.10? |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in bounds:
        lines.append(
            f"| {row['horizon']} | {row['effect']} | {row['ratio_estimate']:.4f} | "
            f"[{row['ci95_ratio_lower']:.4f}, {row['ci95_ratio_upper']:.4f}] | "
            f"{row['familywise_95_ratio_upper']:.4f} | "
            f"{row['familywise_upper_excludes_1_10']} |"
        )
    lines.extend(
        [
            "",
            "Interpretation: a familywise upper bound below 1.10 excludes a 10% beneficial shift under the same symmetric location model. A bound above 1.10 remains `not established`, not equivalence and not evidence of zero effect.",
            "",
            "## M/D command-activity decomposition",
            "",
            "Candidate/comparator ratios across 832 policy-profile blocks (min / median / max):",
            "",
            "| Metric | Min | Median | Max |",
            "|---|---:|---:|---:|",
        ]
    )
    for key, label in (
        ("ratio_executed_M_rms", "Executed normalized M RMS"),
        ("ratio_executed_D_rms", "Executed normalized D RMS"),
        ("ratio_executed_M_tv", "Executed normalized M TV"),
        ("ratio_executed_D_tv", "Executed normalized D TV"),
        ("ratio_decoded_M_rms", "Decoded delta-M RMS"),
        ("ratio_decoded_D_rms", "Decoded delta-D RMS"),
        ("ratio_decoded_M_tv", "Decoded delta-M TV"),
        ("ratio_decoded_D_tv", "Decoded delta-D TV"),
    ):
        row = action[key]
        lines.append(
            f"| {label} | {row['min']:.4f} | {row['median']:.4f} | {row['max']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Failure-map interpretation",
            "",
            f"- Profile-block action RMS failures: {action['profile_block_failure_counts'].get('action_rms_no_harm', 0)}/832.",
            f"- Profile-block action TV failures: {action['profile_block_failure_counts'].get('action_variation_no_harm', 0)}/832.",
            f"- RoCoF failures: {action['profile_block_failure_counts'].get('rocof_no_harm', 0)}/832; worst-peak failures: {action['profile_block_failure_counts'].get('worst_peak_no_harm', 0)}/832.",
            "- The Pareto plot separates endpoint failure, endpoint-qualified but frequency-guard failure, and the five endpoint/non-action-clean policies. None passes the command-activity guard.",
            "",
            "## Claim boundary",
            "",
            "- `actor_main` and `critic_x_reward` at 6 s, and `actor_main` at 30 s, have Bonferroni-familywise one-sided upper bounds below 1.10 under the registered symmetric location model.",
            "- `critic_main` and `actor_x_critic` do not exclude a 10% beneficial shift; the actor-by-critic estimate itself remains above 1.10 with wide uncertainty.",
            "- The per-channel results establish large comparator-relative command amplitude/path length. They do not establish actuator wear, energy, thermal load, or hardware harm.",
            "- Raw-to-projected differences diagnose policy projection only. Projected equals recorded executed action, so R485 contains no separate actuator transfer/damage state.",
            "",
        ]
    )
    return "\n".join(lines)


def write_hashes(paths: Sequence[Path], output: Path) -> None:
    lines = [f"{sha256_file(path)}  {path.name}" for path in paths]
    output.write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    config, config_sha = base.read_verified_json(CONFIG_PATH)
    seal, seal_sha = base.read_verified_json(SEAL_PATH)
    formal, formal_sha = base.read_verified_json(FORMAL_ANALYSIS_PATH)
    prior = json.loads(PRIOR_AUDIT_PATH.read_text(encoding="utf-8"))
    bounds = source_bounds(formal)
    profile_rows, trace_inputs = load_command_rows(config, formal)
    command_summary = aggregate_command_summary(profile_rows)
    policies = policy_rows(profile_rows)
    prior_checks = cross_check_prior_audit(profile_rows, prior)

    if command_summary["endpoint_qualified_policy_count"] != 121:
        raise RuntimeError("endpoint-qualified policy count drift")
    if command_summary["endpoint_and_non_action_clean_policy_count"] != 5:
        raise RuntimeError("non-action-clean policy count drift")
    if command_summary["profile_block_failure_counts"].get("action_rms_no_harm") != 832:
        raise RuntimeError("action RMS failure count drift")
    if command_summary["profile_block_failure_counts"].get("action_variation_no_harm") != 832:
        raise RuntimeError("action TV failure count drift")
    if command_summary["projected_executed_max_abs"] > 1.0e-12:
        raise RuntimeError("projected and executed action fields diverge")

    result = {
        "schema_version": 1,
        "round": "R485",
        "attempt_id": seal["attempt_id"],
        "scope": "scratch_sealed_data_offline_extension",
        "formal_artifacts_modified": False,
        "inputs": {
            "config_sha256": config_sha,
            "formal_seal_sha256": seal_sha,
            "formal_analysis_sha256": formal_sha,
            "prior_postrun_audit_sha256": sha256_file(PRIOR_AUDIT_PATH),
            "reviewed_commit": seal["reviewed_commit"],
            **trace_inputs,
        },
        "source_contrast_bounds": bounds,
        "command_activity_summary": command_summary,
        "pareto_summary": {
            "policy_count": len(policies),
            "front_count": len(nondominated(policies)),
            "endpoint_qualified": sum(bool(row["endpoint_qualified"]) for row in policies),
            "endpoint_and_non_action_clean": sum(
                bool(row["all_non_action_guards_and_endpoints_pass"]) for row in policies
            ),
        },
        "cross_checks": {
            "prior_postrun_audit": prior_checks,
            "formal_status": formal["status"],
            "formal_endpoint_qualified": formal["learner_qualification"]["endpoint_qualified_count"],
            "formal_complete_contract": formal["learner_qualification"]["complete_contract_passing_count"],
            "confidence_inversion_boundary_checks": "PASS",
        },
    }

    bounds_csv = output_root / "source_contrast_bounds.csv"
    profile_csv = output_root / "policy_profile_command_activity.csv"
    policy_csv = output_root / "policy_pareto.csv"
    json_path = output_root / "analysis.json"
    md_path = output_root / "REPORT.md"
    source_png = output_root / "source_contrast_bounds.png"
    pareto_png = output_root / "endpoint_command_frequency_map.png"
    command_png = output_root / "md_command_activity.png"

    flat_bounds = [
        {key: value for key, value in row.items() if key != "inversion_checks"}
        for row in bounds
    ]
    write_csv(bounds_csv, flat_bounds)
    write_csv(profile_csv, profile_rows)
    write_csv(policy_csv, policies)
    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    md_path.write_text(render_markdown(result), encoding="utf-8")
    source_figure(bounds, source_png)
    pareto_figure(policies, pareto_png)
    command_figure(profile_rows, command_png)
    output_paths = [
        bounds_csv,
        profile_csv,
        policy_csv,
        json_path,
        md_path,
        source_png,
        pareto_png,
        command_png,
    ]
    write_hashes(output_paths, output_root / "SHA256SUMS")
    print(
        f"[r485-offline-extension] PASS profiles={len(profile_rows)} "
        f"policies={len(policies)} output={output_root}",
        flush=True,
    )


if __name__ == "__main__":
    main()
