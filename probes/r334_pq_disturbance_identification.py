"""R334 identity and reward-boundary correction around the R333 classifier.

The scientific bank and decision rules remain in the immutable R333 probe.
This module validates the new round identity and diagnostic-reward contract,
then changes only round labels in deep-copied payloads before delegation.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from probes.r333_pq_disturbance_identification import (
    analyse_pq_disturbance_identification,
)


def _translate_identity_only(
    run: Mapping[str, Any],
    sealed: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return R333-compatible copies without changing scientific content."""

    translated_run = copy.deepcopy(dict(run))
    translated_sealed = copy.deepcopy(dict(sealed))
    translated_run["round"] = "R333"
    records = translated_run.get("records")
    if isinstance(records, list):
        for record in records:
            if isinstance(record, dict):
                record["round"] = "R333"
    translated_sealed["round"] = "R333"
    return translated_run, translated_sealed


def _reward_boundary_valid(
    run: Mapping[str, Any],
    sealed: Mapping[str, Any],
) -> bool:
    expected = {
        "reward_diagnostics_computed": True,
        "reward_diagnostics_stored": True,
        "reward_used_for_action": False,
        "reward_used_for_fitting": False,
        "reward_used_for_selection": False,
        "reward_used_for_training": False,
        "reward_used_for_classification": False,
        "reward_used_for_claim": False,
    }
    if sealed.get("reward_boundary") != expected:
        return False
    if any(run.get(key) is not value for key, value in expected.items()):
        return False
    records = run.get("records")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return False
    if len(records) != 6:
        return False
    for record in records:
        if not isinstance(record, Mapping):
            return False
        if any(record.get(key) is not value for key, value in expected.items()):
            return False
    return True


def analyse_r334_pq_disturbance_identification(
    run: Mapping[str, Any],
    sealed: Mapping[str, Any],
    *,
    expected_seal_sha256: str,
    expected_dynamic_model_sha256: str,
    expected_coordinate_inputs: Mapping[str, Mapping[str, object]],
    expected_predictions: Mapping[str, Mapping[str, object]],
    evidence_chain_valid: bool,
) -> dict[str, Any]:
    """Validate R334 corrections and delegate unchanged scientific rules."""

    records = run.get("records")
    record_identity = bool(
        isinstance(records, Sequence)
        and not isinstance(records, (str, bytes))
        and len(records) == 6
        and all(
            isinstance(record, Mapping)
            and record.get("round") == "R334"
            and record.get("question") == "Q-0085"
            for record in records
        )
    )
    r334_identity = bool(
        run.get("round") == sealed.get("round") == "R334"
        and run.get("question") == sealed.get("question") == "Q-0085"
        and evidence_chain_valid is True
        and record_identity
    )
    reward_boundary = _reward_boundary_valid(run, sealed)
    if not r334_identity or not reward_boundary:
        failed = {
            "r334_identity": r334_identity,
            "reward_diagnostic_boundary": reward_boundary,
        }
        return {
            "classification": "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION",
            "validity_guards": {**failed, "all": False},
            "identification_guards": {
                "physical_channel_observable": None,
                "load_sign_correct": None,
                "paired_local_linearity": None,
                "frozen_channel_equivalence": None,
                "all": None,
            },
            "record_metrics": [],
            "point_metrics": [],
            "invalid_reasons": [name for name, passed in failed.items() if not passed],
            "blocking_reasons": [],
            "scope": {
                "identified_physical_channel_count": 0,
                "identified_device": sealed.get("device_idx"),
                "successor_package_required": True,
                "controller_authorized": False,
                "distributed_agent_authorized": False,
                "training_authorized": False,
                "eval_executed": False,
                "reward_diagnostics_computed": bool(
                    run.get("reward_diagnostics_computed") is True
                ),
                "reward_diagnostics_stored": bool(
                    run.get("reward_diagnostics_stored") is True
                ),
                "reward_used_for_scientific_decision": False,
                "paired_local_linearity_guard_interpretation": (
                    "registered-signed-pair-approximate-odd-symmetry-only"
                ),
                "local_or_global_linearity_authorized": False,
                "claim_ceiling": (
                    "one Bus14 active-load channel, one amplitude and waveform, "
                    "two operating points, phasor-domain electromechanical only"
                ),
            },
        }
    translated_run, translated_sealed = _translate_identity_only(run, sealed)
    result = analyse_pq_disturbance_identification(
        translated_run,
        translated_sealed,
        expected_seal_sha256=expected_seal_sha256,
        expected_dynamic_model_sha256=expected_dynamic_model_sha256,
        expected_coordinate_inputs=expected_coordinate_inputs,
        expected_predictions=expected_predictions,
        evidence_chain_valid=evidence_chain_valid,
    )
    validity = dict(result["validity_guards"])
    validity["r334_identity"] = r334_identity
    validity["reward_diagnostic_boundary"] = reward_boundary
    validity["all"] = bool(
        r334_identity
        and reward_boundary
        and all(
            passed
            for name, passed in validity.items()
            if name not in {"all", "r334_identity", "reward_diagnostic_boundary"}
        )
    )
    result["validity_guards"] = validity
    scope = dict(result["scope"])
    scope.update(
        {
            "reward_diagnostics_computed": bool(
                run.get("reward_diagnostics_computed") is True
            ),
            "reward_diagnostics_stored": bool(
                run.get("reward_diagnostics_stored") is True
            ),
            "reward_used_for_scientific_decision": False,
            "paired_local_linearity_guard_interpretation": (
                "registered-signed-pair-approximate-odd-symmetry-only"
            ),
            "local_or_global_linearity_authorized": False,
        }
    )
    result["scope"] = scope
    if validity["all"]:
        result["invalid_reasons"] = []
        return result

    result["classification"] = "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION"
    result["identification_guards"] = {
        "physical_channel_observable": None,
        "load_sign_correct": None,
        "paired_local_linearity": None,
        "frozen_channel_equivalence": None,
        "all": None,
    }
    result["record_metrics"] = []
    result["point_metrics"] = []
    result["blocking_reasons"] = []
    result["invalid_reasons"] = [
        name for name, passed in validity.items() if name != "all" and not passed
    ]
    result["scope"]["identified_physical_channel_count"] = 0
    return result
