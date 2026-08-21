from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_r455_m1_dual_saturation",
    ROOT / "scripts/run_r455_m1_dual_saturation.py",
)
assert SPEC is not None and SPEC.loader is not None
R455 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R455)


def test_contract_freezes_complete_factorial_and_physical_counts() -> None:
    contract = R455.build_contract()
    assert len(contract["cells"]) == 5
    assert len(R455.state_shard_ids()) == 6
    assert len(R455.eval_shard_ids()) == 30
    assert contract["state_trajectory_count"] == 144
    assert contract["state_transition_count"] == 4320
    assert contract["evaluation_trajectory_count"] == 720
    assert contract["evaluation_transition_count"] == 21600
    assert contract["actor_update_steps"] == 16
    assert contract["dual_replay_steps"] == 20


def test_factorial_contains_two_by_two_and_profile_cell() -> None:
    cells = {row["cell_id"]: row for row in R455.CELLS}
    assert set(cells) == {
        "U10_eta050",
        "U100_eta050",
        "U10_eta005",
        "U100_eta005",
        "profile_U100_eta050",
    }
    assert cells["profile_U100_eta050"]["per_profile"] is True
    assert all(cells[name]["per_profile"] is False for name in set(cells) - {"profile_U100_eta050"})


def test_episode_residuals_match_frozen_r425_formulas() -> None:
    reference = {"profiles": {"p": {"action_rms_ref": 1.0, "tv_ref_scenario_mean": 2.0}}}
    actions = R455.np.ones((2, 4, 2), dtype=float)
    previous = R455.np.zeros_like(actions)
    rms, tv = R455._episode_residuals(actions, previous, profile_id="p", reference=reference)
    assert rms == pytest.approx(1.0 / 1.1**2 - 1.0)
    assert tv == pytest.approx(2.0 / (1.1 * 2.0) - 1.0)


def test_guard_checks_use_frozen_reference_factors() -> None:
    reference = {
        "common_frequency_iae_hz_s": 1.0,
        "worst_unit_peak_hz": 1.0,
        "worst_rocof_hz_s": 1.0,
        "action_rms": 1.0,
        "action_total_variation": 1.0,
    }
    candidate = {
        **reference,
        "common_frequency_iae_hz_s": 1.03,
        "action_rms": 1.10,
        "action_total_variation": 1.10,
        "action_saturation_fraction": 0.05,
        "minimum_record_total_variation": 2.0e-6,
        "minimum_record_action_row_dispersion": 2.0e-6,
    }
    assert all(R455.guard_checks(candidate, reference).values())
    candidate["action_rms"] = 1.100001
    assert not R455.guard_checks(candidate, reference)["action_rms_no_harm"]


def test_contract_binds_parent_checkpoint_hashes() -> None:
    inventory = R455._checkpoint_inventory()
    assert len(inventory) == 6
    assert all(len(row["sha256"]) == 64 for row in inventory)
