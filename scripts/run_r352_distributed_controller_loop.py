"""Tune and seal R352's matched neighbour-distributed controller comparison.

Usage: run each staged subcommand through ``scripts/andes_scratch.py`` in WSL,
from ``rehearse-development`` through ``execute-formal``. The formal command
also requires the expected seal digest. Failures are terminal and preserve
create-only artifacts; source drift, output collisions, active peer research
processes, failed physical guards, or an invalid inventory abort the stage.
The module exposes no neural-training command.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
import hashlib
import json
import multiprocessing as mp
import os
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from scripts import run_r341_staged_fresh_model_validation as r341  # noqa: E402
from scripts import run_r344_deterministic_bridge as r344  # noqa: E402
from andes_rl_kundur.control.model_first_distributed_edge import (  # noqa: E402
    EndpointObservation,
    IndependentNeighbourEdgeExecution,
    JointInformationEdgeController,
    LinearNeighbourEdgeController,
    LocalEdgeObservation,
    MatchedEdgeActionGovernor,
)
from andes_rl_kundur.env.andes.model_first_contract import ACTION_EDGES  # noqa: E402


ROUND_ID = "R352"
QUESTION_ID = "Q-0093"
PLAN = ROOT / "memory/rounds/R352/plan.md"
QUESTION = ROOT / "memory/questions/Q-0093.md"
CAPACITY_RECORD = ROOT / "memory/rounds/R352/capacity_ladder_v2.json"
DEVELOPMENT_REHEARSAL = ROOT / "memory/rounds/R352/development_rehearsal_v2.json"
FORMAL_REHEARSAL = ROOT / "memory/rounds/R352/formal_rehearsal.json"
FORMAL_SEAL = ROOT / "memory/rounds/R352/formal_seal.json"
DEFAULT_OUT = ROOT / "results/r352_distributed_controller_loop_v2"
EDGE_FLOW_LIMIT = 0.05
EDGE_SLEW_LIMIT = 0.05
TOTAL_STEPS = 25
SAMPLE_PERIOD_SECONDS = 0.2
STAGGERED_RISE_UNIT = (0.20, 0.60, 1.00, 0.70, 0.35, 0.10)
FREQUENCY_GAINS = (50.0, 200.0, 500.0)
ROCOF_GAINS = (0.0, 25.0, 100.0)


def candidate_grid() -> list[dict[str, float | str]]:
    return [
        {
            "candidate_id": f"kf{int(kf)}_kr{int(kr)}",
            "frequency_difference_gain_per_hz": kf,
            "rocof_difference_gain_s_per_hz": kr,
        }
        for kf in FREQUENCY_GAINS
        for kr in ROCOF_GAINS
    ]


def _scenario_bank(*, identity: str, waveform: str) -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []
    for point in ("FV0", "FV1"):
        for channel in r341.CHANNELS:
            for sign in ("positive", "negative"):
                scenarios.append(
                    {
                        "identity": identity,
                        "scenario_id": (
                            f"{identity.lower()}__{point}__{channel['device_idx']}__{sign}"
                        ),
                        "point": point,
                        "channel": dict(channel),
                        "waveform": waveform,
                        "amplitude_system_pu": float(
                            r344.LOW_AMPLITUDE_BY_DEVICE[str(channel["device_idx"])]
                        ),
                        "sign": sign,
                        "total_steps": TOTAL_STEPS,
                    }
                )
    return scenarios


def development_scenarios() -> list[dict[str, Any]]:
    return _scenario_bank(identity="DEVELOPMENT", waveform="ramp_hold_unit")


def holdout_scenarios() -> list[dict[str, Any]]:
    return _scenario_bank(identity="HOLDOUT", waveform="staggered_rise_unit")


def select_development_candidate(records: list[dict[str, Any]]) -> dict[str, Any]:
    from probes.r352_distributed_controller_loop import (
        select_development_candidate as classify,
    )

    contract = build_contract()
    return classify(
        records,
        scenarios=[row["scenario_id"] for row in contract["development_scenarios"]],
        candidates=contract["candidate_gains"],
        thresholds=contract["thresholds"],
    )


def classify_formal_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    from probes.r352_distributed_controller_loop import (
        classify_formal_records as classify,
    )

    contract = build_contract()
    return classify(
        records,
        expected_scenarios={
            row["scenario_id"] for row in contract["holdout_scenarios"]
        },
        thresholds=contract["thresholds"],
    )


def classify_stage_stop(records: list[dict[str, Any]]) -> str | None:
    from probes.r352_distributed_controller_loop import classify_stage_stop as classify

    return classify(records)


def build_contract() -> dict[str, Any]:
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "neighbour-distributed-deterministic-closed-loop",
        "action_edges": [list(edge) for edge in ACTION_EDGES],
        "action_dimension": len(ACTION_EDGES),
        "edge_flow_limit_system_pu": EDGE_FLOW_LIMIT,
        "edge_slew_limit_system_pu": EDGE_SLEW_LIMIT,
        "sample_period_seconds": SAMPLE_PERIOD_SECONDS,
        "total_steps": TOTAL_STEPS,
        "candidate_gains": candidate_grid(),
        "development_scenarios": development_scenarios(),
        "holdout_scenarios": holdout_scenarios(),
        "holdout_waveform_unit": list(STAGGERED_RISE_UNIT),
        "formal_arms": ["zero_edge", "selected_local", "joint_upper"],
        "thresholds": {
            "minimum_mean_differential_improvement_fraction": 0.02,
            "maximum_single_scenario_differential_worsening_fraction": 0.05,
            "maximum_single_scenario_common_worsening_fraction": 0.05,
            "requested_fleet_imbalance_absolute_maximum_system_pu": 1.0e-12,
        },
        "training_executed": False,
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


def _write_new_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical_bytes(payload)
    with path.open("xb") as handle:
        handle.write(data)
    digest = hashlib.sha256(data).hexdigest()
    with path.with_name(path.name + ".sha256").open(
        "x", encoding="ascii", newline="\n"
    ) as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def _read_hashed_json(path: Path) -> dict[str, Any]:
    sidecar = path.with_name(path.name + ".sha256")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    observed = _sha256_file(path)
    if observed != expected:
        raise RuntimeError(f"hash mismatch for {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return payload


def _source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_r352_distributed_controller_loop.py",
        "controller": ROOT
        / "src/andes_rl_kundur/control/model_first_distributed_edge.py",
        "controller_tests": ROOT / "tests/test_model_first_distributed_edge.py",
        "analysis": ROOT / "probes/r352_distributed_controller_loop.py",
        "r341_profile": ROOT / "scripts/run_r341_staged_fresh_model_validation.py",
        "r344_bridge": ROOT / "scripts/run_r344_deterministic_bridge.py",
        "r335_disturbance": ROOT / "scripts/run_r335_disturbance_package.py",
        "r333_disturbance": ROOT
        / "scripts/run_r333_pq_disturbance_identification.py",
        "r334_installed_runtime": ROOT
        / "scripts/run_r334_pq_disturbance_identification.py",
        "r339_input_bridge": ROOT / "scripts/run_r339_input_bridge_diagnosis.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "project_dependencies": ROOT / "pyproject.toml",
        "physical_contract": ROOT / "src/andes_rl_kundur/control/active_power.py",
        "headroom_allocator": ROOT
        / "src/andes_rl_kundur/control/headroom_aware_edge_allocation.py",
        "model_first_environment": ROOT
        / "src/andes_rl_kundur/env/andes/model_first_env.py",
        "model_first_profile": ROOT
        / "src/andes_rl_kundur/env/andes/model_first_pq_profile.py",
        "model_first_contract": ROOT
        / "src/andes_rl_kundur/env/andes/model_first_contract.py",
        "physical_endpoints": ROOT
        / "src/andes_rl_kundur/evaluation/model_first_physical_bridge.py",
    }
    package_root = ROOT / "src/andes_rl_kundur"
    for path in sorted(package_root.rglob("*.py")):
        relative = path.relative_to(package_root).as_posix()
        sources[f"package::{relative}"] = path
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in sources.items()
    }


def development_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for scenario in development_scenarios():
        specs.append(
            {
                **scenario,
                "record_index": len(specs),
                "mode": "development",
                "arm": "zero_edge",
                "candidate_id": None,
                "frequency_difference_gain_per_hz": 0.0,
                "rocof_difference_gain_s_per_hz": 0.0,
            }
        )
        for candidate in candidate_grid():
            specs.append(
                {
                    **scenario,
                    **candidate,
                    "record_index": len(specs),
                    "mode": "development",
                    "arm": "local_candidate",
                }
            )
    return specs


def development_joint_specs(selected: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            **scenario,
            "record_index": index,
            "mode": "development_joint_diagnostic",
            "arm": "joint_upper",
            "candidate_id": selected["candidate_id"],
            "frequency_difference_gain_per_hz": float(
                selected["frequency_difference_gain_per_hz"]
            ),
            "rocof_difference_gain_s_per_hz": float(
                selected["rocof_difference_gain_s_per_hz"]
            ),
        }
        for index, scenario in enumerate(development_scenarios())
    ]


def formal_specs(selected: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for scenario in holdout_scenarios():
        for arm in ("zero_edge", "selected_local", "joint_upper"):
            specs.append(
                {
                    **scenario,
                    "record_index": len(specs),
                    "mode": "formal",
                    "arm": arm,
                    "candidate_id": (
                        None if arm == "zero_edge" else selected["candidate_id"]
                    ),
                    "frequency_difference_gain_per_hz": (
                        0.0
                        if arm == "zero_edge"
                        else float(selected["frequency_difference_gain_per_hz"])
                    ),
                    "rocof_difference_gain_s_per_hz": (
                        0.0
                        if arm == "zero_edge"
                        else float(selected["rocof_difference_gain_s_per_hz"])
                    ),
                }
            )
    return specs


def _profile_contract(spec: dict[str, Any]):
    from scripts import run_r335_disturbance_package as base

    if spec["identity"] == "DEVELOPMENT":
        return r341._r341_profile_contract(
            channel=spec["channel"],
            shape=f"ramp_hold_unit__{float(spec['amplitude_system_pu']):.2f}",
            sign=str(spec["sign"]),
        )
    if spec["identity"] != "HOLDOUT":
        raise ValueError("unknown R352 scenario identity")
    channel = spec["channel"]
    multiplier = 1.0 if spec["sign"] == "positive" else -1.0
    amplitude = float(spec["amplitude_system_pu"])
    profile = tuple(multiplier * amplitude * value for value in STAGGERED_RISE_UNIT)
    return base.TimedPQProfileContract(
        event_prefix=(
            f"R352_{channel['device_idx']}_{spec['point']}_{spec['sign']}"
        ),
        device_idx=str(channel["device_idx"]),
        bus_idx=int(channel["bus_idx"]),
        initial_active_system_pu=float(channel["initial_active_system_pu"]),
        initial_reactive_system_pu=float(channel["initial_reactive_system_pu"]),
        delta_profile_system_pu=profile,
        plant_baselines=base.BASELINES,
    )


def _run_physical_record(
    spec: dict[str, Any],
    *,
    record_dir: Path,
    trace_path: Path,
    seal_digest: str,
) -> dict[str, Any]:
    if os.name != "posix":
        raise RuntimeError("R352 physical records are WSL/POSIX-only")
    from scripts import run_r335_disturbance_package as base
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

    point_name = str(spec["point"])
    point = Stage1OperatingPoint(point_name, **r341.POINTS[point_name])
    config = replace(
        ModelFirstConfig.for_stage1_operating_point(point),
        tds_post_initialization_convergence_tolerance=base.DYNAMIC_TOLERANCE,
    )
    profile_contract = _profile_contract(spec)

    class PhysicalEnvironment(TimedPQProfileMixin, AndesModelFirstEnv):
        def __init__(self, *, pq_profile_contract, **kwargs):
            self.pq_profile_contract = pq_profile_contract
            super().__init__(**kwargs)

    record_dir.mkdir(parents=True, exist_ok=False)
    previous_cwd = Path.cwd()
    os.chdir(record_dir)
    rows: list[dict[str, Any]] = []
    env = None
    try:
        with base._substep_environment():
            env = PhysicalEnvironment(
                pq_profile_contract=profile_contract,
                model_first_config=config,
            )
            env.reset()
            initial_time = float(env.ss.dae.t)
            initial_event_audit = r344._jsonable(getattr(env, "pq_event_audit", []))
            if not initial_event_audit:
                raise RuntimeError("R352 disturbance profile did not fire its reset event")
            setup_baselines = base._baseline_readback(env.ss)
            setup_baselines[profile_contract.device_idx] = initial_event_audit[0][
                "before"
            ]
            event_inventory = base._r333._alter_event_inventory(env.ss)
            structural_contract = r344._jsonable(env.structural_contract())
            zero_md = {index: np.zeros(2) for index in range(env.N_AGENTS)}
            governor = MatchedEdgeActionGovernor(
                physical_contract=env.bess_contract,
                edge_flow_limit_system_pu=EDGE_FLOW_LIMIT,
                edge_slew_limit_system_pu=EDGE_SLEW_LIMIT,
            )
            frequency_gain = float(spec["frequency_difference_gain_per_hz"])
            rocof_gain = float(spec["rocof_difference_gain_s_per_hz"])
            local_execution = IndependentNeighbourEdgeExecution(
                tuple(
                    LinearNeighbourEdgeController(
                        edge=edge,
                        frequency_difference_gain_per_hz=frequency_gain,
                        rocof_difference_gain_s_per_hz=rocof_gain,
                    )
                    for edge in ACTION_EDGES
                )
            )
            joint_controller = JointInformationEdgeController(
                frequency_difference_gain_per_hz=frequency_gain,
                rocof_difference_gain_s_per_hz=rocof_gain,
            )
            previous_frequency = None
            previous_edge_flows = np.zeros(3)
            for step_index in range(int(spec["total_steps"])):
                frequency = env.get_vsg_frequency_physical_hz()
                rocof = (
                    np.zeros(4)
                    if previous_frequency is None
                    else (frequency - previous_frequency) / SAMPLE_PERIOD_SECONDS
                )
                previous_command = env._previous_bess_command_system_pu.copy()
                soc = env._get_bess_soc()
                voltage = env._get_bess_voltage()
                lower, upper = env.bess_contract.feasible_power_bounds(
                    previous_power_system_pu=previous_command,
                    soc=soc,
                    voltage_pu=voltage,
                    dt_seconds=SAMPLE_PERIOD_SECONDS,
                )
                endpoints = {
                    index: EndpointObservation(
                        node_id=index,
                        frequency_deviation_hz=float(frequency[index] - 60.0),
                        rocof_hz_s=float(rocof[index]),
                        previous_command_system_pu=float(previous_command[index]),
                        soc=float(soc[index]),
                        voltage_pu=float(voltage[index]),
                        lower_residual_power_system_pu=float(lower[index]),
                        upper_residual_power_system_pu=float(upper[index]),
                    )
                    for index in range(4)
                }
                if spec["arm"] == "zero_edge":
                    normalized_action = np.zeros(3)
                    architecture = "zero_three_edge_action"
                elif spec["arm"] in {"local_candidate", "selected_local"}:
                    observations = {
                        edge: LocalEdgeObservation(
                            edge=edge,
                            source=endpoints[edge[0]],
                            target=endpoints[edge[1]],
                            previous_edge_flow_system_pu=float(
                                previous_edge_flows[index]
                            ),
                        )
                        for index, edge in enumerate(ACTION_EDGES)
                    }
                    normalized_action = local_execution.act(observations)
                    architecture = local_execution.architecture
                elif spec["arm"] == "joint_upper":
                    normalized_action = joint_controller.act(endpoints)
                    architecture = joint_controller.architecture
                else:
                    raise ValueError(f"unknown R352 arm: {spec['arm']}")
                governed = governor.govern(
                    normalized_edge_actions=normalized_action,
                    previous_edge_flows_system_pu=previous_edge_flows,
                    base_power_request_system_pu=np.zeros(4),
                    previous_commanded_power_system_pu=previous_command,
                    soc=soc,
                    voltage_pu=voltage,
                    dt_seconds=SAMPLE_PERIOD_SECONDS,
                )
                request = governed.physical_projection.commanded_power_system_pu.copy()
                _, _, _, info = env.step(zero_md, bess_power_request_pu=request)
                row = r344._jsonable(info)
                row["step"] = step_index
                row["t"] = row.pop("time")
                row["normalized_edge_action"] = normalized_action.tolist()
                row["requested_edge_flows_system_pu"] = (
                    governed.requested_edge_flows_system_pu.tolist()
                )
                row["executed_edge_flows_system_pu"] = (
                    governed.executed_edge_flows_system_pu.tolist()
                )
                row["edge_observation_nodes"] = [list(edge) for edge in ACTION_EDGES]
                row["controller"] = {
                    "architecture": architecture,
                    "used_fallback": False,
                    "solver_feasible": True,
                }
                row["internal_limiter_active"] = bridge_internal_limiter_active(
                    row["bess_internal"]
                )
                rows.append(row)
                previous_frequency = frequency.copy()
                previous_edge_flows = governed.executed_edge_flows_system_pu.copy()
            event_audit = r344._jsonable(getattr(env, "pq_event_audit", []))
            env.ss.dae.ts.unpack(attr="t", warn_empty=False)
            tds_grid = np.asarray(env.ss.dae.ts.t, dtype=float).copy()
            terminal_baselines = base._baseline_readback(env.ss)
    finally:
        try:
            if env is not None:
                env.close()
        finally:
            os.chdir(previous_cwd)

    frequency_trace = np.asarray(
        [row["freq_hz_physical"] for row in rows], dtype=float
    )
    coordinates = frequency_coordinate_trace(
        frequency_trace,
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
            frequency_hz=frequency_trace,
            reference_frequency_hz=np.full(4, 60.0),
            requested_node_power=requested,
            achieved_node_power=achieved,
            sample_period_seconds=SAMPLE_PERIOD_SECONDS,
        )
    )
    summary["maximum_requested_fleet_imbalance_system_pu"] = float(
        np.max(np.abs(np.sum(requested, axis=1)))
    )
    summary["maximum_normalized_edge_action"] = float(
        np.max(np.abs([row["normalized_edge_action"] for row in rows]))
    )
    summary["maximum_executed_edge_flow_system_pu"] = float(
        np.max(np.abs([row["executed_edge_flows_system_pu"] for row in rows]))
    )
    guards = r344._physical_guard_summary(
        rows=rows,
        expected_steps=int(spec["total_steps"]),
        initial_time=initial_time,
        expected_m=config.vsg_m_system,
        expected_d=config.vsg_d_system,
    )
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
    guards.update(
        {
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
    )
    action_rows = np.asarray(
        [row["normalized_edge_action"] for row in rows], dtype=float
    )
    information_action_contract_pass = bool(
        action_rows.shape == (int(spec["total_steps"]), 3)
        and np.all(np.isfinite(action_rows))
        and np.max(np.abs(action_rows)) <= 1.0 + 1.0e-12
        and summary["maximum_requested_fleet_imbalance_system_pu"] <= 1.0e-12
        and all(row["edge_observation_nodes"] == [list(edge) for edge in ACTION_EDGES] for row in rows)
        and (
            spec["arm"] != "zero_edge"
            or np.allclose(action_rows, 0.0, rtol=0.0, atol=0.0)
        )
    )
    physical_guards_pass = all(guards.values())
    trace_digest = r344._write_new_gzip_json(
        trace_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "seal_sha256": seal_digest,
            "spec": spec,
            "structural_contract": structural_contract,
            "profile_provenance": {
                "profile_contract": profile_contract.to_dict(),
                "expected_event_inventory": expected_events,
                "observed_event_inventory": event_inventory,
                "event_fire_counts": fire_counts,
                "event_grid": r344._jsonable(event_grid),
                "event_receipts": receipts,
            },
            "rows": rows,
        },
    )
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "record_index": int(spec["record_index"]),
        "mode": str(spec["mode"]),
        "identity": str(spec["identity"]),
        "point": point_name,
        "scenario_id": str(spec["scenario_id"]),
        "arm": str(spec["arm"]),
        "candidate_id": spec.get("candidate_id"),
        "integrity_valid": True,
        "information_action_contract_pass": information_action_contract_pass,
        "physical_guards_pass": physical_guards_pass,
        "guards": guards,
        "metrics": summary,
        "trace": {"path": _path_text(trace_path), "sha256": trace_digest},
        "worker_pid": os.getpid(),
        "training_executed": False,
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


def _maximum_interval_overlap(records: list[dict[str, Any]]) -> int:
    events: list[tuple[int, int]] = []
    for row in records:
        events.append((int(row["worker_started_monotonic_ns"]), 1))
        events.append((int(row["worker_ended_monotonic_ns"]), -1))
    active = maximum = 0
    for _, delta in sorted(events, key=lambda item: (item[0], -item[1])):
        active += delta
        maximum = max(maximum, active)
    return maximum


def _run_specs(
    specs: list[dict[str, Any]],
    *,
    stage: str,
    process_budget: int,
    trace_root: Path,
    seal_digest: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if os.name != "posix":
        raise RuntimeError("R352 physical execution is WSL/POSIX-only")
    if not specs:
        raise ValueError("R352 physical inventory must be non-empty")
    effective_processes = min(int(process_budget), len(specs))
    if effective_processes < 2:
        raise ValueError("R352 requires at least two whole-host Python processes")
    trace_root.mkdir(parents=True, exist_ok=False)
    work_root = Path.cwd() / f"r352_{stage}_records"
    work_root.mkdir(parents=True, exist_ok=False)
    indexed = list(enumerate(specs))
    parent_positions = set(range(0, len(indexed), effective_processes))
    parent_jobs = [item for item in indexed if item[0] in parent_positions]
    child_jobs = [item for item in indexed if item[0] not in parent_positions]

    def paths(index: int, spec: dict[str, Any]) -> tuple[Path, Path]:
        label = f"{index:03d}_{spec['scenario_id']}_{spec['arm']}"
        return work_root / label, trace_root / f"record_{index:03d}.json.gz"

    records: list[dict[str, Any]] = []
    started = time.monotonic()
    context = mp.get_context("fork")
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
            records.append(
                _physical_worker(
                    dict(spec),
                    record_dir=record_dir,
                    trace_path=trace_path,
                    seal_digest=seal_digest,
                )
            )
        for future in as_completed(futures):
            records.append(future.result())
    elapsed = time.monotonic() - started
    records.sort(key=lambda row: int(row["record_index"]))
    unique_processes = len({int(row["worker_pid"]) for row in records})
    maximum_overlap = _maximum_interval_overlap(records)
    process_guard = bool(
        len(records) == len(specs)
        and unique_processes == effective_processes
        and maximum_overlap == effective_processes
    )
    if not process_guard:
        for row in records:
            row["integrity_valid"] = False
    return records, {
        "configured_process_budget": int(process_budget),
        "effective_processes": effective_processes,
        "unique_python_processes": unique_processes,
        "maximum_interval_overlap": maximum_overlap,
        "process_guard": process_guard,
        "elapsed_seconds": elapsed,
        "throughput_trajectories_per_second": len(records) / elapsed,
        "native_threads_per_process": 1,
    }


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R352 physical staging is WSL/POSIX-only")
    cwd = Path.cwd().resolve()
    root = ROOT.resolve()
    if cwd == root or root not in cwd.parents:
        raise RuntimeError("R352 requires repository-local ANDES scratch isolation")


def _other_research_python_processes() -> list[dict[str, Any]]:
    if os.name != "posix":
        return []
    current = os.getpid()
    rows: list[dict[str, Any]] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == current:
            continue
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            )
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if "python" in command and "andes-rl-kundur" in command and "run_r" in command:
            rows.append({"pid": int(entry.name), "command": command})
    return rows


def _memory_snapshot() -> dict[str, int]:
    values: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        name, raw = line.split(":", 1)
        if name in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
            values[f"{name.lower()}_bytes"] = int(raw.split()[0]) * 1024
    return values


def _rehearsal_checks_pass(checks: dict[str, Any]) -> bool:
    return bool(
        checks
        and checks.get("physical_trajectory_executed") is False
        and all(
            value is True
            for name, value in checks.items()
            if name != "physical_trajectory_executed"
        )
    )


def rehearse_development(record_path: Path = DEVELOPMENT_REHEARSAL) -> str:
    _assert_wsl_scratch()
    collisions = [
        path
        for path in (CAPACITY_RECORD, DEFAULT_OUT, FORMAL_REHEARSAL, FORMAL_SEAL)
        if path.exists()
    ]
    if collisions:
        raise FileExistsError(f"R352 pre-development artifact exists: {collisions}")
    contract = build_contract()
    checks = {
        "scratch_isolation": True,
        "development_inventory": len(development_specs()) == 160,
        "development_scenario_count": len(development_scenarios()) == 16,
        "holdout_scenario_count": len(holdout_scenarios()) == 16,
        "development_holdout_disjoint": not (
            {row["scenario_id"] for row in development_scenarios()}
            & {row["scenario_id"] for row in holdout_scenarios()}
        ),
        "formal_output_absent": not FORMAL_SEAL.exists()
        and not (DEFAULT_OUT / "formal_attempt.json").exists(),
        "physical_trajectory_executed": False,
    }
    return _write_new_json(
        record_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_payload_sha256": _payload_sha256(contract),
            "sources": _source_manifest(),
            "installed_andes": r344._installed_andes_identity(),
            "checks": checks,
        },
    )


def measure_capacity(record_path: Path = CAPACITY_RECORD) -> str:
    _assert_wsl_scratch()
    rehearsal = _read_hashed_json(DEVELOPMENT_REHEARSAL)
    if not _rehearsal_checks_pass(rehearsal.get("checks", {})):
        raise RuntimeError("R352 development rehearsal did not pass")
    if rehearsal.get("sources") != _source_manifest():
        raise RuntimeError("R352 source drift after development rehearsal")
    other = _other_research_python_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    rungs: list[dict[str, Any]] = []
    representative = development_specs()[:8]
    capacity_root = Path.cwd() / "r352_capacity_ladder"
    for process_budget in (2, 4, 8):
        specs = [dict(row) for row in representative[:process_budget]]
        for index, spec in enumerate(specs):
            spec["record_index"] = index
        records, process = _run_specs(
            specs,
            stage=f"capacity_{process_budget}",
            process_budget=process_budget,
            trace_root=capacity_root / f"rung_{process_budget}_traces",
            seal_digest="r352-capacity-not-formal",
        )
        valid = bool(
            process.get("process_guard") is True
            and len(records) == process_budget
            and all(row.get("integrity_valid") is True for row in records)
            and all(
                row.get("information_action_contract_pass") is True
                and row.get("physical_guards_pass") is True
                for row in records
            )
        )
        rungs.append(
            {
                "whole_host_python_processes": process_budget,
                "native_threads_per_process": 1,
                "representative_trajectory_count": len(records),
                "process": process,
                "memory_after": _memory_snapshot(),
                "valid": valid,
                "scientific_outcomes_inspected": False,
            }
        )
    valid_rungs = [row for row in rungs if row["valid"] is True]
    if not valid_rungs:
        selected = None
        readiness = "HOLD"
    else:
        selected = max(
            valid_rungs,
            key=lambda row: float(row["process"]["throughput_trajectories_per_second"]),
        )
        readiness = "RUN-READY"
    disk = shutil.disk_usage(ROOT)
    return _write_new_json(
        record_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "readiness": readiness,
            "rungs": rungs,
            "selected": selected,
            "host_logical_processors": os.cpu_count(),
            "other_reserved_processes": len(other),
            "other_processes": other,
            "memory_before": _memory_snapshot(),
            "disk_free_bytes": disk.free,
            "native_threads_per_process": 1,
            "formal_authority": False,
        },
    )


def execute_development(out_dir: Path = DEFAULT_OUT) -> str:
    _assert_wsl_scratch()
    rehearsal = _read_hashed_json(DEVELOPMENT_REHEARSAL)
    capacity = _read_hashed_json(CAPACITY_RECORD)
    if rehearsal.get("sources") != _source_manifest():
        raise RuntimeError("R352 source drift before development")
    selected_capacity = capacity.get("selected")
    if capacity.get("readiness") != "RUN-READY" or not isinstance(
        selected_capacity, dict
    ):
        raise RuntimeError("R352 capacity gate is not RUN-READY")
    if _other_research_python_processes():
        raise RuntimeError("other research Python processes are active")
    out_dir.mkdir(parents=True, exist_ok=False)
    attempt_digest = _write_new_json(
        out_dir / "development_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "development_only": True,
            "holdout_executed": False,
        },
    )
    process_budget = int(selected_capacity["whole_host_python_processes"])
    records, process = _run_specs(
        development_specs(),
        stage="development",
        process_budget=process_budget,
        trace_root=out_dir / "development_traces",
        seal_digest="r352-development-not-formal",
    )
    execution_digest = _write_new_json(
        out_dir / "development_execution.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "attempt_sha256": attempt_digest,
            "process": process,
            "record_count": len(records),
            "records": records,
            "holdout_executed": False,
            "training_executed": False,
        },
    )
    selection = select_development_candidate(records)
    selection.update(
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "development_execution_sha256": execution_digest,
            "training_authorized": False,
        }
    )
    analysis_digest = _write_new_json(
        out_dir / "development_analysis.json", selection
    )
    joint_digest = None
    if selection["classification"] == "DEVELOPMENT-CANDIDATE-SELECTED":
        joint_records, joint_process = _run_specs(
            development_joint_specs(selection["selected"]),
            stage="development_joint",
            process_budget=process_budget,
            trace_root=out_dir / "development_joint_traces",
            seal_digest="r352-development-joint-not-formal",
        )
        joint_valid = bool(
            len(joint_records) == 16
            and joint_process.get("process_guard") is True
            and all(
                row.get("integrity_valid") is True
                and row.get("information_action_contract_pass") is True
                and row.get("physical_guards_pass") is True
                for row in joint_records
            )
        )
        joint_digest = _write_new_json(
            out_dir / "development_joint_execution.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "development_analysis_sha256": analysis_digest,
                "process": joint_process,
                "record_count": len(joint_records),
                "records": joint_records,
                "valid": joint_valid,
                "diagnostic_only": True,
                "training_executed": False,
            },
        )
    manifest_entries = [
        {"path": _path_text(out_dir / "development_attempt.json"), "sha256": attempt_digest},
        {"path": _path_text(out_dir / "development_execution.json"), "sha256": execution_digest},
        {"path": _path_text(out_dir / "development_analysis.json"), "sha256": analysis_digest},
        *[row["trace"] for row in records],
    ]
    if joint_digest is not None:
        joint_payload = _read_hashed_json(out_dir / "development_joint_execution.json")
        manifest_entries.append(
            {
                "path": _path_text(out_dir / "development_joint_execution.json"),
                "sha256": joint_digest,
            }
        )
        manifest_entries.extend(row["trace"] for row in joint_payload["records"])
    _write_new_json(
        out_dir / "development_manifest.json",
        {"schema_version": 1, "round": ROUND_ID, "entries": manifest_entries},
    )
    print(f"development_classification={selection['classification']}", flush=True)
    if selection.get("selected"):
        print(f"selected_candidate={selection['selected']['candidate_id']}", flush=True)
    return analysis_digest


def rehearse_formal(record_path: Path = FORMAL_REHEARSAL) -> str:
    _assert_wsl_scratch()
    selection = _read_hashed_json(DEFAULT_OUT / "development_analysis.json")
    joint = _read_hashed_json(DEFAULT_OUT / "development_joint_execution.json")
    if selection.get("classification") != "DEVELOPMENT-CANDIDATE-SELECTED":
        raise RuntimeError("R352 has no eligible development candidate")
    if joint.get("valid") is not True:
        raise RuntimeError("R352 joint diagnostic did not pass development guards")
    if FORMAL_SEAL.exists() or (DEFAULT_OUT / "formal_attempt.json").exists():
        raise FileExistsError("R352 formal artifact exists before rehearsal")
    capacity = _read_hashed_json(CAPACITY_RECORD)
    other = _other_research_python_processes()
    checks = {
        "scratch_isolation": True,
        "source_identity": True,
        "development_selection_bound": selection.get("holdout_records_inspected")
        is False,
        "joint_development_valid": joint.get("valid") is True,
        "formal_inventory": len(formal_specs(selection["selected"])) == 48,
        "holdout_output_absent": not (DEFAULT_OUT / "formal_execution.json").exists(),
        "other_reserved_processes_zero": len(other) == 0,
        "physical_trajectory_executed": False,
    }
    return _write_new_json(
        record_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "sources": _source_manifest(),
            "contract_payload_sha256": _payload_sha256(build_contract()),
            "development_analysis_sha256": _sha256_file(
                DEFAULT_OUT / "development_analysis.json"
            ),
            "capacity_sha256": _sha256_file(CAPACITY_RECORD),
            "selected_process_budget": capacity["selected"][
                "whole_host_python_processes"
            ],
            "other_processes": other,
            "installed_andes": r344._installed_andes_identity(),
            "checks": checks,
        },
    )


def prepare_formal(seal_path: Path = FORMAL_SEAL) -> str:
    rehearsal = _read_hashed_json(FORMAL_REHEARSAL)
    capacity = _read_hashed_json(CAPACITY_RECORD)
    selection = _read_hashed_json(DEFAULT_OUT / "development_analysis.json")
    if not _rehearsal_checks_pass(rehearsal.get("checks", {})):
        raise RuntimeError("R352 formal rehearsal did not pass")
    if rehearsal.get("sources") != _source_manifest():
        raise RuntimeError("R352 source drift after formal rehearsal")
    if rehearsal.get("development_analysis_sha256") != _sha256_file(
        DEFAULT_OUT / "development_analysis.json"
    ):
        raise RuntimeError("R352 development selection drift")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R352 capacity is not RUN-READY")
    selected = selection["selected"]
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "selected_controller": selected,
        "formal_specs": formal_specs(selected),
        "sources": _source_manifest(),
        "installed_andes": rehearsal["installed_andes"],
        "launch": {
            "whole_host_python_processes": int(
                capacity["selected"]["whole_host_python_processes"]
            ),
            "other_reserved_processes": 0,
            "native_threads_per_process": 1,
            "capacity_sha256": _sha256_file(CAPACITY_RECORD),
            "rehearsal_sha256": _sha256_file(FORMAL_REHEARSAL),
        },
        "development_analysis_sha256": _sha256_file(
            DEFAULT_OUT / "development_analysis.json"
        ),
        "formal_artifacts_create_only": True,
        "retry_authorized": False,
        "training_authorized": False,
    }
    return _write_new_json(seal_path, seal)


def load_seal(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    seal = _read_hashed_json(path)
    digest = _sha256_file(path)
    if digest != expected_sha256:
        raise RuntimeError("R352 seal digest mismatch")
    if seal.get("contract") != build_contract():
        raise RuntimeError("R352 contract drift")
    if seal.get("contract_payload_sha256") != _payload_sha256(build_contract()):
        raise RuntimeError("R352 contract payload drift")
    if seal.get("sources") != _source_manifest():
        raise RuntimeError("R352 sealed source drift")
    if seal.get("installed_andes") != r344._installed_andes_identity():
        raise RuntimeError("R352 installed ANDES identity drift")
    if seal.get("development_analysis_sha256") != _sha256_file(
        DEFAULT_OUT / "development_analysis.json"
    ):
        raise RuntimeError("R352 selected development artifact drift")
    return seal, digest


def execute_formal(
    *,
    expected_sha256: str,
    seal_path: Path = FORMAL_SEAL,
    out_dir: Path = DEFAULT_OUT,
) -> str:
    _assert_wsl_scratch()
    seal, seal_digest = load_seal(seal_path, expected_sha256)
    if _other_research_python_processes():
        raise RuntimeError("other research Python processes are active")
    formal_paths = [
        out_dir / "formal_attempt.json",
        out_dir / "formal_execution.json",
        out_dir / "formal_analysis.json",
        out_dir / "formal_manifest.json",
        out_dir / "formal_zero_edge_traces",
        out_dir / "formal_selected_local_traces",
        out_dir / "formal_joint_upper_traces",
    ]
    collisions = [path for path in formal_paths if path.exists()]
    if collisions:
        raise FileExistsError(f"R352 formal artifact collision: {collisions}")
    attempt_digest = _write_new_json(
        out_dir / "formal_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "retry_authorized": False,
            "training_authorized": False,
        },
    )
    records: list[dict[str, Any]] = []
    stages: list[dict[str, Any]] = []
    terminal_stop: str | None = None
    joint_diagnostic_stop: str | None = None
    for arm in ("zero_edge", "selected_local", "joint_upper"):
        arm_records, process = _run_specs(
            [dict(row) for row in seal["formal_specs"] if row["arm"] == arm],
            stage=f"formal_{arm}",
            process_budget=int(seal["launch"]["whole_host_python_processes"]),
            trace_root=out_dir / f"formal_{arm}_traces",
            seal_digest=seal_digest,
        )
        records.extend(arm_records)
        stage_stop = classify_stage_stop(arm_records)
        stages.append(
            {
                "arm": arm,
                "record_count": len(arm_records),
                "process": process,
                "stop_classification": stage_stop,
            }
        )
        if arm == "joint_upper":
            joint_diagnostic_stop = stage_stop
        elif stage_stop is not None:
            terminal_stop = stage_stop
            break
    records.sort(key=lambda row: int(row["record_index"]))
    execution_digest = _write_new_json(
        out_dir / "formal_execution.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "seal_sha256": seal_digest,
            "attempt_sha256": attempt_digest,
            "stages": stages,
            "record_count": len(records),
            "records": records,
            "training_executed": False,
        },
    )
    analysis = (
        classify_formal_records(records)
        if terminal_stop is None
        else {
            "classification": terminal_stop,
            "local_gate": {"passed": False, "staged_stop": True},
            "joint_upper_is_diagnostic_only": True,
            "training_authorized": False,
        }
    )
    analysis.update(
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "seal_sha256": seal_digest,
            "formal_execution_sha256": execution_digest,
            "selected_controller": seal["selected_controller"],
            "terminal_stage_stop": terminal_stop,
            "joint_diagnostic_stage_stop": joint_diagnostic_stop,
        }
    )
    analysis_digest = _write_new_json(out_dir / "formal_analysis.json", analysis)
    _write_new_json(
        out_dir / "formal_manifest.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "entries": [
                {"path": _path_text(out_dir / "formal_attempt.json"), "sha256": attempt_digest},
                {"path": _path_text(out_dir / "formal_execution.json"), "sha256": execution_digest},
                {"path": _path_text(out_dir / "formal_analysis.json"), "sha256": analysis_digest},
                *[row["trace"] for row in records],
            ],
        },
    )
    print(f"classification={analysis['classification']}", flush=True)
    return analysis_digest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("rehearse-development")
    commands.add_parser("measure-capacity")
    commands.add_parser("execute-development")
    commands.add_parser("rehearse-formal")
    commands.add_parser("prepare-formal")
    formal = commands.add_parser("execute-formal")
    formal.add_argument("--expected-seal-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rehearse-development":
        print(f"development_rehearsal_sha256={rehearse_development()}")
    elif args.command == "measure-capacity":
        print(f"capacity_sha256={measure_capacity()}")
    elif args.command == "execute-development":
        print(f"development_analysis_sha256={execute_development()}")
    elif args.command == "rehearse-formal":
        print(f"formal_rehearsal_sha256={rehearse_formal()}")
    elif args.command == "prepare-formal":
        print(f"formal_seal_sha256={prepare_formal()}")
    elif args.command == "execute-formal":
        print(
            "formal_analysis_sha256="
            f"{execute_formal(expected_sha256=args.expected_seal_sha256)}"
        )
    else:
        raise RuntimeError(f"unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
