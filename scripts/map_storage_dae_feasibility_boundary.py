"""Seal, run, resume, and analyse the R273 Bus14 completion boundary."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.feasibility_screen import (  # noqa: E402
    advance_common_completion_bracket,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from andes_rl_kundur.evaluation.storage_dae_feasibility import (  # noqa: E402
    PLANTS,
    run_zero_support_feasibility_scenario,
)

ROUND_ID = "R273"
PHASE = "boundary"
ENV_SEED = 42
STEPS = 300
ITERATIONS = 4
LOWER_COMPLETE = 0.4419
UPPER_FAILED = 2.1841
DISTURBANCE_LOCATION = "PQ_Bus14"


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def _write_new_canonical(path: Path, payload: object) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(payload)
    temporary = Path(f"{path}.tmp")
    if temporary.exists():
        raise FileExistsError(f"stale temporary artifact exists: {temporary}")
    temporary.write_bytes(data)
    temporary.replace(path)
    digest = sha256_bytes(data)
    sidecar = Path(f"{path}.sha256")
    if sidecar.exists():
        raise FileExistsError(f"refusing to overwrite digest sidecar: {sidecar}")
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _load_json_with_hash(path: Path, expected_sha256: str) -> dict[str, Any]:
    digest = sha256_file(path)
    if digest != expected_sha256.lower():
        raise ValueError(
            f"SHA-256 mismatch for {path}: expected {expected_sha256}, got {digest}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _source_paths() -> dict[str, Path]:
    return {
        "boundary_policy": (
            ROOT / "src/andes_rl_kundur/evaluation/feasibility_screen.py"
        ),
        "diagnostic_evaluator": (
            ROOT
            / "src/andes_rl_kundur/evaluation/storage_dae_feasibility.py"
        ),
        "storage_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py"
        ),
        "v4_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py"
        ),
        "base_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/base_env.py"
        ),
        "active_power_contract": (
            ROOT / "src/andes_rl_kundur/control/active_power.py"
        ),
        "runner": Path(__file__).resolve(),
        "andes_esd1": Path(
            "/home/wya/andes_venv/lib/python3.12/site-packages/"
            "andes/models/distributed/esd1.py"
        ),
        "andes_tds": Path(
            "/home/wya/andes_venv/lib/python3.12/site-packages/"
            "andes/routines/tds.py"
        ),
    }


def _verify_core_bracket(core_summary: dict[str, Any]) -> None:
    if core_summary["decision"]["classification"] != "ENVELOPE-INFEASIBLE":
        raise ValueError("boundary map requires ENVELOPE-INFEASIBLE core evidence")
    by_scenario = {
        str(row["scenario"]): row
        for row in core_summary["scenario_matrix"]
    }
    lower = by_scenario["random_01"]
    upper = by_scenario["random_10"]
    if lower["delta_u"] != {DISTURBANCE_LOCATION: LOWER_COMPLETE}:
        raise ValueError("lower completion bracket does not match sealed plan")
    if upper["delta_u"] != {DISTURBANCE_LOCATION: UPPER_FAILED}:
        raise ValueError("upper failure bracket does not match sealed plan")
    if not all(bool(lower[plant]["completed"]) for plant in PLANTS):
        raise ValueError("lower bracket is not complete for both plants")
    if any(bool(upper[plant]["completed"]) for plant in PLANTS):
        raise ValueError("upper bracket is not failed for both plants")


def prepare_seal(
    *,
    core_summary_path: Path,
    expected_core_summary_sha256: str,
    core_manifest_path: Path,
    expected_core_manifest_sha256: str,
    plan_path: Path,
    manifest_path: Path,
) -> None:
    core_summary = _load_json_with_hash(
        core_summary_path,
        expected_core_summary_sha256,
    )
    _verify_core_bracket(core_summary)
    _load_json_with_hash(core_manifest_path, expected_core_manifest_sha256)
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "phase": PHASE,
        "repository_head": _git_head(),
        "core_summary": {
            "path": str(core_summary_path),
            "sha256": expected_core_summary_sha256,
        },
        "core_manifest": {
            "path": str(core_manifest_path),
            "sha256": expected_core_manifest_sha256,
        },
        "plan": {
            "path": str(plan_path),
            "sha256": sha256_file(plan_path),
        },
        "sources": {
            name: {"path": str(path), "sha256": sha256_file(path)}
            for name, path in _source_paths().items()
        },
        "packages": {
            "andes": importlib.metadata.version("andes"),
            "numpy": importlib.metadata.version("numpy"),
        },
        "execution": {
            "environment_seed": ENV_SEED,
            "steps": STEPS,
            "plants": list(PLANTS),
            "plant_order": "original-first on odd iteration; storage-first on even",
            "disturbance_location": DISTURBANCE_LOCATION,
            "lower_complete": LOWER_COMPLETE,
            "upper_failed": UPPER_FAILED,
            "iterations": ITERATIONS,
            "midpoint_rule": "(lower_complete + upper_failed) / 2",
            "advance_rule": (
                "advance only when both plants agree; stop on plant mismatch"
            ),
        },
        "endpoint_boundary": (
            "60-second completion, solver, DAE, and zero-support audit only"
        ),
    }
    print(_write_new_canonical(manifest_path, payload))


def _verify_seal(
    manifest_path: Path,
    expected_manifest_sha256: str,
) -> dict[str, Any]:
    manifest = _load_json_with_hash(
        manifest_path,
        expected_manifest_sha256,
    )
    if manifest.get("round") != ROUND_ID or manifest.get("phase") != PHASE:
        raise ValueError("boundary seal identity mismatch")
    for item in manifest["sources"].values():
        path = Path(item["path"])
        if sha256_file(path) != item["sha256"]:
            raise ValueError(f"sealed source drift: {path}")
    for key in ("core_summary", "core_manifest", "plan"):
        item = manifest[key]
        if sha256_file(Path(item["path"])) != item["sha256"]:
            raise ValueError(f"sealed {key} drift: {item['path']}")
    core_summary = _load_json_with_hash(
        Path(manifest["core_summary"]["path"]),
        manifest["core_summary"]["sha256"],
    )
    _verify_core_bracket(core_summary)
    return manifest


def _trace_path(out_dir: Path, iteration: int, plant: str) -> Path:
    return (
        out_dir
        / "boundary_traces"
        / f"iteration_{iteration:02d}__{plant}.json"
    )


def _write_trace(path: Path, record: dict[str, Any]) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite trace: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(record)
    temporary = Path(f"{path}.tmp")
    if temporary.exists():
        raise FileExistsError(f"stale trace temporary exists: {temporary}")
    temporary.write_bytes(data)
    temporary.replace(path)
    return sha256_bytes(data)


def _load_resumable_trace(
    path: Path,
    *,
    iteration: int,
    magnitude: float,
    plant: str,
    seal_sha256: str,
) -> dict[str, Any]:
    record = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "round": ROUND_ID,
        "phase": PHASE,
        "iteration": iteration,
        "plant": plant,
        "tested_magnitude": magnitude,
        "delta_u": {DISTURBANCE_LOCATION: magnitude},
        "seal_manifest_sha256": seal_sha256,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"resume provenance mismatch in {path}: {key}")
    if not bool(record.get("provenance_valid", False)):
        raise ValueError(f"invalid trace provenance: {path}")
    return record


def _iteration_rows(
    *,
    out_dir: Path,
    iteration: int,
    magnitude: float,
    seal_sha256: str,
) -> dict[str, dict[str, Any]]:
    rows = {}
    for plant in PLANTS:
        path = _trace_path(out_dir, iteration, plant)
        if not path.exists():
            raise FileNotFoundError(f"missing boundary trace: {path}")
        rows[plant] = _load_resumable_trace(
            path,
            iteration=iteration,
            magnitude=magnitude,
            plant=plant,
            seal_sha256=seal_sha256,
        )
    return rows


def evaluate(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
    out_dir: Path,
    resume: bool,
) -> None:
    manifest = _verify_seal(manifest_path, expected_manifest_sha256)
    execution = manifest["execution"]
    lower = float(execution["lower_complete"])
    upper = float(execution["upper_failed"])

    for iteration in range(1, int(execution["iterations"]) + 1):
        magnitude = (lower + upper) / 2.0
        plant_order = PLANTS if iteration % 2 else tuple(reversed(PLANTS))
        for plant in plant_order:
            path = _trace_path(out_dir, iteration, plant)
            if path.exists():
                if not resume:
                    raise FileExistsError(
                        f"trace exists; use --resume after audit: {path}"
                    )
                _load_resumable_trace(
                    path,
                    iteration=iteration,
                    magnitude=magnitude,
                    plant=plant,
                    seal_sha256=expected_manifest_sha256,
                )
                print(f"[resume] {path.name}", flush=True)
                continue

            print(
                f"[boundary {iteration:02d}/{ITERATIONS:02d}] "
                f"{magnitude:.10f} / {plant}",
                flush=True,
            )
            record = run_zero_support_feasibility_scenario(
                f"r273_boundary_{iteration:02d}",
                {DISTURBANCE_LOCATION: magnitude},
                plant=plant,
                seed=ENV_SEED,
                steps=STEPS,
            )
            record.update(
                {
                    "round": ROUND_ID,
                    "phase": PHASE,
                    "iteration": iteration,
                    "tested_magnitude": magnitude,
                    "seal_manifest_sha256": expected_manifest_sha256,
                    "provenance_valid": True,
                }
            )
            digest = _write_trace(path, record)
            print(
                f"[saved] {path.name} "
                f"{record['successful_steps']}/{record['requested_steps']} "
                f"complete={record['completed']} sha256={digest}",
                flush=True,
            )

        rows = _iteration_rows(
            out_dir=out_dir,
            iteration=iteration,
            magnitude=magnitude,
            seal_sha256=expected_manifest_sha256,
        )
        decision = advance_common_completion_bracket(
            lower_complete=lower,
            upper_failed=upper,
            tested_magnitude=magnitude,
            completion_by_plant={
                plant: bool(rows[plant]["completed"])
                for plant in PLANTS
            },
        )
        print(json.dumps(decision, sort_keys=True), flush=True)
        if decision["classification"] == "PLANT-MISMATCH":
            print("[stop] plant completion mismatch", flush=True)
            return
        lower = float(decision["lower_complete"])
        upper = float(decision["upper_failed"])


def _summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# R273 common completion boundary",
        "",
        f"**Classification:** {summary['classification']}",
        "",
        "| Iteration | Magnitude (pu) | original V4 | storage zero |",
        "|---:|---:|---:|---:|",
    ]
    for row in summary["iterations"]:
        lines.append(
            f"| {row['iteration']} | {row['tested_magnitude']:.10f} | "
            f"{row['completion_by_plant']['original_v4']} | "
            f"{row['completion_by_plant']['storage_zero']} |"
        )
    lines.extend(
        [
            "",
            "## Final completion bracket",
            "",
            f"- lower complete: `{summary['lower_complete']:.10f}` pu",
            f"- upper failed: `{summary['upper_failed']:.10f}` pu",
            f"- width: `{summary['bracket_width']:.10f}` pu",
            "",
            "This is a completion-only boundary. It is not a controller "
            "performance or universal voltage-stability limit.",
            "",
        ]
    )
    return "\n".join(lines)


def analyse(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
    out_dir: Path,
) -> None:
    manifest = _verify_seal(manifest_path, expected_manifest_sha256)
    execution = manifest["execution"]
    lower = float(execution["lower_complete"])
    upper = float(execution["upper_failed"])
    iteration_summaries = []
    trace_hashes = {}
    classification = "COMMON-BOUNDARY"

    for iteration in range(1, int(execution["iterations"]) + 1):
        magnitude = (lower + upper) / 2.0
        rows = _iteration_rows(
            out_dir=out_dir,
            iteration=iteration,
            magnitude=magnitude,
            seal_sha256=expected_manifest_sha256,
        )
        completion_by_plant = {
            plant: bool(rows[plant]["completed"])
            for plant in PLANTS
        }
        decision = advance_common_completion_bracket(
            lower_complete=lower,
            upper_failed=upper,
            tested_magnitude=magnitude,
            completion_by_plant=completion_by_plant,
        )
        iteration_summaries.append(
            {
                "iteration": iteration,
                "tested_magnitude": magnitude,
                "completion_by_plant": completion_by_plant,
                "successful_steps_by_plant": {
                    plant: int(rows[plant]["successful_steps"])
                    for plant in PLANTS
                },
                "last_simulator_time_by_plant": {
                    plant: rows[plant]["last_simulator_time"]
                    for plant in PLANTS
                },
                "solver_messages_by_plant": {
                    plant: rows[plant]["solver_messages"]
                    for plant in PLANTS
                },
                "decision": decision["classification"],
            }
        )
        for plant in PLANTS:
            path = _trace_path(out_dir, iteration, plant)
            trace_hashes[str(path)] = sha256_file(path)
        if decision["classification"] == "PLANT-MISMATCH":
            classification = "PLANT-MISMATCH"
            break
        lower = float(decision["lower_complete"])
        upper = float(decision["upper_failed"])

    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "phase": PHASE,
        "classification": classification,
        "disturbance_location": DISTURBANCE_LOCATION,
        "iterations": iteration_summaries,
        "lower_complete": lower,
        "upper_failed": upper,
        "bracket_width": upper - lower,
        "seal_manifest_sha256": expected_manifest_sha256,
        "core_summary_sha256": manifest["core_summary"]["sha256"],
        "trace_hashes": trace_hashes,
        "endpoint_boundary": manifest["endpoint_boundary"],
        "prospective_screen_contract": {
            "implementation": (
                "andes_rl_kundur.evaluation.feasibility_screen."
                "build_feasibility_screen_contract"
            ),
            "requires_completion_before_controller_evaluation": True,
            "retains_excluded_scenarios": True,
            "reports_excluded_fraction": True,
            "stratifies_by_disturbance_location_and_sign": True,
        },
    }
    summary_path = out_dir / "boundary_summary.json"
    summary_digest = _write_new_canonical(summary_path, summary)
    markdown_path = out_dir / "boundary_summary.md"
    if markdown_path.exists():
        raise FileExistsError(
            f"refusing to overwrite immutable summary: {markdown_path}"
        )
    markdown_path.write_text(_summary_markdown(summary), encoding="utf-8")
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "phase": PHASE,
        "repository_head": manifest["repository_head"],
        "manifest": {
            "path": str(manifest_path),
            "sha256": expected_manifest_sha256,
            "payload": manifest,
        },
        "summary_sha256": summary_digest,
        "summary_markdown_sha256": sha256_file(markdown_path),
        "trace_hashes": trace_hashes,
    }
    provenance_digest = _write_new_canonical(
        out_dir / "boundary_provenance.json",
        provenance,
    )
    print(
        json.dumps(
            {
                "classification": classification,
                "lower_complete": lower,
                "upper_failed": upper,
                "bracket_width": upper - lower,
                "summary_sha256": summary_digest,
                "provenance_sha256": provenance_digest,
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    seal_parser = subparsers.add_parser("prepare-seal")
    seal_parser.add_argument("--core-summary", type=Path, required=True)
    seal_parser.add_argument("--expected-core-summary-sha256", required=True)
    seal_parser.add_argument("--core-manifest", type=Path, required=True)
    seal_parser.add_argument("--expected-core-manifest-sha256", required=True)
    seal_parser.add_argument("--plan", type=Path, required=True)
    seal_parser.add_argument("--manifest", type=Path, required=True)

    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("--manifest", type=Path, required=True)
    evaluate_parser.add_argument("--expected-manifest-sha256", required=True)
    evaluate_parser.add_argument("--out-dir", type=Path, required=True)
    evaluate_parser.add_argument("--resume", action="store_true")

    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--manifest", type=Path, required=True)
    analyse_parser.add_argument("--expected-manifest-sha256", required=True)
    analyse_parser.add_argument("--out-dir", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "prepare-seal":
        prepare_seal(
            core_summary_path=args.core_summary,
            expected_core_summary_sha256=(
                args.expected_core_summary_sha256
            ),
            core_manifest_path=args.core_manifest,
            expected_core_manifest_sha256=(
                args.expected_core_manifest_sha256
            ),
            plan_path=args.plan,
            manifest_path=args.manifest,
        )
    elif args.command == "evaluate":
        evaluate(
            manifest_path=args.manifest,
            expected_manifest_sha256=args.expected_manifest_sha256,
            out_dir=args.out_dir,
            resume=args.resume,
        )
    elif args.command == "analyse":
        analyse(
            manifest_path=args.manifest,
            expected_manifest_sha256=args.expected_manifest_sha256,
            out_dir=args.out_dir,
        )


if __name__ == "__main__":
    main()
