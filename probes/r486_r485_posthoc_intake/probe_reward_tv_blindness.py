"""Throwaway R485 probe: is the M/D reward term blind to temporal order/TV?

Question
--------
For the outcome-blind first frozen policy (``an_cn_r0``, seed 501, all four
same-bank profiles), can the same multiset of executed action rows have very
different normalized TV while receiving exactly the same registered M/D
action cost?

Decision rule fixed before trace loading
---------------------------------------
Within each scenario, retain all 150 complete 4x2 rows and only permute their
order.  Deterministic nearest-neighbour and farthest-neighbour traversals from
zero provide low/high-TV constructions.  Objective blindness is supported if
every profile has high/low combined TV >= 2.0 while the registered M/D action
cost differs by at most 1e-12.  It is refuted if permutation changes the cost,
or if all profiles have TV range <= 1.10.  Other outcomes are inconclusive.

This isolates only the frozen M/D action regularizer.  It is not a closed-loop
ANDES replay and makes no claim that frequency-dependent reward is invariant.

Controls
--------
A synthetic multiset must preserve action cost under reordering while changing
TV.  Every saved ``fleet_mean_m``/``fleet_mean_d`` component is independently
recomputed, and all traces are SHA256 verified before use.

Usage
-----
``python probe_reward_tv_blindness.py --self-check``
``python probe_reward_tv_blindness.py``
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


PROFILE_IDS = ("canary_eval_a", "canary_eval_b", "canary_eval_c", "canary_eval_d")
ACTION_HALF_RANGE = 600.0
PHI_M = 0.0056
PHI_D = 0.0056
SUPPORT_TV_RATIO = 2.0
REFUTE_TV_RATIO = 1.10
REWARD_TOLERANCE = 1.0e-12
EXPECTED_CONFIG_SHA256 = "58ce96255b7afbfb9fc8831d6311454b3c5b3ae9c4159bbc4351ced1db58a835"


def find_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "CLAUDE.md").is_file() and (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("repository root not found")


ROOT = find_root()
OUT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "memory/rounds/R485/config.json"
EVAL_ROOT = (
    ROOT
    / "results/research_loop/r485_60hz_source_factorial"
    / "r485-formal-20260829-a/eval/same/an_cn_r0/seed501"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verified_json(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    sidecar = Path(f"{path}.sha256")
    parts = sidecar.read_text(encoding="ascii").strip().split()
    if len(parts) < 2 or parts[1] != path.name:
        raise ValueError(f"invalid SHA256 sidecar: {sidecar}")
    actual = sha256_file(path)
    if actual != parts[0].lower():
        raise ValueError(f"sealed trace SHA256 mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8")), {
        "path": path.relative_to(ROOT).as_posix(),
        "sidecar": sidecar.relative_to(ROOT).as_posix(),
        "sha256": actual,
        "verified": True,
    }


def action_cost(delta_m: np.ndarray, delta_d: np.ndarray, order: list[int]) -> float:
    terms = []
    for index in order:
        mean_m = math.fsum(float(value) for value in delta_m[index]) / 4.0
        mean_d = math.fsum(float(value) for value in delta_d[index]) / 4.0
        terms.append(
            PHI_M * (mean_m / ACTION_HALF_RANGE) ** 2
            + PHI_D * (mean_d / ACTION_HALF_RANGE) ** 2
        )
    return math.fsum(terms)


def tv(actions: np.ndarray, order: list[int]) -> np.ndarray:
    previous = np.zeros((4, 2), dtype=float)
    total = np.zeros(2, dtype=float)
    for index in order:
        current = np.asarray(actions[index], dtype=float)
        total += np.abs(current - previous).sum(axis=0)
        previous = current
    return total


def greedy_order(actions: np.ndarray, *, farthest: bool) -> list[int]:
    rows = np.asarray(actions, dtype=float)
    remaining = list(range(len(rows)))
    current = np.zeros((4, 2), dtype=float)
    order: list[int] = []
    while remaining:
        distances = np.asarray(
            [float(np.abs(rows[index] - current).sum()) for index in remaining]
        )
        position = int(np.argmax(distances) if farthest else np.argmin(distances))
        selected = remaining.pop(position)
        order.append(selected)
        current = rows[selected]
    return order


def synthetic_self_check() -> dict[str, Any]:
    scalar = np.asarray([0.0, 1.0, -1.0, 0.5], dtype=float)
    actions = np.zeros((4, 4, 2), dtype=float)
    actions[:, :, 0] = scalar[:, None]
    delta_m = actions[:, :, 0] * 100.0
    delta_d = np.zeros((4, 4), dtype=float)
    low_order = greedy_order(actions, farthest=False)
    high_order = greedy_order(actions, farthest=True)
    low_cost = action_cost(delta_m, delta_d, low_order)
    high_cost = action_cost(delta_m, delta_d, high_order)
    low_tv = float(tv(actions, low_order).sum())
    high_tv = float(tv(actions, high_order).sum())
    if abs(low_cost - high_cost) > REWARD_TOLERANCE:
        raise AssertionError("synthetic permutation changed action cost")
    if not high_tv > low_tv:
        raise AssertionError("synthetic TV ordering control failed")
    return {
        "low_order": low_order,
        "high_order": high_order,
        "low_tv": low_tv,
        "high_tv": high_tv,
        "action_cost_abs_difference": abs(low_cost - high_cost),
    }


def summarize_profile(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, input_row = verified_json(path)
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != 6:
        raise ValueError(f"expected 6 scenarios: {path}")
    totals = {
        "original": np.zeros(2),
        "low": np.zeros(2),
        "high": np.zeros(2),
    }
    costs = {"original": 0.0, "low": 0.0, "high": 0.0}
    reward_component_max_abs_error = {"M": 0.0, "D": 0.0}

    for record in records:
        steps = record.get("steps")
        if not isinstance(steps, list) or len(steps) != 150:
            raise ValueError(f"expected 150 steps: {path}")
        actions = np.asarray([step["projected_action_norm"] for step in steps], dtype=float)
        delta_m = np.asarray([step["delta_M"] for step in steps], dtype=float)
        delta_d = np.asarray([step["delta_D"] for step in steps], dtype=float)
        original_order = list(range(len(steps)))
        low_order = greedy_order(actions, farthest=False)
        high_order = greedy_order(actions, farthest=True)
        for name, order in (
            ("original", original_order),
            ("low", low_order),
            ("high", high_order),
        ):
            totals[name] += tv(actions, order)
            costs[name] += action_cost(delta_m, delta_d, order)

        for index, step in enumerate(steps):
            expected_m = -(float(np.mean(delta_m[index])) / ACTION_HALF_RANGE) ** 2
            expected_d = -(float(np.mean(delta_d[index])) / ACTION_HALF_RANGE) ** 2
            reward_component_max_abs_error["M"] = max(
                reward_component_max_abs_error["M"],
                abs(expected_m - float(step["reward_components"]["fleet_mean_m"])),
            )
            reward_component_max_abs_error["D"] = max(
                reward_component_max_abs_error["D"],
                abs(expected_d - float(step["reward_components"]["fleet_mean_d"])),
            )

    max_reward_difference = max(
        abs(costs["original"] - costs["low"]),
        abs(costs["original"] - costs["high"]),
        abs(costs["low"] - costs["high"]),
    )
    if max_reward_difference > REWARD_TOLERANCE:
        raise AssertionError(f"permutation changed action reward: {max_reward_difference}")
    if max(reward_component_max_abs_error.values()) > REWARD_TOLERANCE:
        raise AssertionError("saved reward component recomputation failed")
    combined = {name: float(value.sum()) for name, value in totals.items()}
    return {
        "profile_id": path.stem,
        "tv": {
            name: {"M": float(value[0]), "D": float(value[1]), "combined": combined[name]}
            for name, value in totals.items()
        },
        "high_to_low_combined_tv_ratio": combined["high"] / combined["low"],
        "original_to_low_combined_tv_ratio": combined["original"] / combined["low"],
        "registered_action_cost": costs,
        "max_action_cost_abs_difference": max_reward_difference,
        "saved_reward_component_max_abs_error": reward_component_max_abs_error,
    }, input_row


def decide(rows: list[dict[str, Any]]) -> dict[str, Any]:
    supported = all(
        row["high_to_low_combined_tv_ratio"] >= SUPPORT_TV_RATIO
        and row["max_action_cost_abs_difference"] <= REWARD_TOLERANCE
        for row in rows
    )
    reward_changed = any(
        row["max_action_cost_abs_difference"] > REWARD_TOLERANCE for row in rows
    )
    tv_range_small_all = all(
        row["high_to_low_combined_tv_ratio"] <= REFUTE_TV_RATIO for row in rows
    )
    verdict = (
        "TEMPORAL_TV_OBJECTIVE_BLINDNESS_SUPPORTED"
        if supported
        else "TEMPORAL_TV_OBJECTIVE_BLINDNESS_REFUTED"
        if reward_changed or tv_range_small_all
        else "INCONCLUSIVE"
    )
    return {
        "verdict": verdict,
        "support_criteria_met": supported,
        "reward_changed": reward_changed,
        "tv_range_small_all": tv_range_small_all,
    }


def write_outputs(result: dict[str, Any]) -> None:
    result_path = OUT_DIR / "result.json"
    report_path = OUT_DIR / "REPORT.md"
    sums_path = OUT_DIR / "SHA256SUMS"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# R485 root-cause probe 04: reward temporal-TV blindness",
        "",
        "> Scratch post-hoc sealed-data diagnostic; not registered R485 evidence.",
        "",
        f"**Decision:** `{result['decision']['verdict']}`",
        "",
        "| Profile | original/low TV | high/low TV | action-cost difference |",
        "|---|---:|---:|---:|",
    ]
    for row in result["profiles"]:
        lines.append(
            f"| {row['profile_id']} | {row['original_to_low_combined_tv_ratio']:.2f}x | "
            f"{row['high_to_low_combined_tv_ratio']:.2f}x | "
            f"{row['max_action_cost_abs_difference']:.3e} |"
        )
    lines.extend(
        [
            "",
            "The permutation preserves the action-row multiset and isolates only the",
            "M/D action term. Frequency reward and plant response are not replayed.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    hashed = [Path(__file__).resolve(), result_path, report_path]
    sums_path.write_text(
        "".join(f"{sha256_file(path)}  {path.name}\n" for path in hashed),
        encoding="ascii",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    self_check = synthetic_self_check()
    if args.self_check:
        print(json.dumps({"self_check": "PASS", "details": self_check}, indent=2))
        return 0

    if sha256_file(CONFIG_PATH) != EXPECTED_CONFIG_SHA256:
        raise ValueError("R485 config SHA256 mismatch")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    reward = config["parameter_card"]["reward"]
    coefficients = reward["coefficients"]
    if (
        float(reward["fleet_mean_m_d_divisor"]) != ACTION_HALF_RANGE
        or float(coefficients["phi_h"]) != PHI_M
        or float(coefficients["phi_d"]) != PHI_D
    ):
        raise ValueError("frozen reward parameters do not match probe")

    profiles: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []
    for profile_id in PROFILE_IDS:
        row, input_row = summarize_profile(EVAL_ROOT / f"{profile_id}.json")
        profiles.append(row)
        inputs.append(input_row)
    result = {
        "schema_version": "r485_root_cause_probe_04_v1",
        "scope": "scratch_posthoc_sealed_data_diagnostic",
        "formal_artifacts_modified": False,
        "question": "Is the frozen M/D action reward structurally blind to temporal order and TV?",
        "thresholds": {
            "support_high_to_low_tv_ratio_min": SUPPORT_TV_RATIO,
            "refute_tv_ratio_max": REFUTE_TV_RATIO,
            "reward_tolerance": REWARD_TOLERANCE,
        },
        "lineage": {"config_sha256": EXPECTED_CONFIG_SHA256, "trace_inputs": inputs},
        "self_check": self_check,
        "profiles": profiles,
    }
    result["decision"] = decide(profiles)
    write_outputs(result)
    print(json.dumps({"decision": result["decision"], "profiles": profiles}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
