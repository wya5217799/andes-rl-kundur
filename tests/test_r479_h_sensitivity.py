from __future__ import annotations

import copy

import pytest

from andes_rl_kundur.evaluation.r479_h_sensitivity import (
    H_LEVELS_S,
    analyze_bank,
    build_contract,
    summarize_cell,
)


def _record(h: float, scenario: str, *, peak: float = 0.1) -> dict:
    df = [peak] * 150
    freq = [[50.0 + value] * 4 for value in df]
    freq_physical = [[60.0 + 1.2 * value] * 4 for value in df]
    return {
        "cell_id": f"h{int(h)}_{scenario}",
        "h_device_s": h,
        "scenario_id": scenario,
        "n_steps": 150,
        "tds_failed": False,
        "df_traj": df,
        "traj": {
            "freq_hz": freq,
            "freq_hz_physical": freq_physical,
            "andes_nominal_frequency_hz": [60.0] * 150,
            "M_es": [[2.0 * h] * 4 for _ in df],
            "D_es": [[100.0] * 4 for _ in df],
        },
    }


def _bank() -> list[dict]:
    return [
        _record(h, scenario)
        for h in H_LEVELS_S
        for scenario in ("ls1", "ls2")
    ]


def test_contract_freezes_six_zero_action_cells() -> None:
    contract = build_contract()
    assert contract["h_levels_device_s"] == [10.0, 100.0, 300.0]
    assert contract["d0_device"] == 100.0
    assert contract["steps"] == 150
    assert len(contract["cells"]) == 6
    assert contract["claim_boundary"]["controller_ordering"] is False
    assert contract["h300_semantics"] == "stress-point-not-paper-bound"


def test_summary_checks_runtime_units_and_two_windows() -> None:
    summary = summarize_cell(_record(100.0, "ls1", peak=0.125))
    assert summary["valid"] is True
    assert summary["max_df_6s_hz"] == pytest.approx(0.125)
    assert summary["final_df_6s_hz"] == pytest.approx(0.125)
    assert summary["max_df_30s_hz"] == pytest.approx(0.125)
    assert summary["physical_max_df_6s_hz"] == pytest.approx(0.15)
    assert summary["settled_by_30s"] is True
    assert summary["settling_s_30"] == pytest.approx(0.0)


def test_rehearsal_summary_does_not_mislabel_six_seconds_as_thirty() -> None:
    record = _record(100.0, "ls1")
    for key in ("df_traj",):
        record[key] = record[key][:30]
    for key in (
        "freq_hz",
        "freq_hz_physical",
        "andes_nominal_frequency_hz",
        "M_es",
        "D_es",
    ):
        record["traj"][key] = record["traj"][key][:30]
    record["n_steps"] = 30
    summary = summarize_cell(record, expected_steps=30)
    assert summary["horizon_s"] == pytest.approx(6.0)
    assert "max_df_30s_hz" not in summary
    assert "settled_by_30s" not in summary


def test_summary_rejects_device_base_readback_drift() -> None:
    record = _record(100.0, "ls1")
    record["traj"]["M_es"][40][0] = 199.0
    summary = summarize_cell(record)
    assert summary["valid"] is False
    assert "m_readback_drift" in summary["invalid_reasons"]


def test_analysis_detects_material_open_loop_sensitivity() -> None:
    bank = _bank()
    for record in bank:
        if record["h_device_s"] == 10.0:
            record["df_traj"] = [0.12] * 150
            record["traj"]["freq_hz"] = [[50.12] * 4 for _ in range(150)]
            record["traj"]["freq_hz_physical"] = [
                [60.144] * 4 for _ in range(150)
            ]
    rehearsal = summarize_cell(_record(100.0, "ls1"))
    analysis = analyze_bank(bank, rehearsal)
    assert analysis["classification"] == "OPEN-LOOP-H-SENSITIVE"
    assert analysis["valid"] is True
    assert any(
        row["h_device_s"] == 10.0
        and row["max_df_6s_relative_change"] == pytest.approx(0.2)
        for row in analysis["comparisons"]
    )


def test_analysis_rejects_incomplete_bank() -> None:
    bank = _bank()[:-1]
    rehearsal = summarize_cell(_record(100.0, "ls1"))
    analysis = analyze_bank(bank, rehearsal)
    assert analysis["classification"] == "ENGINEERING-INVALID"
    assert analysis["valid"] is False
    assert "cell_identity_mismatch" in analysis["invalid_reasons"]


def test_analysis_rejects_rehearsal_anchor_mismatch() -> None:
    bank = _bank()
    rehearsal_record = copy.deepcopy(_record(100.0, "ls1"))
    rehearsal_record["df_traj"] = [0.2] * 150
    rehearsal_record["traj"]["freq_hz"] = [[50.2] * 4 for _ in range(150)]
    rehearsal_record["traj"]["freq_hz_physical"] = [
        [60.24] * 4 for _ in range(150)
    ]
    analysis = analyze_bank(bank, summarize_cell(rehearsal_record))
    assert analysis["classification"] == "ENGINEERING-INVALID"
    assert "h100_rehearsal_anchor_mismatch" in analysis["invalid_reasons"]
