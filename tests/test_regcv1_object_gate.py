from __future__ import annotations

import copy
import math

import pytest

from andes_rl_kundur.evaluation.regcv1_object_gate import (
    build_contract,
    classify_regcv1_object_record,
)


def _complete_record() -> dict[str, object]:
    contract = build_contract()
    mappings = [
        {
            "idx": f"REGCV1_{index}",
            "bus": index,
            "gen": index,
            "Sn": 900.0,
            "u": 1,
        }
        for index in range(1, 5)
    ]
    disabled = [
        {"model": model, "idx": index, "syn": index, "u": 0}
        for model in ("GENROU", "TGOV1", "EXDC2")
        for index in range(1, 5)
    ]
    interface: dict[str, object] = {"attempted": True, "completed": True}
    for channel, baseline in (("pref", 0.7), ("qref", 0.08)):
        rows = []
        for index in range(1, 5):
            probe = math.nextafter(baseline, math.inf)
            rows.append(
                {
                    "idx": f"REGCV1_{index}",
                    "baseline": baseline,
                    "probe": probe,
                    "readback": probe,
                    "restored": baseline,
                    "non_target_unchanged": True,
                }
            )
        interface[channel] = rows
    return {
        "schema_version": 1,
        "round": "R384",
        "question": "Q-0104",
        "contract_sha256": "a" * 64,
        "formal_input_complete": True,
        "physical_trajectory_executed": True,
        "trajectory_count": 1,
        "execution_error": None,
        "inventory": {
            "regcv1": mappings,
            "disabled_dynamic_chain": disabled,
            "network": contract["network_inventory"],
        },
        "interface_identity": interface,
        "solver": {
            "setup_completed": True,
            "pflow_converged": True,
            "tds_initialized": True,
            "tds_test_ok": True,
            "tds_converged": True,
            "terminal_time_seconds": 0.2,
            "tds_tolerance": 1.0e-4,
        },
        "finite_guard": {
            "checked": True,
            "dae_finite": True,
            "regcv1_finite": True,
        },
        "drift": {
            "checked": True,
            "max_abs_by_signal": {
                "Pe": 1.0e-6,
                "Qe": 2.0e-6,
                "dw": 1.0e-7,
                "omega": 1.0e-7,
                "v": 3.0e-6,
            },
        },
        "training_executed": False,
    }


def test_contract_freezes_four_device_unchanged_kundur_gate() -> None:
    contract = build_contract()

    assert contract["expected_mapping"] == [
        {"idx": "REGCV1_1", "bus": 1, "gen": 1},
        {"idx": "REGCV1_2", "bus": 2, "gen": 2},
        {"idx": "REGCV1_3", "bus": 3, "gen": 3},
        {"idx": "REGCV1_4", "bus": 4, "gen": 4},
    ]
    assert contract["parameter_card"]["kv"] == 0.01
    assert contract["tds_tf_seconds"] == 0.2
    assert contract["training_authorized"] is False


def test_complete_object_initialization_record_passes() -> None:
    analysis = classify_regcv1_object_record(_complete_record())

    assert analysis["classification"] == "REGCV1-OBJECT-INIT-PASS"
    assert all(analysis["checks"].values())
    assert analysis["training_authorized"] is False
    assert analysis["next_gate"] == "signed_dynamic_pref_qref_authority"


@pytest.mark.parametrize(
    "mutation",
    ["mapping", "replacement", "interface", "solver", "finite", "drift"],
)
def test_scientific_failure_returns_single_registered_stop(mutation: str) -> None:
    record = _complete_record()
    if mutation == "mapping":
        record["inventory"]["regcv1"][0]["bus"] = 99
    elif mutation == "replacement":
        record["inventory"]["disabled_dynamic_chain"][0]["u"] = 1
    elif mutation == "interface":
        record["interface_identity"]["qref"][2]["non_target_unchanged"] = False
    elif mutation == "solver":
        record["solver"]["tds_test_ok"] = False
    elif mutation == "finite":
        record["finite_guard"]["regcv1_finite"] = False
    else:
        record["drift"]["max_abs_by_signal"]["Pe"] = 2.0e-4

    analysis = classify_regcv1_object_record(record)

    assert analysis["classification"] == "STOP-REGCV1-OBJECT-INITIALIZATION"
    assert analysis["training_authorized"] is False


def test_incomplete_formal_record_is_invalid() -> None:
    record = copy.deepcopy(_complete_record())
    del record["contract_sha256"]

    analysis = classify_regcv1_object_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"
    assert analysis["checks"] == {"record_integrity": False}
    assert analysis["training_authorized"] is False


def test_complete_initialization_failure_is_scientific_stop_not_invalid() -> None:
    record = _complete_record()
    record["physical_trajectory_executed"] = False
    record["trajectory_count"] = 0
    record["solver"]["tds_initialized"] = False
    record["solver"]["tds_test_ok"] = False
    record["solver"]["tds_converged"] = False

    analysis = classify_regcv1_object_record(record)

    assert analysis["classification"] == "STOP-REGCV1-OBJECT-INITIALIZATION"
    assert analysis["checks"]["record_integrity"] is True
