#!/usr/bin/env python3
"""Run the single-factor R316 action-withdrawal guard repair."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for path in (ROOT, SRC, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_r315_dynamic_reduction as R315_BASE  # noqa: E402

from andes_rl_kundur.env.andes.model_first_contract import (  # noqa: E402
    stage1_power_coordinates,
)
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (  # noqa: E402
    realization_from_dict,
)
from andes_rl_kundur.evaluation.model_first_stage1_eval_guards import (  # noqa: E402
    build_guarded_fresh_stage1_eval_view,
)
from probes.r316_dynamic_reduction_validation import (  # noqa: E402
    evaluate_dynamic_reduction_validation,
)

ROUND_ID = "R316"
QUESTION_ID = "Q-0071"
DEFAULT_SEAL = ROOT / "memory/rounds/R316/dynamic_reduction_seal.json"
DEFAULT_OUT = ROOT / "results/r316_dynamic_reduction"
EVAL_BOOTSTRAP_RESAMPLES = 10_000
EVAL_BOOTSTRAP_SEED = 2026080316

_path_text = R315_BASE._path_text
_payload_sha256 = R315_BASE._payload_sha256
_read_verified_json = R315_BASE._read_verified_json
_runtime_record = R315_BASE._runtime_record
_sha256_file = R315_BASE._sha256_file
_write_new_json = R315_BASE._write_new_json
EXPECTED_EVAL_GUARDS = R315_BASE.EXPECTED_EVAL_GUARDS


def _holdout_operating_points() -> list[dict[str, object]]:
    return [
        {
            "name": "HS0",
            "vsg_m_device": 177.5,
            "vsg_d_device": 88.75,
            "tie_rx_scale": 1.10,
            "initial_soc": 0.41,
            "training_weights": {
                "OP0": 0.25,
                "OP1": 0.25,
                "OP2": 0.0,
                "HP1": 0.50,
            },
            "simplex": ["OP0", "OP1", "HP1"],
        },
        {
            "name": "HS1",
            "vsg_m_device": 202.5,
            "vsg_d_device": 101.25,
            "tie_rx_scale": 1.35,
            "initial_soc": 0.51,
            "training_weights": {
                "OP0": 0.25,
                "OP1": 0.0,
                "OP2": 0.25,
                "HP1": 0.50,
            },
            "simplex": ["OP0", "OP2", "HP1"],
        },
    ]


def build_contract() -> dict[str, Any]:
    contract = deepcopy(R315_BASE.build_contract())
    contract.update(
        {
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "stage": "sealed-action-withdrawal-guard-repair-holdout",
            "holdout_operating_points": _holdout_operating_points(),
            "execution_guard_repair": {
                "nonzero_achieved_relative_error_max": 0.05,
                "zero_request_achieved_power_abs_max_system_pu": 1e-6,
                "request_command_readback_abs_tolerance_system_pu": 1e-12,
                "source_round": "R315",
                "source_claim": "CLM-0785",
            },
        }
    )
    authority = contract["development_authority"]
    authority["R315_holdout_fitting_forbidden"] = True
    comparison = contract["comparison_identifiability"]
    comparison.pop("R314_vs_R315", None)
    comparison["R315_vs_R316"] = "QUALIFY"
    evaluation = contract["eval"]
    evaluation["bootstrap_seed"] = EVAL_BOOTSTRAP_SEED
    evaluation["guard_synthesis"]["source"] = (
        "authoritative R316 physical record fields with prospective "
        "achieved-power zero-request tolerance"
    )
    return contract


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R316/plan.md",
        "question": ROOT / "memory/questions/Q-0071.md",
        "adapter": Path(__file__).resolve(),
        "R315_execution_core": ROOT / "scripts/run_r315_dynamic_reduction.py",
        "R315_validation_core": ROOT
        / "probes/r315_dynamic_reduction_validation.py",
        "validation_probe": ROOT
        / "probes/r316_dynamic_reduction_validation.py",
        "model_contract": SRC
        / "andes_rl_kundur/env/andes/model_first_contract.py",
        "environment": SRC / "andes_rl_kundur/env/andes/model_first_env.py",
        "dynamic_reduction": SRC
        / "andes_rl_kundur/evaluation/model_first_dynamic_reduction.py",
        "eval_view": SRC
        / "andes_rl_kundur/evaluation/model_first_stage1_eval_view.py",
        "eval_guards": SRC
        / "andes_rl_kundur/evaluation/model_first_stage1_eval_guards.py",
        "eval_v2": SRC / "andes_rl_kundur/evaluation/eval_v2.py",
        "R315_adapter_tests": ROOT / "tests/test_r315_dynamic_reduction.py",
        "R315_validation_tests": ROOT
        / "tests/test_r315_dynamic_reduction_validation.py",
        "adapter_tests": ROOT / "tests/test_r316_dynamic_reduction.py",
        "validation_tests": ROOT
        / "tests/test_r316_dynamic_reduction_validation.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def prepare(seal_path: Path) -> str:
    _predictor, development_artifacts = R315_BASE._load_r314_development()
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "development_artifacts": development_artifacts,
        "invalid_parent": {
            "round": "R315",
            "claim": "CLM-0785",
            "analysis": {
                "path": "results/r315_dynamic_reduction/analysis.json",
                "sha256": (
                    "12e44f04c1941663c2037e57db6cc1c4f0b76314db3ff14bac67b8eced209b0a"
                ),
            },
        },
        "sources": _sources(),
    }
    digest = _write_new_json(seal_path, seal)
    print(f"seal_sha256={digest}", flush=True)
    return digest


def _load_seal(path: Path, expected: str) -> tuple[dict[str, Any], str]:
    seal, digest = _read_verified_json(path, expected)
    if seal.get("round") != ROUND_ID or seal.get("question") != QUESTION_ID:
        raise RuntimeError("R316 seal identity mismatch")
    if seal.get("contract_payload_sha256") != _payload_sha256(seal["contract"]):
        raise RuntimeError("R316 seal contract payload drift")
    if seal.get("contract") != build_contract():
        raise RuntimeError("R316 in-code contract drift")
    _predictor, development_artifacts = R315_BASE._load_r314_development()
    if seal.get("development_artifacts") != development_artifacts:
        raise RuntimeError("sealed R316 development artifact drift")
    parent = seal.get("invalid_parent", {}).get("analysis", {})
    if _sha256_file(ROOT / parent.get("path", "missing")) != parent.get("sha256"):
        raise RuntimeError("R316 invalid-parent analysis drift")
    for name, entry in seal["sources"].items():
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed R316 source drift for {name}")
    return seal, digest


def fit(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    predictor_artifact, development_artifacts = R315_BASE._load_r314_development()
    points = R315_BASE._fit_dynamic_model(predictor_artifact, seal["contract"])
    artifact = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "development_artifacts": development_artifacts,
        "realization_contract": seal["contract"]["realization"],
        "points": points,
        "R313_HP0_used_for_fitting": False,
        "R314_holdout_used_for_fitting": False,
        "R315_holdout_used_for_fitting": False,
        "R316_holdout_accessed": False,
        "controller_development_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
    digest = _write_new_json(out_dir / "dynamic_model.json", artifact)
    print(f"dynamic_model_sha256={digest}", flush=True)


def _load_model(
    out_dir: Path,
    *,
    seal: Mapping[str, object],
    seal_digest: str,
    expected_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    artifact, digest = _read_verified_json(
        out_dir / "dynamic_model.json", expected_sha256
    )
    predictor_artifact, development_artifacts = R315_BASE._load_r314_development()
    expected_points = R315_BASE._fit_dynamic_model(
        predictor_artifact, seal["contract"]
    )
    points = artifact.get("points")
    points_valid = isinstance(points, Mapping) and set(points) == set(expected_points)
    if points_valid:
        for name, expected_point in expected_points.items():
            point = points[name]
            if not isinstance(point, Mapping):
                points_valid = False
                break
            try:
                realization = realization_from_dict(point["realization"])
                points_valid = bool(
                    point.get("training_weights")
                    == expected_point["training_weights"]
                    and np.allclose(
                        np.asarray(point["markov_parameters"], dtype=float),
                        np.asarray(
                            expected_point["markov_parameters"], dtype=float
                        ),
                        rtol=1e-13,
                        atol=1e-15,
                    )
                    and realization.state_matrix.shape == (10, 10)
                    and realization.input_matrix.shape == (10, 4)
                    and realization.output_matrix.shape == (4, 10)
                    and realization.feedthrough_matrix.shape == (4, 4)
                    and realization.spectral_radius <= 0.995 + 1e-10
                )
            except (KeyError, TypeError, ValueError):
                points_valid = False
            if not points_valid:
                break
    if (
        artifact.get("round") != ROUND_ID
        or artifact.get("question") != QUESTION_ID
        or artifact.get("seal_sha256") != seal_digest
        or artifact.get("contract_payload_sha256")
        != seal["contract_payload_sha256"]
        or artifact.get("development_artifacts") != development_artifacts
        or artifact.get("realization_contract") != seal["contract"]["realization"]
        or artifact.get("R313_HP0_used_for_fitting") is not False
        or artifact.get("R314_holdout_used_for_fitting") is not False
        or artifact.get("R315_holdout_used_for_fitting") is not False
        or artifact.get("R316_holdout_accessed") is not False
        or artifact.get("controller_development_authorized") is not False
        or artifact.get("distributed_agent_implementation_authorized") is not False
        or artifact.get("training_authorized") is not False
        or not points_valid
    ):
        raise RuntimeError("R316 dynamic model provenance mismatch")
    return artifact, digest


def _run_trace_sequence(**kwargs: Any) -> dict[str, Any]:
    record = R315_BASE._run_trace_sequence(**kwargs)
    record["round"] = ROUND_ID
    record["question"] = QUESTION_ID
    record["guard_contract"] = build_contract()["execution_guard_repair"]
    return record


def run(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    model_artifact, model_digest = _load_model(
        out_dir, seal=seal, seal_digest=seal_digest
    )
    manifest_path = out_dir.resolve() / "run_manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"R316 run already exists: {manifest_path}")
    entries: list[dict[str, object]] = []
    coordinates: Sequence[str] = tuple(stage1_power_coordinates())
    shapes = seal["contract"]["excitation_shapes"]
    for point_entry in seal["contract"]["holdout_operating_points"]:
        point = R315_BASE._point(point_entry)
        zero_record = _run_trace_sequence(
            point=point,
            coordinate="zero",
            shape="zero",
            sign="zero",
            scalar_sequence=np.zeros(R315_BASE.TOTAL_STEPS),
            seal_digest=seal_digest,
            model_digest=model_digest,
        )
        zero_record["training_weights"] = point_entry["training_weights"]
        zero_record["simplex"] = point_entry["simplex"]
        path, group = R315_BASE._record_path(
            out_dir,
            point=point.name,
            shape="zero",
            coordinate="zero",
            sign="zero",
        )
        digest = _write_new_json(path, zero_record)
        entries.append(
            {
                "path": _path_text(path),
                "sha256": digest,
                "group": group,
                "operating_point": point.name,
                "input_shape": "zero",
                "coordinate": "zero",
                "sign": "zero",
            }
        )
        print(f"trace={point.name}/zero", flush=True)
        for shape, base_sequence in shapes.items():
            for coordinate in coordinates:
                for sign in ("positive", "negative"):
                    record = _run_trace_sequence(
                        point=point,
                        coordinate=coordinate,
                        shape=shape,
                        sign=sign,
                        scalar_sequence=R315_BASE._signed_sequence(
                            base_sequence, sign
                        ),
                        seal_digest=seal_digest,
                        model_digest=model_digest,
                    )
                    record["training_weights"] = point_entry["training_weights"]
                    record["simplex"] = point_entry["simplex"]
                    path, group = R315_BASE._record_path(
                        out_dir,
                        point=point.name,
                        shape=shape,
                        coordinate=coordinate,
                        sign=sign,
                    )
                    digest = _write_new_json(path, record)
                    entries.append(
                        {
                            "path": _path_text(path),
                            "sha256": digest,
                            "group": group,
                            "operating_point": point.name,
                            "input_shape": shape,
                            "coordinate": coordinate,
                            "sign": sign,
                        }
                    )
                    print(
                        f"trace={point.name}/{shape}/{coordinate}/{sign}",
                        flush=True,
                    )
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "dynamic_model_sha256": model_digest,
        "trace_count": len(entries),
        "records": entries,
        "fresh_holdout_execution": True,
        "validation_source_rounds_used": [],
        "development_source": model_artifact["development_artifacts"],
        "guard_repair_source_round": "R315",
        "execution_runtime": _runtime_record(),
        "controller_development_authorized": False,
        "distributed_agent_implementation_authorized": False,
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
        or manifest.get("dynamic_model_sha256") != model_digest
        or manifest.get("trace_count") != 50
        or manifest.get("fresh_holdout_execution") is not True
        or manifest.get("validation_source_rounds_used") != []
        or manifest.get("guard_repair_source_round") != "R315"
        or manifest.get("controller_development_authorized") is not False
        or manifest.get("distributed_agent_implementation_authorized") is not False
        or manifest.get("training_authorized") is not False
    ):
        raise RuntimeError("R316 run manifest contract mismatch")
    records = [
        _read_verified_json(ROOT / entry["path"], entry["sha256"])[0]
        for entry in manifest.get("records", [])
    ]
    if len(records) != 50:
        raise RuntimeError("R316 manifest does not resolve to 50 records")
    return manifest, manifest_digest, records


def eval_records(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    _model, model_digest = _load_model(
        out_dir, seal=seal, seal_digest=seal_digest
    )
    manifest, manifest_digest, _records = _load_run_records(
        out_dir, seal_digest=seal_digest, model_digest=model_digest
    )
    edge_entries = [
        entry for entry in manifest["records"] if entry["group"] == "edge_source"
    ]
    if len(edge_entries) != 36:
        raise RuntimeError("R316 EVAL trigger requires exactly 36 edge records")
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
        "dynamic_model_sha256": model_digest,
        "run_manifest_sha256": manifest_digest,
        "record_count": len(view_entries),
        "records": view_entries,
        "guard_synthesis": "fail-closed-with-prospective-achieved-zero-tolerance",
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
    model_artifact, model_digest = _load_model(
        out_dir, seal=seal, seal_digest=seal_digest
    )
    manifest, manifest_digest, records = _load_run_records(
        out_dir, seal_digest=seal_digest, model_digest=model_digest
    )
    input_manifest, input_manifest_digest = _read_verified_json(
        out_dir / "eval_input_manifest.json"
    )
    if (
        input_manifest.get("record_count") != 36
        or input_manifest.get("run_manifest_sha256") != manifest_digest
        or input_manifest.get("dynamic_model_sha256") != model_digest
        or input_manifest.get("threshold_changes") is not False
        or input_manifest.get("trace_rerun") is not False
        or input_manifest.get("evidence_authority_change") is not False
    ):
        raise RuntimeError("R316 EVAL input manifest contract mismatch")
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
            raise RuntimeError("R316 guarded EVAL view binding mismatch")
        bound_entries.add((entry["source_path"], entry["source_sha256"]))
    if bound_entries != source_entries:
        raise RuntimeError("R316 EVAL source binding mismatch")
    scorecard_path = out_dir / "eval/scorecard.json"
    scorecard, scorecard_digest = _read_verified_json(scorecard_path)
    model_provenance_valid = bool(
        model_artifact.get("seal_sha256") == seal_digest
        and model_artifact.get("development_artifacts")
        == seal["development_artifacts"]
        and model_artifact.get("R314_holdout_used_for_fitting") is False
        and model_artifact.get("R315_holdout_used_for_fitting") is False
        and model_artifact.get("R316_holdout_accessed") is False
    )
    decision = evaluate_dynamic_reduction_validation(
        records,
        model_artifact,
        scorecard,
        seal["contract"],
        expected_seal_sha256=seal_digest,
        expected_model_sha256=model_digest,
        model_provenance_valid=model_provenance_valid,
    )
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "dynamic_model_sha256": model_digest,
        "run_manifest_sha256": manifest_digest,
        "eval_input_manifest_sha256": input_manifest_digest,
        "eval_scorecard_sha256": scorecard_digest,
        "fresh_holdout_execution": True,
        "R313_HP0_used_for_fitting": False,
        "R314_holdout_used_for_fitting": False,
        "R315_holdout_used_for_fitting": False,
        "R316_holdout_used_for_fitting": False,
        **decision,
        "optimization_rule": seal["contract"]["optimization_rules"][
            decision["classification"]
        ],
    }
    analysis_digest = _write_new_json(out_dir / "analysis.json", analysis)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal": {"path": _path_text(seal_path), "sha256": seal_digest},
        "dynamic_model": {
            "path": _path_text(out_dir / "dynamic_model.json"),
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
        "invalid_parent": seal["invalid_parent"],
        "sources_verified": seal["sources"],
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "validation_source_rounds_used": [],
        "R313_HP0_used_for_fitting": False,
        "R314_holdout_used_for_fitting": False,
        "R315_holdout_used_for_fitting": False,
        "R316_holdout_used_for_fitting": False,
        "controller_development_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
    provenance_digest = _write_new_json(out_dir / "provenance.json", provenance)
    print(f"classification={decision['classification']}", flush=True)
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
