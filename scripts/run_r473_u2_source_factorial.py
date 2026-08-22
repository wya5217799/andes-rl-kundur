"""R473 U2 successor: frozen 96-shard R472 reuse plus detached orchestration."""

# ruff: noqa: E402, I001

from __future__ import annotations

import json
import importlib.util
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

_spec = importlib.util.spec_from_file_location(
    "_r473_r470_core", ROOT / "scripts/run_r470_u2_source_factorial.py"
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load isolated R470 execution core")
core = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = core
_spec.loader.exec_module(core)


ROUND_ID = "R473"
PLAN = ROOT / "memory/rounds/R473/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
POWER = ROOT / "memory/rounds/R473/power_analysis.json"
REUSE = ROOT / "memory/rounds/R473/reuse_audit.json"
CAPACITY = ROOT / "memory/rounds/R473/capacity_evidence.json"
REHEARSAL = ROOT / "memory/rounds/R473/rehearsal.json"
SEAL = ROOT / "memory/rounds/R473/formal_seal.json"
OUT = ROOT / "results/research_loop/r473_u2_source_factorial"
R472_OUT = ROOT / "results/research_loop/r472_u2_source_factorial"
SHUTDOWN_INVENTORY = (
    ROOT / "tmp/yang_md_decoupling_marl/r472_shutdown_inventory_20260822.json"
)
TRAIN_SHARDS = ROOT / "tmp/andes/r473_train_shards.json"
EVAL_SHARDS = ROOT / "tmp/andes/r473_eval_shards.json"

_EXCLUDED_CELLS = {
    (arm, seed) for arm in ("an_cn_r0", "an_cn_r1") for seed in core.TRAINING_SEEDS
}
EXPECTED_REUSE = tuple(
    (arm, seed)
    for arm in core.ARMS
    for seed in core.TRAINING_SEEDS
    if (arm, seed) not in _EXCLUDED_CELLS
)

for _name, _value in {
    "ROUND_ID": ROUND_ID,
    "PLAN": PLAN,
    "LINE": LINE,
    "POWER": POWER,
    "CAPACITY": CAPACITY,
    "REHEARSAL": REHEARSAL,
    "SEAL": SEAL,
    "OUT": OUT,
    "TRAIN_SHARDS": TRAIN_SHARDS,
    "EVAL_SHARDS": EVAL_SHARDS,
}.items():
    setattr(core, _name, _value)

_r470_build_contract = core.build_contract
_r470_rehearsal = core.rehearsal
_r470_measure_capacity = core.measure_capacity


def build_contract() -> dict[str, Any]:
    contract = _r470_build_contract()
    inherited = contract.pop("r470")
    inherited["successor_of"] = "R472"
    inherited["immutable_reuse_cells"] = [f"{arm}|{seed}" for arm, seed in EXPECTED_REUSE]
    inherited["missing_training_shards"] = 108 - len(EXPECTED_REUSE)
    inherited["operational_change"] = (
        "owner-ordered-shutdown successor; reuses the frozen 96-shard "
        "shutdown inventory and trains only the 12 an_cn cells"
    )
    contract["r473"] = inherited
    return contract


def authority_checks() -> dict[str, bool]:
    plan = PLAN.read_text(encoding="utf-8")
    line = LINE.read_text(encoding="utf-8")
    return {
        "active_plan": "round: R473" in plan and "state: active" in plan,
        "active_line": "line_id: yang-md-decoupling-marl" in line and "status: active" in line,
        "contract_closed": len(core.ARMS) == 18 and len(core.TRAINING_SEEDS) == 6 and len(EXPECTED_REUSE) == 96,
        "output_absence": not OUT.exists(),
    }


def _verify_hashed_tree(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    entries: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name.endswith(".sha256"):
            continue
        sidecar = Path(f"{path}.sha256")
        if not sidecar.is_file():
            errors.append(f"missing sidecar {core._relative(path)}")
            continue
        expected = sidecar.read_text(encoding="ascii").split()[0]
        actual = core._sha256_file(path)
        if expected != actual:
            errors.append(f"hash mismatch {core._relative(path)}")
        entries.append({"path": core._relative(path), "sha256": actual, "bytes": path.stat().st_size})
    return entries, errors


def _inventory_ok() -> dict[str, Any]:
    sidecar = Path(f"{SHUTDOWN_INVENTORY}.sha256")
    if not sidecar.is_file():
        return {"passed": False, "error": "inventory sidecar missing"}
    want = sidecar.read_text(encoding="ascii").split()[0]
    if core._sha256_file(SHUTDOWN_INVENTORY) != want:
        return {"passed": False, "error": "inventory hash mismatch"}
    inventory = json.loads(SHUTDOWN_INVENTORY.read_text(encoding="utf-8"))
    complete = {
        f"{arm}|{int(seed.removeprefix('seed'))}"
        for arm, seed in (s.split("/") for s in inventory.get("complete_shards", []))
    }
    expected = {f"{arm}|{seed}" for arm, seed in EXPECTED_REUSE}
    if complete != expected or int(inventory.get("complete_shard_count")) != 96:
        return {
            "passed": False,
            "error": "inventory complete set drift",
            "inventory_count": inventory.get("complete_shard_count"),
            "expected": sorted(expected),
        }
    return {"passed": True, "complete_count": len(complete)}


def reuse_audit() -> dict[str, Any]:
    if OUT.exists() or REHEARSAL.exists() or SEAL.exists():
        raise FileExistsError("reuse audit must precede R473 network/formal artifacts")
    inventory = _inventory_ok()
    errors: list[str] = []
    if not inventory["passed"]:
        errors.append(f"shutdown inventory invalid: {inventory.get('error')}")

    donor_entries, errors_d = _verify_hashed_tree(R472_OUT / "donors")
    errors.extend(errors_d)
    donor_rows: dict[int, dict[str, Any]] = {}
    for seed in core.TRAINING_SEEDS:
        manifest_path = R472_OUT / "donors" / f"seed{seed}" / "manifest.json"
        manifest = core._read_hashed_json(manifest_path)
        audit_ok = all(
            bool(manifest["splits"][split]["audit"][key])
            for split in ("development", "evaluation")
            for key in (
                "pi_fixed_point_free", "placebo_nodes_are_non_neighbours",
                "every_semantic_donor_changed", "slot_feature_scenario_time_pools_equal",
            )
        )
        shapes_ok = all(manifest["splits"][split]["shape"] == [24, 2, 31, 4, 7] for split in ("development", "evaluation"))
        base_path = ROOT / manifest["base_state_path"]
        base_ok = core._sha256_file(base_path) == manifest["base_state_sha256"]
        donor_rows[seed] = {
            "manifest_path": core._relative(manifest_path),
            "manifest_sha256": core._sha256_file(manifest_path),
            "base_state_sha256": manifest["base_state_sha256"],
            "audit_ok": audit_ok, "shapes_ok": shapes_ok, "base_ok": base_ok,
        }
        if not (audit_ok and shapes_ok and base_ok):
            errors.append(f"invalid donor seed{seed}")

    completed: list[dict[str, Any]] = []
    observed: set[tuple[str, int]] = set()
    for arm, seed in EXPECTED_REUSE:
        run_dir = R472_OUT / "train" / arm / f"seed{seed}"
        entries, run_errors = _verify_hashed_tree(run_dir)
        errors.extend(run_errors)
        manifest_path = run_dir / "manifest.json"
        manifest = core._read_hashed_json(manifest_path)
        identity = (str(manifest["arm_id"]), int(manifest["training_seed"]))
        expected_identity = (arm, seed)
        required_names = {"half.pt", "final.pt", "full_curves.npz", "manifest.json"}
        names = {Path(row["path"]).name for row in entries}
        valid = bool(
            identity == expected_identity
            and manifest["valid"]
            and int(manifest["interaction_steps"]) == 43_200
            and required_names.issubset(names)
            and manifest["base_state_sha256"] == donor_rows[seed]["base_state_sha256"]
            and identity not in observed
            and not run_errors
        )
        if not valid:
            errors.append(f"invalid reusable shard {arm}|{seed}")
        observed.add(identity)
        completed.append(
            {
                "arm_id": arm, "training_seed": seed, "valid": valid,
                "manifest_path": core._relative(manifest_path),
                "manifest_sha256": core._sha256_file(manifest_path),
                "file_count": len(entries),
                "files_sha256": core.hashlib.sha256(
                    json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest(),
                "bytes": sum(row["bytes"] for row in entries),
            }
        )

    partial_dirs = sorted(
        core._relative(path)
        for path in (R472_OUT / "train").glob("*/*")
        if path.is_dir() and not (path / "manifest.json").is_file()
    )
    expected_set_ok = observed == set(EXPECTED_REUSE)
    if not expected_set_ok:
        errors.append("reusable identity set drift")
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "constructed_networks_before_audit": False,
        "source_round": "R472",
        "shutdown_inventory": inventory,
        "shutdown_inventory_sha256": core._sha256_file(SHUTDOWN_INVENTORY),
        "donor_entries": donor_entries,
        "donors": {str(key): value for key, value in donor_rows.items()},
        "completed_training_shards": completed,
        "completed_count": len(completed),
        "expected_set_ok": expected_set_ok,
        "excluded_partial_directories": partial_dirs,
        "excluded_partial_count": len(partial_dirs),
        "errors": errors,
        "passed": not errors and len(completed) == 96,
    }


def measure_capacity() -> dict[str, Any]:
    payload = _r470_measure_capacity()
    payload["other_python_processes"] = [
        row for row in payload["other_python_processes"]
        if "run_r473_u2_source_factorial.py capacity" not in row
    ]
    payload["readiness"] = "RUN-READY" if int(payload["selected_workers"]) == 16 and not payload["other_python_processes"] else "LOAD-CHECK-REVIEW"
    payload["self_process_excluded"] = True
    return payload


def rehearsal() -> dict[str, Any]:
    checks = _r470_rehearsal()
    checks["terminal_truth_table"] = {
        "normal_horizon_done_accepted": True,
        "premature_done_rejected": True,
        "tds_failure_rejected": True,
        "source": "R471 sealed terminal predicate; R473 performs no donor regeneration",
    }
    reuse = core._read_hashed_json(REUSE)
    checks["reuse_audit"] = {
        "passed": bool(reuse["passed"]),
        "completed_count": int(reuse["completed_count"]),
        "excluded_partial_count": int(reuse["excluded_partial_count"]),
        "expected_set_ok": bool(reuse["expected_set_ok"]),
        "shutdown_inventory_ok": bool(reuse["shutdown_inventory"]["passed"]),
    }
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
        source = Path(folder) / "source.bin"
        target = Path(folder) / "target.bin"
        source.write_bytes(b"r473-hardlink-probe")
        os.link(source, target)
        checks["hardlink_probe"] = {
            "content_equal": source.read_bytes() == target.read_bytes(),
            "same_inode": os.stat(source).st_ino == os.stat(target).st_ino,
            "same_device": os.stat(source).st_dev == os.stat(target).st_dev,
        }
    checks["passed"] = bool(
        checks["passed"]
        and checks["reuse_audit"]["passed"]
        and checks["reuse_audit"]["completed_count"] == 96
        and checks["reuse_audit"]["expected_set_ok"]
        and checks["reuse_audit"]["shutdown_inventory_ok"]
        and all(checks["hardlink_probe"].values())
    )
    return checks


def _hardlink_tree(source_root: Path, target_root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for source in sorted(source_root.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(source_root)
        target = target_root / relative
        if target.exists():
            raise FileExistsError(f"import target exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, target)
        if core._sha256_file(source) != core._sha256_file(target):
            raise RuntimeError(f"hardlink hash mismatch: {target}")
        source_stat = os.stat(source)
        target_stat = os.stat(target)
        if source_stat.st_dev != target_stat.st_dev or source_stat.st_ino != target_stat.st_ino:
            raise RuntimeError(f"not the same hardlink identity: {target}")
        entries.append(
            {
                "source": core._relative(source),
                "target": core._relative(target),
                "sha256": core._sha256_file(target),
                "bytes": target.stat().st_size,
                "same_inode": True,
            }
        )
    return entries


def import_parent_artifacts() -> str:
    core._assert_wsl_scratch()
    core.load_seal()
    reuse = core._read_hashed_json(REUSE)
    if not reuse["passed"] or int(reuse["completed_count"]) != 96:
        raise RuntimeError("reuse audit is not valid")
    if OUT.exists():
        raise FileExistsError(f"R473 output exists: {OUT}")
    entries = _hardlink_tree(R472_OUT / "donors", OUT / "donors")
    for arm, seed in EXPECTED_REUSE:
        entries.extend(
            _hardlink_tree(
                R472_OUT / "train" / arm / f"seed{seed}",
                OUT / "train" / arm / f"seed{seed}",
            )
        )
    return core._write_new_json(
        OUT / "import_provenance.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "source_round": "R472",
            "reuse_audit_sha256": core._sha256_file(REUSE),
            "hardlink_entries": entries,
            "entry_count": len(entries),
            "logical_bytes": sum(row["bytes"] for row in entries),
            "additional_data_bytes": 0,
            "all_same_inode": all(row["same_inode"] for row in entries),
            "imported_training_shards": [f"{arm}|{seed}" for arm, seed in EXPECTED_REUSE],
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )


def prepare() -> dict[str, Any]:
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed: {checks}")
    power = core._read_hashed_json(POWER)
    reuse = core._read_hashed_json(REUSE)
    rehearsal_payload = core._read_hashed_json(REHEARSAL)
    capacity = core._read_hashed_json(CAPACITY)
    if not power["adequate_by_normal_approximation"] or not reuse["passed"] or not rehearsal_payload["passed"]:
        raise RuntimeError("power/reuse/rehearsal gate failed")
    if capacity["readiness"] != "RUN-READY" or int(capacity["selected_workers"]) != 16:
        raise RuntimeError("capacity gate failed")
    sources = {
        "successor_runner": Path(__file__).resolve(),
        "successor_tests": ROOT / "tests/test_run_r473_u2_source_factorial.py",
        "detached_pipeline": ROOT / "scripts/run_r473_detached_pipeline.sh",
        "sealed_r472_parent": ROOT / "scripts/run_r472_u2_source_factorial.py",
        "sealed_r471_parent": ROOT / "scripts/run_r471_u2_source_factorial.py",
        "sealed_r470_parent": ROOT / "scripts/run_r470_u2_source_factorial.py",
        "source_agent": ROOT / "src/andes_rl_kundur/agents/source_factorial_sac.py",
        "source_agent_tests": ROOT / "tests/test_source_factorial_sac.py",
        "u3_agent": ROOT / "src/andes_rl_kundur/agents/executed_action_sac.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "environment": ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
    }
    missing = [
        f"train|{arm}|{seed}"
        for arm in core.ARMS for seed in core.TRAINING_SEEDS
        if (arm, seed) not in set(EXPECTED_REUSE)
    ]
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": core.contract_sha256(),
        "plan_sha256": core._sha256_file(PLAN),
        "power_sha256": core._sha256_file(POWER),
        "reuse_audit_sha256": core._sha256_file(REUSE),
        "rehearsal_sha256": core._sha256_file(REHEARSAL),
        "capacity_sha256": core._sha256_file(CAPACITY),
        "authority": checks,
        "launch": {
            "wsl_python_processes": 17,
            "other_reserved_processes": 0,
            "host_process_budget": 17,
            "native_threads_per_process": 1,
            "detached_from_unified_exec": True,
        },
        "runtime": rehearsal_payload["runtime"],
        "sources": {
            name: {"path": core._relative(path), "sha256": core._sha256_file(path)}
            for name, path in sources.items()
        },
        "formal_authority": True,
        "training_executed": False,
    }
    seal_sha = core._write_new_json(SEAL, seal)
    TRAIN_SHARDS.parent.mkdir(parents=True, exist_ok=True)
    TRAIN_SHARDS.write_text(json.dumps(missing) + "\n", encoding="utf-8")
    EVAL_SHARDS.write_text(
        json.dumps([f"eval|{stage}|{arm}" for stage in ("half", "final") for arm in core.ARMS]) + "\n",
        encoding="utf-8",
    )
    return {
        "seal_sha256": seal_sha,
        "selected_workers": 16,
        "imported_training_shards": len(EXPECTED_REUSE),
        "fresh_training_shards": len(missing),
        "eval_shards": 36,
    }


core.authority_checks = authority_checks
core.build_contract = build_contract
core.measure_capacity = measure_capacity
core.rehearsal = rehearsal
core.prepare = prepare


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "reuse":
        payload = reuse_audit()
        digest = core._write_new_json(REUSE, payload)
        core.safe_emit(json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True))
        raise SystemExit(0)
    if len(sys.argv) == 2 and sys.argv[1] == "import":
        core.safe_emit(import_parent_artifacts())
        raise SystemExit(0)
    raise SystemExit(core.main())
