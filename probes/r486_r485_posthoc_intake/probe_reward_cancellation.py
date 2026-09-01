"""Throwaway R485 sealed-trace probe for one falsifiable mechanism question.

Question
--------
On the outcome-blind first frozen policy (arm ``an_cn_r0``, seed 501, all
four same-bank profiles), does the registered fleet-mean M/D reward term hide
most per-device command magnitude through cross-device cancellation?

Prediction and decision rule (fixed before reading the selected traces)
-----------------------------------------------------------------------
For each channel, compare the registered cost
``mean_t((mean_i(delta_i) / 600)**2)`` with the counterfactual per-device cost
``mean_ti((delta_i / 600)**2)``.  Visibility <= 0.25 in both M and D supports
the mechanism (at least four-fold hidden magnitude).  Visibility >= 0.75 in
either channel refutes it for that channel.  Values between the thresholds are
inconclusive.  These are post-hoc diagnostic thresholds, not R485 evidence.

Negative control and failure modes
----------------------------------
Replacing every four-device vector by its fleet mean must make the two costs
equal within 1e-12.  The script also independently recomputes every saved
``fleet_mean_m``/``fleet_mean_d`` reward component, checks the variance
decomposition, validates 6 records x 150 steps per trace, and verifies every
JSON against its sealed SHA256 sidecar.  Any mismatch aborts without a result.

Usage
-----
``python probe_reward_cancellation.py --self-check``
``python probe_reward_cancellation.py``

The second command writes deterministic scratch outputs beside this file.  It
does not modify the R485 plan, seal, traces, verdict, claims, or manuscript.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable


PROFILE_IDS = ("canary_eval_a", "canary_eval_b", "canary_eval_c", "canary_eval_d")
ACTION_HALF_RANGE = 600.0
SUPPORT_MAX_VISIBILITY = 0.25
REFUTE_MIN_VISIBILITY = 0.75
TOLERANCE = 1.0e-12
EXPECTED_CONFIG_SHA256 = "58ce96255b7afbfb9fc8831d6311454b3c5b3ae9c4159bbc4351ced1db58a835"
EXPECTED_FORMAL_SEAL_SHA256 = "3d5865619b21d4276a0c07616c136c690beefc4f779d65d48f7a0bf3e04ade7f"


def find_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "CLAUDE.md").is_file() and (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("repository root not found")


ROOT = find_root()
OUT_DIR = Path(__file__).resolve().parent
EVAL_ROOT = (
    ROOT
    / "results/research_loop/r485_60hz_source_factorial"
    / "r485-formal-20260829-a/eval/same"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mean(values: Iterable[float]) -> float:
    rows = tuple(float(value) for value in values)
    if not rows:
        raise ValueError("mean requires at least one value")
    return math.fsum(rows) / len(rows)


def vector_costs(values: Iterable[float]) -> tuple[float, float, float]:
    vector = tuple(float(value) / ACTION_HALF_RANGE for value in values)
    if len(vector) != 4 or not all(math.isfinite(value) for value in vector):
        raise ValueError("expected four finite per-device command deltas")
    fleet = mean(vector)
    registered = fleet * fleet
    per_device = mean(value * value for value in vector)
    variance = mean((value - fleet) ** 2 for value in vector)
    return registered, per_device, variance


def synthetic_self_check() -> dict[str, float]:
    common = (120.0, 120.0, 120.0, 120.0)
    registered, per_device, variance = vector_costs(common)
    if abs(registered - per_device) > TOLERANCE or variance > TOLERANCE:
        raise AssertionError("common-mode negative control failed")

    differential = (120.0, -120.0, 120.0, -120.0)
    d_registered, d_per_device, d_variance = vector_costs(differential)
    if abs(d_registered) > TOLERANCE or d_per_device <= 0.0:
        raise AssertionError("differential cancellation self-check failed")
    if abs(d_per_device - d_registered - d_variance) > TOLERANCE:
        raise AssertionError("variance decomposition self-check failed")
    return {
        "common_mode_visibility": registered / per_device,
        "differential_registered_cost": d_registered,
        "differential_per_device_cost": d_per_device,
    }


def verified_json(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    sidecar = Path(f"{path}.sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"sealed input or SHA256 sidecar missing: {path}")
    sidecar_parts = sidecar.read_text(encoding="ascii").strip().split()
    if len(sidecar_parts) < 2 or sidecar_parts[1] != path.name:
        raise ValueError(f"invalid SHA256 sidecar schema: {sidecar}")
    expected = sidecar_parts[0].lower()
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"sealed trace SHA256 mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8")), {
        "path": path.relative_to(ROOT).as_posix(),
        "sidecar": sidecar.relative_to(ROOT).as_posix(),
        "sha256": actual,
        "verified": True,
    }


def trace_paths(kind: str) -> list[Path]:
    if kind == "candidate":
        base = EVAL_ROOT / "an_cn_r0/seed501"
    elif kind == "direct_md_context":
        base = EVAL_ROOT / "local_neighbour_md_km2_kd2/deterministic"
    else:
        raise ValueError(f"unknown trace kind: {kind}")
    return [base / f"{profile_id}.json" for profile_id in PROFILE_IDS]


def summarize(kind: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sums = {
        "M": {"registered": 0.0, "per_device": 0.0, "variance": 0.0},
        "D": {"registered": 0.0, "per_device": 0.0, "variance": 0.0},
    }
    component_max_abs_error = {"M": 0.0, "D": 0.0}
    common_mode_max_abs_error = {"M": 0.0, "D": 0.0}
    decomposition_max_abs_error = {"M": 0.0, "D": 0.0}
    input_rows: list[dict[str, Any]] = []
    step_count = 0

    for path in trace_paths(kind):
        payload, input_row = verified_json(path)
        input_rows.append(input_row)
        records = payload.get("records")
        if not isinstance(records, list) or len(records) != 6:
            raise ValueError(f"expected 6 scenario records: {path}")
        for record in records:
            steps = record.get("steps")
            if not isinstance(steps, list) or len(steps) != 150:
                raise ValueError(f"expected 150 steps per scenario: {path}")
            for step in steps:
                for channel, key, saved_key in (
                    ("M", "delta_M", "fleet_mean_m"),
                    ("D", "delta_D", "fleet_mean_d"),
                ):
                    registered, per_device, variance = vector_costs(step[key])
                    saved = -float(step["reward_components"][saved_key])
                    component_max_abs_error[channel] = max(
                        component_max_abs_error[channel], abs(saved - registered)
                    )
                    common_vector = [mean(step[key])] * 4
                    common_registered, common_per_device, _ = vector_costs(common_vector)
                    common_mode_max_abs_error[channel] = max(
                        common_mode_max_abs_error[channel],
                        abs(common_registered - common_per_device),
                    )
                    decomposition_max_abs_error[channel] = max(
                        decomposition_max_abs_error[channel],
                        abs(per_device - registered - variance),
                    )
                    sums[channel]["registered"] += registered
                    sums[channel]["per_device"] += per_device
                    sums[channel]["variance"] += variance
                step_count += 1

    if step_count != 4 * 6 * 150:
        raise AssertionError(f"unexpected selected step count: {step_count}")
    if max(component_max_abs_error.values()) > TOLERANCE:
        raise AssertionError("saved reward component independent recomputation failed")
    if max(common_mode_max_abs_error.values()) > TOLERANCE:
        raise AssertionError("trace-derived common-mode negative control failed")
    if max(decomposition_max_abs_error.values()) > TOLERANCE:
        raise AssertionError("trace variance decomposition failed")

    channels: dict[str, Any] = {}
    for channel in ("M", "D"):
        registered = sums[channel]["registered"] / step_count
        per_device = sums[channel]["per_device"] / step_count
        variance = sums[channel]["variance"] / step_count
        visibility = registered / per_device if per_device > 0.0 else math.nan
        channels[channel] = {
            "registered_fleet_mean_cost": registered,
            "counterfactual_per_device_cost": per_device,
            "hidden_variance_cost": variance,
            "visibility_fraction": visibility,
            "underweight_factor": per_device / registered if registered > 0.0 else math.inf,
        }

    return {
        "selection": kind,
        "trace_file_count": len(input_rows),
        "scenario_record_count": len(input_rows) * 6,
        "step_count": step_count,
        "channels": channels,
        "checks": {
            "saved_reward_component_max_abs_error": component_max_abs_error,
            "common_mode_negative_control_max_abs_error": common_mode_max_abs_error,
            "variance_decomposition_max_abs_error": decomposition_max_abs_error,
        },
    }, input_rows


def classify(candidate: dict[str, Any]) -> dict[str, Any]:
    visibility = {
        channel: float(candidate["channels"][channel]["visibility_fraction"])
        for channel in ("M", "D")
    }
    per_channel = {
        channel: (
            "SUPPORTS_CANCELLATION"
            if value <= SUPPORT_MAX_VISIBILITY
            else "REFUTES_MATERIAL_CANCELLATION"
            if value >= REFUTE_MIN_VISIBILITY
            else "INCONCLUSIVE"
        )
        for channel, value in visibility.items()
    }
    if all(value == "SUPPORTS_CANCELLATION" for value in per_channel.values()):
        joint = "SUPPORTS_FLEET_MEAN_CANCELLATION_MECHANISM"
    elif any(value == "REFUTES_MATERIAL_CANCELLATION" for value in per_channel.values()):
        joint = "REFUTES_JOINT_M_AND_D_CANCELLATION_MECHANISM"
    else:
        joint = "INCONCLUSIVE"
    return {"per_channel": per_channel, "joint": joint}


def write_outputs(result: dict[str, Any]) -> None:
    result_path = OUT_DIR / "result.json"
    report_path = OUT_DIR / "REPORT.md"
    sums_path = OUT_DIR / "SHA256SUMS"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    candidate = result["candidate"]
    report_lines = [
        "# R485 root-cause probe 01: fleet-mean cancellation",
        "",
        "> Scratch post-hoc sealed-data diagnostic; not registered R485 evidence.",
        "",
        f"**Decision:** `{result['decision']['joint']}`",
        "",
        "| Channel | Visibility | Underweight factor | Classification |",
        "|---|---:|---:|---|",
    ]
    for channel in ("M", "D"):
        row = candidate["channels"][channel]
        report_lines.append(
            f"| {channel} | {row['visibility_fraction']:.6f} | "
            f"{row['underweight_factor']:.3f}x | "
            f"{result['decision']['per_channel'][channel]} |"
        )
    report_lines.extend(
        [
            "",
            "The result says only how much per-device command magnitude the registered",
            "fleet-mean M/D terms see on the fixed minimal sample. It does not establish",
            "training causality, actuator wear, energy, thermal stress, or hardware harm.",
            "",
        ]
    )
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
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

    config_sha = sha256_file(ROOT / "memory/rounds/R485/config.json")
    seal_sha = sha256_file(ROOT / "memory/rounds/R485/formal_seal.json")
    if config_sha != EXPECTED_CONFIG_SHA256 or seal_sha != EXPECTED_FORMAL_SEAL_SHA256:
        raise ValueError("R485 config/formal-seal lineage hash mismatch")

    candidate, candidate_inputs = summarize("candidate")
    direct_md, direct_inputs = summarize("direct_md_context")
    result = {
        "schema_version": "r485_root_cause_probe_01_v1",
        "scope": "scratch_posthoc_sealed_data_diagnostic",
        "formal_artifacts_modified": False,
        "question": (
            "Does registered fleet-mean M/D aggregation materially hide "
            "per-device command magnitude on the first frozen policy?"
        ),
        "selection_rule": (
            "lexicographically first registered arm an_cn_r0, lowest seed 501, "
            "all four same-bank profiles; direct-M/D included only as context"
        ),
        "thresholds": {
            "support_visibility_at_most": SUPPORT_MAX_VISIBILITY,
            "refute_visibility_at_least": REFUTE_MIN_VISIBILITY,
            "numeric_tolerance": TOLERANCE,
        },
        "self_check": self_check,
        "lineage": {
            "config_sha256": config_sha,
            "formal_seal_sha256": seal_sha,
            "trace_inputs": candidate_inputs + direct_inputs,
        },
        "candidate": candidate,
        "direct_md_context": direct_md,
    }
    result["decision"] = classify(candidate)
    write_outputs(result)
    print(json.dumps(result["decision"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
