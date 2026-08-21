"""R430 engineering successor for the R429 adapted-SAC matched bundle.

R429 was sealed and then aborted because the inherited SAC function's default
``out_root`` retained the R428 path.  This successor imports the frozen R429
adapter, rebinds lifecycle paths, and changes one factor: every SAC formal
dispatch passes the R430 output root explicitly.  Science and classification
remain R429-identical.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

_parent_spec = importlib.util.spec_from_file_location(
    "_r430_r429_parent", ROOT / "scripts/run_r429_adapted_sac.py"
)
if _parent_spec is None or _parent_spec.loader is None:
    raise RuntimeError("cannot load the frozen R429 parent runner")
parent = importlib.util.module_from_spec(_parent_spec)
sys.modules[_parent_spec.name] = parent
_parent_spec.loader.exec_module(parent)
base = parent.base

ROUND_ID = "R430"
PLAN = ROOT / "memory/rounds/R430/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
REHEARSAL = ROOT / "memory/rounds/R430/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R430/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R430/formal_seal.json"
OUT = ROOT / "results/research_loop/r430_adapted_sac_successor"
TIER1_OUT = ROOT / "tmp/andes/r430_tier1"
R429_CAPACITY = ROOT / "memory/rounds/R429/capacity_evidence_v3.json"
R429_OUT = ROOT / "results/research_loop/r429_adapted_sac"

_parent_build_contract = parent.build_contract
_parent_source_manifest = parent.source_manifest
_parent_write_new_json = parent.write_new_json
_parent_train_arm_seed = base.train_arm_seed


def build_contract() -> dict[str, Any]:
    contract = copy.deepcopy(_parent_build_contract())
    contract["engineering_successor"] = {
        "successor_of": "R429",
        "single_change": "explicit-sac-out-root",
        "explicit_sac_out_root": True,
    }
    return contract


def train_output_root(arm_id: str, seed: int) -> Path:
    if arm_id not in build_contract()["learning_arm_ids"]:
        raise ValueError(f"unknown learning arm: {arm_id}")
    if seed not in build_contract()["training_seeds"]:
        raise ValueError(f"unknown training seed: {seed}")
    return OUT


def train_arm_seed(arm_id: str, seed: int, restart_count: int = 0) -> str:
    """Dispatch with an explicit R430 output root for both SAC arms."""
    base._assert_wsl_scratch()
    base.load_seal()
    resolved = train_output_root(arm_id, seed)
    if arm_id == "yang_scalar_td3":
        return _parent_train_arm_seed(arm_id, seed, restart_count=restart_count)
    return base._train_sac_arm_seed(
        arm_id,
        seed,
        restart_count=restart_count,
        out_root=resolved,
        total_steps=None,
        require_seal=True,
    )


def source_manifest() -> dict[str, dict[str, str]]:
    sources = _parent_source_manifest()
    replacements = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r430_adapted_sac_successor.py",
        "parent_r429_runner": ROOT / "scripts/run_r429_adapted_sac.py",
    }
    for name, path in replacements.items():
        sources[name] = {
            "path": base._relative(path),
            "sha256": base._sha256_file(path),
        }
    return sources


def parent_manifest() -> dict[str, dict[str, str]]:
    paths = {
        "r429_plan": ROOT / "memory/rounds/R429/plan.md",
        "r429_seal": ROOT / "memory/rounds/R429/formal_seal.json",
        "r429_failure": R429_OUT / "engineering_failure.json",
        "r429_capacity": R429_CAPACITY,
        "r428_analysis": ROOT / "results/research_loop/r428_c1_sac/formal_analysis.json",
        "r425_analysis": ROOT / "results/research_loop/r425_guard_constraints_signfix/formal_analysis.json",
    }
    return {
        name: {"path": base._relative(path), "sha256": base._sha256_file(path)}
        for name, path in paths.items()
    }


def authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    contract = build_contract()
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and "R430" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_closed": len(contract["profiles"]) == 8
        and base.evaluation_record_count(contract) == 240
        and base.training_run_count(contract) == 9
        and list(contract["training_seeds"]) == [401, 402, 403],
        "output_absence": not OUT.exists(),
    }


def output_root_probe() -> dict[str, Any]:
    resolved = {
        f"{arm}|{seed}": base._relative(train_output_root(str(arm), int(seed)))
        for arm in build_contract()["learning_arm_ids"]
        for seed in build_contract()["training_seeds"]
    }
    expected = base._relative(OUT)
    passed = all(value == expected for value in resolved.values())
    passed = passed and OUT.resolve() != R429_OUT.resolve()
    passed = passed and OUT.resolve() != (ROOT / "results/research_loop/r428_c1_sac").resolve()
    return {"passed": bool(passed), "expected": expected, "resolved": resolved}


def write_new_json(path: Path, payload: dict[str, Any]) -> str:
    mutable = copy.deepcopy(payload)
    if path.resolve() == REHEARSAL.resolve():
        probe = output_root_probe()
        mutable.setdefault("checks", {})["successor_output_root_probe"] = bool(
            probe["passed"]
        )
        mutable["successor_output_root_probe"] = probe
    if path.resolve() == SEAL.resolve():
        mutable["single_factor_change"] = (
            "R429-identical science; formal SAC dispatch explicitly passes the "
            "R430 create-only out_root, eliminating the definition-time R428 default"
        )
    if path.name == "formal_analysis.json" and path.parent.resolve() == OUT.resolve():
        mutable.setdefault("repair", {})["engineering_successor"] = {
            "successor_of": "R429",
            "explicit_sac_out_root": True,
        }
    return _parent_write_new_json(path, mutable)


def reuse_capacity() -> str:
    """Reuse the minutes-old identical R429 ladder after a fresh host check."""
    base._assert_wsl_scratch()
    if CAPACITY.exists() or REHEARSAL.exists() or SEAL.exists() or OUT.exists():
        raise FileExistsError("R430 pre-attempt artifact already exists")
    other = base._other_processes()
    if other:
        raise RuntimeError("other research Python processes are active: " + str(other))
    inherited = base._read_hashed_json(R429_CAPACITY)
    if inherited.get("readiness") != "RUN-READY" or int(
        inherited.get("selected_workers", 0)
    ) != 16:
        raise RuntimeError("R429 capacity evidence is not the registered 16-worker anchor")
    logical, physical_memory, wsl_available = base._memory_resources()
    payload = copy.deepcopy(inherited)
    payload.update(
        {
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "authorization": (
                "owner explicitly ordered maximum parallelism; R429 v3 "
                "representative ladder reused after fresh no-load host check"
            ),
            "contract_sha256": base.contract_sha256(build_contract()),
            "host": {
                "logical_processors": logical,
                "physical_memory_bytes": physical_memory,
            },
            "wsl": {"memory_available_bytes": wsl_available},
            "other_processes": other,
            "sources": source_manifest(),
            "installed_runtime": base._installed_runtime(),
            "inherited_capacity": {
                "path": base._relative(R429_CAPACITY),
                "sha256": base._sha256_file(R429_CAPACITY),
                "reuse_basis": "identical physical task and learner; output routing only",
            },
            "scientific_classification_inspected": False,
            "formal_authority": False,
            "training_executed": False,
        }
    )
    payload["empirical_anchor"]["source"] = (
        "R429 v3 selected representative rung plus fresh R430 no-load host check"
    )
    return write_new_json(CAPACITY, payload)


def _patch_parent() -> None:
    values = {
        "ROUND_ID": ROUND_ID,
        "PLAN": PLAN,
        "LINE": LINE,
        "REHEARSAL": REHEARSAL,
        "CAPACITY": CAPACITY,
        "SEAL": SEAL,
        "OUT": OUT,
        "TIER1_OUT": TIER1_OUT,
    }
    for module in (parent, base):
        for name, value in values.items():
            setattr(module, name, value)
    parent.build_contract = build_contract
    parent.source_manifest = source_manifest
    parent.parent_manifest = parent_manifest
    parent.authority_checks = authority_checks
    parent.write_new_json = write_new_json
    parent.prepare.__globals__["build_contract"] = build_contract
    parent.prepare.__globals__["source_manifest"] = source_manifest
    parent.prepare.__globals__["parent_manifest"] = parent_manifest
    parent.prepare.__globals__["authority_checks"] = authority_checks
    parent.prepare.__globals__["write_new_json"] = write_new_json
    base.build_contract = build_contract
    base._source_manifest = source_manifest
    base._parent_manifest = parent_manifest
    base._authority_checks = authority_checks
    base._write_new_json = write_new_json
    base.train_arm_seed = train_arm_seed


_patch_parent()


def _parse_shard(shard_id: str) -> tuple[str, str, int | None]:
    return parent._parse_shard(shard_id)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["reuse-capacity", "rehearse", "prepare", "shard", "evaluate", "classify"],
    )
    parser.add_argument("shard_id", nargs="?")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "reuse-capacity":
        base.safe_emit(f"R430 capacity evidence: {reuse_capacity()}")
    elif args.command == "rehearse":
        base.safe_emit(f"R430 rehearsal artifact: {base.rehearse()}")
    elif args.command == "prepare":
        base.safe_emit(f"R430 formal seal: {parent.prepare()}")
    elif args.command == "shard":
        if args.shard_id is None:
            raise SystemExit("shard requires a registered shard id")
        phase, arm_id, seed = _parse_shard(args.shard_id)
        if phase == "train":
            if seed is None:
                raise SystemExit("training shard requires a seed")
            base.safe_emit("R430 training manifest: " + train_arm_seed(arm_id, seed))
        else:
            base._evaluate_arm_seed(arm_id, seed)
            base.safe_emit(f"R430 evaluation shard complete: {args.shard_id}")
    elif args.command == "evaluate":
        base.evaluate_all()
        base.safe_emit("R430 serial evaluation complete")
    else:
        base.safe_emit(f"R430 formal analysis: {base.classify()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
