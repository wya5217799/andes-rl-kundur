#!/usr/bin/env python3
"""Seal, run, and analyse the R306 model-first Stage-0 canary.

``prepare`` and ``analyse`` are import-safe on Windows.  ``run`` imports ANDES
only inside the command and must be launched through ``scripts/andes_scratch.py``
with the documented WSL interpreter.  Every formal artifact is create-only and
has a SHA-256 sidecar.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import platform
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from andes_rl_kundur.env.andes.model_first_contract import (  # noqa: E402
    ModelFirstConfig,
)

ROUND_ID = "R306"
QUESTION_ID = "Q-0062"
PLAN = ROOT / "memory/rounds/R306/plan.md"
QUESTION = ROOT / "memory/questions/Q-0062.md"
DEFAULT_SEAL = ROOT / "memory/rounds/R306/model_first_stage0_seal.json"
DEFAULT_OUT = ROOT / "results/r306_model_first_stage0"
EXPECTED_M_SYSTEM = np.full(4, 400.0)
EXPECTED_D_SYSTEM = np.full(4, 200.0)
STAGE0_LIMITS = {
    "time_increment_seconds": 0.2,
    "time_tolerance_seconds": 1e-9,
    "dae_residual_max": 1e-8,
    "md_tolerance": 1e-10,
    "power_zero_tolerance": 1e-8,
    "soc_drift_max": 1e-8,
}
REQUIRED_ESD1_INTERNAL_FIELDS = (
    "Pext0",
    "Pext",
    "Pref",
    "Psum",
    "Ipul",
    "Ipcmd_y",
    "Ipout_y",
    "Ipmin",
    "Ipmax",
    "Fvl",
    "Fvh",
    "Ffl",
    "Ffh",
    "v",
    "SOC",
)
REQUIRED_STAGE0_GUARDS = (
    "identity_and_sample_count",
    "pflow_tds_exit",
    "finite_state_algebraic",
    "physical_frequency",
    "time_increment",
    "dae_residual",
    "md_readback",
    "no_md_writes",
    "power_layers",
    "soc",
    "esd1_internal_telemetry",
    "line_8_in_service",
    "g4_retained",
    "graph_and_index_identity",
)
EXPECTED_STRUCTURAL = {
    "node_device_rows": [
        [0, "VSG_1", "R272_BESS_1", 12, 7, 1],
        [1, "VSG_2", "R272_BESS_2", 16, 8, 1],
        [2, "VSG_3", "R272_BESS_3", 14, 10, 2],
        [3, "VSG_4", "R272_BESS_4", 15, 9, 2],
    ],
    "communication_edges": [[0, 1], [0, 3], [1, 2], [2, 3]],
    "action_edges": [[0, 1], [1, 2], [2, 3]],
    "action_incidence": [
        [1.0, 0.0, 0.0],
        [-1.0, 1.0, 0.0],
        [0.0, -1.0, 1.0],
        [0.0, 0.0, -1.0],
    ],
    "action_rank": 3,
    "disturbance_graph": {"kind": "none", "edited_devices": []},
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _payload_sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _write_new_json(path: Path, payload: object) -> str:
    sidecar = path.with_name(path.name + ".sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"formal artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical_bytes(payload)
    digest = hashlib.sha256(data).hexdigest()
    with path.open("xb") as handle:
        handle.write(data)
    with sidecar.open("x", encoding="ascii", newline="\n") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def _read_verified_json(
    path: Path,
    expected_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    sidecar = path.with_name(path.name + ".sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"artifact or sidecar missing: {path}")
    digest = _sha256_file(path)
    recorded = sidecar.read_text(encoding="ascii").split()[0].lower()
    if recorded != digest:
        raise RuntimeError(f"sidecar mismatch for {path}")
    if expected_sha256 is not None and digest != expected_sha256.lower():
        raise RuntimeError(f"unexpected SHA-256 for {path}: {digest}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object: {path}")
    return payload, digest


def _path_text(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _runtime_record() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "andes": importlib.metadata.version("andes")
        if importlib.util.find_spec("andes") is not None
        else "not-installed",
    }


def _source_paths() -> dict[str, Path]:
    return {
        "plan": PLAN,
        "question": QUESTION,
        "adapter": Path(__file__).resolve(),
        "model_contract": ROOT
        / "paper/decoupling_marl_model_first/working/model_contract.md",
        "pure_contract": ROOT
        / "src/andes_rl_kundur/env/andes/model_first_contract.py",
        "model_first_environment": ROOT
        / "src/andes_rl_kundur/env/andes/model_first_env.py",
        "storage_environment": ROOT
        / "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py",
        "v4_environment": ROOT
        / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "base_environment": ROOT
        / "src/andes_rl_kundur/env/andes/base_env.py",
        "active_power_contract": ROOT
        / "src/andes_rl_kundur/control/active_power.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "pure_tests": ROOT / "tests/test_model_first_contract.py",
        "adapter_tests": ROOT / "tests/test_r306_model_first_stage0.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    missing = [path for path in _source_paths().values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing sealed sources: {missing}")
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _verify_sources(seal: Mapping[str, Any]) -> None:
    for name, entry in seal["sources"].items():
        path = ROOT / entry["path"]
        observed = _sha256_file(path)
        if observed != entry["sha256"]:
            raise RuntimeError(
                f"sealed source drift for {name}: {entry['sha256']} != {observed}"
            )


def _finite_vector(value: Any, *, length: int = 4) -> bool:
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return False
    return bool(array.shape == (length,) and np.all(np.isfinite(array)))


def _all_zero(value: Any, tolerance: float) -> bool:
    return bool(
        _finite_vector(value)
        and np.max(np.abs(np.asarray(value, dtype=float))) <= tolerance
    )


def _sample_guard(samples: Sequence[Mapping[str, Any]], predicate) -> bool:
    try:
        return bool(samples and all(predicate(sample) for sample in samples))
    except (KeyError, TypeError, ValueError):
        return False


def evaluate_stage0_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute every Stage-0 guard from raw report fields, fail-closed."""

    raw_samples = report.get("samples")
    samples = raw_samples if isinstance(raw_samples, list) else []
    limits = STAGE0_LIMITS
    identity = bool(
        report.get("round") == ROUND_ID
        and report.get("question") == QUESTION_ID
        and isinstance(report.get("seal_sha256"), str)
        and len(str(report.get("seal_sha256"))) == 64
        and len(samples) == 5
    )

    pflow_tds_exit = _sample_guard(
        samples,
        lambda row: row["pflow_converged"] is True
        and row["tds_failed"] is False
        and row["system_exit_code"] == 0,
    )
    finite_state = _sample_guard(
        samples,
        lambda row: row["finite_state_algebraic"] is True,
    )
    physical_frequency = _sample_guard(
        samples,
        lambda row: float(row["andes_nominal_frequency_hz"]) == 60.0,
    )
    time_increment = False
    try:
        times = [float(report["initial_time"]), *[float(row["time"]) for row in samples]]
        time_increment = bool(
            len(times) == 6
            and np.all(
                np.abs(np.diff(times) - limits["time_increment_seconds"])
                <= limits["time_tolerance_seconds"]
            )
        )
    except (KeyError, TypeError, ValueError):
        time_increment = False
    dae_residual = _sample_guard(
        samples,
        lambda row: np.isfinite(float(row["dae_residual_max"]))
        and float(row["dae_residual_max"]) <= limits["dae_residual_max"],
    )
    md_readback = _sample_guard(
        samples,
        lambda row: _finite_vector(row["vsg_m_actual_system"])
        and _finite_vector(row["vsg_d_actual_system"])
        and np.max(
            np.abs(np.asarray(row["vsg_m_actual_system"]) - EXPECTED_M_SYSTEM)
        )
        <= limits["md_tolerance"]
        and np.max(
            np.abs(np.asarray(row["vsg_d_actual_system"]) - EXPECTED_D_SYSTEM)
        )
        <= limits["md_tolerance"],
    )
    no_md_writes = _sample_guard(
        samples,
        lambda row: row["md_write_count"] == 0,
    )
    zero_power_fields = (
        "bess_requested_power_system_pu",
        "bess_commanded_power_system_pu",
        "bess_external_command_readback_system_pu",
        "bess_internal_power_reference_system_pu",
        "bess_actual_power_system_pu",
    )
    power_layers = _sample_guard(
        samples,
        lambda row: all(
            _all_zero(row[field], limits["power_zero_tolerance"])
            for field in zero_power_fields
        ),
    )
    soc = _sample_guard(
        samples,
        lambda row: _finite_vector(row["bess_soc"])
        and np.min(np.asarray(row["bess_soc"], dtype=float)) >= 0.2
        and np.max(np.asarray(row["bess_soc"], dtype=float)) <= 0.8
        and np.max(np.abs(np.asarray(row["bess_soc"], dtype=float) - 0.5))
        <= limits["soc_drift_max"],
    )

    def internal_valid(row: Mapping[str, Any]) -> bool:
        internal = row["bess_internal"]
        if not isinstance(internal, Mapping):
            return False
        if any(name not in internal for name in REQUIRED_ESD1_INTERNAL_FIELDS):
            return False
        if not all(
            _finite_vector(internal[name]) for name in REQUIRED_ESD1_INTERNAL_FIELDS
        ):
            return False
        return all(
            _all_zero(internal[name], limits["power_zero_tolerance"])
            for name in ("Pext0", "Pext", "Pref", "Psum", "Ipul", "Ipcmd_y", "Ipout_y")
        )

    internal_telemetry = _sample_guard(samples, internal_valid)
    line_8 = _sample_guard(samples, lambda row: row["line_8_in_service"] is True)
    g4_retained = _sample_guard(
        samples,
        lambda row: row["g4_in_service"] is True
        and np.isfinite(float(row["g4_m_actual_system"]))
        and float(row["g4_m_actual_system"]) > 0.1,
    )
    graph_identity = report.get("structural") == EXPECTED_STRUCTURAL

    guards = {
        "identity_and_sample_count": identity,
        "pflow_tds_exit": pflow_tds_exit,
        "finite_state_algebraic": finite_state,
        "physical_frequency": physical_frequency,
        "time_increment": time_increment,
        "dae_residual": dae_residual,
        "md_readback": md_readback,
        "no_md_writes": no_md_writes,
        "power_layers": power_layers,
        "soc": soc,
        "esd1_internal_telemetry": internal_telemetry,
        "line_8_in_service": line_8,
        "g4_retained": g4_retained,
        "graph_and_index_identity": graph_identity,
    }
    if tuple(guards) != REQUIRED_STAGE0_GUARDS:
        raise RuntimeError("internal Stage-0 guard ordering drift")
    passed = all(guards.values())
    return {
        "classification": "STAGE0-PASS" if passed else "INVALID-STAGE0",
        "guards": guards,
        "failures": [name for name, value in guards.items() if not value],
        "stage1_authorized": False,
        "training_authorized": False,
        "claim_ceiling": "implementation-validity-only",
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def prepare(seal_path: Path) -> str:
    config = ModelFirstConfig()
    contract = {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "non-learning-stage0",
        "config": _jsonable(config.__dict__),
        "expected_m_system": EXPECTED_M_SYSTEM.tolist(),
        "expected_d_system": EXPECTED_D_SYSTEM.tolist(),
        "limits": STAGE0_LIMITS,
        "required_esd1_internal_fields": list(REQUIRED_ESD1_INTERNAL_FIELDS),
        "required_guards": list(REQUIRED_STAGE0_GUARDS),
        "structural": EXPECTED_STRUCTURAL,
        "inputs": {
            "md_increment": [[0.0, 0.0]] * 4,
            "bess_power_request_system_pu": [0.0] * 4,
            "pq_edit": None,
        },
        "stage1_authorized": False,
        "training_authorized": False,
    }
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "sources": _sources(),
    }
    digest = _write_new_json(seal_path.resolve(), seal)
    print(f"seal_sha256={digest}", flush=True)
    return digest


def _load_seal(path: Path, expected: str) -> tuple[dict[str, Any], str]:
    seal, digest = _read_verified_json(path.resolve(), expected)
    if seal.get("round") != ROUND_ID or seal.get("question") != QUESTION_ID:
        raise RuntimeError("R306 seal identity mismatch")
    if seal.get("contract_payload_sha256") != _payload_sha256(seal["contract"]):
        raise RuntimeError("R306 seal contract payload drift")
    if seal["contract"].get("stage1_authorized") is not False:
        raise RuntimeError("R306 seal unexpectedly authorizes Stage 1")
    if seal["contract"].get("training_authorized") is not False:
        raise RuntimeError("R306 seal unexpectedly authorizes training")
    _verify_sources(seal)
    return seal, digest


def run(seal_path: Path, expected: str, out_dir: Path) -> None:
    _seal, seal_digest = _load_seal(seal_path, expected)
    report_path = out_dir.resolve() / "stage0_report.json"
    manifest_path = out_dir.resolve() / "run_manifest.json"
    if report_path.exists() or manifest_path.exists():
        raise FileExistsError("R306 Stage-0 artifacts already exist")

    from andes_rl_kundur.env.andes.model_first_env import AndesModelFirstEnv

    env = AndesModelFirstEnv()
    try:
        env.reset()
        initial_time = float(env.ss.dae.t)
        zero_md = {
            index: np.zeros(2, dtype=float) for index in range(env.N_AGENTS)
        }
        samples: list[dict[str, Any]] = []
        for _ in range(5):
            _, _, _, info = env.step(
                zero_md,
                bess_power_request_pu=np.zeros(env.N_AGENTS, dtype=float),
            )
            samples.append(_jsonable(info))
        report = {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "initial_time": initial_time,
            "structural": env.structural_contract(),
            "samples": samples,
            "execution_runtime": _runtime_record(),
        }
    finally:
        env.close()

    result = evaluate_stage0_report(report)
    report_digest = _write_new_json(report_path, report)
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "report": {"path": _path_text(report_path), "sha256": report_digest},
        "classification_preview": result["classification"],
        "failures_preview": result["failures"],
        "stage1_authorized": False,
        "training_authorized": False,
        "execution_runtime": _runtime_record(),
    }
    manifest_digest = _write_new_json(manifest_path, manifest)
    print(f"classification={result['classification']}", flush=True)
    print(f"report_sha256={report_digest}", flush=True)
    print(f"run_manifest_sha256={manifest_digest}", flush=True)
    if result["classification"] != "STAGE0-PASS":
        raise RuntimeError(
            f"R306 Stage-0 failed closed: {', '.join(result['failures'])}"
        )


def analyse(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    out_dir = out_dir.resolve()
    report_path = out_dir / "stage0_report.json"
    manifest_path = out_dir / "run_manifest.json"
    report, report_digest = _read_verified_json(report_path)
    manifest, manifest_digest = _read_verified_json(manifest_path)
    if report.get("seal_sha256") != seal_digest:
        raise RuntimeError("R306 report seal mismatch")
    if manifest.get("seal_sha256") != seal_digest:
        raise RuntimeError("R306 manifest seal mismatch")
    if manifest.get("report") != {
        "path": _path_text(report_path),
        "sha256": report_digest,
    }:
        raise RuntimeError("R306 manifest report binding mismatch")

    decision = evaluate_stage0_report(report)
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "report_sha256": report_digest,
        "run_manifest_sha256": manifest_digest,
        **decision,
    }
    analysis_path = out_dir / "analysis.json"
    analysis_digest = _write_new_json(analysis_path, analysis)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal": {"path": _path_text(seal_path), "sha256": seal_digest},
        "report": {"path": _path_text(report_path), "sha256": report_digest},
        "run_manifest": {
            "path": _path_text(manifest_path),
            "sha256": manifest_digest,
        },
        "analysis": {"path": _path_text(analysis_path), "sha256": analysis_digest},
        "sources_verified": seal["sources"],
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "stage1_authorized": False,
        "training_authorized": False,
    }
    provenance_digest = _write_new_json(out_dir / "provenance.json", provenance)
    print(f"classification={analysis['classification']}", flush=True)
    print(f"analysis_sha256={analysis_digest}", flush=True)
    print(f"provenance_sha256={provenance_digest}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    run_parser.add_argument("--expected-seal-sha256", required=True)
    run_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    analyse_parser = commands.add_parser("analyse")
    analyse_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse_parser.add_argument("--expected-seal-sha256", required=True)
    analyse_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        prepare(args.seal)
    elif args.command == "run":
        run(args.seal, args.expected_seal_sha256, args.out_dir)
    else:
        analyse(args.seal, args.expected_seal_sha256, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
