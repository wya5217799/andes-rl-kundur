from __future__ import annotations

from copy import deepcopy

import pytest

from andes_rl_kundur.evaluation.model_first_stage1_eval_view import (
    build_fresh_stage1_eval_view,
)


def _edge_record() -> dict[str, object]:
    return {
        "round": "R310",
        "question": "Q-0066",
        "coordinate": "edge_1",
        "sign": "positive",
        "controller": "positive",
        "scenario": "op1_edge_1",
        "traces": [{"t": 0.7, "value": [1.0, 2.0]}],
    }


def test_eval_view_binds_source_and_changes_only_pairing_metadata() -> None:
    source = _edge_record()
    frozen = deepcopy(source)

    view = build_fresh_stage1_eval_view(
        source,
        source_path="results/r310/records/op1_edge_1__positive.json",
        source_sha256="a" * 64,
    )

    assert source == frozen
    assert view["sign"] == "paired"
    assert view["pulse_sign"] == "positive"
    assert view["source_record"] == {
        "path": "results/r310/records/op1_edge_1__positive.json",
        "sha256": "a" * 64,
    }
    restored = deepcopy(view)
    restored["sign"] = restored.pop("pulse_sign")
    restored.pop("source_record")
    assert restored == source


@pytest.mark.parametrize(
    "mutate",
    [
        lambda record: record.update(round="R307"),
        lambda record: record.update(coordinate="common"),
        lambda record: record.update(sign="paired"),
        lambda record: record.update(controller="negative"),
    ],
)
def test_eval_view_rejects_nonfresh_or_unpaired_source_records(mutate) -> None:
    source = _edge_record()
    mutate(source)

    with pytest.raises(ValueError):
        build_fresh_stage1_eval_view(
            source,
            source_path="results/r310/source.json",
            source_sha256="a" * 64,
        )


def test_eval_view_rejects_malformed_source_hash() -> None:
    with pytest.raises(ValueError, match="64-character"):
        build_fresh_stage1_eval_view(
            _edge_record(),
            source_path="results/r310/source.json",
            source_sha256="bad",
        )


def test_eval_view_accepts_prospectively_declared_round_identity() -> None:
    source = _edge_record()
    source.update(round="R312", question="Q-0068")

    view = build_fresh_stage1_eval_view(
        source,
        source_path="results/r312/source.json",
        source_sha256="b" * 64,
        expected_round="R312",
        expected_question="Q-0068",
    )

    assert view["round"] == "R312"
    assert view["question"] == "Q-0068"


def test_eval_view_rejects_drift_from_declared_round_identity() -> None:
    with pytest.raises(ValueError, match="declared round/question"):
        build_fresh_stage1_eval_view(
            _edge_record(),
            source_path="results/r312/source.json",
            source_sha256="b" * 64,
            expected_round="R312",
            expected_question="Q-0068",
        )
