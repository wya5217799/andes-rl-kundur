"""Prepare and execute the R339 full-DAE input-bridge diagnosis.

Usage::

    python scripts/run_r339_input_bridge_diagnosis.py prepare
    python scripts/andes_scratch.py scripts/run_r339_input_bridge_diagnosis.py rehearse --expected-sha256 <seal>
    python scripts/andes_scratch.py scripts/run_r339_input_bridge_diagnosis.py execute --expected-sha256 <seal>

The live commands are WSL-only. Sixteen isolated per-channel jobs run
concurrently as one parent job plus fifteen forked workers. Rehearsal traverses the same source,
runtime, case, environment, equilibrium, Jacobian, and finite-difference path
without creating a formal attempt or result artifact.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import os
import platform
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
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

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for _path in (ROOT, SRC):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from memory.tools.artifact_io import (  # noqa: E402
    payload_sha256,
    read_verified_json,
    sha256_file,
    write_new_json,
)

ROUND_ID = "R339"
QUESTION_ID = "Q-0087"
DEFAULT_SEAL = ROOT / "memory/rounds/R339/input_bridge_seal.json"
DEFAULT_OUT = ROOT / "results/r339_input_bridge_diagnosis"
EXPECTED_CASE_SHA256 = "f725e03ba12d8207616f68acdd606bbd35e7c4a68f13e66d7db43925adac2ed8"
FINITE_DIFFERENCE_STEPS = (1.0e-4, 1.0e-5, 1.0e-6)
POINTS = {
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
BASELINES = (
    ("PQ_0", 7, 11.59, -0.735),
    ("PQ_1", 8, 15.75, -0.899),
    ("PQ_Bus14", 14, 2.48, 0.0),
    ("PQ_Bus15", 15, 0.05, 0.0),
)
JOB_SPECS = tuple(
    {"point": point, "input_family": family, "channel": channel}
    for point in ("HS0", "HS1")
    for family in ("control", "load")
    for channel in range(4)
)
WHOLE_HOST_PYTHON_PROCESSES = 16

_GLOBAL_BARRIER: Any = None


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _path_text(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def build_contract() -> dict[str, object]:
    """Return the complete prospective R339 execution contract."""

    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "full-dae-separate-input-diagnosis",
        "operating_points": POINTS,
        "input_families": ["control", "load"],
        "control_channels": [
            "R272_BESS_1/Pext0",
            "R272_BESS_2/Pext0",
            "R272_BESS_3/Pext0",
            "R272_BESS_4/Pext0",
        ],
        "load_channels": [row[0] + "/Ppf" for row in BASELINES],
        "load_baselines": [
            {
                "device_idx": row[0],
                "bus_idx": row[1],
                "active_system_pu": row[2],
                "reactive_system_pu": row[3],
            }
            for row in BASELINES
        ],
        "job_specs": [dict(row) for row in JOB_SPECS],
        "parallel_design": "one parent job plus fifteen forked per-channel jobs",
        "whole_host_python_processes": WHOLE_HOST_PYTHON_PROCESSES,
        "native_threads_per_process": 1,
        "finite_difference_scheme": "central-at-fixed-equilibrium-x-y",
        "finite_difference_steps_system_pu": list(FINITE_DIFFERENCE_STEPS),
        "sample_period_seconds": 0.2,
        "sample_observation_convention": "end-of-held-interval",
        "fresh_nonlinear_trajectory_executed": False,
        "controller_executed": False,
        "closed_loop_executed": False,
        "distributed_runtime_executed": False,
        "training_executed": False,
        "eval_executed": False,
        "formal_retry_authorized": False,
    }


def parallel_schedule() -> dict[str, object]:
    """Expose the exact sixteen-process split for tests and audit."""

    return {
        "parent_job": dict(JOB_SPECS[0]),
        "child_jobs": [dict(row) for row in JOB_SPECS[1:]],
        "total_python_processes": WHOLE_HOST_PYTHON_PROCESSES,
    }


def combine_family_jobs(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    """Assemble four independently extracted derivative columns."""

    ordered = sorted(jobs, key=lambda row: int(row.get("channel", -1)))
    if [int(row.get("channel", -1)) for row in ordered] != [0, 1, 2, 3]:
        raise RuntimeError("input-family combination requires channels 0 through 3")
    identities = {(str(row.get("point")), str(row.get("input_family"))) for row in ordered}
    if len(identities) != 1:
        raise RuntimeError("input-family column identity mismatch")
    base_digests = {str(row.get("base_snapshot_sha256")) for row in ordered}
    if len(base_digests) != 1:
        raise RuntimeError("independent columns disagree on the base snapshot")
    channel_catalogs = {payload_sha256(row.get("channel_ids")) for row in ordered}
    equilibrium_catalogs = {
        payload_sha256(row.get("equilibrium_input_system_pu")) for row in ordered
    }
    if len(channel_catalogs) != 1 or len(equilibrium_catalogs) != 1:
        raise RuntimeError("independent columns disagree on the input catalog")

    combined_steps: list[dict[str, Any]] = []
    for step_index, expected_step in enumerate(FINITE_DIFFERENCE_STEPS):
        rows = [row["steps"][step_index] for row in ordered]
        if any(float(row.get("step_system_pu", -1.0)) != expected_step for row in rows):
            raise RuntimeError("independent columns disagree on the difference step")
        branch_references = {str(row.get("branch_reference_sha256")) for row in rows}
        if len(branch_references) != 1:
            raise RuntimeError("independent columns disagree on the branch reference")
        f_input = np.hstack([np.asarray(row["f_input_column"], dtype=float) for row in rows])
        g_input = np.hstack([np.asarray(row["g_input_column"], dtype=float) for row in rows])
        combined_steps.append(
            {
                "step_system_pu": expected_step,
                "f_input": f_input.tolist(),
                "g_input": g_input.tolist(),
                "midpoint_ratios": [float(row["midpoint_ratio"]) for row in rows],
                "branch_reference_sha256": next(iter(branch_references)),
                "all_branch_snapshots_match": all(
                    row.get("all_branch_snapshots_match") is True for row in rows
                ),
            }
        )
    return {
        "channel_ids": ordered[0]["channel_ids"],
        "equilibrium_input_system_pu": ordered[0]["equilibrium_input_system_pu"],
        "steps": combined_steps,
        "restored_exactly": all(row.get("restored_exactly") is True for row in ordered),
    }


def combine_point_jobs(
    control: dict[str, Any],
    load: dict[str, Any],
) -> dict[str, Any]:
    """Combine independently extracted input families only after base identity."""

    if control.get("point") != load.get("point"):
        raise RuntimeError("cannot combine jobs from different operating points")
    if control.get("input_family") != "control" or load.get("input_family") != "load":
        raise RuntimeError("point combination requires control then load jobs")
    if control.get("base_snapshot_sha256") != load.get("base_snapshot_sha256"):
        raise RuntimeError("independent jobs disagree on the base snapshot")
    return {
        "point": control["point"],
        "base_snapshot_sha256": control["base_snapshot_sha256"],
        "base_snapshot": control.get("base_snapshot"),
        "control_input_derivatives": control["input_derivatives"],
        "load_input_derivatives": load["input_derivatives"],
        "job_metadata": [
            *control.get("job_metadata", []),
            *load.get("job_metadata", []),
        ],
    }


def _source_paths() -> dict[str, Path]:
    paths = {
        "r339_runner": ROOT / "scripts/run_r339_input_bridge_diagnosis.py",
        "input_bridge_math": ROOT / "src/andes_rl_kundur/evaluation/model_first_input_bridge.py",
        "dynamic_reduction_math": ROOT
        / "src/andes_rl_kundur/evaluation/model_first_dynamic_reduction.py",
        "model_first_contract": ROOT / "src/andes_rl_kundur/env/andes/model_first_contract.py",
        "model_first_env": ROOT / "src/andes_rl_kundur/env/andes/model_first_env.py",
        "pq_disturbance": ROOT / "src/andes_rl_kundur/env/andes/model_first_pq_disturbance.py",
        "r339_runner_tests": ROOT / "tests/test_r339_input_bridge_diagnosis.py",
        "r339_analysis_probe": ROOT / "probes/r339_input_bridge_diagnosis.py",
        "r339_analysis_tests": ROOT / "tests/test_r339_input_bridge_probe.py",
        "input_bridge_math_tests": ROOT / "tests/test_model_first_input_bridge.py",
        "andes_scratch": ROOT / "scripts/andes_scratch.py",
        "artifact_io": ROOT / "memory/tools/artifact_io.py",
        "installed_runtime_verifier": ROOT / "scripts/run_r333_pq_disturbance_identification.py",
        "installed_case_verifier": ROOT / "scripts/run_r334_pq_disturbance_identification.py",
    }
    return paths


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": sha256_file(path)}
        for name, path in sorted(_source_paths().items())
    }


def _parent_paths() -> dict[str, Path]:
    paths = {
        "r339_plan": ROOT / "memory/rounds/R339/plan.md",
        "r339_capacity": ROOT / "memory/rounds/R339/host_capacity.json",
        "r339_package_admissibility": ROOT / "memory/rounds/R339/package_admissibility.md",
        "q0087": ROOT / "memory/questions/Q-0087.md",
        "clm0885": ROOT / "memory/claims/CLM-0885.md",
        "r316_model": ROOT / "results/r316_dynamic_reduction/dynamic_model.json",
        "r336_execution": ROOT / "results/r336_disturbance_package/execution.json",
        "r336_analysis": ROOT / "results/r336_disturbance_package/analysis.json",
        "r336_development_execution": ROOT
        / "results/r336_disturbance_package/development_execution.json",
        "r336_second_point_execution": ROOT
        / "results/r336_disturbance_package/holdout_execution.json",
        "r336_run_manifest": ROOT / "results/r336_disturbance_package/run_manifest.json",
    }
    first_seal = ROOT / "memory/rounds/R339/input_bridge_seal.json"
    rehearsal_failure = ROOT / "memory/rounds/R339/rehearsal_failure_01.json"
    second_seal = ROOT / "memory/rounds/R339/input_bridge_seal_v2.json"
    second_rehearsal = ROOT / "memory/rounds/R339/rehearsal_success_02.md"
    third_seal = ROOT / "memory/rounds/R339/input_bridge_seal_v3.json"
    third_rehearsal = ROOT / "memory/rounds/R339/rehearsal_success_03.md"
    if first_seal.is_file():
        paths["r339_first_seal"] = first_seal
    if rehearsal_failure.is_file():
        paths["r339_rehearsal_failure_01"] = rehearsal_failure
    if second_seal.is_file():
        paths["r339_second_seal"] = second_seal
    if second_rehearsal.is_file():
        paths["r339_rehearsal_success_02"] = second_rehearsal
    if third_seal.is_file():
        paths["r339_third_seal"] = third_seal
    if third_rehearsal.is_file():
        paths["r339_rehearsal_success_03"] = third_rehearsal
    return paths


def _parents() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": sha256_file(path)}
        for name, path in sorted(_parent_paths().items())
    }


def _expected_installed_sources() -> dict[str, str]:
    from scripts import run_r333_pq_disturbance_identification as r333

    return dict(r333.EXPECTED_INSTALLED_SOURCES)


def prepare(seal_path: Path, *, created_utc: str | None = None) -> str:
    """Create the source-closed R339 seal."""

    contract = build_contract()
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": created_utc or datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": payload_sha256(contract),
        "sources": _sources(),
        "parents": _parents(),
        "expected_runtime": {
            "andes_version": "2.0.0",
            "installed_sources": _expected_installed_sources(),
            "case_sha256": EXPECTED_CASE_SHA256,
        },
        "formal_artifacts_create_only": True,
        "formal_retry_authorized": False,
    }
    digest = write_new_json(seal_path, payload)
    print(f"seal_sha256={digest}")
    print(f"source_inventory_count={len(payload['sources'])}")
    return digest


def _load_seal(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    payload, digest = read_verified_json(path, expected_sha256=expected_sha256)
    if payload.get("round") != ROUND_ID or payload.get("question") != QUESTION_ID:
        raise RuntimeError("R339 seal identity mismatch")
    contract = build_contract()
    if payload.get("contract") != contract:
        raise RuntimeError("R339 seal contract drift")
    if payload.get("contract_payload_sha256") != payload_sha256(contract):
        raise RuntimeError("R339 seal contract payload hash mismatch")
    for group in ("sources", "parents"):
        for row in payload.get(group, {}).values():
            if sha256_file(ROOT / row["path"]) != row["sha256"]:
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


def _dense_andes_matrix(value: Any) -> np.ndarray:
    from andes.shared import matrix

    return np.asarray(matrix(value), dtype=float)


def _branch_snapshot(env: Any) -> dict[str, object]:
    fields = ("Fvl", "Fvh", "Ffl", "Ffh")
    return {
        "dae_z": np.asarray(env.ss.dae.z, dtype=float).copy(),
        "esd1": {
            name: np.asarray(getattr(env.ss.ESD1, name).v, dtype=float).copy() for name in fields
        },
    }


def _extract_live_job(spec: dict[str, Any]) -> dict[str, Any]:
    """Build one isolated plant and extract one input-derivative column."""

    global _GLOBAL_BARRIER
    if os.name != "posix":
        raise RuntimeError("R339 live extraction is WSL/POSIX-only")
    import resource

    job_dir = Path.cwd() / (
        f"worker-{spec['point']}-{spec['input_family']}-c{spec['channel']}-{os.getpid()}"
    )
    job_dir.mkdir(parents=False, exist_ok=False)
    os.chdir(job_dir)
    ready_ns = time.monotonic_ns()
    if _GLOBAL_BARRIER is None:
        raise RuntimeError("R339 concurrency barrier is unavailable")
    _GLOBAL_BARRIER.wait(timeout=120)
    started_ns = time.monotonic_ns()

    from andes_rl_kundur.env.andes.model_first_contract import (
        ModelFirstConfig,
        Stage1OperatingPoint,
        weighted_common_differential_transform,
    )
    from andes_rl_kundur.env.andes.model_first_env import AndesModelFirstEnv
    from andes_rl_kundur.env.andes.model_first_pq_disturbance import (
        _freeze_constant_power_load,
    )

    class R339BaselineEnv(AndesModelFirstEnv):
        def _pre_setup_addons(self, system):
            super()._pre_setup_addons(system)
            for device_idx, _bus, active, reactive in BASELINES:
                system.PQ.set("p0", device_idx, active, attr="v")
                system.PQ.set("q0", device_idx, reactive, attr="v")
            _freeze_constant_power_load(system)

    point_values = POINTS[spec["point"]]
    point = Stage1OperatingPoint(spec["point"], **point_values)
    config = ModelFirstConfig.for_stage1_operating_point(point)
    env = R339BaselineEnv(model_first_config=config)
    try:
        env.reset()
        system = env.ss
        models = system.exist.pflow_tds
        system.TDS.fg_update(models=models)
        system.j_update(models=models, info="R339 base descriptor snapshot")

        base_x = np.asarray(system.dae.x, dtype=float).copy()
        base_y = np.asarray(system.dae.y, dtype=float).copy()
        base_z = np.asarray(system.dae.z, dtype=float).copy()
        base_f = np.asarray(system.dae.f, dtype=float).copy()
        base_g = np.asarray(system.dae.g, dtype=float).copy()
        tf = np.asarray(system.dae.Tf, dtype=float).copy()
        fx = _dense_andes_matrix(system.dae.fx)
        fy = _dense_andes_matrix(system.dae.fy)
        gx = _dense_andes_matrix(system.dae.gx)
        gy = _dense_andes_matrix(system.dae.gy)
        eig_as = np.asarray(system.EIG.calc_As(dense=True), dtype=float)
        eig_names = [str(value) for value in system.EIG.x_name]

        transform = weighted_common_differential_transform(np.full(4, point.vsg_m_system))
        output_map = np.zeros((4, base_x.size), dtype=float)
        omega_addresses = np.asarray(system.GENCLS.omega.a, dtype=int)[env._vsg_pos]
        for output_index in range(4):
            output_map[output_index, omega_addresses] = transform.forward[output_index]

        base_snapshot = {
            "point": spec["point"],
            "operating_point": dict(point_values),
            "x": base_x,
            "y": base_y,
            "z": base_z,
            "f": base_f,
            "g": base_g,
            "Tf": tf,
            "f_x": fx,
            "f_y": fy,
            "g_x": gx,
            "g_y": gy,
            "state_names": [str(value) for value in system.dae.x_name],
            "algebraic_names": [str(value) for value in system.dae.y_name],
            "eig_state_names": eig_names,
            "eig_state_matrix": eig_as,
            "output_map": output_map,
            "omega_state_addresses": omega_addresses,
            "coordinate_forward": transform.forward,
            "coordinate_inverse": transform.inverse,
            "line_8_in_service": env._line_8_in_service(),
            "g4": env._g4_snapshot(),
            "structural_contract": env.structural_contract(),
        }
        base_snapshot_json = _jsonable(base_snapshot)
        base_snapshot_digest = payload_sha256(base_snapshot_json)

        if spec["input_family"] == "control":
            channel_ids = [str(value) for value in env.bess_idx]
            equilibrium_input = env._get_esd1_vector("Pext0")

            def set_inputs(values: np.ndarray) -> None:
                for device_idx, value in zip(channel_ids, values, strict=True):
                    system.DG.set_paux(system, device_idx, float(value))

        elif spec["input_family"] == "load":
            channel_ids = [row[0] for row in BASELINES]
            positions = [int(system.PQ.idx2uid(name)) for name in channel_ids]
            equilibrium_input = np.asarray(
                [system.PQ.Ppf.v[position] for position in positions], dtype=float
            )

            def set_inputs(values: np.ndarray) -> None:
                for device_idx, value in zip(channel_ids, values, strict=True):
                    system.PQ.set("Ppf", device_idx, float(value), attr="v")

        else:
            raise RuntimeError(f"unknown input family: {spec['input_family']}")

        branch_reference = _branch_snapshot(env)
        branch_reference_digest = payload_sha256(_jsonable(branch_reference))
        selected_column = int(spec["channel"])
        if selected_column < 0 or selected_column >= equilibrium_input.size:
            raise RuntimeError("R339 input column is outside the frozen catalog")
        step_results: list[dict[str, object]] = []
        for difference_step in FINITE_DIFFERENCE_STEPS:
            branch_digests: list[str] = []

            def residual(command: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
                system.dae.x[:] = base_x
                system.dae.y[:] = base_y
                system.dae.z[:] = base_z
                set_inputs(np.asarray(command, dtype=float))
                system.TDS.fg_update(models=models)
                f_value = np.asarray(system.dae.f, dtype=float).copy()
                g_value = np.asarray(system.dae.g, dtype=float).copy()
                branch_digests.append(payload_sha256(_jsonable(_branch_snapshot(env))))
                return f_value, g_value

            centre_f, centre_g = residual(equilibrium_input)
            positive = equilibrium_input.copy()
            negative = equilibrium_input.copy()
            positive[selected_column] += difference_step
            negative[selected_column] -= difference_step
            plus_f, plus_g = residual(positive)
            minus_f, minus_g = residual(negative)
            f_input_column = ((plus_f - minus_f) / (2.0 * difference_step))[:, None]
            g_input_column = ((plus_g - minus_g) / (2.0 * difference_step))[:, None]
            centre = np.concatenate([centre_f, centre_g])
            plus = np.concatenate([plus_f, plus_g])
            minus = np.concatenate([minus_f, minus_g])
            even = (plus + minus) / 2.0 - centre
            odd = (plus - minus) / 2.0
            midpoint_ratio = float(np.linalg.norm(even) / max(np.linalg.norm(odd), 1.0e-12))
            step_results.append(
                {
                    "step_system_pu": difference_step,
                    "f_input_column": f_input_column,
                    "g_input_column": g_input_column,
                    "midpoint_ratio": midpoint_ratio,
                    "branch_reference_sha256": branch_reference_digest,
                    "all_branch_snapshots_match": all(
                        digest == branch_reference_digest for digest in branch_digests
                    ),
                }
            )

        system.dae.x[:] = base_x
        system.dae.y[:] = base_y
        system.dae.z[:] = base_z
        set_inputs(equilibrium_input)
        system.TDS.fg_update(models=models)
        restored = bool(
            np.array_equal(np.asarray(system.dae.x), base_x)
            and np.array_equal(np.asarray(system.dae.y), base_y)
            and np.array_equal(np.asarray(system.dae.z), base_z)
            and np.array_equal(np.asarray(system.dae.f), base_f)
            and np.array_equal(np.asarray(system.dae.g), base_g)
        )
        ended_ns = time.monotonic_ns()
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "point": spec["point"],
            "input_family": spec["input_family"],
            "channel": selected_column,
            "base_snapshot_sha256": base_snapshot_digest,
            "base_snapshot": base_snapshot_json,
            "channel_ids": channel_ids,
            "equilibrium_input_system_pu": equilibrium_input.tolist(),
            "steps": _jsonable(step_results),
            "restored_exactly": restored,
            "job_metadata": {
                "pid": os.getpid(),
                "ready_monotonic_ns": ready_ns,
                "started_monotonic_ns": started_ns,
                "ended_monotonic_ns": ended_ns,
                "elapsed_seconds": (ended_ns - started_ns) / 1.0e9,
                "process_cpu_seconds": usage.ru_utime + usage.ru_stime,
                "maximum_resident_set_kib": int(usage.ru_maxrss),
                "scratch_dir": str(job_dir),
                "native_threads": {
                    name: os.environ.get(name)
                    for name in (
                        "OMP_NUM_THREADS",
                        "OPENBLAS_NUM_THREADS",
                        "MKL_NUM_THREADS",
                        "NUMEXPR_NUM_THREADS",
                    )
                },
                "python": sys.version,
                "platform": platform.platform(),
                "andes": importlib.metadata.version("andes"),
            },
        }
    finally:
        env.close()


def run_parallel_jobs() -> list[dict[str, Any]]:
    """Run all per-channel jobs with one process per physical host core."""

    global _GLOBAL_BARRIER
    if os.name != "posix":
        raise RuntimeError("R339 parallel live extraction is WSL/POSIX-only")
    import multiprocessing as mp

    context = mp.get_context("fork")
    _GLOBAL_BARRIER = context.Barrier(WHOLE_HOST_PYTHON_PROCESSES)
    results: list[dict[str, Any]] = []
    with ProcessPoolExecutor(
        max_workers=WHOLE_HOST_PYTHON_PROCESSES - 1,
        mp_context=context,
    ) as executor:
        futures = [executor.submit(_extract_live_job, dict(spec)) for spec in JOB_SPECS[1:]]
        results.append(_extract_live_job(dict(JOB_SPECS[0])))
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda row: (row["point"], row["input_family"], int(row["channel"])))
    pids = {int(row["job_metadata"]["pid"]) for row in results}
    latest_start = max(int(row["job_metadata"]["started_monotonic_ns"]) for row in results)
    earliest_end = min(int(row["job_metadata"]["ended_monotonic_ns"]) for row in results)
    if (
        len(results) != WHOLE_HOST_PYTHON_PROCESSES
        or len(pids) != WHOLE_HOST_PYTHON_PROCESSES
        or latest_start >= earliest_end
    ):
        raise RuntimeError("sixteen-job concurrency or process isolation did not pass")
    return results


def _combined_points(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {(row["point"], row["input_family"], int(row["channel"])): row for row in jobs}
    expected_keys = {
        (point, family, channel)
        for point in ("HS0", "HS1")
        for family in ("control", "load")
        for channel in range(4)
    }
    if set(by_key) != expected_keys:
        raise RuntimeError("R339 live job inventory mismatch")
    combined: list[dict[str, Any]] = []
    for point in ("HS0", "HS1"):
        families: dict[str, dict[str, Any]] = {}
        for family in ("control", "load"):
            columns = [by_key[(point, family, channel)] for channel in range(4)]
            families[family] = {
                "point": point,
                "input_family": family,
                "base_snapshot_sha256": columns[0]["base_snapshot_sha256"],
                "base_snapshot": columns[0]["base_snapshot"],
                "input_derivatives": combine_family_jobs(columns),
                "job_metadata": [row["job_metadata"] for row in columns],
            }
        combined.append(combine_point_jobs(families["control"], families["load"]))
    return combined


def rehearse(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    """Traverse the formal pre-attempt path without writing project output."""

    seal, seal_digest = _load_seal(seal_path, expected_sha256)
    installed = _verify_installed_andes(seal)
    if out_dir.exists() or (out_dir / "formal_attempt.json").exists():
        raise FileExistsError(f"R339 formal output must be absent: {out_dir}")
    jobs = run_parallel_jobs()
    points = _combined_points(jobs)
    print(f"rehearsal_seal_sha256={seal_digest}")
    print(f"rehearsal_installed_case_sha256={installed['case']['sha256']}")
    print(f"rehearsal_job_count={len(jobs)}")
    print(f"rehearsal_unique_processes={len({row['job_metadata']['pid'] for row in jobs})}")
    print(f"rehearsal_point_count={len(points)}")
    print(
        "rehearsal_max_worker_rss_kib="
        f"{max(row['job_metadata']['maximum_resident_set_kib'] for row in jobs)}"
    )
    print(
        "rehearsal_worker_cpu_seconds_sum="
        f"{sum(row['job_metadata']['process_cpu_seconds'] for row in jobs):.6f}"
    )
    print(
        "rehearsal_overlap_wall_seconds="
        f"{(max(row['job_metadata']['ended_monotonic_ns'] for row in jobs) - min(row['job_metadata']['started_monotonic_ns'] for row in jobs)) / 1.0e9:.6f}"
    )
    print("rehearsal_output_created=false")


def _reserve_attempt(out_dir: Path, seal_digest: str) -> str:
    if out_dir.exists():
        raise FileExistsError(f"R339 formal output already exists: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=False)
    return write_new_json(
        out_dir / "formal_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "physical_execution_started": True,
            "fresh_nonlinear_trajectory_started": False,
            "retry_authorized": False,
        },
    )


def execute(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    """Execute the sealed sixteen-job descriptor extraction once."""

    seal, seal_digest = _load_seal(seal_path, expected_sha256)
    installed = _verify_installed_andes(seal)
    attempt_digest = _reserve_attempt(out_dir, seal_digest)
    try:
        jobs = run_parallel_jobs()
        points = _combined_points(jobs)
        execution_digest = write_new_json(
            out_dir / "execution.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "seal_sha256": seal_digest,
                "formal_attempt_sha256": attempt_digest,
                "job_count": len(jobs),
                "unique_process_count": len({row["job_metadata"]["pid"] for row in jobs}),
                "points": points,
                "fresh_nonlinear_trajectory_executed": False,
                "controller_executed": False,
                "training_executed": False,
                "eval_executed": False,
            },
        )
        provenance_digest = write_new_json(
            out_dir / "provenance.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "seal_sha256": seal_digest,
                "formal_attempt_sha256": attempt_digest,
                "execution_sha256": execution_digest,
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
            out_dir / "run_manifest.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "entries": [
                    {"path": "formal_attempt.json", "sha256": attempt_digest},
                    {"path": "execution.json", "sha256": execution_digest},
                    {"path": "provenance.json", "sha256": provenance_digest},
                ],
            },
        )
    except Exception as error:
        try:
            write_new_json(
                out_dir / "execution_failure.json",
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "question": QUESTION_ID,
                    "created_utc": datetime.now(UTC).isoformat(),
                    "seal_sha256": seal_digest,
                    "formal_attempt_sha256": attempt_digest,
                    "classification": "INVALID",
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "retry_authorized": False,
                },
            )
        finally:
            raise
    print(f"execution_sha256={execution_digest}")
    print(f"provenance_sha256={provenance_digest}")
    print(f"run_manifest_sha256={manifest_digest}")


def _sealed_parent_json(
    seal: dict[str, Any],
    name: str,
) -> tuple[dict[str, Any], str]:
    row = seal.get("parents", {}).get(name)
    if not isinstance(row, dict):
        raise RuntimeError(f"sealed parent is missing: {name}")
    return read_verified_json(
        ROOT / str(row["path"]),
        expected_sha256=str(row["sha256"]),
    )


def analyse(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    """Replay the frozen pure analysis over verified formal and parent data."""

    from probes.r339_input_bridge_diagnosis import analyse_r339_input_bridge

    seal, seal_digest = _load_seal(seal_path, expected_sha256)
    manifest, manifest_digest = read_verified_json(out_dir / "run_manifest.json")
    entries = {str(row["path"]): str(row["sha256"]) for row in manifest.get("entries", [])}
    required_entries = {
        "formal_attempt.json",
        "execution.json",
        "provenance.json",
    }
    if set(entries) != required_entries:
        raise RuntimeError("R339 formal run manifest inventory mismatch")
    attempt, attempt_digest = read_verified_json(
        out_dir / "formal_attempt.json",
        expected_sha256=entries["formal_attempt.json"],
    )
    execution, execution_digest = read_verified_json(
        out_dir / "execution.json",
        expected_sha256=entries["execution.json"],
    )
    provenance, provenance_digest = read_verified_json(
        out_dir / "provenance.json",
        expected_sha256=entries["provenance.json"],
    )
    if (
        attempt.get("seal_sha256") != seal_digest
        or execution.get("seal_sha256") != seal_digest
        or provenance.get("seal_sha256") != seal_digest
        or execution.get("formal_attempt_sha256") != attempt_digest
        or provenance.get("formal_attempt_sha256") != attempt_digest
        or provenance.get("execution_sha256") != execution_digest
    ):
        raise RuntimeError("R339 formal evidence-chain mismatch")

    development, development_digest = _sealed_parent_json(seal, "r336_development_execution")
    second_point, second_point_digest = _sealed_parent_json(seal, "r336_second_point_execution")
    r336_analysis, r336_analysis_digest = _sealed_parent_json(seal, "r336_analysis")
    first = analyse_r339_input_bridge(
        execution,
        development,
        second_point,
        r336_analysis,
    )
    second = analyse_r339_input_bridge(
        execution,
        development,
        second_point,
        r336_analysis,
    )
    replay_digest = payload_sha256(first)
    if payload_sha256(second) != replay_digest:
        raise RuntimeError("R339 pure analysis is not deterministic")
    analysis_payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "formal_attempt_sha256": attempt_digest,
        "execution_sha256": execution_digest,
        "provenance_sha256": provenance_digest,
        "run_manifest_sha256": manifest_digest,
        "parent_sha256": {
            "r336_development_execution": development_digest,
            "r336_second_point_execution": second_point_digest,
            "r336_analysis": r336_analysis_digest,
        },
        "deterministic_replay_payload_sha256": replay_digest,
        **first,
    }
    analysis_digest = write_new_json(out_dir / "analysis.json", analysis_payload)
    print(f"classification={analysis_payload['classification']}")
    print(f"analysis_sha256={analysis_digest}")
    print(f"deterministic_replay_payload_sha256={replay_digest}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    for name in ("rehearse", "execute", "analyse"):
        child = subparsers.add_parser(name)
        child.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
        child.add_argument("--expected-sha256", required=True)
        child.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "prepare":
        prepare(args.seal)
    elif args.command == "rehearse":
        rehearse(args.seal, args.expected_sha256, args.out_dir)
    elif args.command == "execute":
        execute(args.seal, args.expected_sha256, args.out_dir)
    elif args.command == "analyse":
        analyse(args.seal, args.expected_sha256, args.out_dir)
    else:
        raise AssertionError(args.command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
