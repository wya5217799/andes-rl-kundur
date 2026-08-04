"""Prepare, execute, and analyse the sealed R327 reference amendment.

Only the eight missing R326 legacy prefixes are recomputed.  Each pass starts
one fresh worker that synthesizes and consumes each arm locally in the original
R325 arm order.  R326 candidate development artifacts remain immutable and the
conditional holdout is never reachable from this adapter.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
for import_root in (ROOT, ROOT / "src"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

import scripts.run_r326_solver_adequacy as r326  # noqa: E402
from probes.r327_reference_recovery import analyse_r327_recovery  # noqa: E402

ROUND_ID = "R327"
QUESTION_ID = "Q-0080"
R326_SEAL = ROOT / "memory/rounds/R326/solver_adequacy_seal.json"
R326_EXECUTION = ROOT / "results/r326_solver_adequacy/execution.json"
R326_ANALYSIS = ROOT / "results/r326_solver_adequacy/analysis.json"
R326_PROVENANCE = ROOT / "results/r326_solver_adequacy/provenance.json"
R326_MANIFEST = ROOT / "results/r326_solver_adequacy/run_manifest.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R327/reference_recovery_seal.json"
DEFAULT_OUT = ROOT / "results/r327_reference_recovery"
NATIVE_NUMERICAL_THREADS = 24

EXPECTED_KEYS = (
    ("retained_cross", "HS0/triangle/common/positive", "nominal"),
    ("retained_cross", "HS0/triangle/edge_0/positive", "nominal"),
    ("retained_cross", "HS0/triangle/edge_2/positive", "nominal"),
    ("retained_cross", "HS1/triangle/common/negative", "nominal"),
    ("retained_cross", "HS1/triangle/edge_1/positive", "nominal"),
    ("cross_deleted", "HS0/triangle/edge_0/positive", "nominal"),
    ("cross_deleted", "HS0/triangle/edge_1/negative", "nominal"),
    ("cross_deleted", "HS1/triangle/edge_1/positive", "nominal"),
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_text(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


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


def _write_new_json(path: Path, payload: object) -> str:
    return r326._write_new_json(path, payload)


def build_contract() -> dict[str, object]:
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "model-only-legacy-reference-recovery-amendment",
        "parent_round": "R326",
        "reference_recovery": {
            "expected_keys": [list(item) for item in EXPECTED_KEYS],
            "worker_count": 1,
            "native_numerical_threads": NATIVE_NUMERICAL_THREADS,
            "process_start_method": "spawn",
            "design_transfer": "none-rebuild-locally-per-arm",
            "arm_order": ["retained_cross", "cross_deleted"],
            "prefix_action_absolute_tolerance": 2.0e-5,
            "prefix_output_absolute_tolerance": 1.0e-6,
            "candidate_development_source": _path_text(R326_EXECUTION),
            "holdout_access": "forbidden",
        },
        "comparison_identifiability": {
            "decision": "QUALIFY",
            "estimand": "missing-r326-successful-prefix-equivalence-only",
        },
        "classification": [
            "INVALID-REFERENCE-RECOVERY",
            "REFERENCE-RECOVERY-NO-GO",
            "DEVELOPMENT-NO-GO",
            "DEVELOPMENT-ADMISSION-PASS-HOLDOUT-SEALED",
        ],
        "eval": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R327/plan.md",
        "question": ROOT / "memory/questions/Q-0080.md",
        "r325_adapter": ROOT / "scripts/run_r325_constrained_horizon.py",
        "r326_seal": R326_SEAL,
        "r326_execution": R326_EXECUTION,
        "r326_analysis": R326_ANALYSIS,
        "r326_provenance": R326_PROVENANCE,
        "r326_manifest": R326_MANIFEST,
        "r326_adapter": ROOT / "scripts/run_r326_solver_adequacy.py",
        "r326_probe": ROOT / "probes/r326_solver_adequacy.py",
        "solver_module": ROOT / "src/andes_rl_kundur/control/model_first_constrained_qp.py",
        "validation_probe": ROOT / "probes/r327_reference_recovery.py",
        "adapter": ROOT / "scripts/run_r327_reference_recovery.py",
        "validation_tests": ROOT / "tests/test_r327_reference_recovery.py",
        "adapter_tests": ROOT / "tests/test_r327_reference_recovery_adapter.py",
        "project_dependencies": ROOT / "pyproject.toml",
        "artifact_io": ROOT / "memory/tools/artifact_io.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _parent_bundle() -> tuple[dict[str, Any], dict[str, Any], dict[str, object]]:
    seal, seal_digest = r326.r325._read_verified_json(R326_SEAL)
    execution, execution_digest = r326.r325._read_verified_json(R326_EXECUTION)
    analysis, analysis_digest = r326.r325._read_verified_json(R326_ANALYSIS)
    _provenance, provenance_digest = r326.r325._read_verified_json(R326_PROVENANCE)
    _manifest, manifest_digest = r326.r325._read_verified_json(R326_MANIFEST)
    contract = seal.get("contract")
    if not isinstance(contract, dict):
        raise RuntimeError("R326 seal has no contract")
    missing = {
        (str(arm), str(row.get("case")), str(row.get("mismatch")))
        for arm in ("retained_cross", "cross_deleted")
        for row in execution["arms"][arm]["rows"]["development"]
        if row.get("reference_status_matches_r325") is not True
    }
    guards = analysis.get("validity_guards")
    if (
        seal.get("round") != "R326"
        or seal.get("contract_payload_sha256") != _payload_sha256(contract)
        or analysis.get("classification") != "SOLVER-REPAIR-NO-GO"
        or analysis.get("holdout_accessed") is not False
        or execution.get("holdout_accessed") is not False
        or not isinstance(guards, dict)
        or not guards
        or any(value is not True for value in guards.values())
        or missing != set(EXPECTED_KEYS)
    ):
        raise RuntimeError("R326 parent is not the exact valid no-go amendment target")
    parent = {
        "r326_seal": {"path": _path_text(R326_SEAL), "sha256": seal_digest},
        "r326_execution": {
            "path": _path_text(R326_EXECUTION),
            "sha256": execution_digest,
        },
        "r326_analysis": {
            "path": _path_text(R326_ANALYSIS),
            "sha256": analysis_digest,
        },
        "r326_provenance": {
            "path": _path_text(R326_PROVENANCE),
            "sha256": provenance_digest,
        },
        "r326_manifest": {
            "path": _path_text(R326_MANIFEST),
            "sha256": manifest_digest,
        },
        "r326_contract_payload_sha256": seal["contract_payload_sha256"],
        "r326_contract": contract,
    }
    return execution, analysis, parent


def prepare(seal_path: Path) -> str:
    _execution, _analysis, parent = _parent_bundle()
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "parent": parent,
        "sources": _sources(),
    }
    return _write_new_json(seal_path, seal)


def _load_seal(path: Path, expected: str) -> tuple[dict[str, Any], str]:
    seal, digest = r326.r325._read_verified_json(path, expected)
    _execution, _analysis, parent = _parent_bundle()
    contract = build_contract()
    if (
        seal.get("round") != ROUND_ID
        or seal.get("question") != QUESTION_ID
        or seal.get("contract") != contract
        or seal.get("contract_payload_sha256") != _payload_sha256(contract)
        or seal.get("parent") != parent
        or seal.get("sources") != _sources()
    ):
        raise RuntimeError("R327 seal contract, parent, or source drift")
    return seal, digest


def _reference_recovery_pass() -> list[dict[str, object]]:
    """Run the exact eight rows with no serialized synthesized design."""

    with threadpool_limits(limits=NATIVE_NUMERICAL_THREADS):
        parent, _model_digest, _analysis, _analysis_digest = r326.r325._load_parent()
        retained, markov = r326.r325._models(parent)
        status = r326._r325_status_map()
        cases = {item.name: item for item in r326.r325.development_cases()}
        rows: list[dict[str, object]] = []
        for arm, models in (
            ("retained_cross", retained),
            ("cross_deleted", r326.r325._cross_deleted_models(markov)),
        ):
            designs, feasible, error = r326.r325._designs(models)
            if not feasible:
                raise RuntimeError(f"{arm} local design synthesis failed: {error}")
            for expected_key in EXPECTED_KEYS:
                expected_arm, case_name, mismatch_name = expected_key
                if expected_arm != arm:
                    continue
                case = cases[case_name]
                legacy = r326._legacy_prefix(
                    retained[case.point],
                    designs[case.point],
                    case,
                    np.zeros((4, 4)),
                    status[expected_key],
                )
                rows.append(
                    {
                        "arm": arm,
                        "case": case_name,
                        "mismatch": mismatch_name,
                        "reference_completed_steps": len(legacy["samples"]),
                        "reference_target_steps": legacy["target_steps"],
                        "reference_failure_kind": legacy["failure_kind"],
                        "reference_failure_step": legacy["failure_step"],
                        "reference_failure_message": legacy["failure_message"],
                        "reference_status_matches_r325": legacy["replay_complete"],
                        "prefix_samples": legacy["samples"],
                    }
                )
    return rows


def _fresh_reference_pass() -> list[dict[str, object]]:
    with ProcessPoolExecutor(
        max_workers=1,
        mp_context=mp.get_context("spawn"),
    ) as pool:
        return pool.submit(_reference_recovery_pass).result()


def execute(seal_path: Path, expected: str, out_dir: Path) -> str:
    seal, seal_digest = _load_seal(seal_path, expected)
    created_utc = datetime.now(UTC).isoformat()
    first = _fresh_reference_pass()
    second = _fresh_reference_pass()
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": created_utc,
        "seal_sha256": seal_digest,
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "parent_execution_sha256": seal["parent"]["r326_execution"]["sha256"],
        "parent_analysis_sha256": seal["parent"]["r326_analysis"]["sha256"],
        "sealed_source_identity": True,
        "parent_identity": True,
        "holdout_accessed": False,
        "deterministic_reference_replay": _canonical_bytes(first) == _canonical_bytes(second),
        "rows": first,
        "eval": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
    return _write_new_json(out_dir / "execution.json", payload)


def analyse(seal_path: Path, expected: str, out_dir: Path) -> dict[str, str]:
    seal, seal_digest = _load_seal(seal_path, expected)
    execution, execution_digest = r326.r325._read_verified_json(out_dir / "execution.json")
    r326_execution, _r326_analysis, _parent = _parent_bundle()
    execution_view = dict(execution)
    execution_view["execution_sha256"] = execution_digest
    parent_view = dict(r326_execution)
    parent_view["execution_sha256"] = seal["parent"]["r326_execution"]["sha256"]
    first = analyse_r327_recovery(
        execution_view,
        seal["contract"],
        parent_view,
        seal["parent"]["r326_contract"],
        analysis_replay=True,
    )
    second = analyse_r327_recovery(
        execution_view,
        seal["contract"],
        parent_view,
        seal["parent"]["r326_contract"],
        analysis_replay=True,
    )
    deterministic = _canonical_bytes(first) == _canonical_bytes(second)
    if not deterministic:
        first = analyse_r327_recovery(
            execution_view,
            seal["contract"],
            parent_view,
            seal["parent"]["r326_contract"],
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
