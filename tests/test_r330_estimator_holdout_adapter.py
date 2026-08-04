"""Contract tests for the sealed R330 holdout adapter."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest
import scripts.run_r330_estimator_holdout as r330

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r330_estimator_holdout.py"


def _module():
    spec = importlib.util.spec_from_file_location("r330_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R330 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r330_contract_is_exactly_the_registered_untouched_holdout() -> None:
    contract = _module().build_contract()

    assert contract["round"] == "R330"
    assert contract["question"] == "Q-0083"
    assert contract["holdout_base_case_count"] == 16
    assert contract["holdout_case_count"] == 80
    assert contract["mismatch_modes"] == [
        "nominal",
        "plus_scale",
        "minus_scale",
        "signed_reflection",
        "common_differential_exchange",
    ]
    assert len(contract["holdout_case_names"]) == 16
    assert len(contract["holdout_case_records"]) == 16
    assert all(
        set(record)
        == {
            "name",
            "point",
            "initial_soc",
            "disturbance",
            "payload_sha256",
        }
        for record in contract["holdout_case_records"]
    )
    assert contract["limits"]["node_power"] > 0.0
    assert len(contract["runtime_dependency_fingerprint"]["osqp_distribution_sha256"]) == 64
    assert (
        len(contract["runtime_dependency_fingerprint"]["threadpoolctl_distribution_sha256"]) == 64
    )
    assert contract["holdout"]["candidate_count"] == 1
    assert contract["holdout"]["resynthesis_or_tuning"] == "forbidden"
    assert contract["holdout"]["physical_execution"] == "forbidden"


def test_r330_design_and_mismatch_fingerprints_reconstruct_exactly() -> None:
    module = _module()
    plants, controllers, estimators = module._formal_designs()

    first = module._design_fingerprints(plants, controllers, estimators)
    second = module._design_fingerprints(plants, controllers, estimators)

    assert first == second
    assert set(first) == {"HS0", "HS1"}
    assert all(len(record["payload_sha256"]) == 64 for record in first.values())
    assert list(module._mismatch_records()) == [
        "nominal",
        "plus_scale",
        "minus_scale",
        "signed_reflection",
        "common_differential_exchange",
    ]


def test_r330_accepts_only_the_known_r329_closure_drift() -> None:
    parent = _module()._parent_bundle()

    assert parent["r329_expected_closure_source_drift"] == ["plan", "question"]
    assert len(parent["r329_seal"]["sha256"]) == 64
    assert len(parent["r326_seal"]["sha256"]) == 64
    assert parent["r326_seal"]["sha256"] == parent["r326_authority"]["r326_source_sha256"]


def test_r330_execute_replays_the_complete_holdout_without_other_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    calls: list[int] = []
    writes: list[tuple[str, dict[str, object]]] = []
    fingerprints = {"HS0": {"payload_sha256": "f" * 64}}
    mismatches = {"nominal": {"bytes_sha256": "m" * 64}}
    cases = [{"name": "h0", "payload_sha256": "h" * 64}]
    limits = {"node_power": 0.2}
    runtime = {"python_version": "test"}
    seal = {
        "contract_payload_sha256": "c" * 64,
        "contract": {
            "frozen_design_fingerprints": fingerprints,
            "mismatch_fingerprints": mismatches,
            "holdout_case_records": cases,
            "limits": limits,
            "runtime_dependency_fingerprint": runtime,
        },
        "parent": {
            "r329_execution": {"sha256": "e" * 64},
            "r329_analysis": {"sha256": "a" * 64},
        },
    }
    monkeypatch.setattr(module, "_load_seal", lambda *_: (seal, "s" * 64))
    monkeypatch.setattr(
        module,
        "_formal_designs",
        lambda: ({"HS0": object()}, {"HS0": object()}, {"HS0": object()}),
    )
    monkeypatch.setattr(module, "_design_fingerprints", lambda *_: fingerprints)
    monkeypatch.setattr(module, "_mismatch_records", lambda: mismatches)
    monkeypatch.setattr(module, "_case_records", lambda: cases)
    monkeypatch.setattr(module, "_limits_record", lambda: limits)
    monkeypatch.setattr(module, "_runtime_dependency_fingerprint", lambda: runtime)

    def fake_pass(*_args):
        calls.append(len(calls))
        return [{"case": "c", "mismatch": "nominal"}]

    monkeypatch.setattr(module, "_holdout_pass", fake_pass)
    monkeypatch.setattr(
        module,
        "_write_new_json",
        lambda path, payload: writes.append((path.name, dict(payload))) or "d" * 64,
    )

    module.execute(tmp_path / "seal.json", "s" * 64, tmp_path)

    assert [name for name, _payload in writes] == [
        "execution_receipt.json",
        "execution.json",
    ]
    assert writes[0][1]["status"] == "HOLDOUT-OPENED"
    written = writes[1][1]
    assert calls == [0, 1]
    assert written["deterministic_execution_replay"] is True
    assert written["design_fingerprint_identity"] is True
    assert written["mismatch_identity"] is True
    assert written["holdout_case_identity"] is True
    assert written["limits_identity"] is True
    assert written["runtime_dependency_identity"] is True
    assert written["physical_execution_authorized"] is False
    assert written["distributed_agent_implementation_authorized"] is False
    assert written["training_authorized"] is False


def test_r330_parser_and_writer_are_create_only(tmp_path: Path) -> None:
    module = _module()
    parser = module.build_parser()
    action = next(item for item in parser._actions if item.dest == "command")

    assert set(action.choices) == {"prepare", "execute", "analyse"}
    path = tmp_path / "artifact.json"
    digest = module._write_new_json(path, {"ok": True})
    assert len(digest) == 64
    with pytest.raises(FileExistsError):
        module._write_new_json(path, {"ok": False})


def test_r330_analysis_recomputes_artifact_identity_instead_of_trusting_flags(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    observed: list[dict[str, object]] = []
    seal = {
        "contract": {
            "frozen_design_fingerprints": {"HS0": {"payload_sha256": "f" * 64}},
            "mismatch_fingerprints": {"nominal": {"bytes_sha256": "m" * 64}},
            "holdout_case_records": [{"name": "h0", "payload_sha256": "h" * 64}],
            "limits": {"node_power": 0.2},
            "runtime_dependency_fingerprint": {"python_version": "sealed"},
        },
        "contract_payload_sha256": "c" * 64,
        "parent": {
            "r329_execution": {"sha256": "e" * 64},
            "r329_analysis": {"sha256": "a" * 64},
        },
        "sources": {},
    }
    execution = {
        "seal_sha256": "wrong",
        "contract_payload_sha256": "wrong",
        "parent_execution_sha256": "wrong",
        "parent_analysis_sha256": "wrong",
        "sealed_source_identity": True,
        "parent_identity": True,
        "development_identity": True,
        "design_fingerprint_identity": True,
        "mismatch_identity": True,
        "holdout_case_identity": True,
        "limits_identity": True,
        "runtime_dependency_identity": True,
        "design_fingerprints": {},
        "mismatch_fingerprints": {},
        "holdout_case_records": [],
        "limits": {},
        "runtime_dependency_fingerprint": {},
        "execution_receipt_sha256": "wrong",
    }
    receipt = {
        "round": "R330",
        "question": "Q-0083",
        "status": "HOLDOUT-OPENED",
        "seal_sha256": "wrong",
        "contract_payload_sha256": "wrong",
        "parent_execution_sha256": "wrong",
        "parent_analysis_sha256": "wrong",
    }
    monkeypatch.setattr(module, "_load_seal", lambda *_: (seal, "s" * 64))
    monkeypatch.setattr(
        module.r329.r328.r326.r325,
        "_read_verified_json",
        lambda path, *_: (
            (receipt, "r" * 64) if path.name == "execution_receipt.json" else (execution, "x" * 64)
        ),
    )

    def fake_analysis(payload, _contract, *, analysis_replay):
        observed.append(dict(payload))
        return {"classification": "INVALID-ESTIMATOR-HOLDOUT"}

    monkeypatch.setattr(module, "analyse_r330_holdout", fake_analysis)
    monkeypatch.setattr(module, "_write_new_json", lambda *_: "d" * 64)

    module.analyse(tmp_path / "seal.json", "s" * 64, tmp_path)

    assert observed[0]["sealed_source_identity"] is False
    assert observed[0]["parent_identity"] is False
    assert observed[0]["development_identity"] is False
    assert observed[0]["design_fingerprint_identity"] is False
    assert observed[0]["mismatch_identity"] is False
    assert observed[0]["holdout_case_identity"] is False
    assert observed[0]["limits_identity"] is False
    assert observed[0]["runtime_dependency_identity"] is False
    assert observed[0]["execution_receipt_identity"] is False


def test_r330_stops_before_holdout_when_a_frozen_fingerprint_drifts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    calls: list[int] = []
    current_design = {"HS0": {"payload_sha256": "f" * 64}}
    mismatches = {"nominal": {"bytes_sha256": "m" * 64}}
    cases = [{"name": "h0", "payload_sha256": "h" * 64}]
    limits = {"node_power": 0.2}
    runtime = {"python_version": "test"}
    seal = {
        "contract_payload_sha256": "c" * 64,
        "contract": {
            "frozen_design_fingerprints": {"HS0": {"payload_sha256": "different"}},
            "mismatch_fingerprints": mismatches,
            "holdout_case_records": cases,
            "limits": limits,
            "runtime_dependency_fingerprint": runtime,
        },
        "parent": {
            "r329_execution": {"sha256": "e" * 64},
            "r329_analysis": {"sha256": "a" * 64},
        },
    }
    monkeypatch.setattr(module, "_load_seal", lambda *_: (seal, "s" * 64))
    monkeypatch.setattr(
        module,
        "_formal_designs",
        lambda: ({"HS0": object()}, {"HS0": object()}, {"HS0": object()}),
    )
    monkeypatch.setattr(module, "_design_fingerprints", lambda *_: current_design)
    monkeypatch.setattr(module, "_mismatch_records", lambda: mismatches)
    monkeypatch.setattr(module, "_case_records", lambda: cases)
    monkeypatch.setattr(module, "_limits_record", lambda: limits)
    monkeypatch.setattr(module, "_runtime_dependency_fingerprint", lambda: runtime)
    monkeypatch.setattr(module, "_holdout_pass", lambda *_: calls.append(1) or [])

    with pytest.raises(RuntimeError, match="before holdout"):
        module.execute(tmp_path / "seal.json", "s" * 64, tmp_path)

    assert calls == []


def test_r330_windows_spawn_smoke_uses_only_development_data() -> None:
    plants, controllers, estimators = r330._formal_designs()
    development_case = r330.r329.r328.r326.r325.development_cases()[0]

    rows = r330._parallel_pass(
        plants,
        controllers,
        estimators,
        cases=[development_case],
        transforms={"nominal": np.zeros((4, 4))},
        phase="development-smoke",
        maximum_workers=1,
    )

    assert len(rows) == 1
    assert rows[0]["phase"] == "development-smoke"
    assert rows[0]["solver_failed"] is False
    assert rows[0]["execution_error"] is False
    assert rows[0]["native_thread_limit_valid"] is True
