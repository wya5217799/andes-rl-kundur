"""R480 resume adapter — re-execute the R479 six-cell zero-action H-sensitivity
bank after the operator interrupted R479's formal attempt at creation.

Motivation: R479 reached contract + rehearsal + seal, then its execute was
interrupted before any scientific cell ran. Frozen round rules forbid
in-place retries after sealing; this successor prospectively declares reuse
of the R479 seal and rehearsal (hash-bound), keeps the R479 orphaned attempt
byte-for-byte, and writes a fresh attempt into a distinct output root.

Usage::

    python scripts/run_r480_h_sensitivity_resume.py check      (Windows pre-flight)
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \\
        scripts/run_r480_h_sensitivity_resume.py execute        (WSL only)
    python scripts/run_r480_h_sensitivity_resume.py classify
    python scripts/run_r480_h_sensitivity_resume.py verify

Failure modes: any parent drift, orphan tampering, or existing output root
stops the run; every artifact is create-only with a .sha256 sidecar.
"""

from __future__ import annotations

import argparse
import importlib.util
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

_SPEC = importlib.util.spec_from_file_location(
    "r479_runner", ROOT / "scripts" / "run_r479_h_sensitivity.py"
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("R479 parent runner not loadable")
r479 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(r479)

ROUND_ID = "R480"
OUT = ROOT / "results" / "research_loop" / "r480_h_sensitivity"
R479_SEAL = ROOT / "memory" / "rounds" / "R479" / "formal_seal.json"
R479_REHEARSAL = ROOT / "memory" / "rounds" / "R479" / "rehearsal.json"
R479_ORPHAN_ATTEMPT = (
    ROOT / "results" / "research_loop" / "r479_h_sensitivity" / "formal_attempt.json"
)
WORKERS = 6


def _verify_parents() -> dict[str, str]:
    seal, seal_sha = r479.read_verified_json(R479_SEAL)
    rehearsal, rehearsal_sha = r479.read_verified_json(R479_REHEARSAL)
    if rehearsal.get("summary", {}).get("valid") is not True:
        raise RuntimeError("R479 rehearsal is not valid")
    if seal.get("rehearsal_sha256") != rehearsal_sha:
        raise RuntimeError("R479 seal/rehearsal mismatch")
    orphan, orphan_sha = r479.read_verified_json(R479_ORPHAN_ATTEMPT)
    parent = r479._verify_r478_parent()
    return {
        "r479_seal_sha256": seal_sha,
        "r479_rehearsal_sha256": rehearsal_sha,
        "r479_orphan_attempt_sha256": orphan_sha,
        "r479_orphan_cell_ids": json.dumps(orphan.get("cell_ids", []), sort_keys=True),
        "r478_parent_ok": parent["r478_seal_sha256"][:16],
    }


def check() -> int:
    print(json.dumps(_verify_parents(), indent=2, sort_keys=True))
    return 0


def execute() -> int:
    r479._assert_wsl_scratch()
    parents = _verify_parents()
    if OUT.exists():
        raise FileExistsError(f"R480 formal output already exists: {OUT}")
    cells = r479.build_contract()["cells"]
    attempt_sha = r479.write_new_json(
        OUT / "formal_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "started_utc": datetime.now(UTC).isoformat(),
            "reuse": {
                "declared_parent_round": "R479",
                "r479_seal_sha256": parents["r479_seal_sha256"],
                "r479_rehearsal_sha256": parents["r479_rehearsal_sha256"],
                "r479_orphan_attempt_sha256": parents["r479_orphan_attempt_sha256"],
            },
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
                executor.submit(r479.run_cell_captured, cell): cell for cell in cells
            }
            for future in as_completed(future_to_cell):
                cell = future_to_cell[future]
                record = future.result()
                path = OUT / "traces" / f"{cell['cell_id']}.json"
                digest = r479.write_new_json(path, record)
                entries.append(
                    {
                        "cell_id": cell["cell_id"],
                        "path": path.relative_to(ROOT).as_posix(),
                        "sha256": digest,
                        "operational_valid": (
                            record.get("tds_failed") is False
                            and record.get("n_steps")
                            == r479.build_contract()["steps"]
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
    r479.write_new_json(
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
    _verify_parents()
    attempt, attempt_sha = r479.read_verified_json(OUT / "formal_attempt.json")
    execution, execution_sha = r479.read_verified_json(OUT / "formal_execution.json")
    if execution["attempt_sha256"] != attempt_sha:
        raise RuntimeError("R480 execution used a different attempt")
    records = []
    for entry in execution["entries"]:
        record, _digest = r479.read_verified_json(
            ROOT / entry["path"], expected_sha256=entry["sha256"]
        )
        records.append(record)
    rehearsal, _rehearsal_sha = r479.read_verified_json(R479_REHEARSAL)
    analysis = r479.analyze_bank(records, rehearsal["summary"])
    analysis.update(
        {
            "round": ROUND_ID,
            "formal_execution_sha256": execution_sha,
            "formal_attempt_sha256": attempt_sha,
            "r479_reuse": attempt["reuse"],
            "formal_execution_status": execution["status"],
        }
    )
    return r479.write_new_json(OUT / "analysis.json", analysis)


def verify() -> dict[str, Any]:
    _verify_parents()
    execution, execution_sha = r479.read_verified_json(OUT / "formal_execution.json")
    analysis, analysis_sha = r479.read_verified_json(OUT / "analysis.json")
    verified_traces = 0
    for entry in execution["entries"]:
        r479.read_verified_json(ROOT / entry["path"], entry["sha256"])
        verified_traces += 1
    return {
        "round": ROUND_ID,
        "execution_sha256": execution_sha,
        "analysis_sha256": analysis_sha,
        "verified_traces": verified_traces,
        "classification": analysis["classification"],
        "valid": analysis["valid"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "execute", "classify", "verify"))
    return parser


def main(argv: list[str] | None = None) -> int:
    command = _parser().parse_args(argv).command
    if command == "check":
        return check()
    if command == "execute":
        return execute()
    if command == "classify":
        print(f"R480 analysis: {classify()}")
        return 0
    print(json.dumps(verify(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
