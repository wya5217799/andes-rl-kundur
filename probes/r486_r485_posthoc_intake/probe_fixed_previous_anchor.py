"""R485 checkpoint probe: is feedback TV reduction robust to a nonzero anchor?

For each sealed scenario of ``an_cn_r0`` seed 501, replace the time-varying
previous-action actor input by that scenario's own per-agent/channel mean.  If
fixed-mean/actual raw TV is <= 0.50 for all four profiles and both channels,
time-varying previous-action feedback is supported as the amplifier.  Ratios
>= 0.90 everywhere refute it; other outcomes are inconclusive.  Actual actor
replay must remain within 1e-6.

This imports the already verified probe-05 replay functions by a fixed code
hash.  It is a local recorded-observation ablation, not an ANDES replay.

Usage: ``python probe_fixed_previous_anchor.py [--self-check]``
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np


SUPPORT_RATIO_MAX = 0.50
REFUTE_RATIO_MIN = 0.90
REPLAY_TOLERANCE = 1.0e-6
EXPECTED_PROBE05_SHA256 = "aa92a8be81978369e2f72916215740e5fa8088c2cce4aae00aecac6e460f270f"


def find_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "CLAUDE.md").is_file() and (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("repository root not found")


ROOT = find_root()
OUT_DIR = Path(__file__).resolve().parent
PROBE05_PATH = (
    ROOT
    / "tmp/yang-md-decoupling-marl/r485_root_cause_probe_05"
    / "probe_previous_action_feedback.py"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_probe05() -> Any:
    if sha256_file(PROBE05_PATH) != EXPECTED_PROBE05_SHA256:
        raise ValueError("probe-05 code hash mismatch")
    spec = importlib.util.spec_from_file_location("r485_probe05_fixed", PROBE05_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load probe-05 helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_self_check() -> dict[str, Any]:
    previous = np.arange(2 * 3 * 4 * 2, dtype=np.float32).reshape(2, 3, 4, 2)
    fixed = np.repeat(previous.mean(axis=1, keepdims=True), 3, axis=1)
    if fixed.shape != previous.shape:
        raise AssertionError("fixed-anchor shape mismatch")
    if not np.allclose(fixed[:, 0], previous.mean(axis=1), rtol=0.0, atol=0.0):
        raise AssertionError("fixed-anchor mean mismatch")
    if not np.array_equal(fixed[:, 0], fixed[:, -1]):
        raise AssertionError("fixed anchor is not time invariant")
    return {"shape": list(fixed.shape), "time_invariant": True}


def summarize(profile_id: str, actors: list[Any], checkpoint_sha: str, base: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    observations, previous, saved_raw, input_row = base.load_profile(
        base.TRACE_ROOT / f"{profile_id}.json", checkpoint_sha
    )
    replayed = base.actor_outputs(actors, observations, previous)
    replay_error = float(np.max(np.abs(replayed - saved_raw)))
    if replay_error > REPLAY_TOLERANCE:
        raise AssertionError(f"sealed replay mismatch: {replay_error}")
    fixed_previous = np.repeat(previous.mean(axis=1, keepdims=True), previous.shape[1], axis=1)
    zero_previous = np.zeros_like(previous)
    fixed_raw = base.actor_outputs(actors, observations, fixed_previous)
    zero_raw = base.actor_outputs(actors, observations, zero_previous)
    actual_tv = base.path_tv(saved_raw)
    fixed_tv = base.path_tv(fixed_raw)
    zero_tv = base.path_tv(zero_raw)
    return {
        "profile_id": profile_id,
        "actual_raw_tv": {"M": float(actual_tv[0]), "D": float(actual_tv[1])},
        "fixed_mean_prev_raw_tv": {"M": float(fixed_tv[0]), "D": float(fixed_tv[1])},
        "zero_prev_raw_tv": {"M": float(zero_tv[0]), "D": float(zero_tv[1])},
        "fixed_mean_to_actual_tv_ratio": {
            "M": float(fixed_tv[0] / actual_tv[0]),
            "D": float(fixed_tv[1] / actual_tv[1]),
        },
        "zero_to_actual_tv_ratio": {
            "M": float(zero_tv[0] / actual_tv[0]),
            "D": float(zero_tv[1] / actual_tv[1]),
        },
        "fixed_mean_raw_rms": float(np.sqrt(np.mean(np.square(fixed_raw)))),
        "actual_raw_rms": float(np.sqrt(np.mean(np.square(saved_raw)))),
        "sealed_raw_replay_max_abs_error": replay_error,
    }, input_row


def decide(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ratios = [
        row["fixed_mean_to_actual_tv_ratio"][channel]
        for row in rows
        for channel in ("M", "D")
    ]
    supported = all(value <= SUPPORT_RATIO_MAX for value in ratios)
    refuted = all(value >= REFUTE_RATIO_MIN for value in ratios)
    verdict = (
        "TIME_VARYING_PREVIOUS_FEEDBACK_AMPLIFIER_SUPPORTED"
        if supported
        else "TIME_VARYING_PREVIOUS_FEEDBACK_AMPLIFIER_REFUTED"
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
        "# R485 root-cause probe 06: fixed previous-action anchor",
        "",
        "> Scratch post-hoc checkpoint diagnostic; not registered R485 evidence.",
        "",
        f"**Decision:** `{result['decision']['verdict']}`",
        "",
        "| Profile | fixed-mean/actual M TV | fixed-mean/actual D TV | raw RMS fixed/actual |",
        "|---|---:|---:|---:|",
    ]
    for row in result["profiles"]:
        ratio = row["fixed_mean_to_actual_tv_ratio"]
        lines.append(
            f"| {row['profile_id']} | {ratio['M']:.3f} | {ratio['D']:.3f} | "
            f"{row['fixed_mean_raw_rms'] / row['actual_raw_rms']:.3f} |"
        )
    lines.extend(
        [
            "",
            "A scenario-mean anchor removes only temporal variation from the two previous-action",
            "slots. It remains an offline actor-input ablation, not a controller proposal.",
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
    trace_inputs: list[dict[str, Any]] = []
    for profile_id in base.PROFILE_IDS:
        row, input_row = summarize(profile_id, actors, checkpoint_input["sha256"], base)
        profiles.append(row)
        trace_inputs.append(input_row)
    result = {
        "schema_version": "r485_root_cause_probe_06_v1",
        "scope": "scratch_posthoc_checkpoint_diagnostic",
        "formal_artifacts_modified": False,
        "question": "Is TV amplification robust when previous-action input is fixed at a nonzero scenario mean?",
        "thresholds": {
            "support_fixed_to_actual_ratio_max": SUPPORT_RATIO_MAX,
            "refute_fixed_to_actual_ratio_min": REFUTE_RATIO_MIN,
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
            "trace_inputs": trace_inputs,
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
