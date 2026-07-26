"""Run the sealed R275 fast-inertia value gate above R274 droop+PI."""

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

from andes_rl_kundur.evaluation.fast_md_authority import (  # noqa: E402
    BASELINE_CONTROLLER,
    CANDIDATE_CONTROLLER,
    FAST_ENDPOINTS,
    SLOW_ENDPOINTS,
    audit_fast_md_action,
    classify_fast_md_authority,
    frozen_fast_md_contract,
    run_fast_md_scenario,
    summarise_fast_md_trace,
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

ROUND_ID = "R275"
ENV_SEED = 42
STEPS = 300
FINAL_WINDOW_STEPS = 50
FAST_WINDOW_STEPS = 15
BOOTSTRAP_SEED = 2026072604
BOOTSTRAP_RESAMPLES = 10_000
FORMAL_BANK_PATH = ROOT / "results/r274_prospective_active_power_authority/formal_bank.json"
FORMAL_BANK_SHA256 = (
    "9d028e8a0e990fbea6585c674b471dba4d41ea27c1e0b7ecb5d8389092b31f44"
)
R274_PROVENANCE_PATH = (
    ROOT / "results/r274_prospective_active_power_authority/provenance.json"
)
R274_PROVENANCE_SHA256 = (
    "b49247284cfeccd640af9d0aa262dc7cc7cf0c0ae83a76caf02564049970e0af"
)
R274_SUMMARY_PATH = (
    ROOT
    / "results/r274_prospective_active_power_authority/"
    "active_power_authority_summary.json"
)
R274_SUMMARY_SHA256 = (
    "4d62331541798f577910fe7cd8fce129e8e9464bd58f1f771da2a7737fb03f87"
)
R274_FORMAL_SEAL_PATH = ROOT / "memory/rounds/R274/formal_seal.json"
R274_FORMAL_SEAL_SHA256 = (
    "efba41ede1d748171ad62c31bbbe0bc62dffcbedcfd7d458b505df95e97132e8"
)
R272_CONTRACT_PATH = ROOT / "memory/rounds/R272/actuator_contract.json"
R272_CONTRACT_SHA256 = (
    "220559d9f6ae32fbce87c16552d75c7067481921072626ee8b627335a3e0ec4c"
)

CONTINUOUS_ENDPOINTS = (
    *FAST_ENDPOINTS,
    *SLOW_ENDPOINTS,
    "terminal_common_abs_hz",
    "bess_command_l1_device_s",
    "bess_command_total_variation",
    "bess_saturation_fraction",
    "bess_min_soc",
    "bess_max_soc",
    "bess_charge_energy_mwh_total",
    "bess_discharge_energy_mwh_total",
)
TAIL_ENDPOINTS = (*FAST_ENDPOINTS, *SLOW_ENDPOINTS)
STORAGE_RELATIVE_GUARDS = (
    "bess_command_l1_device_s",
    "bess_command_total_variation",
    "bess_charge_energy_mwh_total",
    "bess_discharge_energy_mwh_total",
)


def _write_new_canonical(path: Path, payload: object) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(payload)
    path.write_bytes(data)
    digest = sha256_bytes(data)
    sidecar = path.with_name(path.name + ".sha256")
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
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
        "plan": ROOT / "memory/rounds/R275/plan.md",
        "r275_fast_md_authority": (
            ROOT / "src/andes_rl_kundur/evaluation/fast_md_authority.py"
        ),
        "r275_runner": ROOT / "scripts/eval_fast_md_authority.py",
        "active_power_authority": (
            ROOT / "src/andes_rl_kundur/evaluation/active_power_authority.py"
        ),
        "active_power_contract": (
            ROOT / "src/andes_rl_kundur/control/active_power.py"
        ),
        "base_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/base_env.py"
        ),
        "v4_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py"
        ),
        "storage_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py"
        ),
        "physical_endpoints": (
            ROOT / "src/andes_rl_kundur/evaluation/physical_endpoints.py"
        ),
        "sealed_bank": (
            ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py"
        ),
        "r272_actuator_contract": R272_CONTRACT_PATH,
        "r274_formal_bank": FORMAL_BANK_PATH,
        "r274_provenance": R274_PROVENANCE_PATH,
        "r274_summary": R274_SUMMARY_PATH,
        "r274_formal_seal": R274_FORMAL_SEAL_PATH,
    }


def _source_manifest() -> dict[str, dict[str, str]]:
    return {
        name: {"path": str(path), "sha256": sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _verify_source_manifest(manifest: dict[str, Any]) -> None:
    for name, entry in manifest["sources"].items():
        path = Path(entry["path"])
        actual = sha256_file(path)
        if actual != entry["sha256"]:
            raise ValueError(f"sealed source drift for {name}: {path}")
    for name, entry in manifest["r274_andes_source_guard"].items():
        path = Path(entry["path"])
        actual = sha256_file(path)
        if actual != entry["sha256"]:
            raise ValueError(f"R274 ANDES/source guard drift for {name}: {path}")


def _baseline_trace_hashes(
    provenance: dict[str, Any],
) -> dict[str, str]:
    result = {
        path: digest
        for path, digest in provenance["trace_hashes"].items()
        if "/formal_traces/" in path.replace("\\", "/")
        and path.endswith("__droop_pi.json")
    }
    if len(result) != 24:
        raise ValueError(f"expected 24 immutable R274 baselines, found {len(result)}")
    return dict(sorted(result.items()))


def _validate_baseline_trace(
    path: Path,
    *,
    scenario: dict[str, Any],
    expected_sha256: str,
) -> dict[str, Any]:
    record = _load_json_with_hash(path, expected_sha256)
    expected = {
        "round": "R274",
        "phase": "formal-candidate",
        "controller": "droop_pi",
        "scenario": scenario["name"],
        "delta_u": scenario["delta_u"],
        "formal_bank_sha256": FORMAL_BANK_SHA256,
        "contract_sha256": R272_CONTRACT_SHA256,
        "formal_seal_sha256": R274_FORMAL_SEAL_SHA256,
        "provenance_valid": True,
        "seed": ENV_SEED,
        "requested_steps": STEPS,
        "n_steps": STEPS,
        "completed": True,
        "tds_failed": False,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"R274 baseline mismatch in {path}: {key}")
    expected_controller = {
        "kp_system_pu_per_hz_per_device": 2.0,
        "ki_system_pu_per_hz_s_per_device": 0.2,
    }
    if record.get("controller_config") != expected_controller:
        raise ValueError(f"R274 baseline controller drift in {path}")
    return record


def _baseline_path(scenario_name: str) -> Path:
    return (
        ROOT
        / "results/r274_prospective_active_power_authority/formal_traces"
        / f"{scenario_name}__droop_pi.json"
    )


def _candidate_path(out_dir: Path, scenario_name: str) -> Path:
    return out_dir / "formal_traces" / f"{scenario_name}__common_M_pos.json"


def _formal_candidate_count(out_dir: Path) -> int:
    directory = out_dir / "formal_traces"
    return (
        len(list(directory.glob("*__common_M_pos.json")))
        if directory.exists()
        else 0
    )


def prepare_seal(*, manifest_path: Path, out_dir: Path) -> None:
    if _formal_candidate_count(out_dir) != 0:
        raise ValueError("formal seal must precede every R275 candidate trace")
    if sha256_file(FORMAL_BANK_PATH) != FORMAL_BANK_SHA256:
        raise ValueError("R274 formal bank hash drift")
    if sha256_file(R274_PROVENANCE_PATH) != R274_PROVENANCE_SHA256:
        raise ValueError("R274 provenance hash drift")
    if sha256_file(R274_SUMMARY_PATH) != R274_SUMMARY_SHA256:
        raise ValueError("R274 summary hash drift")
    if sha256_file(R274_FORMAL_SEAL_PATH) != R274_FORMAL_SEAL_SHA256:
        raise ValueError("R274 formal seal hash drift")
    if sha256_file(R272_CONTRACT_PATH) != R272_CONTRACT_SHA256:
        raise ValueError("R272 actuator contract hash drift")

    formal_bank, formal_bank_sha256 = load_scenario_bank(
        FORMAL_BANK_PATH,
        expected_sha256=FORMAL_BANK_SHA256,
    )
    provenance = _load_json_with_hash(
        R274_PROVENANCE_PATH,
        R274_PROVENANCE_SHA256,
    )
    baseline_hashes = _baseline_trace_hashes(provenance)
    for scenario in formal_bank["scenarios"]:
        path = _baseline_path(scenario["name"])
        expected = baseline_hashes.get(str(path.relative_to(ROOT)))
        if expected is None:
            raise ValueError(f"baseline is absent from R274 provenance: {path}")
        _validate_baseline_trace(
            path,
            scenario=scenario,
            expected_sha256=expected,
        )

    r274_seal = _load_json_with_hash(
        R274_FORMAL_SEAL_PATH,
        R274_FORMAL_SEAL_SHA256,
    )
    old_sources = r274_seal["sources"]
    for name, entry in old_sources.items():
        path = Path(entry["path"])
        if sha256_file(path) != entry["sha256"]:
            raise ValueError(f"R274 sealed source drift before R275: {name}")
    andes_source_guard = {
        name: dict(old_sources[name])
        for name in ("andes_esd1", "andes_pvd1", "andes_tds")
    }
    contract = frozen_fast_md_contract()
    contract_sha256 = sha256_bytes(canonical_json_bytes(contract))
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "phase": "formal-fast-md",
        "repository_head": _git_head(),
        "formal_candidate_trace_count_at_freeze": 0,
        "formal_bank": {
            "path": str(FORMAL_BANK_PATH),
            "sha256": formal_bank_sha256,
            "scenario_count": formal_bank["scenario_count"],
        },
        "r274_baseline": {
            "provenance_path": str(R274_PROVENANCE_PATH),
            "provenance_sha256": R274_PROVENANCE_SHA256,
            "summary_path": str(R274_SUMMARY_PATH),
            "summary_sha256": R274_SUMMARY_SHA256,
            "formal_seal_path": str(R274_FORMAL_SEAL_PATH),
            "formal_seal_sha256": R274_FORMAL_SEAL_SHA256,
            "trace_hashes": baseline_hashes,
        },
        "r272_contract": {
            "path": str(R272_CONTRACT_PATH),
            "sha256": R272_CONTRACT_SHA256,
        },
        "candidate_contract": {
            "payload": contract,
            "sha256": contract_sha256,
        },
        "execution": {
            "baseline_controller": BASELINE_CONTROLLER,
            "candidate_controller": CANDIDATE_CONTROLLER,
            "environment_seed": ENV_SEED,
            "steps": STEPS,
            "final_window_steps": FINAL_WINDOW_STEPS,
            "fast_window_steps": FAST_WINDOW_STEPS,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "allowed_shard_count": 2,
        },
        "packages": {
            "python": sys.version,
            "andes": importlib.metadata.version("andes"),
            "numpy": importlib.metadata.version("numpy"),
        },
        "sources": _source_manifest(),
        "r274_andes_source_guard": andes_source_guard,
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
        or manifest.get("phase") != "formal-fast-md"
    ):
        raise ValueError("R275 seal identity mismatch")
    if manifest["formal_candidate_trace_count_at_freeze"] != 0:
        raise ValueError("R275 seal was not frozen at zero candidate traces")
    if manifest["formal_bank"]["sha256"] != FORMAL_BANK_SHA256:
        raise ValueError("R275 seal formal bank mismatch")
    if (
        manifest["candidate_contract"]["payload"]
        != frozen_fast_md_contract()
    ):
        raise ValueError("R275 frozen fast M/D contract drift")
    contract_sha256 = sha256_bytes(
        canonical_json_bytes(manifest["candidate_contract"]["payload"])
    )
    if contract_sha256 != manifest["candidate_contract"]["sha256"]:
        raise ValueError("R275 fast M/D contract hash mismatch")
    _verify_source_manifest(manifest)
    for path_text, expected in manifest["r274_baseline"][
        "trace_hashes"
    ].items():
        path = ROOT / path_text
        if sha256_file(path) != expected:
            raise ValueError(f"R274 baseline trace drift: {path}")
    return manifest, contract_sha256


def smoke(*, out_path: Path) -> None:
    record = run_fast_md_scenario(
        "r275_smoke_bus14_pos_1p0",
        {"PQ_Bus14": 1.0},
        seed=ENV_SEED,
        steps=20,
    )
    record.update({"round": ROUND_ID, "phase": "pre-seal-smoke"})
    summary = (
        summarise_fast_md_trace(
            record,
            final_window_steps=5,
            fast_window_steps=15,
        )
        if record["completed"]
        else None
    )
    payload = {"record": record, "summary": summary}
    digest = _write_new_canonical(out_path, payload)
    print(
        f"[smoke] completed={record['completed']} "
        f"steps={record['n_steps']}/20 sha256={digest}",
        flush=True,
    )


def _validate_candidate_trace(
    path: Path,
    *,
    scenario: dict[str, Any],
    formal_seal_sha256: str,
    fast_contract_sha256: str,
) -> dict[str, Any]:
    record = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "round": ROUND_ID,
        "phase": "formal-candidate",
        "controller": CANDIDATE_CONTROLLER,
        "scenario": scenario["name"],
        "delta_u": scenario["delta_u"],
        "formal_bank_sha256": FORMAL_BANK_SHA256,
        "formal_seal_sha256": formal_seal_sha256,
        "fast_contract_sha256": fast_contract_sha256,
        "provenance_valid": True,
        "seed": ENV_SEED,
        "requested_steps": STEPS,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"R275 candidate provenance mismatch in {path}: {key}")
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
    if shard_count != 2 or shard_index not in (0, 1):
        raise ValueError("R275 formal execution is frozen to two shards, indices 0 and 1")
    manifest, fast_contract_sha256 = _verify_seal(
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    if shard_count != manifest["execution"]["allowed_shard_count"]:
        raise ValueError("shard count differs from the R275 seal")
    formal_bank, _ = load_scenario_bank(
        Path(manifest["formal_bank"]["path"]),
        expected_sha256=manifest["formal_bank"]["sha256"],
    )
    assigned = [
        (index, scenario)
        for index, scenario in enumerate(formal_bank["scenarios"])
        if index % shard_count == shard_index
    ]
    for local_index, (bank_index, scenario) in enumerate(assigned, start=1):
        path = _candidate_path(out_dir, scenario["name"])
        if path.exists():
            if not resume:
                raise FileExistsError(f"formal trace exists: {path}")
            _validate_candidate_trace(
                path,
                scenario=scenario,
                formal_seal_sha256=expected_manifest_sha256,
                fast_contract_sha256=fast_contract_sha256,
            )
            print(f"[resume shard={shard_index}] {path.name}", flush=True)
            continue
        print(
            f"[formal shard={shard_index} {local_index:02d}/{len(assigned):02d}] "
            f"bank_index={bank_index:02d} {scenario['name']}",
            flush=True,
        )
        record = run_fast_md_scenario(
            scenario["name"],
            scenario["delta_u"],
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
                "fast_contract_sha256": fast_contract_sha256,
                "provenance_valid": True,
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


def _mean_effect_percent(candidate: float, baseline: float) -> float:
    if np.isclose(baseline, 0.0, rtol=0.0, atol=1e-15):
        return 0.0 if np.isclose(candidate, 0.0, atol=1e-15) else float("inf")
    return 100.0 * (candidate / baseline - 1.0)


def _controller_summary(
    records: list[dict[str, Any]],
    endpoint_rows: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    means = {
        endpoint: (
            float(np.mean([row[endpoint] for _, row in endpoint_rows]))
            if endpoint_rows
            else None
        )
        for endpoint in CONTINUOUS_ENDPOINTS
    }
    tails = {
        endpoint: (
            empirical_upper_tail(
                {
                    scenario: float(row[endpoint])
                    for scenario, row in endpoint_rows
                }
            )
            if endpoint_rows
            else None
        )
        for endpoint in TAIL_ENDPOINTS
    }
    violations = sum(
        len(step.get("bess_constraint_violations", []))
        for record in records
        for step in record.get("traces", [])
    )
    saturation_reasons = sum(
        bool(reasons)
        for record in records
        for step in record.get("traces", [])
        for reasons in step.get("bess_saturation_reasons", [])
    )
    commands = [
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
    requested = [
        abs(float(value))
        for record in records
        for step in record.get("traces", [])
        for value in step.get("bess_requested_power_system_pu", [])
    ]
    soc = [
        float(value)
        for record in records
        for step in record.get("traces", [])
        for value in step.get("bess_soc", [])
    ]
    return {
        "complete_count": sum(bool(record.get("completed")) for record in records),
        "failure_count": sum(bool(record.get("tds_failed")) for record in records),
        "constraint_violation_count": violations,
        "saturation_reason_count": saturation_reasons,
        "paired_endpoint_count": len(endpoint_rows),
        "means": means,
        "tails": tails,
        "max_abs_requested_power_system_pu": max(requested, default=None),
        "max_abs_commanded_power_system_pu": max(commands, default=None),
        "max_abs_actual_power_system_pu": max(actual, default=None),
        "min_soc": min(soc, default=None),
        "max_soc": max(soc, default=None),
    }


def _tail_effects(
    summaries: dict[str, dict[str, Any]],
) -> tuple[dict[str, float], bool]:
    baseline = summaries[BASELINE_CONTROLLER]["tails"]
    candidate = summaries[CANDIDATE_CONTROLLER]["tails"]
    effects = {
        endpoint: _mean_effect_percent(
            candidate[endpoint]["cvar_upper_tail"],
            baseline[endpoint]["cvar_upper_tail"],
        )
        for endpoint in TAIL_ENDPOINTS
    }
    return effects, all(effect <= 5.0 for effect in effects.values())


def _storage_guard(
    summaries: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    baseline = summaries[BASELINE_CONTROLLER]
    candidate = summaries[CANDIDATE_CONTROLLER]
    relative_effects = {
        endpoint: _mean_effect_percent(
            candidate["means"][endpoint],
            baseline["means"][endpoint],
        )
        for endpoint in STORAGE_RELATIVE_GUARDS
    }
    checks = {
        "zero_constraint_violations": (
            baseline["constraint_violation_count"] == 0
            and candidate["constraint_violation_count"] == 0
        ),
        "zero_saturation_reasons": (
            baseline["saturation_reason_count"] == 0
            and candidate["saturation_reason_count"] == 0
        ),
        "command_within_contract": (
            candidate["max_abs_commanded_power_system_pu"] <= 0.36 + 1e-12
        ),
        "actual_within_contract": (
            candidate["max_abs_actual_power_system_pu"] <= 0.36 + 1e-12
        ),
        "soc_within_contract": (
            candidate["min_soc"] >= 0.20 - 1e-9
            and candidate["max_soc"] <= 0.80 + 1e-9
        ),
        "relative_action_energy_no_worse_5pct": all(
            effect <= 5.0 for effect in relative_effects.values()
        ),
    }
    return {
        "checks": checks,
        "relative_effects_percent": relative_effects,
    }, all(checks.values())


def _summary_markdown(summary: dict[str, Any]) -> str:
    decision = summary["decision"]
    lines = [
        "# R275 fast M/D authority summary",
        "",
        f"**Classification:** `{decision['classification']}`",
        "",
        decision["reason"],
        "",
        "## Completion",
        "",
        "| Arm | Complete | Failures | Constraint violations |",
        "|---|---:|---:|---:|",
    ]
    for name in (BASELINE_CONTROLLER, CANDIDATE_CONTROLLER):
        row = summary["controllers"][name]
        lines.append(
            f"| `{name}` | {row['complete_count']} | {row['failure_count']} | "
            f"{row['constraint_violation_count']} |"
        )
    lines.extend(
        [
            "",
            "## Registered endpoint effects",
            "",
            "| Endpoint | Ratio-of-means effect (%) | 95% interval (%) | Clear |",
            "|---|---:|---:|---:|",
        ]
    )
    contrast = summary["paired_bootstrap"]["contrasts"][
        "candidate_minus_baseline"
    ]
    clear = decision.get("fast_endpoints", {})
    for endpoint in (*FAST_ENDPOINTS, *SLOW_ENDPOINTS):
        effect = contrast["endpoints"][endpoint]["ratio_of_means_percent"]
        interval = effect["percentile_95_interval"]
        is_clear = clear.get(endpoint, {}).get("material_improvement", False)
        lines.append(
            f"| `{endpoint}` | {effect['point']:.6g} | "
            f"[{interval[0]:.6g}, {interval[1]:.6g}] | {is_clear} |"
        )
    lines.extend(
        [
            "",
            "## Guards",
            "",
        ]
    )
    for name, passed in decision["guards"].items():
        lines.append(f"- `{name}`: {passed}")
    lines.append("")
    return "\n".join(lines)


def analyse(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
    out_dir: Path,
) -> None:
    manifest, fast_contract_sha256 = _verify_seal(
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    formal_bank, _ = load_scenario_bank(
        Path(manifest["formal_bank"]["path"]),
        expected_sha256=manifest["formal_bank"]["sha256"],
    )
    baseline_hashes = manifest["r274_baseline"]["trace_hashes"]
    records = {
        BASELINE_CONTROLLER: [],
        CANDIDATE_CONTROLLER: [],
    }
    trace_hashes: dict[str, str] = {}
    endpoint_grid: dict[str, dict[str, dict[str, Any]]] = {}
    action_audits: dict[str, dict[str, bool]] = {}

    for scenario in formal_bank["scenarios"]:
        name = scenario["name"]
        baseline_path = _baseline_path(name)
        baseline_expected = baseline_hashes[str(baseline_path.relative_to(ROOT))]
        baseline = _validate_baseline_trace(
            baseline_path,
            scenario=scenario,
            expected_sha256=baseline_expected,
        )
        candidate_path = _candidate_path(out_dir, name)
        if not candidate_path.exists():
            raise FileNotFoundError(f"missing R275 formal trace: {candidate_path}")
        candidate = _validate_candidate_trace(
            candidate_path,
            scenario=scenario,
            formal_seal_sha256=expected_manifest_sha256,
            fast_contract_sha256=fast_contract_sha256,
        )
        records[BASELINE_CONTROLLER].append(baseline)
        records[CANDIDATE_CONTROLLER].append(candidate)
        trace_hashes[str(baseline_path.relative_to(ROOT))] = sha256_file(
            baseline_path
        )
        trace_hashes[str(candidate_path.relative_to(ROOT))] = sha256_file(
            candidate_path
        )
        endpoint_grid[name] = {}
        if baseline["completed"] and candidate["completed"]:
            baseline_summary = summarise_fast_md_trace(
                baseline,
                final_window_steps=FINAL_WINDOW_STEPS,
                fast_window_steps=FAST_WINDOW_STEPS,
            )
            candidate_summary = summarise_fast_md_trace(
                candidate,
                final_window_steps=FINAL_WINDOW_STEPS,
                fast_window_steps=FAST_WINDOW_STEPS,
            )
            endpoint_grid[name][BASELINE_CONTROLLER] = baseline_summary
            endpoint_grid[name][CANDIDATE_CONTROLLER] = candidate_summary
            action_audits[name] = audit_fast_md_action(candidate_summary)

    paired_scenarios = [
        scenario["name"]
        for scenario in formal_bank["scenarios"]
        if set(endpoint_grid[scenario["name"]])
        == {BASELINE_CONTROLLER, CANDIDATE_CONTROLLER}
    ]
    endpoint_rows = {
        controller: [
            (name, endpoint_grid[name][controller])
            for name in paired_scenarios
        ]
        for controller in (BASELINE_CONTROLLER, CANDIDATE_CONTROLLER)
    }
    controller_summaries = {
        controller: _controller_summary(
            records[controller],
            endpoint_rows[controller],
        )
        for controller in (BASELINE_CONTROLLER, CANDIDATE_CONTROLLER)
    }
    paired = None
    primary_contrast = None
    if paired_scenarios:
        bootstrap_input = {
            controller: {
                endpoint: [
                    endpoint_grid[name][controller][endpoint]
                    for name in paired_scenarios
                ]
                for endpoint in CONTINUOUS_ENDPOINTS
            }
            for controller in (BASELINE_CONTROLLER, CANDIDATE_CONTROLLER)
        }
        paired = paired_bootstrap_contrasts(
            bootstrap_input,
            contrasts=(
                (
                    "candidate_minus_baseline",
                    CANDIDATE_CONTROLLER,
                    BASELINE_CONTROLLER,
                ),
            ),
            seed=BOOTSTRAP_SEED,
            n_resamples=BOOTSTRAP_RESAMPLES,
        )
        paired["available"] = True
        paired["paired_scenarios"] = paired_scenarios
        primary_contrast = paired["contrasts"]["candidate_minus_baseline"]
    else:
        paired = {
            "available": False,
            "paired_scenarios": [],
            "contrasts": {},
        }

    action_budget_pass = (
        len(action_audits) == formal_bank["scenario_count"]
        and all(all(audit.values()) for audit in action_audits.values())
    )
    storage_audit, storage_guard_pass = _storage_guard(controller_summaries)
    if paired_scenarios:
        tail_effects, tail_guard_pass = _tail_effects(controller_summaries)
    else:
        tail_effects, tail_guard_pass = {}, False
    decision = classify_fast_md_authority(
        controller_summaries=controller_summaries,
        primary_contrast=primary_contrast,
        total_scenarios=formal_bank["scenario_count"],
        provenance_hashes_match=True,
        action_budget_pass=action_budget_pass,
        storage_guard_pass=storage_guard_pass,
        tail_guard_pass=tail_guard_pass,
    )
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "experiment": "r275_fast_md_authority",
        "decision": decision,
        "formal_bank": manifest["formal_bank"],
        "candidate_contract": manifest["candidate_contract"],
        "controllers": controller_summaries,
        "completion_pairing": paired_binary_outcome_table(
            [record["completed"] for record in records[CANDIDATE_CONTROLLER]],
            [record["completed"] for record in records[BASELINE_CONTROLLER]],
        ),
        "paired_bootstrap": paired,
        "tail_effects_percent": tail_effects,
        "storage_audit": storage_audit,
        "action_budget_pass": action_budget_pass,
        "action_audits": action_audits,
        "formal_seal": {
            "path": str(manifest_path),
            "sha256": expected_manifest_sha256,
        },
        "trace_hashes": dict(sorted(trace_hashes.items())),
    }
    summary_path = out_dir / "fast_md_authority_summary.json"
    summary_digest = _write_new_canonical(summary_path, summary)
    markdown_path = out_dir / "fast_md_authority_summary.md"
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
        smoke(out_path=args.out)
    elif args.command == "prepare-seal":
        prepare_seal(manifest_path=args.manifest, out_dir=args.out_dir)
    elif args.command == "evaluate":
        evaluate(
            manifest_path=args.manifest,
            expected_manifest_sha256=args.expected_manifest_sha256,
            out_dir=args.out_dir,
            resume=args.resume,
            shard_index=args.shard_index,
            shard_count=args.shard_count,
        )
    elif args.command == "analyse":
        analyse(
            manifest_path=args.manifest,
            expected_manifest_sha256=args.expected_manifest_sha256,
            out_dir=args.out_dir,
        )
    else:  # pragma: no cover
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
