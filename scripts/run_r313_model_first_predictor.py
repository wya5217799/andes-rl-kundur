#!/usr/bin/env python3
"""Seal, fit, execute, EVAL-audit, and analyse the R313 predictor holdout.

``run`` is the only command that imports ANDES indirectly and must execute
through ``scripts/andes_scratch.py`` under WSL.  Every formal artifact is
create-only and carries a SHA-256 sidecar.
"""

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

from run_r310_model_first_stage1 import (  # noqa: E402
    _run_trace,
    _runtime_record,
)
from run_r312_model_first_stage1 import (  # noqa: E402
    _path_text,
    _payload_sha256,
    _read_verified_json,
    _sha256_file,
    _write_new_json,
)

from andes_rl_kundur.env.andes.model_first_contract import (  # noqa: E402
    Stage1OperatingPoint,
    stage1_power_coordinates,
)
from andes_rl_kundur.evaluation.model_first_predictor import (  # noqa: E402
    fit_coupling_retaining_predictor,
)
from andes_rl_kundur.evaluation.model_first_stage1_eval_guards import (  # noqa: E402
    build_guarded_fresh_stage1_eval_view,
)
from probes.r313_predictor_validation import (  # noqa: E402
    evaluate_predictor_validation,
)

ROUND_ID = "R313"
QUESTION_ID = "Q-0069"
DEFAULT_SEAL = ROOT / "memory/rounds/R313/predictor_holdout_seal.json"
DEFAULT_OUT = ROOT / "results/r313_model_first_predictor"
R312_OUT = ROOT / "results/r312_model_first_stage1"
EVAL_BOOTSTRAP_RESAMPLES = 10_000
EVAL_BOOTSTRAP_SEED = 2026080313
EXPECTED_EVAL_GUARDS = {
    "completed": True,
    "tds_test_ok": True,
    "system_exit_code": 0,
    "finite_telemetry": True,
}


def _holdout_operating_points() -> list[dict[str, object]]:
    return [
        {
            "name": "HP0",
            "vsg_m_device": 200.0,
            "vsg_d_device": 100.0,
            "tie_rx_scale": 1.25,
            "initial_soc": 0.50,
            "training_weights": {"OP0": 0.50, "OP1": 0.25, "OP2": 0.25},
        },
        {
            "name": "HP1",
            "vsg_m_device": 180.0,
            "vsg_d_device": 90.0,
            "tie_rx_scale": 1.20,
            "initial_soc": 0.42,
            "training_weights": {"OP0": 0.20, "OP1": 0.60, "OP2": 0.20},
        },
    ]


def build_contract() -> dict[str, Any]:
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "sealed-coupling-retaining-predictor-holdout",
        "training_source": {
            "round": "R312",
            "question": "Q-0068",
            "trace_count": 27,
            "required_classification": "STAGE1-PASS",
        },
        "predictor": {
            "kind": "central-difference-25-step-trajectory-template",
            "operating_point_interpolation": "frozen-barycentric-convex",
            "amplitude_scaling": "linear-from-0.05-system-pu",
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
            "decision": "ALLOW",
            "single_factor": "retain-versus-zero-common-differential-cross-output",
            "matched": [
                "R312-training-records",
                "holdout-bank",
                "input-output-coordinates",
                "barycentric-weights",
                "amplitude-scaling",
                "estimator-budget",
                "metrics",
            ],
            "estimand": "heldout-cross-output-prediction-error-in-this-template",
            "stay_out": [
                "predictor-class-superiority",
                "controller-efficacy",
                "stability-guarantee",
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
                "source": "authoritative R313 physical record fields",
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
            "INVALID-PREDICTOR-VALIDATION",
            "PREDICTOR-NO-GO",
            "PREDICTOR-PASS",
        ],
        "optimization_rules": {
            "INVALID-PREDICTOR-VALIDATION": "new-cause-specific-canary-only",
            "PREDICTOR-NO-GO": "one-pre-registered-single-factor-diagnosis-or-stop",
            "PREDICTOR-PASS": "dynamic-reduction-and-mismatch-gate-separate-round",
        },
        "fresh_holdout_required": True,
        "holdout_fitting_forbidden": True,
        "controller_development_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R313/plan.md",
        "question": ROOT / "memory/questions/Q-0069.md",
        "adapter": Path(__file__).resolve(),
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
        "adapter_tests": ROOT / "tests/test_r313_model_first_predictor.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _load_r312_training() -> tuple[
    list[dict[str, Any]], dict[str, dict[str, str]]
]:
    manifest_path = R312_OUT / "run_manifest.json"
    analysis_path = R312_OUT / "analysis.json"
    provenance_path = R312_OUT / "provenance.json"
    manifest, manifest_digest = _read_verified_json(manifest_path)
    analysis, analysis_digest = _read_verified_json(analysis_path)
    provenance, provenance_digest = _read_verified_json(provenance_path)
    if (
        manifest.get("round") != "R312"
        or manifest.get("question") != "Q-0068"
        or manifest.get("trace_count") != 27
        or manifest.get("fresh_execution") is not True
        or manifest.get("forbidden_source_rounds_used") != []
        or analysis.get("classification") != "STAGE1-PASS"
        or analysis.get("run_manifest_sha256") != manifest_digest
        or provenance.get("forbidden_source_rounds_used") != []
        or provenance.get("training_authorized") is not False
        or provenance.get("run_manifest", {}).get("sha256") != manifest_digest
        or provenance.get("analysis", {}).get("sha256") != analysis_digest
    ):
        raise RuntimeError("R312 training authority chain is not valid")
    records: list[dict[str, Any]] = []
    for entry in manifest.get("records", []):
        if not isinstance(entry, Mapping):
            raise RuntimeError("R312 manifest record entry is invalid")
        record, _ = _read_verified_json(
            ROOT / str(entry["path"]), str(entry["sha256"])
        )
        records.append(record)
    if len(records) != 27:
        raise RuntimeError("R312 manifest does not resolve to exactly 27 records")
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


def prepare(seal_path: Path) -> str:
    _records, training_artifacts = _load_r312_training()
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "training_artifacts": training_artifacts,
        "sources": _sources(),
    }
    digest = _write_new_json(seal_path, seal)
    print(f"seal_sha256={digest}", flush=True)
    return digest


def _load_seal(path: Path, expected: str) -> tuple[dict[str, Any], str]:
    seal, digest = _read_verified_json(path, expected)
    if seal.get("round") != ROUND_ID or seal.get("question") != QUESTION_ID:
        raise RuntimeError("R313 seal identity mismatch")
    if seal.get("contract_payload_sha256") != _payload_sha256(seal["contract"]):
        raise RuntimeError("R313 seal contract payload drift")
    if seal["contract"] != build_contract():
        raise RuntimeError("R313 in-code contract drift")
    for name, entry in seal["sources"].items():
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed source drift for {name}")
    _records, current_training = _load_r312_training()
    if current_training != seal["training_artifacts"]:
        raise RuntimeError("sealed R312 training artifact drift")
    return seal, digest


def fit(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    records, training_artifacts = _load_r312_training()
    predictor = fit_coupling_retaining_predictor(records)
    artifact = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "training_artifacts": training_artifacts,
        "predictor": predictor,
        "holdout_accessed": False,
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
    records, training_artifacts = _load_r312_training()
    expected_predictor = fit_coupling_retaining_predictor(records)
    if (
        artifact.get("round") != ROUND_ID
        or artifact.get("question") != QUESTION_ID
        or artifact.get("seal_sha256") != seal_digest
        or artifact.get("training_artifacts") != training_artifacts
        or artifact.get("predictor") != expected_predictor
        or artifact.get("holdout_accessed") is not False
        or artifact.get("controller_development_authorized") is not False
        or artifact.get("training_authorized") is not False
    ):
        raise RuntimeError("R313 predictor model provenance mismatch")
    return artifact, digest


def _point(entry: Mapping[str, object]) -> Stage1OperatingPoint:
    return Stage1OperatingPoint(
        name=str(entry["name"]),
        vsg_m_device=float(entry["vsg_m_device"]),
        vsg_d_device=float(entry["vsg_d_device"]),
        tie_rx_scale=float(entry["tie_rx_scale"]),
        initial_soc=float(entry["initial_soc"]),
    )


def _amplitude_slug(value: float) -> str:
    return f"{value:.3f}".replace(".", "p")


def _record_path(
    out_dir: Path,
    *,
    point: str,
    coordinate: str,
    sign: str,
    amplitude: float,
) -> tuple[Path, str]:
    if coordinate == "zero":
        return out_dir / "records/baseline" / f"{point}__zero.json", "baseline"
    name = f"{point}__{coordinate}__a{_amplitude_slug(amplitude)}__{sign}.json"
    if coordinate == "common":
        return out_dir / "records/common" / name, "common"
    return out_dir / "records/edge_source" / name, "edge_source"


def run(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    model_artifact, model_digest = _load_model(
        out_dir, seal_digest=seal_digest
    )
    manifest_path = out_dir / "run_manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"R313 run already exists: {manifest_path}")
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
        "training_source": model_artifact["training_artifacts"],
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
        raise RuntimeError("R313 run manifest contract mismatch")
    records = [
        _read_verified_json(ROOT / entry["path"], entry["sha256"])[0]
        for entry in manifest.get("records", [])
    ]
    if len(records) != 34:
        raise RuntimeError("R313 manifest does not resolve to 34 records")
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
        raise RuntimeError("R313 EVAL trigger requires exactly 24 edge records")
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
        raise RuntimeError("R313 EVAL input manifest contract mismatch")
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
            raise RuntimeError("R313 guarded EVAL view binding mismatch")
        bound_entries.add((entry["source_path"], entry["source_sha256"]))
    if bound_entries != source_entries:
        raise RuntimeError("R313 EVAL source binding mismatch")
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
        "holdout_used_for_fitting": False,
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
        "training_artifacts": seal["training_artifacts"],
        "sources_verified": seal["sources"],
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "validation_source_rounds_used": [],
        "holdout_used_for_fitting": False,
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
