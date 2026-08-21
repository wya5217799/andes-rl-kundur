"""R453 — repair R452 M5 aggregation semantics from immutable shards."""
from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from memory.tools.artifact_io import (  # noqa: E402
    payload_sha256,
    read_verified_json,
    sha256_file,
    write_new_json,
)

ROUND = "R453"
PARENT_ROUND = "R452"
PROFILE_IDS = ("eval_a", "eval_b", "eval_c", "eval_d")
PARENT_OUT = ROOT / "results/research_loop/r452_m5_all_candidate_pareto"
PARENT_SHARDS = PARENT_OUT / "shards"
PARENT_SEAL = ROOT / "memory/rounds/R452/formal_seal.json"
PARENT_AUDIT = ROOT / "memory/rounds/R452/algorithm_audit.json"
PARENT_AUDIT_SHA256 = (
    "6d692e72a8e0d160fc3bcd69eb16e0412c4d0a69c86f2d7d4e5a9dc48b07d723"
)
EXPECTED_CANDIDATE_SHA256 = (
    "6f505fa569e5a22d8163da44a38292fecc433180cff7640fce6fff4984433962"
)
PLAN = ROOT / "memory/rounds/R453/plan.md"
REHEARSAL = ROOT / "memory/rounds/R453/rehearsal.json"
SEAL = ROOT / "memory/rounds/R453/formal_seal.json"
RUNNER = ROOT / "scripts/run_r453_m5_aggregate_repair.py"
RUNNER_TEST = ROOT / "tests/test_run_r453_m5_aggregate_repair.py"
OUT = ROOT / "results/research_loop/r453_m5_aggregate_repair"
FORMAL = OUT / "formal_analysis.json"

IMPROVEMENT_MIN = 0.05
COMMON_RATIO_MAX = 1.03
ACTION_RATIO_MAX = 1.10
SATURATION_MAX = 0.05


def expected_shard_paths() -> list[Path]:
    paths: list[Path] = []
    for profile_id in PROFILE_IDS:
        paths.extend(
            PARENT_SHARDS / profile_id / f"candidate_{index:02d}.json"
            for index in range(16)
        )
        paths.append(PARENT_SHARDS / profile_id / "static.json")
    return paths


def _is_finite(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, Mapping):
        return all(_is_finite(item) for item in value.values())
    if isinstance(value, Sequence):
        return all(_is_finite(item) for item in value)
    return True


def candidate_guard(
    summary: Mapping[str, Any], static: Mapping[str, Any]
) -> dict[str, Any]:
    action_rms_ratio = float(summary["action_rms"]) / max(
        float(static["action_rms"]), 1.0e-12
    )
    action_tv_ratio = float(summary["action_total_variation"]) / max(
        float(static["action_total_variation"]), 1.0e-12
    )
    disturbance_improvement = (
        float(static["disturbance_differential_energy"])
        - float(summary["disturbance_differential_energy"])
    ) / max(float(static["disturbance_differential_energy"]), 1.0e-12)
    off_diagonal_improvement = (
        float(static["off_diagonal_response_energy"])
        - float(summary["off_diagonal_response_energy"])
    ) / max(float(static["off_diagonal_response_energy"]), 1.0e-12)
    endpoint = {
        "disturbance_improvement": disturbance_improvement,
        "off_diagonal_improvement": off_diagonal_improvement,
        "disturbance_eligible": disturbance_improvement
        >= IMPROVEMENT_MIN - 1.0e-15,
        "off_diagonal_eligible": off_diagonal_improvement
        >= IMPROVEMENT_MIN - 1.0e-15,
    }
    common = {
        "common_frequency_iae_no_harm": float(
            summary["common_frequency_iae_hz_s"]
        )
        <= COMMON_RATIO_MAX * float(static["common_frequency_iae_hz_s"]),
        "worst_peak_no_harm": float(summary["worst_unit_peak_hz"])
        <= COMMON_RATIO_MAX * float(static["worst_unit_peak_hz"]),
        "rocof_no_harm": float(summary["worst_rocof_hz_s"])
        <= COMMON_RATIO_MAX * float(static["worst_rocof_hz_s"]),
    }
    action = {
        "action_rms_no_harm": action_rms_ratio <= ACTION_RATIO_MAX,
        "action_variation_no_harm": action_tv_ratio <= ACTION_RATIO_MAX,
    }
    valid = bool(static.get("valid") is True and summary.get("valid") is True)
    joint_endpoint = bool(
        endpoint["disturbance_eligible"] and endpoint["off_diagonal_eligible"]
    )
    common_clean = all(common.values())
    action_clean = all(action.values())
    saturation = bool(
        float(summary["action_saturation_fraction"]) <= SATURATION_MAX + 1.0e-15
    )
    return {
        "valid": valid,
        "endpoint": endpoint,
        "joint_endpoint_eligible": joint_endpoint,
        "valid_endpoint_eligible": bool(valid and joint_endpoint),
        "common_no_harm": common,
        "common_clean": common_clean,
        "action_stress_no_harm": action,
        "action_clean": action_clean,
        "saturation_pass": saturation,
        "joint_guard_feasible": bool(
            valid and joint_endpoint and common_clean and action_clean and saturation
        ),
    }


def objectives(
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
    if not all(_is_finite(row["objectives"]) for row in material):
        raise RuntimeError("nonfinite Pareto objective")
    return [
        row
        for index, row in enumerate(material)
        if not any(
            other_index != index
            and _dominates(other["objectives"], row["objectives"])
            for other_index, other in enumerate(material)
        )
    ]


def _minimum(rows: Sequence[Mapping[str, Any]], metric: str) -> dict[str, Any] | None:
    if not rows:
        return None
    row = min(
        rows,
        key=lambda item: (float(item["summary"][metric]), int(item["global_index"])),
    )
    return {
        "candidate_id": row["candidate_id"],
        "value": float(row["summary"][metric]),
        "ratio_to_static": float(row["objectives"][2 if metric == "action_rms" else 3]),
        "genuinely_varying": bool(row["genuinely_varying"]),
    }


def summarize_profile(
    profile_id: str,
    static: Mapping[str, Any],
    raw_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for raw in sorted(raw_rows, key=lambda item: int(item["global_index"])):
        if raw.get("errors") or not isinstance(raw.get("summary"), Mapping):
            raise RuntimeError(f"{profile_id} {raw.get('candidate_id')} invalid row")
        summary = raw["summary"]
        if not _is_finite(summary):
            raise RuntimeError(f"{profile_id} {raw['candidate_id']} nonfinite summary")
        guard = candidate_guard(summary, static)
        rows.append(
            {
                "candidate_id": raw["candidate_id"],
                "global_index": int(raw["global_index"]),
                "k": int(raw["k"]),
                "schedule": raw["schedule"],
                "genuinely_varying": bool(raw["genuinely_varying"]),
                "summary": summary,
                "guards": guard,
                "objectives": list(objectives(summary, static)),
            }
        )
    if len(rows) != 350 or [row["global_index"] for row in rows] != list(range(350)):
        raise RuntimeError(f"{profile_id} candidate inventory is incomplete")
    if len({row["candidate_id"] for row in rows}) != 350:
        raise RuntimeError(f"{profile_id} candidate IDs are not unique")

    endpoint_only = [row for row in rows if row["guards"]["joint_endpoint_eligible"]]
    valid_endpoint = [row for row in rows if row["guards"]["valid_endpoint_eligible"]]
    pareto_source = [
        row
        for row in rows
        if row["guards"]["valid"]
        and row["guards"]["common_clean"]
        and row["guards"]["saturation_pass"]
    ]
    pareto = nondominated(pareto_source)
    return {
        "schema_version": 1,
        "round": ROUND,
        "profile_id": profile_id,
        "static": static,
        "candidate_count": len(rows),
        "candidate_rows": rows,
        "joint_endpoint_eligible_count": len(endpoint_only),
        "valid_joint_endpoint_eligible_count": len(valid_endpoint),
        "joint_guard_feasible_ids": [
            row["candidate_id"]
            for row in rows
            if row["guards"]["joint_guard_feasible"]
        ],
        "conditional_minima": {
            population: {
                "action_rms": _minimum(population_rows, "action_rms"),
                "action_total_variation": _minimum(
                    population_rows, "action_total_variation"
                ),
            }
            for population, population_rows in (
                ("endpoint_only", endpoint_only),
                ("valid_endpoint", valid_endpoint),
            )
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


def verify_parent() -> dict[str, Any]:
    seal, seal_sha = read_verified_json(PARENT_SEAL)
    audit, audit_sha = read_verified_json(PARENT_AUDIT, PARENT_AUDIT_SHA256)
    if seal.get("round") != PARENT_ROUND or seal.get("formal_authority") is not True:
        raise RuntimeError("R452 seal authority mismatch")
    if audit.get("finding", {}).get("classification") != "CANARY-INVALID":
        raise RuntimeError("R452 audit does not record CANARY-INVALID")
    for entry in (seal.get("sources") or {}).values():
        path = ROOT / entry["path"]
        if sha256_file(path) != entry["sha256"]:
            raise RuntimeError(f"R452 sealed source drift: {entry['path']}")

    expected = expected_shard_paths()
    actual = sorted(PARENT_SHARDS.glob("*/*.json"))
    if {path.resolve() for path in actual} != {path.resolve() for path in expected}:
        raise RuntimeError("R452 shard file inventory mismatch")
    profiles: dict[str, dict[str, Any]] = {}
    total_trajectories = 0
    for profile_id in PROFILE_IDS:
        raw_rows: list[dict[str, Any]] = []
        for index in range(16):
            path = PARENT_SHARDS / profile_id / f"candidate_{index:02d}.json"
            payload, _ = read_verified_json(path)
            if (
                payload.get("round") != PARENT_ROUND
                or payload.get("profile_id") != profile_id
                or payload.get("shard_id") != f"candidate|{profile_id}|{index:02d}"
                or payload.get("valid_execution") is not True
                or payload.get("errors")
                or payload.get("contract_sha256") != seal.get("contract_sha256")
            ):
                raise RuntimeError(f"invalid R452 candidate shard: {path}")
            raw_rows.extend(payload["rows"])
            total_trajectories += int(payload["trajectory_count"])
        static_path = PARENT_SHARDS / profile_id / "static.json"
        static_payload, _ = read_verified_json(static_path)
        if (
            static_payload.get("round") != PARENT_ROUND
            or static_payload.get("profile_id") != profile_id
            or static_payload.get("shard_id") != f"static|{profile_id}|00"
            or static_payload.get("valid_execution") is not True
            or static_payload.get("errors")
            or static_payload.get("contract_sha256") != seal.get("contract_sha256")
        ):
            raise RuntimeError(f"invalid R452 static shard: {static_path}")
        total_trajectories += int(static_payload["trajectory_count"])
        profiles[profile_id] = summarize_profile(
            profile_id, static_payload["summary"], raw_rows
        )

    reference = [
        {
            key: row[key]
            for key in ("candidate_id", "global_index", "k", "schedule")
        }
        for row in profiles[PROFILE_IDS[0]]["candidate_rows"]
    ]
    if payload_sha256(reference) != EXPECTED_CANDIDATE_SHA256:
        raise RuntimeError("R452 candidate sequence hash mismatch")
    for profile_id in PROFILE_IDS[1:]:
        other = [
            {
                key: row[key]
                for key in ("candidate_id", "global_index", "k", "schedule")
            }
            for row in profiles[profile_id]["candidate_rows"]
        ]
        if other != reference:
            raise RuntimeError(f"candidate sequence differs for {profile_id}")
    if total_trajectories != 8424:
        raise RuntimeError(f"R452 trajectory count {total_trajectories} != 8424")
    return {
        "seal_sha256": seal_sha,
        "audit_sha256": audit_sha,
        "contract_sha256": seal["contract_sha256"],
        "execution_shards": len(expected),
        "total_trajectories": total_trajectories,
        "profiles": profiles,
    }


def _compare_parent_profiles(profiles: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    comparisons: dict[str, Any] = {}
    for profile_id, payload in profiles.items():
        parent, digest = read_verified_json(PARENT_OUT / "profiles" / f"{profile_id}.json")
        parent_pareto_ids = [row["candidate_id"] for row in parent["pareto"]]
        current_pareto_ids = [row["candidate_id"] for row in payload["pareto"]]
        comparison = {
            "parent_profile_sha256": digest,
            "candidate_rows_match": parent["candidate_rows"]
            == [
                {
                    key: row[key]
                    for key in (
                        "candidate_id",
                        "global_index",
                        "k",
                        "schedule",
                        "genuinely_varying",
                        "summary",
                        "guards",
                        "objectives",
                    )
                    if not (key == "guards")
                }
                | {
                    "guards": {
                        key: value
                        for key, value in row["guards"].items()
                        if key != "valid_endpoint_eligible"
                    }
                }
                for row in payload["candidate_rows"]
            ],
            "joint_guard_feasible_ids_match": parent["joint_guard_feasible_ids"]
            == payload["joint_guard_feasible_ids"],
            "pareto_ids_match": parent_pareto_ids == current_pareto_ids,
            "parent_stored_count": parent["joint_endpoint_eligible_count"],
            "repaired_endpoint_only_count": payload["joint_endpoint_eligible_count"],
            "explicit_valid_endpoint_count": payload[
                "valid_joint_endpoint_eligible_count"
            ],
        }
        if not all(
            comparison[key]
            for key in (
                "candidate_rows_match",
                "joint_guard_feasible_ids_match",
                "pareto_ids_match",
            )
        ):
            raise RuntimeError(f"R452 parent comparison failed for {profile_id}")
        comparisons[profile_id] = comparison
    return comparisons


def _pure_probes() -> dict[str, Any]:
    static = {
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
    invalid_but_endpoint = {
        **static,
        "disturbance_differential_energy": 0.95,
        "off_diagonal_response_energy": 0.95,
        "action_rms": 0.5,
        "valid": False,
    }
    valid_endpoint = {**invalid_but_endpoint, "action_rms": 0.8, "valid": True}
    invalid_guard = candidate_guard(invalid_but_endpoint, static)
    valid_guard = candidate_guard(valid_endpoint, static)
    tied = nondominated(
        [
            {"candidate_id": "a", "objectives": [1.0, 1.0, 1.0, 1.0]},
            {"candidate_id": "b", "objectives": [1.0, 1.0, 1.0, 1.0]},
        ]
    )
    return {
        "invalid_endpoint_only_true": invalid_guard["joint_endpoint_eligible"],
        "invalid_valid_endpoint_false": not invalid_guard["valid_endpoint_eligible"],
        "valid_endpoint_true": valid_guard["valid_endpoint_eligible"],
        "pareto_tie_ids": [row["candidate_id"] for row in tied],
    }


def rehearse() -> int:
    if OUT.exists() or REHEARSAL.exists() or SEAL.exists():
        raise FileExistsError("R453 rehearsal requires absent output/rehearsal/seal")
    parent = verify_parent()
    probes = _pure_probes()
    if not (
        probes["invalid_endpoint_only_true"]
        and probes["invalid_valid_endpoint_false"]
        and probes["valid_endpoint_true"]
        and probes["pareto_tie_ids"] == ["a", "b"]
    ):
        raise RuntimeError("R453 pure rehearsal probes failed")
    payload = {
        "schema_version": 1,
        "round": ROUND,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "rehearsal_ok": True,
        "formal_output_absent": True,
        "parent": {
            key: parent[key]
            for key in (
                "seal_sha256",
                "audit_sha256",
                "contract_sha256",
                "execution_shards",
                "total_trajectories",
            )
        },
        "source_sha256": sha256_file(RUNNER),
        "probes": probes,
    }
    digest = write_new_json(REHEARSAL, payload)
    print(digest)
    return 0


def seal() -> int:
    if OUT.exists() or SEAL.exists():
        raise FileExistsError("R453 seal requires absent formal output and seal")
    rehearsal, rehearsal_sha = read_verified_json(REHEARSAL)
    if rehearsal.get("rehearsal_ok") is not True:
        raise RuntimeError("R453 rehearsal did not pass")
    parent = verify_parent()
    payload = {
        "schema_version": 1,
        "round": ROUND,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "formal_authority": True,
        "training_executed": False,
        "physical_execution_reused_from": PARENT_ROUND,
        "plan_sha256": sha256_file(PLAN),
        "rehearsal_sha256": rehearsal_sha,
        "parent_seal_sha256": parent["seal_sha256"],
        "parent_audit_sha256": parent["audit_sha256"],
        "sources": {
            "runner": {"path": str(RUNNER.relative_to(ROOT)), "sha256": sha256_file(RUNNER)},
            "runner_test": {
                "path": str(RUNNER_TEST.relative_to(ROOT)),
                "sha256": sha256_file(RUNNER_TEST),
            },
        },
    }
    digest = write_new_json(SEAL, payload)
    print(digest)
    return 0


def _load_seal() -> tuple[dict[str, Any], str]:
    seal_payload, digest = read_verified_json(SEAL)
    if seal_payload.get("round") != ROUND or seal_payload.get("formal_authority") is not True:
        raise RuntimeError("R453 seal authority mismatch")
    for entry in seal_payload["sources"].values():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"R453 sealed source drift: {entry['path']}")
    if sha256_file(PLAN) != seal_payload["plan_sha256"]:
        raise RuntimeError("R453 plan drifted after seal")
    if read_verified_json(REHEARSAL)[1] != seal_payload["rehearsal_sha256"]:
        raise RuntimeError("R453 rehearsal drifted after seal")
    return seal_payload, digest


def execute() -> int:
    if OUT.exists():
        raise FileExistsError(f"create-only output already exists: {OUT}")
    seal_payload, seal_sha = _load_seal()
    parent = verify_parent()
    profiles = parent.pop("profiles")
    comparisons = _compare_parent_profiles(profiles)
    feasible_profiles = [
        profile_id
        for profile_id, payload in profiles.items()
        if payload["joint_guard_feasible_ids"]
    ]
    if len(feasible_profiles) == 4:
        verdict = "GUARD-CLEAN-JOINT-HEADROOM-IN-GRID"
    elif feasible_profiles:
        verdict = "PARTIAL-GUARD-CLEAN-JOINT-HEADROOM-IN-GRID"
    else:
        verdict = "NO-GUARD-CLEAN-JOINT-HEADROOM-IN-GRID"

    profile_digests: dict[str, str] = {}
    for profile_id, payload in profiles.items():
        profile_digests[profile_id] = write_new_json(
            OUT / "profiles" / f"{profile_id}.json", payload
        )
    analysis = {
        "schema_version": 1,
        "round": ROUND,
        "formal_authority": True,
        "training_executed": False,
        "physical_execution_reused_from": PARENT_ROUND,
        "seal_sha256": seal_sha,
        "integrity": {
            "valid": True,
            "execution_shards": parent["execution_shards"],
            "candidate_rows": 1400,
            "candidate_trajectories": 8400,
            "static_trajectories": 24,
            "candidate_sequence_sha256": EXPECTED_CANDIDATE_SHA256,
            "parent_contract_sha256": parent["contract_sha256"],
            "parent_seal_sha256": parent["seal_sha256"],
            "parent_audit_sha256": parent["audit_sha256"],
        },
        "population_semantics": {
            "joint_endpoint_eligible_count": "both endpoint improvements >=5%, regardless of valid flag",
            "valid_joint_endpoint_eligible_count": "endpoint-only population intersected with full valid flag",
            "conditional_minima": "reported separately for endpoint_only and valid_endpoint populations",
        },
        "parent_comparison": comparisons,
        "profiles": {
            profile_id: {
                "candidate_count": payload["candidate_count"],
                "joint_endpoint_eligible_count": payload[
                    "joint_endpoint_eligible_count"
                ],
                "valid_joint_endpoint_eligible_count": payload[
                    "valid_joint_endpoint_eligible_count"
                ],
                "joint_guard_feasible_ids": payload["joint_guard_feasible_ids"],
                "conditional_minima": payload["conditional_minima"],
                "pareto_count": len(payload["pareto"]),
                "pareto_ids": [row["candidate_id"] for row in payload["pareto"]],
                "profile_sha256": profile_digests[profile_id],
            }
            for profile_id, payload in profiles.items()
        },
        "classification": {
            "profiles_with_guard_clean_joint_headroom": feasible_profiles,
            "profile_count": len(feasible_profiles),
            "verdict": verdict,
        },
        "seal": {
            "formal_authority": seal_payload["formal_authority"],
            "physical_execution_reused_from": seal_payload[
                "physical_execution_reused_from"
            ],
        },
    }
    digest = write_new_json(FORMAL, analysis)
    print(digest)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("rehearse", "seal", "execute"))
    args = parser.parse_args(argv)
    try:
        return {"rehearse": rehearse, "seal": seal, "execute": execute}[
            args.mode
        ]()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
