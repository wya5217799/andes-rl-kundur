#!/usr/bin/env python3
"""R287 weak-tie stress extension using the sealed R286 execution kernel.

Motivation:
    R286 already implements the seal-first weak-tie transfer matrix. Editing
    that historical runner would invalidate its source hash, while copying its
    roughly 600 lines would create a second implementation. This adapter loads
    the frozen R286 runner, replaces only the prospectively declared R287
    configuration, and records both the adapter and parent-kernel hashes in the
    new seal.

Usage (WSL ANDES environment only):
    python scripts/run_r287_weak_grid_stress.py prepare
    python scripts/run_r287_weak_grid_stress.py smoke --expected-manifest-sha256 HASH
    python scripts/run_r287_weak_grid_stress.py run --expected-manifest-sha256 HASH --shard-index 0
    python scripts/run_r287_weak_grid_stress.py analyse --expected-manifest-sha256 HASH

Failure modes:
    Existing artifacts are never overwritten. Source, bank, checkpoint, and
    seal drift fail closed. A failed smoke or trajectory is retained and is not
    retried. The adapter intentionally cannot change the controller, scenario
    bank, endpoints, guards, or weak-tie plant definition.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
PARENT_RUNNER = ROOT / "scripts/run_r286_weak_grid_td.py"
PLAN = ROOT / "memory/rounds/R287/plan.md"
DEFAULT_SEAL = ROOT / "memory/rounds/R287/weak_tie_stress_seal.json"
DEFAULT_OUT = ROOT / "results/r287_weak_grid_stress"

ROUND_ID = "R287"
QUESTION_ID = "Q-0046"
PHASE = "weak-tie-stress-extension"
TIE_K_LEVELS = (2.5, 3.0)
SHARD_COUNT = 3
HIERARCHICAL_BOOTSTRAP_SEED = 2026073001


def _source_entry(kernel: ModuleType, path: Path) -> dict[str, str]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": kernel.sha256_file(path),
    }


def _adapt_manifest(kernel: ModuleType, payload: object) -> object:
    """Replace R286 provenance with current plan/adapter plus parent hash."""

    if not isinstance(payload, dict) or "sources" not in payload:
        return payload
    adapted = copy.deepcopy(payload)
    sources = dict(adapted["sources"])
    parent_entry = dict(sources["script"])
    sources["parent_runner"] = parent_entry
    sources["script"] = _source_entry(kernel, Path(__file__).resolve())
    sources["plan"] = _source_entry(kernel, PLAN)
    adapted["sources"] = sources
    adapted["adapter_contract"] = {
        "parent_runner": PARENT_RUNNER.relative_to(ROOT).as_posix(),
        "overrides": {
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "phase": PHASE,
            "tie_k_levels": list(TIE_K_LEVELS),
            "shard_count": SHARD_COUNT,
            "hierarchical_bootstrap_seed": HIERARCHICAL_BOOTSTRAP_SEED,
        },
        "unchanged": [
            "scenario_bank",
            "controller_arms",
            "checkpoints",
            "weak_tie_environment",
            "primary_endpoints",
            "statistics",
            "decision_tree",
            "guards",
        ],
    }
    return adapted


def _load_kernel() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "_r287_parent_weak_tie_kernel",
        PARENT_RUNNER,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load parent runner: {PARENT_RUNNER}")
    kernel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kernel)

    kernel.ROUND_ID = ROUND_ID
    kernel.QUESTION = QUESTION_ID
    kernel.PHASE = PHASE
    kernel.TIE_K_LEVELS = TIE_K_LEVELS
    kernel.SHARD_COUNT = SHARD_COUNT
    kernel.HIERARCHICAL_BOOTSTRAP_SEED = HIERARCHICAL_BOOTSTRAP_SEED
    kernel.DEFAULT_SEAL = DEFAULT_SEAL
    kernel.DEFAULT_OUT = DEFAULT_OUT

    parent_write_new = kernel._write_new

    def write_new(path: Path, payload: object) -> str:
        if Path(path).resolve() == DEFAULT_SEAL.resolve():
            payload = _adapt_manifest(kernel, payload)
        return parent_write_new(path, payload)

    parent_write_new_text = kernel._write_new_text

    def write_new_text(path: Path, content: str) -> str:
        content = content.replace(
            "# R286 weak-tie zero-training transfer",
            "# R287 weak-tie zero-training stress extension",
            1,
        )
        return parent_write_new_text(path, content)

    kernel._write_new = write_new
    kernel._write_new_text = write_new_text
    return kernel


def _smoke(
    kernel: ModuleType,
    manifest_path: Path,
    expected: str,
    out_dir: Path,
) -> None:
    manifest = kernel._verify(manifest_path, expected)
    bank, _ = kernel.load_scenario_bank(
        kernel.FORMAL_BANK,
        expected_sha256=manifest["formal_bank"]["sha256"],
    )
    scenario = bank["scenarios"][0]
    arm = "q0"
    tie_k = max(TIE_K_LEVELS)
    path = out_dir / "smoke" / (
        f"{scenario['name']}__{arm}__k{tie_k:.2f}.json"
    )
    if path.exists():
        record = kernel._validate_trace(
            path,
            scenario,
            arm,
            tie_k,
            manifest,
            expected,
        )
        if not record.get("completed") or record.get("tds_failed"):
            raise RuntimeError(f"retained failed smoke forbids retry: {path}")
        print(f"[resume-smoke] {path.name}", flush=True)
        return

    controller, controller_config = kernel._make_controller(
        arm,
        manifest["arms"][arm],
    )
    record = kernel._run_scenario(
        controller,
        controller_name=arm,
        controller_config=controller_config,
        scenario_name=scenario["name"],
        delta_u=scenario["delta_u"],
        tie_k=tie_k,
        evidence_hashes={
            "weak_tie_seal": expected,
            "formal_bank": manifest["formal_bank"]["sha256"],
        },
    )
    record.update(
        {
            "location": scenario["location"],
            "sign": scenario["sign"],
            "severity": scenario["severity"],
            "weak_tie_seal_sha256": expected,
            "formal_bank_sha256": manifest["formal_bank"]["sha256"],
            "execution_shard_index": "smoke",
            "execution_shard_count": SHARD_COUNT,
            "smoke": True,
        }
    )
    digest = kernel._write_new(path, record)
    if not record["completed"]:
        raise RuntimeError(f"smoke failed and is retained: {path}")
    injection = kernel._injection_consistent([record])
    if not injection["pass"]:
        raise RuntimeError(f"smoke injection audit failed: {injection}")
    print(
        f"[r287-smoke] {path.name} completed=True "
        f"wall={record['wall_clock_s']:.1f}s sha256={digest}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--manifest", type=Path, default=DEFAULT_SEAL)
    prepare_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)

    smoke_parser = commands.add_parser("smoke")
    smoke_parser.add_argument("--manifest", type=Path, default=DEFAULT_SEAL)
    smoke_parser.add_argument("--expected-manifest-sha256", required=True)
    smoke_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)

    run_parser = commands.add_parser("run")
    run_parser.add_argument("--manifest", type=Path, default=DEFAULT_SEAL)
    run_parser.add_argument("--expected-manifest-sha256", required=True)
    run_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    run_parser.add_argument("--shard-index", type=int, required=True)
    run_parser.add_argument("--shard-count", type=int, default=SHARD_COUNT)

    analyse_parser = commands.add_parser("analyse")
    analyse_parser.add_argument("--manifest", type=Path, default=DEFAULT_SEAL)
    analyse_parser.add_argument("--expected-manifest-sha256", required=True)
    analyse_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)

    args = parser.parse_args()
    kernel = _load_kernel()
    if args.command == "prepare":
        kernel.prepare(args.manifest, args.out_dir)
    elif args.command == "smoke":
        _smoke(
            kernel,
            args.manifest,
            args.expected_manifest_sha256,
            args.out_dir,
        )
    elif args.command == "run":
        kernel.run_shard(
            args.manifest,
            args.expected_manifest_sha256,
            args.out_dir,
            args.shard_index,
            args.shard_count,
        )
    else:
        kernel.analyse(
            args.manifest,
            args.expected_manifest_sha256,
            args.out_dir,
        )


if __name__ == "__main__":
    main()
