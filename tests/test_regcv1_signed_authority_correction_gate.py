from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

from andes_rl_kundur.evaluation.regcv1_signed_authority_correction_gate import (
    build_signed_authority_correction_contract,
    classify_regcv1_signed_authority_correction_record,
)
from andes_rl_kundur.evaluation.regcv1_signed_authority_gate import (
    build_signed_authority_contract,
)

ROOT = Path(__file__).resolve().parents[1]
R387_TEST = ROOT / "tests/test_regcv1_signed_authority_gate.py"


def _load_r387_fixtures():
    spec = importlib.util.spec_from_file_location("r387_test_fixtures", R387_TEST)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _sha(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def passing_record() -> tuple[dict[str, object], dict[str, object]]:
    fixtures = _load_r387_fixtures()
    _, record = fixtures.passing_record()
    contract = build_signed_authority_correction_contract()
    record["schema_version"] = 2
    record["round"] = "R388"
    record["contract_sha256"] = _sha(contract)
    for arm in record["arms"]:
        trajectory = arm["trajectory"]
        if trajectory["captured"] is not True:
            continue
        trajectory["start_time_seconds"] = 0.0
        trajectory["initial"] = {
            "captured": True,
            "time_seconds": 0.0,
            "dae_finite": True,
            "regcv1_finite": True,
            "bus_v": {key: values[0] for key, values in trajectory["bus_v"].items()},
            "regcv1": {
                signal: {idx: values[0] for idx, values in rows.items()}
                for signal, rows in trajectory["regcv1"].items()
            },
        }
        trajectory["time"] = [1.0 / 30.0, 1.0, 2.0]
    return contract, record


def _truncate_arm(arm: dict[str, object], terminal: float = 1.0) -> None:
    trajectory = arm["trajectory"]
    trajectory["time"] = [1.0 / 30.0, 0.5, terminal]
    for values in trajectory["bus_v"].values():
        del values[3:]
    for rows in trajectory["regcv1"].values():
        for values in rows.values():
            del values[3:]
    arm["solver"]["terminal_time_seconds"] = terminal
    arm["solver"]["tds_converged"] = False


def test_contract_changes_only_lifecycle_and_evidence_schema() -> None:
    parent = build_signed_authority_contract()
    expected = copy.deepcopy(parent)
    expected.update(
        {
            "schema_version": 2,
            "round": "R388",
            "parent_round": "R387",
            "correction_of_contract_sha256": _sha(parent),
            "trajectory_evidence": {
                "start_time_seconds": 0.0,
                "max_first_sample_time_seconds": 1.0 / 30.0 + 1.0e-4,
                "bus_identity_order_independent": True,
                "initial_snapshot_required": True,
                "advanced_partial_error": "TDS terminated before horizon",
            },
        }
    )

    assert build_signed_authority_correction_contract() == expected


def test_canonical_json_round_trip_preserves_bus_identity_and_passes() -> None:
    contract, record = passing_record()
    round_tripped = json.loads(json.dumps(record, sort_keys=True))

    analysis = classify_regcv1_signed_authority_correction_record(
        round_tripped,
        contract=contract,
    )

    assert analysis["classification"] == "REGCV1-SIGNED-AUTHORITY-PASS"
    assert all(analysis["checks"].values())


def test_native_post_start_grid_is_bound_to_separate_initial_snapshot() -> None:
    contract, record = passing_record()

    analysis = classify_regcv1_signed_authority_correction_record(record, contract=contract)

    assert analysis["classification"] == "REGCV1-SIGNED-AUTHORITY-PASS"
    assert record["arms"][0]["trajectory"]["time"][0] == 1.0 / 30.0
    assert record["arms"][0]["trajectory"]["initial"]["time_seconds"] == 0.0


def test_advanced_partial_nonconverged_trace_is_scientific_stop() -> None:
    contract, record = passing_record()
    arm = record["arms"][4]
    _truncate_arm(arm)
    arm["scientific_error"] = "TDS terminated before horizon"

    analysis = classify_regcv1_signed_authority_correction_record(record, contract=contract)

    assert analysis["classification"] == "STOP-REGCV1-SIGNED-AUTHORITY"
    assert analysis["checks"]["record_integrity"] is True
    assert analysis["checks"]["native_solver"] is False
    assert analysis["responses"] == []


def test_short_trace_without_typed_partial_error_is_analysis_invalid() -> None:
    contract, record = passing_record()
    _truncate_arm(record["arms"][4])

    analysis = classify_regcv1_signed_authority_correction_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_missing_initial_snapshot_is_analysis_invalid() -> None:
    contract, record = passing_record()
    record["arms"][1]["trajectory"]["initial"]["captured"] = False

    analysis = classify_regcv1_signed_authority_correction_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_substituted_initial_bus_identity_is_analysis_invalid() -> None:
    contract, record = passing_record()
    bus_v = record["arms"][1]["trajectory"]["initial"]["bus_v"]
    bus_v["bogus"] = bus_v.pop("1")

    analysis = classify_regcv1_signed_authority_correction_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_native_first_sample_too_late_is_analysis_invalid() -> None:
    contract, record = passing_record()
    record["arms"][1]["trajectory"]["time"][0] = 0.5

    analysis = classify_regcv1_signed_authority_correction_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_mutated_correction_contract_is_analysis_invalid() -> None:
    contract, record = passing_record()
    contract["trajectory_evidence"]["max_first_sample_time_seconds"] = 0.5
    record["contract_sha256"] = _sha(contract)

    analysis = classify_regcv1_signed_authority_correction_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"
