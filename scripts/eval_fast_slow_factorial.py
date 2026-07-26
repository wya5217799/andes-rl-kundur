"""Run the sealed R276 four-arm fast/slow factorial gate."""

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
    audit_fast_md_action,
    frozen_fast_md_contract,
    summarise_fast_md_trace,
)
from andes_rl_kundur.evaluation.fast_slow_factorial import (  # noqa: E402
    ARMS,
    COMBINED_ARM,
    ENDPOINTS,
    FAST_ARM,
    SLOW_ARM,
    ZERO_ARM,
    classify_fast_slow_factorial,
    factorial_bootstrap,
    run_fast_only_scenario,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    empirical_upper_tail,
    load_scenario_bank,
    paired_binary_outcome_table,
    sha256_bytes,
    sha256_file,
)

ROUND_ID = "R276"
ENV_SEED = 42
STEPS = 300
FINAL_WINDOW_STEPS = 50
FAST_WINDOW_STEPS = 15
BOOTSTRAP_SEED = 2026072605
BOOTSTRAP_RESAMPLES = 10_000
SHARD_COUNT = 3

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
R272_CONTRACT_PATH = ROOT / "memory/rounds/R272/actuator_contract.json"
R272_CONTRACT_SHA256 = (
    "220559d9f6ae32fbce87c16552d75c7067481921072626ee8b627335a3e0ec4c"
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
        "plan": ROOT / "memory/rounds/R276/plan.md",
        "factorial_module": (
            ROOT / "src/andes_rl_kundur/evaluation/fast_slow_factorial.py"
        ),
        "factorial_runner": ROOT / "scripts/eval_fast_slow_factorial.py",
        "r275_fast_md_module": (
            ROOT / "src/andes_rl_kundur/evaluation/fast_md_authority.py"
        ),
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
        "r272_contract": R272_CONTRACT_PATH,
        "r274_formal_bank": FORMAL_BANK_PATH,
        "r274_provenance": R274_PROVENANCE_PATH,
        "r275_provenance": R275_PROVENANCE_PATH,
        "r275_summary": R275_SUMMARY_PATH,
        "r275_formal_seal": R275_FORMAL_SEAL_PATH,
    }


def _source_manifest() -> dict[str, dict[str, str]]:
    return {
        name: {"path": str(path), "sha256": sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _verify_source_manifest(manifest: dict[str, Any]) -> None:
    for name, entry in manifest["sources"].items():
        path = Path(entry["path"])
        if sha256_file(path) != entry["sha256"]:
            raise ValueError(f"sealed source drift for {name}: {path}")
    for name, entry in manifest["andes_source_guard"].items():
        path = Path(entry["path"])
        if sha256_file(path) != entry["sha256"]:
            raise ValueError(f"sealed ANDES source drift for {name}: {path}")


def _trace_hashes_by_arm() -> dict[str, dict[str, str]]:
    r274 = _load_json_with_hash(
        R274_PROVENANCE_PATH,
        R274_PROVENANCE_SHA256,
    )["trace_hashes"]
    r275 = _load_json_with_hash(
        R275_PROVENANCE_PATH,
        R275_PROVENANCE_SHA256,
    )["trace_hashes"]
    result = {
        ZERO_ARM: {
            path: digest
            for path, digest in r274.items()
            if "/screen_traces/" in path.replace("\\", "/")
            and path.endswith("__zero_support.json")
        },
        SLOW_ARM: {
            path: digest
            for path, digest in r274.items()
            if "/formal_traces/" in path.replace("\\", "/")
            and path.endswith("__droop_pi.json")
        },
        COMBINED_ARM: {
            path: digest
            for path, digest in r275.items()
            if "/r275_fast_md_authority/formal_traces/" in path.replace("\\", "/")
            and path.endswith("__common_M_pos.json")
        },
    }
    for arm, hashes in result.items():
        if len(hashes) != 24:
            raise ValueError(f"expected 24 immutable {arm} traces, found {len(hashes)}")
    return {arm: dict(sorted(hashes.items())) for arm, hashes in result.items()}


def _reused_path(arm: str, scenario_name: str) -> Path:
    if arm == ZERO_ARM:
        return (
            ROOT
            / "results/r274_prospective_active_power_authority/screen_traces"
            / f"{scenario_name}__zero_support.json"
        )
    if arm == SLOW_ARM:
        return (
            ROOT
            / "results/r274_prospective_active_power_authority/formal_traces"
            / f"{scenario_name}__droop_pi.json"
        )
    if arm == COMBINED_ARM:
        return (
            ROOT
            / "results/r275_fast_md_authority/formal_traces"
            / f"{scenario_name}__common_M_pos.json"
        )
    raise ValueError(f"no reused path for arm {arm}")


def _fast_path(out_dir: Path, scenario_name: str) -> Path:
    return out_dir / "formal_traces" / f"{scenario_name}__fast_only.json"


def _fast_trace_count(out_dir: Path) -> int:
    directory = out_dir / "formal_traces"
    return (
        len(list(directory.glob("*__fast_only.json")))
        if directory.exists()
        else 0
    )


def _validate_reused_trace(
    path: Path,
    *,
    arm: str,
    scenario: dict[str, Any],
    expected_sha256: str,
) -> dict[str, Any]:
    record = _load_json_with_hash(path, expected_sha256)
    expected_controller = {
        ZERO_ARM: "zero_support",
        SLOW_ARM: "droop_pi",
        COMBINED_ARM: "slow_droop_pi_plus_common_m_pos",
    }[arm]
    expected_round = "R275" if arm == COMBINED_ARM else "R274"
    expected = {
        "round": expected_round,
        "controller": expected_controller,
        "scenario": scenario["name"],
        "delta_u": scenario["delta_u"],
        "seed": ENV_SEED,
        "requested_steps": STEPS,
        "n_steps": STEPS,
        "completed": True,
        "tds_failed": False,
        "provenance_valid": True,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"reused {arm} trace mismatch in {path}: {key}")
    if arm == COMBINED_ARM:
        if record.get("formal_seal_sha256") != R275_FORMAL_SEAL_SHA256:
            raise ValueError(f"combined seal mismatch in {path}")
        if record.get("fast_contract_sha256") != R275_FAST_CONTRACT_SHA256:
            raise ValueError(f"combined fast contract mismatch in {path}")
    return record


def prepare_seal(*, manifest_path: Path, out_dir: Path) -> None:
    if _fast_trace_count(out_dir) != 0:
        raise ValueError("R276 seal must precede every fast-only formal trace")
    fixed_artifacts = {
        FORMAL_BANK_PATH: FORMAL_BANK_SHA256,
        R274_PROVENANCE_PATH: R274_PROVENANCE_SHA256,
        R275_PROVENANCE_PATH: R275_PROVENANCE_SHA256,
        R275_SUMMARY_PATH: R275_SUMMARY_SHA256,
        R275_FORMAL_SEAL_PATH: R275_FORMAL_SEAL_SHA256,
        R272_CONTRACT_PATH: R272_CONTRACT_SHA256,
    }
    for path, expected in fixed_artifacts.items():
        if sha256_file(path) != expected:
            raise ValueError(f"fixed input artifact drift: {path}")
    contract = frozen_fast_md_contract()
    contract_sha256 = sha256_bytes(canonical_json_bytes(contract))
    if contract_sha256 != R275_FAST_CONTRACT_SHA256:
        raise ValueError("R275 fast M/D contract payload drift")
    formal_bank, formal_bank_sha256 = load_scenario_bank(
        FORMAL_BANK_PATH,
        expected_sha256=FORMAL_BANK_SHA256,
    )
    reused_hashes = _trace_hashes_by_arm()
    for scenario in formal_bank["scenarios"]:
        for arm in (ZERO_ARM, SLOW_ARM, COMBINED_ARM):
            path = _reused_path(arm, scenario["name"])
            expected = reused_hashes[arm][str(path.relative_to(ROOT))]
            _validate_reused_trace(
                path,
                arm=arm,
                scenario=scenario,
                expected_sha256=expected,
            )
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
        "phase": "formal-fast-slow-factorial",
        "repository_head": _git_head(),
        "formal_fast_trace_count_at_freeze": 0,
        "formal_bank": {
            "path": str(FORMAL_BANK_PATH),
            "sha256": formal_bank_sha256,
            "scenario_count": formal_bank["scenario_count"],
        },
        "reused_trace_hashes": reused_hashes,
        "fast_contract": {
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
            "arms": list(ARMS),
            "new_arm": FAST_ARM,
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
        or manifest.get("phase") != "formal-fast-slow-factorial"
    ):
        raise ValueError("R276 seal identity mismatch")
    if manifest["formal_fast_trace_count_at_freeze"] != 0:
        raise ValueError("R276 seal was not frozen at zero new traces")
    if manifest["execution"]["shard_count"] != SHARD_COUNT:
        raise ValueError("R276 sealed shard count drift")
    if manifest["fast_contract"]["payload"] != frozen_fast_md_contract():
        raise ValueError("R276 fast contract payload drift")
    contract_sha256 = sha256_bytes(
        canonical_json_bytes(manifest["fast_contract"]["payload"])
    )
    if contract_sha256 != manifest["fast_contract"]["sha256"]:
        raise ValueError("R276 fast contract hash mismatch")
    _verify_source_manifest(manifest)
    for hashes in manifest["reused_trace_hashes"].values():
        for path_text, expected in hashes.items():
            if sha256_file(ROOT / path_text) != expected:
                raise ValueError(f"reused trace hash drift: {path_text}")
    return manifest, contract_sha256


def smoke(*, out_path: Path) -> None:
    record = run_fast_only_scenario(
        "r276_fast_only_smoke_bus14_pos_1p0",
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
    digest = _write_new_canonical(
        out_path,
        {"record": record, "summary": summary},
    )
    print(
        f"[smoke] completed={record['completed']} "
        f"steps={record['n_steps']}/20 sha256={digest}",
        flush=True,
    )


def _validate_fast_trace(
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
        "controller": FAST_ARM,
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
            raise ValueError(f"R276 fast trace mismatch in {path}: {key}")
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
        raise ValueError("R276 formal execution requires shard-count 3 and indices 0..2")
    manifest, fast_contract_sha256 = _verify_seal(
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
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
        path = _fast_path(out_dir, scenario["name"])
        if path.exists():
            if not resume:
                raise FileExistsError(f"formal trace exists: {path}")
            _validate_fast_trace(
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
        record = run_fast_only_scenario(
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


def _fast_only_storage_audit(
    records: list[dict[str, Any]],
    summaries: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    max_request = max(
        abs(float(value))
        for record in records
        for step in record["traces"]
        for value in step["bess_requested_power_system_pu"]
    )
    max_command = max(
        abs(float(value))
        for record in records
        for step in record["traces"]
        for value in step["bess_commanded_power_system_pu"]
    )
    max_actual = max(
        abs(float(value))
        for record in records
        for step in record["traces"]
        for value in step["bess_actual_power_system_pu"]
    )
    max_soc_deviation = max(
        abs(float(value) - 0.5)
        for record in records
        for step in record["traces"]
        for value in step["bess_soc"]
    )
    max_energy = max(
        abs(float(value))
        for record in records
        for step in record["traces"]
        for key in (
            "bess_charge_energy_mwh_total",
            "bess_discharge_energy_mwh_total",
        )
        for value in step[key]
    )
    violations = sum(
        len(step["bess_constraint_violations"])
        for record in records
        for step in record["traces"]
    )
    saturations = sum(
        bool(reasons)
        for record in records
        for step in record["traces"]
        for reasons in step["bess_saturation_reasons"]
    )
    action_audits = {
        scenario: audit_fast_md_action(summary)
        for scenario, summary in summaries.items()
    }
    checks = {
        "zero_requested_power": max_request <= 1e-12,
        "zero_commanded_power": max_command <= 1e-12,
        "zero_actual_power": max_actual <= 1e-9,
        "soc_exactly_half": max_soc_deviation <= 1e-9,
        "zero_storage_energy": max_energy <= 1e-9,
        "zero_constraint_violations": violations == 0,
        "zero_saturation_reasons": saturations == 0,
        "exact_fast_action_budget": (
            len(action_audits) == 24
            and all(all(audit.values()) for audit in action_audits.values())
        ),
    }
    return {
        "checks": checks,
        "max_abs_requested_power_system_pu": max_request,
        "max_abs_commanded_power_system_pu": max_command,
        "max_abs_actual_power_system_pu": max_actual,
        "max_abs_soc_deviation": max_soc_deviation,
        "max_abs_energy_mwh": max_energy,
        "action_audits": action_audits,
    }, all(checks.values())


def _tail_audit(
    endpoint_grid: dict[str, dict[str, dict[str, Any]]],
    scenario_names: list[str],
) -> tuple[dict[str, Any], bool]:
    result: dict[str, Any] = {}
    all_pass = True
    for endpoint in ENDPOINTS:
        combined_values = {
            name: float(endpoint_grid[name][COMBINED_ARM][endpoint])
            for name in scenario_names
        }
        best_values = {
            name: min(
                float(endpoint_grid[name][SLOW_ARM][endpoint]),
                float(endpoint_grid[name][FAST_ARM][endpoint]),
            )
            for name in scenario_names
        }
        combined_tail = empirical_upper_tail(combined_values)
        best_tail = empirical_upper_tail(best_values)
        reference = best_tail["cvar_upper_tail"]
        effect = (
            0.0
            if np.isclose(reference, 0.0, atol=1e-15)
            and np.isclose(combined_tail["cvar_upper_tail"], 0.0, atol=1e-15)
            else 100.0 * (combined_tail["cvar_upper_tail"] / reference - 1.0)
        )
        passed = bool(effect <= 5.0)
        all_pass = all_pass and passed
        result[endpoint] = {
            "combined": combined_tail,
            "best_single": best_tail,
            "effect_percent": float(effect),
            "pass": passed,
        }
    return result, all_pass


def _summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# R276 fast/slow factorial summary",
        "",
        f"**Classification:** `{summary['decision']['classification']}`",
        "",
        summary["decision"]["reason"],
        "",
        "## Registered factorial endpoints",
        "",
        "| Endpoint | Interaction (% zero) | Interaction 95% abs. CI | Combined vs best single | Joint clear |",
        "|---|---:|---:|---:|---:|",
    ]
    for endpoint in ENDPOINTS:
        evidence = summary["factorial"]["endpoints"][endpoint]
        interaction = evidence["interaction"]
        best = evidence["combined_minus_best_single"]["ratio_of_means_percent"]
        decision = summary["decision"]["endpoint_decisions"][endpoint]
        interval = interaction["absolute_percentile_95_interval"]
        lines.append(
            f"| `{endpoint}` | {interaction['percent_of_zero_point']:.6g} | "
            f"[{interval[0]:.6g}, {interval[1]:.6g}] | "
            f"{best['point']:.6g}% | {decision['joint_clear']} |"
        )
    lines.extend(["", "## Guards", ""])
    for name, passed in summary["decision"]["guards"].items():
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
    records_by_arm: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    endpoint_grid: dict[str, dict[str, dict[str, Any]]] = {}
    trace_hashes: dict[str, str] = {}
    fast_summaries: dict[str, dict[str, Any]] = {}

    for scenario in formal_bank["scenarios"]:
        name = scenario["name"]
        endpoint_grid[name] = {}
        for arm in (ZERO_ARM, SLOW_ARM, COMBINED_ARM):
            path = _reused_path(arm, name)
            expected = manifest["reused_trace_hashes"][arm][
                str(path.relative_to(ROOT))
            ]
            record = _validate_reused_trace(
                path,
                arm=arm,
                scenario=scenario,
                expected_sha256=expected,
            )
            records_by_arm[arm].append(record)
            trace_hashes[str(path.relative_to(ROOT))] = sha256_file(path)
            endpoint_grid[name][arm] = summarise_fast_md_trace(
                record,
                final_window_steps=FINAL_WINDOW_STEPS,
                fast_window_steps=FAST_WINDOW_STEPS,
            )
        path = _fast_path(out_dir, name)
        if not path.exists():
            raise FileNotFoundError(f"missing R276 fast-only trace: {path}")
        fast_record = _validate_fast_trace(
            path,
            scenario=scenario,
            formal_seal_sha256=expected_manifest_sha256,
            fast_contract_sha256=fast_contract_sha256,
        )
        records_by_arm[FAST_ARM].append(fast_record)
        trace_hashes[str(path.relative_to(ROOT))] = sha256_file(path)
        fast_summary = summarise_fast_md_trace(
            fast_record,
            final_window_steps=FINAL_WINDOW_STEPS,
            fast_window_steps=FAST_WINDOW_STEPS,
        )
        fast_summaries[name] = fast_summary
        endpoint_grid[name][FAST_ARM] = fast_summary

    scenario_names = [scenario["name"] for scenario in formal_bank["scenarios"]]
    completion_guard_pass = all(
        len(records_by_arm[arm]) == 24
        and all(
            record["completed"]
            and not record["tds_failed"]
            and record["n_steps"] == STEPS
            for record in records_by_arm[arm]
        )
        for arm in ARMS
    )
    endpoints_by_arm = {
        arm: {
            endpoint: [
                endpoint_grid[name][arm][endpoint]
                for name in scenario_names
            ]
            for endpoint in ENDPOINTS
        }
        for arm in ARMS
    }
    factorial = factorial_bootstrap(
        endpoints_by_arm,
        seed=BOOTSTRAP_SEED,
        n_resamples=BOOTSTRAP_RESAMPLES,
    )
    storage_audit, action_storage_guard_pass = _fast_only_storage_audit(
        records_by_arm[FAST_ARM],
        fast_summaries,
    )
    tail_audit, tail_guard_pass = _tail_audit(endpoint_grid, scenario_names)
    decision = classify_fast_slow_factorial(
        factorial=factorial,
        provenance_guard_pass=True,
        completion_guard_pass=completion_guard_pass,
        action_storage_guard_pass=action_storage_guard_pass,
        tail_guard_pass=tail_guard_pass,
    )
    arm_means = {
        arm: {
            endpoint: float(np.mean(endpoints_by_arm[arm][endpoint]))
            for endpoint in ENDPOINTS
        }
        for arm in ARMS
    }
    completion_pairing = {
        f"{left}_vs_{right}": paired_binary_outcome_table(
            [record["completed"] for record in records_by_arm[left]],
            [record["completed"] for record in records_by_arm[right]],
        )
        for left, right in (
            (FAST_ARM, ZERO_ARM),
            (COMBINED_ARM, SLOW_ARM),
            (COMBINED_ARM, FAST_ARM),
        )
    }
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "experiment": "r276_fast_slow_factorial",
        "decision": decision,
        "formal_bank": manifest["formal_bank"],
        "fast_contract": manifest["fast_contract"],
        "arm_means": arm_means,
        "factorial": factorial,
        "completion_pairing": completion_pairing,
        "storage_action_audit": storage_audit,
        "tail_audit": tail_audit,
        "formal_seal": {
            "path": str(manifest_path),
            "sha256": expected_manifest_sha256,
        },
        "trace_hashes": dict(sorted(trace_hashes.items())),
    }
    summary_path = out_dir / "fast_slow_factorial_summary.json"
    summary_digest = _write_new_canonical(summary_path, summary)
    markdown_path = out_dir / "fast_slow_factorial_summary.md"
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
