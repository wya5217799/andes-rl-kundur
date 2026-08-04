#!/usr/bin/env python3
"""Replay the sealed R317 scalar grid and diagnose its rejection cause.

Usage:
    python scripts/run_r318_rejection_diagnosis.py prepare
    python scripts/run_r318_rejection_diagnosis.py diagnose --expected-sha256 <seal>
    python scripts/run_r318_rejection_diagnosis.py analyse --expected-sha256 <seal>

The adapter exposes no physical, EVAL, performance-selection, or optimization
command.  It never widens the R317 grid and never loads the conditional bipolar
or mismatch examination.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for path in (ROOT, SRC, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_r317_offline_controller as R317  # noqa: E402

from andes_rl_kundur.control.model_first_offline_feedback import (  # noqa: E402
    FeedbackLimits,
    augmented_closed_loop_radius,
    simulate_delayed_output_feedback,
    synthesize_dc_inverse_gains,
)
from probes.r318_rejection_diagnosis import (  # noqa: E402
    classify_rejection_diagnosis,
)

ROUND_ID = "R318"
QUESTION_ID = "Q-0073"
DEFAULT_SEAL = ROOT / "memory/rounds/R318/rejection_diagnosis_seal.json"
DEFAULT_OUT = ROOT / "results/r318_rejection_diagnosis"
R317_SEAL = ROOT / "memory/rounds/R317/offline_controller_seal.json"
R317_RESULT = ROOT / "results/r317_offline_controller/controller_result.json"
R317_ANALYSIS = ROOT / "results/r317_offline_controller/analysis.json"
R317_PROVENANCE = ROOT / "results/r317_offline_controller/provenance.json"


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _payload_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_text(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_new_json(path: Path, payload: object) -> str:
    if path.exists() or path.with_suffix(path.suffix + ".sha256").exists():
        raise FileExistsError(f"create-only artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    path.write_text(text, encoding="utf-8")
    digest = _sha256_file(path)
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="ascii"
    )
    return digest


def _read_verified_json(
    path: Path,
    expected_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    if not path.is_file():
        raise FileNotFoundError(path)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not sidecar.is_file():
        raise FileNotFoundError(sidecar)
    digest = _sha256_file(path)
    sidecar_digest = sidecar.read_text(encoding="ascii").split()[0]
    if digest != sidecar_digest or (
        expected_sha256 is not None and digest != expected_sha256
    ):
        raise RuntimeError(f"hash mismatch for {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON artifact is not an object: {path}")
    return payload, digest


def build_contract() -> dict[str, Any]:
    parent = R317.build_contract()
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "parent_round": "R317",
        "parent_claim": "CLM-0795",
        "scalar_candidates": list(parent["scalar_candidates"]),
        "maximum_pole_radius": parent["maximum_pole_radius"],
        "development_case_count": parent["development_case_count"],
        "limits": dict(parent["limits"]),
        "sample_period_seconds": parent["sample_period_seconds"],
        "horizon_steps": parent["horizon_steps"],
        "first_command": parent["first_command"],
        "diagnostics": [
            "per-point-and-maximum-augmented-pole-radius",
            "pole-pass",
            "governor-evaluated",
            "finite-development-output",
            "node-power-ramp-soc-extrema",
            "constraint-violation-types",
            "fully-feasible",
        ],
        "repair_mapping": {
            "POLE-ONLY-REJECTION": "augmented-observer-quadratic-regulator",
            "GOVERNOR-ONLY-REJECTION": "constrained-receding-horizon",
            "MIXED-REJECTION": "augmented-observer-quadratic-regulator",
            "DIAGNOSTIC-CONFLICT": "repair-r317-selection-implementation",
        },
        "performance_selection_authorized": False,
        "r317_examination_accessed": False,
        "eval": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R318/plan.md",
        "question": ROOT / "memory/questions/Q-0073.md",
        "parent_claim": ROOT / "memory/claims/CLM-0795.md",
        "parent_R317_adapter": ROOT / "scripts/run_r317_offline_controller.py",
        "controller_module": SRC
        / "andes_rl_kundur/control/model_first_offline_feedback.py",
        "diagnostic_probe": ROOT / "probes/r318_rejection_diagnosis.py",
        "adapter": Path(__file__).resolve(),
        "diagnostic_tests": ROOT / "tests/test_r318_rejection_diagnosis.py",
        "adapter_tests": ROOT
        / "tests/test_r318_rejection_diagnosis_adapter.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _load_r317_authority() -> dict[str, object]:
    seal, seal_digest = _read_verified_json(R317_SEAL)
    result, result_digest = _read_verified_json(R317_RESULT)
    analysis, analysis_digest = _read_verified_json(R317_ANALYSIS)
    provenance, provenance_digest = _read_verified_json(R317_PROVENANCE)
    if (
        seal.get("round") != "R317"
        or seal.get("question") != "Q-0072"
        or result.get("seal_sha256") != seal_digest
        or analysis.get("controller_result_sha256") != result_digest
        or analysis.get("classification") != "OFFLINE-CONTROLLER-NO-GO"
        or not all(analysis.get("validity_guards", {}).values())
        or analysis.get("arms", {}).get("retained_cross", {}).get(
            "selection_feasible"
        )
        is not False
        or analysis.get("arms", {}).get("cross_deleted", {}).get(
            "selection_feasible"
        )
        is not False
        or provenance.get("analysis", {}).get("sha256") != analysis_digest
        or provenance.get("controller_result", {}).get("sha256") != result_digest
        or provenance.get("eval_status") != "NOT-APPLICABLE-MODEL-ONLY"
    ):
        raise RuntimeError("R317 authority chain mismatch")
    return {
        "seal": {"path": _path_text(R317_SEAL), "sha256": seal_digest},
        "controller_result": {
            "path": _path_text(R317_RESULT),
            "sha256": result_digest,
        },
        "analysis": {"path": _path_text(R317_ANALYSIS), "sha256": analysis_digest},
        "provenance": {
            "path": _path_text(R317_PROVENANCE),
            "sha256": provenance_digest,
        },
    }


def prepare(seal_path: Path) -> str:
    authority = _load_r317_authority()
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "parent": authority,
        "sources": _sources(),
    }
    digest = _write_new_json(seal_path, seal)
    print(f"seal_sha256={digest}", flush=True)
    return digest


def _load_seal(path: Path, expected: str) -> tuple[dict[str, Any], str]:
    seal, digest = _read_verified_json(path, expected)
    contract = build_contract()
    if (
        seal.get("round") != ROUND_ID
        or seal.get("question") != QUESTION_ID
        or seal.get("contract") != contract
        or seal.get("contract_payload_sha256") != _payload_sha256(contract)
        or seal.get("parent") != _load_r317_authority()
    ):
        raise RuntimeError("R318 seal contract or parent drift")
    for name, entry in seal["sources"].items():
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"R318 sealed source drift for {name}")
    return seal, digest


def _gain_identity(
    reconstructed: dict[str, np.ndarray | float],
    parent_result: dict[str, Any],
) -> bool:
    parent = parent_result.get("gain_family", {})
    return bool(
        np.isclose(
            float(reconstructed["condition_number"]),
            float(parent.get("condition_number", float("nan"))),
            rtol=1e-13,
            atol=1e-15,
        )
        and all(
            np.allclose(
                np.asarray(reconstructed[name], dtype=float),
                np.asarray(parent.get(name), dtype=float),
                rtol=1e-13,
                atol=1e-15,
            )
            for name in (
                "averaged_dc_gain",
                "retained_cross_base",
                "cross_deleted_base",
            )
        )
    )


def _diagnose_arm(
    realizations,
    *,
    base_gain: np.ndarray,
    limits: FeedbackLimits,
    scalar_candidates: list[float],
    maximum_pole_radius: float,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    violation_types: set[str] = set()
    maximum_interventions = 0
    for scalar in scalar_candidates:
        gain = scalar * base_gain
        point_radii = {
            name: augmented_closed_loop_radius(realization, gain)
            for name, realization in realizations.items()
        }
        maximum_radius = max(point_radii.values())
        pole_pass = bool(maximum_radius <= maximum_pole_radius)
        row: dict[str, object] = {
            "scalar": scalar,
            "point_pole_radii": point_radii,
            "maximum_pole_radius": maximum_radius,
            "pole_pass": pole_pass,
            "governor_evaluated": False,
            "governor_pass": False,
            "fully_feasible": False,
            "development_case_count": 0,
            "finite": None,
            "constraint_violation_count": None,
            "governor_intervention_count": None,
            "maximum_node_power": None,
            "maximum_node_ramp": None,
            "minimum_soc": None,
            "maximum_soc": None,
            "constraint_violation_types": [],
        }
        if pole_pass:
            row["governor_evaluated"] = True
            traces = [
                simulate_delayed_output_feedback(
                    realizations[case.point],
                    case.disturbance,
                    gain=gain,
                    initial_soc=case.initial_soc,
                    limits=limits,
                )
                for case in R317.development_cases()
            ]
            finite = all(
                np.all(np.isfinite(trace.outputs))
                and np.all(np.isfinite(trace.node_actions))
                and np.all(np.isfinite(trace.soc))
                for trace in traces
            )
            violations = sum(trace.constraint_violation_count for trace in traces)
            interventions = sum(
                trace.governor_intervention_count for trace in traces
            )
            node_deltas = [
                np.vstack((trace.node_actions[:1], np.diff(trace.node_actions, axis=0)))
                for trace in traces
            ]
            max_power = max(float(np.max(np.abs(trace.node_actions))) for trace in traces)
            max_ramp = max(float(np.max(np.abs(delta))) for delta in node_deltas)
            min_soc = min(float(np.min(trace.soc)) for trace in traces)
            max_soc = max(float(np.max(trace.soc)) for trace in traces)
            types: list[str] = []
            if not finite:
                types.append("non-finite")
            if max_power > limits.node_power + 1e-12:
                types.append("node-power")
            if max_ramp > limits.node_ramp + 1e-12:
                types.append("node-ramp")
            if min_soc < limits.minimum_soc - 1e-12 or max_soc > limits.maximum_soc + 1e-12:
                types.append("soc")
            if violations and not types:
                types.append("reported-constraint-violation")
            governor_pass = finite and violations == 0 and not types
            row.update(
                {
                    "governor_pass": governor_pass,
                    "fully_feasible": governor_pass,
                    "development_case_count": len(traces),
                    "finite": finite,
                    "constraint_violation_count": violations,
                    "governor_intervention_count": interventions,
                    "maximum_node_power": max_power,
                    "maximum_node_ramp": max_ramp,
                    "minimum_soc": min_soc,
                    "maximum_soc": max_soc,
                    "constraint_violation_types": types,
                }
            )
            maximum_interventions = max(maximum_interventions, interventions)
            violation_types.update(types)
        rows.append(row)
    minimum_row = min(rows, key=lambda item: item["maximum_pole_radius"])
    return (
        {
            "candidate_count": len(rows),
            "pole_feasible_count": sum(bool(row["pole_pass"]) for row in rows),
            "governor_evaluated_count": sum(
                bool(row["governor_evaluated"]) for row in rows
            ),
            "fully_feasible_count": sum(
                bool(row["fully_feasible"]) for row in rows
            ),
            "minimum_pole_radius": minimum_row["maximum_pole_radius"],
            "minimum_pole_scalar": minimum_row["scalar"],
            "maximum_governor_intervention_count": maximum_interventions,
            "constraint_violation_types": sorted(violation_types),
        },
        rows,
    )


def _calculate() -> dict[str, Any]:
    parent_result, parent_result_digest = _read_verified_json(R317_RESULT)
    model, model_digest, _parent_analysis, _parent_analysis_digest = R317._load_parent()
    realizations = R317._realizations(model)
    contract = build_contract()
    limits = FeedbackLimits(**contract["limits"])
    family = synthesize_dc_inverse_gains(
        list(realizations.values()),
        maximum_condition_number=R317.build_contract()[
            "maximum_dc_gain_condition_number"
        ],
    )
    reconstructed = {
        "averaged_dc_gain": family.averaged_dc_gain,
        "condition_number": family.condition_number,
        "retained_cross_base": family.retained_cross_base,
        "cross_deleted_base": family.cross_deleted_base,
    }
    arms: dict[str, object] = {}
    candidates: dict[str, object] = {}
    for name, base_gain in (
        ("retained_cross", family.retained_cross_base),
        ("cross_deleted", family.cross_deleted_base),
    ):
        summary, rows = _diagnose_arm(
            realizations,
            base_gain=base_gain,
            limits=limits,
            scalar_candidates=contract["scalar_candidates"],
            maximum_pole_radius=contract["maximum_pole_radius"],
        )
        arms[name] = summary
        candidates[name] = rows
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "parent_controller_result_sha256": parent_result_digest,
        "parent_dynamic_model_sha256": model_digest,
        "gain_reconstruction_identity": _gain_identity(
            reconstructed, parent_result
        ),
        "arms": arms,
        "candidates": candidates,
        "r317_examination_accessed": False,
        "performance_selection_performed": False,
        "physical_execution_performed": False,
        "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def diagnose(seal_path: Path, expected: str, out_dir: Path) -> str:
    seal, seal_digest = _load_seal(seal_path, expected)
    first = _calculate()
    second = _calculate()
    deterministic = _payload_sha256(first) == _payload_sha256(second)
    candidate_contract = bool(
        all(
            arm["candidate_count"]
            == len(seal["contract"]["scalar_candidates"])
            for arm in first["arms"].values()
        )
    )
    first.update(
        {
            "schema_version": 1,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "contract_payload_sha256": seal["contract_payload_sha256"],
            "validity_guards": {
                "sealed_parent_identity": True,
                "gain_reconstruction_identity": first[
                    "gain_reconstruction_identity"
                ],
                "candidate_contract": candidate_contract,
                "deterministic_replay": deterministic,
                "no_examination_or_eval": bool(
                    first["r317_examination_accessed"] is False
                    and first["performance_selection_performed"] is False
                    and first["eval_status"] == "NOT-APPLICABLE-MODEL-ONLY"
                ),
            },
        }
    )
    digest = _write_new_json(out_dir / "diagnostic.json", first)
    print(f"diagnostic_sha256={digest}", flush=True)
    return digest


def analyse(seal_path: Path, expected: str, out_dir: Path) -> str:
    seal, seal_digest = _load_seal(seal_path, expected)
    diagnostic, diagnostic_digest = _read_verified_json(out_dir / "diagnostic.json")
    if (
        diagnostic.get("seal_sha256") != seal_digest
        or diagnostic.get("contract_payload_sha256")
        != seal["contract_payload_sha256"]
    ):
        raise RuntimeError("R318 diagnostic provenance mismatch")
    analysis = classify_rejection_diagnosis(diagnostic)
    analysis.update(
        {
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "diagnostic_sha256": diagnostic_digest,
            "contract_payload_sha256": seal["contract_payload_sha256"],
        }
    )
    analysis_digest = _write_new_json(out_dir / "analysis.json", analysis)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal": {"path": _path_text(seal_path), "sha256": seal_digest},
        "diagnostic": {
            "path": _path_text(out_dir / "diagnostic.json"),
            "sha256": diagnostic_digest,
        },
        "analysis": {
            "path": _path_text(out_dir / "analysis.json"),
            "sha256": analysis_digest,
        },
        "parent": seal["parent"],
        "physical_execution_performed": False,
        "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
    provenance_digest = _write_new_json(out_dir / "provenance.json", provenance)
    print(f"classification={analysis['classification']}", flush=True)
    print(f"analysis_sha256={analysis_digest}", flush=True)
    print(f"provenance_sha256={provenance_digest}", flush=True)
    return analysis_digest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "diagnose", "analyse"))
    parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--expected-sha256")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare":
        if args.expected_sha256 is not None:
            raise SystemExit("prepare does not accept --expected-sha256")
        prepare(args.seal)
        return 0
    if not args.expected_sha256:
        raise SystemExit(f"{args.command} requires --expected-sha256")
    if args.command == "diagnose":
        diagnose(args.seal, args.expected_sha256, args.out)
    else:
        analyse(args.seal, args.expected_sha256, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
