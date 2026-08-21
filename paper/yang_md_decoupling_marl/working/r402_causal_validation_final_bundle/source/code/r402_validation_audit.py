#!/usr/bin/env python3
"""Independent causal/implementation audit for the R402 validation package.

The script intentionally separates:

1. registered quantities recomputed from raw evaluation JSONs;
2. post-hoc diagnostics from trajectories and checkpoints;
3. mechanically established source-code findings; and
4. unavailable causal evidence that requires prospective ANDES execution.

Usage
-----
python r402_validation_audit.py \
  --package-root /path/to/r402_causal_validation_v1 \
  --output-dir /path/to/generated \
  [--source-zip /path/to/r402_causal_validation_v1.zip]

Dependencies: numpy, pandas, PyYAML, torch.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
import sys
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
import torch
import yaml

PAIR_KINDS = ("common", "differential", "localized")
LEARNING_ARMS = (
    "yang_scalar_td3",
    "cd_matd3_no_message",
    "cd_matd3_message",
)
DETERMINISTIC_ARM = "local_neighbour_md_km2_kd2"
CHECKPOINT_EPISODES = (240, 480, 720, 960, 1200, 1440)


@dataclass(frozen=True)
class EvaluationRecord:
    source_file: str
    payload: Mapping[str, Any]

    @property
    def arm_id(self) -> str:
        return str(self.payload["arm_id"])

    @property
    def seed(self) -> int | None:
        value = self.payload.get("training_seed")
        return None if value is None else int(value)

    @property
    def profile_id(self) -> str:
        return str(self.payload["profile_id"])

    @property
    def scenario_id(self) -> str:
        return str(self.payload["scenario_id"])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_contract(root: Path) -> dict[str, Any]:
    payload = yaml.safe_load((root / "contract/frozen_config.yaml").read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("contract"), dict):
        raise ValueError("contract/frozen_config.yaml does not contain a contract mapping")
    return dict(payload["contract"])


def discover_records(root: Path) -> list[EvaluationRecord]:
    evaluation_root = root / "existing_r402/raw_evaluation"
    records: list[EvaluationRecord] = []
    for path in sorted(evaluation_root.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("records")
        if not isinstance(rows, list):
            raise ValueError(f"{path} does not contain a records list")
        rel = path.relative_to(evaluation_root).as_posix()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"non-object record in {path}")
            records.append(EvaluationRecord(source_file=rel, payload=row))
    return records


def record_arrays(record: EvaluationRecord) -> dict[str, np.ndarray]:
    payload = record.payload
    steps = payload["steps"]
    return {
        "frequency": np.asarray([step["freq_hz_physical"] for step in steps], dtype=float),
        "action": np.asarray([step["action_norm"] for step in steps], dtype=float),
        "delta_m": np.asarray([step["delta_M"] for step in steps], dtype=float),
        "delta_d": np.asarray([step["delta_D"] for step in steps], dtype=float),
        "m": np.asarray([step["M_es"] for step in steps], dtype=float),
        "d": np.asarray([step["D_es"] for step in steps], dtype=float),
        "initial_frequency": np.asarray(payload["initial_freq_hz_physical"], dtype=float),
        "baseline_m": np.asarray(payload["identity"]["baseline_m0"], dtype=float),
        "baseline_d": np.asarray(payload["identity"]["baseline_d0"], dtype=float),
    }


def _settling_time(response: np.ndarray, dt: float) -> float:
    norms = np.linalg.norm(response, axis=1)
    peak = float(np.max(norms))
    if peak == 0.0:
        return 0.0
    threshold = 0.02 * peak
    for index in range(norms.size):
        if np.all(norms[index:] <= threshold):
            return float((index + 1) * dt)
    return float(norms.size * dt)


def summarise_profile_independent(
    records: Sequence[EvaluationRecord], contract: Mapping[str, Any]
) -> dict[str, Any]:
    """Independent implementation of the registered six-trajectory summary."""

    if len(records) != 6:
        raise ValueError("profile block must contain exactly six records")
    profile_ids = {row.profile_id for row in records}
    arm_ids = {row.arm_id for row in records}
    seeds = {row.seed for row in records}
    if len(profile_ids) != 1 or len(arm_ids) != 1 or len(seeds) != 1:
        raise ValueError("profile block must share profile, arm and seed")
    profile_id = next(iter(profile_ids))
    arm_id = next(iter(arm_ids))
    seed = next(iter(seeds))
    nominal = float(contract["physical_nominal_frequency_hz"])
    dt = float(contract["dt_seconds"])
    transform = np.asarray(contract["differential_transform"], dtype=float)
    action_lower, action_upper = map(float, contract["action_bounds"])
    slew_limit = float(contract["action_slew_limit"])
    decoder = contract["decoder"]
    mapping_atol = float(decoder["mapping_atol"])

    by_kind_sign: dict[tuple[str, str], EvaluationRecord] = {}
    arrays_by_id: dict[str, dict[str, np.ndarray]] = {}
    for record in records:
        kind = str(record.payload["pair_kind"])
        sign = str(record.payload["sign"])
        by_kind_sign[(kind, sign)] = record
        arrays_by_id[record.scenario_id] = record_arrays(record)

    pair_responses: dict[str, dict[str, Any]] = {}
    for pair_kind in PAIR_KINDS:
        positive = by_kind_sign[(pair_kind, "positive")]
        negative = by_kind_sign[(pair_kind, "negative")]
        pos_f = arrays_by_id[positive.scenario_id]["frequency"] - nominal
        neg_f = arrays_by_id[negative.scenario_id]["frequency"] - nominal
        odd = 0.5 * (pos_f - neg_f)
        common = np.mean(odd, axis=1)
        differential = odd @ transform.T
        magnitude = float(positive.payload["magnitude"])
        pair_responses[pair_kind] = {
            "common": common,
            "differential": differential,
            "magnitude": magnitude,
        }

    common_pair = pair_responses["common"]
    differential_pair = pair_responses["differential"]
    off_diagonal = (
        float(np.sum(np.mean(common_pair["differential"] ** 2, axis=1)))
        * dt
        / float(common_pair["magnitude"]) ** 2
        + float(np.sum(differential_pair["common"] ** 2))
        * dt
        / float(differential_pair["magnitude"]) ** 2
    )
    differential_energy = sum(
        float(np.sum(np.mean(pair_responses[kind]["differential"] ** 2, axis=1)))
        * dt
        / float(pair_responses[kind]["magnitude"]) ** 2
        for kind in PAIR_KINDS
    )

    blocks = [record_arrays(record) for record in records]
    common_iae = sum(
        float(np.sum(np.abs(np.mean(block["frequency"] - nominal, axis=1))) * dt)
        for block in blocks
    )
    worst_peak = max(float(np.max(np.abs(block["frequency"] - nominal))) for block in blocks)
    worst_rocof = max(
        float(
            np.max(
                np.abs(
                    np.diff(
                        np.vstack([block["initial_frequency"], block["frequency"]]),
                        axis=0,
                    )
                    / dt
                )
            )
        )
        for block in blocks
    )

    action_blocks = [block["action"] for block in blocks]
    all_actions = np.stack(action_blocks)
    differences = [
        np.diff(np.concatenate([np.zeros((1, 4, 2)), action], axis=0), axis=0)
        for action in action_blocks
    ]
    total_variation = float(
        sum(np.sum(np.mean(np.abs(diff), axis=(1, 2))) for diff in differences)
    )
    saturation = np.logical_or(
        all_actions <= action_lower + 1e-9,
        all_actions >= action_upper - 1e-9,
    )
    bound_violation = bool(
        np.any(all_actions < action_lower - 1e-9)
        or np.any(all_actions > action_upper + 1e-9)
    )
    slew_violation = bool(
        any(np.any(np.abs(diff) > slew_limit + 1e-9) for diff in differences)
    )

    mapping_checks: list[bool] = []
    for block in blocks:
        action = block["action"]
        expected_dm = np.where(action[:, :, 0] >= 0.0, 600.0 * action[:, :, 0], 200.0 * action[:, :, 0])
        expected_dd = np.where(action[:, :, 1] >= 0.0, 600.0 * action[:, :, 1], 200.0 * action[:, :, 1])
        expected_m = np.maximum(block["baseline_m"][None, :] + expected_dm, float(decoder["m_lower_clamp"]))
        expected_d = np.maximum(block["baseline_d"][None, :] + expected_dd, float(decoder["d_lower_clamp"]))
        mapping_checks.extend(
            [
                bool(np.allclose(block["delta_m"], expected_dm, rtol=0.0, atol=mapping_atol)),
                bool(np.allclose(block["delta_d"], expected_dd, rtol=0.0, atol=mapping_atol)),
                bool(np.allclose(block["m"], expected_m, rtol=0.0, atol=mapping_atol)),
                bool(np.allclose(block["d"], expected_d, rtol=0.0, atol=mapping_atol)),
            ]
        )

    row: dict[str, Any] = {
        "arm_id": arm_id,
        "seed": seed,
        "profile_id": profile_id,
        "record_count": len(records),
        "off_diagonal_response_energy": off_diagonal,
        "disturbance_differential_energy": differential_energy,
        "common_frequency_iae_hz_s": common_iae,
        "worst_unit_peak_hz": worst_peak,
        "worst_rocof_hz_s": worst_rocof,
        "action_rms": float(np.sqrt(np.mean(all_actions**2))),
        "action_total_variation": total_variation,
        "minimum_record_total_variation": float(
            min(np.sum(np.mean(np.abs(diff), axis=(1, 2))) for diff in differences)
        ),
        "maximum_action_row_dispersion": float(
            max(np.max(np.ptp(action, axis=1)) for action in action_blocks)
        ),
        "minimum_record_action_row_dispersion": float(
            min(np.max(np.ptp(action, axis=1)) for action in action_blocks)
        ),
        "action_saturation_fraction": float(np.mean(saturation)),
        "action_bound_violation": bound_violation,
        "action_slew_violation": slew_violation,
        "actuator_mapping_pass": all(mapping_checks),
    }
    for kind in PAIR_KINDS:
        row[f"settling_{kind}_seconds"] = _settling_time(
            np.asarray(pair_responses[kind]["differential"]), dt
        )
    row["valid"] = bool(
        row["actuator_mapping_pass"]
        and not bound_violation
        and not slew_violation
        and all(
            np.isfinite(float(row[key])) and float(row[key]) >= 0.0
            for key in (
                "off_diagonal_response_energy",
                "disturbance_differential_energy",
                "common_frequency_iae_hz_s",
                "worst_unit_peak_hz",
                "worst_rocof_hz_s",
            )
        )
    )
    return row


def group_profile_records(records: Sequence[EvaluationRecord]) -> dict[tuple[str, int | None, str], list[EvaluationRecord]]:
    grouped: dict[tuple[str, int | None, str], list[EvaluationRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.arm_id, record.seed, record.profile_id)].append(record)
    return grouped


def registered_recomputation(
    root: Path, records: Sequence[EvaluationRecord], contract: Mapping[str, Any], output: Path
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summaries = [
        summarise_profile_independent(block, contract)
        for _, block in sorted(group_profile_records(records).items(), key=lambda item: str(item[0]))
    ]
    profile_df = pd.DataFrame(summaries).sort_values(
        ["arm_id", "seed", "profile_id"], na_position="first"
    )
    profile_df.to_csv(output / "registered_profile_metrics.csv", index=False)

    endpoint_rows: list[dict[str, Any]] = []
    for (arm, seed), group in profile_df.groupby(["arm_id", "seed"], dropna=False):
        endpoint_rows.append(
            {
                "arm_id": arm,
                "seed": seed,
                "off_diagonal_response_energy": float(group["off_diagonal_response_energy"].sum()),
                "disturbance_differential_energy": float(group["disturbance_differential_energy"].sum()),
            }
        )
    endpoint_df = pd.DataFrame(endpoint_rows).sort_values(["arm_id", "seed"], na_position="first")
    endpoint_df.to_csv(output / "registered_endpoint_aggregates.csv", index=False)

    reference = profile_df[profile_df["arm_id"] == DETERMINISTIC_ARM].set_index("profile_id")
    guard_rows: list[dict[str, Any]] = []
    metric_map = {
        "common_iae_ratio": "common_frequency_iae_hz_s",
        "worst_peak_ratio": "worst_unit_peak_hz",
        "rocof_ratio": "worst_rocof_hz_s",
        "action_rms_ratio": "action_rms",
        "action_tv_ratio": "action_total_variation",
    }
    for _, row in profile_df[profile_df["arm_id"].isin(LEARNING_ARMS)].iterrows():
        ref = reference.loc[row["profile_id"]]
        output_row: dict[str, Any] = {
            "arm_id": row["arm_id"],
            "seed": int(row["seed"]),
            "profile_id": row["profile_id"],
        }
        for out_name, metric in metric_map.items():
            output_row[out_name] = float(row[metric]) / float(ref[metric])
        output_row["normalized_action_saturation_fraction"] = float(row["action_saturation_fraction"])
        output_row["common_guard_pass"] = all(
            output_row[name] <= 1.03 + 1e-15
            for name in ("common_iae_ratio", "worst_peak_ratio", "rocof_ratio")
        )
        output_row["action_stress_guard_pass"] = all(
            output_row[name] <= 1.10 + 1e-15
            for name in ("action_rms_ratio", "action_tv_ratio")
        )
        guard_rows.append(output_row)
    guard_df = pd.DataFrame(guard_rows).sort_values(["arm_id", "seed", "profile_id"])
    guard_df.to_csv(output / "registered_guard_ratios_by_profile.csv", index=False)

    worst = (
        guard_df.groupby(["arm_id", "seed"], as_index=False)
        .agg(
            common_iae_ratio=("common_iae_ratio", "max"),
            worst_peak_ratio=("worst_peak_ratio", "max"),
            rocof_ratio=("rocof_ratio", "max"),
            action_rms_ratio=("action_rms_ratio", "max"),
            action_tv_ratio=("action_tv_ratio", "max"),
            normalized_action_saturation_fraction=("normalized_action_saturation_fraction", "max"),
        )
        .sort_values(["arm_id", "seed"])
    )
    worst.to_csv(output / "registered_worst_guard_ratios.csv", index=False)

    formal = json.loads((root / "existing_r402/formals/endpoint_table.json").read_text(encoding="utf-8"))
    diffs: list[dict[str, Any]] = []
    for _, row in endpoint_df.iterrows():
        arm = str(row["arm_id"])
        seed = None if pd.isna(row["seed"]) else int(row["seed"])
        if seed is None:
            expected = formal["deterministic_aggregate"]
        else:
            expected = formal["per_seed_aggregates"][f"{arm}_s{seed}"]
        for metric in ("off_diagonal_response_energy", "disturbance_differential_energy"):
            actual = float(row[metric])
            target = float(expected[metric])
            diffs.append(
                {
                    "arm_id": arm,
                    "seed": seed,
                    "metric": metric,
                    "recomputed": actual,
                    "formal": target,
                    "abs_diff": abs(actual - target),
                    "rel_diff": abs(actual - target) / max(abs(target), 1e-300),
                }
            )
    pd.DataFrame(diffs).to_csv(output / "registered_recomputation_diff.csv", index=False)
    return profile_df, endpoint_df, guard_df, worst


def _cancelled_mean_penalty_ratio(values: np.ndarray) -> float:
    denominator = float(np.mean(values**2))
    if denominator == 0.0:
        return 0.0
    return float(np.mean(np.mean(values, axis=1) ** 2) / denominator)


def action_diagnostics(
    records: Sequence[EvaluationRecord], contract: Mapping[str, Any], output: Path
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    transform = np.asarray(contract["differential_transform"], dtype=float)
    lower_m = float(contract["decoder"]["m_lower_clamp"])
    lower_d = float(contract["decoder"]["d_lower_clamp"])
    slew = float(contract["action_slew_limit"])

    grouped: dict[tuple[str, int | None], list[EvaluationRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.arm_id, record.seed)].append(record)

    run_rows: list[dict[str, Any]] = []
    profile_rows: list[dict[str, Any]] = []
    trajectory_rows: list[dict[str, Any]] = []

    def make_row(block: Sequence[EvaluationRecord], arm: str, seed: int | None, profile: str | None) -> dict[str, Any]:
        arrays = [record_arrays(record) for record in block]
        actions = np.concatenate([row["action"] for row in arrays], axis=0)
        delta_m = np.concatenate([row["delta_m"] for row in arrays], axis=0)
        delta_d = np.concatenate([row["delta_d"] for row in arrays], axis=0)
        m_values = np.concatenate([row["m"] for row in arrays], axis=0)
        d_values = np.concatenate([row["d"] for row in arrays], axis=0)
        diffs = np.concatenate(
            [
                np.diff(np.concatenate([np.zeros((1, 4, 2)), row["action"]], axis=0), axis=0)
                for row in arrays
            ],
            axis=0,
        )
        common_orthonormal = 2.0 * np.mean(actions, axis=1)  # t x component
        differential = np.einsum("ij,tjk->tik", transform, actions)
        total_energy = float(np.sum(actions**2))
        common_energy = float(np.sum(common_orthonormal**2))
        differential_energy = float(np.sum(differential**2))
        return {
            "arm_id": arm,
            "seed": seed,
            "profile_id": profile,
            "trajectory_count": len(block),
            "scalar_action_samples": int(actions.size),
            "mean_action": float(np.mean(actions)),
            "mean_abs_action": float(np.mean(np.abs(actions))),
            "action_rms": float(np.sqrt(np.mean(actions**2))),
            "positive_action_fraction": float(np.mean(actions > 0.0)),
            "negative_action_fraction": float(np.mean(actions < 0.0)),
            "normalized_boundary_fraction": float(np.mean(np.abs(actions) >= 1.0 - 1e-9)),
            "slew_hit_fraction": float(np.mean(np.isclose(np.abs(diffs), slew, rtol=0.0, atol=5e-8))),
            "mean_delta_m": float(np.mean(delta_m)),
            "mean_delta_d": float(np.mean(delta_d)),
            "rms_delta_m": float(np.sqrt(np.mean(delta_m**2))),
            "rms_delta_d": float(np.sqrt(np.mean(delta_d**2))),
            "m_min": float(np.min(m_values)),
            "m_max": float(np.max(m_values)),
            "d_min": float(np.min(d_values)),
            "d_max": float(np.max(d_values)),
            "m_lower_clamp_fraction": float(np.mean(np.isclose(m_values, lower_m, rtol=0.0, atol=1e-8))),
            "d_lower_clamp_fraction": float(np.mean(np.isclose(d_values, lower_d, rtol=0.0, atol=1e-8))),
            "m_above_600_fraction": float(np.mean(m_values > 600.0 + 1e-8)),
            "d_above_300_fraction": float(np.mean(d_values > 300.0 + 1e-8)),
            "normalized_common_mode_energy_fraction": common_energy / max(total_energy, 1e-300),
            "normalized_differential_mode_energy_fraction": differential_energy / max(total_energy, 1e-300),
            "global_mean_cancellation_ratio_m": _cancelled_mean_penalty_ratio(delta_m),
            "global_mean_cancellation_ratio_d": _cancelled_mean_penalty_ratio(delta_d),
            # R402 defaults to mechanical_H, so the M mean is divided by two
            # before squaring; the D mean is not rescaled.
            "scalar_reward_m_penalty_coverage": 0.25 * _cancelled_mean_penalty_ratio(delta_m),
            "scalar_reward_d_penalty_coverage": _cancelled_mean_penalty_ratio(delta_d),
        }

    for (arm, seed), block in sorted(grouped.items(), key=lambda item: (item[0][0], -1 if item[0][1] is None else item[0][1])):
        run_rows.append(make_row(block, arm, seed, None))
        by_profile: dict[str, list[EvaluationRecord]] = defaultdict(list)
        for record in block:
            by_profile[record.profile_id].append(record)
        for profile, profile_block in sorted(by_profile.items()):
            profile_rows.append(make_row(profile_block, arm, seed, profile))
        for record in block:
            arrays = record_arrays(record)
            m_clamp = bool(np.any(np.isclose(arrays["m"], lower_m, rtol=0.0, atol=1e-8)))
            d_clamp = bool(np.any(np.isclose(arrays["d"], lower_d, rtol=0.0, atol=1e-8)))
            m_above = bool(np.any(arrays["m"] > 600.0 + 1e-8))
            d_above = bool(np.any(arrays["d"] > 300.0 + 1e-8))
            trajectory_rows.append(
                {
                    "arm_id": arm,
                    "seed": seed,
                    "profile_id": record.profile_id,
                    "scenario_id": record.scenario_id,
                    "pair_kind": record.payload["pair_kind"],
                    "sign": record.payload["sign"],
                    "any_m_lower_clamp": m_clamp,
                    "any_d_lower_clamp": d_clamp,
                    "any_physical_lower_clamp": m_clamp or d_clamp,
                    "any_m_above_600": m_above,
                    "any_d_above_300": d_above,
                    "any_reference_upper_box_excursion": m_above or d_above,
                }
            )

    run_df = pd.DataFrame(run_rows).sort_values(["arm_id", "seed"], na_position="first")
    profile_df = pd.DataFrame(profile_rows).sort_values(["arm_id", "seed", "profile_id"], na_position="first")
    trajectory_df = pd.DataFrame(trajectory_rows).sort_values(["arm_id", "seed", "profile_id", "scenario_id"], na_position="first")
    run_df.to_csv(output / "action_geometry_by_run.csv", index=False)
    profile_df.to_csv(output / "action_geometry_by_profile.csv", index=False)
    trajectory_df.to_csv(output / "physical_clamp_by_trajectory.csv", index=False)
    return run_df, profile_df, trajectory_df


def reconstructed_frequency_costs(
    records: Sequence[EvaluationRecord], contract: Mapping[str, Any], output: Path
) -> pd.DataFrame:
    nominal = float(contract["physical_nominal_frequency_hz"])
    dt = float(contract["dt_seconds"])
    transform = np.asarray(contract["differential_transform"], dtype=float)
    sigma_f = float(contract["reward_contract"]["cd_matd3"]["sigma_f_hz"])
    sigma_rocof = float(contract["reward_contract"]["cd_matd3"]["sigma_rocof_hz_s"])
    rows: list[dict[str, Any]] = []
    for record in records:
        arrays = record_arrays(record)
        deviation = arrays["frequency"] - nominal
        rocof = np.diff(np.vstack([arrays["initial_frequency"], arrays["frequency"]]), axis=0) / dt
        z_d = deviation @ transform.T
        common = float(
            np.sum(
                np.mean((deviation / sigma_f) ** 2, axis=1)
                + np.mean((rocof / sigma_rocof) ** 2, axis=1)
            )
        )
        frequency_differential = float(np.sum(np.sum((z_d / sigma_f) ** 2, axis=1) / 3.0))
        rows.append(
            {
                "arm_id": record.arm_id,
                "seed": record.seed,
                "profile_id": record.profile_id,
                "scenario_id": record.scenario_id,
                "pair_kind": record.payload["pair_kind"],
                "sign": record.payload["sign"],
                "common_cost_exact_from_frequency": common,
                "frequency_only_differential_cost": frequency_differential,
                "common_budget": float(contract["reward_contract"]["cd_matd3"]["common_budget_per_episode"]),
                "common_budget_exceeded": common > float(contract["reward_contract"]["cd_matd3"]["common_budget_per_episode"]),
                "full_differential_cost_available": False,
                "missing_term": "T_d P_es",
            }
        )
    df = pd.DataFrame(rows).sort_values(["arm_id", "seed", "profile_id", "scenario_id"], na_position="first")
    df.to_csv(output / "frequency_cost_reconstruction_by_trajectory.csv", index=False)
    summary = (
        df.groupby(["arm_id", "seed"], dropna=False, as_index=False)
        .agg(
            common_cost_mean=("common_cost_exact_from_frequency", "mean"),
            common_cost_median=("common_cost_exact_from_frequency", "median"),
            common_cost_min=("common_cost_exact_from_frequency", "min"),
            common_cost_max=("common_cost_exact_from_frequency", "max"),
            common_budget_exceed_fraction=("common_budget_exceeded", "mean"),
            frequency_only_differential_mean=("frequency_only_differential_cost", "mean"),
            frequency_only_differential_max=("frequency_only_differential_cost", "max"),
        )
    )
    summary.to_csv(output / "frequency_cost_reconstruction_by_run.csv", index=False)
    return summary


def _flatten_checkpoint_section(payload: Mapping[str, Any], section: str) -> torch.Tensor:
    tensors: list[torch.Tensor] = []
    value = payload[section]
    if section in {"actors", "actor_targets"}:
        for actor_id in sorted(value, key=int):
            for name in sorted(value[actor_id]):
                tensors.append(value[actor_id][name].detach().double().reshape(-1))
    else:
        for name in sorted(value):
            tensors.append(value[name].detach().double().reshape(-1))
    return torch.cat(tensors)


def checkpoint_diagnostics(root: Path, contract: Mapping[str, Any], output: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ckpt_root = root / "existing_r402/checkpoints"
    lambda_rows: list[dict[str, Any]] = []
    tail_rows: list[dict[str, Any]] = []
    drift_rows: list[dict[str, Any]] = []
    slot_rows: list[dict[str, Any]] = []
    equality_rows: list[dict[str, Any]] = []
    target_gap_rows: list[dict[str, Any]] = []
    schedule = list(contract["training_contract"]["development_scenario_order"])

    for arm in LEARNING_ARMS:
        for seed in (401, 402, 403):
            run = ckpt_root / arm / f"seed{seed}"
            snapshots: dict[int, Mapping[str, Any]] = {}
            for episode in CHECKPOINT_EPISODES:
                payload = torch.load(
                    run / "snapshots" / f"episode{episode}.pt",
                    map_location="cpu",
                    weights_only=True,
                )
                snapshots[episode] = payload
                lambda_rows.append(
                    {
                        "arm_id": arm,
                        "seed": seed,
                        "episode": episode,
                        "lagrange": float(payload.get("lagrange", 0.0)),
                    }
                )
            final_payload = torch.load(run / "final.pt", map_location="cpu", weights_only=True)

            max_abs = 0.0
            for section in ("actors", "critic", "actor_targets", "critic_target"):
                final_vec = _flatten_checkpoint_section(final_payload, section)
                snap_vec = _flatten_checkpoint_section(snapshots[1440], section)
                max_abs = max(max_abs, float(torch.max(torch.abs(final_vec - snap_vec))))
            equality_rows.append(
                {
                    "arm_id": arm,
                    "seed": seed,
                    "final_equals_episode1440_tensorwise": max_abs == 0.0,
                    "maximum_absolute_tensor_difference": max_abs,
                    "final_file_sha256": sha256_file(run / "final.pt"),
                    "episode1440_file_sha256": sha256_file(run / "snapshots/episode1440.pt"),
                }
            )

            for section in ("actors", "critic"):
                for previous, current in zip(CHECKPOINT_EPISODES, CHECKPOINT_EPISODES[1:]):
                    a = _flatten_checkpoint_section(snapshots[previous], section)
                    b = _flatten_checkpoint_section(snapshots[current], section)
                    change = float(torch.linalg.vector_norm(b - a))
                    norm = float(torch.linalg.vector_norm(a))
                    drift_rows.append(
                        {
                            "arm_id": arm,
                            "seed": seed,
                            "section": section,
                            "from_episode": previous,
                            "to_episode": current,
                            "l2_parameter_change": change,
                            "relative_parameter_change": change / max(norm, 1e-300),
                        }
                    )

            actor = _flatten_checkpoint_section(final_payload, "actors")
            actor_target = _flatten_checkpoint_section(final_payload, "actor_targets")
            critic = _flatten_checkpoint_section(final_payload, "critic")
            critic_target = _flatten_checkpoint_section(final_payload, "critic_target")
            target_gap_rows.append(
                {
                    "arm_id": arm,
                    "seed": seed,
                    "actor_target_relative_gap": float(torch.linalg.vector_norm(actor - actor_target)) / max(float(torch.linalg.vector_norm(actor)), 1e-300),
                    "critic_target_relative_gap": float(torch.linalg.vector_norm(critic - critic_target)) / max(float(torch.linalg.vector_norm(critic)), 1e-300),
                }
            )

            for actor_id, state_dict in final_payload["actors"].items():
                first_weight = state_dict["net.0.weight"].detach().double().numpy()
                slot_norms = np.linalg.norm(first_weight, axis=0)
                row: dict[str, Any] = {
                    "arm_id": arm,
                    "seed": seed,
                    "actor_id": int(actor_id),
                    "local_slot_mean_norm": float(np.mean(slot_norms[:3])),
                    "neighbour_slot_mean_norm": float(np.mean(slot_norms[3:])),
                    "neighbour_to_local_norm_ratio": float(np.mean(slot_norms[3:]) / max(np.mean(slot_norms[:3]), 1e-300)),
                }
                for index, value in enumerate(slot_norms):
                    row[f"slot_{index}_first_layer_norm"] = float(value)
                slot_rows.append(row)

            manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
            common_costs = list(manifest.get("episode_common_costs", []))
            trace = list(manifest.get("lagrange_trace", []))
            if arm.startswith("cd_matd3"):
                if len(common_costs) != 20 or len(trace) != 20:
                    raise ValueError(f"unexpected CD tail length for {arm} seed {seed}")
                first_episode = int(manifest["episodes_attempted"]) - len(trace) + 1
                for index, (cost, lambda_post) in enumerate(zip(common_costs, trace)):
                    episode = first_episode + index
                    lambda_used = math.nan if index == 0 else float(trace[index - 1])
                    tail_rows.append(
                        {
                            "arm_id": arm,
                            "seed": seed,
                            "episode": episode,
                            "scenario_id": schedule[(episode - 1) % len(schedule)],
                            "common_cost": float(cost),
                            "common_budget": float(contract["reward_contract"]["cd_matd3"]["common_budget_per_episode"]),
                            "lambda_used_during_episode": lambda_used,
                            "lambda_post_episode": float(lambda_post),
                            "lambda_used_known": index > 0,
                            "lambda_used_zero": None if index == 0 else lambda_used == 0.0,
                            "lambda_used_below_0_05": None if index == 0 else lambda_used < 0.05,
                            "lambda_used_below_0_1": None if index == 0 else lambda_used < 0.1,
                        }
                    )

    lambda_df = pd.DataFrame(lambda_rows).sort_values(["arm_id", "seed", "episode"])
    tail_df = pd.DataFrame(tail_rows).sort_values(["arm_id", "seed", "episode"])
    drift_df = pd.DataFrame(drift_rows).sort_values(["arm_id", "seed", "section", "from_episode"])
    slot_df = pd.DataFrame(slot_rows).sort_values(["arm_id", "seed", "actor_id"])
    lambda_df.to_csv(output / "checkpoint_lagrange_history.csv", index=False)
    tail_df.to_csv(output / "retained_tail_lambda_usage.csv", index=False)
    drift_df.to_csv(output / "checkpoint_parameter_drift.csv", index=False)
    slot_df.to_csv(output / "actor_input_slot_weight_norms.csv", index=False)
    pd.DataFrame(equality_rows).to_csv(output / "final_checkpoint_identity.csv", index=False)
    pd.DataFrame(target_gap_rows).to_csv(output / "target_network_gaps.csv", index=False)

    tail_summary = (
        tail_df[tail_df["lambda_used_known"]]
        .groupby(["arm_id", "seed"], as_index=False)
        .agg(
            known_episode_count=("lambda_used_during_episode", "count"),
            lambda_used_min=("lambda_used_during_episode", "min"),
            lambda_used_median=("lambda_used_during_episode", "median"),
            lambda_used_max=("lambda_used_during_episode", "max"),
            lambda_used_zero_fraction=("lambda_used_zero", "mean"),
            lambda_used_below_0_05_fraction=("lambda_used_below_0_05", "mean"),
            lambda_used_below_0_1_fraction=("lambda_used_below_0_1", "mean"),
        )
    )
    tail_summary.to_csv(output / "retained_tail_lambda_summary.csv", index=False)
    return lambda_df, tail_df, drift_df, slot_df


def verify_integrity(root: Path, output: Path, source_zip: Path | None = None) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    top_lines = [line for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines() if line.strip()]
    top_bad = 0
    for line in top_lines:
        expected, rel = line.split(None, 1)
        rel = rel.strip().lstrip("*")
        path = root / rel
        actual = sha256_file(path) if path.is_file() else None
        top_bad += int(actual != expected)
    rows.append(
        {
            "check": "top_level_SHA256SUMS",
            "status": "PASS" if top_bad == 0 else "FAIL",
            "checked": len(top_lines),
            "failed": top_bad,
            "detail": "All listed files match" if top_bad == 0 else "At least one listed file mismatched",
        }
    )

    package_manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    manifest_entries = {str(row["path"]): row for row in package_manifest["files"]}
    actual_files = {
        path.relative_to(root).as_posix(): path for path in root.rglob("*") if path.is_file()
    }
    bad_manifest_hashes = 0
    for rel, metadata in manifest_entries.items():
        path = root / rel
        if not path.is_file() or path.stat().st_size != int(metadata["size"]) or sha256_file(path) != str(metadata["sha256"]):
            bad_manifest_hashes += 1
    unlisted = sorted(set(actual_files) - set(manifest_entries))
    rows.append(
        {
            "check": "manifest_entry_hashes",
            "status": "PASS" if bad_manifest_hashes == 0 else "FAIL",
            "checked": len(manifest_entries),
            "failed": bad_manifest_hashes,
            "detail": "Hashes and sizes match for listed entries",
        }
    )
    rows.append(
        {
            "check": "manifest_inventory_completeness",
            "status": "WARN" if unlisted else "PASS",
            "checked": len(actual_files),
            "failed": len(unlisted),
            "detail": "Unlisted files: " + ", ".join(unlisted),
        }
    )

    sidecar_checked = 0
    sidecar_failed = 0
    for sidecar in root.rglob("*.sha256"):
        target = Path(str(sidecar)[: -len(".sha256")])
        if not target.is_file():
            # Files such as environment/source_hashes.sha256 are inventories,
            # not filename sidecars.
            continue
        words = sidecar.read_text(encoding="ascii", errors="replace").split()
        expected = words[0] if words else ""
        sidecar_checked += 1
        sidecar_failed += int(sha256_file(target) != expected)
    rows.append(
        {
            "check": "filename_sha256_sidecars",
            "status": "PASS" if sidecar_failed == 0 else "FAIL",
            "checked": sidecar_checked,
            "failed": sidecar_failed,
            "detail": "All actual filename sidecars match" if sidecar_failed == 0 else "Sidecar mismatch detected",
        }
    )

    if source_zip is not None:
        bad_members = 0
        member_count = 0
        with zipfile.ZipFile(source_zip) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                member_count += 1
                try:
                    with archive.open(info) as handle:
                        while handle.read(1024 * 1024):
                            pass
                except Exception:
                    bad_members += 1
        rows.append(
            {
                "check": "zip_crc",
                "status": "PASS" if bad_members == 0 else "FAIL",
                "checked": member_count,
                "failed": bad_members,
                "detail": f"source_zip_sha256={sha256_file(source_zip)}",
            }
        )

    df = pd.DataFrame(rows)
    df.to_csv(output / "package_integrity.csv", index=False)
    write_json(
        output / "package_inventory_gap.json",
        {
            "manifest_declared_file_count": int(package_manifest["file_count"]),
            "manifest_entry_count": len(manifest_entries),
            "actual_file_count": len(actual_files),
            "unlisted_file_count": len(unlisted),
            "unlisted_files": unlisted,
        },
    )
    return df


def line_number(path: Path, pattern: str, start: int = 1) -> int | None:
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if index >= start and pattern in line:
            return index
    return None


def static_source_findings(root: Path, output: Path) -> pd.DataFrame:
    source_root = root / "existing_r402/source_files"
    runner = source_root / "scripts/run_r402_cd_matd3_canary.py"
    learner = source_root / "src/andes_rl_kundur/agents/cd_matd3.py"
    env = source_root / "src/andes_rl_kundur/env/andes/base_env.py"
    contract = source_root / "src/andes_rl_kundur/evaluation/cd_matd3_canary.py"
    summarizer = source_root / "src/andes_rl_kundur/evaluation/md_decoupling_headroom.py"
    projector = source_root / "src/andes_rl_kundur/control/per_vsg_md.py"
    v4_config = source_root / "src/andes_rl_kundur/env/andes/v4_config.py"

    source_text = {
        "runner": runner.read_text(encoding="utf-8"),
        "learner": learner.read_text(encoding="utf-8"),
        "env": env.read_text(encoding="utf-8"),
        "contract": contract.read_text(encoding="utf-8"),
        "summarizer": summarizer.read_text(encoding="utf-8"),
        "projector": projector.read_text(encoding="utf-8"),
        "v4_config": v4_config.read_text(encoding="utf-8"),
    }

    checks = {
        "runner_masks_runtime_actor_input": "actor_joint = _mask_actor_obs(arm_id, joint)" in source_text["runner"],
        "runner_stores_unmasked_joint": "agent.store(\n                    joint," in source_text["runner"],
        "learner_target_uses_full_next_obs": 'next_actions = self._target_actions(batch["next_obs"])' in source_text["learner"],
        "learner_actor_uses_full_obs_slice": 'batch["obs"][:, i * OBS_DIM:(i + 1) * OBS_DIM]' in source_text["learner"],
        "external_stateful_projector": "self.previous_action = action.copy()" in source_text["projector"],
        "actor_observation_dim_is_seven": "OBS_DIM = 7" in source_text["learner"],
        "target_action_has_no_slew_projection": "return (target + noise).clamp(-1.0, 1.0)" in source_text["learner"],
        "deterministic_only_frequency_adapter": "adapt_v4_observations_to_physical(observation)" in source_text["runner"],
        "scalar_penalty_uses_global_mean": "global_ah_avg = float(np.mean(delta_M))" in source_text["env"],
        "physical_parameter_map_has_lower_only": "M_new[i] = max(self.M0[i] + delta_M[i], M_MIN)" in source_text["env"],
        "registered_saturation_is_normalized_boundary": "all_actions <= lower + tolerance" in source_text["summarizer"],
        "differential_cost_uses_absolute_p_es": "p_d = np.asarray(p_es, dtype=float) @ transform.T" in source_text["learner"],
        "historical_memoryless_obs_default": "include_own_action_obs: bool = False" in source_text["v4_config"],
        "observation_rows_omit_md_profile_time": all(token in source_text["env"] for token in ("o[0] = P_es[i] / 2.0", "o[1] = d_omega[i] / 3.0", "o[2] = omega_dot[i] * self._omega_scale / 5.0")),
    }
    if not all(checks.values()):
        missing = [name for name, ok in checks.items() if not ok]
        raise RuntimeError("static source audit patterns not found: " + ", ".join(missing))

    findings = [
        {
            "finding_id": "F1",
            "finding": "no-message actor train–execution masking mismatch",
            "epistemic_status": "PROVED-MATHEMATICALLY",
            "evidence_class": "CODE-MECHANICAL",
            "severity": "CRITICAL",
            "evidence": "Runtime action selection masks slots 3..6, but replay stores full joint/next_joint and actor/target updates consume full slices.",
            "source_refs": "scripts/run_r402_cd_matd3_canary.py:L390-L445; src/andes_rl_kundur/agents/cd_matd3.py:L206-L257,L298-L322",
            "causal_scope": "Invalidates the matched message-vs-no-message estimand; endpoint effect of a corrected mask is not identified.",
        },
        {
            "finding_id": "F2",
            "finding": "stateful slew projector omitted from learner state and target/actor optimization",
            "epistemic_status": "PROVED-MATHEMATICALLY",
            "evidence_class": "CODE-MECHANICAL",
            "severity": "CRITICAL",
            "evidence": "Executed action depends on previous_action; observation has seven slots and excludes it; TD3 target and actor paths use raw clipped actions without the projector.",
            "source_refs": "control/per_vsg_md.py:L63-L103; scripts/run_r402_cd_matd3_canary.py:L357-L445; agents/cd_matd3.py:L206-L238,L298-L322",
            "causal_scope": "Creates a non-Markov learner interface and trains critics/actors on potentially non-executable one-step actions. Physical endpoint effect still requires intervention.",
        },
        {
            "finding_id": "F3",
            "finding": "frequency-observation adapter is applied to deterministic comparator but not learning arms",
            "epistemic_status": "PROVED-MATHEMATICALLY",
            "evidence_class": "CODE-MECHANICAL",
            "severity": "HIGH",
            "evidence": "Frozen contract names a 50-to-60 adapter; deterministic evaluation calls it, while training/evaluation learning paths call _joint_obs directly.",
            "source_refs": "evaluation/cd_matd3_canary.py:L207-L214; scripts/run_r402_cd_matd3_canary.py:L390-L392,L575-L583",
            "causal_scope": "Establishes path asymmetry/contract ambiguity; does not prove failure because training and evaluation share the same raw learner scale.",
        },
        {
            "finding_id": "F4",
            "finding": "scalar TD3 action terms penalize common mean, not componentwise effort",
            "epistemic_status": "PROVED-MATHEMATICALLY",
            "evidence_class": "CODE-MECHANICAL",
            "severity": "HIGH",
            "evidence": "Reward uses squared mean(delta_M) and squared mean(delta_D); cancelling differential actions can be large with near-zero penalty.",
            "source_refs": "env/andes/base_env.py:L685-L750",
            "causal_scope": "Weakens the claim that scalar-TD3 failure is strong counter-evidence against missing RMS/TV effort regularization.",
        },
        {
            "finding_id": "F5",
            "finding": "registered saturation guard does not measure physical M/D clamp occupancy",
            "epistemic_status": "PROVED-MATHEMATICALLY",
            "evidence_class": "CODE-MECHANICAL",
            "severity": "HIGH",
            "evidence": "The guard counts normalized action at +/-1; plant mapping separately applies M>=20 and D>=10 lower clamps.",
            "source_refs": "env/andes/base_env.py:L358-L371; evaluation/md_decoupling_headroom.py:L416-L422",
            "causal_scope": "A reported saturation fraction of zero cannot be interpreted as absence of physical clipping/dead zones.",
        },
        {
            "finding_id": "F6",
            "finding": "CD differential objective is not the signed odd-response endpoint",
            "epistemic_status": "PROVED-MATHEMATICALLY",
            "evidence_class": "CODE-MECHANICAL",
            "severity": "HIGH",
            "evidence": "Training squares T_d(f-60) and absolute T_d P_es per trajectory; the registered endpoint uses positive/negative odd response pairs and a finite-window cross term.",
            "source_refs": "agents/cd_matd3.py:L456-L482; evaluation/md_decoupling_headroom.py:L331-L371",
            "causal_scope": "Establishes objective–gate mismatch; magnitude of the missing P_es term is unavailable.",
        },
        {
            "finding_id": "F7",
            "finding": "CD critic component-order docstring conflicts with actual storage/objective order",
            "epistemic_status": "PROVED-MATHEMATICALLY",
            "evidence_class": "CODE-MECHANICAL",
            "severity": "LOW",
            "evidence": "Docstring says common,differential, but runner stores -differential,-common and actor correctly uses q[0]+lambda*q[1].",
            "source_refs": "agents/cd_matd3.py:L290-L322; scripts/run_r402_cd_matd3_canary.py:L428-L445",
            "causal_scope": "Documentation defect only; runtime arithmetic is internally consistent.",
        },
        {
            "finding_id": "F8",
            "finding": "memoryless actor state omits profile-dependent M/D state and explicit phase information",
            "epistemic_status": "PROVED-MATHEMATICALLY",
            "evidence_class": "CODE-MECHANICAL",
            "severity": "MEDIUM",
            "evidence": "The frozen actor row has seven P/frequency/RoCoF slots. Historical V4 defaults exclude previous action and time, and no baseline/current M, D or profile identifier is included although decoder dynamics depend on them.",
            "source_refs": "agents/cd_matd3.py:L29-L47; env/andes/base_env.py:L557-L622; env/andes/v4_config.py:L83-L112; scripts/run_r402_cd_matd3_canary.py:L220-L249",
            "causal_scope": "Establishes a broader partial-observation design fact. It does not prove impossibility because the deterministic local-neighbour controller succeeds on the same direct-M/D object.",
        },
    ]
    df = pd.DataFrame(findings)
    df.to_csv(output / "implementation_findings.csv", index=False)
    write_json(output / "static_source_pattern_checks.json", checks)
    return df


def package_documentation_findings(root: Path, output: Path) -> pd.DataFrame:
    training_readme = (root / "training_diagnostics/README.md").read_text(encoding="utf-8")
    known = (root / "provenance/known_exceptions.md").read_text(encoding="utf-8")
    endpoint_contract = (root / "contract/endpoint_and_guard_definition.md").read_text(encoding="utf-8")
    run_summary = pd.read_csv(root / "training_diagnostics/run_summary.csv")
    cd_rows = run_summary[run_summary["arm_id"].str.startswith("cd_matd3")]
    actual_tail_count = int(cd_rows["retained_common_costs"].sum())
    rows = [
        {
            "issue_id": "D1",
            "issue": "Training diagnostics README says CD common-cost/lambda lists are empty",
            "observed": "README line 8 and known_exceptions line 35 state empty lists",
            "correct_value": f"Six CD manifests each retain 20 common costs and 20 lambda values ({actual_tail_count} common-cost values total)",
            "impact": "Documentation/availability-map defect; it would incorrectly discard usable multiplier-tail evidence.",
        },
        {
            "issue_id": "D2",
            "issue": "Decision-tree document says 240 + 24 records",
            "observed": "endpoint_and_guard_definition.md contains '240 + 24 records'",
            "correct_value": "240 total = 216 learning + 24 deterministic",
            "impact": "Repeats the previously repaired counting ambiguity; no endpoint/classification effect.",
        },
        {
            "issue_id": "D3",
            "issue": "Package manifest claims full inventory but omits files",
            "observed": "manifest.json has 387 entries while extracted package has 399 files",
            "correct_value": "12 files are unlisted, including all nine run manifest.json files, root manifest/SHA files, and nested audit SHA file",
            "impact": "Top-level inventory is incomplete, although run manifests have valid filename sidecars and listed files hash correctly.",
        },
        {
            "issue_id": "D4",
            "issue": "Copied source subset is not import-complete",
            "observed": "Three project-local imports cannot be resolved inside existing_r402/source_files",
            "correct_value": "Missing agents/networks.py and scenarios/contract.py (referenced by the frozen learner/environment source)",
            "impact": "The bundle supports static audit but is not a self-contained executable reproduction of the historical learner.",
        },
    ]
    # Keep assertions explicit so the audit fails if the package changes.
    if "episode_common_costs / lagrange_trace lists are empty" not in training_readme:
        raise RuntimeError("Expected training README contradiction not found")
    if "empty lists for episode_common_costs / lagrange_trace" not in known:
        raise RuntimeError("Expected known-exceptions contradiction not found")
    if "240 + 24 records" not in endpoint_contract:
        raise RuntimeError("Expected 240 + 24 wording not found")
    df = pd.DataFrame(rows)
    df.to_csv(output / "package_documentation_findings.csv", index=False)
    return df


def hypothesis_verdicts(output: Path) -> pd.DataFrame:
    rows = [
        ["H1", "R402 learned policies fail registered physical gate", "REGISTERED-EMPIRICAL", "Established", "All 36 learning arm-seed-profile blocks fail common no-harm and action-stress families; both endpoint medians are worse than deterministic."],
        ["H2", "Runtime messages are useless/harmful", "UNAVAILABLE", "Not identified", "The no-message arm is not a clean ablation because actor/target training sees full message slots while execution masks them."],
        ["H3", "No-message train–execution mask mismatch contributed to its failure", "PLAUSIBLE-NOT-IDENTIFIED", "Strong candidate", "Code defect is mechanical and final weights load message slots, but no corrected paired ANDES intervention exists."],
        ["H4", "Stateful slew/hidden-action mismatch contributed to all learned-arm failures", "PLAUSIBLE-NOT-IDENTIFIED", "Strongest shared implementation candidate", "Code mismatch is mechanical and slew is frequently active; corrected paired experiment absent."],
        ["H5", "Missing componentwise action-effort regularization caused action stress", "PLAUSIBLE-NOT-IDENTIFIED", "Supported", "CD objective omits effort and observed actions/TV/clamps are large; R404 combines effort with another repair and cannot isolate the effect."],
        ["H6", "Missing effort alone caused endpoint degradation", "PLAUSIBLE-NOT-IDENTIFIED", "Insufficient", "Action stress can alter dynamics, but endpoint causality is not isolated and objective/optimization/interface alternatives remain."],
        ["H7", "Scalar TD3 disproves the effort hypothesis", "CONTRADICTED", "False as stated", "Its action terms penalize squared global means, not componentwise RMS/TV; differential cancellation can evade them."],
        ["H8", "Multiplier deleted the common objective throughout training", "CONTRADICTED", "Too strong", "Only final-20 and six coarse checkpoints exist; lambda is often zero/small in the tail but not continuously observed and gradient scales are missing."],
        ["H9", "Multiplier calibration weakened common pressure in the retained tail", "POST-HOC-DIAGNOSTIC", "Supported", "Across the 19 exactly recoverable final-tail episode usages per CD run, zero-lambda fractions are 0.368–0.895 and <0.1 fractions are 0.737–1.000."],
        ["H10", "Objective–gate mismatch exists", "PROVED-MATHEMATICALLY", "Established", "Training per-trajectory squared costs differ from signed odd-response endpoints and reference-relative guards; P_es term is unavailable in evaluation logs."],
        ["H11", "Optimization failed to converge", "UNAVAILABLE", "Not established", "No losses, Bellman calibration, replay coverage or checkpoint performance; substantial late parameter drift is diagnostic, not a certificate."],
        ["H12", "Direct M/D has no physical authority", "CONTRADICTED", "False", "The deterministic direct-M/D controller materially improves endpoints and passes guards."],
        ["H13", "Direct M/D has limited learnable incremental headroom", "PLAUSIBLE-NOT-IDENTIFIED", "Open", "Strong comparator and interface geometry support plausibility; R402-specific DAE authority matrices/interventions are absent."],
        ["H14", "Energy-port success proves action-basis mismatch caused R402", "CONTRADICTED", "Invalid inference", "Energy-port evidence is a different actuator/estimator/bank object and was not a matched intervention."],
        ["H15", "Physical actuator map was unsaturated", "CONTRADICTED", "False if saturation means lower-clamp inactivity", "Normalized boundary saturation is zero, but 179/216 learning trajectories contain at least one physical M/D lower-clamp event."],
        ["H16", "Frequency-scale path asymmetry caused failure", "PLAUSIBLE-NOT-IDENTIFIED", "Open", "Comparator and learner paths differ, but learner train/eval scale is internally matched; a uniform-adapter reproduction is needed."],
        ["H17", "Memoryless observation/state insufficiency materially contributed to failure", "PLAUSIBLE-NOT-IDENTIFIED", "Serious alternative", "The actor omits previous action, current/baseline M-D, profile identity and explicit phase. F2 proves one hidden action-state mismatch, but the deterministic reference rules out a blanket impossibility claim."],
        ["H18", "Centralized-critic credit assignment caused the failure", "UNAVAILABLE", "Not identified", "Four independent actors use a shared global critic and coordinate-wise actor updates, but no per-agent counterfactual values, gradient decomposition or calibrated alternative is retained."],
        ["H19", "Development-to-evaluation distribution shift caused the failure", "PLAUSIBLE-NOT-IDENTIFIED", "Cannot separate fit from generalization", "Training and evaluation profiles differ, while no final or periodic learned-checkpoint evaluation on the development profiles was retained."],
    ]
    df = pd.DataFrame(rows, columns=["hypothesis_id", "hypothesis", "epistemic_status", "verdict", "basis"])
    df.to_csv(output / "hypothesis_verdicts.csv", index=False)
    return df


def next_experiment_matrix(output: Path) -> pd.DataFrame:
    rows = [
        ["E0", "Instrumented frozen-code reproduction", "Historical code unchanged; add complete logs, development-profile checkpoint evaluation and held-out Q calibration only", "Fresh paired seeds; evaluate fixed checkpoints on development, diagnostic and fresh held-out banks", "Separates package/log absence, optimization/credit diagnostics and fit-versus-distribution-shift; baseline for all interventions", "P0", "Required"],
        ["E1", "No-message mask-consistency fix", "Mask neighbour slots in all actor and target-actor forwards; critic may retain full centralized state", "Paired with E0, same random numbers", "Identifies effect of F1 and restores valid message/no-message estimand", "P0", "Required before any message claim"],
        ["E2", "Slew-aware Markov action interface", "Preserve actor target-action semantics; augment state with previous executed action; project behavior, target and online actor actions through the same frozen slew map", "Paired with E0 and E1", "Identifies effect of F2 on action stress/endpoints without bundling command reparameterization", "P0", "Required before optimization attribution"],
        ["E3", "Uniform frequency adapter", "Apply the sealed 50-to-60 conversion consistently to every actor arm, or formally reseal legacy scale for all comparators", "Paired common-random-number reproduction", "Resolves F3 contract/comparator asymmetry", "P1", "High"],
        ["E4", "Effort-only intervention", "Add componentwise executed-action magnitude and increment penalty; keep common weight/endpoint objective fixed", "Run after E1+E2 code validity", "Identifies action-effort effect without bundling multiplier repair", "P1", "High"],
        ["E5", "Multiplier-only intervention", "Fixed common weight versus projected multiplier; no effort change", "Run after E1+E2", "Identifies multiplier calibration effect", "P1", "High"],
        ["E6", "Objective-alignment intervention", "Baseline-subtracted/signed-pair-compatible differential target; log full P_es", "Run after E1+E2", "Identifies objective–gate mismatch, including absolute P_es term", "P1", "High"],
        ["E7", "Frozen-policy message interventions M0–M7", "True/zero/delay/permutation/swap/noise/slot perturbations", "Use corrected message-trained checkpoints and common random numbers", "Value-of-information and sensitivity; not a substitute for E1", "P1", "High"],
        ["E8", "R402-specific DAE/LTV authority export", "Actual f_x,f_y,g_x,g_y,f_u,g_u and constrained 30-step maps at all profiles", "Non-training prospective calculation", "Bounds direct-M/D authority and conditioning", "P2", "Journal-grade"],
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "experiment_id",
            "name",
            "single_change",
            "pairing",
            "causal_question",
            "priority",
            "necessity",
        ],
    )
    df.to_csv(output / "required_next_experiments.csv", index=False)
    return df



def descriptive_endpoint_comparisons(endpoint_df: pd.DataFrame, output: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create descriptive seed-median ratios and matched-arm contrasts.

    These are arithmetic summaries only.  In particular, the message/no-message
    contrast is not promoted to a causal message estimand because source audit F1
    shows that the no-message actor was trained with unmasked neighbour slots.
    """

    deterministic = endpoint_df[endpoint_df["arm_id"] == DETERMINISTIC_ARM]
    if deterministic.shape[0] != 1:
        raise ValueError("expected one deterministic aggregate row")
    det_cross = float(deterministic.iloc[0]["off_diagonal_response_energy"])
    det_diff = float(deterministic.iloc[0]["disturbance_differential_energy"])
    rows: list[dict[str, Any]] = []
    for arm in LEARNING_ARMS:
        group = endpoint_df[endpoint_df["arm_id"] == arm]
        cross = float(group["off_diagonal_response_energy"].median())
        differential = float(group["disturbance_differential_energy"].median())
        rows.append(
            {
                "arm_id": arm,
                "seed_count": int(group.shape[0]),
                "seed_median_off_diagonal_response_energy": cross,
                "seed_median_disturbance_differential_energy": differential,
                "cross_ratio_to_deterministic": cross / det_cross,
                "differential_ratio_to_deterministic": differential / det_diff,
                "cross_improvement_percent_vs_deterministic": 100.0 * (det_cross - cross) / det_cross,
                "differential_improvement_percent_vs_deterministic": 100.0 * (det_diff - differential) / det_diff,
            }
        )
    median_df = pd.DataFrame(rows)
    median_df.to_csv(output / "registered_seed_medians.csv", index=False)

    pivot = endpoint_df[endpoint_df["arm_id"].isin(LEARNING_ARMS)].pivot(
        index="seed", columns="arm_id",
        values=["off_diagonal_response_energy", "disturbance_differential_energy"],
    )
    contrasts: list[dict[str, Any]] = []
    for seed in sorted(int(value) for value in pivot.index):
        cross_message = float(pivot.loc[seed, ("off_diagonal_response_energy", "cd_matd3_message")])
        cross_no = float(pivot.loc[seed, ("off_diagonal_response_energy", "cd_matd3_no_message")])
        diff_message = float(pivot.loc[seed, ("disturbance_differential_energy", "cd_matd3_message")])
        diff_no = float(pivot.loc[seed, ("disturbance_differential_energy", "cd_matd3_no_message")])
        contrasts.append(
            {
                "seed": seed,
                "cross_message_minus_no_message": cross_message - cross_no,
                "cross_percent_change_message_vs_no_message": 100.0 * (cross_message - cross_no) / cross_no,
                "differential_message_minus_no_message": diff_message - diff_no,
                "differential_percent_change_message_vs_no_message": 100.0 * (diff_message - diff_no) / diff_no,
                "causal_interpretation_allowed": False,
                "reason": "F1 no-message actor train-execution masking mismatch",
            }
        )
    contrast_df = pd.DataFrame(contrasts)
    contrast_df.to_csv(output / "descriptive_message_no_message_contrasts.csv", index=False)
    return median_df, contrast_df


def decoder_asymmetry_theory(output: Path) -> None:
    sigma = 0.1
    expected_positive_part = sigma / math.sqrt(2.0 * math.pi)
    expected_delta = 400.0 * expected_positive_part
    payload = {
        "decoder": {
            "positive_slope": 600.0,
            "negative_slope": 200.0,
            "formula": "delta_q(a)=600*a for a>=0 and 200*a for a<0",
        },
        "symmetric_zero_mean_action_identity": {
            "formula": "E[delta_q(A)] = 400 E[A_+] > 0 for any nondegenerate distribution symmetric about zero",
            "interpretation": "zero-mean normalized exploration is not zero-mean in decoded physical parameter space",
        },
        "gaussian_example": {
            "sigma": sigma,
            "E_A_positive": expected_positive_part,
            "E_delta_q_before_slew_clamp": expected_delta,
            "units": "same units as decoded Delta M or Delta D",
            "scope": "pre-slew/pre-clamp analytic reference only",
        },
    }
    write_json(output / "decoder_asymmetry_theory.json", payload)


def source_dependency_gaps(root: Path, output: Path) -> pd.DataFrame:
    """Find project-local imports that cannot be resolved inside the copied source subset."""

    source_root = root / "existing_r402/source_files"
    rows: list[dict[str, Any]] = []
    for path in sorted(source_root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            module = str(node.module)
            if not module.startswith("andes_rl_kundur"):
                continue
            module_file = source_root / "src" / Path(*module.split("."))
            candidate_py = module_file.with_suffix(".py")
            candidate_init = module_file / "__init__.py"
            resolved = candidate_py.is_file() or candidate_init.is_file()
            rows.append(
                {
                    "source_file": path.relative_to(source_root).as_posix(),
                    "imported_module": module,
                    "resolved_inside_bundle": resolved,
                    "expected_python_file": candidate_py.relative_to(source_root).as_posix(),
                }
            )
    df = pd.DataFrame(rows).drop_duplicates().sort_values(
        ["resolved_inside_bundle", "source_file", "imported_module"]
    )
    df.to_csv(output / "source_dependency_resolution.csv", index=False)
    unresolved = df[~df["resolved_inside_bundle"]]
    if set(unresolved["imported_module"]) != {
        "andes_rl_kundur.agents.networks",
        "andes_rl_kundur.scenarios.contract",
    }:
        raise RuntimeError("unexpected copied-source dependency gap set")
    return df


def evidence_coverage_matrix(output: Path) -> pd.DataFrame:
    rows = [
        ["C1", "Registered R402 trajectories/endpoints/guards", "available", "240 trajectories; 40 profile summaries; exact endpoint recomputation", "Confirms CANARY-FAIL only"],
        ["C2", "Final and periodic checkpoints", "available", "9 final + 54 periodic checkpoints", "Supports coarse parameter/lambda diagnostics"],
        ["C3", "Full 1440-episode cost/lambda history", "absent", "Only final 20 values plus six snapshot lambdas", "Cannot characterize whole-run multiplier exposure"],
        ["C4", "Actor/critic update logs and Q calibration", "absent", "No losses, TD residuals, gradient decomposition, held-out returns", "Optimization/convergence cause unavailable"],
        ["C5", "Replay snapshots and support diagnostics", "absent", "In-memory ring discarded", "Coverage/OOD cause unavailable"],
        ["C6", "Complete evaluation P_es and cost decomposition", "absent", "Frequency/M/D/action retained; P_es not retained", "Full differential training objective cannot be reconstructed"],
        ["C7", "Raw observation and pre-slew action chain", "absent", "Only post-slew normalized action stored", "Cannot replay exact actor inputs or projection counterfactuals"],
        ["C8", "Frozen-policy M0-M7 interventions", "not_executed", "Manifest only", "Runtime-message value remains unidentified"],
        ["C9", "Successor S0-S5 paired training", "not_executed", "Contract only; no fresh seeds/banks", "Multiplier/effort/alignment causal effects remain unidentified"],
        ["C10", "R402-specific DAE/LTV authority export", "absent", "R405 matrices belong to a different object", "Direct-M/D conditioning/headroom remains open"],
        ["C11", "Copied source dependency closure", "partial", "agents/networks.py and scenarios/contract.py absent", "Static audit possible; package not self-executing"],
        ["C12", "Formal execution provenance", "absent", "formal_execution.json was never generated", "Reporting/provenance limitation; no demonstrated policy-outcome cause"],
        ["C13", "Learned-checkpoint evaluation on development profiles", "absent", "Only final-checkpoint held-out evaluation is retained", "Cannot distinguish optimization failure on the training distribution from development-to-evaluation shift"],
    ]
    df = pd.DataFrame(rows, columns=["coverage_id", "evidence_object", "status", "delivered_content", "causal_consequence"])
    df.to_csv(output / "evidence_coverage_matrix.csv", index=False)
    return df


def root_cause_ranking(output: Path) -> pd.DataFrame:
    """Inference-to-best-explanation ranking; explicitly not a causal-effect estimate."""

    rows = [
        [1, "Stateful slew/hidden-action learner-interface mismatch", "all three learning arms", "PROVED-MATHEMATICALLY for code fact; PLAUSIBLE-NOT-IDENTIFIED for outcome contribution", "High", "Explains raw-vs-executed action inconsistency, frequent slew activation, replay/target mismatch and hidden projector state", "E2"],
        [2, "Training-objective versus physical-gate mismatch", "all learning arms; exact form differs by arm", "PROVED-MATHEMATICALLY for mismatch; PLAUSIBLE-NOT-IDENTIFIED for effect", "High", "Directly fits poor endpoints despite finite training and explains why reward success could not override physical gate", "E6"],
        [3, "Componentwise effort omission/cancellation plus decoder/clamp geometry", "CD arms; scalar arm has weak common-mean action terms", "POST-HOC-DIAGNOSTIC + PLAUSIBLE-NOT-IDENTIFIED", "Medium-high", "Fits RMS/TV failures, frequent clamps, asymmetric decoded bias; endpoint mediation unisolated", "E4"],
        [4, "Multiplier/budget calibration", "CD arms only", "POST-HOC-DIAGNOSTIC + PLAUSIBLE-NOT-IDENTIFIED", "Medium", "Lambda was often zero/small in retained tail and common guards failed; cannot explain scalar arm or whole training", "E5"],
        [5, "Optimization/critic/replay insufficiency", "all learning arms", "UNAVAILABLE", "Potentially high but unmeasured", "Compatible with late parameter drift and failure, but no Q/loss/coverage evidence", "E0"],
        [6, "Broader partial observation of profile/current M-D/phase", "all learning arms", "PROVED-MATHEMATICALLY for omitted fields; PLAUSIBLE-NOT-IDENTIFIED for effect", "Medium", "Can compound F2 and profile heterogeneity; deterministic reference is counter-evidence against impossibility", "E0 then targeted state intervention only if needed"],
        [7, "Development-to-evaluation distribution shift", "all learning arms", "PLAUSIBLE-NOT-IDENTIFIED", "Medium", "Profiles differ and no learned checkpoint was evaluated on the development profiles, so fit and generalization cannot be separated", "E0 development-versus-heldout checkpoint evaluation"],
        [8, "Centralized-critic credit assignment insufficiency", "all learning arms", "UNAVAILABLE", "Open", "Global joint critic and coordinate-wise actor updates may be adequate or may obscure per-agent credit; no diagnostic decomposition exists", "E0 gradient/Q diagnostics"],
        [9, "Frequency-adapter path asymmetry", "learning arms versus deterministic comparator", "PROVED-MATHEMATICALLY for path difference; PLAUSIBLE-NOT-IDENTIFIED for effect", "Medium-low", "Contract inconsistency is real; learner train/eval remains internally matched", "E3"],
        [10, "No-message actor masking defect", "no-message arm and message contrast", "PROVED-MATHEMATICALLY for defect; PLAUSIBLE-NOT-IDENTIFIED for endpoint effect", "High for ablation validity; low for explaining all arms", "Invalidates message/no-message causal comparison but cannot explain message/scalar failures", "E1"],
        [11, "Limited direct-M/D incremental authority/headroom", "all direct-M/D controllers", "PLAUSIBLE-NOT-IDENTIFIED", "Open", "Strong deterministic reference suggests limited headroom, but also proves nonzero authority; R402-specific maps absent", "E8"],
    ]
    df = pd.DataFrame(
        rows,
        columns=["rank", "candidate", "scope", "epistemic_status", "explanatory_scope", "fit_and_limit", "discriminating_experiment"],
    )
    df.to_csv(output / "root_cause_ranking.csv", index=False)
    return df

def create_summary_json(
    output: Path,
    integrity: pd.DataFrame,
    endpoints: pd.DataFrame,
    profile_guards: pd.DataFrame,
    worst_guards: pd.DataFrame,
    action: pd.DataFrame,
    clamp_trajectory: pd.DataFrame,
    drift: pd.DataFrame,
    slot: pd.DataFrame,
    tail: pd.DataFrame,
) -> None:
    learning_action = action[action["arm_id"].isin(LEARNING_ARMS)]
    summary = {
        "package_integrity": {
            "all_listed_hashes_pass": bool((integrity[integrity["check"].isin(["top_level_SHA256SUMS", "manifest_entry_hashes", "filename_sha256_sidecars"])]["status"] == "PASS").all()),
            "inventory_completeness_warning": bool((integrity["check"] == "manifest_inventory_completeness").any()),
        },
        "registered": {
            "trajectory_count": 240,
            "learning_trajectory_count": 216,
            "deterministic_trajectory_count": 24,
            "learning_profile_block_count": int(profile_guards.shape[0]),
            "all_learning_blocks_common_guard_fail": bool((~profile_guards["common_guard_pass"]).all()),
            "all_learning_blocks_action_guard_fail": bool((~profile_guards["action_stress_guard_pass"]).all()),
        },
        "post_hoc": {
            "learning_trajectories_with_any_physical_lower_clamp": int(clamp_trajectory[(clamp_trajectory["arm_id"].isin(LEARNING_ARMS)) & clamp_trajectory["any_physical_lower_clamp"]].shape[0]),
            "learning_trajectory_total": int(clamp_trajectory[clamp_trajectory["arm_id"].isin(LEARNING_ARMS)].shape[0]),
            "learning_trajectories_with_reference_upper_box_excursion": int(clamp_trajectory[(clamp_trajectory["arm_id"].isin(LEARNING_ARMS)) & clamp_trajectory["any_reference_upper_box_excursion"]].shape[0]),
            "maximum_observed_m": float(action["m_max"].max()),
            "maximum_observed_d": float(action["d_max"].max()),
            "median_relative_actor_change_1200_to_1440": float(drift[(drift["section"] == "actors") & (drift["from_episode"] == 1200)]["relative_parameter_change"].median()),
            "median_relative_critic_change_1200_to_1440": float(drift[(drift["section"] == "critic") & (drift["from_episode"] == 1200)]["relative_parameter_change"].median()),
            "no_message_neighbour_to_local_weight_norm_ratio_mean": float(slot[slot["arm_id"] == "cd_matd3_no_message"]["neighbour_to_local_norm_ratio"].mean()),
            "message_neighbour_to_local_weight_norm_ratio_mean": float(slot[slot["arm_id"] == "cd_matd3_message"]["neighbour_to_local_norm_ratio"].mean()),
        },
        "causal_evidence_availability": {
            "full_training_logs": False,
            "message_interventions": False,
            "successor_S0_S5": False,
            "r402_specific_dae_authority": False,
        },
    }
    write_json(output / "audit_summary.json", summary)


def run(args: argparse.Namespace) -> None:
    root = args.package_root.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    contract = read_contract(root)
    records = discover_records(root)
    if len(records) != 240:
        raise ValueError(f"expected 240 records, found {len(records)}")

    integrity = verify_integrity(root, output, args.source_zip.resolve() if args.source_zip else None)
    profile, endpoint, profile_guards, worst_guards = registered_recomputation(root, records, contract, output)
    endpoint_medians, descriptive_contrasts = descriptive_endpoint_comparisons(endpoint, output)
    decoder_asymmetry_theory(output)
    action, action_profile, clamp_trajectory = action_diagnostics(records, contract, output)
    frequency_cost = reconstructed_frequency_costs(records, contract, output)
    lambda_df, tail, drift, slot = checkpoint_diagnostics(root, contract, output)
    implementation = static_source_findings(root, output)
    source_dependencies = source_dependency_gaps(root, output)
    documentation = package_documentation_findings(root, output)
    coverage = evidence_coverage_matrix(output)
    hypotheses = hypothesis_verdicts(output)
    experiments = next_experiment_matrix(output)
    ranking = root_cause_ranking(output)
    create_summary_json(output, integrity, endpoint, profile_guards, worst_guards, action, clamp_trajectory, drift, slot, tail)

    data_dictionary = {
        "registered_profile_metrics.csv": "Independent six-trajectory registered summary per arm/seed/profile.",
        "registered_endpoint_aggregates.csv": "Four-profile registered endpoint aggregates.",
        "registered_seed_medians.csv": "Seed-median endpoint values and ratios to deterministic reference.",
        "descriptive_message_no_message_contrasts.csv": "Per-seed descriptive contrast; causal interpretation explicitly disabled because of F1.",
        "registered_guard_ratios_by_profile.csv": "Reference-relative guards at the registered unit of analysis.",
        "registered_worst_guard_ratios.csv": "Worst profile ratios per learning run.",
        "registered_recomputation_diff.csv": "Difference versus frozen endpoint_table.json.",
        "decoder_asymmetry_theory.json": "Analytic positive-bias identity for the asymmetric piecewise decoder.",
        "action_geometry_by_run.csv": "Post-hoc normalized/decoded/physical action diagnostics per run.",
        "action_geometry_by_profile.csv": "Same diagnostics per profile.",
        "physical_clamp_by_trajectory.csv": "Per-trajectory physical lower-clamp and reference-upper-box events.",
        "frequency_cost_reconstruction_by_trajectory.csv": "Exact common frequency cost and frequency-only differential cost; P_es term absent.",
        "frequency_cost_reconstruction_by_run.csv": "Run-level summary of the above.",
        "checkpoint_lagrange_history.csv": "Numerically ordered lambda values at six snapshots.",
        "retained_tail_lambda_usage.csv": "Final-20 CD costs and post-update lambda, plus 19 exactly known episode-use lambdas.",
        "retained_tail_lambda_summary.csv": "Run-level tail lambda usage fractions.",
        "checkpoint_parameter_drift.csv": "Coarse consecutive snapshot parameter displacement.",
        "actor_input_slot_weight_norms.csv": "Final actor first-layer input-column norms.",
        "final_checkpoint_identity.csv": "Tensor equality between final.pt and episode1440.pt.",
        "target_network_gaps.csv": "Final online-target parameter gaps.",
        "implementation_findings.csv": "Source-code-mechanical findings and causal scope.",
        "source_dependency_resolution.csv": "Project-local import closure of the copied source subset.",
        "evidence_coverage_matrix.csv": "Requested causal evidence versus what the package actually delivers.",
        "package_documentation_findings.csv": "Package/reporting contradictions found during audit.",
        "hypothesis_verdicts.csv": "Epistemic classification of candidate mechanisms.",
        "required_next_experiments.csv": "Minimal updated discriminating experiment matrix.",
        "root_cause_ranking.csv": "Inference-to-best-explanation ranking; not a causal-effect estimate.",
        "package_integrity.csv": "Hash/CRC/inventory checks.",
        "package_inventory_gap.json": "Exact files omitted from package manifest.",
        "audit_summary.json": "Compact machine-readable headline results.",
    }
    write_json(output / "DATA_DICTIONARY.json", data_dictionary)

    print(f"R402 audit complete: {output}")
    print(f"records={len(records)}, profile_blocks={len(profile)}, endpoint_rows={len(endpoint)}")
    print(f"generated_files={len(list(output.iterdir()))}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-zip", type=Path)
    return parser.parse_args(argv)


if __name__ == "__main__":
    run(parse_args())
