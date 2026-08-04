"""Prepare, execute, and analyse the R333 timed-PQ identification bank.

Usage::

    python scripts/run_r333_pq_disturbance_identification.py canary --out tmp/.../canary.json
    python scripts/run_r333_pq_disturbance_identification.py prepare
    python scripts/andes_scratch.py scripts/run_r333_pq_disturbance_identification.py execute --expected-sha256 <seal>
    python scripts/run_r333_pq_disturbance_identification.py analyse --expected-sha256 <seal>

The physical ``canary`` and ``execute`` commands are WSL-only.  The formal
bank uses pre-setup absolute Alter events, zero controller/ESD1 requests, and
create-only artifacts.  EVAL and training are never imported or executed.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import os
import platform
import sys
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from memory.tools.artifact_io import (  # noqa: E402
    payload_sha256,
    read_verified_json,
    sha256_file,
    verified_digest_only,
    write_new_json,
)
from probes.r333_pq_disturbance_identification import (  # noqa: E402
    analyse_pq_disturbance_identification,
)

from andes_rl_kundur.env.andes.model_first_contract import (  # noqa: E402
    ModelFirstConfig,
    Stage1OperatingPoint,
    stage1_power_coordinates,
    weighted_common_differential_transform,
)
from andes_rl_kundur.env.andes.model_first_pq_disturbance import (  # noqa: E402
    TimedPQDisturbanceContract,
    TimedPQDisturbanceMixin,
    pq_runtime_snapshot,
)
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (  # noqa: E402
    realization_from_dict,
    simulate_state_space,
)

ROUND_ID = "R333"
QUESTION_ID = "Q-0085"
DEFAULT_SEAL = ROOT / "memory/rounds/R333/pq_disturbance_identification_seal.json"
DEFAULT_OUT = ROOT / "results/r333_pq_disturbance_identification"
R316_MODEL = ROOT / "results/r316_dynamic_reduction/dynamic_model.json"
R329_SEAL = ROOT / "memory/rounds/R329/disturbance_estimator_seal.json"
R332_ANALYSIS = ROOT / "results/r332_andes_bridge_reconciliation/analysis.json"

POINTS = (
    Stage1OperatingPoint("HS0", 177.5, 88.75, 1.10, 0.41),
    Stage1OperatingPoint("HS1", 202.5, 101.25, 1.35, 0.51),
)
SIGNS = ("zero", "positive", "negative")
SIGN_DELTA = {"zero": 0.0, "positive": 0.05, "negative": -0.05}
DEVICE_IDX = "PQ_Bus14"
BUS_IDX = 14
CONTROLLED_BUS_ORDER = (12, 16, 14, 15)
NOMINAL_TIE_LINES = {
    "Line_4": {"r": 0.02201, "x": 0.22001},
    "Line_5": {"r": 0.02202, "x": 0.22002},
    "Line_6": {"r": 0.02200, "x": 0.22000},
}
INITIAL_ACTIVE_SYSTEM_PU = 2.48
INITIAL_REACTIVE_SYSTEM_PU = 0.0
ACTIVE_STEPS = 5
TOTAL_STEPS = 25
SUBSTEPS = 5
DYNAMIC_TOLERANCE = 1.0e-10

EXPECTED_INSTALLED_SOURCES = {
    "andes/models/static/pq.py": "958db0ff11cc5d3108bc084579090c43d33b5bbb37c0f8c3ea209b1af9bd0ae3",
    "andes/models/timer.py": "3bb4eac11e38691a6e4a3f9f5a92601d4fa851bf29c28e2568586580eba654b6",
    "andes/core/model/model.py": "fd5502a78fa43e84132d089152f8806fb5facf35b939e0be4eced1db870ebe96",
    "andes/core/param.py": "5dd76b168ab16eefcb2f54cbdda64e7a725bb5360e615afbb16c297b44757b89",
    "andes/routines/tds.py": "224ff43d78de8e6808efa0a6b858d8dbe2ca511128a90a8260009c8146d6e8ba",
    "andes/system/facade.py": "b6aa12d10811a5b35e0d5939c309d3414713daff4f5d30f2b9063e0d518080c9",
    "andes/models/timeseries.py": "57b4949ccbdca488e23180879c2eee6d949f96ad86c8ec21b5650e079ef1da46",
    "andes/system/dae_compactor.py": "121d779bbf9c5aca097d362a92500383f9518dab0f4ab4d21c13ea0463df95f9",
    "andes/models/dynload/fload.py": "0f0df94d8a678da4830b663113e4154d6ac7f9787c2adfb3d50107b4de380876",
    "andes/models/dynload/zip.py": "869d8f640c9dea22a0c5e28045c507d7e297124cadd1b9d14e1a61b10afc02e6",
}
OFFICIAL_SOURCES = (
    "https://docs.andes.app/en/v2.0.0/reference/models/StaticLoad.html#pq",
    "https://docs.andes.app/en/v2.0.0/reference/models/TimedEvent.html#alter",
    "https://docs.andes.app/en/v2.0.0/tutorials/04-time-domain.html#adding-disturbances",
    "https://docs.andes.app/en/v2.0.0/tutorials/04-time-domain.html#altering-dynamic-vs-static-models",
    "https://docs.andes.app/en/v2.0.0/tutorials/11-frequency-response.html#implementing-load-shedding",
    "https://github.com/CURENT/andes/blob/v2.0.0/andes/models/static/pq.py",
    "https://github.com/CURENT/andes/blob/v2.0.0/andes/models/timer.py",
    "https://github.com/CURENT/andes/blob/v2.0.0/andes/routines/tds.py",
    "https://github.com/CURENT/andes/blob/v2.0.0/andes/system/dae_compactor.py",
    "https://github.com/CURENT/andes/blob/v2.0.0/andes/models/dynload/fload.py",
    "https://github.com/CURENT/andes/blob/v2.0.0/andes/models/dynload/zip.py",
)

_payload_sha256 = payload_sha256


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


def _frozen_node_input_basis() -> np.ndarray:
    vectors = stage1_power_coordinates(1.0)
    return np.column_stack([vectors[name] for name in ("common", "edge_0", "edge_1", "edge_2")])


def _coordinate_input_sequence(*, delta_load_system_pu: float) -> np.ndarray:
    node_sequence = np.zeros((TOTAL_STEPS, 4), dtype=float)
    target_position = CONTROLLED_BUS_ORDER.index(BUS_IDX)
    node_sequence[:ACTIVE_STEPS, target_position] = -float(delta_load_system_pu)
    basis = _frozen_node_input_basis()
    return np.linalg.solve(basis, node_sequence.T).T


def build_contract() -> dict[str, object]:
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "minimal-physical-pq-disturbance-identification",
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
        "signs": list(SIGNS),
        "record_count": len(POINTS) * len(SIGNS),
        "device_idx": DEVICE_IDX,
        "bus_idx": BUS_IDX,
        "controlled_bus_order": list(CONTROLLED_BUS_ORDER),
        "nominal_tie_lines": NOMINAL_TIE_LINES,
        "pre_event_active_load_system_pu": INITIAL_ACTIVE_SYSTEM_PU,
        "pre_event_reactive_load_system_pu": INITIAL_REACTIVE_SYSTEM_PU,
        "amplitude_system_pu": 0.05,
        "system_base_mva": 100.0,
        "vsg_device_base_mva": 200.0,
        "active_steps": ACTIVE_STEPS,
        "recovery_steps": TOTAL_STEPS - ACTIVE_STEPS,
        "steps": TOTAL_STEPS,
        "control_period_seconds": 0.2,
        "tds_substeps": SUBSTEPS,
        "tds_max_segment_seconds": 0.2 / SUBSTEPS,
        "event_times_seconds": {"apply": 0.5, "restore": 1.5},
        "event_row_semantics": "exact-event row is pre-event",
        "event_mechanism": "pre-setup absolute Alter assignments to PQ.Ppf and PQ.Qpf",
        "node_disturbance_map": [0.0, 0.0, -1.0, 0.0],
        "frozen_input_coordinates": ["common", "edge_0", "edge_1", "edge_2"],
        "parent_model": "immutable R316 retained order-10 realization",
        "thresholds": {
            "pq_readback_absolute_tolerance_system_pu": 1e-12,
            "zero_actuator_power_absolute_maximum_system_pu": 1e-6,
            "algebraic_residual_absolute_maximum": 1e-6,
            "signal_to_baseline_drift_energy_ratio_minimum": 10.0,
            "pair_midpoint_nonlinearity_ratio_maximum": 0.10,
            "reduced_physical_total_nrmse_maximum": 0.15,
            "reduced_physical_peak_vector_residual_maximum": 0.20,
        },
        "classification": [
            "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION",
            "BLOCK",
            "QUALIFY",
        ],
        "allow_is_reachable": False,
        "physical_execution_planned": True,
        "physical_execution_performed": False,
        "controller_executed": False,
        "closed_loop_executed": False,
        "distributed_runtime_executed": False,
        "training_executed": False,
        "eval_executed": False,
        "successor_package_required": True,
    }


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R333/plan.md",
        "question": ROOT / "memory/questions/Q-0085.md",
        "helper": SRC / "andes_rl_kundur/env/andes/model_first_pq_disturbance.py",
        "probe": ROOT / "probes/r333_pq_disturbance_identification.py",
        "adapter": Path(__file__).resolve(),
        "helper_tests": ROOT / "tests/test_model_first_pq_disturbance.py",
        "probe_tests": ROOT / "tests/test_r333_pq_disturbance_identification.py",
        "adapter_tests": ROOT / "tests/test_r333_pq_disturbance_adapter.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _parents() -> dict[str, dict[str, str]]:
    return {
        "r316_dynamic_model": {
            "path": _path_text(R316_MODEL),
            "sha256": verified_digest_only(R316_MODEL),
        },
        "r329_seal": {
            "path": _path_text(R329_SEAL),
            "sha256": verified_digest_only(R329_SEAL),
        },
        "r332_analysis": {
            "path": _path_text(R332_ANALYSIS),
            "sha256": verified_digest_only(R332_ANALYSIS),
        },
    }


def prepare(seal_path: Path, *, created_utc: str | None = None) -> str:
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": created_utc or datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "parents": _parents(),
        "sources": _sources(),
        "installed_andes": {
            "version": "2.0.0",
            "official_tag_commit": "eda5163c9ee8d19945a1dd5d1771fec5da608c27",
            "sources": EXPECTED_INSTALLED_SOURCES,
        },
        "official_sources": list(OFFICIAL_SOURCES),
    }
    return write_new_json(seal_path, seal)


def _load_seal(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    seal, digest = read_verified_json(path, expected_sha256)
    if (
        seal.get("round") != ROUND_ID
        or seal.get("question") != QUESTION_ID
        or seal.get("contract") != build_contract()
        or seal.get("contract_payload_sha256") != _payload_sha256(build_contract())
        or seal.get("parents") != _parents()
        or seal.get("sources") != _sources()
        or seal.get("installed_andes", {}).get("version") != "2.0.0"
        or seal.get("installed_andes", {}).get("sources") != EXPECTED_INSTALLED_SOURCES
        or seal.get("official_sources") != list(OFFICIAL_SOURCES)
    ):
        raise RuntimeError("R333 seal contract, source, parent, or authority drift")
    return seal, digest


def _verify_installed_andes() -> dict[str, object]:
    import andes

    version = importlib.metadata.version("andes")
    package_root = Path(andes.__file__).resolve().parent.parent
    actual = {
        relative: sha256_file(package_root / relative)
        for relative in EXPECTED_INSTALLED_SOURCES
    }
    if version != "2.0.0" or actual != EXPECTED_INSTALLED_SOURCES:
        raise RuntimeError("installed ANDES identity does not match the R333 seal")
    return {
        "version": version,
        "package_root": str(package_root),
        "sources": actual,
    }


def _load_r316_model() -> tuple[dict[str, Any], str]:
    payload, digest = read_verified_json(R316_MODEL)
    points = payload.get("points")
    if (
        payload.get("round") != "R316"
        or not isinstance(points, dict)
        or set(points) != {"HS0", "HS1"}
        or payload.get("training_authorized") is not False
    ):
        raise RuntimeError("R316 dynamic model identity or scope mismatch")
    for point in POINTS:
        realization_from_dict(points[point.name]["realization"])
    return payload, digest


def _event_receipts(
    *,
    contract: TimedPQDisturbanceContract,
    pre_event_snapshot: dict[str, object],
    post_apply_snapshot: dict[str, object],
    pre_restore_snapshot: dict[str, object],
    post_restore_snapshot: dict[str, object],
) -> list[dict[str, object]]:
    def receipt(
        *,
        idx: str,
        parameter: str,
        before: float,
        target: float,
        readback: float,
        scheduled_time: float,
        observation_time: float,
    ) -> dict[str, object]:
        return {
            "idx": idx,
            "mechanism": "Alter",
            "device_idx": DEVICE_IDX,
            "parameter": parameter,
            "method": "=",
            "scheduled_event_time_seconds": scheduled_time,
            "observation_time_seconds": observation_time,
            "before_system_pu": before,
            "target_system_pu": target,
            "readback_system_pu": readback,
            "system_base_mva": 100.0,
            "quantity": (
                "active-power consumption"
                if parameter == "Ppf"
                else "reactive-power consumption"
            ),
            "positive_sign": "increased consumption",
            "exact_event_row_semantics": "pre-event",
        }

    apply_observation = float(post_apply_snapshot["dae_time_seconds"])
    restore_observation = float(post_restore_snapshot["dae_time_seconds"])
    return [
        receipt(
            idx="R333_apply_p",
            parameter="Ppf",
            before=float(pre_event_snapshot["Ppf_system_pu"]),
            target=contract.disturbed_active_system_pu,
            readback=float(post_apply_snapshot["Ppf_system_pu"]),
            scheduled_time=contract.apply_time_seconds,
            observation_time=apply_observation,
        ),
        receipt(
            idx="R333_apply_q",
            parameter="Qpf",
            before=float(pre_event_snapshot["Qpf_system_pu"]),
            target=contract.initial_reactive_system_pu,
            readback=float(post_apply_snapshot["Qpf_system_pu"]),
            scheduled_time=contract.apply_time_seconds,
            observation_time=apply_observation,
        ),
        receipt(
            idx="R333_restore_p",
            parameter="Ppf",
            before=float(pre_restore_snapshot["Ppf_system_pu"]),
            target=contract.initial_active_system_pu,
            readback=float(post_restore_snapshot["Ppf_system_pu"]),
            scheduled_time=contract.restore_time_seconds,
            observation_time=restore_observation,
        ),
        receipt(
            idx="R333_restore_q",
            parameter="Qpf",
            before=float(pre_restore_snapshot["Qpf_system_pu"]),
            target=contract.initial_reactive_system_pu,
            readback=float(post_restore_snapshot["Qpf_system_pu"]),
            scheduled_time=contract.restore_time_seconds,
            observation_time=restore_observation,
        ),
    ]


def _event_grid_guard(times: object) -> dict[str, object]:
    grid = np.asarray(times, dtype=float).reshape(-1)
    details: dict[str, object] = {}
    strictly_increasing = bool(
        grid.size and np.all(np.isfinite(grid)) and np.all(np.diff(grid) > 0.0)
    )
    passed = strictly_increasing
    for label, event_time in (("apply", 0.5), ("restore", 1.5)):
        exact = np.flatnonzero(grid == event_time)
        before = np.flatnonzero(np.isclose(grid, event_time - 1e-4, rtol=0.0, atol=1e-12))
        after = np.flatnonzero(np.isclose(grid, event_time + 1e-4, rtol=0.0, atol=1e-12))
        row_pass = bool(
            len(exact) == len(before) == len(after) == 1
            and before[0] < exact[0] < after[0]
        )
        passed = passed and row_pass
        details[label] = {
            "event_time_seconds": event_time,
            "pre_critical_present": len(before) == 1,
            "exact_row_present": len(exact) == 1,
            "first_post_critical_present": len(after) == 1,
            "exact_row_semantics": "pre-event",
        }
    return {
        "pass": bool(passed),
        "strictly_increasing": strictly_increasing,
        "events": details,
    }


def _alter_event_inventory(system: Any) -> list[dict[str, object]]:
    model = system.Alter
    rows: list[dict[str, object]] = []
    for position in range(int(model.n)):
        rows.append(
            {
                "idx": str(model.idx.v[position]),
                "model": str(model.model.v[position]),
                "dev": str(model.dev.v[position]),
                "src": str(model.src.v[position]),
                "t": float(model.t.v[position]),
                "method": str(model.method.v[position]),
                "amount": float(model.amount.v[position]),
            }
        )
    return rows


def _tie_line_readback(system: Any) -> dict[str, dict[str, float]]:
    indices = [str(value) for value in system.Line.idx.v]
    return {
        line_idx: {
            "r": float(system.Line.r.v[indices.index(line_idx)]),
            "x": float(system.Line.x.v[indices.index(line_idx)]),
        }
        for line_idx in NOMINAL_TIE_LINES
    }


def _internal_limiter_active(info: dict[str, Any]) -> bool:
    internal = info["bess_internal"]
    ipul = np.asarray(internal["Ipul"], dtype=float)
    ipcmd = np.asarray(internal["Ipcmd_y"], dtype=float)
    ipmin = np.asarray(internal["Ipmin"], dtype=float)
    ipmax = np.asarray(internal["Ipmax"], dtype=float)
    return bool(
        not np.allclose(ipul, ipcmd, rtol=0.0, atol=1e-8)
        or np.any(ipcmd < ipmin - 1e-8)
        or np.any(ipcmd > ipmax + 1e-8)
        or any(
            not np.allclose(internal[name], np.ones(4), rtol=0.0, atol=1e-12)
            for name in ("Fvl", "Fvh", "Ffl", "Ffh")
        )
    )


@contextmanager
def _substep_environment():
    previous = os.environ.get("N_SUBSTEPS")
    if previous not in (None, str(SUBSTEPS)):
        raise RuntimeError("inherited N_SUBSTEPS override is forbidden")
    os.environ["N_SUBSTEPS"] = str(SUBSTEPS)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("N_SUBSTEPS", None)
        else:
            os.environ["N_SUBSTEPS"] = previous


def _run_record(
    *,
    point: Stage1OperatingPoint,
    sign: str,
    seal_digest: str,
    model_payload: dict[str, Any],
    model_digest: str,
) -> dict[str, object]:
    from andes_rl_kundur.env.andes.model_first_env import AndesModelFirstEnv

    class AndesModelFirstTimedPQEnv(TimedPQDisturbanceMixin, AndesModelFirstEnv):
        def __init__(self, *, pq_disturbance_contract, **kwargs):
            self.pq_disturbance_contract = pq_disturbance_contract
            super().__init__(**kwargs)

    delta = SIGN_DELTA[sign]
    event_contract = TimedPQDisturbanceContract(
        device_idx=DEVICE_IDX,
        bus_idx=BUS_IDX,
        initial_active_system_pu=INITIAL_ACTIVE_SYSTEM_PU,
        initial_reactive_system_pu=INITIAL_REACTIVE_SYSTEM_PU,
        delta_active_system_pu=delta,
    )
    config = replace(
        ModelFirstConfig.for_stage1_operating_point(point),
        tds_post_initialization_convergence_tolerance=DYNAMIC_TOLERANCE,
    )
    coordinate_input = _coordinate_input_sequence(delta_load_system_pu=delta)
    realization = realization_from_dict(model_payload["points"][point.name]["realization"])
    prediction = simulate_state_space(realization, coordinate_input)

    with _substep_environment():
        env = AndesModelFirstTimedPQEnv(
            pq_disturbance_contract=event_contract,
            model_first_config=config,
        )
        rows: list[dict[str, Any]] = []
        try:
            env.reset()
            apply_ids = {"R333_apply_p", "R333_apply_q"}
            apply_batches = [
                batch
                for batch in env.pq_event_audit
                if set(batch["event_ids"]) == apply_ids
            ]
            if len(apply_batches) != 1:
                raise RuntimeError("R333 apply-event callback audit is non-unique")
            pre_event = _jsonable(apply_batches[0]["before"])
            post_apply = _jsonable(apply_batches[0]["after"])
            event_inventory = _alter_event_inventory(env.ss)
            tie_line_readback = _tie_line_readback(env.ss)
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
                row["pq_active_load_delta_system_pu"] = delta if step < ACTIVE_STEPS else 0.0
                frequency = np.asarray(row["freq_hz_physical"], dtype=float)
                row["delta_f_physical_hz"] = (frequency - 60.0).tolist()
                rows.append(row)
            restore_ids = {"R333_restore_p", "R333_restore_q"}
            restore_batches = [
                batch
                for batch in env.pq_event_audit
                if set(batch["event_ids"]) == restore_ids
            ]
            if len(restore_batches) != 1:
                raise RuntimeError("R333 restore-event callback audit is non-unique")
            pre_restore = _jsonable(restore_batches[0]["before"])
            post_restore = _jsonable(restore_batches[0]["after"])
            event_callback_audit = _jsonable(env.pq_event_audit)
            env.ss.dae.ts.unpack(attr="t", warn_empty=False)
            tds_grid = np.asarray(env.ss.dae.ts.t, dtype=float).copy()
            terminal_snapshot = pq_runtime_snapshot(env.ss, event_contract)
        finally:
            env.close()

    transform = weighted_common_differential_transform(np.full(4, point.vsg_m_system))
    delta_frequency = np.asarray([row["delta_f_physical_hz"] for row in rows], dtype=float)
    outputs = (transform.forward @ (delta_frequency / 60.0).T).T
    event_grid = _event_grid_guard(tds_grid)
    expected_inventory = list(event_contract.alter_records())
    event_receipts = _event_receipts(
        contract=event_contract,
        pre_event_snapshot=pre_event,
        post_apply_snapshot=post_apply,
        pre_restore_snapshot=pre_restore,
        post_restore_snapshot=post_restore,
    )

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
        "tie_line_readback": tie_line_readback,
        "sign": sign,
        "device_idx": DEVICE_IDX,
        "delta_load_system_pu": delta,
        "event_contract": event_contract.to_dict(),
        "event_inventory": event_inventory,
        "alter_event_inventory_guard": event_inventory == expected_inventory,
        "event_callback_audit": event_callback_audit,
        "event_fire_counts": {
            event["idx"]: sum(
                int(event["idx"] in batch["event_ids"])
                for batch in event_callback_audit
            )
            for event in expected_inventory
        },
        "event_grid": _jsonable(event_grid),
        "exact_event_sample_order_guard": event_grid["pass"] is True,
        "event_receipts": event_receipts,
        "pq_active": post_apply["active"],
        "constant_power_weights": post_apply["constant_power_weights"],
        "active_fload_replacements_for_device": post_apply[
            "active_fload_replacements_for_device"
        ],
        "active_zip_replacements_for_device": post_apply[
            "active_zip_replacements_for_device"
        ],
        "pre_event_snapshot": pre_event,
        "post_apply_snapshot": post_apply,
        "pre_restore_snapshot": pre_restore,
        "post_restore_snapshot": post_restore,
        "terminal_snapshot": terminal_snapshot,
        "completed": len(rows) == TOTAL_STEPS
        and not any(bool(row["tds_failed"]) for row in rows),
        "tds_failed": any(bool(row["tds_failed"]) for row in rows),
        "n_steps": len(rows),
        "requested_steps": TOTAL_STEPS,
        "time_seconds": [float(row["t"]) for row in rows],
        "tds_time_grid_seconds": tds_grid.tolist(),
        "output_coordinates": outputs.tolist(),
        "predicted_output_coordinates": prediction.tolist(),
        "coordinate_input_sequence": coordinate_input.tolist(),
        "initialization_solver": initialization,
        "md_write_count_maximum": max(int(row["md_write_count"]) for row in rows),
        "bess_requested_power_absolute_maximum_system_pu": max(
            float(np.max(np.abs(row["bess_requested_power_system_pu"]))) for row in rows
        ),
        "bess_commanded_power_absolute_maximum_system_pu": max(
            float(np.max(np.abs(row["bess_commanded_power_system_pu"]))) for row in rows
        ),
        "bess_actual_power_absolute_maximum_system_pu": max(
            float(np.max(np.abs(row["bess_actual_power_system_pu"]))) for row in rows
        ),
        "bess_internal_power_absolute_maximum_system_pu": max(
            float(np.max(np.abs(row["bess_internal"][name])))
            for row in rows
            for name in ("Pext0", "Pext", "Pref", "Psum")
        ),
        "internal_limiter_active": any(_internal_limiter_active(row) for row in rows),
        "external_saturation_active": any(
            any(bool(reasons) for reasons in row["bess_saturation_reasons"])
            for row in rows
        ),
        "constraint_violation_count": sum(
            len(row["bess_constraint_violations"]) for row in rows
        ),
        "line_8_all_in_service": all(bool(row["line_8_in_service"]) for row in rows),
        "g4_all_in_service": all(bool(row["g4_in_service"]) for row in rows),
        "all_states_finite": all(bool(row["finite_state_algebraic"]) for row in rows),
        "system_exit_code_maximum": max(abs(int(row["system_exit_code"])) for row in rows),
        "algebraic_residual_absolute_maximum": max(
            float(row["dae_g_residual_max"]) for row in rows
        ),
        "negative_load_crossing": event_contract.disturbed_active_system_pu < 0.0,
        "tds_grid_guard": event_grid["pass"] is True,
        "traces": rows,
    }


def _runtime_record(installed: dict[str, object]) -> dict[str, object]:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "andes": installed,
        "native_threads": {
            name: os.environ.get(name)
            for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
        },
    }


def canary(out_path: Path) -> None:
    installed = _verify_installed_andes()
    model, model_digest = _load_r316_model()
    record = _run_record(
        point=POINTS[0],
        sign="positive",
        seal_digest="development-canary-not-formal",
        model_payload=model,
        model_digest=model_digest,
    )
    payload = {
        "stage": "development-canary",
        "not_formal_evidence": True,
        "record": record,
        "runtime": _runtime_record(installed),
    }
    digest = write_new_json(out_path, payload)
    print(f"canary_completed={record['completed']}", flush=True)
    print(f"canary_event_guard={record['exact_event_sample_order_guard']}", flush=True)
    print(f"canary_sha256={digest}", flush=True)


def _reserve_formal_attempt(
    out_dir: Path,
    *,
    seal_digest: str,
    created_utc: str | None = None,
) -> str:
    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"R333 formal output is not empty: {out_dir}")
    return write_new_json(
        out_dir / "formal_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "stage": "formal-execution-started",
            "created_utc": created_utc or datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "physical_execution_started": True,
            "controller_executed": False,
            "distributed_runtime_executed": False,
            "training_executed": False,
            "eval_executed": False,
            "retry_authorized": False,
        },
    )


def _write_execution_failure(
    out_dir: Path,
    *,
    seal_digest: str,
    attempt_digest: str,
    error: Exception,
) -> None:
    try:
        write_new_json(
            out_dir / "execution_failure.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "classification": "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION",
                "created_utc": datetime.now(UTC).isoformat(),
                "seal_sha256": seal_digest,
                "formal_attempt_sha256": attempt_digest,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "retry_authorized": False,
            },
        )
    except Exception:
        pass


def execute(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    _seal, seal_digest = _load_seal(seal_path, expected_sha256)
    installed = _verify_installed_andes()
    model, model_digest = _load_r316_model()
    out_dir = out_dir.resolve()
    attempt_digest = _reserve_formal_attempt(out_dir, seal_digest=seal_digest)
    try:
        records = [
            _run_record(
                point=point,
                sign=sign,
                seal_digest=seal_digest,
                model_payload=model,
                model_digest=model_digest,
            )
            for point in POINTS
            for sign in SIGNS
        ]
    except Exception as error:
        _write_execution_failure(
            out_dir,
            seal_digest=seal_digest,
            attempt_digest=attempt_digest,
            error=error,
        )
        raise
    execution = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "dynamic_model_sha256": model_digest,
        "formal_attempt_sha256": attempt_digest,
        "records": records,
        "source_identity": True,
        "parent_identity": True,
        "runtime_identity": True,
        "physical_execution_performed": True,
        "controller_executed": False,
        "closed_loop_executed": False,
        "distributed_runtime_executed": False,
        "training_executed": False,
        "eval_executed": False,
    }
    execution_digest = write_new_json(out_dir / "execution.json", execution)
    provenance_digest = write_new_json(
        out_dir / "provenance.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "execution_sha256": execution_digest,
            "formal_attempt_sha256": attempt_digest,
            "dynamic_model_sha256": model_digest,
            "runtime": _runtime_record(installed),
            "physical_execution_performed": True,
            "controller_executed": False,
            "distributed_runtime_executed": False,
            "training_executed": False,
            "eval_executed": False,
        },
    )
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "record_count": len(records),
        "records": [
            {
                "name": "formal_attempt",
                "path": _path_text(out_dir / "formal_attempt.json"),
                "sha256": attempt_digest,
            },
            {
                "name": "execution",
                "path": _path_text(out_dir / "execution.json"),
                "sha256": execution_digest,
            },
            {
                "name": "provenance",
                "path": _path_text(out_dir / "provenance.json"),
                "sha256": provenance_digest,
            },
        ],
        "training_executed": False,
        "eval_executed": False,
    }
    manifest_digest = write_new_json(out_dir / "run_manifest.json", manifest)
    print(f"record_count={len(records)}", flush=True)
    print(f"execution_sha256={execution_digest}", flush=True)
    print(f"run_manifest_sha256={manifest_digest}", flush=True)


def _validated_manifest_entries(
    manifest: dict[str, Any],
    out_dir: Path,
) -> dict[str, dict[str, Any]]:
    raw_entries = manifest.get("records")
    if not isinstance(raw_entries, list) or len(raw_entries) != 3:
        raise RuntimeError("R333 manifest must contain exactly three artifacts")
    if not all(isinstance(entry, dict) for entry in raw_entries):
        raise RuntimeError("R333 manifest contains a non-object artifact entry")
    names = [str(entry.get("name")) for entry in raw_entries]
    if len(names) != len(set(names)):
        raise RuntimeError("R333 manifest contains duplicate artifact names")
    entries = {name: entry for name, entry in zip(names, raw_entries, strict=True)}
    expected_paths = {
        "formal_attempt": _path_text(out_dir / "formal_attempt.json"),
        "execution": _path_text(out_dir / "execution.json"),
        "provenance": _path_text(out_dir / "provenance.json"),
    }
    if set(entries) != set(expected_paths) or any(
        entries[name].get("path") != path for name, path in expected_paths.items()
    ):
        raise RuntimeError("R333 manifest artifact inventory mismatch")
    return entries


def analyse(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected_sha256)
    manifest, manifest_digest = read_verified_json(out_dir / "run_manifest.json")
    if (
        manifest.get("round") != ROUND_ID
        or manifest.get("question") != QUESTION_ID
        or manifest.get("seal_sha256") != seal_digest
        or manifest.get("record_count") != 6
    ):
        raise RuntimeError("R333 run manifest identity mismatch")
    entries = _validated_manifest_entries(manifest, out_dir.resolve())
    attempt_entry = entries["formal_attempt"]
    execution_entry = entries["execution"]
    provenance_entry = entries["provenance"]
    attempt, attempt_digest = read_verified_json(
        ROOT / attempt_entry["path"], attempt_entry["sha256"]
    )
    execution, execution_digest = read_verified_json(
        ROOT / execution_entry["path"], execution_entry["sha256"]
    )
    provenance, provenance_digest = read_verified_json(
        ROOT / provenance_entry["path"], provenance_entry["sha256"]
    )
    model, model_digest = _load_r316_model()
    expected_inputs: dict[str, dict[str, object]] = {}
    expected_predictions: dict[str, dict[str, object]] = {}
    for point in POINTS:
        expected_inputs[point.name] = {}
        expected_predictions[point.name] = {}
        realization = realization_from_dict(model["points"][point.name]["realization"])
        for sign in SIGNS:
            coordinate_input = _coordinate_input_sequence(
                delta_load_system_pu=SIGN_DELTA[sign]
            )
            expected_inputs[point.name][sign] = coordinate_input.tolist()
            expected_predictions[point.name][sign] = simulate_state_space(
                realization,
                coordinate_input,
            ).tolist()
    evidence_chain_valid = bool(
        attempt.get("round") == ROUND_ID
        and attempt.get("question") == QUESTION_ID
        and attempt.get("stage") == "formal-execution-started"
        and attempt.get("seal_sha256") == seal_digest
        and attempt.get("physical_execution_started") is True
        and attempt.get("retry_authorized") is False
        and execution.get("formal_attempt_sha256") == attempt_digest
        and execution.get("seal_sha256") == seal_digest
        and execution.get("dynamic_model_sha256") == model_digest
        and provenance.get("formal_attempt_sha256") == attempt_digest
        and provenance.get("execution_sha256") == execution_digest
        and provenance.get("seal_sha256") == seal_digest
        and provenance.get("dynamic_model_sha256") == model_digest
        and provenance.get("runtime", {}).get("andes", {}).get("version") == "2.0.0"
        and provenance.get("runtime", {}).get("andes", {}).get("sources")
        == EXPECTED_INSTALLED_SOURCES
        and manifest.get("training_executed") is False
        and manifest.get("eval_executed") is False
    )
    analysis_kwargs = {
        "expected_seal_sha256": seal_digest,
        "expected_dynamic_model_sha256": model_digest,
        "expected_coordinate_inputs": expected_inputs,
        "expected_predictions": expected_predictions,
        "evidence_chain_valid": evidence_chain_valid,
    }
    first = analyse_pq_disturbance_identification(
        execution,
        seal["contract"],
        **analysis_kwargs,
    )
    second = analyse_pq_disturbance_identification(
        execution,
        seal["contract"],
        **analysis_kwargs,
    )
    if first != second:
        raise RuntimeError("R333 analysis replay is nondeterministic")
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "seal_sha256": seal_digest,
        "formal_attempt_sha256": attempt_digest,
        "execution_sha256": execution_digest,
        "provenance_sha256": provenance_digest,
        "run_manifest_sha256": manifest_digest,
        "dynamic_model_sha256": model_digest,
        "evidence_chain_valid": evidence_chain_valid,
        "deterministic_replay": True,
        **first,
    }
    digest = write_new_json(out_dir / "analysis.json", analysis)
    print(f"classification={analysis['classification']}", flush=True)
    print(f"analysis_sha256={digest}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    canary_parser = subparsers.add_parser("canary")
    canary_parser.add_argument("--out", type=Path, required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
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
    if args.command == "canary":
        canary(args.out)
    elif args.command == "prepare":
        digest = prepare(args.seal)
        print(f"seal_sha256={digest}", flush=True)
    elif args.command == "execute":
        execute(args.seal, args.expected_sha256, args.out)
    else:
        analyse(args.seal, args.expected_sha256, args.out)


if __name__ == "__main__":
    main()
