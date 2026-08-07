"""Seal and execute R351's matched three-edge physical canary.

The entrypoint has no optimizer, training, or performance-comparison command.
Physical subcommands are WSL-only and must be launched through
``scripts/andes_scratch.py`` so ANDES scratch files stay isolated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from scripts import run_r344_deterministic_bridge as r344  # noqa: E402
from andes_rl_kundur.control.active_power import (  # noqa: E402
    r272_frozen_bess_contract,
)
from andes_rl_kundur.control.model_first_distributed_edge import (  # noqa: E402
    MatchedEdgeActionGovernor,
)
from andes_rl_kundur.env.andes.model_first_contract import (  # noqa: E402
    ACTION_EDGES,
    active_power_incidence,
)

ROUND_ID = "R351"
QUESTION_ID = "Q-0092"
PLAN = ROOT / "memory/rounds/R351/plan.md"
QUESTION = ROOT / "memory/questions/Q-0092.md"
PLUMBING_REHEARSAL_RECORD = ROOT / "memory/rounds/R351/rehearsal.json"
REHEARSAL_RECORD = ROOT / "memory/rounds/R351/formal_rehearsal_v2.json"
CAPACITY_RECORD = ROOT / "memory/rounds/R351/capacity_measurement.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R351/formal_seal.json"
DEFAULT_OUT = ROOT / "results/r351_matched_distributed_bridge"
EDGE_FLOW = 0.05
ACTIVE_INTERVALS = 5
RECOVERY_INTERVALS = 20
PROCESS_BUDGET = 2


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _path_text(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_new_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical_bytes(payload)
    with path.open("xb") as handle:
        handle.write(data)
    digest = hashlib.sha256(data).hexdigest()
    with path.with_name(path.name + ".sha256").open(
        "x", encoding="ascii", newline="\n"
    ) as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def _read_hashed_json(path: Path) -> dict[str, Any]:
    expected = path.with_name(path.name + ".sha256").read_text(
        encoding="ascii"
    ).split()[0]
    if _sha256_file(path) != expected:
        raise ValueError(f"hash mismatch: {path}")
    return _read_json(path)


def build_zero_specs() -> list[dict[str, Any]]:
    return [
        {
            "record_index": index,
            "mode": "zero_canary",
            "point": point,
            "scenario_id": f"{point}_matched_edge_zero",
            "arm": "matched_edge_zero",
            "active_intervals": 0,
            "total_steps": ACTIVE_INTERVALS,
        }
        for index, point in enumerate(("FV0", "FV1"))
    ]


def build_signed_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    index = len(build_zero_specs())
    for point in ("FV0", "FV1"):
        for edge_index, edge in enumerate(ACTION_EDGES):
            for sign in (-1, 1):
                specs.append(
                    {
                        "record_index": index,
                        "mode": "signed_canary",
                        "point": point,
                        "scenario_id": (
                            f"{point}_edge_{edge[0]}_{edge[1]}_"
                            f"{'positive' if sign > 0 else 'negative'}"
                        ),
                        "arm": "matched_endpoint_local_three_edge",
                        "edge_index": edge_index,
                        "coordinate_index": edge_index + 1,
                        "sign": sign,
                        "magnitude_system_pu": EDGE_FLOW,
                        "active_intervals": ACTIVE_INTERVALS,
                        "recovery_intervals": RECOVERY_INTERVALS,
                        "total_steps": ACTIVE_INTERVALS + RECOVERY_INTERVALS,
                    }
                )
                index += 1
    return specs


def governed_request_profile(spec: dict[str, Any]) -> np.ndarray:
    """Generate the exact node request profile through the matched governor."""

    steps = int(spec["total_steps"])
    governor = MatchedEdgeActionGovernor(
        physical_contract=r272_frozen_bess_contract(),
        edge_flow_limit_system_pu=EDGE_FLOW,
        edge_slew_limit_system_pu=EDGE_FLOW,
    )
    previous_edge = np.zeros(3)
    previous_command = np.zeros(4)
    profile: list[np.ndarray] = []
    for step in range(steps):
        action = np.zeros(3)
        if spec["mode"] == "signed_canary" and step < int(spec["active_intervals"]):
            action[int(spec["edge_index"])] = int(spec["sign"])
        governed = governor.govern(
            normalized_edge_actions=action,
            previous_edge_flows_system_pu=previous_edge,
            base_power_request_system_pu=np.zeros(4),
            previous_commanded_power_system_pu=previous_command,
            soc=np.full(4, 0.5),
            voltage_pu=np.ones(4),
            dt_seconds=0.2,
        )
        profile.append(governed.physical_projection.commanded_power_system_pu.copy())
        previous_edge = governed.executed_edge_flows_system_pu.copy()
        previous_command = governed.physical_projection.commanded_power_system_pu.copy()
    return np.asarray(profile)


def _profile_contract(spec: dict[str, Any]) -> dict[str, Any]:
    profile = governed_request_profile(spec)
    return {
        "record_index": int(spec["record_index"]),
        "scenario_id": str(spec["scenario_id"]),
        "shape": list(profile.shape),
        "sha256": _payload_sha256(profile.tolist()),
    }


def build_contract() -> dict[str, Any]:
    zero = build_zero_specs()
    signed = build_signed_specs()
    profiles = [_profile_contract(spec) for spec in zero + signed]
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "matched-neighbour-edge-execution-gate",
        "information_pattern": "endpoint-neighbour-only",
        "action_edges": [list(edge) for edge in ACTION_EDGES],
        "action_dimension": 3,
        "edge_flow_limit_system_pu": EDGE_FLOW,
        "edge_slew_limit_system_pu": EDGE_FLOW,
        "active_intervals": ACTIVE_INTERVALS,
        "recovery_intervals": RECOVERY_INTERVALS,
        "zero_record_count": len(zero),
        "signed_record_count": len(signed),
        "total_record_count": len(zero) + len(signed),
        "profiles": profiles,
        "physical_guards": r344.build_contract()["physical_guards"],
        "signed_guards": r344.build_contract()["canaries"],
        "worker_processes": PROCESS_BUDGET,
        "native_threads_per_process": 1,
        "training_executed": False,
        "performance_comparison_executed": False,
    }


def classify_canary_records(records: list[dict[str, Any]]) -> str:
    if len(records) != 14 or any(
        row.get("integrity_valid") is not True for row in records
    ):
        return "INVALID-DISTRIBUTED-EDGE-EXECUTION"
    if any(row.get("matched_governor_valid") is not True for row in records):
        return "INVALID-DISTRIBUTED-EDGE-CONTRACT"
    if any(row.get("physical_guards_pass") is not True for row in records):
        return "DISTRIBUTED-EDGE-PHYSICAL-GUARD-FAIL"
    return "DISTRIBUTED-EDGE-EXECUTION-ELIGIBLE"


def _source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "adapter": Path(__file__).resolve(),
        "controller": ROOT
        / "src/andes_rl_kundur/control/model_first_distributed_edge.py",
        "controller_tests": ROOT / "tests/test_model_first_distributed_edge.py",
        "adapter_tests": ROOT / "tests/test_r351_matched_distributed_bridge.py",
        "plan": PLAN,
        "question": QUESTION,
        "r344_bridge": ROOT / "scripts/run_r344_deterministic_bridge.py",
        "physical_contract": ROOT / "src/andes_rl_kundur/control/active_power.py",
        "headroom_allocator": ROOT
        / "src/andes_rl_kundur/control/headroom_aware_edge_allocation.py",
        "model_first_contract": ROOT
        / "src/andes_rl_kundur/env/andes/model_first_contract.py",
    }
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in sources.items()
    }


def _bind_r344_identity() -> None:
    r344.ROUND_ID = ROUND_ID
    r344.QUESTION_ID = QUESTION_ID


def _run_specs(
    specs: list[dict[str, Any]],
    *,
    stage: str,
    trace_root: Path,
    seal_digest: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _bind_r344_identity()
    records, process = r344._run_physical_specs(
        specs=specs,
        stage=stage,
        process_budget=PROCESS_BUDGET,
        trace_root=trace_root,
        seal_digest=seal_digest,
    )
    specs_by_index = {int(spec["record_index"]): spec for spec in specs}
    incidence = active_power_incidence()
    for row in records:
        spec = specs_by_index[int(row["record_index"])]
        profile = governed_request_profile(spec)
        if spec["mode"] == "signed_canary":
            coordinate = np.zeros(3)
            coordinate[int(spec["edge_index"])] = (
                int(spec["sign"]) * float(spec["magnitude_system_pu"])
            )
            expected = np.zeros_like(profile)
            expected[: int(spec["active_intervals"])] = incidence @ coordinate
        else:
            expected = np.zeros_like(profile)
        row["matched_governor_valid"] = bool(
            np.allclose(profile, expected, rtol=0.0, atol=1.0e-12)
        )
        row["matched_governor_profile_sha256"] = _payload_sha256(profile.tolist())
        row["training_executed"] = False
        row["performance_comparison_executed"] = False
    return records, process


def rehearse(record_path: Path = REHEARSAL_RECORD) -> str:
    if os.name != "posix":
        raise RuntimeError("R351 rehearsal is WSL/POSIX-only")
    if ROOT.resolve() == Path.cwd().resolve() or ROOT.resolve() not in Path.cwd().resolve().parents:
        raise RuntimeError("R351 rehearsal requires repository scratch isolation")
    formal_paths = [DEFAULT_SEAL, DEFAULT_OUT, REHEARSAL_RECORD]
    preexisting = [str(path) for path in formal_paths if path.exists() and path != record_path]
    if preexisting:
        raise FileExistsError(f"R351 pre-rehearsal artifact exists: {preexisting}")
    installed = r344._installed_andes_identity()
    contract = build_contract()
    return _write_new_json(
        record_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "installed_andes": installed,
            "contract_payload_sha256": _payload_sha256(contract),
            "sources": _source_manifest(),
            "checks": {
                "scratch_isolation": True,
                "inventory_count": contract["total_record_count"] == 14,
                "all_profiles_finite": all(
                    np.all(np.isfinite(governed_request_profile(spec)))
                    for spec in build_zero_specs() + build_signed_specs()
                ),
                "formal_output_absent": not DEFAULT_OUT.exists()
                and not DEFAULT_SEAL.exists(),
                "physical_trajectory_executed": False,
            },
        },
    )


def measure_capacity(record_path: Path = CAPACITY_RECORD) -> str:
    if os.name != "posix":
        raise RuntimeError("R351 capacity measurement is WSL/POSIX-only")
    if not PLUMBING_REHEARSAL_RECORD.exists():
        raise RuntimeError("R351 capacity measurement requires rehearsal")
    scratch = Path.cwd() / "r351_capacity_measurement"
    records, process = _run_specs(
        [build_zero_specs()[0], build_signed_specs()[0]],
        stage="r351_capacity",
        trace_root=scratch / "traces",
        seal_digest="capacity-measurement-not-a-formal-seal",
    )
    valid = bool(
        len(records) == 2
        and process.get("process_guard") is True
        and all(row.get("physical_guards_pass") is True for row in records)
        and all(row.get("matched_governor_valid") is True for row in records)
    )
    return _write_new_json(
        record_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "representative_records": [
                row["scenario_id"] for row in records
            ],
            "worker_processes": PROCESS_BUDGET,
            "native_threads_per_process": 1,
            "host_logical_processors": os.cpu_count(),
            "other_reserved_processes": 0,
            "process": process,
            "valid": valid,
            "scientific_outcomes_inspected": False,
            "formal_authority": False,
        },
    )


def rehearsal_passed(rehearsal: dict[str, Any]) -> bool:
    """Require every rehearsal guard, including explicit outcome blindness."""

    checks = rehearsal.get("checks", {})
    return bool(
        checks.get("scratch_isolation") is True
        and checks.get("inventory_count") is True
        and checks.get("all_profiles_finite") is True
        and checks.get("formal_output_absent") is True
        and checks.get("physical_trajectory_executed") is False
    )


def prepare(seal_path: Path = DEFAULT_SEAL) -> str:
    rehearsal = _read_hashed_json(REHEARSAL_RECORD)
    capacity = _read_hashed_json(CAPACITY_RECORD)
    if not rehearsal_passed(rehearsal) or capacity.get("valid") is not True:
        raise RuntimeError("R351 rehearsal and capacity gates must pass before seal")
    if DEFAULT_OUT.exists():
        raise FileExistsError("R351 result root exists before seal")
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "sources": _source_manifest(),
        "launch": {
            "host_process_budget": PROCESS_BUDGET,
            "wsl_python_processes": PROCESS_BUDGET,
            "other_reserved_processes": 0,
            "native_threads_per_process": 1,
            "rehearsal_sha256": _sha256_file(REHEARSAL_RECORD),
            "capacity_sha256": _sha256_file(CAPACITY_RECORD),
        },
        "formal_artifacts_create_only": True,
        "retry_authorized": False,
        "training_authorized": False,
    }
    return _write_new_json(seal_path, seal)


def load_seal(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    seal = _read_hashed_json(path)
    digest = _sha256_file(path)
    if digest != expected_sha256:
        raise RuntimeError("R351 seal digest mismatch")
    if seal.get("contract") != build_contract():
        raise RuntimeError("R351 contract drift")
    if seal.get("contract_payload_sha256") != _payload_sha256(build_contract()):
        raise RuntimeError("R351 contract payload drift")
    for source in seal.get("sources", {}).values():
        if _sha256_file(ROOT / source["path"]) != source["sha256"]:
            raise RuntimeError(f"R351 sealed source drift: {source['path']}")
    return seal, digest


def execute_canaries(
    *,
    seal_path: Path,
    expected_sha256: str,
    out_dir: Path = DEFAULT_OUT,
) -> str:
    _, seal_digest = load_seal(seal_path, expected_sha256)
    out_dir.mkdir(parents=True, exist_ok=False)
    attempt_digest = _write_new_json(
        out_dir / "attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "retry_authorized": False,
        },
    )
    zero, zero_process = _run_specs(
        build_zero_specs(),
        stage="r351_zero",
        trace_root=out_dir / "zero_traces",
        seal_digest=seal_digest,
    )
    if any(
        not row["integrity_valid"]
        or not row["matched_governor_valid"]
        or not row["physical_guards_pass"]
        for row in zero
    ):
        signed: list[dict[str, Any]] = []
        signed_process: dict[str, Any] = {"not_started": True}
    else:
        signed, signed_process = _run_specs(
            build_signed_specs(),
            stage="r351_signed",
            trace_root=out_dir / "signed_traces",
            seal_digest=seal_digest,
        )
    records = sorted(zero + signed, key=lambda row: int(row["record_index"]))
    classification = classify_canary_records(records)
    execution_digest = _write_new_json(
        out_dir / "execution.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "seal_sha256": seal_digest,
            "attempt_sha256": attempt_digest,
            "record_count": len(records),
            "zero_process": zero_process,
            "signed_process": signed_process,
            "records": records,
            "training_executed": False,
            "performance_comparison_executed": False,
        },
    )
    analysis_digest = _write_new_json(
        out_dir / "analysis.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "seal_sha256": seal_digest,
            "execution_sha256": execution_digest,
            "classification": classification,
            "record_count": len(records),
            "all_physical_guards_pass": bool(
                len(records) == 14
                and all(row["physical_guards_pass"] for row in records)
            ),
            "all_matched_governor_checks_pass": bool(
                len(records) == 14
                and all(row["matched_governor_valid"] for row in records)
            ),
            "deterministic_tuning_authorized": (
                classification == "DISTRIBUTED-EDGE-EXECUTION-ELIGIBLE"
            ),
            "training_authorized": False,
        },
    )
    _write_new_json(
        out_dir / "manifest.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "entries": [
                {"path": _path_text(out_dir / "attempt.json"), "sha256": attempt_digest},
                {"path": _path_text(out_dir / "execution.json"), "sha256": execution_digest},
                {"path": _path_text(out_dir / "analysis.json"), "sha256": analysis_digest},
                *[row["trace"] for row in records],
            ],
        },
    )
    print(f"classification={classification}", flush=True)
    return analysis_digest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("rehearse")
    commands.add_parser("measure-capacity")
    commands.add_parser("prepare")
    execute = commands.add_parser("execute-canaries")
    execute.add_argument("--expected-seal-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rehearse":
        print(f"rehearsal_sha256={rehearse()}", flush=True)
        return 0
    if args.command == "measure-capacity":
        print(f"capacity_sha256={measure_capacity()}", flush=True)
        return 0
    if args.command == "prepare":
        print(f"seal_sha256={prepare()}", flush=True)
        return 0
    if args.command == "execute-canaries":
        print(
            "analysis_sha256="
            f"{execute_canaries(seal_path=DEFAULT_SEAL, expected_sha256=args.expected_seal_sha256)}",
            flush=True,
        )
        return 0
    raise RuntimeError(f"unsupported R351 command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
