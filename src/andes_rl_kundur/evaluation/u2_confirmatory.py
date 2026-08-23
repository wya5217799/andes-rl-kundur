"""Fail-closed integrity interface for U2 confirmatory execution.

The round adapter supplies paths and the frozen scientific contract. This
module owns the three behaviours that must stay local and independently
testable: complete seal verification, executable terminal semantics, and
classification precedence.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_hashed_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"missing hashed JSON: {path}")
    sidecar = Path(f"{path}.sha256")
    if not sidecar.is_file():
        raise RuntimeError(f"missing hash sidecar: {sidecar}")
    tokens = sidecar.read_text(encoding="ascii").split()
    if not tokens or tokens[0] != _sha256(path):
        raise RuntimeError(f"hash sidecar drift: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"invalid JSON: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def _repo_relative(path: Path, repo_root: Path) -> str:
    resolved = path.resolve()
    root = repo_root.resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as error:
        raise RuntimeError(f"path escapes repository: {path}") from error


def _resolve_sealed_path(raw_path: object, repo_root: Path) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise RuntimeError(f"invalid sealed path: {raw_path!r}")
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError(f"sealed path escapes repository: {raw_path}")
    path = (repo_root / relative).resolve()
    _repo_relative(path, repo_root)
    return path


def validate_review_coverage(
    review_paths: Sequence[Path],
    *,
    repo_root: Path,
    reviewed_files: Sequence[Path],
) -> dict[str, str]:
    """Require two passing reviews over one identical current hash map."""

    if len(review_paths) != 2:
        raise RuntimeError("exactly two independent review artifacts are required")
    expected = {
        _repo_relative(path, repo_root): _sha256(path)
        for path in reviewed_files
    }
    observed: list[dict[str, str]] = []
    for path in review_paths:
        review = _read_hashed_json(path)
        if review.get("decision") != "PASS":
            raise RuntimeError(f"review decision is not PASS: {path}")
        if int(review.get("open_p0_count", -1)) != 0:
            raise RuntimeError(f"review has open P0 findings: {path}")
        if int(review.get("open_p1_count", -1)) != 0:
            raise RuntimeError(f"review has open P1 findings: {path}")
        files = review.get("reviewed_files")
        if not isinstance(files, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in files.items()
        ):
            raise RuntimeError(f"invalid reviewed_files map: {path}")
        observed.append(dict(files))
    if observed[0] != observed[1]:
        raise RuntimeError("reviewed_files maps are not identical")
    if observed[0] != expected:
        raise RuntimeError("reviewed_files map does not match current source hashes")
    return expected


def verify_formal_seal(
    *,
    repo_root: Path,
    seal_path: Path,
    round_id: str,
    contract_sha256: str,
    bound_files: Mapping[str, Path],
    review_paths: Sequence[Path],
    reviewed_files: Sequence[Path],
    expected_shards: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    """Verify every R476 authority input through one fail-closed interface."""

    seal = _read_hashed_json(seal_path)
    if seal.get("round") != round_id:
        raise RuntimeError("formal seal round mismatch")
    if seal.get("contract_sha256") != contract_sha256:
        raise RuntimeError("formal seal contract mismatch")
    if seal.get("formal_authority") is not True:
        raise RuntimeError("formal seal lacks authority")

    for field, path in bound_files.items():
        if seal.get(field) != _sha256(path):
            raise RuntimeError(f"sealed bound-file drift: {field}: {path}")

    sources = seal.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise RuntimeError("formal seal has no sources")
    for name, row in sources.items():
        if not isinstance(row, dict):
            raise RuntimeError(f"invalid sealed source entry: {name}")
        path = _resolve_sealed_path(row.get("path"), repo_root)
        if not path.is_file() or row.get("sha256") != _sha256(path):
            raise RuntimeError(f"sealed source drift: {path}")

    shard_rows = seal.get("shard_lists")
    if not isinstance(shard_rows, dict):
        raise RuntimeError("formal seal has no shard_lists")
    if set(shard_rows) != set(expected_shards):
        raise RuntimeError("sealed shard list names drift")
    for name, expected in expected_shards.items():
        row = shard_rows.get(name)
        if not isinstance(row, dict):
            raise RuntimeError(f"invalid sealed shard list: {name}")
        path = _resolve_sealed_path(row.get("path"), repo_root)
        if not path.is_file() or row.get("sha256") != _sha256(path):
            raise RuntimeError(f"sealed shard list hash drift: {name}: {path}")
        try:
            actual = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise RuntimeError(f"invalid shard list JSON: {path}") from error
        if actual != list(expected):
            raise RuntimeError(f"shard list content drift: {name}")

    reviewed_map = validate_review_coverage(
        review_paths,
        repo_root=repo_root,
        reviewed_files=reviewed_files,
    )
    if seal.get("reviewed_files") != reviewed_map:
        raise RuntimeError("sealed reviewed_files map drift")
    return seal


def terminal_invalid(
    *,
    done: bool,
    tds_failed: bool,
    time_index: int,
    steps: int,
) -> bool:
    """Reject solver failure or a terminal before the registered final step."""

    return bool(tds_failed) or (bool(done) and int(time_index) < int(steps) - 1)


def terminal_truth_table(
    predicate: Callable[..., bool],
) -> dict[str, bool]:
    """Execute the four registered terminal cases against ``predicate``."""

    return {
        "normal_nonterminal_accepted": not predicate(
            done=False, tds_failed=False, time_index=5, steps=30
        ),
        "normal_horizon_done_accepted": not predicate(
            done=True, tds_failed=False, time_index=29, steps=30
        ),
        "premature_done_rejected": predicate(
            done=True, tds_failed=False, time_index=28, steps=30
        ),
        "tds_failure_rejected": predicate(
            done=False, tds_failed=True, time_index=5, steps=30
        ),
    }


def classify_confirmatory(
    *,
    design_valid: bool,
    missing_shards: Sequence[str],
    integrity_errors: Sequence[str],
    dynamics_stable: bool,
    established_factors: Sequence[str],
) -> dict[str, str]:
    """Classify validity before exposing any confirmatory effect wording."""

    execution_complete = not missing_shards
    integrity_pass = not integrity_errors
    validity_pass = bool(design_valid and execution_complete and integrity_pass)
    if not design_valid:
        verdict = "DESIGN-INVALID"
    elif not execution_complete:
        verdict = "EXECUTION-INCOMPLETE"
    elif not integrity_pass:
        verdict = "INTEGRITY-INVALID"
    elif established_factors:
        verdict = "MATERIAL-EFFECT-ESTABLISHED"
    else:
        verdict = "MATERIAL-EFFECT-NOT-ESTABLISHED"
    return {
        "design": "VALID" if design_valid else "INVALID",
        "execution": "COMPLETE" if execution_complete else "INCOMPLETE",
        "integrity": "PASS" if integrity_pass else "FAIL",
        "training_dynamics": (
            "STABLE" if dynamics_stable else "UNSTABLE"
        ) if validity_pass else "NOT_ASSESSED",
        "material_effect": (
            "ESTABLISHED" if established_factors else "NOT_ESTABLISHED"
        ) if validity_pass else "NOT_TESTED",
        "verdict": verdict,
    }
