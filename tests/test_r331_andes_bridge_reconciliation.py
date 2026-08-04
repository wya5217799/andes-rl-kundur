from __future__ import annotations

from copy import deepcopy

from probes.r331_andes_bridge_reconciliation import (
    REQUIRED_MAPPING_IDS,
    evaluate_bridge_reconciliation,
)


def _row(identifier: str, disposition: str = "exact") -> dict[str, object]:
    return {
        "id": identifier,
        "reduced_model_meaning": f"reduced meaning for {identifier}",
        "implementation_locators": [
            "paper/decoupling_marl_model_first/working/model_contract.md:1"
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
        "round": "R331",
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


def test_exact_inventory_with_declared_platform_omission_qualifies() -> None:
    result = evaluate_bridge_reconciliation(_payload())
    assert result["classification"] == "QUALIFY"
    assert result["validity_guards"]["mapping_inventory"] is True
    assert result["bridge_guards"]["all"] is True
    assert result["qualification_ids"]


def test_all_exact_or_derived_rows_allow_bridge_design() -> None:
    payload = _payload()
    for row in payload["mapping_rows"]:
        row["disposition"] = "derived" if row["id"] == "reduced_latent_state" else "exact"
    result = evaluate_bridge_reconciliation(payload)
    assert result["classification"] == "ALLOW"
    assert result["qualification_ids"] == []


def test_missing_inventory_row_is_invalid() -> None:
    payload = _payload()
    payload["mapping_rows"].pop()
    assert (
        evaluate_bridge_reconciliation(payload)["classification"] == "INVALID-BRIDGE-RECONCILIATION"
    )


def test_blank_official_locator_is_invalid() -> None:
    payload = _payload()
    payload["mapping_rows"][0]["official_locators"] = []
    result = evaluate_bridge_reconciliation(payload)
    assert result["classification"] == "INVALID-BRIDGE-RECONCILIATION"
    assert result["validity_guards"]["mapping_fields_and_locators"] is False


def test_unresolved_implementation_or_unversioned_official_locator_is_invalid() -> None:
    for field, value in (
        ("implementation_locators", ["src/example.py#invented"]),
        ("official_locators", ["https://docs.andes.app/en/latest/"]),
    ):
        payload = _payload()
        payload["mapping_rows"][0][field] = value
        result = evaluate_bridge_reconciliation(payload)
        assert result["classification"] == "INVALID-BRIDGE-RECONCILIATION"
        assert result["validity_guards"]["mapping_fields_and_locators"] is False


def test_hidden_md_write_blocks() -> None:
    payload = _payload()
    payload["semantic_guards"]["no_hidden_md_write"] = False
    result = evaluate_bridge_reconciliation(payload)
    assert result["classification"] == "BLOCK"
    assert "no_hidden_md_write" in result["blocking_guard_ids"]


def test_requested_power_cannot_stand_in_for_achieved_power() -> None:
    payload = _payload()
    payload["semantic_guards"]["requested_projected_internal_achieved_distinguished"] = False
    result = evaluate_bridge_reconciliation(payload)
    assert result["classification"] == "BLOCK"
    assert "requested_projected_internal_achieved_distinguished" in result["blocking_guard_ids"]


def test_wrong_incidence_sign_blocks() -> None:
    payload = _payload()
    payload["semantic_guards"]["active_power_incidence_sign_correct"] = False
    assert evaluate_bridge_reconciliation(payload)["classification"] == "BLOCK"


def test_unsupported_required_mapping_blocks() -> None:
    payload = _payload()
    payload["mapping_rows"][0]["disposition"] = "unsupported"
    result = evaluate_bridge_reconciliation(payload)
    assert result["classification"] == "BLOCK"
    assert result["blocking_mapping_ids"] == [payload["mapping_rows"][0]["id"]]


def test_over_ceiling_platform_claim_blocks() -> None:
    payload = _payload()
    payload["semantic_guards"]["platform_claim_ceiling_respected"] = False
    assert evaluate_bridge_reconciliation(payload)["classification"] == "BLOCK"


def test_any_execution_or_training_makes_reconciliation_invalid() -> None:
    for field in (
        "physical_execution_performed",
        "controller_executed",
        "distributed_runtime_executed",
        "training_executed",
        "eval_executed",
    ):
        payload = deepcopy(_payload())
        payload["scope_guards"][field] = True
        assert (
            evaluate_bridge_reconciliation(payload)["classification"]
            == "INVALID-BRIDGE-RECONCILIATION"
        )
