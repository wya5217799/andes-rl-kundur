"""R485 checkpoint probe: is raw RMS mainly a quasi-static actor setpoint?

For ``an_cn_r0`` seed 501, freeze each scenario's canonical observation and
previous-action inputs at their own 150-step means.  If constant-anchor/actual
raw RMS is >= 0.90 in every profile and both channels, quasi-static actor output
is supported as the dominant RMS source.  Ratios <= 0.50 everywhere refute it;
other outcomes are inconclusive.  Actual replay must remain within 1e-6.

This is a local actor-input decomposition, not a closed-loop endpoint replay.

Usage: ``python probe_quasistatic_rms.py [--self-check]``
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np


SUPPORT_RATIO_MIN = 0.90
REFUTE_RATIO_MAX = 0.50
REPLAY_TOLERANCE = 1.0e-6
EXPECTED_PROBE05_SHA256 = "aa92a8be81978369e2f72916215740e5fa8088c2cce4aae00aecac6e460f270f"


def find_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "CLAUDE.md").is_file() and (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("repository root not found")


ROOT = find_root()
OUT_DIR = Path(__file__).resolve().parent
PROBE05_PATH = ROOT / "tmp/yang-md-decoupling-marl/r485_root_cause_probe_05/probe_previous_action_feedback.py"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_probe05() -> Any:
    if sha256_file(PROBE05_PATH) != EXPECTED_PROBE05_SHA256:
        raise ValueError("probe-05 code hash mismatch")
    spec = importlib.util.spec_from_file_location("r485_probe05_rms", PROBE05_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load probe-05 helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def channel_rms(actions: np.ndarray) -> np.ndarray:
    rows = np.asarray(actions, dtype=float)
    return np.sqrt(np.mean(np.square(rows), axis=(0, 1, 2)))


def synthetic_self_check() -> dict[str, Any]:
    values = np.zeros((2, 3, 4, 2), dtype=np.float32)
    values[..., 0] = 0.25
    values[..., 1] = -0.50
    rms = channel_rms(values)
    if not np.allclose(rms, [0.25, 0.50], rtol=0.0, atol=1e-15):
        raise AssertionError("channel RMS self-check failed")
    mean_fixed = np.repeat(values.mean(axis=1, keepdims=True), 3, axis=1)
    if not np.array_equal(values, mean_fixed):
        raise AssertionError("mean-anchor self-check failed")
    return {"rms": rms.tolist(), "mean_anchor": "PASS"}


def summarize(profile_id: str, actors: list[Any], checkpoint_sha: str, base: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    observations, previous, saved_raw, input_row = base.load_profile(
        base.TRACE_ROOT / f"{profile_id}.json", checkpoint_sha
    )
    replayed = base.actor_outputs(actors, observations, previous)
    replay_error = float(np.max(np.abs(replayed - saved_raw)))
    if replay_error > REPLAY_TOLERANCE:
        raise AssertionError(f"sealed raw replay mismatch: {replay_error}")

    fixed_previous = np.repeat(previous.mean(axis=1, keepdims=True), previous.shape[1], axis=1)
    fixed_observations = np.repeat(
        observations.mean(axis=1, keepdims=True), observations.shape[1], axis=1
    )
    fixed_prev_only_raw = base.actor_outputs(actors, observations, fixed_previous)
    constant_anchor_raw = base.actor_outputs(actors, fixed_observations, fixed_previous)
    actual_rms = channel_rms(saved_raw)
    fixed_prev_rms = channel_rms(fixed_prev_only_raw)
    constant_rms = channel_rms(constant_anchor_raw)
    return {
        "profile_id": profile_id,
        "actual_raw_rms": {"M": float(actual_rms[0]), "D": float(actual_rms[1])},
        "fixed_prev_raw_rms": {"M": float(fixed_prev_rms[0]), "D": float(fixed_prev_rms[1])},
        "constant_anchor_raw_rms": {"M": float(constant_rms[0]), "D": float(constant_rms[1])},
        "constant_anchor_to_actual_rms_ratio": {
            "M": float(constant_rms[0] / actual_rms[0]),
            "D": float(constant_rms[1] / actual_rms[1]),
        },
        "fixed_prev_to_actual_rms_ratio": {
            "M": float(fixed_prev_rms[0] / actual_rms[0]),
            "D": float(fixed_prev_rms[1] / actual_rms[1]),
        },
        "constant_anchor_raw_tv": {
            "M": float(base.path_tv(constant_anchor_raw)[0]),
            "D": float(base.path_tv(constant_anchor_raw)[1]),
        },
        "sealed_raw_replay_max_abs_error": replay_error,
    }, input_row


def decide(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ratios = [
        row["constant_anchor_to_actual_rms_ratio"][channel]
        for row in rows
        for channel in ("M", "D")
    ]
    supported = all(value >= SUPPORT_RATIO_MIN for value in ratios)
    refuted = all(value <= REFUTE_RATIO_MAX for value in ratios)
    verdict = (
        "QUASISTATIC_ACTOR_SETPOINT_RMS_SUPPORTED"
        if supported
        else "QUASISTATIC_ACTOR_SETPOINT_RMS_REFUTED"
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
        "# R485 root-cause probe 09: quasi-static RMS",
        "",
        "> Scratch post-hoc checkpoint diagnostic; not registered R485 evidence.",
        "",
        f"**Decision:** `{result['decision']['verdict']}`",
        "",
        "| Profile | constant/actual M RMS | constant/actual D RMS | fixed-prev/actual combined view |",
        "|---|---:|---:|---:|",
    ]
    for row in result["profiles"]:
        constant = row["constant_anchor_to_actual_rms_ratio"]
        fixed = row["fixed_prev_to_actual_rms_ratio"]
        lines.append(
            f"| {row['profile_id']} | {constant['M']:.3f} | {constant['D']:.3f} | "
            f"M {fixed['M']:.3f}, D {fixed['D']:.3f} |"
        )
    lines.extend(
        [
            "",
            "A high ratio means most raw magnitude remains when all actor inputs are",
            "time-constant within a scenario. Endpoint behavior is not evaluated.",
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

    base = load_probe05()
    base.torch.set_num_threads(1)
    actors, payload, checkpoint_input = base.load_actors()
    profiles: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []
    for profile_id in base.PROFILE_IDS:
        row, input_row = summarize(profile_id, actors, checkpoint_input["sha256"], base)
        profiles.append(row)
        inputs.append(input_row)
    result = {
        "schema_version": "r485_root_cause_probe_09_v1",
        "scope": "scratch_posthoc_checkpoint_diagnostic",
        "formal_artifacts_modified": False,
        "question": "Is raw RMS mainly retained by a quasi-static actor setpoint?",
        "thresholds": {
            "support_constant_to_actual_ratio_min": SUPPORT_RATIO_MIN,
            "refute_constant_to_actual_ratio_max": REFUTE_RATIO_MAX,
            "replay_tolerance": REPLAY_TOLERANCE,
        },
        "lineage": {
            "probe05_code_sha256": EXPECTED_PROBE05_SHA256,
            "checkpoint": checkpoint_input,
            "checkpoint_identity": {
                "kind": payload["kind"],
                "arm_id": payload["arm_id"],
                "seed": payload["seed"],
                "stage": payload["stage"],
            },
            "trace_inputs": inputs,
        },
        "self_check": self_check,
        "profiles": profiles,
    }
    result["decision"] = decide(profiles)
    write_outputs(result)
    print(json.dumps({"decision": result["decision"], "profiles": profiles}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
