"""R408 P6 telemetry supplement: per-arm zero-sum leak diagnostics.

The R408 formal execution archived arm-level ratios and guards (frozen
estimator) but its sigma_v/sigma_p telemetry aggregates over all three arms
of each bank (zero/local/candidate), so the leak numbers were dominated by
the local arm's common PI action and are unusable for the P6 mechanism
question.  This supplement re-runs ONLY the disturbance trajectories of the
Stage-A bandpass arms (plus zero/local and K=2 for reference) and computes
per-arm:

  sigma_v_l2        L2 norm of 1^T * normalized_command over all steps
  sigma_p_l2        L2 norm of 1^T * (feasible - zero_anchor) over all steps
  sigma_p_l2_over_K sigma_p_l2 / K for K > 0

This is a diagnostic supplement, NOT a formal re-attempt: the R408 formal
decision (Q-ENTRY at bandpass_k3p5) is unaffected.  Output is create-only
with .sha256 sidecars under results/research_loop/r408_v2_solving_gate_telemetry_supplement/.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import numpy as np  # noqa: E402

from scripts.run_r408_v2_solving_gate import (  # noqa: E402
    K_GRID_STAGE_A,
    LOCAL_ARM,
    ZERO_ARM,
    _run_job,
    bandpass_arm_id,
    build_contract,
    phase_jobs,
)

OUT = ROOT / "results/research_loop/r408_v2_solving_gate_telemetry_supplement"

EXTRA_ARMS = ("bandpass_k2", "bandpass_k3p5", "bandpass_k4")


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
        raise FileExistsError(f"artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(f"{digest}\n", encoding="utf-8")
    return digest


def _disturbance_records(arm_id: str) -> list[dict[str, Any]]:
    contract = build_contract(arm_id)
    return [
        _run_job(job, contract=contract)
        for job in phase_jobs("development", contract=contract)
        if job["experiment_kind"] == "disturbance" and job["arm_id"] == arm_id
    ]


def _leak_l2(records: Sequence[Mapping[str, Any]], key: str) -> float:
    values: list[float] = []
    for record in records:
        if record["experiment_kind"] != "disturbance":
            continue
        for row in record.get("steps", []):
            values.append(float(row["zero_sum_telemetry"][key]))
    return float(np.sqrt(np.sum(np.square(values)))) if values else float("nan")


def arm_leak(arm_id: str) -> dict[str, Any]:
    records = _disturbance_records(arm_id)
    sigma_v = _leak_l2(records, "sigma_v")
    sigma_p = _leak_l2(records, "sigma_p")
    sigma_d = _leak_l2(records, "sigma_distortion")
    payload: dict[str, Any] = {
        "arm_id": arm_id,
        "disturbance_record_count": len(records),
        "sigma_v_l2": sigma_v,
        "sigma_p_l2": sigma_p,
        "sigma_distortion_l2": sigma_d,
    }
    if arm_id.startswith("bandpass_k"):
        k = float(arm_id[len("bandpass_k"):].replace("p", "."))
        payload["k"] = k
        if k > 0.0:
            payload["sigma_p_l2_over_K"] = sigma_p / k
    return payload


def main() -> int:
    arm_ids = [
        ZERO_ARM,
        LOCAL_ARM,
        *[bandpass_arm_id(k) for k in K_GRID_STAGE_A],
        *EXTRA_ARMS,
    ]
    results = [arm_leak(arm_id) for arm_id in arm_ids]
    if OUT.exists():
        raise FileExistsError(f"supplement root already exists: {OUT}")
    payload = {
        "schema_version": 1,
        "round": "R408",
        "purpose": "diagnostic-supplement (P6 per-arm zero-sum leak)",
        "formal_decision_affected": False,
        "arms": results,
    }
    digest = _write_new_json(OUT / "telemetry.json", payload)
    _write_new_json(
        OUT / "manifest.json",
        {
            "schema_version": 1,
            "round": "R408",
            "purpose": "diagnostic-supplement",
            "entries": [
                {"path": _relative(OUT / "telemetry.json"), "sha256": digest}
            ],
        },
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
