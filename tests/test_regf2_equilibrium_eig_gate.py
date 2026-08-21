from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import numpy as np
import pytest

from andes_rl_kundur.evaluation.regf2_equilibrium_eig_gate import (
    build_regf2_equilibrium_eig_contract,
    classify_regf2_equilibrium_eig_record,
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


def _object_evidence(contract: dict) -> dict:
    parent = contract["object_contract"]
    return {
        "source": {
            "andes_version": "2.0.0",
            "xlsx_json_static_equal": True,
            "derived_case_deterministic": True,
            "xlsx_case_sha256": parent["xlsx_case_sha256"],
            "json_case_sha256": parent["json_case_sha256"],
            "derived_case_sha256": parent["derived_case_sha256"],
            "regf1_source_sha256": parent["regf1_source_sha256"],
            "regf2_source_sha256": parent["regf2_source_sha256"],
            "eig_source_sha256": contract["eig_source_sha256"],
            "pll2_source_sha256": contract["pll2_source_sha256"],
            "numpy_version": contract["numpy_version"],
            "scipy_version": contract["scipy_version"],
            "system_source_sha256": contract["system_source_sha256"],
            "tds_source_sha256": contract["tds_source_sha256"],
            "dae_source_sha256": contract["dae_source_sha256"],
        },
        "inventory": {
            "network": deepcopy(parent["network_inventory"]),
            "forbidden_model_counts": {
                name: 0 for name in parent["forbidden_models"]
            },
            "forbidden_dae_names": [],
            "regf2": [
                {
                    **mapping,
                    "Sn": 900.0,
                    "u": 1,
                    "input_parameter_card": deepcopy(parent["parameter_card"]),
                    "runtime_parameter_card": deepcopy(
                        parent["runtime_parameter_card"]
                    ),
                    "pll": f"PLL2_{index}",
                }
                for index, mapping in enumerate(parent["expected_mapping"], 1)
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
                    "idx": f"REGF2_{index}",
                    "static_p": 7.0,
                    "static_q": 0.8,
                    "pref": 7.0,
                    "qref": 0.8,
                    "pref_match": True,
                    "qref_match": True,
                }
                for index in range(1, 5)
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
    }


def _state_bindings(contract: dict) -> tuple[list[str], list[dict]]:
    names: list[str] = []
    rows: list[dict] = []
    for model, variables in contract["registered_state_variables"].items():
        prefix = "REGF2" if model == "REGF2" else "PLL2"
        for device in range(1, 5):
            idx = f"{prefix}_{device}"
            for variable in variables:
                name = f"{variable} {model} {idx}"
                rows.append(
                    {
                        "model": model,
                        "idx": idx,
                        "variable": variable,
                        "dae_name": name,
                        "original_address": len(names),
                        "status": "retained",
                        "reduced_index": len(names),
                    }
                )
                names.append(name)
    return names, rows


def _arm(contract: dict, arm_spec: dict) -> dict:
    names, bindings = _state_bindings(contract)
    eigenvalues = -np.arange(1, len(names) + 1, dtype=float)
    matrix = np.diag(eigenvalues)
    snapshot = {
        "time": 0.0,
        "x": [0.0] * len(names),
        "y": [1.0],
        "z": [1.0],
        "f": [0.0] * len(names),
        "g": [0.0],
    }
    evidence = _object_evidence(contract)
    return {
        "name": arm_spec["name"],
        "tds_tolerance": arm_spec["tds_tolerance"],
        "execution_error": None,
        "scientific_error": None,
        "trajectory_attempted": False,
        "physical_trajectory_executed": False,
        "trajectory_count": 0,
        **evidence,
        "solver": {
            "setup_completed": True,
            "pflow_converged": True,
            "tds_initialized": True,
            "tds_test_ok": True,
            "eig_return": True,
            "system_exit_code": 0,
            "actual_tds_tolerance": arm_spec["tds_tolerance"],
            "time_before_eig": 0.0,
            "time_after_eig": 0.0,
            "state_max_abs_delta": 0.0,
        },
        "finite_guard": {
            "checked": True,
            "dae_finite": True,
            "jacobian_finite": True,
            "state_matrix_finite": True,
        },
        "matrix": {
            "captured": True,
            "as": matrix.tolist(),
            "state_names": names,
            "andes_eigenvalues": [
                {"real": float(value), "imag": 0.0} for value in eigenvalues
            ],
            "zero_tf_state_names": [],
            "zero_tf_state_addresses": [],
            "dead_algebraic_indices": [],
            "dae_state_catalog": [
                {"address": index, "name": name, "tf": 1.0}
                for index, name in enumerate(names)
            ],
            "dae_algebraic_names": ["y0"],
            "dae_discrete_names": ["z0"],
            "eig_augmented_algebraic_names": ["y0"],
            "state_bindings": bindings,
        },
        "equilibrium_snapshot": {
            "captured": True,
            "before": deepcopy(snapshot),
            "after": deepcopy(snapshot),
        },
    }


def _record() -> dict:
    contract = build_regf2_equilibrium_eig_contract()
    return {
        "schema_version": 1,
        "round": "R390",
        "question": "Q-0108",
        "contract_sha256": _sha256(contract),
        "formal_input_complete": True,
        "execution_error": None,
        "training_executed": False,
        "post_init_action_executed": False,
        "trajectory_count": 0,
        "arms": [_arm(contract, arm) for arm in contract["arms"]],
    }


def _add_zero_tf_folded_tail(record: dict) -> None:
    for arm in record["arms"]:
        matrix = arm["matrix"]
        folded_name = "folded Other OTHER_1"
        matrix["dae_state_catalog"].append(
            {
                "address": len(matrix["dae_state_catalog"]),
                "name": folded_name,
                "tf": 0.0,
            }
        )
        matrix["zero_tf_state_addresses"] = [
            len(matrix["dae_state_catalog"]) - 1
        ]
        matrix["zero_tf_state_names"] = [folded_name]
        matrix["eig_augmented_algebraic_names"] = ["y0", folded_name]
        matrix["dead_algebraic_indices"] = [1]
        for phase in ("before", "after"):
            arm["equilibrium_snapshot"][phase]["x"].append(0.0)
            arm["equilibrium_snapshot"][phase]["f"].append(0.0)


def _empty_matrix() -> dict:
    return {
        "captured": False,
        "as": [],
        "state_names": [],
        "andes_eigenvalues": [],
        "zero_tf_state_names": [],
        "zero_tf_state_addresses": [],
        "dead_algebraic_indices": [],
        "dae_state_catalog": [],
        "dae_algebraic_names": [],
        "dae_discrete_names": [],
        "eig_augmented_algebraic_names": [],
        "state_bindings": [],
    }


def _empty_snapshot() -> dict:
    return {"captured": False, "before": None, "after": None}


def _failed_matrix(arm: dict) -> dict:
    matrix = arm["matrix"]
    return {
        "captured": False,
        "as": [],
        "state_names": [],
        "andes_eigenvalues": [],
        "zero_tf_state_names": deepcopy(matrix["zero_tf_state_names"]),
        "zero_tf_state_addresses": deepcopy(matrix["zero_tf_state_addresses"]),
        "dead_algebraic_indices": deepcopy(matrix["dead_algebraic_indices"]),
        "dae_state_catalog": deepcopy(matrix["dae_state_catalog"]),
        "dae_algebraic_names": deepcopy(matrix["dae_algebraic_names"]),
        "dae_discrete_names": deepcopy(matrix["dae_discrete_names"]),
        "eig_augmented_algebraic_names": deepcopy(
            matrix["eig_augmented_algebraic_names"]
        ),
        "state_bindings": [],
    }


def test_contract_freezes_two_no_trajectory_numerical_arms() -> None:
    contract = build_regf2_equilibrium_eig_contract()

    assert contract["round"] == "R390"
    assert contract["question"] == "Q-0108"
    assert contract["arms"] == [
        {"name": "r389_reference_tol_1e-4", "tds_tolerance": 1.0e-4},
        {"name": "sensitivity_tol_1e-6", "tds_tolerance": 1.0e-6},
    ]
    assert contract["trajectory_count"] == 0
    assert contract["post_init_actions_authorized"] is False
    assert contract["training_authorized"] is False
    assert contract["positive_real_tolerance"] == 1.0e-7
    assert contract["eig_source_sha256"] == (
        "10a97879f0b3f15a59dc51f1ab6a6bd9a6f7ac6e7ada0337949af78e07ef5707"
    )
    assert contract["pll2_source_sha256"] == (
        "ee147a79fcc7e375c67ccf885ccc0f97b6dca3a2490e2ead71afccb5b2f9081f"
    )
    assert contract["numpy_version"] == "2.4.3"
    assert contract["scipy_version"] == "1.17.1"
    assert contract["system_source_sha256"] == (
        "b6aa12d10811a5b35e0d5939c309d3414713daff4f5d30f2b9063e0d518080c9"
    )
    assert contract["tds_source_sha256"] == (
        "224ff43d78de8e6808efa0a6b858d8dbe2ca511128a90a8260009c8146d6e8ba"
    )
    assert contract["dae_source_sha256"] == (
        "c702f8634b719b3fcaffc80efb60f5a572f06d5df9197e3d87e7400b0d5c45b1"
    )
    assert contract["r389_parent_sha256"]["formal_manifest"] == (
        "5e109995295d6dca573fe45f776556b772fb1a9fb9c192020b68bc9cc42ef43d"
    )


def test_valid_reproducible_nonpositive_spectrum_is_eig_eligible_only() -> None:
    analysis = classify_regf2_equilibrium_eig_record(_record())

    assert analysis["classification"] == (
        "REGF2-EIG-ELIGIBLE-NO-POSITIVE-REAL-MODE"
    )
    assert analysis["positive_real_count"] == 0
    assert analysis["post_init_actions_authorized"] is False
    assert analysis["training_authorized"] is False


def test_valid_equilibrium_with_unreconciled_spectrum_stops_as_numerical() -> None:
    record = _record()
    record["arms"][0]["matrix"]["andes_eigenvalues"][0]["real"] = 999.0

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == (
        "STOP-REGF2-SPECTRUM-NUMERICALLY-UNRESOLVED"
    )


def test_reproducible_positive_real_mode_is_scientific_stop_not_invalid() -> None:
    record = _record()
    for arm in record["arms"]:
        arm["matrix"]["as"][0][0] = 0.5
        arm["matrix"]["andes_eigenvalues"][0]["real"] = 0.5

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "STOP-REGF2-POSITIVE-REAL-GUARD"
    assert analysis["positive_real_count"] == 1
    assert analysis["checks"]["arm_integrity"] is True


def test_missing_registered_state_binding_is_analysis_invalid() -> None:
    record = _record()
    record["arms"][0]["matrix"]["state_bindings"].pop()

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_noncanonical_supplied_contract_is_analysis_invalid() -> None:
    record = _record()
    forged = build_regf2_equilibrium_eig_contract()
    forged["positive_real_tolerance"] = 0.0

    analysis = classify_regf2_equilibrium_eig_record(record, forged)

    assert analysis["classification"] == "ANALYSIS-INVALID"
    assert analysis["checks"]["canonical_contract"] is False


def test_installed_eig_source_drift_is_analysis_invalid() -> None:
    record = _record()
    record["arms"][1]["source"]["eig_source_sha256"] = "0" * 64

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_eig_time_or_state_advance_is_equilibrium_stop() -> None:
    record = _record()
    record["arms"][0]["solver"]["state_max_abs_delta"] = 1.0e-6

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_cross_arm_positive_count_disagreement_is_numerical_stop() -> None:
    record = _record()
    record["arms"][1]["matrix"]["as"][0][0] = 0.5
    record["arms"][1]["matrix"]["andes_eigenvalues"][0]["real"] = 0.5

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == (
        "STOP-REGF2-SPECTRUM-NUMERICALLY-UNRESOLVED"
    )


def test_complete_pflow_failure_is_scientific_equilibrium_stop() -> None:
    record = _record()
    arm = record["arms"][0]
    arm["scientific_error"] = "PFlow did not converge"
    arm["solver"].update(
        pflow_converged=False,
        tds_initialized=False,
        tds_test_ok=False,
        eig_return=False,
        time_before_eig=0.0,
        time_after_eig=0.0,
        state_max_abs_delta=0.0,
    )
    arm["references"] = {
        "phase": None,
        "checked": False,
        "absolute_tolerance": 1.0e-12,
        "rows": [],
    }
    arm["finite_guard"].update(
        dae_finite=False,
        jacobian_finite=False,
        state_matrix_finite=False,
    )
    arm["matrix"] = _empty_matrix()
    arm["equilibrium_snapshot"] = _empty_snapshot()

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "STOP-REGF2-EQUILIBRIUM-INVALID"


@pytest.mark.parametrize(
    ("tds_initialized", "tds_test_ok"), ((True, False), (False, True))
)
def test_each_independent_init_flag_failure_is_scientific_stop(
    tds_initialized: bool, tds_test_ok: bool
) -> None:
    record = _record()
    arm = record["arms"][0]
    arm["scientific_error"] = "TDS initialization failed"
    arm["solver"].update(
        tds_initialized=tds_initialized,
        tds_test_ok=tds_test_ok,
        eig_return=False,
        time_before_eig=0.0,
        time_after_eig=0.0,
        state_max_abs_delta=0.0,
    )
    arm["matrix"] = _empty_matrix()
    arm["equilibrium_snapshot"] = _empty_snapshot()

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "STOP-REGF2-EQUILIBRIUM-INVALID"


def test_polluted_pflow_failure_matrix_is_analysis_invalid() -> None:
    record = _record()
    arm = record["arms"][0]
    arm["scientific_error"] = "PFlow did not converge"
    arm["solver"].update(
        pflow_converged=False,
        tds_initialized=False,
        tds_test_ok=False,
        eig_return=False,
        time_before_eig=0.0,
        time_after_eig=0.0,
        state_max_abs_delta=0.0,
    )
    arm["references"] = {
        "phase": None,
        "checked": False,
        "absolute_tolerance": 1.0e-12,
        "rows": [],
    }
    arm["matrix"]["captured"] = False

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_nonzero_system_exit_code_is_equilibrium_stop() -> None:
    record = _record()
    record["arms"][0]["solver"]["system_exit_code"] = 1

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "STOP-REGF2-EQUILIBRIUM-INVALID"


def test_complete_eig_calculation_failure_is_numerical_stop() -> None:
    record = _record()
    arm = record["arms"][0]
    arm["scientific_error"] = "EIG calculation failed"
    arm["solver"]["eig_return"] = False
    arm["finite_guard"]["state_matrix_finite"] = False
    arm["matrix"] = _failed_matrix(arm)

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == (
        "STOP-REGF2-SPECTRUM-NUMERICALLY-UNRESOLVED"
    )


def test_eig_failure_with_consistent_state_advance_is_equilibrium_stop() -> None:
    record = _record()
    arm = record["arms"][0]
    arm["scientific_error"] = "EIG calculation failed"
    arm["solver"]["eig_return"] = False
    arm["finite_guard"]["state_matrix_finite"] = False
    arm["equilibrium_snapshot"]["after"]["x"][0] = 0.25
    arm["solver"]["state_max_abs_delta"] = 0.25
    arm["matrix"] = _failed_matrix(arm)

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "STOP-REGF2-EQUILIBRIUM-INVALID"


def test_eig_failure_with_complete_bad_residual_is_equilibrium_stop() -> None:
    record = _record()
    arm = record["arms"][0]
    arm["scientific_error"] = "EIG calculation failed"
    arm["solver"]["eig_return"] = False
    arm["finite_guard"]["state_matrix_finite"] = False
    arm["initialization_diagnostics"].update(
        bad_combined_indices=[1],
        residual_count=1,
        residuals=[
            {
                "combined_index": 1,
                "name": "residual REGF2 REGF2_1",
                "residual": 0.1,
                "equation": "registered residual",
                "model": "REGF2",
                "idx": "REGF2_1",
            }
        ],
    )
    arm["matrix"] = _failed_matrix(arm)

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "STOP-REGF2-EQUILIBRIUM-INVALID"


def test_forged_folded_binding_that_remains_reduced_is_analysis_invalid() -> None:
    record = _record()
    matrix = record["arms"][0]["matrix"]
    binding = matrix["state_bindings"][0]
    binding["status"] = "folded"
    binding["reduced_index"] = None
    matrix["zero_tf_state_names"] = [binding["dae_name"]]

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_subpicosecond_time_advance_is_equilibrium_stop() -> None:
    record = _record()
    arm = record["arms"][0]
    arm["equilibrium_snapshot"]["after"]["time"] = 5.0e-13
    arm["solver"]["time_after_eig"] = 5.0e-13

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "STOP-REGF2-EQUILIBRIUM-INVALID"


def test_scalar_delta_cannot_hide_archived_state_change() -> None:
    record = _record()
    arm = record["arms"][0]
    arm["equilibrium_snapshot"]["after"]["x"][0] = 1.0
    arm["solver"]["state_max_abs_delta"] = 0.0

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_forged_dae_catalog_name_is_analysis_invalid() -> None:
    record = _record()
    matrix = record["arms"][0]["matrix"]
    forged = "forged REGF2 REGF2_1"
    matrix["dae_state_catalog"][0]["name"] = forged
    matrix["state_names"][0] = forged
    matrix["state_bindings"][0]["dae_name"] = forged

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_dead_algebraic_index_must_resolve_in_archived_catalog() -> None:
    record = _record()
    record["arms"][0]["matrix"]["dead_algebraic_indices"] = [999999]

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_cross_arm_state_catalog_mismatch_is_analysis_invalid() -> None:
    record = _record()
    arm = record["arms"][1]
    arm["matrix"]["dae_state_catalog"][0]["name"] = "other REGF2 REGF2_1"
    arm["matrix"]["state_names"][0] = "other REGF2 REGF2_1"
    arm["matrix"]["state_bindings"][0]["dae_name"] = "other REGF2 REGF2_1"

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_actual_tolerance_readback_must_match_frozen_arm() -> None:
    record = _record()
    record["arms"][1]["solver"]["actual_tds_tolerance"] = 1.0e-4

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_nonmapping_arm_is_analysis_invalid_not_exception() -> None:
    record = _record()
    record["arms"][0] = "malformed"

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_tied_conjugate_leading_set_reproduces_independent_of_mode_order() -> None:
    record = _record()
    for arm_index, frequencies in enumerate(((1.0, 2.0), (2.0, 1.0))):
        arm = record["arms"][arm_index]
        matrix = np.asarray(arm["matrix"]["as"], dtype=float)
        for offset, frequency in zip((0, 2), frequencies, strict=True):
            matrix[offset : offset + 2, offset : offset + 2] = [
                [-0.5, -frequency],
                [frequency, -0.5],
            ]
        values = np.linalg.eigvals(matrix)
        arm["matrix"]["as"] = matrix.tolist()
        arm["matrix"]["andes_eigenvalues"] = [
            {"real": float(value.real), "imag": float(value.imag)}
            for value in values
        ]

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == (
        "REGF2-EIG-ELIGIBLE-NO-POSITIVE-REAL-MODE"
    )


def test_registered_nonzero_tf_constraint_eliminated_state_is_representable() -> None:
    record = _record()
    for arm in record["arms"]:
        matrix_record = arm["matrix"]
        matrix = np.asarray(matrix_record["as"], dtype=float)[1:, 1:]
        matrix_record["as"] = matrix.tolist()
        matrix_record["state_names"].pop(0)
        matrix_record["andes_eigenvalues"].pop(0)
        first = matrix_record["state_bindings"][0]
        first["status"] = "eliminated"
        first["reduced_index"] = None
        for binding in matrix_record["state_bindings"][1:]:
            binding["reduced_index"] -= 1

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == (
        "REGF2-EIG-ELIGIBLE-NO-POSITIVE-REAL-MODE"
    )


def test_cross_arm_extra_stable_state_and_dimension_is_analysis_invalid() -> None:
    record = _record()
    arm = record["arms"][1]
    matrix_record = arm["matrix"]
    matrix = np.asarray(matrix_record["as"], dtype=float)
    expanded = np.zeros((len(matrix) + 1, len(matrix) + 1), dtype=float)
    expanded[:-1, :-1] = matrix
    expanded[-1, -1] = -999.0
    matrix_record["as"] = expanded.tolist()
    matrix_record["state_names"].append("extra Other OTHER_1")
    matrix_record["andes_eigenvalues"].append({"real": -999.0, "imag": 0.0})
    matrix_record["dae_state_catalog"].append(
        {
            "address": len(matrix_record["dae_state_catalog"]),
            "name": "extra Other OTHER_1",
            "tf": 1.0,
        }
    )
    for phase in ("before", "after"):
        arm["equilibrium_snapshot"][phase]["x"].append(0.0)
        arm["equilibrium_snapshot"][phase]["f"].append(0.0)

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_dead_index_in_folded_augmented_algebraic_tail_is_valid() -> None:
    record = _record()
    _add_zero_tf_folded_tail(record)

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == (
        "REGF2-EIG-ELIGIBLE-NO-POSITIVE-REAL-MODE"
    )


def test_forged_augmented_algebraic_order_is_analysis_invalid() -> None:
    record = _record()
    _add_zero_tf_folded_tail(record)
    for arm in record["arms"]:
        arm["matrix"]["eig_augmented_algebraic_names"].reverse()

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_failed_eig_arm_with_forged_dae_catalog_is_analysis_invalid() -> None:
    record = _record()
    arm = record["arms"][0]
    arm["scientific_error"] = "EIG calculation failed"
    arm["solver"]["eig_return"] = False
    arm["finite_guard"]["state_matrix_finite"] = False
    arm["matrix"] = _failed_matrix(arm)
    arm["matrix"]["dae_state_catalog"][0]["name"] = "forged Other OTHER_1"

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_failed_eig_arm_with_duplicate_dae_name_is_analysis_invalid() -> None:
    record = _record()
    arm = record["arms"][0]
    arm["scientific_error"] = "EIG calculation failed"
    arm["solver"]["eig_return"] = False
    arm["finite_guard"]["state_matrix_finite"] = False
    arm["matrix"] = _failed_matrix(arm)
    arm["matrix"]["dae_state_catalog"][1]["name"] = arm["matrix"][
        "dae_state_catalog"
    ][0]["name"]

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_truncated_discrete_vector_is_analysis_invalid() -> None:
    record = _record()
    for arm in record["arms"]:
        for phase in ("before", "after"):
            arm["equilibrium_snapshot"][phase]["z"] = []

    analysis = classify_regf2_equilibrium_eig_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"
