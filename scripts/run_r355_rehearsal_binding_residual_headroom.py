"""Rehearse, seal, and execute the create-only R355 invocation recovery.

Usage::

    python scripts/run_r355_rehearsal_binding_residual_headroom.py rehearsal
    python scripts/run_r355_rehearsal_binding_residual_headroom.py prepare
    python scripts/run_r355_rehearsal_binding_residual_headroom.py analyse \
        --expected-seal-sha256 <sha256>

The adapter delegates the full scientific path to R354 and changes only the
rehearsal path supplied when the inherited formal entry loads its seal.  No
command runs ANDES, training, distributed execution, or EVAL.  Formal outputs
are canonical and create-only; retry is not authorized.

Frozen predecessor or source drift, a failed rehearsal-binding smoke check,
an existing create-only artifact, or any delegated inventory, seal, numerical,
or serialization failure stops the command.  A stopped formal attempt is not
retried in another output directory.
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
from tempfile import TemporaryDirectory
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

from scripts import run_r354_certificate_compatible_residual_headroom as predecessor  # noqa: E402

parent = predecessor.parent
ROUND_ID = "R355"
QUESTION_ID = "Q-0094"
DEFAULT_SEAL = ROOT / "memory/rounds/R355/analysis_seal.json"
DEFAULT_REHEARSAL = ROOT / "memory/rounds/R355/rehearsal.json"
DEFAULT_OUT = ROOT / "results/r355_rehearsal_binding_residual_headroom"
PLAN = ROOT / "memory/rounds/R355/plan.md"
R354_PLAN = ROOT / "memory/rounds/R354/plan.md"
R354_REHEARSAL = ROOT / "memory/rounds/R354/rehearsal.json"
R354_SEAL = ROOT / "memory/rounds/R354/analysis_seal.json"
R354_OUT = ROOT / "results/r354_certificate_compatible_residual_headroom"

_PARENT_LOAD_SEAL = parent.load_seal
_PREDECESSOR_BUILD_CONTRACT = predecessor.build_contract
_PREDECESSOR_PARENT_PATHS = predecessor.parent_paths
_FROZEN_R354 = {
    R354_PLAN: "ed79efbd68df702baf5e7855c45c4b956dc76883bb6a8f05d784ed5c5c7c1b49",
    R354_REHEARSAL: "9b9fe79d1909ac0cf54c7a33c22cef26af774530433542bdd135906089d635e8",
    R354_SEAL: "8526f9bbbf3ff4066236b085c61a6f3d067393e3de89354cbe1e66b5ffefa563",
    ROOT / "scripts/run_r354_certificate_compatible_residual_headroom.py": (
        "357ed93d5a82f3627fb73d5c080a4207c68480db64c711f09f0823bc69728f44"
    ),
    ROOT / "probes/r354_certificate_compatible_residual_headroom.py": (
        "3799d2e7c6e22a0922176d280d8a633dcf60d087cc8aec91283fb24092ac46c0"
    ),
    ROOT / "tests/test_r354_certificate_compatible_residual_headroom.py": (
        "a53733b79b3915a52cbff2894d555dbcb606981af1e98c2bb7d4c973813206cd"
    ),
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_contract() -> dict[str, Any]:
    """Return the unchanged R354 contract plus the bounded invocation repair."""

    inherited = _PREDECESSOR_BUILD_CONTRACT()
    contract = deepcopy(inherited)
    contract["round"] = ROUND_ID
    contract["stage"] = "create-only-rehearsal-binding-residual-headroom-recovery"
    contract["recovery"] = {
        "parent_round": "R354",
        "parent_seal_sha256": _FROZEN_R354[R354_SEAL],
        "parent_rehearsal_sha256": _FROZEN_R354[R354_REHEARSAL],
        "authorized_change": "load-seal-rehearsal-path-binding-only",
        "certificate_fields": inherited["recovery"]["certificate_fields"],
        "inherited_certificate_recovery": inherited["recovery"],
        "r354_attempt_created": False,
        "r354_result_root_created": False,
    }
    return contract


def source_paths(*, include_rehearsal: bool) -> dict[str, Path]:
    """Return the R355 sources and byte-frozen predecessor/package closure."""

    paths = {
        "plan": PLAN,
        "adapter": Path(__file__).resolve(),
        "invocation_tests": ROOT / "tests/test_r355_rehearsal_binding_residual_headroom.py",
        "r354_closed_plan": R354_PLAN,
        "r354_adapter": ROOT / "scripts/run_r354_certificate_compatible_residual_headroom.py",
        "r354_probe": ROOT / "probes/r354_certificate_compatible_residual_headroom.py",
        "r354_tests": ROOT / "tests/test_r354_certificate_compatible_residual_headroom.py",
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
    """Return the R354 pre-attempt chain and all inherited evidence parents."""

    return {
        "r354_rehearsal": R354_REHEARSAL,
        "r354_seal": R354_SEAL,
        **_PREDECESSOR_PARENT_PATHS(),
    }


def _verify_predecessor_inputs() -> None:
    for path, expected in _FROZEN_R354.items():
        if not path.is_file() or _sha256_file(path) != expected:
            raise RuntimeError(f"R355 frozen R354 input drift: {path}")
    sealed = json.loads(R354_SEAL.read_text(encoding="utf-8"))
    closed_plan = R354_PLAN.read_text(encoding="utf-8")
    default_rehearsal = parent.load_seal.__kwdefaults__["rehearsal_path"]
    if (
        sealed.get("round") != "R354"
        or sealed.get("question") != QUESTION_ID
        or sealed.get("retry_authorized") is not False
        or sealed.get("sources", {}).get("rehearsal", {}).get("sha256")
        != _FROZEN_R354[R354_REHEARSAL]
        or "state: aborted" not in closed_plan
        or "sealed pre-attempt invocation invalid" not in closed_plan
        or default_rehearsal != predecessor.parent.DEFAULT_REHEARSAL
        or R354_OUT.exists()
    ):
        raise RuntimeError("R355 parent pre-attempt failure identity drift")
    for name, path in (
        ("adapter", ROOT / "scripts/run_r354_certificate_compatible_residual_headroom.py"),
        ("probe", ROOT / "probes/r354_certificate_compatible_residual_headroom.py"),
        ("recovery_tests", ROOT / "tests/test_r354_certificate_compatible_residual_headroom.py"),
    ):
        if sealed["sources"][name]["sha256"] != _sha256_file(path):
            raise RuntimeError(f"R355 sealed R354 source identity drift: {name}")


@contextmanager
def _predecessor_runtime(
    *,
    seal_path: Path = DEFAULT_SEAL,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
    out_dir: Path = DEFAULT_OUT,
) -> Iterator[None]:
    """Bind R354 to R355 and repair only the inherited seal-loader default."""

    replacements = {
        "ROUND_ID": ROUND_ID,
        "DEFAULT_SEAL": seal_path,
        "DEFAULT_REHEARSAL": rehearsal_path,
        "DEFAULT_OUT": out_dir,
        "PLAN": PLAN,
        "build_contract": build_contract,
        "source_paths": source_paths,
        "parent_paths": parent_paths,
    }
    previous = {name: getattr(predecessor, name) for name in replacements}
    previous_load_seal = parent.load_seal

    def load_seal_with_current_rehearsal(
        path: Path,
        expected_sha256: str,
        *,
        rehearsal_path: Path = rehearsal_path,
        out_dir: Path = out_dir,
    ) -> tuple[dict[str, Any], str]:
        return _PARENT_LOAD_SEAL(
            path,
            expected_sha256,
            rehearsal_path=rehearsal_path,
            out_dir=out_dir,
        )

    for name, value in replacements.items():
        setattr(predecessor, name, value)
    parent.load_seal = load_seal_with_current_rehearsal
    try:
        yield
    finally:
        parent.load_seal = previous_load_seal
        for name, value in previous.items():
            setattr(predecessor, name, value)


def rehearsal(
    record_path: Path = DEFAULT_REHEARSAL,
    *,
    out_dir: Path = DEFAULT_OUT,
) -> str:
    """Exercise the exact corrected pre-attempt path without a result."""

    _verify_predecessor_inputs()
    with _predecessor_runtime(rehearsal_path=record_path, out_dir=out_dir):
        rehearsal_digest = predecessor.rehearsal(record_path, out_dir=out_dir)
        with TemporaryDirectory(prefix="r355-rehearsal-smoke-") as directory:
            smoke_seal = Path(directory) / "analysis_seal.json"
            seal_digest = predecessor.prepare(
                smoke_seal,
                rehearsal_path=record_path,
                out_dir=out_dir,
            )
            with predecessor._parent_runtime():
                parent.load_seal(
                    smoke_seal,
                    seal_digest,
                    out_dir=out_dir,
                )
        return rehearsal_digest


def prepare(
    seal_path: Path = DEFAULT_SEAL,
    *,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
    out_dir: Path = DEFAULT_OUT,
) -> str:
    """Create the source- and parent-bound R355 seal after rehearsal."""

    _verify_predecessor_inputs()
    with _predecessor_runtime(
        seal_path=seal_path,
        rehearsal_path=rehearsal_path,
        out_dir=out_dir,
    ):
        return predecessor.prepare(
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
    """Verify the R355 seal through the corrected inherited call seam."""

    _verify_predecessor_inputs()
    with _predecessor_runtime(
        seal_path=path,
        rehearsal_path=rehearsal_path,
        out_dir=out_dir,
    ):
        return predecessor.load_seal(
            path,
            expected_sha256,
            rehearsal_path=rehearsal_path,
            out_dir=out_dir,
        )


def analyse(expected_sha256: str) -> str:
    """Execute the one sealed analysis with only rehearsal binding repaired."""

    _verify_predecessor_inputs()
    with _predecessor_runtime():
        return predecessor.analyse(expected_sha256)


def build_parser() -> argparse.ArgumentParser:
    """Return the three create-only R355 commands."""

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
    raise RuntimeError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
