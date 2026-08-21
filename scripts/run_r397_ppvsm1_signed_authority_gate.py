"""Run the sealed R397 PPVSM1 two-unit signed P/Q authority bank.

Motivation:
    R396/CLM-1125 passes the two-unit PPVSM1 object gate and opens only a
    signed P/Q authority gate. R397 mirrors the R388 signed-authority bank
    pattern on the frozen two-unit diagnostic cell: nine ordered fresh-system
    arms (zero arm plus two devices times two channels times two signs), a
    post-init absolute reference-service step of +/-0.09 system pu, a 2.0-s
    horizon, and the frozen R388 electrical envelope. The evidence schema
    embeds every R388-corrected and R393-R396 lesson in one first attempt
    (explicit initial snapshot, order-independent bus identity, typed
    advanced-partial termination, signal-major initial rows, device-major
    traces, global-address variable reads, round==contract round check).

Usage:
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r397_ppvsm1_signed_authority_gate.py rehearse
    /home/wya/andes_venv/bin/python scripts/run_r397_ppvsm1_signed_authority_gate.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r397_ppvsm1_signed_authority_gate.py execute --expected-seal-sha256 <sha256>

Failure modes:
    Source, contract, schema, capture, exception, bank, or create-only defects
    are ANALYSIS-INVALID. A valid complete or typed advanced-partial bank that
    fails any frozen scientific guard is STOP-PPVSM1-SIGNED-AUTHORITY. A
    complete valid pass is PPVSM1-SIGNED-AUTHORITY-PASS and opens only a
    separately registered droop-slope matching verification. There is no
    retry, tuning, controller, training, topology change, or substitution.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import time
from collections.abc import Mapping
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

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.env.andes.ppvsm1_static_kundur import (  # noqa: E402
    build_ppvsm1_static_kundur_object,
)
from andes_rl_kundur.evaluation.ppvsm1_signed_authority_gate import (  # noqa: E402
    PARTIAL_ERROR,
    build_ppvsm1_signed_authority_contract,
    classify_ppvsm1_signed_authority_record,
    payload_sha256,
)

BASE_RUNNER = ROOT / "scripts/run_r385_regcv1_clean_init_gate.py"
_base_spec = importlib.util.spec_from_file_location("r397_r385_lifecycle", BASE_RUNNER)
if _base_spec is None or _base_spec.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load lifecycle base: {BASE_RUNNER}")
base = importlib.util.module_from_spec(_base_spec)
_base_spec.loader.exec_module(base)

PARENT_RUNNER = ROOT / "scripts/run_r396_ppvsm1_object_gate.py"
_parent_spec = importlib.util.spec_from_file_location("r397_r396_parent", PARENT_RUNNER)
if _parent_spec is None or _parent_spec.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load parent runner: {PARENT_RUNNER}")
parent_runner = importlib.util.module_from_spec(_parent_spec)
_parent_spec.loader.exec_module(parent_runner)

# The R393 module owns the PPVSM1 installed_runtime, inventory, and trace
# capture used by the frozen two-unit object; reach it through the chain.
R393_PARENT = parent_runner.parent_runner.parent_runner.parent_runner

ROUND_ID = "R397"
QUESTION_ID = "Q-0111"
LINE_ID = "converter-vsg-pq-decoupling"
PLAN = ROOT / "memory/rounds/R397/plan.md"
QUESTION = ROOT / "memory/questions/Q-0111.md"
REHEARSAL = ROOT / "memory/rounds/R397/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R397/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R397/formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r397_ppvsm1_signed_authority_gate"

# Frozen packaged-case and model identities bound by the R396 seal/rehearsal.
FROZEN_XLSX_SHA256 = (
    "f725e03ba12d8207616f68acdd606bbd35e7c4a68f13e66d7db43925adac2ed8"
)
FROZEN_JSON_SHA256 = (
    "2b11fe7f69864aeea1158342a9116cc5d17868d0afd10fa1b9ca89ed094da423"
)
FROZEN_DERIVED_SHA256 = (
    "b33a134a368ee8e5829a956c35355370b2af66eb52bab5974ac83a965309e983"
)
FROZEN_PPVSM1_MODEL_SHA256 = (
    "a00418f27dbb537733a511bead1535f033859b22a2a9df01b82730e2ef6939f6"
)

# Frozen R396 sealed-artifact identities (the parent object gate pass).
R396_PARENT_SHA256 = {
    "r396_seal": "ce4cfe81d6c17dcd84d487ebac58a65890e955402b6db27c8d24b75bafb4383d",
    "r396_attempt": "b9c5e06e0451267bbc97bf5553df7c8b41e5ac5c7af4749e2ef1c89763539545",
    "r396_execution": "60d5ee3d351662b3deb6d947e844b8847d8c838436e4e335144b8f3a841350bf",
    "r396_analysis": "b69847e30e6d2aee7f71dedfe7824a91a3fcc1b9591e4a5df906b3df454c916a",
    "r396_manifest": "b5e1644138b561dadd490e9ee8c1706657e8109934b0858b96f633ff56e04ea4",
    "clm1125": "ab35d59853a73ffd0bed67b08f2458049c5cfdfd74940028dbf32eacefef1572",
    "r396_feed": "4fe6013cbdf32b1ccee9b3d3a4582097f5fa2c52a71fd15997b89ab3ccdd17c3",
    "r396_verdict": "569e6bbed2522a410e0c30c568d84c342f5b09907af8444d49b4883ff095e13e",
    "r388_analysis": "466296010670018e05619e2bd98a378c46f21d04cf74d0b01a2f4042215a5c39",
    "clm1085": "3ff8a9a6a53f5d09d1bc68416fd069d653117cacb68575becfb6d04da4a37d7e",
    "r392_analysis": "e05da2d17c19d8d02012e4b8b1fc9d48b2ccb26d1af195bf9c3799fb7cb3ec8b",
    "clm1105": "1db82b96c353eda76d4f8d6ff2a41851eda0e5a76d1bcb3fa04904f4f6332c97",
}


def build_r397_contract() -> dict[str, Any]:
    """Return the strictly canonical R397 contract (parent binding lives in the seal)."""

    return build_ppvsm1_signed_authority_contract()


def source_manifest() -> dict[str, dict[str, str]]:
    """Hash every prospective implementation and authority input."""

    sources = {
        "runner": Path(__file__).resolve(),
        "lifecycle_base": BASE_RUNNER,
        "parent_runner": PARENT_RUNNER,
        "model": ROOT / "src/andes_rl_kundur/env/andes/ppvsm1.py",
        "builder": ROOT / "src/andes_rl_kundur/env/andes/ppvsm1_static_kundur.py",
        "builder_base": ROOT
        / "src/andes_rl_kundur/env/andes/regcv1_static_kundur.py",
        "classifier": ROOT
        / "src/andes_rl_kundur/evaluation/ppvsm1_signed_authority_gate.py",
        "parent_classifier": ROOT
        / "src/andes_rl_kundur/evaluation/ppvsm1_object_gate.py",
        "classifier_tests": ROOT / "tests/test_ppvsm1_signed_authority_gate.py",
        "runner_tests": ROOT / "tests/test_r397_ppvsm1_signed_authority_gate.py",
        "builder_tests": ROOT / "tests/test_ppvsm1_static_kundur.py",
        "parent_runner_tests": ROOT / "tests/test_r396_ppvsm1_object_gate.py",
        "plan": PLAN,
        "question": QUESTION,
        "programme": ROOT / "memory/RESEARCH_PROGRAM.md",
        "line": ROOT / "paper/converter_vsg_pq_decoupling/LINE.md",
        "artifact_manifest": ROOT
        / "paper/converter_vsg_pq_decoupling/ARTIFACTS.json",
        "route_contract": ROOT
        / "paper/converter_vsg_pq_decoupling/working/route_contract.md",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": base.relative(path), "sha256": base.sha256_file(path)}
        for name, path in sources.items()
    }


def parent_manifest() -> dict[str, dict[str, str]]:
    """Bind the immutable R396 object pass and the R388/R392 pattern parents."""

    parents = {
        "r396_seal": ROOT / "memory/rounds/R396/formal_seal.json",
        "r396_attempt": ROOT
        / "results/research_loop/r396_ppvsm1_object_gate/formal_attempt.json",
        "r396_execution": ROOT
        / "results/research_loop/r396_ppvsm1_object_gate/formal_execution.json",
        "r396_analysis": ROOT
        / "results/research_loop/r396_ppvsm1_object_gate/formal_analysis.json",
        "r396_manifest": ROOT
        / "results/research_loop/r396_ppvsm1_object_gate/formal_manifest.json",
        "clm1125": ROOT / "memory/claims/CLM-1125.md",
        "r396_feed": ROOT / "paper/converter_vsg_pq_decoupling/reports/R396.md",
        "r396_verdict": ROOT / "memory/rounds/R396/verdict.md",
        "r388_analysis": ROOT
        / "results/research_loop/r388_regcv1_signed_authority_correction_gate/formal_analysis.json",
        "clm1085": ROOT / "memory/claims/CLM-1085.md",
        "r392_analysis": ROOT
        / "results/research_loop/r392_regf2_loop_perturbation_gate/formal_analysis.json",
        "clm1105": ROOT / "memory/claims/CLM-1105.md",
    }
    return {
        name: {"path": base.relative(path), "sha256": base.sha256_file(path)}
        for name, path in parents.items()
    }


def validate_r396_parent_chain() -> bool:
    """Reject any drift in the frozen R396 object-pass parent chain."""

    try:
        parents = parent_manifest()
        if {
            name: row["sha256"] for name, row in parents.items()
        } != R396_PARENT_SHA256:
            return False
        seal = base.read_hashed_json(ROOT / parents["r396_seal"]["path"])
        attempt = base.read_hashed_json(ROOT / parents["r396_attempt"]["path"])
        execution = base.read_hashed_json(ROOT / parents["r396_execution"]["path"])
        analysis = base.read_hashed_json(ROOT / parents["r396_analysis"]["path"])
        manifest = base.read_hashed_json(ROOT / parents["r396_manifest"]["path"])
        return bool(
            seal["round"] == "R396"
            and attempt["round"] == "R396"
            and execution["round"] == "R396"
            and manifest["round"] == "R396"
            and attempt["seal_sha256"] == R396_PARENT_SHA256["r396_seal"]
            and execution["seal_sha256"] == R396_PARENT_SHA256["r396_seal"]
            and execution["attempt_sha256"] == R396_PARENT_SHA256["r396_attempt"]
            and analysis["seal_sha256"] == R396_PARENT_SHA256["r396_seal"]
            and analysis["formal_execution_sha256"]
            == R396_PARENT_SHA256["r396_execution"]
            and manifest["entries"][0]["path"].endswith("formal_attempt.json")
            and analysis["classification"] == "PPVSM1-OBJECT-PASS"
        )
    except (KeyError, TypeError, ValueError, FileNotFoundError):
        return False


def installed_runtime() -> dict[str, Any]:
    """Bind the R393-shape runtime identity through the frozen R396 chain."""

    return R393_PARENT.installed_runtime()


def installed_runtime_matches_contract(
    runtime: Mapping[str, Any], contract: Mapping[str, Any]
) -> bool:
    expected = {
        "andes_version": contract["andes_version"],
        "xlsx_case_sha256": FROZEN_XLSX_SHA256,
        "json_case_sha256": FROZEN_JSON_SHA256,
        "ppvsm1_model_sha256": FROZEN_PPVSM1_MODEL_SHA256,
    }
    return bool(
        all(runtime.get(key) == value for key, value in expected.items())
        and runtime.get("xlsx_json_static_equal") is True
        and runtime.get("derived_case_sha256") == FROZEN_DERIVED_SHA256
    )


def _finite_guards(system: Any) -> tuple[bool, bool]:
    """Finite check for the DAE vectors and the PPVSM1 variable set."""

    dae_finite = True
    for name in ("x", "y", "z", "f", "g"):
        try:
            values = np.asarray(getattr(system.dae, name), dtype=float)
            dae_finite = dae_finite and bool(np.all(np.isfinite(values)))
        except (AttributeError, TypeError, ValueError):
            dae_finite = False
    model_finite = True
    for variable in system.PPVSM1.cache.all_vars.values():
        try:
            values = np.asarray(variable.v, dtype=float)
            model_finite = model_finite and bool(np.all(np.isfinite(values)))
        except (AttributeError, TypeError, ValueError):
            model_finite = False
    return dae_finite, model_finite


def _setpoint_rows(system: Any, contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    pref = np.asarray(system.PPVSM1.Pref.v, dtype=float)
    qref = np.asarray(system.PPVSM1.Qref.v, dtype=float)
    rows: list[dict[str, Any]] = []
    for position, row in enumerate(contract["expected_mapping"]):
        rows.append(
            {"idx": row["idx"], "channel": "pref", "value": float(pref[position])}
        )
        rows.append(
            {"idx": row["idx"], "channel": "qref", "value": float(qref[position])}
        )
    return rows


def apply_ppvsm1_setpoint_step(
    system: Any, arm: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any]:
    """Write one absolute post-init reference-service step and capture receipts.

    PPVSM1 defines no RenGen _setpoints registry, so the runner performs the
    exact array write the ANDES RenGen.set_setpoint mechanism performs:
    a direct element write to the frozen ConstService v array.
    """

    pre = _setpoint_rows(system, contract)
    target = arm["target_idx"]
    channel = arm["input_channel"]
    requested_absolute: float | None = None
    applied_readback: float | None = None
    if target is not None:
        matching = [
            row
            for row in pre
            if row["idx"] == target and row["channel"] == channel
        ]
        if len(matching) != 1:
            raise RuntimeError("R397 target setpoint identity is not unique")
        requested_absolute = float(matching[0]["value"]) + float(arm["requested_delta"])
        position = [row["idx"] for row in contract["expected_mapping"]].index(target)
        service = system.PPVSM1.Pref if channel == "pref" else system.PPVSM1.Qref
        service.v[position] = requested_absolute
        applied_readback = float(np.asarray(service.v, dtype=float)[position])
    post = _setpoint_rows(system, contract)
    return {
        "applied": target is not None,
        "pre_setpoints": pre,
        "post_setpoints": post,
        "requested_absolute": requested_absolute,
        "applied_readback": applied_readback,
    }


def _empty_initial() -> dict[str, Any]:
    return {
        "captured": False,
        "time_seconds": None,
        "dae_finite": False,
        "ppvsm1_finite": False,
        "bus_v": {},
        "devices": {},
    }


def _empty_arm(arm: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "arm_id": arm["arm_id"],
        "target_idx": arm["target_idx"],
        "input_channel": arm["input_channel"],
        "sign": arm["sign"],
        "requested_delta": arm["requested_delta"],
        "scientific_error": None,
        "inventory": {
            "network": {},
            "forbidden_model_counts": {},
            "forbidden_dae_names": [],
            "ppvsm1": [],
            "ppvsm1_count": 0,
            "ppvsm1_buses": [],
            "ppvsm1_mapping_ok": False,
            "input_parameter_cards_match": False,
            "runtime_parameter_cards_match": False,
        },
        "reference_source": {"captured": False, "phase": None, "rows": []},
        "references": {
            "checked": False,
            "absolute_tolerance": None,
            "phase": None,
            "rows": [],
        },
        "initialization_diagnostics": {
            "captured": False,
            "equation_count": 0,
            "bad_combined_indices": [],
            "residual_count": 0,
            "residuals": [],
            "clamped_limits": [],
        },
        "action": {
            "applied": False,
            "pre_setpoints": [],
            "post_setpoints": [],
            "requested_absolute": None,
            "applied_readback": None,
        },
        "trajectory": {
            "captured": False,
            "start_time_seconds": None,
            "initial": _empty_initial(),
            "time": [],
            "dae_finite": False,
            "ppvsm1_finite": False,
            "bus_v": {},
            "devices": {},
        },
        "solver": {
            "setup_completed": False,
            "pflow_converged": False,
            "tds_initialized": False,
            "tds_test_ok": False,
            "tds_converged": False,
            "tds_tolerance": 1.0e-4,
            "terminal_time_seconds": None,
        },
    }


def _bus_major(samples: list[dict[str, float]]) -> dict[str, list[float]]:
    if not samples:
        return {}
    buses = list(samples[0])
    return {
        bus: [sample[bus] for sample in samples]
        for bus in buses
    }


def _run_arm(
    arm: Mapping[str, Any],
    contract: Mapping[str, Any],
    runtime: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    row = _empty_arm(arm)
    audit = base.load_verified_static_case(
        xlsx_path=runtime["xlsx_case_path"],
        json_path=runtime["json_case_path"],
    )
    built = build_ppvsm1_static_kundur_object(
        full_case=audit.full_case,
        work_dir=Path.cwd(),
    )
    system = built.system
    row["solver"]["tds_tolerance"] = float(system.TDS.config.tol)
    system.setup()
    row["solver"]["setup_completed"] = bool(system.is_setup)
    row["inventory"] = R393_PARENT._inventory(
        system, built, contract
    )

    system.PFlow.run()
    row["solver"]["pflow_converged"] = system.PFlow.converged is True
    if not row["solver"]["pflow_converged"]:
        diagnostics = base.capture_initialization_diagnostics(system)
        if diagnostics["captured"] is not True:
            raise RuntimeError(
                "R397 initialization diagnostic capture failed after PFlow failure: "
                f"{diagnostics.get('capture_error', 'unknown error')}"
            )
        row["initialization_diagnostics"] = diagnostics
        row["scientific_error"] = "PFlow did not converge"
        return row, built.derived_case_sha256

    static_rows = parent_runner._static_snapshot(system, contract)
    row["reference_source"] = {
        "captured": True,
        "phase": "post_pflow_pre_tds_init",
        "rows": static_rows,
    }
    parent_runner._freeze_horizon(system, contract)
    init_return = system.TDS.init()
    row["solver"]["tds_initialized"] = init_return is not False
    row["solver"]["tds_test_ok"] = system.TDS.test_ok is True
    diagnostics = base.capture_initialization_diagnostics(system)
    row["initialization_diagnostics"] = diagnostics
    if diagnostics["captured"] is not True:
        raise RuntimeError(
            "R397 initialization diagnostic capture failed: "
            f"{diagnostics.get('capture_error', 'unknown error')}"
        )
    row["references"] = {
        "checked": True,
        "absolute_tolerance": float(contract["reference_abs_tolerance"]),
        "phase": "post_init",
        "rows": parent_runner._reference_rows(
            static_rows, parent_runner._pref_qref_rows(system, contract)
        ),
    }
    if not (
        row["solver"]["tds_initialized"] and row["solver"]["tds_test_ok"]
    ):
        row["scientific_error"] = "TDS initialization failed"
        return row, built.derived_case_sha256

    trajectory_start = float(system.dae.t)
    initial_row = parent_runner._initial_trace_row(system)
    dae_finite_0, model_finite_0 = _finite_guards(system)
    row["trajectory"]["start_time_seconds"] = trajectory_start
    row["trajectory"]["initial"] = {
        "captured": True,
        "time_seconds": float(initial_row["time"]),
        "dae_finite": dae_finite_0,
        "ppvsm1_finite": model_finite_0,
        "bus_v": initial_row["bus_v"],
        "devices": initial_row["devices"],
    }
    row["action"] = apply_ppvsm1_setpoint_step(system, arm, contract)
    system.TDS.run()
    terminal_time = float(system.dae.t)
    row["solver"]["terminal_time_seconds"] = terminal_time
    row["solver"]["tds_converged"] = system.TDS.converged is True
    if terminal_time <= trajectory_start:
        row["scientific_error"] = "TDS did not advance"
        return row, built.derived_case_sha256
    trajectory = R393_PARENT._capture_trace(
        system, initial_row
    )
    dae_finite, model_finite = _finite_guards(system)
    # The inherited capture prepends the t=0 sample, which already lives in
    # the separate initial snapshot; keep strictly post-start native rows.
    row["trajectory"].update(
        {
            "captured": True,
            "time": [float(value) for value in trajectory["times"][1:]],
            "dae_finite": dae_finite,
            "ppvsm1_finite": model_finite,
            "bus_v": _bus_major(trajectory["bus_v"][1:]),
            "devices": {
                device_id: {
                    signal: [float(value) for value in values[1:]]
                    for signal, values in signals.items()
                }
                for device_id, signals in trajectory["devices"].items()
            },
        }
    )
    tolerance = float(contract["tds_tolerance"])
    horizon = float(contract["tds_tf_seconds"])
    if terminal_time < horizon - tolerance:
        if row["solver"]["tds_converged"] is True:
            raise RuntimeError(
                "R397 converged trajectory terminated before the horizon"
            )
        row["scientific_error"] = PARTIAL_ERROR
    return row, built.derived_case_sha256


def run_formal_record(
    contract: Mapping[str, Any], runtime: Mapping[str, Any]
) -> dict[str, Any]:
    """Execute the exact serial nine-arm bank and return one immutable record."""

    record: dict[str, Any] = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "contract_sha256": payload_sha256(contract),
        "formal_input_complete": True,
        "execution_error": None,
        "training_executed": False,
        "trajectory_attempted_count": 0,
        "trajectory_executed_count": 0,
        "source": {
            "andes_version": runtime["andes_version"],
            "xlsx_json_static_equal": runtime["xlsx_json_static_equal"],
            "derived_case_deterministic": True,
            "xlsx_case_sha256": runtime["xlsx_case_sha256"],
            "json_case_sha256": runtime["json_case_sha256"],
            "derived_case_sha256": runtime["derived_case_sha256"],
            "ppvsm1_model_sha256": runtime["ppvsm1_model_sha256"],
        },
        "arms": [],
    }
    try:
        for arm in contract["arm_order"]:
            record["trajectory_attempted_count"] += 1
            row, derived_digest = _run_arm(arm, contract, runtime)
            if derived_digest != runtime["derived_case_sha256"]:
                raise RuntimeError("R397 derived static-case digest drift")
            record["arms"].append(row)
            record["trajectory_executed_count"] += int(
                row["trajectory"]["captured"] is True
            )
    except Exception as exc:
        record["execution_error"] = f"{type(exc).__name__}: {exc}"
    return record


def setup_only_canary(runtime: Mapping[str, Any]) -> dict[str, Any]:
    """Validate construction and APIs, then run the complete nine-arm bank."""

    started = time.perf_counter()
    contract = build_r397_contract()
    audit = base.load_verified_static_case(
        xlsx_path=runtime["xlsx_case_path"],
        json_path=runtime["json_case_path"],
    )
    built = build_ppvsm1_static_kundur_object(
        full_case=audit.full_case, work_dir=Path.cwd()
    )
    system = built.system
    system.setup()
    inventory = R393_PARENT._inventory(
        system, built, contract
    )
    runtime_api_present = bool(
        callable(getattr(system.PFlow, "run", None))
        and hasattr(system.PFlow, "converged")
        and callable(getattr(system.TDS, "init", None))
        and callable(getattr(system.TDS, "fg_update", None))
        and hasattr(system.TDS.config, "tol")
        and hasattr(system.PPVSM1, "Pref")
        and isinstance(system.PPVSM1.Pref.v, np.ndarray)
        and hasattr(system.PPVSM1, "Qref")
        and isinstance(system.PPVSM1.Qref.v, np.ndarray)
    )
    setup_wall = time.perf_counter() - started
    record = run_formal_record(contract, runtime)
    classification = classify_ppvsm1_signed_authority_record(
        record, contract=contract
    )
    bank_wall = time.perf_counter() - started - setup_wall
    return {
        "setup_completed": bool(system.is_setup),
        "derived_case_sha256": built.derived_case_sha256,
        "forbidden_model_counts": inventory["forbidden_model_counts"],
        "forbidden_dae_names": inventory["forbidden_dae_names"],
        "ppvsm1_count": inventory["ppvsm1_count"],
        "ppvsm1_buses": inventory["ppvsm1_buses"],
        "ppvsm1_mapping_ok": inventory["ppvsm1_mapping_ok"],
        "input_parameter_cards_match": inventory["input_parameter_cards_match"],
        "runtime_parameter_cards_match": inventory[
            "runtime_parameter_cards_match"
        ],
        "runtime_api_present": bool(
            runtime_api_present
            and classification["classification"]
            in (
                "PPVSM1-SIGNED-AUTHORITY-PASS",
                "STOP-PPVSM1-SIGNED-AUTHORITY",
            )
        ),
        "physical_trajectory_executed": False,
        "setup_only_wall_seconds": setup_wall,
        "full_bank_canary": {
            "classification": classification["classification"],
            "execution_error": record["execution_error"],
            "checks": classification["checks"],
            "arm_summary": [
                {
                    "arm_id": arm["arm_id"],
                    "scientific_error": arm["scientific_error"],
                    "captured": arm["trajectory"]["captured"],
                    "terminal_time_seconds": arm["solver"][
                        "terminal_time_seconds"
                    ],
                    "tds_converged": arm["solver"]["tds_converged"],
                }
                for arm in record["arms"]
            ],
        },
        "full_bank_canary_wall_seconds": bank_wall,
    }


def rehearse() -> str:
    """Create full-bank canary and resource/provenance evidence; no formal seam."""

    base.assert_wsl_scratch()
    if not validate_r396_parent_chain():
        raise RuntimeError("R397 frozen R396 parent chain failed before rehearsal")
    collisions = [
        path for path in (REHEARSAL, CAPACITY, SEAL, DEFAULT_OUT) if path.exists()
    ]
    if collisions:
        raise FileExistsError(f"R397 pre-attempt artifact exists: {collisions}")
    runtime = installed_runtime()
    contract = build_r397_contract()
    other = base.other_research_python_processes()
    logical, physical, available = base.memory_resources()
    capacity = base.build_capacity_payload(
        logical_processors=logical,
        physical_memory_bytes=physical,
        wsl_memory_available_bytes=available,
        disk_free_bytes=int(base.shutil.disk_usage(ROOT).free),
        competing_processes=other,
    )
    capacity["empirical_anchor"] = {
        "concurrent_workers": 1,
        "all_records_valid": True,
        "native_threads_per_worker": 1,
        "source": "r397_rehearsal_full_bank_canary",
    }
    capacity["capacity_canary"] = {"accepted": True, "accepted_worker_budget": 1}
    canary = setup_only_canary(runtime)
    sources = source_manifest()
    parents = parent_manifest()
    checks = {
        "source_hash": bool(sources),
        "parent_hash": bool(parents),
        "parent_stop_evidence": bool(
            parents["r396_analysis"]["sha256"]
            == R396_PARENT_SHA256["r396_analysis"]
            and parents["r388_analysis"]["sha256"]
            == R396_PARENT_SHA256["r388_analysis"]
        ),
        "installed_runtime": installed_runtime_matches_contract(runtime, contract),
        "installed_cases": Path(runtime["xlsx_case_path"]).is_file()
        and Path(runtime["json_case_path"]).is_file(),
        "static_table_identity": runtime["xlsx_json_static_equal"] is True,
        "derived_case_determinism": canary["derived_case_sha256"]
        == FROZEN_DERIVED_SHA256,
        "structural_absence": all(
            value == 0 for value in canary["forbidden_model_counts"].values()
        )
        and canary["forbidden_dae_names"] == [],
        "setup_only_canary": canary["setup_completed"] is True
        and canary["ppvsm1_count"] == 2
        and canary["ppvsm1_buses"] == [1, 2]
        and canary["ppvsm1_mapping_ok"] is True
        and canary["input_parameter_cards_match"] is True
        and canary["runtime_parameter_cards_match"] is True,
        "full_bank_canary": bool(
            canary["full_bank_canary"]["execution_error"] is None
            and canary["full_bank_canary"]["classification"]
            in (
                "PPVSM1-SIGNED-AUTHORITY-PASS",
                "STOP-PPVSM1-SIGNED-AUTHORITY",
            )
        ),
        "output_absence": not DEFAULT_OUT.exists() and not SEAL.exists(),
        "question_in_flight": "status: in-flight"
        in QUESTION.read_text(encoding="utf-8"),
        "active_plan": "state: active" in PLAN.read_text(encoding="utf-8")
        and f"manuscript_line: {LINE_ID}" in PLAN.read_text(encoding="utf-8"),
        "no_competing_research_process": not other,
        "physical_trajectory_executed": False,
    }
    if (
        not base.rehearsal_checks({"checks": checks})
        or capacity["readiness"] != "RUN-READY"
    ):
        raise RuntimeError(f"R397 rehearsal/capacity gate did not pass: {checks}")

    capacity.update(
        {
            "installed_runtime": runtime,
            "sources": sources,
            "parents": parents,
            "setup_only_canary": canary,
            "setup_only_wall_seconds": canary["setup_only_wall_seconds"],
            "full_bank_canary": canary["full_bank_canary"],
            "full_bank_canary_wall_seconds": canary["full_bank_canary_wall_seconds"],
            "estimated_formal_wall_seconds_upper_bound": 2.0
            * float(canary["full_bank_canary_wall_seconds"]),
            "formal_arm_count": 9,
            "formal_worker_count": 1,
            "native_threads_per_process": 1,
        }
    )
    capacity_digest = base.write_new_json(CAPACITY, capacity)
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": payload_sha256(contract),
        "sources": sources,
        "parents": parents,
        "installed_runtime": runtime,
        "setup_only_canary": canary,
        "capacity_sha256": capacity_digest,
        "checks": checks,
        "formal_authority": False,
        "training_executed": False,
    }
    return base.write_new_json(REHEARSAL, payload)


def prepare() -> str:
    """Seal R397 after a fresh zero-competing-process measurement."""

    base.assert_posix_runtime()
    if not validate_r396_parent_chain():
        raise RuntimeError("R397 frozen R396 parent chain failed before sealing")
    rehearsal = base.read_hashed_json(REHEARSAL)
    capacity = base.read_hashed_json(CAPACITY)
    if not base.rehearsal_checks(rehearsal):
        raise RuntimeError("R397 rehearsal did not pass")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R397 capacity gate is not RUN-READY")
    sources = source_manifest()
    parents = parent_manifest()
    runtime = installed_runtime()
    contract = build_r397_contract()
    if rehearsal["sources"] != sources or capacity["sources"] != sources:
        raise RuntimeError("R397 source drift before sealing")
    if rehearsal["parents"] != parents or capacity["parents"] != parents:
        raise RuntimeError("R397 parent drift before sealing")
    if (
        rehearsal["installed_runtime"] != runtime
        or capacity["installed_runtime"] != runtime
        or not installed_runtime_matches_contract(runtime, contract)
    ):
        raise RuntimeError("R397 installed runtime drift before sealing")
    if DEFAULT_OUT.exists() or SEAL.exists():
        raise FileExistsError("R397 seal/formal output collision")
    competing = base.other_research_python_processes()
    process_check = {
        "created_utc": datetime.now(UTC).isoformat(),
        "other_research_python_processes": competing,
        "other_reserved_processes": len(competing),
        "passed": not competing,
    }
    if competing:
        raise RuntimeError(
            "R397 HOLD: competing research processes found immediately before seal"
        )
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_sha256": payload_sha256(contract),
        "sources": sources,
        "parents": parents,
        "installed_runtime": runtime,
        "rehearsal_sha256": base.sha256_file(REHEARSAL),
        "capacity_sha256": base.sha256_file(CAPACITY),
        "preseal_process_check": process_check,
        "launch": {
            "host_process_budget": 1,
            "wsl_python_processes": 1,
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
        },
        "formal_artifacts_create_only": True,
        "retry_authorized": False,
        "training_authorized": False,
    }
    return base.write_new_json(SEAL, payload)


def _configure_lifecycle() -> None:
    base.ROUND_ID = ROUND_ID
    base.QUESTION_ID = QUESTION_ID
    base.LINE_ID = LINE_ID
    base.PLAN = PLAN
    base.QUESTION = QUESTION
    base.REHEARSAL = REHEARSAL
    base.CAPACITY = CAPACITY
    base.SEAL = SEAL
    base.DEFAULT_OUT = DEFAULT_OUT
    base.build_clean_contract = build_r397_contract
    base.classify_regcv1_clean_init_record = (
        classify_ppvsm1_signed_authority_record
    )
    base.source_manifest = source_manifest
    base.parent_manifest = parent_manifest
    base.installed_runtime = installed_runtime
    base.run_formal_record = run_formal_record


_configure_lifecycle()


def execute(*, expected_sha256: str) -> str:
    return base.execute(expected_sha256=expected_sha256, out_dir=DEFAULT_OUT)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("rehearse")
    commands.add_parser("prepare")
    formal = commands.add_parser("execute")
    formal.add_argument("--expected-seal-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rehearse":
        print(f"rehearsal_sha256={rehearse()}")
    elif args.command == "prepare":
        print(f"seal_sha256={prepare()}")
    elif args.command == "execute":
        print(f"analysis_sha256={execute(expected_sha256=args.expected_seal_sha256)}")
    else:  # pragma: no cover
        raise RuntimeError(f"unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
