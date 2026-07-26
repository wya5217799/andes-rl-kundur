"""Prepare, execute, resume, and analyse the prospective R272 authority gate."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.control.active_power import (  # noqa: E402
    r272_frozen_bess_contract,
)
from andes_rl_kundur.evaluation.active_power_authority import (  # noqa: E402
    R272_KI_SYSTEM_PU_PER_HZ_S_PER_DEVICE,
    R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE,
    classify_active_power_authority,
    run_active_power_scenario,
    summarise_active_power_trace,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    build_scenario_bank,
    canonical_json_bytes,
    empirical_upper_tail,
    load_scenario_bank,
    paired_bootstrap_contrasts,
    sha256_bytes,
    sha256_file,
    write_scenario_bank,
)

ROUND_ID = "R272"
BANK_N = 20
BANK_SEED = 2026072601
ENV_SEED = 42
STEPS = 300
FINAL_WINDOW_STEPS = 50
BOOTSTRAP_SEED = 2026072602
BOOTSTRAP_RESAMPLES = 10_000
PRIMARY_CONTROLLERS = ("zero_support", "droop_pi")
SECONDARY_CONTROLLER = "droop"
DEVELOPMENT_SCENARIOS = tuple(
    {
        "name": f"dev_PQ_0_{'neg' if magnitude < 0 else 'pos'}",
        "delta_u": {"PQ_0": magnitude},
    }
    for magnitude in (-1.5, 1.5)
)
CONTINUOUS_ENDPOINTS = (
    "vsg_mean_iae_hz_s",
    "final_window_common_abs_mean_hz",
    "terminal_common_abs_hz",
    "normalized_sync_loss_hz2",
    "worst_bus_peak_abs_hz",
    "max_abs_rocof_hz_s",
    "bess_command_l1_device_s",
    "bess_command_total_variation",
    "bess_saturation_fraction",
    "bess_min_soc",
    "bess_max_soc",
    "bess_charge_energy_mwh_total",
    "bess_discharge_energy_mwh_total",
)


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


def _contract_payload() -> dict[str, Any]:
    contract = r272_frozen_bess_contract()
    physical = asdict(contract)
    physical["source_ids"] = list(physical["source_ids"])
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "semantics": "four independent GFL ESD1 devices beside frozen PV+GENCLS VSG proxies",
        "physical": physical,
        "derived": {
            "device_power_mva": contract.device_power_mva,
            "device_energy_mwh": contract.device_energy_mwh,
            "device_power_limit_system_pu": contract.device_power_limit_system_pu,
            "device_ramp_limit_system_pu_per_s": (
                contract.device_ramp_limit_system_pu_per_s
            ),
            "initial_discharge_headroom_mwh": (
                contract.initial_discharge_headroom_mwh
            ),
            "initial_charge_headroom_mwh": contract.initial_charge_headroom_mwh,
            "round_trip_efficiency": contract.round_trip_efficiency,
        },
        "placement_buses": [12, 16, 14, 15],
        "vsg_md": {
            "M": [200.0] * 4,
            "D": [100.0] * 4,
            "normalized_action": [[0.0, 0.0]] * 4,
        },
        "controllers": {
            "zero_support": {"kp": 0.0, "ki": 0.0},
            "droop": {
                "kp_system_pu_per_hz_per_device": (
                    R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE
                ),
                "ki_system_pu_per_hz_s_per_device": 0.0,
            },
            "droop_pi": {
                "kp_system_pu_per_hz_per_device": (
                    R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE
                ),
                "ki_system_pu_per_hz_s_per_device": (
                    R272_KI_SYSTEM_PU_PER_HZ_S_PER_DEVICE
                ),
                "anti_windup": "conditional freeze when the previous projection saturates in the same direction",
            },
        },
        "timing": {
            "control_interval_s": 0.2,
            "steps": STEPS,
            "horizon_s": STEPS * 0.2,
            "final_window_steps": FINAL_WINDOW_STEPS,
            "final_window_s": FINAL_WINDOW_STEPS * 0.2,
        },
        "formal": {
            "bank_n": BANK_N,
            "bank_seed": BANK_SEED,
            "environment_seed": ENV_SEED,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "primary_controllers": list(PRIMARY_CONTROLLERS),
        },
    }


def prepare_contract(path: Path) -> None:
    digest = _write_new_canonical(path, _contract_payload())
    print(digest)


def prepare_bank(path: Path) -> None:
    generator_source = (
        ROOT / "src/andes_rl_kundur/evaluation/paper_strict_eval.py"
    )
    payload = build_scenario_bank(
        n=BANK_N,
        seed=BANK_SEED,
        repository_head=_git_head(),
        generator_source_sha256=sha256_file(generator_source),
    )
    digest = write_scenario_bank(path, payload)
    print(digest)


def _source_paths() -> dict[str, Path]:
    return {
        "active_power_contract": (
            ROOT / "src/andes_rl_kundur/control/active_power.py"
        ),
        "storage_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py"
        ),
        "authority_evaluator": (
            ROOT / "src/andes_rl_kundur/evaluation/active_power_authority.py"
        ),
        "physical_endpoints": (
            ROOT / "src/andes_rl_kundur/evaluation/physical_endpoints.py"
        ),
        "sealed_bank": (
            ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py"
        ),
        "v4_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py"
        ),
        "base_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/base_env.py"
        ),
        "runner": Path(__file__).resolve(),
        "andes_esd1": Path(
            "/home/wya/andes_venv/lib/python3.12/site-packages/andes/models/distributed/esd1.py"
        ),
        "andes_pvd1": Path(
            "/home/wya/andes_venv/lib/python3.12/site-packages/andes/models/distributed/pvd1.py"
        ),
        "andes_group": Path(
            "/home/wya/andes_venv/lib/python3.12/site-packages/andes/models/group.py"
        ),
    }


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
    source_hashes = {
        name: {
            "path": str(path),
            "sha256": sha256_file(path),
        }
        for name, path in _source_paths().items()
    }
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "repository_head": _git_head(),
        "bank": {
            "path": str(bank_path),
            "sha256": bank_digest,
            "scenario_count": bank["scenario_count"],
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
        "sources": source_hashes,
        "packages": {
            "andes": importlib.metadata.version("andes"),
            "numpy": importlib.metadata.version("numpy"),
        },
        "execution": {
            "controllers": list(PRIMARY_CONTROLLERS),
            "steps": STEPS,
            "final_window_steps": FINAL_WINDOW_STEPS,
            "environment_seed": ENV_SEED,
        },
    }
    digest = _write_new_canonical(manifest_path, payload)
    print(digest)


def _verify_seal(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
) -> dict[str, Any]:
    manifest = _load_json_with_hash(manifest_path, expected_manifest_sha256)
    if manifest.get("round") != ROUND_ID:
        raise ValueError("seal round mismatch")
    for item in manifest["sources"].values():
        path = Path(item["path"])
        actual = sha256_file(path)
        if actual != item["sha256"]:
            raise ValueError(f"sealed source drift: {path}")
    for key in ("bank", "contract", "plan"):
        item = manifest[key]
        if sha256_file(Path(item["path"])) != item["sha256"]:
            raise ValueError(f"sealed {key} drift: {item['path']}")
    return manifest


def _trace_path(out_dir: Path, scenario_name: str, controller: str) -> Path:
    return out_dir / "traces" / f"{scenario_name}__{controller}.json"


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
    scenario: dict[str, Any],
    controller: str,
    bank_sha256: str | None,
    contract_sha256: str | None,
    seal_sha256: str | None,
) -> None:
    record = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "scenario": scenario["name"],
        "controller": controller,
        "delta_u": scenario["delta_u"],
        "bank_sha256": bank_sha256,
        "contract_sha256": contract_sha256,
        "seal_manifest_sha256": seal_sha256,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"resume provenance mismatch in {path}: {key}")


def run_development(out_dir: Path, *, resume: bool) -> None:
    for scenario_index, scenario in enumerate(DEVELOPMENT_SCENARIOS):
        order = (
            PRIMARY_CONTROLLERS
            if scenario_index % 2 == 0
            else tuple(reversed(PRIMARY_CONTROLLERS))
        )
        for controller in order:
            path = _trace_path(out_dir, scenario["name"], controller)
            if path.exists():
                if not resume:
                    raise FileExistsError(f"development trace exists: {path}")
                _validate_resumable_trace(
                    path,
                    scenario=scenario,
                    controller=controller,
                    bank_sha256=None,
                    contract_sha256=None,
                    seal_sha256=None,
                )
                print(f"[resume] {path.name}")
                continue
            print(f"[development] {scenario['name']} / {controller}", flush=True)
            record = run_active_power_scenario(
                scenario["name"],
                scenario["delta_u"],
                controller_name=controller,
                seed=ENV_SEED,
                steps=STEPS,
            )
            record.update(
                {
                    "phase": "development",
                    "bank_sha256": None,
                    "contract_sha256": None,
                    "seal_manifest_sha256": None,
                }
            )
            digest = _write_trace(path, record)
            print(
                f"[saved] {path.name} {record['n_steps']}/{STEPS} "
                f"tds_failed={record['tds_failed']} sha256={digest}",
                flush=True,
            )


def evaluate(
    *,
    bank_path: Path,
    expected_bank_sha256: str,
    contract_path: Path,
    expected_contract_sha256: str,
    manifest_path: Path,
    expected_manifest_sha256: str,
    out_dir: Path,
    resume: bool,
) -> None:
    manifest = _verify_seal(
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    bank, bank_digest = load_scenario_bank(
        bank_path,
        expected_sha256=expected_bank_sha256,
    )
    _load_json_with_hash(contract_path, expected_contract_sha256)
    if manifest["bank"]["sha256"] != bank_digest:
        raise ValueError("bank does not match seal")
    if manifest["contract"]["sha256"] != expected_contract_sha256:
        raise ValueError("contract does not match seal")

    for scenario_index, scenario in enumerate(bank["scenarios"]):
        order = (
            PRIMARY_CONTROLLERS
            if scenario_index % 2 == 0
            else tuple(reversed(PRIMARY_CONTROLLERS))
        )
        for controller in order:
            path = _trace_path(out_dir, scenario["name"], controller)
            if path.exists():
                if not resume:
                    raise FileExistsError(f"formal trace exists: {path}")
                _validate_resumable_trace(
                    path,
                    scenario=scenario,
                    controller=controller,
                    bank_sha256=bank_digest,
                    contract_sha256=expected_contract_sha256,
                    seal_sha256=expected_manifest_sha256,
                )
                print(f"[resume] {path.name}", flush=True)
                continue

            print(
                f"[formal {scenario_index + 1:02d}/{BANK_N}] "
                f"{scenario['name']} / {controller}",
                flush=True,
            )
            record = run_active_power_scenario(
                scenario["name"],
                scenario["delta_u"],
                controller_name=controller,
                seed=ENV_SEED,
                steps=STEPS,
            )
            record.update(
                {
                    "phase": "formal",
                    "bank_sha256": bank_digest,
                    "contract_sha256": expected_contract_sha256,
                    "seal_manifest_sha256": expected_manifest_sha256,
                }
            )
            digest = _write_trace(path, record)
            print(
                f"[saved] {path.name} {record['n_steps']}/{STEPS} "
                f"tds_failed={record['tds_failed']} sha256={digest}",
                flush=True,
            )


def _controller_summary(
    records: list[dict[str, Any]],
    endpoint_rows: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    complete = [record["completed"] for record in records]
    failures = [record["tds_failed"] or not record["completed"] for record in records]
    if endpoint_rows:
        means = {
            endpoint: float(
                np.mean([row[endpoint] for _, row in endpoint_rows])
            )
            for endpoint in CONTINUOUS_ENDPOINTS
        }
        tails = {
            endpoint: empirical_upper_tail(
                {
                    scenario: float(row[endpoint])
                    for scenario, row in endpoint_rows
                }
            )
            for endpoint in (
                "vsg_mean_iae_hz_s",
                "final_window_common_abs_mean_hz",
                "worst_bus_peak_abs_hz",
                "max_abs_rocof_hz_s",
            )
        }
    else:
        means = {endpoint: None for endpoint in CONTINUOUS_ENDPOINTS}
        tails = {
            endpoint: None
            for endpoint in (
                "vsg_mean_iae_hz_s",
                "final_window_common_abs_mean_hz",
                "worst_bus_peak_abs_hz",
                "max_abs_rocof_hz_s",
            )
        }
    constraint_violations = sum(
        len(step.get("bess_constraint_violations", []))
        for record in records
        for step in record.get("traces", [])
    )
    return {
        "scenario_count": len(records),
        "complete_count": int(sum(complete)),
        "failure_count": int(sum(failures)),
        "paired_endpoint_count": len(endpoint_rows),
        "constraint_violation_count": int(constraint_violations),
        "means": means,
        "tails": tails,
    }


def _summary_markdown(summary: dict[str, Any]) -> str:
    decision = summary["decision"]
    lines = [
        "# R272 active-power authority summary",
        "",
        f"**Classification:** {decision['classification']}",
        "",
        "| Controller | complete | failures | paired endpoints | constraint violations |",
        "|---|---:|---:|---:|---:|",
    ]
    for controller in PRIMARY_CONTROLLERS:
        controller_summary = summary["controllers"][controller]
        lines.append(
            f"| `{controller}` | {controller_summary['complete_count']} | "
            f"{controller_summary['failure_count']} | "
            f"{controller_summary['paired_endpoint_count']} | "
            f"{controller_summary['constraint_violation_count']} |"
        )
    lines.extend(["", "## Co-primary paired evidence", ""])
    contrast = summary["paired_bootstrap"].get("contrasts", {}).get(
        "primary_minus_baseline"
    )
    if contrast is None:
        lines.append(
            "Unavailable: no complete paired traces support physical endpoint statistics."
        )
    else:
        lines.extend(
            [
                "| Endpoint | zero support mean | droop+PI mean | effect (%) | 95% interval |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for endpoint in (
            "vsg_mean_iae_hz_s",
            "final_window_common_abs_mean_hz",
        ):
            effect = contrast["endpoints"][endpoint]["ratio_of_means_percent"]
            baseline = summary["controllers"]["zero_support"]["means"][endpoint]
            primary = summary["controllers"]["droop_pi"]["means"][endpoint]
            interval = effect["percentile_95_interval"]
            lines.append(
                f"| `{endpoint}` | {baseline:.9g} | {primary:.9g} | "
                f"{effect['point']:+.6f} | "
                f"[{interval[0]:+.6f}, {interval[1]:+.6f}] |"
            )
    lines.extend(
        [
            "",
            "## Guards",
            "",
            *[
                f"- {'PASS' if passed else 'FAIL'} — `{name}`"
                for name, passed in decision["guards"].items()
            ],
            "",
            "## Interpretation boundary",
            "",
            "This is a hybrid PV+GENCLS plus independent GFL ESD1 authority proxy. "
            "It is not unified GFM-BESS, EMT, fault-current, topology, or learning evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def analyse(
    *,
    bank_path: Path,
    expected_bank_sha256: str,
    contract_path: Path,
    expected_contract_sha256: str,
    manifest_path: Path,
    expected_manifest_sha256: str,
    out_dir: Path,
) -> None:
    manifest = _verify_seal(
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    bank, bank_digest = load_scenario_bank(
        bank_path,
        expected_sha256=expected_bank_sha256,
    )
    _load_json_with_hash(contract_path, expected_contract_sha256)
    records_by_controller: dict[str, list[dict[str, Any]]] = {
        controller: [] for controller in PRIMARY_CONTROLLERS
    }
    record_grid: dict[str, dict[str, dict[str, Any]]] = {}
    trace_hashes: dict[str, str] = {}
    for scenario in bank["scenarios"]:
        record_grid[scenario["name"]] = {}
        for controller in PRIMARY_CONTROLLERS:
            path = _trace_path(out_dir, scenario["name"], controller)
            if not path.exists():
                raise FileNotFoundError(f"missing formal trace: {path}")
            _validate_resumable_trace(
                path,
                scenario=scenario,
                controller=controller,
                bank_sha256=bank_digest,
                contract_sha256=expected_contract_sha256,
                seal_sha256=expected_manifest_sha256,
            )
            record = json.loads(path.read_text(encoding="utf-8"))
            records_by_controller[controller].append(record)
            record_grid[scenario["name"]][controller] = record
            trace_hashes[str(path)] = sha256_file(path)

    paired_scenarios = [
        scenario["name"]
        for scenario in bank["scenarios"]
        if all(
            record_grid[scenario["name"]][controller]["completed"]
            and not record_grid[scenario["name"]][controller]["tds_failed"]
            for controller in PRIMARY_CONTROLLERS
        )
    ]
    endpoints_by_controller: dict[
        str, list[tuple[str, dict[str, Any]]]
    ] = {controller: [] for controller in PRIMARY_CONTROLLERS}
    for scenario_name in paired_scenarios:
        for controller in PRIMARY_CONTROLLERS:
            endpoints_by_controller[controller].append(
                (
                    scenario_name,
                    summarise_active_power_trace(
                        record_grid[scenario_name][controller],
                        final_window_steps=FINAL_WINDOW_STEPS,
                    ),
                )
            )

    controller_summaries = {
        controller: _controller_summary(
            records_by_controller[controller],
            endpoints_by_controller[controller],
        )
        for controller in PRIMARY_CONTROLLERS
    }
    if paired_scenarios:
        bootstrap_input = {
            controller: {
                endpoint: [
                    float(row[endpoint])
                    for _, row in endpoints_by_controller[controller]
                ]
                for endpoint in CONTINUOUS_ENDPOINTS
            }
            for controller in PRIMARY_CONTROLLERS
        }
        paired = paired_bootstrap_contrasts(
            bootstrap_input,
            contrasts=(
                ("primary_minus_baseline", "droop_pi", "zero_support"),
            ),
            seed=BOOTSTRAP_SEED,
            n_resamples=BOOTSTRAP_RESAMPLES,
        )
        paired["available"] = True
        paired["paired_scenarios"] = paired_scenarios
        primary_contrast = paired["contrasts"]["primary_minus_baseline"]
    else:
        paired = {
            "available": False,
            "paired_scenarios": [],
            "unavailable_reason": "no scenario has two complete primary traces",
            "contrasts": {},
        }
        primary_contrast = None
    decision = classify_active_power_authority(
        controller_summaries=controller_summaries,
        primary_contrast=primary_contrast,
        total_scenarios=BANK_N,
        provenance_hashes_match=True,
    )
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "bank_sha256": bank_digest,
        "contract_sha256": expected_contract_sha256,
        "seal_manifest_sha256": expected_manifest_sha256,
        "controllers": controller_summaries,
        "paired_bootstrap": paired,
        "decision": decision,
        "trace_hashes": trace_hashes,
        "interpretation_boundary": (
            "hybrid PV+GENCLS plus independent GFL ESD1 authority proxy; "
            "not unified GFM-BESS, EMT, topology, or learning evidence"
        ),
    }
    summary_path = out_dir / "active_power_authority_summary.json"
    summary_digest = _write_new_canonical(summary_path, summary)
    markdown_path = out_dir / "active_power_authority_summary.md"
    if markdown_path.exists():
        raise FileExistsError(f"refusing to overwrite summary: {markdown_path}")
    markdown_path.write_text(_summary_markdown(summary), encoding="utf-8")
    provenance = {
        "round": ROUND_ID,
        "repository_head": _git_head(),
        "manifest": {
            "path": str(manifest_path),
            "sha256": expected_manifest_sha256,
            "payload": manifest,
        },
        "bank_sha256": bank_digest,
        "contract_sha256": expected_contract_sha256,
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

    contract_parser = subparsers.add_parser("prepare-contract")
    contract_parser.add_argument("--out", type=Path, required=True)

    bank_parser = subparsers.add_parser("prepare-bank")
    bank_parser.add_argument("--bank", type=Path, required=True)

    development_parser = subparsers.add_parser("development")
    development_parser.add_argument("--out-dir", type=Path, required=True)
    development_parser.add_argument("--resume", action="store_true")

    seal_parser = subparsers.add_parser("prepare-seal")
    seal_parser.add_argument("--bank", type=Path, required=True)
    seal_parser.add_argument("--expected-bank-sha256", required=True)
    seal_parser.add_argument("--contract", type=Path, required=True)
    seal_parser.add_argument("--expected-contract-sha256", required=True)
    seal_parser.add_argument("--plan", type=Path, required=True)
    seal_parser.add_argument("--manifest", type=Path, required=True)

    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("--bank", type=Path, required=True)
    evaluate_parser.add_argument("--expected-bank-sha256", required=True)
    evaluate_parser.add_argument("--contract", type=Path, required=True)
    evaluate_parser.add_argument("--expected-contract-sha256", required=True)
    evaluate_parser.add_argument("--manifest", type=Path, required=True)
    evaluate_parser.add_argument("--expected-manifest-sha256", required=True)
    evaluate_parser.add_argument("--out-dir", type=Path, required=True)
    evaluate_parser.add_argument("--resume", action="store_true")

    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--bank", type=Path, required=True)
    analyse_parser.add_argument("--expected-bank-sha256", required=True)
    analyse_parser.add_argument("--contract", type=Path, required=True)
    analyse_parser.add_argument("--expected-contract-sha256", required=True)
    analyse_parser.add_argument("--manifest", type=Path, required=True)
    analyse_parser.add_argument("--expected-manifest-sha256", required=True)
    analyse_parser.add_argument("--out-dir", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "prepare-contract":
        prepare_contract(args.out)
    elif args.command == "prepare-bank":
        prepare_bank(args.bank)
    elif args.command == "development":
        run_development(args.out_dir, resume=args.resume)
    elif args.command == "prepare-seal":
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
            bank_path=args.bank,
            expected_bank_sha256=args.expected_bank_sha256,
            contract_path=args.contract,
            expected_contract_sha256=args.expected_contract_sha256,
            manifest_path=args.manifest,
            expected_manifest_sha256=args.expected_manifest_sha256,
            out_dir=args.out_dir,
            resume=args.resume,
        )
    elif args.command == "analyse":
        analyse(
            bank_path=args.bank,
            expected_bank_sha256=args.expected_bank_sha256,
            contract_path=args.contract,
            expected_contract_sha256=args.expected_contract_sha256,
            manifest_path=args.manifest,
            expected_manifest_sha256=args.expected_manifest_sha256,
            out_dir=args.out_dir,
        )


if __name__ == "__main__":
    main()
