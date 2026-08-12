from __future__ import annotations

import copy
from pathlib import Path

import pytest

from andes_rl_kundur.evaluation.deterministic_decoupling import build_contract
from andes_rl_kundur.evaluation.deterministic_decoupling_identity_correction import (
    IdentityContractError,
    build_corrected_contract,
    require_identity_alignment,
    scan_execution_identities,
    validate_contract_correction,
)


def test_correction_changes_only_round_and_literal_classifier_identity() -> None:
    parent = build_contract()

    corrected = build_corrected_contract(parent)

    assert corrected["round"] == "R375"
    assert corrected["expected_vsg_idx"] == [
        "VSG_1",
        "VSG_2",
        "VSG_3",
        "VSG_4",
    ]
    assert corrected["expected_vsg_buses"] == [12, 16, 14, 15]
    assert validate_contract_correction(parent, corrected) is True


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("thresholds", "heldout_primary_ratio_max"), 0.96),
        (("common_gains", "kp_system_pu_per_hz"), 2.1),
        (("evaluation", "record_count"), 31),
        (("expected_vsg_buses",), [12, 16, 15, 14]),
    ],
)
def test_correction_rejects_every_nonidentity_scientific_change(
    path: tuple[str, ...],
    value: object,
) -> None:
    parent = build_contract()
    corrected = build_corrected_contract(parent)
    cursor = corrected
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value

    assert validate_contract_correction(parent, corrected) is False


def test_identity_scan_does_not_parse_performance_arrays(tmp_path: Path) -> None:
    execution = tmp_path / "execution.json"
    identity = (
        b'{"n_agents":4,"vsg_buses":[12,16,14,15],'
        b'"vsg_idx":["VSG_1","VSG_2","VSG_3","VSG_4"]}'
    )
    execution.write_bytes(
        b'{"record_count":2,"records":['
        b'{"identity":' + identity + b',"steps":[NOT_VALID_JSON]},'
        b'{"identity":' + identity + b',"steps":[ALSO_NOT_JSON]}]}'
    )

    scanned = scan_execution_identities(execution)

    assert scanned["record_count"] == 2
    assert scanned["identities"] == [
        {
            "n_agents": 4,
            "vsg_buses": [12, 16, 14, 15],
            "vsg_idx": ["VSG_1", "VSG_2", "VSG_3", "VSG_4"],
        }
    ] * 2
    assert scanned["performance_fields_parsed"] is False


def test_plan_runtime_and_classifier_identity_must_agree() -> None:
    corrected = build_corrected_contract(build_contract())
    plan = "Four agents `VSG_1..VSG_4` at buses `[12,16,14,15]`."
    scan = {
        "record_count": 60,
        "identities": [
            {
                "n_agents": 4,
                "vsg_idx": ["VSG_1", "VSG_2", "VSG_3", "VSG_4"],
                "vsg_buses": [12, 16, 14, 15],
            }
        ]
        * 60,
        "performance_fields_parsed": False,
    }

    proof = require_identity_alignment(
        plan_text=plan,
        execution_identity_scan=scan,
        corrected_contract=corrected,
    )

    assert proof["valid"] is True
    assert proof["unique_runtime_identity_count"] == 1
    assert proof["performance_fields_parsed"] is False


def test_identity_mismatch_fails_before_summary() -> None:
    corrected = build_corrected_contract(build_contract())
    bad_scan = {
        "record_count": 60,
        "identities": [
            {
                "n_agents": 4,
                "vsg_idx": ["ES1", "ES2", "ES3", "ES4"],
                "vsg_buses": [12, 16, 14, 15],
            }
        ]
        * 60,
        "performance_fields_parsed": False,
    }

    with pytest.raises(IdentityContractError, match="runtime identity"):
        require_identity_alignment(
            plan_text="`VSG_1..VSG_4` at buses `[12,16,14,15]`",
            execution_identity_scan=bad_scan,
            corrected_contract=corrected,
        )


def test_parent_contract_is_not_mutated() -> None:
    parent = build_contract()
    before = copy.deepcopy(parent)

    build_corrected_contract(parent)

    assert parent == before
