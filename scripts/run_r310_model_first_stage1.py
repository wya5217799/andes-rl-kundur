#!/usr/bin/env python3
"""Seal, run, EVAL-audit, and analyse the fresh R310 Stage-1 bank.

``prepare``, ``eval``, and ``analyse`` are import-safe on Windows. ``run``
imports ANDES only inside the command and must execute through the repository
WSL scratch launcher. Every formal JSON artifact is create-only and has a
SHA-256 sidecar.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from andes_rl_kundur.env.andes.model_first_contract import (  # noqa: E402
    ModelFirstConfig,
    stage1_operating_points,
    stage1_power_coordinates,
)
from andes_rl_kundur.evaluation.model_first_stage1 import (  # noqa: E402
    ACTIVE_STEPS,
    TOTAL_STEPS,
    evaluate_stage1_records,
)
from andes_rl_kundur.evaluation.model_first_stage1_eval_view import (  # noqa: E402
    build_fresh_stage1_eval_view,
)
from andes_rl_kundur.evaluation.model_first_two_phase_tds_canary import (  # noqa: E402
    DYNAMIC_TOL_ZERO,
    DYNAMIC_TOLERANCE,
    INITIALIZATION_TOL_ZERO,
    INITIALIZATION_TOLERANCE,
)

ROUND_ID = "R310"
QUESTION_ID = "Q-0066"
PLAN = ROOT / "memory/rounds/R310/plan.md"
QUESTION = ROOT / "memory/questions/Q-0066.md"
MODEL_CONTRACT = (
    ROOT / "paper/decoupling_marl_model_first/working/model_contract.md"
)
DEFAULT_SEAL = ROOT / "memory/rounds/R310/fresh_stage1_seal.json"
DEFAULT_OUT = ROOT / "results/r310_model_first_stage1"
LOCAL_VECTOR_ARCHITECTURE = "four_local_dapi_agents_with_neighbour_edge_channels"
RECOVERY_STEPS = TOTAL_STEPS - ACTIVE_STEPS
EVAL_BOOTSTRAP_RESAMPLES = 10_000
EVAL_BOOTSTRAP_SEED = 2026080310


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


def _source_paths() -> dict[str, Path]:
    return {
        "plan": PLAN,
        "question": QUESTION,
        "adapter": Path(__file__).resolve(),
        "model_contract": MODEL_CONTRACT,
        "pure_contract": SRC
        / "andes_rl_kundur/env/andes/model_first_contract.py",
        "environment": SRC / "andes_rl_kundur/env/andes/model_first_env.py",
        "stage1_evaluator": SRC
        / "andes_rl_kundur/evaluation/model_first_stage1.py",
        "eval_view": SRC
        / "andes_rl_kundur/evaluation/model_first_stage1_eval_view.py",
        "eval_v2": SRC / "andes_rl_kundur/evaluation/eval_v2.py",
        "contract_tests": ROOT / "tests/test_model_first_contract.py",
        "stage1_tests": ROOT / "tests/test_model_first_stage1.py",
        "eval_view_tests": ROOT
        / "tests/test_model_first_stage1_eval_view.py",
        "adapter_tests": ROOT / "tests/test_r310_model_first_stage1.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def build_contract() -> dict[str, Any]:
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "fresh-nonlearning-stage1",
        "operating_points": [asdict(point) for point in stage1_operating_points()],
        "positive_power_coordinates_system_pu": {
            name: vector.tolist()
            for name, vector in stage1_power_coordinates().items()
        },
        "active_steps": ACTIVE_STEPS,
        "recovery_steps": RECOVERY_STEPS,
        "control_period_seconds": 0.2,
        "trace_count": 27,
        "fresh_execution_required": True,
        "forbidden_source_rounds": ["R307", "R308"],
        "solver": {
            "initialization_tolerance": INITIALIZATION_TOLERANCE,
            "initialization_tiny_correction_threshold": INITIALIZATION_TOL_ZERO,
            "dynamic_tolerance": DYNAMIC_TOLERANCE,
            "dynamic_tiny_correction_threshold": DYNAMIC_TOL_ZERO,
            "transition_count": 1,
        },
        "classification": [
            "INVALID-STAGE1-EXECUTION",
            "STAGE1-AUTHORITY-NO-GO",
            "STAGE1-PASS",
        ],
        "eval": {
            "trigger": {
                "run_manifest_trace_count": 27,
                "verified_edge_record_count": 18,
                "source_sidecars_required": True,
            },
            "source_bound_view": {
                "sign": "paired",
                "pulse_sign": "copy original sign",
                "source_record": "bind original path and sha256",
                "all_other_fields": "deep-copy unchanged",
            },
            "execution_profile": "vector_power",
            "required_active_window_seconds": 1.0,
            "bootstrap_resamples": EVAL_BOOTSTRAP_RESAMPLES,
            "bootstrap_seed": EVAL_BOOTSTRAP_SEED,
            "evidence_status": "EXTERNAL_AUTHORITY_REQUIRED",
            "effect_optimization_authorized": False,
        },
        "optimization_rules": {
            "INVALID-STAGE1-EXECUTION": "new-cause-specific-canary-only",
            "STAGE1-AUTHORITY-NO-GO": (
                "one-single-factor-nonlearning-diagnosis-or-stop"
            ),
            "STAGE1-PASS": "predictor-construction-in-separate-round-only",
        },
        "predictor_fitting_authorized": False,
        "controller_development_authorized": False,
        "training_authorized": False,
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
        raise RuntimeError("R310 seal identity mismatch")
    if seal.get("contract_payload_sha256") != _payload_sha256(seal["contract"]):
        raise RuntimeError("R310 seal contract payload drift")
    if seal["contract"].get("training_authorized") is not False:
        raise RuntimeError("R310 seal unexpectedly authorizes training")
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


def _record_path(
    out_dir: Path,
    *,
    point: str,
    coordinate: str,
    sign: str,
) -> tuple[Path, str]:
    if coordinate == "zero":
        return out_dir / "records/baseline" / f"{point}__zero.json", "baseline"
    if coordinate == "common":
        return (
            out_dir / "records/common" / f"{point}__common__{sign}.json",
            "common",
        )
    scenario = f"{point.lower()}_{coordinate}"
    return (
        out_dir / "records/edge_source" / f"{scenario}__{sign}.json",
        "edge_source",
    )


def _run_trace(
    *,
    point: Any,
    coordinate: str,
    sign: str,
    seal_digest: str,
    round_id: str = ROUND_ID,
    question_id: str = QUESTION_ID,
    pulse_amplitude_system_pu: float = 0.05,
) -> dict[str, Any]:
    from andes_rl_kundur.env.andes.model_first_env import AndesModelFirstEnv

    config = replace(
        ModelFirstConfig.for_stage1_operating_point(point),
        tds_post_initialization_convergence_tolerance=DYNAMIC_TOLERANCE,
    )
    vectors = stage1_power_coordinates(pulse_amplitude_system_pu)
    pulse = (
        np.zeros(4)
        if coordinate == "zero"
        else vectors[coordinate] * (1.0 if sign == "positive" else -1.0)
    )
    env = AndesModelFirstEnv(model_first_config=config)
    rows: list[dict[str, Any]] = []
    try:
        env.reset()
        initialization_solver = _jsonable(
            env._model_first_initialization_solver_contract
        )
        initial_soc_readback = env._get_bess_soc().copy()
        zero_md = {index: np.zeros(2) for index in range(env.N_AGENTS)}
        for step in range(TOTAL_STEPS):
            requested = pulse if step < ACTIVE_STEPS else np.zeros(4)
            _, _, _, info = env.step(zero_md, bess_power_request_pu=requested)
            row = _jsonable(info)
            row["step"] = step
            row["t"] = row.pop("time")
            frequency = np.asarray(row["freq_hz_physical"], dtype=float)
            row["delta_f_physical_hz"] = (frequency - 60.0).tolist()
            row["action_norm"] = [[0.0, 0.0] for _ in range(4)]
            rows.append(row)
        structural = _jsonable(env.structural_contract())
    finally:
        env.close()

    completed = len(rows) == TOTAL_STEPS and not any(
        bool(row["tds_failed"]) for row in rows
    )
    scenario = f"{point.name.lower()}_{coordinate}"
    if coordinate != "zero" and not np.isclose(
        pulse_amplitude_system_pu, 0.05, rtol=0.0, atol=1e-15
    ):
        amplitude_slug = f"{pulse_amplitude_system_pu:.6f}".rstrip("0").rstrip(".")
        scenario = f"{scenario}_a{amplitude_slug.replace('.', 'p')}"
    record: dict[str, Any] = {
        "schema_version": 1,
        "round": round_id,
        "question": question_id,
        "seal_sha256": seal_digest,
        "scenario": scenario,
        "controller": sign,
        "operating_point": point.name,
        "coordinate": coordinate,
        "sign": sign,
        "location": f"{point.name}/{coordinate}",
        "severity": f"tie_k={point.tie_rx_scale:g}",
        "initial_soc": point.initial_soc,
        "pulse_amplitude_system_pu": (
            0.0 if coordinate == "zero" else float(pulse_amplitude_system_pu)
        ),
        "initial_soc_readback": initial_soc_readback.tolist(),
        "initialization_solver": initialization_solver,
        "completed": completed,
        "tds_failed": not completed,
        "n_steps": len(rows),
        "requested_steps": TOTAL_STEPS,
        "metric_frequency_basis": "andes_physical_hz",
        "andes_nominal_frequency_hz": 60.0,
        "controller_config": {
            "architecture": LOCAL_VECTOR_ARCHITECTURE,
            "area_residual": {"active_steps": ACTIVE_STEPS},
        },
        "structural": structural,
        "execution_runtime": _runtime_record(),
        "traces": rows,
    }
    if coordinate.startswith("edge_"):
        record["mechanism_trace"] = [
            {
                "total_residual_sum_system_pu": float(
                    np.sum(row["bess_requested_power_system_pu"])
                ),
                "total_residual_rms_system_pu": float(
                    np.sqrt(
                        np.mean(
                            np.square(row["bess_requested_power_system_pu"])
                        )
                    )
                ),
            }
            for row in rows
        ]
    return record


def run(seal_path: Path, expected: str, out_dir: Path) -> None:
    _seal, seal_digest = _load_seal(seal_path, expected)
    out_dir = out_dir.resolve()
    manifest_path = out_dir / "run_manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"R310 run already exists: {manifest_path}")

    entries: list[dict[str, str]] = []
    coordinates: Sequence[str] = tuple(stage1_power_coordinates())
    for point in stage1_operating_points():
        jobs = [("zero", "zero")]
        jobs.extend(
            (coordinate, sign)
            for coordinate in coordinates
            for sign in ("positive", "negative")
        )
        for coordinate, sign in jobs:
            record = _run_trace(
                point=point,
                coordinate=coordinate,
                sign=sign,
                seal_digest=seal_digest,
            )
            path, group = _record_path(
                out_dir,
                point=point.name,
                coordinate=coordinate,
                sign=sign,
            )
            digest = _write_new_json(path, record)
            entries.append(
                {"path": _path_text(path), "sha256": digest, "group": group}
            )
            print(f"trace={point.name}/{coordinate}/{sign}", flush=True)

    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "trace_count": len(entries),
        "records": entries,
        "fresh_execution": True,
        "forbidden_source_rounds_used": [],
        "execution_runtime": _runtime_record(),
        "training_authorized": False,
    }
    digest = _write_new_json(manifest_path, manifest)
    print(f"trace_count={len(entries)}", flush=True)
    print(f"run_manifest_sha256={digest}", flush=True)


def _load_run_records(
    out_dir: Path,
    seal_digest: str,
) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    manifest, manifest_digest = _read_verified_json(out_dir / "run_manifest.json")
    if (
        manifest.get("seal_sha256") != seal_digest
        or manifest.get("round") != ROUND_ID
        or manifest.get("question") != QUESTION_ID
        or manifest.get("trace_count") != 27
        or manifest.get("fresh_execution") is not True
        or manifest.get("forbidden_source_rounds_used") != []
    ):
        raise RuntimeError("R310 manifest freshness or identity mismatch")
    records = [
        _read_verified_json(ROOT / entry["path"], entry["sha256"])[0]
        for entry in manifest.get("records", [])
    ]
    return manifest, manifest_digest, records


def eval_records(seal_path: Path, expected: str, out_dir: Path) -> None:
    _seal, seal_digest = _load_seal(seal_path, expected)
    manifest, manifest_digest, _records = _load_run_records(out_dir, seal_digest)
    edge_entries = [
        entry for entry in manifest["records"] if entry["group"] == "edge_source"
    ]
    if len(edge_entries) != 18:
        raise RuntimeError("R310 EVAL trigger requires exactly 18 edge records")

    view_entries: list[dict[str, str]] = []
    eval_input = out_dir.resolve() / "eval_input"
    for entry in edge_entries:
        record, _ = _read_verified_json(ROOT / entry["path"], entry["sha256"])
        view = build_fresh_stage1_eval_view(
            record,
            source_path=entry["path"],
            source_sha256=entry["sha256"],
        )
        destination = eval_input / Path(entry["path"]).name
        view_digest = _write_new_json(destination, view)
        view_entries.append(
            {
                "path": _path_text(destination),
                "sha256": view_digest,
                "source_path": entry["path"],
                "source_sha256": entry["sha256"],
            }
        )
    eval_input_manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "run_manifest_sha256": manifest_digest,
        "record_count": len(view_entries),
        "records": view_entries,
        "transformation": {
            "sign": "paired",
            "pulse_sign": "copy original sign",
            "source_record": "bind original path and sha256",
            "all_other_fields": "deep-copy unchanged",
        },
        "threshold_changes": False,
        "trace_rerun": False,
        "evidence_authority_change": False,
    }
    input_manifest_digest = _write_new_json(
        out_dir / "eval_input_manifest.json",
        eval_input_manifest,
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
    print(f"eval_input_manifest_sha256={input_manifest_digest}", flush=True)
    print(f"diagnostic_pass={scorecard['validity']['diagnostic_pass']}", flush=True)
    print(f"evidence_status={scorecard['evidence_status']['status']}", flush=True)
    print(json.dumps(outputs, indent=2), flush=True)


def analyse(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    manifest, manifest_digest, records = _load_run_records(out_dir, seal_digest)
    input_manifest, input_manifest_digest = _read_verified_json(
        out_dir / "eval_input_manifest.json"
    )
    if (
        input_manifest.get("record_count") != 18
        or input_manifest.get("run_manifest_sha256") != manifest_digest
        or input_manifest.get("threshold_changes") is not False
        or input_manifest.get("trace_rerun") is not False
    ):
        raise RuntimeError("R310 EVAL input manifest contract mismatch")
    source_entries = {
        (entry["path"], entry["sha256"])
        for entry in manifest["records"]
        if entry["group"] == "edge_source"
    }
    bound_entries = {
        (entry["source_path"], entry["source_sha256"])
        for entry in input_manifest["records"]
    }
    if bound_entries != source_entries:
        raise RuntimeError("R310 EVAL source binding mismatch")

    scorecard_path = out_dir / "eval/scorecard.json"
    scorecard, scorecard_digest = _read_verified_json(scorecard_path)
    decision = evaluate_stage1_records(
        records,
        scorecard,
        expected_round=ROUND_ID,
        expected_question=QUESTION_ID,
        require_two_phase_solver=True,
    )
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "run_manifest_sha256": manifest_digest,
        "eval_input_manifest_sha256": input_manifest_digest,
        "eval_scorecard_sha256": scorecard_digest,
        "fresh_execution": True,
        "optimization_rule": seal["contract"]["optimization_rules"][
            decision["classification"]
        ],
        **decision,
    }
    analysis_path = out_dir / "analysis.json"
    analysis_digest = _write_new_json(analysis_path, analysis)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal": {"path": _path_text(seal_path), "sha256": seal_digest},
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
        "analysis": {"path": _path_text(analysis_path), "sha256": analysis_digest},
        "sources_verified": seal["sources"],
        "contract_payload_sha256": seal["contract_payload_sha256"],
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
    for command in ("run", "eval", "analyse"):
        subparser = commands.add_parser(command)
        subparser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
        subparser.add_argument("--expected-seal-sha256", required=True)
        subparser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        prepare(args.seal)
    elif args.command == "run":
        run(args.seal, args.expected_seal_sha256, args.out_dir)
    elif args.command == "eval":
        eval_records(args.seal, args.expected_seal_sha256, args.out_dir)
    else:
        analyse(args.seal, args.expected_seal_sha256, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
