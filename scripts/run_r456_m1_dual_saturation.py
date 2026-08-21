"""R456 successor entry for the R455 M1 fixed-bank diagnostic.

R455 produced no formal result because its sealed runner exposed phase-specific
shard subcommands while the shared driver invokes the fixed ``shard`` command.
This successor changes only that orchestration interface.  Scientific logic is
imported from and source-sealed with the R455 implementation.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_r455_m1_dual_saturation as BASE


def _bind_successor_paths() -> None:
    BASE.ROUND_ID = "R456"
    BASE.PLAN = ROOT / "memory/rounds/R456/plan.md"
    BASE.CAPACITY = ROOT / "memory/rounds/R456/capacity_evidence.json"
    BASE.REHEARSAL = ROOT / "memory/rounds/R456/rehearsal.json"
    BASE.SEAL = ROOT / "memory/rounds/R456/formal_seal.json"
    BASE.STATE_SHARDS = ROOT / "tmp/andes/r456_m1_state_shards.json"
    BASE.EVAL_SHARDS = ROOT / "tmp/andes/r456_m1_eval_shards.json"
    BASE.OUT = ROOT / "results/research_loop/r456_m1_dual_saturation"


_bind_successor_paths()


def authority_checks() -> dict[str, bool]:
    """Round-aware successor authority check (R455 text was literal)."""

    plan_text = BASE.PLAN.read_text(encoding="utf-8")
    line_text = BASE.LINE.read_text(encoding="utf-8")
    checkpoints = BASE._checkpoint_inventory()
    parent_reference = BASE.PARENT_OUT / "reference_action_stats.json"
    parent_analysis = BASE.PARENT_OUT / "formal_analysis.json"
    return {
        "active_plan": f"round: {BASE.ROUND_ID}" in plan_text and "state: active" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "cell_inventory": len(BASE.CELLS) == 5 and len({row["cell_id"] for row in BASE.CELLS}) == 5,
        "shard_inventory": len(BASE.state_shard_ids()) == 6 and len(BASE.eval_shard_ids()) == 30,
        "checkpoint_inventory": len(checkpoints) == 6,
        "parent_reference": bool(BASE._verify_sidecar(parent_reference)),
        "parent_analysis": bool(BASE._verify_sidecar(parent_analysis)),
        "ceiling_release_law": BASE.projected_dual_step(10.0, -1.0, eta=0.05, ceiling=10.0) < 10.0,
        "output_absence": not BASE.OUT.exists(),
    }


# Base functions resolve this name from their module globals at call time.
BASE.authority_checks = authority_checks


def prepare() -> str:
    """Seal both the successor interface and imported scientific source."""

    BASE._assert_wsl_scratch()
    checks = BASE.authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed: {checks}")
    rehearsal_payload = BASE._read_hashed_json(BASE.REHEARSAL)
    capacity = BASE._read_hashed_json(BASE.CAPACITY)
    if not rehearsal_payload.get("passed"):
        raise RuntimeError("rehearsal did not pass")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError(f"capacity not RUN-READY: {capacity.get('readiness')}")
    selected = int(capacity["selected_workers"])
    sources = {
        "successor_runner": Path(__file__).resolve(),
        "scientific_runner": ROOT / "scripts/run_r455_m1_dual_saturation.py",
        "diagnostic_module": ROOT / "src/andes_rl_kundur/agents/cd_matd3_dual_factorial.py",
        "successor_tests": ROOT / "tests/test_run_r456_m1_dual_saturation.py",
        "scientific_runner_tests": ROOT / "tests/test_run_r455_m1_dual_saturation.py",
        "module_tests": ROOT / "tests/test_cd_matd3_dual_factorial.py",
        "parent_runner": ROOT / "scripts/run_r425_guard_constraints_signfix.py",
        "parent_learner": ROOT / "src/andes_rl_kundur/agents/cd_matd3_guard_constraints_vfix.py",
        "base_learner": ROOT / "src/andes_rl_kundur/agents/cd_matd3.py",
        "environment": ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "summariser": ROOT / "src/andes_rl_kundur/evaluation/md_decoupling_headroom.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
    }
    parent_paths = [
        BASE.PARENT_OUT / "reference_action_stats.json",
        BASE.PARENT_OUT / "formal_analysis.json",
        *[
            BASE.PARENT_OUT / "train" / arm / f"seed{seed}" / "manifest.json"
            for arm in BASE.ARMS
            for seed in BASE.SEEDS
        ],
        *[
            BASE.PARENT_OUT
            / "eval"
            / str(BASE.R425.build_contract()["deterministic_arm_id"])
            / "deterministic"
            / f"{profile_id}.json"
            for profile_id in BASE.build_contract()["evaluation_profiles"]
        ],
        *[
            BASE.PARENT_OUT / "eval" / arm / f"seed{seed}" / f"{profile_id}.json"
            for arm in BASE.ARMS
            for seed in BASE.SEEDS
            for profile_id in BASE.build_contract()["evaluation_profiles"]
        ],
    ]
    seal = {
        "schema_version": 1,
        "round": BASE.ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": BASE.contract_sha256(),
        "plan_sha256": BASE._sha256_file(BASE.PLAN),
        "capacity_sha256": BASE._sha256_file(BASE.CAPACITY),
        "rehearsal_sha256": BASE._sha256_file(BASE.REHEARSAL),
        "authority": checks,
        "runtime": rehearsal_payload["runtime"],
        "launch": {
            "host_process_budget": selected + 1,
            "wsl_python_processes": selected + 1,
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
            "state_shards": len(BASE.state_shard_ids()),
            "intervention_cells": len(BASE.eval_shard_ids()),
            "evaluation_shards": len(BASE.eval_shard_ids()),
            "shared_driver_subcommand": "shard",
        },
        "sources": {
            name: {"path": BASE._relative(path), "sha256": BASE._sha256_file(path)}
            for name, path in sources.items()
        },
        "checkpoints": BASE._checkpoint_inventory(),
        "parent_inputs": [
            {"path": BASE._relative(path), "sha256": BASE._verify_sidecar(path)}
            for path in parent_paths
        ],
        "formal_authority": True,
        "training_executed": False,
        "successor_of": "R455",
        "single_engineering_change": (
            "expose the shared driver's fixed `shard <id>` interface and dispatch "
            "two-field ids to state shards, three-field ids to evaluation shards"
        ),
    }
    digest = BASE._write_new_json(BASE.SEAL, seal)
    BASE.STATE_SHARDS.parent.mkdir(parents=True, exist_ok=True)
    BASE.STATE_SHARDS.write_text(json.dumps(BASE.state_shard_ids()) + "\n", encoding="utf-8")
    return json.dumps(
        {
            "seal_sha256": digest,
            "selected_workers": selected,
            "state_shards": len(BASE.state_shard_ids()),
            "evaluation_shards": len(BASE.eval_shard_ids()),
        },
        indent=2,
        sort_keys=True,
    )


def dispatch_shard(shard_id: str) -> str:
    """Translate the shared driver's fixed command by shard-id arity."""

    field_count = len(shard_id.split("|"))
    if field_count == 2:
        return BASE.run_state_shard(shard_id)
    if field_count == 3:
        return BASE.run_eval_shard(shard_id)
    raise ValueError(f"unregistered shard id: {shard_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "capacity",
            "rehearse",
            "prepare",
            "seal",
            "state-shards",
            "intervene",
            "eval-shards",
            "shard",
            "aggregate",
        ),
    )
    parser.add_argument("shard_id", nargs="?")
    args = parser.parse_args()
    if args.command == "capacity":
        print(BASE.measure_capacity(), flush=True)
    elif args.command == "rehearse":
        print(BASE.rehearsal(), flush=True)
    elif args.command in ("prepare", "seal"):
        print(prepare(), flush=True)
    elif args.command == "state-shards":
        print(json.dumps(BASE.state_shard_ids()), flush=True)
    elif args.command == "eval-shards":
        print(json.dumps(BASE.eval_shard_ids()), flush=True)
    elif args.command == "intervene":
        print(BASE.intervene(), flush=True)
    elif args.command == "aggregate":
        print(BASE.aggregate(), flush=True)
    else:
        if args.shard_id is None:
            raise SystemExit("shard requires an id")
        print(dispatch_shard(args.shard_id), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
