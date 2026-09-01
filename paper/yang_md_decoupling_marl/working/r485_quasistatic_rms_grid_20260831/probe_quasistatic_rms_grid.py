"""Bounded R485 checkpoint replay for quasi-static RMS prevalence.

Freeze the same 8-arm x 3-seed grid used by feedback probe 08 and evaluate all
four R485 profiles.  Within each scenario, replace every canonical-observation
and previous-executed-action actor input by its 150-step mean.  Compare the
resulting raw-action channel RMS with the sealed raw actor output.

This is a post-hoc actor-path decomposition.  It does not replay the plant,
evaluate endpoints, or establish a training/closed-loop causal mechanism.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np


ARM_IDS = (
    "an_cn_r0",
    "an_cn_r1",
    "an_cp_r0",
    "an_cp_r1",
    "ap_cn_r0",
    "ap_cn_r1",
    "ap_cp_r0",
    "ap_cp_r1",
)
SEEDS = (501, 513, 526)
PROFILE_IDS = (
    "canary_eval_a",
    "canary_eval_b",
    "canary_eval_c",
    "canary_eval_d",
)
SUPPORT_RATIO_MIN = 0.90
WEAK_RATIO_MAX = 0.50
SUPPORT_PREVALENCE_MIN = 0.90
REFUTE_PREVALENCE_MIN = 0.50
REPLAY_TOLERANCE = 1.0e-6
EXPECTED_GRID_HELPER_SHA256 = (
    "56843c4f178b0ba397d2a579715d18a60ae685f3d73885ca2252d89952ed2c61"
)
EXPECTED_BASE_HELPER_SHA256 = (
    "aa92a8be81978369e2f72916215740e5fa8088c2cce4aae00aecac6e460f270f"
)


def find_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "CLAUDE.md").is_file() and (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("repository root not found")


ROOT = find_root()
OUT_DIR = Path(__file__).resolve().parent
GRID_HELPER_PATH = (
    ROOT / "probes/r486_r485_posthoc_intake/probe_feedback_generality.py"
)
BASE_HELPER_PATH = (
    ROOT / "probes/r486_r485_posthoc_intake/probe_previous_action_feedback.py"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_grid_helper() -> Any:
    if sha256_file(GRID_HELPER_PATH) != EXPECTED_GRID_HELPER_SHA256:
        raise ValueError("grid-helper code hash mismatch")
    spec = importlib.util.spec_from_file_location("r485_probe08_rms_grid", GRID_HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load grid helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_base_helper() -> Any:
    if sha256_file(BASE_HELPER_PATH) != EXPECTED_BASE_HELPER_SHA256:
        raise ValueError("base-helper code hash mismatch")
    spec = importlib.util.spec_from_file_location("r485_probe05_rms_grid", BASE_HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load base helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def channel_rms(actions: np.ndarray) -> np.ndarray:
    rows = np.asarray(actions, dtype=float)
    return np.sqrt(np.mean(np.square(rows), axis=(0, 1, 2)))


def synthetic_self_check(grid: Any) -> dict[str, Any]:
    routing = grid.synthetic_self_check()
    values = np.zeros((2, 3, 4, 2), dtype=np.float32)
    values[..., 0] = 0.25
    values[..., 1] = -0.50
    rms = channel_rms(values)
    if not np.allclose(rms, [0.25, 0.50], rtol=0.0, atol=1.0e-15):
        raise AssertionError("channel RMS self-check failed")
    mean_fixed = np.repeat(values.mean(axis=1, keepdims=True), 3, axis=1)
    if not np.array_equal(values, mean_fixed):
        raise AssertionError("mean-anchor self-check failed")
    return {"routing": routing, "rms": rms.tolist(), "mean_anchor": "PASS"}


def load_trace(
    base: Any,
    grid: Any,
    arm_id: str,
    seed: int,
    profile_id: str,
    checkpoint_sha: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    path = grid.ATTEMPT_ROOT / f"eval/same/{arm_id}/seed{seed}/{profile_id}.json"
    input_row = base.verified_sidecar(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != 6:
        raise ValueError(f"expected 6 records: {path}")
    observations = np.zeros((6, 150, 4, 7), dtype=np.float32)
    previous = np.zeros((6, 150, 4, 2), dtype=np.float32)
    saved_raw = np.zeros((6, 150, 4, 2), dtype=np.float32)
    source = grid.actor_source(arm_id)
    for record_index, record in enumerate(records):
        if record.get("checkpoint_sha256") != checkpoint_sha:
            raise ValueError(f"trace/checkpoint hash mismatch: {path}")
        steps = record.get("steps")
        if not isinstance(steps, list) or len(steps) != 150:
            raise ValueError(f"expected 150 steps: {path}")
        prior = np.zeros((4, 2), dtype=np.float32)
        for step_index, step in enumerate(steps):
            observations[record_index, step_index] = grid.source_rows(
                np.asarray(step["canonical_observation"], dtype=np.float32), source
            )
            previous[record_index, step_index] = prior
            saved_raw[record_index, step_index] = np.asarray(
                step["raw_action_norm"], dtype=np.float32
            )
            prior = np.asarray(step["projected_action_norm"], dtype=np.float32)
    return observations, previous, saved_raw, input_row


def summarize_profile(
    base: Any,
    grid: Any,
    actors: list[Any],
    arm_id: str,
    seed: int,
    profile_id: str,
    checkpoint_sha: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    observations, previous, saved_raw, trace_input = load_trace(
        base, grid, arm_id, seed, profile_id, checkpoint_sha
    )
    replayed = grid.actor_outputs_production_style(base, actors, observations, previous)
    replay_error = float(np.max(np.abs(replayed - saved_raw)))
    if replay_error > REPLAY_TOLERANCE:
        raise AssertionError(
            f"sealed raw replay mismatch for {arm_id}/seed{seed}/{profile_id}: "
            f"{replay_error}"
        )

    fixed_previous = np.repeat(
        previous.mean(axis=1, keepdims=True), previous.shape[1], axis=1
    )
    fixed_observations = np.repeat(
        observations.mean(axis=1, keepdims=True), observations.shape[1], axis=1
    )
    fixed_prev_only = grid.actor_outputs_production_style(
        base, actors, observations, fixed_previous
    )
    constant_anchor = grid.actor_outputs_production_style(
        base, actors, fixed_observations, fixed_previous
    )
    actual_rms = channel_rms(saved_raw)
    fixed_prev_rms = channel_rms(fixed_prev_only)
    constant_rms = channel_rms(constant_anchor)
    row = {
        "arm_id": arm_id,
        "seed": seed,
        "profile_id": profile_id,
        "actor_source": grid.actor_source(arm_id),
        "actual_raw_rms": {"M": float(actual_rms[0]), "D": float(actual_rms[1])},
        "fixed_prev_raw_rms": {
            "M": float(fixed_prev_rms[0]),
            "D": float(fixed_prev_rms[1]),
        },
        "constant_anchor_raw_rms": {
            "M": float(constant_rms[0]),
            "D": float(constant_rms[1]),
        },
        "constant_anchor_to_actual_rms_ratio": {
            "M": float(constant_rms[0] / actual_rms[0]),
            "D": float(constant_rms[1] / actual_rms[1]),
        },
        "fixed_prev_to_actual_rms_ratio": {
            "M": float(fixed_prev_rms[0] / actual_rms[0]),
            "D": float(fixed_prev_rms[1] / actual_rms[1]),
        },
        "sealed_raw_replay_max_abs_error": replay_error,
    }
    del observations, previous, saved_raw, replayed, fixed_prev_only, constant_anchor
    gc.collect()
    return row, trace_input


def ratio_values(rows: list[dict[str, Any]]) -> np.ndarray:
    return np.asarray(
        [
            row["constant_anchor_to_actual_rms_ratio"][channel]
            for row in rows
            for channel in ("M", "D")
        ],
        dtype=float,
    )


def summarize_ratios(values: np.ndarray) -> dict[str, float]:
    return {
        "min": float(np.min(values)),
        "q05": float(np.quantile(values, 0.05)),
        "median": float(np.median(values)),
        "q95": float(np.quantile(values, 0.95)),
        "max": float(np.max(values)),
        "support_prevalence": float(np.mean(values >= SUPPORT_RATIO_MIN)),
        "weak_prevalence": float(np.mean(values <= WEAK_RATIO_MAX)),
    }


def decide(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = ratio_values(rows)
    summary = summarize_ratios(values)
    supported = (
        summary["support_prevalence"] >= SUPPORT_PREVALENCE_MIN
        and summary["weak_prevalence"] == 0.0
    )
    refuted = summary["weak_prevalence"] >= REFUTE_PREVALENCE_MIN
    verdict = (
        "QUASISTATIC_RMS_GRID_SUPPORTED"
        if supported
        else "QUASISTATIC_RMS_GRID_REFUTED"
        if refuted
        else "QUASISTATIC_RMS_GRID_HETEROGENEOUS"
    )
    return {"verdict": verdict, **summary}


def grouped_summary(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for value in sorted({str(row[key]) for row in rows}):
        selected = [row for row in rows if str(row[key]) == value]
        output[value] = summarize_ratios(ratio_values(selected))
    return output


def channel_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for channel in ("M", "D"):
        values = np.asarray(
            [row["constant_anchor_to_actual_rms_ratio"][channel] for row in rows],
            dtype=float,
        )
        output[channel] = summarize_ratios(values)
    return output


def write_outputs(result: dict[str, Any]) -> None:
    result_path = OUT_DIR / "result.json"
    sidecar_path = OUT_DIR / "result.json.sha256"
    report_path = OUT_DIR / "REPORT.md"
    sums_path = OUT_DIR / "SHA256SUMS"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    sidecar_path.write_text(
        f"{sha256_file(result_path)}  {result_path.name}\n", encoding="ascii"
    )
    decision = result["decision"]
    lines = [
        "# R485 quasi-static RMS fixed-grid checkpoint replay",
        "",
        "> Post-hoc actor-path diagnostic; no ANDES trajectory or training.",
        "",
        f"**Decision:** `{decision['verdict']}`",
        "",
        f"- Grid: {result['counts']['policies']} policies x "
        f"{result['counts']['profiles']} profiles = "
        f"{result['counts']['policy_profile_blocks']} blocks / "
        f"{result['counts']['channel_ratios']} channel ratios.",
        f"- Ratio min / q05 / median / q95 / max: {decision['min']:.3f} / "
        f"{decision['q05']:.3f} / {decision['median']:.3f} / "
        f"{decision['q95']:.3f} / {decision['max']:.3f}.",
        f"- Prevalence >= {SUPPORT_RATIO_MIN:.2f}: "
        f"{decision['support_prevalence']:.1%}; prevalence <= {WEAK_RATIO_MAX:.2f}: "
        f"{decision['weak_prevalence']:.1%}.",
        "",
        "| Profile | min | median | max | >=0.90 | <=0.50 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for profile_id, summary in result["by_profile"].items():
        lines.append(
            f"| {profile_id} | {summary['min']:.3f} | {summary['median']:.3f} | "
            f"{summary['max']:.3f} | {summary['support_prevalence']:.1%} | "
            f"{summary['weak_prevalence']:.1%} |"
        )
    lines.extend(
        [
            "",
            "| Channel | min | median | max | >=0.90 | <=0.50 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for channel, summary in result["by_channel"].items():
        lines.append(
            f"| {channel} | {summary['min']:.3f} | {summary['median']:.3f} | "
            f"{summary['max']:.3f} | {summary['support_prevalence']:.1%} | "
            f"{summary['weak_prevalence']:.1%} |"
        )
    lines.extend(
        [
            "",
            "The grid tests recurrence of retained raw RMS across fixed factors, seeds,",
            "and profiles. It does not evaluate closed-loop endpoints, stability, or the",
            "effect of retraining or modifying the controller.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    hashed = [Path(__file__).resolve(), result_path, sidecar_path, report_path]
    sums_path.write_text(
        "".join(f"{sha256_file(path)}  {path.name}\n" for path in hashed),
        encoding="ascii",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--refresh-existing", action="store_true")
    args = parser.parse_args()
    grid = load_grid_helper()
    self_check = synthetic_self_check(grid)
    if args.self_check:
        print(json.dumps({"self_check": "PASS", "details": self_check}, indent=2))
        return 0
    if args.refresh_existing:
        result_path = OUT_DIR / "result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        rows = result["rows"]
        result["decision"] = decide(rows)
        result["by_profile"] = grouped_summary(rows, "profile_id")
        result["by_arm"] = grouped_summary(rows, "arm_id")
        result["by_channel"] = channel_summary(rows)
        write_outputs(result)
        print(json.dumps({"decision": result["decision"], "by_channel": result["by_channel"]}, indent=2))
        return 0

    base = load_base_helper()
    base.torch.set_num_threads(1)
    rows: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []
    for arm_id in ARM_IDS:
        for seed in SEEDS:
            actors, payload, checkpoint_input = grid.load_policy(base, arm_id, seed)
            inputs.append(checkpoint_input)
            for profile_id in PROFILE_IDS:
                row, trace_input = summarize_profile(
                    base,
                    grid,
                    actors,
                    arm_id,
                    seed,
                    profile_id,
                    checkpoint_input["sha256"],
                )
                rows.append(row)
                inputs.append(trace_input)
            del actors, payload
            gc.collect()

    result = {
        "schema_version": "r485_quasistatic_rms_grid_v1",
        "scope": "scratch_posthoc_checkpoint_grid",
        "formal_artifacts_modified": False,
        "new_andes_trajectories": 0,
        "new_training_runs": 0,
        "question": (
            "Does quasi-static raw RMS retention recur across the frozen "
            "8-arm x 3-seed x 4-profile grid?"
        ),
        "selection": {
            "arms": list(ARM_IDS),
            "seeds": list(SEEDS),
            "profiles": list(PROFILE_IDS),
            "outcome_visible_fixed_grid": True,
        },
        "thresholds": {
            "support_ratio_min": SUPPORT_RATIO_MIN,
            "weak_ratio_max": WEAK_RATIO_MAX,
            "support_prevalence_min": SUPPORT_PREVALENCE_MIN,
            "refute_prevalence_min": REFUTE_PREVALENCE_MIN,
            "replay_tolerance": REPLAY_TOLERANCE,
        },
        "counts": {
            "policies": len(ARM_IDS) * len(SEEDS),
            "profiles": len(PROFILE_IDS),
            "policy_profile_blocks": len(rows),
            "channel_ratios": len(rows) * 2,
        },
        "lineage": {
            "grid_helper": {
                "path": GRID_HELPER_PATH.relative_to(ROOT).as_posix(),
                "sha256": EXPECTED_GRID_HELPER_SHA256,
            },
            "base_helper": {
                "path": BASE_HELPER_PATH.relative_to(ROOT).as_posix(),
                "sha256": EXPECTED_BASE_HELPER_SHA256,
            },
            "inputs": inputs,
        },
        "self_check": self_check,
        "rows": rows,
    }
    result["decision"] = decide(rows)
    result["by_profile"] = grouped_summary(rows, "profile_id")
    result["by_arm"] = grouped_summary(rows, "arm_id")
    result["by_channel"] = channel_summary(rows)
    write_outputs(result)
    print(json.dumps({"decision": result["decision"], "counts": result["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
