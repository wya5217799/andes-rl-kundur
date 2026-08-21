"""R411 derived view: per-amplitude message contrast ladder (probe).

Plan-registered execution amendment for R411 (R410 endpoint-table
precedent): the frozen canary classifier returns CANARY-FAIL without its
``canary`` payload, so the message-minus-comparator improvements are not
part of ``formal_analysis.json``.  This probe reads the sealed R411
evaluation records read-only and recomputes, per amplitude factor, the
message arm's three-seed-median improvement over the matched no-message arm
and the scalar arm (the same arithmetic as
``cd_matd3_canary.classify_canary``), plus the two-of-three seed counts.

The output is a create-only hashed JSON under the R411 results root and is
a derived view of the sealed records; it does not change the frozen
classifier, thresholds, or classification.

Usage (WSL, through the scratch launcher):
  python scripts/andes_scratch.py probes/r411_message_contrast_ladder.py
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import run_r411_probe_amplitude_ladder as runner  # noqa: E402
from andes_rl_kundur.evaluation.md_decoupling_headroom import (  # noqa: E402
    summarise_profile,
)

OUT = ROOT / "results/research_loop/r411_probe_amplitude_ladder"

_ENDPOINTS = (
    "off_diagonal_response_energy",
    "disturbance_differential_energy",
)


def _summaries(factor: float) -> list[dict[str, Any]]:
    key = runner.amplitude_key(factor)
    summaries = []
    for arm_id, seed in runner._arm_seed_pairs():
        for profile_id in runner.evaluation_profiles():
            path = runner._block_path(arm_id, seed, key, profile_id)
            payload = runner._read_hashed_json(path)
            summary = summarise_profile(
                payload["records"], contract=runner.scaled_contract(factor)
            )
            summary["profile_id"] = profile_id
            summary["arm_id"] = arm_id
            summary["training_seed"] = None if seed is None else int(seed)
            summaries.append(summary)
    return summaries


def _arm_endpoints(
    summaries: Sequence[Mapping[str, Any]], arm_id: str, seed: int | None
) -> dict[str, float]:
    rows = [
        row
        for row in summaries
        if row["arm_id"] == arm_id
        and (row["training_seed"] is None) == (seed is None)
        and (seed is None or row["training_seed"] == seed)
    ]
    return {
        endpoint: float(
            sum(float(row[endpoint]) for row in rows)
        )
        for endpoint in _ENDPOINTS
    }


def _contrast(factor: float) -> dict[str, Any]:
    contract = runner._frozen_contract()
    summaries = _summaries(factor)
    full_arm = str(contract["learning_arm_ids"][2])
    comparators = [str(value) for value in contract["learning_arm_ids"][:2]]
    seeds = [int(seed) for seed in contract["training_seeds"]]
    payload: dict[str, Any] = {}
    per_seed: dict[str, dict[str, float]] = {
        f"{arm_id}|{seed}": _arm_endpoints(summaries, arm_id, seed)
        for arm_id in contract["learning_arm_ids"]
        for seed in seeds
    }
    medians = {
        str(arm_id): {
            endpoint: float(
                np.median(
                    [per_seed[f"{arm_id}|{seed}"][endpoint] for seed in seeds]
                )
            )
            for endpoint in _ENDPOINTS
        }
        for arm_id in contract["learning_arm_ids"]
    }
    for comparator in comparators:
        per_endpoint: dict[str, dict[str, float]] = {e: {} for e in _ENDPOINTS}
        for seed in seeds:
            base = per_seed[f"{comparator}|{seed}"]
            full = per_seed[f"{full_arm}|{seed}"]
            for endpoint in _ENDPOINTS:
                per_endpoint[endpoint][seed] = (
                    base[endpoint] - full[endpoint]
                ) / base[endpoint]
        payload[comparator] = {
            # R410 endpoint-table formula verbatim: per-arm three-seed
            # medians first, then the improvement ratio.
            "median_improvement": {
                endpoint: float(
                    (
                        medians[comparator][endpoint]
                        - medians[full_arm][endpoint]
                    )
                    / medians[comparator][endpoint]
                )
                for endpoint in _ENDPOINTS
            },
            "seed_values": {
                str(seed): {
                    endpoint: per_endpoint[endpoint][seed]
                    for endpoint in _ENDPOINTS
                }
                for seed in seeds
            },
            "two_of_three": {
                endpoint: sum(
                    1 for seed in seeds if per_endpoint[endpoint][seed] > 0.0
                )
                >= 2
                for endpoint in _ENDPOINTS
            },
        }
    return payload


def main() -> int:
    table = {
        runner.amplitude_key(factor): {
            "amplitude_factor": float(factor),
            "contrast": _contrast(factor),
        }
        for factor in runner.AMPLITUDE_FACTORS
    }
    sign_stability = {}
    for comparator in ("cd_matd3_no_message", "yang_scalar_td3"):
        for endpoint in _ENDPOINTS:
            values = [
                float(
                    table[key]["contrast"][comparator]["median_improvement"][
                        endpoint
                    ]
                )
                for key in table
            ]
            sign_stability[f"{comparator}|{endpoint}"] = {
                "median_improvements": values,
                "negative_sign_stable": all(value < 0.0 for value in values),
                "two_of_three_stable": all(
                    bool(
                        table[key]["contrast"][comparator]["two_of_three"][
                            endpoint
                        ]
                    )
                    for key in table
                ),
            }
    payload = {
        "schema_version": 1,
        "round": "R411",
        "role": "derived_view_of_sealed_records_no_classifier_change",
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": runner._sha256_file(runner.SEAL),
        "amplitudes": table,
        "sign_stability": sign_stability,
    }
    digest = runner._write_new_json(OUT / "message_contrast_ladder.json", payload)
    print(f"R411 message contrast ladder: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
