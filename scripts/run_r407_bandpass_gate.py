"""Sealed WSL runner for the B round: 0.4 Hz ring-edge bandpass gate.

Tests the owner-approved candidate-B bandpass (route_decision_bandpass_b_2026-08-16.md)
on the paralleled line's feasibility-native energy ports: second-order
positive-real bandpass F(s) = K * 2*zeta*wm*s / (s^2 + 2*zeta*wm*s + wm^2),
wm = 2*pi*0.4, zeta = 0.35 frozen, bilinear with 0.4 Hz gain correction,
acting on ring-edge frequency differences (strictly transparent to common
frequency).  Only the gain K is searched over the frozen grid
{0.10, 0.25, 0.50, 1.00, 2.00} on the R379 development bank with the R379
estimators and thresholds (differential <= 0.95, probe cross <= 1.10).

Any K passing both thresholds and every guard returns BAND-PASS; otherwise
BAND-FAIL.  No held-out access, no training, no M/D path re-enable.
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

from andes_rl_kundur.control.active_power import (  # noqa: E402
    r272_frozen_bess_contract,
)
from andes_rl_kundur.control.feasibility_native_deterministic import (  # noqa: E402
    FeasibilityNativeLocalController,
)
from andes_rl_kundur.control.feasibility_native_vsg_action import (  # noqa: E402
    FeasibilityNativeVSGActionMap,
)
from andes_rl_kundur.control.ring_bandpass_damping import RingBandpassDamping
from andes_rl_kundur.evaluation.gate_b3_deterministic import (  # noqa: E402
    LOCAL_ARM,
    ZERO_ARM,
    build_contract as _base_contract,
    controller_spec,
    phase_jobs,
    probe_request,
    summarize_phase_records,
)
from scripts.run_r372_energy_port_object_gate import (  # noqa: E402
    _identity,
    _port_row,
)

ROUND_ID = "R407"
OUT = ROOT / "results/research_loop/r407_bandpass_gate"

K_GRID = (0.10, 0.25, 0.50, 1.00, 2.00)
PARALLEL_WORKERS = 8
F0_HZ = 0.4
ZETA = 0.35
ACTION_CLIP = 0.70
DIFFERENTIAL_RATIO_MAX = 0.95
PROBE_CROSS_RATIO_MAX = 1.10


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
    contract["bandpass"] = {
        "f0_hz": F0_HZ,
        "zeta": ZETA,
        "controller_action_clip": ACTION_CLIP,
    }
    contract["k_grid"] = [float(k) for k in K_GRID]
    contract["training_authorized"] = False
    return contract


def k_contract(k: float) -> dict[str, Any]:
    contract = build_contract()
    arm_id = bandpass_arm_id(k)
    contract["bandpass_k"] = float(k)
    contract["development"] = dict(contract["development"])
    contract["development"]["arm_ids"] = [
        ZERO_ARM,
        LOCAL_ARM,
        arm_id,
    ]
    # The frozen job-expansion check derives the expected record count from
    # the arm list, so it must be overridden together with the arms.
    contract["development"]["record_count"] = len(
        contract["development"]["arm_ids"]
    ) * (len(contract["probe_arm_ids"]) + 2)
    return contract


def bandpass_arm_id(k: float) -> str:
    # Repo arm-id convention (R379): p-notation for the decimal point.
    return f"bandpass_k{str(k).replace('.', 'p')}"


class BandpassArmController:
    """Adapter: R379 act(frequencies_hz, dt) -> normalized zero-sum actions."""

    def __init__(self, *, k: float, nominal_frequency_hz: float) -> None:
        self._bandpass = RingBandpassDamping(
            n=4, dt=0.2, f0_hz=F0_HZ, zeta=ZETA, gain=k
        )
        self._nominal = float(nominal_frequency_hz)

    def act(self, frequencies_hz: Sequence[float], dt_seconds: float) -> np.ndarray:
        frequencies = np.asarray(frequencies_hz, dtype=float)
        deviations = frequencies - self._nominal
        command = self._bandpass.step(deviations)
        return np.clip(command, -ACTION_CLIP, ACTION_CLIP)


def bandpass_arm_controller(
    arm_id: str, *, contract: Mapping[str, Any]
) -> BandpassArmController:
    # Parse the K from the arm id itself so the adapter never depends on a
    # separate contract field drifting out of sync with the arm registry.
    prefix = "bandpass_k"
    if not arm_id.startswith(prefix):
        raise ValueError(f"not a bandpass arm: {arm_id}")
    k = float(arm_id[len(prefix):].replace("p", "."))
    return BandpassArmController(k=k, nominal_frequency_hz=60.0)


def bandpass_decision(grid_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Pure decision: first K whose arm passes -> BAND-PASS, else BAND-FAIL."""
    found = None
    for result in grid_results:
        if not result.get("any_pass"):
            continue
        for arm in result.get("arm_results", []):
            if bool(arm.get("passed")):
                found = {"k": result["k"], "arm_id": arm["arm_id"]}
                break
        if found:
            break
    return {
        "classification": "BAND-PASS" if found else "BAND-FAIL",
        "found_candidate": found,
    }


def k_check(k: float) -> dict[str, Any]:
    contract = k_contract(k)
    records = [
        _run_job(job, contract=contract)
        for job in phase_jobs("development", contract=contract)
    ]
    phase = summarize_phase_records(records, phase="development", contract=contract)
    local = phase["arm_summaries"][LOCAL_ARM]
    local_diff = float(local["disturbance"]["mean_differential_frequency_energy_hz2_s"])
    local_off = float(local["probe"]["off_diagonal_response_energy_hz2_s"])
    arm = phase["arm_summaries"][bandpass_arm_id(k)]
    diff_ratio = (
        float(arm["disturbance"]["mean_differential_frequency_energy_hz2_s"])
        / local_diff
        if local_diff > 0.0
        else float("inf")
    )
    cross_ratio = (
        float(arm["probe"]["off_diagonal_response_energy_hz2_s"]) / local_off
        if local_off > 0.0
        else float("inf")
    )
    passed = bool(
        diff_ratio <= DIFFERENTIAL_RATIO_MAX
        and cross_ratio <= PROBE_CROSS_RATIO_MAX
        and arm["guards_pass"]
    )
    return {
        "k": float(k),
        "arm_id": bandpass_arm_id(k),
        "record_count": len(records),
        "differential_ratio": diff_ratio,
        "probe_cross_ratio": cross_ratio,
        "guards_pass": bool(arm["guards_pass"]),
        "guard_errors": list(arm["guard_errors"]),
        "passed": passed,
        "any_pass": passed,
        "arm_results": [
            {
                "arm_id": bandpass_arm_id(k),
                "passed": passed,
            }
        ],
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
            "bandpass_controller": _sha256_file(
                ROOT / "src/andes_rl_kundur/control/ring_bandpass_damping.py"
            ),
            "classifier": _sha256_file(
                ROOT / "src/andes_rl_kundur/evaluation/gate_b3_deterministic.py"
            ),
        },
    }



REQUIRED_ROW_KEYS = (
    "normalized_action",
    "controller_action",
    "common_action",
    "differential_action",
    "lower_power_system_pu",
    "upper_power_system_pu",
    "zero_anchor_power_system_pu",
    "feasible_power_system_pu",
    "headroom_fraction",
    "bound_contact",
)


def _enrich_row(
    row: dict[str, Any],
    *,
    normalized: np.ndarray,
    controller_action: np.ndarray,
    common_action: np.ndarray,
    differential_action: np.ndarray,
    mapped: Any,
) -> dict[str, Any]:
    """Attach every estimator-required power/action field to one step row.

    The R407-pre-repair-3 defect dropped these fields, so the estimator
    reported a missing lower_power_system_pu guard error on every record.
    This seam is pure and locked by a regression test.
    """
    lower = np.asarray(mapped.lower_power_system_pu, dtype=float)
    upper = np.asarray(mapped.upper_power_system_pu, dtype=float)
    zero_anchor = np.asarray(mapped.zero_anchor_power_system_pu, dtype=float)
    feasible = np.asarray(mapped.feasible_power_system_pu, dtype=float)
    headroom_fraction = np.where(
        feasible >= 0.0,
        np.divide(
            np.abs(feasible - zero_anchor),
            upper - zero_anchor,
            out=np.zeros_like(feasible),
            where=(upper - zero_anchor) > 1.0e-12,
        ),
        np.divide(
            np.abs(feasible - zero_anchor),
            zero_anchor - lower,
            out=np.zeros_like(feasible),
            where=(zero_anchor - lower) > 1.0e-12,
        ),
    )
    bound_contact = np.abs(normalized) >= 0.70 - 1.0e-12
    row.update(
        {
            "normalized_action": normalized.tolist(),
            "controller_action": controller_action.tolist(),
            "common_action": common_action.tolist(),
            "differential_action": differential_action.tolist(),
            "lower_power_system_pu": lower.tolist(),
            "upper_power_system_pu": upper.tolist(),
            "zero_anchor_power_system_pu": zero_anchor.tolist(),
            "feasible_power_system_pu": feasible.tolist(),
            "headroom_fraction": headroom_fraction.tolist(),
            "bound_contact": [bool(value) for value in bound_contact],
        }
    )
    return row


def _make_controller(arm_id: str, contract: Mapping[str, Any]) -> Any:
    """Bandpass-aware controller factory; zero/local delegate to the R379 spec."""
    if arm_id.startswith("bandpass_k"):
        return bandpass_arm_controller(arm_id, contract=contract)
    spec = controller_spec(arm_id, contract=contract)
    architecture = spec["architecture"]
    common = {
        "device_count": int(contract["device_count"]),
        "nominal_frequency_hz": float(contract["nominal_frequency_hz"]),
        "kp_n_per_hz": float(spec.get("kp_n_per_hz", 0.0)),
        "ki_n_per_hz_s": float(spec.get("ki_n_per_hz_s", 0.0)),
    }
    if architecture == "zero_feedback":
        return None
    if architecture == "local_feasibility_native":
        return FeasibilityNativeLocalController(**common)
    raise ValueError(f"unsupported arm in the bandpass round: {arm_id}")


def _run_job(job: Mapping[str, Any], *, contract: Mapping[str, Any]) -> dict[str, Any]:
    """Forked R379 job loop with the bandpass-aware controller factory."""
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv

    base_env = AndesMultiVSGEnvV4(
        random_disturbance=False,
        comm_fail_prob=0.0,
        comm_delay_steps=0,
    )
    base_env.seed(int(contract["seed"]))
    base_env.STEPS_PER_EPISODE = int(contract["steps"])
    port_env = AndesVSGEnergyPortEnv(base_env=base_env)
    action_map = FeasibilityNativeVSGActionMap(r272_frozen_bess_contract())
    controller = _make_controller(str(job["arm_id"]), contract)
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] = {}
    failure: str | None = None
    previous_power_system_pu = np.zeros(4, dtype=float)
    current_soc = np.full(4, float(contract["soc_initial"]), dtype=float)
    try:
        port_env.reset(delta_u=dict(job["delta_u"]))
        identity = _identity(base_env)
        for _step_index in range(int(contract["steps"])):
            frequencies = (
                np.asarray(base_env._get_vsg_omega(), dtype=float)
                * float(contract["nominal_frequency_hz"])
            )
            controller_action = (
                np.zeros(4, dtype=float)
                if controller is None
                else controller.act(
                    frequencies_hz=frequencies,
                    dt_seconds=float(contract["dt_seconds"]),
                )
            )
            normalized = controller_action.copy()
            if job["experiment_kind"] == "probe":
                normalized = normalized + probe_request(
                    str(job["input_mode"]),
                    str(job["sign"]),
                    contract=contract,
                )
            common_action = np.mean(normalized) * np.ones(4, dtype=float)
            differential_action = normalized - common_action
            voltage_pu = np.asarray(
                [
                    base_env.ss.GENCLS.v.v[position]
                    for position in base_env._vsg_pos
                ],
                dtype=float,
            )
            mapped = action_map.map_action(
                normalized_actions=normalized,
                previous_power_system_pu=previous_power_system_pu,
                soc=current_soc,
                voltage_pu=voltage_pu,
                dt_seconds=float(contract["dt_seconds"]),
            )
            _observation, _reward, done, info = port_env.step(
                mapped.feasible_power_system_pu
            )
            row = _port_row(info, step_index=_step_index, done=bool(done))
            row = _enrich_row(
                row,
                normalized=normalized,
                controller_action=controller_action,
                common_action=common_action,
                differential_action=differential_action,
                mapped=mapped,
            )
            rows.append(row)
            previous_power_system_pu = np.asarray(
                row["commanded_power_system_pu"], dtype=float
            )
            current_soc = np.asarray(row["soc"], dtype=float)
            if row["tds_failed"]:
                failure = "TDS failed"
                break
    except Exception as exc:  # retained in the immutable attempt
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        port_env.close()
    return {
        "phase": str(job["phase"]),
        "arm_id": str(job["arm_id"]),
        "experiment_kind": str(job["experiment_kind"]),
        "condition_id": str(job["condition_id"]),
        "delta_u": dict(job["delta_u"]),
        "input_mode": job["input_mode"],
        "sign": job["sign"],
        "identity": identity,
        "steps": rows,
        "completed_steps": len(rows),
        "tds_failed": failure is not None
        or any(bool(row["tds_failed"]) for row in rows),
        "failure": failure,
        "reward_used_for_gate": False,
        "training_executed": False,
    }



def _capacity_job(_job_id: int) -> dict[str, Any]:
    contract = k_contract(K_GRID[0])
    job = phase_jobs("development", contract=contract)[0]
    record = _run_job(job, contract=contract)
    return {"ok": bool(record["completed_steps"] > 0)}


def measure_capacity() -> str:
    payload = {"rungs": []}
    for workers in (1, 2, 4, 8):
        start = time.monotonic()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_capacity_job, range(workers)))
        wall = time.monotonic() - start
        payload["rungs"].append(
            {
                "workers": workers,
                "jobs": len(results),
                "wall_seconds": round(wall, 3),
                "throughput_jobs_per_second": round(len(results) / max(wall, 1e-9), 4),
                "all_ok": all(result["ok"] for result in results),
            }
        )
    return json.dumps(payload, indent=2, sort_keys=True)


def rehearse() -> str:
    checks = _pre_attempt_checks()
    k = K_GRID[0]
    contract = k_contract(k)
    job = phase_jobs("development", contract=contract)[0]
    record = _run_job(job, contract=contract)
    return json.dumps(
        {
            "rehearsal": True,
            "k": k,
            "pre_attempt": {
                "contract_round": checks["contract_round"],
                "output_absence": checks["output_absence"],
            },
            "scenario": {
                "rows": int(len(record.get("steps", []))),
                "tds_failed": bool(record.get("tds_failed")),
                "identity_ok": bool(record.get("identity") is not None),
            },
        },
        indent=2,
        sort_keys=True,
    )


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
            "k_grid": [float(k) for k in K_GRID],
            "bandpass": build_contract()["bandpass"],
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
    # Owner-approved parallel execution (amendment A-2): the five K points
    # are independent, so they fan out over the worker pool; each worker runs
    # one native numerical thread (pinned at module import).
    with ProcessPoolExecutor(max_workers=PARALLEL_WORKERS) as pool:
        grid_results = list(pool.map(k_check, K_GRID))
    decision = bandpass_decision(grid_results)
    execution_digest = _write_new_json(
        OUT / "formal_execution.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "attempt_sha256": attempt_digest,
            "grid_results": grid_results,
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
        "classification": decision["classification"],
        "found_candidate": decision["found_candidate"],
        "k_grid": [float(k) for k in K_GRID],
        "training_authorized": False,
        "held_out_accessed": False,
        "next_gate": (
            "separately registered held-out gate for the found K"
            if decision["found_candidate"]
            else "none; bandpass stage closed within the frozen K grid"
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
            "classification": decision["classification"],
            "found_candidate": decision["found_candidate"],
            "per_k": [
                {
                    "k": r["k"],
                    "differential_ratio": r["differential_ratio"],
                    "probe_cross_ratio": r["probe_cross_ratio"],
                    "passed": r["passed"],
                }
                for r in grid_results
            ],
        },
        indent=2,
        sort_keys=True,
    )


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
        out = ROOT / "memory/rounds/R407/capacity_evidence_ladder.json"
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        safe_emit(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    safe_emit(execute())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())