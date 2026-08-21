from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_r458_dev_select_eval_validate_test",
    ROOT / "scripts/run_r458_dev_select_eval_validate.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _static() -> dict[str, float | bool]:
    return {
        "disturbance_differential_energy": 1.0,
        "off_diagonal_response_energy": 1.0,
        "common_frequency_iae_hz_s": 1.0,
        "worst_unit_peak_hz": 1.0,
        "worst_rocof_hz_s": 1.0,
        "action_rms": 1.0,
        "action_total_variation": 1.0,
        "action_saturation_fraction": 0.0,
        "valid": True,
    }


def test_candidate_sequence_reused_verbatim_from_r452() -> None:
    rows = MODULE.candidates()
    assert Counter(row["k"] for row in rows) == {2: 25, 3: 125, 5: 200}
    assert MODULE.R452.candidate_sequence_sha256() == MODULE.R452.EXPECTED_CANDIDATE_SHA256


def test_shard_inventories_cover_development_and_evaluation_only() -> None:
    dev = MODULE.expected_dev_shard_ids()
    ev = MODULE.expected_eval_shard_ids()
    assert len(dev) == 34 and len(set(dev)) == 34
    assert len(ev) == 8 and len(set(ev)) == 8
    assert sum(s.startswith("dev|candidate|") for s in dev) == 32
    assert sum(s.startswith("dev|static|") for s in dev) == 2
    assert sum(s.startswith("eval|static|") for s in ev) == 4
    assert sum(s.startswith("eval|winner|") for s in ev) == 4


def test_guard_boundary_is_inclusive() -> None:
    static = _static()
    boundary = {
        **static,
        "disturbance_differential_energy": 0.95,
        "off_diagonal_response_energy": 0.95,
        "common_frequency_iae_hz_s": 1.03,
        "worst_unit_peak_hz": 1.03,
        "worst_rocof_hz_s": 1.03,
        "action_rms": 1.10,
        "action_total_variation": 1.10,
        "action_saturation_fraction": 0.05,
    }
    guard = MODULE.candidate_guard(boundary, static)
    assert guard["joint_endpoint_eligible"]
    assert guard["common_clean"]
    assert guard["action_clean"]
    assert guard["saturation_pass"]
    assert guard["joint_guard_feasible"]


def test_selection_priority_ordering_matches_plan() -> None:
    # _guard_margin exposes exactly the seven registered relative violations;
    # a negative value means inside the frozen guard.
    static = _static()
    clean = {
        **static,
        "disturbance_differential_energy": 0.9,
        "off_diagonal_response_energy": 0.9,
        "common_frequency_iae_hz_s": 1.0,
        "worst_unit_peak_hz": 1.0,
        "worst_rocof_hz_s": 1.0,
        "action_rms": 1.0,
        "action_total_variation": 1.0,
        "action_saturation_fraction": 0.0,
    }
    margin = MODULE._guard_margin(static, clean)
    assert all(value <= 1e-12 for key, value in margin.items() if not key.startswith("_"))
    assert MODULE.candidate_guard(clean, static)["joint_guard_feasible"]


def test_contract_pins_development_only_selection_then_evaluation() -> None:
    contract = MODULE.build_contract()["r458"]
    assert contract["development_profile_ids"] == ["dev_a", "dev_b"]
    assert contract["evaluation_profile_ids"] == ["eval_a", "eval_b", "eval_c", "eval_d"]
    assert contract["candidate_sequence_sha256"] == MODULE.R452.EXPECTED_CANDIDATE_SHA256
    assert contract["selection_rule"]["priority_1"]
    assert contract["selection_rule"]["priority_2"]
    assert contract["selection_rule"]["priority_3"]
