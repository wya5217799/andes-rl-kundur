"""R485 reward probe: are M/D magnitude terms numerically dominated?

For the outcome-blind first frozen policy (``an_cn_r0``, seed 501), accumulate
the positive cost contributed by frequency terms and by M/D action terms.
Compute both the registered fleet-mean M/D cost and a per-device mean-square
counterfactual.  Numerical dominance is supported if both M/D/frequency ratios
are <= 0.10 in every profile.  It is refuted if registered ratios are >= 0.50
everywhere; other outcomes are inconclusive.

This is a post-hoc decomposition on sealed rows, not a reward redesign or a
claim that reweighting would preserve endpoints.

Usage: ``python probe_reward_scale_dominance.py [--self-check]``
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
SUPPORT_RATIO_MAX = 0.10
REFUTE_RATIO_MIN = 0.50
COMPONENT_TOLERANCE = 1.0e-12
EXPECTED_CONFIG_SHA256 = "58ce96255b7afbfb9fc8831d6311454b3c5b3ae9c4159bbc4351ced1db58a835"


def find_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "CLAUDE.md").is_file() and (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("repository root not found")


ROOT = find_root()
OUT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "memory/rounds/R485/config.json"
TRACE_ROOT = (
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
        raise ValueError(f"SHA256 mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8")), {
        "path": path.relative_to(ROOT).as_posix(),
        "sidecar": sidecar.relative_to(ROOT).as_posix(),
        "sha256": actual,
        "verified": True,
    }


def synthetic_self_check() -> dict[str, Any]:
    values = np.asarray([1.0, -1.0, 1.0, -1.0])
    fleet = float(np.mean(values)) ** 2
    per_device = float(np.mean(np.square(values)))
    variance = float(np.mean(np.square(values - np.mean(values))))
    if abs(per_device - fleet - variance) > COMPONENT_TOLERANCE:
        raise AssertionError("mean-square decomposition failed")
    own = np.asarray([0.1, -0.1, 0.2, -0.2])
    frequency_absolute = -np.square(own)
    if np.any(frequency_absolute > 0.0):
        raise AssertionError("frequency cost sign self-check failed")
    return {"fleet_cost": fleet, "per_device_cost": per_device, "variance": variance}


def summarize_profile(path: Path, coefficients: dict[str, float]) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, input_row = verified_json(path)
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != 6:
        raise ValueError(f"expected 6 records: {path}")
    frequency_costs: list[float] = []
    registered_md_costs: list[float] = []
    per_device_md_costs: list[float] = []
    max_component_error = {
        "frequency_differential": 0.0,
        "frequency_absolute": 0.0,
        "fleet_mean_m": 0.0,
        "fleet_mean_d": 0.0,
        "mean_square_decomposition": 0.0,
    }
    step_count = 0
    for record in records:
        if record.get("arm_id") != "an_cn_r0":
            raise ValueError("unexpected arm identity")
        steps = record.get("steps")
        if not isinstance(steps, list) or len(steps) != 150:
            raise ValueError(f"expected 150 steps: {path}")
        for step in steps:
            parts = step["reward_components"]
            canonical = np.asarray(step["canonical_observation"], dtype=float)
            own = canonical[:, 1] * 3.0 / (2.0 * math.pi)
            expected_frequency_differential = np.zeros(4, dtype=float)
            expected_frequency_absolute = -np.square(own)
            saved_frequency_differential = np.asarray(parts["frequency_differential"], dtype=float)
            saved_frequency_absolute = np.asarray(parts["frequency_absolute"], dtype=float)
            max_component_error["frequency_differential"] = max(
                max_component_error["frequency_differential"],
                float(np.max(np.abs(saved_frequency_differential - expected_frequency_differential))),
            )
            max_component_error["frequency_absolute"] = max(
                max_component_error["frequency_absolute"],
                float(np.max(np.abs(saved_frequency_absolute - expected_frequency_absolute))),
            )

            delta_m = np.asarray(step["delta_M"], dtype=float)
            delta_d = np.asarray(step["delta_D"], dtype=float)
            registered_m = (float(np.mean(delta_m)) / ACTION_HALF_RANGE) ** 2
            registered_d = (float(np.mean(delta_d)) / ACTION_HALF_RANGE) ** 2
            per_device_m = float(np.mean(np.square(delta_m / ACTION_HALF_RANGE)))
            per_device_d = float(np.mean(np.square(delta_d / ACTION_HALF_RANGE)))
            variance_m = float(np.mean(np.square((delta_m - np.mean(delta_m)) / ACTION_HALF_RANGE)))
            variance_d = float(np.mean(np.square((delta_d - np.mean(delta_d)) / ACTION_HALF_RANGE)))
            max_component_error["mean_square_decomposition"] = max(
                max_component_error["mean_square_decomposition"],
                abs(per_device_m - registered_m - variance_m),
                abs(per_device_d - registered_d - variance_d),
            )
            max_component_error["fleet_mean_m"] = max(
                max_component_error["fleet_mean_m"],
                abs(-registered_m - float(parts["fleet_mean_m"])),
            )
            max_component_error["fleet_mean_d"] = max(
                max_component_error["fleet_mean_d"],
                abs(-registered_d - float(parts["fleet_mean_d"])),
            )

            frequency_costs.append(
                -float(
                    np.mean(
                        coefficients["phi_f"] * saved_frequency_differential
                        + coefficients["phi_abs"] * saved_frequency_absolute
                    )
                )
            )
            registered_md_costs.append(
                coefficients["phi_h"] * registered_m + coefficients["phi_d"] * registered_d
            )
            per_device_md_costs.append(
                coefficients["phi_h"] * per_device_m + coefficients["phi_d"] * per_device_d
            )
            step_count += 1

    if max(max_component_error.values()) > COMPONENT_TOLERANCE:
        raise AssertionError(f"reward component reconstruction failed: {max_component_error}")
    frequency = math.fsum(frequency_costs)
    registered = math.fsum(registered_md_costs)
    per_device = math.fsum(per_device_md_costs)
    if frequency <= 0.0:
        raise ValueError("frequency cost denominator is non-positive")
    return {
        "profile_id": path.stem,
        "step_count": step_count,
        "cost_sums": {
            "frequency": frequency,
            "registered_fleet_mean_md": registered,
            "counterfactual_per_device_md": per_device,
        },
        "md_to_frequency_ratio": {
            "registered": registered / frequency,
            "counterfactual_per_device": per_device / frequency,
        },
        "md_share_of_frequency_plus_md": {
            "registered": registered / (frequency + registered),
            "counterfactual_per_device": per_device / (frequency + per_device),
        },
        "component_reconstruction_max_abs_error": max_component_error,
    }, input_row


def decide(rows: list[dict[str, Any]]) -> dict[str, Any]:
    supported = all(
        row["md_to_frequency_ratio"]["registered"] <= SUPPORT_RATIO_MAX
        and row["md_to_frequency_ratio"]["counterfactual_per_device"] <= SUPPORT_RATIO_MAX
        for row in rows
    )
    refuted = all(
        row["md_to_frequency_ratio"]["registered"] >= REFUTE_RATIO_MIN for row in rows
    )
    verdict = (
        "MD_MAGNITUDE_PENALTY_NUMERICALLY_DOMINATED_SUPPORTED"
        if supported
        else "MD_MAGNITUDE_PENALTY_NUMERICALLY_DOMINATED_REFUTED"
        if refuted
        else "INCONCLUSIVE"
    )
    return {"verdict": verdict, "support_criteria_met": supported, "refute_criteria_met": refuted}


def write_outputs(result: dict[str, Any]) -> None:
    result_path = OUT_DIR / "result.json"
    report_path = OUT_DIR / "REPORT.md"
    sums_path = OUT_DIR / "SHA256SUMS"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# R485 root-cause probe 07: reward-scale dominance",
        "",
        "> Scratch post-hoc reward decomposition; not registered R485 evidence.",
        "",
        f"**Decision:** `{result['decision']['verdict']}`",
        "",
        "| Profile | registered M/D ÷ frequency | per-device M/D ÷ frequency |",
        "|---|---:|---:|",
    ]
    for row in result["profiles"]:
        ratio = row["md_to_frequency_ratio"]
        lines.append(
            f"| {row['profile_id']} | {ratio['registered']:.4f} | "
            f"{ratio['counterfactual_per_device']:.4f} |"
        )
    lines.extend(
        [
            "",
            "This compares numerical contributions on one frozen policy. It does not",
            "establish how retraining with different coefficients would behave.",
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
    coefficients = {key: float(value) for key, value in reward["coefficients"].items()}
    if float(reward["fleet_mean_m_d_divisor"]) != ACTION_HALF_RANGE:
        raise ValueError("reward divisor mismatch")
    profiles: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []
    for profile_id in PROFILE_IDS:
        row, input_row = summarize_profile(TRACE_ROOT / f"{profile_id}.json", coefficients)
        profiles.append(row)
        inputs.append(input_row)
    result = {
        "schema_version": "r485_root_cause_probe_07_v1",
        "scope": "scratch_posthoc_sealed_data_diagnostic",
        "formal_artifacts_modified": False,
        "question": "Are M/D magnitude penalties numerically dominated by frequency terms?",
        "thresholds": {
            "support_md_to_frequency_ratio_max": SUPPORT_RATIO_MAX,
            "refute_registered_ratio_min": REFUTE_RATIO_MIN,
            "component_tolerance": COMPONENT_TOLERANCE,
        },
        "lineage": {"config_sha256": EXPECTED_CONFIG_SHA256, "trace_inputs": inputs},
        "self_check": self_check,
        "coefficients": coefficients,
        "profiles": profiles,
    }
    result["decision"] = decide(profiles)
    write_outputs(result)
    print(json.dumps({"decision": result["decision"], "profiles": profiles}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
