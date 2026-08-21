"""Sealed WSL runner for R406: frozen alpha line-sweep on the first-order family.

Loops the frozen alpha grid {0.675, 0.625, 0.65, 0.70, 0.725, 0.75, 0.80,
0.85} over the R376-R379 first-order high-pass mutual-damping family on the
same 60-record development bank with the same estimators.  Any candidate at
any grid point passing both frozen endpoint thresholds (differential ratio
<= 0.95, probe-cross ratio <= 1.10) and every guard returns
SWEEP-FOUND-CANDIDATE; otherwise SWEEP-NO-CANDIDATE.  No held-out access,
no training, no grid/gain/order change.

--rehearse exercises the same pre-attempt verification path on alpha 0.675
without creating formal artifacts.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Mapping, TextIO

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.evaluation.gate_b3_deterministic import (  # noqa: E402
    LOCAL_ARM,
    ZERO_ARM,
    build_contract as _base_contract,
    phase_jobs,
    summarize_phase_records,
)
from scripts.run_r379_gate_b3_deterministic import _run_job  # noqa: E402

ROUND_ID = "R406"
PLAN = ROOT / "memory/rounds/R406/plan.md"
SEAL = ROOT / "memory/rounds/R406/formal_seal.json"
OUT = ROOT / "results/research_loop/r406_alpha_sweep"

ALPHA_GRID = (0.675, 0.625, 0.65, 0.70, 0.725, 0.75, 0.80, 0.85)
DIFFERENTIAL_RATIO_MAX = 0.95
PROBE_CROSS_RATIO_MAX = 1.10


def sweep_contract(alpha: float) -> dict[str, Any]:
    contract = _base_contract()
    alpha_f = float(alpha)
    contract["highpass_alpha"] = alpha_f
    # controller_spec reads the per-candidate highpass_alpha, so every
    # distributed candidate must carry the grid point (the R406-pre-repair
    # bug overrode only the inert top-level field).
    for candidate in contract["distributed_candidates"]:
        candidate["highpass_alpha"] = alpha_f
    contract["round"] = ROUND_ID
    return contract


def _local_summaries(phase: Mapping[str, Any]) -> tuple[float, float]:
    local = phase["arm_summaries"][LOCAL_ARM]
    diff = float(local["disturbance"]["mean_differential_frequency_energy_hz2_s"])
    off = float(local["probe"]["off_diagonal_response_energy_hz2_s"])
    return diff, off


def alpha_check(alpha: float) -> dict[str, Any]:
    """Run the development phase at one alpha and check every damping arm."""
    contract = sweep_contract(alpha)
    if not all(
        float(c.get("highpass_alpha")) == float(alpha)
        for c in contract["distributed_candidates"]
    ):
        raise ValueError("alpha grid point did not propagate into candidates")
    records = [
        _run_job(job, contract=contract)
        for job in phase_jobs("development", contract=contract)
    ]
    phase = summarize_phase_records(records, phase="development", contract=contract)
    local_diff, local_off = _local_summaries(phase)
    arm_results = []
    any_pass = False
    for arm_id, summary in phase["arm_summaries"].items():
        if arm_id in (ZERO_ARM, LOCAL_ARM):
            continue
        diff_ratio = (
            float(summary["disturbance"]["mean_differential_frequency_energy_hz2_s"])
            / local_diff
            if local_diff > 0.0
            else float("inf")
        )
        cross_ratio = (
            float(summary["probe"]["off_diagonal_response_energy_hz2_s"])
            / local_off
            if local_off > 0.0
            else float("inf")
        )
        passed = bool(
            diff_ratio <= DIFFERENTIAL_RATIO_MAX
            and cross_ratio <= PROBE_CROSS_RATIO_MAX
            and summary["guards_pass"]
        )
        any_pass = any_pass or passed
        arm_results.append(
            {
                "arm_id": arm_id,
                "differential_ratio": diff_ratio,
                "probe_cross_ratio": cross_ratio,
                "guards_pass": bool(summary["guards_pass"]),
                "guard_errors": list(summary["guard_errors"]),
                "passed": passed,
            }
        )
    return {
        "alpha": float(alpha),
        "record_count": len(records),
        "any_pass": any_pass,
        "arm_results": arm_results,
    }


def _pre_attempt_checks() -> dict[str, Any]:
    import andes

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    return {
        "contract_round": ROUND_ID,
        "output_absence": not OUT.exists(),
        "installed_runtime": {
            "python": sys.version,
            "andes_version": str(getattr(andes, "__version__", "unknown")),
            "case_path": str(case_path),
            "case_sha256": _sha256_file(case_path),
        },
        "source_manifest": {
            "runner": _sha256_file(Path(__file__).resolve()),
            "classifier": _sha256_file(
                ROOT / "src/andes_rl_kundur/evaluation/gate_b3_deterministic.py"
            ),
            "controller": _sha256_file(
                ROOT / "src/andes_rl_kundur/control/feasibility_native_deterministic.py"
            ),
        },
    }


def safe_emit(message: str, *, stream: TextIO | None = None) -> bool:
    target = sys.stdout if stream is None else stream
    try:
        print(message, file=target, flush=True)
    except BrokenPipeError:
        return False
    return True


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> str:
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(f"formal artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(f"{digest}\n", encoding="utf-8")
    return digest


def sweep_decision(
    grid_results: list[dict[str, Any]],
    *,
    differential_ratio_max: float = DIFFERENTIAL_RATIO_MAX,
    probe_cross_ratio_max: float = PROBE_CROSS_RATIO_MAX,
) -> dict[str, Any]:
    """Pure sweep decision: FOUND if any alpha has any passing arm."""
    found = None
    for result in grid_results:
        if not result.get("any_pass"):
            continue
        for arm in result.get("arm_results", []):
            if bool(arm.get("passed")):
                found = {"alpha": result["alpha"], "arm_id": arm["arm_id"]}
                break
        if found:
            break
    return {
        "classification": (
            "SWEEP-FOUND-CANDIDATE" if found else "SWEEP-NO-CANDIDATE"
        ),
        "found_candidate": found,
    }


def rehearse() -> str:
    checks = _pre_attempt_checks()
    alpha = ALPHA_GRID[0]
    contract = sweep_contract(alpha)
    job = phase_jobs("development", contract=contract)[0]
    record = _run_job(job, contract=contract)
    payload = {
        "rehearsal": True,
        "alpha": alpha,
        "pre_attempt": {
            "contract_round": checks["contract_round"],
            "output_absence": checks["output_absence"],
        },
        "scenario": {
            "rows": int(len(record.get("steps", []))),
            "tds_failed": bool(record.get("tds_failed")),
            "identity_ok": bool(record.get("identity") is not None),
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def execute() -> str:
    checks = _pre_attempt_checks()
    if not checks["output_absence"]:
        raise FileExistsError("formal output root already exists")
    attempt_digest = _write_new_json(
        OUT / "formal_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "pre_attempt": checks,
            "alpha_grid": list(ALPHA_GRID),
            "thresholds": {
                "differential_ratio_max": DIFFERENTIAL_RATIO_MAX,
                "probe_cross_ratio_max": PROBE_CROSS_RATIO_MAX,
            },
            "training_authorized": False,
            "held_out_accessed": False,
        },
    )
    entries = [
        {"path": _relative(OUT / "formal_attempt.json"), "sha256": attempt_digest}
    ]
    grid_results = [alpha_check(alpha) for alpha in ALPHA_GRID]
    decision = sweep_decision(grid_results)
    found = decision["found_candidate"]
    classification = decision["classification"]
    execution_digest = _write_new_json(
        OUT / "formal_execution.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "attempt_sha256": attempt_digest,
            "grid_results": [
                {
                    "alpha": r["alpha"],
                    "record_count": r["record_count"],
                    "arm_results": r["arm_results"],
                }
                for r in grid_results
            ],
        },
    )
    entries.append(
        {"path": _relative(OUT / "formal_execution.json"), "sha256": execution_digest}
    )
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "attempt_sha256": attempt_digest,
        "execution_sha256": execution_digest,
        "classification": classification,
        "found_candidate": found,
        "alpha_grid": list(ALPHA_GRID),
        "training_authorized": False,
        "held_out_accessed": False,
        "next_gate": (
            "separately registered held-out gate for the found candidate"
            if found
            else "none; first-order family closed within the frozen grid"
        ),
    }
    analysis_digest = _write_new_json(OUT / "formal_analysis.json", analysis)
    entries.append(
        {"path": _relative(OUT / "formal_analysis.json"), "sha256": analysis_digest}
    )
    _write_new_json(
        OUT / "formal_manifest.json",
        {"schema_version": 1, "round": ROUND_ID, "entries": entries},
    )
    return json.dumps(
        {
            "classification": classification,
            "found_candidate": found,
            "per_alpha_passes": [
                r["alpha"] for r in grid_results if r["any_pass"]
            ],
        },
        indent=2,
        sort_keys=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--rehearse", action="store_true")
    group.add_argument("--execute", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.rehearse:
        safe_emit(rehearse())
        return 0
    safe_emit(execute())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
