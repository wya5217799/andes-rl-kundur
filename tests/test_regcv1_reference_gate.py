from __future__ import annotations

import hashlib
import importlib.util
import json
from copy import deepcopy
from pathlib import Path

from andes_rl_kundur.evaluation.regcv1_reference_gate import (
    build_reference_contract,
    classify_regcv1_reference_record,
)

ROOT = Path(__file__).resolve().parents[1]


def _payload_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _base_record() -> dict:
    path = ROOT / "tests/test_regcv1_clean_init_gate.py"
    spec = importlib.util.spec_from_file_location("r385_record_fixture", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    record = deepcopy(module._record())
    contract = build_reference_contract()
    record["round"] = "R386"
    record["contract_sha256"] = _payload_sha256(contract)
    rows = [
        {
            "idx": row["idx"],
            "static_p": row["static_p"],
            "static_q": row["static_q"],
        }
        for row in record["references"]["rows"]
    ]
    record["reference_source"] = {
        "captured": True,
        "phase": "post_pflow_pre_tds_init",
        "pflow_converged_at_capture": True,
        "tds_initialized_at_capture": False,
        "rows": rows,
    }
    record["references"]["absolute_tolerance"] = contract[
        "reference_abs_tolerance"
    ]
    return record


def test_valid_reference_source_preserves_clean_pass() -> None:
    analysis = classify_regcv1_reference_record(_base_record())

    assert analysis["round"] == "R386"
    assert analysis["classification"] == "REGCV1-CLEAN-INIT-PASS"
    assert analysis["checks"]["reference_source_timing"] is True


def test_wrong_capture_phase_or_contract_digest_is_invalid() -> None:
    record = _base_record()
    record["reference_source"]["tds_initialized_at_capture"] = True
    assert (
        classify_regcv1_reference_record(record)["classification"]
        == "ANALYSIS-INVALID"
    )

    record = _base_record()
    record["contract_sha256"] = "0" * 64
    assert (
        classify_regcv1_reference_record(record)["classification"]
        == "ANALYSIS-INVALID"
    )


def test_source_rows_must_be_complete_unique_and_used_verbatim() -> None:
    record = _base_record()
    record["reference_source"]["rows"][0].pop("static_q")
    assert (
        classify_regcv1_reference_record(record)["classification"]
        == "ANALYSIS-INVALID"
    )

    record = _base_record()
    record["references"]["rows"][0]["pref"] = 999.0
    record["references"]["rows"][0]["pref_match"] = True
    assert (
        classify_regcv1_reference_record(record)["classification"]
        == "ANALYSIS-INVALID"
    )

    record = _base_record()
    record["references"]["absolute_tolerance"] = 1.0
    assert (
        classify_regcv1_reference_record(record)["classification"]
        == "ANALYSIS-INVALID"
    )


def test_expected_pflow_failure_is_scientific_stop_without_snapshot() -> None:
    record = _base_record()
    record["reference_source"] = {
        "captured": False,
        "phase": None,
        "pflow_converged_at_capture": False,
        "tds_initialized_at_capture": False,
        "rows": [],
    }
    record["references"] = {"checked": False, "rows": []}
    record["scientific_error"] = "PFlow.run returned a non-success value"
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
    record["finite_guard"]["checked"] = False
    record["drift"]["checked"] = False

    analysis = classify_regcv1_reference_record(record)

    assert analysis["classification"] == "STOP-REGCV1-CLEAN-INITIALIZATION"
    assert analysis["checks"]["reference_source_timing"] is False


def test_pflow_failure_requires_exact_empty_pre_capture_sentinel() -> None:
    for mutate in ("phase", "rows", "references"):
        record = _base_record()
        record["reference_source"] = {
            "captured": False,
            "phase": None,
            "pflow_converged_at_capture": False,
            "tds_initialized_at_capture": False,
            "rows": [],
        }
        record["references"] = {"checked": False, "rows": []}
        record["scientific_error"] = "PFlow.run returned a non-success value"
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
        record["finite_guard"]["checked"] = False
        record["drift"]["checked"] = False
        if mutate == "phase":
            record["reference_source"]["phase"] = "bogus"
        elif mutate == "rows":
            record["reference_source"]["rows"] = [{"garbage": True}]
        else:
            record["references"] = {"checked": True, "rows": [{"garbage": True}]}

        assert (
            classify_regcv1_reference_record(record)["classification"]
            == "ANALYSIS-INVALID"
        )

    record = _base_record()
    record["reference_source"]["rows"][1]["idx"] = "REGCV1_1"
    assert (
        classify_regcv1_reference_record(record)["classification"]
        == "ANALYSIS-INVALID"
    )

    record = _base_record()
    record["references"]["rows"][2]["static_p"] += 0.1
    assert (
        classify_regcv1_reference_record(record)["classification"]
        == "ANALYSIS-INVALID"
    )
