from __future__ import annotations

import pytest

from andes_rl_kundur.evaluation.model_first_profile_feasibility import (
    ProfileBankFeasibilityError,
    require_profile_bank_feasible,
)
from scripts import run_r340_fresh_model_validation as r340


def _build_r340_contract(spec: dict[str, object]):
    return r340._r340_profile_contract(
        channel=spec["channel"],
        shape=str(spec["profile_key"]),
        sign=str(spec["sign"]),
    )


def test_r340_bank_is_rejected_before_sealing_with_all_infeasible_rows() -> None:
    with pytest.raises(ProfileBankFeasibilityError) as captured:
        require_profile_bank_feasible(r340._record_specs(), _build_r340_contract)

    failures = captured.value.failures
    assert len(failures) == 4
    assert {
        (
            row["point"],
            row["channel_device_idx"],
            row["waveform"],
            row["amplitude_system_pu"],
            row["sign"],
            row["error_message"],
        )
        for row in failures
    } == {
        (
            point,
            "PQ_Bus15",
            waveform,
            0.07,
            "negative",
            "negative load during the profile is forbidden",
        )
        for point in ("HV0", "HV1")
        for waveform in ("held_pulse_unit", "two_pulse_unit")
    }


def test_feasible_subset_passes_without_creating_an_artifact() -> None:
    feasible = [
        row
        for row in r340._record_specs()
        if not (
            row["channel"] is not None
            and row["channel"]["device_idx"] == "PQ_Bus15"
            and row["amplitude_system_pu"] == 0.07
            and row["sign"] == "negative"
        )
    ]

    assert require_profile_bank_feasible(feasible, _build_r340_contract) is None
