"""R386 reference-capture correction contract and pure classifier."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from andes_rl_kundur.evaluation.regcv1_clean_init_gate import (
    build_clean_contract,
    classify_regcv1_clean_init_record,
)

REFERENCE_PHASE = "post_pflow_pre_tds_init"


def _payload_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def build_reference_contract() -> dict[str, Any]:
    """Return the R385 scientific gate with only R386 capture proof added."""

    contract = deepcopy(build_clean_contract())
    contract["round"] = "R386"
    contract["reference_source_phase"] = REFERENCE_PHASE
    return contract


def _row_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _reference_source_pass(
    record: Mapping[str, Any], contract: Mapping[str, Any]
) -> bool:
    try:
        source = record["reference_source"]
        source_rows = source["rows"]
        comparison_rows = record["references"]["rows"]
        expected_idx = [row["idx"] for row in contract["expected_mapping"]]
        if (
            source["captured"] is not True
            or source["phase"] != contract["reference_source_phase"]
            or source["pflow_converged_at_capture"] is not True
            or source["tds_initialized_at_capture"] is not False
            or not _row_sequence(source_rows)
            or not _row_sequence(comparison_rows)
            or len(source_rows) != 4
            or len(comparison_rows) != 4
        ):
            return False

        normalized_source = [
            {
                "idx": str(row["idx"]),
                "static_p": float(row["static_p"]),
                "static_q": float(row["static_q"]),
            }
            for row in source_rows
        ]
        tolerance = float(record["references"]["absolute_tolerance"])
        if tolerance != float(contract["reference_abs_tolerance"]):
            return False
        normalized_comparison: list[dict[str, Any]] = []
        for row in comparison_rows:
            static_p = float(row["static_p"])
            static_q = float(row["static_q"])
            pref = float(row["pref"])
            qref = float(row["qref"])
            if not all(_finite(value) for value in (static_p, static_q, pref, qref)):
                return False
            pref_match = math.isclose(
                pref,
                static_p,
                rel_tol=0.0,
                abs_tol=tolerance,
            )
            qref_match = math.isclose(
                qref,
                static_q,
                rel_tol=0.0,
                abs_tol=tolerance,
            )
            if row["pref_match"] is not pref_match or row["qref_match"] is not qref_match:
                return False
            normalized_comparison.append(
                {
                    "idx": str(row["idx"]),
                    "static_p": static_p,
                    "static_q": static_q,
                }
            )
        return bool(
            [row["idx"] for row in normalized_source] == expected_idx
            and len(set(expected_idx)) == len(expected_idx)
            and all(
                _finite(row["static_p"]) and _finite(row["static_q"])
                for row in normalized_source
            )
            and normalized_comparison == normalized_source
        )
    except (KeyError, TypeError, ValueError):
        return False


def _empty_pre_capture_sentinel(record: Mapping[str, Any]) -> bool:
    try:
        source = record["reference_source"]
        references = record["references"]
        return bool(
            source
            == {
                "captured": False,
                "phase": None,
                "pflow_converged_at_capture": False,
                "tds_initialized_at_capture": False,
                "rows": [],
            }
            and references == {"checked": False, "rows": []}
        )
    except (KeyError, TypeError):
        return False


def _analysis_invalid() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": "R386",
        "question": "Q-0105",
        "classification": "ANALYSIS-INVALID",
        "checks": {
            "record_integrity": False,
            "reference_source_timing": False,
        },
        "claim_scope": (
            "structurally clean four-REGCV1 initialization and zero-input "
            "validity only"
        ),
        "next_gate": None,
        "retry_authorized": False,
        "training_authorized": False,
    }


def classify_regcv1_reference_record(
    record: Mapping[str, Any],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify one R386 record while reusing the reviewed R385 gate."""

    expected = build_reference_contract()
    spec = expected if contract is None else contract
    try:
        reference_source_valid = _reference_source_pass(record, spec)
        expected_pflow_failure = bool(
            record["scientific_error"]
            == "PFlow.run returned a non-success value"
            and record["solver"]["pflow_converged"] is False
            and _empty_pre_capture_sentinel(record)
        )
        valid_r386_envelope = bool(
            spec == expected
            and record["schema_version"] == 1
            and record["round"] == "R386"
            and record["question"] == "Q-0105"
            and record["contract_sha256"] == _payload_sha256(spec)
            and (reference_source_valid or expected_pflow_failure)
        )
    except (KeyError, TypeError, ValueError):
        valid_r386_envelope = False
    if not valid_r386_envelope:
        return _analysis_invalid()

    base_contract = build_clean_contract()
    normalized = deepcopy(dict(record))
    normalized["round"] = "R385"
    normalized["contract_sha256"] = _payload_sha256(base_contract)
    analysis = classify_regcv1_clean_init_record(
        normalized,
        contract=base_contract,
    )
    analysis["round"] = "R386"
    analysis["checks"] = {
        **analysis["checks"],
        "reference_source_timing": reference_source_valid,
    }
    return analysis


__all__ = ["build_reference_contract", "classify_regcv1_reference_record"]
