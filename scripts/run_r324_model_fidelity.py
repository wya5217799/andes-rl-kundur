#!/usr/bin/env python3
"""Seal, execute, and analyse the R324 model-fidelity gate.

Usage::

    python scripts/run_r324_model_fidelity.py prepare
    python scripts/run_r324_model_fidelity.py execute --expected-sha256 <seal>
    python scripts/run_r324_model_fidelity.py analyse --expected-sha256 <seal>

The physical ``execute`` command is WSL-only and must be launched through
``scripts/andes_scratch.py``.  Artifacts are create-only and carry SHA-256
sidecars.  The round executes no controller, EVAL profile, or training path.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
from collections.abc import Mapping
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

from probes.r324_model_fidelity_validation import (  # noqa: E402
    EXPECTED_SUBSTEPS,
    FREQUENCY_MAX_ABS_HZ,
    PEAK_TIME_MAX_ABS_SECONDS,
    POWER_MAX_ABS,
    REQUIRED_PARAMETER_IDS,
    SOC_MAX_ABS,
    TERMINAL_NORMALIZED_L2,
    evaluate_model_fidelity,
)

from andes_rl_kundur.env.andes.model_first_contract import (  # noqa: E402
    ModelFirstConfig,
    stage1_operating_points,
    stage1_power_coordinates,
)

ROUND_ID = "R324"
QUESTION_ID = "Q-0079"
PLAN = ROOT / "memory/rounds/R324/plan.md"
QUESTION = ROOT / "memory/questions/Q-0079.md"
DEFAULT_SEAL = ROOT / "memory/rounds/R324/model_fidelity_seal.json"
DEFAULT_OUT = ROOT / "results/r324_model_fidelity"

ACTIVE_STEPS = 5
RECOVERY_STEPS = 20
TOTAL_STEPS = ACTIVE_STEPS + RECOVERY_STEPS
INITIALIZATION_TOLERANCE = 1e-4
INITIALIZATION_TOL_ZERO = 1e-10
DYNAMIC_TOLERANCE = 1e-10
DYNAMIC_TOL_ZERO = 1e-16


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _payload_sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _write_new_json(path: Path, payload: object) -> str:
    path = path.resolve()
    sidecar = path.with_suffix(path.suffix + ".sha256")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"create-only artifact already exists: {path}")
    encoded = _canonical_bytes(payload)
    with path.open("xb") as handle:
        handle.write(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    with sidecar.open("x", encoding="ascii", newline="\n") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def _read_verified_json(
    path: Path,
    expected_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    path = path.resolve()
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not path.is_file() or not sidecar.is_file():
        raise RuntimeError(f"missing artifact or sidecar: {path}")
    digest = _sha256_file(path)
    recorded = sidecar.read_text(encoding="ascii").strip().split()[0]
    if digest != recorded:
        raise RuntimeError(f"sidecar mismatch for {path}")
    if expected_sha256 is not None and digest != expected_sha256:
        raise RuntimeError(f"expected hash mismatch for {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"artifact root must be an object: {path}")
    return payload, digest


def _path_text(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _binding(
    identifier: str,
    value: object,
    unit: str,
    base: str,
    represented_object: str,
    source_locator: str,
    provenance_class: str,
    calibration_ceiling: str,
) -> dict[str, object]:
    return {
        "id": identifier,
        "value": value,
        "unit": unit,
        "base": base,
        "represented_object": represented_object,
        "source_locator": source_locator,
        "provenance_class": provenance_class,
        "binding_status": "bound",
        "physically_calibrated": False,
        "calibration_ceiling": calibration_ceiling,
    }


def build_parameter_bindings() -> list[dict[str, object]]:
    """Return the prospective, honest parameter-source inventory."""

    case = "andes://kundur/kundur_full.xlsx; paper/decoupling_marl_model_first/working/model_contract.md#model-of-record-and-physical-base"
    v4 = "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py"
    model = "paper/decoupling_marl_model_first/working/model_contract.md#equation-to-implementation-reconciliation"
    storage = "memory/rounds/R272/plan.md#frozen-physical-contract"
    official = "paper/decoupling_marl_model_first/reports/R323.md#official-source-scope"
    execution = "memory/rounds/R324/plan.md#frozen-physical-execution"
    assumption = "declared benchmark/proxy assumption; not a calibrated device"
    rows = [
        _binding("kundur_case_identity", "ANDES kundur_full.xlsx", "case", "ANDES 2.0.0", "two-area benchmark network", case, "case-source", "benchmark case only; not a measured installation"),
        _binding("system_base_mva", 100.0, "MVA", "system", "per-unit conversion base", case, "case-source", "case base only; not equipment calibration"),
        _binding("nominal_frequency_hz", 60.0, "Hz", "system", "physical frequency base", case, "case-source", "case nominal only"),
        _binding("original_g4_retained", True, "boolean", "case", "original Kundur generator 4", model, "explicit-modelling-assumption", assumption),
        _binding("default_line_trip_disabled", True, "boolean", "case", "Line 8 default event", model, "explicit-modelling-assumption", assumption),
        _binding("controlled_vsg_locations", [12, 16, 14, 15], "bus indices", "network", "four controlled GENCLS proxies", f"{v4}#AndesMultiVSGEnvV4.VSG_BUSES", "literature-derived", "topology proxy; not site calibration"),
        _binding("controlled_vsg_device_rating_mva", 200.0, "MVA", "device", "each controlled GENCLS proxy", "src/andes_rl_kundur/env/andes/base_env.py#AndesBaseEnv.VSG_SN", "explicit-modelling-assumption", assumption),
        _binding("controlled_vsg_active_dispatch_device_pu", 0.5, "p.u.", "200-MVA device", "each controlled static generator", f"{v4}#AndesMultiVSGEnvV4._build_system", "explicit-modelling-assumption", assumption),
        _binding("controlled_vsg_inertia_device", [200.0] * 4, "M=2H", "200-MVA device input", "four GENCLS proxies", f"{v4}#L16-L18; {model}", "literature-derived", "paper-range design proxy; not identified inertia"),
        _binding("controlled_vsg_damping_device", [100.0] * 4, "GENCLS D", "200-MVA device input", "four GENCLS proxies", f"{v4}#L16-L18; {model}", "literature-derived", "paper-range design proxy; not identified damping"),
        _binding("controlled_vsg_stator_resistance_pu", 0.001, "p.u.", "device", "controlled GENCLS electrical proxy", f"{v4}#AndesMultiVSGEnvV4._build_system", "explicit-modelling-assumption", assumption),
        _binding("controlled_vsg_transient_reactance_pu", 0.15, "p.u.", "device", "controlled GENCLS electrical proxy", f"{v4}#AndesMultiVSGEnvV4._build_system", "explicit-modelling-assumption", assumption),
        _binding("radial_line_voltage_kv", 230.0, "kV", "bus", "four added radial connections", f"{v4}#AndesMultiVSGEnvV4.NEW_BUS_VN", "case-source", "matched benchmark voltage base; not line identification"),
        _binding("radial_line_resistance_pu", 0.002, "p.u.", "network case base", "four added radial connections", f"{v4}#AndesMultiVSGEnvV4.NEW_LINE_R", "explicit-modelling-assumption", assumption),
        _binding("radial_line_reactance_pu", 0.20, "p.u.", "network case base", "four added radial connections", f"{v4}#AndesMultiVSGEnvV4.NEW_LINE_X", "explicit-modelling-assumption", assumption),
        _binding("radial_line_shunt_pu", 0.0175, "p.u.", "network case base", "four added radial connections", f"{v4}#AndesMultiVSGEnvV4.NEW_LINE_B", "explicit-modelling-assumption", assumption),
        _binding("added_loads_system_pu", {"bus14": {"p": 2.48, "q": 0.0}, "bus15": {"p": 0.0, "q": 0.0}}, "p.u.", "100-MVA system", "added proxy-bus operating load", f"{v4}#AndesMultiVSGEnvV4.NEW_LOADS", "literature-derived", "benchmark operating assumption; not measured load"),
        _binding("wind_proxy_contract", {"bus": 8, "rating_mva": 100.0, "p0_device_pu": 1.0, "M": 0.1, "D": 0.0, "ra": 0.001, "xd1": 0.15}, "mixed", "100-MVA device", "separate low-inertia GENCLS wind proxy", f"{v4}#AndesMultiVSGEnvV4.WF2", "explicit-modelling-assumption", "location/rating literature-motivated; dynamics are an uncalibrated proxy"),
        _binding("storage_locations", [12, 16, 14, 15], "bus indices", "network", "four independent ESD1 devices", "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py#AndesMultiVSGEnvV4Storage._pre_setup_addons", "explicit-modelling-assumption", assumption),
        _binding("storage_module_count", 50, "modules/device", "aggregate", "each storage equivalent", storage, "explicit-modelling-assumption", "feasibility sizing assumption; not a real installation"),
        _binding("storage_module_power_mva", 0.72, "MVA", "module", "experimental BESS module anchor", "https://doi.org/10.1016/j.epsr.2022.108567; memory/rounds/R272/plan.md#capacity-anchor", "literature-derived", "capacity anchor only; not the simulated plant manufacturer"),
        _binding("storage_module_energy_mwh", 0.56, "MWh", "module", "experimental BESS module anchor", "https://doi.org/10.1016/j.epsr.2022.108567; memory/rounds/R272/plan.md#capacity-anchor", "literature-derived", "capacity anchor only; not the simulated plant manufacturer"),
        _binding("storage_device_power_mva", 36.0, "MVA", "device", "50-module storage equivalent", "src/andes_rl_kundur/control/active_power.py#EnergyFeasibleBESSContract.device_power_mva", "derived", "derived aggregate; not calibrated hardware"),
        _binding("storage_device_energy_mwh", 28.0, "MWh", "device", "50-module storage equivalent", "src/andes_rl_kundur/control/active_power.py#EnergyFeasibleBESSContract.device_energy_mwh", "derived", "derived aggregate; not calibrated hardware"),
        _binding("storage_power_limit_device_pu", 1.0, "p.u.", "36-MVA device", "ESD1 active-power capability", f"{official}; src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py#pmx", "official-model-default", "model/nameplate boundary; not validated converter capability"),
        _binding("storage_active_current_limit_device_pu", 1.0, "p.u.", "36-MVA device", "PVD1/ESD1 active current", f"{official}; src/andes_rl_kundur/control/active_power.py#EnergyFeasibleBESSContract", "official-model-default", "nameplate current assumption; no fault-current claim"),
        _binding("storage_active_current_lag_seconds", 0.02, "s", "device", "ESD1/PVD1 active-current state", f"{official}; src/andes_rl_kundur/control/active_power.py#r272_frozen_bess_contract", "official-model-default", "software default; not identified hardware response"),
        _binding("storage_soc_integrator_scale", 1.0, "s", "device", "ESD1 SOC differential equation", f"{official}; src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py#Tf", "official-model-default", "software scaling default; not hardware identification"),
        _binding("storage_soc_contract", {"initial": 0.5, "minimum": 0.2, "maximum": 0.8}, "fraction", "device energy", "storage energy state", "https://www.wecc.org/sites/default/files/documents/meeting/2024/ESD%20Modeling%20Guidelines%20-%20Final.pdf; memory/rounds/R272/plan.md#per-device-frozen-fields", "literature-derived", "typical-range assumption; not measured initial SOC"),
        _binding("storage_efficiencies", {"charge": 0.9848857802, "discharge": 0.9848857802, "round_trip": 0.97}, "fraction", "grid-to-storage", "ESD1 SOC energy conversion", "https://doi.org/10.1016/j.epsr.2022.108567; memory/rounds/R272/plan.md#per-device-frozen-fields", "derived", "equal split of a literature lower-bound round-trip value"),
        _binding("storage_active_power_priority", True, "boolean", "device", "ESD1 current priority", "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py#pqflag", "explicit-modelling-assumption", assumption),
        _binding("storage_reactive_power_excluded", True, "boolean", "device", "ESD1 reactive service", "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py#qmn-qmx", "explicit-modelling-assumption", assumption),
        _binding("external_ramp_system_pu_per_second", 0.36, "system p.u./s", "100-MVA system", "repository power projection", "src/andes_rl_kundur/control/active_power.py#r272_frozen_bess_contract; memory/rounds/R272/plan.md#per-device-frozen-fields", "explicit-modelling-assumption", "conservative one-second nameplate ramp; not manufacturer data"),
        _binding("control_period_seconds", 0.2, "s", "execution", "sampled controller boundary", f"{model}; {execution}", "explicit-modelling-assumption", "paper-path sampling assumption; not hardware delay"),
        _binding("initialization_seconds", 0.5, "s", "execution", "unperturbed TDS initialization", f"{model}; {execution}", "explicit-modelling-assumption", "numerical initialization protocol only"),
        _binding("tds_method", "trapezoid", "method", "ANDES TDS", "DAE integration", f"{official}; {execution}", "official-model-default", "phasor-domain numerical method; no EMT equivalence"),
        _binding("tds_solver_tolerances", {"initialization": 1e-4, "initialization_tiny": 1e-10, "dynamic": 1e-10, "dynamic_tiny": 1e-16}, "Newton correction", "ANDES TDS", "initialization and pulse execution", f"{execution}; memory/rounds/R309/plan.md", "explicit-modelling-assumption", "numerical stopping contract; not physical calibration"),
        _binding("tds_substep_refinement", [5, 10, 20], "substeps per 0.2 s", "execution", "maximum TDS segment length", execution, "explicit-modelling-assumption", "prospective convergence sequence only"),
        _binding("open_loop_pulse", [0.0, 0.0, -0.05, 0.05], "system p.u.", "100-MVA system", "edge-2 signed ESD1 request", f"{model}#stage-0-and-stage-1-non-learning-probe-contract; {execution}", "explicit-modelling-assumption", "small-signal probe, not a controller command distribution"),
        _binding("open_loop_active_duration_seconds", 1.0, "s", "execution", "held pulse duration", execution, "explicit-modelling-assumption", "probe protocol only"),
        _binding("open_loop_recovery_duration_seconds", 4.0, "s", "execution", "zero-request recovery", execution, "explicit-modelling-assumption", "finite observation window only"),
    ]
    identifiers = {str(row["id"]) for row in rows}
    if identifiers != set(REQUIRED_PARAMETER_IDS) or len(rows) != len(identifiers):
        raise RuntimeError("R324 parameter inventory does not match the validator")
    return sorted(rows, key=lambda row: str(row["id"]))


def build_contract() -> dict[str, Any]:
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "parameter-provenance-and-open-loop-time-step-convergence",
        "parameter_bindings": build_parameter_bindings(),
        "execution": {
            "operating_point": "OP0",
            "coordinate": "edge_2",
            "sign": "negative",
            "pulse_system_pu": [0.0, 0.0, -0.05, 0.05],
            "active_steps": ACTIVE_STEPS,
            "recovery_steps": RECOVERY_STEPS,
            "control_period_seconds": 0.2,
            "tds_substeps": list(EXPECTED_SUBSTEPS),
            "tds_max_segment_seconds": [0.04, 0.02, 0.01],
            "tds_method": "trapezoid",
            "initialization_tolerance": INITIALIZATION_TOLERANCE,
            "initialization_tiny_correction_threshold": INITIALIZATION_TOL_ZERO,
            "dynamic_tolerance": DYNAMIC_TOLERANCE,
            "dynamic_tiny_correction_threshold": DYNAMIC_TOL_ZERO,
        },
        "thresholds": {
            "maximum_achieved_power_difference_system_pu": POWER_MAX_ABS,
            "maximum_frequency_difference_hz": FREQUENCY_MAX_ABS_HZ,
            "maximum_soc_difference": SOC_MAX_ABS,
            "terminal_state_normalized_l2_difference": TERMINAL_NORMALIZED_L2,
            "maximum_peak_time_difference_seconds": PEAK_TIME_MAX_ABS_SECONDS,
        },
        "classification": [
            "INVALID-MODEL-FIDELITY-CHECK",
            "PARAMETER-PROVENANCE-NO-GO",
            "TIME-STEP-CONVERGENCE-NO-GO",
            "MODEL-FIDELITY-GATE-PASS",
        ],
        "controller_executed": False,
        "closed_loop_executed": False,
        "eval_status": "NOT-APPLICABLE-OPEN-LOOP-CONVERGENCE",
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def _source_paths() -> dict[str, Path]:
    return {
        "plan": PLAN,
        "question": QUESTION,
        "adapter": Path(__file__).resolve(),
        "validator": ROOT / "probes/r324_model_fidelity_validation.py",
        "model_contract": ROOT / "paper/decoupling_marl_model_first/working/model_contract.md",
        "model_environment": SRC / "andes_rl_kundur/env/andes/model_first_env.py",
        "model_configuration": SRC / "andes_rl_kundur/env/andes/model_first_contract.py",
        "storage_environment": SRC / "andes_rl_kundur/env/andes/andes_vsg_storage_env.py",
        "active_power_contract": SRC / "andes_rl_kundur/control/active_power.py",
        "v4_environment": SRC / "andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "base_environment": SRC / "andes_rl_kundur/env/andes/base_env.py",
        "r272_parameter_source": ROOT / "memory/rounds/R272/plan.md",
        "r323_official_audit": ROOT / "paper/decoupling_marl_model_first/reports/R323.md",
        "validator_tests": ROOT / "tests/test_r324_model_fidelity_validation.py",
        "adapter_tests": ROOT / "tests/test_r324_model_fidelity.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def prepare(seal_path: Path) -> str:
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "sources": _sources(),
    }
    digest = _write_new_json(seal_path, seal)
    print(f"seal_sha256={digest}", flush=True)
    return digest


def _load_seal(path: Path, expected: str) -> tuple[dict[str, Any], str]:
    seal, digest = _read_verified_json(path, expected)
    if seal.get("round") != ROUND_ID or seal.get("question") != QUESTION_ID:
        raise RuntimeError("R324 seal identity mismatch")
    if seal.get("contract_payload_sha256") != _payload_sha256(seal["contract"]):
        raise RuntimeError("R324 seal contract payload drift")
    if seal["contract"] != build_contract():
        raise RuntimeError("R324 in-code contract drift")
    for name, entry in seal["sources"].items():
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed source drift for {name}")
    return seal, digest


def _runtime_record() -> dict[str, Any]:
    try:
        andes_version = importlib.metadata.version("andes")
    except importlib.metadata.PackageNotFoundError:
        andes_version = None
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "andes": andes_version,
    }


@contextmanager
def _substep_environment(substeps: int):
    previous = os.environ.get("N_SUBSTEPS")
    os.environ["N_SUBSTEPS"] = str(substeps)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("N_SUBSTEPS", None)
        else:
            os.environ["N_SUBSTEPS"] = previous


def _internal_limiter_active(info: Mapping[str, Any]) -> bool:
    internal = info["bess_internal"]
    ipul = np.asarray(internal["Ipul"], dtype=float)
    ipcmd = np.asarray(internal["Ipcmd_y"], dtype=float)
    ipmin = np.asarray(internal["Ipmin"], dtype=float)
    ipmax = np.asarray(internal["Ipmax"], dtype=float)
    if not np.allclose(ipul, ipcmd, rtol=0.0, atol=1e-8):
        return True
    if np.any(ipcmd < ipmin - 1e-8) or np.any(ipcmd > ipmax + 1e-8):
        return True
    return any(
        not np.allclose(internal[name], np.ones(4), rtol=0.0, atol=1e-12)
        for name in ("Fvl", "Fvh", "Ffl", "Ffh")
    )


def _run_trace(*, substeps: int, seal_digest: str) -> dict[str, Any]:
    from andes_rl_kundur.env.andes.model_first_env import AndesModelFirstEnv

    point = next(point for point in stage1_operating_points() if point.name == "OP0")
    config = replace(
        ModelFirstConfig.for_stage1_operating_point(point),
        tds_post_initialization_convergence_tolerance=DYNAMIC_TOLERANCE,
    )
    pulse = -stage1_power_coordinates()["edge_2"]
    with _substep_environment(substeps):
        env = AndesModelFirstEnv(model_first_config=config)
        infos: list[dict[str, Any]] = []
        try:
            env.reset()
            initialization = _jsonable(env._model_first_initialization_solver_contract)
            zero_md = {index: np.zeros(2) for index in range(env.N_AGENTS)}
            for step in range(TOTAL_STEPS):
                request = pulse if step < ACTIVE_STEPS else np.zeros(4)
                _, _, _, info = env.step(
                    zero_md,
                    bess_power_request_pu=request,
                )
                infos.append(dict(info))
            terminal_x = np.asarray(env.ss.dae.x, dtype=float).copy()
            terminal_y = np.asarray(env.ss.dae.y, dtype=float).copy()
            method = str(env.ss.TDS.config.method)
        finally:
            env.close()

    completed = len(infos) == TOTAL_STEPS and not any(
        bool(info["tds_failed"]) for info in infos
    )
    external_saturation = [
        any(bool(reasons) for reasons in info["bess_saturation_reasons"])
        for info in infos
    ]
    internal_limiter = [_internal_limiter_active(info) for info in infos]
    guard_failures: list[str] = []
    if not completed:
        guard_failures.append("incomplete_or_tds_failed")
    if any(external_saturation):
        guard_failures.append("external_saturation")
    if any(internal_limiter):
        guard_failures.append("internal_limiter")
    if any(info["bess_constraint_violations"] for info in infos):
        guard_failures.append("constraint_violation")

    return {
        "substeps": substeps,
        "max_segment_seconds": 0.2 / substeps,
        "operating_point": "OP0",
        "coordinate": "edge_2",
        "sign": "negative",
        "completed": completed,
        "execution_guard_failures": guard_failures,
        "time_seconds": [float(info["time"]) for info in infos],
        "achieved_power_system_pu": _jsonable(
            [info["bess_actual_power_system_pu"] for info in infos]
        ),
        "frequency_hz": _jsonable([info["freq_hz_physical"] for info in infos]),
        "soc": _jsonable([info["bess_soc"] for info in infos]),
        "requested_power_system_pu": _jsonable(
            [info["bess_requested_power_system_pu"] for info in infos]
        ),
        "commanded_power_system_pu": _jsonable(
            [info["bess_commanded_power_system_pu"] for info in infos]
        ),
        "external_command_readback_system_pu": _jsonable(
            [info["bess_external_command_readback_system_pu"] for info in infos]
        ),
        "vsg_m_actual_system": _jsonable(
            [info["vsg_m_actual_system"] for info in infos]
        ),
        "vsg_d_actual_system": _jsonable(
            [info["vsg_d_actual_system"] for info in infos]
        ),
        "dae_g_residual_max": [float(info["dae_g_residual_max"]) for info in infos],
        "pflow_converged": [bool(info["pflow_converged"]) for info in infos],
        "tds_failed": [bool(info["tds_failed"]) for info in infos],
        "system_exit_code": [int(info["system_exit_code"]) for info in infos],
        "finite_state_algebraic": [
            bool(info["finite_state_algebraic"]) for info in infos
        ],
        "line_8_in_service": [bool(info["line_8_in_service"]) for info in infos],
        "g4_in_service": [bool(info["g4_in_service"]) for info in infos],
        "md_write_count": [int(info["md_write_count"]) for info in infos],
        "external_saturation_active": external_saturation,
        "internal_limiter_active": internal_limiter,
        "constraint_violation_count": [
            len(info["bess_constraint_violations"]) for info in infos
        ],
        "tds_method": method,
        "initialization_tolerance": initialization["convergence_tolerance"],
        "initialization_tiny_correction_threshold": initialization[
            "tiny_correction_threshold"
        ],
        "dynamic_tolerance": DYNAMIC_TOLERANCE,
        "dynamic_tiny_correction_threshold": DYNAMIC_TOL_ZERO,
        "terminal_x": terminal_x.tolist(),
        "terminal_y": terminal_y.tolist(),
    }


def execute(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    out_dir = out_dir.resolve()
    if (out_dir / "run_manifest.json").exists():
        raise FileExistsError(f"R324 run already exists: {out_dir}")
    traces = [
        _run_trace(substeps=substeps, seal_digest=seal_digest)
        for substeps in EXPECTED_SUBSTEPS
    ]
    execution_payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "parameter_bindings": seal["contract"]["parameter_bindings"],
        "traces": traces,
        "physical_execution_performed": True,
        "controller_executed": False,
        "closed_loop_executed": False,
        "eval_status": "NOT-APPLICABLE-OPEN-LOOP-CONVERGENCE",
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
    execution_path = out_dir / "execution.json"
    execution_digest = _write_new_json(execution_path, execution_payload)
    provenance_path = out_dir / "provenance.json"
    provenance_digest = _write_new_json(
        provenance_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "execution_sha256": execution_digest,
            "execution_runtime": _runtime_record(),
            "physical_execution_performed": True,
            "controller_executed": False,
            "closed_loop_executed": False,
            "eval_status": "NOT-APPLICABLE-OPEN-LOOP-CONVERGENCE",
            "distributed_agent_implementation_authorized": False,
            "training_authorized": False,
        },
    )
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "records": [
            {"path": _path_text(execution_path), "sha256": execution_digest},
            {"path": _path_text(provenance_path), "sha256": provenance_digest},
        ],
        "trace_count": len(traces),
        "training_authorized": False,
    }
    manifest_digest = _write_new_json(out_dir / "run_manifest.json", manifest)
    print(f"trace_count={len(traces)}", flush=True)
    print(f"execution_sha256={execution_digest}", flush=True)
    print(f"run_manifest_sha256={manifest_digest}", flush=True)


def analyse(seal_path: Path, expected: str, out_dir: Path) -> None:
    _seal, seal_digest = _load_seal(seal_path, expected)
    manifest, _manifest_digest = _read_verified_json(out_dir / "run_manifest.json")
    if (
        manifest.get("round") != ROUND_ID
        or manifest.get("question") != QUESTION_ID
        or manifest.get("seal_sha256") != seal_digest
        or manifest.get("trace_count") != 3
    ):
        raise RuntimeError("R324 run manifest identity mismatch")
    execution_entry = manifest["records"][0]
    execution, _execution_digest = _read_verified_json(
        ROOT / execution_entry["path"], execution_entry["sha256"]
    )
    first = evaluate_model_fidelity(execution)
    second = evaluate_model_fidelity(execution)
    if first != second:
        raise RuntimeError("R324 formal analysis is not deterministic")
    analysis = dict(first)
    analysis.update(
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "seal_sha256": seal_digest,
            "deterministic_replay": True,
        }
    )
    digest = _write_new_json(out_dir / "analysis.json", analysis)
    print(f"classification={analysis['classification']}", flush=True)
    print(f"analysis_sha256={digest}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
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
    if args.command == "prepare":
        prepare(args.seal)
    elif args.command == "execute":
        execute(args.seal, args.expected_sha256, args.out)
    else:
        analyse(args.seal, args.expected_sha256, args.out)


if __name__ == "__main__":
    main()
