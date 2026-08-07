"""Rehearse, seal, and execute the create-only R362 shared-prediction gate.

The adapter rebuilds the R359 exact fifteen-field causal observations,
attaches the frozen R341-model shared-prediction messages (four-step open-loop
frequency-deviation prediction per one-hop neighbour node, twenty-three fields
total), fits the four pre-registered frozen non-neural map families (fixed
affine, RBF kernel ridge, k-NN, quadratic polynomial basis) per physical edge,
and evaluates development leave-one-scenario-out per family.  Any passing
family yields the registered four-way OR classification; a failure of every
family further weakens the surveyed information-path hypothesis and stops this
route.  A failed development gate stops before the frozen holdout controller,
holdout counterfactuals, simulation, or training.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"


ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from probes import r353_matched_residual_headroom as r353_probe  # noqa: E402
from probes.r362_shared_prediction_residual import (  # noqa: E402
    SHARED_PREDICTION_FAMILY,
    build_shared_prediction_observations_from_parent_inventory,
    classify_shared_prediction_gate,
    leave_one_scenario_out_family_proposals,
    predict_holdout_with_frozen_family,
)
from scripts import run_r344_deterministic_bridge as r344_parent  # noqa: E402
from scripts import run_r353_matched_residual_headroom as r353_parent  # noqa: E402
from scripts import run_r359_neighbour_causal_residual as r359_parent  # noqa: E402
from scripts import run_r360_flexible_neighbour_residual as r360_parent  # noqa: E402
from scripts import run_r361_neighbour_message_residual as r361_parent  # noqa: E402

from andes_rl_kundur.control.active_power import (  # noqa: E402
    r272_frozen_bess_contract,
)
from andes_rl_kundur.control.neighbour_message_residual import (  # noqa: E402
    ONE_HOP_NEIGHBOUR_MESSAGES,
)
from andes_rl_kundur.control.residual_headroom import endpoint_values  # noqa: E402
from andes_rl_kundur.control.shared_prediction_residual import (  # noqa: E402
    PREDICTION_STEPS,
    SHARED_PREDICTION_OBSERVATION_DIMENSION,
)
from andes_rl_kundur.env.andes.model_first_contract import ACTION_EDGES  # noqa: E402

ROUND_ID = "R362"
QUESTION_ID = "Q-0099"
SAMPLES_PER_TRACE = 25
STARTUP_ZERO_STEPS = 2
EDGE_FLOW_LIMIT = 0.05
MINIMUM_IMPROVEMENT = 0.02
CONFIDENCE_LEVEL = 0.95
MAXIMUM_SINGLE_SCENARIO_RATIO = 1.05
MODEL_ADEQUACY_TOLERANCE = 1.0e-8
MAXIMUM_ITERATIONS = 20_000
FUNCTION_TOLERANCE = 1.0e-9
FEASIBILITY_TOLERANCE = 1.0e-8

PLAN = ROOT / "memory/rounds/R362/plan.md"
QUESTION = ROOT / "memory/questions/Q-0099.md"
CAPACITY = ROOT / "memory/rounds/R362/capacity_evidence.json"
DEFAULT_REHEARSAL = ROOT / "memory/rounds/R362/rehearsal.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R362/analysis_seal.json"
DEFAULT_OUT = ROOT / "results/r362_shared_prediction_residual"
R358_ANALYSIS = ROOT / "results/r358_physical_joint_endpoint_qp/analysis.json"
R358_MANIFEST = ROOT / "results/r358_physical_joint_endpoint_qp/manifest.json"
R358_SEAL = ROOT / "memory/rounds/R358/analysis_seal.json"
R358_CLAIM = ROOT / "memory/claims/CLM-0940.md"
R358_VERDICT = ROOT / "memory/rounds/R358/verdict.md"
R358_FEED = ROOT / "paper/decoupling_marl_model_first/reports/R358.md"
R359_ANALYSIS = ROOT / "results/r359_neighbour_causal_residual/analysis.json"
R359_MANIFEST = ROOT / "results/r359_neighbour_causal_residual/manifest.json"
R359_SEAL = ROOT / "memory/rounds/R359/analysis_seal.json"
R359_CLAIM = ROOT / "memory/claims/CLM-0945.md"
R359_VERDICT = ROOT / "memory/rounds/R359/verdict.md"
R359_FEED = ROOT / "paper/decoupling_marl_model_first/reports/R359.md"
R360_ANALYSIS = ROOT / "results/r360_flexible_neighbour_residual/analysis.json"
R360_MANIFEST = ROOT / "results/r360_flexible_neighbour_residual/manifest.json"
R360_SEAL = ROOT / "memory/rounds/R360/analysis_seal.json"
R360_CLAIM = ROOT / "memory/claims/CLM-0950.md"
R360_VERDICT = ROOT / "memory/rounds/R360/verdict.md"
R360_FEED = ROOT / "paper/decoupling_marl_model_first/reports/R360.md"
R361_ANALYSIS = ROOT / "results/r361_neighbour_message_residual/analysis.json"
R361_MANIFEST = ROOT / "results/r361_neighbour_message_residual/manifest.json"
R361_SEAL = ROOT / "memory/rounds/R361/analysis_seal.json"
R361_CLAIM = ROOT / "memory/claims/CLM-0955.md"
R361_VERDICT = ROOT / "memory/rounds/R361/verdict.md"
R361_FEED = ROOT / "paper/decoupling_marl_model_first/reports/R361.md"


def build_contract() -> dict[str, Any]:
    """Return the prospectively frozen shared-prediction analysis contract."""

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "shared-prediction-neighbour-learnability-gate",
        "inventory": {
            "development_pairs": 16,
            "holdout_pairs": 16,
            "positive_development_targets": 10,
            "zero_development_targets": 6,
            "samples_per_trace": SAMPLES_PER_TRACE,
        },
        "information": {
            "edge_actor_count": 3,
            "continuous_fields_per_actor": SHARED_PREDICTION_OBSERVATION_DIMENSION,
            "own_fields": 15,
            "prediction_message_fields": PREDICTION_STEPS,
            "neighbours_per_edge": 2,
            "prediction_steps": PREDICTION_STEPS,
            "one_hop_neighbour_table": {
                str(edge): list(message) for edge, message in ONE_HOP_NEIGHBOUR_MESSAGES.items()
            },
            "message_content": "frozen R341-model causal open-loop frequency-deviation prediction (Hz)",
            "startup_zero_steps": STARTUP_ZERO_STEPS,
            "forbidden_fields": [
                "achieved_power",
                "operating_point",
                "disturbance_channel",
                "disturbance_sign",
                "scenario_identity",
                "other_edge_actions",
                "neighbour_commands",
                "neighbour_edge_flows",
                "future_realized_values",
                "realized_endpoints",
                "oracle_values",
            ],
        },
        "prediction_generator": {
            "model": "R341 order-12 separate-input point model per operating point",
            "estimator": "disturbance-augmented, frozen R344 output scales",
            "disturbance_scale": 0.05,
            "measurement_fraction": 0.01,
            "future_residual_control": "zero",
            "future_disturbance": "held at estimated value",
            "horizon_steps": PREDICTION_STEPS,
            "tuning_executed": False,
        },
        "controller_family": {
            "members": sorted(SHARED_PREDICTION_FAMILY),
            "affine": {"standardization": "train-fold", "sweep": False},
            "rbf_kernel_ridge": {
                "width": "training-pair-median-distance heuristic",
                "regularization": 1.0e-3,
                "sweep": False,
            },
            "knn": {"k": 5, "distance": "standardized-euclidean", "sweep": False},
            "quadratic_polynomial": {
                "degree": 2,
                "basis": "all first-order plus pairwise interactions",
                "regularization": "none",
                "sweep": False,
            },
            "development_validation": "leave-one-scenario-out",
            "selection_semantics": "pre-registered OR over all members",
            "tuning_executed": False,
        },
        "statistics": {
            "minimum_improvement_fraction": MINIMUM_IMPROVEMENT,
            "confidence_level": CONFIDENCE_LEVEL,
            "maximum_single_scenario_ratio": MAXIMUM_SINGLE_SCENARIO_RATIO,
            "paired_bootstrap_resamples": 10_000,
        },
        "gates": {
            "development": "nominal and mismatch-bounded endpoint groups per family",
            "holdout": "never read unless every development family passes",
            "stop_rule": "all families fail both endpoint groups -> information-path hypothesis further weakened, route stops",
        },
        "authorization": {
            "training": False,
            "simulation": False,
            "eval": False,
            "holdout_residual_labels_read": 0,
        },
    }


def source_paths(*, include_rehearsal: bool) -> dict[str, Path]:
    """Return the complete R362 implementation closure."""

    paths = {
        "plan": PLAN,
        "question": QUESTION,
        "capacity": CAPACITY,
        "adapter": Path(__file__).resolve(),
        "probe": ROOT / "probes/r362_shared_prediction_residual.py",
        "probe_tests": ROOT / "tests/test_r362_shared_prediction_residual.py",
        "controller_src": ROOT / "src/andes_rl_kundur/control/shared_prediction_residual.py",
        "adapter_tests": ROOT / "tests/test_r362_shared_prediction_residual_analysis.py",
        "r361_adapter": Path(r361_parent.__file__).resolve(),
        "r361_probe": ROOT / "probes/r361_neighbour_message_residual.py",
        "r360_adapter": Path(r360_parent.__file__).resolve(),
        "r360_probe": ROOT / "probes/r360_flexible_neighbour_residual.py",
        "r359_adapter": Path(r359_parent.__file__).resolve(),
        "r359_probe": ROOT / "probes/r359_neighbour_causal_residual.py",
        "r353_adapter": Path(r353_parent.__file__).resolve(),
        "r353_probe": Path(r353_probe.__file__).resolve(),
        "r344_adapter": Path(r344_parent.__file__).resolve(),
    }
    package_root = ROOT / "src/andes_rl_kundur"
    for path in sorted(package_root.rglob("*.py")):
        relative = path.relative_to(package_root).as_posix()
        paths[f"package_{relative}"] = path
    if include_rehearsal:
        paths["rehearsal"] = DEFAULT_REHEARSAL
    return paths


def parent_paths() -> dict[str, Path]:
    """Return exact R341/R352 trace parents plus terminal R358-R361 evidence."""

    paths = dict(r353_parent.parent_paths())
    paths.update(
        {
            "r344_adapter": Path(r344_parent.__file__).resolve(),
            "r358_analysis": R358_ANALYSIS,
            "r358_manifest": R358_MANIFEST,
            "r358_seal": R358_SEAL,
            "r358_claim": R358_CLAIM,
            "r358_verdict": R358_VERDICT,
            "r358_feed": R358_FEED,
            "r359_analysis": R359_ANALYSIS,
            "r359_manifest": R359_MANIFEST,
            "r359_seal": R359_SEAL,
            "r359_claim": R359_CLAIM,
            "r359_verdict": R359_VERDICT,
            "r359_feed": R359_FEED,
            "r360_analysis": R360_ANALYSIS,
            "r360_manifest": R360_MANIFEST,
            "r360_seal": R360_SEAL,
            "r360_claim": R360_CLAIM,
            "r360_verdict": R360_VERDICT,
            "r360_feed": R360_FEED,
            "r361_analysis": R361_ANALYSIS,
            "r361_manifest": R361_MANIFEST,
            "r361_seal": R361_SEAL,
            "r361_claim": R361_CLAIM,
            "r361_verdict": R361_VERDICT,
            "r361_feed": R361_FEED,
        }
    )
    return paths


def _record(path: Path) -> dict[str, str]:
    try:
        rendered = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        rendered = path.resolve().as_posix()
    return {"path": rendered, "sha256": r353_parent._sha256_file(path)}


def _source_snapshot(
    *,
    include_rehearsal: bool,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
) -> dict[str, dict[str, str]]:
    paths = source_paths(include_rehearsal=False)
    if include_rehearsal:
        paths["rehearsal"] = rehearsal_path
    return {name: _record(path) for name, path in paths.items()}


def _parent_snapshot() -> dict[str, dict[str, str]]:
    return {name: _record(path) for name, path in parent_paths().items()}


def _verify_r358_parent() -> dict[str, Any]:
    for path in (R358_ANALYSIS, R358_MANIFEST, R358_SEAL):
        r353_parent._verify_sidecar(path)
    analysis = r353_parent._read_json(R358_ANALYSIS)
    if (
        analysis.get("round") != "R358"
        or analysis.get("question") != "Q-0095"
        or analysis.get("classification") != "PHYSICAL-HEADROOM-FOUND"
        or analysis.get("accepted_physical_feasible_candidate_count") != 10
        or analysis.get("inherited_relaxed_infeasible_count") != 6
        or analysis.get("information_constraints_included") is not False
        or analysis.get("physical_constraints_included") is not True
        or analysis.get("holdout_cases_read") != 0
        or analysis.get("training_authorized") is not False
        or analysis.get("simulation_authorized") is not False
    ):
        raise RuntimeError("R358 parent decision drift")
    candidates = analysis.get("candidate_results")
    partition = analysis.get("r356_status_partition")
    if (
        not isinstance(candidates, list)
        or len(candidates) != 10
        or not all(
            row.get("accepted") is True and row.get("target_feasible") is True for row in candidates
        )
        or not isinstance(partition, Mapping)
        or len(partition.get("primal_infeasible", [])) != 6
    ):
        raise RuntimeError("R358 target partition drift")
    return analysis


def _verify_r359_parent() -> dict[str, Any]:
    for path in (R359_ANALYSIS, R359_MANIFEST, R359_SEAL):
        r353_parent._verify_sidecar(path)
    analysis = r353_parent._read_json(R359_ANALYSIS)
    if (
        analysis.get("round") != "R359"
        or analysis.get("question") != "Q-0096"
        or analysis.get("classification") != "NO-NEIGHBOUR-CAUSAL-HEADROOM"
        or analysis.get("holdout_cases_read") != 0
        or analysis.get("holdout_residual_labels_read") != 0
        or analysis.get("training_authorized") is not False
        or analysis.get("simulation_authorized") is not False
    ):
        raise RuntimeError("R359 parent decision drift")
    return analysis


def _verify_r360_parent() -> dict[str, Any]:
    for path in (R360_ANALYSIS, R360_MANIFEST, R360_SEAL):
        r353_parent._verify_sidecar(path)
    analysis = r353_parent._read_json(R360_ANALYSIS)
    if (
        analysis.get("round") != "R360"
        or analysis.get("question") != "Q-0097"
        or analysis.get("classification") != "NO-NEIGHBOUR-LEARNABLE-STRUCTURE"
        or analysis.get("holdout_cases_read") != 0
        or analysis.get("holdout_residual_labels_read") != 0
        or analysis.get("training_authorized") is not False
        or analysis.get("simulation_authorized") is not False
    ):
        raise RuntimeError("R360 parent decision drift")
    return analysis


def _verify_r361_parent() -> dict[str, Any]:
    for path in (R361_ANALYSIS, R361_MANIFEST, R361_SEAL):
        r353_parent._verify_sidecar(path)
    analysis = r353_parent._read_json(R361_ANALYSIS)
    if (
        analysis.get("round") != "R361"
        or analysis.get("question") != "Q-0098"
        or analysis.get("classification") != "NO-NEIGHBOUR-LEARNABLE-STRUCTURE"
        or analysis.get("holdout_cases_read") != 0
        or analysis.get("holdout_residual_labels_read") != 0
        or analysis.get("training_authorized") is not False
        or analysis.get("simulation_authorized") is not False
    ):
        raise RuntimeError("R361 parent decision drift")
    return analysis


def _verify_entry_preconditions(
    out_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if out_dir.exists():
        raise FileExistsError(f"R362 result root already exists: {out_dir}")
    if "state: active" not in PLAN.read_text(encoding="utf-8"):
        raise RuntimeError("R362 active plan identity is missing")
    question_text = QUESTION.read_text(encoding="utf-8")
    if "status: in-flight" not in question_text or "R362:" not in question_text:
        raise RuntimeError("R362 in-flight question identity is missing")
    for path in source_paths(include_rehearsal=False).values():
        if not path.is_file():
            raise RuntimeError(f"R362 source is missing: {path}")
    r353_parent._verify_parent_decisions()
    _verify_r358_parent()
    _verify_r359_parent()
    _verify_r360_parent()
    _verify_r361_parent()
    development = r353_parent.load_parent_inventory("development")
    holdout = r353_parent.load_parent_inventory("holdout")
    if len(development) != 16 or len(holdout) != 16:
        raise RuntimeError("R362 requires sixteen exact pairs per bank")
    return development, holdout, r353_parent._read_json(R358_ANALYSIS)


def _observations(
    inventory: Sequence[Mapping[str, Any]],
) -> dict[str, dict[tuple[int, int], tuple[Any, ...]]]:
    from scripts.run_r344_deterministic_bridge import OUTPUT_SCALES
    from scripts.run_r353_matched_residual_headroom import (
        R341_CANDIDATE_MODELS,
        POINT_MODEL_DIGESTS,
    )

    return build_shared_prediction_observations_from_parent_inventory(
        inventory=inventory,
        physical_contract=r272_frozen_bess_contract(),
        candidate_models=r353_parent._read_json(R341_CANDIDATE_MODELS),
        point_model_digests=POINT_MODEL_DIGESTS,
        output_scales_by_point=OUTPUT_SCALES,
        nominal_frequency_hz=60.0,
        sample_period_seconds=0.2,
        startup_zero_steps=STARTUP_ZERO_STEPS,
        expected_horizon=SAMPLES_PER_TRACE,
    )


def _targets(
    cases: Sequence[Mapping[str, Any]],
    r358: Mapping[str, Any],
) -> dict[str, np.ndarray]:
    from probes.r359_neighbour_causal_residual import build_development_targets

    return build_development_targets(
        scenario_ids=[str(case["scenario_id"]) for case in cases],
        candidate_results=r358["candidate_results"],
        inherited_infeasible_scenario_ids=r358["r356_status_partition"]["primal_infeasible"],
        horizon=SAMPLES_PER_TRACE,
        edge_flow_limit_system_pu=EDGE_FLOW_LIMIT,
        startup_zero_steps=STARTUP_ZERO_STEPS,
    )


def _baseline_rows(cases: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": str(case["scenario_id"]),
            "base_endpoints": endpoint_values(
                case["base_outputs"],
                sample_period_seconds=0.2,
            ),
        }
        for case in cases
    ]


def _endpoint_gates(
    cases: Sequence[Mapping[str, Any]],
    projected: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    baseline = _baseline_rows(cases)
    return {
        "nominal": r353_probe.candidate_gate(
            cases,
            baseline,
            projected,
            candidate="local",
            endpoint_field="nominal_endpoints",
            minimum_improvement_fraction=MINIMUM_IMPROVEMENT,
            confidence_level=CONFIDENCE_LEVEL,
            maximum_single_scenario_ratio=MAXIMUM_SINGLE_SCENARIO_RATIO,
        ),
        "mismatch_bounded": r353_probe.candidate_gate(
            cases,
            baseline,
            projected,
            candidate="local",
            endpoint_field="mismatch_bounded_endpoints",
            minimum_improvement_fraction=MINIMUM_IMPROVEMENT,
            confidence_level=CONFIDENCE_LEVEL,
            maximum_single_scenario_ratio=MAXIMUM_SINGLE_SCENARIO_RATIO,
        ),
    }


def _project_cases(
    cases: Sequence[Mapping[str, Any]],
    proposals: Mapping[str, np.ndarray],
) -> list[dict[str, Any]]:
    return [
        r353_probe.project_local_case(
            case,
            proposals[str(case["scenario_id"])] * EDGE_FLOW_LIMIT,
            maximum_iterations=MAXIMUM_ITERATIONS,
            function_tolerance=FUNCTION_TOLERANCE,
            feasibility_tolerance=FEASIBILITY_TOLERANCE,
        )
        for case in cases
    ]


def _family_gates(
    cases: Sequence[Mapping[str, Any]],
    family_proposals: Mapping[str, Mapping[str, np.ndarray]],
) -> dict[str, dict[str, Any]]:
    return {
        name: _endpoint_gates(cases, _project_cases(cases, proposals))
        for name, proposals in family_proposals.items()
    }


def _development_stage(
    inventory: Sequence[Mapping[str, Any]],
    r358: Mapping[str, Any],
) -> dict[str, Any]:
    cases = r353_parent._build_cases(list(inventory))
    envelopes = r353_probe.development_envelopes(cases)
    r353_probe.assign_envelopes(cases, envelopes)
    observations = _observations(inventory)
    targets = _targets(cases, r358)
    family_proposals = leave_one_scenario_out_family_proposals(
        observations_by_scenario=observations,
        normalized_targets_by_scenario=targets,
        horizon=SAMPLES_PER_TRACE,
        startup_zero_steps=STARTUP_ZERO_STEPS,
    )
    family_gates = _family_gates(cases, family_proposals)
    family_projected = {
        name: _project_cases(cases, proposals)
        for name, proposals in family_proposals.items()
    }
    integrity = {
        "complete_inventory": len(cases) == 16 and len(observations) == 16 and len(targets) == 16,
        "exact_information": all(
            len(edge_rows) == 3
            and all(
                len(rows) == SAMPLES_PER_TRACE - STARTUP_ZERO_STEPS for rows in edge_rows.values()
            )
            for edge_rows in observations.values()
        ),
        "neighbour_table_frozen": all(
            set(edge_rows) == set(ACTION_EDGES)
            and all(
                row.edge == edge
                and row.source_neighbour_prediction.node_id
                == ONE_HOP_NEIGHBOUR_MESSAGES[edge][0]
                and row.target_neighbour_prediction.node_id
                == ONE_HOP_NEIGHBOUR_MESSAGES[edge][1]
                for edge, rows in edge_rows.items()
                for row in rows
            )
            for edge_rows in observations.values()
        ),
        "prediction_horizon_frozen": all(
            all(
                np.asarray(row.source_neighbour_prediction.values_hz).shape
                == (PREDICTION_STEPS,)
                and np.asarray(row.target_neighbour_prediction.values_hz).shape
                == (PREDICTION_STEPS,)
                for rows in edge_rows.values()
                for row in rows
            )
            for edge_rows in observations.values()
        ),
        "startup_mask": all(
            np.array_equal(
                proposal[:STARTUP_ZERO_STEPS],
                np.zeros((STARTUP_ZERO_STEPS, 3)),
            )
            for proposals in family_proposals.values()
            for proposal in proposals.values()
        ),
        "physical_projection": all(
            row.get("feasible") is True
            for projections in family_projected.values()
            for row in projections
        ),
    }
    family_scientific = {
        name: {
            "nominal_endpoints": gates["nominal"]["pass"],
            "mismatch_bounded_endpoints": gates["mismatch_bounded"]["pass"],
        }
        for name, gates in family_gates.items()
    }
    decision = classify_shared_prediction_gate(
        integrity_checks=integrity,
        family_scientific_checks=family_scientific,
    )
    return {
        "cases": cases,
        "envelopes": envelopes,
        "observations": observations,
        "targets": targets,
        "family_proposals": family_proposals,
        "family_projected": family_projected,
        "family_gates": family_gates,
        "integrity_checks": integrity,
        "family_scientific_checks": family_scientific,
        "decision": decision,
    }


def _controller_payload(controllers: Mapping[tuple[int, int], Any]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for edge in ACTION_EDGES:
        controller = controllers[edge]
        row: dict[str, Any] = {"edge": list(edge)}
        for field, value in vars(controller).items():
            if isinstance(value, np.ndarray):
                row[field] = value.tolist()
            elif isinstance(value, (int, float, str, tuple)):
                row[field] = value
        payload.append(row)
    return payload


def _fit_full_development_family(
    *,
    family_name: str,
    observations_by_scenario: Mapping[str, Any],
    normalized_targets_by_scenario: Mapping[str, Any],
    horizon: int,
    startup_zero_steps: int,
) -> dict[tuple[int, int], Any]:
    """Fit one frozen family once on every development scenario."""

    from probes.r362_shared_prediction_residual import _fit_family

    controllers = _fit_family(
        training_scenario_ids=tuple(
            sorted(str(item) for item in observations_by_scenario)
        ),
        observations_by_scenario=observations_by_scenario,
        normalized_targets_by_scenario=normalized_targets_by_scenario,
        horizon=int(horizon),
        startup_zero_steps=int(startup_zero_steps),
    )
    return controllers[family_name]


def _verify_entry_closed(out_dir: Path) -> None:
    _verify_entry_preconditions(out_dir)


def rehearsal(
    record_path: Path = DEFAULT_REHEARSAL,
    *,
    out_dir: Path = DEFAULT_OUT,
) -> str:
    """Exercise the same pre-attempt closure without outcome evaluation."""

    if record_path.exists():
        raise FileExistsError(f"create-only output already exists: {record_path}")
    development, holdout, r358 = _verify_entry_preconditions(out_dir)
    development_observations = _observations(development)
    holdout_observations = _observations(holdout)
    cases = r353_parent._build_cases(development)
    targets = _targets(cases, r358)
    if not (
        len(development_observations) == 16
        and len(holdout_observations) == 16
        and len(targets) == 16
        and sum(np.any(target, axis=None) for target in targets.values()) == 10
        and all(
            all(len(rows) == SAMPLES_PER_TRACE - STARTUP_ZERO_STEPS for rows in edge_rows.values())
            for edge_rows in (*development_observations.values(), *holdout_observations.values())
        )
    ):
        raise RuntimeError("R362 rehearsal inventory or observation check failed")
    contract = build_contract()
    return r353_parent._write_new_json(
        record_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_payload_sha256": r353_parent._payload_sha256(contract),
            "development_pair_count": len(development),
            "holdout_pair_count": len(holdout),
            "development_target_partition": {"positive": 10, "zero": 6},
            "observation_fields_per_edge": SHARED_PREDICTION_OBSERVATION_DIMENSION,
            "observation_rows_per_edge": SAMPLES_PER_TRACE - STARTUP_ZERO_STEPS,
            "prediction_steps": PREDICTION_STEPS,
            "family_members": sorted(SHARED_PREDICTION_FAMILY),
            "one_hop_neighbour_table": {
                str(edge): list(message) for edge, message in ONE_HOP_NEIGHBOUR_MESSAGES.items()
            },
            "holdout_residual_labels_read": 0,
            "source_snapshot": _source_snapshot(include_rehearsal=False),
            "parent_snapshot": _parent_snapshot(),
            "formal_output_absent": True,
            "attempt_created": False,
            "result_created": False,
            "simulator_executed": False,
            "training_executed": False,
        },
    )


def prepare(
    seal_path: Path = DEFAULT_SEAL,
    *,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
    out_dir: Path = DEFAULT_OUT,
) -> str:
    """Create the exact source-, parent-, and rehearsal-bound R362 seal."""

    if seal_path.exists():
        raise FileExistsError(f"create-only output already exists: {seal_path}")
    _verify_entry_preconditions(out_dir)
    r353_parent._verify_sidecar(rehearsal_path)
    record = r353_parent._read_json(rehearsal_path)
    contract = build_contract()
    sources = _source_snapshot(include_rehearsal=False)
    parents = _parent_snapshot()
    if (
        record.get("round") != ROUND_ID
        or record.get("question") != QUESTION_ID
        or record.get("contract_payload_sha256") != r353_parent._payload_sha256(contract)
        or record.get("development_pair_count") != 16
        or record.get("holdout_pair_count") != 16
        or record.get("development_target_partition") != {"positive": 10, "zero": 6}
        or record.get("observation_fields_per_edge")
        != SHARED_PREDICTION_OBSERVATION_DIMENSION
        or record.get("prediction_steps") != PREDICTION_STEPS
        or record.get("family_members") != sorted(SHARED_PREDICTION_FAMILY)
        or record.get("one_hop_neighbour_table")
        != {str(edge): list(message) for edge, message in ONE_HOP_NEIGHBOUR_MESSAGES.items()}
        or record.get("holdout_residual_labels_read") != 0
        or record.get("source_snapshot") != sources
        or record.get("parent_snapshot") != parents
        or record.get("formal_output_absent") is not True
        or record.get("attempt_created") is not False
    ):
        raise RuntimeError("R362 rehearsal record drift")
    return r353_parent._write_new_json(
        seal_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract": contract,
            "contract_payload_sha256": r353_parent._payload_sha256(contract),
            "sources": _source_snapshot(
                include_rehearsal=True,
                rehearsal_path=rehearsal_path,
            ),
            "parents": parents,
            "result_root_absent_at_freeze": True,
            "retry_authorized": False,
        },
    )


def load_seal(
    path: Path,
    expected_sha256: str,
    *,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
    out_dir: Path = DEFAULT_OUT,
) -> tuple[dict[str, Any], str]:
    """Verify the exact R362 seal and complete immutable closure."""

    payload = r353_parent._read_json(path)
    actual = r353_parent._sha256_file(path)
    if actual != expected_sha256:
        raise RuntimeError(f"R362 seal digest mismatch: {actual}")
    r353_parent._verify_sidecar(path)
    _verify_entry_preconditions(out_dir)
    contract = payload.get("contract")
    if (
        payload.get("round") != ROUND_ID
        or payload.get("question") != QUESTION_ID
        or contract != build_contract()
        or payload.get("contract_payload_sha256") != r353_parent._payload_sha256(contract)
        or payload.get("sources")
        != _source_snapshot(
            include_rehearsal=True,
            rehearsal_path=rehearsal_path,
        )
        or payload.get("parents") != _parent_snapshot()
        or payload.get("retry_authorized") is not False
    ):
        raise RuntimeError("R362 contract, source, or parent drift")
    return payload, actual


def analyse(
    expected_sha256: str,
    *,
    out_dir: Path = DEFAULT_OUT,
    seal_path: Path = DEFAULT_SEAL,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
) -> str:
    """Execute the single sealed staged offline R362 analysis."""

    seal, seal_digest = load_seal(
        seal_path,
        expected_sha256,
        rehearsal_path=rehearsal_path,
        out_dir=out_dir,
    )
    development_inventory, holdout_inventory, r358 = _verify_entry_preconditions(out_dir)
    out_dir.mkdir(parents=True, exist_ok=False)
    attempt_path = out_dir / "analysis_attempt.json"
    attempt_digest = r353_parent._write_new_json(
        attempt_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "worker_processes": 1,
            "native_threads_per_process": 1,
            "retry_authorized": False,
            "holdout_residual_labels_read": 0,
            "simulator_executed": False,
            "training_executed": False,
        },
    )
    started = time.perf_counter()
    try:
        development = _development_stage(development_inventory, r358)
        decision = development["decision"]
        holdout_payload: dict[str, Any] | None = None
        frozen_entries: list[dict[str, str]] = []
        holdout_cases_read = 0
        if decision["classification"] == "NEIGHBOUR-LEARNABLE-STRUCTURE-FOUND":
            passing = decision["passing_families"]
            controller_entries: list[dict[str, str]] = []
            for family_name in passing:
                controllers = _fit_full_development_family(
                    family_name=family_name,
                    observations_by_scenario=development["observations"],
                    normalized_targets_by_scenario=development["targets"],
                    horizon=SAMPLES_PER_TRACE,
                    startup_zero_steps=STARTUP_ZERO_STEPS,
                )
                controller_path = out_dir / f"frozen_controller_{family_name}.json"
                controller_digest = r353_parent._write_new_json(
                    controller_path,
                    {
                        "schema_version": 1,
                        "round": ROUND_ID,
                        "family": family_name,
                        "controllers": _controller_payload(controllers),
                        "development_scenario_ids": sorted(development["targets"]),
                        "holdout_labels_read_before_freeze": 0,
                    },
                )
                controller_entries.append(
                    {
                        "path": controller_path.relative_to(ROOT).as_posix(),
                        "sha256": controller_digest,
                    }
                )
                holdout_observations = _observations(holdout_inventory)
                normalized_predictions = {
                    scenario_id: predict_holdout_with_frozen_family(
                        controllers=controllers,
                        observations=rows,
                        horizon=SAMPLES_PER_TRACE,
                        startup_zero_steps=STARTUP_ZERO_STEPS,
                    )
                    for scenario_id, rows in holdout_observations.items()
                }
                predictions_path = out_dir / f"holdout_predictions_{family_name}.json"
                predictions_digest = r353_parent._write_new_json(
                    predictions_path,
                    {
                        "schema_version": 1,
                        "round": ROUND_ID,
                        "family": family_name,
                        "controller_sha256": controller_digest,
                        "predictions": {
                            key: value.tolist()
                            for key, value in sorted(normalized_predictions.items())
                        },
                        "holdout_labels_read_before_freeze": 0,
                    },
                )
                controller_entries.append(
                    {
                        "path": predictions_path.relative_to(ROOT).as_posix(),
                        "sha256": predictions_digest,
                    }
                )
            frozen_entries.extend(controller_entries)
            holdout_cases = r353_parent._build_cases(holdout_inventory)
            r353_probe.assign_envelopes(holdout_cases, development["envelopes"])
            adequacy = r353_probe.model_adequacy_gate(
                holdout_cases,
                development["envelopes"],
                absolute_tolerance=MODEL_ADEQUACY_TOLERANCE,
            )
            holdout_integrity = {
                "complete_inventory": len(holdout_cases) == 16,
                "frozen_controller_before_outcomes": True,
                "holdout_model_adequacy": adequacy["pass"],
            }
            holdout_scientific: dict[str, dict[str, bool]] = {}
            for family_name in passing:
                predictions_path = out_dir / f"holdout_predictions_{family_name}.json"
                predictions_payload = r353_parent._read_json(predictions_path)
                projected = _project_cases(holdout_cases, predictions_payload["predictions"])
                gates = _endpoint_gates(holdout_cases, projected)
                holdout_scientific[family_name] = {
                    "nominal_endpoints": gates["nominal"]["pass"],
                    "mismatch_bounded_endpoints": gates["mismatch_bounded"]["pass"],
                }
                holdout_integrity[f"physical_projection_{family_name}"] = all(
                    row.get("feasible") is True for row in projected
                )
            holdout_integrity["complete_inventory"] = (
                len(holdout_cases) == 16 and len(holdout_integrity) >= 3 + len(passing)
            )
            decision = classify_shared_prediction_gate(
                integrity_checks=holdout_integrity,
                family_scientific_checks=holdout_scientific,
            )
            holdout_payload = {
                "case_count": len(holdout_cases),
                "model_adequacy": adequacy,
                "family_scientific_checks": holdout_scientific,
                "integrity_checks": holdout_integrity,
                "decision": decision,
            }
            holdout_cases_read = len(holdout_cases)

        analysis_path = out_dir / "analysis.json"
        analysis_digest = r353_parent._write_new_json(
            analysis_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "seal_sha256": seal_digest,
                "contract_payload_sha256": seal["contract_payload_sha256"],
                "analysis_attempt_sha256": attempt_digest,
                "elapsed_seconds": time.perf_counter() - started,
                "classification": decision["classification"],
                "passing_families": decision.get("passing_families", []),
                "family_failed_scientific_checks": decision.get(
                    "family_failed_scientific_checks", {}
                ),
                "development": {
                    "case_count": len(development["cases"]),
                    "target_partition": {"positive": 10, "zero": 6},
                    "family_gates": development["family_gates"],
                    "integrity_checks": development["integrity_checks"],
                    "family_scientific_checks": development["family_scientific_checks"],
                    "decision": development["decision"],
                },
                "holdout": holdout_payload,
                "holdout_cases_read": holdout_cases_read,
                "holdout_residual_labels_read": 0,
                "exact_information_constraints_included": True,
                "physical_constraints_included": True,
                "shared_prediction_constraints_included": True,
                "simulation_authorized": False,
                "training_authorized": False,
                "distributed_runtime_executed": False,
                "eval_executed": False,
                "simulator_executed": False,
            },
        )
        manifest_path = out_dir / "manifest.json"
        manifest_digest = r353_parent._write_new_json(
            manifest_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "entries": [
                    {
                        "path": attempt_path.relative_to(ROOT).as_posix(),
                        "sha256": attempt_digest,
                    },
                    *frozen_entries,
                    {
                        "path": analysis_path.relative_to(ROOT).as_posix(),
                        "sha256": analysis_digest,
                    },
                ],
            },
        )
        print(f"classification={decision['classification']}", flush=True)
        print(f"analysis_sha256={analysis_digest}", flush=True)
        print(f"manifest_sha256={manifest_digest}", flush=True)
        return analysis_digest
    except Exception as error:
        failure_path = out_dir / "failure.json"
        if not failure_path.exists():
            r353_parent._write_new_json(
                failure_path,
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "question": QUESTION_ID,
                    "classification": "ANALYSIS-INVALID",
                    "created_utc": datetime.now(UTC).isoformat(),
                    "seal_sha256": seal_digest,
                    "analysis_attempt_sha256": attempt_digest,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "retry_authorized": False,
                    "holdout_cases_read": 0,
                    "training_authorized": False,
                    "simulation_authorized": False,
                },
            )
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("rehearsal")
    subparsers.add_parser("prepare")
    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--expected-seal-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rehearsal":
        print(f"rehearsal_sha256={rehearsal()}", flush=True)
    elif args.command == "prepare":
        print(f"seal_sha256={prepare()}", flush=True)
    else:
        analyse(str(args.expected_seal_sha256))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
