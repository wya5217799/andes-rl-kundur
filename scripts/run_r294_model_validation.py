#!/usr/bin/env python3
"""Seal, execute, and analyse R294 Stage-A non-learning model validation.

Usage (prepare/analyse use ordinary project Python; run uses WSL ANDES):
    python scripts/run_r294_model_validation.py prepare
    python scripts/andes_scratch.py scripts/run_r294_model_validation.py run \
      --expected-seal-sha256 HASH --shard-index 0 --shard-count 3
    python scripts/run_r294_model_validation.py analyse \
      --expected-seal-sha256 HASH

The 16 LPV corners, one fixed-LTI anchor, eight held-out points, metrics, and
decision thresholds are frozen into a create-only seal before ANDES executes.
Retained failed records are never retried or filtered.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.model_validation import (  # noqa: E402
    compare_coordinate_responses,
    compare_modes,
    coordinate_response,
    model_point_passes,
    multilinear_interpolate,
    participation_mode,
)

ROUND_ID = "R294"
QUESTION_ID = "Q-0051"
STAGE = "stage_a_equilibrium_modal_coupling"
SHARD_COUNT = 3
DEFAULT_SEAL = ROOT / "memory/rounds/R294/model_validation_stage_a_seal.json"
DEFAULT_OUT = ROOT / "results/r294_model_validation/stage_a"
PLAN = ROOT / "memory/rounds/R294/plan.md"
PURE_MODULE = ROOT / "src/andes_rl_kundur/evaluation/model_validation.py"
ENV_SOURCE = ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py"
STORAGE_SOURCE = ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py"
ACTIVE_POWER_SOURCE = ROOT / "src/andes_rl_kundur/control/active_power.py"

AXIS_ORDER = ("m_scale", "d_scale", "tie_k", "soc")
BOUNDS = {
    "m_scale": (0.75, 1.25),
    "d_scale": (0.75, 1.25),
    "tie_k": (1.0, 2.0),
    "soc": (0.3, 0.7),
}
FIXED_ANCHOR = {
    "name": "fixed_lti_anchor",
    "role": "fixed_anchor",
    "m_scale": 1.0,
    "d_scale": 1.0,
    "tie_k": 1.0,
    "soc": 0.5,
}
HOLDOUTS = (
    {"name": "centre", "m_scale": 1.0, "d_scale": 1.0, "tie_k": 1.5, "soc": 0.5},
    {"name": "low_interior", "m_scale": 0.875, "d_scale": 0.875, "tie_k": 1.25, "soc": 0.4},
    {"name": "high_interior", "m_scale": 1.125, "d_scale": 1.125, "tie_k": 1.75, "soc": 0.6},
    {"name": "cross_low_m_high_d", "m_scale": 0.875, "d_scale": 1.125, "tie_k": 1.75, "soc": 0.4},
    {"name": "cross_high_m_low_d", "m_scale": 1.125, "d_scale": 0.875, "tie_k": 1.25, "soc": 0.6},
    {"name": "m_lower_face", "m_scale": 0.75, "d_scale": 1.0, "tie_k": 1.5, "soc": 0.5},
    {"name": "d_upper_face", "m_scale": 1.0, "d_scale": 1.25, "tie_k": 1.5, "soc": 0.5},
    {"name": "soc_lower_face", "m_scale": 1.0, "d_scale": 1.0, "tie_k": 1.5, "soc": 0.3},
)
THRESHOLDS = {
    "positive_real_tolerance": 1e-7,
    "mode_frequency_relative_error_max": 0.05,
    "mode_damping_absolute_error_max": 0.01,
    "participation_cosine_min": 0.90,
    "coordinate_response_nrmse_max": 0.15,
    "coupling_ratio_absolute_error_max": 0.05,
    "hard_decoupling_cross_self_ratio_max": 0.20,
    "approximately_decoupled_cross_self_ratio_max": 0.05,
    "eigenvector_condition_number_max": 1e12,
}
RESPONSE = {"horizon_seconds": 10.0, "sample_count": 201}
FREQUENCY_BAND_HZ = (0.2, 1.5)
AREA_1_KEYS = ("genrou1", "genrou2", "vsg12", "vsg16")
AREA_2_KEYS = ("genrou3", "genrou4", "vsg14", "vsg15")
TIE_IDX = ("Line_4", "Line_5", "Line_6")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_new(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.with_suffix(path.suffix + ".sha256").exists():
        raise FileExistsError(f"create-only artifact already exists: {path}")
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as handle:
        handle.write(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    with path.with_suffix(path.suffix + ".sha256").open("x", encoding="ascii") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def _verify_sidecar(path: Path) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"missing or empty artifact: {path}")
    if not sidecar.is_file() or sidecar.stat().st_size == 0:
        raise RuntimeError(f"missing or empty sidecar: {sidecar}")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    observed = sha256_file(path)
    if expected != observed:
        raise RuntimeError(f"sidecar mismatch for {path}: {expected} != {observed}")
    return observed


def _source_entry(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}


def _training_points() -> list[dict[str, Any]]:
    points = []
    for values in itertools.product(*(BOUNDS[axis] for axis in AXIS_ORDER)):
        point = dict(zip(AXIS_ORDER, values, strict=True))
        name = "corner__" + "__".join(f"{axis}_{value:g}" for axis, value in point.items())
        points.append({"name": name, "role": "lpv_corner", **point})
    return points


def operating_bank() -> list[dict[str, Any]]:
    holdouts = [{"role": "holdout", **point} for point in HOLDOUTS]
    points = [*_training_points(), dict(FIXED_ANCHOR), *holdouts]
    for index, point in enumerate(points):
        point["order"] = index
    names = [point["name"] for point in points]
    if len(names) != len(set(names)):
        raise RuntimeError("operating-point names are not unique")
    return points


def _seal_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "plant": {
            "class": "AndesMultiVSGEnvV4Storage",
            "truth": "full nonlinear ANDES DAE linearized at each operating point",
            "vsg_m_base": [200.0] * 4,
            "vsg_d_base": [100.0] * 4,
            "bess_soc_schedule": "all four ESD1 SOCinit parameters",
            "tie_schedule": "Line_4/5/6 r and x multiplied by tie_k via Model.set",
            "toggler": "disabled by environment variable before plant build",
        },
        "models": {
            "fixed_lti": "state matrix at fixed_lti_anchor",
            "descriptor_lpv": "four-axis multilinear interpolation of the 16 corner state matrices",
        },
        "axis_order": list(AXIS_ORDER),
        "bounds": {key: list(value) for key, value in BOUNDS.items()},
        "operating_bank": operating_bank(),
        "frequency_band_hz": list(FREQUENCY_BAND_HZ),
        "area_1_keys": list(AREA_1_KEYS),
        "area_2_keys": list(AREA_2_KEYS),
        "response": RESPONSE,
        "thresholds": THRESHOLDS,
        "decision_tree": [
            "any execution guard failure -> INVALID-STAGE-A-EXECUTION",
            "all LPV holdouts pass -> STAGE-A-DESCRIPTOR-LPV-ELIGIBLE",
            "otherwise -> STAGE-A-NONLINEAR-OR-NARROWER-DOMAIN-REQUIRED",
            "truth max cross/self > 0.20 -> DECOUPLING-NO-GO",
            "truth max cross/self in (0.05,0.20] -> RETAIN-CROSS-BLOCKS",
            "truth max cross/self <= 0.05 -> APPROXIMATE-DECOUPLING-ELIGIBLE",
        ],
        "claim_boundary": (
            "Stage A tests local equilibrium/modal/coupling fidelity only; it does not "
            "validate nonlinear prediction, actuator authority, a controller, MARL, or deployment."
        ),
        "shard_count": SHARD_COUNT,
        "sources": {
            "plan": _source_entry(PLAN),
            "runner": _source_entry(Path(__file__).resolve()),
            "pure_module": _source_entry(PURE_MODULE),
            "environment": _source_entry(ENV_SOURCE),
            "storage_environment": _source_entry(STORAGE_SOURCE),
            "active_power_contract": _source_entry(ACTIVE_POWER_SOURCE),
        },
    }


def prepare(seal_path: Path, out_dir: Path) -> None:
    payload = _seal_payload()
    digest = _write_new(seal_path, payload)
    (out_dir / "records").mkdir(parents=True, exist_ok=True)
    print(f"seal_sha256={digest}")
    print(f"points={len(payload['operating_bank'])} shards={SHARD_COUNT}")


def _verify_seal(seal_path: Path, expected_sha256: str) -> dict[str, Any]:
    observed = _verify_sidecar(seal_path)
    if observed != expected_sha256:
        raise RuntimeError(f"seal hash mismatch: {expected_sha256} != {observed}")
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    for name, entry in seal["sources"].items():
        source = ROOT / entry["path"]
        current = sha256_file(source)
        if current != entry["sha256"]:
            raise RuntimeError(f"sealed source drift for {name}: {entry['sha256']} != {current}")
    return seal


def _simple(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    return None


def _max_abs(values: Any) -> float | None:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return None
    finite = np.abs(array[np.isfinite(array)])
    return None if finite.size == 0 else float(np.max(finite))


def _reduced_state_index(ss: Any, original_address: int) -> int:
    name = str(ss.dae.x_name[int(original_address)])
    names = [str(value) for value in ss.EIG.x_name]
    matches = [index for index, value in enumerate(names) if value == name]
    if len(matches) != 1:
        raise RuntimeError(f"state name {name!r} has {len(matches)} reduced matches")
    return matches[0]


def _state_maps(ss: Any, env: Any) -> tuple[dict[str, int], list[int]]:
    machine: dict[str, int] = {}
    for position, idx in enumerate(ss.GENROU.idx.v):
        if int(idx) <= 4:
            machine[f"genrou{int(idx)}"] = _reduced_state_index(
                ss, int(ss.GENROU.omega.a[position])
            )
    gencls_indices = list(ss.GENCLS.idx.v)
    gencls_buses = list(ss.GENCLS.bus.v)
    vsg_omega: list[int] = []
    for idx in env.vsg_idx:
        position = gencls_indices.index(idx)
        reduced = _reduced_state_index(ss, int(ss.GENCLS.omega.a[position]))
        machine[f"vsg{int(gencls_buses[position])}"] = reduced
        vsg_omega.append(reduced)
    required = set(AREA_1_KEYS) | set(AREA_2_KEYS)
    if set(machine) != required:
        raise RuntimeError(f"machine-state map mismatch: {sorted(machine)} != {sorted(required)}")
    return machine, vsg_omega


def _run_point(point: dict[str, Any], seal_hash: str) -> dict[str, Any]:
    os.environ["DISABLE_TOGGLER"] = "1"
    import andes

    from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
        AndesMultiVSGEnvV4Storage,
    )

    env = AndesMultiVSGEnvV4Storage(random_disturbance=False, comm_fail_prob=0.0)
    ss = env._build_system()
    m_values = [float(value * point["m_scale"]) for value in env.M0]
    d_values = [float(value * point["d_scale"]) for value in env.D0_HETEROGENEOUS]
    for idx, value in zip(env.vsg_idx, m_values, strict=True):
        ss.GENCLS.set("M", idx, value, attr="v")
    for idx, value in zip(env.vsg_idx, d_values, strict=True):
        ss.GENCLS.set("D", idx, value, attr="v")
    tie_detail: dict[str, dict[str, float]] = {}
    for idx in TIE_IDX:
        line_position = list(ss.Line.idx.v).index(idx)
        new_r = float(ss.Line.r.v[line_position] * point["tie_k"])
        new_x = float(ss.Line.x.v[line_position] * point["tie_k"])
        ss.Line.set("r", idx, new_r, attr="v")
        ss.Line.set("x", idx, new_x, attr="v")
        tie_detail[idx] = {"r": new_r, "x": new_x}
    for idx in env.bess_idx:
        ss.ESD1.set("SOCinit", idx, float(point["soc"]), attr="v")

    pflow_return = ss.PFlow.run()
    eig_return = ss.EIG.run() if bool(pflow_return) else False
    eigenvalues = np.asarray(ss.EIG.mu) if bool(eig_return) else np.asarray([])
    state_matrix = np.asarray(ss.EIG.As, dtype=float) if bool(eig_return) else np.empty((0, 0))
    max_f = _max_abs(ss.dae.f)
    max_g = _max_abs(ss.dae.g)
    tolerance = float(ss.TDS.config.tol)
    finite_spectrum = bool(
        eigenvalues.size
        and np.all(np.isfinite(eigenvalues.real))
        and np.all(np.isfinite(eigenvalues.imag))
        and state_matrix.size
        and np.all(np.isfinite(state_matrix))
    )
    positive_count = int(
        np.count_nonzero(eigenvalues.real > THRESHOLDS["positive_real_tolerance"])
    ) if eigenvalues.size else 0
    residual_pass = bool(
        max_f is not None and max_g is not None and max(max_f, max_g) < tolerance
    )
    execution_pass = bool(
        pflow_return
        and eig_return
        and ss.TDS.test_ok is True
        and ss.exit_code == 0
        and residual_pass
        and finite_spectrum
        and positive_count == 0
    )
    machine_states: dict[str, int] = {}
    vsg_omega_states: list[int] = []
    mode = None
    if execution_pass:
        machine_states, vsg_omega_states = _state_maps(ss, env)
        mode = participation_mode(
            state_matrix,
            machine_states,
            AREA_1_KEYS,
            AREA_2_KEYS,
            frequency_band_hz=FREQUENCY_BAND_HZ,
        )
        if mode is None or float(mode["eigenvector_condition_number"]) > THRESHOLDS["eigenvector_condition_number_max"]:
            execution_pass = False
    guards = {
        "pflow_return": _simple(pflow_return),
        "eig_return": _simple(eig_return),
        "tds_test_ok": _simple(ss.TDS.test_ok),
        "system_exit_code": int(ss.exit_code),
        "dae_max_abs_f": max_f,
        "dae_max_abs_g": max_g,
        "initialization_tolerance": tolerance,
        "residual_pass": residual_pass,
        "finite_spectrum_and_matrix": finite_spectrum,
        "positive_real_tolerance": THRESHOLDS["positive_real_tolerance"],
        "positive_real_count": positive_count,
        "max_eigenvalue_real": None if not eigenvalues.size else float(np.max(eigenvalues.real)),
        "registered_mode_present": mode is not None,
        "eigenvector_condition_pass": bool(
            mode is not None
            and float(mode["eigenvector_condition_number"])
            <= THRESHOLDS["eigenvector_condition_number_max"]
        ),
        "execution_pass": execution_pass,
    }
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "point": point,
        "seal_sha256": seal_hash,
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "andes_version": getattr(andes, "__version__", "unknown"),
        },
        "executed": {
            "m_values": m_values,
            "d_values": d_values,
            "tie_lines": tie_detail,
            "soc_init": [float(point["soc"])] * 4,
        },
        "guards": guards,
        "state_names": [str(value) for value in ss.EIG.x_name] if bool(eig_return) else [],
        "machine_state_indices": machine_states,
        "vsg_omega_state_indices": vsg_omega_states,
        "state_matrix": state_matrix.tolist(),
        "eigenvalues": [[float(value.real), float(value.imag)] for value in eigenvalues],
        "interarea_mode": mode,
    }


def run_shard(
    seal_path: Path,
    expected_sha256: str,
    out_dir: Path,
    shard_index: int,
    shard_count: int,
) -> None:
    seal = _verify_seal(seal_path, expected_sha256)
    if shard_count != int(seal["shard_count"]) or not 0 <= shard_index < shard_count:
        raise ValueError("shard contract mismatch")
    points = [
        point for point in seal["operating_bank"] if int(point["order"]) % shard_count == shard_index
    ]
    for point in points:
        path = out_dir / "records" / f"{point['order']:02d}__{point['name']}.json"
        if path.exists():
            _verify_sidecar(path)
            retained = json.loads(path.read_text(encoding="utf-8"))
            if retained.get("seal_sha256") != expected_sha256:
                raise RuntimeError(f"retained record seal mismatch: {path}")
            print(f"[resume] {path.name} pass={retained['guards']['execution_pass']}", flush=True)
            continue
        record = _run_point(point, expected_sha256)
        digest = _write_new(path, record)
        print(
            f"[point] {path.name} pass={record['guards']['execution_pass']} "
            f"sha256={digest}",
            flush=True,
        )


def _point_key(point: dict[str, Any]) -> tuple[float, ...]:
    return tuple(float(point[axis]) for axis in AXIS_ORDER)


def _point_comparison(
    truth_record: dict[str, Any],
    prediction_matrix: np.ndarray,
    thresholds: dict[str, float],
) -> dict[str, Any]:
    machine_states = truth_record["machine_state_indices"]
    predicted_mode = participation_mode(
        prediction_matrix,
        machine_states,
        AREA_1_KEYS,
        AREA_2_KEYS,
        frequency_band_hz=FREQUENCY_BAND_HZ,
    )
    mode_comparison = compare_modes(truth_record["interarea_mode"], predicted_mode)
    truth_response = coordinate_response(
        np.asarray(truth_record["state_matrix"], dtype=float),
        truth_record["vsg_omega_state_indices"],
        **RESPONSE,
    )
    predicted_response = coordinate_response(
        prediction_matrix,
        truth_record["vsg_omega_state_indices"],
        **RESPONSE,
    )
    response_comparison = compare_coordinate_responses(truth_response, predicted_response)
    passed = model_point_passes(mode_comparison, response_comparison, thresholds)
    return {
        "mode": mode_comparison,
        "predicted_mode": predicted_mode,
        "response": response_comparison,
        "pass": passed,
    }


def analyse(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    seal = _verify_seal(seal_path, expected_sha256)
    records: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for point in seal["operating_bank"]:
        path = out_dir / "records" / f"{point['order']:02d}__{point['name']}.json"
        if not path.exists():
            missing.append(path.name)
            continue
        _verify_sidecar(path)
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("seal_sha256") != expected_sha256:
            raise RuntimeError(f"record seal mismatch: {path}")
        records[point["name"]] = record
    if missing:
        raise RuntimeError(f"missing Stage-A records: {missing}")

    invalid = [name for name, record in records.items() if record["guards"]["execution_pass"] is not True]
    state_name_sets = {tuple(record["state_names"]) for record in records.values()}
    if len(state_name_sets) != 1:
        invalid.append("STATE_NAME_DRIFT")
    result: dict[str, Any] = {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "seal_sha256": expected_sha256,
        "record_count": len(records),
        "invalid_records": invalid,
        "thresholds": seal["thresholds"],
        "claim_boundary": seal["claim_boundary"],
    }
    if invalid:
        result.update(
            {
                "model_decision": "INVALID-STAGE-A-EXECUTION",
                "decoupling_decision": "NOT-EVALUATED",
                "fixed_lti_all_holdouts_pass": False,
                "descriptor_lpv_all_holdouts_pass": False,
                "holdouts": [],
            }
        )
    else:
        corner_matrices = {
            _point_key(record["point"]): np.asarray(record["state_matrix"], dtype=float)
            for record in records.values()
            if record["point"]["role"] == "lpv_corner"
        }
        fixed_matrix = np.asarray(records[FIXED_ANCHOR["name"]]["state_matrix"], dtype=float)
        holdout_results = []
        for point in seal["operating_bank"]:
            if point["role"] != "holdout":
                continue
            truth = records[point["name"]]
            lpv_matrix = multilinear_interpolate(
                corner_matrices, point, seal["bounds"], seal["axis_order"]
            )
            lpv = _point_comparison(truth, lpv_matrix, seal["thresholds"])
            fixed = _point_comparison(truth, fixed_matrix, seal["thresholds"])
            holdout_results.append({"point": point, "fixed_lti": fixed, "descriptor_lpv": lpv})
        fixed_pass = all(row["fixed_lti"]["pass"] for row in holdout_results)
        lpv_pass = all(row["descriptor_lpv"]["pass"] for row in holdout_results)
        truth_cross = [
            max(row["descriptor_lpv"]["response"]["truth_coupling"].values())
            for row in holdout_results
        ]
        max_truth_cross = max(truth_cross)
        if max_truth_cross > seal["thresholds"]["hard_decoupling_cross_self_ratio_max"]:
            decoupling = "DECOUPLING-NO-GO"
        elif max_truth_cross > seal["thresholds"]["approximately_decoupled_cross_self_ratio_max"]:
            decoupling = "RETAIN-CROSS-BLOCKS"
        else:
            decoupling = "APPROXIMATE-DECOUPLING-ELIGIBLE"
        result.update(
            {
                "model_decision": (
                    "STAGE-A-DESCRIPTOR-LPV-ELIGIBLE"
                    if lpv_pass
                    else "STAGE-A-NONLINEAR-OR-NARROWER-DOMAIN-REQUIRED"
                ),
                "decoupling_decision": decoupling,
                "fixed_lti_all_holdouts_pass": fixed_pass,
                "descriptor_lpv_all_holdouts_pass": lpv_pass,
                "max_truth_cross_self_ratio": max_truth_cross,
                "holdouts": holdout_results,
            }
        )
    summary_path = out_dir / "stage_a_summary.json"
    summary_hash = _write_new(summary_path, result)
    provenance = {
        "seal": {"path": seal_path.relative_to(ROOT).as_posix(), "sha256": expected_sha256},
        "summary": {"path": summary_path.relative_to(ROOT).as_posix(), "sha256": summary_hash},
        "records": {
            name: sha256_file(out_dir / "records" / f"{record['point']['order']:02d}__{name}.json")
            for name, record in records.items()
        },
        "analysis_runtime": {"python": sys.version, "platform": platform.platform()},
    }
    _write_new(out_dir / "provenance.json", provenance)
    print(f"model_decision={result['model_decision']}")
    print(f"decoupling_decision={result['decoupling_decision']}")
    print(f"summary_sha256={summary_hash}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    prepare_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    run_parser.add_argument("--expected-seal-sha256", required=True)
    run_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    run_parser.add_argument("--shard-index", type=int, required=True)
    run_parser.add_argument("--shard-count", type=int, default=SHARD_COUNT)
    analyse_parser = commands.add_parser("analyse")
    analyse_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse_parser.add_argument("--expected-seal-sha256", required=True)
    analyse_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.seal, args.out_dir)
    elif args.command == "run":
        run_shard(
            args.seal,
            args.expected_seal_sha256,
            args.out_dir,
            args.shard_index,
            args.shard_count,
        )
    elif args.command == "analyse":
        analyse(args.seal, args.expected_seal_sha256, args.out_dir)
    else:  # pragma: no cover
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
