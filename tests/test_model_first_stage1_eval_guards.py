from __future__ import annotations

from copy import deepcopy

import pytest

from andes_rl_kundur.evaluation.model_first_stage1_eval_guards import (
    build_guarded_fresh_stage1_eval_view,
    synthesize_fresh_stage1_eval_guards,
)


def _source_record() -> dict[str, object]:
    row = {
        "t": 0.7,
        "system_exit_code": 0,
        "tds_failed": False,
        "finite_state_algebraic": True,
        "freq_hz_physical": [60.0, 60.0, 60.0, 60.0],
        "delta_f_physical_hz": [0.0, 0.0, 0.0, 0.0],
        "bess_requested_power_system_pu": [0.05, -0.05, 0.0, 0.0],
        "bess_commanded_power_system_pu": [0.05, -0.05, 0.0, 0.0],
        "bess_actual_power_system_pu": [0.05, -0.05, 0.0, 0.0],
        "bess_soc": [0.5, 0.5, 0.5, 0.5],
    }
    return {
        "round": "R310",
        "question": "Q-0066",
        "coordinate": "edge_0",
        "sign": "positive",
        "controller": "positive",
        "scenario": "op0_edge_0",
        "completed": True,
        "tds_failed": False,
        "n_steps": 2,
        "requested_steps": 2,
        "initialization_solver": {
            "tds_test_ok": True,
            "system_exit_code": 0,
        },
        "traces": [deepcopy(row), {**deepcopy(row), "t": 0.9}],
        "guards": {
            "completed": False,
            "tds_test_ok": False,
            "system_exit_code": 9,
            "finite_telemetry": False,
        },
    }


def test_guard_synthesis_uses_authoritative_fields_not_existing_guard_object() -> None:
    source = _source_record()

    assert synthesize_fresh_stage1_eval_guards(source) == {
        "completed": True,
        "tds_test_ok": True,
        "system_exit_code": 0,
        "finite_telemetry": True,
    }


def test_guarded_view_is_source_bound_and_does_not_mutate_source() -> None:
    source = _source_record()
    frozen = deepcopy(source)

    view = build_guarded_fresh_stage1_eval_view(
        source,
        source_path="results/r310/source.json",
        source_sha256="a" * 64,
    )

    assert source == frozen
    assert view["guards"] == {
        "completed": True,
        "tds_test_ok": True,
        "system_exit_code": 0,
        "finite_telemetry": True,
    }
    assert view["sign"] == "paired"
    assert view["pulse_sign"] == "positive"
    assert view["source_record"]["sha256"] == "a" * 64


def test_guarded_view_accepts_prospectively_declared_round_identity() -> None:
    source = _source_record()
    source.update(round="R312", question="Q-0068")

    view = build_guarded_fresh_stage1_eval_view(
        source,
        source_path="results/r312/source.json",
        source_sha256="c" * 64,
        expected_round="R312",
        expected_question="Q-0068",
    )

    assert view["round"] == "R312"
    assert view["question"] == "Q-0068"
    assert view["guards"] == {
        "completed": True,
        "tds_test_ok": True,
        "system_exit_code": 0,
        "finite_telemetry": True,
    }


@pytest.mark.parametrize(
    "mutate",
    [
        lambda record: record.update(completed=False),
        lambda record: record.update(tds_failed=True),
        lambda record: record.update(n_steps=1),
        lambda record: record["initialization_solver"].update(tds_test_ok=False),
        lambda record: record["initialization_solver"].update(system_exit_code=1),
        lambda record: record["traces"][0].update(system_exit_code=1),
        lambda record: record["traces"][0].update(finite_state_algebraic=False),
        lambda record: record["traces"][0].update(
            freq_hz_physical=[float("nan"), 60.0, 60.0, 60.0]
        ),
    ],
)
def test_guard_synthesis_rejects_invalid_or_unknown_source_state(mutate) -> None:
    source = _source_record()
    mutate(source)

    with pytest.raises(ValueError):
        synthesize_fresh_stage1_eval_guards(source)
