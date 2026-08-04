#!/usr/bin/env python3
"""Run the sealed R317 model-only delayed-feedback synthesis gate.

Usage:
    python scripts/run_r317_offline_controller.py prepare
    python scripts/run_r317_offline_controller.py execute --expected-sha256 <seal>
    python scripts/run_r317_offline_controller.py analyse --expected-sha256 <seal>

The script never imports ANDES and exposes no physical-run or EVAL command.
All scientific thresholds and cases are returned by :func:`build_contract` and
are sealed before the first controller outcome is computed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from andes_rl_kundur.control.model_first_offline_feedback import (  # noqa: E402
    FeedbackCase,
    FeedbackLimits,
    GainSelection,
    NoFeasibleFeedbackGain,
    select_scalar_multiplier,
    simulate_delayed_output_feedback,
    synthesize_dc_inverse_gains,
)
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (  # noqa: E402
    StateSpaceRealization,
    realization_from_dict,
)
from probes.r317_offline_controller_validation import (  # noqa: E402
    evaluate_offline_controller,
)

ROUND_ID = "R317"
QUESTION_ID = "Q-0072"
PARENT_MODEL = ROOT / "results/r316_dynamic_reduction/dynamic_model.json"
PARENT_ANALYSIS = ROOT / "results/r316_dynamic_reduction/analysis.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R317/offline_controller_seal.json"
DEFAULT_OUT = ROOT / "results/r317_offline_controller"
HORIZON_STEPS = 50
POINT_SOC = {"HS0": 0.41, "HS1": 0.51}
COORDINATES = ("common", "edge_0", "edge_1", "edge_2")


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
    """Return the exact prospective R317 controller and rejection contract."""

    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "model-only-delayed-cross-feedback-synthesis",
        "parent_round": "R316",
        "parent_claim": "CLM-0790",
        "sample_period_seconds": 0.2,
        "horizon_steps": HORIZON_STEPS,
        "coordinates": list(COORDINATES),
        "points": [
            {"name": name, "initial_soc": soc} for name, soc in POINT_SOC.items()
        ],
        "law": "u[k]=-alpha*K*y[k-1]",
        "first_command": "zero",
        "retained_base_gain": "inverse-of-equally-weighted-average-DC-gain",
        "matched_baseline": (
            "same-base-gain-with-common-differential-feedback-blocks-zeroed"
        ),
        "maximum_dc_gain_condition_number": 1.0e6,
        "scalar_candidates": [value / 100.0 for value in range(1, 101)],
        "selection_order": [
            "minimum-worst-normalized-output-energy",
            "minimum-mean-normalized-output-energy",
            "minimum-alpha",
        ],
        "development_shapes": {
            "impulse": [0.05],
            "triangle": [0.02, 0.04, 0.05, 0.04, 0.02],
        },
        "examination_shapes": {
            "bipolar": [0.05, 0.05, 0.0, -0.05, -0.05],
        },
        "development_case_count": 32,
        "examination_base_case_count": 16,
        "mismatch_mode_count": 5,
        "examination_case_count": 80,
        "mismatch_scale": 0.15,
        "mismatch_pointwise_ceiling": 0.20,
        "limits": asdict(FeedbackLimits()),
        "maximum_pole_radius": 0.995,
        "minimum_improvement": 0.02,
        "comparison_identifiability": {
            "decision": "ALLOW",
            "single_factor": (
                "retain-versus-delete-common-differential-feedback-blocks"
            ),
            "matched": [
                "full-retained-cross-plant-models",
                "delivered-information",
                "four-coordinate-action",
                "node-basis-and-governor",
                "sample-timing-and-horizon",
                "scalar-candidate-count",
                "disturbances-and-mismatch-transforms",
                "objective-and-metrics",
            ],
        },
        "classification": [
            "INVALID-OFFLINE-CONTROLLER",
            "OFFLINE-CONTROLLER-NO-GO",
            "OFFLINE-CONTROLLER-PASS",
        ],
        "eval": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def _disturbance(sequence: list[float], coordinate_index: int, sign: float) -> np.ndarray:
    values = np.zeros((HORIZON_STEPS, 4))
    values[: len(sequence), coordinate_index] = sign * np.asarray(sequence)
    return values


def _cases(shapes: dict[str, list[float]]) -> list[FeedbackCase]:
    cases: list[FeedbackCase] = []
    for point, initial_soc in POINT_SOC.items():
        for shape, sequence in shapes.items():
            for coordinate_index, coordinate in enumerate(COORDINATES):
                for sign_name, sign in (("positive", 1.0), ("negative", -1.0)):
                    cases.append(
                        FeedbackCase(
                            point=point,
                            name=f"{point}/{shape}/{coordinate}/{sign_name}",
                            disturbance=_disturbance(sequence, coordinate_index, sign),
                            initial_soc=initial_soc,
                        )
                    )
    return cases


def development_cases() -> list[FeedbackCase]:
    """Return the 32 cases visible to scalar selection."""

    return _cases(build_contract()["development_shapes"])


def examination_cases() -> list[FeedbackCase]:
    """Return the 16 bipolar cases hidden from scalar selection."""

    return _cases(build_contract()["examination_shapes"])


def mismatch_transforms() -> dict[str, np.ndarray]:
    """Return the five sealed additive-output mismatch transforms."""

    reflection = np.diag([1.0, -1.0, 1.0, -1.0])
    exchange = np.array(
        [
            [0.0, 1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    return {
        "nominal": np.zeros((4, 4)),
        "plus_scale": 0.15 * np.eye(4),
        "minus_scale": -0.15 * np.eye(4),
        "signed_reflection": 0.15 * reflection,
        "common_differential_exchange": 0.15 * exchange,
    }


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R317/plan.md",
        "question": ROOT / "memory/questions/Q-0072.md",
        "parent_claim": ROOT / "memory/claims/CLM-0790.md",
        "parent_model": PARENT_MODEL,
        "parent_analysis": PARENT_ANALYSIS,
        "controller_module": SRC
        / "andes_rl_kundur/control/model_first_offline_feedback.py",
        "validation_probe": ROOT / "probes/r317_offline_controller_validation.py",
        "adapter": Path(__file__).resolve(),
        "controller_tests": ROOT / "tests/test_model_first_offline_feedback.py",
        "validation_tests": ROOT
        / "tests/test_r317_offline_controller_validation.py",
        "adapter_tests": ROOT / "tests/test_r317_offline_controller.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _load_parent() -> tuple[dict[str, Any], str, dict[str, Any], str]:
    model, model_digest = _read_verified_json(PARENT_MODEL)
    analysis, analysis_digest = _read_verified_json(PARENT_ANALYSIS)
    if (
        model.get("round") != "R316"
        or model.get("question") != "Q-0071"
        or model.get("controller_development_authorized") is not False
        or model.get("distributed_agent_implementation_authorized") is not False
        or model.get("training_authorized") is not False
        or set(model.get("points", {})) != set(POINT_SOC)
        or analysis.get("classification") != "DYNAMIC-REDUCTION-PASS"
        or analysis.get("dynamic_model_sha256") != model_digest
        or analysis.get("controller_development_authorized") is not False
        or analysis.get("training_authorized") is not False
    ):
        raise RuntimeError("R316 parent authority contract mismatch")
    return model, model_digest, analysis, analysis_digest


def prepare(seal_path: Path) -> str:
    """Seal sources and the complete prospective contract create-only."""

    _model, model_digest, _analysis, analysis_digest = _load_parent()
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "parent": {
            "dynamic_model": {
                "path": _path_text(PARENT_MODEL),
                "sha256": model_digest,
            },
            "analysis": {
                "path": _path_text(PARENT_ANALYSIS),
                "sha256": analysis_digest,
            },
        },
        "sources": _sources(),
    }
    digest = _write_new_json(seal_path, seal)
    print(f"seal_sha256={digest}", flush=True)
    return digest


def _load_seal(path: Path, expected: str) -> tuple[dict[str, Any], str]:
    seal, digest = _read_verified_json(path, expected)
    if (
        seal.get("round") != ROUND_ID
        or seal.get("question") != QUESTION_ID
        or seal.get("contract") != build_contract()
        or seal.get("contract_payload_sha256") != _payload_sha256(build_contract())
    ):
        raise RuntimeError("R317 seal contract drift")
    _model, model_digest, _analysis, analysis_digest = _load_parent()
    if seal.get("parent") != {
        "dynamic_model": {"path": _path_text(PARENT_MODEL), "sha256": model_digest},
        "analysis": {"path": _path_text(PARENT_ANALYSIS), "sha256": analysis_digest},
    }:
        raise RuntimeError("R317 sealed parent drift")
    for name, entry in seal["sources"].items():
        source = ROOT / entry["path"]
        if _sha256_file(source) != entry["sha256"]:
            raise RuntimeError(f"R317 sealed source drift for {name}")
    return seal, digest


def _realizations(model: dict[str, Any]) -> dict[str, StateSpaceRealization]:
    points = model.get("points")
    if not isinstance(points, dict) or set(points) != set(POINT_SOC):
        raise RuntimeError("R316 point set mismatch")
    result = {
        name: realization_from_dict(entry["realization"])
        for name, entry in points.items()
    }
    if not all(
        realization.state_matrix.shape == (10, 10)
        and realization.input_matrix.shape == (10, 4)
        and realization.output_matrix.shape == (4, 10)
        and realization.feedthrough_matrix.shape == (4, 4)
        for realization in result.values()
    ):
        raise RuntimeError("R316 realization matrix contract mismatch")
    return result


def _selection_payload(selection: GainSelection) -> dict[str, object]:
    return {
        "selection_feasible": True,
        "selected_scalar": selection.scalar,
        "candidate_count": selection.candidate_count,
        "development_case_count": selection.case_count,
        "maximum_pole_radius": selection.maximum_pole_radius,
        "development_mean_output_energy_ratio": selection.mean_output_energy_ratio,
        "development_worst_output_energy_ratio": selection.worst_output_energy_ratio,
        "development_governor_intervention_count": (
            selection.governor_intervention_count
        ),
        "development_constraint_violation_count": (
            selection.constraint_violation_count
        ),
        "selected_gain": selection.gain.tolist(),
    }


def _infeasible_payload() -> dict[str, object]:
    return {
        "selection_feasible": False,
        "selected_scalar": None,
        "candidate_count": len(build_contract()["scalar_candidates"]),
        "development_case_count": len(development_cases()),
        "maximum_pole_radius": None,
        "examination": {
            "case_count": 0,
            "finite": True,
            "constraint_violation_count": 0,
            "energy_ratios_to_zero": [],
            "not_run_reason": "no-feasible-scalar",
        },
    }


def _examine(
    realizations: dict[str, StateSpaceRealization],
    selection: GainSelection,
    *,
    limits: FeedbackLimits,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    ratios: list[float] = []
    violations = 0
    finite = True
    for case in examination_cases():
        realization = realizations[case.point]
        for mismatch_name, mismatch in mismatch_transforms().items():
            zero = simulate_delayed_output_feedback(
                realization,
                case.disturbance,
                gain=np.zeros((4, 4)),
                initial_soc=case.initial_soc,
                limits=limits,
                mismatch_transform=mismatch,
            )
            controlled = simulate_delayed_output_feedback(
                realization,
                case.disturbance,
                gain=selection.gain,
                initial_soc=case.initial_soc,
                limits=limits,
                mismatch_transform=mismatch,
            )
            ratio = controlled.output_energy / max(
                zero.output_energy, np.finfo(float).tiny
            )
            node_deltas = np.vstack(
                (
                    controlled.node_actions[:1],
                    np.diff(controlled.node_actions, axis=0),
                )
            )
            row = {
                "case": case.name,
                "point": case.point,
                "mismatch": mismatch_name,
                "output_energy": controlled.output_energy,
                "zero_control_output_energy": zero.output_energy,
                "output_energy_ratio_to_zero": ratio,
                "coordinate_action_energy": controlled.coordinate_action_energy,
                "maximum_node_power": float(
                    np.max(np.abs(controlled.node_actions))
                ),
                "maximum_node_ramp": float(np.max(np.abs(node_deltas))),
                "minimum_soc": float(np.min(controlled.soc)),
                "maximum_soc": float(np.max(controlled.soc)),
                "governor_intervention_count": (
                    controlled.governor_intervention_count
                ),
                "constraint_violation_count": (
                    controlled.constraint_violation_count
                ),
            }
            row_finite = all(
                np.isfinite(value)
                for key, value in row.items()
                if key
                not in {
                    "case",
                    "point",
                    "mismatch",
                    "governor_intervention_count",
                    "constraint_violation_count",
                }
            )
            finite = finite and row_finite
            violations += controlled.constraint_violation_count
            ratios.append(ratio)
            rows.append(row)
    summary = {
        "case_count": len(rows),
        "finite": finite,
        "constraint_violation_count": violations,
        "energy_ratios_to_zero": ratios,
    }
    return summary, rows


def _calculate(model: dict[str, Any]) -> dict[str, Any]:
    contract = build_contract()
    limits = FeedbackLimits(**contract["limits"])
    realizations = _realizations(model)
    family = synthesize_dc_inverse_gains(
        list(realizations.values()),
        maximum_condition_number=contract["maximum_dc_gain_condition_number"],
    )
    development = development_cases()
    arms: dict[str, dict[str, object]] = {}
    case_rows: dict[str, list[dict[str, object]]] = {}
    for name, base_gain in (
        ("retained_cross", family.retained_cross_base),
        ("cross_deleted", family.cross_deleted_base),
    ):
        try:
            selection = select_scalar_multiplier(
                realizations,
                development,
                base_gain=base_gain,
                scalar_candidates=contract["scalar_candidates"],
                limits=limits,
                maximum_pole_radius=contract["maximum_pole_radius"],
            )
        except NoFeasibleFeedbackGain:
            arms[name] = _infeasible_payload()
            case_rows[name] = []
            continue
        arm = _selection_payload(selection)
        examination, rows = _examine(realizations, selection, limits=limits)
        arm["examination"] = examination
        arms[name] = arm
        case_rows[name] = rows
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "gain_family": {
            "averaged_dc_gain": family.averaged_dc_gain.tolist(),
            "condition_number": family.condition_number,
            "retained_cross_base": family.retained_cross_base.tolist(),
            "cross_deleted_base": family.cross_deleted_base.tolist(),
        },
        "arms": arms,
        "cases": case_rows,
        "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_performed": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def execute(seal_path: Path, expected: str, out_dir: Path) -> str:
    """Compute the frozen controller result and deterministic replay guard."""

    seal, seal_digest = _load_seal(seal_path, expected)
    model, model_digest, _parent_analysis, _parent_analysis_digest = _load_parent()
    first = _calculate(model)
    second = _calculate(model)
    deterministic = _payload_sha256(first) == _payload_sha256(second)
    first.update(
        {
            "schema_version": 1,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "contract_payload_sha256": seal["contract_payload_sha256"],
            "parent_dynamic_model_sha256": model_digest,
            "validity_guards": {
                "sealed_source_identity": True,
                "matrix_contract": True,
                "deterministic_replay": deterministic,
                "case_contract": bool(
                    len(development_cases()) == seal["contract"]["development_case_count"]
                    and len(examination_cases())
                    * len(mismatch_transforms())
                    == seal["contract"]["examination_case_count"]
                ),
                "comparison_contract": bool(
                    seal["contract"]["comparison_identifiability"]["decision"]
                    == "ALLOW"
                ),
                "eval_not_run": True,
            },
        }
    )
    digest = _write_new_json(out_dir / "controller_result.json", first)
    print(f"controller_result_sha256={digest}", flush=True)
    return digest


def analyse(seal_path: Path, expected: str, out_dir: Path) -> str:
    """Apply the frozen pure classifier and write measured provenance."""

    seal, seal_digest = _load_seal(seal_path, expected)
    result, result_digest = _read_verified_json(out_dir / "controller_result.json")
    if (
        result.get("seal_sha256") != seal_digest
        or result.get("contract_payload_sha256")
        != seal["contract_payload_sha256"]
    ):
        raise RuntimeError("R317 controller result provenance mismatch")
    analysis = evaluate_offline_controller(result)
    analysis.update(
        {
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "controller_result_sha256": result_digest,
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
        "controller_result": {
            "path": _path_text(out_dir / "controller_result.json"),
            "sha256": result_digest,
        },
        "analysis": {
            "path": _path_text(out_dir / "analysis.json"),
            "sha256": analysis_digest,
        },
        "parent": seal["parent"],
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
    parser.add_argument("command", choices=("prepare", "execute", "analyse"))
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
    if args.command == "execute":
        execute(args.seal, args.expected_sha256, args.out)
    else:
        analyse(args.seal, args.expected_sha256, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
