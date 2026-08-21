"""Classify the R392 one-variable-at-a-time REGF2 loop-perturbation gate.

Motivation:
    R391/CLM-1100 locates two reproducible positive-real local modes in the
    exact initialized four-stock-REGF2 reduced model but participation is
    association, not causality. R392 perturbs exactly one explicit REGF2
    parameter per arm, before setup, and re-runs the frozen no-time-advance
    EIG gate. This pure classifier maps per-arm material-root movement to a
    bounded mechanism attribution per the prospectively frozen prediction
    table. It imports no ANDES runtime code so records replay on Windows.

Failure modes:
    Any schema, provenance, perturbation-readback, guard-field, or artifact
    defect is ANALYSIS-INVALID. A reference-arm failure is a platform STOP.
    A perturbation arm that fails power flow, initialization, or a finite
    guard is a typed per-arm stop and contributes no attribution.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from andes_rl_kundur.evaluation import regf2_equilibrium_eig_correction_gate as r391

ROUND_ID = "R392"
QUESTION_ID = "Q-0109"
LINE_ID = "converter-vsg-pq-decoupling"

R391_PARENT_SHA256 = {
    "seal": "59c480f793dc8974958496a0c7c4926b44aa6b2d242077fea23961df155a6cea",
    "attempt": "18a903b25452829bafc8b7734d1871768c7d15734ba56a94b85813740f04fb1b",
    "execution": "77231c9b95de877c83ed1d4a09710168b6bb249bb1c4b7c1d4e7561a9c7543d8",
    "analysis": "170658c967798aced2f4b62b614dd2863d2a8445ea4e92fbc2ac05968731619e",
    "manifest": "47b8ff337f47161ea8309b9e606d2dc719038d2974449551e515aa8f966c715f",
    "claim": "dde17a7cf1651076019597a34e8491f1cc43ba81f9f1d93e6655a0b020230201",
    "feed": "4e17ff2bddbcee6630a431447ca203d1b39f951beda26b8f2b040b595886d3f8",
    "diagnosis": "057bc8f2854bae1152807789dd4d5098d39643b251edcc70a159111aeca84a00",
    "publication_audit": "a078ed53eb0012c28de7232be7fac61afe5c0e652e3b479a88da2e2d69e66f96",
    "verdict": "783563039870384cdcff1c58ca7ab8a79b40d16651c643f06d72debcdd1c0f47",
}

R391_REFERENCE_ROOTS = {
    "leading": {"real": 46.41533383454654, "imag": 0.0},
    "second": {"real": 4.606789511264594, "imag": 0.0},
}

ARMS = (
    {
        "name": "A0_reference",
        "tds_tolerance": 1.0e-4,
        "perturbation": None,
    },
    {
        "name": "H1a_mf_x4",
        "tds_tolerance": 1.0e-4,
        "perturbation": {"param": "mf", "factor": 4.0},
    },
    {
        "name": "H1b_mf_div4",
        "tds_tolerance": 1.0e-4,
        "perturbation": {"param": "mf", "factor": 0.25},
    },
    {
        "name": "H2a_Tpm_x10",
        "tds_tolerance": 1.0e-4,
        "perturbation": {"param": "Tpm", "factor": 10.0},
    },
    {
        "name": "H2b_Tr_x10",
        "tds_tolerance": 1.0e-4,
        "perturbation": {"param": "Tr", "factor": 10.0},
    },
    {
        "name": "H3a_KIv_x4",
        "tds_tolerance": 1.0e-4,
        "perturbation": {"param": "KIv", "factor": 4.0},
    },
    {
        "name": "H3b_KIv_div4",
        "tds_tolerance": 1.0e-4,
        "perturbation": {"param": "KIv", "factor": 0.25},
    },
    {
        "name": "H4_Sn_100",
        "tds_tolerance": 1.0e-4,
        "perturbation": {"param": "Sn", "value": 100.0},
    },
)

CARD_DEFAULTS = {
    "mf": 0.15,
    "dd": 0.11,
    "Tpm": 0.025,
    "Tr": 0.005,
    "KIv": 10.0,
    "Sn": 900.0,
}

FAMILY_OF = {
    "H1a_mf_x4": "VSM-INERTIA",
    "H1b_mf_div4": "VSM-INERTIA",
    "H2a_Tpm_x10": "SENSING-CHAIN",
    "H2b_Tr_x10": "SENSING-CHAIN",
    "H3a_KIv_x4": "VOLTAGE-OUTER-PI",
    "H3b_KIv_div4": "VOLTAGE-OUTER-PI",
    "H4_Sn_100": "RATING-SCALE",
}

PREDICTION = {
    "VSM-INERTIA": {"lambda1": True, "lambda2": False},
    "SENSING-CHAIN": {"lambda1": True, "lambda2": False},
    "VOLTAGE-OUTER-PI": {"lambda1": False, "lambda2": True},
    "RATING-SCALE": {"lambda1": True, "lambda2": True},
}

THRESHOLDS = {
    "material_root_real_threshold": 1.0e-6,
    "movement_relative_threshold": 0.10,
    "reproduction_relative_tolerance": 1.0e-6,
    "reduced_state_count": 64,
}

TYPED_ARM_STOPS = {
    "PFlow did not converge",
    "TDS initialization failed",
}


def payload_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def expected_perturbation_value(
    spec: Mapping[str, Any] | None, card_defaults: Mapping[str, float]
) -> float | None:
    """Return the frozen expected value for a perturbation spec."""

    if spec is None:
        return None
    param = str(spec["param"])
    if param not in card_defaults:
        raise ValueError(f"unknown perturbation parameter: {param}")
    if "value" in spec:
        return float(spec["value"])
    return float(card_defaults[param]) * float(spec["factor"])


def build_regf2_loop_perturbation_contract() -> dict[str, Any]:
    """Return R391's science unchanged plus the frozen R392 bank and table."""

    science = r391.build_regf2_equilibrium_eig_correction_contract()
    contract = deepcopy(science)
    contract.update(
        {
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "parent_round": "R391",
            "parent_contract_sha256": payload_sha256(science),
            "parent_r391_sha256": deepcopy(R391_PARENT_SHA256),
            "r391_reference_roots": deepcopy(R391_REFERENCE_ROOTS),
            "arms": deepcopy(list(ARMS)),
            "card_defaults": deepcopy(CARD_DEFAULTS),
            "family_of": deepcopy(FAMILY_OF),
            "prediction": deepcopy(PREDICTION),
            "thresholds": deepcopy(THRESHOLDS),
            "trajectory_count": 0,
            "post_init_actions_authorized": False,
            "retry_authorized": False,
            "training_authorized": False,
        }
    )
    return contract


def _finite_number(value: object) -> bool:
    return bool(
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _material_roots(
    eigenvalues: object, threshold: float
) -> list[complex] | None:
    """Return roots with Re > threshold sorted by descending real part."""

    if not isinstance(eigenvalues, list) or not eigenvalues:
        return None
    roots: list[complex] = []
    for row in eigenvalues:
        if (
            not isinstance(row, Mapping)
            or not _finite_number(row.get("real"))
            or not _finite_number(row.get("imag"))
        ):
            return None
        value = complex(float(row["real"]), float(row["imag"]))
        if value.real > threshold:
            roots.append(value)
    roots.sort(key=lambda value: (-value.real, abs(value.imag)))
    return roots


def _relative_deviation(value: complex, baseline: complex) -> float:
    denominator = abs(baseline.real)
    if denominator == 0.0:
        return float("inf") if value.real != 0.0 else 0.0
    return abs(value.real - baseline.real) / denominator


def _moved(
    arm_roots: list[complex],
    a0_roots: list[complex],
    position: int,
    threshold: float,
) -> bool:
    """True when the position-th material root moved beyond the threshold."""

    if len(arm_roots) != len(a0_roots):
        return True
    if position >= len(a0_roots):
        return False
    return bool(
        _relative_deviation(arm_roots[position], a0_roots[position]) > threshold
    )


def _perturbation_valid(
    arm: Mapping[str, Any], spec: Mapping[str, Any], contract: Mapping[str, Any]
) -> tuple[bool, float | None]:
    """Validate the archived perturbation spec and exact four-device readback."""

    try:
        recorded = arm["perturbation"]
        spec_perturbation = spec["perturbation"]
        expected = expected_perturbation_value(
            spec_perturbation, contract["card_defaults"]
        )
        if expected is None:
            return bool(
                recorded["param"] is None
                and recorded["factor"] is None
                and recorded["expected_value"] is None
                and recorded["applied"] is False
                and recorded["readback"] == []
            ), None
        readback = recorded["readback"]
        return bool(
            recorded["param"] == spec_perturbation["param"]
            and recorded["expected_value"] == expected
            and recorded["applied"] is True
            and isinstance(readback, list)
            and len(readback) == 4
            and all(
                _finite_number(value) and float(value) == expected
                for value in readback
            )
        ), expected
    except (KeyError, TypeError):
        return False, None


def _arm_outcome(
    arm: Mapping[str, Any],
    spec: Mapping[str, Any],
    contract: Mapping[str, Any],
    *,
    is_reference: bool,
) -> dict[str, Any]:
    """Validate one arm record and extract its material-root movement."""

    thresholds = contract["thresholds"]
    outcome: dict[str, Any] = {
        "name": spec["name"],
        "valid": False,
        "completed": False,
        "arm_stop": None,
        "perturbation_readback_ok": False,
        "guard_fields_ok": False,
        "material_roots": None,
        "lambda1_moved": None,
        "lambda2_moved": None,
    }
    try:
        if arm["execution_error"] is not None:
            return outcome
        if not (
            arm["trajectory_attempted"] is False
            and arm["physical_trajectory_executed"] is False
            and arm["trajectory_count"] == 0
        ):
            return outcome
        perturbation_ok, _ = _perturbation_valid(arm, spec, contract)
        outcome["perturbation_readback_ok"] = perturbation_ok
        if not perturbation_ok:
            return outcome
        scientific_error = arm["scientific_error"]
        if scientific_error in TYPED_ARM_STOPS:
            if is_reference:
                return outcome
            outcome["valid"] = True
            outcome["arm_stop"] = str(scientific_error)
            return outcome
        if scientific_error is not None:
            return outcome
        solver = arm["solver"]
        finite = arm["finite_guard"]
        snapshot = arm["equilibrium_snapshot"]
        diagnostics = arm["initialization_diagnostics"]
        matrix = arm["matrix"]
        guard_fields_ok = bool(
            solver["setup_completed"] is True
            and solver["pflow_converged"] is True
            and solver["tds_initialized"] is True
            and solver["tds_test_ok"] is True
            and solver["eig_return"] is True
            and solver["system_exit_code"] == 0
            and solver["actual_tds_tolerance"] == spec["tds_tolerance"]
            and solver["time_before_eig"] == 0.0
            and solver["time_after_eig"] == 0.0
            and solver["state_max_abs_delta"] == 0.0
            and finite["checked"] is True
            and finite["dae_finite"] is True
            and finite["jacobian_finite"] is True
            and finite["state_matrix_finite"] is True
            and snapshot["captured"] is True
            and snapshot["before"]["time"] == 0.0
            and snapshot["after"]["time"] == 0.0
            and diagnostics["captured"] is True
            and diagnostics["residual_count"] == 0
            and diagnostics["clamped_limits"] == []
            and matrix["captured"] is True
            and len(matrix["state_names"])
            == thresholds["reduced_state_count"]
            and len(matrix["andes_eigenvalues"]) == len(matrix["state_names"])
        )
        outcome["guard_fields_ok"] = guard_fields_ok
        if not guard_fields_ok:
            return outcome
        roots = _material_roots(
            matrix["andes_eigenvalues"],
            thresholds["material_root_real_threshold"],
        )
        if roots is None:
            return outcome
        outcome["material_roots"] = [
            {"real": value.real, "imag": value.imag} for value in roots
        ]
        outcome["valid"] = True
        outcome["completed"] = True
        return outcome
    except (KeyError, TypeError, ValueError):
        return outcome


def classify_regf2_loop_perturbation_record(
    record: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate the eight-arm record and emit the frozen mechanism verdict."""

    thresholds = contract["thresholds"]
    checks = {
        "schema": False,
        "arm_order": False,
        "reference_reproduction": False,
        "attribution": False,
    }
    try:
        arms = record["arms"]
        checks["schema"] = bool(
            record["schema_version"] == 1
            and record["round"] == ROUND_ID
            and record["question"] == QUESTION_ID
            and record["contract_sha256"] == payload_sha256(contract)
            and record.get("formal_input_complete") is True
            and record.get("execution_error") is None
            and record.get("training_executed") is False
            and record.get("post_init_action_executed") is False
            and record.get("trajectory_count") == 0
            and isinstance(arms, list)
            and len(arms) == len(contract["arms"])
        )
        if not checks["schema"]:
            return {
                "classification": "ANALYSIS-INVALID",
                "checks": checks,
                "arm_outcomes": [],
                "attribution": {},
            }
        checks["arm_order"] = [arm["name"] for arm in arms] == [
            spec["name"] for spec in contract["arms"]
        ]
        if not checks["arm_order"]:
            return {
                "classification": "ANALYSIS-INVALID",
                "checks": checks,
                "arm_outcomes": [],
                "attribution": {},
            }
    except (KeyError, TypeError):
        return {
            "classification": "ANALYSIS-INVALID",
            "checks": checks,
            "arm_outcomes": [],
            "attribution": {},
        }

    arm_outcomes = [
        _arm_outcome(arm, spec, contract, is_reference=index == 0)
        for index, (arm, spec) in enumerate(zip(arms, contract["arms"]))
    ]

    if any(
        not outcome["valid"] and outcome["arm_stop"] is None
        for outcome in arm_outcomes[1:]
    ):
        return {
            "classification": "ANALYSIS-INVALID",
            "checks": checks,
            "arm_outcomes": arm_outcomes,
            "attribution": {},
        }

    reference = arm_outcomes[0]
    if not (reference["valid"] and reference["completed"]):
        return {
            "classification": "STOP-REGF2-PERTURBATION-PLATFORM",
            "checks": checks,
            "arm_outcomes": arm_outcomes,
            "attribution": {},
        }
    a0_roots = [
        complex(row["real"], row["imag"]) for row in reference["material_roots"]
    ]
    frozen = contract["r391_reference_roots"]
    if len(a0_roots) != 2:
        checks["reference_reproduction"] = False
        return {
            "classification": "STOP-REGF2-PERTURBATION-PLATFORM",
            "checks": checks,
            "arm_outcomes": arm_outcomes,
            "attribution": {},
        }
    tolerance = thresholds["reproduction_relative_tolerance"]
    checks["reference_reproduction"] = bool(
        _relative_deviation(a0_roots[0], complex(frozen["leading"]["real"], 0.0))
        <= tolerance
        and _relative_deviation(
            a0_roots[1], complex(frozen["second"]["real"], 0.0)
        )
        <= tolerance
    )
    if not checks["reference_reproduction"]:
        return {
            "classification": "STOP-REGF2-PERTURBATION-PLATFORM",
            "checks": checks,
            "arm_outcomes": arm_outcomes,
            "attribution": {},
        }

    movement_threshold = thresholds["movement_relative_threshold"]
    for outcome in arm_outcomes[1:]:
        if outcome["completed"]:
            arm_roots = [
                complex(row["real"], row["imag"])
                for row in outcome["material_roots"]
            ]
            outcome["lambda1_moved"] = _moved(
                arm_roots, a0_roots, 0, movement_threshold
            )
            outcome["lambda2_moved"] = _moved(
                arm_roots, a0_roots, 1, movement_threshold
            )

    families = sorted(set(contract["family_of"].values()))
    attribution: dict[str, Any] = {}
    for family in families:
        family_arms = [
            outcome
            for outcome in arm_outcomes[1:]
            if contract["family_of"][outcome["name"]] == family
        ]
        if not family_arms or any(not outcome["completed"] for outcome in family_arms):
            attribution[family] = {
                "lambda1_moved": False,
                "lambda2_moved": False,
                "supported": False,
                "note": "family arm missing or not completed",
            }
            continue
        lambda1 = all(
            outcome["lambda1_moved"] is True for outcome in family_arms
        )
        lambda2 = all(
            outcome["lambda2_moved"] is True for outcome in family_arms
        )
        prediction = contract["prediction"][family]
        supported = bool(
            (lambda1, lambda2) == (prediction["lambda1"], prediction["lambda2"])
        )
        attribution[family] = {
            "lambda1_moved": lambda1,
            "lambda2_moved": lambda2,
            "supported": supported,
            "note": None,
        }

    supported = [family for family in families if attribution[family]["supported"]]
    any_movement = any(
        attribution[family]["lambda1_moved"] or attribution[family]["lambda2_moved"]
        for family in families
    )
    if not supported and any_movement:
        classification = "MECHANISM-UNPREDICTED"
    elif len(supported) == 1:
        classification = f"MECHANISM-{supported[0]}"
    elif len(supported) > 1:
        classification = "MECHANISM-MIXED"
    else:
        classification = "MECHANISM-NONE-ISOLATED"
    checks["attribution"] = True
    return {
        "classification": classification,
        "checks": checks,
        "arm_outcomes": arm_outcomes,
        "attribution": attribution,
    }


__all__ = [
    "build_regf2_loop_perturbation_contract",
    "classify_regf2_loop_perturbation_record",
    "expected_perturbation_value",
    "payload_sha256",
]
