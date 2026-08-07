"""Stage, execute, and analyse the R344 deterministic physical bridge.

Usage::

    python scripts/run_r344_deterministic_bridge.py prepare
    python scripts/run_r344_deterministic_bridge.py rehearse
    python scripts/run_r344_deterministic_bridge.py capacity-ladder
    python scripts/run_r344_deterministic_bridge.py execute-canaries
    python scripts/run_r344_deterministic_bridge.py execute-formal
    python scripts/run_r344_deterministic_bridge.py analyse

Physical commands are WSL-only and must run through ``scripts/andes_scratch.py``.
The adapter has no training, distributed-runtime, or EVAL entry point.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

THREAD_ENVIRONMENT = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)
for _thread_variable in THREAD_ENVIRONMENT:
    os.environ[_thread_variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

ROUND_ID = "R344"
QUESTION_ID = "Q-0090"
PARENT_SEAL = ROOT / "memory/rounds/R341/validation_seal.json"
CANDIDATE_MODELS = ROOT / "results/r341_staged_fresh_model_validation/candidate_models.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R344/formal_seal.json"
REHEARSAL_RECORD = ROOT / "memory/rounds/R344/rehearsal.json"
CAPACITY_RECORD = ROOT / "memory/rounds/R344/capacity_ladder_attempt_2.json"
DEFAULT_OUT = ROOT / "results/r344_deterministic_bridge"
LOW_AMPLITUDE_BY_DEVICE = {
    "PQ_0": 0.03,
    "PQ_1": 0.03,
    "PQ_Bus14": 0.03,
    "PQ_Bus15": 0.02,
}
OUTPUT_SCALES = {
    "FV0": [
        0.0005208588784582888,
        0.00020891280532014673,
        0.0002641363410614004,
        0.0004599914624251534,
    ],
    "FV1": [
        0.0005014001877174584,
        0.0002058568956880255,
        0.00024780152784620513,
        0.00043006662398575727,
    ],
}
POINT_MODEL_DIGESTS = {
    "FV0": "c858441f0fd48c7f69da98f569bca4a88f3547324af6a301ebf42de60c055cf5",
    "FV1": "c65ead6face6015ed951b7d55b13b90847fb557462ab946d730392666cf9200c",
}


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _payload_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_text(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{_path_text(path)} must contain a JSON object")
    return value


def _write_new_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical_bytes(payload)
    with path.open("xb") as handle:
        handle.write(data)
    digest = hashlib.sha256(data).hexdigest()
    sidecar = path.with_name(path.name + ".sha256")
    with sidecar.open("x", encoding="ascii", newline="\n") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def _write_new_gzip_json(path: Path, payload: object) -> str:
    sidecar = path.with_name(path.name + ".sha256")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"create-only compressed artifact already exists: {path}")
    with path.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            stream.write(_canonical_bytes(payload))
    digest = _sha256_file(path)
    with sidecar.open("x", encoding="ascii", newline="\n") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


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


def _read_hashed_json(path: Path) -> dict[str, Any]:
    sidecar = path.with_name(path.name + ".sha256")
    expected = sidecar.read_text(encoding="ascii").split()[0].lower()
    actual = _sha256_file(path)
    if actual != expected:
        raise ValueError(f"hash mismatch: {path}")
    return _read_json(path)


def _parent_contract() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    parent = _read_json(PARENT_SEAL)
    if _sha256_file(PARENT_SEAL) != (
        "27bd29f9a9e15f0d1dea8c84608b8cd37cbaafe404dbcc9a78582bbb9d4d1815"
    ):
        raise RuntimeError("R341 validation seal drift")
    if _sha256_file(CANDIDATE_MODELS) != (
        "7a74cb78dca8c5e30f32a344ca43704079a1549c966ff21de492eba7a3f1e32e"
    ):
        raise RuntimeError("R341 candidate model drift")
    specs = parent.get("record_specs")
    if not isinstance(specs, list) or len(specs) != 66:
        raise RuntimeError("R341 record inventory drift")
    return parent, specs


def control_coordinate_basis():
    """Return the frozen common-plus-action-tree node-power basis."""

    import numpy as np

    from andes_rl_kundur.env.andes.model_first_contract import (
        active_power_incidence,
    )

    return np.column_stack((np.ones(4), active_power_incidence()))


def build_point_controller(point: str):
    """Load one exact R341 order-12 object and build the frozen controller."""

    import numpy as np

    from andes_rl_kundur.control.model_first_separate_input import (
        SeparateInputHorizonController,
        SeparateInputRealization,
    )
    from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
        StateSpaceRealization,
    )

    if point not in POINT_MODEL_DIGESTS:
        raise ValueError(f"unknown R344 operating point: {point}")
    candidate = _read_json(CANDIDATE_MODELS)
    raw = candidate["points"][point]["order12"]
    digest = _payload_sha256(raw)
    if digest != POINT_MODEL_DIGESTS[point]:
        raise RuntimeError(f"R341 {point} order-12 object drift")
    realization = StateSpaceRealization(
        state_matrix=np.asarray(raw["state_matrix"], dtype=float),
        input_matrix=np.asarray(raw["input_matrix"], dtype=float),
        output_matrix=np.asarray(raw["output_matrix"], dtype=float),
        feedthrough_matrix=np.asarray(raw["feedthrough_matrix"], dtype=float),
        retained_singular_values=np.asarray(
            raw["retained_singular_values"], dtype=float
        ),
    )
    controller = SeparateInputHorizonController(
        SeparateInputRealization.from_joint(realization),
        output_scales=OUTPUT_SCALES[point],
        action_scales=np.full(4, 0.36),
        horizon_steps=25,
        disturbance_scale=0.05,
        measurement_fraction=0.01,
        maximum_solver_iterations=20_000,
        absolute_solver_tolerance=1.0e-9,
        relative_solver_tolerance=1.0e-9,
        feasibility_tolerance=1.0e-8,
    )
    return controller, {
        "point": point,
        "candidate_models_sha256": _sha256_file(CANDIDATE_MODELS),
        "order12_canonical_sha256": digest,
        "controller": asdict(controller.identity),
        "observability_rank": controller.estimator.observability_rank,
        "estimator_error_pole_radius": controller.estimator.error_pole_radius,
        "estimator_normalized_covariance_residual": (
            controller.estimator.normalized_covariance_residual
        ),
    }


def select_capacity_rung(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Select maximum measured throughput without looking at endpoints."""

    valid = []
    for row in results:
        throughput = float(row.get("throughput_jobs_per_second", math.nan))
        workers = int(row.get("worker_processes", 0))
        if row.get("valid") is True and workers > 0 and math.isfinite(throughput):
            valid.append(row)
    if not valid:
        raise ValueError("no valid capacity rung")
    return max(
        valid,
        key=lambda row: (
            float(row["throughput_jobs_per_second"]),
            -int(row["worker_processes"]),
        ),
    )


def classify_formal_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply the frozen paired deterministic-bridge stop tree."""

    endpoints = (
        "common_coordinate_iae",
        "differential_coordinate_energy",
    )
    if not records or any(row.get("integrity_valid") is not True for row in records):
        return {
            "classification": "INVALID-DETERMINISTIC-BRIDGE",
            "guards": {"integrity": False},
        }
    if any(
        row.get("physical_guards_pass") is not True
        or int(row.get("fallback_count", 0)) != 0
        for row in records
    ):
        return {
            "classification": "DETERMINISTIC-PHYSICAL-GUARD-FAIL",
            "guards": {"integrity": True, "physical": False},
        }

    pairs: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    try:
        for row in records:
            point = str(row["point"])
            scenario = str(row["scenario_id"])
            arm = str(row["arm"])
            if point not in ("FV0", "FV1") or arm not in (
                "zero_control",
                "frozen_controller",
            ):
                raise ValueError
            metrics = row["metrics"]
            if not isinstance(metrics, dict) or any(
                not math.isfinite(float(metrics[name])) or float(metrics[name]) < 0.0
                for name in endpoints
            ):
                raise ValueError
            arms = pairs.setdefault((point, scenario), {})
            if arm in arms:
                raise ValueError
            arms[arm] = row
    except (KeyError, TypeError, ValueError):
        return {
            "classification": "INVALID-DETERMINISTIC-BRIDGE",
            "guards": {"integrity": False, "complete_paired_inventory": False},
        }
    complete_inventory = len(records) == 32 and len(pairs) == 16 and all(
        set(arms) == {"zero_control", "frozen_controller"}
        for arms in pairs.values()
    )
    if not complete_inventory:
        return {
            "classification": "INVALID-DETERMINISTIC-BRIDGE",
            "guards": {"integrity": False, "complete_paired_inventory": False},
        }

    mean_improvement: dict[str, float] = {}
    point_directional: dict[str, dict[str, bool]] = {}
    scenario_no_harm = True
    for endpoint in endpoints:
        zero_values = []
        controlled_values = []
        for arms in pairs.values():
            zero = float(arms["zero_control"]["metrics"][endpoint])
            controlled = float(arms["frozen_controller"]["metrics"][endpoint])
            if zero <= 0.0:
                return {
                    "classification": "INVALID-DETERMINISTIC-BRIDGE",
                    "guards": {"integrity": False, "positive_zero_endpoint": False},
                }
            zero_values.append(zero)
            controlled_values.append(controlled)
            scenario_no_harm = scenario_no_harm and controlled <= 1.05 * zero
        zero_mean = sum(zero_values) / len(zero_values)
        controlled_mean = sum(controlled_values) / len(controlled_values)
        mean_improvement[endpoint] = (zero_mean - controlled_mean) / zero_mean
        for point in ("FV0", "FV1"):
            point_pairs = [arms for (pair_point, _), arms in pairs.items() if pair_point == point]
            point_zero = sum(
                float(arms["zero_control"]["metrics"][endpoint])
                for arms in point_pairs
            ) / len(point_pairs)
            point_controlled = sum(
                float(arms["frozen_controller"]["metrics"][endpoint])
                for arms in point_pairs
            ) / len(point_pairs)
            point_directional.setdefault(point, {})[endpoint] = (
                point_controlled < point_zero
            )

    engagement = all(
        arms["frozen_controller"].get("controller_engaged") is True
        for arms in pairs.values()
    )
    material = all(value >= 0.02 for value in mean_improvement.values())
    directional = all(
        value for point in point_directional.values() for value in point.values()
    )
    efficacy_pass = engagement and material and directional and scenario_no_harm
    return {
        "classification": (
            "DETERMINISTIC-BRIDGE-PASS"
            if efficacy_pass
            else "VALID-NO-DETERMINISTIC-BENEFIT"
        ),
        "paired_mean_improvement_fraction": mean_improvement,
        "point_directional_improvement": point_directional,
        "guards": {
            "integrity": True,
            "physical": True,
            "complete_paired_inventory": True,
            "controller_engagement": engagement,
            "minimum_mean_improvement": material,
            "point_directional_improvement": directional,
            "maximum_scenario_worsening": scenario_no_harm,
        },
    }


def _is_low_amplitude(spec: dict[str, Any]) -> bool:
    channel = spec.get("channel")
    if not isinstance(channel, dict):
        return False
    device = str(channel.get("device_idx"))
    expected = LOW_AMPLITUDE_BY_DEVICE.get(device)
    return expected is not None and float(spec.get("amplitude_system_pu", -1.0)) == expected


def build_contract() -> dict[str, Any]:
    """Return the prospective R344 controller, inventory, and stop contract."""

    parent, specs = _parent_contract()
    zero_jobs = [spec for spec in specs if spec.get("waveform") == "zero"]
    capacity_jobs = [
        spec
        for spec in specs
        if spec.get("waveform") in ("ramp_hold_unit", "separated_pulse_unit")
        and _is_low_amplitude(spec)
    ]
    formal_scenarios = [
        spec
        for spec in capacity_jobs
        if spec.get("waveform") == "ramp_hold_unit"
    ]
    signed_authority_jobs = [
        {
            "point": point,
            "coordinate_index": coordinate,
            "sign": sign,
            "magnitude_system_pu": 0.05,
            "active_intervals": 5,
            "recovery_intervals": 20,
        }
        for point in ("FV0", "FV1")
        for coordinate in range(4)
        for sign in (-1, 1)
    ]
    if not (
        len(zero_jobs) == 2
        and len(capacity_jobs) == 32
        and len(formal_scenarios) == 16
        and len(signed_authority_jobs) == 16
    ):
        raise RuntimeError("R344 staged inventory does not match the frozen plan")
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "separate-input-deterministic-physical-bridge",
        "parent_round": "R341",
        "parent_claim": "CLM-0900",
        "points": parent["contract"]["operating_points"],
        "controller": {
            "family": "centralized-full-output-constrained-horizon",
            "information_pattern": "full-output-centralized",
            "input_contract": "four-control-plus-four-disturbance",
            "horizon_steps": 25,
            "output_scales_by_point": OUTPUT_SCALES,
            "action_scales_system_pu": [0.36] * 4,
            "estimator_augmented_order": 16,
            "disturbance_scale_system_pu": 0.05,
            "measurement_fraction": 0.01,
            "solver": "osqp-builtin-direct",
            "solver_version": "1.1.3",
            "solver_algebra": "builtin",
            "maximum_solver_iterations": 20_000,
            "absolute_solver_tolerance": 1.0e-9,
            "relative_solver_tolerance": 1.0e-9,
            "feasibility_tolerance": 1.0e-8,
            "fallback": "bounded-ramp-toward-zero",
            "fallback_is_formal_failure": True,
        },
        "capacity": {
            "job_count": len(capacity_jobs),
            "jobs": capacity_jobs,
            "worker_rungs": [16, 24, 32],
            "native_threads_per_worker": 1,
            "selection": "highest-valid-completed-job-throughput",
            "minimum_wsl_available_memory_bytes": 4 * 1024**3,
            "swap_use_allowed": False,
        },
        "canaries": {
            "zero_action_job_count": len(zero_jobs),
            "zero_action_jobs": zero_jobs,
            "zero_action_intervals": 5,
            "zero_request_absolute_tolerance_system_pu": 1.0e-8,
            "zero_soc_drift_absolute_tolerance": 1.0e-8,
            "zero_equilibrium_algebraic_residual_absolute_tolerance": 1.0e-8,
            "signed_authority_job_count": len(signed_authority_jobs),
            "signed_authority_jobs": signed_authority_jobs,
            "request_command_absolute_tolerance_system_pu": 1.0e-12,
            "final_active_relative_achieved_error": 0.05,
            "edge_command_neutrality_absolute_tolerance_system_pu": 1.0e-12,
            "edge_achieved_imbalance_fraction_of_command_l1": 0.05,
            "automatic_formal_release": False,
        },
        "physical_guards": {
            "time_increment_seconds": 0.2,
            "time_absolute_tolerance_seconds": 1.0e-9,
            "algebraic_residual_absolute_maximum": 1.0e-6,
            "scheduled_md_absolute_tolerance": 1.0e-10,
            "soc_range": [0.2, 0.8],
            "node_power_absolute_maximum_system_pu": 0.36,
            "node_ramp_absolute_maximum_system_pu": 0.072,
            "line_8_required": True,
            "g4_required": True,
            "external_saturation_allowed": False,
            "internal_limiter_allowed": False,
            "solver_fallback_allowed": False,
        },
        "formal": {
            "scenario_count": len(formal_scenarios),
            "scenarios": formal_scenarios,
            "arms": ["zero_control", "frozen_controller"],
            "trajectory_count": 2 * len(formal_scenarios),
            "total_steps": 25,
            "sample_period_seconds": 0.2,
            "amplitude_by_device_system_pu": LOW_AMPLITUDE_BY_DEVICE,
            "minimum_mean_improvement_fraction": 0.02,
            "maximum_single_scenario_worsening_fraction": 0.05,
            "formal_retry_authorized": False,
        },
        "training_executed": False,
        "distributed_runtime_executed": False,
        "eval_executed": False,
        "topology_change_executed": False,
    }


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R344/plan.md",
        "parent_validation_seal": PARENT_SEAL,
        "candidate_models": CANDIDATE_MODELS,
        "controller": ROOT / "src/andes_rl_kundur/control/model_first_separate_input.py",
        "bridge_metrics": ROOT
        / "src/andes_rl_kundur/evaluation/model_first_physical_bridge.py",
        "environment": ROOT / "src/andes_rl_kundur/env/andes/model_first_env.py",
        "profile": ROOT / "src/andes_rl_kundur/env/andes/model_first_pq_profile.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "installed_runtime_verifier": ROOT
        / "scripts/run_r334_pq_disturbance_identification.py",
        "inherited_profile_runtime": ROOT
        / "scripts/run_r341_staged_fresh_model_validation.py",
        "adapter": Path(__file__).resolve(),
        "controller_tests": ROOT / "tests/test_model_first_separate_input.py",
        "bridge_tests": ROOT / "tests/test_model_first_physical_bridge.py",
        "adapter_tests": ROOT / "tests/test_r344_deterministic_bridge.py",
        "project_dependencies": ROOT / "pyproject.toml",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _installed_andes_identity() -> dict[str, Any]:
    from scripts import run_r334_pq_disturbance_identification as r334

    return r334._verify_installed_andes()


def _distribution_hash(name: str) -> str:
    distribution = importlib.metadata.distribution(name)
    digest = hashlib.sha256()
    digest.update(b"python-distribution-v1\0")
    for item in sorted(
        distribution.files or (), key=lambda value: str(value).replace("\\", "/")
    ):
        path = Path(distribution.locate_file(item))
        if not path.is_file():
            raise RuntimeError(f"installed distribution file is missing: {item}")
        digest.update(str(item).replace("\\", "/").encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_sha256_file(path)))
    return digest.hexdigest()


def _numerical_runtime_identity() -> dict[str, Any]:
    import numpy as np
    import osqp
    import scipy

    executable = Path(sys.executable).resolve()
    identity = {
        "python_version": platform.python_version(),
        "python_executable_sha256": _sha256_file(executable),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "osqp_version": osqp.__version__,
        "osqp_algebra": osqp.default_algebra(),
        "osqp_distribution_sha256": _distribution_hash("osqp"),
    }
    if identity["osqp_version"] != "1.1.3" or identity["osqp_algebra"] != "builtin":
        raise RuntimeError(f"R344 numerical runtime drift: {identity}")
    return identity


def _r344_python_process_count() -> int:
    if os.name != "posix":
        return 0
    count = 0
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            )
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if "python" in command and "run_r344_deterministic_bridge.py" in command:
            count += 1
    return count


def _formal_output_paths(out_dir: Path = DEFAULT_OUT) -> list[Path]:
    return [
        DEFAULT_SEAL,
        out_dir / "canary_attempt.json",
        out_dir / "canary_execution.json",
        out_dir / "canary_failure.json",
        out_dir / "formal_attempt.json",
        out_dir / "formal_execution.json",
        out_dir / "formal_analysis.json",
        out_dir / "formal_failure.json",
        out_dir / "formal_traces",
    ]


def pre_attempt_checks(
    *,
    output_paths: list[Path] | None = None,
    cwd: Path | None = None,
    scratch_root: Path | None = None,
) -> dict[str, Any]:
    """Run the same identity and isolation checks used before live stages."""

    current = (cwd or Path.cwd()).resolve()
    allowed_root = (scratch_root or (ROOT / "tmp/andes")).resolve()
    if current == ROOT.resolve() or not current.is_relative_to(allowed_root):
        raise RuntimeError(
            f"R344 scratch isolation failed: cwd={current}, root={allowed_root}"
        )
    paths_to_check = output_paths if output_paths is not None else _formal_output_paths()
    existing = [path for path in paths_to_check if path.exists()]
    if existing:
        rendered = ", ".join(str(path) for path in existing)
        raise FileExistsError(f"pre-existing R344 formal asset: {rendered}")
    installed = _installed_andes_identity()
    if not installed.get("version") or not installed.get("sources"):
        raise RuntimeError("installed ANDES package identity is incomplete")
    case = installed.get("case")
    if not isinstance(case, dict) or not case.get("sha256"):
        raise RuntimeError("installed Kundur case identity is incomplete")
    process_count = _r344_python_process_count()
    if process_count > 1:
        raise RuntimeError(f"R344 rehearsal process budget exceeded: {process_count} > 1")
    thread_values = {name: os.environ.get(name) for name in THREAD_ENVIRONMENT}
    if set(thread_values.values()) != {"1"}:
        raise RuntimeError(f"native thread contract drift: {thread_values}")
    contract = build_contract()
    encoded = _canonical_bytes(contract)
    manifest_roundtrip = json.loads(encoded.decode("utf-8")) == contract
    if not manifest_roundtrip:
        raise RuntimeError("R344 manifest canonical roundtrip failed")
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "checks": {
            "source_hash": True,
            "parent_hash": True,
            "installed_package": True,
            "installed_case": True,
            "manifest_roundtrip": True,
            "output_absence": True,
            "process_budget": True,
            "scratch_isolation": True,
        },
        "sources": _sources(),
        "parent_validation_seal_sha256": _sha256_file(PARENT_SEAL),
        "candidate_models_sha256": _sha256_file(CANDIDATE_MODELS),
        "installed_andes": installed,
        "numerical_runtime": _numerical_runtime_identity(),
        "contract_payload_sha256": hashlib.sha256(encoded).hexdigest(),
        "manifest_roundtrip": manifest_roundtrip,
        "scratch_isolation": True,
        "scratch_directory": str(current),
        "wsl_python_processes": process_count,
        "native_threads_per_process": 1,
        "thread_environment": thread_values,
    }


def rehearse(
    *,
    record_path: Path = REHEARSAL_RECORD,
    output_paths: list[Path] | None = None,
    cwd: Path | None = None,
    scratch_root: Path | None = None,
) -> str:
    """Persist one create-only, no-trajectory same-path rehearsal."""

    payload = {
        **pre_attempt_checks(
            output_paths=output_paths,
            cwd=cwd,
            scratch_root=scratch_root,
        ),
        "phase": "same-pre-attempt-path-rehearsal",
        "physical_trajectory_executed": False,
        "formal_attempt_created": False,
        "formal_seal_created": False,
        "training_executed": False,
        "distributed_runtime_executed": False,
        "eval_executed": False,
    }
    return _write_new_json(record_path, payload)


def _plan_launch_fields() -> dict[str, int]:
    text = (ROOT / "memory/rounds/R344/plan.md").read_text(encoding="utf-8")
    values = {}
    for name in (
        "wsl_python_processes",
        "host_process_budget",
        "other_reserved_processes",
    ):
        match = re.search(rf"(?m)^- {name}:\s*(\d+)\s*$", text)
        if match is None:
            raise RuntimeError(f"R344 plan is missing launch field: {name}")
        values[name] = int(match.group(1))
    return values


def _verified_launch_prerequisites() -> dict[str, Any]:
    """Verify post-capacity readiness before creating the formal seal."""

    rehearsal = _read_hashed_json(REHEARSAL_RECORD)
    capacity = _read_hashed_json(CAPACITY_RECORD)
    capacity_digest = _sha256_file(CAPACITY_RECORD)
    host_path = ROOT / "memory/rounds/R344/host_capacity.json"
    host = _read_json(host_path)
    selected = int(capacity.get("selected_worker_processes", 0))
    if selected not in build_contract()["capacity"]["worker_rungs"]:
        raise RuntimeError("R344 capacity selection is not a frozen rung")
    if (
        capacity.get("performance_endpoints_inspected") is not False
        or capacity.get("formal_output_created") is not False
        or capacity.get("training_executed") is not False
    ):
        raise RuntimeError("R344 capacity artifact crossed the non-claiming boundary")
    current_installed = _installed_andes_identity()
    current_runtime = _numerical_runtime_identity()
    if (
        rehearsal.get("sources") != _sources()
        or rehearsal.get("parent_validation_seal_sha256") != _sha256_file(PARENT_SEAL)
        or rehearsal.get("candidate_models_sha256") != _sha256_file(CANDIDATE_MODELS)
        or rehearsal.get("contract_payload_sha256") != _payload_sha256(build_contract())
        or rehearsal.get("installed_andes") != current_installed
        or rehearsal.get("numerical_runtime") != current_runtime
        or rehearsal.get("physical_trajectory_executed") is not False
        or rehearsal.get("formal_attempt_created") is not False
        or rehearsal.get("formal_seal_created") is not False
    ):
        raise RuntimeError("R344 rehearsal identity or no-output boundary drift")
    capacity_binding = host.get("capacity_ladder")
    if not isinstance(capacity_binding, dict):
        raise RuntimeError("R344 host capacity is missing ladder binding")
    if (
        host.get("execution_readiness") != "READY"
        or int(host.get("whole_host_python_process_budget", 0)) != selected
        or int(host.get("other_reserved_processes", -1)) != 0
        or int(host.get("available_processes_for_r344", 0)) != selected
        or int(host.get("native_threads_per_process", 0)) != 1
        or capacity_binding.get("sha256") != capacity_digest
        or int(capacity_binding.get("selected_worker_processes", 0)) != selected
    ):
        raise RuntimeError("R344 host capacity is not READY for the selected rung")
    plan_fields = _plan_launch_fields()
    if plan_fields != {
        "wsl_python_processes": selected,
        "host_process_budget": selected,
        "other_reserved_processes": 0,
    }:
        raise RuntimeError("R344 plan launch fields do not match measured capacity")
    return {
        "worker_processes": selected,
        "native_threads_per_process": 1,
        "other_reserved_processes": 0,
        "installed_andes": current_installed,
        "numerical_runtime": current_runtime,
        "rehearsal": {
            "path": _path_text(REHEARSAL_RECORD),
            "sha256": _sha256_file(REHEARSAL_RECORD),
        },
        "capacity": {
            "path": _path_text(CAPACITY_RECORD),
            "sha256": capacity_digest,
        },
        "host_capacity": {
            "path": _path_text(host_path),
            "sha256": _sha256_file(host_path),
        },
    }


def _round_state(round_id: str) -> str:
    plan = ROOT / f"memory/rounds/{round_id}/plan.md"
    text = plan.read_text(encoding="utf-8")
    match = re.search(r"(?m)^state:\s*([^\s#]+)", text)
    if match is None:
        raise RuntimeError(f"cannot determine {round_id} state")
    return match.group(1).strip()


def _other_research_python_processes() -> list[dict[str, Any]]:
    if os.name != "posix":
        return []
    rows = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            )
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        research_entry = any(
            token in command
            for token in (
                "andes_scratch.py",
                "scripts/run_r",
                "scripts/train.py",
                "scripts/eval_",
                "scripts/score_",
                "run_parallel_wsl_shards.py",
            )
        )
        if (
            "python" in command
            and research_entry
            and "run_r344_deterministic_bridge.py" not in command
        ):
            rows.append({"pid": int(entry.name), "command": command})
    return rows


def assert_capacity_available() -> None:
    """Refuse the ladder while another manuscript retains the whole host."""

    state = _round_state("R343")
    if state == "active":
        raise RuntimeError("R343 still reserves the accepted whole-host process budget")
    others = _other_research_python_processes()
    if others:
        raise RuntimeError(f"other research Python processes are active: {others}")


def _linux_memory_snapshot() -> dict[str, int]:
    if os.name != "posix":
        raise RuntimeError("R344 capacity measurement is WSL/POSIX-only")
    values: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        name, raw = line.split(":", 1)
        fields = raw.strip().split()
        if fields:
            values[name] = int(fields[0]) * 1024
    required = ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree")
    if any(name not in values for name in required):
        raise RuntimeError("incomplete /proc/meminfo capacity snapshot")
    return {name: values[name] for name in required}


def _maximum_interval_overlap(records: list[dict[str, Any]]) -> int:
    events = []
    for row in records:
        events.append((int(row["worker_started_monotonic_ns"]), 1))
        events.append((int(row["worker_ended_monotonic_ns"]), -1))
    active = 0
    maximum = 0
    for _, delta in sorted(events, key=lambda item: (item[0], -item[1])):
        active += delta
        maximum = max(maximum, active)
    return maximum


def _capacity_worker(
    spec: dict[str, Any],
    *,
    record_dir: Path,
    trace_path: Path,
) -> dict[str, Any]:
    import resource

    from scripts import run_r341_staged_fresh_model_validation as r341

    row = r341._run_record_isolated(
        spec,
        record_dir,
        trace_path,
        "R344-capacity-non-claiming",
        _sha256_file(CANDIDATE_MODELS),
    )
    usage = resource.getrusage(resource.RUSAGE_SELF)
    row.update(
        {
            "capacity_non_claiming": True,
            "capacity_endpoint_selection": False,
            "capacity_record_dir": str(record_dir),
            "maximum_resident_set_kib": int(usage.ru_maxrss),
            "process_cpu_seconds": float(usage.ru_utime + usage.ru_stime),
        }
    )
    return row


def _run_capacity_rung(
    *,
    worker_processes: int,
    specs: list[dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    if os.name != "posix":
        raise RuntimeError("R344 capacity ladder is WSL/POSIX-only")
    import multiprocessing as mp

    from scripts import run_r341_staged_fresh_model_validation as r341

    if worker_processes < 2 or worker_processes > len(specs):
        raise ValueError("worker_processes is outside the representative inventory")
    rung_dir = out_dir / f"rung_{worker_processes:02d}"
    trace_root = rung_dir / "traces"
    trace_root.mkdir(parents=True, exist_ok=False)
    work_root = Path.cwd() / f"r344_capacity_{worker_processes:02d}"
    work_root.mkdir(parents=True, exist_ok=False)
    indexed = list(enumerate(specs))
    parent_positions = set(range(0, len(indexed), worker_processes))
    parent_jobs = [item for item in indexed if item[0] in parent_positions]
    child_jobs = [item for item in indexed if item[0] not in parent_positions]
    start_memory = _linux_memory_snapshot()
    memory_samples = [start_memory]
    stop_monitor = threading.Event()

    def monitor() -> None:
        while not stop_monitor.wait(0.1):
            memory_samples.append(_linux_memory_snapshot())

    def paths(index: int, spec: dict[str, Any]) -> tuple[Path, Path]:
        label = (
            f"{index:02d}_{spec['point']}_{spec['channel']['device_idx']}_"
            f"{spec['waveform']}_{spec['sign']}"
        )
        return work_root / label, trace_root / f"job_{index:02d}.json.gz"

    context = mp.get_context("fork")
    results: list[dict[str, Any]] = []
    started = time.monotonic()
    previous_steps = r341.TOTAL_STEPS
    r341.TOTAL_STEPS = 25
    try:
        with r341._configured_r336_runtime():
            with ProcessPoolExecutor(
                max_workers=worker_processes - 1,
                mp_context=context,
            ) as executor:
                futures = []
                for index, spec in child_jobs:
                    record_dir, trace_path = paths(index, spec)
                    futures.append(
                        executor.submit(
                            _capacity_worker,
                            dict(spec),
                            record_dir=record_dir,
                            trace_path=trace_path,
                        )
                    )
                monitor_thread = threading.Thread(target=monitor, daemon=True)
                monitor_thread.start()
                try:
                    for index, spec in parent_jobs:
                        record_dir, trace_path = paths(index, spec)
                        results.append(
                            _capacity_worker(
                                dict(spec),
                                record_dir=record_dir,
                                trace_path=trace_path,
                            )
                        )
                    for future in as_completed(futures):
                        results.append(future.result())
                finally:
                    stop_monitor.set()
                    monitor_thread.join()
    finally:
        r341.TOTAL_STEPS = previous_steps
    elapsed = time.monotonic() - started
    memory_samples.append(_linux_memory_snapshot())
    results.sort(key=lambda row: int(row["record_index"]))
    expected_processes = min(worker_processes, len(specs))
    unique_processes = len({int(row["worker_pid"]) for row in results})
    maximum_overlap = _maximum_interval_overlap(results)
    minimum_available = min(row["MemAvailable"] for row in memory_samples)
    minimum_swap_free = min(row["SwapFree"] for row in memory_samples)
    swap_use = minimum_swap_free < start_memory["SwapFree"]
    isolation = len({str(row["capacity_record_dir"]) for row in results}) == len(
        results
    ) and all(Path(str(row["capacity_record_dir"])).is_relative_to(work_root) for row in results)
    all_completed = len(results) == len(specs) and all(
        row.get("record_valid") is True for row in results
    )
    valid = bool(
        all_completed
        and unique_processes == expected_processes
        and maximum_overlap == expected_processes
        and isolation
        and not swap_use
        and minimum_available >= 4 * 1024**3
    )
    execution = {
        "schema_version": 1,
        "round": ROUND_ID,
        "phase": "non-claiming-capacity-rung",
        "worker_processes": worker_processes,
        "native_threads_per_process": 1,
        "job_count": len(specs),
        "completed_job_count": len(results),
        "elapsed_seconds": elapsed,
        "throughput_jobs_per_second": len(results) / elapsed,
        "unique_python_processes": unique_processes,
        "maximum_interval_overlap": maximum_overlap,
        "scratch_isolation": isolation,
        "memory_start": start_memory,
        "minimum_wsl_available_memory_bytes": minimum_available,
        "swap_use_detected": swap_use,
        "maximum_worker_resident_set_kib": max(
            int(row["maximum_resident_set_kib"]) for row in results
        ),
        "all_jobs_completed_and_valid": all_completed,
        "valid": valid,
        "performance_endpoints_inspected": False,
        "formal_output_created": False,
        "records": results,
    }
    digest = _write_new_json(rung_dir / "execution.json", execution)
    return {
        key: execution[key]
        for key in (
            "worker_processes",
            "native_threads_per_process",
            "job_count",
            "completed_job_count",
            "elapsed_seconds",
            "throughput_jobs_per_second",
            "unique_python_processes",
            "maximum_interval_overlap",
            "scratch_isolation",
            "minimum_wsl_available_memory_bytes",
            "swap_use_detected",
            "maximum_worker_resident_set_kib",
            "all_jobs_completed_and_valid",
            "valid",
        )
    } | {
        "execution": {"path": _path_text(rung_dir / "execution.json"), "sha256": digest}
    }


def run_capacity_ladder(
    *,
    out_dir: Path = DEFAULT_OUT / "capacity_attempt_2",
    record_path: Path = CAPACITY_RECORD,
) -> str:
    """Measure 16/24/32 single-thread rungs and freeze the fastest valid one."""

    assert_capacity_available()
    if out_dir.exists() or record_path.exists():
        raise FileExistsError("R344 capacity ladder is create-only")
    contract = build_contract()
    specs = [dict(row) for row in contract["capacity"]["jobs"]]
    out_dir.mkdir(parents=True, exist_ok=False)
    results = []
    for worker_processes in contract["capacity"]["worker_rungs"]:
        try:
            row = _run_capacity_rung(
                worker_processes=int(worker_processes),
                specs=specs,
                out_dir=out_dir,
            )
        except Exception as error:
            failure_path = out_dir / f"rung_{int(worker_processes):02d}/failure.json"
            failure_digest = _write_new_json(
                failure_path,
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "phase": "non-claiming-capacity-rung-failure",
                    "worker_processes": int(worker_processes),
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "valid": False,
                    "performance_endpoints_inspected": False,
                    "formal_output_created": False,
                },
            )
            row = {
                "worker_processes": int(worker_processes),
                "native_threads_per_process": 1,
                "job_count": len(specs),
                "completed_job_count": 0,
                "throughput_jobs_per_second": 0.0,
                "valid": False,
                "failure": {
                    "path": _path_text(failure_path),
                    "sha256": failure_digest,
                },
            }
        results.append(row)
        if row["valid"] is not True:
            break
    try:
        selected = select_capacity_rung(results)
    except ValueError:
        selected = None
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "non-claiming-capacity-ladder",
        "created_utc": datetime.now(UTC).isoformat(),
        "candidate_models_sha256": _sha256_file(CANDIDATE_MODELS),
        "worker_rungs_attempted": [row["worker_processes"] for row in results],
        "results": results,
        "selected_worker_processes": (
            None if selected is None else int(selected["worker_processes"])
        ),
        "classification": (
            "CAPACITY-READY" if selected is not None else "CAPACITY-NO-VALID-RUNG"
        ),
        "selection": "highest-valid-completed-job-throughput",
        "performance_endpoints_inspected": False,
        "formal_output_created": False,
        "training_executed": False,
    }
    digest = _write_new_json(record_path, payload)
    if selected is None:
        raise RuntimeError(
            f"R344 capacity ladder produced no valid rung; artifact_sha256={digest}"
        )
    return digest


def build_zero_canary_specs() -> list[dict[str, Any]]:
    return [
        {
            "record_index": index,
            "mode": "zero_canary",
            "point": point,
            "scenario_id": f"zero__{point}",
            "arm": "controller_bypassed",
            "total_steps": 5,
        }
        for index, point in enumerate(("FV0", "FV1"))
    ]


def build_signed_canary_specs() -> list[dict[str, Any]]:
    jobs = build_contract()["canaries"]["signed_authority_jobs"]
    return [
        {
            "record_index": index,
            "mode": "signed_canary",
            "point": str(job["point"]),
            "coordinate_index": int(job["coordinate_index"]),
            "sign": int(job["sign"]),
            "magnitude_system_pu": float(job["magnitude_system_pu"]),
            "active_intervals": int(job["active_intervals"]),
            "recovery_intervals": int(job["recovery_intervals"]),
            "total_steps": int(job["active_intervals"])
            + int(job["recovery_intervals"]),
            "scenario_id": (
                f"signed__{job['point']}__c{job['coordinate_index']}__"
                f"{'pos' if int(job['sign']) > 0 else 'neg'}"
            ),
            "arm": "controller_bypassed",
        }
        for index, job in enumerate(jobs)
    ]


def build_formal_specs() -> list[dict[str, Any]]:
    scenarios = build_contract()["formal"]["scenarios"]
    specs = []
    for scenario in scenarios:
        scenario_id = (
            f"{scenario['point']}__{scenario['channel']['device_idx']}__"
            f"{scenario['sign']}"
        )
        for arm in ("zero_control", "frozen_controller"):
            specs.append(
                {
                    **scenario,
                    "record_index": len(specs),
                    "mode": "formal",
                    "scenario_id": scenario_id,
                    "arm": arm,
                    "total_steps": 25,
                }
            )
    if len(specs) != 32:
        raise RuntimeError("R344 formal inventory drift")
    return specs


def classify_canary_stage(
    records: list[dict[str, Any]], *, mode: str, count: int
) -> str:
    """Apply integrity before physical guards for one fixed canary stage."""

    if (
        len(records) != count
        or any(row.get("mode") != mode for row in records)
        or any(row.get("integrity_valid") is not True for row in records)
    ):
        return "INVALID-DETERMINISTIC-BRIDGE"
    if any(row.get("physical_guards_pass") is not True for row in records):
        return "DETERMINISTIC-PHYSICAL-GUARD-FAIL"
    return "CANARY-STAGE-PASS"


def _controller_solver_row(step: Any) -> dict[str, Any]:
    solution = step.solver.solution
    return {
        "used_fallback": bool(step.used_fallback),
        "fallback_reason": step.fallback_reason,
        "achieved_control_coordinates": step.achieved_control_coordinates.tolist(),
        "requested_control_coordinates": step.requested_control_coordinates.tolist(),
        "requested_node_power": step.requested_node_power.tolist(),
        "innovation": step.estimate.innovation.tolist(),
        "predicted_estimate": step.estimate.predicted_estimate.tolist(),
        "solver_feasible": bool(solution.feasible),
        "solver_message": str(solution.message),
        "solver_status_value": int(step.solver.status_value),
        "solver_iterations": int(solution.solver_iterations),
        "solver_maximum_constraint_residual": float(
            solution.maximum_constraint_residual
        ),
        "solver_primal_residual": float(step.solver.primal_residual),
        "solver_dual_residual": float(step.solver.dual_residual),
        "solver_primal_residual_ratio": float(step.solver.primal_residual_ratio),
        "solver_dual_residual_ratio": float(step.solver.dual_residual_ratio),
        "solver_duality_gap": float(step.solver.duality_gap),
    }


def _physical_guard_summary(
    *,
    rows: list[dict[str, Any]],
    expected_steps: int,
    initial_time: float,
    expected_m: Any,
    expected_d: Any,
) -> dict[str, bool]:
    import numpy as np

    expected_times = initial_time + 0.2 * np.arange(1, len(rows) + 1)
    actual_times = np.asarray([row["t"] for row in rows], dtype=float)
    requested = np.asarray(
        [row["bess_requested_power_system_pu"] for row in rows], dtype=float
    )
    commanded = np.asarray(
        [row["bess_commanded_power_system_pu"] for row in rows], dtype=float
    )
    achieved = np.asarray(
        [row["bess_actual_power_system_pu"] for row in rows], dtype=float
    )
    external_readback = np.asarray(
        [row["bess_external_command_readback_system_pu"] for row in rows],
        dtype=float,
    )
    internal_achieved = np.asarray(
        [
            np.asarray(row["bess_internal"]["v"], dtype=float)
            * np.asarray(row["bess_internal"]["Ipout_y"], dtype=float)
            for row in rows
        ],
        dtype=float,
    )
    soc_readback = np.asarray([row["bess_soc"] for row in rows], dtype=float)
    internal_soc = np.asarray(
        [row["bess_internal"]["SOC"] for row in rows], dtype=float
    )
    voltage_readback = np.asarray(
        [row["bess_bus_voltage_pu"] for row in rows], dtype=float
    )
    internal_voltage = np.asarray(
        [row["bess_internal"]["v"] for row in rows], dtype=float
    )
    ramp = np.vstack((commanded[:1], np.diff(commanded, axis=0)))
    internal_finite = all(
        all(np.all(np.isfinite(np.asarray(value, dtype=float))) for value in row["bess_internal"].values())
        for row in rows
    )
    return {
        "complete": len(rows) == expected_steps,
        "time_grid": bool(
            np.allclose(actual_times, expected_times, rtol=0.0, atol=1.0e-9)
        ),
        "tds_success": all(not bool(row["tds_failed"]) for row in rows),
        "system_exit_zero": all(int(row["system_exit_code"]) == 0 for row in rows),
        "finite_state_algebraic": all(
            bool(row["finite_state_algebraic"]) for row in rows
        ),
        "algebraic_residual": max(
            float(row["dae_g_residual_max"]) for row in rows
        )
        <= 1.0e-6,
        "scheduled_m": all(
            np.allclose(
                np.asarray(row["vsg_m_actual_system"], dtype=float),
                expected_m,
                rtol=0.0,
                atol=1.0e-10,
            )
            for row in rows
        ),
        "scheduled_d": all(
            np.allclose(
                np.asarray(row["vsg_d_actual_system"], dtype=float),
                expected_d,
                rtol=0.0,
                atol=1.0e-10,
            )
            for row in rows
        ),
        "node_power": bool(np.max(np.abs(commanded)) <= 0.36 + 1.0e-12),
        "node_ramp": bool(np.max(np.abs(ramp)) <= 0.072 + 1.0e-12),
        "request_command_identity": bool(
            np.allclose(requested, commanded, rtol=0.0, atol=1.0e-12)
        ),
        "external_command_readback_identity": bool(
            np.allclose(commanded, external_readback, rtol=0.0, atol=1.0e-12)
        ),
        "achieved_power_readback_identity": bool(
            np.allclose(achieved, internal_achieved, rtol=0.0, atol=1.0e-12)
        ),
        "soc_readback_identity": bool(
            np.allclose(soc_readback, internal_soc, rtol=0.0, atol=1.0e-12)
        ),
        "voltage_readback_identity": bool(
            np.allclose(
                voltage_readback, internal_voltage, rtol=0.0, atol=1.0e-12
            )
        ),
        "soc": all(
            np.all(np.asarray(row["bess_soc"], dtype=float) >= 0.2 - 1.0e-12)
            and np.all(np.asarray(row["bess_soc"], dtype=float) <= 0.8 + 1.0e-12)
            for row in rows
        ),
        "external_projection_inactive": all(
            not any(row["bess_saturation_reasons"]) for row in rows
        ),
        "internal_limiter_inactive": all(
            not bool(row["internal_limiter_active"]) for row in rows
        ),
        "internal_telemetry_finite": internal_finite,
        "constraint_violations_absent": all(
            not row["bess_constraint_violations"] for row in rows
        ),
        "line_8_in_service": all(bool(row["line_8_in_service"]) for row in rows),
        "g4_in_service": all(bool(row["g4_in_service"]) for row in rows),
        "md_write_absent": all(int(row["md_write_count"]) == 0 for row in rows),
        "solver_fallback_absent": all(
            not bool(row.get("controller", {}).get("used_fallback", False))
            for row in rows
        ),
        "solver_feasible": all(
            bool(row.get("controller", {}).get("solver_feasible", True))
            for row in rows
        ),
        "requested_values_finite": bool(np.all(np.isfinite(requested))),
        "commanded_values_finite": bool(np.all(np.isfinite(commanded))),
    }


def _zero_canary_guards(
    *, rows: list[dict[str, Any]], initial_soc: Any
) -> dict[str, bool]:
    import numpy as np

    requested = np.asarray(
        [row["bess_requested_power_system_pu"] for row in rows], dtype=float
    )
    commanded = np.asarray(
        [row["bess_commanded_power_system_pu"] for row in rows], dtype=float
    )
    achieved = np.asarray(
        [row["bess_actual_power_system_pu"] for row in rows], dtype=float
    )
    soc = np.asarray([row["bess_soc"] for row in rows], dtype=float)
    frequency = np.asarray([row["freq_hz_physical"] for row in rows], dtype=float)
    return {
        "zero_request": bool(np.max(np.abs(requested)) <= 1.0e-8),
        "zero_command": bool(np.max(np.abs(commanded)) <= 1.0e-8),
        "zero_achieved_power": bool(np.max(np.abs(achieved)) <= 1.0e-8),
        "zero_soc_drift": bool(
            np.max(np.abs(soc - np.asarray(initial_soc, dtype=float))) <= 1.0e-8
        ),
        "zero_frequency_equilibrium": bool(
            np.max(np.abs(frequency - 60.0)) <= 1.0e-8
        ),
        "zero_algebraic_equilibrium": max(
            float(row["dae_g_residual_max"]) for row in rows
        )
        <= 1.0e-8,
        "nominal_frequency_identity": all(
            float(row["control_nominal_frequency_hz"]) == 60.0
            and float(row["andes_nominal_frequency_hz"]) == 60.0
            for row in rows
        ),
    }


def _signed_canary_guards(
    *,
    spec: dict[str, Any],
    rows: list[dict[str, Any]],
    initial_soc: Any,
) -> dict[str, bool]:
    import numpy as np

    basis = control_coordinate_basis()
    coordinate = np.zeros(4)
    coordinate[int(spec["coordinate_index"])] = int(spec["sign"]) * float(
        spec["magnitude_system_pu"]
    )
    expected = basis @ coordinate
    active = int(spec["active_intervals"])
    requested = np.asarray(
        [row["bess_requested_power_system_pu"] for row in rows], dtype=float
    )
    commanded = np.asarray(
        [row["bess_commanded_power_system_pu"] for row in rows], dtype=float
    )
    achieved = np.asarray(
        [row["bess_actual_power_system_pu"] for row in rows], dtype=float
    )
    soc = np.asarray([row["bess_soc"] for row in rows], dtype=float)
    expected_profile = np.zeros_like(requested)
    expected_profile[:active] = expected
    active_mask = np.abs(expected) > 1.0e-12
    final_achieved = achieved[active - 1]
    final_soc_change = np.asarray(initial_soc, dtype=float) - soc[active - 1]
    coordinate_index = int(spec["coordinate_index"])
    command_l1 = float(np.sum(np.abs(expected)))
    return {
        "signed_request_profile": bool(
            np.allclose(requested, expected_profile, rtol=0.0, atol=1.0e-12)
        ),
        "signed_command_profile": bool(
            np.allclose(commanded, expected_profile, rtol=0.0, atol=1.0e-12)
        ),
        "achieved_sign": bool(
            np.all(expected[active_mask] * final_achieved[active_mask] > 0.0)
        ),
        "final_active_achieved_tracking": bool(
            np.max(np.abs(final_achieved - expected))
            <= 0.05 * float(spec["magnitude_system_pu"])
        ),
        "edge_requested_neutrality": bool(
            coordinate_index == 0
            or np.max(np.abs(np.sum(requested, axis=1))) <= 1.0e-12
        ),
        "edge_commanded_neutrality": bool(
            coordinate_index == 0
            or np.max(np.abs(np.sum(commanded, axis=1))) <= 1.0e-12
        ),
        "edge_achieved_imbalance": bool(
            coordinate_index == 0
            or abs(float(np.sum(final_achieved))) <= 0.05 * command_l1
        ),
        "soc_direction": bool(
            np.all(expected[active_mask] * final_soc_change[active_mask] > 0.0)
        ),
    }


def _run_physical_record(
    spec: dict[str, Any],
    *,
    record_dir: Path,
    trace_path: Path,
    seal_digest: str,
) -> dict[str, Any]:
    if os.name != "posix":
        raise RuntimeError("R344 physical records are WSL/POSIX-only")
    import numpy as np
    from scripts import run_r335_disturbance_package as base
    from scripts import run_r341_staged_fresh_model_validation as r341

    from andes_rl_kundur.env.andes.model_first_contract import (
        ModelFirstConfig,
        Stage1OperatingPoint,
    )
    from andes_rl_kundur.env.andes.model_first_env import AndesModelFirstEnv
    from andes_rl_kundur.env.andes.model_first_pq_profile import TimedPQProfileMixin
    from andes_rl_kundur.evaluation.model_first_physical_bridge import (
        bridge_internal_limiter_active,
        frequency_coordinate_trace,
        summarize_bridge_trace,
    )

    mode = str(spec["mode"])
    point_name = str(spec["point"])
    point = Stage1OperatingPoint(point_name, **r341.POINTS[point_name])
    config = replace(
        ModelFirstConfig.for_stage1_operating_point(point),
        tds_post_initialization_convergence_tolerance=base.DYNAMIC_TOLERANCE,
    )
    profile_contract = None
    environment_type: Any = AndesModelFirstEnv
    environment_kwargs: dict[str, Any] = {"model_first_config": config}
    if mode == "formal":
        profile_contract = r341._r341_profile_contract(
            channel=spec["channel"],
            shape=str(spec["profile_key"]),
            sign=str(spec["sign"]),
        )

        class PhysicalEnvironment(TimedPQProfileMixin, AndesModelFirstEnv):
            def __init__(self, *, pq_profile_contract, **kwargs):
                self.pq_profile_contract = pq_profile_contract
                super().__init__(**kwargs)

        environment_type = PhysicalEnvironment
        environment_kwargs["pq_profile_contract"] = profile_contract

    record_dir.mkdir(parents=True, exist_ok=False)
    previous_cwd = Path.cwd()
    os.chdir(record_dir)
    rows: list[dict[str, Any]] = []
    controller = None
    controller_identity = None
    env = None
    try:
        with base._substep_environment():
            env = environment_type(**environment_kwargs)
            env.reset()
            initial_time = float(env.ss.dae.t)
            initial_soc = env._get_bess_soc().copy()
            structural_contract = _jsonable(env.structural_contract())
            initial_event_audit = _jsonable(getattr(env, "pq_event_audit", []))
            setup_baselines = None
            terminal_baselines = None
            event_inventory = None
            if mode == "formal" and not initial_event_audit:
                raise RuntimeError("R344 formal profile did not fire its reset event")
            if mode == "formal" and profile_contract is not None:
                setup_baselines = base._baseline_readback(env.ss)
                setup_baselines[profile_contract.device_idx] = initial_event_audit[0][
                    "before"
                ]
                event_inventory = base._r333._alter_event_inventory(env.ss)
            if mode == "formal" and spec["arm"] == "frozen_controller":
                controller, controller_identity = build_point_controller(point_name)
                controller.reset()
            prior_estimate = np.zeros(16)
            zero_md = {index: np.zeros(2) for index in range(env.N_AGENTS)}
            basis = control_coordinate_basis()
            reference_frequency = np.full(4, 60.0)
            active_intervals = int(spec.get("active_intervals", 0))
            for step_index in range(int(spec["total_steps"])):
                frequency_before = env.get_vsg_frequency_physical_hz()
                delivered = frequency_coordinate_trace(
                    frequency_before.reshape(1, 4),
                    reference_frequency_hz=reference_frequency,
                    inertia_system=config.vsg_m_system,
                )[0]
                achieved_before = env._get_bess_actual_power()
                commanded_before = env._previous_bess_command_system_pu.copy()
                soc_before = env._get_bess_soc()
                controller_row = None
                if controller is not None:
                    controller_step = controller.step(
                        prior_estimate=prior_estimate,
                        previous_delivered_output=delivered,
                        previous_achieved_node_power=achieved_before,
                        previous_commanded_node_power=commanded_before,
                        soc=soc_before,
                    )
                    prior_estimate = controller_step.estimate.predicted_estimate.copy()
                    request = controller_step.requested_node_power.copy()
                    controller_row = _controller_solver_row(controller_step)
                elif mode == "signed_canary" and step_index < active_intervals:
                    coordinate = np.zeros(4)
                    coordinate[int(spec["coordinate_index"])] = (
                        int(spec["sign"]) * float(spec["magnitude_system_pu"])
                    )
                    request = basis @ coordinate
                else:
                    request = np.zeros(4)
                _, _, _, info = env.step(
                    zero_md,
                    bess_power_request_pu=request,
                )
                row = _jsonable(info)
                row["step"] = step_index
                row["t"] = row.pop("time")
                row["delivered_coordinates_before_action"] = delivered.tolist()
                row["achieved_node_power_before_action"] = achieved_before.tolist()
                row["commanded_node_power_before_action"] = commanded_before.tolist()
                row["controller"] = controller_row or {"bypassed": True}
                row["internal_limiter_active"] = bridge_internal_limiter_active(
                    row["bess_internal"]
                )
                rows.append(row)
            event_audit = _jsonable(getattr(env, "pq_event_audit", []))
            if mode == "formal":
                env.ss.dae.ts.unpack(attr="t", warn_empty=False)
                tds_grid = np.asarray(env.ss.dae.ts.t, dtype=float).copy()
                terminal_baselines = base._baseline_readback(env.ss)
            else:
                tds_grid = np.asarray([], dtype=float)
    finally:
        try:
            if env is not None:
                env.close()
        finally:
            os.chdir(previous_cwd)

    frequency = np.asarray([row["freq_hz_physical"] for row in rows], dtype=float)
    coordinates = frequency_coordinate_trace(
        frequency,
        reference_frequency_hz=np.full(4, 60.0),
        inertia_system=config.vsg_m_system,
    )
    requested = np.asarray(
        [row["bess_requested_power_system_pu"] for row in rows], dtype=float
    )
    achieved = np.asarray(
        [row["bess_actual_power_system_pu"] for row in rows], dtype=float
    )
    summary = asdict(
        summarize_bridge_trace(
            coordinate_outputs=coordinates,
            frequency_hz=frequency,
            reference_frequency_hz=np.full(4, 60.0),
            requested_node_power=requested,
            achieved_node_power=achieved,
            sample_period_seconds=0.2,
        )
    )
    guards = _physical_guard_summary(
        rows=rows,
        expected_steps=int(spec["total_steps"]),
        initial_time=initial_time,
        expected_m=config.vsg_m_system,
        expected_d=config.vsg_d_system,
    )
    if mode == "zero_canary":
        guards.update(_zero_canary_guards(rows=rows, initial_soc=initial_soc))
    elif mode == "signed_canary":
        guards.update(
            _signed_canary_guards(
                spec=spec,
                rows=rows,
                initial_soc=initial_soc,
            )
        )
    profile_guards: dict[str, bool] = {}
    profile_provenance: dict[str, Any] = {}
    if mode == "formal" and profile_contract is not None:
        expected_events = list(profile_contract.alter_records())
        event_times = [float(event["t"]) for event in expected_events]
        event_grid = base._event_grid_guard(tds_grid, event_times)
        receipts = base._event_receipts(profile_contract, event_audit)
        fire_counts = {
            event["idx"]: sum(
                int(event["idx"] in batch["event_ids"]) for batch in event_audit
            )
            for event in expected_events
        }
        profile_guards = {
            "event_inventory": event_inventory == expected_events,
            "event_fire_once": all(count == 1 for count in fire_counts.values()),
            "event_grid": event_grid["pass"] is True,
            "event_readback": all(
                receipt.get("valid") is True
                and float(receipt["absolute_error_system_pu"]) <= 1.0e-12
                and float(receipt["time_absolute_error_seconds"]) <= 1.0e-9
                for receipt in receipts
            ),
            "setup_baseline": base._baseline_snapshot_guard(
                setup_baselines, tolerance=1.0e-12
            ),
            "terminal_baseline": base._baseline_snapshot_guard(
                terminal_baselines, tolerance=1.0e-12
            ),
        }
        profile_provenance = {
            "profile_contract": profile_contract.to_dict(),
            "expected_event_inventory": expected_events,
            "observed_event_inventory": event_inventory,
            "event_fire_counts": fire_counts,
            "event_grid": _jsonable(event_grid),
            "event_receipts": receipts,
            "setup_baseline_readback": _jsonable(setup_baselines),
            "terminal_baseline_readback": _jsonable(terminal_baselines),
        }
    guards.update(profile_guards)
    physical_guards_pass = all(guards.values())
    fallback_count = sum(
        int(bool(row.get("controller", {}).get("used_fallback", False)))
        for row in rows
    )
    trace_digest = _write_new_gzip_json(
        trace_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "seal_sha256": seal_digest,
            "spec": spec,
            "point_controller": controller_identity,
            "structural_contract": structural_contract,
            "initial_event_audit": initial_event_audit,
            "event_audit": event_audit,
            "profile_provenance": profile_provenance,
            "rows": rows,
        },
    )
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "record_index": int(spec["record_index"]),
        "mode": mode,
        "point": point_name,
        "scenario_id": str(spec["scenario_id"]),
        "arm": str(spec["arm"]),
        "integrity_valid": True,
        "physical_guards_pass": physical_guards_pass,
        "guards": guards,
        "fallback_count": fallback_count,
        "controller_engaged": bool(summary["controller_engaged"]),
        "metrics": summary,
        "trace": {"path": _path_text(trace_path), "sha256": trace_digest},
        "worker_pid": os.getpid(),
        "training_executed": False,
        "distributed_runtime_executed": False,
        "eval_executed": False,
    }


def _physical_worker(
    spec: dict[str, Any],
    *,
    record_dir: Path,
    trace_path: Path,
    seal_digest: str,
) -> dict[str, Any]:
    started_ns = time.monotonic_ns()
    row = _run_physical_record(
        spec,
        record_dir=record_dir,
        trace_path=trace_path,
        seal_digest=seal_digest,
    )
    ended_ns = time.monotonic_ns()
    row.update(
        {
            "worker_started_monotonic_ns": started_ns,
            "worker_ended_monotonic_ns": ended_ns,
            "worker_elapsed_seconds": (ended_ns - started_ns) / 1.0e9,
        }
    )
    return row


def _run_physical_specs(
    *,
    specs: list[dict[str, Any]],
    stage: str,
    process_budget: int,
    trace_root: Path,
    seal_digest: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if os.name != "posix":
        raise RuntimeError("R344 physical execution is WSL/POSIX-only")
    import multiprocessing as mp

    if not specs:
        raise ValueError("physical stage inventory must be non-empty")
    effective_processes = min(int(process_budget), len(specs))
    if effective_processes < 2:
        raise ValueError("R344 physical stages require at least two processes")
    trace_root.mkdir(parents=True, exist_ok=False)
    work_root = Path.cwd() / f"r344_{stage}_records"
    work_root.mkdir(parents=True, exist_ok=False)
    indexed = list(enumerate(specs))
    parent_positions = set(range(0, len(indexed), effective_processes))
    parent_jobs = [item for item in indexed if item[0] in parent_positions]
    child_jobs = [item for item in indexed if item[0] not in parent_positions]

    def paths(index: int, spec: dict[str, Any]) -> tuple[Path, Path]:
        label = f"{index:02d}_{spec['scenario_id']}_{spec['arm']}"
        return work_root / label, trace_root / f"record_{index:02d}.json.gz"

    results: list[dict[str, Any]] = []
    context = mp.get_context("fork")
    started = time.monotonic()
    with ProcessPoolExecutor(
        max_workers=effective_processes - 1,
        mp_context=context,
    ) as executor:
        futures = []
        for index, spec in child_jobs:
            record_dir, trace_path = paths(index, spec)
            futures.append(
                executor.submit(
                    _physical_worker,
                    dict(spec),
                    record_dir=record_dir,
                    trace_path=trace_path,
                    seal_digest=seal_digest,
                )
            )
        for index, spec in parent_jobs:
            record_dir, trace_path = paths(index, spec)
            results.append(
                _physical_worker(
                    dict(spec),
                    record_dir=record_dir,
                    trace_path=trace_path,
                    seal_digest=seal_digest,
                )
            )
        for future in as_completed(futures):
            results.append(future.result())
    elapsed = time.monotonic() - started
    results.sort(key=lambda row: int(row["record_index"]))
    unique_processes = len({int(row["worker_pid"]) for row in results})
    maximum_overlap = _maximum_interval_overlap(results)
    process_guard = bool(
        len(results) == len(specs)
        and unique_processes == effective_processes
        and maximum_overlap == effective_processes
    )
    if not process_guard:
        for row in results:
            row["integrity_valid"] = False
    return results, {
        "configured_process_budget": int(process_budget),
        "effective_processes": effective_processes,
        "unique_python_processes": unique_processes,
        "maximum_interval_overlap": maximum_overlap,
        "process_guard": process_guard,
        "elapsed_seconds": elapsed,
        "throughput_trajectories_per_second": len(results) / elapsed,
        "native_threads_per_process": 1,
    }


def _write_stage_artifacts(
    *,
    out_dir: Path,
    name: str,
    seal_digest: str,
    records: list[dict[str, Any]],
    process: dict[str, Any],
    classification: str,
) -> dict[str, Any]:
    execution_path = out_dir / f"{name}_execution.json"
    execution_digest = _write_new_json(
        execution_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "stage": name,
            "seal_sha256": seal_digest,
            "created_utc": datetime.now(UTC).isoformat(),
            "process": process,
            "record_count": len(records),
            "records": records,
            "training_executed": False,
            "distributed_runtime_executed": False,
            "eval_executed": False,
        },
    )
    analysis_path = out_dir / f"{name}_analysis.json"
    analysis_digest = _write_new_json(
        analysis_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "stage": name,
            "classification": classification,
            "record_count": len(records),
            "all_physical_guards_pass": bool(
                records and all(row["physical_guards_pass"] for row in records)
            ),
            "training_authorized": False,
            "formal_release_automatic": False,
        },
    )
    manifest_path = out_dir / f"{name}_manifest.json"
    manifest_digest = _write_new_json(
        manifest_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "stage": name,
            "entries": [
                {"path": _path_text(execution_path), "sha256": execution_digest},
                {"path": _path_text(analysis_path), "sha256": analysis_digest},
                *[row["trace"] for row in records],
            ],
        },
    )
    return {
        "stage": name,
        "classification": classification,
        "execution": {"path": _path_text(execution_path), "sha256": execution_digest},
        "analysis": {"path": _path_text(analysis_path), "sha256": analysis_digest},
        "manifest": {"path": _path_text(manifest_path), "sha256": manifest_digest},
    }


def execute_canaries(
    *,
    seal_path: Path,
    expected_sha256: str,
    out_dir: Path = DEFAULT_OUT,
) -> str:
    """Execute zero then signed gates, stopping before any formal bridge."""

    seal, seal_digest = load_seal(seal_path, expected_sha256)
    process_budget = int(seal["launch"]["worker_processes"])
    out_dir.mkdir(parents=True, exist_ok=True)
    attempt_path = out_dir / "canary_attempt.json"
    attempt_digest = _write_new_json(
        attempt_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "physical_execution_started": True,
            "formal_bridge_started": False,
            "retry_authorized": False,
        },
    )
    stages = []
    try:
        zero_records, zero_process = _run_physical_specs(
            specs=build_zero_canary_specs(),
            stage="zero_canary",
            process_budget=process_budget,
            trace_root=out_dir / "zero_canary_traces",
            seal_digest=seal_digest,
        )
        zero_classification = classify_canary_stage(
            zero_records, mode="zero_canary", count=2
        )
        stages.append(
            _write_stage_artifacts(
                out_dir=out_dir,
                name="zero_canary",
                seal_digest=seal_digest,
                records=zero_records,
                process=zero_process,
                classification=zero_classification,
            )
        )
        if zero_classification != "CANARY-STAGE-PASS":
            terminal = zero_classification
        else:
            signed_records, signed_process = _run_physical_specs(
                specs=build_signed_canary_specs(),
                stage="signed_canary",
                process_budget=process_budget,
                trace_root=out_dir / "signed_canary_traces",
                seal_digest=seal_digest,
            )
            signed_classification = classify_canary_stage(
                signed_records, mode="signed_canary", count=16
            )
            stages.append(
                _write_stage_artifacts(
                    out_dir=out_dir,
                    name="signed_canary",
                    seal_digest=seal_digest,
                    records=signed_records,
                    process=signed_process,
                    classification=signed_classification,
                )
            )
            terminal = (
                "CANARIES-PASS"
                if signed_classification == "CANARY-STAGE-PASS"
                else signed_classification
            )
        digest = _write_new_json(
            out_dir / "canary_analysis.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "seal_sha256": seal_digest,
                "canary_attempt_sha256": attempt_digest,
                "classification": terminal,
                "stages": stages,
                "formal_release_automatic": False,
                "formal_bridge_started": False,
                "training_authorized": False,
            },
        )
    except Exception as error:
        _write_new_json(
            out_dir / "canary_failure.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "seal_sha256": seal_digest,
                "canary_attempt_sha256": attempt_digest,
                "classification": "INVALID-DETERMINISTIC-BRIDGE",
                "error_type": type(error).__name__,
                "error_message": str(error),
                "retry_authorized": False,
                "training_authorized": False,
            },
        )
        raise
    print(f"canary_classification={terminal}", flush=True)
    return digest


def execute_formal(
    *,
    seal_path: Path,
    expected_sha256: str,
    out_dir: Path = DEFAULT_OUT,
) -> str:
    """Run the once-only paired bridge after explicit canary release."""

    seal, seal_digest = load_seal(seal_path, expected_sha256)
    canary = _read_hashed_json(out_dir / "canary_analysis.json")
    if (
        canary.get("seal_sha256") != seal_digest
        or canary.get("classification") != "CANARIES-PASS"
    ):
        raise RuntimeError("R344 formal release requires sealed passing canaries")
    process_budget = int(seal["launch"]["worker_processes"])
    attempt_digest = _write_new_json(
        out_dir / "formal_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "canary_analysis_sha256": _sha256_file(out_dir / "canary_analysis.json"),
            "physical_execution_started": True,
            "formal_bridge_started": True,
            "retry_authorized": False,
        },
    )
    try:
        records, process = _run_physical_specs(
            specs=build_formal_specs(),
            stage="formal",
            process_budget=process_budget,
            trace_root=out_dir / "formal_traces",
            seal_digest=seal_digest,
        )
        execution_digest = _write_new_json(
            out_dir / "formal_execution.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "seal_sha256": seal_digest,
                "formal_attempt_sha256": attempt_digest,
                "created_utc": datetime.now(UTC).isoformat(),
                "process": process,
                "record_count": len(records),
                "records": records,
                "training_executed": False,
                "distributed_runtime_executed": False,
                "eval_executed": False,
            },
        )
        analysis = classify_formal_records(records)
        analysis.update(
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "seal_sha256": seal_digest,
                "formal_execution_sha256": execution_digest,
                "training_authorized": False,
                "residual_headroom_question_authorized": (
                    analysis["classification"] == "DETERMINISTIC-BRIDGE-PASS"
                ),
            }
        )
        analysis_digest = _write_new_json(out_dir / "formal_analysis.json", analysis)
        _write_new_json(
            out_dir / "formal_manifest.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "entries": [
                    {
                        "path": _path_text(out_dir / "formal_attempt.json"),
                        "sha256": attempt_digest,
                    },
                    {
                        "path": _path_text(out_dir / "formal_execution.json"),
                        "sha256": execution_digest,
                    },
                    {
                        "path": _path_text(out_dir / "formal_analysis.json"),
                        "sha256": analysis_digest,
                    },
                    *[row["trace"] for row in records],
                ],
            },
        )
    except Exception as error:
        _write_new_json(
            out_dir / "formal_failure.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "seal_sha256": seal_digest,
                "formal_attempt_sha256": attempt_digest,
                "classification": "INVALID-DETERMINISTIC-BRIDGE",
                "error_type": type(error).__name__,
                "error_message": str(error),
                "retry_authorized": False,
                "training_authorized": False,
            },
        )
        raise
    print(f"formal_classification={analysis['classification']}", flush=True)
    return analysis_digest


def prepare(seal_path: Path = DEFAULT_SEAL) -> str:
    """Create one source-bound R344 seal before any physical output."""

    launch = _verified_launch_prerequisites()
    preexisting = [path for path in _formal_output_paths() if path.exists()]
    if preexisting:
        raise FileExistsError(f"R344 physical/formal asset exists before seal: {preexisting}")
    formal_trace_dir = DEFAULT_OUT / "formal_traces"
    trace_count = len(list(formal_trace_dir.glob("*.json.gz"))) if formal_trace_dir.exists() else 0
    if trace_count:
        raise RuntimeError("formal traces already exist before the R344 seal")
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "launch": launch,
        "sources": _sources(),
        "formal_trace_count_at_freeze": trace_count,
        "formal_artifacts_create_only": True,
        "formal_retry_authorized": False,
    }
    return _write_new_json(seal_path, seal)


def load_seal(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    """Verify one exact seal, contract, and every bound source."""

    payload = _read_json(path)
    digest = _sha256_file(path)
    if digest != expected_sha256:
        raise RuntimeError("R344 seal digest mismatch")
    if payload.get("round") != ROUND_ID or payload.get("question") != QUESTION_ID:
        raise RuntimeError("R344 seal identity mismatch")
    contract = payload.get("contract")
    if contract != build_contract() or payload.get("contract_payload_sha256") != _payload_sha256(
        contract
    ):
        raise RuntimeError("R344 contract drift")
    if payload.get("formal_trace_count_at_freeze") != 0:
        raise RuntimeError("R344 seal must precede every formal trace")
    if payload.get("launch") != _verified_launch_prerequisites():
        raise RuntimeError("R344 launch prerequisite drift")
    for name, source in payload.get("sources", {}).items():
        source_path = ROOT / str(source["path"])
        if _sha256_file(source_path) != source.get("sha256"):
            raise RuntimeError(f"R344 sealed source drift: {name}")
    return payload, digest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in (
        "prepare",
        "rehearse",
        "capacity-ladder",
        "execute-canaries",
        "execute-formal",
        "analyse",
    ):
        child = subparsers.add_parser(command)
        child.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
        if command in {"execute-canaries", "execute-formal", "analyse"}:
            child.add_argument("--expected-sha256", required=True)
        child.add_argument(
            "--out",
            type=Path,
            default=(
                DEFAULT_OUT / "capacity_attempt_2"
                if command == "capacity-ladder"
                else DEFAULT_OUT
            ),
        )
        if command == "capacity-ladder":
            child.add_argument("--record", type=Path, default=CAPACITY_RECORD)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare":
        print(f"seal_sha256={prepare(args.seal)}", flush=True)
        return 0
    if args.command == "rehearse":
        print(f"rehearsal_sha256={rehearse()}", flush=True)
        return 0
    if args.command == "capacity-ladder":
        print(
            "capacity_ladder_sha256="
            f"{run_capacity_ladder(out_dir=args.out, record_path=args.record)}",
            flush=True,
        )
        return 0
    if args.command == "execute-canaries":
        print(
            "canary_analysis_sha256="
            f"{execute_canaries(seal_path=args.seal, expected_sha256=args.expected_sha256, out_dir=args.out)}",
            flush=True,
        )
        return 0
    if args.command == "execute-formal":
        print(
            "formal_analysis_sha256="
            f"{execute_formal(seal_path=args.seal, expected_sha256=args.expected_sha256, out_dir=args.out)}",
            flush=True,
        )
        return 0
    if args.command == "analyse":
        _, seal_digest = load_seal(args.seal, args.expected_sha256)
        analysis = _read_hashed_json(args.out / "formal_analysis.json")
        if analysis.get("seal_sha256") != seal_digest:
            raise RuntimeError("R344 formal analysis seal drift")
        print(f"classification={analysis['classification']}", flush=True)
        return 0
    raise RuntimeError(f"R344 command is not implemented yet: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
