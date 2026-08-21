"""Sealed WSL runner for R408: V2 non-learning solving gate.

Tests the owner-authorized V2 follow-up candidates (owner decision
working/route_owner_decision_v2_solving_2026-08-15.md) on the same
feasibility-native energy-port object as R379/R406/R407 (buses 12/16/14/15,
dev bank, seed 42, 0.2 s x 50 steps, frozen estimators and thresholds
r_d <= 0.95, r_cross <= 1.10, all guards):

Stage A  K -> 0 anchor audit and small-gain grid of the frozen 0.4 Hz
         ring-edge bandpass: K in {0, 0.001, 0.003, 0.01, 0.03, 0.05, 0.075,
         0.1}, with per-step zero-sum telemetry (sigma_v of the normalized
         command, sigma_p of the physical power vs zero anchor, sigma of the
         port distortion).  Discriminates the P6 small-gain anomaly:
         anchor semantics vs heterogeneous port-map zero-sum leakage vs
         protocol artifact.  No Q judgment at this stage.
Stage B  bandpass gain extension: K in {2.25, 2.50, 2.75, 3.00, 3.25, 3.50,
         4.00} (advisory prediction r_d(3.5) ~ 0.944, r_cross(3.5) ~ 0.569).
Stage C  fixed parallel blend B1: highpass(alpha=0.85, ks=kc=1) + 0.70 *
         bandpass(K=2), mixed before the common clip (advisory prediction
         (0.946, 1.088)).
Stage D  time-varying A/B blend E1: cosine cross-fade 3.6-4.0 s, both laws
         run continuously (advisory prediction (0.940, 1.080)).

Decision (pre-registered): the first Stage B/C/D arm passing both frozen
endpoint thresholds and every guard returns Q-ENTRY; otherwise
SEARCHED-FAMILIES-NEGATIVE (bounded negative over the searched finite
families, not a universal impossibility theorem).  A secondary strict gate
r_cross <= 0.95 is recorded for the found candidate without changing the
primary decision.

--rehearse exercises the same pre-attempt verification path on bandpass_k0p1
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
from andes_rl_kundur.control.blend_damping import (  # noqa: E402
    FixedBlendController,
    TimeVaryingBlendController,
)
from andes_rl_kundur.control.feasibility_native_deterministic import (  # noqa: E402
    FeasibilityNativeLocalController,
    HPDampingDistributedController,
)
from andes_rl_kundur.control.feasibility_native_vsg_action import (  # noqa: E402
    FeasibilityNativeVSGActionMap,
)
from andes_rl_kundur.control.ring_bandpass_damping import RingBandpassDamping  # noqa: E402
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

ROUND_ID = "R408"
OUT = ROOT / "results/research_loop/r408_v2_solving_gate"

K_GRID_STAGE_A = (0.0, 0.001, 0.003, 0.01, 0.03, 0.05, 0.075, 0.1)
K_GRID_STAGE_B = (2.25, 2.50, 2.75, 3.00, 3.25, 3.50, 4.00)
BLEND_B1 = "blend_b1"
BLEND_E1 = "blend_e1"
BLEND_A_ALPHA = 0.85
BLEND_B_K = 2.0
PARALLEL_WORKERS = 8
F0_HZ = 0.4
ZETA = 0.35
ACTION_CLIP = 0.70
DIFFERENTIAL_RATIO_MAX = 0.95
PROBE_CROSS_RATIO_MAX = 1.10
STRICT_CROSS_RATIO_MAX = 0.95


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


def bandpass_arm_id(k: float) -> str:
    """Frozen arm-id convention: decimal point rendered as 'p' (R407)."""
    return "bandpass_k" + f"{float(k):g}".replace(".", "p")


def _bandpass_k_from_arm_id(arm_id: str) -> float:
    prefix = "bandpass_k"
    if not arm_id.startswith(prefix):
        raise ValueError(f"not a bandpass arm: {arm_id}")
    return float(arm_id[len(prefix):].replace("p", "."))


def build_contract(arm_id: str) -> dict[str, Any]:
    """One frozen 3-arm development contract (zero/local/candidate)."""
    contract = _base_contract()
    contract["round"] = ROUND_ID
    contract["development"]["arm_ids"] = [ZERO_ARM, LOCAL_ARM, arm_id]
    contract["development"]["record_count"] = (
        len(contract["development"]["arm_ids"]) * (len(contract["probe_arm_ids"]) + 2)
    )
    contract["training_authorized"] = False
    contract["r408"] = {"arm_id": arm_id}
    return contract


class BandpassArmController:
    """R407 adapter: normalized zero-sum bandpass command with clip."""

    def __init__(self, *, k: float, nominal_frequency_hz: float) -> None:
        self._bandpass = RingBandpassDamping(
            n=4, dt=0.2, f0_hz=F0_HZ, zeta=ZETA, gain=k
        )
        self._nominal = float(nominal_frequency_hz)

    def act(self, frequencies_hz: Sequence[float], dt_seconds: float) -> np.ndarray:
        frequencies = np.asarray(frequencies_hz, dtype=float)
        command = self._bandpass.step(frequencies - self._nominal)
        return np.clip(command, -ACTION_CLIP, ACTION_CLIP)


def _blend_sub_controllers(contract: Mapping[str, Any]):
    """Frozen A (alpha=0.85, ks=kc=1) and B (K=2) laws for the blend arms."""
    adjacency = {
        int(index): tuple(neighbours)
        for index, neighbours in contract["adjacency"].items()
    }
    a_law = HPDampingDistributedController(
        adjacency=adjacency,
        device_count=int(contract["device_count"]),
        nominal_frequency_hz=float(contract["nominal_frequency_hz"]),
        kp_n_per_hz=float(contract["local_gains"]["kp_n_per_hz"]),
        ki_n_per_hz_s=float(contract["local_gains"]["ki_n_per_hz_s"]),
        ks_n_per_hz=1.0,
        kc_n_per_s=1.0,
        highpass_alpha=BLEND_A_ALPHA,
    )
    b_law = BandpassArmController(
        k=BLEND_B_K,
        nominal_frequency_hz=float(contract["nominal_frequency_hz"]),
    )
    return a_law, b_law


def _make_controller(arm_id: str, contract: Mapping[str, Any]) -> Any:
    if arm_id in (BLEND_B1, BLEND_E1):
        a_law, b_law = _blend_sub_controllers(contract)
        if arm_id == BLEND_B1:
            return FixedBlendController(a_controller=a_law, b_controller=b_law)
        return TimeVaryingBlendController(a_controller=a_law, b_controller=b_law)
    if arm_id.startswith("bandpass_k"):
        return BandpassArmController(
            k=_bandpass_k_from_arm_id(arm_id),
            nominal_frequency_hz=float(contract["nominal_frequency_hz"]),
        )
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
    raise ValueError(f"unsupported arm in the R408 round: {arm_id}")


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
    """Attach estimator-required fields plus the P6 zero-sum telemetry."""
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
    commanded = np.asarray(row["commanded_power_system_pu"], dtype=float)
    requested = np.asarray(row["requested_power_system_pu"], dtype=float)
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
            "zero_sum_telemetry": {
                "sigma_v": float(np.sum(normalized)),
                "sigma_p": float(np.sum(feasible - zero_anchor)),
                "sigma_distortion": float(np.sum(commanded - requested)),
            },
        }
    )
    return row


def _run_job(job: Mapping[str, Any], *, contract: Mapping[str, Any]) -> dict[str, Any]:
    """Forked R407 job loop with blend-aware factory and P6 telemetry."""
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


def _telemetry_l2(records: Sequence[Mapping[str, Any]], key: str) -> float:
    """L2 norm of a per-step scalar telemetry over all disturbance records."""
    values: list[float] = []
    for record in records:
        if record["experiment_kind"] != "disturbance":
            continue
        for row in record.get("steps", []):
            values.append(float(row["zero_sum_telemetry"][key]))
    return float(np.sqrt(np.sum(np.square(values)))) if values else float("nan")


def arm_check(arm_id: str) -> dict[str, Any]:
    """Run the full development bank for one arm and classify it."""
    contract = build_contract(arm_id)
    records = [
        _run_job(job, contract=contract)
        for job in phase_jobs("development", contract=contract)
    ]
    phase = summarize_phase_records(records, phase="development", contract=contract)
    local = phase["arm_summaries"][LOCAL_ARM]
    zero = phase["arm_summaries"][ZERO_ARM]
    arm = phase["arm_summaries"][arm_id]
    local_diff = float(local["disturbance"]["mean_differential_frequency_energy_hz2_s"])
    local_off = float(local["probe"]["off_diagonal_response_energy_hz2_s"])
    zero_diff = float(zero["disturbance"]["mean_differential_frequency_energy_hz2_s"])
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
    strict_cross_pass = bool(cross_ratio <= STRICT_CROSS_RATIO_MAX)
    payload: dict[str, Any] = {
        "arm_id": arm_id,
        "record_count": len(records),
        "differential_ratio": diff_ratio,
        "probe_cross_ratio": cross_ratio,
        "strict_cross_pass": strict_cross_pass,
        "guards_pass": bool(arm["guards_pass"]),
        "guard_errors": list(arm["guard_errors"]),
        "passed": passed,
        "any_pass": passed,
        "zero_arm_differential_energy": zero_diff,
        "local_arm_differential_energy": local_diff,
        "local_arm_probe_off_diagonal_energy": local_off,
        "telemetry": {
            "sigma_v_l2": _telemetry_l2(records, "sigma_v"),
            "sigma_p_l2": _telemetry_l2(records, "sigma_p"),
            "sigma_distortion_l2": _telemetry_l2(records, "sigma_distortion"),
        },
    }
    k = None
    if arm_id.startswith("bandpass_k"):
        k = _bandpass_k_from_arm_id(arm_id)
        payload["k"] = k
        if k > 0.0:
            payload["telemetry"]["sigma_p_l2_over_K"] = (
                payload["telemetry"]["sigma_p_l2"] / k
            )
    payload["telemetry"]["zero_over_local_differential_ratio"] = (
        zero_diff / local_diff if local_diff > 0.0 else float("inf")
    )
    return payload


def solving_decision(grid_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Pre-registered tree: first passing Stage B/C/D arm -> Q-ENTRY."""
    for result in grid_results:
        if bool(result.get("passed")):
            return {
                "classification": "Q-ENTRY",
                "found_candidate": {
                    "arm_id": result["arm_id"],
                    "differential_ratio": result["differential_ratio"],
                    "probe_cross_ratio": result["probe_cross_ratio"],
                    "strict_cross_pass": bool(result["strict_cross_pass"]),
                },
            }
    return {
        "classification": "SEARCHED-FAMILIES-NEGATIVE",
        "found_candidate": None,
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
            "blend_controller": _sha256_file(
                ROOT / "src/andes_rl_kundur/control/blend_damping.py"
            ),
            "bandpass_controller": _sha256_file(
                ROOT / "src/andes_rl_kundur/control/ring_bandpass_damping.py"
            ),
            "classifier": _sha256_file(
                ROOT / "src/andes_rl_kundur/evaluation/gate_b3_deterministic.py"
            ),
        },
    }


def _capacity_job(_job_id: int) -> dict[str, Any]:
    contract = build_contract("bandpass_k0p1")
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
                "throughput_jobs_per_second": round(
                    len(results) / max(wall, 1e-9), 4
                ),
                "all_ok": all(result["ok"] for result in results),
            }
        )
    return json.dumps(payload, indent=2, sort_keys=True)


def rehearse() -> str:
    checks = _pre_attempt_checks()
    contract = build_contract("bandpass_k0p1")
    job = phase_jobs("development", contract=contract)[0]
    record = _run_job(job, contract=contract)
    row_has_telemetry = bool(
        record.get("steps")
        and "zero_sum_telemetry" in record["steps"][0]
    )
    return json.dumps(
        {
            "rehearsal": True,
            "pre_attempt": {
                "contract_round": checks["contract_round"],
                "output_absence": checks["output_absence"],
            },
            "scenario": {
                "rows": int(len(record.get("steps", []))),
                "tds_failed": bool(record.get("tds_failed")),
                "identity_ok": bool(record.get("identity") is not None),
                "telemetry_present": row_has_telemetry,
            },
        },
        indent=2,
        sort_keys=True,
    )


def _all_arm_ids() -> list[str]:
    return [
        *[bandpass_arm_id(k) for k in K_GRID_STAGE_A],
        *[bandpass_arm_id(k) for k in K_GRID_STAGE_B],
        BLEND_B1,
        BLEND_E1,
    ]


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
            "stage_a_k_grid": [float(k) for k in K_GRID_STAGE_A],
            "stage_b_k_grid": [float(k) for k in K_GRID_STAGE_B],
            "blends": {
                "blend_b1": {
                    "a_alpha": BLEND_A_ALPHA,
                    "b_k": BLEND_B_K,
                    "b_weight": 0.70,
                },
                "blend_e1": {
                    "a_alpha": BLEND_A_ALPHA,
                    "b_k": BLEND_B_K,
                    "fade_start_s": 3.6,
                    "fade_end_s": 4.0,
                },
            },
            "thresholds": {
                "differential_ratio_max": DIFFERENTIAL_RATIO_MAX,
                "probe_cross_ratio_max": PROBE_CROSS_RATIO_MAX,
                "strict_cross_ratio_max": STRICT_CROSS_RATIO_MAX,
            },
            "training_authorized": False,
            "held_out_accessed": False,
        },
    )
    entries = [
        {"path": _relative(OUT / "formal_attempt.json"), "sha256": attempt_digest}
    ]
    # Owner-authorized parallel execution: all arm checks are independent;
    # each worker pins one native numerical thread at import.
    arm_ids = _all_arm_ids()
    with ProcessPoolExecutor(max_workers=PARALLEL_WORKERS) as pool:
        grid_results = list(pool.map(arm_check, arm_ids))
    decision = solving_decision(
        [result for result in grid_results if result["arm_id"] not in {
            *[bandpass_arm_id(k) for k in K_GRID_STAGE_A]
        }]
    )
    execution_digest = _write_new_json(
        OUT / "formal_execution.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "attempt_sha256": attempt_digest,
            "arm_results": grid_results,
        },
    )
    entries.append(
        {"path": _relative(OUT / "formal_execution.json"), "sha256": execution_digest}
    )
    p6 = _p6_verdict(grid_results)
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "attempt_sha256": attempt_digest,
        "execution_sha256": execution_digest,
        "classification": decision["classification"],
        "found_candidate": decision["found_candidate"],
        "p6_verdict": p6,
        "training_authorized": False,
        "held_out_accessed": False,
        "next_gate": (
            "separately registered held-out gate for the found arm"
            if decision["found_candidate"]
            else "none; searched finite families closed within the frozen grids"
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
            "p6_verdict": p6,
            "per_arm": [
                {
                    "arm_id": r["arm_id"],
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


def _p6_verdict(grid_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Pre-registered P6 discrimination from the Stage A telemetry."""
    stage_a = [r for r in grid_results if r["arm_id"].startswith("bandpass_k")]
    zero_result = next((r for r in stage_a if r["arm_id"] == "bandpass_k0"), None)
    zero_over_local = (
        float(zero_result["telemetry"]["zero_over_local_differential_ratio"])
        if zero_result
        else float("nan")
    )
    sigma_rows = [
        {
            "k": r["k"],
            "sigma_v_l2": r["telemetry"]["sigma_v_l2"],
            "sigma_p_l2": r["telemetry"]["sigma_p_l2"],
            "sigma_p_l2_over_K": r["telemetry"].get("sigma_p_l2_over_K"),
            "sigma_distortion_l2": r["telemetry"]["sigma_distortion_l2"],
        }
        for r in stage_a
        if "k" in r
    ]
    anchor_verdict = (
        "zero-anchor-equals-zero-action"
        if abs(zero_over_local - 2.787) < 0.35
        else (
            "zero-anchor-equals-baseline"
            if abs(zero_over_local - 1.0) < 0.15
            else "indeterminate"
        )
    )
    positive_k = [s for s in sigma_rows if s["k"] > 0.0 and s["sigma_p_l2"] > 0.0]
    leak_scaling = (
        "first-order-in-K"
        if positive_k
        and all(
            abs(float(s["sigma_p_l2_over_K"]) - float(positive_k[0]["sigma_p_l2_over_K"]))
            < 0.5 * abs(float(positive_k[0]["sigma_p_l2_over_K"]))
            for s in positive_k
        )
        else "not-first-order-in-K"
    )
    return {
        "zero_over_local_differential_ratio": zero_over_local,
        "predicted_zero_anchor_ratio": 2.787,
        "anchor_verdict": anchor_verdict,
        "leak_scaling": leak_scaling,
        "sigma_rows": sigma_rows,
    }


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
        out = ROOT / "memory/rounds/R408/capacity_evidence.json"
        out.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        safe_emit(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    safe_emit(execute())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
