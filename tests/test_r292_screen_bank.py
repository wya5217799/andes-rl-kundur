from __future__ import annotations

import json
from pathlib import Path

import pytest

from andes_rl_kundur.evaluation.r292_screen_bank import (
    assess_r292_screened_bank,
)

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_BANK = ROOT / "results/r292_fresh_bank/candidate_bank.json"
PLANT = "r292_q0_common_pulse_plus_droop_pi"


def _eligible_rows(bank: dict[str, object]) -> list[dict[str, object]]:
    return [
        {
            "scenario": scenario["name"],
            "plant": PLANT,
            "delta_u": scenario["delta_u"],
            "completed": True,
            "tds_failed": False,
            "n_steps": 300,
            "requested_steps": 300,
            "physical_valid": True,
            "performance_endpoints_inspected": False,
            "trace_sha256": f"{index:064x}",
        }
        for index, scenario in enumerate(bank["scenarios"], start=1)
    ]


def test_r292_bank_assessment_accepts_all_valid_q0_rows() -> None:
    bank = json.loads(CANDIDATE_BANK.read_text(encoding="utf-8"))

    assessment = assess_r292_screened_bank(
        bank,
        _eligible_rows(bank),
        generated_bank_sha256="a" * 64,
        completion_evidence_sha256="b" * 64,
        controller_trace_count=0,
    )

    assert assessment["decision"]["classification"] == "PASS"
    assert assessment["formal_bank"]["scenario_count"] == 24
    assert assessment["feasibility_contract"]["expected_plants"] == [PLANT]
    assert assessment["formal_bank"]["selection_rule"] == (
        "all-and-only eligible R292 q0 physical-screen rows"
    )


def test_r292_bank_assessment_rejects_wrong_plant() -> None:
    bank = json.loads(CANDIDATE_BANK.read_text(encoding="utf-8"))
    rows = _eligible_rows(bank)
    rows[0]["plant"] = "storage_zero"

    with pytest.raises(ValueError, match="R292 q0 plant"):
        assess_r292_screened_bank(
            bank,
            rows,
            generated_bank_sha256="a" * 64,
            completion_evidence_sha256="b" * 64,
            controller_trace_count=0,
        )
