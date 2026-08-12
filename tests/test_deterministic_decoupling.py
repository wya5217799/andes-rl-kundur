from __future__ import annotations

import copy

import numpy as np
import pytest

from andes_rl_kundur.evaluation.deterministic_decoupling import (
    build_contract,
    classify_summaries,
    controller_spec,
    phase_jobs,
    probe_request,
    project_modes,
    select_development_candidate,
    summarize_arm_records,
)


def test_contract_separates_development_and_held_out_banks() -> None:
    contract = build_contract()

    assert contract["development"]["record_count"] == 60
    assert contract["evaluation"]["record_count"] == 30
    assert contract["development"]["probe_condition"] == {
        "condition_id": "dev_probe_pq0_plus_0p35",
        "delta_u": {"PQ_0": 0.35},
    }
    assert contract["evaluation"]["probe_condition"] == {
        "condition_id": "eval_probe_bus14_minus_0p55",
        "delta_u": {"PQ_Bus14": -0.55},
    }
    assert len(contract["distributed_candidates"]) == 4
    assert contract["training_authorized"] is False
    assert len(phase_jobs("development", contract=contract)) == 60
    assert len(
        phase_jobs(
            "evaluation",
            selected_arm_id="distributed_ks0p5_kc0p5",
            contract=contract,
        )
    ) == 30
    np.testing.assert_allclose(
        probe_request("inter_area", "negative", contract=contract),
        [-0.025, -0.025, 0.025, 0.025],
    )
    assert controller_spec(
        "distributed_ks1_kc0p5", contract=contract
    ) == {
        "architecture": "distributed_cross_coordinate",
        "kp_system_pu_per_hz": 2.0,
        "ki_system_pu_per_hz_s": 0.2,
        "sync_gain_system_pu_per_hz": 1.0,
        "consensus_gain_per_s": 0.5,
    }


def test_mode_projection_uses_registered_arithmetic_coordinates() -> None:
    values = np.asarray([[1.0, 1.0, -1.0, -1.0], [2.0, 0.0, 0.0, 0.0]])

    projected = project_modes(values, contract=build_contract())

    np.testing.assert_allclose(projected[0], [0.0, 1.0, 0.0, 0.0])
    np.testing.assert_allclose(projected[1], [0.5, 0.5, 1.0, 0.0])


def _summary(
    *,
    offdiag: float,
    cross_ratio: float,
    differential: float,
    settling: float,
    common: float = 1.0,
    peak: float = 1.0,
    rocof: float = 1.0,
    guards: bool = True,
) -> dict[str, object]:
    conditions = {
        "a": {
            "differential_frequency_energy_hz2_s": differential,
            "differential_settling_seconds": settling,
            "common_frequency_iae_hz_s": common,
            "worst_device_peak_abs_hz": peak,
            "max_rocof_hz_per_s": rocof,
        },
        "b": {
            "differential_frequency_energy_hz2_s": differential,
            "differential_settling_seconds": settling,
            "common_frequency_iae_hz_s": common,
            "worst_device_peak_abs_hz": peak,
            "max_rocof_hz_per_s": rocof,
        },
    }
    return {
        "probe": {
            "off_diagonal_response_energy_hz2_s": offdiag,
            "off_diagonal_to_diagonal_energy_ratio": cross_ratio,
        },
        "disturbance": {
            "mean_differential_frequency_energy_hz2_s": differential,
            "mean_differential_settling_seconds": settling,
            "conditions": conditions,
        },
        "guards_pass": guards,
    }


def test_development_selection_is_eligible_then_deterministically_ranked() -> None:
    contract = build_contract()
    summaries = {
        "zero_feedback": _summary(
            offdiag=12.0, cross_ratio=0.6, differential=12.0, settling=6.0
        ),
        "local_diagonal_pi": _summary(
            offdiag=10.0, cross_ratio=0.5, differential=10.0, settling=5.0
        ),
    }
    for index, candidate in enumerate(contract["distributed_candidates"]):
        factor = 0.90 + 0.01 * index
        summaries[candidate["arm_id"]] = _summary(
            offdiag=10.0 * factor,
            cross_ratio=0.5 * factor,
            differential=10.0 * factor,
            settling=4.0,
        )

    selection = select_development_candidate(summaries, contract=contract)

    assert selection["classification"] == "DEVELOPMENT-CANDIDATE-SELECTED"
    assert selection["selected_arm_id"] == "distributed_ks0p5_kc0p5"
    assert selection["training_authorized"] is False


def test_held_out_pass_requires_cross_and_differential_gain_without_harm() -> None:
    contract = build_contract()
    selected = "distributed_ks0p5_kc0p5"
    development = {
        "classification": "DEVELOPMENT-CANDIDATE-SELECTED",
        "selected_arm_id": selected,
    }
    evaluation = {
        "zero_feedback": _summary(
            offdiag=12.0, cross_ratio=0.6, differential=12.0, settling=6.0
        ),
        "local_diagonal_pi": _summary(
            offdiag=10.0, cross_ratio=0.5, differential=10.0, settling=5.0
        ),
        selected: _summary(
            offdiag=9.0,
            cross_ratio=0.45,
            differential=9.0,
            settling=4.8,
            common=1.02,
            peak=1.05,
            rocof=1.05,
        ),
    }

    result = classify_summaries(development, evaluation, contract=contract)

    assert result["classification"] == "DETERMINISTIC-DECOUPLING-PASS"
    assert all(result["checks"].values())
    assert result["training_authorized"] is False
    assert result["next_gate"] == "non_learning_time_varying_headroom"


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("unsafe", "STOP-UNSAFE-CONTROL"),
        ("cross", "STOP-NO-CROSS-DECOUPLING"),
        ("differential", "STOP-NO-DIFFERENTIAL-BENEFIT"),
        ("common", "STOP-COMMON-MODE-HARM"),
    ],
)
def test_held_out_classifier_returns_each_typed_stop(
    mutation: str,
    expected: str,
) -> None:
    selected = "distributed_ks0p5_kc0p5"
    development = {
        "classification": "DEVELOPMENT-CANDIDATE-SELECTED",
        "selected_arm_id": selected,
    }
    candidate = _summary(
        offdiag=9.0,
        cross_ratio=0.45,
        differential=9.0,
        settling=4.8,
        common=1.02,
        peak=1.05,
        rocof=1.05,
    )
    if mutation == "unsafe":
        candidate["guards_pass"] = False
    elif mutation == "cross":
        candidate["probe"]["off_diagonal_response_energy_hz2_s"] = 9.6
    elif mutation == "differential":
        candidate["disturbance"][
            "mean_differential_frequency_energy_hz2_s"
        ] = 9.6
    else:
        for row in candidate["disturbance"]["conditions"].values():
            row["common_frequency_iae_hz_s"] = 1.06
    evaluation = {
        "zero_feedback": _summary(
            offdiag=12.0, cross_ratio=0.6, differential=12.0, settling=6.0
        ),
        "local_diagonal_pi": _summary(
            offdiag=10.0, cross_ratio=0.5, differential=10.0, settling=5.0
        ),
        selected: candidate,
    }

    result = classify_summaries(development, evaluation)

    assert result["classification"] == expected
    assert result["training_authorized"] is False


def test_raw_probe_summary_retains_absolute_and_normalized_cross_energy() -> None:
    contract = copy.deepcopy(build_contract())
    contract["steps"] = 2
    records: list[dict[str, object]] = []
    modes = list(contract["mode_ids"])
    for mode_index, input_mode in enumerate(modes):
        input_basis = np.asarray(contract["modes"][input_mode], dtype=float)
        cross_basis = np.asarray(
            contract["modes"][modes[(mode_index + 1) % len(modes)]],
            dtype=float,
        )
        for sign_name, sign in (("positive", 1.0), ("negative", -1.0)):
            frequency = 60.0 + sign * (0.1 * input_basis + 0.05 * cross_basis)
            rows = []
            for step_index in range(2):
                rows.append(
                    {
                        "step_index": step_index,
                        "time": 0.7 + 0.2 * step_index,
                        "freq_hz_physical": frequency.tolist(),
                        "requested_power_system_pu": [0.0] * 4,
                        "commanded_power_system_pu": [0.0] * 4,
                        "achieved_power_system_pu": [0.0] * 4,
                        "common_request_system_pu": [0.0] * 4,
                        "differential_request_system_pu": [0.0] * 4,
                        "soc": [0.5] * 4,
                        "saturation_reasons": [[], [], [], []],
                        "md_action_norm": np.zeros((4, 2)).tolist(),
                        "tds_failed": False,
                    }
                )
            records.append(
                {
                    "experiment_kind": "probe",
                    "condition_id": "probe",
                    "input_mode": input_mode,
                    "sign": sign_name,
                    "steps": rows,
                    "completed_steps": 2,
                    "tds_failed": False,
                    "failure": None,
                }
            )

    summary = summarize_arm_records(records, contract=contract)

    assert summary["probe"]["diagonal_response_energy_hz2_s"] == pytest.approx(
        0.016
    )
    assert summary["probe"]["off_diagonal_response_energy_hz2_s"] == pytest.approx(
        0.004
    )
    assert summary["probe"][
        "off_diagonal_to_diagonal_energy_ratio"
    ] == pytest.approx(0.25)
    assert summary["guards_pass"] is True
