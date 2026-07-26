#!/usr/bin/env python3
"""Amend only the float32 physical-zero-sum audit in the sealed R278 result."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.icems_residual import (  # noqa: E402
    CONTROLLER,
    classify_icems_pilot,
    physical_zero_sum_tolerance,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)

ORIGINAL_SUMMARY = (
    ROOT
    / "results/r278_icems_residual_pilot_s49/"
    "icems_residual_pilot_summary.json"
)
ORIGINAL_SUMMARY_SHA256 = (
    "d0abf23e9d8fb6b69f98970272ed2a476b64f501b4270e0a3a4dc7097230e056"
)
ORIGINAL_PROVENANCE = (
    ROOT / "results/r278_icems_residual_pilot_s49/provenance.json"
)
ORIGINAL_PROVENANCE_SHA256 = (
    "042aac2a72c39fa876254654191a4ba6f9c24300c7bd8c66329c35837a40e9a4"
)
ORIGINAL_SEAL = ROOT / "memory/rounds/R278/pilot_seal.json"
ORIGINAL_SEAL_SHA256 = (
    "ef354927d1235614e0708f321b12bb4a1137b8dc18740bec3f11e37c085353d2"
)


def _load_object(path: Path, expected_sha256: str) -> dict[str, Any]:
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise ValueError(
            f"hash mismatch for {path}: expected {expected_sha256}, got {actual}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def _write_new(path: Path, payload: object) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact: {path}")
    data = canonical_json_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    digest = sha256_bytes(data)
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n",
        encoding="utf-8",
    )
    return digest


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def repair(output: Path) -> None:
    summary = _load_object(ORIGINAL_SUMMARY, ORIGINAL_SUMMARY_SHA256)
    _load_object(ORIGINAL_PROVENANCE, ORIGINAL_PROVENANCE_SHA256)
    _load_object(ORIGINAL_SEAL, ORIGINAL_SEAL_SHA256)
    if summary["decision"]["classification"] != "INVALID":
        raise ValueError("the frozen input is not the original INVALID result")
    original_guards = summary["decision"]["guards"]
    if not (
        original_guards["provenance_valid"]
        and original_guards["complete_24_pairs"]
        and original_guards["storage_guard_pass"]
        and original_guards["tail_guard_pass"]
        and not original_guards["action_guard_pass"]
    ):
        raise ValueError("original failure is not isolated to the action audit")

    tolerance = physical_zero_sum_tolerance()
    expected_tolerance = float(
        4 * np.spacing(np.float32(500.0))
    )
    if tolerance != expected_tolerance:
        raise ValueError("physical tolerance is not the registered four-ULP bound")

    for path_text, expected in summary["trace_hashes"].items():
        if sha256_file(ROOT / path_text) != expected:
            raise ValueError(f"trace hash drift: {path_text}")

    repaired_audits: dict[str, dict[str, bool]] = {}
    observed_by_scenario: dict[str, float] = {}
    for path_text in sorted(summary["trace_hashes"]):
        if not (
            path_text.startswith(
                "results/r278_icems_residual_pilot_s49/pilot_traces/"
            )
            and path_text.endswith(f"__{CONTROLLER}.json")
        ):
            continue
        record = json.loads((ROOT / path_text).read_text(encoding="utf-8"))
        scenario = str(record["scenario"])
        observed = max(
            abs(float(row["r278_physical_m_residual_sum"]))
            for row in record["traces"]
        )
        observed_by_scenario[scenario] = observed
        original = dict(summary["action_audits"][scenario])
        failed_names = {name for name, passed in original.items() if not passed}
        if failed_names != {"physical_zero_sum"}:
            raise ValueError(
                f"{scenario} had non-numerical action failures: {failed_names}"
            )
        original["physical_zero_sum"] = observed <= tolerance
        repaired_audits[scenario] = original

    if len(repaired_audits) != 24:
        raise ValueError(f"expected 24 candidate traces, got {len(repaired_audits)}")
    action_guard_pass = all(
        all(audit.values()) for audit in repaired_audits.values()
    )
    if not action_guard_pass:
        raise ValueError("four-ULP repair did not clear every physical sum audit")

    contrast = summary["paired_bootstrap"]["contrasts"][
        "candidate_minus_baseline"
    ]
    decision = classify_icems_pilot(
        primary_contrast=contrast,
        provenance_valid=True,
        complete_pairs=True,
        action_guard_pass=True,
        storage_guard_pass=True,
        tail_guard_pass=True,
    )
    if decision["classification"] != "PILOT-NO-GO":
        raise ValueError(
            "audit repair unexpectedly changed the registered result to "
            f"{decision['classification']}"
        )

    payload = {
        "schema_version": 1,
        "round": "R278",
        "amendment": "float32_physical_zero_sum_audit_only",
        "evidence_role": "viewed_development_only",
        "original_result": {
            "summary_path": str(ORIGINAL_SUMMARY),
            "summary_sha256": ORIGINAL_SUMMARY_SHA256,
            "provenance_path": str(ORIGINAL_PROVENANCE),
            "provenance_sha256": ORIGINAL_PROVENANCE_SHA256,
            "pilot_seal_path": str(ORIGINAL_SEAL),
            "pilot_seal_sha256": ORIGINAL_SEAL_SHA256,
            "classification": "INVALID",
        },
        "repair": {
            "reason": (
                "the old 1e-8 absolute threshold was below float32 "
                "representation precision at the 500-unit inertia scale"
            ),
            "physical_scale": 500.0,
            "device_count": 4,
            "float32_ulp_at_scale": float(np.spacing(np.float32(500.0))),
            "absolute_sum_tolerance": tolerance,
            "maximum_observed_abs_sum": max(observed_by_scenario.values()),
            "trajectory_or_bootstrap_changes": False,
            "retraining": False,
        },
        "decision": decision,
        "action_guard_pass": action_guard_pass,
        "repaired_action_audits": repaired_audits,
        "observed_abs_physical_sum_by_scenario": observed_by_scenario,
        "unchanged_primary_contrast": {
            endpoint: contrast["endpoints"][endpoint]
            for endpoint in (
                "normalized_sync_loss_hz2",
                "fast_inter_area_iae_hz_s",
            )
        },
        "source": {
            "path": str(Path(__file__).resolve()),
            "sha256": sha256_file(Path(__file__).resolve()),
            "repository_head": _git_head(),
            "command": " ".join(sys.argv),
        },
    }
    digest = _write_new(output, payload)
    print(
        f"[repaired] classification={decision['classification']} "
        f"max_abs_sum={max(observed_by_scenario.values()):.9g} "
        f"tolerance={tolerance:.9g} sha256={digest}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "memory/rounds/R278/analysis_repair.json",
    )
    args = parser.parse_args()
    repair(args.output)


if __name__ == "__main__":
    main()
