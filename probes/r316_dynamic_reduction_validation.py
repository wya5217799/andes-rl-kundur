"""R316 guard-repair view over the otherwise frozen R315 validation logic.

The only semantic change is the achieved-power treatment on vector elements
whose requested power is zero. Command-path fields are not normalized and
remain subject to the original 1e-12 checks.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy

import numpy as np

from probes import r315_dynamic_reduction_validation as R315_BASE


def normalize_achieved_power_residue(
    requested_power: object,
    achieved_power: object,
    *,
    zero_request_tolerance: float,
) -> np.ndarray:
    """Zero only achieved-power solver residue under a prospective bound."""

    requested = np.asarray(requested_power, dtype=float)
    achieved = np.asarray(achieved_power, dtype=float)
    tolerance = float(zero_request_tolerance)
    if (
        requested.shape != (4,)
        or achieved.shape != requested.shape
        or not np.all(np.isfinite(requested))
        or not np.all(np.isfinite(achieved))
        or not np.isfinite(tolerance)
        or tolerance <= 0.0
    ):
        raise ValueError("requested/achieved power and tolerance are invalid")
    zero = np.abs(requested) <= R315_BASE.ZERO_TOLERANCE
    if np.any(np.abs(achieved[zero]) > tolerance):
        raise ValueError("zero-request achieved-power residue exceeds the bound")
    normalized = achieved.copy()
    normalized[zero] = 0.0
    return normalized


def _guard_view(
    record: Mapping[str, object],
    *,
    zero_request_tolerance: float,
) -> dict[str, object]:
    """Build an ephemeral view accepted by the unchanged R315 guard logic."""

    view = deepcopy(dict(record))
    if record.get("round") == "R316" and record.get("question") == "Q-0071":
        view["round"] = "R315"
    else:
        view["round"] = "invalid-source-identity"
    rows = view.get("traces")
    if not isinstance(rows, list):
        return view
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            row["bess_actual_power_system_pu"] = normalize_achieved_power_residue(
                row["bess_requested_power_system_pu"],
                row["bess_actual_power_system_pu"],
                zero_request_tolerance=zero_request_tolerance,
            ).tolist()
        except (KeyError, TypeError, ValueError):
            # Leave an invalid source untouched so the inherited validator fails.
            pass
    return view


def evaluate_dynamic_reduction_validation(
    records: Sequence[Mapping[str, object]],
    model: Mapping[str, object],
    eval_scorecard: Mapping[str, object],
    contract: Mapping[str, object],
    *,
    expected_seal_sha256: str,
    expected_model_sha256: str,
    model_provenance_valid: bool,
) -> dict[str, object]:
    """Apply the R316 single-factor guard repair and frozen scientific gates."""

    repair = contract.get("execution_guard_repair")
    if not isinstance(repair, Mapping):
        raise ValueError("R316 execution guard repair is missing")
    tolerance = float(repair["zero_request_achieved_power_abs_max_system_pu"])
    source_identity_valid = all(
        record.get("round") == "R316" and record.get("question") == "Q-0071"
        for record in records
    )
    model_identity_valid = bool(
        model.get("round") == "R316"
        and model.get("question") == "Q-0071"
        and model.get("R315_holdout_used_for_fitting") is False
        and model.get("R316_holdout_accessed") is False
    )
    views = [
        _guard_view(record, zero_request_tolerance=tolerance) for record in records
    ]
    model_view = deepcopy(dict(model))
    model_view["round"] = "R315" if model_identity_valid else "invalid-model-identity"
    model_view["R315_holdout_accessed"] = False
    result = R315_BASE.evaluate_dynamic_reduction_validation(
        views,
        model_view,
        eval_scorecard,
        contract,
        expected_seal_sha256=expected_seal_sha256,
        expected_model_sha256=expected_model_sha256,
        model_provenance_valid=bool(
            model_provenance_valid and model_identity_valid
        ),
    )
    execution_guards = result.get("execution_guards")
    if isinstance(execution_guards, dict):
        execution_guards["original_R316_record_identity"] = source_identity_valid
        execution_guards["original_R316_model_identity"] = model_identity_valid
    if not source_identity_valid or not model_identity_valid:
        result["classification"] = "INVALID-DYNAMIC-REDUCTION-VALIDATION"
        result["metric_guards"] = None
        result["metric_summary"] = None
        result["cases"] = []
        result["claim_ceiling"] = "invalid-no-model-effect-interpretation"
    result["execution_guard_repair"] = {
        "zero_request_achieved_power_abs_max_system_pu": tolerance,
        "normalized_field": "bess_actual_power_system_pu-only",
        "command_path_normalized": False,
        "base_validator": "R315-frozen-except-round-identity-view",
    }
    return result
