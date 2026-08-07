"""Rehearse, seal, and execute the create-only R354 residual recovery.

Usage::

    python scripts/run_r354_certificate_compatible_residual_headroom.py rehearsal
    python scripts/run_r354_certificate_compatible_residual_headroom.py prepare
    python scripts/run_r354_certificate_compatible_residual_headroom.py analyse \
        --expected-seal-sha256 <sha256>

The adapter binds the terminal R353 failure and delegates its unchanged
scientific contract to the frozen R353 runner while installing only the R354
certificate serializer.  Source drift, parent drift, unsupported certificate
fields, existing create-only outputs, or any delegated failure stop the run.
No command runs ANDES, training, distributed execution, or EVAL; retry is not
authorized.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from probes import r354_certificate_compatible_residual_headroom as recovery  # noqa: E402
from scripts import run_r353_matched_residual_headroom as parent  # noqa: E402

ROUND_ID = "R354"
QUESTION_ID = "Q-0094"
DEFAULT_SEAL = ROOT / "memory/rounds/R354/analysis_seal.json"
DEFAULT_REHEARSAL = ROOT / "memory/rounds/R354/rehearsal.json"
DEFAULT_OUT = ROOT / "results/r354_certificate_compatible_residual_headroom"
PLAN = ROOT / "memory/rounds/R354/plan.md"
R353_SEAL = ROOT / "memory/rounds/R353/analysis_seal.json"
R353_ATTEMPT = ROOT / "results/r353_matched_residual_headroom/analysis_attempt.json"
R353_FAILURE = ROOT / "results/r353_matched_residual_headroom/failure.json"

_PARENT_BUILD_CONTRACT = parent.build_contract
_PARENT_PARENT_PATHS = parent.parent_paths
_FROZEN_R353 = {
    R353_SEAL: "b58d3521d6cffff781da72e3bf6baa175426b2f94d8c130fd982c5b0478decc0",
    R353_ATTEMPT: "6c3f22c184e682e97f7497b372440edd4a782bfb1e72bcddf2750674dafe8d86",
    R353_FAILURE: "09e2c55e7c6d7db532135c18333ef7a9ebae349fa6a933384e1a312e2b79b33d",
    ROOT / "scripts/run_r353_matched_residual_headroom.py": (
        "63b7880684ee892f35cc30f2476ba0d8f6021214bbd3f1553303f82d32f98c4e"
    ),
    ROOT / "probes/r353_matched_residual_headroom.py": (
        "37fa859d588b392fbb1fa63d5242aeccf998a2d33aa0a29020dac79793b8482b"
    ),
    ROOT / "tests/test_r353_matched_residual_headroom.py": (
        "708b7dda80e7457c70b02c118902d3fde2d585e18b43d35b339e722d2b08b1e3"
    ),
    ROOT / "tests/test_r353_matched_residual_analysis.py": (
        "6701a3e7a6dc8d1d0a29f64b2d5ca86dfa9d81413895f16105206c8d66324632"
    ),
    ROOT / "src/andes_rl_kundur/control/minimum_norm_certificate.py": (
        "9dc24a0189c1d29368b7bd4da0a8c21a02a108ea214c5bf8ca303e6664ad69f8"
    ),
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source(path: Path) -> dict[str, str]:
    return {
        "path": path.resolve().relative_to(ROOT.resolve()).as_posix(),
        "sha256": _sha256_file(path),
    }


def build_contract() -> dict[str, Any]:
    """Return the R353-identical contract plus the bounded R354 repair identity."""

    contract = deepcopy(_PARENT_BUILD_CONTRACT())
    contract["round"] = ROUND_ID
    contract["stage"] = "create-only-certificate-compatible-residual-headroom-recovery"
    contract["recovery"] = {
        "parent_round": "R353",
        "parent_seal_sha256": _FROZEN_R353[R353_SEAL],
        "parent_attempt_sha256": _FROZEN_R353[R353_ATTEMPT],
        "parent_failure_sha256": _FROZEN_R353[R353_FAILURE],
        "authorized_change": "minimum-norm-certificate-serialization-only",
        "certificate_fields": [
            "valid",
            "feasible",
            "reason",
            "active_constraint_count",
            "maximum_constraint_violation",
            "stationarity_residual",
            "complementarity_residual",
            "optimality_tolerance",
            "multipliers",
        ],
    }
    contract["resource_budget"] = {
        "host_process_budget": 1,
        "analysis_processes": 1,
        "wsl_python_processes": 0,
        "native_threads_per_process": 1,
        "other_reserved_processes_at_plan": 0,
        "retry_authorized": False,
    }
    return contract


def source_paths(*, include_rehearsal: bool) -> dict[str, Path]:
    """Return the R354 files and byte-unchanged R353/package source closure."""

    paths = {
        "plan": PLAN,
        "adapter": Path(__file__).resolve(),
        "probe": ROOT / "probes/r354_certificate_compatible_residual_headroom.py",
        "recovery_tests": (
            ROOT / "tests/test_r354_certificate_compatible_residual_headroom.py"
        ),
        "r353_adapter": ROOT / "scripts/run_r353_matched_residual_headroom.py",
        "r353_probe": ROOT / "probes/r353_matched_residual_headroom.py",
        "r353_probe_tests": ROOT / "tests/test_r353_matched_residual_headroom.py",
        "r353_adapter_tests": ROOT / "tests/test_r353_matched_residual_analysis.py",
    }
    package_root = ROOT / "src/andes_rl_kundur"
    for path in sorted(package_root.rglob("*.py")):
        relative = path.relative_to(package_root).as_posix()
        paths[f"package_{relative}"] = path
    if include_rehearsal:
        paths["rehearsal"] = DEFAULT_REHEARSAL
    return paths


def parent_paths() -> dict[str, Path]:
    """Return the R353 terminal chain plus its unchanged R341/R352 parents."""

    return {
        "r353_seal": R353_SEAL,
        "r353_attempt": R353_ATTEMPT,
        "r353_failure": R353_FAILURE,
        **_PARENT_PARENT_PATHS(),
    }


def _verify_recovery_inputs() -> None:
    for path, expected in _FROZEN_R353.items():
        if not path.is_file() or _sha256_file(path) != expected:
            raise RuntimeError(f"R354 frozen R353 input drift: {path}")
    failure = json.loads(R353_FAILURE.read_text(encoding="utf-8"))
    if (
        failure.get("round") != "R353"
        or failure.get("question") != QUESTION_ID
        or failure.get("classification") != "ANALYSIS-INVALID"
        or failure.get("error_type") != "AttributeError"
        or failure.get("retry_authorized") is not False
        or failure.get("training_authorized") is not False
    ):
        raise RuntimeError("R354 parent failure identity drift")
    fields = tuple(build_contract()["recovery"]["certificate_fields"])
    from dataclasses import fields as dataclass_fields

    import numpy as np

    from andes_rl_kundur.control.minimum_norm_certificate import (
        MinimumNormCertificate,
    )

    if tuple(field.name for field in dataclass_fields(MinimumNormCertificate)) != fields:
        raise RuntimeError("R354 certificate schema drift")
    smoke_certificate = MinimumNormCertificate(
        valid=True,
        feasible=True,
        reason="serializer-smoke-check",
        active_constraint_count=1,
        maximum_constraint_violation=0.0,
        stationarity_residual=0.0,
        complementarity_residual=0.0,
        optimality_tolerance=1.0e-4,
        multipliers=np.asarray([1.0]),
    )
    smoke_payload = recovery.certificate_payload(smoke_certificate)
    if tuple(smoke_payload) != fields or smoke_payload["multipliers"] != [1.0]:
        raise RuntimeError("R354 certificate serializer smoke check failed")


@contextmanager
def _parent_runtime() -> Iterator[None]:
    """Bind the frozen parent runner to R354 identity for one serial operation."""

    replacements = {
        "ROUND_ID": ROUND_ID,
        "DEFAULT_SEAL": DEFAULT_SEAL,
        "DEFAULT_REHEARSAL": DEFAULT_REHEARSAL,
        "DEFAULT_OUT": DEFAULT_OUT,
        "PLAN": PLAN,
        "build_contract": build_contract,
        "source_paths": source_paths,
        "parent_paths": parent_paths,
    }
    previous = {name: getattr(parent, name) for name in replacements}
    for name, value in replacements.items():
        setattr(parent, name, value)
    try:
        with recovery.certificate_serialization_scope():
            yield
    finally:
        for name, value in previous.items():
            setattr(parent, name, value)


def load_parent_inventory(bank: str) -> list[dict[str, Any]]:
    """Load the unchanged R353 parent inventory under the R354 binding."""

    _verify_recovery_inputs()
    with _parent_runtime():
        return parent.load_parent_inventory(bank)


def rehearsal(
    record_path: Path = DEFAULT_REHEARSAL,
    *,
    out_dir: Path = DEFAULT_OUT,
) -> str:
    """Exercise the exact R354 pre-attempt path without creating a result."""

    _verify_recovery_inputs()
    with _parent_runtime():
        return parent.rehearsal(record_path, out_dir=out_dir)


def prepare(
    seal_path: Path = DEFAULT_SEAL,
    *,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
    out_dir: Path = DEFAULT_OUT,
) -> str:
    """Create the source- and parent-bound R354 seal after rehearsal."""

    _verify_recovery_inputs()
    with _parent_runtime():
        return parent.prepare(
            seal_path,
            rehearsal_path=rehearsal_path,
            out_dir=out_dir,
        )


def load_seal(
    path: Path,
    expected_sha256: str,
    *,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
    out_dir: Path = DEFAULT_OUT,
) -> tuple[dict[str, Any], str]:
    """Verify the exact R354 seal and complete recovery closure."""

    _verify_recovery_inputs()
    with _parent_runtime():
        return parent.load_seal(
            path,
            expected_sha256,
            rehearsal_path=rehearsal_path,
            out_dir=out_dir,
        )


def analyse(expected_sha256: str) -> str:
    """Execute the one sealed R354 analysis with only serialization repaired."""

    _verify_recovery_inputs()
    with _parent_runtime():
        return parent.analyse(expected_sha256, out_dir=DEFAULT_OUT)


def build_parser() -> argparse.ArgumentParser:
    """Return the three create-only R354 commands."""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    rehearsal_parser = subparsers.add_parser("rehearsal")
    rehearsal_parser.add_argument("--record", type=Path, default=DEFAULT_REHEARSAL)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--expected-seal-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rehearsal":
        print(rehearsal(args.record), flush=True)
        return 0
    if args.command == "prepare":
        print(prepare(args.seal), flush=True)
        return 0
    if args.command == "analyse":
        analyse(args.expected_seal_sha256)
        return 0
    raise AssertionError(f"unexpected command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
