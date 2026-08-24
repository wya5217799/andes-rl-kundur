"""R479 formal adapter for corrected-card zero-action H sensitivity.

Usage (physical commands are WSL-only through ``andes_scratch.py``)::

    python scripts/run_r479_h_sensitivity.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r479_h_sensitivity.py rehearse
    python scripts/run_r479_h_sensitivity.py seal
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r479_h_sensitivity.py execute
    python scripts/run_r479_h_sensitivity.py classify
    python scripts/run_r479_h_sensitivity.py verify

Formal artifacts are create-only and hash-sidecar protected.  The six
scientific cells are defined and analyzed in the evaluation module; this file
owns only authority checks, sealing, execution orchestration, and artifact I/O.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from memory.tools.artifact_io import (  # noqa: E402
    read_verified_json,
    sha256_file,
    write_new_json,
)

from andes_rl_kundur.evaluation.r479_h_sensitivity import (  # noqa: E402
    SHORT_STEPS,
    analyze_bank,
    build_contract,
    run_cell,
    run_cell_captured,
    summarize_cell,
)

ROUND_ID = "R479"
ROUND_DIR = ROOT / "memory" / "rounds" / ROUND_ID
PLAN = ROUND_DIR / "plan.md"
APPROVAL = ROUND_DIR / "OWNER_APPROVED.json"
CAPACITY = ROUND_DIR / "capacity_evidence.json"
CONTRACT = ROUND_DIR / "contract.json"
REHEARSAL = ROUND_DIR / "rehearsal.json"
SEAL = ROUND_DIR / "formal_seal.json"
OUT = ROOT / "results" / "research_loop" / "r479_h_sensitivity"
DEVELOPMENT_SCREEN = ROOT / "tmp" / "r479_h_sensitivity_screen.json"
R478_SEAL = ROOT / "memory" / "rounds" / "R478" / "formal_seal.json"
PARAMETER_CARD = (
    ROOT
    / "paper"
    / "yang_md_decoupling_marl"
    / "working"
    / "md_parameter_card_20260824.json"
)
WORKERS = 6

SOURCE_PATHS = {
    "runner": ROOT / "scripts" / "run_r479_h_sensitivity.py",
    "evaluation": ROOT
    / "src"
    / "andes_rl_kundur"
    / "evaluation"
    / "r479_h_sensitivity.py",
    "tests": ROOT / "tests" / "test_r479_h_sensitivity.py",
    "plan": PLAN,
    "approval": APPROVAL,
    "capacity": CAPACITY,
    "contract": CONTRACT,
}


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _sha256_normalized(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk.replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def _source_manifest() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _relative(path), "sha256": _sha256_normalized(path)}
        for name, path in SOURCE_PATHS.items()
    }


def _parent_manifest() -> dict[str, dict[str, str]]:
    return {
        "r478_seal": {
            "path": _relative(R478_SEAL),
            "sha256": sha256_file(R478_SEAL),
        },
        "parameter_card": {
            "path": _relative(PARAMETER_CARD),
            "sha256": sha256_file(PARAMETER_CARD),
        },
    }


def _verify_r478_parent() -> dict[str, Any]:
    payload = json.loads(R478_SEAL.read_text(encoding="utf-8"))
    mismatches = []
    for name, item in payload["sources"].items():
        path = ROOT / item["path"]
        actual = _sha256_normalized(path)
        if actual != item["sha256"]:
            mismatches.append(
                {"name": name, "path": item["path"], "actual": actual}
            )
    if mismatches:
        raise RuntimeError(f"R478 sealed parent drift: {mismatches}")
    card_digest = sha256_file(PARAMETER_CARD)
    expected_card = payload["sources"]["parameter_card"]["sha256"]
    if _sha256_normalized(PARAMETER_CARD) != expected_card:
        raise RuntimeError("R478 parameter-card drift")
    return {
        "r478_seal_sha256": sha256_file(R478_SEAL),
        "parameter_card_sha256": card_digest,
        "verified_source_count": len(payload["sources"]),
    }


def _installed_runtime() -> dict[str, Any]:
    import andes

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    return {
        "python": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "andes_module": str(Path(andes.__file__).resolve()),
        "case_path": str(case_path),
        "case_sha256": sha256_file(case_path),
    }


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R479 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R479 must run through scripts/andes_scratch.py")


def _approval_valid() -> bool:
    payload = json.loads(APPROVAL.read_text(encoding="utf-8"))
    return payload.get("approved") is True and payload.get("round") == ROUND_ID


def _contract_valid() -> bool:
    payload, _ = read_verified_json(CONTRACT)
    return payload == build_contract()


def _plan_state() -> str:
    for line in PLAN.read_text(encoding="utf-8").splitlines():
        if line.startswith("state:"):
            return line.split(":", 1)[1].strip()
    raise RuntimeError("R479 plan has no state")


def prepare() -> str:
    if CONTRACT.exists() or CONTRACT.with_suffix(".json.sha256").exists():
        raise FileExistsError(f"R479 contract already exists: {CONTRACT}")
    return write_new_json(CONTRACT, build_contract())


def _pre_attempt_checks() -> dict[str, Any]:
    runtime = _installed_runtime()
    parent = _verify_r478_parent()
    checks = {
        "source_hash": bool(_source_manifest()),
        "parent_hash": parent["verified_source_count"] > 0,
        "installed_package": runtime["andes_version"] != "unknown",
        "installed_case": Path(runtime["case_path"]).is_file(),
        "output_absence": not OUT.exists(),
        "active_plan": (
            _plan_state() == "active"
            and "manuscript_line: yang-md-decoupling-marl"
            in PLAN.read_text(encoding="utf-8")
        ),
        "owner_approved": _approval_valid(),
        "contract_closed": _contract_valid(),
    }
    if not all(checks.values()):
        raise RuntimeError(f"R479 pre-attempt check failed: {checks}")
    return {"checks": checks, "runtime": runtime, "parent": parent}


def rehearse() -> str:
    _assert_wsl_scratch()
    if REHEARSAL.exists() or SEAL.exists() or OUT.exists():
        raise FileExistsError("R479 rehearsal/seal/formal artifact already exists")
    pre_attempt = _pre_attempt_checks()
    cell = next(
        item
        for item in build_contract()["cells"]
        if item["h_device_s"] == 100.0 and item["scenario_id"] == "ls1"
    )
    started = time.perf_counter()
    record = run_cell(cell, steps=SHORT_STEPS)
    elapsed = time.perf_counter() - started
    summary = summarize_cell(record, expected_steps=SHORT_STEPS)
    if summary["valid"] is not True:
        raise RuntimeError(f"R479 rehearsal trace invalid: {summary}")
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "phase": "same-pre-attempt-path-rehearsal",
        **pre_attempt,
        "cell": cell,
        "summary": summary,
        "elapsed_seconds": elapsed,
        "record_json_bytes": len(
            json.dumps(record, ensure_ascii=False, allow_nan=False).encode("utf-8")
        ),
        "formal_attempt_created": False,
        "formal_outputs_created": False,
    }
    return write_new_json(REHEARSAL, payload)


def _seal_payload() -> dict[str, Any]:
    rehearsal, rehearsal_sha = read_verified_json(REHEARSAL)
    if rehearsal.get("summary", {}).get("valid") is not True:
        raise RuntimeError("R479 rehearsal is not valid")
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "sources": _source_manifest(),
        "parents": _parent_manifest(),
        "rehearsal_sha256": rehearsal_sha,
        "worker_budget": {
            "workers": WORKERS,
            "launcher": 1,
            "native_threads_per_process": 1,
        },
        "output_root": _relative(OUT),
        "authority": "owner-approved R479 zero-action H sensitivity only",
    }


def seal() -> str:
    if SEAL.exists():
        raise FileExistsError(f"R479 seal already exists: {SEAL}")
    if _plan_state() != "active":
        raise RuntimeError("R479 must be active before formal sealing")
    _verify_r478_parent()
    if not _approval_valid() or not _contract_valid():
        raise RuntimeError("R479 approval or contract invalid")
    return write_new_json(SEAL, _seal_payload())


def screen() -> str:
    """Run a non-claim-bearing six-worker diagnostic while R479 is queued."""

    _assert_wsl_scratch()
    if _plan_state() != "queued":
        raise RuntimeError("R479 development screen is only valid while queued")
    if DEVELOPMENT_SCREEN.exists():
        raise FileExistsError(f"R479 development screen exists: {DEVELOPMENT_SCREEN}")
    if not _approval_valid() or not _contract_valid():
        raise RuntimeError("R479 approval or contract invalid")
    parent = _verify_r478_parent()
    cells = build_contract()["cells"]
    started = time.perf_counter()
    records: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(run_cell_captured, cell) for cell in cells]
        for future in as_completed(futures):
            records.append(future.result())
    anchor_record = next(
        record for record in records if record.get("cell_id") == "h100_ls1"
    )
    analysis = analyze_bank(records, summarize_cell(anchor_record))
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "status": "development-only-non-claim-bearing",
        "formal_substitute": False,
        "workers": WORKERS,
        "unique_worker_pids": sorted(
            {int(record["worker_pid"]) for record in records if "worker_pid" in record}
        ),
        "elapsed_seconds": time.perf_counter() - started,
        "parent": parent,
        "analysis": analysis,
    }
    return write_new_json(DEVELOPMENT_SCREEN, payload)


def _verify_seal(*, require_runtime: bool = False) -> tuple[dict[str, Any], str]:
    payload, digest = read_verified_json(SEAL)
    for item in payload["sources"].values():
        if _sha256_normalized(ROOT / item["path"]) != item["sha256"]:
            raise RuntimeError(f"R479 sealed source drift: {item['path']}")
    for item in payload["parents"].values():
        if sha256_file(ROOT / item["path"]) != item["sha256"]:
            raise RuntimeError(f"R479 sealed parent drift: {item['path']}")
    if payload["worker_budget"] != {
        "workers": WORKERS,
        "launcher": 1,
        "native_threads_per_process": 1,
    }:
        raise RuntimeError("R479 sealed worker budget mismatch")
    rehearsal, rehearsal_sha = read_verified_json(REHEARSAL)
    if rehearsal_sha != payload["rehearsal_sha256"]:
        raise RuntimeError("R479 sealed rehearsal mismatch")
    if not _approval_valid() or not _contract_valid():
        raise RuntimeError("R479 sealed approval or contract invalid")
    if require_runtime:
        current_runtime = _installed_runtime()
        expected_runtime = rehearsal["runtime"]
        for key in ("andes_version", "case_sha256"):
            if current_runtime[key] != expected_runtime[key]:
                raise RuntimeError(f"R479 installed runtime drift: {key}")
    _verify_r478_parent()
    return payload, digest


def execute() -> int:
    _assert_wsl_scratch()
    _, seal_sha = _verify_seal(require_runtime=True)
    if OUT.exists():
        raise FileExistsError(f"R479 formal output already exists: {OUT}")
    cells = build_contract()["cells"]
    attempt_sha = write_new_json(
        OUT / "formal_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "started_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_sha,
            "cell_ids": [cell["cell_id"] for cell in cells],
            "workers": WORKERS,
            "scientific_outcomes_inspected": False,
        },
    )
    started = time.perf_counter()
    entries: list[dict[str, Any]] = []
    orchestration_error: str | None = None
    try:
        with ProcessPoolExecutor(max_workers=WORKERS) as executor:
            future_to_cell = {
                executor.submit(run_cell_captured, cell): cell for cell in cells
            }
            for future in as_completed(future_to_cell):
                cell = future_to_cell[future]
                record = future.result()
                path = OUT / "traces" / f"{cell['cell_id']}.json"
                digest = write_new_json(path, record)
                entries.append(
                    {
                        "cell_id": cell["cell_id"],
                        "path": _relative(path),
                        "sha256": digest,
                        "operational_valid": (
                            record.get("tds_failed") is False
                            and record.get("n_steps") == build_contract()["steps"]
                        ),
                    }
                )
    except Exception as error:
        orchestration_error = f"{type(error).__name__}: {str(error)[:500]}"

    expected_ids = {cell["cell_id"] for cell in cells}
    actual_ids = {entry["cell_id"] for entry in entries}
    terminal = (
        orchestration_error is None
        and actual_ids == expected_ids
        and all(entry["operational_valid"] for entry in entries)
    )
    write_new_json(
        OUT / "formal_execution.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "status": "complete" if terminal else "engineering-invalid",
            "attempt_sha256": attempt_sha,
            "elapsed_seconds": time.perf_counter() - started,
            "expected_cells": len(cells),
            "completed_cells": len(entries),
            "entries": sorted(entries, key=lambda item: item["cell_id"]),
            "orchestration_error": orchestration_error,
            "scientific_outcomes_inspected": False,
        },
    )
    return 0 if terminal else 1


def classify() -> str:
    _, seal_sha = _verify_seal()
    attempt, attempt_sha = read_verified_json(OUT / "formal_attempt.json")
    execution, execution_sha = read_verified_json(OUT / "formal_execution.json")
    rehearsal, rehearsal_sha = read_verified_json(REHEARSAL)
    if attempt["seal_sha256"] != seal_sha:
        raise RuntimeError("R479 attempt used a different seal")
    if execution["attempt_sha256"] != attempt_sha:
        raise RuntimeError("R479 execution used a different attempt")
    records = []
    for entry in execution["entries"]:
        record, digest = read_verified_json(
            ROOT / entry["path"], expected_sha256=entry["sha256"]
        )
        if digest != entry["sha256"]:
            raise RuntimeError(f"R479 trace hash mismatch: {entry['cell_id']}")
        records.append(record)
    analysis = analyze_bank(records, rehearsal["summary"])
    analysis.update(
        {
            "formal_execution_sha256": execution_sha,
            "formal_attempt_sha256": attempt_sha,
            "formal_seal_sha256": seal_sha,
            "rehearsal_sha256": rehearsal_sha,
            "formal_execution_status": execution["status"],
        }
    )
    return write_new_json(OUT / "analysis.json", analysis)


def verify() -> dict[str, Any]:
    _, seal_sha = _verify_seal()
    execution, execution_sha = read_verified_json(OUT / "formal_execution.json")
    analysis, analysis_sha = read_verified_json(OUT / "analysis.json")
    verified_traces = 0
    for entry in execution["entries"]:
        read_verified_json(ROOT / entry["path"], entry["sha256"])
        verified_traces += 1
    return {
        "round": ROUND_ID,
        "seal_sha256": seal_sha,
        "execution_sha256": execution_sha,
        "analysis_sha256": analysis_sha,
        "verified_traces": verified_traces,
        "classification": analysis["classification"],
        "valid": analysis["valid"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "prepare",
            "rehearse",
            "seal",
            "screen",
            "execute",
            "classify",
            "verify",
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    command = _parser().parse_args(argv).command
    if command == "prepare":
        print(f"R479 contract: {prepare()}")
        return 0
    if command == "rehearse":
        print(f"R479 rehearsal: {rehearse()}")
        return 0
    if command == "seal":
        print(f"R479 seal: {seal()}")
        return 0
    if command == "screen":
        print(f"R479 development screen: {screen()}")
        return 0
    if command == "execute":
        return execute()
    if command == "classify":
        print(f"R479 analysis: {classify()}")
        return 0
    print(json.dumps(verify(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
