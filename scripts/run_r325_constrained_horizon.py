"""Create, execute, and analyse the sealed R325 model-only controller study.

Usage:
  python scripts/run_r325_constrained_horizon.py prepare
  python scripts/run_r325_constrained_horizon.py execute --expected-sha256 HASH
  python scripts/run_r325_constrained_horizon.py analyse --expected-sha256 HASH

All durable JSON outputs are create-only and receive SHA-256 sidecars. The
adapter never parses the R321 examination; it verifies that artifact by digest
only. Failures stop with a non-zero exit and preserve all existing artifacts.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory.tools import artifact_io  # noqa: E402
from probes.r325_constrained_horizon_validation import (  # noqa: E402
    analyse_r325_execution,
    development_allows_holdout,
)

from andes_rl_kundur.control.model_first_constrained_horizon import (  # noqa: E402
    ConstrainedHorizonInfeasible,
    simulate_constrained_horizon_feedback,
    synthesize_constrained_horizon,
)
from andes_rl_kundur.control.model_first_observer_lqr import (  # noqa: E402
    delete_common_differential_markov_blocks,
)
from andes_rl_kundur.control.model_first_offline_feedback import (  # noqa: E402
    FeedbackCase,
    FeedbackLimits,
)
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (  # noqa: E402
    StateSpaceRealization,
    enforce_spectral_radius,
    fit_era_realization,
    realization_from_dict,
    simulate_state_space,
)

_canonical_bytes = artifact_io.canonical_json_bytes
_payload_sha256 = artifact_io.payload_sha256
_read_verified_json = artifact_io.read_verified_json
_sha256_file = artifact_io.sha256_file
_verified_digest_only = artifact_io.verified_digest_only
_write_new_json = artifact_io.write_new_json

ROUND_ID = "R325"
QUESTION_ID = "Q-0078"
PARENT_MODEL = ROOT / "results/r316_dynamic_reduction/dynamic_model.json"
PARENT_ANALYSIS = ROOT / "results/r316_dynamic_reduction/analysis.json"
R321_ANALYSIS = ROOT / "results/r321_pole_target_examination/analysis.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R325/constrained_horizon_seal.json"
DEFAULT_OUT = ROOT / "results/r325_constrained_horizon"
COORDINATES = ("common", "edge_0", "edge_1", "edge_2")
POINT_SOC = {"HS0": 0.41, "HS1": 0.51}
SIMULATION_STEPS = 50


def _path_text(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def build_contract() -> dict[str, Any]:
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "model-only-actuator-constrained-finite-horizon-output-feedback",
        "parent_round": "R316",
        "r321_analysis_access": "HASH-ONLY-NO-PARSE",
        "sample_period_seconds": 0.2,
        "simulation_steps": SIMULATION_STEPS,
        "coordinates": list(COORDINATES),
        "points": [
            {"name": name, "initial_soc": soc} for name, soc in POINT_SOC.items()
        ],
        "delay_augmentation": {
            "state": "z[k]=[x[k],y[k-1]]",
            "first_measurement": "zero",
            "initial_estimate": "zero",
            "first_command": "zero",
            "disturbance_preview": False,
        },
        "observer": {
            "kind": "corrected-state-fixed-pole-placement",
            "target_poles": [
                0.0,
                0.0,
                0.0,
                0.0,
                0.8,
                0.8155555555555556,
                0.8311111111111111,
                0.8466666666666667,
                0.8622222222222222,
                0.8777777777777778,
                0.8933333333333333,
                0.9088888888888889,
                0.9244444444444444,
                0.94,
            ],
            "method": "YT",
            "relative_tolerance": 1.0e-6,
            "maximum_iterations": 100,
            "target_absolute_tolerance": 1.0e-8,
        },
        "controller": {
            "kind": "receding-finite-horizon-output-feedback",
            "horizon_steps": 25,
            "horizon_source": "sealed-R319-Markov-horizon",
            "output_scales": {
                "HS0": [
                    0.0002668112041645563,
                    0.00015882926554077416,
                    0.00019288206508276265,
                    0.0002124274132893341,
                ],
                "HS1": [
                    0.00025989821599602683,
                    0.00014880082973969276,
                    0.00018244950507686816,
                    0.00020106658488483798,
                ],
            },
            "action_scales": [0.36, 0.36, 0.36, 0.36],
            "stage_objective": "unit-normalized-output-plus-coordinate-action-energy",
            "terminal_multiplier": 0.0,
            "disturbance_forecast": "zero",
            "weight_candidate_count": 0,
            "horizon_candidate_count": 0,
        },
        "solver": {
            "name": "scipy-SLSQP",
            "maximum_iterations": 200,
            "function_tolerance": 1.0e-9,
            "feasibility_tolerance": 1.0e-8,
            "objective_gradient": "analytic",
            "initialization": "deterministic-ramp-to-zero",
            "cross_arm_warm_start": False,
        },
        "limits": asdict(FeedbackLimits()),
        "synthesis_count_per_point_and_arm": 1,
        "tuning_candidate_count": 0,
        "retained_arm": "unchanged-R316-order-10-realizations",
        "matched_baseline": {
            "single_factor": "delete-common-differential-transfer-blocks",
            "markov_horizon_steps": 25,
            "era_order": 10,
            "block_rows": 8,
            "block_columns": 8,
            "maximum_model_spectral_radius": 0.995,
            "executed_plant": "unchanged-full-retained-cross-R316-realization",
        },
        "development_shapes": {
            "impulse": [0.05],
            "triangle": [0.02, 0.04, 0.05, 0.04, 0.02],
        },
        "development_case_count": 32,
        "holdout_shapes": {"separated_doublet": [0.05, 0.0, 0.0, 0.05]},
        "holdout_base_case_count": 16,
        "holdout_mismatch_mode_count": 5,
        "holdout_case_count": 80,
        "gates": {
            "development_mean_output_energy_ratio_maximum": 0.98,
            "development_worst_output_energy_ratio_maximum": 1.0,
            "holdout_mean_output_energy_ratio_maximum": 0.98,
            "holdout_worst_output_energy_ratio_maximum": 1.0,
            "retained_to_deleted_mean_ratio_maximum": 0.98,
            "retained_worst_not_larger": True,
        },
        "comparison_identifiability": {
            "decision": "ALLOW",
            "identified_estimand": "value-of-retaining-named-cross-blocks-in-this-fixed-controller",
            "single_factor": "retain-versus-delete-named-transfer-blocks",
            "matched": [
                "full-retained-cross-executed-plants",
                "delivered-four-coordinate-information-and-known-point",
                "four-coordinate-action-node-map-and-hard-limits",
                "observer-template-normalization-horizon-objective-and-solver",
                "development-holdout-mismatch-and-metrics",
                "zero-search-zero-tuning-and-zero-seed-selection",
            ],
        },
        "classification": [
            "INVALID-CONSTRAINED-HORIZON",
            "FORMULATION-INFEASIBLE",
            "DEVELOPMENT-NO-GO",
            "FRESH-HOLDOUT-NO-GO",
            "RETAINED-BLOCK-NO-VALUE",
            "CONSTRAINED-HORIZON-PASS",
        ],
        "eval": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def _disturbance(sequence: list[float], coordinate: int, sign: float) -> np.ndarray:
    values = np.zeros((SIMULATION_STEPS, 4))
    values[: len(sequence), coordinate] = sign * np.asarray(sequence, dtype=float)
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
    return _cases(build_contract()["development_shapes"])


def holdout_cases() -> list[FeedbackCase]:
    return _cases(build_contract()["holdout_shapes"])


def mismatch_transforms() -> dict[str, np.ndarray]:
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
        "plan": ROOT / "memory/rounds/R325/plan.md",
        "question": ROOT / "memory/questions/Q-0078.md",
        "parent_model": PARENT_MODEL,
        "parent_analysis": PARENT_ANALYSIS,
        "observer_cause_claim": ROOT / "memory/claims/CLM-0810.md",
        "diagnosis_claim": ROOT / "memory/claims/CLM-0820.md",
        "fidelity_claim": ROOT / "memory/claims/CLM-0830.md",
        "artifact_io": ROOT / "memory/tools/artifact_io.py",
        "artifact_io_tests": ROOT / "memory/tools/tests/test_artifact_io.py",
        "controller_module": ROOT / "src/andes_rl_kundur/control/model_first_constrained_horizon.py",
        "observer_module": ROOT / "src/andes_rl_kundur/control/model_first_observer_lqr.py",
        "offline_feedback_module": ROOT
        / "src/andes_rl_kundur/control/model_first_offline_feedback.py",
        "dynamic_reduction_module": ROOT
        / "src/andes_rl_kundur/evaluation/model_first_dynamic_reduction.py",
        "validation_probe": ROOT / "probes/r325_constrained_horizon_validation.py",
        "adapter": ROOT / "scripts/run_r325_constrained_horizon.py",
        "controller_tests": ROOT / "tests/test_model_first_constrained_horizon.py",
        "validation_tests": ROOT / "tests/test_r325_constrained_horizon_validation.py",
        "adapter_tests": ROOT / "tests/test_r325_constrained_horizon.py",
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
        or model.get("R316_holdout_accessed") is not False
        or set(model.get("points", {})) != set(POINT_SOC)
        or analysis.get("classification") != "DYNAMIC-REDUCTION-PASS"
        or analysis.get("dynamic_model_sha256") != model_digest
        or analysis.get("training_authorized") is not False
    ):
        raise RuntimeError("R316 parent authority contract mismatch")
    return model, model_digest, analysis, analysis_digest


def prepare(seal_path: Path) -> str:
    _model, model_digest, _analysis, analysis_digest = _load_parent()
    r321_digest = _verified_digest_only(R321_ANALYSIS)
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "parent": {
            "dynamic_model": {"path": _path_text(PARENT_MODEL), "sha256": model_digest},
            "analysis": {"path": _path_text(PARENT_ANALYSIS), "sha256": analysis_digest},
            "r321_analysis_hash_only": {
                "path": _path_text(R321_ANALYSIS),
                "sha256": r321_digest,
                "access": "HASH-ONLY-NO-PARSE",
            },
        },
        "sources": _sources(),
    }
    return _write_new_json(seal_path, seal)


def _load_seal(path: Path, expected: str) -> tuple[dict[str, Any], str]:
    seal, digest = _read_verified_json(path, expected)
    contract = build_contract()
    _model, model_digest, _analysis, analysis_digest = _load_parent()
    r321_digest = _verified_digest_only(R321_ANALYSIS)
    if (
        seal.get("round") != ROUND_ID
        or seal.get("question") != QUESTION_ID
        or seal.get("contract") != contract
        or seal.get("contract_payload_sha256") != _payload_sha256(contract)
        or seal.get("parent")
        != {
            "dynamic_model": {"path": _path_text(PARENT_MODEL), "sha256": model_digest},
            "analysis": {"path": _path_text(PARENT_ANALYSIS), "sha256": analysis_digest},
            "r321_analysis_hash_only": {
                "path": _path_text(R321_ANALYSIS),
                "sha256": r321_digest,
                "access": "HASH-ONLY-NO-PARSE",
            },
        }
        or seal.get("sources") != _sources()
    ):
        raise RuntimeError("R325 seal contract, parent, or source drift")
    return seal, digest


def _models(
    model: dict[str, Any],
) -> tuple[dict[str, StateSpaceRealization], dict[str, np.ndarray]]:
    points = model.get("points")
    if not isinstance(points, dict) or set(points) != set(POINT_SOC):
        raise RuntimeError("R316 point set mismatch")
    retained = {
        name: realization_from_dict(entry["realization"])
        for name, entry in points.items()
    }
    markov = {
        name: np.asarray(entry["markov_parameters"], dtype=float)
        for name, entry in points.items()
    }
    if not all(item.state_matrix.shape == (10, 10) for item in retained.values()):
        raise RuntimeError("R316 realization order mismatch")
    return retained, markov


def _cross_deleted_models(
    markov: dict[str, np.ndarray],
) -> dict[str, StateSpaceRealization]:
    config = build_contract()["matched_baseline"]
    result: dict[str, StateSpaceRealization] = {}
    for point, tensor in markov.items():
        realization = fit_era_realization(
            delete_common_differential_markov_blocks(tensor),
            order=config["era_order"],
            block_rows=config["block_rows"],
            block_columns=config["block_columns"],
        )
        if realization.spectral_radius > config["maximum_model_spectral_radius"]:
            realization = enforce_spectral_radius(
                realization,
                maximum_radius=config["maximum_model_spectral_radius"],
            )
        result[point] = realization
    return result


def _designs(
    models: dict[str, StateSpaceRealization],
) -> tuple[dict[str, object], bool, str | None]:
    contract = build_contract()
    controller = contract["controller"]
    observer = contract["observer"]
    designs: dict[str, object] = {}
    try:
        for point, realization in models.items():
            design = synthesize_constrained_horizon(
                realization,
                output_scales=controller["output_scales"][point],
                action_scales=controller["action_scales"],
                observer_target_poles=observer["target_poles"],
                horizon_steps=controller["horizon_steps"],
                method=observer["method"],
                relative_tolerance=observer["relative_tolerance"],
                maximum_iterations=observer["maximum_iterations"],
            )
            if design.observer_target_max_abs_error > observer["target_absolute_tolerance"]:
                raise RuntimeError("observer target tolerance failed")
            designs[point] = design
    except (ValueError, RuntimeError, np.linalg.LinAlgError) as exc:
        return {}, False, str(exc)
    return designs, True, None


def _zero_energy(
    plant: StateSpaceRealization,
    case: FeedbackCase,
    mismatch: np.ndarray,
) -> float:
    output = simulate_state_space(plant, case.disturbance)
    delivered = output + output @ mismatch.T
    return float(np.sum(np.square(delivered)))


def _evaluate_phase(
    arm: str,
    phase: str,
    plants: dict[str, StateSpaceRealization],
    designs: dict[str, object],
    cases: list[FeedbackCase],
    transforms: dict[str, np.ndarray],
) -> list[dict[str, Any]]:
    limits = FeedbackLimits()
    solver = build_contract()["solver"]
    rows: list[dict[str, Any]] = []
    for case in cases:
        for mismatch_name, mismatch in transforms.items():
            zero_energy = _zero_energy(plants[case.point], case, mismatch)
            row: dict[str, Any] = {
                "arm": arm,
                "phase": phase,
                "case": case.name,
                "mismatch": mismatch_name,
                "zero_output_energy": zero_energy,
            }
            try:
                trace = simulate_constrained_horizon_feedback(
                    plants[case.point],
                    case.disturbance,
                    design=designs[case.point],
                    initial_soc=case.initial_soc,
                    limits=limits,
                    mismatch_transform=mismatch,
                    maximum_solver_iterations=solver["maximum_iterations"],
                    function_tolerance=solver["function_tolerance"],
                    feasibility_tolerance=solver["feasibility_tolerance"],
                )
                if zero_energy <= np.finfo(float).tiny:
                    raise RuntimeError("zero-control output energy is degenerate")
                ratio = trace.output_energy / zero_energy
                ramp = np.vstack(
                    (trace.node_actions[:1], np.diff(trace.node_actions, axis=0))
                )
                row.update(
                    {
                        "solver_failed": False,
                        "execution_error": False,
                        "output_energy": trace.output_energy,
                        "output_energy_ratio": float(ratio),
                        "coordinate_action_energy": trace.coordinate_action_energy,
                        "maximum_node_power": float(np.max(np.abs(trace.node_actions))),
                        "maximum_node_ramp": float(np.max(np.abs(ramp))),
                        "minimum_soc": float(np.min(trace.soc)),
                        "maximum_soc": float(np.max(trace.soc)),
                        "maximum_solver_iterations": int(
                            np.max(trace.solver_iterations)
                        ),
                        "maximum_constraint_residual": trace.maximum_constraint_residual,
                        "constraint_violation_count": trace.constraint_violation_count,
                    }
                )
            except ConstrainedHorizonInfeasible as exc:
                row.update(
                    {
                        "solver_failed": True,
                        "execution_error": False,
                        "error": str(exc),
                    }
                )
            except (RuntimeError, ValueError) as exc:
                row.update(
                    {
                        "solver_failed": False,
                        "execution_error": True,
                        "error": str(exc),
                    }
                )
            rows.append(row)
    return rows


def _execute_payload(
    seal: dict[str, Any],
    seal_digest: str,
    *,
    created_utc: str,
) -> dict[str, Any]:
    parent, model_digest, _analysis, analysis_digest = _load_parent()
    retained, markov = _models(parent)
    synthesis_models = {
        "retained_cross": retained,
        "cross_deleted": _cross_deleted_models(markov),
    }
    arms: dict[str, dict[str, Any]] = {}
    nominal = {"nominal": np.zeros((4, 4))}
    for arm, models in synthesis_models.items():
        designs, feasible, error = _designs(models)
        arm_payload: dict[str, Any] = {
            "observer_synthesis_succeeded": feasible,
            "observer_synthesis_error": error,
            "rows": {"development": []},
        }
        if feasible:
            arm_payload["rows"]["development"] = _evaluate_phase(
                arm,
                "development",
                retained,
                designs,
                development_cases(),
                nominal,
            )
        arms[arm] = arm_payload

    payload: dict[str, Any] = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": created_utc,
        "seal_sha256": seal_digest,
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "dynamic_model_sha256": model_digest,
        "parent_analysis_sha256": analysis_digest,
        "sealed_source_identity": True,
        "r321_analysis_access": "HASH-ONLY-NO-PARSE",
        "holdout_accessed": False,
        "arms": arms,
        "eval": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
    holdout_accessed = development_allows_holdout(payload, seal["contract"])
    payload["holdout_accessed"] = holdout_accessed
    if holdout_accessed:
        for arm, models in synthesis_models.items():
            designs, feasible, error = _designs(models)
            if not feasible:
                arms[arm]["observer_synthesis_succeeded"] = False
                arms[arm]["observer_synthesis_error"] = error
                continue
            arms[arm]["rows"]["holdout"] = _evaluate_phase(
                arm,
                "holdout",
                retained,
                designs,
                holdout_cases(),
                mismatch_transforms(),
            )
    return payload


def execute(seal_path: Path, expected: str, out_dir: Path) -> str:
    seal, seal_digest = _load_seal(seal_path, expected)
    created_utc = datetime.now(UTC).isoformat()
    first = _execute_payload(
        seal,
        seal_digest,
        created_utc=created_utc,
    )
    second = _execute_payload(
        seal,
        seal_digest,
        created_utc=created_utc,
    )
    first["deterministic_execution_replay"] = bool(
        _canonical_bytes(first) == _canonical_bytes(second)
    )
    return _write_new_json(out_dir / "execution.json", first)


def analyse(seal_path: Path, expected: str, out_dir: Path) -> dict[str, str]:
    seal, seal_digest = _load_seal(seal_path, expected)
    execution, execution_digest = _read_verified_json(out_dir / "execution.json")
    execution_view = dict(execution)
    execution_view["execution_sha256"] = execution_digest
    first = analyse_r325_execution(
        execution_view,
        seal["contract"],
        analysis_replay=True,
    )
    second = analyse_r325_execution(
        execution_view,
        seal["contract"],
        analysis_replay=True,
    )
    deterministic = _canonical_bytes(first) == _canonical_bytes(second)
    if not deterministic:
        first = analyse_r325_execution(
            execution_view,
            seal["contract"],
            analysis_replay=False,
        )
    analysis_digest = _write_new_json(out_dir / "analysis.json", first)
    provenance = {
        "round": ROUND_ID,
        "seal_sha256": seal_digest,
        "execution_sha256": execution_digest,
        "analysis_sha256": analysis_digest,
        "sources": seal["sources"],
        "parent": seal["parent"],
    }
    provenance_digest = _write_new_json(out_dir / "provenance.json", provenance)
    manifest = {
        "round": ROUND_ID,
        "classification": first["classification"],
        "files": {
            "execution.json": execution_digest,
            "analysis.json": analysis_digest,
            "provenance.json": provenance_digest,
        },
    }
    manifest_digest = _write_new_json(out_dir / "run_manifest.json", manifest)
    return {
        "classification": str(first["classification"]),
        "execution_sha256": execution_digest,
        "analysis_sha256": analysis_digest,
        "provenance_sha256": provenance_digest,
        "run_manifest_sha256": manifest_digest,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("prepare", "execute", "analyse"):
        item = subparsers.add_parser(command)
        item.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
        if command != "prepare":
            item.add_argument("--expected-sha256", required=True)
            item.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare":
        print(prepare(args.seal))
    elif args.command == "execute":
        print(execute(args.seal, args.expected_sha256, args.out))
    else:
        print(json.dumps(analyse(args.seal, args.expected_sha256, args.out), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
