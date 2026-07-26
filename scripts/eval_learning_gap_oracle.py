"""Run the sealed R277 optimistic zero-sum inertia learning-gap audit."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.learning_gap_oracle import (  # noqa: E402
    BASELINE_CONTROLLER,
    CANDIDATE_NAMES,
    ENDPOINTS,
    audit_zero_sum_action,
    classify_learning_gap,
    frozen_learning_gap_contract,
    run_learning_gap_scenario,
    select_outcome_oracle,
    summarise_learning_gap_trace,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    empirical_upper_tail,
    load_scenario_bank,
    paired_binary_outcome_table,
    paired_bootstrap_contrasts,
    sha256_bytes,
    sha256_file,
)

ROUND_ID = "R277"
ENV_SEED = 42
STEPS = 300
FINAL_WINDOW_STEPS = 50
FAST_WINDOW_STEPS = 15
BOOTSTRAP_SEED = 2026072606
BOOTSTRAP_RESAMPLES = 10_000
SHARD_COUNT = 8
EXPECTED_SCENARIOS = 24
EXPECTED_CANDIDATES = 6
EXPECTED_NEW_TRACES = EXPECTED_SCENARIOS * EXPECTED_CANDIDATES

FORMAL_BANK_PATH = (
    ROOT / "results/r274_prospective_active_power_authority/formal_bank.json"
)
FORMAL_BANK_SHA256 = (
    "9d028e8a0e990fbea6585c674b471dba4d41ea27c1e0b7ecb5d8389092b31f44"
)
R275_PROVENANCE_PATH = ROOT / "results/r275_fast_md_authority/provenance.json"
R275_PROVENANCE_SHA256 = (
    "681ba69d959a1e943724468c66a20b51b9775d12a5733d13a744399351f8f99d"
)
R275_SUMMARY_PATH = (
    ROOT / "results/r275_fast_md_authority/fast_md_authority_summary.json"
)
R275_SUMMARY_SHA256 = (
    "30a1cc6ee7da0759236b9119ffcee706716432bd57b6ed988a42fafc4dc3d29d"
)
R275_FORMAL_SEAL_PATH = ROOT / "memory/rounds/R275/formal_seal.json"
R275_FORMAL_SEAL_SHA256 = (
    "fd075c29f20c56835283e620af83922df9c55d8942380e534003c70d1ae7cd52"
)
R275_FAST_CONTRACT_SHA256 = (
    "54ed2c2d534ecdee4d448efd7fd67dcbd32cd9d1acfac4e568e08e50a6b120e0"
)
R276_SUMMARY_PATH = (
    ROOT / "results/r276_fast_slow_factorial/fast_slow_factorial_summary.json"
)
R276_SUMMARY_SHA256 = (
    "49d2b84c7b70c3a17c38e11a915b6e89a89f93b3876f57cdd897b5e7370d088d"
)
R272_CONTRACT_PATH = ROOT / "memory/rounds/R272/actuator_contract.json"
R272_CONTRACT_SHA256 = (
    "220559d9f6ae32fbce87c16552d75c7067481921072626ee8b627335a3e0ec4c"
)

STORAGE_RELATIVE_ENDPOINTS = (
    "bess_command_l1_device_s",
    "bess_command_total_variation",
    "bess_charge_energy_mwh_total",
    "bess_discharge_energy_mwh_total",
)
CONTINUOUS_ENDPOINTS = (
    *ENDPOINTS,
    "terminal_common_abs_hz",
    *STORAGE_RELATIVE_ENDPOINTS,
)


def _write_new_canonical(path: Path, payload: object) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(payload)
    path.write_bytes(data)
    digest = sha256_bytes(data)
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n",
        encoding="utf-8",
    )
    return digest


def _load_json_with_hash(path: Path, expected_sha256: str) -> dict[str, Any]:
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise ValueError(
            f"hash mismatch for {path}: expected {expected_sha256}, got {actual}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R277/plan.md",
        "learning_gap_module": (
            ROOT / "src/andes_rl_kundur/evaluation/learning_gap_oracle.py"
        ),
        "learning_gap_runner": ROOT / "scripts/eval_learning_gap_oracle.py",
        "r275_fast_md_module": (
            ROOT / "src/andes_rl_kundur/evaluation/fast_md_authority.py"
        ),
        "active_power_authority": (
            ROOT / "src/andes_rl_kundur/evaluation/active_power_authority.py"
        ),
        "active_power_contract": (
            ROOT / "src/andes_rl_kundur/control/active_power.py"
        ),
        "base_environment": ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
        "v4_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py"
        ),
        "storage_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py"
        ),
        "physical_endpoints": (
            ROOT / "src/andes_rl_kundur/evaluation/physical_endpoints.py"
        ),
        "sealed_bank": ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py",
        "r272_contract": R272_CONTRACT_PATH,
        "r274_formal_bank": FORMAL_BANK_PATH,
        "r275_provenance": R275_PROVENANCE_PATH,
        "r275_summary": R275_SUMMARY_PATH,
        "r275_formal_seal": R275_FORMAL_SEAL_PATH,
        "r276_summary": R276_SUMMARY_PATH,
    }


def _source_manifest() -> dict[str, dict[str, str]]:
    return {
        name: {"path": str(path), "sha256": sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _verify_source_manifest(manifest: dict[str, Any]) -> None:
    for group in ("sources", "andes_source_guard"):
        for name, entry in manifest[group].items():
            path = Path(entry["path"])
            if sha256_file(path) != entry["sha256"]:
                raise ValueError(f"sealed source drift for {name}: {path}")


def _baseline_hashes() -> dict[str, str]:
    hashes = _load_json_with_hash(
        R275_PROVENANCE_PATH,
        R275_PROVENANCE_SHA256,
    )["trace_hashes"]
    selected = {
        path: digest
        for path, digest in hashes.items()
        if "/r275_fast_md_authority/formal_traces/" in path.replace("\\", "/")
        and path.endswith("__common_M_pos.json")
    }
    if len(selected) != EXPECTED_SCENARIOS:
        raise ValueError(f"expected 24 R275 baseline hashes, found {len(selected)}")
    return dict(sorted(selected.items()))


def _baseline_path(scenario_name: str) -> Path:
    return (
        ROOT
        / "results/r275_fast_md_authority/formal_traces"
        / f"{scenario_name}__common_M_pos.json"
    )


def _candidate_path(out_dir: Path, scenario_name: str, candidate: str) -> Path:
    return out_dir / "formal_traces" / f"{scenario_name}__{candidate}.json"


def _candidate_trace_count(out_dir: Path) -> int:
    trace_dir = out_dir / "formal_traces"
    return len(list(trace_dir.glob("*.json"))) if trace_dir.exists() else 0


def _validate_baseline_trace(
    path: Path,
    *,
    scenario: dict[str, Any],
    expected_sha256: str,
) -> dict[str, Any]:
    record = _load_json_with_hash(path, expected_sha256)
    expected = {
        "round": "R275",
        "controller": "slow_droop_pi_plus_common_m_pos",
        "scenario": scenario["name"],
        "delta_u": scenario["delta_u"],
        "seed": ENV_SEED,
        "requested_steps": STEPS,
        "n_steps": STEPS,
        "completed": True,
        "tds_failed": False,
        "formal_seal_sha256": R275_FORMAL_SEAL_SHA256,
        "fast_contract_sha256": R275_FAST_CONTRACT_SHA256,
        "provenance_valid": True,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"R275 baseline mismatch in {path}: {key}")
    return record


def prepare_seal(*, manifest_path: Path, out_dir: Path) -> None:
    if _candidate_trace_count(out_dir) != 0:
        raise ValueError("R277 seal must precede every formal candidate trace")
    fixed_artifacts = {
        FORMAL_BANK_PATH: FORMAL_BANK_SHA256,
        R275_PROVENANCE_PATH: R275_PROVENANCE_SHA256,
        R275_SUMMARY_PATH: R275_SUMMARY_SHA256,
        R275_FORMAL_SEAL_PATH: R275_FORMAL_SEAL_SHA256,
        R276_SUMMARY_PATH: R276_SUMMARY_SHA256,
        R272_CONTRACT_PATH: R272_CONTRACT_SHA256,
    }
    for path, expected in fixed_artifacts.items():
        if sha256_file(path) != expected:
            raise ValueError(f"fixed input artifact drift: {path}")
    bank, bank_sha256 = load_scenario_bank(
        FORMAL_BANK_PATH,
        expected_sha256=FORMAL_BANK_SHA256,
    )
    baseline_hashes = _baseline_hashes()
    for scenario in bank["scenarios"]:
        path = _baseline_path(scenario["name"])
        _validate_baseline_trace(
            path,
            scenario=scenario,
            expected_sha256=baseline_hashes[str(path.relative_to(ROOT))],
        )
    contract = frozen_learning_gap_contract()
    contract_sha256 = sha256_bytes(canonical_json_bytes(contract))
    r275_seal = _load_json_with_hash(
        R275_FORMAL_SEAL_PATH,
        R275_FORMAL_SEAL_SHA256,
    )
    andes_source_guard = {
        name: dict(r275_seal["r274_andes_source_guard"][name])
        for name in ("andes_esd1", "andes_pvd1", "andes_tds")
    }
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "phase": "formal-learning-gap-oracle",
        "repository_head": _git_head(),
        "formal_candidate_trace_count_at_freeze": 0,
        "formal_bank": {
            "path": str(FORMAL_BANK_PATH),
            "sha256": bank_sha256,
            "scenario_count": bank["scenario_count"],
        },
        "baseline_trace_hashes": baseline_hashes,
        "candidate_contract": {
            "payload": contract,
            "sha256": contract_sha256,
        },
        "execution": {
            "environment_seed": ENV_SEED,
            "steps": STEPS,
            "final_window_steps": FINAL_WINDOW_STEPS,
            "fast_window_steps": FAST_WINDOW_STEPS,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "shard_count": SHARD_COUNT,
            "scenario_count": EXPECTED_SCENARIOS,
            "candidate_count": EXPECTED_CANDIDATES,
            "requested_new_trajectories": EXPECTED_NEW_TRACES,
            "candidate_order": list(CANDIDATE_NAMES),
        },
        "packages": {
            "python": sys.version,
            "andes": importlib.metadata.version("andes"),
            "numpy": importlib.metadata.version("numpy"),
        },
        "sources": _source_manifest(),
        "andes_source_guard": andes_source_guard,
    }
    digest = _write_new_canonical(manifest_path, manifest)
    print(f"[sealed] {manifest_path} sha256={digest}", flush=True)


def _verify_seal(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
) -> tuple[dict[str, Any], str]:
    manifest = _load_json_with_hash(manifest_path, expected_manifest_sha256)
    if (
        manifest.get("round") != ROUND_ID
        or manifest.get("phase") != "formal-learning-gap-oracle"
    ):
        raise ValueError("R277 seal identity mismatch")
    execution = manifest["execution"]
    if manifest["formal_candidate_trace_count_at_freeze"] != 0:
        raise ValueError("R277 seal was not frozen at zero candidate traces")
    if (
        execution["shard_count"] != SHARD_COUNT
        or execution["requested_new_trajectories"] != EXPECTED_NEW_TRACES
        or tuple(execution["candidate_order"]) != CANDIDATE_NAMES
    ):
        raise ValueError("R277 sealed execution contract drift")
    contract = frozen_learning_gap_contract()
    if manifest["candidate_contract"]["payload"] != contract:
        raise ValueError("R277 candidate contract payload drift")
    contract_sha256 = sha256_bytes(canonical_json_bytes(contract))
    if contract_sha256 != manifest["candidate_contract"]["sha256"]:
        raise ValueError("R277 candidate contract hash mismatch")
    _verify_source_manifest(manifest)
    for path_text, expected in manifest["baseline_trace_hashes"].items():
        if sha256_file(ROOT / path_text) != expected:
            raise ValueError(f"baseline trace hash drift: {path_text}")
    return manifest, contract_sha256


def smoke(*, out_path: Path) -> None:
    record = run_learning_gap_scenario(
        "r277_learning_gap_smoke_bus14_pos_1p0",
        {"PQ_Bus14": 1.0},
        candidate_name="h1_pos",
        seed=ENV_SEED,
        steps=20,
    )
    record.update({"round": ROUND_ID, "phase": "pre-seal-smoke"})
    summary = (
        summarise_learning_gap_trace(
            record,
            final_window_steps=5,
            fast_window_steps=15,
        )
        if record["completed"]
        else None
    )
    audit = audit_zero_sum_action(record)
    digest = _write_new_canonical(
        out_path,
        {"record": record, "summary": summary, "action_audit": audit},
    )
    print(
        f"[smoke] completed={record['completed']} "
        f"steps={record['n_steps']}/20 action_pass={all(audit.values())} "
        f"sha256={digest}",
        flush=True,
    )


def _validate_candidate_trace(
    path: Path,
    *,
    scenario: dict[str, Any],
    candidate: str,
    formal_seal_sha256: str,
    candidate_contract_sha256: str,
) -> dict[str, Any]:
    record = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "round": ROUND_ID,
        "phase": "formal-candidate",
        "controller": candidate,
        "scenario": scenario["name"],
        "delta_u": scenario["delta_u"],
        "formal_bank_sha256": FORMAL_BANK_SHA256,
        "formal_seal_sha256": formal_seal_sha256,
        "candidate_contract_sha256": candidate_contract_sha256,
        "provenance_valid": True,
        "seed": ENV_SEED,
        "requested_steps": STEPS,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"R277 candidate trace mismatch in {path}: {key}")
    return record


def evaluate(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
    out_dir: Path,
    resume: bool,
    shard_index: int,
    shard_count: int,
) -> None:
    if shard_count != SHARD_COUNT or not 0 <= shard_index < SHARD_COUNT:
        raise ValueError("R277 formal execution requires shard-count 8, indices 0..7")
    manifest, contract_sha256 = _verify_seal(
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    bank, _ = load_scenario_bank(
        Path(manifest["formal_bank"]["path"]),
        expected_sha256=manifest["formal_bank"]["sha256"],
    )
    tasks = [
        (scenario_index, scenario, candidate)
        for scenario_index, scenario in enumerate(bank["scenarios"])
        for candidate in CANDIDATE_NAMES
    ]
    assigned = [
        (task_index, scenario_index, scenario, candidate)
        for task_index, (scenario_index, scenario, candidate) in enumerate(tasks)
        if task_index % shard_count == shard_index
    ]
    for local_index, (task_index, scenario_index, scenario, candidate) in enumerate(
        assigned,
        start=1,
    ):
        path = _candidate_path(out_dir, scenario["name"], candidate)
        if path.exists():
            if not resume:
                raise FileExistsError(f"formal trace exists: {path}")
            _validate_candidate_trace(
                path,
                scenario=scenario,
                candidate=candidate,
                formal_seal_sha256=expected_manifest_sha256,
                candidate_contract_sha256=contract_sha256,
            )
            print(f"[resume shard={shard_index}] {path.name}", flush=True)
            continue
        print(
            f"[formal shard={shard_index} {local_index:02d}/{len(assigned):02d}] "
            f"task={task_index:03d} bank={scenario_index:02d} "
            f"{scenario['name']} {candidate}",
            flush=True,
        )
        record = run_learning_gap_scenario(
            scenario["name"],
            scenario["delta_u"],
            candidate_name=candidate,
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
                "formal_bank_sha256": FORMAL_BANK_SHA256,
                "formal_seal_sha256": expected_manifest_sha256,
                "candidate_contract_sha256": contract_sha256,
                "provenance_valid": True,
                "execution_task_index": task_index,
                "execution_shard_index": shard_index,
                "execution_shard_count": shard_count,
            }
        )
        digest = _write_new_canonical(path, record)
        print(
            f"[saved] {path.name} {record['n_steps']}/{STEPS} "
            f"completed={record['completed']} sha256={digest}",
            flush=True,
        )


def _effect_percent(candidate: float, baseline: float) -> float:
    if np.isclose(baseline, 0.0, rtol=0.0, atol=1e-15):
        return 0.0 if np.isclose(candidate, 0.0, atol=1e-15) else float("inf")
    return 100.0 * (candidate / baseline - 1.0)


def _physical_storage_contract(records: list[dict[str, Any]]) -> dict[str, Any]:
    violations = sum(
        len(step.get("bess_constraint_violations", []))
        for record in records
        for step in record.get("traces", [])
    )
    saturation_reasons = sum(
        bool(reason)
        for record in records
        for step in record.get("traces", [])
        for reason in step.get("bess_saturation_reasons", [])
    )
    commanded = [
        abs(float(value))
        for record in records
        for step in record.get("traces", [])
        for value in step.get("bess_commanded_power_system_pu", [])
    ]
    actual = [
        abs(float(value))
        for record in records
        for step in record.get("traces", [])
        for value in step.get("bess_actual_power_system_pu", [])
    ]
    soc = [
        float(value)
        for record in records
        for step in record.get("traces", [])
        for value in step.get("bess_soc", [])
    ]
    checks = {
        "zero_constraint_violations": violations == 0,
        "zero_saturation_reasons": saturation_reasons == 0,
        "command_within_contract": max(commanded, default=float("inf")) <= 0.36
        + 1e-12,
        "actual_within_contract": max(actual, default=float("inf")) <= 0.36
        + 1e-12,
        "soc_within_contract": (
            min(soc, default=float("-inf")) >= 0.20 - 1e-9
            and max(soc, default=float("inf")) <= 0.80 + 1e-9
        ),
    }
    return {
        "checks": checks,
        "pass": all(checks.values()),
        "constraint_violation_count": violations,
        "saturation_reason_count": saturation_reasons,
        "max_abs_commanded_power_system_pu": max(commanded, default=None),
        "max_abs_actual_power_system_pu": max(actual, default=None),
        "min_soc": min(soc, default=None),
        "max_soc": max(soc, default=None),
    }


def _tail_audit(
    baseline: dict[str, dict[str, Any]],
    selected: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    result: dict[str, Any] = {}
    for endpoint in ENDPOINTS:
        baseline_tail = empirical_upper_tail(
            {
                scenario: float(summary[endpoint])
                for scenario, summary in baseline.items()
            }
        )
        selected_tail = empirical_upper_tail(
            {
                scenario: float(summary[endpoint])
                for scenario, summary in selected.items()
            }
        )
        effect = _effect_percent(
            float(selected_tail["cvar_upper_tail"]),
            float(baseline_tail["cvar_upper_tail"]),
        )
        result[endpoint] = {
            "baseline": baseline_tail,
            "oracle": selected_tail,
            "effect_percent": effect,
            "pass": effect <= 5.0,
        }
    return result, all(row["pass"] for row in result.values())


def _summary_markdown(summary: dict[str, Any]) -> str:
    decision = summary["decision"]
    contrast = summary["paired_bootstrap"]["contrasts"]["oracle_minus_baseline"]
    lines = [
        "# R277 learning-gap oracle summary",
        "",
        f"**Classification:** `{decision['classification']}`",
        "",
        decision["reason"],
        "",
        "## Oracle selection",
        "",
        f"- Non-baseline selections: "
        f"{summary['oracle_selection']['nonbaseline_selection_count']}/24",
        f"- Selection counts: "
        f"`{json.dumps(summary['oracle_selection']['selection_counts'], sort_keys=True)}`",
        "",
        "## Registered endpoint effects",
        "",
        "| Endpoint | Oracle vs baseline | Paired 95% interval |",
        "|---|---:|---:|",
    ]
    for endpoint in ENDPOINTS:
        effect = contrast["endpoints"][endpoint]["ratio_of_means_percent"]
        interval = effect["percentile_95_interval"]
        lines.append(
            f"| `{endpoint}` | {effect['point']:.6g}% | "
            f"[{interval[0]:.6g}%, {interval[1]:.6g}%] |"
        )
    lines.extend(["", "## Guards", ""])
    for name, passed in decision["guards"].items():
        lines.append(f"- `{name}`: {passed}")
    return "\n".join(lines) + "\n"


def analyse(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
    out_dir: Path,
) -> None:
    manifest, contract_sha256 = _verify_seal(
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    bank, _ = load_scenario_bank(
        Path(manifest["formal_bank"]["path"]),
        expected_sha256=manifest["formal_bank"]["sha256"],
    )
    baseline_hashes = manifest["baseline_trace_hashes"]
    baseline_records: dict[str, dict[str, Any]] = {}
    baseline_summaries: dict[str, dict[str, Any]] = {}
    candidate_records: dict[str, dict[str, dict[str, Any]]] = {}
    candidate_summaries: dict[str, dict[str, dict[str, Any] | None]] = {}
    valid_candidates: dict[str, dict[str, bool]] = {}
    action_audits: dict[str, dict[str, bool]] = {}
    trace_hashes: dict[str, str] = {}
    all_candidate_records: list[dict[str, Any]] = []

    for scenario in bank["scenarios"]:
        name = scenario["name"]
        baseline_path = _baseline_path(name)
        baseline = _validate_baseline_trace(
            baseline_path,
            scenario=scenario,
            expected_sha256=baseline_hashes[str(baseline_path.relative_to(ROOT))],
        )
        baseline_records[name] = baseline
        baseline_summaries[name] = summarise_learning_gap_trace(baseline)
        trace_hashes[str(baseline_path.relative_to(ROOT))] = sha256_file(
            baseline_path
        )
        candidate_records[name] = {}
        candidate_summaries[name] = {}
        valid_candidates[name] = {}
        for candidate in CANDIDATE_NAMES:
            path = _candidate_path(out_dir, name, candidate)
            if not path.exists():
                raise FileNotFoundError(f"missing R277 formal trace: {path}")
            record = _validate_candidate_trace(
                path,
                scenario=scenario,
                candidate=candidate,
                formal_seal_sha256=expected_manifest_sha256,
                candidate_contract_sha256=contract_sha256,
            )
            candidate_records[name][candidate] = record
            all_candidate_records.append(record)
            trace_hashes[str(path.relative_to(ROOT))] = sha256_file(path)
            audit = audit_zero_sum_action(record)
            action_audits[f"{name}__{candidate}"] = audit
            complete = (
                record["completed"]
                and not record["tds_failed"]
                and record["n_steps"] == STEPS
            )
            summary = (
                summarise_learning_gap_trace(record)
                if complete
                else None
            )
            candidate_summaries[name][candidate] = summary
            valid_candidates[name][candidate] = bool(
                complete and all(audit.values())
            )

    selection, selected_summaries = select_outcome_oracle(
        baseline_summaries,
        candidate_summaries,
        valid_candidates=valid_candidates,
    )
    selected_records = {
        scenario: (
            baseline_records[scenario]
            if row["selected"] == BASELINE_CONTROLLER
            else candidate_records[scenario][row["selected"]]
        )
        for scenario, row in selection["scenarios"].items()
    }
    scenario_names = [scenario["name"] for scenario in bank["scenarios"]]
    bootstrap_input = {
        BASELINE_CONTROLLER: {
            endpoint: [
                baseline_summaries[name][endpoint]
                for name in scenario_names
            ]
            for endpoint in CONTINUOUS_ENDPOINTS
        },
        "oracle": {
            endpoint: [
                selected_summaries[name][endpoint]
                for name in scenario_names
            ]
            for endpoint in CONTINUOUS_ENDPOINTS
        },
    }
    paired = paired_bootstrap_contrasts(
        bootstrap_input,
        contrasts=(
            ("oracle_minus_baseline", "oracle", BASELINE_CONTROLLER),
        ),
        seed=BOOTSTRAP_SEED,
        n_resamples=BOOTSTRAP_RESAMPLES,
    )
    paired["paired_scenarios"] = scenario_names
    contrast = paired["contrasts"]["oracle_minus_baseline"]

    tail_audit, tail_guard_pass = _tail_audit(
        baseline_summaries,
        selected_summaries,
    )
    storage_relative_effects = {
        endpoint: _effect_percent(
            float(np.mean([selected_summaries[name][endpoint] for name in scenario_names])),
            float(np.mean([baseline_summaries[name][endpoint] for name in scenario_names])),
        )
        for endpoint in STORAGE_RELATIVE_ENDPOINTS
    }
    storage_relative_guard_pass = all(
        effect <= 5.0 for effect in storage_relative_effects.values()
    )
    storage_contract = _physical_storage_contract(all_candidate_records)
    action_specific_keys = (
        "exact_action",
        "residual_zero_sum",
        "fleet_mean_action_exact",
        "physical_m_exact",
        "fleet_mean_m_exact",
        "d_exact",
    )
    action_contract_guard_pass = (
        len(action_audits) == EXPECTED_NEW_TRACES
        and all(
            all(audit[key] for key in action_specific_keys)
            for audit in action_audits.values()
        )
    )
    completion_guard_pass = (
        len(all_candidate_records) == EXPECTED_NEW_TRACES
        and len(selected_records) == EXPECTED_SCENARIOS
        and all(
            record["completed"]
            and not record["tds_failed"]
            and record["n_steps"] == STEPS
            for record in selected_records.values()
        )
        and all(record["completed"] for record in baseline_records.values())
    )
    decision = classify_learning_gap(
        contrast=contrast,
        nonbaseline_selection_count=selection["nonbaseline_selection_count"],
        provenance_guard_pass=True,
        completion_guard_pass=completion_guard_pass,
        action_contract_guard_pass=action_contract_guard_pass,
        storage_contract_guard_pass=bool(storage_contract["pass"]),
        storage_relative_guard_pass=storage_relative_guard_pass,
        tail_guard_pass=tail_guard_pass,
    )
    candidate_completion = {
        candidate: {
            "complete": sum(
                bool(candidate_records[name][candidate]["completed"])
                for name in scenario_names
            ),
            "tds_failed": sum(
                bool(candidate_records[name][candidate]["tds_failed"])
                for name in scenario_names
            ),
        }
        for candidate in CANDIDATE_NAMES
    }
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "experiment": "r277_learning_gap_oracle",
        "decision": decision,
        "formal_bank": manifest["formal_bank"],
        "candidate_contract": manifest["candidate_contract"],
        "candidate_completion": candidate_completion,
        "completion_pairing": paired_binary_outcome_table(
            [selected_records[name]["completed"] for name in scenario_names],
            [baseline_records[name]["completed"] for name in scenario_names],
        ),
        "oracle_selection": selection,
        "paired_bootstrap": paired,
        "tail_audit": tail_audit,
        "storage_contract_audit": storage_contract,
        "storage_relative_effects_percent": storage_relative_effects,
        "action_contract_guard_pass": action_contract_guard_pass,
        "action_audits": action_audits,
        "formal_seal": {
            "path": str(manifest_path),
            "sha256": expected_manifest_sha256,
        },
        "trace_hashes": dict(sorted(trace_hashes.items())),
    }
    summary_path = out_dir / "learning_gap_oracle_summary.json"
    summary_digest = _write_new_canonical(summary_path, summary)
    markdown_path = out_dir / "learning_gap_oracle_summary.md"
    if markdown_path.exists():
        raise FileExistsError(f"refusing to overwrite {markdown_path}")
    markdown_path.write_text(_summary_markdown(summary), encoding="utf-8")
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "repository_head": _git_head(),
        "formal_manifest": {
            "path": str(manifest_path),
            "sha256": expected_manifest_sha256,
            "payload": manifest,
        },
        "summary": {
            "path": str(summary_path),
            "sha256": summary_digest,
        },
        "trace_hashes": dict(sorted(trace_hashes.items())),
        "packages": manifest["packages"],
        "sources": manifest["sources"],
        "analysis_command": " ".join(sys.argv),
    }
    provenance_path = out_dir / "provenance.json"
    provenance_digest = _write_new_canonical(provenance_path, provenance)
    print(
        f"[analysed] classification={decision['classification']} "
        f"summary_sha256={summary_digest} provenance_sha256={provenance_digest}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    smoke_parser = subparsers.add_parser("smoke")
    smoke_parser.add_argument("--out", type=Path, required=True)

    seal_parser = subparsers.add_parser("prepare-seal")
    seal_parser.add_argument("--manifest", type=Path, required=True)
    seal_parser.add_argument("--out-dir", type=Path, required=True)

    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("--manifest", type=Path, required=True)
    evaluate_parser.add_argument("--expected-manifest-sha256", required=True)
    evaluate_parser.add_argument("--out-dir", type=Path, required=True)
    evaluate_parser.add_argument("--resume", action="store_true")
    evaluate_parser.add_argument("--shard-index", type=int, required=True)
    evaluate_parser.add_argument("--shard-count", type=int, required=True)

    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--manifest", type=Path, required=True)
    analyse_parser.add_argument("--expected-manifest-sha256", required=True)
    analyse_parser.add_argument("--out-dir", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "smoke":
        smoke(out_path=args.out.resolve())
    elif args.command == "prepare-seal":
        prepare_seal(
            manifest_path=args.manifest.resolve(),
            out_dir=args.out_dir.resolve(),
        )
    elif args.command == "evaluate":
        evaluate(
            manifest_path=args.manifest.resolve(),
            expected_manifest_sha256=args.expected_manifest_sha256,
            out_dir=args.out_dir.resolve(),
            resume=args.resume,
            shard_index=args.shard_index,
            shard_count=args.shard_count,
        )
    elif args.command == "analyse":
        analyse(
            manifest_path=args.manifest.resolve(),
            expected_manifest_sha256=args.expected_manifest_sha256,
            out_dir=args.out_dir.resolve(),
        )
    else:  # pragma: no cover
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
