from __future__ import annotations

import copy
import hashlib
import json
from types import SimpleNamespace

import pytest

from andes_rl_kundur.evaluation.regcv1_signed_authority_gate import (
    apply_regcv1_setpoint_step,
    build_signed_authority_contract,
    classify_regcv1_signed_authority_record,
)


def _sha(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _setpoint_rows() -> list[dict[str, object]]:
    rows = []
    for number in range(1, 5):
        idx = f"REGCV1_{number}"
        rows.extend(
            (
                {"idx": idx, "channel": "pref", "value": 0.70 + number / 100},
                {"idx": idx, "channel": "qref", "value": 0.10 + number / 100},
            )
        )
    return rows


def _inventory(contract: dict[str, object]) -> dict[str, object]:
    return {
        "network": copy.deepcopy(contract["network_inventory"]),
        "forbidden_model_counts": {name: 0 for name in contract["forbidden_models"]},
        "forbidden_dae_names": [],
        "regcv1": [{**row, "Sn": 900.0, "u": 1} for row in contract["expected_mapping"]],
    }


def _reference_rows() -> list[dict[str, object]]:
    return [
        {
            "idx": f"REGCV1_{number}",
            "static_p": 0.70 + number / 100,
            "static_q": 0.10 + number / 100,
        }
        for number in range(1, 5)
    ]


def _arm_record(
    spec: dict[str, object],
    arm: dict[str, object],
) -> dict[str, object]:
    idxes = [f"REGCV1_{number}" for number in range(1, 5)]
    pre = _setpoint_rows()
    post = copy.deepcopy(pre)
    target = arm["target_idx"]
    channel = arm["input_channel"]
    requested_absolute = None
    applied_readback = None
    if target is not None:
        for row in post:
            if row["idx"] == target and row["channel"] == channel:
                row["value"] = float(row["value"]) + float(arm["requested_delta"])
                requested_absolute = row["value"]
                applied_readback = row["value"]

    pe = {idx: [0.70 + number / 100] * 3 for number, idx in enumerate(idxes, start=1)}
    qe = {idx: [0.10 + number / 100] * 3 for number, idx in enumerate(idxes, start=1)}
    if target is not None:
        sign = int(arm["sign"])
        same = pe if channel == "pref" else qe
        cross = qe if channel == "pref" else pe
        for idx in idxes:
            response = sign * (0.001 if idx == target else 0.0001)
            same[idx] = [same[idx][0], same[idx][0] + response / 2, same[idx][0] + response]
        cross[target] = [
            cross[target][0],
            cross[target][0] + sign * 0.000025,
            cross[target][0] + sign * 0.00005,
        ]

    source_rows = _reference_rows()
    return {
        **copy.deepcopy(arm),
        "scientific_error": None,
        "inventory": _inventory(spec),
        "reference_source": {
            "captured": True,
            "phase": "post_pflow_pre_tds_init",
            "pflow_converged_at_capture": True,
            "tds_initialized_at_capture": False,
            "rows": source_rows,
        },
        "references": {
            "checked": True,
            "absolute_tolerance": 1.0e-12,
            "rows": [
                {
                    **row,
                    "pref": row["static_p"],
                    "qref": row["static_q"],
                    "pref_match": True,
                    "qref_match": True,
                }
                for row in source_rows
            ],
        },
        "initialization_diagnostics": {
            "captured": True,
            "equation_count": 112,
            "residual_count": 0,
            "bad_combined_indices": [],
            "residuals": [],
            "clamped_limits": [],
        },
        "solver": {
            "setup_completed": True,
            "pflow_converged": True,
            "tds_initialized": True,
            "tds_test_ok": True,
            "tds_converged": True,
            "tds_tolerance": 1.0e-4,
            "terminal_time_seconds": 2.0,
        },
        "action": {
            "applied": target is not None,
            "pre_setpoints": pre,
            "post_setpoints": post,
            "requested_absolute": requested_absolute,
            "applied_readback": applied_readback,
        },
        "trajectory": {
            "captured": True,
            "time": [0.0, 1.0, 2.0],
            "dae_finite": True,
            "regcv1_finite": True,
            "bus_v": {str(number): [1.0, 1.0, 1.0] for number in range(1, 11)},
            "regcv1": {
                "Pe": pe,
                "Qe": qe,
                "Id": copy.deepcopy(pe),
                "Iq": {idx: [0.0, 0.0, 0.0] for idx in idxes},
                "omega": {idx: [1.0, 1.0, 1.0] for idx in idxes},
            },
        },
    }


def passing_record() -> tuple[dict[str, object], dict[str, object]]:
    contract = build_signed_authority_contract()
    record = {
        "schema_version": 1,
        "round": "R387",
        "question": "Q-0106",
        "contract_sha256": _sha(contract),
        "formal_input_complete": True,
        "execution_error": None,
        "training_executed": False,
        "trajectory_attempted_count": 17,
        "trajectory_executed_count": 17,
        "source": {
            "andes_version": "2.0.0",
            "xlsx_json_static_equal": True,
            "derived_case_deterministic": True,
            "xlsx_case_sha256": "b" * 64,
            "json_case_sha256": "c" * 64,
            "derived_case_sha256": "d" * 64,
            "regcv1_source_sha256": "e" * 64,
        },
        "arms": [_arm_record(contract, arm) for arm in contract["arm_order"]],
    }
    return contract, record


def test_contract_freezes_exact_seventeen_arm_bank() -> None:
    contract = build_signed_authority_contract()

    assert contract["step_abs_system_pu"] == pytest.approx(0.09)
    assert contract["tds_tf_seconds"] == pytest.approx(2.0)
    assert contract["authority_abs_floor_system_pu"] == pytest.approx(2.0e-4)
    assert len(contract["arm_order"]) == 17
    assert contract["arm_order"][0] == {
        "arm_id": "zero",
        "target_idx": None,
        "input_channel": None,
        "sign": 0,
        "requested_delta": 0.0,
    }
    assert contract["arm_order"][-1]["arm_id"] == "regcv1_4_qref_positive"


class _FakeRenGen:
    def __init__(self) -> None:
        self.values = {
            "pref": {f"REGCV1_{number}": 0.70 + number / 100 for number in range(1, 5)},
            "qref": {f"REGCV1_{number}": 0.10 + number / 100 for number in range(1, 5)},
        }

    def get_pref(self, _system, idx):
        return self.values["pref"][idx]

    def set_pref(self, _system, idx, value):
        self.values["pref"][idx] = value

    def get_qref(self, _system, idx):
        return self.values["qref"][idx]

    def set_qref(self, _system, idx, value):
        self.values["qref"][idx] = value


def test_apply_step_changes_only_the_requested_device_channel() -> None:
    contract = build_signed_authority_contract()
    system = SimpleNamespace(RenGen=_FakeRenGen())
    arm = contract["arm_order"][1]

    receipt = apply_regcv1_setpoint_step(system, arm)

    changed = [
        (before, after)
        for before, after in zip(receipt["pre_setpoints"], receipt["post_setpoints"], strict=True)
        if before["value"] != after["value"]
    ]
    assert len(changed) == 1
    assert changed[0][1]["idx"] == arm["target_idx"]
    assert changed[0][1]["channel"] == arm["input_channel"]
    assert receipt["applied_readback"] == pytest.approx(receipt["requested_absolute"])


def test_complete_signed_and_attributed_bank_passes() -> None:
    contract, record = passing_record()

    analysis = classify_regcv1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "REGCV1-SIGNED-AUTHORITY-PASS"
    assert all(analysis["checks"].values())
    assert len(analysis["responses"]) == 16
    assert len(analysis["paired_separations"]) == 8


def test_wrong_signed_target_response_is_a_scientific_stop() -> None:
    contract, record = passing_record()
    arm = record["arms"][1]
    target = arm["target_idx"]
    baseline = record["arms"][0]["trajectory"]["regcv1"]["Pe"][target][-1]
    arm["trajectory"]["regcv1"]["Pe"][target][-1] = baseline + 0.001

    analysis = classify_regcv1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "STOP-REGCV1-SIGNED-AUTHORITY"
    assert analysis["checks"]["signed_self_response"] is False


def test_non_target_dominance_is_a_scientific_stop() -> None:
    contract, record = passing_record()
    arm = record["arms"][1]
    target = arm["target_idx"]
    other = "REGCV1_2"
    baseline = record["arms"][0]["trajectory"]["regcv1"]["Pe"]
    arm["trajectory"]["regcv1"]["Pe"][target][-1] = baseline[target][-1] - 0.001
    arm["trajectory"]["regcv1"]["Pe"][other][-1] = baseline[other][-1] - 0.0009

    analysis = classify_regcv1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "STOP-REGCV1-SIGNED-AUTHORITY"
    assert analysis["checks"]["target_attribution"] is False


def test_voltage_guard_failure_is_a_scientific_stop() -> None:
    contract, record = passing_record()
    record["arms"][3]["trajectory"]["bus_v"]["5"][1] = 0.89

    analysis = classify_regcv1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "STOP-REGCV1-SIGNED-AUTHORITY"
    assert analysis["checks"]["electrical_envelope"] is False


def test_duplicate_or_missing_arm_is_analysis_invalid() -> None:
    contract, record = passing_record()
    record["arms"][1]["arm_id"] = "zero"

    analysis = classify_regcv1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"
    assert analysis["checks"] == {"record_integrity": False}


def test_source_hash_drift_is_analysis_invalid() -> None:
    contract, record = passing_record()
    record["source"]["regcv1_source_sha256"] = "not-a-digest"

    analysis = classify_regcv1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_native_nonconvergence_is_a_scientific_stop_not_invalid() -> None:
    contract, record = passing_record()
    record["arms"][4]["solver"]["tds_converged"] = False

    analysis = classify_regcv1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "STOP-REGCV1-SIGNED-AUTHORITY"
    assert analysis["checks"]["native_solver"] is False


def test_expected_pflow_failure_is_a_scientific_stop() -> None:
    contract, record = passing_record()
    arm = record["arms"][5]
    arm["scientific_error"] = "PFlow.run returned a non-success value"
    arm["reference_source"] = {
        "captured": False,
        "phase": None,
        "pflow_converged_at_capture": False,
        "tds_initialized_at_capture": False,
        "rows": [],
    }
    arm["references"] = {
        "checked": False,
        "absolute_tolerance": None,
        "rows": [],
    }
    arm["action"] = {
        "applied": False,
        "pre_setpoints": [],
        "post_setpoints": [],
        "requested_absolute": None,
        "applied_readback": None,
    }
    arm["trajectory"] = {
        "captured": False,
        "time": [],
        "dae_finite": False,
        "regcv1_finite": False,
        "bus_v": {},
        "regcv1": {},
    }
    arm["solver"].update(
        {
            "pflow_converged": False,
            "tds_initialized": False,
            "tds_test_ok": False,
            "tds_converged": False,
            "terminal_time_seconds": None,
        }
    )
    record["trajectory_executed_count"] = 16

    analysis = classify_regcv1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "STOP-REGCV1-SIGNED-AUTHORITY"
    assert analysis["checks"]["record_integrity"] is True


def test_malformed_residual_row_is_analysis_invalid() -> None:
    contract, record = passing_record()
    diagnostics = record["arms"][2]["initialization_diagnostics"]
    diagnostics["residual_count"] = 1
    diagnostics["bad_combined_indices"] = [999]
    diagnostics["residuals"] = [{}]

    analysis = classify_regcv1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_action_baseline_not_bound_to_reference_is_analysis_invalid() -> None:
    contract, record = passing_record()
    arm = record["arms"][1]
    arm["action"]["pre_setpoints"][0]["value"] = 100.0
    arm["action"]["post_setpoints"][0]["value"] = 100.0

    analysis = classify_regcv1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_truncated_trace_ending_at_terminal_time_is_analysis_invalid() -> None:
    contract, record = passing_record()
    record["arms"][1]["trajectory"]["time"] = [1.9, 1.95, 2.0]

    analysis = classify_regcv1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_expected_tds_initialization_failure_is_a_scientific_stop() -> None:
    contract, record = passing_record()
    arm = record["arms"][6]
    arm["scientific_error"] = "native TDS initialization guard failed"
    arm["action"] = {
        "applied": False,
        "pre_setpoints": [],
        "post_setpoints": [],
        "requested_absolute": None,
        "applied_readback": None,
    }
    arm["trajectory"] = {
        "captured": False,
        "time": [],
        "dae_finite": False,
        "regcv1_finite": False,
        "bus_v": {},
        "regcv1": {},
    }
    arm["solver"].update(
        {
            "tds_initialized": False,
            "tds_test_ok": False,
            "tds_converged": False,
            "terminal_time_seconds": None,
        }
    )
    record["trajectory_executed_count"] = 16

    analysis = classify_regcv1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "STOP-REGCV1-SIGNED-AUTHORITY"
    assert analysis["checks"]["record_integrity"] is True


def test_expected_no_time_advance_is_a_scientific_stop() -> None:
    contract, record = passing_record()
    arm = record["arms"][7]
    arm["scientific_error"] = "TDS did not advance"
    arm["trajectory"] = {
        "captured": False,
        "time": [],
        "dae_finite": False,
        "regcv1_finite": False,
        "bus_v": {},
        "regcv1": {},
    }
    arm["solver"].update(
        {
            "tds_converged": False,
            "terminal_time_seconds": 0.0,
        }
    )
    record["trajectory_executed_count"] = 16

    analysis = classify_regcv1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "STOP-REGCV1-SIGNED-AUTHORITY"
    assert analysis["checks"]["record_integrity"] is True


def test_malformed_reference_boolean_is_analysis_invalid() -> None:
    contract, record = passing_record()
    record["arms"][1]["references"]["rows"][0]["pref_match"] = "yes"

    analysis = classify_regcv1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_post_hoc_threshold_contract_is_analysis_invalid() -> None:
    contract, record = passing_record()
    contract["authority_abs_floor_system_pu"] = 0.0
    contract["paired_separation_floor_system_pu"] = 0.0
    record["contract_sha256"] = _sha(contract)

    analysis = classify_regcv1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_substituted_bus_trace_key_is_analysis_invalid() -> None:
    contract, record = passing_record()
    bus_v = record["arms"][1]["trajectory"]["bus_v"]
    bus_v["bogus"] = bus_v.pop("1")

    analysis = classify_regcv1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"
