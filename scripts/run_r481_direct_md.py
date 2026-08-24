"""R481 formal adapter — fresh-holdout direct-M/D deterministic bank.

Usage (physical commands are WSL-only through ``andes_scratch.py``)::

    python scripts/run_r481_direct_md.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \\
        scripts/run_r481_direct_md.py rehearse
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \\
        scripts/run_r481_direct_md.py capacity
    python scripts/run_r481_direct_md.py seal
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \\
        scripts/run_r481_direct_md.py execute
    python scripts/run_r481_direct_md.py verify

Formal artifacts are create-only and hash-sidecar protected.  The scientific
contract, fresh-profile generator, and Phase-1A gate live in
``andes_rl_kundur.evaluation.r481_fresh_profiles``; the R399 classification
machinery is reused unchanged.  This file owns authority checks, sealing,
execution orchestration, and artifact I/O only.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from memory.tools.artifact_io import (  # noqa: E402
    read_verified_json,
    sha256_file,
    write_new_json,
)

from andes_rl_kundur.evaluation.r481_fresh_profiles import (  # noqa: E402
    build_contract,
    phase1a_gate,
)

ROUND_ID = "R481"
ROUND_DIR = ROOT / "memory" / "rounds" / ROUND_ID
PLAN = ROUND_DIR / "plan.md"
APPROVAL = ROUND_DIR / "OWNER_APPROVED.json"
CAPACITY = ROUND_DIR / "capacity_evidence.json"
CONTRACT = ROUND_DIR / "contract.json"
REHEARSAL = ROUND_DIR / "rehearsal.json"
SEAL = ROUND_DIR / "formal_seal.json"
OUT = ROOT / "results" / "research_loop" / "r481_direct_md"

WORKERS = 16
CAPACITY_QUICK_JOBS = 8

_R479_RUNNER = ROOT / "scripts" / "run_r479_h_sensitivity.py"
_SPEC = importlib.util.spec_from_file_location("r479_runner", _R479_RUNNER)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover
    raise RuntimeError("R479 parent runner not loadable")
_r479 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_r479)

R478_SEAL = (
    ROOT / "memory" / "rounds" / "R478" / "formal_seal_r478_port_unseen_repair6.json"
)
PARAMETER_CARD = (
    ROOT / "paper" / "yang_md_decoupling_marl" / "working"
    / "md_parameter_card_20260824.json"
)

SOURCE_PATHS = {
    "runner": ROOT / "scripts" / "run_r481_direct_md.py",
    "evaluation": ROOT / "src" / "andes_rl_kundur" / "evaluation"
    / "r481_fresh_profiles.py",
    "headroom_classifier": ROOT / "src" / "andes_rl_kundur" / "evaluation"
    / "md_decoupling_headroom.py",
    "controller": ROOT / "src" / "andes_rl_kundur" / "control" / "per_vsg_md.py",
    "tests": ROOT / "tests" / "test_r481_direct_md.py",
    "plan": PLAN,
    "approval": APPROVAL,
    "contract": CONTRACT,
}


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _sha256_normalized(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk.replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def _source_manifest() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _relative(path), "sha256": _sha256_normalized(path)}
        for name, path in SOURCE_PATHS.items()
    }


def _parent_manifest() -> dict[str, dict[str, str]]:
    return {
        "r478_seal": {
            "path": _relative(R478_SEAL),
            "sha256": sha256_file(R478_SEAL),
        },
        "parameter_card": {
            "path": _relative(PARAMETER_CARD),
            "sha256": sha256_file(PARAMETER_CARD),
        },
    }


def _verify_r478_parent() -> dict[str, Any]:
    return _r479._verify_r478_parent()


def _installed_runtime() -> dict[str, Any]:
    import andes

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    return {
        "python": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "andes_module": str(Path(andes.__file__).resolve()),
        "case_path": str(case_path),
        "case_sha256": sha256_file(case_path),
    }


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R481 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R481 must run through scripts/andes_scratch.py")


def _approval_valid() -> bool:
    payload = json.loads(APPROVAL.read_text(encoding="utf-8"))
    return payload.get("approved") is True and payload.get("round") == ROUND_ID


def _contract_valid() -> bool:
    payload, _ = read_verified_json(CONTRACT)
    return payload == build_contract()


def _plan_state() -> str:
    for line in PLAN.read_text(encoding="utf-8").splitlines():
        if line.startswith("state:"):
            return line.split(":", 1)[1].strip()
    raise RuntimeError("R481 plan has no state")


def prepare() -> str:
    if CONTRACT.exists() or CONTRACT.with_suffix(".json.sha256").exists():
        raise FileExistsError(f"R481 contract already exists: {CONTRACT}")
    return write_new_json(CONTRACT, build_contract())


def _pre_attempt_checks() -> dict[str, Any]:
    runtime = _installed_runtime()
    parent = _verify_r478_parent()
    checks = {
        "source_hash": bool(_source_manifest()),
        "parent_hash": parent["verified_source_count"] > 0,
        "installed_package": runtime["andes_version"] != "unknown",
        "installed_case": Path(runtime["case_path"]).is_file(),
        "output_absence": not OUT.exists(),
        "active_plan": (
            _plan_state() == "active"
            and "manuscript_line: yang-md-decoupling-marl"
            in PLAN.read_text(encoding="utf-8")
        ),
        "owner_approved": _approval_valid(),
        "contract_closed": _contract_valid(),
    }
    if not all(checks.values()):
        raise RuntimeError(f"R481 pre-attempt check failed: {checks}")
    return {"checks": checks, "runtime": runtime, "parent": parent}


def _controller_for(arm_id: str):
    from andes_rl_kundur.control.per_vsg_md import (
        LocalNeighbourMDExecution,
        local_neighbour_md_candidates,
    )

    if arm_id == "zero":
        return None
    contracts = {row.name: row for row in local_neighbour_md_candidates()}
    if arm_id not in contracts:
        raise ValueError(f"unknown arm: {arm_id}")
    return LocalNeighbourMDExecution(contracts[arm_id])


def _run_job(job: dict[str, Any]) -> dict[str, Any]:
    """Run one 30-step record on the corrected card (R399 schema)."""

    import resource

    import numpy as np

    from andes_rl_kundur.control.per_vsg_md import adapt_v4_observations_to_physical
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4

    profile = job["profile"]
    scenario = job["scenario"]
    arm_id = str(job["arm_id"])
    contract = build_contract()
    total_steps = int(job.get("steps_override") or contract["steps"])
    baseline_m = np.asarray(profile["baseline_m0"], dtype=float)
    baseline_d = np.asarray(profile["baseline_d0"], dtype=float)
    env: Any | None = None
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] = {}
    initial_frequency: list[float] = []
    failure: str | None = None
    try:
        env = AndesMultiVSGEnvV4(
            random_disturbance=False,
            comm_fail_prob=0.0,
            comm_delay_steps=0,
        )
        env.M0 = baseline_m.copy()
        env.D0_HETEROGENEOUS = baseline_d.copy()
        env.NEW_LOADS = {
            14: {
                "p0": float(profile["steady_loads"]["PQ_Bus14"]),
                "q0": 0.0,
            },
            15: {
                "p0": float(profile["steady_loads"]["PQ_Bus15"]),
                "q0": 0.0,
            },
        }
        env.seed(int(contract["seed"]))
        env.STEPS_PER_EPISODE = total_steps
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        positions = list(env._vsg_pos)
        identity = {
            "n_agents": int(env.N_AGENTS),
            "vsg_idx": [str(value) for value in env.vsg_idx],
            "vsg_buses": [
                int(env.ss.GENCLS.bus.v[position]) for position in positions
            ],
            "obs_dim": int(env.OBS_DIM),
            "baseline_m0": [float(value) for value in profile["baseline_m0"]],
            "baseline_d0": [float(value) for value in profile["baseline_d0"]],
            "control_nominal_frequency_hz": float(env.FN),
            "physical_nominal_frequency_hz": float(env.andes_nominal_frequency_hz),
        }
        initial_frequency = (
            np.asarray(env._get_vsg_omega(), dtype=float)
            * float(env.andes_nominal_frequency_hz)
        ).tolist()
        controller = _controller_for(arm_id)
        if controller is not None:
            controller.reset()
        for step_index in range(total_steps):
            if controller is None:
                action = np.zeros((4, 2), dtype=np.float32)
            else:
                action = controller.act(adapt_v4_observations_to_physical(observation))
            action_dict = {
                actor: np.asarray(action[actor], dtype=np.float32)
                for actor in range(4)
            }
            observation, _reward, done, info = env.step(action_dict)
            # Corrected-card telemetry: info["M_es"]/["D_es"] are device-base
            # reports (the R399 summariser contract).  The raw ANDES
            # GENCLS.M.v / D.v are system-base and must not feed the
            # device-base mapping check.
            actual_m = np.asarray(info["M_es"], dtype=float)
            actual_d = np.asarray(info["D_es"], dtype=float)
            rows.append(
                {
                    "step_index": step_index,
                    "time": float(info["time"]),
                    "action_norm": action.astype(float).tolist(),
                    "freq_hz_physical": np.asarray(
                        info["freq_hz_physical"], dtype=float
                    ).tolist(),
                    "M_es": actual_m.tolist(),
                    "D_es": actual_d.tolist(),
                    "delta_M": np.asarray(info["delta_M"], dtype=float).tolist(),
                    "delta_D": np.asarray(info["delta_D"], dtype=float).tolist(),
                    "tds_failed": bool(info["tds_failed"]),
                    "done": bool(done),
                }
            )
            if info["tds_failed"]:
                failure = "TDS failed"
                break
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        if env is not None:
            env.close()
    return {
        "profile_id": str(profile["profile_id"]),
        "split": str(profile["split"]),
        "scenario_id": str(scenario["scenario_id"]),
        "pair_kind": str(scenario["pair_kind"]),
        "sign": str(scenario["sign"]),
        "magnitude": float(scenario["magnitude"]),
        "delta_u": dict(scenario["delta_u"]),
        "arm_id": arm_id,
        "identity": identity,
        "initial_freq_hz_physical": initial_frequency,
        "steps": rows,
        "completed_steps": len(rows),
        "completed": failure is None and len(rows) == total_steps,
        "tds_failed": failure is not None
        or any(bool(row["tds_failed"]) for row in rows),
        "failure": failure,
        "worker_max_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "reward_used_for_gate": False,
        "training_executed": False,
    }


def _rehearsal_jobs(contract: dict[str, Any]) -> list[dict[str, Any]]:
    profile = next(
        row for row in contract["profiles"] if row["split"] == "development"
    )
    return [
        {"profile": profile, "scenario": scenario, "arm_id": "zero"}
        for scenario in profile["scenarios"]
    ]


def rehearse() -> str:
    _assert_wsl_scratch()
    if REHEARSAL.exists() or SEAL.exists() or OUT.exists():
        raise FileExistsError("R481 rehearsal/seal/formal artifact already exists")
    pre_attempt = _pre_attempt_checks()
    from andes_rl_kundur.evaluation.md_decoupling_headroom import summarise_profile

    jobs = _rehearsal_jobs(build_contract())
    started = time.perf_counter()
    records = [_run_job(job) for job in jobs]
    elapsed = time.perf_counter() - started
    summary = summarise_profile(records, contract=build_contract())
    if summary["valid"] is not True:
        raise RuntimeError(f"R481 rehearsal summary invalid: {summary}")
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "phase": "same-pre-attempt-path-rehearsal",
        **pre_attempt,
        "rehearsal_scope": "zero arm on the first fresh development profile, six scenarios",
        "summary": summary,
        "elapsed_seconds": elapsed,
        "formal_attempt_created": False,
        "formal_outputs_created": False,
    }
    return write_new_json(REHEARSAL, payload)


def _capacity_jobs(contract: dict[str, Any]) -> list[dict[str, Any]]:
    profiles = {str(row["profile_id"]): row for row in contract["profiles"]}
    eval_ids = [
        str(row["profile_id"])
        for row in contract["profiles"]
        if row["split"] == "evaluation"
    ]
    dev_id = next(
        str(row["profile_id"])
        for row in contract["profiles"]
        if row["split"] == "development"
    )
    choices = (
        (dev_id, "zero", "common", "negative"),
        (dev_id, "local_neighbour_md_km2_kd2", "localized", "positive"),
        (eval_ids[0], "zero", "common", "positive"),
        (eval_ids[1], "local_neighbour_md_km1_kd1", "differential", "positive"),
        (eval_ids[2], "local_neighbour_md_km0p5_kd2", "localized", "negative"),
        (eval_ids[3], "local_neighbour_md_km2_kd0p5", "differential", "negative"),
        (eval_ids[0], "local_neighbour_md_km2_kd2", "common", "negative"),
        (eval_ids[3], "zero", "localized", "positive"),
    )
    jobs = []
    for profile_id, arm_id, pair_kind, sign in choices:
        profile = profiles[profile_id]
        scenario = next(
            row
            for row in profile["scenarios"]
            if row["pair_kind"] == pair_kind and row["sign"] == sign
        )
        jobs.append(
            {
                "profile": profile,
                "scenario": scenario,
                "arm_id": arm_id,
                "steps_override": int(contract["steps"]),
            }
        )
    return jobs


def capacity() -> str:
    _assert_wsl_scratch()
    if CAPACITY.exists() or SEAL.exists() or OUT.exists():
        raise FileExistsError("R481 capacity/seal/formal artifact already exists")
    rehearsal, _ = read_verified_json(REHEARSAL)
    if rehearsal.get("summary", {}).get("valid") is not True:
        raise RuntimeError("R481 rehearsal did not pass")
    jobs = _capacity_jobs(build_contract())
    started = time.perf_counter()
    records: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=WORKERS) as executor:
        records = list(executor.map(_run_job, jobs))
    wall = time.perf_counter() - started
    valid = all(
        record["completed"] is True and record["tds_failed"] is False
        for record in records
    )
    return write_new_json(
        CAPACITY,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "quick_confirm": {
                "workers": WORKERS,
                "jobs": len(records),
                "wall_seconds": wall,
                "all_records_valid": bool(valid),
                "failures": [
                    record["failure"]
                    for record in records
                    if record["completed"] is not True or record["tds_failed"] is not False
                ],
            },
            "empirical_anchor": {
                "source": _relative(
                    ROOT / "memory" / "rounds" / "R478" / "capacity_r478_md_ninelaw.json"
                ),
                "source_sha256": "2f40f57c6495f51df156b40e97c16023488befa83b294a102224e5be56df279c",
                "same_corrected_andes_family": True,
                "all_records_valid": True,
                "concurrent_workers": 9,
                "native_threads_per_worker": 1,
                "history_ladder_r452_r477": "16 workers selected in every round R452-R477 on this host",
            },
            "selected": {
                "workers": WORKERS,
                "launcher_processes": 1,
                "reason": (
                    "history ladder R452-R477 16-worker precedent plus this "
                    "round's 16x8 quick confirm; bank has 360 independent records"
                ),
            },
            "whole_host_python_process_budget": WORKERS + 1,
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
            "capacity_trace_role": "non_claim_bearing_quick_confirmation",
        },
    )


def _seal_payload() -> dict[str, Any]:
    rehearsal, rehearsal_sha = read_verified_json(REHEARSAL)
    capacity, capacity_sha = read_verified_json(CAPACITY)
    if rehearsal.get("summary", {}).get("valid") is not True:
        raise RuntimeError("R481 rehearsal is not valid")
    if capacity.get("quick_confirm", {}).get("all_records_valid") is not True:
        raise RuntimeError("R481 capacity quick confirm is not valid")
    contract = build_contract()
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_sha256": sha256_file(CONTRACT),
        "sources": _source_manifest(),
        "parents": _parent_manifest(),
        "rehearsal_sha256": rehearsal_sha,
        "capacity_sha256": capacity_sha,
        "worker_budget": {
            "workers": WORKERS,
            "launcher": 1,
            "native_threads_per_process": 1,
        },
        "output_root": _relative(OUT),
        "formal_job_count": sum(
            len(profile["scenarios"]) for profile in contract["profiles"]
        )
        * len(contract["arm_ids"]),
        "authority": (
            "owner-approved R481 fresh-holdout direct-M/D formal bank; "
            "training and downstream attribution remain closed"
        ),
    }


def seal() -> str:
    if SEAL.exists():
        raise FileExistsError(f"R481 seal already exists: {SEAL}")
    if _plan_state() != "active":
        raise RuntimeError("R481 must be active before formal sealing")
    _verify_r478_parent()
    if not _approval_valid() or not _contract_valid():
        raise RuntimeError("R481 approval or contract invalid")
    return write_new_json(SEAL, _seal_payload())


def _verify_seal(*, require_runtime: bool = False) -> tuple[dict[str, Any], str]:
    payload, digest = read_verified_json(SEAL)
    for item in payload["sources"].values():
        if _sha256_normalized(ROOT / item["path"]) != item["sha256"]:
            raise RuntimeError(f"R481 sealed source drift: {item['path']}")
    for item in payload["parents"].values():
        if sha256_file(ROOT / item["path"]) != item["sha256"]:
            raise RuntimeError(f"R481 sealed parent drift: {item['path']}")
    if payload["worker_budget"] != {
        "workers": WORKERS,
        "launcher": 1,
        "native_threads_per_process": 1,
    }:
        raise RuntimeError("R481 sealed worker budget mismatch")
    if payload["contract"] != build_contract():
        raise RuntimeError("R481 contract drift")
    rehearsal, rehearsal_sha = read_verified_json(REHEARSAL)
    capacity, capacity_sha = read_verified_json(CAPACITY)
    if rehearsal_sha != payload["rehearsal_sha256"]:
        raise RuntimeError("R481 sealed rehearsal mismatch")
    if capacity_sha != payload["capacity_sha256"]:
        raise RuntimeError("R481 sealed capacity mismatch")
    if not _approval_valid() or not _contract_valid():
        raise RuntimeError("R481 sealed approval or contract invalid")
    if require_runtime:
        current_runtime = _installed_runtime()
        expected_runtime = rehearsal["runtime"]
        for key in ("andes_version", "case_sha256"):
            if current_runtime[key] != expected_runtime[key]:
                raise RuntimeError(f"R481 installed runtime drift: {key}")
    _verify_r478_parent()
    return payload, digest


def _formal_jobs(contract: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"profile": profile, "scenario": scenario, "arm_id": arm_id}
        for profile in contract["profiles"]
        for scenario in profile["scenarios"]
        for arm_id in contract["arm_ids"]
    ]


def execute() -> int:
    _assert_wsl_scratch()
    _, seal_sha = _verify_seal(require_runtime=True)
    if OUT.exists():
        raise FileExistsError(f"R481 formal output already exists: {OUT}")
    contract = build_contract()
    jobs = _formal_jobs(contract)
    attempt_sha = write_new_json(
        OUT / "formal_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "started_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_sha,
            "job_count": len(jobs),
            "workers": WORKERS,
            "scientific_outcomes_inspected": False,
        },
    )
    started = time.perf_counter()
    orchestration_error: str | None = None
    records: list[dict[str, Any]] = []
    try:
        with ProcessPoolExecutor(max_workers=WORKERS) as executor:
            records = list(executor.map(_run_job, jobs))
    except Exception as error:
        orchestration_error = f"{type(error).__name__}: {str(error)[:500]}"
    terminal = (
        orchestration_error is None
        and len(records) == len(jobs)
        and all(
            record["completed"] is True and record["tds_failed"] is False
            for record in records
        )
    )
    execution = {
        "schema_version": 1,
        "round": ROUND_ID,
        "status": "complete" if terminal else "engineering-invalid",
        "attempt_sha256": attempt_sha,
        "seal_sha256": seal_sha,
        "elapsed_seconds": time.perf_counter() - started,
        "expected_records": len(jobs),
        "completed_records": len(records),
        "orchestration_error": orchestration_error,
        "records": records,
        "scientific_outcomes_inspected": False,
        "reward_used_for_gate": False,
        "training_executed": False,
    }
    execution_sha = write_new_json(OUT / "formal_execution.json", execution)

    if terminal:
        from andes_rl_kundur.evaluation.md_decoupling_headroom import (
            classify_bank,
            summarise_profile,
        )

        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for record in records:
            key = (str(record["profile_id"]), str(record["arm_id"]))
            grouped.setdefault(key, []).append(record)
        summaries = [
            summarise_profile(grouped[key], contract=contract)
            for key in sorted(grouped)
        ]
        headroom = classify_bank(summaries, contract=contract)
        selected_arm = headroom.get("selected_deterministic_arm")
        gate = (
            phase1a_gate(
                summaries,
                contract=contract,
                selected_arm=str(selected_arm),
            )
            if selected_arm is not None
            else {"passed_4_of_4": False, "passed_count": 0, "reason": "no_selected_arm"}
        )
        if headroom.get("classification") not in {
            "HEADROOM-PASS",
            "STOP-NO-JOINT-HEADROOM",
        }:
            classification = "ENGINEERING-INVALID"
        elif gate.get("passed_4_of_4") is True:
            classification = "DIRECT-MD-FORMAL-PASS"
        else:
            classification = "DIRECT-MD-FORMAL-FAIL"
        analysis = {
            "schema_version": 1,
            "round": ROUND_ID,
            "classification": classification,
            "headroom_classification": headroom.get("classification"),
            "selected_deterministic_arm": selected_arm,
            "phase1a_gate": gate,
            "headroom": headroom,
            "summaries": summaries,
            "seal_sha256": seal_sha,
            "formal_execution_sha256": execution_sha,
            "reward_used_for_gate": False,
            "training_authorized": False,
            "claim_scope": "frozen fresh heterogeneous bank only",
        }
        write_new_json(OUT / "formal_analysis.json", analysis)
    return 0 if terminal else 1


def verify() -> dict[str, Any]:
    _, seal_sha = _verify_seal()
    execution, execution_sha = read_verified_json(OUT / "formal_execution.json")
    if execution.get("status") != "complete":
        return {
            "round": ROUND_ID,
            "seal_sha256": seal_sha,
            "execution_sha256": execution_sha,
            "status": execution.get("status"),
            "classification": "ENGINEERING-INVALID",
        }
    analysis, analysis_sha = read_verified_json(OUT / "formal_analysis.json")
    if analysis.get("formal_execution_sha256") != execution_sha:
        raise RuntimeError("R481 analysis execution mismatch")
    return {
        "round": ROUND_ID,
        "seal_sha256": seal_sha,
        "execution_sha256": execution_sha,
        "analysis_sha256": analysis_sha,
        "classification": analysis["classification"],
        "headroom_classification": analysis["headroom_classification"],
        "selected_arm": analysis["selected_deterministic_arm"],
        "phase1a_passed_count": analysis["phase1a_gate"]["passed_count"],
        "record_count": execution["completed_records"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("prepare", "rehearse", "capacity", "seal", "execute", "verify"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    command = _parser().parse_args(argv).command
    if command == "prepare":
        print(f"R481 contract: {prepare()}")
        return 0
    if command == "rehearse":
        print(f"R481 rehearsal: {rehearse()}")
        return 0
    if command == "capacity":
        print(f"R481 capacity: {capacity()}")
        return 0
    if command == "seal":
        print(f"R481 seal: {seal()}")
        return 0
    if command == "execute":
        return execute()
    print(json.dumps(verify(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
