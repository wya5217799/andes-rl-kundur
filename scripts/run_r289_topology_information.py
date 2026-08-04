#!/usr/bin/env python3
"""R289 multigraph topology-information experiment adapter.

The immutable R288 probe remains the execution kernel for hashing, EIG cells,
and analysis.  This adapter replaces only the round identity and the pre-EIG
selection stage: three exact canonical single-circuit outages in retained
parallel corridors.  R288 artifacts are read-only structural input.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.topology_information import (  # noqa: E402
    select_parallel_circuit_variants,
)

PARENT_PROBE = ROOT / "probes" / "r288_topology_information.py"
PLAN = ROOT / "memory" / "rounds" / "R289" / "plan.md"
R288_INVENTORY = (
    ROOT / "results" / "r288_topology_information" / "topology_inventory.json"
)
R288_INVENTORY_SHA256 = (
    "ccf52b98fc082f3469950dd7895741e4b366cabaf9b75e96bf3204c3cc8ce7a2"
)
ROUND_ID = "R289"
QUESTION_ID = "Q-0047"
TARGET_GROUPS = {
    "topology_1": (5, 6),
    "topology_2": (6, 7),
    "topology_3": (9, 10),
}
EXPECTED_SELECTED_LINES = ("Line_0", "Line_2", "Line_9")
DEFAULT_SEAL = ROOT / "memory" / "rounds" / ROUND_ID / "topology_information_seal.json"
DEFAULT_OUT = ROOT / "results" / "r289_topology_information"


def _source_entry(kernel: ModuleType, path: Path) -> dict[str, str]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": kernel.sha256_file(path),
    }


def _seal_sources(kernel: ModuleType) -> dict[str, dict[str, str]]:
    return {
        "plan": _source_entry(kernel, PLAN),
        "adapter": _source_entry(kernel, Path(__file__).resolve()),
        "parent_probe": _source_entry(kernel, PARENT_PROBE),
        "pure_decision_module": _source_entry(kernel, kernel.PURE_MODULE),
        "eig_common": _source_entry(kernel, kernel.COMMON_MODULE),
        "environment": _source_entry(kernel, kernel.ENV_SOURCE),
        "r281_anchor_source": _source_entry(kernel, kernel.R281_SUMMARY),
        "r288_structural_input": _source_entry(kernel, R288_INVENTORY),
    }


def _prepare(kernel: ModuleType, seal_path: Path, out_dir: Path) -> None:
    seal_path = seal_path.resolve()
    out_dir = out_dir.resolve()
    inventory_path = out_dir / kernel.DEFAULT_INVENTORY_NAME
    if seal_path.exists() or inventory_path.exists():
        raise FileExistsError("R289 prepare artifacts already exist; refusing overwrite")

    r288, r288_digest = kernel._read_verified_json(
        R288_INVENTORY,
        R288_INVENTORY_SHA256,
    )
    if r288.get("selection_status") != "STRUCTURALLY-INFEASIBLE":
        raise RuntimeError("R288 structural input has unexpected status")

    common = kernel._load_common()
    _, ss, vsg_pos = common.build_frozen_plant()
    lines = kernel._line_rows(ss)
    selection = select_parallel_circuit_variants(
        lines,
        target_groups=TARGET_GROUPS,
    )
    if tuple(selection["selected"]) != EXPECTED_SELECTED_LINES:
        raise RuntimeError(
            f"canonical line drift: {selection['selected']} "
            f"!= {list(EXPECTED_SELECTED_LINES)}"
        )
    pflow_checks = {
        line_idx: kernel._q0_pflow(common, line_idx)
        for line_idx in selection["selected"]
    }
    pflow_pass = all(
        check["pflow_converged"]
        and check["opened_line_pass"]
        and check["g4_zeroed"]
        and check["total_m_pass"]
        for check in pflow_checks.values()
    )
    counts = kernel._plant_counts(ss, vsg_pos)
    inventory = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "pre-EIG multigraph topology selection",
        "created_utc": datetime.now(UTC).isoformat(),
        "selection_status": "COMPLETE" if pflow_pass else "INVALID-Q0-PFLOW",
        "base_plant_counts": counts,
        "r288_structural_input": {
            "path": R288_INVENTORY.relative_to(ROOT).as_posix(),
            "sha256": r288_digest,
        },
        "selection_contract": {
            "interpretation": "same-node multigraph line-status and admittance change",
            "target_groups": {
                name: list(endpoints) for name, endpoints in TARGET_GROUPS.items()
            },
            "canonical_rule": "lowest numeric Line_ suffix in each matched group",
            "expected_selected_lines": list(EXPECTED_SELECTED_LINES),
            "excluded_groups": {
                "7-8": "prior Line_4/5/6 corridor axis",
                "8-9": "contains protected Line_8 Toggler line",
            },
            "recorded_parameter_fields": ["r", "x", "b", "b1", "b2"],
            "q0_pflow_before_eig": True,
        },
        "selected": selection["selected"],
        "topologies": selection["topologies"],
        "q0_pflow_checks": pflow_checks,
        "lines": lines,
        "sources": _seal_sources(kernel),
    }
    inventory_digest = kernel._write_new_json(inventory_path, inventory)
    if not pflow_pass:
        print(f"inventory_sha256={inventory_digest}", flush=True)
        raise RuntimeError("R289 q0 PFlow/physical pre-seal guard failed; no seal written")

    topologies: list[dict[str, Any]] = [
        {"name": "nominal", "opened_line": None}
    ]
    for row in selection["topologies"]:
        line = row["line"]
        topologies.append(
            {
                "name": row["name"],
                "opened_line": row["selected_line"],
                "endpoints": row["endpoints"],
                "group_lines": row["group_lines"],
                "line": {
                    key: line[key]
                    for key in (
                        "idx",
                        "position",
                        "bus1",
                        "bus2",
                        "r",
                        "x",
                        "b",
                        "b1",
                        "b2",
                    )
                },
            }
        )
    contract = {
        "topologies": topologies,
        "allocations": {
            key: list(values) for key, values in kernel.allocation_library().items()
        },
        "thresholds": dict(kernel.DEFAULT_THRESHOLDS),
        "positive_real_tolerance": kernel.POSITIVE_REAL_TOLERANCE,
        "required_cell_guards": list(kernel.REQUIRED_CELL_GUARDS),
        "mode_rule": {
            "frequency_band_hz": [0.2, 1.5],
            "conjugate_merge": True,
            "pick": "max abs(P_area1-P_area2)",
        },
        "nominal_anchors": kernel._r281_anchors(common),
        "anchor_mapping": {
            "q0": "R281 q=0",
            "h1_pos": "R281 q=+0.25",
            "h1_neg": "R281 q=-0.25",
        },
        "matrix_shape": [4, 7],
        "topology_semantics": (
            "single-circuit outage in a retained parallel group; "
            "multigraph/status/admittance change, simple adjacency unchanged"
        ),
    }
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "topology_inventory": {
            "path": inventory_path.relative_to(ROOT).as_posix(),
            "sha256": inventory_digest,
        },
        "contract": contract,
        "contract_payload_sha256": kernel._canonical_payload_sha256(contract),
        "sources": _seal_sources(kernel),
        "adapter_contract": {
            "parent_probe": PARENT_PROBE.relative_to(ROOT).as_posix(),
            "overrides": {
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "selection": "canonical retained parallel-circuit outages",
            },
            "unchanged": [
                "allocation_library",
                "eig_cell",
                "mode_identification",
                "branch_checks",
                "estimands",
                "classification",
                "artifact_immutability",
            ],
        },
        "asset_protection": {
            "r288_read_only": True,
            "no_training": True,
            "no_time_domain": True,
            "no_gnn": True,
            "no_manuscript_write": True,
            "formal_artifacts_are_create_only": True,
        },
    }
    seal_digest = kernel._write_new_json(seal_path, seal)
    print(f"inventory_sha256={inventory_digest}", flush=True)
    print(f"seal_sha256={seal_digest}", flush=True)
    print(f"selected={selection['selected']}", flush=True)


def _load_kernel() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "_r289_parent_topology_kernel",
        PARENT_PROBE,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load parent probe: {PARENT_PROBE}")
    kernel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kernel)
    kernel.ROUND_ID = ROUND_ID
    kernel.QUESTION_ID = QUESTION_ID
    kernel.PLAN = PLAN
    kernel._seal_sources = lambda: _seal_sources(kernel)
    kernel.prepare = lambda seal_path, out_dir: _prepare(kernel, seal_path, out_dir)
    return kernel


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    prepare.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    run = commands.add_parser("run")
    run.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    run.add_argument("--expected-seal-sha256", required=True)
    run.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    analyse = commands.add_parser("analyse")
    analyse.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse.add_argument("--expected-seal-sha256", required=True)
    analyse.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    kernel = _load_kernel()
    if args.command == "prepare":
        kernel.prepare(args.seal, args.out_dir)
    elif args.command == "run":
        kernel.run(args.seal, args.expected_seal_sha256, args.out_dir)
    else:
        kernel.analyse(args.seal, args.expected_seal_sha256, args.out_dir)


if __name__ == "__main__":
    main()
