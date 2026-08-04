"""Prepare, execute, and analyse the R335 physical disturbance package.

Usage::

    python scripts/run_r335_disturbance_package.py prepare
    python scripts/andes_scratch.py scripts/run_r335_disturbance_package.py execute --expected-sha256 <seal>
    python scripts/run_r335_disturbance_package.py analyse --expected-sha256 <seal>

Physical commands are WSL-only.  Formal outputs are create-only, HS0 fitting
is persisted before HS1 execution, and no controller, training, or EVAL path is
imported or executed.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import os
import platform
import sys
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

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
from probes.r335_disturbance_package import (  # noqa: E402
    analyse_r335_disturbance_package,
    fit_r335_disturbance_map,
)
from scripts import run_r333_pq_disturbance_identification as _r333  # noqa: E402

from andes_rl_kundur.env.andes.model_first_contract import (  # noqa: E402
    ModelFirstConfig,
    Stage1OperatingPoint,
    stage1_power_coordinates,
    weighted_common_differential_transform,
)
from andes_rl_kundur.env.andes.model_first_pq_disturbance import (  # noqa: E402
    pq_runtime_snapshot,
)
from andes_rl_kundur.env.andes.model_first_pq_profile import (  # noqa: E402
    PQProfileBaseline,
    TimedPQProfileContract,
    TimedPQProfileMixin,
)

ROUND_ID = "R335"
QUESTION_ID = "Q-0086"
DEFAULT_SEAL = ROOT / "memory/rounds/R335/disturbance_package_seal.json"
DEFAULT_OUT = ROOT / "results/r335_disturbance_package"
R316_MODEL = ROOT / "results/r316_dynamic_reduction/dynamic_model.json"

POINTS = (
    Stage1OperatingPoint("HS0", 177.5, 88.75, 1.10, 0.41),
    Stage1OperatingPoint("HS1", 202.5, 101.25, 1.35, 0.51),
)
CHANNELS = (
    {
        "device_idx": "PQ_0",
        "bus_idx": 7,
        "node_index": 0,
        "initial_active_system_pu": 11.59,
        "initial_reactive_system_pu": -0.735,
    },
    {
        "device_idx": "PQ_1",
        "bus_idx": 8,
        "node_index": 1,
        "initial_active_system_pu": 15.75,
        "initial_reactive_system_pu": -0.899,
    },
    {
        "device_idx": "PQ_Bus14",
        "bus_idx": 14,
        "node_index": 2,
        "initial_active_system_pu": 2.48,
        "initial_reactive_system_pu": 0.0,
    },
    {
        "device_idx": "PQ_Bus15",
        "bus_idx": 15,
        "node_index": 3,
        "initial_active_system_pu": 0.05,
        "initial_reactive_system_pu": 0.0,
    },
)
SHAPES = {
    "impulse": (0.05,),
    "triangle": (0.02, 0.04, 0.05, 0.04, 0.02),
}
TOTAL_STEPS = 25
SUBSTEPS = 5
PARALLEL_WORKERS = 4
DYNAMIC_TOLERANCE = 1.0e-10
EXPECTED_CASE_SHA256 = "f725e03ba12d8207616f68acdd606bbd35e7c4a68f13e66d7db43925adac2ed8"

BASELINES = tuple(
    PQProfileBaseline(
        str(row["device_idx"]),
        int(row["bus_idx"]),
        float(row["initial_active_system_pu"]),
        float(row["initial_reactive_system_pu"]),
    )
    for row in CHANNELS
)


def _node_input_basis() -> np.ndarray:
    vectors = stage1_power_coordinates(1.0)
    return np.column_stack(
        [vectors[name] for name in ("common", "edge_0", "edge_1", "edge_2")]
    )


def build_contract() -> dict[str, object]:
    """Return the complete prospective R335 scientific contract."""

    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "four-channel-physical-disturbance-package",
        "development_point": "HS0",
        "holdout_point": "HS1",
        "operating_points": [point.name for point in POINTS],
        "operating_point_records": [
            {
                "name": point.name,
                "vsg_m_device": point.vsg_m_device,
                "vsg_d_device": point.vsg_d_device,
                "tie_rx_scale": point.tie_rx_scale,
                "initial_soc": point.initial_soc,
            }
            for point in POINTS
        ],
        "channels": [dict(row) for row in CHANNELS],
        "channel_names": [str(row["device_idx"]) for row in CHANNELS],
        "shapes": {name: list(values) for name, values in SHAPES.items()},
        "signs": ["positive", "negative"],
        "record_count_per_point": 1 + 2 * len(CHANNELS) * len(SHAPES),
        "record_count": 2 * (1 + 2 * len(CHANNELS) * len(SHAPES)),
        "total_steps": TOTAL_STEPS,
        "control_period_seconds": 0.2,
        "tds_substeps": SUBSTEPS,
        "tds_max_segment_seconds": 0.2 / SUBSTEPS,
        "parallel_workers_per_split": PARALLEL_WORKERS,
        "parallel_scope": "records within one split only",
        "development_fit_holdout_order_remains_serial": True,
        "event_start_seconds": 0.5,
        "event_row_semantics": "exact-event row is pre-event",
        "system_base_mva": 100.0,
        "vsg_device_base_mva": 200.0,
        "node_input_basis": _node_input_basis().tolist(),
        "frozen_input_coordinates": ["common", "edge_0", "edge_1", "edge_2"],
        "fit_method": "unregularized-joint-signed-waveform-least-squares",
        "thresholds": {
            "pq_readback_absolute_tolerance_system_pu": 1.0e-12,
            "zero_actuator_power_absolute_maximum_system_pu": 1.0e-6,
            "algebraic_residual_absolute_maximum": 1.0e-6,
            "signal_to_baseline_drift_energy_ratio_minimum": 10.0,
            "pair_midpoint_nonlinearity_ratio_maximum": 0.10,
            "total_nrmse_maximum": 0.15,
            "peak_vector_residual_maximum": 0.20,
            "node_power_sum_absolute_error_maximum": 0.20,
            "singular_value_ratio_minimum": 0.10,
        },
        "classifications": [
            "INVALID-PHYSICAL-DISTURBANCE-PACKAGE",
            "BLOCK",
            "QUALIFY",
            "ALLOW",
        ],
        "physical_execution_planned": True,
        "controller_executed": False,
        "closed_loop_executed": False,
        "distributed_runtime_executed": False,
        "training_executed": False,
        "eval_executed": False,
        "title_changed": False,
        "reward_diagnostics_computed": True,
        "reward_diagnostics_stored": True,
        "reward_used_for_action": False,
        "reward_used_for_fitting": False,
        "reward_used_for_selection": False,
        "reward_used_for_training": False,
        "reward_used_for_classification": False,
        "reward_used_for_claim": False,
    }


def _path_text(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


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


def _source_paths() -> dict[str, Path]:
    paths = {
        f"src_{path.relative_to(SRC).as_posix()}": path
        for path in sorted(SRC.rglob("*.py"))
    }
    paths.update(
        {
            "r335_probe": ROOT / "probes/r335_disturbance_package.py",
            "r335_adapter": ROOT / "scripts/run_r335_disturbance_package.py",
            "r335_profile_tests": ROOT / "tests/test_model_first_pq_profile.py",
            "r335_probe_tests": ROOT / "tests/test_r335_disturbance_package.py",
            "r335_adapter_tests": ROOT
            / "tests/test_r335_disturbance_package_adapter.py",
            "r333_adapter": ROOT
            / "scripts/run_r333_pq_disturbance_identification.py",
            "r333_probe": ROOT / "probes/r333_pq_disturbance_identification.py",
            "andes_scratch": ROOT / "scripts/andes_scratch.py",
            "artifact_io": ROOT / "memory/tools/artifact_io.py",
        }
    )
    by_path: dict[str, tuple[str, Path]] = {}
    for name, path in paths.items():
        relative = _path_text(path)
        by_path.setdefault(relative, (name, path))
    return {name: path for name, path in by_path.values()}


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": sha256_file(path)}
        for name, path in sorted(_source_paths().items())
    }


def _parent_paths() -> dict[str, Path]:
    return {
        "r316_model": R316_MODEL,
        "r316_analysis": ROOT / "results/r316_dynamic_reduction/analysis.json",
        "r329_seal": ROOT / "memory/rounds/R329/disturbance_estimator_seal.json",
        "r329_analysis": ROOT / "results/r329_disturbance_estimator/analysis.json",
        "r334_seal": ROOT
        / "memory/rounds/R334/pq_disturbance_identification_seal.json",
        "r334_analysis": ROOT
        / "results/r334_pq_disturbance_identification/analysis.json",
        "r334_claim": ROOT / "memory/claims/CLM-0880.md",
        "r335_plan": ROOT / "memory/rounds/R335/plan.md",
        "q0086": ROOT / "memory/questions/Q-0086.md",
    }


def _parents() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": sha256_file(path)}
        for name, path in sorted(_parent_paths().items())
    }


def prepare(seal_path: Path, *, created_utc: str | None = None) -> str:
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
            "installed_sources": dict(_r333.EXPECTED_INSTALLED_SOURCES),
            "case_sha256": EXPECTED_CASE_SHA256,
        },
        "formal_artifacts_create_only": True,
        "formal_retry_authorized": False,
        "holdout_access_before_fit_forbidden": True,
    }
    digest = write_new_json(seal_path, payload)
    print(f"seal_sha256={digest}")
    print(f"source_inventory_count={len(payload['sources'])}")
    return digest


def _load_seal(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    payload, digest = read_verified_json(path, expected_sha256=expected_sha256)
    if payload.get("round") != ROUND_ID or payload.get("question") != QUESTION_ID:
        raise RuntimeError("R335 seal identity mismatch")
    if payload.get("contract") != build_contract():
        raise RuntimeError("R335 seal contract drift")
    if payload.get("contract_payload_sha256") != payload_sha256(build_contract()):
        raise RuntimeError("R335 seal contract payload hash mismatch")
    for row in payload.get("sources", {}).values():
        if sha256_file(ROOT / row["path"]) != row["sha256"]:
            raise RuntimeError(f"sealed source drift: {row['path']}")
    for row in payload.get("parents", {}).values():
        if sha256_file(ROOT / row["path"]) != row["sha256"]:
            raise RuntimeError(f"sealed parent drift: {row['path']}")
    return payload, digest


def _verify_installed_andes(seal: dict[str, Any]) -> dict[str, object]:
    installed = _r333._verify_installed_andes()
    expected = seal["expected_runtime"]
    if importlib.metadata.version("andes") != expected["andes_version"]:
        raise RuntimeError("installed ANDES version drift")
    if installed["sources"] != expected["installed_sources"]:
        raise RuntimeError("installed ANDES source drift")
    if installed["case"]["sha256"] != expected["case_sha256"]:
        raise RuntimeError("installed Kundur case drift")
    return installed


def _load_r316_model() -> tuple[dict[str, Any], str]:
    payload, digest = read_verified_json(R316_MODEL)
    if payload.get("round") != "R316" or set(payload.get("points", {})) != {
        "HS0",
        "HS1",
    }:
        raise RuntimeError("R316 dynamic model identity mismatch")
    return payload, digest


def _manifest_entries_match(
    manifest: dict[str, Any], expected: dict[str, str]
) -> bool:
    entries = manifest.get("entries")
    if not isinstance(entries, list) or len(entries) != len(expected):
        return False
    indexed: dict[str, str] = {}
    for row in entries:
        if not isinstance(row, dict):
            return False
        path = str(row.get("path"))
        digest = str(row.get("sha256"))
        if path in indexed:
            return False
        indexed[path] = digest
    return indexed == expected


def _profile_contract(
    *, channel: dict[str, object] | None, shape: str, sign: str
) -> TimedPQProfileContract:
    if channel is None:
        target = CHANNELS[-1]
        profile = (0.0,)
        prefix = "R335_zero"
    else:
        target = channel
        multiplier = 1.0 if sign == "positive" else -1.0
        profile = tuple(multiplier * value for value in SHAPES[shape])
        prefix = f"R335_{target['device_idx']}_{shape}_{sign}"
    return TimedPQProfileContract(
        event_prefix=prefix,
        device_idx=str(target["device_idx"]),
        bus_idx=int(target["bus_idx"]),
        initial_active_system_pu=float(target["initial_active_system_pu"]),
        initial_reactive_system_pu=float(target["initial_reactive_system_pu"]),
        delta_profile_system_pu=profile,
        plant_baselines=BASELINES,
    )


def _event_grid_guard(times: object, event_times: list[float]) -> dict[str, object]:
    grid = np.asarray(times, dtype=float).reshape(-1)
    strictly_increasing = bool(
        grid.size and np.all(np.isfinite(grid)) and np.all(np.diff(grid) > 0.0)
    )
    details: dict[str, object] = {}
    passed = strictly_increasing
    for event_time in sorted(set(event_times)):
        exact = np.flatnonzero(grid == event_time)
        before = np.flatnonzero(
            np.isclose(grid, event_time - 1.0e-4, rtol=0.0, atol=1.0e-12)
        )
        after = np.flatnonzero(
            np.isclose(grid, event_time + 1.0e-4, rtol=0.0, atol=1.0e-12)
        )
        row_pass = bool(
            len(exact) == len(before) == len(after) == 1
            and before[0] < exact[0] < after[0]
        )
        passed = passed and row_pass
        details[f"{event_time:.6f}"] = {
            "event_time_seconds": event_time,
            "pre_critical_present": len(before) == 1,
            "exact_row_present": len(exact) == 1,
            "first_post_critical_present": len(after) == 1,
            "exact_row_semantics": "pre-event",
        }
    return {"pass": bool(passed), "strictly_increasing": strictly_increasing, "events": details}


def _baseline_readback(system: Any) -> dict[str, dict[str, object]]:
    return {
        baseline.device_idx: pq_runtime_snapshot(
            system,
            SimpleNamespace(device_idx=baseline.device_idx, bus_idx=baseline.bus_idx),
        )
        for baseline in BASELINES
    }


def _baseline_snapshot_guard(
    snapshots: dict[str, dict[str, object]], *, tolerance: float
) -> bool:
    expected_weights = {
        "p2p": 1.0,
        "p2i": 0.0,
        "p2z": 0.0,
        "q2q": 1.0,
        "q2i": 0.0,
        "q2z": 0.0,
    }
    if set(snapshots) != {row.device_idx for row in BASELINES}:
        return False
    for baseline in BASELINES:
        row = snapshots[baseline.device_idx]
        replacements = row.get("replacement_records", {})
        if not isinstance(replacements, dict):
            return False
        replacement_rows = []
        for name in ("FLoad", "ZIP"):
            items = replacements.get(name, [])
            if not isinstance(items, list):
                return False
            replacement_rows.extend(items)
        if not (
            row.get("device_idx") == baseline.device_idx
            and row.get("bus_idx") == baseline.bus_idx
            and row.get("raw_active") is True
            and row.get("effective_active") is True
            and row.get("active") is True
            and abs(float(row.get("Ppf_system_pu")) - baseline.active_system_pu)
            <= tolerance
            and abs(float(row.get("Qpf_system_pu")) - baseline.reactive_system_pu)
            <= tolerance
            and row.get("pq2z_config") == 0
            and row.get("vcmp_enable") == 0
            and row.get("constant_power_weights") == expected_weights
            and row.get("active_fload_replacements_for_device") == 0
            and row.get("active_zip_replacements_for_device") == 0
            and all(not bool(item.get("raw_active")) for item in replacement_rows)
        ):
            return False
    return True


def _event_receipts(
    contract: TimedPQProfileContract,
    audit: list[dict[str, Any]],
) -> list[dict[str, object]]:
    receipts: list[dict[str, object]] = []
    for event in contract.alter_records():
        matches = [row for row in audit if event["idx"] in row["event_ids"]]
        if len(matches) != 1:
            receipts.append({"idx": event["idx"], "valid": False, "match_count": len(matches)})
            continue
        row = matches[0]
        receipts.append(
            {
                "idx": event["idx"],
                "scheduled_event_time_seconds": float(event["t"]),
                "observation_time_seconds": float(row["after"]["dae_time_seconds"]),
                "time_absolute_error_seconds": abs(
                    float(row["after"]["dae_time_seconds"]) - float(event["t"])
                ),
                "before_system_pu": float(row["before"]["Ppf_system_pu"]),
                "target_system_pu": float(event["amount"]),
                "readback_system_pu": float(row["after"]["Ppf_system_pu"]),
                "absolute_error_system_pu": abs(
                    float(row["after"]["Ppf_system_pu"]) - float(event["amount"])
                ),
                "valid": True,
            }
        )
    return receipts


@contextmanager
def _substep_environment():
    with _r333._substep_environment():
        yield


def _run_record(
    *,
    point: Stage1OperatingPoint,
    channel: dict[str, object] | None,
    shape: str,
    sign: str,
    seal_digest: str,
    model_digest: str,
) -> dict[str, object]:
    from andes_rl_kundur.env.andes.model_first_env import AndesModelFirstEnv

    class AndesModelFirstProfileEnv(TimedPQProfileMixin, AndesModelFirstEnv):
        def __init__(self, *, pq_profile_contract, **kwargs):
            self.pq_profile_contract = pq_profile_contract
            super().__init__(**kwargs)

    contract = _profile_contract(channel=channel, shape=shape, sign=sign)
    config = replace(
        ModelFirstConfig.for_stage1_operating_point(point),
        tds_post_initialization_convergence_tolerance=DYNAMIC_TOLERANCE,
    )
    active_profile = np.asarray(contract.delta_profile_system_pu, dtype=float)
    padded_profile = np.zeros(TOTAL_STEPS, dtype=float)
    padded_profile[: active_profile.size] = active_profile

    with _substep_environment():
        env = AndesModelFirstProfileEnv(
            pq_profile_contract=contract,
            model_first_config=config,
        )
        rows: list[dict[str, Any]] = []
        try:
            env.reset()
            initial_audit = _jsonable(env.pq_event_audit)
            if not initial_audit:
                raise RuntimeError("first R335 timed profile event did not fire at reset")
            setup_baselines = _baseline_readback(env.ss)
            first_before = initial_audit[0]["before"]
            setup_baselines[contract.device_idx] = first_before
            event_inventory = _r333._alter_event_inventory(env.ss)
            tie_line_readback = _r333._tie_line_readback(env.ss)
            initialization = _jsonable(env._model_first_initialization_solver_contract)
            zero_md = {index: np.zeros(2) for index in range(env.N_AGENTS)}
            for step in range(TOTAL_STEPS):
                _, _, _, info = env.step(
                    zero_md,
                    bess_power_request_pu=np.zeros(4),
                )
                row = _jsonable(info)
                row["step"] = step
                row["t"] = row.pop("time")
                row["pq_active_load_delta_system_pu"] = float(padded_profile[step])
                frequency = np.asarray(row["freq_hz_physical"], dtype=float)
                row["delta_f_physical_hz"] = (frequency - 60.0).tolist()
                rows.append(row)
            event_callback_audit = _jsonable(env.pq_event_audit)
            env.ss.dae.ts.unpack(attr="t", warn_empty=False)
            tds_grid = np.asarray(env.ss.dae.ts.t, dtype=float).copy()
            terminal_baselines = _baseline_readback(env.ss)
        finally:
            env.close()

    transform = weighted_common_differential_transform(np.full(4, point.vsg_m_system))
    delta_frequency = np.asarray(
        [row["delta_f_physical_hz"] for row in rows], dtype=float
    )
    outputs = (transform.forward @ (delta_frequency / 60.0).T).T
    expected_inventory = list(contract.alter_records())
    event_times = [float(event["t"]) for event in expected_inventory]
    event_grid = _event_grid_guard(tds_grid, event_times)
    receipts = _event_receipts(contract, event_callback_audit)
    fire_counts = {
        event["idx"]: sum(
            int(event["idx"] in batch["event_ids"]) for batch in event_callback_audit
        )
        for event in expected_inventory
    }
    tolerance = 1.0e-12
    setup_guard = _baseline_snapshot_guard(setup_baselines, tolerance=tolerance)
    terminal_guard = _baseline_snapshot_guard(terminal_baselines, tolerance=tolerance)
    completed = len(rows) == TOTAL_STEPS and not any(
        bool(row["tds_failed"]) for row in rows
    )
    zero_actuator = (
        max(int(row["md_write_count"]) for row in rows) == 0
        and max(
            float(np.max(np.abs(row["bess_requested_power_system_pu"])))
            for row in rows
        )
        <= 1.0e-6
        and max(
            float(np.max(np.abs(row["bess_commanded_power_system_pu"])))
            for row in rows
        )
        <= 1.0e-6
        and max(
            float(np.max(np.abs(row["bess_actual_power_system_pu"])))
            for row in rows
        )
        <= 1.0e-6
    )
    reward_fields = ("r_f", "r_h", "r_d", "r_smooth")
    reward_stored = all(
        all(name in row and np.isfinite(float(row[name])) for name in reward_fields)
        for row in rows
    )
    record_valid = bool(
        event_inventory == expected_inventory
        and all(count == 1 for count in fire_counts.values())
        and event_grid["pass"] is True
        and all(
            receipt.get("valid") is True
            and float(receipt["absolute_error_system_pu"]) <= tolerance
            and float(receipt["time_absolute_error_seconds"]) <= 1.0e-9
            for receipt in receipts
        )
        and setup_guard
        and terminal_guard
        and completed
        and zero_actuator
        and all(bool(row["line_8_in_service"]) for row in rows)
        and all(bool(row["g4_in_service"]) for row in rows)
        and all(bool(row["finite_state_algebraic"]) for row in rows)
        and max(abs(int(row["system_exit_code"])) for row in rows) == 0
        and max(float(row["dae_g_residual_max"]) for row in rows) <= 1.0e-6
        and reward_stored
    )
    channel_name = "zero" if channel is None else str(channel["device_idx"])
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "seal_sha256": seal_digest,
        "dynamic_model_sha256": model_digest,
        "operating_point": point.name,
        "operating_point_configuration": {
            "name": point.name,
            "vsg_m_device": point.vsg_m_device,
            "vsg_d_device": point.vsg_d_device,
            "tie_rx_scale": point.tie_rx_scale,
            "initial_soc": point.initial_soc,
        },
        "channel": channel_name,
        "shape": shape,
        "sign": sign,
        "event_contract": contract.to_dict(),
        "event_inventory": event_inventory,
        "alter_event_inventory_guard": event_inventory == expected_inventory,
        "event_callback_audit": event_callback_audit,
        "event_fire_counts": fire_counts,
        "event_grid": _jsonable(event_grid),
        "event_receipts": receipts,
        "setup_baseline_readback": _jsonable(setup_baselines),
        "terminal_baseline_readback": _jsonable(terminal_baselines),
        "setup_baseline_guard": setup_guard,
        "terminal_restore_guard": terminal_guard,
        "tie_line_readback": tie_line_readback,
        "completed": completed,
        "n_steps": len(rows),
        "requested_steps": TOTAL_STEPS,
        "delta_profile_system_pu": padded_profile.tolist(),
        "time_seconds": [float(row["t"]) for row in rows],
        "tds_time_grid_seconds": tds_grid.tolist(),
        "output_coordinates": outputs.tolist(),
        "initialization_solver": initialization,
        "zero_actuator_guard": zero_actuator,
        "line_8_all_in_service": all(bool(row["line_8_in_service"]) for row in rows),
        "g4_all_in_service": all(bool(row["g4_in_service"]) for row in rows),
        "all_states_finite": all(bool(row["finite_state_algebraic"]) for row in rows),
        "system_exit_code_maximum": max(abs(int(row["system_exit_code"])) for row in rows),
        "algebraic_residual_absolute_maximum": max(
            float(row["dae_g_residual_max"]) for row in rows
        ),
        "reward_diagnostics_computed": reward_stored,
        "reward_diagnostics_stored": reward_stored,
        "reward_used_for_action": False,
        "reward_used_for_fitting": False,
        "reward_used_for_selection": False,
        "reward_used_for_training": False,
        "reward_used_for_classification": False,
        "reward_used_for_claim": False,
        "record_valid": record_valid,
        "traces": rows,
    }


def _record_specs(
    point: Stage1OperatingPoint, *, seal_digest: str, model_digest: str
) -> list[dict[str, object]]:
    specs: list[dict[str, object]] = [
        {
            "point": point,
            "channel": None,
            "shape": "zero",
            "sign": "zero",
            "seal_digest": seal_digest,
            "model_digest": model_digest,
        }
    ]
    for channel in CHANNELS:
        for shape in SHAPES:
            for sign in ("positive", "negative"):
                specs.append(
                    {
                        "point": point,
                        "channel": channel,
                        "shape": shape,
                        "sign": sign,
                        "seal_digest": seal_digest,
                        "model_digest": model_digest,
                    }
                )
    return specs


def _run_record_isolated(
    spec: dict[str, object], record_dir: Path
) -> dict[str, object]:
    record_dir.mkdir(parents=True, exist_ok=False)
    previous = Path.cwd()
    os.chdir(record_dir)
    try:
        return _run_record(**spec)
    finally:
        os.chdir(previous)


def _run_point(
    point: Stage1OperatingPoint, *, seal_digest: str, model_digest: str
) -> list[dict[str, object]]:
    specs = _record_specs(
        point,
        seal_digest=seal_digest,
        model_digest=model_digest,
    )
    work_root = Path.cwd() / f"r335_{point.name.lower()}_records"
    work_root.mkdir(parents=True, exist_ok=False)
    directories = []
    for index, spec in enumerate(specs):
        channel = spec["channel"]
        channel_name = "zero" if channel is None else str(channel["device_idx"])
        directories.append(
            work_root
            / f"{index:02d}_{channel_name}_{spec['shape']}_{spec['sign']}"
        )
    with ProcessPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
        futures = [
            executor.submit(_run_record_isolated, spec, directory)
            for spec, directory in zip(specs, directories, strict=True)
        ]
        return [future.result() for future in futures]


def canary(out_path: Path, *, full_point: bool = False) -> None:
    model, model_digest = _load_r316_model()
    if full_point:
        records = _run_point(
            POINTS[0],
            seal_digest="development-canary-not-formal",
            model_digest=model_digest,
        )
    else:
        records = [
            _run_record(
                point=POINTS[0],
                channel=CHANNELS[-1],
                shape="triangle",
                sign="positive",
                seal_digest="development-canary-not-formal",
                model_digest=model_digest,
            )
        ]
    digest = write_new_json(
        out_path,
        {
            "stage": "development-canary",
            "not_formal_evidence": True,
            "parallel_path_exercised": full_point,
            "records": records,
            "model_loaded": model.get("round") == "R316",
        },
    )
    print(f"canary_record_count={len(records)}")
    print(f"canary_all_records_valid={all(row['record_valid'] for row in records)}")
    print(f"canary_sha256={digest}")


def _reserve_attempt(out_dir: Path, seal_digest: str) -> str:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"R335 formal output is not empty: {out_dir}")
    return write_new_json(
        out_dir / "formal_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "physical_execution_started": True,
            "holdout_started": False,
            "controller_executed": False,
            "closed_loop_executed": False,
            "distributed_runtime_executed": False,
            "training_executed": False,
            "eval_executed": False,
            "retry_authorized": False,
        },
    )


def execute(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected_sha256)
    installed = _verify_installed_andes(seal)
    model, model_digest = _load_r316_model()
    attempt_digest = _reserve_attempt(out_dir, seal_digest)
    development_started = datetime.now(UTC).isoformat()
    try:
        development_records = _run_point(
            POINTS[0], seal_digest=seal_digest, model_digest=model_digest
        )
        development_digest = write_new_json(
            out_dir / "development_execution.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "started_utc": development_started,
                "seal_sha256": seal_digest,
                "formal_attempt_sha256": attempt_digest,
                "dynamic_model_sha256": model_digest,
                "split": "development",
                "operating_point": "HS0",
                "records": development_records,
            },
        )
        fit = fit_r335_disturbance_map(
            contract={
                **seal["contract"],
                "channels": seal["contract"]["channel_names"],
            },
            development_records=development_records,
            realization_payload=model["points"]["HS0"]["realization"],
        )
        fit.update(
            {
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "seal_sha256": seal_digest,
                "development_execution_sha256": development_digest,
                "dynamic_model_sha256": model_digest,
                "fit_created_before_holdout": True,
            }
        )
        fit_digest = write_new_json(out_dir / "fit.json", fit)
        holdout_started = datetime.now(UTC).isoformat()
        holdout_records = _run_point(
            POINTS[1], seal_digest=seal_digest, model_digest=model_digest
        )
        holdout_digest = write_new_json(
            out_dir / "holdout_execution.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "started_utc": holdout_started,
                "seal_sha256": seal_digest,
                "formal_attempt_sha256": attempt_digest,
                "fit_sha256": fit_digest,
                "dynamic_model_sha256": model_digest,
                "split": "holdout",
                "operating_point": "HS1",
                "records": holdout_records,
            },
        )
        all_records = development_records + holdout_records
        all_guards_pass = all(row["record_valid"] is True for row in all_records)
        execution_digest = write_new_json(
            out_dir / "execution.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "seal_sha256": seal_digest,
                "formal_attempt_sha256": attempt_digest,
                "development_execution_sha256": development_digest,
                "fit_sha256": fit_digest,
                "holdout_execution_sha256": holdout_digest,
                "development_finished_before_fit": True,
                "fit_created_before_holdout": True,
                "record_count": len(all_records),
                "all_record_guards_pass": all_guards_pass,
                "physical_execution_performed": True,
                "controller_executed": False,
                "closed_loop_executed": False,
                "distributed_runtime_executed": False,
                "training_executed": False,
                "eval_executed": False,
                "reward_diagnostics_computed": True,
                "reward_diagnostics_stored": True,
                "reward_used_for_action": False,
                "reward_used_for_fitting": False,
                "reward_used_for_selection": False,
                "reward_used_for_training": False,
                "reward_used_for_classification": False,
                "reward_used_for_claim": False,
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
                "development_execution_sha256": development_digest,
                "fit_sha256": fit_digest,
                "holdout_execution_sha256": holdout_digest,
                "execution_sha256": execution_digest,
                "dynamic_model_sha256": model_digest,
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
                    {
                        "path": "development_execution.json",
                        "sha256": development_digest,
                    },
                    {"path": "fit.json", "sha256": fit_digest},
                    {"path": "holdout_execution.json", "sha256": holdout_digest},
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
                    "classification": "INVALID-PHYSICAL-DISTURBANCE-PACKAGE",
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "retry_authorized": False,
                },
            )
        finally:
            raise
    print(f"development_execution_sha256={development_digest}")
    print(f"fit_sha256={fit_digest}")
    print(f"holdout_execution_sha256={holdout_digest}")
    print(f"execution_sha256={execution_digest}")
    print(f"provenance_sha256={provenance_digest}")
    print(f"run_manifest_sha256={manifest_digest}")


def analyse(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected_sha256)
    attempt, attempt_digest = read_verified_json(out_dir / "formal_attempt.json")
    development, development_digest = read_verified_json(
        out_dir / "development_execution.json"
    )
    fit, fit_digest = read_verified_json(out_dir / "fit.json")
    holdout, holdout_digest = read_verified_json(out_dir / "holdout_execution.json")
    execution, execution_digest = read_verified_json(out_dir / "execution.json")
    provenance, provenance_digest = read_verified_json(out_dir / "provenance.json")
    manifest, manifest_digest = read_verified_json(out_dir / "run_manifest.json")
    model, model_digest = _load_r316_model()
    expected_manifest = {
        "formal_attempt.json": attempt_digest,
        "development_execution.json": development_digest,
        "fit.json": fit_digest,
        "holdout_execution.json": holdout_digest,
        "execution.json": execution_digest,
        "provenance.json": provenance_digest,
    }
    reward_boundary = {
        "reward_diagnostics_computed": True,
        "reward_diagnostics_stored": True,
        "reward_used_for_action": False,
        "reward_used_for_fitting": False,
        "reward_used_for_selection": False,
        "reward_used_for_training": False,
        "reward_used_for_classification": False,
        "reward_used_for_claim": False,
    }
    scope_boundary = {
        "controller_executed": False,
        "closed_loop_executed": False,
        "distributed_runtime_executed": False,
        "training_executed": False,
        "eval_executed": False,
    }
    chain_valid = bool(
        attempt["round"] == ROUND_ID
        and attempt["question"] == QUESTION_ID
        and attempt["seal_sha256"] == seal_digest
        and attempt["physical_execution_started"] is True
        and attempt["retry_authorized"] is False
        and all(attempt.get(name) is value for name, value in scope_boundary.items())
        and development["round"] == ROUND_ID
        and development["question"] == QUESTION_ID
        and development["seal_sha256"] == seal_digest
        and development["dynamic_model_sha256"] == model_digest
        and fit["round"] == ROUND_ID
        and fit["question"] == QUESTION_ID
        and fit["seal_sha256"] == seal_digest
        and fit["development_execution_sha256"] == development_digest
        and fit["dynamic_model_sha256"] == model_digest
        and fit["fit_created_before_holdout"] is True
        and holdout["round"] == ROUND_ID
        and holdout["question"] == QUESTION_ID
        and holdout["seal_sha256"] == seal_digest
        and holdout["fit_sha256"] == fit_digest
        and holdout["dynamic_model_sha256"] == model_digest
        and str(fit["created_utc"]) <= str(holdout["started_utc"])
        and execution["seal_sha256"] == seal_digest
        and development["formal_attempt_sha256"] == attempt_digest
        and holdout["formal_attempt_sha256"] == attempt_digest
        and execution["formal_attempt_sha256"] == attempt_digest
        and execution["development_execution_sha256"] == development_digest
        and execution["fit_sha256"] == fit_digest
        and execution["holdout_execution_sha256"] == holdout_digest
    )
    chain_valid = bool(
        chain_valid
        and execution["round"] == ROUND_ID
        and execution["question"] == QUESTION_ID
        and execution["development_finished_before_fit"] is True
        and execution["fit_created_before_holdout"] is True
        and all(execution.get(name) is value for name, value in reward_boundary.items())
        and all(execution.get(name) is value for name, value in scope_boundary.items())
        and provenance["round"] == ROUND_ID
        and provenance["question"] == QUESTION_ID
        and provenance["seal_sha256"] == seal_digest
        and provenance["execution_sha256"] == execution_digest
        and provenance["dynamic_model_sha256"] == model_digest
        and manifest["round"] == ROUND_ID
        and manifest["question"] == QUESTION_ID
        and _manifest_entries_match(manifest, expected_manifest)
    )
    analysis_contract = {
        **seal["contract"],
        "channels": seal["contract"]["channel_names"],
    }
    kwargs = {
        "contract": analysis_contract,
        "development_records": development["records"],
        "holdout_records": holdout["records"],
        "fit_payload": fit,
        "realization_payloads": {
            point: model["points"][point]["realization"] for point in ("HS0", "HS1")
        },
        "execution_validity": {
            "all_guards_pass": chain_valid
            and execution["all_record_guards_pass"] is True
            and execution["record_count"] == seal["contract"]["record_count"]
        },
    }
    first = analyse_r335_disturbance_package(**kwargs)
    second = analyse_r335_disturbance_package(**kwargs)
    deterministic_replay = first == second
    result = {
        **first,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "formal_attempt_sha256": attempt_digest,
        "development_execution_sha256": development_digest,
        "fit_sha256": fit_digest,
        "holdout_execution_sha256": holdout_digest,
        "execution_sha256": execution_digest,
        "provenance_sha256": provenance_digest,
        "run_manifest_sha256": manifest_digest,
        "dynamic_model_sha256": model_digest,
        "source_inventory_count": len(seal["sources"]),
        "evidence_chain_valid": chain_valid,
        "deterministic_replay": deterministic_replay,
        "reward_diagnostics_computed": True,
        "reward_diagnostics_stored": True,
        "reward_used_for_action": False,
        "reward_used_for_fitting": False,
        "reward_used_for_selection": False,
        "reward_used_for_training": False,
        "reward_used_for_classification": False,
        "reward_used_for_claim": False,
    }
    if not chain_valid or not deterministic_replay:
        result["classification"] = "INVALID-PHYSICAL-DISTURBANCE-PACKAGE"
    digest = write_new_json(out_dir / "analysis.json", result)
    print(f"classification={result['classification']}")
    print(f"analysis_sha256={digest}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    canary_parser = subparsers.add_parser("canary")
    canary_parser.add_argument("--out", type=Path, required=True)
    canary_parser.add_argument("--full-point", action="store_true")
    execute_parser = subparsers.add_parser("execute")
    execute_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    execute_parser.add_argument("--expected-sha256", required=True)
    execute_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse_parser.add_argument("--expected-sha256", required=True)
    analyse_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "prepare":
        prepare(args.seal)
    elif args.command == "canary":
        canary(args.out, full_point=args.full_point)
    elif args.command == "execute":
        execute(args.seal, args.expected_sha256, args.out)
    else:
        analyse(args.seal, args.expected_sha256, args.out)


if __name__ == "__main__":
    main()
