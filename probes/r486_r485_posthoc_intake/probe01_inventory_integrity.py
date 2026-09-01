"""PROTOTYPE: independently audit the sealed R485 inventory and lineage.

Question: can missing, duplicate, corrupt, or cross-round artifacts manufacture
the reported 0/208 complete-contract result?  This script is read-only.  It
streams one evaluation JSON at a time and writes only a recomputable summary.

Usage:
  python tmp/yang-md-decoupling-marl/r485_prepaper_audit/probe01_inventory_integrity.py --self-check
  python tmp/yang-md-decoupling-marl/r485_prepaper_audit/probe01_inventory_integrity.py --output <path>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
ROUND_DIR = ROOT / "memory" / "rounds" / "R485"
ATTEMPT = (
    ROOT
    / "results"
    / "research_loop"
    / "r485_60hz_source_factorial"
    / "r485-formal-20260829-a"
)


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json_bytes(path: Path) -> tuple[dict[str, Any], bytes]:
    data = path.read_bytes()
    return json.loads(data), data


def duplicate_keys(keys: list[tuple[Any, ...]]) -> list[tuple[Any, ...]]:
    return [key for key, count in Counter(keys).items() if count != 1]


def negative_control() -> dict[str, bool]:
    keys = [("same", "arm", 501, "profile", "scenario")]
    duplicated = keys + [keys[0]]
    expected = digest_bytes(b"sealed")
    corrupted = digest_bytes(b"sealed-corrupted")
    result = {
        "duplicate_detected": bool(duplicate_keys(duplicated)),
        "hash_corruption_detected": corrupted != expected,
    }
    if not all(result.values()):
        raise AssertionError(f"negative control failed: {result}")
    return result


def load_sidecar_map() -> tuple[dict[Path, str], list[str]]:
    targets: dict[Path, str] = {}
    errors: list[str] = []
    for sidecar in sorted(ATTEMPT.rglob("*.sha256")):
        parts = sidecar.read_text(encoding="ascii").strip().split()
        target = sidecar.with_suffix("")
        if len(parts) != 2:
            errors.append(f"malformed sidecar: {sidecar.relative_to(ROOT)}")
            continue
        expected, named = parts
        if named != target.name:
            errors.append(
                f"sidecar target mismatch: {sidecar.relative_to(ROOT)} -> {named}"
            )
        if not target.is_file():
            errors.append(f"sidecar target missing: {target.relative_to(ROOT)}")
            continue
        targets[target.resolve()] = expected.lower()
    return targets, errors


def run() -> dict[str, Any]:
    started = time.time()
    config = json.loads((ROUND_DIR / "config.json").read_text(encoding="utf-8"))
    seal = json.loads((ROUND_DIR / "formal_seal.json").read_text(encoding="utf-8"))
    card = json.loads(
        (ROUND_DIR / "resolved_parameter_card.json").read_text(encoding="utf-8")
    )
    expected_card = seal["resolved_parameter_card_sha256"]
    arms = tuple(config["arms"])
    seeds = tuple(config["formal_seeds"])
    errors: list[str] = []
    checked: set[Path] = set()
    sidecars, sidecar_errors = load_sidecar_map()
    errors.extend(sidecar_errors)

    def check_data(path: Path, data: bytes, embedded: str | None = None) -> str:
        resolved = path.resolve()
        actual = digest_bytes(data)
        sidecar_hash = sidecars.get(resolved)
        if sidecar_hash is not None and actual != sidecar_hash:
            errors.append(f"sidecar hash mismatch: {path.relative_to(ROOT)}")
        if embedded is not None and actual != embedded:
            errors.append(f"embedded hash mismatch: {path.relative_to(ROOT)}")
        checked.add(resolved)
        return actual

    def check_file(path: Path, embedded: str | None = None) -> str:
        resolved = path.resolve()
        actual = digest_file(path)
        sidecar_hash = sidecars.get(resolved)
        if sidecar_hash is not None and actual != sidecar_hash:
            errors.append(f"sidecar hash mismatch: {path.relative_to(ROOT)}")
        if embedded is not None and actual != embedded:
            errors.append(f"embedded hash mismatch: {path.relative_to(ROOT)}")
        checked.add(resolved)
        return actual

    # Windows execution hashes bind working-tree bytes, whose line endings can
    # differ from normalized Git blobs.  Bind seal -> both reviews by exact
    # hash, then require no semantic Git diff from review to seal commit.
    reviewed_commit = seal["reviewed_commit"]
    review_a = json.loads((ROUND_DIR / "code_review_a.json").read_text(encoding="utf-8"))
    review_b = json.loads((ROUND_DIR / "code_review_b.json").read_text(encoding="utf-8"))
    seal_commit = subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", "memory/rounds/R485/formal_seal.json"],
        cwd=ROOT,
        text=True,
    ).strip()
    source_mismatches: list[str] = []
    for item in seal["sources"].values():
        path = item["path"]
        if (
            review_a["reviewed_files"].get(path) != item["sha256"]
            or review_b["reviewed_files"].get(path) != item["sha256"]
            or subprocess.run(
                ["git", "diff", "--quiet", reviewed_commit, seal_commit, "--", path],
                cwd=ROOT,
                check=False,
            ).returncode
            != 0
        ):
            source_mismatches.append(path)
    errors.extend(f"sealed source mismatch: {path}" for path in source_mismatches)

    base_keys: list[tuple[int]] = []
    base_hashes: dict[int, tuple[str, str]] = {}
    base_files = sorted((ATTEMPT / "bases").glob("seed*/manifest.json"))
    for path in base_files:
        manifest, data = read_json_bytes(path)
        manifest_hash = check_data(path, data)
        seed = manifest["seed"]
        base_state = Path(manifest["base_state"]["path"])
        if not base_state.is_absolute():
            base_state = ROOT / base_state
        base_state_hash = check_file(base_state, manifest["base_state"]["sha256"])
        base_keys.append((seed,))
        base_hashes[seed] = (manifest_hash, base_state_hash)
        if (manifest["round"], manifest["scope"]) != ("R485", "formal"):
            errors.append(f"base identity mismatch: {path.relative_to(ROOT)}")
        if manifest["resolved_parameter_card_sha256"] != expected_card:
            errors.append(f"base card mismatch: {path.relative_to(ROOT)}")

    train_keys: list[tuple[str, int]] = []
    train_lineage: dict[tuple[str, int], dict[str, str]] = {}
    train_files = sorted((ATTEMPT / "train").glob("*/seed*/manifest.json"))
    for path in train_files:
        manifest, data = read_json_bytes(path)
        manifest_hash = check_data(path, data)
        arm = path.parent.parent.name
        seed = int(path.parent.name.removeprefix("seed"))
        train_keys.append((arm, seed))
        if (manifest["arm_id"], manifest["seed"]) != (arm, seed):
            errors.append(f"training path/schema mismatch: {path.relative_to(ROOT)}")
        if (manifest["round"], manifest["scope"], manifest["valid"]) != (
            "R485",
            "formal",
            True,
        ):
            errors.append(f"training validity mismatch: {path.relative_to(ROOT)}")
        if manifest["resolved_parameter_card_sha256"] != expected_card:
            errors.append(f"training card mismatch: {path.relative_to(ROOT)}")
        if manifest["interaction_steps"] != config["training"]["interaction_steps"]:
            errors.append(f"training budget mismatch: {path.relative_to(ROOT)}")
        expected_base_manifest, expected_base_state = base_hashes.get(seed, (None, None))
        if manifest["base_manifest_sha256"] != expected_base_manifest:
            errors.append(f"training base-manifest mismatch: {path.relative_to(ROOT)}")
        if manifest["base_state_sha256"] != expected_base_state:
            errors.append(f"training base-state mismatch: {path.relative_to(ROOT)}")
        final_hash = check_file(path.parent / "final.pt", manifest["final_checkpoint_sha256"])
        check_file(path.parent / "half.pt", manifest["half_checkpoint_sha256"])
        check_file(path.parent / "curves.npz", manifest["curves_sha256"])
        train_lineage[(arm, seed)] = {
            "manifest": manifest_hash,
            "checkpoint": final_hash,
            "base_manifest": manifest["base_manifest_sha256"],
        }

    evaluation_keys: list[tuple[str, str, int | None, str]] = []
    trajectory_keys: list[tuple[Any, ...]] = []
    learned_files = 0
    deterministic_files = 0
    completed_trajectories = 0
    eval_files = sorted((ATTEMPT / "eval").rglob("*.json"))
    for path in eval_files:
        payload, data = read_json_bytes(path)
        check_data(path, data)
        records = payload.get("records")
        if not isinstance(records, list) or len(records) != 6:
            errors.append(f"evaluation record count mismatch: {path.relative_to(ROOT)}")
            continue
        rel = path.relative_to(ATTEMPT / "eval")
        bank = rel.parts[0]
        deterministic = "deterministic" in rel.parts
        if deterministic:
            deterministic_files += 1
            arm = records[0]["arm_id"]
            seed = None
        else:
            learned_files += 1
            arm = rel.parts[1]
            seed = int(rel.parts[2].removeprefix("seed"))
        profile = path.stem
        evaluation_keys.append((bank, arm, seed, profile))
        seen_scenarios: set[str] = set()
        for record in records:
            completed_trajectories += 1
            scenario = record["scenario_id"]
            seen_scenarios.add(scenario)
            trajectory_keys.append((bank, arm, seed, profile, scenario))
            if (record["round"], record["scope"], record["bank"]) != (
                "R485",
                "formal",
                bank,
            ):
                errors.append(f"evaluation identity mismatch: {path.relative_to(ROOT)}")
            if record["profile_id"] != profile:
                errors.append(f"profile mismatch: {path.relative_to(ROOT)}")
            if record["resolved_parameter_card_sha256"] != expected_card:
                errors.append(f"evaluation card mismatch: {path.relative_to(ROOT)}")
            if not record["completed"] or record["tds_failed"]:
                errors.append(f"incomplete evaluation: {path.relative_to(ROOT)}#{scenario}")
            if record["completed_steps"] != config["evaluation"]["steps"]:
                errors.append(f"evaluation horizon mismatch: {path.relative_to(ROOT)}#{scenario}")
            if len(record["steps"]) != config["evaluation"]["steps"]:
                errors.append(f"saved-step mismatch: {path.relative_to(ROOT)}#{scenario}")
            if not deterministic:
                lineage = train_lineage.get((arm, seed))
                if lineage is None:
                    errors.append(f"missing training lineage: {path.relative_to(ROOT)}")
                    continue
                expected = (
                    arm,
                    seed,
                    lineage["checkpoint"],
                    lineage["manifest"],
                    lineage["base_manifest"],
                    "final",
                )
                observed = (
                    record["arm_id"],
                    record["training_seed"],
                    record["checkpoint_sha256"],
                    record["training_manifest_sha256"],
                    record["base_manifest_sha256"],
                    record["stage"],
                )
                if observed != expected:
                    errors.append(f"evaluation lineage mismatch: {path.relative_to(ROOT)}#{scenario}")
        if len(seen_scenarios) != 6:
            errors.append(f"duplicate scenario within profile: {path.relative_to(ROOT)}")

    analysis, analysis_data = read_json_bytes(ATTEMPT / "formal_analysis.json")
    check_data(ATTEMPT / "formal_analysis.json", analysis_data)

    for target, expected in sidecars.items():
        if target not in checked:
            if digest_file(target) != expected:
                errors.append(f"unvisited sidecar hash mismatch: {target.relative_to(ROOT)}")
            checked.add(target)

    expected_train = {(arm, seed) for arm in arms for seed in seeds}
    if set(train_keys) != expected_train:
        errors.append("training roster differs from the frozen arm x seed product")
    if set(base_keys) != {(seed,) for seed in seeds}:
        errors.append("base roster differs from the frozen seed set")
    for label, keys in (
        ("base", base_keys),
        ("training", train_keys),
        ("evaluation", evaluation_keys),
        ("trajectory", trajectory_keys),
    ):
        duplicates = duplicate_keys(keys)
        if duplicates:
            errors.append(f"{label} duplicate keys: {len(duplicates)}")

    observed = {
        "base_manifests": len(base_files),
        "training_manifests": len(train_files),
        "learned_evaluation_profiles": learned_files,
        "deterministic_evaluation_profiles": deterministic_files,
        "evaluation_profiles": len(eval_files),
        "trajectories": completed_trajectories,
        "sidecars": len(sidecars),
    }
    expected = {
        "base_manifests": 26,
        "training_manifests": 208,
        "learned_evaluation_profiles": 832,
        "deterministic_evaluation_profiles": 16,
        "evaluation_profiles": 848,
        "trajectories": 5088,
        "sidecars": 1499,
    }
    if observed != expected:
        errors.append(f"inventory count mismatch: observed={observed}, expected={expected}")
    formal_inventory = analysis["inventory"]
    formal_projection = {
        "base_manifests": formal_inventory["expected_base_manifests"],
        "training_manifests": formal_inventory["expected_training_manifests"],
        "evaluation_profiles": formal_inventory["expected_evaluation_profiles"],
        "trajectories": formal_inventory["expected_trajectories"],
    }
    independent_projection = {
        key: observed[key]
        for key in ("base_manifests", "training_manifests", "evaluation_profiles", "trajectories")
    }
    if formal_projection != independent_projection:
        errors.append("formal-analysis inventory disagrees with independent inventory")

    return {
        "schema_version": 1,
        "probe": "R485 pre-paper audit probe 01: inventory and lineage",
        "question": "Can missing, duplicate, corrupt, or cross-round artifacts manufacture 0/208?",
        "prediction": expected,
        "negative_control": negative_control(),
        "stop_threshold": "any real missing/duplicate/hash/lineage/schema mismatch is P0",
        "observed": observed,
        "reviewed_commit": reviewed_commit,
        "sealed_source_mismatches": source_mismatches,
        "formal_inventory_projection": formal_projection,
        "errors": errors,
        "decision": "PASS_PROCEED_TO_METRIC_RECOMPUTATION" if not errors else "P0_STOP",
        "elapsed_seconds": round(time.time() - started, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_check:
        print(json.dumps(negative_control(), indent=2, sort_keys=True))
        return 0
    result = run()
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["decision"] != "P0_STOP" else 2


if __name__ == "__main__":
    raise SystemExit(main())
