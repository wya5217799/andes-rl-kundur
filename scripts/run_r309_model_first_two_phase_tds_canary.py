#!/usr/bin/env python3
"""Seal, run, evaluate, and analyse the R309 two-phase TDS canary."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
from collections.abc import Mapping
from dataclasses import replace
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
from andes_rl_kundur.evaluation.model_first_two_phase_tds_canary import (  # noqa: E402
    ACTIVE_STEPS,
    ALGEBRAIC_RESIDUAL_MAX,
    DYNAMIC_TOL_ZERO,
    DYNAMIC_TOLERANCE,
    EXPECTED_STEPS,
    INITIALIZATION_TOL_ZERO,
    INITIALIZATION_TOLERANCE,
    evaluate_two_phase_tds_canary_records,
)

ROUND_ID = "R309"
QUESTION_ID = "Q-0065"
PLAN = ROOT / "memory/rounds/R309/plan.md"
QUESTION = ROOT / "memory/questions/Q-0065.md"
DEFAULT_SEAL = ROOT / "memory/rounds/R309/two_phase_tds_canary_seal.json"
DEFAULT_OUT = ROOT / "results/r309_model_first_two_phase_tds_canary"
RECOVERY_STEPS = EXPECTED_STEPS - ACTIVE_STEPS


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
        "contract": SRC / "andes_rl_kundur/env/andes/model_first_contract.py",
        "environment": SRC / "andes_rl_kundur/env/andes/model_first_env.py",
        "evaluator": SRC
        / "andes_rl_kundur/evaluation/model_first_two_phase_tds_canary.py",
        "contract_tests": ROOT / "tests/test_model_first_contract.py",
        "evaluator_tests": ROOT
        / "tests/test_model_first_two_phase_tds_canary.py",
        "adapter_tests": ROOT
        / "tests/test_r309_model_first_two_phase_tds_canary.py",
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
        "stage": "two-phase-solver-validity-only",
        "tds_method": "trapezoid",
        "initialization_tds_convergence_tolerance": INITIALIZATION_TOLERANCE,
        "initialization_tds_tiny_correction_threshold": INITIALIZATION_TOL_ZERO,
        "dynamic_tds_convergence_tolerance": DYNAMIC_TOLERANCE,
        "dynamic_tds_tiny_correction_threshold": DYNAMIC_TOL_ZERO,
        "solver_transition_count": 1,
        "algebraic_readback_semantics": "post_control_step_recomputed_dae_g",
        "algebraic_residual_max": ALGEBRAIC_RESIDUAL_MAX,
        "operating_point": "OP1",
        "trace_bank": ["OP1/zero/zero", "OP1/edge_2/negative"],
        "active_steps": ACTIVE_STEPS,
        "recovery_steps": RECOVERY_STEPS,
        "control_period_seconds": 0.2,
        "evaluation_kind": "bounded_execution_integrity_not_eval_v2_efficacy",
        "parameter_sweep_authorized": False,
        "full_stage1_authorized": False,
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
        raise RuntimeError("R309 seal identity mismatch")
    if seal.get("contract_payload_sha256") != _payload_sha256(seal["contract"]):
        raise RuntimeError("R309 seal contract payload drift")
    if seal["contract"].get("training_authorized") is not False:
        raise RuntimeError("R309 seal unexpectedly authorizes training")
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


def _run_trace(*, coordinate: str, sign: str, seal_digest: str) -> dict[str, Any]:
    from andes_rl_kundur.env.andes.model_first_env import AndesModelFirstEnv

    point = next(point for point in stage1_operating_points() if point.name == "OP1")
    config = replace(
        ModelFirstConfig.for_stage1_operating_point(point),
        tds_post_initialization_convergence_tolerance=DYNAMIC_TOLERANCE,
    )
    pulse = (
        np.zeros(4)
        if coordinate == "zero"
        else -stage1_power_coordinates()["edge_2"]
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
        for step in range(EXPECTED_STEPS):
            requested = pulse if step < ACTIVE_STEPS else np.zeros(4)
            _, _, _, info = env.step(zero_md, bess_power_request_pu=requested)
            row = _jsonable(info)
            row["step"] = step
            row["t"] = row.pop("time")
            rows.append(row)
        structural = _jsonable(env.structural_contract())
    finally:
        env.close()

    completed = len(rows) == EXPECTED_STEPS and not any(
        bool(row["tds_failed"]) for row in rows
    )
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "seal_sha256": seal_digest,
        "scenario": f"op1_{coordinate}",
        "operating_point": "OP1",
        "coordinate": coordinate,
        "sign": sign,
        "initial_soc": point.initial_soc,
        "initial_soc_readback": initial_soc_readback.tolist(),
        "initialization_solver": initialization_solver,
        "completed": completed,
        "tds_failed": not completed,
        "n_steps": len(rows),
        "requested_steps": EXPECTED_STEPS,
        "structural": structural,
        "execution_runtime": _runtime_record(),
        "traces": rows,
    }


def run(seal_path: Path, expected: str, out_dir: Path) -> None:
    _seal, seal_digest = _load_seal(seal_path, expected)
    out_dir = out_dir.resolve()
    manifest_path = out_dir / "run_manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"R309 run already exists: {manifest_path}")
    entries: list[dict[str, str]] = []
    for coordinate, sign in (("zero", "zero"), ("edge_2", "negative")):
        record = _run_trace(
            coordinate=coordinate,
            sign=sign,
            seal_digest=seal_digest,
        )
        path = out_dir / "records" / f"op1__{coordinate}__{sign}.json"
        digest = _write_new_json(path, record)
        entries.append({"path": _path_text(path), "sha256": digest})
        print(f"trace=OP1/{coordinate}/{sign}", flush=True)
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "trace_count": len(entries),
        "records": entries,
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
    if manifest.get("seal_sha256") != seal_digest:
        raise RuntimeError("R309 manifest seal mismatch")
    records = [
        _read_verified_json(ROOT / entry["path"], entry["sha256"])[0]
        for entry in manifest.get("records", [])
    ]
    return manifest, manifest_digest, records


def eval_records(seal_path: Path, expected: str, out_dir: Path) -> None:
    _seal, seal_digest = _load_seal(seal_path, expected)
    manifest, manifest_digest, records = _load_run_records(out_dir, seal_digest)
    decision = evaluate_two_phase_tds_canary_records(records)
    scorecard = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "run_manifest_sha256": manifest_digest,
        "source": {"trace_count": manifest.get("trace_count")},
        "evidence_status": {
            "status": "EXTERNAL_AUTHORITY_REQUIRED",
            "eligible": None,
            "scope": "two-phase-solver-validity-only",
        },
        **decision,
    }
    digest = _write_new_json(out_dir / "eval/scorecard.json", scorecard)
    print(f"classification={decision['classification']}", flush=True)
    print("evidence_status=EXTERNAL_AUTHORITY_REQUIRED", flush=True)
    print(f"eval_scorecard_sha256={digest}", flush=True)


def analyse(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    _manifest, manifest_digest, records = _load_run_records(out_dir, seal_digest)
    scorecard, scorecard_digest = _read_verified_json(
        out_dir / "eval/scorecard.json"
    )
    decision = evaluate_two_phase_tds_canary_records(records)
    if scorecard.get("classification") != decision["classification"]:
        raise RuntimeError("R309 scorecard decision drift")
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "run_manifest_sha256": manifest_digest,
        "eval_scorecard_sha256": scorecard_digest,
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
        "eval_scorecard": {
            "path": _path_text(out_dir / "eval/scorecard.json"),
            "sha256": scorecard_digest,
        },
        "analysis": {"path": _path_text(analysis_path), "sha256": analysis_digest},
        "sources_verified": seal["sources"],
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "training_authorized": False,
    }
    provenance_digest = _write_new_json(out_dir / "provenance.json", provenance)
    print(f"classification={analysis['classification']}", flush=True)
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
