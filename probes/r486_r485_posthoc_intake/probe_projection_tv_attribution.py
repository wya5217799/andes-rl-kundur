"""Throwaway R485 probe: does projection manufacture executed-command TV?

Question
--------
On the outcome-blind first frozen policy (``an_cn_r0``, seed 501, four
same-bank profiles), is the recorded executed total variation mainly created
by amplitude/slew projection, or is the learned raw proposal already more
active than the direct-M/D comparator before projection?

Decision rule fixed before trace loading
----------------------------------------
TV includes the zero-to-first transition separately for every scenario.  The
projection-manufacture mechanism is refuted when every selected profile and
both M/D channels have projected/raw TV <= 0.90 while candidate/direct-MD raw
TV > 1.10.  It is supported only if every profile in both channels has
projected/raw TV >= 1.10.  Other outcomes are inconclusive.  These symmetric
10% bounds are post-hoc diagnostic materiality thresholds, not R485 evidence.

Controls
--------
An independently written float32 amplitude+slew replay must reproduce every
saved projected action and ``action_delta_norm`` within 1e-7.  A synthetic
identity-projector sequence must have TV ratio exactly one.  Every trace is
verified against its sealed SHA256 sidecar before use.

Usage
-----
``python probe_projection_tv_attribution.py --self-check``
``python probe_projection_tv_attribution.py``
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
SLEW_LIMIT = 0.25
SUPPRESS_MAX_RATIO = 0.90
MATERIAL_MIN_RATIO = 1.10
REPLAY_TOLERANCE = 1.0e-7
EXPECTED_CARD_SHA256 = "325860a1f3eb5836ee7464ba9d2cf8fa0c7de51597e687bebeae0889323fa9ec"


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


def project_independent(previous: np.ndarray, raw: np.ndarray, limit: float) -> np.ndarray:
    """Independent replay of the frozen float32 amplitude then slew mapping."""

    previous32 = np.asarray(previous, dtype=np.float32)
    raw32 = np.asarray(raw, dtype=np.float32)
    amplitude = np.clip(raw32, -1.0, 1.0).astype(np.float32)
    previous64 = previous32.astype(np.float64)
    delta64 = np.clip(amplitude.astype(np.float64) - previous64, -limit, limit)
    executed = np.clip(previous64 + delta64, -1.0, 1.0).astype(np.float32)
    overshoot = executed.astype(np.float64) - previous64 > limit
    undershoot = executed.astype(np.float64) - previous64 < -limit
    if np.any(overshoot):
        executed[overshoot] = np.nextafter(executed[overshoot], np.float32(-np.inf))
    if np.any(undershoot):
        executed[undershoot] = np.nextafter(executed[undershoot], np.float32(np.inf))
    return np.clip(executed, -1.0, 1.0).astype(np.float32)


def path_tv(sequence: list[np.ndarray]) -> np.ndarray:
    previous = np.zeros_like(sequence[0], dtype=np.float64)
    total = np.zeros(sequence[0].shape[1], dtype=np.float64)
    for row in sequence:
        current = np.asarray(row, dtype=np.float64)
        total += np.abs(current - previous).sum(axis=0)
        previous = current
    return total


def synthetic_self_check() -> dict[str, Any]:
    sequence = [
        np.asarray([[0.10, -0.10], [0.05, 0.0]], dtype=np.float32),
        np.asarray([[0.20, -0.20], [0.10, 0.05]], dtype=np.float32),
    ]
    previous = np.zeros((2, 2), dtype=np.float32)
    projected: list[np.ndarray] = []
    for raw in sequence:
        current = project_independent(previous, raw, limit=2.0)
        projected.append(current)
        previous = current
    raw_tv = path_tv(sequence)
    projected_tv = path_tv(projected)
    if not np.array_equal(sequence[0], projected[0]) or not np.array_equal(sequence[1], projected[1]):
        raise AssertionError("synthetic identity projector failed")
    if not np.array_equal(raw_tv, projected_tv):
        raise AssertionError("synthetic identity TV control failed")

    first = project_independent(np.zeros(2, dtype=np.float32), np.asarray([0.8, -0.8]), SLEW_LIMIT)
    second = project_independent(first, np.asarray([0.8, -0.8]), SLEW_LIMIT)
    if not np.array_equal(first, np.asarray([0.25, -0.25], dtype=np.float32)):
        raise AssertionError("synthetic slew first step failed")
    if not np.array_equal(second, np.asarray([0.50, -0.50], dtype=np.float32)):
        raise AssertionError("synthetic slew second step failed")
    return {"identity_tv_ratio": (projected_tv / raw_tv).tolist(), "slew_first": first.tolist()}


def verified_json(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    sidecar = Path(f"{path}.sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"sealed trace or sidecar missing: {path}")
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


def paths(kind: str) -> list[Path]:
    if kind == "candidate":
        base = EVAL_ROOT / "an_cn_r0/seed501"
    elif kind == "direct_md":
        base = EVAL_ROOT / "local_neighbour_md_km2_kd2/deterministic"
    else:
        raise ValueError(f"unknown kind: {kind}")
    return [base / f"{profile}.json" for profile in PROFILE_IDS]


def summarize(kind: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    profile_rows: list[dict[str, Any]] = []
    input_rows: list[dict[str, Any]] = []
    global_replay_error = 0.0
    global_delta_error = 0.0
    global_amplitude_clip_error = 0.0

    for profile_id, path in zip(PROFILE_IDS, paths(kind), strict=True):
        payload, input_row = verified_json(path)
        input_rows.append(input_row)
        records = payload.get("records")
        if not isinstance(records, list) or len(records) != 6:
            raise ValueError(f"expected 6 scenarios: {path}")
        raw_sequence_by_record: list[list[np.ndarray]] = []
        projected_sequence_by_record: list[list[np.ndarray]] = []
        active_elements = 0
        slew_limited_elements = 0
        element_count = 0

        for record in records:
            steps = record.get("steps")
            if not isinstance(steps, list) or len(steps) != 150:
                raise ValueError(f"expected 150 steps: {path}")
            previous = np.zeros((4, 2), dtype=np.float32)
            raw_sequence: list[np.ndarray] = []
            projected_sequence: list[np.ndarray] = []
            for step in steps:
                raw = np.asarray(step["raw_action_norm"], dtype=np.float32)
                saved = np.asarray(step["projected_action_norm"], dtype=np.float32)
                saved_delta = np.asarray(step["action_delta_norm"], dtype=np.float32)
                replayed = project_independent(previous, raw, SLEW_LIMIT)
                global_replay_error = max(
                    global_replay_error, float(np.max(np.abs(replayed - saved)))
                )
                global_delta_error = max(
                    global_delta_error,
                    float(np.max(np.abs((saved - previous) - saved_delta))),
                )
                amplitude = np.clip(raw, -1.0, 1.0).astype(np.float32)
                global_amplitude_clip_error = max(
                    global_amplitude_clip_error, float(np.max(np.abs(amplitude - raw)))
                )
                active_elements += int(np.count_nonzero(np.abs(saved - raw) > REPLAY_TOLERANCE))
                slew_limited_elements += int(
                    np.count_nonzero(np.abs(amplitude - previous) > SLEW_LIMIT + REPLAY_TOLERANCE)
                )
                element_count += raw.size
                raw_sequence.append(raw)
                projected_sequence.append(saved)
                previous = saved
            raw_sequence_by_record.append(raw_sequence)
            projected_sequence_by_record.append(projected_sequence)

        raw_tv = sum((path_tv(rows) for rows in raw_sequence_by_record), np.zeros(2))
        projected_tv = sum(
            (path_tv(rows) for rows in projected_sequence_by_record), np.zeros(2)
        )
        profile_rows.append(
            {
                "profile_id": profile_id,
                "raw_tv": {"M": float(raw_tv[0]), "D": float(raw_tv[1])},
                "projected_tv": {
                    "M": float(projected_tv[0]),
                    "D": float(projected_tv[1]),
                },
                "projected_to_raw_tv_ratio": {
                    "M": float(projected_tv[0] / raw_tv[0]),
                    "D": float(projected_tv[1] / raw_tv[1]),
                },
                "projection_active_fraction": active_elements / element_count,
                "slew_limited_target_fraction": slew_limited_elements / element_count,
            }
        )

    if global_replay_error > REPLAY_TOLERANCE:
        raise AssertionError(f"projector replay mismatch: {global_replay_error}")
    if global_delta_error > REPLAY_TOLERANCE:
        raise AssertionError(f"saved action delta mismatch: {global_delta_error}")
    return {
        "selection": kind,
        "profiles": profile_rows,
        "checks": {
            "projector_replay_max_abs_error": global_replay_error,
            "saved_action_delta_max_abs_error": global_delta_error,
            "raw_amplitude_clip_max_abs_change": global_amplitude_clip_error,
        },
    }, input_rows


def decide(candidate: dict[str, Any], direct_md: dict[str, Any]) -> dict[str, Any]:
    direct_by_profile = {row["profile_id"]: row for row in direct_md["profiles"]}
    rows: list[dict[str, Any]] = []
    for candidate_row in candidate["profiles"]:
        reference = direct_by_profile[candidate_row["profile_id"]]
        raw_ratio = {
            channel: candidate_row["raw_tv"][channel] / reference["raw_tv"][channel]
            for channel in ("M", "D")
        }
        rows.append(
            {
                "profile_id": candidate_row["profile_id"],
                "projected_to_raw_tv_ratio": candidate_row["projected_to_raw_tv_ratio"],
                "candidate_to_direct_raw_tv_ratio": raw_ratio,
            }
        )

    projection_suppresses_all = all(
        row["projected_to_raw_tv_ratio"][channel] <= SUPPRESS_MAX_RATIO
        for row in rows
        for channel in ("M", "D")
    )
    raw_material_all = all(
        row["candidate_to_direct_raw_tv_ratio"][channel] > MATERIAL_MIN_RATIO
        for row in rows
        for channel in ("M", "D")
    )
    projection_increases_all = all(
        row["projected_to_raw_tv_ratio"][channel] >= MATERIAL_MIN_RATIO
        for row in rows
        for channel in ("M", "D")
    )
    if projection_suppresses_all and raw_material_all:
        verdict = "RAW_PROPOSAL_ACTIVE_PROJECTION_MANUFACTURE_REFUTED"
    elif projection_increases_all:
        verdict = "PROJECTION_MANUFACTURE_SUPPORTED"
    else:
        verdict = "INCONCLUSIVE"
    return {
        "verdict": verdict,
        "projection_suppresses_all": projection_suppresses_all,
        "candidate_raw_material_vs_direct_all": raw_material_all,
        "projection_increases_all": projection_increases_all,
        "paired_profiles": rows,
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
        "# R485 root-cause probe 02: raw versus projected TV",
        "",
        "> Scratch post-hoc sealed-data diagnostic; not registered R485 evidence.",
        "",
        f"**Decision:** `{result['decision']['verdict']}`",
        "",
        "| Profile | projected/raw M | projected/raw D | raw/direct M | raw/direct D |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in result["decision"]["paired_profiles"]:
        projected = row["projected_to_raw_tv_ratio"]
        raw = row["candidate_to_direct_raw_tv_ratio"]
        lines.append(
            f"| {row['profile_id']} | {projected['M']:.4f} | {projected['D']:.4f} | "
            f"{raw['M']:.2f}x | {raw['D']:.2f}x |"
        )
    lines.extend(
        [
            "",
            "This attributes path length only on the recorded closed-loop trajectory.",
            "It does not identify why the deterministic raw actor changes rapidly, and",
            "it is not a counterfactual raw-action ANDES replay.",
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

    card_path = ROOT / "memory/rounds/R485/resolved_parameter_card.json"
    card_sha = sha256_file(card_path)
    if card_sha != EXPECTED_CARD_SHA256:
        raise ValueError(
            "resolved parameter card hash differs; inspect lineage before changing the expected hash"
        )
    card = json.loads(card_path.read_text(encoding="utf-8"))
    if float(card["action"]["slew_limit"]) != SLEW_LIMIT:
        raise ValueError("resolved slew limit does not match probe")

    candidate, candidate_inputs = summarize("candidate")
    direct_md, direct_inputs = summarize("direct_md")
    result = {
        "schema_version": "r485_root_cause_probe_02_v1",
        "scope": "scratch_posthoc_sealed_data_diagnostic",
        "formal_artifacts_modified": False,
        "question": (
            "Does projection manufacture executed TV, or is raw policy activity already material?"
        ),
        "selection_rule": (
            "lexicographically first arm an_cn_r0, lowest seed 501, all four same-bank "
            "profiles; paired direct-M/D context"
        ),
        "thresholds": {
            "projection_suppression_ratio_at_most": SUPPRESS_MAX_RATIO,
            "material_ratio_at_least": MATERIAL_MIN_RATIO,
            "replay_tolerance": REPLAY_TOLERANCE,
        },
        "lineage": {
            "resolved_parameter_card_sha256": card_sha,
            "trace_inputs": candidate_inputs + direct_inputs,
        },
        "self_check": self_check,
        "candidate": candidate,
        "direct_md": direct_md,
    }
    result["decision"] = decide(candidate, direct_md)
    write_outputs(result)
    print(json.dumps(result["decision"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
