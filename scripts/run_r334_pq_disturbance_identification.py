"""Correct R333's evidence binding without changing its scientific bank.

Usage::

    python scripts/run_r334_pq_disturbance_identification.py prepare
    python scripts/andes_scratch.py scripts/run_r334_pq_disturbance_identification.py execute --expected-sha256 <seal>
    python scripts/run_r334_pq_disturbance_identification.py analyse --expected-sha256 <seal>

The physical ``execute`` command is WSL-only. Reward diagnostics inherited
from the environment are stored but are never read by the R334 classifier.
"""

from __future__ import annotations

import argparse
import copy
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for search_path in (ROOT, SRC):
    if str(search_path) not in sys.path:
        sys.path.insert(0, str(search_path))

from memory.tools.artifact_io import (  # noqa: E402
    payload_sha256,
    read_verified_json,
    sha256_file,
    verified_digest_only,
    write_new_json,
)
from probes.r334_pq_disturbance_identification import (  # noqa: E402
    analyse_r334_pq_disturbance_identification,
)
from scripts import run_r333_pq_disturbance_identification as _base  # noqa: E402

ROUND_ID = "R334"
QUESTION_ID = "Q-0085"
DEFAULT_SEAL = ROOT / "memory/rounds/R334/pq_disturbance_identification_seal.json"
DEFAULT_OUT = ROOT / "results/r334_pq_disturbance_identification"
EXPECTED_CASE_SHA256 = "f725e03ba12d8207616f68acdd606bbd35e7c4a68f13e66d7db43925adac2ed8"
REWARD_BOUNDARY = {
    "reward_diagnostics_computed": True,
    "reward_diagnostics_stored": True,
    "reward_used_for_action": False,
    "reward_used_for_fitting": False,
    "reward_used_for_selection": False,
    "reward_used_for_training": False,
    "reward_used_for_classification": False,
    "reward_used_for_claim": False,
}
_R333_BUILD_CONTRACT = _base.build_contract


def _path_text(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


@contextmanager
def _scoped_r334_binding() -> Iterator[None]:
    """Bind the inherited runner to R334 and restore it even on failure."""

    previous_round = _base.ROUND_ID
    previous_question = _base.QUESTION_ID
    try:
        _base.ROUND_ID = ROUND_ID
        _base.QUESTION_ID = QUESTION_ID
        yield
    finally:
        _base.ROUND_ID = previous_round
        _base.QUESTION_ID = previous_question


def build_contract() -> dict[str, object]:
    with _scoped_r334_binding():
        contract = copy.deepcopy(_R333_BUILD_CONTRACT())
    contract.update(
        {
            "reward_boundary": dict(REWARD_BOUNDARY),
            "pair_midpoint_metric": "normalized-l2-midpoint-residual",
            "evidence_correction": (
                "complete repository-local runtime source superset and explicit "
                "diagnostic-reward non-use boundary"
            ),
        }
    )
    return contract


def _source_paths() -> dict[str, Path]:
    explicit = {
        "plan": ROOT / "memory/rounds/R334/plan.md",
        "question": ROOT / "memory/questions/Q-0085.md",
        "r334_probe": ROOT / "probes/r334_pq_disturbance_identification.py",
        "r334_adapter": Path(__file__).resolve(),
        "r334_tests": ROOT / "tests/test_r334_pq_disturbance_correction.py",
        "r333_probe": ROOT / "probes/r333_pq_disturbance_identification.py",
        "r333_adapter": ROOT / "scripts/run_r333_pq_disturbance_identification.py",
        "r333_helper": (
            SRC / "andes_rl_kundur/env/andes/model_first_pq_disturbance.py"
        ),
        "andes_scratch": ROOT / "scripts/andes_scratch.py",
        "artifact_io": ROOT / "memory/tools/artifact_io.py",
    }
    explicit_paths = {path.resolve() for path in explicit.values()}
    package_sources = {
        f"package::{path.relative_to(SRC).as_posix()}": path
        for path in sorted(
            (
                candidate
                for candidate in SRC.rglob("*.py")
                if candidate.is_file() and candidate.resolve() not in explicit_paths
            ),
            key=lambda candidate: candidate.relative_to(SRC).as_posix(),
        )
    }
    return {**explicit, **package_sources}


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _parents() -> dict[str, dict[str, str]]:
    parents = {
        "r316_dynamic_model": {
            "path": _path_text(_base.R316_MODEL),
            "sha256": verified_digest_only(_base.R316_MODEL),
        },
        "r329_seal": {
            "path": _path_text(_base.R329_SEAL),
            "sha256": verified_digest_only(_base.R329_SEAL),
        },
        "r332_analysis": {
            "path": _path_text(_base.R332_ANALYSIS),
            "sha256": verified_digest_only(_base.R332_ANALYSIS),
        },
    }
    for name, path in {
        "r333_process_correction": ROOT / "memory/claims/CLM-0875.md",
        "r333_failed_gate_feed": (
            ROOT / "paper/decoupling_marl_model_first/reports/R333.md"
        ),
        "r333_failed_gate_verdict": ROOT / "memory/rounds/R333/verdict.md",
    }.items():
        parents[name] = {"path": _path_text(path), "sha256": sha256_file(path)}
    return parents


def prepare(seal_path: Path, *, created_utc: str | None = None) -> str:
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": created_utc or datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": payload_sha256(contract),
        "parents": _parents(),
        "sources": _sources(),
        "installed_andes": {
            "version": "2.0.0",
            "official_tag_commit": "eda5163c9ee8d19945a1dd5d1771fec5da608c27",
            "sources": _base.EXPECTED_INSTALLED_SOURCES,
        },
        "installed_andes_case": {
            "relative_path": "andes/cases/kundur/kundur_full.xlsx",
            "sha256": EXPECTED_CASE_SHA256,
        },
        "official_sources": list(_base.OFFICIAL_SOURCES),
        "reward_boundary": dict(REWARD_BOUNDARY),
    }
    return write_new_json(seal_path, seal)


def _load_seal(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    seal, digest = read_verified_json(path, expected_sha256)
    contract = build_contract()
    if (
        seal.get("round") != ROUND_ID
        or seal.get("question") != QUESTION_ID
        or seal.get("contract") != contract
        or seal.get("contract_payload_sha256") != payload_sha256(contract)
        or seal.get("parents") != _parents()
        or seal.get("sources") != _sources()
        or seal.get("installed_andes", {}).get("version") != "2.0.0"
        or seal.get("installed_andes", {}).get("sources")
        != _base.EXPECTED_INSTALLED_SOURCES
        or seal.get("installed_andes_case", {}).get("sha256")
        != EXPECTED_CASE_SHA256
        or seal.get("official_sources") != list(_base.OFFICIAL_SOURCES)
        or seal.get("reward_boundary") != REWARD_BOUNDARY
    ):
        raise RuntimeError("R334 seal contract, source, parent, or authority drift")
    return seal, digest


def _verify_installed_andes() -> dict[str, object]:
    import andes

    installed = _base._verify_installed_andes()
    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    case_digest = sha256_file(case_path)
    if case_digest != EXPECTED_CASE_SHA256:
        raise RuntimeError("installed ANDES Kundur case identity mismatch")
    return {
        **installed,
        "case": {"path": str(case_path), "sha256": case_digest},
    }


def _reward_fields_stored(records: list[dict[str, object]]) -> bool:
    fields = ("r_f", "r_h", "r_d", "r_smooth")
    return bool(
        len(records) == 6
        and all(
            isinstance(record.get("traces"), list)
            and len(record["traces"]) == 25
            and all(
                isinstance(row, dict) and all(field in row for field in fields)
                for row in record["traces"]
            )
            for record in records
        )
    )


def _reserve_formal_attempt(
    out_dir: Path,
    *,
    seal_digest: str,
    created_utc: str | None = None,
) -> str:
    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"R334 formal output is not empty: {out_dir}")
    return write_new_json(
        out_dir / "formal_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "stage": "formal-execution-started",
            "created_utc": created_utc or datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "physical_execution_started": True,
            "controller_executed": False,
            "distributed_runtime_executed": False,
            "training_executed": False,
            "eval_executed": False,
            "retry_authorized": False,
            **REWARD_BOUNDARY,
        },
    )


def _write_execution_failure(
    out_dir: Path,
    *,
    seal_digest: str,
    attempt_digest: str,
    error: Exception,
) -> None:
    try:
        write_new_json(
            out_dir / "execution_failure.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "classification": "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION",
                "created_utc": datetime.now(UTC).isoformat(),
                "seal_sha256": seal_digest,
                "formal_attempt_sha256": attempt_digest,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "retry_authorized": False,
                **REWARD_BOUNDARY,
            },
        )
    except Exception:
        pass


def execute(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    _seal, seal_digest = _load_seal(seal_path, expected_sha256)
    installed = _verify_installed_andes()
    model, model_digest = _base._load_r316_model()
    out_dir = out_dir.resolve()
    attempt_digest = _reserve_formal_attempt(out_dir, seal_digest=seal_digest)
    try:
        with _scoped_r334_binding():
            records = [
                _base._run_record(
                    point=point,
                    sign=sign,
                    seal_digest=seal_digest,
                    model_payload=model,
                    model_digest=model_digest,
                )
                for point in _base.POINTS
                for sign in _base.SIGNS
            ]
        if not _reward_fields_stored(records):
            raise RuntimeError("inherited reward diagnostics were not stored")
        for record in records:
            record.update(REWARD_BOUNDARY)
    except Exception as error:
        _write_execution_failure(
            out_dir,
            seal_digest=seal_digest,
            attempt_digest=attempt_digest,
            error=error,
        )
        raise
    execution = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "dynamic_model_sha256": model_digest,
        "formal_attempt_sha256": attempt_digest,
        "records": records,
        "source_identity": True,
        "parent_identity": True,
        "runtime_identity": True,
        "physical_execution_performed": True,
        "controller_executed": False,
        "closed_loop_executed": False,
        "distributed_runtime_executed": False,
        "training_executed": False,
        "eval_executed": False,
        **REWARD_BOUNDARY,
    }
    execution_digest = write_new_json(out_dir / "execution.json", execution)
    provenance_digest = write_new_json(
        out_dir / "provenance.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "execution_sha256": execution_digest,
            "formal_attempt_sha256": attempt_digest,
            "dynamic_model_sha256": model_digest,
            "runtime": _base._runtime_record(installed),
            "physical_execution_performed": True,
            "controller_executed": False,
            "distributed_runtime_executed": False,
            "training_executed": False,
            "eval_executed": False,
            **REWARD_BOUNDARY,
        },
    )
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "record_count": len(records),
        "records": [
            {
                "name": "formal_attempt",
                "path": _path_text(out_dir / "formal_attempt.json"),
                "sha256": attempt_digest,
            },
            {
                "name": "execution",
                "path": _path_text(out_dir / "execution.json"),
                "sha256": execution_digest,
            },
            {
                "name": "provenance",
                "path": _path_text(out_dir / "provenance.json"),
                "sha256": provenance_digest,
            },
        ],
        "training_executed": False,
        "eval_executed": False,
        **REWARD_BOUNDARY,
    }
    manifest_digest = write_new_json(out_dir / "run_manifest.json", manifest)
    print(f"record_count={len(records)}", flush=True)
    print(f"execution_sha256={execution_digest}", flush=True)
    print(f"run_manifest_sha256={manifest_digest}", flush=True)


def _validated_manifest_entries(
    manifest: dict[str, Any],
    out_dir: Path,
) -> dict[str, dict[str, Any]]:
    rows = manifest.get("records")
    if not isinstance(rows, list) or len(rows) != 3:
        raise RuntimeError("R334 manifest must contain exactly three artifacts")
    if not all(isinstance(row, dict) for row in rows):
        raise RuntimeError("R334 manifest contains a non-object artifact entry")
    names = [str(row.get("name")) for row in rows]
    if len(names) != len(set(names)):
        raise RuntimeError("R334 manifest contains duplicate artifact names")
    entries = {name: row for name, row in zip(names, rows, strict=True)}
    expected = {
        "formal_attempt": _path_text(out_dir / "formal_attempt.json"),
        "execution": _path_text(out_dir / "execution.json"),
        "provenance": _path_text(out_dir / "provenance.json"),
    }
    if set(entries) != set(expected) or any(
        entries[name].get("path") != path for name, path in expected.items()
    ):
        raise RuntimeError("R334 manifest artifact inventory mismatch")
    return entries


def _reward_metadata_matches(payload: dict[str, Any]) -> bool:
    return all(payload.get(key) is value for key, value in REWARD_BOUNDARY.items())


def analyse(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected_sha256)
    manifest, manifest_digest = read_verified_json(out_dir / "run_manifest.json")
    if (
        manifest.get("round") != ROUND_ID
        or manifest.get("question") != QUESTION_ID
        or manifest.get("seal_sha256") != seal_digest
        or manifest.get("record_count") != 6
    ):
        raise RuntimeError("R334 run manifest identity mismatch")
    entries = _validated_manifest_entries(manifest, out_dir.resolve())
    attempt, attempt_digest = read_verified_json(
        ROOT / entries["formal_attempt"]["path"],
        entries["formal_attempt"]["sha256"],
    )
    execution, execution_digest = read_verified_json(
        ROOT / entries["execution"]["path"],
        entries["execution"]["sha256"],
    )
    provenance, provenance_digest = read_verified_json(
        ROOT / entries["provenance"]["path"],
        entries["provenance"]["sha256"],
    )
    model, model_digest = _base._load_r316_model()
    expected_inputs: dict[str, dict[str, object]] = {}
    expected_predictions: dict[str, dict[str, object]] = {}
    for point in _base.POINTS:
        expected_inputs[point.name] = {}
        expected_predictions[point.name] = {}
        realization = _base.realization_from_dict(
            model["points"][point.name]["realization"]
        )
        for sign in _base.SIGNS:
            coordinate_input = _base._coordinate_input_sequence(
                delta_load_system_pu=_base.SIGN_DELTA[sign]
            )
            expected_inputs[point.name][sign] = coordinate_input.tolist()
            expected_predictions[point.name][sign] = _base.simulate_state_space(
                realization, coordinate_input
            ).tolist()
    evidence_chain_valid = bool(
        attempt.get("round") == ROUND_ID
        and attempt.get("question") == QUESTION_ID
        and attempt.get("stage") == "formal-execution-started"
        and attempt.get("seal_sha256") == seal_digest
        and attempt.get("physical_execution_started") is True
        and attempt.get("retry_authorized") is False
        and execution.get("formal_attempt_sha256") == attempt_digest
        and execution.get("seal_sha256") == seal_digest
        and execution.get("dynamic_model_sha256") == model_digest
        and provenance.get("formal_attempt_sha256") == attempt_digest
        and provenance.get("execution_sha256") == execution_digest
        and provenance.get("seal_sha256") == seal_digest
        and provenance.get("dynamic_model_sha256") == model_digest
        and provenance.get("runtime", {}).get("andes", {}).get("version") == "2.0.0"
        and provenance.get("runtime", {}).get("andes", {}).get("sources")
        == _base.EXPECTED_INSTALLED_SOURCES
        and provenance.get("runtime", {}).get("andes", {}).get("case", {}).get(
            "sha256"
        )
        == EXPECTED_CASE_SHA256
        and all(
            _reward_metadata_matches(payload)
            for payload in (attempt, execution, provenance, manifest)
        )
        and manifest.get("training_executed") is False
        and manifest.get("eval_executed") is False
    )
    kwargs = {
        "expected_seal_sha256": seal_digest,
        "expected_dynamic_model_sha256": model_digest,
        "expected_coordinate_inputs": expected_inputs,
        "expected_predictions": expected_predictions,
        "evidence_chain_valid": evidence_chain_valid,
    }
    first = analyse_r334_pq_disturbance_identification(
        execution, seal["contract"], **kwargs
    )
    second = analyse_r334_pq_disturbance_identification(
        execution, seal["contract"], **kwargs
    )
    if first != second:
        raise RuntimeError("R334 analysis replay is nondeterministic")
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "seal_sha256": seal_digest,
        "formal_attempt_sha256": attempt_digest,
        "execution_sha256": execution_digest,
        "provenance_sha256": provenance_digest,
        "run_manifest_sha256": manifest_digest,
        "dynamic_model_sha256": model_digest,
        "source_inventory_count": len(seal["sources"]),
        "evidence_chain_valid": evidence_chain_valid,
        "deterministic_replay": True,
        **REWARD_BOUNDARY,
        **first,
    }
    digest = write_new_json(out_dir / "analysis.json", analysis)
    print(f"classification={analysis['classification']}", flush=True)
    print(f"analysis_sha256={digest}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    execute_parser = commands.add_parser("execute")
    execute_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    execute_parser.add_argument("--expected-sha256", required=True)
    execute_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    analyse_parser = commands.add_parser("analyse")
    analyse_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse_parser.add_argument("--expected-sha256", required=True)
    analyse_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "prepare":
        digest = prepare(args.seal)
        print(f"seal_sha256={digest}", flush=True)
    elif args.command == "execute":
        execute(args.seal, args.expected_sha256, args.out)
    else:
        analyse(args.seal, args.expected_sha256, args.out)


if __name__ == "__main__":
    main()
