"""Seal, run, resume, and analyse the R273 completion-only DAE diagnosis."""

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

from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    load_scenario_bank,
    sha256_bytes,
    sha256_file,
)
from andes_rl_kundur.evaluation.storage_dae_feasibility import (  # noqa: E402
    PLANTS,
    classify_storage_dae_attribution,
    run_zero_support_feasibility_scenario,
)

ROUND_ID = "R273"
ENV_SEED = 42
STEPS = 300
FAILURE_SCENARIOS = ("random_00", "random_05", "random_10")
CONTROL_SCENARIOS = ("random_01", "random_11", "random_16", "random_09")
ORDERED_SCENARIOS = (*FAILURE_SCENARIOS, *CONTROL_SCENARIOS)
EXPECTED_DELTAS = {
    "random_00": {"PQ_Bus14": 2.2},
    "random_05": {"PQ_Bus14": 2.2772},
    "random_10": {"PQ_Bus14": 2.1841},
    "random_01": {"PQ_Bus14": 0.4419},
    "random_11": {"PQ_Bus14": -0.6458},
    "random_16": {"PQ_Bus14": -2.1415},
    "random_09": {"PQ_Bus15": 2.1086},
}


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
        "andes_pvd1": Path(
            "/home/wya/andes_venv/lib/python3.12/site-packages/"
            "andes/models/distributed/pvd1.py"
        ),
        "andes_tds": Path(
            "/home/wya/andes_venv/lib/python3.12/site-packages/"
            "andes/routines/tds.py"
        ),
    }


def _selected_cases(bank: dict[str, Any]) -> list[dict[str, Any]]:
    by_name = {
        str(item["name"]): item
        for item in bank["scenarios"]
    }
    selected = []
    for name in ORDERED_SCENARIOS:
        if name not in by_name:
            raise ValueError(f"R273 case missing from R272 bank: {name}")
        delta_u = by_name[name]["delta_u"]
        if delta_u != EXPECTED_DELTAS[name]:
            raise ValueError(f"R273 frozen delta mismatch for {name}: {delta_u}")
        selected.append(
            {
                "name": name,
                "delta_u": delta_u,
                "role": (
                    "registered_failure"
                    if name in FAILURE_SCENARIOS
                    else "signed_location_control"
                ),
            }
        )
    return selected


def prepare_seal(
    *,
    bank_path: Path,
    expected_bank_sha256: str,
    contract_path: Path,
    expected_contract_sha256: str,
    plan_path: Path,
    manifest_path: Path,
) -> None:
    bank, bank_digest = load_scenario_bank(
        bank_path,
        expected_sha256=expected_bank_sha256,
    )
    contract = _load_json_with_hash(contract_path, expected_contract_sha256)
    sources = {
        name: {"path": str(path), "sha256": sha256_file(path)}
        for name, path in _source_paths().items()
    }
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "repository_head": _git_head(),
        "bank": {
            "path": str(bank_path),
            "sha256": bank_digest,
        },
        "contract": {
            "path": str(contract_path),
            "sha256": sha256_file(contract_path),
            "payload_sha256": sha256_bytes(canonical_json_bytes(contract)),
        },
        "plan": {
            "path": str(plan_path),
            "sha256": sha256_file(plan_path),
        },
        "sources": sources,
        "packages": {
            "andes": importlib.metadata.version("andes"),
            "numpy": importlib.metadata.version("numpy"),
        },
        "execution": {
            "environment_seed": ENV_SEED,
            "steps": STEPS,
            "plants": list(PLANTS),
            "failure_scenarios": list(FAILURE_SCENARIOS),
            "control_scenarios": list(CONTROL_SCENARIOS),
            "plant_order": "original-first on even case index; storage-first on odd",
        },
        "cases": _selected_cases(bank),
        "endpoint_boundary": (
            "completion, solver, initialization, DAE, and zero-support audit only"
        ),
    }
    digest = _write_new_canonical(manifest_path, payload)
    print(digest)


def _verify_seal(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
) -> dict[str, Any]:
    manifest = _load_json_with_hash(
        manifest_path,
        expected_manifest_sha256,
    )
    if manifest.get("round") != ROUND_ID:
        raise ValueError("seal round mismatch")
    for item in manifest["sources"].values():
        path = Path(item["path"])
        if sha256_file(path) != item["sha256"]:
            raise ValueError(f"sealed source drift: {path}")
    for key in ("bank", "contract", "plan"):
        item = manifest[key]
        if sha256_file(Path(item["path"])) != item["sha256"]:
            raise ValueError(f"sealed {key} drift: {item['path']}")
    return manifest


def _trace_path(out_dir: Path, scenario: str, plant: str) -> Path:
    return out_dir / "traces" / f"{scenario}__{plant}.json"


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


def _validate_resumable_trace(
    path: Path,
    *,
    case: dict[str, Any],
    plant: str,
    bank_sha256: str,
    contract_sha256: str,
    seal_sha256: str,
) -> dict[str, Any]:
    record = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "scenario": case["name"],
        "delta_u": case["delta_u"],
        "plant": plant,
        "bank_sha256": bank_sha256,
        "contract_sha256": contract_sha256,
        "seal_manifest_sha256": seal_sha256,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"resume provenance mismatch in {path}: {key}")
    return record


def evaluate(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
    out_dir: Path,
    resume: bool,
) -> None:
    manifest = _verify_seal(
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    bank_sha256 = manifest["bank"]["sha256"]
    contract_sha256 = manifest["contract"]["sha256"]
    cases = manifest["cases"]
    for case_index, case in enumerate(cases):
        plant_order = (
            PLANTS
            if case_index % 2 == 0
            else tuple(reversed(PLANTS))
        )
        for plant in plant_order:
            path = _trace_path(out_dir, case["name"], plant)
            if path.exists():
                if not resume:
                    raise FileExistsError(
                        f"trace exists; pass --resume after provenance audit: {path}"
                    )
                _validate_resumable_trace(
                    path,
                    case=case,
                    plant=plant,
                    bank_sha256=bank_sha256,
                    contract_sha256=contract_sha256,
                    seal_sha256=expected_manifest_sha256,
                )
                print(f"[resume] {path.name}", flush=True)
                continue

            print(
                f"[core {case_index + 1:02d}/{len(cases):02d}] "
                f"{case['name']} / {plant}",
                flush=True,
            )
            record = run_zero_support_feasibility_scenario(
                case["name"],
                case["delta_u"],
                plant=plant,
                seed=ENV_SEED,
                steps=STEPS,
            )
            record.update(
                {
                    "round": ROUND_ID,
                    "phase": "core",
                    "role": case["role"],
                    "bank_sha256": bank_sha256,
                    "contract_sha256": contract_sha256,
                    "seal_manifest_sha256": expected_manifest_sha256,
                    "provenance_valid": True,
                }
            )
            digest = _write_trace(path, record)
            print(
                f"[saved] {path.name} "
                f"{record['successful_steps']}/{record['requested_steps']} "
                f"tds_failed={record['tds_failed']} sha256={digest}",
                flush=True,
            )


def _summary_markdown(summary: dict[str, Any]) -> str:
    decision = summary["decision"]
    lines = [
        "# R273 storage-DAE feasibility attribution",
        "",
        f"**Classification:** {decision['classification']}",
        "",
        "| Scenario | Role | original V4 | storage zero |",
        "|---|---|---:|---:|",
    ]
    for item in summary["scenario_matrix"]:
        original = item["original_v4"]
        storage = item["storage_zero"]
        lines.append(
            f"| `{item['scenario']}` | {item['role']} | "
            f"{original['successful_steps']}/{original['requested_steps']} | "
            f"{storage['successful_steps']}/{storage['requested_steps']} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- completion vectors match: `{decision['completion_vectors_match']}`",
            "- all registered failures reproduced: "
            f"`{decision['all_registered_failures_reproduced']}`",
            f"- all controls complete: `{decision['all_controls_complete']}`",
            f"- reason: {decision['reason']}",
            "",
            "## Interpretation boundary",
            "",
            "This is completion/solver/DAE attribution only. No frequency "
            "performance endpoint or controller claim is evaluated.",
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
    manifest = _verify_seal(
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    records = []
    trace_hashes = {}
    scenario_matrix = []
    for case in manifest["cases"]:
        by_plant = {}
        for plant in PLANTS:
            path = _trace_path(out_dir, case["name"], plant)
            if not path.exists():
                raise FileNotFoundError(f"missing core trace: {path}")
            record = _validate_resumable_trace(
                path,
                case=case,
                plant=plant,
                bank_sha256=manifest["bank"]["sha256"],
                contract_sha256=manifest["contract"]["sha256"],
                seal_sha256=expected_manifest_sha256,
            )
            records.append(record)
            by_plant[plant] = {
                "completed": bool(record["completed"]),
                "tds_failed": bool(record["tds_failed"]),
                "successful_steps": int(record["successful_steps"]),
                "attempted_steps": int(record["attempted_steps"]),
                "requested_steps": int(record["requested_steps"]),
                "last_simulator_time": record["last_simulator_time"],
                "solver_messages": record["solver_messages"],
                "initial_dae": record["initial_dae"],
                "model_counts": record["model_counts"],
            }
            trace_hashes[str(path)] = sha256_file(path)
        scenario_matrix.append(
            {
                "scenario": case["name"],
                "role": case["role"],
                "delta_u": case["delta_u"],
                **by_plant,
            }
        )

    decision = classify_storage_dae_attribution(
        records,
        failure_scenarios=FAILURE_SCENARIOS,
        control_scenarios=CONTROL_SCENARIOS,
    )
    controller_counts = {
        plant: {
            "complete_count": sum(
                bool(row["completed"])
                for row in records
                if row["plant"] == plant
            ),
            "failure_count": sum(
                bool(row["tds_failed"])
                for row in records
                if row["plant"] == plant
            ),
        }
        for plant in PLANTS
    }
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "decision": decision,
        "controller_counts": controller_counts,
        "failure_scenarios": list(FAILURE_SCENARIOS),
        "control_scenarios": list(CONTROL_SCENARIOS),
        "scenario_matrix": scenario_matrix,
        "bank_sha256": manifest["bank"]["sha256"],
        "contract_sha256": manifest["contract"]["sha256"],
        "seal_manifest_sha256": expected_manifest_sha256,
        "trace_hashes": trace_hashes,
        "endpoint_boundary": manifest["endpoint_boundary"],
    }
    summary_path = out_dir / "storage_dae_feasibility_summary.json"
    summary_digest = _write_new_canonical(summary_path, summary)
    markdown_path = out_dir / "storage_dae_feasibility_summary.md"
    if markdown_path.exists():
        raise FileExistsError(
            f"refusing to overwrite immutable summary: {markdown_path}"
        )
    markdown_path.write_text(_summary_markdown(summary), encoding="utf-8")
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
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
        out_dir / "provenance.json",
        provenance,
    )
    print(
        json.dumps(
            {
                "classification": decision["classification"],
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
    seal_parser.add_argument("--bank", type=Path, required=True)
    seal_parser.add_argument("--expected-bank-sha256", required=True)
    seal_parser.add_argument("--contract", type=Path, required=True)
    seal_parser.add_argument("--expected-contract-sha256", required=True)
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
            bank_path=args.bank,
            expected_bank_sha256=args.expected_bank_sha256,
            contract_path=args.contract,
            expected_contract_sha256=args.expected_contract_sha256,
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
