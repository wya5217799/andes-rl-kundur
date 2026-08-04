from __future__ import annotations

import numpy as np
from probes.r335_disturbance_package import (
    analyse_r335_disturbance_package,
    fit_r335_disturbance_map,
)

CHANNELS = ("load_0", "load_1", "load_2", "load_3")
SHAPES = {"impulse": (0.05,), "triangle": (0.02, 0.04, 0.05, 0.04, 0.02)}
TOTAL_STEPS = 6
NODE_BASIS = np.asarray(
    [
        [1.0, 1.0, 0.0, 0.0],
        [1.0, -1.0, 1.0, 0.0],
        [1.0, 0.0, -1.0, 1.0],
        [1.0, 0.0, 0.0, -1.0],
    ]
)
EXPECTED_MAP = np.linalg.solve(NODE_BASIS, -np.eye(4))
REWARD_BOUNDARY = {
    "reward_diagnostics_computed": True,
    "reward_diagnostics_stored": True,
    "reward_used_for_action": False,
    "reward_used_for_fitting": False,
    "reward_used_for_selection": False,
    "reward_used_for_training": False,
    "reward_used_for_classification": False,
    "reward_used_for_claim": False,
}


def _identity_realization() -> dict[str, object]:
    return {
        "state_matrix": np.zeros((4, 4)).tolist(),
        "input_matrix": np.zeros((4, 4)).tolist(),
        "output_matrix": np.zeros((4, 4)).tolist(),
        "feedthrough_matrix": np.eye(4).tolist(),
        "spectral_radius": 0.0,
        "retained_singular_values": [1.0, 1.0, 1.0, 1.0],
    }


def test_fit_recovers_one_cross_coupled_map_without_holdout_records() -> None:
    records: list[dict[str, object]] = [
        {
            "operating_point": "HS0",
            "channel": "zero",
            "shape": "zero",
            "sign": "zero",
            "output_coordinates": np.zeros((TOTAL_STEPS, 4)).tolist(),
        }
    ]
    for column, channel in enumerate(CHANNELS):
        for shape, active in SHAPES.items():
            profile = np.zeros(TOTAL_STEPS)
            profile[: len(active)] = active
            response = profile[:, None] * EXPECTED_MAP[:, column][None, :]
            for sign, multiplier in (("positive", 1.0), ("negative", -1.0)):
                records.append(
                    {
                        "operating_point": "HS0",
                        "channel": channel,
                        "shape": shape,
                        "sign": sign,
                        "output_coordinates": (multiplier * response).tolist(),
                    }
                )

    fit = fit_r335_disturbance_map(
        contract={
            "development_point": "HS0",
            "channels": list(CHANNELS),
            "shapes": {name: list(values) for name, values in SHAPES.items()},
            "total_steps": TOTAL_STEPS,
        },
        development_records=records,
        realization_payload=_identity_realization(),
    )

    np.testing.assert_allclose(fit["coordinate_map"], EXPECTED_MAP, atol=1e-12)
    assert fit["holdout_records_accessed"] is False
    assert fit["fit_record_count"] == 16


def test_fit_rejects_duplicate_development_record() -> None:
    records = _formal_records("HS0")
    records.append(dict(records[1]))

    with np.testing.assert_raises_regex(ValueError, "duplicate development"):
        fit_r335_disturbance_map(
            contract={
                "development_point": "HS0",
                "channels": list(CHANNELS),
                "shapes": {name: list(values) for name, values in SHAPES.items()},
                "total_steps": TOTAL_STEPS,
            },
            development_records=records,
            realization_payload=_identity_realization(),
        )


def _formal_records(
    point: str, *, coordinate_map: np.ndarray = EXPECTED_MAP
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = [
        {
            "round": "R335",
            "question": "Q-0086",
            "operating_point": point,
            "channel": "zero",
            "shape": "zero",
            "sign": "zero",
            "output_coordinates": np.zeros((TOTAL_STEPS, 4)).tolist(),
            "record_valid": True,
            **REWARD_BOUNDARY,
        }
    ]
    for column, channel in enumerate(CHANNELS):
        for shape, active in SHAPES.items():
            profile = np.zeros(TOTAL_STEPS)
            profile[: len(active)] = active
            response = profile[:, None] * coordinate_map[:, column][None, :]
            for sign, multiplier in (("positive", 1.0), ("negative", -1.0)):
                records.append(
                    {
                        "round": "R335",
                        "question": "Q-0086",
                        "operating_point": point,
                        "channel": channel,
                        "shape": shape,
                        "sign": sign,
                        "output_coordinates": (multiplier * response).tolist(),
                        "record_valid": True,
                        **REWARD_BOUNDARY,
                    }
                )
    return records


def test_analysis_allows_full_rank_cross_coupled_map_on_untouched_point() -> None:
    contract = {
        "round": "R335",
        "question": "Q-0086",
        "development_point": "HS0",
        "holdout_point": "HS1",
        "channels": list(CHANNELS),
        "shapes": {name: list(values) for name, values in SHAPES.items()},
        "total_steps": TOTAL_STEPS,
        "node_input_basis": NODE_BASIS.tolist(),
        "thresholds": {
            "signal_to_baseline_drift_energy_ratio_minimum": 10.0,
            "pair_midpoint_nonlinearity_ratio_maximum": 0.10,
            "total_nrmse_maximum": 0.15,
            "peak_vector_residual_maximum": 0.20,
            "node_power_sum_absolute_error_maximum": 0.20,
            "singular_value_ratio_minimum": 0.10,
        },
    }
    development = _formal_records("HS0")
    fit = fit_r335_disturbance_map(
        contract=contract,
        development_records=development,
        realization_payload=_identity_realization(),
    )
    fit.update(
        {
            "round": "R335",
            "question": "Q-0086",
            "fit_created_before_holdout": True,
        }
    )

    analysis = analyse_r335_disturbance_package(
        contract=contract,
        development_records=development,
        holdout_records=_formal_records("HS1"),
        fit_payload=fit,
        realization_payloads={
            "HS0": _identity_realization(),
            "HS1": _identity_realization(),
        },
        execution_validity={"all_guards_pass": True},
    )

    assert analysis["classification"] == "ALLOW"
    assert all(analysis["identification_guards"].values())
    assert analysis["package_metrics"]["rank"] == 4
    assert analysis["package_metrics"]["singular_value_ratio"] == 1.0
    assert analysis["holdout_used_for_fitting"] is False


def test_analysis_invalidates_any_reward_boundary_violation() -> None:
    contract, development, fit = _valid_inputs()
    holdout = _formal_records("HS1")
    holdout[1]["reward_used_for_classification"] = True

    analysis = analyse_r335_disturbance_package(
        contract=contract,
        development_records=development,
        holdout_records=holdout,
        fit_payload=fit,
        realization_payloads={
            "HS0": _identity_realization(),
            "HS1": _identity_realization(),
        },
        execution_validity={"all_guards_pass": True},
    )

    assert analysis["classification"] == "INVALID-PHYSICAL-DISTURBANCE-PACKAGE"
    assert analysis["validity_guards"]["reward_boundary"] is False


def test_analysis_returns_invalid_for_incomplete_inventory_without_metrics() -> None:
    contract, development, fit = _valid_inputs()

    analysis = analyse_r335_disturbance_package(
        contract=contract,
        development_records=development,
        holdout_records=_formal_records("HS1")[:-1],
        fit_payload=fit,
        realization_payloads={
            "HS0": _identity_realization(),
            "HS1": _identity_realization(),
        },
        execution_validity={"all_guards_pass": True},
    )

    assert analysis["classification"] == "INVALID-PHYSICAL-DISTURBANCE-PACKAGE"
    assert analysis["validity_guards"]["strict_inventory"] is False
    assert analysis["record_metrics"] == {}


def test_analysis_blocks_an_untouched_point_prediction_failure() -> None:
    contract, development, fit = _valid_inputs()
    holdout = _formal_records("HS1")
    for row in holdout[1:]:
        row["output_coordinates"] = (
            2.0 * np.asarray(row["output_coordinates"], dtype=float)
        ).tolist()

    analysis = analyse_r335_disturbance_package(
        contract=contract,
        development_records=development,
        holdout_records=holdout,
        fit_payload=fit,
        realization_payloads={
            "HS0": _identity_realization(),
            "HS1": _identity_realization(),
        },
        execution_validity={"all_guards_pass": True},
    )

    assert analysis["classification"] == "BLOCK"
    assert analysis["identification_guards"]["untouched_holdout_within_envelope"] is False


def test_analysis_qualifies_rank_deficient_but_well_predicted_package() -> None:
    node_map = -np.eye(4)
    node_map[:, 3] = node_map[:, 2]
    coordinate_map = np.linalg.solve(NODE_BASIS, node_map)
    contract = _contract()
    development = _formal_records("HS0", coordinate_map=coordinate_map)
    fit = fit_r335_disturbance_map(
        contract=contract,
        development_records=development,
        realization_payload=_identity_realization(),
    )
    fit.update(
        {
            "round": "R335",
            "question": "Q-0086",
            "fit_created_before_holdout": True,
        }
    )

    analysis = analyse_r335_disturbance_package(
        contract=contract,
        development_records=development,
        holdout_records=_formal_records("HS1", coordinate_map=coordinate_map),
        fit_payload=fit,
        realization_payloads={
            "HS0": _identity_realization(),
            "HS1": _identity_realization(),
        },
        execution_validity={"all_guards_pass": True},
    )

    assert analysis["classification"] == "QUALIFY"
    assert analysis["identification_guards"]["full_rank_conditioned_coverage"] is False
    assert analysis["package_metrics"]["rank"] == 3


def _contract() -> dict[str, object]:
    return {
        "round": "R335",
        "question": "Q-0086",
        "development_point": "HS0",
        "holdout_point": "HS1",
        "channels": list(CHANNELS),
        "shapes": {name: list(values) for name, values in SHAPES.items()},
        "total_steps": TOTAL_STEPS,
        "node_input_basis": NODE_BASIS.tolist(),
        "thresholds": {
            "signal_to_baseline_drift_energy_ratio_minimum": 10.0,
            "pair_midpoint_nonlinearity_ratio_maximum": 0.10,
            "total_nrmse_maximum": 0.15,
            "peak_vector_residual_maximum": 0.20,
            "node_power_sum_absolute_error_maximum": 0.20,
            "singular_value_ratio_minimum": 0.10,
        },
    }


def _valid_inputs() -> tuple[dict[str, object], list[dict[str, object]], dict[str, object]]:
    contract = _contract()
    development = _formal_records("HS0")
    fit = fit_r335_disturbance_map(
        contract=contract,
        development_records=development,
        realization_payload=_identity_realization(),
    )
    fit.update(
        {
            "round": "R335",
            "question": "Q-0086",
            "fit_created_before_holdout": True,
        }
    )
    return contract, development, fit
