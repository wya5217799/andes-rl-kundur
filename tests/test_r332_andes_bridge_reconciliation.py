from __future__ import annotations

from copy import deepcopy

import pytest
from probes.r332_andes_bridge_reconciliation import (
    REQUIRED_MAPPING_IDS,
    evaluate_bridge_reconciliation,
)


def _row(identifier: str, disposition: str = "exact") -> dict[str, object]:
    return {
        "id": identifier,
        "reduced_model_meaning": f"reduced meaning for {identifier}",
        "implementation_locators": [
            "results/r316_dynamic_reduction/dynamic_model.json#/realization_contract"
        ],
        "official_locators": ["https://docs.andes.app/en/v2.0.0/tutorials/04-time-domain.html"],
        "unit": "declared",
        "base": "declared",
        "sign": "declared",
        "sample_time": "declared",
        "disposition": disposition,
        "claim_ceiling_consequence": "phasor-domain simulation only",
    }


def _payload() -> dict[str, object]:
    rows = [_row(identifier) for identifier in sorted(REQUIRED_MAPPING_IDS)]
    rows[-1]["disposition"] = "declared-omission"
    return {
        "schema_version": 1,
        "round": "R332",
        "question": "Q-0084",
        "mapping_rows": rows,
        "source_identity": {
            "repository_sources_match": True,
            "installed_andes_version": "2.0.0",
            "installed_sources_match": True,
            "installed_semantics_match": True,
            "official_sources_primary": True,
        },
        "semantic_guards": {
            "no_hidden_md_write": True,
            "requested_projected_internal_achieved_distinguished": True,
            "active_power_incidence_sign_correct": True,
            "physical_frequency_base_60_hz": True,
            "sample_order_and_delay_explicit": True,
            "disturbance_and_initialization_explicit": True,
            "all_feasibility_limits_explicit": True,
            "reduced_latent_state_not_claimed_as_physical_readback": True,
            "platform_claim_ceiling_respected": True,
        },
        "scope_guards": {
            "physical_execution_performed": False,
            "controller_executed": False,
            "distributed_runtime_executed": False,
            "training_executed": False,
            "eval_executed": False,
        },
        "deterministic_replay": True,
    }


def test_exact_inventory_with_declared_omission_qualifies() -> None:
    result = evaluate_bridge_reconciliation(_payload())
    assert result["classification"] == "QUALIFY"
    assert result["validity_guards"]["mapping_fields_and_locators"] is True


def test_all_exact_or_derived_rows_allow_bridge_design() -> None:
    payload = _payload()
    for row in payload["mapping_rows"]:
        row["disposition"] = "derived" if row["id"] == "reduced_latent_state" else "exact"
    assert evaluate_bridge_reconciliation(payload)["classification"] == "ALLOW"


def test_missing_inventory_row_is_invalid() -> None:
    payload = _payload()
    payload["mapping_rows"].pop()
    assert (
        evaluate_bridge_reconciliation(payload)["classification"] == "INVALID-BRIDGE-RECONCILIATION"
    )


@pytest.mark.parametrize(
    "field",
    (
        "reduced_model_meaning",
        "unit",
        "base",
        "sign",
        "sample_time",
        "claim_ceiling_consequence",
    ),
)
def test_blank_material_mapping_field_is_invalid(field: str) -> None:
    payload = _payload()
    payload["mapping_rows"][0][field] = "  "
    result = evaluate_bridge_reconciliation(payload)
    assert result["classification"] == "INVALID-BRIDGE-RECONCILIATION"
    assert result["validity_guards"]["mapping_fields_and_locators"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("implementation_locators", ["src/example.py#invented"]),
        (
            "implementation_locators",
            ["paper/decoupling_marl_model_first/LINE.md:9999"],
        ),
        (
            "implementation_locators",
            ["results/r316_dynamic_reduction/dynamic_model.json#/missing"],
        ),
        ("official_locators", ["https://docs.andes.app/en/latest/"]),
        ("official_locators", ["https://example.com/en/v2.0.0/"]),
    ),
)
def test_unresolved_or_nonprimary_locator_is_invalid(
    field: str,
    value: list[str],
) -> None:
    payload = _payload()
    payload["mapping_rows"][0][field] = value
    result = evaluate_bridge_reconciliation(payload)
    assert result["classification"] == "INVALID-BRIDGE-RECONCILIATION"
    assert result["validity_guards"]["mapping_fields_and_locators"] is False


@pytest.mark.parametrize(
    "field",
    (
        "repository_sources_match",
        "installed_sources_match",
        "installed_semantics_match",
        "official_sources_primary",
    ),
)
def test_false_source_identity_field_is_invalid(field: str) -> None:
    payload = _payload()
    payload["source_identity"][field] = False
    assert (
        evaluate_bridge_reconciliation(payload)["classification"] == "INVALID-BRIDGE-RECONCILIATION"
    )


@pytest.mark.parametrize(
    "guard",
    (
        "no_hidden_md_write",
        "requested_projected_internal_achieved_distinguished",
        "active_power_incidence_sign_correct",
        "platform_claim_ceiling_respected",
    ),
)
def test_false_semantic_guard_blocks(guard: str) -> None:
    payload = _payload()
    payload["semantic_guards"][guard] = False
    result = evaluate_bridge_reconciliation(payload)
    assert result["classification"] == "BLOCK"
    assert guard in result["blocking_guard_ids"]


def test_unsupported_required_mapping_blocks() -> None:
    payload = _payload()
    payload["mapping_rows"][0]["disposition"] = "unsupported"
    assert evaluate_bridge_reconciliation(payload)["classification"] == "BLOCK"


def test_forbidden_execution_or_training_is_invalid() -> None:
    for field in _payload()["scope_guards"]:
        payload = deepcopy(_payload())
        payload["scope_guards"][field] = True
        assert (
            evaluate_bridge_reconciliation(payload)["classification"]
            == "INVALID-BRIDGE-RECONCILIATION"
        )


def test_nondeterministic_replay_is_invalid() -> None:
    payload = _payload()
    payload["deterministic_replay"] = False
    assert (
        evaluate_bridge_reconciliation(payload)["classification"] == "INVALID-BRIDGE-RECONCILIATION"
    )
