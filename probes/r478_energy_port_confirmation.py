"""Run one scratch-only Yang energy-port confirmation block in parallel."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_r415_energy_port_extra_banks as R415  # noqa: E402

BLOCK_ID = "a4_conditions_b"
WORKERS = 16


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("physical confirmation is WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("physical confirmation requires andes_scratch.py")


def _identity_snapshot() -> dict[str, Any]:
    sources = R415._source_manifest()
    sources.update(
        {
            "r478_confirmation_probe": {
                "path": Path(__file__).resolve().relative_to(ROOT).as_posix(),
                "sha256": _sha256(Path(__file__).resolve()),
            },
            "r478_parameter_card": {
                "path": (
                    "paper/yang_md_decoupling_marl/working/"
                    "md_parameter_card_20260824.json"
                ),
                "sha256": _sha256(
                    ROOT
                    / "paper/yang_md_decoupling_marl/working/"
                    "md_parameter_card_20260824.json"
                ),
            },
        }
    )
    return {
        "scientific_sources": sources,
        "installed_runtime": R415._installed_runtime(),
    }


def registered_jobs() -> list[dict[str, Any]]:
    """Return the frozen 30-job alternate-condition block."""
    block = R415.block_by_id(BLOCK_ID)
    contract = R415.build_block_contract(block)
    jobs = R415.phase_jobs("development", contract=contract)
    if len(jobs) != 30:
        raise RuntimeError(f"expected 30 registered jobs, got {len(jobs)}")
    return [dict(job) for job in jobs]


def _run_index(index: int) -> dict[str, Any]:
    os.environ.update(
        {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )
    block = R415.block_by_id(BLOCK_ID)
    contract = R415.build_block_contract(block)
    job = R415.phase_jobs("development", contract=contract)[index]
    record = R415._run_job(job, contract=contract, block=block)
    record["registered_order"] = index
    return record


def run_confirmation(*, workers: int = WORKERS) -> dict[str, Any]:
    """Execute and classify the frozen alternate-condition block."""
    _assert_wsl_scratch()
    if workers != WORKERS:
        raise ValueError(f"confirmation requires the measured {WORKERS} workers")
    pre_attempt = _identity_snapshot()
    jobs = registered_jobs()
    with ProcessPoolExecutor(max_workers=workers) as executor:
        records = list(executor.map(_run_index, range(len(jobs))))
    block = R415.block_by_id(BLOCK_ID)
    contract = R415.build_block_contract(block)
    identity_ok = all(
        record.get("identity") == R415._expected_identity(contract)
        for record in records
    )
    completed = all(
        len(record.get("steps", [])) == int(contract["steps"])
        and record.get("tds_failed") is False
        for record in records
    )
    summary = (
        R415._block_summary(records, contract)
        if identity_ok and completed
        else None
    )
    post_attempt = _identity_snapshot()
    if pre_attempt != post_attempt:
        raise RuntimeError("source/runtime identity drifted during confirmation")
    return {
        "schema_version": 1,
        "created_utc": datetime.now(UTC).isoformat(),
        "round": "R478",
        "manuscript_line": "yang-md-decoupling-marl",
        "scope": "scratch_route_confirmation_not_formal_evidence",
        "block_id": BLOCK_ID,
        "workers": workers,
        "record_count": len(records),
        "identity_ok": identity_ok,
        "completed": completed,
        "summary": summary,
        "records": records,
        "training_authorized": False,
        "formal_evidence": False,
        "pre_attempt": pre_attempt,
        "post_attempt": post_attempt,
        "identity_stable": True,
        "sources": {
            "confirmation_probe": _sha256(Path(__file__).resolve()),
            "r415_runner": _sha256(
                ROOT / "scripts/run_r415_energy_port_extra_banks.py"
            ),
            "base_env": _sha256(
                ROOT / "src/andes_rl_kundur/env/andes/base_env.py"
            ),
            "parameter_card": _sha256(
                ROOT
                / "paper/yang_md_decoupling_marl/working/"
                "md_parameter_card_20260824.json"
            ),
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.out.exists() or Path(f"{args.out}.sha256").exists():
        raise FileExistsError(f"refusing to overwrite: {args.out}")
    payload = run_confirmation()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    digest = _sha256(args.out)
    Path(f"{args.out}.sha256").write_text(
        f"{digest}  {args.out.name}\n", encoding="ascii"
    )
    print(
        json.dumps(
            {
                "output": str(args.out),
                "sha256": digest,
                "completed": payload["completed"],
                "identity_ok": payload["identity_ok"],
                "summary": payload["summary"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
