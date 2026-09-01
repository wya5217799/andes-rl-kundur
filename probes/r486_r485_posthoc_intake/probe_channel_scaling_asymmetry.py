"""Throwaway R485 probe: is channel scaling the main M/D asymmetry source?

Question
--------
Across the existing 832 learned policy-profile blocks, does the fixed action
decoder create the comparator-relative M-versus-D command-activity asymmetry,
or is the asymmetry already present in normalized action coordinates?

Decision rule fixed before CSV loading
-------------------------------------
For RMS and TV separately, form ``M-relative / D-relative`` before and after
decoding.  Scaling as the primary source is refuted if at least 95% of blocks
already exceed 1.10 in normalized coordinates and the median two-sided decoder
distortion is below 1.10 for both metrics.  It is supported if at least half of
blocks cross from normalized <= 1.10 to decoded > 1.10 for either metric.
Other outcomes are inconclusive.  These are scratch diagnostic thresholds.

Controls
--------
The sealed parameter card must give identical positive/negative gains to M and
D.  An independent piecewise decoder must reproduce saved ``delta_M`` and
``delta_D`` within the card's mapping tolerance on one candidate and one
direct-M/D trace.  The aggregate CSV and traces are SHA256 verified.

Usage
-----
``python probe_channel_scaling_asymmetry.py --self-check``
``python probe_channel_scaling_asymmetry.py``
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


MATERIAL_RATIO = 1.10
PREVALENCE_REFUTE_MIN = 0.95
PREVALENCE_SUPPORT_MIN = 0.50
EXPECTED_CSV_SHA256 = "c941f1e323eed40c515382228cdd58a4ee56cb58e520a9b8548fe3cd566d9255"
EXPECTED_CARD_SHA256 = "325860a1f3eb5836ee7464ba9d2cf8fa0c7de51597e687bebeae0889323fa9ec"


def find_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "CLAUDE.md").is_file() and (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("repository root not found")


ROOT = find_root()
OUT_DIR = Path(__file__).resolve().parent
CSV_PATH = (
    ROOT
    / "tmp/yang-md-decoupling-marl/r485_offline_extension"
    / "policy_profile_command_activity.csv"
)
CARD_PATH = ROOT / "memory/rounds/R485/resolved_parameter_card.json"
EVAL_ROOT = (
    ROOT
    / "results/research_loop/r485_60hz_source_factorial"
    / "r485-formal-20260829-a/eval/same"
)
TRACE_PATHS = (
    EVAL_ROOT / "an_cn_r0/seed501/canary_eval_a.json",
    EVAL_ROOT / "local_neighbour_md_km2_kd2/deterministic/canary_eval_a.json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verified_sidecar(path: Path) -> dict[str, Any]:
    sidecar = Path(f"{path}.sha256")
    parts = sidecar.read_text(encoding="ascii").strip().split()
    if len(parts) < 2 or parts[1] != path.name:
        raise ValueError(f"invalid SHA256 sidecar: {sidecar}")
    actual = sha256_file(path)
    if actual != parts[0].lower():
        raise ValueError(f"SHA256 mismatch: {path}")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sidecar": sidecar.relative_to(ROOT).as_posix(),
        "sha256": actual,
        "verified": True,
    }


def decode(actions: np.ndarray, negative: float, positive: float) -> np.ndarray:
    rows = np.asarray(actions, dtype=float)
    return np.where(rows >= 0.0, rows * positive, rows * -negative)


def synthetic_self_check() -> dict[str, Any]:
    actions = np.asarray([-1.0, -0.5, 0.0, 0.5, 1.0])
    decoded = decode(actions, -200.0, 600.0)
    expected = np.asarray([-200.0, -100.0, 0.0, 300.0, 600.0])
    if not np.array_equal(decoded, expected):
        raise AssertionError("piecewise decoder self-check failed")
    return {"actions": actions.tolist(), "decoded": decoded.tolist()}


def verify_trace_mapping(card: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    decoder = card["action"]["decoder"]
    tolerance = float(decoder["mapping_atol"])
    max_error = {"M": 0.0, "D": 0.0}
    inputs: list[dict[str, Any]] = []
    steps_checked = 0
    for path in TRACE_PATHS:
        inputs.append(verified_sidecar(path))
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload.get("records")
        if not isinstance(records, list) or len(records) != 6:
            raise ValueError(f"expected 6 scenario records: {path}")
        for record in records:
            steps = record.get("steps")
            if not isinstance(steps, list) or len(steps) != 150:
                raise ValueError(f"expected 150 steps: {path}")
            for step in steps:
                action = np.asarray(step["projected_action_norm"], dtype=float)
                expected_m = decode(
                    action[:, 0],
                    float(decoder["delta_m_negative"]),
                    float(decoder["delta_m_positive"]),
                )
                expected_d = decode(
                    action[:, 1],
                    float(decoder["delta_d_negative"]),
                    float(decoder["delta_d_positive"]),
                )
                max_error["M"] = max(
                    max_error["M"],
                    float(np.max(np.abs(expected_m - np.asarray(step["delta_M"], dtype=float)))),
                )
                max_error["D"] = max(
                    max_error["D"],
                    float(np.max(np.abs(expected_d - np.asarray(step["delta_D"], dtype=float)))),
                )
                steps_checked += 1
    if max(max_error.values()) > tolerance:
        raise AssertionError(f"saved decoder mapping mismatch: {max_error}")
    return {
        "steps_checked": steps_checked,
        "mapping_atol": tolerance,
        "max_abs_error": max_error,
    }, inputs


def load_rows() -> tuple[list[dict[str, float]], dict[str, Any]]:
    actual = sha256_file(CSV_PATH)
    if actual != EXPECTED_CSV_SHA256:
        raise ValueError("offline extension CSV SHA256 mismatch")
    fields = (
        "ratio_projected_M_rms",
        "ratio_projected_D_rms",
        "ratio_decoded_M_rms",
        "ratio_decoded_D_rms",
        "ratio_projected_M_tv",
        "ratio_projected_D_tv",
        "ratio_decoded_M_tv",
        "ratio_decoded_D_tv",
    )
    rows: list[dict[str, float]] = []
    with CSV_PATH.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            parsed = {field: float(row[field]) for field in fields}
            if not all(np.isfinite(value) and value > 0.0 for value in parsed.values()):
                raise ValueError("CSV contains non-positive or non-finite ratio")
            rows.append(parsed)
    if len(rows) != 832:
        raise ValueError(f"expected 832 policy-profile rows, got {len(rows)}")
    return rows, {
        "path": CSV_PATH.relative_to(ROOT).as_posix(),
        "sha256": actual,
        "verified": True,
    }


def summarize(rows: list[dict[str, float]], metric: str) -> dict[str, Any]:
    normalized = np.asarray(
        [row[f"ratio_projected_M_{metric}"] / row[f"ratio_projected_D_{metric}"] for row in rows]
    )
    decoded = np.asarray(
        [row[f"ratio_decoded_M_{metric}"] / row[f"ratio_decoded_D_{metric}"] for row in rows]
    )
    signed_distortion = decoded / normalized
    two_sided_distortion = np.maximum(signed_distortion, 1.0 / signed_distortion)
    normalized_material = normalized > MATERIAL_RATIO
    decoded_material = decoded > MATERIAL_RATIO
    crossed = (~normalized_material) & decoded_material
    return {
        "metric": metric,
        "normalized_asymmetry": {
            "min": float(np.min(normalized)),
            "median": float(np.median(normalized)),
            "q95": float(np.quantile(normalized, 0.95)),
            "max": float(np.max(normalized)),
            "fraction_above_1p10": float(np.mean(normalized_material)),
        },
        "decoded_asymmetry": {
            "min": float(np.min(decoded)),
            "median": float(np.median(decoded)),
            "q95": float(np.quantile(decoded, 0.95)),
            "max": float(np.max(decoded)),
            "fraction_above_1p10": float(np.mean(decoded_material)),
        },
        "decoder_distortion": {
            "signed_median": float(np.median(signed_distortion)),
            "two_sided_median": float(np.median(two_sided_distortion)),
            "two_sided_q95": float(np.quantile(two_sided_distortion, 0.95)),
            "crossed_normalized_to_decoded_fraction": float(np.mean(crossed)),
        },
    }


def decide(summaries: dict[str, dict[str, Any]], identical_gains: bool) -> dict[str, Any]:
    refuted = identical_gains and all(
        row["normalized_asymmetry"]["fraction_above_1p10"] >= PREVALENCE_REFUTE_MIN
        and row["decoder_distortion"]["two_sided_median"] < MATERIAL_RATIO
        for row in summaries.values()
    )
    supported = any(
        row["decoder_distortion"]["crossed_normalized_to_decoded_fraction"]
        >= PREVALENCE_SUPPORT_MIN
        for row in summaries.values()
    )
    verdict = (
        "CHANNEL_SCALING_PRIMARY_CAUSE_REFUTED"
        if refuted
        else "CHANNEL_SCALING_PRIMARY_CAUSE_SUPPORTED"
        if supported
        else "INCONCLUSIVE"
    )
    return {"verdict": verdict, "refute_criteria_met": refuted, "support_criteria_met": supported}


def write_outputs(result: dict[str, Any]) -> None:
    result_path = OUT_DIR / "result.json"
    report_path = OUT_DIR / "REPORT.md"
    sums_path = OUT_DIR / "SHA256SUMS"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# R485 root-cause probe 03: channel-scaling asymmetry",
        "",
        "> Scratch post-hoc sealed-data diagnostic; not registered R485 evidence.",
        "",
        f"**Decision:** `{result['decision']['verdict']}`",
        "",
        "| Metric | normalized median M/D | normalized >1.10 | decoded median M/D | decoder median distortion |",
        "|---|---:|---:|---:|---:|",
    ]
    for metric in ("rms", "tv"):
        row = result["summaries"][metric]
        lines.append(
            f"| {metric.upper()} | {row['normalized_asymmetry']['median']:.3f} | "
            f"{row['normalized_asymmetry']['fraction_above_1p10']:.1%} | "
            f"{row['decoded_asymmetry']['median']:.3f} | "
            f"{row['decoder_distortion']['two_sided_median']:.3f} |"
        )
    lines.extend(
        [
            "",
            "The decoder can reshape severity through the common sign-asymmetric map,",
            "but this probe asks only whether it creates the M/D relative asymmetry.",
            "It does not explain why the normalized raw actor is highly active.",
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

    if sha256_file(CARD_PATH) != EXPECTED_CARD_SHA256:
        raise ValueError("resolved parameter card SHA256 mismatch")
    card = json.loads(CARD_PATH.read_text(encoding="utf-8"))
    decoder = card["action"]["decoder"]
    identical_gains = (
        float(decoder["delta_m_negative"]) == float(decoder["delta_d_negative"])
        and float(decoder["delta_m_positive"]) == float(decoder["delta_d_positive"])
    )
    mapping_check, trace_inputs = verify_trace_mapping(card)
    rows, csv_input = load_rows()
    summaries = {metric: summarize(rows, metric) for metric in ("rms", "tv")}
    result = {
        "schema_version": "r485_root_cause_probe_03_v1",
        "scope": "scratch_posthoc_sealed_data_diagnostic",
        "formal_artifacts_modified": False,
        "question": "Is decoder scaling the primary source of M/D relative activity asymmetry?",
        "thresholds": {
            "material_ratio": MATERIAL_RATIO,
            "refute_prevalence_min": PREVALENCE_REFUTE_MIN,
            "support_crossing_prevalence_min": PREVALENCE_SUPPORT_MIN,
        },
        "lineage": {
            "resolved_parameter_card_sha256": EXPECTED_CARD_SHA256,
            "inputs": [csv_input, *trace_inputs],
        },
        "self_check": self_check,
        "decoder": {
            "delta_m_negative": decoder["delta_m_negative"],
            "delta_m_positive": decoder["delta_m_positive"],
            "delta_d_negative": decoder["delta_d_negative"],
            "delta_d_positive": decoder["delta_d_positive"],
            "identical_m_d_gains": identical_gains,
        },
        "mapping_check": mapping_check,
        "summaries": summaries,
    }
    result["decision"] = decide(summaries, identical_gains)
    write_outputs(result)
    print(json.dumps({"decision": result["decision"], "summaries": summaries}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
