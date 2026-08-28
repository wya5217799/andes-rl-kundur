"""Fail-closed integrity interface for U2 confirmatory execution.

The round adapter supplies paths and the frozen scientific contract. This
module owns the three behaviours that must stay local and independently
testable: complete seal verification, executable terminal semantics, and
classification precedence.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ReviewCoverage:
    """The common provenance accepted from two independent reviews."""

    reviewed_commit: str
    reviewer_ids: tuple[str, str]
    reviewed_files: dict[str, str]


@dataclass(frozen=True)
class ConfirmatoryAnalysisContext:
    """Round-bound dependencies for the frozen U2 confirmatory analysis."""

    round_id: str
    contract_sha256: str
    seal_sha256: str
    output_root: Path
    arms: tuple[str, ...]
    seeds: tuple[int, ...]
    primary_metric: str
    secondary_metric: str
    materiality_log: float
    scope: str
    read_hashed_json: Callable[[Path], dict[str, Any]]
    arm_factors: Callable[[str], Mapping[str, Any]]
    paired_main_effects: Callable[[str, str], dict[str, list[float]]]
    signflip_p_one_sided: Callable[[list[float], float], float]
    exact_bootstrap_ci: Callable[[list[float]], tuple[float, float]]
    apply_holm_two: Callable[[dict[str, dict[str, Any]]], None]
    design_valid: Callable[[], bool]
    created_utc: str


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


read_hashed_json = _read_hashed_json


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
    commit_file_sha256: Callable[[Path, str, str], str] | None = None,
) -> ReviewCoverage:
    """Require independent reviews over one current, committed hash map."""

    if len(review_paths) != 2:
        raise RuntimeError("exactly two independent review artifacts are required")
    expected = {
        _repo_relative(path, repo_root): _sha256(path)
        for path in reviewed_files
    }
    observed_files: list[dict[str, str]] = []
    observed_commits: list[str] = []
    reviewer_ids: list[str] = []
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
        reviewed_commit = review.get("reviewed_commit")
        if (
            not isinstance(reviewed_commit, str)
            or len(reviewed_commit) != 40
            or any(character not in "0123456789abcdef" for character in reviewed_commit)
        ):
            raise RuntimeError(f"invalid reviewed_commit: {path}")
        reviewer_id = review.get("reviewer_id")
        if not isinstance(reviewer_id, str) or not reviewer_id.strip():
            raise RuntimeError(f"missing reviewer_id: {path}")
        observed_files.append(dict(files))
        observed_commits.append(reviewed_commit)
        reviewer_ids.append(reviewer_id.strip())
    if observed_files[0] != observed_files[1]:
        raise RuntimeError("reviewed_files maps are not identical")
    if observed_files[0] != expected:
        raise RuntimeError("reviewed_files map does not match current source hashes")
    if observed_commits[0] != observed_commits[1]:
        raise RuntimeError("reviewed_commit values are not identical")
    if reviewer_ids[0] == reviewer_ids[1]:
        raise RuntimeError("reviews are not independent")
    snapshot_sha256 = commit_file_sha256 or git_commit_file_sha256
    for relative, expected_sha256 in expected.items():
        if snapshot_sha256(repo_root, observed_commits[0], relative) != expected_sha256:
            raise RuntimeError(f"reviewed_commit does not contain reviewed source: {relative}")
    return ReviewCoverage(
        reviewed_commit=observed_commits[0],
        reviewer_ids=(reviewer_ids[0], reviewer_ids[1]),
        reviewed_files=expected,
    )


def git_commit_file_sha256(repo_root: Path, commit: str, relative_path: str) -> str:
    """Hash reviewed bytes while allowing only checkout newline conversion.

    A Windows checkout may contain a mix of LF and CRLF files even with
    ``core.autocrlf`` enabled, so neither raw blobs nor unconditional smudge
    filters reproduce every executed file.  Compare the current file with the
    reviewed blob after canonicalizing CRLF to LF.  Return the current-byte
    digest only when that is the sole difference; any content drift retains
    the blob digest and therefore fails the caller's current-hash comparison.
    """

    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "show",
            f"{commit}:{relative_path}",
        ],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"cannot read reviewed commit {commit}: {relative_path}: {detail}")
    blob = result.stdout
    current_path = repo_root / relative_path
    try:
        current = current_path.read_bytes()
    except OSError as error:
        raise RuntimeError(f"cannot read reviewed working file: {current_path}: {error}") from error
    text_suffixes = {".json", ".md", ".py", ".sh", ".toml", ".txt", ".yaml", ".yml"}
    is_text_path = current_path.suffix.lower() in text_suffixes
    normalized_blob = blob.replace(b"\r\n", b"\n")
    normalized_current = current.replace(b"\r\n", b"\n")
    newline_only_change = is_text_path and normalized_current == normalized_blob
    accepted = current if newline_only_change else blob
    return hashlib.sha256(accepted).hexdigest()


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
    commit_file_sha256: Callable[[Path, str, str], str] | None = None,
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
        if path.suffix == ".json":
            _read_hashed_json(path)
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

    review = validate_review_coverage(
        review_paths,
        repo_root=repo_root,
        reviewed_files=reviewed_files,
        commit_file_sha256=commit_file_sha256,
    )
    if seal.get("reviewed_files") != review.reviewed_files:
        raise RuntimeError("sealed reviewed_files map drift")
    if seal.get("reviewed_commit") != review.reviewed_commit:
        raise RuntimeError("sealed reviewed_commit drift")
    if seal.get("reviewer_ids") != list(review.reviewer_ids):
        raise RuntimeError("sealed reviewer provenance drift")
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


class TerminalGuardedEnvironment:
    """Apply the rehearsed terminal predicate to every real environment step."""

    def __init__(
        self,
        environment: Any,
        *,
        steps: int,
        predicate: Callable[..., bool] = terminal_invalid,
    ) -> None:
        self._environment = environment
        self._steps = int(steps)
        self._predicate = predicate
        self._time_index = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self._environment, name)

    def reset(self, *args: Any, **kwargs: Any) -> Any:
        self._time_index = 0
        return self._environment.reset(*args, **kwargs)

    def step(self, *args: Any, **kwargs: Any) -> Any:
        result = self._environment.step(*args, **kwargs)
        if len(result) != 4:
            raise RuntimeError("unexpected environment step result")
        _observation, _reward, done, info = result
        tds_failed = bool(info.get("tds_failed"))
        if self._predicate(
            done=bool(done),
            tds_failed=tds_failed,
            time_index=self._time_index,
            steps=self._steps,
        ):
            kind = "TDS failure" if tds_failed else "premature terminal"
            raise RuntimeError(f"{kind} at step {self._time_index} of {self._steps}")
        self._time_index += 1
        return result


def guard_environment_builder(
    builder: Callable[..., Any],
    *,
    steps: int,
    predicate: Callable[..., bool] = terminal_invalid,
) -> Callable[..., TerminalGuardedEnvironment]:
    """Wrap a real ANDES environment builder with the shared terminal gate."""

    def guarded(*args: Any, **kwargs: Any) -> TerminalGuardedEnvironment:
        return TerminalGuardedEnvironment(
            builder(*args, **kwargs),
            steps=steps,
            predicate=predicate,
        )

    return guarded


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


def build_confirmatory_analysis(
    context: ConfirmatoryAnalysisContext,
    *,
    missing_shards: Sequence[str],
) -> dict[str, Any]:
    """Build the complete frozen U2 analysis behind the package interface."""

    if missing_shards:
        classification = classify_confirmatory(
            design_valid=context.design_valid(),
            missing_shards=missing_shards,
            integrity_errors=[],
            dynamics_stable=False,
            established_factors=[],
        )
        return {
            "schema_version": 1,
            "round": context.round_id,
            "contract_sha256": context.contract_sha256,
            "seal_sha256": context.seal_sha256,
            "integrity": {"valid": True, "errors": []},
            "missing_shards": list(missing_shards),
            "main_effects": {},
            "primary_materiality_tests": {},
            "classification": classification,
            "created_utc": context.created_utc,
        }

    integrity_errors: list[str] = []
    base_hashes: dict[int, set[str]] = {seed: set() for seed in context.seeds}
    reward_hashes: dict[bool, set[str]] = {False: set(), True: set()}
    stability_rows: dict[str, list[dict[str, Any]]] = {}
    for arm in context.arms:
        stability_rows[arm] = []
        for seed in context.seeds:
            manifest = context.read_hashed_json(
                context.output_root / "train" / arm / f"seed{seed}" / "manifest.json"
            )
            if not manifest["valid"] or int(manifest["interaction_steps"]) != 43_200:
                integrity_errors.append(f"invalid training {arm} seed{seed}")
            base_hashes[seed].add(str(manifest["base_state_sha256"]))
            reward = bool(context.arm_factors(arm)["reward_access"])
            reward_hashes[reward].add(str(manifest["reward_function_sha256"]))
            stability_rows[arm].append(manifest["stability"])
    for seed, hashes in base_hashes.items():
        if len(hashes) != 1:
            integrity_errors.append(f"base state mismatch seed{seed}")
    if (
        any(len(hashes) != 1 for hashes in reward_hashes.values())
        or reward_hashes[False] != reward_hashes[True]
    ):
        integrity_errors.append("reward implementation hash mismatch")

    stage_effects = {
        stage: {
            metric: context.paired_main_effects(stage, metric)
            for metric in (context.primary_metric, context.secondary_metric)
        }
        for stage in ("half", "final")
    }
    final_primary = stage_effects["final"][context.primary_metric]
    primary_tests: dict[str, dict[str, Any]] = {}
    for factor in ("actor", "critic"):
        values = final_primary[factor]
        p_value = context.signflip_p_one_sided(values, context.materiality_log)
        ci_low, ci_high = context.exact_bootstrap_ci(values)
        primary_tests[factor] = {
            "paired_log_effects": values,
            "mean_log_effect": float(np.mean(values)),
            "geometric_improvement": float(math.exp(float(np.mean(values))) - 1.0),
            "materiality_log": context.materiality_log,
            "materiality_p_one_sided": p_value,
            "bootstrap_ci95_descriptive": [ci_low, ci_high],
            "holm_reject": False,
            "direction_count_positive": int(sum(value > 0 for value in values)),
            "seed_min": float(np.min(values)),
            "seed_median": float(np.median(values)),
            "leave_one_out_means": [
                float(np.mean([value for index, value in enumerate(values) if index != skip]))
                for skip in range(len(values))
            ],
        }
    context.apply_holm_two(primary_tests)

    direction_flips = {}
    for factor in ("actor", "critic"):
        half = float(np.mean(stage_effects["half"][context.primary_metric][factor]))
        final = float(np.mean(stage_effects["final"][context.primary_metric][factor]))
        direction_flips[factor] = {
            "half_mean": half,
            "final_mean": final,
            "flipped": bool(np.sign(half) != np.sign(final)),
        }
    no_plateau = [
        f"{arm}|{seed}|{kind}"
        for arm in context.arms
        for seed, row in zip(context.seeds, stability_rows[arm], strict=True)
        for kind in ("critic_loss", "actor_loss")
        if not row[kind]["stable"]
    ]
    dynamics_stable = not any(
        row["flipped"] for row in direction_flips.values()
    ) and not no_plateau
    established = [
        factor for factor, row in primary_tests.items() if row["holm_reject"]
    ]
    classification = classify_confirmatory(
        design_valid=context.design_valid(),
        missing_shards=[],
        integrity_errors=integrity_errors,
        dynamics_stable=dynamics_stable,
        established_factors=established,
    )
    for row in primary_tests.values():
        row["material_effect"] = (
            "NOT_TESTED"
            if classification["material_effect"] == "NOT_TESTED"
            else ("ESTABLISHED" if row["holm_reject"] else "NOT_ESTABLISHED")
        )
    return {
        "schema_version": 1,
        "round": context.round_id,
        "contract_sha256": context.contract_sha256,
        "seal_sha256": context.seal_sha256,
        "integrity": {
            "valid": not integrity_errors,
            "errors": integrity_errors,
            "six_seed_base_hashes": {
                str(seed): sorted(values) for seed, values in base_hashes.items()
            },
            "reward_hashes": {
                str(key): sorted(values) for key, values in reward_hashes.items()
            },
        },
        "missing_shards": [],
        "main_effects": stage_effects,
        "primary_materiality_tests": primary_tests,
        "optimization": {
            "direction_flips": direction_flips,
            "nonplateau_rows": no_plateau,
            "unresolved": not dynamics_stable,
        },
        "classification": {
            **classification,
            "scope": context.scope,
            "universal_intrinsic_claim_authorized": False,
        },
        "created_utc": context.created_utc,
    }


def check_artifact_budget(
    output_root: Path,
    *,
    max_bytes: int = 650 * 1024 * 1024,
) -> dict[str, int]:
    """Fail before finalization when the sealed artifact budget is exceeded."""

    total_bytes = (
        sum(path.stat().st_size for path in output_root.rglob("*") if path.is_file())
        if output_root.exists()
        else 0
    )
    if total_bytes > max_bytes:
        raise RuntimeError(
            f"R476 artifact budget exceeded: {total_bytes} > {max_bytes} bytes"
        )
    return {"total_bytes": total_bytes, "max_bytes": max_bytes}


def recalibrate_eta(
    first_wave: Mapping[str, Any],
    *,
    remaining_training_shards: int,
    evaluation_wave_count: int,
) -> dict[str, Any]:
    """Persist a scope-preserving ETA update after the first bounded wave."""

    failed = first_wave.get("failed")
    results = first_wave.get("results")
    completed = len(results) if isinstance(results, Mapping) else 0
    wall_seconds = float(first_wave.get("wall_seconds", 0.0))
    if failed or completed < 1 or wall_seconds <= 0:
        raise RuntimeError("first training wave is incomplete; ETA cannot be recalibrated")
    training_waves = math.ceil(remaining_training_shards / completed)
    remaining_wave_equivalents = training_waves + int(evaluation_wave_count)
    return {
        "schema_version": 1,
        "basis": "observed first 16-shard training wave",
        "first_wave_completed_shards": completed,
        "first_wave_wall_seconds": wall_seconds,
        "remaining_training_shards": int(remaining_training_shards),
        "evaluation_wave_count": int(evaluation_wave_count),
        "concurrency_unchanged": True,
        "scope_unchanged": True,
        "estimated_remaining_seconds": wall_seconds * remaining_wave_equivalents,
        "estimated_remaining_range_seconds": [
            wall_seconds * remaining_wave_equivalents * 0.8,
            wall_seconds * remaining_wave_equivalents * 1.5,
        ],
    }


def inventory_artifacts(
    *,
    repo_root: Path,
    result_root: Path,
    log_roots: Sequence[Path],
    phase: str,
    exit_code: int,
    created_utc: str,
) -> dict[str, Any]:
    """Inventory preserved result and log files on every pipeline exit."""

    rows: list[dict[str, Any]] = []
    for root in (result_root, *log_roots):
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            row: dict[str, Any] = {
                "path": _repo_relative(path, repo_root),
                "bytes": path.stat().st_size,
                "is_log": root != result_root,
            }
            if not path.name.endswith(".sha256"):
                sidecar = Path(f"{path}.sha256")
                row["sidecar_present"] = sidecar.is_file()
                if sidecar.is_file():
                    tokens = sidecar.read_text(encoding="ascii").split()
                    row["sidecar_valid"] = bool(tokens and tokens[0] == _sha256(path))
            rows.append(row)
    return {
        "schema_version": 1,
        "phase": phase,
        "exit_code": int(exit_code),
        "interrupted": int(exit_code) in (130, 143),
        "same_round_resume_authorized": False,
        "partial_files_are_scientific": False,
        "file_count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
        "files": rows,
        "created_utc": created_utc,
    }
