"""PROTOTYPE: independently verify the full-832 per-channel command CSV."""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
EVAL = ROOT / "results" / "research_loop" / "r485_60hz_source_factorial" / "r485-formal-20260829-a" / "eval" / "same"
CSV_PATH = ROOT / "tmp" / "yang-md-decoupling-marl" / "r485_offline_extension" / "policy_profile_command_activity.csv"
DIRECT = "local_neighbour_md_km2_kd2"


def command_metrics(payload: dict[str, Any]) -> dict[str, float]:
    records = payload["records"]
    raw = np.asarray([[step["raw_action_norm"] for step in record["steps"]] for record in records], dtype=float)
    projected = np.asarray([[step["projected_action_norm"] for step in record["steps"]] for record in records], dtype=float)
    executed = np.asarray([[step["action_norm"] for step in record["steps"]] for record in records], dtype=float)
    delta_m = np.asarray([[step["delta_M"] for step in record["steps"]] for record in records], dtype=float)
    delta_d = np.asarray([[step["delta_D"] for step in record["steps"]] for record in records], dtype=float)
    result: dict[str, float] = {}
    for name, values in (("raw", raw), ("projected", projected), ("executed", executed)):
        differences = np.diff(np.concatenate([np.zeros((6, 1, 4, 2)), values], axis=1), axis=1)
        result[f"{name}_combined_rms"] = float(np.sqrt(np.mean(values**2)))
        result[f"{name}_combined_tv"] = float(np.sum(np.mean(np.abs(differences), axis=(2, 3))))
        for channel, index in (("M", 0), ("D", 1)):
            result[f"{name}_{channel}_rms"] = float(np.sqrt(np.mean(values[..., index] ** 2)))
            result[f"{name}_{channel}_tv"] = float(np.sum(np.mean(np.abs(differences[..., index]), axis=2)))
    for channel, values in (("M", delta_m), ("D", delta_d)):
        differences = np.diff(np.concatenate([np.zeros((6, 1, 4)), values], axis=1), axis=1)
        result[f"decoded_{channel}_rms"] = float(np.sqrt(np.mean(values**2)))
        result[f"decoded_{channel}_tv"] = float(np.sum(np.mean(np.abs(differences), axis=2)))
    result["raw_projection_max_abs"] = float(np.max(np.abs(raw - projected)))
    result["projected_executed_max_abs"] = float(np.max(np.abs(projected - executed)))
    return result


def run() -> dict[str, Any]:
    started = time.time()
    with CSV_PATH.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    csv_rows = {(row["arm_id"], int(row["training_seed"]), row["profile_id"]): row for row in rows}
    if len(csv_rows) != 832:
        raise ValueError("CSV roster is not 832 unique policy-profile rows")
    references = {
        path.stem: command_metrics(json.loads(path.read_bytes()))
        for path in sorted((EVAL / DIRECT / "deterministic").glob("*.json"))
    }
    mismatches: list[str] = []
    max_abs = 0.0
    max_rel = 0.0
    ratios: dict[str, list[float]] = {name: [] for name in ("projected_M_rms", "projected_D_rms", "projected_M_tv", "projected_D_tv")}
    checked_fields = 0
    for path in sorted(EVAL.glob("*/seed*/*.json")):
        payload = json.loads(path.read_bytes())
        first = payload["records"][0]
        key = (first["arm_id"], int(first["training_seed"]), first["profile_id"])
        row = csv_rows[key]
        candidate = command_metrics(payload)
        reference = references[first["profile_id"]]
        for prefix, metrics in (("candidate", candidate), ("reference", reference)):
            for name, expected in metrics.items():
                field = f"{prefix}_{name}"
                observed = float(row[field])
                error = abs(observed - expected)
                relative = error / max(abs(expected), 1.0e-300)
                max_abs = max(max_abs, error)
                max_rel = max(max_rel, relative)
                checked_fields += 1
                if not math.isclose(observed, expected, rel_tol=1.0e-12, abs_tol=1.0e-12):
                    mismatches.append(f"{key}|{field}")
        for stage in ("raw", "projected", "executed"):
            for channel in ("combined", "M", "D"):
                for metric in ("rms", "tv"):
                    field = f"ratio_{stage}_{channel}_{metric}"
                    expected = candidate[f"{stage}_{channel}_{metric}"] / reference[f"{stage}_{channel}_{metric}"]
                    observed = float(row[field])
                    checked_fields += 1
                    if not math.isclose(observed, expected, rel_tol=1.0e-12, abs_tol=1.0e-12):
                        mismatches.append(f"{key}|{field}")
        for channel in ("M", "D"):
            for metric in ("rms", "tv"):
                field = f"ratio_decoded_{channel}_{metric}"
                expected = candidate[f"decoded_{channel}_{metric}"] / reference[f"decoded_{channel}_{metric}"]
                observed = float(row[field])
                checked_fields += 1
                if not math.isclose(observed, expected, rel_tol=1.0e-12, abs_tol=1.0e-12):
                    mismatches.append(f"{key}|{field}")
        for name in ratios:
            ratios[name].append(float(row[f"ratio_{name}"]))
    medians = {name: float(np.median(values)) for name, values in ratios.items()}
    negative_control = {
        "correct_projected_rms_m_over_d": medians["projected_M_rms"] / medians["projected_D_rms"],
        "swapped_denominator_projected_rms_m_over_d": medians["projected_M_rms"] / float(np.median([1.0 / value for value in ratios["projected_D_rms"]])),
        "swapping_denominator_changes_result": not math.isclose(
            medians["projected_M_rms"] / medians["projected_D_rms"],
            medians["projected_M_rms"] / float(np.median([1.0 / value for value in ratios["projected_D_rms"]])),
        ),
    }
    return {
        "schema_version": 1,
        "probe": "R485 pre-paper audit probe 04: per-channel extension",
        "question": "Are the full-832 per-channel ratios reproducible from sealed records?",
        "rows": len(csv_rows),
        "checked_fields": checked_fields,
        "max_absolute_error": max_abs,
        "max_relative_error": max_rel,
        "mismatch_count": len(mismatches),
        "first_mismatches": mismatches[:20],
        "projected_executed_max_abs": max(float(row["candidate_projected_executed_max_abs"]) for row in rows),
        "median_ratios": medians,
        "negative_control": negative_control,
        "decision": "PASS_EXTENSION_NUMERICALLY_REPRODUCIBLE" if not mismatches else "P1_EXTENSION_INVALID",
        "elapsed_seconds": round(time.time() - started, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["mismatch_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
