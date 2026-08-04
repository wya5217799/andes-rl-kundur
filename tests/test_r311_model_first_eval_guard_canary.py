from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r311_model_first_eval_guard_canary.py"


def _module():
    spec = importlib.util.spec_from_file_location("r311_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R311 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _passing_scorecard() -> dict[str, object]:
    return {
        "validity": {
            "diagnostic_pass": True,
            "input_integrity": {"pass": True},
            "execution_contract": {
                "pass": True,
                "violation_count": 0,
                "failed_check_counts": {},
            },
        },
        "evidence_status": {"status": "EXTERNAL_AUTHORITY_REQUIRED"},
    }


def test_r311_contract_freezes_sources_eval_profile_and_no_learning() -> None:
    contract = _module().build_contract()

    assert contract["round"] == "R311"
    assert contract["question"] == "Q-0067"
    assert contract["source_pair"] == {
        "positive": {
            "path": "results/r310_model_first_stage1/records/edge_source/op0_edge_0__positive.json",
            "sha256": "db59415d00238cbd58339c52671e67a8926d517ca0a464a89f49fdffb3bba17d",
        },
        "negative": {
            "path": "results/r310_model_first_stage1/records/edge_source/op0_edge_0__negative.json",
            "sha256": "eae0611606d0bc543c7d038f0a91d589f9d0822cf119e1d2be4d42f3a061c7a1",
        },
    }
    assert contract["eval"] == {
        "baseline": "positive",
        "execution_profile": "vector_power",
        "required_active_window_seconds": 1.0,
        "bootstrap_resamples": 1000,
        "bootstrap_seed": 2026080311,
        "evidence_status": "EXTERNAL_AUTHORITY_REQUIRED",
    }
    assert contract["physical_trace_rerun"] is False
    assert contract["r310_amendment_authorized"] is False
    assert contract["training_authorized"] is False


def test_r311_parser_exposes_only_prepare_run_analyse() -> None:
    parser = _module().build_parser()
    action = next(item for item in parser._actions if item.dest == "command")

    assert set(action.choices) == {"prepare", "run", "analyse"}


def test_r311_classifier_is_binary_and_fail_closed() -> None:
    module = _module()
    assert (
        module.classify_scorecard(_passing_scorecard())
        == "EVAL-GUARD-ADAPTER-CANARY-PASS"
    )

    for mutate in (
        lambda score: score["validity"].update(diagnostic_pass=False),
        lambda score: score["validity"]["input_integrity"].update(pass_=False),
        lambda score: score["validity"]["execution_contract"].update(pass_=False),
        lambda score: score["validity"]["execution_contract"].update(
            violation_count=1
        ),
        lambda score: score["validity"]["execution_contract"].update(
            failed_check_counts={"x": 1}
        ),
        lambda score: score["evidence_status"].update(status="ELIGIBLE"),
    ):
        score = _passing_scorecard()
        mutate(score)
        if "pass_" in score["validity"].get("input_integrity", {}):
            score["validity"]["input_integrity"]["pass"] = score["validity"][
                "input_integrity"
            ].pop("pass_")
        if "pass_" in score["validity"].get("execution_contract", {}):
            score["validity"]["execution_contract"]["pass"] = score["validity"][
                "execution_contract"
            ].pop("pass_")
        assert (
            module.classify_scorecard(score)
            == "INVALID-EVAL-GUARD-ADAPTER-CANARY"
        )


def test_r311_json_writer_is_create_only(tmp_path: Path) -> None:
    module = _module()
    path = tmp_path / "artifact.json"

    digest = module._write_new_json(path, {"ok": True})
    assert len(digest) == 64
    assert path.with_suffix(".json.sha256").is_file()
    with pytest.raises(FileExistsError):
        module._write_new_json(path, {"ok": False})
