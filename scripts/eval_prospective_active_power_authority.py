"""Run the prospectively screened R274 active-power authority gate."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.active_power_authority import (  # noqa: E402
    R272_KI_SYSTEM_PU_PER_HZ_S_PER_DEVICE,
    R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE,
    classify_active_power_authority,
    run_active_power_scenario,
    summarise_active_power_trace,
)
from andes_rl_kundur.evaluation.prospective_authority import (  # noqa: E402
    R274_CANDIDATE_COUNT,
    assess_screened_authority_bank,
    audit_zero_support_screen_record,
    build_stratified_authority_candidates,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    empirical_upper_tail,
    load_scenario_bank,
    paired_binary_outcome_table,
    paired_bootstrap_contrasts,
    sha256_bytes,
    sha256_file,
    write_scenario_bank,
)

ROUND_ID = "R274"
CANDIDATE_SEED = 2026072603
ENV_SEED = 42
STEPS = 300
FINAL_WINDOW_STEPS = 50
BOOTSTRAP_SEED = 2026072602
BOOTSTRAP_RESAMPLES = 10_000
R272_CONTRACT_SHA256 = (
    "220559d9f6ae32fbce87c16552d75c7067481921072626ee8b627335a3e0ec4c"
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
CONTROLLERS = ("zero_support", "droop_pi")


class _MessageCollector(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


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
        "prospective_authority": (
            ROOT
            / "src/andes_rl_kundur/evaluation/prospective_authority.py"
        ),
        "feasibility_screen": (
            ROOT / "src/andes_rl_kundur/evaluation/feasibility_screen.py"
        ),
        "active_power_authority": (
            ROOT
            / "src/andes_rl_kundur/evaluation/active_power_authority.py"
        ),
        "physical_endpoints": (
            ROOT / "src/andes_rl_kundur/evaluation/physical_endpoints.py"
        ),
        "sealed_bank": (
            ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py"
        ),
        "active_power_contract": (
            ROOT / "src/andes_rl_kundur/control/active_power.py"
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
        "r272_runner": ROOT / "scripts/eval_active_power_authority.py",
        "r274_runner": Path(__file__).resolve(),
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


def _source_manifest() -> dict[str, dict[str, str]]:
    return {
        name: {"path": str(path), "sha256": sha256_file(path)}
        for name, path in _source_paths().items()
    }


def prepare_candidates(path: Path) -> None:
    generator_path = _source_paths()["prospective_authority"]
    bank = build_stratified_authority_candidates(
        seed=CANDIDATE_SEED,
        repository_head=_git_head(),
        generator_source_sha256=sha256_file(generator_path),
    )
    print(write_scenario_bank(path, bank))


def prepare_candidate_seal(
    *,
    bank_path: Path,
    expected_bank_sha256: str,
    contract_path: Path,
    expected_contract_sha256: str,
    plan_path: Path,
    manifest_path: Path,
) -> None:
    if expected_contract_sha256.lower() != R272_CONTRACT_SHA256:
        raise ValueError("R274 must reuse the exact R272 contract hash")
    bank, bank_digest = load_scenario_bank(
        bank_path,
        expected_sha256=expected_bank_sha256,
    )
    _load_json_with_hash(contract_path, expected_contract_sha256)
    expected_bank = build_stratified_authority_candidates(
        seed=CANDIDATE_SEED,
        repository_head=str(bank["repository_head"]),
        generator_source_sha256=sha256_file(
            _source_paths()["prospective_authority"]
        ),
    )
    if bank != expected_bank:
        raise ValueError("candidate bank does not match the frozen generator")
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "phase": "candidate-screen",
        "repository_head": _git_head(),
        "candidate_bank": {
            "path": str(bank_path),
            "sha256": bank_digest,
            "scenario_count": bank["scenario_count"],
        },
        "contract": {
            "path": str(contract_path),
            "sha256": expected_contract_sha256,
        },
        "plan": {
            "path": str(plan_path),
            "sha256": sha256_file(plan_path),
        },
        "sources": _source_manifest(),
        "packages": {
            "andes": importlib.metadata.version("andes"),
            "numpy": importlib.metadata.version("numpy"),
        },
        "execution": {
            "controller": "zero_support",
            "plant": "v4_plus_independent_esd1",
            "environment_seed": ENV_SEED,
            "steps": STEPS,
            "screen_endpoint_boundary": (
                "completion, solver, zero-power, SOC, M/D, constraint, "
                "stratum, and provenance only"
            ),
            "formal_controller_trace_count_at_freeze": 0,
        },
    }
    print(_write_new_canonical(manifest_path, payload))


def _verify_source_manifest(manifest: dict[str, Any]) -> None:
    for item in manifest["sources"].values():
        path = Path(item["path"])
        if sha256_file(path) != item["sha256"]:
            raise ValueError(f"sealed source drift: {path}")


def _verify_candidate_seal(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
) -> dict[str, Any]:
    manifest = _load_json_with_hash(
        manifest_path,
        expected_manifest_sha256,
    )
    if (
        manifest.get("round") != ROUND_ID
        or manifest.get("phase") != "candidate-screen"
    ):
        raise ValueError("candidate seal identity mismatch")
    _verify_source_manifest(manifest)
    for key in ("candidate_bank", "contract", "plan"):
        item = manifest[key]
        if sha256_file(Path(item["path"])) != item["sha256"]:
            raise ValueError(f"sealed {key} drift: {item['path']}")
    if manifest["contract"]["sha256"] != R272_CONTRACT_SHA256:
        raise ValueError("candidate seal does not use the R272 contract")
    return manifest


def _screen_trace_path(out_dir: Path, scenario_name: str) -> Path:
    return out_dir / "screen_traces" / f"{scenario_name}__zero_support.json"


def _formal_trace_path(out_dir: Path, scenario_name: str) -> Path:
    return out_dir / "formal_traces" / f"{scenario_name}__droop_pi.json"


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


def _validate_screen_trace(
    path: Path,
    *,
    scenario: dict[str, Any],
    bank_sha256: str,
    contract_sha256: str,
    candidate_seal_sha256: str,
) -> dict[str, Any]:
    record = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "scenario": scenario["name"],
        "controller": "zero_support",
        "delta_u": scenario["delta_u"],
        "phase": "screen",
        "candidate_bank_sha256": bank_sha256,
        "contract_sha256": contract_sha256,
        "candidate_seal_sha256": candidate_seal_sha256,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"screen trace provenance mismatch in {path}: {key}")
    if not bool(record.get("provenance_valid", False)):
        raise ValueError(f"invalid screen provenance: {path}")
    return record


def _run_zero_support_with_solver_messages(
    scenario: dict[str, Any],
) -> dict[str, Any]:
    collector = _MessageCollector()
    logger = logging.getLogger("andes.routines.tds")
    logger.addHandler(collector)
    try:
        try:
            record = run_active_power_scenario(
                scenario["name"],
                scenario["delta_u"],
                controller_name="zero_support",
                seed=ENV_SEED,
                steps=STEPS,
            )
        except Exception as exc:
            record = {
                "experiment": "r274_prospective_active_power_authority",
                "controller": "zero_support",
                "scenario": scenario["name"],
                "delta_u": dict(scenario["delta_u"]),
                "requested_steps": STEPS,
                "n_steps": 0,
                "tds_failed": True,
                "completed": False,
                "traces": [],
                "setup_error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
                "seed": ENV_SEED,
            }
    finally:
        logger.removeHandler(collector)
    record["solver_messages"] = collector.messages
    return record


def screen(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
    out_dir: Path,
    resume: bool,
) -> None:
    manifest = _verify_candidate_seal(
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    bank, bank_sha256 = load_scenario_bank(
        Path(manifest["candidate_bank"]["path"]),
        expected_sha256=manifest["candidate_bank"]["sha256"],
    )
    contract_sha256 = manifest["contract"]["sha256"]
    for index, scenario in enumerate(bank["scenarios"], start=1):
        path = _screen_trace_path(out_dir, scenario["name"])
        if path.exists():
            if not resume:
                raise FileExistsError(f"screen trace exists: {path}")
            _validate_screen_trace(
                path,
                scenario=scenario,
                bank_sha256=bank_sha256,
                contract_sha256=contract_sha256,
                candidate_seal_sha256=expected_manifest_sha256,
            )
            print(f"[resume] {path.name}", flush=True)
            continue
        print(
            f"[screen {index:02d}/{len(bank['scenarios']):02d}] "
            f"{scenario['name']} / zero_support",
            flush=True,
        )
        record = _run_zero_support_with_solver_messages(scenario)
        record.update(
            {
                "round": ROUND_ID,
                "phase": "screen",
                "location": scenario["location"],
                "sign": scenario["sign"],
                "severity": scenario["severity"],
                "candidate_bank_sha256": bank_sha256,
                "contract_sha256": contract_sha256,
                "candidate_seal_sha256": expected_manifest_sha256,
                "provenance_valid": True,
            }
        )
        digest = _write_trace(path, record)
        print(
            f"[saved] {path.name} {record['n_steps']}/{STEPS} "
            f"completed={record['completed']} sha256={digest}",
            flush=True,
        )


def _formal_trace_count(out_dir: Path) -> int:
    directory = out_dir / "formal_traces"
    return len(list(directory.glob("*.json"))) if directory.exists() else 0


def analyse_screen(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
    out_dir: Path,
) -> None:
    manifest = _verify_candidate_seal(
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    bank, bank_sha256 = load_scenario_bank(
        Path(manifest["candidate_bank"]["path"]),
        expected_sha256=manifest["candidate_bank"]["sha256"],
    )
    contract_sha256 = manifest["contract"]["sha256"]
    audits = []
    trace_hashes = {}
    solver_rows = []
    for scenario in bank["scenarios"]:
        path = _screen_trace_path(out_dir, scenario["name"])
        if not path.exists():
            raise FileNotFoundError(f"missing screen trace: {path}")
        record = _validate_screen_trace(
            path,
            scenario=scenario,
            bank_sha256=bank_sha256,
            contract_sha256=contract_sha256,
            candidate_seal_sha256=expected_manifest_sha256,
        )
        digest = sha256_file(path)
        audits.append(
            audit_zero_support_screen_record(
                record,
                trace_sha256=digest,
            )
        )
        trace_hashes[str(path)] = digest
        solver_rows.append(
            {
                "scenario": scenario["name"],
                "completed": bool(record["completed"]),
                "tds_failed": bool(record["tds_failed"]),
                "n_steps": int(record["n_steps"]),
                "requested_steps": int(record["requested_steps"]),
                "solver_messages": list(record.get("solver_messages", [])),
                "setup_error": record.get("setup_error"),
            }
        )
    evidence = {
        "schema_version": 1,
        "round": ROUND_ID,
        "phase": "completion-only-screen",
        "candidate_bank_sha256": bank_sha256,
        "contract_sha256": contract_sha256,
        "candidate_seal_sha256": expected_manifest_sha256,
        "controller_performance_endpoints_inspected": False,
        "rows": audits,
        "solver_rows": solver_rows,
        "trace_hashes": trace_hashes,
    }
    evidence_path = out_dir / "screen_evidence.json"
    evidence_sha256 = _write_new_canonical(evidence_path, evidence)
    assessment = assess_screened_authority_bank(
        bank,
        audits,
        generated_bank_sha256=bank_sha256,
        completion_evidence_sha256=evidence_sha256,
        controller_trace_count=_formal_trace_count(out_dir),
    )
    formal_bank_path = out_dir / "formal_bank.json"
    formal_bank_sha256 = write_scenario_bank(
        formal_bank_path,
        assessment["formal_bank"],
    )
    contract_path = out_dir / "feasibility_screen_contract.json"
    screen_contract_sha256 = _write_new_canonical(
        contract_path,
        assessment["feasibility_contract"],
    )
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "phase": "completion-only-screen",
        "decision": assessment["decision"],
        "generated_nontriviality": assessment["generated_nontriviality"],
        "included_nontriviality": assessment["included_nontriviality"],
        "row_decisions": assessment["row_decisions"],
        "candidate_bank_sha256": bank_sha256,
        "candidate_seal_sha256": expected_manifest_sha256,
        "contract_sha256": contract_sha256,
        "screen_evidence_sha256": evidence_sha256,
        "screen_contract_sha256": screen_contract_sha256,
        "formal_bank_sha256": formal_bank_sha256,
        "controller_performance_endpoints_inspected": False,
        "controller_trace_count_at_freeze": _formal_trace_count(out_dir),
    }
    summary_path = out_dir / "screen_summary.json"
    summary_sha256 = _write_new_canonical(summary_path, summary)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "phase": "completion-only-screen",
        "repository_head": manifest["repository_head"],
        "candidate_manifest": {
            "path": str(manifest_path),
            "sha256": expected_manifest_sha256,
            "payload": manifest,
        },
        "candidate_bank_sha256": bank_sha256,
        "contract_sha256": contract_sha256,
        "screen_evidence_sha256": evidence_sha256,
        "screen_contract_sha256": screen_contract_sha256,
        "formal_bank_sha256": formal_bank_sha256,
        "screen_summary_sha256": summary_sha256,
        "trace_hashes": trace_hashes,
    }
    provenance_sha256 = _write_new_canonical(
        out_dir / "screen_provenance.json",
        provenance,
    )
    print(
        json.dumps(
            {
                "classification": assessment["decision"]["classification"],
                "included_count": assessment["formal_bank"]["scenario_count"],
                "excluded_count": assessment["included_nontriviality"][
                    "excluded_count"
                ],
                "screen_summary_sha256": summary_sha256,
                "formal_bank_sha256": formal_bank_sha256,
                "provenance_sha256": provenance_sha256,
            },
            indent=2,
        )
    )


def _verify_screen_trace_hashes(provenance: dict[str, Any]) -> None:
    for path_text, expected in provenance["trace_hashes"].items():
        path = Path(path_text)
        if sha256_file(path) != expected:
            raise ValueError(f"screen trace hash drift: {path}")


def prepare_formal_seal(
    *,
    candidate_manifest_path: Path,
    expected_candidate_manifest_sha256: str,
    screen_summary_path: Path,
    expected_screen_summary_sha256: str,
    screen_contract_path: Path,
    expected_screen_contract_sha256: str,
    screen_provenance_path: Path,
    expected_screen_provenance_sha256: str,
    formal_bank_path: Path,
    expected_formal_bank_sha256: str,
    out_dir: Path,
    manifest_path: Path,
) -> None:
    candidate_manifest = _verify_candidate_seal(
        manifest_path=candidate_manifest_path,
        expected_manifest_sha256=expected_candidate_manifest_sha256,
    )
    summary = _load_json_with_hash(
        screen_summary_path,
        expected_screen_summary_sha256,
    )
    if summary["decision"]["classification"] != "PASS":
        raise ValueError("formal seal requires a passing screen")
    contract = _load_json_with_hash(
        screen_contract_path,
        expected_screen_contract_sha256,
    )
    provenance = _load_json_with_hash(
        screen_provenance_path,
        expected_screen_provenance_sha256,
    )
    _verify_screen_trace_hashes(provenance)
    formal_bank, formal_bank_sha256 = load_scenario_bank(
        formal_bank_path,
        expected_sha256=expected_formal_bank_sha256,
    )
    if _formal_trace_count(out_dir) != 0:
        raise ValueError(
            "formal seal must be frozen before any droop+PI controller trace"
        )
    if contract["controller_trace_count_at_freeze"] != 0:
        raise ValueError("screen contract was not frozen prospectively")
    included_names = {
        row["scenario"]
        for row in summary["row_decisions"]
        if row["eligible"]
    }
    if included_names != {
        row["name"] for row in formal_bank["scenarios"]
    }:
        raise ValueError("formal bank differs from all-and-only screen subset")
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "phase": "formal-controller",
        "repository_head": _git_head(),
        "candidate_manifest": {
            "path": str(candidate_manifest_path),
            "sha256": expected_candidate_manifest_sha256,
        },
        "candidate_bank": candidate_manifest["candidate_bank"],
        "contract": candidate_manifest["contract"],
        "plan": candidate_manifest["plan"],
        "screen_summary": {
            "path": str(screen_summary_path),
            "sha256": expected_screen_summary_sha256,
        },
        "screen_contract": {
            "path": str(screen_contract_path),
            "sha256": expected_screen_contract_sha256,
        },
        "screen_provenance": {
            "path": str(screen_provenance_path),
            "sha256": expected_screen_provenance_sha256,
        },
        "formal_bank": {
            "path": str(formal_bank_path),
            "sha256": formal_bank_sha256,
            "scenario_count": formal_bank["scenario_count"],
        },
        "frozen_baseline_trace_hashes": provenance["trace_hashes"],
        "sources": _source_manifest(),
        "packages": candidate_manifest["packages"],
        "execution": {
            "candidate_controller": "droop_pi",
            "kp_system_pu_per_hz_per_device": (
                R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE
            ),
            "ki_system_pu_per_hz_s_per_device": (
                R272_KI_SYSTEM_PU_PER_HZ_S_PER_DEVICE
            ),
            "environment_seed": ENV_SEED,
            "steps": STEPS,
            "final_window_steps": FINAL_WINDOW_STEPS,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "controller_trace_count_at_freeze": 0,
        },
    }
    print(_write_new_canonical(manifest_path, payload))


def _verify_formal_seal(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = _load_json_with_hash(
        manifest_path,
        expected_manifest_sha256,
    )
    if (
        manifest.get("round") != ROUND_ID
        or manifest.get("phase") != "formal-controller"
    ):
        raise ValueError("formal seal identity mismatch")
    _verify_source_manifest(manifest)
    candidate_manifest = _verify_candidate_seal(
        manifest_path=Path(manifest["candidate_manifest"]["path"]),
        expected_manifest_sha256=manifest["candidate_manifest"]["sha256"],
    )
    for key in (
        "screen_summary",
        "screen_contract",
        "screen_provenance",
        "formal_bank",
    ):
        item = manifest[key]
        if sha256_file(Path(item["path"])) != item["sha256"]:
            raise ValueError(f"sealed {key} drift: {item['path']}")
    for path_text, expected in manifest["frozen_baseline_trace_hashes"].items():
        if sha256_file(Path(path_text)) != expected:
            raise ValueError(f"frozen baseline trace drift: {path_text}")
    return manifest, candidate_manifest


def _validate_formal_trace(
    path: Path,
    *,
    scenario: dict[str, Any],
    formal_bank_sha256: str,
    contract_sha256: str,
    formal_seal_sha256: str,
) -> dict[str, Any]:
    record = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "scenario": scenario["name"],
        "controller": "droop_pi",
        "delta_u": scenario["delta_u"],
        "phase": "formal-candidate",
        "formal_bank_sha256": formal_bank_sha256,
        "contract_sha256": contract_sha256,
        "formal_seal_sha256": formal_seal_sha256,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"formal trace provenance mismatch in {path}: {key}")
    if not bool(record.get("provenance_valid", False)):
        raise ValueError(f"invalid formal trace provenance: {path}")
    return record


def evaluate(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
    out_dir: Path,
    resume: bool,
) -> None:
    manifest, _ = _verify_formal_seal(
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    formal_bank, formal_bank_sha256 = load_scenario_bank(
        Path(manifest["formal_bank"]["path"]),
        expected_sha256=manifest["formal_bank"]["sha256"],
    )
    contract_sha256 = manifest["contract"]["sha256"]
    for index, scenario in enumerate(formal_bank["scenarios"], start=1):
        path = _formal_trace_path(out_dir, scenario["name"])
        if path.exists():
            if not resume:
                raise FileExistsError(f"formal trace exists: {path}")
            _validate_formal_trace(
                path,
                scenario=scenario,
                formal_bank_sha256=formal_bank_sha256,
                contract_sha256=contract_sha256,
                formal_seal_sha256=expected_manifest_sha256,
            )
            print(f"[resume] {path.name}", flush=True)
            continue
        print(
            f"[formal {index:02d}/{formal_bank['scenario_count']:02d}] "
            f"{scenario['name']} / droop_pi",
            flush=True,
        )
        record = run_active_power_scenario(
            scenario["name"],
            scenario["delta_u"],
            controller_name="droop_pi",
            seed=ENV_SEED,
            steps=STEPS,
        )
        record.update(
            {
                "round": ROUND_ID,
                "phase": "formal-candidate",
                "location": scenario["location"],
                "sign": scenario["sign"],
                "severity": scenario["severity"],
                "formal_bank_sha256": formal_bank_sha256,
                "contract_sha256": contract_sha256,
                "formal_seal_sha256": expected_manifest_sha256,
                "provenance_valid": True,
            }
        )
        digest = _write_trace(path, record)
        print(
            f"[saved] {path.name} {record['n_steps']}/{STEPS} "
            f"completed={record['completed']} sha256={digest}",
            flush=True,
        )


def _controller_summary(
    records: list[dict[str, Any]],
    endpoint_rows: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
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
    failures = [
        bool(record["tds_failed"]) or not bool(record["completed"])
        for record in records
    ]
    violations = sum(
        len(step.get("bess_constraint_violations", []))
        for record in records
        for step in record.get("traces", [])
    )
    return {
        "scenario_count": len(records),
        "complete_count": sum(bool(record["completed"]) for record in records),
        "failure_count": sum(failures),
        "paired_endpoint_count": len(endpoint_rows),
        "constraint_violation_count": violations,
        "means": means,
        "tails": tails,
    }


def _flatten_steps(
    records: list[dict[str, Any]],
    field: str,
) -> np.ndarray:
    return np.asarray(
        [
            value
            for record in records
            for step in record.get("traces", [])
            for value in step.get(field, [])
        ],
        dtype=float,
    )


def _physical_contract_audit(
    records_by_controller: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    by_controller = {}
    all_guards = []
    for controller, records in records_by_controller.items():
        requested = _flatten_steps(
            records,
            "bess_requested_power_system_pu",
        )
        commanded = _flatten_steps(
            records,
            "bess_commanded_power_system_pu",
        )
        actual = _flatten_steps(
            records,
            "bess_actual_power_system_pu",
        )
        soc = _flatten_steps(records, "bess_soc")
        m_values = _flatten_steps(records, "M_es")
        d_values = _flatten_steps(records, "D_es")
        actions = np.asarray(
            [
                value
                for record in records
                for step in record.get("traces", [])
                for agent in step.get("action_norm", [])
                for value in agent
            ],
            dtype=float,
        )
        violations = [
            violation
            for record in records
            for step in record.get("traces", [])
            for violation in step.get("bess_constraint_violations", [])
        ]
        saturation_reason_count = sum(
            bool(reason)
            for record in records
            for step in record.get("traces", [])
            for reasons in step.get("bess_saturation_reasons", [])
            for reason in reasons
        )
        expected_config = (
            {
                "kp_system_pu_per_hz_per_device": 0.0,
                "ki_system_pu_per_hz_s_per_device": 0.0,
            }
            if controller == "zero_support"
            else {
                "kp_system_pu_per_hz_per_device": (
                    R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE
                ),
                "ki_system_pu_per_hz_s_per_device": (
                    R272_KI_SYSTEM_PU_PER_HZ_S_PER_DEVICE
                ),
            }
        )
        controller_config_valid = all(
            record.get("controller_config") == expected_config
            for record in records
        )
        m_unique = sorted(set(m_values.tolist()))
        d_unique = sorted(set(d_values.tolist()))
        max_requested = (
            float(np.max(np.abs(requested))) if requested.size else None
        )
        max_commanded = (
            float(np.max(np.abs(commanded))) if commanded.size else None
        )
        max_actual = float(np.max(np.abs(actual))) if actual.size else None
        min_soc = float(np.min(soc)) if soc.size else None
        max_soc = float(np.max(soc)) if soc.size else None
        guards = {
            "controller_config_frozen": controller_config_valid,
            "vsg_md_frozen_200_100": (
                m_unique == [200.0] and d_unique == [100.0]
            ),
            "vsg_normalized_action_zero": (
                bool(actions.size)
                and float(np.max(np.abs(actions))) == 0.0
            ),
            "zero_constraint_violations": not violations,
            "soc_within_0_20_0_80": (
                min_soc is not None
                and max_soc is not None
                and min_soc >= 0.20
                and max_soc <= 0.80
            ),
            "command_within_device_power_limit": (
                max_commanded is not None and max_commanded <= 0.36 + 1e-9
            ),
            "actual_within_device_power_limit": (
                max_actual is not None and max_actual <= 0.36 + 1e-9
            ),
            "physical_frequency_basis": all(
                record.get("metric_frequency_basis")
                == "andes_physical_hz"
                for record in records
            ),
        }
        all_guards.extend(guards.values())
        by_controller[controller] = {
            "guards": guards,
            "max_abs_requested_power_system_pu": max_requested,
            "max_abs_commanded_power_system_pu": max_commanded,
            "max_abs_actual_power_system_pu": max_actual,
            "min_soc": min_soc,
            "max_soc": max_soc,
            "m_unique": m_unique,
            "d_unique": d_unique,
            "vsg_action_max_abs": (
                float(np.max(np.abs(actions))) if actions.size else None
            ),
            "constraint_violation_count": len(violations),
            "saturation_reason_count": saturation_reason_count,
        }
    return {
        "all_guards_pass": all(all_guards),
        "by_controller": by_controller,
    }


def _summary_markdown(summary: dict[str, Any]) -> str:
    decision = summary["decision"]
    lines = [
        "# R274 prospectively screened active-power authority",
        "",
        f"**Classification:** {decision['classification']}",
        "",
        "| Controller | complete | failures | paired endpoints | violations |",
        "|---|---:|---:|---:|---:|",
    ]
    for controller in CONTROLLERS:
        row = summary["controllers"][controller]
        lines.append(
            f"| `{controller}` | {row['complete_count']} | "
            f"{row['failure_count']} | {row['paired_endpoint_count']} | "
            f"{row['constraint_violation_count']} |"
        )
    contrast = summary["paired_bootstrap"].get("contrasts", {}).get(
        "primary_minus_baseline"
    )
    lines.extend(["", "## Co-primary evidence", ""])
    if contrast is None:
        lines.append("No complete paired endpoint contrast is available.")
    else:
        lines.extend(
            [
                "| Endpoint | zero support | droop+PI | effect | 95% interval |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for endpoint in (
            "vsg_mean_iae_hz_s",
            "final_window_common_abs_mean_hz",
        ):
            effect = contrast["endpoints"][endpoint][
                "ratio_of_means_percent"
            ]
            interval = effect["percentile_95_interval"]
            lines.append(
                f"| `{endpoint}` | "
                f"{summary['controllers']['zero_support']['means'][endpoint]:.9g} | "
                f"{summary['controllers']['droop_pi']['means'][endpoint]:.9g} | "
                f"{effect['point']:+.6f}% | "
                f"[{interval[0]:+.6f}, {interval[1]:+.6f}] |"
            )
    lines.extend(
        [
            "",
            "## Prospective screen",
            "",
            f"- included: `{summary['screen']['included_count']}`",
            f"- excluded and retained: `{summary['screen']['excluded_count']}`",
            f"- excluded fraction: `{summary['screen']['excluded_fraction']:.6f}`",
            "",
            "## Interpretation boundary",
            "",
            "This is a hybrid PV+GENCLS plus independent GFL ESD1 authority "
            "proxy. It is not unified GFM-BESS, learning, topology, EMT, "
            "fault-current, cross-simulator, HIL, or deployment evidence.",
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
    manifest, candidate_manifest = _verify_formal_seal(
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    formal_bank, formal_bank_sha256 = load_scenario_bank(
        Path(manifest["formal_bank"]["path"]),
        expected_sha256=manifest["formal_bank"]["sha256"],
    )
    candidate_bank, candidate_bank_sha256 = load_scenario_bank(
        Path(candidate_manifest["candidate_bank"]["path"]),
        expected_sha256=candidate_manifest["candidate_bank"]["sha256"],
    )
    candidate_by_name = {
        row["name"]: row for row in candidate_bank["scenarios"]
    }
    contract_sha256 = manifest["contract"]["sha256"]
    records_by_controller = {controller: [] for controller in CONTROLLERS}
    record_grid = {}
    trace_hashes = {}
    for scenario in formal_bank["scenarios"]:
        name = scenario["name"]
        baseline_path = _screen_trace_path(out_dir, name)
        baseline = _validate_screen_trace(
            baseline_path,
            scenario=candidate_by_name[name],
            bank_sha256=candidate_bank_sha256,
            contract_sha256=contract_sha256,
            candidate_seal_sha256=manifest["candidate_manifest"]["sha256"],
        )
        candidate_path = _formal_trace_path(out_dir, name)
        if not candidate_path.exists():
            raise FileNotFoundError(f"missing formal trace: {candidate_path}")
        candidate = _validate_formal_trace(
            candidate_path,
            scenario=scenario,
            formal_bank_sha256=formal_bank_sha256,
            contract_sha256=contract_sha256,
            formal_seal_sha256=expected_manifest_sha256,
        )
        record_grid[name] = {
            "zero_support": baseline,
            "droop_pi": candidate,
        }
        records_by_controller["zero_support"].append(baseline)
        records_by_controller["droop_pi"].append(candidate)
        trace_hashes[str(baseline_path)] = sha256_file(baseline_path)
        trace_hashes[str(candidate_path)] = sha256_file(candidate_path)

    paired_scenarios = [
        scenario["name"]
        for scenario in formal_bank["scenarios"]
        if all(
            record_grid[scenario["name"]][controller]["completed"]
            and not record_grid[scenario["name"]][controller]["tds_failed"]
            for controller in CONTROLLERS
        )
    ]
    endpoints_by_controller = {controller: [] for controller in CONTROLLERS}
    for scenario_name in paired_scenarios:
        for controller in CONTROLLERS:
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
        for controller in CONTROLLERS
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
            for controller in CONTROLLERS
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
            "contrasts": {},
            "unavailable_reason": "no complete primary pair",
        }
        primary_contrast = None
    decision = classify_active_power_authority(
        controller_summaries=controller_summaries,
        primary_contrast=primary_contrast,
        total_scenarios=formal_bank["scenario_count"],
        provenance_hashes_match=True,
    )
    physical_audit = _physical_contract_audit(records_by_controller)
    if not physical_audit["all_guards_pass"]:
        decision = {
            **decision,
            "classification": "INVALID",
            "reason": "one or more frozen R272 physical-contract audits failed",
        }
    screen_summary = _load_json_with_hash(
        Path(manifest["screen_summary"]["path"]),
        manifest["screen_summary"]["sha256"],
    )
    baseline_success = [
        bool(record_grid[scenario["name"]]["zero_support"]["completed"])
        for scenario in formal_bank["scenarios"]
    ]
    candidate_success = [
        bool(record_grid[scenario["name"]]["droop_pi"]["completed"])
        for scenario in formal_bank["scenarios"]
    ]
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "decision": decision,
        "screen": {
            "candidate_count": R274_CANDIDATE_COUNT,
            "included_count": formal_bank["scenario_count"],
            "excluded_count": screen_summary["included_nontriviality"][
                "excluded_count"
            ],
            "excluded_fraction": screen_summary["included_nontriviality"][
                "excluded_fraction"
            ],
            "decision": screen_summary["decision"],
            "generated_nontriviality": screen_summary[
                "generated_nontriviality"
            ],
            "included_nontriviality": screen_summary[
                "included_nontriviality"
            ],
            "row_decisions": screen_summary["row_decisions"],
        },
        "controllers": controller_summaries,
        "completion_pairing": paired_binary_outcome_table(
            candidate_success,
            baseline_success,
        ),
        "paired_bootstrap": paired,
        "physical_contract_audit": physical_audit,
        "formal_bank_sha256": formal_bank_sha256,
        "candidate_bank_sha256": candidate_bank_sha256,
        "contract_sha256": contract_sha256,
        "formal_seal_sha256": expected_manifest_sha256,
        "trace_hashes": trace_hashes,
        "interpretation_boundary": (
            "hybrid PV+GENCLS plus independent GFL ESD1 authority proxy; "
            "not unified GFM-BESS, learning, topology, EMT, HIL, or deployment"
        ),
    }
    summary_path = out_dir / "active_power_authority_summary.json"
    summary_sha256 = _write_new_canonical(summary_path, summary)
    markdown_path = out_dir / "active_power_authority_summary.md"
    if markdown_path.exists():
        raise FileExistsError(f"refusing to overwrite summary: {markdown_path}")
    markdown_path.write_text(_summary_markdown(summary), encoding="utf-8")
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "repository_head": manifest["repository_head"],
        "formal_manifest": {
            "path": str(manifest_path),
            "sha256": expected_manifest_sha256,
            "payload": manifest,
        },
        "summary_sha256": summary_sha256,
        "summary_markdown_sha256": sha256_file(markdown_path),
        "trace_hashes": trace_hashes,
    }
    provenance_sha256 = _write_new_canonical(
        out_dir / "provenance.json",
        provenance,
    )
    print(
        json.dumps(
            {
                "classification": decision["classification"],
                "paired_count": len(paired_scenarios),
                "summary_sha256": summary_sha256,
                "provenance_sha256": provenance_sha256,
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    candidates_parser = subparsers.add_parser("prepare-candidates")
    candidates_parser.add_argument("--out", type=Path, required=True)

    candidate_seal_parser = subparsers.add_parser("prepare-candidate-seal")
    candidate_seal_parser.add_argument("--bank", type=Path, required=True)
    candidate_seal_parser.add_argument("--expected-bank-sha256", required=True)
    candidate_seal_parser.add_argument("--contract", type=Path, required=True)
    candidate_seal_parser.add_argument(
        "--expected-contract-sha256",
        required=True,
    )
    candidate_seal_parser.add_argument("--plan", type=Path, required=True)
    candidate_seal_parser.add_argument("--manifest", type=Path, required=True)

    screen_parser = subparsers.add_parser("screen")
    screen_parser.add_argument("--manifest", type=Path, required=True)
    screen_parser.add_argument("--expected-manifest-sha256", required=True)
    screen_parser.add_argument("--out-dir", type=Path, required=True)
    screen_parser.add_argument("--resume", action="store_true")

    analyse_screen_parser = subparsers.add_parser("analyse-screen")
    analyse_screen_parser.add_argument("--manifest", type=Path, required=True)
    analyse_screen_parser.add_argument(
        "--expected-manifest-sha256",
        required=True,
    )
    analyse_screen_parser.add_argument("--out-dir", type=Path, required=True)

    formal_seal_parser = subparsers.add_parser("prepare-formal-seal")
    formal_seal_parser.add_argument(
        "--candidate-manifest",
        type=Path,
        required=True,
    )
    formal_seal_parser.add_argument(
        "--expected-candidate-manifest-sha256",
        required=True,
    )
    formal_seal_parser.add_argument(
        "--screen-summary",
        type=Path,
        required=True,
    )
    formal_seal_parser.add_argument(
        "--expected-screen-summary-sha256",
        required=True,
    )
    formal_seal_parser.add_argument(
        "--screen-contract",
        type=Path,
        required=True,
    )
    formal_seal_parser.add_argument(
        "--expected-screen-contract-sha256",
        required=True,
    )
    formal_seal_parser.add_argument(
        "--screen-provenance",
        type=Path,
        required=True,
    )
    formal_seal_parser.add_argument(
        "--expected-screen-provenance-sha256",
        required=True,
    )
    formal_seal_parser.add_argument(
        "--formal-bank",
        type=Path,
        required=True,
    )
    formal_seal_parser.add_argument(
        "--expected-formal-bank-sha256",
        required=True,
    )
    formal_seal_parser.add_argument("--out-dir", type=Path, required=True)
    formal_seal_parser.add_argument("--manifest", type=Path, required=True)

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
    if args.command == "prepare-candidates":
        prepare_candidates(args.out)
    elif args.command == "prepare-candidate-seal":
        prepare_candidate_seal(
            bank_path=args.bank,
            expected_bank_sha256=args.expected_bank_sha256,
            contract_path=args.contract,
            expected_contract_sha256=args.expected_contract_sha256,
            plan_path=args.plan,
            manifest_path=args.manifest,
        )
    elif args.command == "screen":
        screen(
            manifest_path=args.manifest,
            expected_manifest_sha256=args.expected_manifest_sha256,
            out_dir=args.out_dir,
            resume=args.resume,
        )
    elif args.command == "analyse-screen":
        analyse_screen(
            manifest_path=args.manifest,
            expected_manifest_sha256=args.expected_manifest_sha256,
            out_dir=args.out_dir,
        )
    elif args.command == "prepare-formal-seal":
        prepare_formal_seal(
            candidate_manifest_path=args.candidate_manifest,
            expected_candidate_manifest_sha256=(
                args.expected_candidate_manifest_sha256
            ),
            screen_summary_path=args.screen_summary,
            expected_screen_summary_sha256=(
                args.expected_screen_summary_sha256
            ),
            screen_contract_path=args.screen_contract,
            expected_screen_contract_sha256=(
                args.expected_screen_contract_sha256
            ),
            screen_provenance_path=args.screen_provenance,
            expected_screen_provenance_sha256=(
                args.expected_screen_provenance_sha256
            ),
            formal_bank_path=args.formal_bank,
            expected_formal_bank_sha256=args.expected_formal_bank_sha256,
            out_dir=args.out_dir,
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
