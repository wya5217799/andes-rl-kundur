from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from probes.r334_pq_disturbance_identification import (
    _translate_identity_only,
    analyse_r334_pq_disturbance_identification,
)
from scripts import run_r334_pq_disturbance_identification as adapter

ROOT = Path(__file__).resolve().parents[1]
R333_EXECUTION = (
    ROOT / "results/r333_pq_disturbance_identification/execution.json"
)


def _r334_payload() -> tuple[dict, dict, dict, dict]:
    execution = json.loads(R333_EXECUTION.read_text(encoding="utf-8"))
    execution["round"] = "R334"
    execution.update(adapter.REWARD_BOUNDARY)
    inputs: dict[str, dict[str, object]] = {"HS0": {}, "HS1": {}}
    predictions: dict[str, dict[str, object]] = {"HS0": {}, "HS1": {}}
    for record in execution["records"]:
        record["round"] = "R334"
        record.update(adapter.REWARD_BOUNDARY)
        inputs[record["operating_point"]][record["sign"]] = record[
            "coordinate_input_sequence"
        ]
        predictions[record["operating_point"]][record["sign"]] = record[
            "predicted_output_coordinates"
        ]
    return execution, adapter.build_contract(), inputs, predictions


def _analyse(execution: dict) -> dict:
    _run, contract, inputs, predictions = _r334_payload()
    return analyse_r334_pq_disturbance_identification(
        execution,
        contract,
        expected_seal_sha256=execution["seal_sha256"],
        expected_dynamic_model_sha256=execution["dynamic_model_sha256"],
        expected_coordinate_inputs=inputs,
        expected_predictions=predictions,
        evidence_chain_valid=True,
    )


def test_contract_preserves_science_and_declares_reward_boundary() -> None:
    contract = adapter.build_contract()
    assert contract["round"] == "R334"
    assert contract["question"] == "Q-0085"
    assert contract["record_count"] == 6
    assert contract["amplitude_system_pu"] == 0.05
    assert contract["thresholds"] == {
        "pq_readback_absolute_tolerance_system_pu": 1e-12,
        "zero_actuator_power_absolute_maximum_system_pu": 1e-6,
        "algebraic_residual_absolute_maximum": 1e-6,
        "signal_to_baseline_drift_energy_ratio_minimum": 10.0,
        "pair_midpoint_nonlinearity_ratio_maximum": 0.10,
        "reduced_physical_total_nrmse_maximum": 0.15,
        "reduced_physical_peak_vector_residual_maximum": 0.20,
    }
    assert contract["pair_midpoint_metric"] == "normalized-l2-midpoint-residual"
    assert contract["reward_boundary"] == adapter.REWARD_BOUNDARY
    translated = copy.deepcopy(contract)
    translated["round"] = "R333"
    translated.pop("reward_boundary")
    translated.pop("pair_midpoint_metric")
    translated.pop("evidence_correction")
    assert translated == adapter._R333_BUILD_CONTRACT()


def test_source_inventory_is_conservative_and_closes_reported_gaps() -> None:
    source_paths = adapter._source_paths()
    paths = {path.resolve() for path in source_paths.values()}
    assert len(paths) == len(source_paths)
    required = {
        ROOT / "src/andes_rl_kundur/env/andes/model_first_contract.py",
        ROOT / "src/andes_rl_kundur/evaluation/model_first_dynamic_reduction.py",
        ROOT / "src/andes_rl_kundur/env/andes/model_first_env.py",
        ROOT / "scripts/run_r333_pq_disturbance_identification.py",
        ROOT / "probes/r333_pq_disturbance_identification.py",
        ROOT / "src/andes_rl_kundur/env/andes/model_first_pq_disturbance.py",
        ROOT / "scripts/andes_scratch.py",
        ROOT / "memory/tools/artifact_io.py",
    }
    assert {path.resolve() for path in required} <= paths
    assert {
        path.resolve()
        for path in (ROOT / "src/andes_rl_kundur").rglob("*.py")
    } <= paths


def test_identity_translation_changes_only_round_fields() -> None:
    execution, contract, _inputs, _predictions = _r334_payload()
    translated_execution, translated_contract = _translate_identity_only(
        execution, contract
    )
    expected_execution = copy.deepcopy(execution)
    expected_execution["round"] = "R333"
    for record in expected_execution["records"]:
        record["round"] = "R333"
    expected_contract = copy.deepcopy(contract)
    expected_contract["round"] = "R333"
    assert translated_execution == expected_execution
    assert translated_contract == expected_contract
    assert execution["round"] == "R334"
    assert contract["round"] == "R334"


def test_reward_diagnostics_are_required_but_values_do_not_affect_decision() -> None:
    execution, _contract, _inputs, _predictions = _r334_payload()
    baseline = _analyse(execution)
    assert baseline["classification"] == "QUALIFY"
    assert baseline["scope"]["paired_local_linearity_guard_interpretation"] == (
        "registered-signed-pair-approximate-odd-symmetry-only"
    )
    assert baseline["scope"]["local_or_global_linearity_authorized"] is False
    changed = copy.deepcopy(execution)
    for record in changed["records"]:
        for row in record["traces"]:
            row["r_f"] = 123.0
            row["r_h"] = -456.0
            row["r_d"] = 789.0
            row["r_smooth"] = -0.25
    assert _analyse(changed) == baseline


def test_reward_field_presence_does_not_affect_decision() -> None:
    execution, _contract, _inputs, _predictions = _r334_payload()
    baseline = _analyse(execution)
    for record in execution["records"]:
        for row in record["traces"]:
            for field in ("r_f", "r_h", "r_d", "r_smooth"):
                row.pop(field, None)
    assert _analyse(execution) == baseline


def test_missing_reward_boundary_metadata_invalidates_without_metrics() -> None:
    execution, _contract, _inputs, _predictions = _r334_payload()
    execution["reward_used_for_classification"] = True
    result = _analyse(execution)
    assert result["classification"] == (
        "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION"
    )
    assert result["validity_guards"]["reward_diagnostic_boundary"] is False
    assert result["record_metrics"] == []
    assert result["point_metrics"] == []


def test_prepare_is_create_only_and_seals_runtime_source_superset(
    tmp_path: Path,
) -> None:
    seal_path = tmp_path / "seal.json"
    digest = adapter.prepare(seal_path, created_utc="2026-08-04T00:00:00+00:00")
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    assert len(digest) == 64
    assert seal["round"] == "R334"
    assert seal["installed_andes_case"]["sha256"] == adapter.EXPECTED_CASE_SHA256
    assert any(
        row["path"].endswith("model_first_env.py")
        for row in seal["sources"].values()
    )
    loaded, loaded_digest = adapter._load_seal(seal_path, digest)
    assert loaded == seal
    assert loaded_digest == digest
    with pytest.raises(FileExistsError):
        adapter.prepare(seal_path, created_utc="2026-08-04T00:00:00+00:00")


def test_load_seal_rejects_source_inventory_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seal_path = tmp_path / "seal.json"
    digest = adapter.prepare(seal_path, created_utc="2026-08-04T00:00:00+00:00")
    monkeypatch.setattr(adapter, "_sources", lambda: {})
    with pytest.raises(RuntimeError, match="source"):
        adapter._load_seal(seal_path, digest)


def test_scoped_binding_restores_inherited_globals_after_exception() -> None:
    original = (adapter._base.ROUND_ID, adapter._base.QUESTION_ID)
    with pytest.raises(RuntimeError, match="boom"):
        with adapter._scoped_r334_binding():
            assert adapter._base.ROUND_ID == "R334"
            assert adapter._base.QUESTION_ID == "Q-0085"
            raise RuntimeError("boom")
    assert (adapter._base.ROUND_ID, adapter._base.QUESTION_ID) == original


def test_parser_defaults_are_isolated_to_r334() -> None:
    parser = adapter.build_parser()
    prepare_args = parser.parse_args(["prepare"])
    execute_args = parser.parse_args(["execute", "--expected-sha256", "0" * 64])
    assert prepare_args.seal == adapter.DEFAULT_SEAL
    assert execute_args.seal == adapter.DEFAULT_SEAL
    assert execute_args.out == adapter.DEFAULT_OUT
    assert "R333" not in str(prepare_args.seal)
    assert "r333" not in str(execute_args.out)


def test_direct_script_entrypoint_resolves_repository_imports(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_r334_pq_disturbance_identification.py"),
            "--help",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "prepare" in completed.stdout


def test_manifest_inventory_is_exact_and_unique() -> None:
    out = adapter.DEFAULT_OUT
    rows = [
        {"name": name, "path": adapter._path_text(out / filename), "sha256": "0" * 64}
        for name, filename in (
            ("formal_attempt", "formal_attempt.json"),
            ("execution", "execution.json"),
            ("provenance", "provenance.json"),
        )
    ]
    manifest = {"records": rows}
    assert set(adapter._validated_manifest_entries(manifest, out)) == {
        "formal_attempt",
        "execution",
        "provenance",
    }
    bad = copy.deepcopy(manifest)
    bad["records"][2]["name"] = "execution"
    with pytest.raises(RuntimeError, match="duplicate"):
        adapter._validated_manifest_entries(bad, out)


def test_mixed_or_legacy_identity_is_invalid_before_delegation() -> None:
    execution, contract, inputs, predictions = _r334_payload()
    for run_round, contract_round in (("R333", "R334"), ("R334", "R333")):
        run = copy.deepcopy(execution)
        sealed = copy.deepcopy(contract)
        run["round"] = run_round
        sealed["round"] = contract_round
        result = analyse_r334_pq_disturbance_identification(
            run,
            sealed,
            expected_seal_sha256=run["seal_sha256"],
            expected_dynamic_model_sha256=run["dynamic_model_sha256"],
            expected_coordinate_inputs=inputs,
            expected_predictions=predictions,
            evidence_chain_valid=True,
        )
        assert result["classification"] == (
            "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION"
        )
        assert result["validity_guards"]["r334_identity"] is False


def test_bad_record_identity_short_circuits_before_inherited_classifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execution, contract, inputs, predictions = _r334_payload()
    execution["records"][0]["round"] = "R333"

    def forbidden(*_args, **_kwargs):
        raise AssertionError("inherited classifier must not be called")

    monkeypatch.setattr(
        "probes.r334_pq_disturbance_identification."
        "analyse_pq_disturbance_identification",
        forbidden,
    )
    result = analyse_r334_pq_disturbance_identification(
        execution,
        contract,
        expected_seal_sha256=execution["seal_sha256"],
        expected_dynamic_model_sha256=execution["dynamic_model_sha256"],
        expected_coordinate_inputs=inputs,
        expected_predictions=predictions,
        evidence_chain_valid=True,
    )
    assert result["classification"] == (
        "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION"
    )
    assert result["validity_guards"]["r334_identity"] is False
