"""Pure nominal pole-cause diagnostics and formal R320 classifier.

The module operates only on already sealed matrices or machine summaries. It
runs no disturbance case, physical simulator, EVAL profile, or performance
comparison and cannot repair a controller after outcomes are visible.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np


EXPECTED_VALIDITY_GUARDS = {
    "sealed_parent_identity",
    "matrix_gain_contract",
    "deterministic_replay",
    "failed_mode_contract",
    "no_performance_access",
    "placement_contract",
    "eval_not_run",
}
EXPECTED_MODELS = {
    "retained_cross/HS0",
    "retained_cross/HS1",
    "cross_deleted/HS0",
    "cross_deleted/HS1",
}
RADIUS_IDENTITY_TOLERANCE = 1.0e-12
STRUCTURAL_MARGIN = 1.0e-10
PLACEMENT_ERROR_TOLERANCE = 1.0e-8
CONTROLLER_TARGET_RADIUS = 0.98
OBSERVER_TARGET_RADIUS = 0.94


def _state_and_channel(
    state_matrix: object,
    channel_matrix: object,
    *,
    kind: str,
) -> tuple[np.ndarray, np.ndarray]:
    state = np.asarray(state_matrix, dtype=float)
    channel = np.asarray(channel_matrix, dtype=float)
    order = state.shape[0] if state.ndim == 2 else 0
    valid_channel = (
        channel.ndim == 2
        and ((kind == "control" and channel.shape[0] == order)
             or (kind == "observe" and channel.shape[1] == order))
    )
    if (
        order < 1
        or state.shape != (order, order)
        or not valid_channel
        or not np.all(np.isfinite(state))
        or not np.all(np.isfinite(channel))
    ):
        raise ValueError("state and channel matrices are finite and dimensionally consistent")
    return state, channel


def controllability_matrix(state_matrix: object, input_matrix: object) -> np.ndarray:
    """Return ``[B, AB, ..., A^(n-1)B]`` for one finite discrete pair."""

    state, inputs = _state_and_channel(
        state_matrix, input_matrix, kind="control"
    )
    blocks = [inputs]
    for _ in range(1, state.shape[0]):
        blocks.append(state @ blocks[-1])
    return np.hstack(blocks)


def observability_matrix(state_matrix: object, output_matrix: object) -> np.ndarray:
    """Return the vertically stacked finite-horizon observability matrix."""

    state, outputs = _state_and_channel(
        state_matrix, output_matrix, kind="observe"
    )
    blocks = [outputs]
    for _ in range(1, state.shape[0]):
        blocks.append(blocks[-1] @ state)
    return np.vstack(blocks)


def normalized_pbh_margin(
    state_matrix: object,
    channel_matrix: object,
    eigenvalue: complex,
    *,
    kind: str,
) -> float:
    """Return the scale-normalized smallest PBH singular value."""

    if kind not in {"control", "observe"}:
        raise ValueError("kind must be 'control' or 'observe'")
    state, channel = _state_and_channel(
        state_matrix, channel_matrix, kind=kind
    )
    value = complex(eigenvalue)
    if not np.isfinite(value.real) or not np.isfinite(value.imag):
        raise ValueError("eigenvalue must be finite")
    shifted = value * np.eye(state.shape[0]) - state
    pbh = (
        np.hstack((shifted, channel))
        if kind == "control"
        else np.vstack((shifted, channel))
    )
    singular_values = np.linalg.svd(pbh, compute_uv=False)
    largest = float(singular_values[0])
    if largest == 0.0:
        return 0.0
    return float(singular_values[-1] / largest)


def _invalid(payload: Mapping[str, object], reason: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": payload.get("round"),
        "question": payload.get("question"),
        "classification": "INVALID-POLE-CAUSE-DIAGNOSIS",
        "invalid_reason": reason,
        "fixed_template_repair_eligible": False,
        "physical_closed_loop_round_eligible": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
        "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
    }


def _optional_margin(value: object, count: int, *, name: str) -> float | None:
    if count == 0:
        if value is not None:
            raise ValueError(f"{name} margin exists without a failed mode")
        return None
    margin = float(value)
    if not np.isfinite(margin) or margin < 0.0:
        raise ValueError(f"{name} margin is invalid")
    return margin


def _model_summary(value: Mapping[str, object], *, name: str) -> dict[str, Any]:
    dimension = int(value.get("state_dimension", -1))
    if dimension < 1:
        raise ValueError(f"{name} state dimension is invalid")
    radii: dict[str, float] = {}
    for field in (
        "stored_controller_pole_radius",
        "recomputed_controller_pole_radius",
        "stored_observer_pole_radius",
        "recomputed_observer_pole_radius",
    ):
        radius = float(value.get(field, float("nan")))
        if not np.isfinite(radius) or radius < 0.0:
            raise ValueError(f"{name} {field} is invalid")
        radii[field] = radius
    controller_count = int(value.get("failed_controller_mode_count", -1))
    observer_count = int(value.get("failed_observer_mode_count", -1))
    if controller_count < 0 or observer_count < 0:
        raise ValueError(f"{name} failed-mode count is invalid")
    controller_margin = _optional_margin(
        value.get("minimum_failed_controller_pbh_margin"),
        controller_count,
        name=f"{name} controller",
    )
    observer_margin = _optional_margin(
        value.get("minimum_failed_observer_pbh_margin"),
        observer_count,
        name=f"{name} observer",
    )
    placement = value.get("placement")
    if not isinstance(placement, Mapping):
        raise ValueError(f"{name} placement summary is missing")
    return {
        "state_dimension": dimension,
        **radii,
        "failed_controller_mode_count": controller_count,
        "failed_observer_mode_count": observer_count,
        "controllability_rank": int(value.get("controllability_rank", -1)),
        "observability_rank": int(value.get("observability_rank", -1)),
        "minimum_failed_controller_pbh_margin": controller_margin,
        "minimum_failed_observer_pbh_margin": observer_margin,
        "placement": dict(placement),
    }


def evaluate_pole_cause(payload: object) -> dict[str, Any]:
    """Classify one immutable R320 nominal pole-cause diagnostic."""

    if not isinstance(payload, Mapping):
        return _invalid({}, "payload is not an object")
    if payload.get("round") != "R320" or payload.get("question") != "Q-0075":
        return _invalid(payload, "round or question identity mismatch")
    validity = payload.get("validity_guards")
    if not isinstance(validity, Mapping) or set(validity) != EXPECTED_VALIDITY_GUARDS:
        return _invalid(payload, "validity guard contract mismatch")
    if not all(value is True for value in validity.values()):
        return _invalid(payload, "one or more validity guards failed")
    models_value = payload.get("models")
    if not isinstance(models_value, Mapping) or set(models_value) != EXPECTED_MODELS:
        return _invalid(payload, "model contract mismatch")
    try:
        models = {
            str(name): _model_summary(value, name=str(name))
            for name, value in models_value.items()
            if isinstance(value, Mapping)
        }
        if set(models) != EXPECTED_MODELS:
            raise ValueError("one or more model summaries are not objects")
    except (TypeError, ValueError) as exc:
        return _invalid(payload, str(exc))

    radius_identity = all(
        abs(
            model["stored_controller_pole_radius"]
            - model["recomputed_controller_pole_radius"]
        )
        <= RADIUS_IDENTITY_TOLERANCE
        and abs(
            model["stored_observer_pole_radius"]
            - model["recomputed_observer_pole_radius"]
        )
        <= RADIUS_IDENTITY_TOLERANCE
        for model in models.values()
    )
    failed_mode_contract = bool(
        sum(model["failed_controller_mode_count"] for model in models.values()) > 0
        and sum(model["failed_observer_mode_count"] for model in models.values()) > 0
    )
    if not radius_identity or not failed_mode_contract:
        return {
            "schema_version": 1,
            "round": "R320",
            "question": "Q-0075",
            "classification": "DIAGNOSTIC-CONFLICT",
            "validity_guards": dict(validity),
            "models": models,
            "radius_identity_passed": radius_identity,
            "failed_mode_contract_passed": failed_mode_contract,
            "fixed_template_repair_eligible": False,
            "physical_closed_loop_round_eligible": False,
            "distributed_agent_implementation_authorized": False,
            "training_authorized": False,
            "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
            "claim_ceiling": "conflict-only-no-pole-cause-interpretation",
        }

    structural_checks = {
        name: {
            "full_controllability_rank": bool(
                model["controllability_rank"] == model["state_dimension"]
            ),
            "full_observability_rank": bool(
                model["observability_rank"] == model["state_dimension"]
            ),
            "failed_controller_pbh_margin": bool(
                model["failed_controller_mode_count"] == 0
                or model["minimum_failed_controller_pbh_margin"]
                >= STRUCTURAL_MARGIN
            ),
            "failed_observer_pbh_margin": bool(
                model["failed_observer_mode_count"] == 0
                or model["minimum_failed_observer_pbh_margin"]
                >= STRUCTURAL_MARGIN
            ),
        }
        for name, model in models.items()
    }
    structural_pass = all(
        all(checks.values()) for checks in structural_checks.values()
    )
    if not structural_pass:
        placement_withheld = all(
            model["placement"].get("attempted") is False
            and model["placement"].get("not_run_reason") == "structural-failure"
            for model in models.values()
        )
        if not placement_withheld:
            return _invalid(payload, "placement ran despite structural failure")
        return {
            "schema_version": 1,
            "round": "R320",
            "question": "Q-0075",
            "classification": "STRUCTURAL-POLE-NO-GO",
            "validity_guards": dict(validity),
            "models": models,
            "structural_checks": structural_checks,
            "fixed_template_repair_eligible": False,
            "physical_closed_loop_round_eligible": False,
            "distributed_agent_implementation_authorized": False,
            "training_authorized": False,
            "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
            "claim_ceiling": "nominal structural pole no-go on four augmented pairs",
        }

    try:
        placement_checks = {
            name: {
                "attempted": placement.get("attempted") is True,
                "finite": placement.get("finite") is True,
                "controller_target_accuracy": bool(
                    float(placement.get("controller_target_max_abs_error", float("inf")))
                    <= PLACEMENT_ERROR_TOLERANCE
                ),
                "observer_target_accuracy": bool(
                    float(placement.get("observer_target_max_abs_error", float("inf")))
                    <= PLACEMENT_ERROR_TOLERANCE
                ),
                "controller_radius": bool(
                    float(placement.get("controller_maximum_radius", float("inf")))
                    <= CONTROLLER_TARGET_RADIUS + PLACEMENT_ERROR_TOLERANCE
                ),
                "observer_radius": bool(
                    float(placement.get("observer_maximum_radius", float("inf")))
                    <= OBSERVER_TARGET_RADIUS + PLACEMENT_ERROR_TOLERANCE
                ),
            }
            for name, model in models.items()
            for placement in (model["placement"],)
        }
    except (TypeError, ValueError):
        return _invalid(payload, "placement metrics are invalid")
    placement_pass = all(
        all(checks.values()) for checks in placement_checks.values()
    )
    classification = (
        "POLE-TARGET-ELIGIBLE" if placement_pass else "TARGET-PLACEMENT-NO-GO"
    )
    return {
        "schema_version": 1,
        "round": "R320",
        "question": "Q-0075",
        "classification": classification,
        "validity_guards": dict(validity),
        "models": models,
        "structural_checks": structural_checks,
        "placement_checks": placement_checks,
        "fixed_template_repair_eligible": placement_pass,
        "physical_closed_loop_round_eligible": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
        "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
        "claim_ceiling": (
            "nominal mathematical eligibility of one fixed pole template on four "
            "augmented pairs"
            if placement_pass
            else "single fixed pole template rejected without target search"
        ),
        "stay_out": [
            "disturbance-rejection efficacy",
            "retained-cross or decoupling value",
            "physical stability, robustness, or safety",
            "distributed execution, agent, or MARL value",
            "topology generalization, HIL, or deployment",
        ],
    }
