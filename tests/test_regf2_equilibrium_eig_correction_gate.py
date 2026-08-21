from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path

from andes_rl_kundur.evaluation import regf2_equilibrium_eig_gate as parent
from andes_rl_kundur.evaluation.regf2_equilibrium_eig_correction_gate import (
    PARENT_R390_SHA256,
    build_regf2_equilibrium_eig_correction_contract,
    classify_regf2_equilibrium_eig_correction_record,
    payload_sha256,
)


def _parent_test_module():
    path = Path(__file__).with_name("test_regf2_equilibrium_eig_gate.py")
    spec = importlib.util.spec_from_file_location("r391_parent_test_fixture", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _record() -> dict:
    fixture = _parent_test_module()
    record = fixture._record()
    contract = build_regf2_equilibrium_eig_correction_contract()
    record.update(
        schema_version=2,
        round="R391",
        contract_sha256=payload_sha256(contract),
    )
    for arm in record["arms"]:
        matrix = arm["matrix"]
        replacements = {}
        for binding in matrix["state_bindings"]:
            configured_name = binding["dae_name"]
            ordinal = binding["idx"].rsplit("_", 1)[1]
            raw_name = f"{binding['variable']} {binding['model']} {ordinal}"
            replacements[configured_name] = raw_name
            binding["dae_name"] = raw_name
        for row in matrix["dae_state_catalog"]:
            row["name"] = replacements.get(row["name"], row["name"])
        for field in (
            "state_names",
            "zero_tf_state_names",
            "dae_algebraic_names",
            "dae_discrete_names",
            "eig_augmented_algebraic_names",
        ):
            matrix[field] = [replacements.get(name, name) for name in matrix[field]]
    return record


def test_contract_changes_only_correction_provenance() -> None:
    parent_contract = parent.build_regf2_equilibrium_eig_contract()
    contract = build_regf2_equilibrium_eig_correction_contract()
    scientific_view = deepcopy(contract)
    for key in (
        "parent_round",
        "correction_of_contract_sha256",
        "parent_r390_sha256",
        "evidence_corrections",
        "sparse_adapter_runtime",
    ):
        scientific_view.pop(key)
    scientific_view["schema_version"] = parent_contract["schema_version"]
    scientific_view["round"] = parent_contract["round"]

    assert scientific_view == parent_contract
    assert contract["parent_r390_sha256"] == PARENT_R390_SHA256
    assert contract["sparse_adapter_runtime"] == {
        "andes_shared_sha256": (
            "4de1748db771159d36cb30bf315f70956cfda6a9f7f6ca020ec74674d1e8c15c"
        ),
        "kvxopt_base_sha256": (
            "75d075ca30ca1d988b4218c0d9892264f14658fde94579ade94d9de42c76414b"
        ),
        "kvxopt_version": "1.3.3.1",
    }


def test_actual_andes_display_names_pass_parent_science() -> None:
    analysis = classify_regf2_equilibrium_eig_correction_record(_record())

    assert analysis["classification"] == (
        "REGF2-EIG-ELIGIBLE-NO-POSITIVE-REAL-MODE"
    )
    assert analysis["checks"]["correction_contract"] is True
    assert analysis["checks"]["raw_andes_state_binding"] is True


def test_raw_record_is_not_mutated_by_normalized_replay() -> None:
    record = _record()
    before = deepcopy(record)

    classify_regf2_equilibrium_eig_correction_record(record)

    assert record == before


def test_malformed_state_catalog_rows_are_analysis_invalid() -> None:
    record = _record()
    binding = record["arms"][0]["matrix"]["state_bindings"][0]
    record["arms"][0]["matrix"]["dae_state_catalog"][
        binding["original_address"]
    ] = 123

    analysis = classify_regf2_equilibrium_eig_correction_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"
    assert analysis["checks"]["raw_andes_state_binding"] is False


def test_forged_display_ordinal_is_analysis_invalid() -> None:
    record = _record()
    arm = record["arms"][0]
    binding = arm["matrix"]["state_bindings"][0]
    forged = binding["dae_name"].rsplit(" ", 1)[0] + " 99"
    address = binding["original_address"]
    old = binding["dae_name"]
    binding["dae_name"] = forged
    arm["matrix"]["dae_state_catalog"][address]["name"] = forged
    arm["matrix"]["state_names"] = [
        forged if name == old else name for name in arm["matrix"]["state_names"]
    ]

    analysis = classify_regf2_equilibrium_eig_correction_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"
    assert analysis["checks"]["raw_andes_state_binding"] is False


def test_post_hoc_contract_mutation_is_analysis_invalid() -> None:
    contract = build_regf2_equilibrium_eig_correction_contract()
    contract["positive_real_threshold"] = 0.0

    analysis = classify_regf2_equilibrium_eig_correction_record(
        _record(), contract
    )

    assert analysis["classification"] == "ANALYSIS-INVALID"
    assert analysis["checks"]["correction_contract"] is False


def test_nonmapping_record_is_analysis_invalid() -> None:
    analysis = classify_regf2_equilibrium_eig_correction_record("malformed")

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_eig_failure_arm_preserves_raw_catalog_identity() -> None:
    fixture = _parent_test_module()
    record = _record()
    arm = record["arms"][0]
    arm["scientific_error"] = "EIG calculation failed"
    arm["solver"]["eig_return"] = False
    arm["finite_guard"]["state_matrix_finite"] = False
    arm["matrix"] = fixture._failed_matrix(arm)

    analysis = classify_regf2_equilibrium_eig_correction_record(record)

    assert analysis["classification"] == (
        "STOP-REGF2-SPECTRUM-NUMERICALLY-UNRESOLVED"
    )


def test_eig_failure_rejects_malformed_state_catalog_rows() -> None:
    fixture = _parent_test_module()
    record = _record()
    arm = record["arms"][0]
    arm["scientific_error"] = "EIG calculation failed"
    arm["solver"]["eig_return"] = False
    arm["finite_guard"]["state_matrix_finite"] = False
    arm["matrix"] = fixture._failed_matrix(arm)
    arm["matrix"]["dae_state_catalog"][0] = 123

    analysis = classify_regf2_equilibrium_eig_correction_record(record)

    assert analysis["classification"] == "ANALYSIS-INVALID"
    assert analysis["checks"]["raw_andes_state_binding"] is False
