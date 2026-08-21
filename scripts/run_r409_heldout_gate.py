"""Sealed WSL runner for R409: held-out gate for the R408 Q-ENTRY arm.

The R408 plan's pre-registered decision tree required a separately
registered held-out gate before any title-supporting use of the found
candidate (0.4 Hz ring-edge bandpass at K=3.5).  This runner executes the
frozen candidate on the R379 evaluation (held-out) bank - the unseen
probe/disturbance scenarios (PQ_0 / bus15, seed 42, 0.2 s x 50 steps) -
with arms zero / local / bandpass_k3p5, the same frozen estimators and
thresholds (r_d <= 0.95, r_cross <= 1.10) and all guards.

Any endpoint or guard failing returns HELDOUT-FAIL without retry or tuning.
No held-out bank is used anywhere else in this repository.

--rehearse exercises the same pre-attempt verification path on one held-out
bandpass_k3p5 trajectory without creating formal artifacts.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO

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
    summarize_arm_records,
)
from scripts.run_r408_v2_solving_gate import (  # noqa: E402
    _make_controller,
    _run_job,
)

ROUND_ID = "R409"
OUT = ROOT / "results/research_loop/r409_heldout_gate"
CANDIDATE_ARM = "bandpass_k3p5"
EVAL_ARMS = (ZERO_ARM, LOCAL_ARM, CANDIDATE_ARM)
DIFFERENTIAL_RATIO_MAX = 0.95
PROBE_CROSS_RATIO_MAX = 1.10
STRICT_CROSS_RATIO_MAX = 0.95
PARALLEL_WORKERS = 8


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


def build_contract() -> dict[str, Any]:
    contract = _base_contract()
    contract["round"] = ROUND_ID
    contract["evaluation"]["arm_ids"] = list(EVAL_ARMS)
    contract["evaluation"]["record_count"] = (
        len(EVAL_ARMS) * (len(contract["probe_arm_ids"]) + 2)
    )
    contract["training_authorized"] = False
    return contract


def evaluation_jobs(*, contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Expand the frozen held-out bank: 8 paired probes + 2 disturbances/arm."""
    phase = contract["evaluation"]
    jobs: list[dict[str, Any]] = []
    for arm_id in phase["arm_ids"]:
        for input_mode in contract["mode_ids"]:
            for sign in ("positive", "negative"):
                jobs.append({
                    "order": len(jobs),
                    "phase": "evaluation",
                    "arm_id": arm_id,
                    "experiment_kind": "probe",
                    "condition_id": phase["probe_condition"]["condition_id"],
                    "delta_u": dict(phase["probe_condition"]["delta_u"]),
                    "input_mode": input_mode,
                    "sign": sign,
                })
        for condition in phase["disturbance_conditions"]:
            jobs.append({
                "order": len(jobs),
                "phase": "evaluation",
                "arm_id": arm_id,
                "experiment_kind": "disturbance",
                "condition_id": condition["condition_id"],
                "delta_u": dict(condition["delta_u"]),
                "input_mode": None,
                "sign": None,
            })
    if len(jobs) != int(phase["record_count"]):
        raise RuntimeError("expanded held-out jobs do not match the frozen count")
    return jobs


def _expected_identity(contract: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "n_agents": int(contract["device_count"]),
        "vsg_idx": list(contract["expected_vsg_idx"]),
        "vsg_buses": list(contract["expected_vsg_buses"]),
    }


def arm_check(arm_id: str) -> dict[str, Any]:
    contract = build_contract()
    jobs = [job for job in evaluation_jobs(contract=contract) if job["arm_id"] == arm_id]
    records = [_run_job(job, contract=contract) for job in jobs]
    for record in records:
        if dict(record.get("identity", {})) != _expected_identity(contract):
            raise ValueError(f"{arm_id}: VSG identity drift")
    summary = summarize_arm_records(records, contract=contract)
    return {
        "arm_id": arm_id,
        "record_count": len(records),
        "summary": summary,
    }


def heldout_decision(results: list[dict[str, Any]]) -> dict[str, Any]:
    local = next(r for r in results if r["arm_id"] == LOCAL_ARM)
    candidate = next(r for r in results if r["arm_id"] == CANDIDATE_ARM)
    local_diff = float(local["summary"]["disturbance"]["mean_differential_frequency_energy_hz2_s"])
    local_off = float(local["summary"]["probe"]["off_diagonal_response_energy_hz2_s"])
    diff_ratio = (
        float(candidate["summary"]["disturbance"]["mean_differential_frequency_energy_hz2_s"])
        / local_diff
        if local_diff > 0.0
        else float("inf")
    )
    cross_ratio = (
        float(candidate["summary"]["probe"]["off_diagonal_response_energy_hz2_s"]) / local_off
        if local_off > 0.0
        else float("inf")
    )
    guards_pass = bool(candidate["summary"]["guards_pass"])
    passed = bool(
        diff_ratio <= DIFFERENTIAL_RATIO_MAX
        and cross_ratio <= PROBE_CROSS_RATIO_MAX
        and guards_pass
    )
    return {
        "classification": "HELDOUT-PASS" if passed else "HELDOUT-FAIL",
        "found_arm": CANDIDATE_ARM,
        "differential_ratio": diff_ratio,
        "probe_cross_ratio": cross_ratio,
        "strict_cross_pass": bool(cross_ratio <= STRICT_CROSS_RATIO_MAX),
        "guards_pass": guards_pass,
        "guard_errors": list(candidate["summary"]["guard_errors"]),
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
            "r408_runner": _sha256_file(
                ROOT / "scripts/run_r408_v2_solving_gate.py"
            ),
            "classifier": _sha256_file(
                ROOT / "src/andes_rl_kundur/evaluation/gate_b3_deterministic.py"
            ),
        },
    }


def _capacity_job(_job_id: int) -> dict[str, Any]:
    contract = build_contract()
    job = [j for j in evaluation_jobs(contract=contract) if j["arm_id"] == CANDIDATE_ARM][0]
    record = _run_job(job, contract=contract)
    return {"ok": bool(record["completed_steps"] > 0)}


def measure_capacity() -> str:
    payload = {"rungs": []}
    for workers in (1, 2, 4, 8):
        start = time.monotonic()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_capacity_job, range(workers)))
        wall = time.monotonic() - start
        payload["rungs"].append({
            "workers": workers,
            "jobs": len(results),
            "wall_seconds": round(wall, 3),
            "throughput_jobs_per_second": round(len(results) / max(wall, 1e-9), 4),
            "all_ok": all(result["ok"] for result in results),
        })
    return json.dumps(payload, indent=2, sort_keys=True)


def rehearse() -> str:
    checks = _pre_attempt_checks()
    contract = build_contract()
    job = [j for j in evaluation_jobs(contract=contract) if j["arm_id"] == CANDIDATE_ARM][0]
    record = _run_job(job, contract=contract)
    return json.dumps({
        "rehearsal": True,
        "pre_attempt": {
            "contract_round": checks["contract_round"],
            "output_absence": checks["output_absence"],
        },
        "scenario": {
            "rows": int(len(record.get("steps", []))),
            "tds_failed": bool(record.get("tds_failed")),
            "identity_ok": bool(record.get("identity") is not None),
        },
    }, indent=2, sort_keys=True)


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
            "evaluation_arms": list(EVAL_ARMS),
            "candidate_arm": CANDIDATE_ARM,
            "thresholds": {
                "differential_ratio_max": DIFFERENTIAL_RATIO_MAX,
                "probe_cross_ratio_max": PROBE_CROSS_RATIO_MAX,
                "strict_cross_ratio_max": STRICT_CROSS_RATIO_MAX,
            },
            "training_authorized": False,
            "held_out_accessed": True,
        },
    )
    entries = [{"path": _relative(OUT / "formal_attempt.json"), "sha256": attempt_digest}]
    with ProcessPoolExecutor(max_workers=PARALLEL_WORKERS) as pool:
        results = list(pool.map(arm_check, EVAL_ARMS))
    decision = heldout_decision(results)
    execution_digest = _write_new_json(
        OUT / "formal_execution.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "attempt_sha256": attempt_digest,
            "arms": results,
        },
    )
    entries.append({"path": _relative(OUT / "formal_execution.json"), "sha256": execution_digest})
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "attempt_sha256": attempt_digest,
        "execution_sha256": execution_digest,
        "classification": decision["classification"],
        "candidate_arm": decision["found_arm"],
        "differential_ratio": decision["differential_ratio"],
        "probe_cross_ratio": decision["probe_cross_ratio"],
        "strict_cross_pass": decision["strict_cross_pass"],
        "guards_pass": decision["guards_pass"],
        "guard_errors": decision["guard_errors"],
        "training_authorized": False,
        "held_out_accessed": True,
        "next_gate": "none; held-out gate is terminal for the R408 candidate",
    }
    analysis_digest = _write_new_json(OUT / "formal_analysis.json", analysis)
    entries.append({"path": _relative(OUT / "formal_analysis.json"), "sha256": analysis_digest})
    _write_new_json(
        OUT / "formal_manifest.json",
        {"schema_version": 1, "round": ROUND_ID, "entries": entries},
    )
    return json.dumps(decision, indent=2, sort_keys=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--rehearse", action="store_true")
    group.add_argument("--measure-capacity", action="store_true")
    group.add_argument("--execute", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.rehearse:
        safe_emit(rehearse())
        return 0
    if args.measure_capacity:
        payload = json.loads(measure_capacity())
        out = ROOT / "memory/rounds/R409/capacity_evidence.json"
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        safe_emit(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    safe_emit(execute())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
