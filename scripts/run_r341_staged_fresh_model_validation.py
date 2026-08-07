"""Seal, construct, execute, and analyse R341 staged fresh validation.

The live construction and trajectory commands are WSL-only. Candidate
construction is a distinct create-only phase. Its exact artifact hash is then
bound into the validation seal before any nonlinear trajectory can start.
"""

from __future__ import annotations

import argparse
import gzip
import importlib.metadata
import os
import platform
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
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

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for _path in (ROOT, SRC):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from memory.tools.artifact_io import (  # noqa: E402
    canonical_json_bytes,
    payload_sha256,
    read_verified_json,
    sha256_file,
    write_new_json,
)

ROUND_ID = "R341"
QUESTION_ID = "Q-0089"
DEFAULT_CONSTRUCTION_SEAL = ROOT / "memory/rounds/R341/construction_seal.json"
DEFAULT_VALIDATION_SEAL = ROOT / "memory/rounds/R341/validation_seal.json"
DEFAULT_DEVELOPMENT_SEAL = ROOT / "memory/rounds/R341/development_seal.json"
DEFAULT_OUT = ROOT / "results/r341_staged_fresh_model_validation"
DEFAULT_CANARY_OUT = ROOT / "tmp/r341_development_canary"
EXPECTED_CASE_SHA256 = "f725e03ba12d8207616f68acdd606bbd35e7c4a68f13e66d7db43925adac2ed8"
WHOLE_HOST_PYTHON_PROCESSES = 16
TOTAL_STEPS = 1000

POINTS = {
    "FV0": {
        "vsg_m_device": 183.75,
        "vsg_d_device": 91.875,
        "tie_rx_scale": 1.16,
        "initial_soc": 0.435,
    },
    "FV1": {
        "vsg_m_device": 211.25,
        "vsg_d_device": 105.625,
        "tie_rx_scale": 1.40,
        "initial_soc": 0.535,
    },
}
DEVELOPMENT_POINTS = {
    "HS0": {
        "vsg_m_device": 177.5,
        "vsg_d_device": 88.75,
        "tie_rx_scale": 1.10,
        "initial_soc": 0.41,
    },
    "HS1": {
        "vsg_m_device": 202.5,
        "vsg_d_device": 101.25,
        "tie_rx_scale": 1.35,
        "initial_soc": 0.51,
    },
}
CHANNELS = (
    {
        "device_idx": "PQ_0",
        "bus_idx": 7,
        "initial_active_system_pu": 11.59,
        "initial_reactive_system_pu": -0.735,
    },
    {
        "device_idx": "PQ_1",
        "bus_idx": 8,
        "initial_active_system_pu": 15.75,
        "initial_reactive_system_pu": -0.899,
    },
    {
        "device_idx": "PQ_Bus14",
        "bus_idx": 14,
        "initial_active_system_pu": 2.48,
        "initial_reactive_system_pu": 0.0,
    },
    {
        "device_idx": "PQ_Bus15",
        "bus_idx": 15,
        "initial_active_system_pu": 0.05,
        "initial_reactive_system_pu": 0.0,
    },
)
WAVEFORMS = {
    "ramp_hold_unit": (0.25, 0.50, 0.75, 1.00, 1.00, 0.75, 0.50, 0.25),
    "separated_pulse_unit": (1.00, 0.50, 0.00, 0.00, 0.00, 0.50, 1.00),
}
SIGNS = ("positive", "negative")
CANDIDATE_JOBS = tuple(
    {"point": point, "input_family": family, "channel": channel}
    for point in POINTS
    for family in ("control", "load")
    for channel in range(4)
)


def _path_text(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _jsonable(value: Any) -> Any:
    try:
        import numpy as np

        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.generic):
            return value.item()
    except ImportError:
        pass
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _channel_amplitudes(channel: dict[str, object]) -> tuple[float, float]:
    baseline = float(channel["initial_active_system_pu"])
    return round(min(0.03, 0.40 * baseline), 12), round(min(0.07, 0.80 * baseline), 12)


def _record_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for point_name in POINTS:
        specs.append(
            {
                "record_index": len(specs),
                "point": point_name,
                "channel": None,
                "waveform": "zero",
                "profile_key": "zero",
                "amplitude_system_pu": 0.0,
                "sign": "zero",
            }
        )
        for channel in CHANNELS:
            for waveform in WAVEFORMS:
                for amplitude in _channel_amplitudes(channel):
                    for sign in SIGNS:
                        specs.append(
                            {
                                "record_index": len(specs),
                                "point": point_name,
                                "channel": dict(channel),
                                "waveform": waveform,
                                "profile_key": f"{waveform}__{amplitude:.2f}",
                                "amplitude_system_pu": amplitude,
                                "sign": sign,
                            }
                        )
    return specs


def build_contract() -> dict[str, object]:
    """Return the complete prospective R341 scientific contract."""

    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "fresh-nonlinear-model-validation",
        "operating_points": POINTS,
        "channels": [dict(row) for row in CHANNELS],
        "waveforms": {name: list(values) for name, values in WAVEFORMS.items()},
        "amplitude_rule": {
            "lower": "min(0.03, 0.40 * initial_active_system_pu)",
            "higher": "min(0.07, 0.80 * initial_active_system_pu)",
        },
        "signs": list(SIGNS),
        "record_count_per_point": 33,
        "record_count": 66,
        "stages": ["zero", "sentinel", "local", "second-wave"],
        "total_steps": TOTAL_STEPS,
        "validation_horizon_seconds": 200.0,
        "estimated_wall_minutes": [11.0, 15.0],
        "estimated_from": "R336 measured 25-step per-record throughput scaled to 1000 steps at sixteen processes",
        "sample_period_seconds": 0.2,
        "tds_substeps": 5,
        "sample_observation_convention": "end-of-held-interval",
        "candidate_construction": {
            "method": "frozen-R339-point-scheduled-descriptor-to-ERA",
            "finite_difference_steps_system_pu": [1.0e-4, 1.0e-5, 1.0e-6],
            "order": 12,
            "block_rows": 8,
            "block_columns": 8,
            "markov_samples": 25,
            "pole_projection": False,
            "trajectory_fit_count": 0,
            "trajectory_selection_count": 0,
        },
        "thresholds": {
            "nrmse_maximum": 0.15,
            "peak_vector_residual_maximum": 0.20,
        },
        "whole_host_python_processes": WHOLE_HOST_PYTHON_PROCESSES,
        "native_threads_per_process": 1,
        "candidate_artifact_create_only": True,
        "validation_seal_binds_candidate_sha256": True,
        "formal_construction_retry_authorized": False,
        "formal_validation_retry_authorized": False,
        "controller_executed": False,
        "closed_loop_executed": False,
        "distributed_runtime_executed": False,
        "training_executed": False,
        "eval_executed": False,
    }


def staged_bank_schedule() -> list[dict[str, object]]:
    """Return the immutable early-result partition of the formal bank."""

    stages: dict[str, list[int]] = {
        "zero": [],
        "sentinel": [],
        "local": [],
        "second-wave": [],
    }
    for spec in _record_specs():
        index = int(spec["record_index"])
        channel = spec["channel"]
        if channel is None:
            stage = "zero"
        elif spec["waveform"] == "separated_pulse_unit":
            stage = "second-wave"
        elif channel["device_idx"] in {"PQ_0", "PQ_1"}:
            stage = "sentinel"
        else:
            stage = "local"
        stages[stage].append(index)
    return [
        {"name": name, "record_indices": indices}
        for name, indices in stages.items()
    ]


def development_canary_contract() -> dict[str, object]:
    """Return the frozen short-run contract on already exposed points."""

    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "identity": "DEVELOPMENT",
        "points": list(DEVELOPMENT_POINTS),
        "operating_points": DEVELOPMENT_POINTS,
        "waveform": "ramp_hold_unit",
        "amplitude_rule": "min(0.07, 0.80 * initial_active_system_pu)",
        "signs": list(SIGNS),
        "record_count": 18,
        "total_steps": 25,
        "sample_period_seconds": 0.2,
        "whole_host_python_processes": WHOLE_HOST_PYTHON_PROCESSES,
        "native_threads_per_process": 1,
        "formal_evidence": False,
    }


def _development_record_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for point_name in DEVELOPMENT_POINTS:
        specs.append(
            {
                "record_index": len(specs),
                "point": point_name,
                "channel": None,
                "waveform": "zero",
                "profile_key": "zero",
                "amplitude_system_pu": 0.0,
                "sign": "zero",
            }
        )
        for channel in CHANNELS:
            amplitude = _channel_amplitudes(channel)[1]
            for sign in SIGNS:
                specs.append(
                    {
                        "record_index": len(specs),
                        "point": point_name,
                        "channel": dict(channel),
                        "waveform": "ramp_hold_unit",
                        "profile_key": f"ramp_hold_unit__{amplitude:.2f}",
                        "amplitude_system_pu": amplitude,
                        "sign": sign,
                    }
                )
    return specs


@contextmanager
def _development_configuration():
    """Temporarily route the shared execution seam to the exposed canary."""

    global POINTS, CANDIDATE_JOBS, TOTAL_STEPS
    previous = POINTS, CANDIDATE_JOBS, TOTAL_STEPS
    POINTS = DEVELOPMENT_POINTS
    CANDIDATE_JOBS = tuple(
        {"point": point, "input_family": family, "channel": channel}
        for point in POINTS
        for family in ("control", "load")
        for channel in range(4)
    )
    TOTAL_STEPS = 25
    try:
        yield
    finally:
        POINTS, CANDIDATE_JOBS, TOTAL_STEPS = previous


def candidate_then_bank_schedule() -> dict[str, object]:
    """Expose the candidate-first sixteen-process schedule for audit."""

    parent_indices = list(range(0, 66, WHOLE_HOST_PYTHON_PROCESSES))
    child_indices = [index for index in range(66) if index not in parent_indices]
    return {
        "candidate_jobs": [dict(row) for row in CANDIDATE_JOBS],
        "candidate_artifact_create_only": True,
        "validation_seal_binds_candidate_sha256": True,
        "candidate_precedes_every_trajectory": True,
        "parent_record_indices": parent_indices,
        "child_record_indices": child_indices,
        "whole_host_python_processes": WHOLE_HOST_PYTHON_PROCESSES,
        "native_threads_per_process": 1,
    }


def _source_paths() -> dict[str, Path]:
    return {
        "r341_runner": Path(__file__).resolve(),
        "r341_probe": ROOT / "probes/r341_staged_fresh_model_validation.py",
        "r341_tests": ROOT / "tests/test_r341_staged_fresh_model_validation.py",
        "r339_runner": ROOT / "scripts/run_r339_input_bridge_diagnosis.py",
        "r339_probe": ROOT / "probes/r339_input_bridge_diagnosis.py",
        "r336_runner": ROOT / "scripts/run_r336_disturbance_package.py",
        "r335_runner": ROOT / "scripts/run_r335_disturbance_package.py",
        "input_bridge_math": ROOT / "src/andes_rl_kundur/evaluation/model_first_input_bridge.py",
        "dynamic_reduction_math": ROOT
        / "src/andes_rl_kundur/evaluation/model_first_dynamic_reduction.py",
        "model_first_contract": ROOT / "src/andes_rl_kundur/env/andes/model_first_contract.py",
        "model_first_env": ROOT / "src/andes_rl_kundur/env/andes/model_first_env.py",
        "pq_profile": ROOT / "src/andes_rl_kundur/env/andes/model_first_pq_profile.py",
        "profile_feasibility": ROOT
        / "src/andes_rl_kundur/evaluation/model_first_profile_feasibility.py",
        "pq_disturbance": ROOT / "src/andes_rl_kundur/env/andes/model_first_pq_disturbance.py",
        "andes_scratch": ROOT / "scripts/andes_scratch.py",
        "artifact_io": ROOT / "memory/tools/artifact_io.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": sha256_file(path)}
        for name, path in sorted(_source_paths().items())
    }


def _construction_parent_paths() -> dict[str, Path]:
    return {
        "r341_plan": ROOT / "memory/rounds/R341/plan.md",
        "r341_capacity": ROOT / "memory/rounds/R341/host_capacity.json",
        "adr0013": ROOT
        / "docs/adr/0013-candidate-before-validation-and-capacity-bound-long-horizon.md",
        "q0089": ROOT / "memory/questions/Q-0089.md",
        "clm0890": ROOT / "memory/claims/CLM-0890.md",
        "r339_seal": ROOT / "memory/rounds/R339/input_bridge_seal_v3.json",
        "r339_execution": ROOT / "results/r339_input_bridge_diagnosis/execution.json",
        "r339_analysis": ROOT / "results/r339_input_bridge_diagnosis/analysis.json",
        "r339_verdict": ROOT / "memory/rounds/R339/verdict.md",
    }


def _parents(paths: dict[str, Path]) -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": sha256_file(path)}
        for name, path in sorted(paths.items())
    }


def _expected_installed_sources() -> dict[str, str]:
    from scripts import run_r333_pq_disturbance_identification as r333

    return dict(r333.EXPECTED_INSTALLED_SOURCES)


def prepare_canary(seal_path: Path, *, created_utc: str | None = None) -> str:
    """Write the create-only source-closed development-canary seal."""

    contract = development_canary_contract()
    payload = {
        "schema_version": 1,
        "phase": "development-canary",
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": created_utc or datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": payload_sha256(contract),
        "sources": _sources(),
        "parents": _parents(_construction_parent_paths()),
        "expected_runtime": {
            "andes_version": "2.0.0",
            "installed_sources": _expected_installed_sources(),
            "case_sha256": EXPECTED_CASE_SHA256,
        },
        "formal_evidence": False,
        "output_create_only": True,
        "retry_authorized": False,
    }
    digest = write_new_json(seal_path, payload)
    print(f"development_seal_sha256={digest}")
    return digest


def prepare_construction(seal_path: Path, *, created_utc: str | None = None) -> str:
    """Write the create-only source-closed construction seal."""

    contract = build_contract()
    payload = {
        "schema_version": 1,
        "phase": "construction",
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": created_utc or datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": payload_sha256(contract),
        "sources": _sources(),
        "parents": _parents(_construction_parent_paths()),
        "expected_runtime": {
            "andes_version": "2.0.0",
            "installed_sources": _expected_installed_sources(),
            "case_sha256": EXPECTED_CASE_SHA256,
        },
        "formal_artifacts_create_only": True,
        "formal_retry_authorized": False,
    }
    digest = write_new_json(seal_path, payload)
    print(f"construction_seal_sha256={digest}")
    return digest


def _load_seal(path: Path, expected_sha256: str, *, phase: str) -> tuple[dict[str, Any], str]:
    payload, digest = read_verified_json(path, expected_sha256=expected_sha256)
    if (
        payload.get("phase") != phase
        or payload.get("round") != ROUND_ID
        or payload.get("question") != QUESTION_ID
    ):
        raise RuntimeError(f"R340 {phase} seal identity mismatch")
    contract = build_contract()
    if payload.get("contract") != contract:
        raise RuntimeError(f"R340 {phase} contract drift")
    if payload.get("contract_payload_sha256") != payload_sha256(contract):
        raise RuntimeError(f"R340 {phase} contract hash drift")
    for group in ("sources", "parents"):
        for row in payload.get(group, {}).values():
            if sha256_file(ROOT / str(row["path"])) != row["sha256"]:
                raise RuntimeError(f"sealed {group[:-1]} drift: {row['path']}")
    return payload, digest


def _load_canary_seal(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    payload, digest = read_verified_json(path, expected_sha256=expected_sha256)
    contract = development_canary_contract()
    if (
        payload.get("phase") != "development-canary"
        or payload.get("round") != ROUND_ID
        or payload.get("question") != QUESTION_ID
        or payload.get("formal_evidence") is not False
    ):
        raise RuntimeError("R341 development seal identity mismatch")
    if payload.get("contract") != contract:
        raise RuntimeError("R341 development contract drift")
    if payload.get("contract_payload_sha256") != payload_sha256(contract):
        raise RuntimeError("R341 development contract hash drift")
    for group in ("sources", "parents"):
        for row in payload.get(group, {}).values():
            if sha256_file(ROOT / str(row["path"])) != row["sha256"]:
                raise RuntimeError(f"sealed {group[:-1]} drift: {row['path']}")
    return payload, digest


def _verify_installed_andes(seal: dict[str, Any]) -> dict[str, object]:
    from scripts import run_r334_pq_disturbance_identification as r334

    installed = r334._verify_installed_andes()
    expected = seal["expected_runtime"]
    if importlib.metadata.version("andes") != expected["andes_version"]:
        raise RuntimeError("installed ANDES version drift")
    if installed["sources"] != expected["installed_sources"]:
        raise RuntimeError("installed ANDES source drift")
    if installed["case"]["sha256"] != expected["case_sha256"]:
        raise RuntimeError("installed Kundur case drift")
    return _jsonable(installed)


@contextmanager
def _configured_r339_extractor():
    from scripts import run_r339_input_bridge_diagnosis as r339

    replacements = {
        "ROUND_ID": ROUND_ID,
        "QUESTION_ID": QUESTION_ID,
        "POINTS": POINTS,
        "JOB_SPECS": CANDIDATE_JOBS,
        "WHOLE_HOST_PYTHON_PROCESSES": WHOLE_HOST_PYTHON_PROCESSES,
    }
    previous = {name: getattr(r339, name) for name in replacements}
    for name, value in replacements.items():
        setattr(r339, name, value)
    try:
        yield r339
    finally:
        for name, value in previous.items():
            setattr(r339, name, value)


def _run_candidate_jobs() -> list[dict[str, Any]]:
    if os.name != "posix":
        raise RuntimeError("R340 live candidate construction is WSL/POSIX-only")
    import multiprocessing as mp

    previous_cwd = Path.cwd()
    with _configured_r339_extractor() as r339:
        context = mp.get_context("fork")
        r339._GLOBAL_BARRIER = context.Barrier(WHOLE_HOST_PYTHON_PROCESSES)
        results: list[dict[str, Any]] = []
        try:
            with ProcessPoolExecutor(
                max_workers=WHOLE_HOST_PYTHON_PROCESSES - 1,
                mp_context=context,
            ) as executor:
                futures = [
                    executor.submit(r339._extract_live_job, dict(spec))
                    for spec in CANDIDATE_JOBS[1:]
                ]
                results.append(r339._extract_live_job(dict(CANDIDATE_JOBS[0])))
                for future in as_completed(futures):
                    results.append(future.result())
        finally:
            os.chdir(previous_cwd)
            r339._GLOBAL_BARRIER = None
    results.sort(key=lambda row: (row["point"], row["input_family"], row["channel"]))
    pids = {int(row["job_metadata"]["pid"]) for row in results}
    latest_start = max(int(row["job_metadata"]["started_monotonic_ns"]) for row in results)
    earliest_end = min(int(row["job_metadata"]["ended_monotonic_ns"]) for row in results)
    if len(results) != 16 or len(pids) != 16 or latest_start >= earliest_end:
        raise RuntimeError("R340 candidate sixteen-process concurrency guard failed")
    return results


def _combine_candidate_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from scripts import run_r339_input_bridge_diagnosis as r339

    indexed = {
        (str(row["point"]), str(row["input_family"]), int(row["channel"])): row for row in jobs
    }
    expected = {
        (point, family, channel)
        for point in POINTS
        for family in ("control", "load")
        for channel in range(4)
    }
    if set(indexed) != expected:
        raise RuntimeError("R340 candidate extraction inventory mismatch")
    combined: list[dict[str, Any]] = []
    for point in POINTS:
        families: dict[str, dict[str, Any]] = {}
        for family in ("control", "load"):
            rows = [indexed[(point, family, channel)] for channel in range(4)]
            families[family] = {
                "point": point,
                "input_family": family,
                "base_snapshot_sha256": rows[0]["base_snapshot_sha256"],
                "base_snapshot": rows[0]["base_snapshot"],
                "input_derivatives": r339.combine_family_jobs(rows),
                "job_metadata": [row["job_metadata"] for row in rows],
            }
        combined.append(r339.combine_point_jobs(families["control"], families["load"]))
    return combined


def rehearse_construction(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    """Traverse construction without creating a formal artifact or trajectory."""

    seal, seal_digest = _load_seal(seal_path, expected_sha256, phase="construction")
    _verify_installed_andes(seal)
    if out_dir.exists():
        raise FileExistsError(f"R340 formal output must be absent: {out_dir}")
    jobs = _run_candidate_jobs()
    points = _combine_candidate_jobs(jobs)
    print(f"rehearsal_construction_seal_sha256={seal_digest}")
    print(f"rehearsal_candidate_job_count={len(jobs)}")
    print(f"rehearsal_unique_processes={len({row['job_metadata']['pid'] for row in jobs})}")
    print(f"rehearsal_combined_point_count={len(points)}")
    print("rehearsal_candidate_gate_evaluated=false")
    print("rehearsal_fresh_nonlinear_trajectory_executed=false")
    print("rehearsal_formal_output_created=false")


def construct(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    """Perform the one create-only formal candidate construction."""

    seal, seal_digest = _load_seal(seal_path, expected_sha256, phase="construction")
    installed = _verify_installed_andes(seal)
    if out_dir.exists():
        raise FileExistsError(f"R340 construction output already exists: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=False)
    attempt_digest = write_new_json(
        out_dir / "construction_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "construction_seal_sha256": seal_digest,
            "physical_execution_started": True,
            "fresh_nonlinear_trajectory_started": False,
            "retry_authorized": False,
        },
    )
    try:
        jobs = _run_candidate_jobs()
        points = _combine_candidate_jobs(jobs)
        from probes.r341_staged_fresh_model_validation import build_candidate_bank

        candidates = build_candidate_bank(points)
        candidate_digest = write_new_json(
            out_dir / "candidate_models.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "construction_seal_sha256": seal_digest,
                "construction_attempt_sha256": attempt_digest,
                **candidates,
            },
        )
        execution_digest = write_new_json(
            out_dir / "construction_execution.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "construction_seal_sha256": seal_digest,
                "construction_attempt_sha256": attempt_digest,
                "candidate_models_sha256": candidate_digest,
                "job_count": len(jobs),
                "unique_process_count": len({row["job_metadata"]["pid"] for row in jobs}),
                "points": points,
                "construction_pass": candidates["construction_pass"],
                "fresh_nonlinear_trajectory_executed": False,
                "controller_executed": False,
                "distributed_runtime_executed": False,
                "training_executed": False,
                "eval_executed": False,
            },
        )
        provenance_digest = write_new_json(
            out_dir / "construction_provenance.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "construction_seal_sha256": seal_digest,
                "construction_attempt_sha256": attempt_digest,
                "candidate_models_sha256": candidate_digest,
                "construction_execution_sha256": execution_digest,
                "runtime": {
                    "python": sys.version,
                    "platform": platform.platform(),
                    "andes": installed,
                    "native_threads": {
                        name: os.environ.get(name)
                        for name in (
                            "OMP_NUM_THREADS",
                            "OPENBLAS_NUM_THREADS",
                            "MKL_NUM_THREADS",
                            "NUMEXPR_NUM_THREADS",
                        )
                    },
                },
            },
        )
        manifest_digest = write_new_json(
            out_dir / "construction_manifest.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "entries": [
                    {"path": "construction_attempt.json", "sha256": attempt_digest},
                    {"path": "candidate_models.json", "sha256": candidate_digest},
                    {"path": "construction_execution.json", "sha256": execution_digest},
                    {"path": "construction_provenance.json", "sha256": provenance_digest},
                ],
            },
        )
    except Exception as error:
        write_new_json(
            out_dir / "construction_failure.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "construction_seal_sha256": seal_digest,
                "construction_attempt_sha256": attempt_digest,
                "classification": "INVALID",
                "error_type": type(error).__name__,
                "error_message": str(error),
                "retry_authorized": False,
            },
        )
        raise
    print(f"candidate_models_sha256={candidate_digest}")
    print(f"construction_execution_sha256={execution_digest}")
    print(f"construction_manifest_sha256={manifest_digest}")
    print(f"construction_pass={str(candidates['construction_pass']).lower()}")


def _verified_construction_artifacts(
    out_dir: Path, candidate_sha256: str
) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    manifest, manifest_digest = read_verified_json(out_dir / "construction_manifest.json")
    entries = {str(row["path"]): str(row["sha256"]) for row in manifest.get("entries", [])}
    required = {
        "construction_attempt.json",
        "candidate_models.json",
        "construction_execution.json",
        "construction_provenance.json",
    }
    if set(entries) != required or entries["candidate_models.json"] != candidate_sha256:
        raise RuntimeError("R340 construction manifest inventory mismatch")
    candidate, _ = read_verified_json(
        out_dir / "candidate_models.json", expected_sha256=candidate_sha256
    )
    if candidate.get("construction_pass") is not True:
        raise RuntimeError("R340 candidate construction did not pass")
    paths = {
        "construction_seal": DEFAULT_CONSTRUCTION_SEAL,
        "construction_attempt": out_dir / "construction_attempt.json",
        "candidate_models": out_dir / "candidate_models.json",
        "construction_execution": out_dir / "construction_execution.json",
        "construction_provenance": out_dir / "construction_provenance.json",
        "construction_manifest": out_dir / "construction_manifest.json",
    }
    parents = _parents(paths)
    parents["construction_manifest"]["sha256"] = manifest_digest
    return candidate, parents


def prepare_validation(
    seal_path: Path,
    *,
    candidate_sha256: str,
    out_dir: Path,
    created_utc: str | None = None,
) -> str:
    """Seal the exact constructed candidate before any nonlinear trajectory."""

    candidate, construction_parents = _verified_construction_artifacts(out_dir, candidate_sha256)
    from andes_rl_kundur.evaluation.model_first_profile_feasibility import (
        require_profile_bank_feasible,
    )

    require_profile_bank_feasible(
        _record_specs(),
        lambda spec: _r341_profile_contract(
            channel=spec["channel"],
            shape=str(spec["profile_key"]),
            sign=str(spec["sign"]),
        ),
    )
    contract = build_contract()
    payload = {
        "schema_version": 1,
        "phase": "validation",
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": created_utc or datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": payload_sha256(contract),
        "candidate": {
            "path": _path_text(out_dir / "candidate_models.json"),
            "sha256": candidate_sha256,
            "construction_method": candidate["construction_method"],
            "construction_pass": True,
        },
        "sources": _sources(),
        "parents": construction_parents,
        "expected_runtime": {
            "andes_version": "2.0.0",
            "installed_sources": _expected_installed_sources(),
            "case_sha256": EXPECTED_CASE_SHA256,
        },
        "record_specs": _record_specs(),
        "record_specs_payload_sha256": payload_sha256(_record_specs()),
        "formal_artifacts_create_only": True,
        "formal_retry_authorized": False,
    }
    digest = write_new_json(seal_path, payload)
    print(f"validation_seal_sha256={digest}")
    print(f"candidate_models_sha256={candidate_sha256}")
    return digest


def _load_validation_seal(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    payload, digest = _load_seal(path, expected_sha256, phase="validation")
    if payload.get("record_specs") != _record_specs():
        raise RuntimeError("R340 validation record inventory drift")
    if payload.get("record_specs_payload_sha256") != payload_sha256(_record_specs()):
        raise RuntimeError("R340 validation record inventory hash drift")
    candidate_row = payload.get("candidate", {})
    read_verified_json(
        ROOT / str(candidate_row.get("path")),
        expected_sha256=str(candidate_row.get("sha256")),
    )
    return payload, digest


def rehearse_validation(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    """Verify the sealed candidate and output absence without a trajectory."""

    seal, seal_digest = _load_validation_seal(seal_path, expected_sha256)
    installed = _verify_installed_andes(seal)
    if (out_dir / "formal_attempt.json").exists():
        raise FileExistsError("R340 formal validation attempt already exists")
    print(f"rehearsal_validation_seal_sha256={seal_digest}")
    print(f"rehearsal_candidate_models_sha256={seal['candidate']['sha256']}")
    print(f"rehearsal_installed_case_sha256={installed['case']['sha256']}")
    print("rehearsal_fresh_nonlinear_trajectory_executed=false")
    print("rehearsal_formal_attempt_created=false")


def _profile_values(profile_key: str) -> tuple[float, ...]:
    waveform, amplitude_text = profile_key.split("__", 1)
    amplitude = float(amplitude_text)
    return tuple(amplitude * value for value in WAVEFORMS[waveform])


def _r341_profile_contract(*, channel: dict[str, object] | None, shape: str, sign: str):
    from scripts import run_r335_disturbance_package as base

    if channel is None:
        target = CHANNELS[-1]
        profile = (0.0,)
        prefix = "R341_zero"
    else:
        target = channel
        multiplier = 1.0 if sign == "positive" else -1.0
        profile = tuple(multiplier * value for value in _profile_values(shape))
        prefix = f"R341_{target['device_idx']}_{shape}_{sign}".replace(".", "p")
    return base.TimedPQProfileContract(
        event_prefix=prefix,
        device_idx=str(target["device_idx"]),
        bus_idx=int(target["bus_idx"]),
        initial_active_system_pu=float(target["initial_active_system_pu"]),
        initial_reactive_system_pu=float(target["initial_reactive_system_pu"]),
        delta_profile_system_pu=profile,
        plant_baselines=base.BASELINES,
    )


@contextmanager
def _configured_r336_runtime():
    from scripts import run_r335_disturbance_package as base

    replacements = {
        "ROUND_ID": ROUND_ID,
        "QUESTION_ID": QUESTION_ID,
        "_profile_contract": _r341_profile_contract,
        "TOTAL_STEPS": TOTAL_STEPS,
    }
    previous = {name: getattr(base, name) for name in replacements}
    for name, value in replacements.items():
        setattr(base, name, value)
    try:
        yield base
    finally:
        for name, value in previous.items():
            setattr(base, name, value)


def _run_record_isolated(
    spec: dict[str, Any],
    record_dir: Path,
    trace_path: Path,
    seal_digest: str,
    candidate_digest: str,
) -> dict[str, Any]:
    from scripts import run_r335_disturbance_package as base

    from andes_rl_kundur.env.andes.model_first_contract import Stage1OperatingPoint

    record_dir.mkdir(parents=True, exist_ok=False)
    previous = Path.cwd()
    started_ns = time.monotonic_ns()
    os.chdir(record_dir)
    try:
        point_name = str(spec["point"])
        point = Stage1OperatingPoint(point_name, **POINTS[point_name])
        row = base._run_record(
            point=point,
            channel=spec["channel"],
            shape=str(spec["profile_key"]),
            sign=str(spec["sign"]),
            seal_digest=seal_digest,
            model_digest=candidate_digest,
        )
    finally:
        os.chdir(previous)
    ended_ns = time.monotonic_ns()
    traces = row.pop("traces")
    trace_digest = _write_new_gzip_json(
        trace_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "record_index": int(spec["record_index"]),
            "validation_seal_sha256": seal_digest,
            "candidate_models_sha256": candidate_digest,
            "traces": traces,
        },
    )
    row.update(
        {
            "record_index": int(spec["record_index"]),
            "waveform": str(spec["waveform"]),
            "amplitude_system_pu": float(spec["amplitude_system_pu"]),
            "profile_key": str(spec["profile_key"]),
            "shape": str(spec["waveform"]),
            "worker_pid": os.getpid(),
            "worker_started_monotonic_ns": started_ns,
            "worker_ended_monotonic_ns": ended_ns,
            "trace_count": len(traces),
            "trace_artifact": {
                "path": _path_text(trace_path),
                "sha256": trace_digest,
                "compression": "gzip-canonical-json",
            },
        }
    )
    return row


def _write_new_gzip_json(path: Path, payload: object) -> str:
    """Create one deterministic compressed trace artifact and hash sidecar."""

    sidecar = path.with_suffix(path.suffix + ".sha256")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"create-only compressed artifact already exists: {path}")
    with path.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            stream.write(canonical_json_bytes(payload))
    digest = sha256_file(path)
    with sidecar.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def _run_canary_records(
    *, seal_digest: str, candidate_digest: str, out_dir: Path
) -> list[dict[str, Any]]:
    if os.name != "posix":
        raise RuntimeError("R341 development canary is WSL/POSIX-only")
    import multiprocessing as mp

    specs = _development_record_specs()
    parent_indices = set(range(0, len(specs), WHOLE_HOST_PYTHON_PROCESSES))
    work_root = Path.cwd() / "r341_development_records"
    work_root.mkdir(parents=True, exist_ok=False)
    trace_root = out_dir / "trace_records"
    trace_root.mkdir(parents=False, exist_ok=False)
    directories = {
        int(spec["record_index"]): work_root
        / f"{int(spec['record_index']):02d}_{spec['point']}_{'zero' if spec['channel'] is None else spec['channel']['device_idx']}_{spec['sign']}"
        for spec in specs
    }
    results: list[dict[str, Any]] = []
    with _configured_r336_runtime():
        context = mp.get_context("fork")
        child_specs = [spec for spec in specs if spec["record_index"] not in parent_indices]
        parent_specs = [spec for spec in specs if spec["record_index"] in parent_indices]
        with ProcessPoolExecutor(
            max_workers=WHOLE_HOST_PYTHON_PROCESSES - 1,
            mp_context=context,
        ) as executor:
            futures = [
                executor.submit(
                    _run_record_isolated,
                    spec,
                    directories[int(spec["record_index"])],
                    trace_root / f"record_{int(spec['record_index']):02d}.json.gz",
                    seal_digest,
                    candidate_digest,
                )
                for spec in child_specs
            ]
            for spec in parent_specs:
                results.append(
                    _run_record_isolated(
                        spec,
                        directories[int(spec["record_index"])],
                        trace_root / f"record_{int(spec['record_index']):02d}.json.gz",
                        seal_digest,
                        candidate_digest,
                    )
                )
            for future in as_completed(futures):
                results.append(future.result())
    results.sort(key=lambda row: int(row["record_index"]))
    unique_processes = len({int(row["worker_pid"]) for row in results})
    if len(results) != 18 or not 2 <= unique_processes <= WHOLE_HOST_PYTHON_PROCESSES:
        raise RuntimeError("R341 development process inventory guard failed")
    return results


def canary(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    """Run the frozen exposed-point short canary and retain every outcome."""

    seal, seal_digest = _load_canary_seal(seal_path, expected_sha256)
    installed = _verify_installed_andes(seal)
    if out_dir.exists():
        raise FileExistsError(f"R341 development output already exists: {out_dir}")

    from andes_rl_kundur.evaluation.model_first_profile_feasibility import (
        require_profile_bank_feasible,
    )
    from probes import r341_staged_fresh_model_validation as analysis_probe

    with _development_configuration():
        require_profile_bank_feasible(
            _development_record_specs(),
            lambda spec: _r341_profile_contract(
                channel=spec["channel"],
                shape=str(spec["profile_key"]),
                sign=str(spec["sign"]),
            ),
        )
        out_dir.mkdir(parents=True, exist_ok=False)
        attempt_digest = write_new_json(
            out_dir / "canary_attempt.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "identity": "DEVELOPMENT",
                "created_utc": datetime.now(UTC).isoformat(),
                "development_seal_sha256": seal_digest,
                "formal_evidence": False,
                "retry_authorized": False,
            },
        )
        try:
            jobs = _run_candidate_jobs()
            points = _combine_candidate_jobs(jobs)
            previous_names = analysis_probe.POINT_NAMES
            analysis_probe.POINT_NAMES = tuple(DEVELOPMENT_POINTS)
            try:
                candidate = analysis_probe.build_candidate_bank(points)
            finally:
                analysis_probe.POINT_NAMES = previous_names
            candidate_digest = write_new_json(out_dir / "candidate_models.json", candidate)
            if candidate.get("construction_pass") is not True:
                analysis = {
                    "classification": "BLOCK-CONSTRUCTION",
                    "identity": "DEVELOPMENT",
                    "formal_evidence": False,
                    "construction_pass": False,
                }
                records: list[dict[str, Any]] = []
            else:
                records = _run_canary_records(
                    seal_digest=seal_digest,
                    candidate_digest=candidate_digest,
                    out_dir=out_dir,
                )
                analysis = analysis_probe.analyse_development_canary(
                    candidate_payload=candidate,
                    records=records,
                    chain_valid=True,
                )
            execution_digest = write_new_json(
                out_dir / "canary_execution.json",
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "question": QUESTION_ID,
                    "identity": "DEVELOPMENT",
                    "created_utc": datetime.now(UTC).isoformat(),
                    "development_seal_sha256": seal_digest,
                    "canary_attempt_sha256": attempt_digest,
                    "candidate_models_sha256": candidate_digest,
                    "record_count": len(records),
                    "records": records,
                    "formal_evidence": False,
                    "controller_executed": False,
                    "distributed_runtime_executed": False,
                    "training_executed": False,
                },
            )
            analysis.update(
                {
                    "development_seal_sha256": seal_digest,
                    "candidate_models_sha256": candidate_digest,
                    "canary_execution_sha256": execution_digest,
                }
            )
            analysis_digest = write_new_json(out_dir / "canary_analysis.json", analysis)
            trace_entries = [
                {
                    "path": str(row["trace_artifact"]["path"]),
                    "sha256": str(row["trace_artifact"]["sha256"]),
                }
                for row in records
            ]
            manifest_digest = write_new_json(
                out_dir / "canary_manifest.json",
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "identity": "DEVELOPMENT",
                    "entries": [
                        {"path": "canary_attempt.json", "sha256": attempt_digest},
                        {"path": "candidate_models.json", "sha256": candidate_digest},
                        {"path": "canary_execution.json", "sha256": execution_digest},
                        {"path": "canary_analysis.json", "sha256": analysis_digest},
                        *trace_entries,
                    ],
                    "formal_evidence": False,
                },
            )
        except Exception as error:
            write_new_json(
                out_dir / "canary_failure.json",
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "question": QUESTION_ID,
                    "identity": "DEVELOPMENT",
                    "created_utc": datetime.now(UTC).isoformat(),
                    "development_seal_sha256": seal_digest,
                    "canary_attempt_sha256": attempt_digest,
                    "classification": "INVALID",
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "formal_evidence": False,
                    "retry_authorized": False,
                },
            )
            raise
    print(f"classification={analysis['classification']}")
    print(f"canary_manifest_sha256={manifest_digest}")
    print(f"record_count={len(records)}")
    print(f"andes_version={installed['version'] if 'version' in installed else '2.0.0'}")


def _run_stage_records(
    *,
    specs: list[dict[str, Any]],
    seal_digest: str,
    candidate_digest: str,
    work_root: Path,
    trace_root: Path,
) -> list[dict[str, Any]]:
    if os.name != "posix":
        raise RuntimeError("R341 live nonlinear validation is WSL/POSIX-only")
    import multiprocessing as mp

    parent_positions = set(range(0, len(specs), WHOLE_HOST_PYTHON_PROCESSES))
    parent_specs = [spec for position, spec in enumerate(specs) if position in parent_positions]
    child_specs = [spec for position, spec in enumerate(specs) if position not in parent_positions]
    directories = {
        int(spec["record_index"]): work_root
        / f"{int(spec['record_index']):02d}_{spec['point']}_{'zero' if spec['channel'] is None else spec['channel']['device_idx']}_{spec['waveform']}_{float(spec['amplitude_system_pu']):.2f}_{spec['sign']}"
        for spec in specs
    }
    results: list[dict[str, Any]] = []
    with _configured_r336_runtime():
        context = mp.get_context("fork")
        with ProcessPoolExecutor(
            max_workers=min(WHOLE_HOST_PYTHON_PROCESSES - 1, len(child_specs)),
            mp_context=context,
        ) as executor:
            futures = [
                executor.submit(
                    _run_record_isolated,
                    spec,
                    directories[int(spec["record_index"])],
                    trace_root / f"record_{int(spec['record_index']):02d}.json.gz",
                    seal_digest,
                    candidate_digest,
                )
                for spec in child_specs
            ]
            for spec in parent_specs:
                results.append(
                    _run_record_isolated(
                        spec,
                        directories[int(spec["record_index"])],
                        trace_root / f"record_{int(spec['record_index']):02d}.json.gz",
                        seal_digest,
                        candidate_digest,
                    )
                )
            for future in as_completed(futures):
                results.append(future.result())
    results.sort(key=lambda row: int(row["record_index"]))
    if len(results) != len(specs):
        raise RuntimeError("R341 stage record inventory guard failed")
    return results


def _run_validation_records(
    *,
    seal_digest: str,
    candidate_digest: str,
    candidate_payload: dict[str, Any],
    out_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    from probes.r341_staged_fresh_model_validation import analyse_r341_prefix

    specs_by_index = {int(spec["record_index"]): spec for spec in _record_specs()}
    work_root = Path.cwd() / "r341_staged_fresh_records"
    work_root.mkdir(parents=True, exist_ok=False)
    trace_root = out_dir / "trace_records"
    trace_root.mkdir(parents=False, exist_ok=False)
    stage_root = out_dir / "stages"
    stage_root.mkdir(parents=False, exist_ok=False)
    results: list[dict[str, Any]] = []
    stage_artifacts: list[dict[str, Any]] = []
    terminal_classification = "PASS-PREFIX"
    for stage in staged_bank_schedule():
        stage_name = str(stage["name"])
        indices = [int(index) for index in stage["record_indices"]]
        stage_records = _run_stage_records(
            specs=[specs_by_index[index] for index in indices],
            seal_digest=seal_digest,
            candidate_digest=candidate_digest,
            work_root=work_root,
            trace_root=trace_root,
        )
        results.extend(stage_records)
        results.sort(key=lambda row: int(row["record_index"]))
        if stage_name == "zero":
            valid = all(row.get("record_valid") is True for row in results)
            analysis = {
                "classification": "PASS-PREFIX" if valid else "INVALID",
                "stage": stage_name,
                "record_count": len(results),
                "expected_record_indices": sorted(int(row["record_index"]) for row in results),
                "validity_pass": valid,
                "record_metrics": {},
                "claim_ceiling": "zero-reference prefix only",
            }
        else:
            expected_indices = sorted(int(row["record_index"]) for row in results)
            analysis = analyse_r341_prefix(
                candidate_payload=candidate_payload,
                records=results,
                expected_record_indices=expected_indices,
                stage_name=stage_name,
                chain_valid=True,
            )
        execution_path = stage_root / f"{stage_name}_execution.json"
        execution_digest = write_new_json(
            execution_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "stage": stage_name,
                "created_utc": datetime.now(UTC).isoformat(),
                "validation_seal_sha256": seal_digest,
                "candidate_models_sha256": candidate_digest,
                "record_indices": indices,
                "records": stage_records,
                "unique_process_count": len({row["worker_pid"] for row in stage_records}),
            },
        )
        analysis_path = stage_root / f"{stage_name}_analysis.json"
        analysis_digest = write_new_json(analysis_path, analysis)
        manifest_path = stage_root / f"{stage_name}_manifest.json"
        manifest_digest = write_new_json(
            manifest_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "stage": stage_name,
                "entries": [
                    {"path": _path_text(execution_path), "sha256": execution_digest},
                    {"path": _path_text(analysis_path), "sha256": analysis_digest},
                    *[
                        {
                            "path": str(row["trace_artifact"]["path"]),
                            "sha256": str(row["trace_artifact"]["sha256"]),
                        }
                        for row in stage_records
                    ],
                ],
            },
        )
        terminal_classification = str(analysis["classification"])
        stage_artifacts.append(
            {
                "stage": stage_name,
                "classification": terminal_classification,
                "record_count": len(stage_records),
                "unique_process_count": len({row["worker_pid"] for row in stage_records}),
                "execution": {"path": _path_text(execution_path), "sha256": execution_digest},
                "analysis": {"path": _path_text(analysis_path), "sha256": analysis_digest},
                "manifest": {"path": _path_text(manifest_path), "sha256": manifest_digest},
            }
        )
        if terminal_classification != "PASS-PREFIX":
            break
    return results, stage_artifacts, terminal_classification


def execute(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    """Execute the sealed 66-record nonlinear validation once."""

    seal, seal_digest = _load_validation_seal(seal_path, expected_sha256)
    installed = _verify_installed_andes(seal)
    candidate_path = ROOT / str(seal["candidate"]["path"])
    candidate, candidate_digest = read_verified_json(
        candidate_path, expected_sha256=str(seal["candidate"]["sha256"])
    )
    if candidate.get("construction_pass") is not True:
        raise RuntimeError("R340 sealed candidate did not pass construction")
    attempt_digest = write_new_json(
        out_dir / "formal_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "validation_seal_sha256": seal_digest,
            "candidate_models_sha256": candidate_digest,
            "physical_execution_started": True,
            "fresh_nonlinear_trajectory_started": True,
            "retry_authorized": False,
        },
    )
    try:
        records, stage_artifacts, terminal_classification = _run_validation_records(
            seal_digest=seal_digest,
            candidate_digest=candidate_digest,
            candidate_payload=candidate,
            out_dir=out_dir,
        )
        all_guards = all(row.get("record_valid") is True for row in records)
        execution_digest = write_new_json(
            out_dir / "validation_execution.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "validation_seal_sha256": seal_digest,
                "formal_attempt_sha256": attempt_digest,
                "candidate_models_sha256": candidate_digest,
                "candidate_precedes_every_trajectory": True,
                "record_count": len(records),
                "unique_process_count": len({row["worker_pid"] for row in records}),
                "maximum_stage_process_count": max(
                    int(row["unique_process_count"]) for row in stage_artifacts
                ),
                "formal_bank_complete": len(records) == 66,
                "terminal_stage_classification": terminal_classification,
                "stage_artifacts": stage_artifacts,
                "all_record_guards_pass": all_guards,
                "records": records,
                "controller_executed": False,
                "closed_loop_executed": False,
                "distributed_runtime_executed": False,
                "training_executed": False,
                "eval_executed": False,
            },
        )
        provenance_digest = write_new_json(
            out_dir / "validation_provenance.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "validation_seal_sha256": seal_digest,
                "formal_attempt_sha256": attempt_digest,
                "candidate_models_sha256": candidate_digest,
                "validation_execution_sha256": execution_digest,
                "runtime": {
                    "python": sys.version,
                    "platform": platform.platform(),
                    "andes": installed,
                    "native_threads": {
                        name: os.environ.get(name)
                        for name in (
                            "OMP_NUM_THREADS",
                            "OPENBLAS_NUM_THREADS",
                            "MKL_NUM_THREADS",
                            "NUMEXPR_NUM_THREADS",
                        )
                    },
                },
            },
        )
        manifest_digest = write_new_json(
            out_dir / "validation_manifest.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "entries": [
                    {"path": "formal_attempt.json", "sha256": attempt_digest},
                    {"path": "validation_execution.json", "sha256": execution_digest},
                    {"path": "validation_provenance.json", "sha256": provenance_digest},
                    *[
                        row[kind]
                        for row in stage_artifacts
                        for kind in ("execution", "analysis", "manifest")
                    ],
                    *[
                        {
                            "path": str(row["trace_artifact"]["path"]),
                            "sha256": str(row["trace_artifact"]["sha256"]),
                        }
                        for row in records
                    ],
                ],
            },
        )
    except Exception as error:
        write_new_json(
            out_dir / "validation_failure.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "validation_seal_sha256": seal_digest,
                "formal_attempt_sha256": attempt_digest,
                "candidate_models_sha256": candidate_digest,
                "classification": "INVALID",
                "error_type": type(error).__name__,
                "error_message": str(error),
                "retry_authorized": False,
            },
        )
        raise
    print(f"validation_execution_sha256={execution_digest}")
    print(f"validation_provenance_sha256={provenance_digest}")
    print(f"validation_manifest_sha256={manifest_digest}")
    print(f"record_count={len(records)}")
    print(f"terminal_stage_classification={terminal_classification}")
    print(f"unique_process_count={len({row['worker_pid'] for row in records})}")


def analyse(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    """Replay the sealed R341 full-bank or valid-prefix analysis twice."""

    from probes.r341_staged_fresh_model_validation import (
        analyse_r340_validation,
        analyse_r341_prefix,
    )

    seal, seal_digest = _load_validation_seal(seal_path, expected_sha256)
    candidate, candidate_digest = read_verified_json(
        ROOT / str(seal["candidate"]["path"]),
        expected_sha256=str(seal["candidate"]["sha256"]),
    )
    manifest, manifest_digest = read_verified_json(out_dir / "validation_manifest.json")
    entries = {str(row["path"]): str(row["sha256"]) for row in manifest.get("entries", [])}
    required = {
        "formal_attempt.json",
        "validation_execution.json",
        "validation_provenance.json",
    }
    trace_entries = {
        name: digest for name, digest in entries.items() if name.endswith(".json.gz")
    }
    if set(entries).intersection(required) != required:
        raise RuntimeError("R341 validation manifest inventory mismatch")
    attempt, attempt_digest = read_verified_json(
        out_dir / "formal_attempt.json", expected_sha256=entries["formal_attempt.json"]
    )
    execution, execution_digest = read_verified_json(
        out_dir / "validation_execution.json",
        expected_sha256=entries["validation_execution.json"],
    )
    provenance, provenance_digest = read_verified_json(
        out_dir / "validation_provenance.json",
        expected_sha256=entries["validation_provenance.json"],
    )
    if len(trace_entries) != int(execution.get("record_count", -1)):
        raise RuntimeError("R341 validation trace count mismatch")
    expected_trace_entries = {
        str(row["trace_artifact"]["path"]): str(row["trace_artifact"]["sha256"])
        for row in execution.get("records", [])
    }
    if trace_entries != expected_trace_entries:
        raise RuntimeError("R341 trace manifest does not match execution records")
    for path_text, digest in entries.items():
        artifact_path = out_dir / path_text if "/" not in path_text else ROOT / path_text
        if sha256_file(artifact_path) != digest:
            raise RuntimeError(f"R341 manifest hash mismatch: {path_text}")
    for path_text, digest in trace_entries.items():
        trace_path = ROOT / path_text
        if sha256_file(trace_path) != digest:
            raise RuntimeError(f"R341 compressed trace hash mismatch: {path_text}")
    chain_valid = bool(
        attempt.get("validation_seal_sha256") == seal_digest
        and attempt.get("candidate_models_sha256") == candidate_digest
        and attempt.get("physical_execution_started") is True
        and attempt.get("fresh_nonlinear_trajectory_started") is True
        and attempt.get("retry_authorized") is False
        and execution.get("validation_seal_sha256") == seal_digest
        and execution.get("formal_attempt_sha256") == attempt_digest
        and execution.get("candidate_models_sha256") == candidate_digest
        and 1 <= int(execution.get("maximum_stage_process_count", 0))
        <= WHOLE_HOST_PYTHON_PROCESSES
        and provenance.get("validation_seal_sha256") == seal_digest
        and provenance.get("formal_attempt_sha256") == attempt_digest
        and provenance.get("candidate_models_sha256") == candidate_digest
        and provenance.get("validation_execution_sha256") == execution_digest
        and str(candidate.get("created_utc")) < str(seal.get("created_utc"))
        and str(seal.get("created_utc")) < str(attempt.get("created_utc"))
    )
    if execution.get("formal_bank_complete") is True:
        first = analyse_r340_validation(
            candidate_payload=candidate,
            execution=execution,
            chain_valid=chain_valid,
        )
        second = analyse_r340_validation(
            candidate_payload=candidate,
            execution=execution,
            chain_valid=chain_valid,
        )
    else:
        stage_artifacts = execution.get("stage_artifacts", [])
        if not isinstance(stage_artifacts, list) or not stage_artifacts:
            raise RuntimeError("R341 partial execution lacks a completed stage")
        last_stage = stage_artifacts[-1]
        if last_stage.get("classification") not in {
            "BLOCK-CONSTRUCTION",
            "BLOCK-FULL-LINEARIZATION",
            "BLOCK-REDUCTION",
        }:
            raise RuntimeError("R341 incomplete bank lacks a valid early block")
        indices = sorted(int(row["record_index"]) for row in execution.get("records", []))
        kwargs = {
            "candidate_payload": candidate,
            "records": execution.get("records", []),
            "expected_record_indices": indices,
            "stage_name": str(last_stage["stage"]),
            "chain_valid": chain_valid,
        }
        first = analyse_r341_prefix(**kwargs)
        second = analyse_r341_prefix(**kwargs)
        stored_stage, _ = read_verified_json(
            ROOT / str(last_stage["analysis"]["path"]),
            expected_sha256=str(last_stage["analysis"]["sha256"]),
        )
        if first != stored_stage:
            raise RuntimeError("R341 stored early analysis drift")
    replay_digest = payload_sha256(first)
    if payload_sha256(second) != replay_digest:
        raise RuntimeError("R341 pure analysis is not deterministic")
    analysis_digest = write_new_json(
        out_dir / "analysis.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "validation_seal_sha256": seal_digest,
            "candidate_models_sha256": candidate_digest,
            "formal_attempt_sha256": attempt_digest,
            "validation_execution_sha256": execution_digest,
            "validation_provenance_sha256": provenance_digest,
            "validation_manifest_sha256": manifest_digest,
            "deterministic_replay_payload_sha256": replay_digest,
            **first,
        },
    )
    print(f"classification={first['classification']}")
    print(f"analysis_sha256={analysis_digest}")
    print(f"deterministic_replay_payload_sha256={replay_digest}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_canary_parser = subparsers.add_parser("prepare-canary")
    prepare_canary_parser.add_argument("--seal", type=Path, default=DEFAULT_DEVELOPMENT_SEAL)

    canary_parser = subparsers.add_parser("canary")
    canary_parser.add_argument("--seal", type=Path, default=DEFAULT_DEVELOPMENT_SEAL)
    canary_parser.add_argument("--expected-sha256", required=True)
    canary_parser.add_argument("--out", type=Path, default=DEFAULT_CANARY_OUT)

    prepare_construction_parser = subparsers.add_parser("prepare-construction")
    prepare_construction_parser.add_argument("--seal", type=Path, default=DEFAULT_CONSTRUCTION_SEAL)

    rehearse_construction_parser = subparsers.add_parser("rehearse-construction")
    rehearse_construction_parser.add_argument(
        "--seal", type=Path, default=DEFAULT_CONSTRUCTION_SEAL
    )
    rehearse_construction_parser.add_argument("--expected-sha256", required=True)
    rehearse_construction_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)

    construct_parser = subparsers.add_parser("construct")
    construct_parser.add_argument("--seal", type=Path, default=DEFAULT_CONSTRUCTION_SEAL)
    construct_parser.add_argument("--expected-sha256", required=True)
    construct_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)

    prepare_validation_parser = subparsers.add_parser("prepare-validation")
    prepare_validation_parser.add_argument("--seal", type=Path, default=DEFAULT_VALIDATION_SEAL)
    prepare_validation_parser.add_argument("--candidate-sha256", required=True)
    prepare_validation_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)

    rehearse_validation_parser = subparsers.add_parser("rehearse-validation")
    rehearse_validation_parser.add_argument("--seal", type=Path, default=DEFAULT_VALIDATION_SEAL)
    rehearse_validation_parser.add_argument("--expected-sha256", required=True)
    rehearse_validation_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)

    execute_parser = subparsers.add_parser("execute")
    execute_parser.add_argument("--seal", type=Path, default=DEFAULT_VALIDATION_SEAL)
    execute_parser.add_argument("--expected-sha256", required=True)
    execute_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)

    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--seal", type=Path, default=DEFAULT_VALIDATION_SEAL)
    analyse_parser.add_argument("--expected-sha256", required=True)
    analyse_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "prepare-canary":
        prepare_canary(args.seal)
    elif args.command == "canary":
        canary(args.seal, args.expected_sha256, args.out)
    elif args.command == "prepare-construction":
        prepare_construction(args.seal)
    elif args.command == "rehearse-construction":
        rehearse_construction(args.seal, args.expected_sha256, args.out)
    elif args.command == "construct":
        construct(args.seal, args.expected_sha256, args.out)
    elif args.command == "prepare-validation":
        prepare_validation(
            args.seal,
            candidate_sha256=args.candidate_sha256,
            out_dir=args.out,
        )
    elif args.command == "rehearse-validation":
        rehearse_validation(args.seal, args.expected_sha256, args.out)
    elif args.command == "execute":
        execute(args.seal, args.expected_sha256, args.out)
    elif args.command == "analyse":
        analyse(args.seal, args.expected_sha256, args.out)
    else:
        raise RuntimeError(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
