#!/usr/bin/env python3
"""Seal, fit, execute, EVAL-audit, and analyse the R314 local predictor."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for path in (ROOT, SRC, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from run_r313_model_first_predictor import (  # noqa: E402
    EXPECTED_EVAL_GUARDS,
    _load_r312_training,
    _path_text,
    _payload_sha256,
    _point,
    _read_verified_json,
    _record_path,
    _run_trace,
    _runtime_record,
    _sha256_file,
    _write_new_json,
)

from andes_rl_kundur.env.andes.model_first_contract import (  # noqa: E402
    Stage1OperatingPoint,
    stage1_power_coordinates,
)
from andes_rl_kundur.evaluation.model_first_predictor import (  # noqa: E402
    augment_predictor_with_development_point,
    fit_coupling_retaining_predictor,
)
from andes_rl_kundur.evaluation.model_first_stage1_eval_guards import (  # noqa: E402
    build_guarded_fresh_stage1_eval_view,
)
from probes.r313_predictor_validation import (  # noqa: E402
    evaluate_predictor_validation,
)

ROUND_ID = "R314"
QUESTION_ID = "Q-0070"
DEFAULT_SEAL = ROOT / "memory/rounds/R314/local_predictor_seal.json"
DEFAULT_OUT = ROOT / "results/r314_local_predictor"
R313_OUT = ROOT / "results/r313_model_first_predictor"
DEVELOPMENT_POINT = Stage1OperatingPoint("HP1", 180.0, 90.0, 1.20, 0.42)
DEVELOPMENT_AMPLITUDES = (0.025, 0.065)
EVAL_BOOTSTRAP_RESAMPLES = 10_000
EVAL_BOOTSTRAP_SEED = 2026080314


def _holdout_operating_points() -> list[dict[str, object]]:
    return [
        {
            "name": "HQ0",
            "vsg_m_device": 175.0,
            "vsg_d_device": 87.5,
            "tie_rx_scale": 1.10,
            "initial_soc": 0.40,
            "training_weights": {
                "OP0": 0.20,
                "OP1": 0.30,
                "OP2": 0.0,
                "HP1": 0.50,
            },
            "simplex": ["OP0", "OP1", "HP1"],
        },
        {
            "name": "HQ1",
            "vsg_m_device": 205.0,
            "vsg_d_device": 102.5,
            "tie_rx_scale": 1.40,
            "initial_soc": 0.52,
            "training_weights": {
                "OP0": 0.20,
                "OP1": 0.0,
                "OP2": 0.30,
                "HP1": 0.50,
            },
            "simplex": ["OP0", "OP2", "HP1"],
        },
    ]


def build_contract() -> dict[str, Any]:
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "sealed-local-simplex-predictor-holdout",
        "development_sources": {
            "R312": {"question": "Q-0068", "trace_count": 27},
            "R313_HP1_only": {
                "question": "Q-0069",
                "trace_count": 17,
                "amplitudes_system_pu": [0.025, 0.065],
            },
            "forbidden_R313_operating_points": ["HP0"],
            "total_trace_count": 44,
        },
        "model_authority": {
            "training_rounds": ["R312", "R313"],
            "training_questions": ["Q-0068", "Q-0069"],
            "training_trace_count": 44,
            "development_point": "HP1",
            "development_amplitudes_system_pu": [0.025, 0.065],
            "amplitude_model": "linear-equal-average-unit-response",
        },
        "predictor": {
            "kind": "central-difference-25-step-local-simplex-template",
            "development_response": "equal-average-unit-response-at-0.05",
            "amplitude_scaling": "linear-no-quadratic-term",
            "output_coordinates": "exact-weighted-common-plus-three-differential",
            "validation_zero_usage": "actual-response-reference-only",
        },
        "holdout_operating_points": _holdout_operating_points(),
        "holdout_amplitudes_system_pu": [0.025, 0.065],
        "active_steps": 5,
        "recovery_steps": 20,
        "sample_period_seconds": 0.2,
        "holdout_trace_count": 34,
        "thresholds": {
            "total_nrmse_max": 0.15,
            "peak_magnitude_relative_error_max": 0.10,
            "peak_timing_error_seconds_max": 0.2,
            "aggregate_cross_squared_error_reduction_min": 0.20,
            "cross_record_win_fraction_min": 0.75,
        },
        "comparison_identifiability": {
            "local_full_vs_block": "ALLOW",
            "R313_vs_R314": "QUALIFY",
            "local_single_factor": (
                "retain-versus-zero-common-differential-cross-output"
            ),
            "cross_estimand": (
                "heldout-cross-output-prediction-error-in-this-local-template"
            ),
            "R313_to_R314_difference": (
                "combined-added-HP1-development-data-plus-local-simplex-rule"
            ),
            "stay_out": [
                "isolated-causal-value-of-local-rule",
                "isolated-causal-value-of-added-data",
                "predictor-class-superiority",
                "controller-efficacy",
                "distributed-execution-value",
                "multi-agent-or-MARL-value",
                "topology-or-deployment-generalization",
            ],
        },
        "eval": {
            "trigger": {
                "run_manifest_trace_count": 34,
                "verified_edge_record_count": 24,
                "source_sidecars_required": True,
            },
            "guard_synthesis": {
                "source": "authoritative R314 physical record fields",
                "mapping": EXPECTED_EVAL_GUARDS,
                "fail_closed": True,
            },
            "source_bound_view": True,
            "execution_profile": "vector_power",
            "required_active_window_seconds": 1.0,
            "bootstrap_resamples": EVAL_BOOTSTRAP_RESAMPLES,
            "bootstrap_seed": EVAL_BOOTSTRAP_SEED,
            "evidence_status": "EXTERNAL_AUTHORITY_REQUIRED",
            "effect_optimization_authorized": False,
        },
        "classification": [
            "INVALID-LOCAL-PREDICTOR-VALIDATION",
            "LOCAL-PREDICTOR-NO-GO",
            "LOCAL-PREDICTOR-PASS",
        ],
        "optimization_rules": {
            "INVALID-LOCAL-PREDICTOR-VALIDATION": (
                "new-cause-specific-canary-only"
            ),
            "LOCAL-PREDICTOR-NO-GO": (
                "registered-amplitude-diagnosis-or-pivot-to-dynamic-reduction"
            ),
            "LOCAL-PREDICTOR-PASS": (
                "dynamic-reduction-and-mismatch-gate-separate-round"
            ),
        },
        "fresh_holdout_required": True,
        "R313_HP1_development_only": True,
        "R313_HP0_fitting_forbidden": True,
        "holdout_fitting_forbidden": True,
        "controller_development_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R314/plan.md",
        "question": ROOT / "memory/questions/Q-0070.md",
        "adapter": Path(__file__).resolve(),
        "lifecycle_core": ROOT / "scripts/run_r313_model_first_predictor.py",
        "execution_core": ROOT / "scripts/run_r310_model_first_stage1.py",
        "model_contract": SRC
        / "andes_rl_kundur/env/andes/model_first_contract.py",
        "environment": SRC / "andes_rl_kundur/env/andes/model_first_env.py",
        "predictor": SRC
        / "andes_rl_kundur/evaluation/model_first_predictor.py",
        "validation_probe": ROOT / "probes/r313_predictor_validation.py",
        "eval_view": SRC
        / "andes_rl_kundur/evaluation/model_first_stage1_eval_view.py",
        "eval_guards": SRC
        / "andes_rl_kundur/evaluation/model_first_stage1_eval_guards.py",
        "eval_v2": SRC / "andes_rl_kundur/evaluation/eval_v2.py",
        "predictor_tests": ROOT / "tests/test_model_first_predictor.py",
        "validation_tests": ROOT / "tests/test_r313_predictor_validation.py",
        "adapter_tests": ROOT / "tests/test_r314_local_predictor.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _load_r313_hp1_development() -> tuple[
    list[dict[str, Any]], dict[str, dict[str, str]]
]:
    manifest_path = R313_OUT / "run_manifest.json"
    analysis_path = R313_OUT / "analysis.json"
    provenance_path = R313_OUT / "provenance.json"
    manifest, manifest_digest = _read_verified_json(manifest_path)
    analysis, analysis_digest = _read_verified_json(analysis_path)
    provenance, provenance_digest = _read_verified_json(provenance_path)
    if (
        manifest.get("round") != "R313"
        or manifest.get("question") != "Q-0069"
        or manifest.get("trace_count") != 34
        or manifest.get("fresh_holdout_execution") is not True
        or manifest.get("validation_source_rounds_used") != []
        or analysis.get("classification") != "PREDICTOR-NO-GO"
        or analysis.get("run_manifest_sha256") != manifest_digest
        or analysis.get("eval_integrity") is not True
        or not all(analysis.get("execution_guards", {}).values())
        or provenance.get("run_manifest", {}).get("sha256") != manifest_digest
        or provenance.get("analysis", {}).get("sha256") != analysis_digest
        or provenance.get("holdout_used_for_fitting") is not False
        or provenance.get("training_authorized") is not False
    ):
        raise RuntimeError("R313 development authority chain is not valid")
    selected_entries = [
        entry
        for entry in manifest.get("records", [])
        if isinstance(entry, Mapping) and entry.get("operating_point") == "HP1"
    ]
    if len(selected_entries) != 17 or any(
        entry.get("operating_point") == "HP0" for entry in selected_entries
    ):
        raise RuntimeError("R313 HP1 development selector is not exact")
    records = [
        _read_verified_json(ROOT / entry["path"], entry["sha256"])[0]
        for entry in selected_entries
    ]
    artifacts = {
        "run_manifest": {
            "path": _path_text(manifest_path),
            "sha256": manifest_digest,
        },
        "analysis": {"path": _path_text(analysis_path), "sha256": analysis_digest},
        "provenance": {
            "path": _path_text(provenance_path),
            "sha256": provenance_digest,
        },
    }
    return records, artifacts


def _load_development() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, dict[str, dict[str, str]]],
]:
    r312_records, r312_artifacts = _load_r312_training()
    hp1_records, r313_artifacts = _load_r313_hp1_development()
    return (
        r312_records,
        hp1_records,
        {"R312": r312_artifacts, "R313_HP1_only": r313_artifacts},
    )


def prepare(seal_path: Path) -> str:
    _r312, _hp1, development_artifacts = _load_development()
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "development_artifacts": development_artifacts,
        "sources": _sources(),
    }
    digest = _write_new_json(seal_path, seal)
    print(f"seal_sha256={digest}", flush=True)
    return digest


def _load_seal(path: Path, expected: str) -> tuple[dict[str, Any], str]:
    seal, digest = _read_verified_json(path, expected)
    if seal.get("round") != ROUND_ID or seal.get("question") != QUESTION_ID:
        raise RuntimeError("R314 seal identity mismatch")
    if seal.get("contract_payload_sha256") != _payload_sha256(seal["contract"]):
        raise RuntimeError("R314 seal contract payload drift")
    if seal["contract"] != build_contract():
        raise RuntimeError("R314 in-code contract drift")
    for name, entry in seal["sources"].items():
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed source drift for {name}")
    _r312, _hp1, current_artifacts = _load_development()
    if current_artifacts != seal["development_artifacts"]:
        raise RuntimeError("sealed R314 development artifact drift")
    return seal, digest


def _fit_model(
    r312_records: Sequence[Mapping[str, object]],
    hp1_records: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    base = fit_coupling_retaining_predictor(r312_records)
    return augment_predictor_with_development_point(
        base,
        hp1_records,
        point=DEVELOPMENT_POINT,
        development_round="R313",
        development_question="Q-0069",
        amplitudes_system_pu=DEVELOPMENT_AMPLITUDES,
    )


def fit(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    r312_records, hp1_records, development_artifacts = _load_development()
    predictor = _fit_model(r312_records, hp1_records)
    artifact = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "development_artifacts": development_artifacts,
        "predictor": predictor,
        "R313_HP1_development_only": True,
        "R313_HP0_accessed": False,
        "R314_holdout_accessed": False,
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "controller_development_authorized": False,
        "training_authorized": False,
    }
    digest = _write_new_json(out_dir / "predictor_model.json", artifact)
    print(f"predictor_model_sha256={digest}", flush=True)


def _load_model(
    out_dir: Path,
    *,
    seal_digest: str,
    expected_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    artifact, digest = _read_verified_json(
        out_dir / "predictor_model.json", expected_sha256
    )
    r312_records, hp1_records, development_artifacts = _load_development()
    expected_predictor = _fit_model(r312_records, hp1_records)
    if (
        artifact.get("round") != ROUND_ID
        or artifact.get("question") != QUESTION_ID
        or artifact.get("seal_sha256") != seal_digest
        or artifact.get("development_artifacts") != development_artifacts
        or artifact.get("predictor") != expected_predictor
        or artifact.get("R313_HP1_development_only") is not True
        or artifact.get("R313_HP0_accessed") is not False
        or artifact.get("R314_holdout_accessed") is not False
        or artifact.get("controller_development_authorized") is not False
        or artifact.get("training_authorized") is not False
    ):
        raise RuntimeError("R314 local predictor model provenance mismatch")
    return artifact, digest


def run(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    model_artifact, model_digest = _load_model(out_dir, seal_digest=seal_digest)
    manifest_path = out_dir / "run_manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"R314 run already exists: {manifest_path}")
    entries: list[dict[str, object]] = []
    coordinates: Sequence[str] = tuple(stage1_power_coordinates())
    amplitudes = [
        float(value) for value in seal["contract"]["holdout_amplitudes_system_pu"]
    ]
    for point_entry in seal["contract"]["holdout_operating_points"]:
        point = _point(point_entry)
        zero_record = _run_trace(
            point=point,
            coordinate="zero",
            sign="zero",
            seal_digest=seal_digest,
            round_id=ROUND_ID,
            question_id=QUESTION_ID,
        )
        zero_record["training_weights"] = point_entry["training_weights"]
        zero_record["simplex"] = point_entry["simplex"]
        zero_record["predictor_model_sha256"] = model_digest
        path, group = _record_path(
            out_dir,
            point=point.name,
            coordinate="zero",
            sign="zero",
            amplitude=0.0,
        )
        digest = _write_new_json(path, zero_record)
        entries.append(
            {
                "path": _path_text(path),
                "sha256": digest,
                "group": group,
                "operating_point": point.name,
                "coordinate": "zero",
                "sign": "zero",
                "amplitude_system_pu": 0.0,
            }
        )
        print(f"trace={point.name}/zero", flush=True)
        for coordinate in coordinates:
            for sign in ("positive", "negative"):
                for amplitude in amplitudes:
                    record = _run_trace(
                        point=point,
                        coordinate=coordinate,
                        sign=sign,
                        seal_digest=seal_digest,
                        round_id=ROUND_ID,
                        question_id=QUESTION_ID,
                        pulse_amplitude_system_pu=amplitude,
                    )
                    record["training_weights"] = point_entry["training_weights"]
                    record["simplex"] = point_entry["simplex"]
                    record["predictor_model_sha256"] = model_digest
                    path, group = _record_path(
                        out_dir,
                        point=point.name,
                        coordinate=coordinate,
                        sign=sign,
                        amplitude=amplitude,
                    )
                    digest = _write_new_json(path, record)
                    entries.append(
                        {
                            "path": _path_text(path),
                            "sha256": digest,
                            "group": group,
                            "operating_point": point.name,
                            "coordinate": coordinate,
                            "sign": sign,
                            "amplitude_system_pu": amplitude,
                        }
                    )
                    print(
                        f"trace={point.name}/{coordinate}/{sign}/{amplitude:.3f}",
                        flush=True,
                    )
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "predictor_model_sha256": model_digest,
        "trace_count": len(entries),
        "records": entries,
        "fresh_holdout_execution": True,
        "validation_source_rounds_used": [],
        "development_source": model_artifact["development_artifacts"],
        "execution_runtime": _runtime_record(),
        "controller_development_authorized": False,
        "training_authorized": False,
    }
    digest = _write_new_json(manifest_path, manifest)
    print(f"trace_count={len(entries)}", flush=True)
    print(f"run_manifest_sha256={digest}", flush=True)


def _load_run_records(
    out_dir: Path,
    *,
    seal_digest: str,
    model_digest: str,
) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    manifest, manifest_digest = _read_verified_json(out_dir / "run_manifest.json")
    if (
        manifest.get("round") != ROUND_ID
        or manifest.get("question") != QUESTION_ID
        or manifest.get("seal_sha256") != seal_digest
        or manifest.get("predictor_model_sha256") != model_digest
        or manifest.get("trace_count") != 34
        or manifest.get("fresh_holdout_execution") is not True
        or manifest.get("validation_source_rounds_used") != []
        or manifest.get("controller_development_authorized") is not False
        or manifest.get("training_authorized") is not False
    ):
        raise RuntimeError("R314 run manifest contract mismatch")
    records = [
        _read_verified_json(ROOT / entry["path"], entry["sha256"])[0]
        for entry in manifest.get("records", [])
    ]
    if len(records) != 34:
        raise RuntimeError("R314 manifest does not resolve to 34 records")
    return manifest, manifest_digest, records


def eval_records(seal_path: Path, expected: str, out_dir: Path) -> None:
    _seal, seal_digest = _load_seal(seal_path, expected)
    _model, model_digest = _load_model(out_dir, seal_digest=seal_digest)
    manifest, manifest_digest, _records = _load_run_records(
        out_dir, seal_digest=seal_digest, model_digest=model_digest
    )
    edge_entries = [
        entry for entry in manifest["records"] if entry["group"] == "edge_source"
    ]
    if len(edge_entries) != 24:
        raise RuntimeError("R314 EVAL trigger requires exactly 24 edge records")
    eval_input = out_dir.resolve() / "eval_input"
    view_entries: list[dict[str, object]] = []
    for entry in edge_entries:
        record, source_digest = _read_verified_json(
            ROOT / entry["path"], entry["sha256"]
        )
        view = build_guarded_fresh_stage1_eval_view(
            record,
            source_path=entry["path"],
            source_sha256=source_digest,
            expected_round=ROUND_ID,
            expected_question=QUESTION_ID,
        )
        destination = eval_input / Path(entry["path"]).name
        view_digest = _write_new_json(destination, view)
        view_entries.append(
            {
                "path": _path_text(destination),
                "sha256": view_digest,
                "source_path": entry["path"],
                "source_sha256": source_digest,
                "guards": EXPECTED_EVAL_GUARDS,
            }
        )
    input_manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "predictor_model_sha256": model_digest,
        "run_manifest_sha256": manifest_digest,
        "record_count": len(view_entries),
        "records": view_entries,
        "guard_synthesis": "fail-closed-from-authoritative-source-fields",
        "threshold_changes": False,
        "trace_rerun": False,
        "evidence_authority_change": False,
    }
    input_digest = _write_new_json(
        out_dir / "eval_input_manifest.json", input_manifest
    )
    from andes_rl_kundur.evaluation.eval_v2 import (
        evaluate_trace_directory,
        write_scorecard,
    )

    scorecard = evaluate_trace_directory(
        eval_input,
        baseline="positive",
        execution_profile="vector_power",
        required_active_window_seconds=1.0,
        bootstrap_resamples=EVAL_BOOTSTRAP_RESAMPLES,
        bootstrap_seed=EVAL_BOOTSTRAP_SEED,
    )
    outputs = write_scorecard(scorecard, out_dir / "eval", overwrite=False)
    print(f"eval_input_manifest_sha256={input_digest}", flush=True)
    print(f"diagnostic_pass={scorecard['validity']['diagnostic_pass']}", flush=True)
    print(f"evidence_status={scorecard['evidence_status']['status']}", flush=True)
    print(json.dumps(outputs, indent=2), flush=True)


def analyse(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    model_artifact, model_digest = _load_model(out_dir, seal_digest=seal_digest)
    manifest, manifest_digest, records = _load_run_records(
        out_dir, seal_digest=seal_digest, model_digest=model_digest
    )
    input_manifest, input_manifest_digest = _read_verified_json(
        out_dir / "eval_input_manifest.json"
    )
    if (
        input_manifest.get("record_count") != 24
        or input_manifest.get("run_manifest_sha256") != manifest_digest
        or input_manifest.get("predictor_model_sha256") != model_digest
        or input_manifest.get("threshold_changes") is not False
        or input_manifest.get("trace_rerun") is not False
        or input_manifest.get("evidence_authority_change") is not False
    ):
        raise RuntimeError("R314 EVAL input manifest contract mismatch")
    source_entries = {
        (entry["path"], entry["sha256"])
        for entry in manifest["records"]
        if entry["group"] == "edge_source"
    }
    bound_entries: set[tuple[str, str]] = set()
    for entry in input_manifest["records"]:
        view, _ = _read_verified_json(ROOT / entry["path"], entry["sha256"])
        binding = view.get("source_record")
        if (
            not isinstance(binding, Mapping)
            or binding.get("path") != entry["source_path"]
            or binding.get("sha256") != entry["source_sha256"]
            or view.get("guards") != EXPECTED_EVAL_GUARDS
        ):
            raise RuntimeError("R314 guarded EVAL view binding mismatch")
        bound_entries.add((entry["source_path"], entry["source_sha256"]))
    if bound_entries != source_entries:
        raise RuntimeError("R314 EVAL source binding mismatch")
    scorecard_path = out_dir / "eval/scorecard.json"
    scorecard, scorecard_digest = _read_verified_json(scorecard_path)
    decision = evaluate_predictor_validation(
        records,
        model_artifact["predictor"],
        scorecard,
        seal["contract"],
        expected_round=ROUND_ID,
        expected_question=QUESTION_ID,
        expected_seal_sha256=seal_digest,
        model_provenance_valid=True,
    )
    base_classification = str(decision["classification"])
    classification_map = {
        "INVALID-PREDICTOR-VALIDATION": "INVALID-LOCAL-PREDICTOR-VALIDATION",
        "PREDICTOR-NO-GO": "LOCAL-PREDICTOR-NO-GO",
        "PREDICTOR-PASS": "LOCAL-PREDICTOR-PASS",
    }
    decision["base_classification"] = base_classification
    decision["classification"] = classification_map[base_classification]
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "predictor_model_sha256": model_digest,
        "run_manifest_sha256": manifest_digest,
        "eval_input_manifest_sha256": input_manifest_digest,
        "eval_scorecard_sha256": scorecard_digest,
        "fresh_holdout_execution": True,
        "R313_HP1_development_only": True,
        "R313_HP0_used_for_fitting": False,
        "R314_holdout_used_for_fitting": False,
        "optimization_rule": seal["contract"]["optimization_rules"][
            decision["classification"]
        ],
        **decision,
    }
    analysis_digest = _write_new_json(out_dir / "analysis.json", analysis)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal": {"path": _path_text(seal_path), "sha256": seal_digest},
        "predictor_model": {
            "path": _path_text(out_dir / "predictor_model.json"),
            "sha256": model_digest,
        },
        "run_manifest": {
            "path": _path_text(out_dir / "run_manifest.json"),
            "sha256": manifest_digest,
        },
        "eval_input_manifest": {
            "path": _path_text(out_dir / "eval_input_manifest.json"),
            "sha256": input_manifest_digest,
        },
        "eval_scorecard": {
            "path": _path_text(scorecard_path),
            "sha256": scorecard_digest,
        },
        "analysis": {
            "path": _path_text(out_dir / "analysis.json"),
            "sha256": analysis_digest,
        },
        "development_artifacts": seal["development_artifacts"],
        "sources_verified": seal["sources"],
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "validation_source_rounds_used": [],
        "R313_HP1_development_only": True,
        "R313_HP0_used_for_fitting": False,
        "R314_holdout_used_for_fitting": False,
        "controller_development_authorized": False,
        "training_authorized": False,
    }
    provenance_digest = _write_new_json(out_dir / "provenance.json", provenance)
    print(f"classification={analysis['classification']}", flush=True)
    print(f"optimization_rule={analysis['optimization_rule']}", flush=True)
    print(f"analysis_sha256={analysis_digest}", flush=True)
    print(f"provenance_sha256={provenance_digest}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    for command in ("fit", "run", "eval", "analyse"):
        subparser = commands.add_parser(command)
        subparser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
        subparser.add_argument("--expected-seal-sha256", required=True)
        subparser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        prepare(args.seal)
    elif args.command == "fit":
        fit(args.seal, args.expected_seal_sha256, args.out_dir)
    elif args.command == "run":
        run(args.seal, args.expected_seal_sha256, args.out_dir)
    elif args.command == "eval":
        eval_records(args.seal, args.expected_seal_sha256, args.out_dir)
    else:
        analyse(args.seal, args.expected_seal_sha256, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
