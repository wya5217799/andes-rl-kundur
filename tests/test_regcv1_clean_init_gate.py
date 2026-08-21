from __future__ import annotations

import hashlib
import json
from copy import deepcopy

from andes_rl_kundur.evaluation.regcv1_clean_init_gate import (
    build_clean_contract,
    classify_regcv1_clean_init_record,
)


def _payload_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _record() -> dict:
    contract = build_clean_contract()
    return {
        "schema_version": 1,
        "round": "R385",
        "question": "Q-0105",
        "contract_sha256": _payload_sha256(contract),
        "formal_input_complete": True,
        "execution_error": None,
        "scientific_error": None,
        "trajectory_attempted": True,
        "physical_trajectory_executed": True,
        "trajectory_count": 1,
        "training_executed": False,
        "source": {
            "xlsx_json_static_equal": True,
            "xlsx_case_sha256": "a" * 64,
            "json_case_sha256": "b" * 64,
            "derived_case_sha256": "c" * 64,
            "derived_case_deterministic": True,
        },
        "inventory": {
            "network": {
                "bus_count": 10,
                "line_count": 15,
                "pq_count": 2,
                "static_gen_count": 4,
                "static_generator_buses": [1, 2, 3, 4],
            },
            "forbidden_model_counts": {
                "GENROU": 0,
                "TGOV1": 0,
                "EXDC2": 0,
                "Toggler": 0,
            },
            "forbidden_dae_names": [],
            "regcv1": [
                {
                    "idx": f"REGCV1_{index}",
                    "bus": index,
                    "gen": index,
                    "Sn": 900.0,
                    "u": 1,
                }
                for index in range(1, 5)
            ],
        },
        "references": {
            "checked": True,
            "rows": [
                {
                    "idx": f"REGCV1_{index}",
                    "static_p": 0.7,
                    "static_q": 0.1,
                    "pref": 0.7,
                    "qref": 0.1,
                    "pref_match": True,
                    "qref_match": True,
                }
                for index in range(1, 5)
            ],
        },
        "initialization_diagnostics": {
            "captured": True,
            "equation_count": 100,
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
        "finite_guard": {
            "checked": True,
            "dae_finite": True,
            "regcv1_finite": True,
        },
        "drift": {
            "checked": True,
            "max_abs_by_signal": {
                "Pe": 0.0,
                "Qe": 0.0,
                "dw": 0.0,
                "omega": 0.0,
                "v": 0.0,
            },
        },
    }


def test_clean_record_passes_and_opens_only_signed_authority() -> None:
    analysis = classify_regcv1_clean_init_record(_record())

    assert analysis["classification"] == "REGCV1-CLEAN-INIT-PASS"
    assert analysis["next_gate"] == "signed_dynamic_pref_qref_authority"
    assert analysis["training_authorized"] is False


def test_native_initialization_failure_is_scientific_stop() -> None:
    record = _record()
    record["trajectory_attempted"] = False
    record["physical_trajectory_executed"] = False
    record["trajectory_count"] = 0
    record["solver"].update(
        tds_test_ok=False,
        tds_converged=False,
        terminal_time_seconds=0.0,
    )
    record["finite_guard"]["checked"] = False
    record["drift"]["checked"] = False
    record["initialization_diagnostics"].update(
        bad_combined_indices=[7],
        residual_count=1,
        residuals=[
            {
                "combined_index": 7,
                "name": "Pe REGCV1 1",
                "residual": 0.2,
                "equation": "Pe - p_ref",
                "model": "REGCV1",
                "idx": "REGCV1_1",
            }
        ],
    )

    analysis = classify_regcv1_clean_init_record(record)

    assert analysis["classification"] == "STOP-REGCV1-CLEAN-INITIALIZATION"
    assert analysis["next_gate"] is None
    assert analysis["retry_authorized"] is False


def test_missing_diagnostics_or_retained_legacy_model_is_invalid() -> None:
    for mutate in ("diagnostics", "legacy"):
        record = deepcopy(_record())
        if mutate == "diagnostics":
            record["initialization_diagnostics"]["captured"] = False
        else:
            record["inventory"]["forbidden_model_counts"]["TGOV1"] = 4

        analysis = classify_regcv1_clean_init_record(record)

        assert analysis["classification"] == "ANALYSIS-INVALID"
        assert analysis["next_gate"] is None


def test_missing_hash_or_contract_digest_is_invalid() -> None:
    for field in (
        "xlsx_case_sha256",
        "json_case_sha256",
        "derived_case_sha256",
    ):
        record = _record()
        record["source"][field] = "not-a-sha256"
        assert (
            classify_regcv1_clean_init_record(record)["classification"]
            == "ANALYSIS-INVALID"
        )

    record = _record()
    record["contract_sha256"] = "0" * 64
    assert (
        classify_regcv1_clean_init_record(record)["classification"]
        == "ANALYSIS-INVALID"
    )


def test_malformed_or_incomplete_diagnostic_rows_are_invalid() -> None:
    malformed_rows = [
        {
            "equation_count": 100,
            "bad_combined_indices": [7],
            "residual_count": 1,
            "residuals": ["not-a-row"],
            "clamped_limits": [],
        },
        {
            "equation_count": 100,
            "bad_combined_indices": [7],
            "residual_count": 1,
            "residuals": [
                {
                    "combined_index": 7,
                    "name": "Pe REGCV1 1",
                    "residual": 1.0e-8,
                    "equation": "Pe - p_ref",
                    "model": "REGCV1",
                    "idx": "REGCV1_1",
                }
            ],
            "clamped_limits": [],
        },
        {
            "equation_count": 100,
            "bad_combined_indices": [],
            "residual_count": 0,
            "residuals": [],
            "clamped_limits": [{"model": "REGCV1"}],
        },
    ]
    for values in malformed_rows:
        record = _record()
        record["initialization_diagnostics"].update(values)
        assert (
            classify_regcv1_clean_init_record(record)["classification"]
            == "ANALYSIS-INVALID"
        )


def test_execution_error_or_false_trajectory_accounting_is_invalid() -> None:
    record = _record()
    record["execution_error"] = "RuntimeError: diagnostic capture failed"
    assert (
        classify_regcv1_clean_init_record(record)["classification"]
        == "ANALYSIS-INVALID"
    )

    record = _record()
    record["trajectory_attempted"] = False
    assert (
        classify_regcv1_clean_init_record(record)["classification"]
        == "ANALYSIS-INVALID"
    )
