"""Tabulate the sealed R402 canary bank for the feed endpoint table.

The pre-registered classifier already returned CANARY-FAIL on the no-harm
guards (formal_analysis.json).  This probe only tabulates the same bank:
per-arm-seed aggregate endpoints over the four evaluation profiles, the
three-seed medians, improvement ratios versus each comparator and versus the
deterministic reference, and the worst guard ratios per arm-seed.  It does
not change the classification; its output is the feed source for the
headline numbers.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import numpy as np

from andes_rl_kundur.evaluation.md_decoupling_headroom import summarise_profile
from andes_rl_kundur.evaluation.cd_matd3_canary import build_contract

OUT = ROOT / "results/research_loop/r402_cd_matd3_canary"
OUTPUT = OUT / "endpoint_table.json"


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError("endpoint table exists")
    contract = build_contract()
    evaluation = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "evaluation"
    ]
    profiles = [str(p["profile_id"]) for p in evaluation]
    endpoints = ("off_diagonal_response_energy", "disturbance_differential_energy")

    def summary(arm_id, seed):
        rows = {}
        for profile_id in profiles:
            suffix = "deterministic" if seed is None else f"seed{seed}"
            path = OUT / "eval" / arm_id / suffix / f"{profile_id}.json"
            payload = _read_json(path)
            row = summarise_profile(payload["records"], contract=contract)
            rows[profile_id] = row
        return rows

    def aggregate(arm_id, seed):
        rows = summary(arm_id, seed)
        return {
            endpoint: sum(float(rows[p][endpoint]) for p in profiles)
            for endpoint in endpoints
        }

    det_arm = str(contract["deterministic_arm_id"])
    det_rows = summary(det_arm, None)
    det_agg = aggregate(det_arm, None)
    arms = [str(a) for a in contract["learning_arm_ids"]]
    seeds = [int(s) for s in contract["training_seeds"]]

    per_seed = {}
    worst_guard = {}
    for arm_id in arms:
        for seed in seeds:
            per_seed[(arm_id, seed)] = aggregate(arm_id, seed)
            ratios = {"common_iae": [], "worst_peak": [], "rocof": [],
                      "action_rms": [], "action_tv": [], "saturation": []}
            rows = summary(arm_id, seed)
            for p in profiles:
                det = det_rows[p]
                row = rows[p]
                ratios["common_iae"].append(
                    float(row["common_frequency_iae_hz_s"])
                    / float(det["common_frequency_iae_hz_s"]))
                ratios["worst_peak"].append(
                    float(row["worst_unit_peak_hz"])
                    / float(det["worst_unit_peak_hz"]))
                ratios["rocof"].append(
                    float(row["worst_rocof_hz_s"])
                    / float(det["worst_rocof_hz_s"]))
                ratios["action_rms"].append(
                    float(row["action_rms"]) / float(det["action_rms"]))
                ratios["action_tv"].append(
                    float(row["action_total_variation"])
                    / float(det["action_total_variation"]))
                ratios["saturation"].append(
                    float(row["action_saturation_fraction"]))
            worst_guard[(arm_id, seed)] = {
                name: float(np.max(values)) for name, values in ratios.items()
            }

    def median(arm_id):
        return {
            endpoint: float(np.median(
                [per_seed[(arm_id, seed)][endpoint] for seed in seeds]
            ))
            for endpoint in endpoints
        }

    medians = {arm_id: median(arm_id) for arm_id in arms}
    full = arms[2]
    improvements = {}
    for comparator in arms[:2]:
        improvements[comparator] = {
            endpoint: float(
                (medians[comparator][endpoint] - medians[full][endpoint])
                / medians[comparator][endpoint]
            )
            for endpoint in endpoints
        }
    versus_deterministic = {
        arm_id: {
            endpoint: float(
                medians[arm_id][endpoint] / det_agg[endpoint]
            )
            for endpoint in endpoints
        }
        for arm_id in arms
    }

    payload = {
        "schema_version": 1,
        "round": "R402",
        "manuscript_line": str(contract["manuscript_line"]),
        "classification_authority": (
            "formal_analysis.json (CANARY-FAIL, pre-registered classifier)"
        ),
        "deterministic_aggregate": det_agg,
        "deterministic_profile_summaries": {
            p: {
                "common_frequency_iae_hz_s": float(
                    det_rows[p]["common_frequency_iae_hz_s"]),
                "worst_unit_peak_hz": float(
                    det_rows[p]["worst_unit_peak_hz"]),
                "worst_rocof_hz_s": float(
                    det_rows[p]["worst_rocof_hz_s"]),
                "action_rms": float(det_rows[p]["action_rms"]),
                "action_total_variation": float(
                    det_rows[p]["action_total_variation"]),
            }
            for p in profiles
        },
        "per_seed_aggregates": {
            f"{arm_id}_s{seed}": per_seed[(arm_id, seed)]
            for arm_id in arms
            for seed in seeds
        },
        "seed_medians": medians,
        "full_method_improvement_vs_comparators": improvements,
        "median_endpoint_ratio_vs_deterministic": versus_deterministic,
        "worst_guard_ratios_vs_deterministic": {
            f"{arm_id}_s{seed}": worst_guard[(arm_id, seed)]
            for arm_id in arms
            for seed in seeds
        },
    }
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    digest = _sha256_file(OUTPUT)
    Path(f"{OUTPUT}.sha256").write_text(
        f"{digest}  {OUTPUT.name}\n", encoding="ascii"
    )
    print(f"endpoint table: {digest}")


if __name__ == "__main__":
    main()
