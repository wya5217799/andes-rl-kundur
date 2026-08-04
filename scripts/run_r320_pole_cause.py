#!/usr/bin/env python3
"""Run the sealed R320 nominal pole-cause diagnosis.

Usage:
    python scripts/run_r320_pole_cause.py prepare
    python scripts/run_r320_pole_cause.py diagnose --expected-sha256 <seal>
    python scripts/run_r320_pole_cause.py analyse --expected-sha256 <seal>

The script consumes only sealed nominal models and gains. It defines no
disturbance case and exposes no performance, ANDES, physical, EVAL, or training
command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.signal import place_poles

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from andes_rl_kundur.control.model_first_observer_lqr import (  # noqa: E402
    build_delay_augmented_model,
    delete_common_differential_markov_blocks,
)
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (  # noqa: E402
    StateSpaceRealization,
    enforce_spectral_radius,
    fit_era_realization,
    realization_from_dict,
)
from probes.r320_pole_cause_diagnosis import (  # noqa: E402
    controllability_matrix,
    evaluate_pole_cause,
    normalized_pbh_margin,
    observability_matrix,
)

ROUND_ID = "R320"
QUESTION_ID = "Q-0075"
R316_MODEL = ROOT / "results/r316_dynamic_reduction/dynamic_model.json"
R319_SEAL = ROOT / "memory/rounds/R319/observer_lqr_seal.json"
R319_RESULT = ROOT / "results/r319_observer_lqr/controller_result.json"
R319_ANALYSIS = ROOT / "results/r319_observer_lqr/analysis.json"
R319_PROVENANCE = ROOT / "results/r319_observer_lqr/provenance.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R320/pole_cause_seal.json"
DEFAULT_OUT = ROOT / "results/r320_pole_cause"
ARMS = ("retained_cross", "cross_deleted")
POINTS = ("HS0", "HS1")


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
    if path.exists() or path.with_suffix(path.suffix + ".sha256").exists():
        raise FileExistsError(f"create-only artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    path.write_text(text, encoding="utf-8")
    digest = _sha256_file(path)
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="ascii"
    )
    return digest


def _read_verified_json(
    path: Path,
    expected_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    if not path.is_file():
        raise FileNotFoundError(path)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not sidecar.is_file():
        raise FileNotFoundError(sidecar)
    digest = _sha256_file(path)
    sidecar_digest = sidecar.read_text(encoding="ascii").split()[0]
    if digest != sidecar_digest or (
        expected_sha256 is not None and digest != expected_sha256
    ):
        raise RuntimeError(f"hash mismatch for {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON artifact is not an object: {path}")
    return payload, digest


def build_contract() -> dict[str, Any]:
    """Return the exact prospective R320 diagnostic contract."""

    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "nominal-pole-cause-and-placement-feasibility",
        "parent_round": "R319",
        "parent_claim": "CLM-0805",
        "model_keys": [f"{arm}/{point}" for arm in ARMS for point in POINTS],
        "state_dimension": 14,
        "maximum_registered_radius": 0.995,
        "radius_identity_tolerance": 1.0e-12,
        "relative_rank_and_pbh_tolerance": 1.0e-10,
        "controller_target_poles": np.linspace(0.90, 0.98, 14).tolist(),
        "observer_target_poles": (
            [0.0] * 4 + np.linspace(0.80, 0.94, 10).tolist()
        ),
        "placement_method": "YT",
        "placement_relative_tolerance": 1.0e-6,
        "placement_maximum_iterations": 100,
        "placement_target_tolerance": 1.0e-8,
        "controller_target_radius": 0.98,
        "observer_target_radius": 0.94,
        "performance_case_access": "PROHIBITED",
        "comparison": "DESCRIPTIVE-NO-EFFICACY-ESTIMAND",
        "classification": [
            "INVALID-POLE-CAUSE-DIAGNOSIS",
            "DIAGNOSTIC-CONFLICT",
            "STRUCTURAL-POLE-NO-GO",
            "TARGET-PLACEMENT-NO-GO",
            "POLE-TARGET-ELIGIBLE",
        ],
        "eval": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R320/plan.md",
        "question": ROOT / "memory/questions/Q-0075.md",
        "dynamic_model_claim": ROOT / "memory/claims/CLM-0790.md",
        "static_pole_claim": ROOT / "memory/claims/CLM-0800.md",
        "observer_lqr_claim": ROOT / "memory/claims/CLM-0805.md",
        "r316_model": R316_MODEL,
        "r319_seal": R319_SEAL,
        "r319_result": R319_RESULT,
        "r319_analysis": R319_ANALYSIS,
        "r319_provenance": R319_PROVENANCE,
        "observer_lqr_module": SRC
        / "andes_rl_kundur/control/model_first_observer_lqr.py",
        "diagnostic_probe": ROOT / "probes/r320_pole_cause_diagnosis.py",
        "adapter": Path(__file__).resolve(),
        "probe_tests": ROOT / "tests/test_r320_pole_cause_diagnosis.py",
        "adapter_tests": ROOT / "tests/test_r320_pole_cause.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _load_parent() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, str]]:
    seal, seal_digest = _read_verified_json(R319_SEAL)
    result, result_digest = _read_verified_json(R319_RESULT)
    analysis, analysis_digest = _read_verified_json(R319_ANALYSIS)
    provenance, provenance_digest = _read_verified_json(R319_PROVENANCE)
    if (
        seal.get("round") != "R319"
        or seal.get("question") != "Q-0074"
        or result.get("seal_sha256") != seal_digest
        or analysis.get("classification") != "OBSERVER-LQR-NO-GO"
        or analysis.get("controller_result_sha256") != result_digest
        or not all(analysis.get("validity_guards", {}).values())
        or analysis.get("comparison", {}).get("mean_energy_reduction_vs_cross_deleted")
        is not None
        or analysis.get("comparison", {}).get("worst_energy_reduction_vs_cross_deleted")
        is not None
        or provenance.get("controller_result", {}).get("sha256") != result_digest
        or provenance.get("analysis", {}).get("sha256") != analysis_digest
        or provenance.get("physical_execution_performed") is not False
        or provenance.get("eval_status") != "NOT-APPLICABLE-MODEL-ONLY"
    ):
        raise RuntimeError("R319 parent authority contract mismatch")
    for arm in ARMS:
        if (
            analysis["arms"][arm]["examination_case_count"] != 0
            or analysis["arms"][arm]["energy_ratios_to_zero"] != []
            or result["cases"][arm]["examination"] != []
        ):
            raise RuntimeError("R319 hidden examination was accessed")
    hashes = {
        "seal": seal_digest,
        "result": result_digest,
        "analysis": analysis_digest,
        "provenance": provenance_digest,
    }
    return seal, result, analysis, hashes


def prepare(seal_path: Path) -> str:
    _seal, _result, _analysis, hashes = _load_parent()
    contract = build_contract()
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "parent": {
            "seal": {"path": _path_text(R319_SEAL), "sha256": hashes["seal"]},
            "controller_result": {
                "path": _path_text(R319_RESULT),
                "sha256": hashes["result"],
            },
            "analysis": {
                "path": _path_text(R319_ANALYSIS),
                "sha256": hashes["analysis"],
            },
            "provenance": {
                "path": _path_text(R319_PROVENANCE),
                "sha256": hashes["provenance"],
            },
        },
        "sources": _sources(),
    }
    digest = _write_new_json(seal_path, payload)
    print(f"seal_sha256={digest}", flush=True)
    return digest


def _load_seal(path: Path, expected: str) -> tuple[dict[str, Any], str]:
    seal, digest = _read_verified_json(path, expected)
    contract = build_contract()
    if (
        seal.get("round") != ROUND_ID
        or seal.get("question") != QUESTION_ID
        or seal.get("contract") != contract
        or seal.get("contract_payload_sha256") != _payload_sha256(contract)
    ):
        raise RuntimeError("R320 seal contract drift")
    _parent_seal, _result, _analysis, hashes = _load_parent()
    expected_parent = {
        "seal": {"path": _path_text(R319_SEAL), "sha256": hashes["seal"]},
        "controller_result": {
            "path": _path_text(R319_RESULT),
            "sha256": hashes["result"],
        },
        "analysis": {"path": _path_text(R319_ANALYSIS), "sha256": hashes["analysis"]},
        "provenance": {
            "path": _path_text(R319_PROVENANCE),
            "sha256": hashes["provenance"],
        },
    }
    if seal.get("parent") != expected_parent:
        raise RuntimeError("R320 sealed parent drift")
    for name, entry in seal["sources"].items():
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"R320 sealed source drift for {name}")
    return seal, digest


def _r316_models() -> tuple[dict[str, StateSpaceRealization], dict[str, np.ndarray]]:
    model, _digest = _read_verified_json(R316_MODEL)
    if model.get("round") != "R316" or set(model.get("points", {})) != set(POINTS):
        raise RuntimeError("R316 model identity mismatch")
    retained = {
        point: realization_from_dict(model["points"][point]["realization"])
        for point in POINTS
    }
    markov = {
        point: np.asarray(model["points"][point]["markov_parameters"], dtype=float)
        for point in POINTS
    }
    return retained, markov


def _cross_deleted_models(markov: dict[str, np.ndarray]) -> dict[str, StateSpaceRealization]:
    result: dict[str, StateSpaceRealization] = {}
    for point, tensor in markov.items():
        realization = fit_era_realization(
            delete_common_differential_markov_blocks(tensor),
            order=10,
            block_rows=8,
            block_columns=8,
        )
        if realization.spectral_radius > 0.995:
            realization = enforce_spectral_radius(realization, maximum_radius=0.995)
        result[point] = realization
    return result


def _relative_rank(matrix: np.ndarray, tolerance: float) -> int:
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    if singular_values.size == 0 or singular_values[0] == 0.0:
        return 0
    return int(np.sum(singular_values > tolerance * singular_values[0]))


def _complex_record(value: complex) -> dict[str, float]:
    return {
        "real": float(value.real),
        "imag": float(value.imag),
        "magnitude": float(abs(value)),
    }


def _target_error(achieved: np.ndarray, target: np.ndarray) -> float:
    cost = np.abs(achieved.reshape(-1, 1) - target.reshape(1, -1))
    rows, columns = linear_sum_assignment(cost)
    return float(np.max(cost[rows, columns]))


def _placement(
    state: np.ndarray,
    inputs: np.ndarray,
    measured: np.ndarray,
) -> dict[str, object]:
    contract = build_contract()
    controller_target = np.asarray(contract["controller_target_poles"], dtype=float)
    observer_target = np.asarray(contract["observer_target_poles"], dtype=float)
    try:
        controller = place_poles(
            state,
            inputs,
            controller_target,
            method=contract["placement_method"],
            rtol=contract["placement_relative_tolerance"],
            maxiter=contract["placement_maximum_iterations"],
        )
        corrected_observer = place_poles(
            state.T,
            (measured @ state).T,
            observer_target,
            method=contract["placement_method"],
            rtol=contract["placement_relative_tolerance"],
            maxiter=contract["placement_maximum_iterations"],
        )
        feedback = np.asarray(controller.gain_matrix, dtype=float)
        filter_gain = np.asarray(corrected_observer.gain_matrix.T, dtype=float)
        controller_poles = np.linalg.eigvals(state - inputs @ feedback)
        observer_poles = np.linalg.eigvals(
            (np.eye(state.shape[0]) - filter_gain @ measured) @ state
        )
        finite = bool(
            np.all(np.isfinite(feedback))
            and np.all(np.isfinite(filter_gain))
            and np.all(np.isfinite(controller_poles))
            and np.all(np.isfinite(observer_poles))
        )
        return {
            "attempted": True,
            "finite": finite,
            "controller_target_max_abs_error": _target_error(
                controller_poles, controller_target
            ),
            "observer_target_max_abs_error": _target_error(
                observer_poles, observer_target
            ),
            "controller_maximum_radius": float(np.max(np.abs(controller_poles))),
            "observer_maximum_radius": float(np.max(np.abs(observer_poles))),
        }
    except (np.linalg.LinAlgError, ValueError) as exc:
        return {
            "attempted": True,
            "finite": False,
            "error": type(exc).__name__,
            "controller_target_max_abs_error": 1.0e99,
            "observer_target_max_abs_error": 1.0e99,
            "controller_maximum_radius": 1.0e99,
            "observer_maximum_radius": 1.0e99,
        }


def _calculate(result: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    contract = build_contract()
    retained, markov = _r316_models()
    model_families = {
        "retained_cross": retained,
        "cross_deleted": _cross_deleted_models(markov),
    }
    model_payloads: dict[str, dict[str, object]] = {}
    matrices: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for arm in ARMS:
        for point in POINTS:
            key = f"{arm}/{point}"
            augmented = build_delay_augmented_model(model_families[arm][point])
            state = augmented.state_matrix
            inputs = augmented.input_matrix
            measured = augmented.measurement_matrix
            feedback = np.asarray(
                result["arms"][arm]["point_designs"][point]["feedback_gain"],
                dtype=float,
            )
            filter_gain = np.asarray(
                result["arms"][arm]["point_designs"][point]["filter_gain"],
                dtype=float,
            )
            if feedback.shape != (4, 14) or filter_gain.shape != (14, 4):
                raise RuntimeError(f"R319 gain shape mismatch for {key}")
            controller_poles = np.linalg.eigvals(state - inputs @ feedback)
            observer_poles = np.linalg.eigvals(
                (np.eye(14) - filter_gain @ measured) @ state
            )
            open_poles = np.linalg.eigvals(state)
            failed_controller = [
                value for value in controller_poles
                if abs(value) > contract["maximum_registered_radius"]
            ]
            failed_observer = [
                value for value in observer_poles
                if abs(value) > contract["maximum_registered_radius"]
            ]
            controller_margins = [
                normalized_pbh_margin(state, inputs, value, kind="control")
                for value in failed_controller
            ]
            observer_margins = [
                normalized_pbh_margin(state, measured, value, kind="observe")
                for value in failed_observer
            ]
            model_payloads[key] = {
                "state_dimension": 14,
                "stored_controller_pole_radius": analysis["arms"][arm][
                    "point_designs"
                ][point]["controller_pole_radius"],
                "recomputed_controller_pole_radius": float(
                    np.max(np.abs(controller_poles))
                ),
                "stored_observer_pole_radius": analysis["arms"][arm][
                    "point_designs"
                ][point]["observer_pole_radius"],
                "recomputed_observer_pole_radius": float(
                    np.max(np.abs(observer_poles))
                ),
                "failed_controller_mode_count": len(failed_controller),
                "failed_observer_mode_count": len(failed_observer),
                "failed_controller_modes": [
                    {
                        **_complex_record(value),
                        "nearest_open_loop_distance": float(
                            np.min(np.abs(open_poles - value))
                        ),
                        "normalized_pbh_margin": margin,
                    }
                    for value, margin in zip(failed_controller, controller_margins)
                ],
                "failed_observer_modes": [
                    {
                        **_complex_record(value),
                        "nearest_open_loop_distance": float(
                            np.min(np.abs(open_poles - value))
                        ),
                        "normalized_pbh_margin": margin,
                    }
                    for value, margin in zip(failed_observer, observer_margins)
                ],
                "controllability_rank": _relative_rank(
                    controllability_matrix(state, inputs),
                    contract["relative_rank_and_pbh_tolerance"],
                ),
                "observability_rank": _relative_rank(
                    observability_matrix(state, measured),
                    contract["relative_rank_and_pbh_tolerance"],
                ),
                "minimum_failed_controller_pbh_margin": (
                    min(controller_margins) if controller_margins else None
                ),
                "minimum_failed_observer_pbh_margin": (
                    min(observer_margins) if observer_margins else None
                ),
            }
            matrices[key] = (state, inputs, measured)

    structural_pass = all(
        value["controllability_rank"] == 14
        and value["observability_rank"] == 14
        and (
            value["minimum_failed_controller_pbh_margin"] is None
            or value["minimum_failed_controller_pbh_margin"]
            >= contract["relative_rank_and_pbh_tolerance"]
        )
        and (
            value["minimum_failed_observer_pbh_margin"] is None
            or value["minimum_failed_observer_pbh_margin"]
            >= contract["relative_rank_and_pbh_tolerance"]
        )
        for value in model_payloads.values()
    )
    for key, value in model_payloads.items():
        value["placement"] = (
            _placement(*matrices[key])
            if structural_pass
            else {"attempted": False, "not_run_reason": "structural-failure"}
        )
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "models": model_payloads,
        "structural_pass": structural_pass,
        "performance_case_accessed": False,
        "r319_examination_case_count": 0,
        "physical_execution_performed": False,
        "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def diagnose(seal_path: Path, expected: str, out_dir: Path) -> str:
    seal, seal_digest = _load_seal(seal_path, expected)
    _parent_seal, result, analysis, _hashes = _load_parent()
    first = _calculate(result, analysis)
    second = _calculate(result, analysis)
    deterministic = _payload_sha256(first) == _payload_sha256(second)
    failed_count_valid = bool(
        sum(
            value["failed_controller_mode_count"]
            for value in first["models"].values()
        ) > 0
        and sum(
            value["failed_observer_mode_count"]
            for value in first["models"].values()
        ) > 0
    )
    first.update(
        {
            "schema_version": 1,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "contract_payload_sha256": seal["contract_payload_sha256"],
            "validity_guards": {
                "sealed_parent_identity": True,
                "matrix_gain_contract": True,
                "deterministic_replay": deterministic,
                "failed_mode_contract": failed_count_valid,
                "no_performance_access": bool(
                    first["performance_case_accessed"] is False
                    and first["r319_examination_case_count"] == 0
                ),
                "placement_contract": bool(
                    len(seal["contract"]["controller_target_poles"]) == 14
                    and len(seal["contract"]["observer_target_poles"]) == 14
                ),
                "eval_not_run": bool(
                    first["physical_execution_performed"] is False
                    and first["eval_status"] == "NOT-APPLICABLE-MODEL-ONLY"
                ),
            },
        }
    )
    digest = _write_new_json(out_dir / "diagnostic.json", first)
    print(f"diagnostic_sha256={digest}", flush=True)
    return digest


def analyse(seal_path: Path, expected: str, out_dir: Path) -> str:
    seal, seal_digest = _load_seal(seal_path, expected)
    diagnostic, diagnostic_digest = _read_verified_json(out_dir / "diagnostic.json")
    if (
        diagnostic.get("seal_sha256") != seal_digest
        or diagnostic.get("contract_payload_sha256")
        != seal["contract_payload_sha256"]
    ):
        raise RuntimeError("R320 diagnostic provenance mismatch")
    analysis = evaluate_pole_cause(diagnostic)
    analysis.update(
        {
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "diagnostic_sha256": diagnostic_digest,
            "contract_payload_sha256": seal["contract_payload_sha256"],
        }
    )
    analysis_digest = _write_new_json(out_dir / "analysis.json", analysis)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal": {"path": _path_text(seal_path), "sha256": seal_digest},
        "diagnostic": {
            "path": _path_text(out_dir / "diagnostic.json"),
            "sha256": diagnostic_digest,
        },
        "analysis": {
            "path": _path_text(out_dir / "analysis.json"),
            "sha256": analysis_digest,
        },
        "parent": seal["parent"],
        "performance_case_accessed": False,
        "physical_execution_performed": False,
        "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
    provenance_digest = _write_new_json(out_dir / "provenance.json", provenance)
    print(f"classification={analysis['classification']}", flush=True)
    print(f"analysis_sha256={analysis_digest}", flush=True)
    print(f"provenance_sha256={provenance_digest}", flush=True)
    return analysis_digest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "diagnose", "analyse"))
    parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--expected-sha256")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare":
        if args.expected_sha256 is not None:
            raise SystemExit("prepare does not accept --expected-sha256")
        prepare(args.seal)
        return 0
    if not args.expected_sha256:
        raise SystemExit(f"{args.command} requires --expected-sha256")
    if args.command == "diagnose":
        diagnose(args.seal, args.expected_sha256, args.out)
    else:
        analyse(args.seal, args.expected_sha256, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
