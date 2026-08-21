from __future__ import annotations

import hashlib
import json
from copy import deepcopy

from andes_rl_kundur.evaluation.regf2_object_init_gate import (
    build_regf2_object_init_contract,
    classify_regf2_object_init_record,
)


def _sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _record() -> dict:
    contract = build_regf2_object_init_contract()
    device_ids = [f"REGF2_{index}" for index in range(1, 5)]
    times = [0.0, 0.1, 0.2]
    return {
        "schema_version": 1,
        "round": "R389",
        "question": "Q-0107",
        "contract_sha256": _sha256(contract),
        "formal_input_complete": True,
        "execution_error": None,
        "scientific_error": None,
        "training_executed": False,
        "post_init_action_executed": False,
        "trajectory_attempted": True,
        "physical_trajectory_executed": True,
        "trajectory_count": 1,
        "source": {
            "andes_version": "2.0.0",
            "xlsx_json_static_equal": True,
            "derived_case_deterministic": True,
            "xlsx_case_sha256": contract["xlsx_case_sha256"],
            "json_case_sha256": contract["json_case_sha256"],
            "derived_case_sha256": contract["derived_case_sha256"],
            "regf1_source_sha256": contract["regf1_source_sha256"],
            "regf2_source_sha256": contract["regf2_source_sha256"],
        },
        "inventory": {
            "network": deepcopy(contract["network_inventory"]),
            "forbidden_model_counts": {
                name: 0 for name in contract["forbidden_models"]
            },
            "forbidden_dae_names": [],
            "regf2": [
                {
                    **mapping,
                    "Sn": 900.0,
                    "u": 1,
                    "input_parameter_card": deepcopy(contract["parameter_card"]),
                    "runtime_parameter_card": deepcopy(
                        contract["runtime_parameter_card"]
                    ),
                    "pll": f"PLL2_{index}",
                }
                for index, mapping in enumerate(contract["expected_mapping"], 1)
            ],
            "pll2": [
                {"idx": f"PLL2_{index}", "bus": index, "u": 1}
                for index in range(1, 5)
            ],
        },
        "references": {
            "phase": "post-pflow-pre-init-to-post-init",
            "checked": True,
            "absolute_tolerance": 1.0e-12,
            "rows": [
                {
                    "idx": device_id,
                    "static_p": 7.0,
                    "static_q": 0.8,
                    "pref": 7.0,
                    "qref": 0.8,
                    "pref_match": True,
                    "qref_match": True,
                }
                for device_id in device_ids
            ],
        },
        "initialization_diagnostics": {
            "captured": True,
            "equation_count": 200,
            "bad_combined_indices": [],
            "residual_count": 0,
            "residuals": [],
            "clamped_limits": [],
        },
        "solver": {
            "setup_completed": True,
            "pflow_converged": True,
            "tds_initialized": True,
            "tds_test_ok": True,
            "tds_converged": True,
            "terminal_time_seconds": 0.2,
            "tds_tolerance": 1.0e-4,
        },
        "trace": {
            "checked": True,
            "times": times,
            "bus_v": [
                {str(bus): 1.0 for bus in range(1, 11)} for _ in times
            ],
            "devices": {
                device_id: {
                    "Pe": [7.0, 7.0, 7.0],
                    "Qe": [0.8, 0.8, 0.8],
                    "Id": [7.0, 7.0, 7.0],
                    "Iq": [-0.8, -0.8, -0.8],
                    "virtual_frequency": [1.0, 1.0, 1.0],
                }
                for device_id in device_ids
            },
        },
        "finite_guard": {
            "checked": True,
            "dae_finite": True,
            "regf2_finite": True,
        },
    }


def test_clean_regf2_record_passes_only_object_initialization() -> None:
    analysis = classify_regf2_object_init_record(_record())

    assert analysis["classification"] == "REGF2-OBJECT-INIT-PASS"
    assert analysis["next_gate"] == "regf2_dynamic_signal_authority"
    assert analysis["post_init_actions_authorized"] is False
    assert analysis["training_authorized"] is False


def test_complete_native_initialization_failure_is_scientific_stop() -> None:
    record = _record()
    record["scientific_error"] = "TDS initialization failed"
    record["trajectory_attempted"] = False
    record["physical_trajectory_executed"] = False
    record["trajectory_count"] = 0
    record["solver"].update(
        tds_initialized=False,
        tds_test_ok=False,
        tds_converged=False,
        terminal_time_seconds=0.0,
    )
    record["trace"] = {
        "checked": False,
        "times": [],
        "bus_v": [],
        "devices": {},
    }
    record["finite_guard"] = {
        "checked": True,
        "dae_finite": False,
        "regf2_finite": False,
    }
    record["initialization_diagnostics"].update(
        bad_combined_indices=[17],
        residual_count=1,
        residuals=[
            {
                "combined_index": 17,
                "name": "Pe REGF2 REGF2_1",
                "residual": 0.25,
                "equation": "Pe balance",
                "model": "REGF2",
                "idx": "REGF2_1",
            }
        ],
    )

    analysis = classify_regf2_object_init_record(record)

    assert analysis["classification"] == "STOP-REGF2-OBJECT-INITIALIZATION"
    assert analysis["next_gate"] is None


def test_pflow_failure_requires_exact_pre_reference_sentinel() -> None:
    record = _record()
    record["scientific_error"] = "PFlow did not converge"
    record["trajectory_attempted"] = False
    record["physical_trajectory_executed"] = False
    record["trajectory_count"] = 0
    record["solver"].update(
        pflow_converged=False,
        tds_initialized=False,
        tds_test_ok=False,
        tds_converged=False,
        terminal_time_seconds=0.0,
    )
    record["references"] = {
        "phase": None,
        "checked": False,
        "absolute_tolerance": 1.0e-12,
        "rows": [],
    }
    record["trace"] = {
        "checked": False,
        "times": [],
        "bus_v": [],
        "devices": {},
    }

    assert (
        classify_regf2_object_init_record(record)["classification"]
        == "STOP-REGF2-OBJECT-INITIALIZATION"
    )

    record["references"]["phase"] = "polluted"
    assert (
        classify_regf2_object_init_record(record)["classification"]
        == "ANALYSIS-INVALID"
    )


def test_expected_tds_failures_require_solver_and_trace_identity() -> None:
    partial = _record()
    partial["scientific_error"] = "TDS did not reach horizon"
    partial["solver"].update(tds_converged=False, terminal_time_seconds=0.1)
    partial["trace"]["times"] = [0.0, 0.05, 0.1]
    partial["trace"]["bus_v"] = partial["trace"]["bus_v"][:3]
    for signals in partial["trace"]["devices"].values():
        for name in signals:
            signals[name] = signals[name][:3]
    assert (
        classify_regf2_object_init_record(partial)["classification"]
        == "STOP-REGF2-OBJECT-INITIALIZATION"
    )

    forged_convergence = deepcopy(partial)
    forged_convergence["solver"]["tds_converged"] = True
    assert (
        classify_regf2_object_init_record(forged_convergence)["classification"]
        == "ANALYSIS-INVALID"
    )

    terminal_mismatch = deepcopy(partial)
    terminal_mismatch["solver"]["terminal_time_seconds"] = 0.08
    assert (
        classify_regf2_object_init_record(terminal_mismatch)["classification"]
        == "ANALYSIS-INVALID"
    )

    missing_trace = deepcopy(partial)
    missing_trace["trace"] = {
        "checked": False,
        "times": [],
        "bus_v": [],
        "devices": {},
    }
    assert (
        classify_regf2_object_init_record(missing_trace)["classification"]
        == "ANALYSIS-INVALID"
    )


def test_initialization_failure_requires_completed_finite_status() -> None:
    record = _record()
    record["scientific_error"] = "TDS initialization failed"
    record["trajectory_attempted"] = False
    record["physical_trajectory_executed"] = False
    record["trajectory_count"] = 0
    record["solver"].update(
        tds_initialized=False,
        tds_test_ok=False,
        tds_converged=False,
        terminal_time_seconds=0.0,
    )
    record["trace"] = {
        "checked": False,
        "times": [],
        "bus_v": [],
        "devices": {},
    }
    record["finite_guard"]["checked"] = False

    assert (
        classify_regf2_object_init_record(record)["classification"]
        == "ANALYSIS-INVALID"
    )

    record["finite_guard"]["checked"] = True
    record["solver"]["tds_initialized"] = True
    assert (
        classify_regf2_object_init_record(record)["classification"]
        == "STOP-REGF2-OBJECT-INITIALIZATION"
    )

    test_only = deepcopy(record)
    test_only["solver"]["tds_initialized"] = False
    test_only["solver"]["tds_test_ok"] = True
    assert (
        classify_regf2_object_init_record(test_only)["classification"]
        == "STOP-REGF2-OBJECT-INITIALIZATION"
    )


def test_provenance_inventory_diagnostics_and_action_defects_are_invalid() -> None:
    mutations = []

    bad_hash = _record()
    bad_hash["source"]["regf2_source_sha256"] = "0" * 64
    mutations.append(bad_hash)

    bad_case_hash = _record()
    bad_case_hash["source"]["xlsx_case_sha256"] = "0" * 64
    mutations.append(bad_case_hash)

    bad_pll = _record()
    bad_pll["inventory"]["pll2"][0]["bus"] = 10
    mutations.append(bad_pll)

    bad_runtime_card = _record()
    bad_runtime_card["inventory"]["regf2"][0]["runtime_parameter_card"][
        "Pmax"
    ] = 1.0
    mutations.append(bad_runtime_card)

    bad_diag = _record()
    bad_diag["initialization_diagnostics"].update(
        bad_combined_indices=[999],
        residual_count=1,
        residuals=[{}],
    )
    mutations.append(bad_diag)

    action = _record()
    action["post_init_action_executed"] = True
    mutations.append(action)

    for record in mutations:
        assert (
            classify_regf2_object_init_record(record)["classification"]
            == "ANALYSIS-INVALID"
        )


def test_trace_recomputation_makes_guard_or_drift_failure_a_stop() -> None:
    guard = _record()
    guard["trace"]["bus_v"][1]["4"] = 1.2
    assert (
        classify_regf2_object_init_record(guard)["classification"]
        == "STOP-REGF2-OBJECT-INITIALIZATION"
    )

    drift = _record()
    drift["trace"]["devices"]["REGF2_3"]["Pe"][-1] = 7.001
    assert (
        classify_regf2_object_init_record(drift)["classification"]
        == "STOP-REGF2-OBJECT-INITIALIZATION"
    )


def test_reference_flags_and_supplied_contract_cannot_forge_a_pass() -> None:
    record = _record()
    record["references"]["rows"][0]["pref"] = 999.0
    assert (
        classify_regf2_object_init_record(record)["classification"]
        == "ANALYSIS-INVALID"
    )

    mutated_contract = build_regf2_object_init_contract()
    mutated_contract["drift_abs_limit_system_pu"] = 1.0
    record = _record()
    record["contract_sha256"] = _sha256(mutated_contract)
    assert (
        classify_regf2_object_init_record(record, contract=mutated_contract)[
            "classification"
        ]
        == "ANALYSIS-INVALID"
    )
