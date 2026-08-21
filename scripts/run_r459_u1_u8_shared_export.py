"""R459 shared provenance/model/protocol export for GPT Pro U1--U8 work.

WSL-only physical entry:
    python scripts/andes_scratch.py scripts/run_r459_u1_u8_shared_export.py probe
    python scripts/andes_scratch.py scripts/run_r459_u1_u8_shared_export.py rehearse
    python scripts/andes_scratch.py scripts/run_r459_u1_u8_shared_export.py prepare
    python scripts/andes_scratch.py scripts/run_r459_u1_u8_shared_export.py run
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_name, "1")
os.environ["DISABLE_TOGGLER"] = "1"

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from andes_rl_kundur.evaluation.u1_u8_shared_export import (  # noqa: E402
    build_object_a,
    build_object_b,
    runtime_manifest,
    sha256_file,
    verify_model_bundle,
    verify_sha256sums,
    write_json_new,
    write_model_bundle,
    write_sha256sums,
    write_text_new,
)

ROUND = "R459"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
PLAN = ROOT / "memory/rounds/R459/plan.md"
CAPACITY = ROOT / "memory/rounds/R459/capacity_evidence.json"
REHEARSAL = ROOT / "memory/rounds/R459/rehearsal.json"
REHEARSAL_AMENDMENT = ROOT / "memory/rounds/R459/rehearsal_amendment.json"
SEAL = ROOT / "memory/rounds/R459/formal_seal.json"
OUT = ROOT / "results/research_loop/r459_u1_u8_shared_export"
REQUEST = ROOT / "paper/yang_md_decoupling_marl/working/gpt_pro_additional_data_request_20260821"

SOURCE_PATHS = {
    "runner": Path(__file__).resolve(),
    "shared_export": ROOT / "src/andes_rl_kundur/evaluation/u1_u8_shared_export.py",
    "object_b_adapter": ROOT / "src/andes_rl_kundur/evaluation/vsg_energy_port_source_adapter.py",
    "object_b_bridge": ROOT / "src/andes_rl_kundur/evaluation/vsg_energy_port_source_bridge.py",
    "object_b_model": ROOT / "src/andes_rl_kundur/evaluation/vsg_energy_port_source_model.py",
    "descriptor_reduction": ROOT / "src/andes_rl_kundur/evaluation/model_first_input_bridge.py",
    "object_a_environment": ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
    "object_a_base_environment": ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
    "md_projector": ROOT / "src/andes_rl_kundur/control/per_vsg_md.py",
    "scratch_launcher": ROOT / "scripts/andes_scratch.py",
    "plan": PLAN,
}


def _utc() -> str:
    return datetime.now(UTC).isoformat()


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R459 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R459 must run through scripts/andes_scratch.py")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _authority() -> dict[str, bool]:
    return {
        "active_plan": PLAN.is_file() and "round: R459" in PLAN.read_text(encoding="utf-8")
        and "state: active" in PLAN.read_text(encoding="utf-8"),
        "active_line": LINE.is_file() and "line_id: yang-md-decoupling-marl" in LINE.read_text(encoding="utf-8")
        and "status: active" in LINE.read_text(encoding="utf-8"),
        "request_import_verified": (REQUEST / "IMPORT_NOTE.md").is_file()
        and "12/12" in (REQUEST / "IMPORT_NOTE.md").read_text(encoding="utf-8"),
        "formal_output_absent": not OUT.exists(),
    }


def _resources(start: float) -> dict[str, Any]:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "wall_seconds": time.perf_counter() - start,
        "user_cpu_seconds": float(usage.ru_utime),
        "system_cpu_seconds": float(usage.ru_stime),
        "peak_rss_bytes": int(usage.ru_maxrss) * 1024,
        "native_threads": {name: int(os.environ.get(name, "1")) for name in (
            "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"
        )},
    }


def _build() -> tuple[dict[str, Any], dict[str, Any]]:
    return build_object_a(), build_object_b()


def probe() -> dict[str, Any]:
    _assert_wsl_scratch()
    start = time.perf_counter()
    object_a, object_b = _build()
    return {
        "round": ROUND,
        "formal_authority": False,
        "mode": "capacity-probe",
        "object_a_B_shape": list(object_a["maps"]["B_u_r_physical_stack"].shape),
        "object_b_A_shape": list(object_b["continuous"]["A_continuous"].shape),
        "object_b_B_shape": list(object_b["continuous"]["B_continuous"].shape),
        "resources": _resources(start),
    }


def rehearse() -> dict[str, Any]:
    _assert_wsl_scratch()
    authority = _authority()
    if not all(authority.values()):
        raise RuntimeError(f"authority failed before rehearsal: {authority}")
    if REHEARSAL.exists():
        raise FileExistsError(REHEARSAL)
    start = time.perf_counter()
    object_a, object_b = _build()
    scratch_out = Path.cwd() / "r459_rehearsal_export"
    write_model_bundle(scratch_out, object_a, object_b)
    verification = verify_model_bundle(scratch_out)
    payload = {
        "schema_version": 1,
        "round": ROUND,
        "created_utc": _utc(),
        "formal_authority": False,
        "training_executed": False,
        "same_pre_attempt_path": True,
        "authority": authority,
        "runtime": runtime_manifest(ROOT),
        "verification": verification,
        "scratch_output": str(scratch_out),
        "resources": _resources(start),
        "passed": bool(verification["passed"] and all(authority.values())),
    }
    write_json_new(REHEARSAL, payload)
    write_text_new(Path(f"{REHEARSAL}.sha256"), f"{sha256_file(REHEARSAL)}  {REHEARSAL.name}\n")
    return payload


def prepare() -> dict[str, Any]:
    _assert_wsl_scratch()
    authority = _authority()
    if not all(authority.values()):
        raise RuntimeError(f"authority failed before seal: {authority}")
    if SEAL.exists():
        raise FileExistsError(SEAL)
    rehearsal = _read_json(REHEARSAL)
    capacity = _read_json(CAPACITY)
    if not rehearsal.get("passed"):
        raise RuntimeError("rehearsal did not pass")
    amendment = _read_json(REHEARSAL_AMENDMENT)
    if amendment.get("original_rehearsal_sha256") != sha256_file(REHEARSAL):
        raise RuntimeError("rehearsal amendment does not bind the preserved rehearsal")
    if amendment.get("scientific_path_affected") is not False:
        raise RuntimeError("rehearsal amendment is not provenance-only")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError(f"capacity is not RUN-READY: {capacity.get('readiness')}")
    runtime = runtime_manifest(ROOT)
    sources = {
        name: {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}
        for name, path in SOURCE_PATHS.items()
    }
    seal = {
        "schema_version": 1,
        "round": ROUND,
        "created_utc": _utc(),
        "formal_authority": True,
        "training_executed": False,
        "authority": authority,
        "runtime": runtime,
        "plan_sha256": sha256_file(PLAN),
        "capacity_sha256": sha256_file(CAPACITY),
        "rehearsal_sha256": sha256_file(REHEARSAL),
        "rehearsal_amendment_sha256": sha256_file(REHEARSAL_AMENDMENT),
        "request_sha256sums_sha256": sha256_file(REQUEST / "SHA256SUMS"),
        "sources": sources,
        "launch": capacity["formal_allocation"],
        "completion": {
            "required_verdict": "SHARED-MODEL-EXPORT-VALID",
            "required_hash_failures": 0,
            "output_root": OUT.relative_to(ROOT).as_posix(),
        },
    }
    write_json_new(SEAL, seal)
    write_text_new(Path(f"{SEAL}.sha256"), f"{sha256_file(SEAL)}  {SEAL.name}\n")
    return {"seal_sha256": sha256_file(SEAL), "launch": seal["launch"]}


def _load_seal() -> dict[str, Any]:
    seal = _read_json(SEAL)
    if seal.get("round") != ROUND or not seal.get("formal_authority"):
        raise RuntimeError("invalid R459 formal seal")
    if sha256_file(PLAN) != seal["plan_sha256"]:
        raise RuntimeError("plan drifted after seal")
    if sha256_file(CAPACITY) != seal["capacity_sha256"]:
        raise RuntimeError("capacity evidence drifted after seal")
    if sha256_file(REHEARSAL) != seal["rehearsal_sha256"]:
        raise RuntimeError("rehearsal drifted after seal")
    if sha256_file(REHEARSAL_AMENDMENT) != seal["rehearsal_amendment_sha256"]:
        raise RuntimeError("rehearsal amendment drifted after seal")
    for name, entry in seal["sources"].items():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed source drift: {name}")
    if OUT.exists():
        raise FileExistsError(OUT)
    return seal


def _git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, text=True, encoding="utf-8",
        errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return completed.stdout


def _input_inventory() -> list[dict[str, Any]]:
    paths = {
        "external_request": REQUEST / "SHA256SUMS",
        "r446_analysis": ROOT / "results/research_loop/r446_md_authority_fd/formal_analysis.json",
        "r447_analysis": ROOT / "results/research_loop/r447_p1_complex_response/formal_analysis.json",
        "r458_analysis": ROOT / "results/research_loop/r458_dev_select_eval_validate/formal_analysis.json",
        "r458_selection": ROOT / "results/research_loop/r458_dev_select_eval_validate/selection.json",
        "r458_seal": ROOT / "memory/rounds/R458/formal_seal.json",
    }
    rows = []
    for role, path in paths.items():
        if path.is_file():
            rows.append({
                "role": role, "path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(path), "size_bytes": path.stat().st_size,
            })
    return rows


def _write_contracts(out: Path, seal: dict[str, Any]) -> None:
    write_json_new(out / "contracts/object_registry.json", {
        "schema_version": 1,
        "objects": [
            {"object_id": "Object A", "meaning": "four GENCLS direct M/D parameter modulation", "source_round": "R446", "pooling_key": "object_a_md"},
            {"object_id": "Object B", "meaning": "four VSG sampled active-power energy ports plus three PQ inputs", "source_round": "R447", "pooling_key": "object_b_energy_port"},
        ],
        "pooling_forbidden": True,
        "reason": "different actuators, input dimensions, coordinates, and evidence lineages",
    })
    write_json_new(out / "contracts/units_and_coordinates.json", {
        "nominal_frequency_hz": 60.0, "control_period_seconds": 0.2,
        "object_a": {"normalized_action": "dimensionless", "M": "GENCLS M=2H seconds", "D": "GENCLS damping pu", "mapping": "piecewise one-sided at zero"},
        "object_b": {"control": "system pu active power", "disturbance": "system pu active PQ load", "output": "Hz", "sample_convention": "post-step"},
        "frequency_base_warning": "legacy V4 controller observation slots use 50-Hz scaling and require explicit 60/50 conversion; Object B output is physical 60-Hz frequency",
    })
    r458_analysis = _read_json(ROOT / "results/research_loop/r458_dev_select_eval_validate/formal_analysis.json")
    write_json_new(out / "contracts/profile_protocol.json", {
        "source_round": "R458", "r458_seal_sha256": sha256_file(ROOT / "memory/rounds/R458/formal_seal.json"),
        "development_profiles": ["dev_a", "dev_b"], "evaluation_profiles": ["eval_a", "eval_b", "eval_c", "eval_d"],
        "selection_before_evaluation": True, "selection_sha256": r458_analysis["selection_sha256"],
        "fixed_bank_scope": True, "distributional_transfer_probability_supported": False,
        "r459_execution": "no profile trajectories rerun; protocol is exported by hash from sealed R458",
    })
    write_json_new(out / "contracts/guard_contract.json", {
        "source_rounds": ["R452", "R458"], "relative_to_static_per_profile": True,
        "thresholds": {"joint_endpoint_improvement_min_each": 0.05, "maximum_common_harm": 0.03, "maximum_action_stress_harm": 0.10, "maximum_action_saturation_fraction": 0.05},
        "joint_rule": "valid AND both endpoints eligible AND all common no-harm AND both action-stress no-harm AND saturation pass",
        "r458_verdict": r458_analysis["classification"],
    })
    write_json_new(out / "contracts/claim_evidence_map.json", {
        "schema_version": 1, "round": ROUND,
        "claims": [
            {"claim_id": "R459-OBS-A", "scope": "Object A complete executable mapping export", "artifacts": ["model_exports/object_a/dae_snapshot.npz", "model_exports/object_a/input_output_maps.npz", "model_exports/object_a/execution_contract.json"]},
            {"claim_id": "R459-OBS-B", "scope": "Object B complete sampled-model export", "artifacts": ["model_exports/object_b/dae_snapshot.npz", "model_exports/object_b/continuous_reduced_model.npz", "model_exports/object_b/sampled_model.npz", "model_exports/object_b/controllers.npz"]},
            {"claim_id": "R459-SEP", "scope": "Object A and B are non-poolable", "artifacts": ["contracts/object_registry.json", "checks/classification.json"]},
        ],
        "downstream_math_claims_upgraded": [],
    })
    write_json_new(out / "provenance/reproduction_manifest.json", {
        **seal["runtime"], "round": ROUND, "seal_sha256": sha256_file(SEAL),
        "dirty_worktree_bound_by_patch_and_source_hashes": True,
        "formal_output_create_only": True, "training_executed": False,
    })
    write_json_new(out / "provenance/source_hashes.json", seal["sources"])
    write_json_new(out / "provenance/input_inventory.json", _input_inventory())
    write_text_new(out / "provenance/git_diff.patch", _git_output("diff", "--binary", "--no-ext-diff", "HEAD"))
    write_text_new(out / "provenance/git_status_porcelain.txt", "\n".join(seal["runtime"]["git_status_porcelain"]) + "\n")
    pip_freeze = subprocess.run([sys.executable, "-m", "pip", "freeze", "--all"], check=True, text=True, stdout=subprocess.PIPE).stdout
    write_text_new(out / "provenance/environment.txt", json.dumps(seal["runtime"], indent=2, ensure_ascii=False, sort_keys=True) + "\n\n[pip freeze --all]\n" + pip_freeze)


def run() -> dict[str, Any]:
    _assert_wsl_scratch()
    seal = _load_seal()
    started = _utc()
    start = time.perf_counter()
    object_a, object_b = _build()
    write_model_bundle(OUT, object_a, object_b)
    _write_contracts(OUT, seal)
    model_verification = verify_model_bundle(OUT)
    resources = _resources(start)
    command = {
        "command": [sys.executable, str(Path(__file__).resolve()), "run"],
        "cwd": str(Path.cwd()), "start_utc": started, "scientific_end_utc": _utc(),
        "exit_code": 0 if model_verification["passed"] else 3,
        "environment_diff": {name: os.environ.get(name) for name in (
            "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "DISABLE_TOGGLER"
        )},
        "resources": resources,
    }
    write_text_new(OUT / "provenance/commands.jsonl", json.dumps(command, ensure_ascii=False, sort_keys=True) + "\n")
    write_json_new(OUT / "checks/classification.json", model_verification)
    hashed_entries = write_sha256sums(OUT)
    hash_verification = verify_sha256sums(OUT)
    final_pass = bool(model_verification["passed"] and hash_verification["passed"])
    report = {
        "schema_version": 1, "round": ROUND, "created_utc": _utc(),
        "model_verification": model_verification, "hash_verification": hash_verification,
        "hashed_entries": hashed_entries, "resources": resources,
        "passed": final_pass,
        "verdict": "SHARED-MODEL-EXPORT-VALID" if final_pass else "SHARED-MODEL-EXPORT-INVALID",
    }
    write_json_new(OUT / "checks/verification_report.json", report)
    write_text_new(OUT / "checks/verification_report.json.sha256", f"{sha256_file(OUT / 'checks/verification_report.json')}  verification_report.json\n")
    if not final_pass:
        raise RuntimeError(json.dumps(report, ensure_ascii=False))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("probe", "rehearse", "prepare", "run"))
    args = parser.parse_args()
    if args.command == "probe":
        payload = probe()
    elif args.command == "rehearse":
        payload = rehearse()
    elif args.command == "prepare":
        payload = prepare()
    else:
        payload = run()
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
