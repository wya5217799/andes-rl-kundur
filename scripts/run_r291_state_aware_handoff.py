#!/usr/bin/env python3
"""Prepare, execute, and analyse the sealed R291 five-arm handoff gate.

Motivation
----------
R291 tests whether a causal state-aware withdrawal of fast common-inertia
support has timing-specific value beyond fixed three- and five-second
schedules.  This adapter owns immutable bank/seal/trace I/O and paired
analysis.  Controller semantics live in
``evaluation/state_aware_handoff.py``.

Usage
-----
Prepare once before any formal trace::

    python scripts/run_r291_state_aware_handoff.py prepare

Run three disjoint shards through ``scripts/andes_scratch.py``::

    python scripts/andes_scratch.py \
      scripts/run_r291_state_aware_handoff.py run-shard \
      --expected-seal-sha256 <hash> --shard-index 0 --shard-count 3

After every shard completes::

    python scripts/run_r291_state_aware_handoff.py analyse \
      --expected-seal-sha256 <hash>

Failure modes
-------------
Artifacts are never overwritten.  Source, bank, seal, controller, scenario,
or trace drift raises before interpretation.  Failed ANDES trajectories are
retained; any missing or incomplete arm makes the formal decision INVALID.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import logging
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.prospective_authority import (  # noqa: E402
    build_stratified_authority_candidates,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    load_scenario_bank,
    paired_bootstrap_contrasts,
    sha256_bytes,
    sha256_file,
    write_scenario_bank,
)
from andes_rl_kundur.evaluation.state_aware_handoff import (  # noqa: E402
    COMMON_HANDOFF,
    CONTROLLERS,
    FIXED_3S,
    FIXED_5S,
    FULL_HANDOFF,
    GUARD_ENDPOINTS,
    PRIMARY_ENDPOINTS,
    SLOW_ONLY,
    classify_state_aware_handoff,
    frozen_handoff_contract,
    run_handoff_scenario,
    summarise_handoff_trace,
)

ROUND_ID = "R291"
QUESTION_ID = "Q-0048"
CANDIDATE_SEED = 2026073001
BOOTSTRAP_SEED = 2026073002
BOOTSTRAP_RESAMPLES = 10_000
ENV_SEED = 42
STEPS = 300
SHARD_COUNT = 3
DEFAULT_SEAL = ROOT / "memory/rounds/R291/formal_seal.json"
DEFAULT_OUT = ROOT / "results/r291_state_aware_handoff"
REFERENCE_BANKS = (
    ROOT / "results/r274_prospective_active_power_authority/formal_bank.json",
    ROOT / "results/r279_fresh_bank/formal_bank.json",
)
CONTRASTS = (
    ("common_vs_fixed3", COMMON_HANDOFF, FIXED_3S),
    ("common_vs_fixed5", COMMON_HANDOFF, FIXED_5S),
    ("full_vs_fixed3", FULL_HANDOFF, FIXED_3S),
    ("full_vs_fixed5", FULL_HANDOFF, FIXED_5S),
    ("full_vs_common", FULL_HANDOFF, COMMON_HANDOFF),
    ("fixed5_vs_fixed3", FIXED_5S, FIXED_3S),
)


class _MessageCollector(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(self.format(record))


def _write_new(path: Path, payload: object) -> str:
    if path.exists() or path.with_name(path.name + ".sha256").exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(payload)
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        raise FileExistsError(f"stale temporary artifact exists: {temporary}")
    temporary.write_bytes(data)
    temporary.replace(path)
    digest = sha256_bytes(data)
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n",
        encoding="ascii",
    )
    return digest


def _load_json(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    if expected_sha256 is not None and sha256_file(path) != expected_sha256:
        raise ValueError(f"hash mismatch for {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def _path_text(path: Path) -> str:
    """Return a repository-relative path, or absolute text for isolated tests."""
    try:
        selected = path.relative_to(ROOT)
    except ValueError:
        selected = path.resolve()
    return str(selected).replace("\\", "/")


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R291/plan.md",
        "question": ROOT / "memory/questions/Q-0048.md",
        "deep_research": ROOT
        / "docs/research/2026-07-30_state_aware_multitimescale_handoff_deep_research.md",
        "runner": Path(__file__).resolve(),
        "handoff": ROOT
        / "src/andes_rl_kundur/evaluation/state_aware_handoff.py",
        "active_power": ROOT
        / "src/andes_rl_kundur/control/active_power.py",
        "fast_authority": ROOT
        / "src/andes_rl_kundur/evaluation/fast_md_authority.py",
        "physical_endpoints": ROOT
        / "src/andes_rl_kundur/evaluation/physical_endpoints.py",
        "sealed_bank": ROOT
        / "src/andes_rl_kundur/evaluation/sealed_bank.py",
        "candidate_generator": ROOT
        / "src/andes_rl_kundur/evaluation/prospective_authority.py",
        "scenario_generator": ROOT
        / "src/andes_rl_kundur/evaluation/paper_strict_eval.py",
        "storage_env": ROOT
        / "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py",
        "v4_env": ROOT
        / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
    }


def _delta_key(scenario: dict[str, Any]) -> str:
    return json.dumps(
        scenario["delta_u"],
        sort_keys=True,
        separators=(",", ":"),
    )


def _assert_fresh(
    candidate: dict[str, Any],
    references: list[dict[str, Any]],
) -> None:
    reference_keys = {
        _delta_key(scenario)
        for reference in references
        for scenario in reference["scenarios"]
    }
    duplicates = [
        scenario["name"]
        for scenario in candidate["scenarios"]
        if _delta_key(scenario) in reference_keys
    ]
    if duplicates:
        raise ValueError(
            f"R291 candidate bank duplicates viewed delta_u values: {duplicates}"
        )


def _trace_path(out_dir: Path, scenario: str, controller: str) -> Path:
    return out_dir / "traces" / f"{scenario}__{controller}.json"


def prepare(seal_path: Path, out_dir: Path) -> None:
    """Freeze the fresh bank, handoff contract, sources, and execution."""
    if seal_path.exists() or seal_path.with_name(seal_path.name + ".sha256").exists():
        raise FileExistsError(f"R291 seal already exists: {seal_path}")
    trace_dir = out_dir / "traces"
    trace_count = len(list(trace_dir.glob("*.json"))) if trace_dir.exists() else 0
    if trace_count:
        raise ValueError("R291 must be sealed before every formal trace")
    for source in _source_paths().values():
        if not source.is_file():
            raise FileNotFoundError(f"missing R291 sealed source: {source}")

    references: list[dict[str, Any]] = []
    reference_entries: list[dict[str, Any]] = []
    for path in REFERENCE_BANKS:
        reference, digest = load_scenario_bank(path)
        references.append(reference)
        reference_entries.append(
            {
                "path": _path_text(path),
                "sha256": digest,
            }
        )
    generator_path = _source_paths()["candidate_generator"]
    candidate = build_stratified_authority_candidates(
        seed=CANDIDATE_SEED,
        repository_head=_git_head(),
        generator_source_sha256=sha256_file(generator_path),
    )
    if int(candidate["scenario_count"]) != 24:
        raise ValueError("R291 candidate generator must produce exactly 24 scenarios")
    _assert_fresh(candidate, references)

    bank_path = out_dir / "formal_bank.json"
    bank_hash = write_scenario_bank(bank_path, candidate)
    contract_path = out_dir / "handoff_contract.json"
    contract_hash = _write_new(contract_path, frozen_handoff_contract())
    sources = {
        name: {
            "path": _path_text(path),
            "sha256": sha256_file(path),
        }
        for name, path in _source_paths().items()
    }
    packages: dict[str, str] = {"python": sys.version}
    for name in ("andes", "numpy", "scipy"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "NOT-INSTALLED"
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "formal-state-aware-handoff",
        "repository_head": _git_head(),
        "formal_bank": {
            "path": _path_text(bank_path),
            "sha256": bank_hash,
            "scenario_count": 24,
            "generator_seed": CANDIDATE_SEED,
            "redraw_after_failure": False,
            "performance_screening": False,
        },
        "viewed_reference_banks": reference_entries,
        "freshness": {
            "exact_delta_u_overlap_count": 0,
        },
        "handoff_contract": {
            "path": _path_text(contract_path),
            "sha256": contract_hash,
        },
        "execution": {
            "controllers": list(CONTROLLERS),
            "environment_seed": ENV_SEED,
            "steps": STEPS,
            "control_dt_s": 0.2,
            "shard_count": SHARD_COUNT,
            "maximum_andes_processes": 3,
            "formal_trace_count_at_freeze": trace_count,
            "resume_without_overwrite": True,
        },
        "statistics": {
            "contrasts": [list(row) for row in CONTRASTS],
            "primary_endpoints": list(PRIMARY_ENDPOINTS),
            "guard_endpoints": list(GUARD_ENDPOINTS),
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "confidence": 0.95,
        },
        "sources": sources,
        "packages": packages,
    }
    digest = _write_new(seal_path, payload)
    print(
        f"[sealed] {_path_text(seal_path)} sha256={digest} "
        f"bank_sha256={bank_hash}",
        flush=True,
    )


def _verify_seal(seal_path: Path, expected_sha256: str) -> dict[str, Any]:
    seal = _load_json(seal_path, expected_sha256)
    if (
        seal.get("round") != ROUND_ID
        or seal.get("question") != QUESTION_ID
        or seal.get("phase") != "formal-state-aware-handoff"
    ):
        raise ValueError("not the R291 formal handoff seal")
    for entry in seal["sources"].values():
        path = ROOT / entry["path"]
        if sha256_file(path) != entry["sha256"]:
            raise ValueError(f"sealed source drift: {entry['path']}")
    contract = _load_json(
        ROOT / seal["handoff_contract"]["path"],
        seal["handoff_contract"]["sha256"],
    )
    if contract != frozen_handoff_contract():
        raise ValueError("runtime handoff contract differs from sealed contract")
    candidate, _ = load_scenario_bank(
        ROOT / seal["formal_bank"]["path"],
        expected_sha256=seal["formal_bank"]["sha256"],
    )
    references = [
        load_scenario_bank(
            ROOT / entry["path"],
            expected_sha256=entry["sha256"],
        )[0]
        for entry in seal["viewed_reference_banks"]
    ]
    _assert_fresh(candidate, references)
    if seal["execution"]["formal_trace_count_at_freeze"] != 0:
        raise ValueError("R291 was not sealed at zero formal traces")
    return seal


def _validate_trace(
    path: Path,
    *,
    scenario: dict[str, Any],
    controller: str,
    seal: dict[str, Any],
    seal_hash: str,
) -> dict[str, Any]:
    record = _load_json(path)
    expected = {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "formal-state-aware-handoff",
        "controller": controller,
        "scenario": scenario["name"],
        "delta_u": scenario["delta_u"],
        "formal_seal_sha256": seal_hash,
        "formal_bank_sha256": seal["formal_bank"]["sha256"],
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"R291 trace provenance mismatch in {path}: {key}")
    sidecar = path.with_name(path.name + ".sha256")
    if not sidecar.is_file():
        raise ValueError(f"R291 trace is missing hash sidecar: {path}")
    sidecar_hash = sidecar.read_text(encoding="ascii").split()[0]
    if sha256_file(path) != sidecar_hash:
        raise ValueError(f"R291 trace sidecar mismatch: {path}")
    return record


def _run_retained(
    scenario: dict[str, Any],
    controller: str,
) -> dict[str, Any]:
    collector = _MessageCollector()
    logger = logging.getLogger("andes.routines.tds")
    logger.addHandler(collector)
    try:
        try:
            record = run_handoff_scenario(
                scenario["name"],
                scenario["delta_u"],
                controller_name=controller,
                seed=ENV_SEED,
                steps=STEPS,
            )
        except Exception as exc:
            record = {
                "experiment": "r291_state_aware_handoff",
                "controller": controller,
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


def run_shard(
    seal_path: Path,
    expected_sha256: str,
    out_dir: Path,
    shard_index: int,
    shard_count: int,
) -> None:
    """Run all five arms for one disjoint scenario shard."""
    seal = _verify_seal(seal_path, expected_sha256)
    if (
        shard_count != int(seal["execution"]["shard_count"])
        or not 0 <= shard_index < shard_count
    ):
        raise ValueError("R291 shard contract drift")
    bank, _ = load_scenario_bank(
        ROOT / seal["formal_bank"]["path"],
        expected_sha256=seal["formal_bank"]["sha256"],
    )
    selected = [
        scenario
        for index, scenario in enumerate(bank["scenarios"])
        if index % shard_count == shard_index
    ]
    total = len(selected) * len(CONTROLLERS)
    count = 0
    for scenario in selected:
        for controller in CONTROLLERS:
            count += 1
            path = _trace_path(out_dir, scenario["name"], controller)
            if path.exists():
                _validate_trace(
                    path,
                    scenario=scenario,
                    controller=controller,
                    seal=seal,
                    seal_hash=expected_sha256,
                )
                print(f"[resume {count:03d}/{total:03d}] {path.name}", flush=True)
                continue
            record = _run_retained(scenario, controller)
            record.update(
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "question": QUESTION_ID,
                    "phase": "formal-state-aware-handoff",
                    "location": scenario["location"],
                    "sign": scenario["sign"],
                    "severity": scenario["severity"],
                    "formal_seal_sha256": expected_sha256,
                    "formal_bank_sha256": seal["formal_bank"]["sha256"],
                    "execution_shard_index": shard_index,
                    "execution_shard_count": shard_count,
                }
            )
            digest = _write_new(path, record)
            print(
                f"[run {count:03d}/{total:03d}] {path.name} "
                f"completed={record['completed']} sha256={digest}",
                flush=True,
            )


def smoke() -> None:
    """Run two 20-step viewed-bank integration checks without endpoint output."""
    reference, _ = load_scenario_bank(REFERENCE_BANKS[0])
    scenario = reference["scenarios"][0]
    rows = []
    for controller in (COMMON_HANDOFF, FULL_HANDOFF):
        try:
            record = run_handoff_scenario(
                scenario["name"],
                scenario["delta_u"],
                controller_name=controller,
                seed=ENV_SEED,
                steps=20,
            )
            rows.append(
                {
                    "controller": controller,
                    "completed": bool(record["completed"]),
                    "tds_failed": bool(record["tds_failed"]),
                    "n_steps": int(record["n_steps"]),
                    "constraint_violation_count": sum(
                        len(step.get("bess_constraint_violations", []))
                        for step in record.get("traces", [])
                    ),
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "controller": controller,
                    "completed": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
    print(json.dumps({"smoke": rows}, sort_keys=True), flush=True)
    if not all(
        row.get("completed")
        and row.get("n_steps") == 20
        and row.get("constraint_violation_count") == 0
        for row in rows
    ):
        raise SystemExit(2)


def _trace_storage_valid(record: dict[str, Any]) -> bool:
    if not record.get("completed") or record.get("tds_failed"):
        return False
    contract = frozen_handoff_contract()
    del contract
    for row in record["traces"]:
        if row.get("bess_constraint_violations"):
            return False
        soc = np.asarray(row["bess_soc"], dtype=float)
        commanded = np.asarray(
            row["bess_commanded_power_system_pu"],
            dtype=float,
        )
        if (
            not np.all(np.isfinite(soc))
            or not np.all(np.isfinite(commanded))
            or np.any(soc < 0.2 - 1e-9)
            or np.any(soc > 0.8 + 1e-9)
            or np.any(np.abs(commanded) > 0.36 + 1e-12)
        ):
            return False
    return True


def _action_valid(controller: str, summary: dict[str, Any]) -> bool:
    contract = frozen_handoff_contract()
    budgets = contract["budgets"]
    l1 = float(summary["action_l1_agent_s"])
    max_m = float(summary["max_abs_m_action_norm"])
    max_d = float(summary["max_abs_d_action_norm"])
    if controller == SLOW_ONLY:
        return (
            np.isclose(l1, 0.0, rtol=0.0, atol=1e-12)
            and np.isclose(max_m, 0.0, rtol=0.0, atol=1e-12)
            and np.isclose(max_d, 0.0, rtol=0.0, atol=1e-12)
        )
    if not (
        max_m <= float(budgets["max_abs_m_action_norm"]) + 1e-9
        and np.isclose(max_d, 0.0, rtol=0.0, atol=1e-12)
    ):
        return False
    if controller == FIXED_3S:
        return np.isclose(
            l1,
            budgets["fixed_3s_action_l1_agent_s"],
            rtol=0.0,
            atol=1e-9,
        )
    if controller == FIXED_5S:
        return np.isclose(
            l1,
            budgets["max_action_l1_agent_s"],
            rtol=0.0,
            atol=1e-9,
        )
    return (
        l1 <= float(budgets["max_action_l1_agent_s"]) + 1e-9
        and float(summary["adaptive_internal_max_slew_per_step"])
        <= float(budgets["adaptive_internal_slew_per_step"]) + 1e-8
    )


def _upper_tail(values: list[float]) -> float:
    array = np.asarray(values, dtype=float)
    count = max(1, int(math.ceil(0.10 * array.size)))
    return float(np.mean(np.sort(array)[-count:]))


def _relative_point(contrast: dict[str, Any], endpoint: str) -> float:
    entry = contrast["endpoints"][endpoint]["ratio_of_means_percent"]["point"]
    return float(entry) if entry is not None else float("inf")


def _no_harm(
    *,
    contrast: dict[str, Any],
    left_endpoints: dict[str, list[float]],
    right_endpoints: dict[str, list[float]],
) -> tuple[bool, dict[str, Any]]:
    details: dict[str, Any] = {}
    passed = True
    for endpoint in (*PRIMARY_ENDPOINTS, *GUARD_ENDPOINTS):
        point = _relative_point(contrast, endpoint)
        left_tail = _upper_tail(left_endpoints[endpoint])
        right_tail = _upper_tail(right_endpoints[endpoint])
        tail_ratio = (
            100.0 * (left_tail / right_tail - 1.0)
            if not np.isclose(right_tail, 0.0, rtol=0.0, atol=1e-15)
            else float("inf")
        )
        endpoint_pass = point <= 5.0 and tail_ratio <= 5.0
        details[endpoint] = {
            "ratio_of_means_point_percent": point,
            "left_upper_10pct_tail": left_tail,
            "right_upper_10pct_tail": right_tail,
            "tail_percent": tail_ratio,
            "pass": endpoint_pass,
        }
        passed = passed and endpoint_pass
    return passed, details


def analyse(
    seal_path: Path,
    expected_sha256: str,
    out_dir: Path,
) -> None:
    """Verify all retained traces, compute paired evidence, and decide once."""
    seal = _verify_seal(seal_path, expected_sha256)
    bank, bank_hash = load_scenario_bank(
        ROOT / seal["formal_bank"]["path"],
        expected_sha256=seal["formal_bank"]["sha256"],
    )
    trace_hashes: dict[str, str] = {}
    trace_summaries: list[dict[str, Any]] = []
    records: dict[tuple[str, str], dict[str, Any]] = {}
    summaries: dict[tuple[str, str], dict[str, Any]] = {}
    missing: list[str] = []
    for scenario in bank["scenarios"]:
        for controller in CONTROLLERS:
            path = _trace_path(out_dir, scenario["name"], controller)
            if not path.is_file():
                missing.append(str(path.relative_to(ROOT)).replace("\\", "/"))
                continue
            record = _validate_trace(
                path,
                scenario=scenario,
                controller=controller,
                seal=seal,
                seal_hash=expected_sha256,
            )
            records[(scenario["name"], controller)] = record
            trace_hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = (
                sha256_file(path)
            )
            row: dict[str, Any] = {
                "scenario": scenario["name"],
                "controller": controller,
                "completed": bool(record.get("completed")),
                "tds_failed": bool(record.get("tds_failed")),
                "n_steps": int(record.get("n_steps", 0)),
                "setup_error": record.get("setup_error"),
                "solver_messages": record.get("solver_messages", []),
            }
            if record.get("completed") and not record.get("tds_failed"):
                try:
                    summary = summarise_handoff_trace(record)
                    summaries[(scenario["name"], controller)] = summary
                    row["summary"] = summary
                except Exception as exc:
                    row["summary_error"] = {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    }
            trace_summaries.append(row)

    controller_summaries: dict[str, dict[str, Any]] = {}
    for controller in CONTROLLERS:
        controller_records = [
            records.get((scenario["name"], controller))
            for scenario in bank["scenarios"]
        ]
        available_summaries = [
            summaries[(scenario["name"], controller)]
            for scenario in bank["scenarios"]
            if (scenario["name"], controller) in summaries
        ]
        complete_count = sum(
            bool(record and record.get("completed") and not record.get("tds_failed"))
            for record in controller_records
        )
        constraint_count = sum(
            len(step.get("bess_constraint_violations", []))
            for record in controller_records
            if record
            for step in record.get("traces", [])
        )
        action_pass = (
            len(available_summaries) == 24
            and all(_action_valid(controller, summary) for summary in available_summaries)
        )
        storage_pass = (
            all(record is not None for record in controller_records)
            and all(
                _trace_storage_valid(record)
                for record in controller_records
                if record is not None
            )
        )
        controller_summaries[controller] = {
            "complete_count": complete_count,
            "failure_count": 24 - complete_count,
            "constraint_violation_count": constraint_count,
            "action_budget_pass": action_pass,
            "storage_guard_pass": storage_pass,
            "tail_guard_pass": len(available_summaries) == 24,
            "forced_release_count": sum(
                bool(summary.get("forced_release", False))
                for summary in available_summaries
            ),
            "action_l1_agent_s": (
                [float(row["action_l1_agent_s"]) for row in available_summaries]
                if len(available_summaries) == 24
                else None
            ),
        }

    all_complete = (
        not missing
        and len(records) == 24 * len(CONTROLLERS)
        and len(summaries) == 24 * len(CONTROLLERS)
    )
    bootstrap: dict[str, Any] | None = None
    guard_no_harm: dict[str, bool] = {}
    guard_details: dict[str, Any] = {}
    if all_complete:
        endpoint_names = (
            *PRIMARY_ENDPOINTS,
            *GUARD_ENDPOINTS,
            "action_l1_agent_s",
        )
        endpoints: dict[str, dict[str, list[float]]] = {
            controller: {
                endpoint: [
                    float(summaries[(scenario["name"], controller)][endpoint])
                    for scenario in bank["scenarios"]
                ]
                for endpoint in endpoint_names
            }
            for controller in CONTROLLERS
        }
        bootstrap = paired_bootstrap_contrasts(
            endpoints,
            contrasts=CONTRASTS,
            seed=BOOTSTRAP_SEED,
            n_resamples=BOOTSTRAP_RESAMPLES,
        )
        for name, left, right in CONTRASTS:
            if name == "fixed5_vs_fixed3":
                continue
            passed, details = _no_harm(
                contrast=bootstrap["contrasts"][name],
                left_endpoints=endpoints[left],
                right_endpoints=endpoints[right],
            )
            guard_no_harm[name] = passed
            guard_details[name] = details
        decision = classify_state_aware_handoff(
            controller_summaries=controller_summaries,
            contrasts=bootstrap["contrasts"],
            provenance_hashes_match=True,
            guard_no_harm=guard_no_harm,
        )
    else:
        decision = {
            "classification": "INVALID",
            "reason": "missing, incomplete, failed, or non-summarisable formal traces",
            "guards": {
                "missing_trace_count": len(missing),
                "record_count": len(records),
                "summary_count": len(summaries),
                "expected_trace_count": 24 * len(CONTROLLERS),
            },
            "common_timing_gate": False,
            "full_incremental_gate": False,
            "recommended_state_set": "none",
        }

    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "experiment": "r291_state_aware_handoff",
        "formal_seal_sha256": expected_sha256,
        "formal_bank_sha256": bank_hash,
        "scenario_count": 24,
        "controller_count": len(CONTROLLERS),
        "expected_trace_count": 24 * len(CONTROLLERS),
        "observed_trace_count": len(records),
        "missing_traces": missing,
        "controller_summaries": controller_summaries,
        "paired_bootstrap": bootstrap,
        "guard_no_harm": guard_no_harm,
        "guard_details": guard_details,
        "decision": decision,
        "trace_summaries": trace_summaries,
    }
    summary_path = out_dir / "formal_summary.json"
    summary_hash = _write_new(summary_path, payload)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "repository_head": _git_head(),
        "formal_seal": {
            "path": _path_text(seal_path),
            "sha256": expected_sha256,
        },
        "formal_bank": seal["formal_bank"],
        "handoff_contract": seal["handoff_contract"],
        "formal_summary": {
            "path": _path_text(summary_path),
            "sha256": summary_hash,
        },
        "source_hashes": seal["sources"],
        "trace_hashes": dict(sorted(trace_hashes.items())),
        "paper_files_modified_during_execution": False,
    }
    provenance_hash = _write_new(out_dir / "provenance.json", provenance)
    print(
        f"[analysed] classification={decision['classification']} "
        f"summary_sha256={summary_hash} provenance_sha256={provenance_hash}",
        flush=True,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("smoke")

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    prepare_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)

    run_parser = subparsers.add_parser("run-shard")
    run_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    run_parser.add_argument("--expected-seal-sha256", required=True)
    run_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    run_parser.add_argument("--shard-index", type=int, required=True)
    run_parser.add_argument("--shard-count", type=int, default=SHARD_COUNT)

    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse_parser.add_argument("--expected-seal-sha256", required=True)
    analyse_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.command == "smoke":
        smoke()
    elif args.command == "prepare":
        prepare(args.seal, args.out_dir)
    elif args.command == "run-shard":
        run_shard(
            args.seal,
            args.expected_seal_sha256,
            args.out_dir,
            args.shard_index,
            args.shard_count,
        )
    elif args.command == "analyse":
        analyse(args.seal, args.expected_seal_sha256, args.out_dir)
    else:  # pragma: no cover
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
