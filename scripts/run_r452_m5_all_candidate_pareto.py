"""R452 M5: complete R439 candidate guard table and finite-grid Pareto front.

Physical commands are WSL-only and must run through ``andes_scratch.py``.
Formal outputs are create-only JSON files with SHA-256 sidecars.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import itertools
import json
import math
import os
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_name] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


R439_RUNNER = ROOT / "scripts/run_r439_timevarying_oracle.py"
R441_RUNNER = ROOT / "scripts/run_r441_timevarying_guard.py"
R439 = _load_module("_r452_r439_parent", R439_RUNNER)
R441 = _load_module("_r452_r441_parent", R441_RUNNER)

ROUND_ID = "R452"
PLAN = ROOT / "memory/rounds/R452/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
CAPACITY = ROOT / "memory/rounds/R452/capacity_evidence.json"
REHEARSAL = ROOT / "memory/rounds/R452/rehearsal.json"
SEAL = ROOT / "memory/rounds/R452/formal_seal.json"
SHARDS = ROOT / "tmp/andes/r452_m5_shards.json"
OUT = ROOT / "results/research_loop/r452_m5_all_candidate_pareto"
R441_OUT = ROOT / "results/research_loop/r441_timevarying_guard"

PROFILE_IDS = ("eval_a", "eval_b", "eval_c", "eval_d")
M_GRID = tuple(float(value) for value in R439.M_GRID)
SEGMENT_COUNTS = (2, 3, 5)
RANDOM_SAMPLES_K5 = int(R439.RANDOM_SAMPLES_K5)
STATIC_SELECTED = str(R439.STATIC_SELECTED)
SEED = 399
CHUNKS_PER_PROFILE = 16
CAPACITY_RUNGS = (1, 2, 4, 8, 12, 16)
CAPACITY_JOBS_PER_RUNG = 32
WORKER_RSS_FLOOR_BYTES = 943_718_400
OS_FLOOR_BYTES = 3 * 1024**3

IMPROVEMENT_MIN = 0.05
COMMON_HARM_MAX = 0.03
ACTION_STRESS_HARM_MAX = 0.10
SATURATION_MAX = 0.05
ANCHOR_REL_TOL = 1.0e-6
EXPECTED_CANDIDATE_SHA256 = (
    "6f505fa569e5a22d8163da44a38292fecc433180cff7640fce6fff4984433962"
)

SUMMARY_KEYS = (
    "disturbance_differential_energy",
    "off_diagonal_response_energy",
    "common_frequency_iae_hz_s",
    "worst_unit_peak_hz",
    "worst_rocof_hz_s",
    "action_rms",
    "action_total_variation",
    "action_saturation_fraction",
)


def _sha256_file(path: Path) -> str:
    return R441._sha256_file(path)


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> str:
    return R441._write_new_json(path, payload)


def _read_hashed_json(path: Path) -> dict[str, Any]:
    return R441._read_hashed_json(path)


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _canonical_sha256(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def candidates() -> list[dict[str, Any]]:
    """Reproduce R439 generation order while retaining generated duplicates."""
    diagonal = tuple((value, value) for value in M_GRID)
    rows: list[dict[str, Any]] = []
    global_index = 0
    for k in (2, 3):
        for local_index, schedule in enumerate(
            itertools.product(diagonal, repeat=k)
        ):
            rows.append(
                {
                    "candidate_id": f"k{k}_{local_index:03d}",
                    "global_index": global_index,
                    "k": k,
                    "schedule": [list(pair) for pair in schedule],
                }
            )
            global_index += 1
    rng = np.random.default_rng(SEED)
    grid = np.asarray(diagonal)
    for local_index in range(RANDOM_SAMPLES_K5):
        indices = rng.integers(0, len(grid), size=5)
        schedule = [
            [float(value) for value in row]
            for row in grid[indices]
        ]
        rows.append(
            {
                "candidate_id": f"k5_{local_index:03d}",
                "global_index": global_index,
                "k": 5,
                "schedule": schedule,
            }
        )
        global_index += 1
    return rows


def candidate_sequence_sha256() -> str:
    return _canonical_sha256(candidates())


def candidate_chunks() -> list[list[dict[str, Any]]]:
    rows = candidates()
    base_size, remainder = divmod(len(rows), CHUNKS_PER_PROFILE)
    chunks: list[list[dict[str, Any]]] = []
    start = 0
    for index in range(CHUNKS_PER_PROFILE):
        size = base_size + (1 if index < remainder else 0)
        chunks.append(rows[start : start + size])
        start += size
    if start != len(rows):
        raise AssertionError("candidate chunk partition is incomplete")
    return chunks


def expected_shard_ids() -> list[str]:
    candidate_ids = [
        f"candidate|{profile_id}|{chunk_index:02d}"
        for profile_id in PROFILE_IDS
        for chunk_index in range(CHUNKS_PER_PROFILE)
    ]
    static_ids = [f"static|{profile_id}|00" for profile_id in PROFILE_IDS]
    return candidate_ids + static_ids


def _schedule_tuple(candidate: Mapping[str, Any]) -> tuple[tuple[float, float], ...]:
    return tuple(
        (float(pair[0]), float(pair[1])) for pair in candidate["schedule"]
    )


def genuinely_varying(schedule: Sequence[Sequence[float]]) -> bool:
    pairs = [tuple(float(value) for value in pair) for pair in schedule]
    return any(left != right for left, right in zip(pairs, pairs[1:]))


def build_contract() -> dict[str, Any]:
    contract = copy.deepcopy(R439.build_contract())
    contract["round"] = ROUND_ID
    contract["r452"] = {
        "parent_rounds": ["R439", "R441"],
        "profile_ids": list(PROFILE_IDS),
        "candidate_counts": {"2": 25, "3": 125, "5": 200},
        "candidate_total_per_profile": 350,
        "candidate_sequence_sha256": EXPECTED_CANDIDATE_SHA256,
        "chunks_per_profile": CHUNKS_PER_PROFILE,
        "execution_shards": 68,
        "candidate_trajectories": 8_400,
        "static_trajectories": 24,
        "thresholds": {
            "joint_endpoint_improvement_min": IMPROVEMENT_MIN,
            "maximum_common_harm": COMMON_HARM_MAX,
            "maximum_action_stress_harm": ACTION_STRESS_HARM_MAX,
            "maximum_action_saturation_fraction": SATURATION_MAX,
            "anchor_relative_tolerance": ANCHOR_REL_TOL,
        },
        "static_selected": STATIC_SELECTED,
        "plan_sha256": _sha256_file(PLAN),
    }
    return contract


def contract_sha256(contract: Mapping[str, Any] | None = None) -> str:
    return _canonical_sha256(build_contract() if contract is None else contract)


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R452 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R452 must run through scripts/andes_scratch.py")


def authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    rows = candidates()
    counts = Counter(int(row["k"]) for row in rows)
    return {
        "active_plan": "round: R452" in plan_text and "state: active" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "candidate_contract": len(rows) == 350
        and counts == {2: 25, 3: 125, 5: 200}
        and candidate_sequence_sha256() == EXPECTED_CANDIDATE_SHA256,
        "shard_contract": len(expected_shard_ids()) == 68
        and len(set(expected_shard_ids())) == 68,
        "output_absence": not OUT.exists(),
    }


def installed_runtime() -> dict[str, Any]:
    import andes

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    return {
        "python": sys.version,
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "andes_module": str(Path(andes.__file__).resolve()),
        "case_path": str(case_path),
        "case_sha256": _sha256_file(case_path),
    }


def load_seal() -> dict[str, Any]:
    seal = _read_hashed_json(SEAL)
    if seal.get("round") != ROUND_ID:
        raise RuntimeError("seal belongs to another round")
    if seal.get("contract_sha256") != contract_sha256():
        raise RuntimeError("contract drifted from seal")
    for name, entry in (seal.get("sources") or {}).items():
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed source drift: {name}")
    if _sha256_file(CAPACITY) != seal.get("capacity_sha256"):
        raise RuntimeError("capacity evidence drifted from seal")
    if _sha256_file(REHEARSAL) != seal.get("rehearsal_sha256"):
        raise RuntimeError("rehearsal drifted from seal")
    return seal


def _profiles_by_id() -> dict[str, dict[str, Any]]:
    return {
        str(profile["profile_id"]): profile
        for profile in R439._profiles()
        if str(profile["profile_id"]) in PROFILE_IDS
    }


def _trajectory_errors(records: Sequence[Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    for record in records:
        if not record.get("completed") or record.get("tds_failed"):
            errors.append(
                f"{record.get('scenario_id')}: {record.get('failure') or 'incomplete'}"
            )
    return errors


def _run_summary(
    profile: Mapping[str, Any],
    *,
    static: bool = False,
    schedule: Sequence[Sequence[float]] | None = None,
) -> tuple[dict[str, Any] | None, list[str], int]:
    scenarios = R439._evaluation_scenarios(profile)
    records = [
        R439._run_trajectory(
            profile,
            scenario,
            static_arm=STATIC_SELECTED if static else None,
            timevarying=None if static else tuple(
                (float(pair[0]), float(pair[1])) for pair in (schedule or ())
            ),
        )
        for scenario in scenarios
    ]
    errors = _trajectory_errors(records)
    if errors:
        return None, errors, len(records)
    try:
        summary = R441.summarise_profile(records, contract=build_contract())
    except Exception as exc:  # noqa: BLE001
        return None, [f"summary: {type(exc).__name__}: {exc}"], len(records)
    return summary, [], len(records)


def _shard_path(kind: str, profile_id: str, chunk_index: int) -> Path:
    if kind == "static":
        return OUT / "shards" / profile_id / "static.json"
    return OUT / "shards" / profile_id / f"candidate_{chunk_index:02d}.json"


def run_shard(shard_id: str) -> str:
    _assert_wsl_scratch()
    load_seal()
    kind, profile_id, chunk_text = shard_id.split("|")
    if shard_id not in expected_shard_ids():
        raise ValueError(f"unregistered shard: {shard_id}")
    profile = _profiles_by_id()[profile_id]
    chunk_index = int(chunk_text)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "round": ROUND_ID,
        "shard_id": shard_id,
        "kind": kind,
        "profile_id": profile_id,
        "contract_sha256": contract_sha256(),
        "created_utc": datetime.now(UTC).isoformat(),
    }
    if kind == "static":
        summary, errors, trajectory_count = _run_summary(profile, static=True)
        payload.update(
            {
                "trajectory_count": trajectory_count,
                "summary": summary,
                "errors": errors,
                "valid_execution": not errors and summary is not None,
            }
        )
    else:
        chunk = candidate_chunks()[chunk_index]
        rows = []
        trajectory_count = 0
        for candidate in chunk:
            summary, errors, count = _run_summary(
                profile, schedule=candidate["schedule"]
            )
            trajectory_count += count
            rows.append(
                {
                    **candidate,
                    "genuinely_varying": genuinely_varying(candidate["schedule"]),
                    "summary": summary,
                    "errors": errors,
                }
            )
        payload.update(
            {
                "chunk_index": chunk_index,
                "candidate_count": len(rows),
                "trajectory_count": trajectory_count,
                "candidate_ids": [row["candidate_id"] for row in rows],
                "rows": rows,
                "errors": [
                    f"{row['candidate_id']}: {error}"
                    for row in rows
                    for error in row["errors"]
                ],
                "valid_execution": all(
                    not row["errors"] and row["summary"] is not None for row in rows
                ),
            }
        )
    return _write_new_json(_shard_path(kind, profile_id, chunk_index), payload)


def candidate_guard(
    summary: Mapping[str, Any], static: Mapping[str, Any]
) -> dict[str, Any]:
    static_r_d = float(static["disturbance_differential_energy"])
    static_r_x = float(static["off_diagonal_response_energy"])
    r_d = float(summary["disturbance_differential_energy"])
    r_x = float(summary["off_diagonal_response_energy"])
    improvement_d = (static_r_d - r_d) / max(static_r_d, 1.0e-12)
    improvement_x = (static_r_x - r_x) / max(static_r_x, 1.0e-12)
    common = {
        "common_frequency_iae_no_harm": float(summary["common_frequency_iae_hz_s"])
        <= (1.0 + COMMON_HARM_MAX) * float(static["common_frequency_iae_hz_s"]),
        "worst_peak_no_harm": float(summary["worst_unit_peak_hz"])
        <= (1.0 + COMMON_HARM_MAX) * float(static["worst_unit_peak_hz"]),
        "rocof_no_harm": float(summary["worst_rocof_hz_s"])
        <= (1.0 + COMMON_HARM_MAX) * float(static["worst_rocof_hz_s"]),
    }
    action = {
        "action_rms_no_harm": float(summary["action_rms"])
        <= (1.0 + ACTION_STRESS_HARM_MAX) * float(static["action_rms"]),
        "action_variation_no_harm": float(summary["action_total_variation"])
        <= (1.0 + ACTION_STRESS_HARM_MAX)
        * float(static["action_total_variation"]),
    }
    endpoint = {
        "disturbance_improvement": improvement_d,
        "off_diagonal_improvement": improvement_x,
        "disturbance_eligible": improvement_d >= IMPROVEMENT_MIN - 1.0e-15,
        "off_diagonal_eligible": improvement_x >= IMPROVEMENT_MIN - 1.0e-15,
    }
    joint_endpoint = bool(
        endpoint["disturbance_eligible"] and endpoint["off_diagonal_eligible"]
    )
    valid = bool(static.get("valid") is True and summary.get("valid") is True)
    saturation = bool(
        float(summary["action_saturation_fraction"]) <= SATURATION_MAX + 1.0e-15
    )
    common_clean = all(common.values())
    action_clean = all(action.values())
    return {
        "valid": valid,
        "endpoint": endpoint,
        "joint_endpoint_eligible": joint_endpoint,
        "common_no_harm": common,
        "common_clean": common_clean,
        "action_stress_no_harm": action,
        "action_clean": action_clean,
        "saturation_pass": saturation,
        "joint_guard_feasible": bool(
            valid and joint_endpoint and common_clean and action_clean and saturation
        ),
    }


def _objectives(
    summary: Mapping[str, Any], static: Mapping[str, Any]
) -> tuple[float, float, float, float]:
    return tuple(
        float(summary[key]) / max(float(static[key]), 1.0e-12)
        for key in (
            "disturbance_differential_energy",
            "off_diagonal_response_energy",
            "action_rms",
            "action_total_variation",
        )
    )


def _dominates(left: Sequence[float], right: Sequence[float]) -> bool:
    return all(a <= b for a, b in zip(left, right, strict=True)) and any(
        a < b for a, b in zip(left, right, strict=True)
    )


def nondominated(rows: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    material = list(rows)
    for row in material:
        if not all(math.isfinite(float(value)) for value in row["objectives"]):
            raise ValueError("all Pareto objectives must be finite")
    result = []
    for index, row in enumerate(material):
        objective = tuple(float(value) for value in row["objectives"])
        if not any(
            other_index != index
            and _dominates(
                tuple(float(value) for value in other["objectives"]), objective
            )
            for other_index, other in enumerate(material)
        ):
            result.append(row)
    return result


def _is_finite(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float, np.integer, np.floating)):
        return math.isfinite(float(value))
    if isinstance(value, Mapping):
        return all(_is_finite(item) for item in value.values())
    if isinstance(value, Sequence):
        return all(_is_finite(item) for item in value)
    return True


def _anchor_compare(actual: Any, expected: Any, path: str = "") -> dict[str, Any]:
    failures: list[str] = []
    max_relative_error = 0.0

    def visit(left: Any, right: Any, location: str) -> None:
        nonlocal max_relative_error
        if isinstance(right, bool) or isinstance(left, bool):
            if left is not right:
                failures.append(location)
            return
        if isinstance(right, (int, float)) and isinstance(left, (int, float)):
            relative = abs(float(left) - float(right)) / max(abs(float(right)), 1.0e-12)
            max_relative_error = max(max_relative_error, relative)
            if not math.isfinite(relative) or relative > ANCHOR_REL_TOL:
                failures.append(location)
            return
        if isinstance(right, Mapping) and isinstance(left, Mapping):
            if set(left) != set(right):
                failures.append(location + ".keys")
                return
            for key in right:
                visit(left[key], right[key], f"{location}/{key}")
            return
        if isinstance(right, Sequence) and not isinstance(right, (str, bytes)):
            if not isinstance(left, Sequence) or len(left) != len(right):
                failures.append(location + ".length")
                return
            for index, (left_item, right_item) in enumerate(zip(left, right, strict=True)):
                visit(left_item, right_item, f"{location}/{index}")
            return
        if left != right:
            failures.append(location)

    visit(actual, expected, path or "/")
    return {
        "passes": not failures,
        "max_relative_error": max_relative_error,
        "failures": failures,
    }


def _load_r441_profile(profile_id: str) -> dict[str, Any]:
    return _read_hashed_json(R441_OUT / "profiles" / f"{profile_id}.json")


def _summarize_profile_rows(
    profile_id: str,
    static: Mapping[str, Any],
    raw_rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    integrity_errors: list[str] = []
    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        summary = raw.get("summary")
        if summary is None or raw.get("errors"):
            integrity_errors.append(f"{profile_id} {raw.get('candidate_id')} invalid trajectory")
            continue
        if not _is_finite(summary):
            integrity_errors.append(f"{profile_id} {raw.get('candidate_id')} nonfinite summary")
            continue
        guard = candidate_guard(summary, static)
        objective = _objectives(summary, static)
        rows.append(
            {
                "candidate_id": raw["candidate_id"],
                "global_index": int(raw["global_index"]),
                "k": int(raw["k"]),
                "schedule": raw["schedule"],
                "genuinely_varying": bool(raw["genuinely_varying"]),
                "summary": summary,
                "guards": guard,
                "objectives": list(objective),
            }
        )
    rows.sort(key=lambda row: int(row["global_index"]))
    eligible = [
        row
        for row in rows
        if row["guards"]["valid"] and row["guards"]["joint_endpoint_eligible"]
    ]
    pareto_source = [
        row
        for row in rows
        if row["guards"]["valid"]
        and row["guards"]["common_clean"]
        and row["guards"]["saturation_pass"]
    ]
    pareto = list(nondominated(pareto_source))

    def minimum(metric: str) -> dict[str, Any] | None:
        if not eligible:
            return None
        row = min(
            eligible,
            key=lambda item: (float(item["summary"][metric]), int(item["global_index"])),
        )
        return {
            "candidate_id": row["candidate_id"],
            "value": float(row["summary"][metric]),
            "ratio_to_static": float(row["summary"][metric])
            / max(float(static[metric]), 1.0e-12),
            "genuinely_varying": bool(row["genuinely_varying"]),
        }

    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "profile_id": profile_id,
        "static": static,
        "candidate_count": len(rows),
        "candidate_rows": rows,
        "joint_endpoint_eligible_count": len(eligible),
        "joint_guard_feasible_ids": [
            row["candidate_id"]
            for row in rows
            if row["guards"]["joint_guard_feasible"]
        ],
        "conditional_minima": {
            "action_rms": minimum("action_rms"),
            "action_total_variation": minimum("action_total_variation"),
        },
        "pareto": [
            {
                "candidate_id": row["candidate_id"],
                "global_index": row["global_index"],
                "k": row["k"],
                "schedule": row["schedule"],
                "genuinely_varying": row["genuinely_varying"],
                "objectives": row["objectives"],
            }
            for row in pareto
        ],
    }
    return payload, integrity_errors


def aggregate() -> str:
    _assert_wsl_scratch()
    seal = load_seal()
    expected_candidates = candidates()
    expected_ids = [row["candidate_id"] for row in expected_candidates]
    integrity_errors: list[str] = []
    shard_payloads: dict[str, dict[str, Any]] = {}
    for shard_id in expected_shard_ids():
        kind, profile_id, chunk_text = shard_id.split("|")
        try:
            payload = _read_hashed_json(
                _shard_path(kind, profile_id, int(chunk_text))
            )
        except Exception as exc:  # noqa: BLE001
            integrity_errors.append(f"{shard_id}: {type(exc).__name__}: {exc}")
            continue
        if payload.get("shard_id") != shard_id:
            integrity_errors.append(f"{shard_id}: shard identity mismatch")
        if payload.get("contract_sha256") != contract_sha256():
            integrity_errors.append(f"{shard_id}: contract mismatch")
        if not payload.get("valid_execution"):
            integrity_errors.append(f"{shard_id}: invalid execution")
        shard_payloads[shard_id] = payload

    profile_outputs: dict[str, dict[str, Any]] = {}
    anchor_checks: dict[str, Any] = {}
    candidate_trajectory_count = 0
    static_trajectory_count = 0
    for profile_id in PROFILE_IDS:
        static_id = f"static|{profile_id}|00"
        if static_id not in shard_payloads:
            continue
        static_payload = shard_payloads[static_id]
        static_trajectory_count += int(static_payload.get("trajectory_count", 0))
        static = static_payload.get("summary")
        if static is None:
            integrity_errors.append(f"{profile_id}: missing static summary")
            continue
        raw_rows: list[dict[str, Any]] = []
        for chunk_index in range(CHUNKS_PER_PROFILE):
            shard_id = f"candidate|{profile_id}|{chunk_index:02d}"
            payload = shard_payloads.get(shard_id)
            if payload is None:
                continue
            candidate_trajectory_count += int(payload.get("trajectory_count", 0))
            raw_rows.extend(payload.get("rows") or [])
        actual_ids = [str(row.get("candidate_id")) for row in raw_rows]
        if actual_ids != expected_ids:
            integrity_errors.append(f"{profile_id}: candidate ID/order mismatch")
        profile_payload, errors = _summarize_profile_rows(profile_id, static, raw_rows)
        integrity_errors.extend(errors)

        sealed = _load_r441_profile(profile_id)
        static_anchor = _anchor_compare(static, sealed["static"], "/static")
        winner_schedule = sealed["winner_candidate"]
        winner_k = int(sealed["winner_k"])
        winner_rows = [
            row
            for row in profile_payload["candidate_rows"]
            if int(row["k"]) == winner_k and row["schedule"] == winner_schedule
        ]
        if not winner_rows:
            winner_anchor = {
                "passes": False,
                "max_relative_error": math.inf,
                "failures": ["winner candidate absent"],
            }
            winner_guard_anchor = copy.deepcopy(winner_anchor)
        else:
            winner_anchor = _anchor_compare(
                winner_rows[0]["summary"], sealed["winner"], "/winner"
            )
            inherited_guard = R441._guard_report(static, winner_rows[0]["summary"])
            winner_guard_anchor = _anchor_compare(
                inherited_guard, sealed["guards"], "/guards"
            )
        anchor_checks[profile_id] = {
            "static": static_anchor,
            "winner": winner_anchor,
            "winner_guard": winner_guard_anchor,
            "passes": bool(
                static_anchor["passes"]
                and winner_anchor["passes"]
                and winner_guard_anchor["passes"]
            ),
        }
        if not anchor_checks[profile_id]["passes"]:
            integrity_errors.append(f"{profile_id}: R441 anchor failure")
        profile_outputs[profile_id] = profile_payload

    if candidate_trajectory_count != 8_400:
        integrity_errors.append(
            f"candidate trajectory count {candidate_trajectory_count} != 8400"
        )
    if static_trajectory_count != 24:
        integrity_errors.append(
            f"static trajectory count {static_trajectory_count} != 24"
        )
    if len(profile_outputs) != 4:
        integrity_errors.append(f"profile output count {len(profile_outputs)} != 4")
    if any(payload["candidate_count"] != 350 for payload in profile_outputs.values()):
        integrity_errors.append("one or more profiles do not contain 350 valid rows")

    for profile_id, payload in profile_outputs.items():
        _write_new_json(OUT / "profiles" / f"{profile_id}.json", payload)

    feasible_profiles = [
        profile_id
        for profile_id, payload in profile_outputs.items()
        if payload["joint_guard_feasible_ids"]
    ]
    if integrity_errors:
        verdict = "CANARY-INVALID"
    elif len(feasible_profiles) == 4:
        verdict = "GUARD-CLEAN-JOINT-HEADROOM-IN-GRID"
    elif feasible_profiles:
        verdict = "PARTIAL-GUARD-CLEAN-JOINT-HEADROOM-IN-GRID"
    else:
        verdict = "NO-GUARD-CLEAN-JOINT-HEADROOM-IN-GRID"
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "contract_sha256": contract_sha256(),
        "seal_sha256": _sha256_file(SEAL),
        "integrity": {
            "valid": not integrity_errors,
            "errors": integrity_errors,
            "execution_shards": len(shard_payloads),
            "candidate_rows": sum(
                payload["candidate_count"] for payload in profile_outputs.values()
            ),
            "candidate_trajectories": candidate_trajectory_count,
            "static_trajectories": static_trajectory_count,
            "candidate_sequence_sha256": candidate_sequence_sha256(),
        },
        "anchor_checks": anchor_checks,
        "profiles": {
            profile_id: {
                "candidate_count": payload["candidate_count"],
                "joint_endpoint_eligible_count": payload[
                    "joint_endpoint_eligible_count"
                ],
                "joint_guard_feasible_ids": payload["joint_guard_feasible_ids"],
                "conditional_minima": payload["conditional_minima"],
                "pareto": payload["pareto"],
                "profile_table": _relative(
                    OUT / "profiles" / f"{profile_id}.json"
                ),
            }
            for profile_id, payload in profile_outputs.items()
        },
        "classification": {
            "profiles_with_guard_clean_joint_headroom": feasible_profiles,
            "profile_count": len(feasible_profiles),
            "verdict": verdict,
        },
        "formal_authority": bool(seal.get("formal_authority")),
        "training_executed": False,
    }
    return _write_new_json(OUT / "formal_analysis.json", analysis)


def _capacity_job(_job_id: int) -> dict[str, Any]:
    profile = R439._profiles()[0]
    scenario = R439._evaluation_scenarios(profile)[0]
    record = R439._run_trajectory(profile, scenario, static_arm=STATIC_SELECTED)
    return {
        "ok": bool(record.get("completed")) and not bool(record.get("tds_failed")),
        "completed_steps": int(record.get("completed_steps", 0)),
    }


def capture_parent_candidate_sequence() -> list[list[list[float]]]:
    """Exercise R439's real generator with physical execution temporarily stubbed."""
    captured: list[list[list[float]]] = []
    original_run = R439._run_trajectory
    original_summary = R439.summarise_profile

    def capture_run(
        _profile: Mapping[str, Any],
        _scenario: Mapping[str, Any],
        *,
        static_arm: str | None = None,
        timevarying: Sequence[Sequence[float]] | None = None,
    ) -> dict[str, Any]:
        if static_arm is None and timevarying is not None:
            captured.append(
                [[float(value) for value in pair] for pair in timevarying]
            )
        return {"captured": True}

    def capture_summary(_records: Sequence[Mapping[str, Any]], **_kwargs: Any) -> dict[str, Any]:
        return {
            "valid": True,
            "disturbance_differential_energy": 1.0,
            "off_diagonal_response_energy": 1.0,
        }

    try:
        R439._run_trajectory = capture_run
        R439.summarise_profile = capture_summary
        R439._oracle_for_profile(R439._profiles()[0])
    finally:
        R439._run_trajectory = original_run
        R439.summarise_profile = original_summary
    if len(captured) != 350 * 6:
        raise AssertionError(f"parent generator emitted {len(captured)} candidate calls")
    collapsed = []
    for start in range(0, len(captured), 6):
        group = captured[start : start + 6]
        if any(schedule != group[0] for schedule in group[1:]):
            raise AssertionError("parent candidate changed across its six scenarios")
        collapsed.append(group[0])
    return collapsed


def _meminfo() -> dict[str, int]:
    result: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].isdigit():
            result[parts[0].rstrip(":")] = int(parts[1]) * 1024
    return result


def measure_capacity() -> str:
    _assert_wsl_scratch()
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed before capacity: {checks}")
    mem = _meminfo()
    process_lines = subprocess.run(
        ["ps", "-eo", "pid=,args="], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    other = [
        line.strip()
        for line in process_lines
        if ("scripts/run_" in line or "soft_spot_shard_driver.py" in line)
        and "run_r452" not in line
        and "run_r439_timevarying_oracle.py" not in line
    ]
    rungs: list[dict[str, Any]] = []
    previous_accepted_throughput: float | None = None
    selected = 0
    accepting = True
    for workers in CAPACITY_RUNGS:
        start = time.monotonic()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(_capacity_job, range(CAPACITY_JOBS_PER_RUNG)))
        wall = time.monotonic() - start
        throughput = len(rows) / max(wall, 1.0e-12)
        memory_safe = (
            workers * WORKER_RSS_FLOOR_BYTES + OS_FLOOR_BYTES
            <= int(mem["MemTotal"])
        )
        gain = (
            None
            if previous_accepted_throughput is None
            else throughput / previous_accepted_throughput
        )
        repeats: list[dict[str, float]] = []
        repeat_all_ok = True
        if gain is not None and 1.03 <= gain <= 1.07:
            repeat_start = time.monotonic()
            with ProcessPoolExecutor(max_workers=workers) as pool:
                repeat_rows = list(
                    pool.map(_capacity_job, range(CAPACITY_JOBS_PER_RUNG))
                )
            repeat_wall = time.monotonic() - repeat_start
            repeat_throughput = len(repeat_rows) / max(repeat_wall, 1.0e-12)
            repeats.append(
                {
                    "wall_seconds": repeat_wall,
                    "throughput_jobs_per_second": repeat_throughput,
                }
            )
            repeat_all_ok = all(item["ok"] for item in repeat_rows)
            throughput = (throughput + repeat_throughput) / 2.0
            gain = throughput / previous_accepted_throughput
        all_ok = all(row["ok"] for row in rows) and repeat_all_ok
        accepted = bool(
            accepting
            and all_ok
            and memory_safe
            and (gain is None or gain >= 1.05)
        )
        if accepted:
            selected = workers
            previous_accepted_throughput = throughput
        else:
            accepting = False
        rungs.append(
            {
                "workers": workers,
                "jobs": len(rows),
                "wall_seconds": wall,
                "throughput_jobs_per_second": throughput,
                "marginal_gain": gain,
                "memory_safe": memory_safe,
                "all_ok": all_ok,
                "accepted": accepted,
                "repeats": repeats,
            }
        )
    selected_row = next(
        (row for row in rungs if row["workers"] == selected),
        {"throughput_jobs_per_second": 0.0},
    )
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "authority": checks,
        "rungs": rungs,
        "jobs_per_rung": CAPACITY_JOBS_PER_RUNG,
        "selected_workers": selected,
        "selected_throughput_jobs_per_second": selected_row[
            "throughput_jobs_per_second"
        ],
        "worker_rss_floor_bytes": WORKER_RSS_FLOOR_BYTES,
        "os_floor_bytes": OS_FLOOR_BYTES,
        "wsl_mem_total_bytes": int(mem["MemTotal"]),
        "wsl_mem_available_bytes": int(mem["MemAvailable"]),
        "other_python_processes": other,
        "other_reserved_processes": 0,
        "host_process_budget": selected + 1,
        "wsl_python_processes": selected + 1,
        "native_threads_per_process": 1,
        "estimated_formal_seconds": 8_424
        / max(float(selected_row["throughput_jobs_per_second"]), 1.0e-12),
        "readiness": "RUN-READY" if selected > 0 and not other else "LOAD-CHECK-REVIEW",
    }
    digest = _write_new_json(CAPACITY, payload)
    return json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True)


def rehearsal() -> str:
    _assert_wsl_scratch()
    checks = authority_checks()
    rows = candidates()
    k5_schedules = [
        tuple(tuple(pair) for pair in row["schedule"])
        for row in rows
        if int(row["k"]) == 5
    ]
    chunks = candidate_chunks()
    parent_sequence = capture_parent_candidate_sequence()
    static_fixture = {
        "disturbance_differential_energy": 1.0,
        "off_diagonal_response_energy": 1.0,
        "common_frequency_iae_hz_s": 1.0,
        "worst_unit_peak_hz": 1.0,
        "worst_rocof_hz_s": 1.0,
        "action_rms": 1.0,
        "action_total_variation": 1.0,
        "action_saturation_fraction": 0.0,
        "valid": True,
    }
    boundary_fixture = {
        **static_fixture,
        "disturbance_differential_energy": 0.95,
        "off_diagonal_response_energy": 0.95,
        "common_frequency_iae_hz_s": 1.03,
        "worst_unit_peak_hz": 1.03,
        "worst_rocof_hz_s": 1.03,
        "action_rms": 1.10,
        "action_total_variation": 1.10,
        "action_saturation_fraction": 0.05,
    }
    boundary_guard = candidate_guard(boundary_fixture, static_fixture)
    tied = [
        {"id": "a", "objectives": [1.0, 1.0, 1.0, 1.0]},
        {"id": "b", "objectives": [1.0, 1.0, 1.0, 1.0]},
    ]
    profile = R439._profiles()[0]
    scenario = R439._evaluation_scenarios(profile)[0]
    static_record = R439._run_trajectory(
        profile, scenario, static_arm=STATIC_SELECTED
    )
    candidate_record = R439._run_trajectory(
        profile, scenario, timevarying=_schedule_tuple(rows[0])
    )
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "formal_authority": False,
        "training_executed": False,
        "authority": checks,
        "runtime": installed_runtime(),
        "generator": {
            "counts": dict(Counter(str(row["k"]) for row in rows)),
            "total": len(rows),
            "sequence_sha256": candidate_sequence_sha256(),
            "k5_unique_schedules": len(set(k5_schedules)),
            "k5_duplicate_rows": len(k5_schedules) - len(set(k5_schedules)),
            "parent_path_exact_match": parent_sequence
            == [row["schedule"] for row in rows],
        },
        "chunks": {
            "count": len(chunks),
            "sizes": [len(chunk) for chunk in chunks],
            "covered_global_indices": [
                int(row["global_index"]) for chunk in chunks for row in chunk
            ],
        },
        "guard_boundary": boundary_guard,
        "pareto_tie_ids": [row["id"] for row in nondominated(tied)],
        "physical": {
            "static_completed": bool(static_record.get("completed")),
            "static_steps": int(static_record.get("completed_steps", 0)),
            "candidate_completed": bool(candidate_record.get("completed")),
            "candidate_steps": int(candidate_record.get("completed_steps", 0)),
            "static_identity": static_record.get("identity"),
            "candidate_identity": candidate_record.get("identity"),
        },
    }
    payload["passed"] = bool(
        all(checks.values())
        and payload["generator"]
        == {
            "counts": {"2": 25, "3": 125, "5": 200},
            "total": 350,
            "sequence_sha256": EXPECTED_CANDIDATE_SHA256,
            "k5_unique_schedules": 192,
            "k5_duplicate_rows": 8,
            "parent_path_exact_match": True,
        }
        and payload["chunks"]["count"] == CHUNKS_PER_PROFILE
        and payload["chunks"]["covered_global_indices"] == list(range(350))
        and boundary_guard["joint_guard_feasible"]
        and payload["pareto_tie_ids"] == ["a", "b"]
        and payload["physical"]["static_completed"]
        and payload["physical"]["candidate_completed"]
        and payload["physical"]["static_steps"] == int(build_contract()["steps"])
        and payload["physical"]["candidate_steps"] == int(build_contract()["steps"])
        and payload["physical"]["static_identity"]
        == payload["physical"]["candidate_identity"]
    )
    digest = _write_new_json(REHEARSAL, payload)
    return json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True)


def prepare() -> str:
    _assert_wsl_scratch()
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed: {checks}")
    rehearsal_payload = _read_hashed_json(REHEARSAL)
    if not rehearsal_payload.get("passed"):
        raise RuntimeError("rehearsal did not pass")
    capacity = _read_hashed_json(CAPACITY)
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError(f"capacity not RUN-READY: {capacity.get('readiness')}")
    selected = int(capacity["selected_workers"])
    if selected != 16:
        raise RuntimeError(
            f"measured workers={selected}; update the prospective plan budget before seal"
        )
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r452_m5_all_candidate_pareto.py",
        "r439_runner": R439_RUNNER,
        "r441_runner": R441_RUNNER,
        "summary": ROOT / "src/andes_rl_kundur/evaluation/md_decoupling_headroom.py",
        "v4_environment": ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
    }
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(),
        "plan_sha256": _sha256_file(PLAN),
        "authority": checks,
        "runtime": rehearsal_payload["runtime"],
        "capacity_sha256": _sha256_file(CAPACITY),
        "rehearsal_sha256": _sha256_file(REHEARSAL),
        "launch": {
            "host_process_budget": selected + 1,
            "wsl_python_processes": selected + 1,
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
            "execution_shards": len(expected_shard_ids()),
        },
        "sources": {
            name: {"path": _relative(path), "sha256": _sha256_file(path)}
            for name, path in sources.items()
        },
        "formal_authority": True,
        "training_executed": False,
    }
    digest = _write_new_json(SEAL, seal)
    SHARDS.parent.mkdir(parents=True, exist_ok=True)
    SHARDS.write_text(json.dumps(expected_shard_ids()) + "\n", encoding="utf-8")
    return json.dumps(
        {
            "seal_sha256": digest,
            "selected_workers": selected,
            "execution_shards": len(expected_shard_ids()),
            "estimated_formal_seconds": capacity["estimated_formal_seconds"],
        },
        indent=2,
        sort_keys=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("capacity", "rehearse", "prepare", "shard", "aggregate")
    )
    parser.add_argument("shard_id", nargs="?")
    args = parser.parse_args()
    if args.command == "capacity":
        print(measure_capacity(), flush=True)
    elif args.command == "rehearse":
        print(rehearsal(), flush=True)
    elif args.command == "prepare":
        print(prepare(), flush=True)
    elif args.command == "aggregate":
        print(aggregate(), flush=True)
    else:
        if args.shard_id is None:
            raise SystemExit("shard requires kind|profile|chunk")
        print(run_shard(args.shard_id), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
