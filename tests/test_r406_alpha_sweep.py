"""Slice-8 tests: R406 sweep decision tree."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_r406_alpha_sweep import (  # noqa: E402
    ALPHA_GRID,
    sweep_contract,
    sweep_decision,
)


def test_sweep_contract_propagates_alpha_into_candidates():
    # R406-pre-repair regression: controller_spec resolves highpass_alpha
    # from distributed_candidates, so every candidate must carry the grid
    # point or the whole sweep silently re-runs one fixed controller.
    for alpha in ALPHA_GRID:
        contract = sweep_contract(alpha)
        assert contract["highpass_alpha"] == alpha
        assert len(contract["distributed_candidates"]) == 4
        assert all(
            float(c["highpass_alpha"]) == alpha
            for c in contract["distributed_candidates"]
        )


def test_sweep_grid_is_frozen():
    assert ALPHA_GRID == (0.675, 0.625, 0.65, 0.70, 0.725, 0.75, 0.80, 0.85)


def _grid(passes):
    out = []
    for idx, (alpha, passed_arms) in enumerate(passes):
        out.append(
            {
                "alpha": alpha,
                "any_pass": bool(passed_arms),
                "arm_results": [
                    {"arm_id": arm, "passed": True} for arm in passed_arms
                ],
            }
        )
    return out


def test_no_candidate_when_everything_fails():
    d = sweep_decision(_grid([(0.675, []), (0.70, []), (0.85, [])]))
    assert d["classification"] == "SWEEP-NO-CANDIDATE"
    assert d["found_candidate"] is None


def test_found_reports_first_passing_alpha_and_arm():
    d = sweep_decision(
        _grid(
            [
                (0.675, []),
                (0.70, ["damping_arm_1"]),
                (0.725, ["damping_arm_2", "damping_arm_1"]),
            ]
        )
    )
    assert d["classification"] == "SWEEP-FOUND-CANDIDATE"
    assert d["found_candidate"] == {"alpha": 0.70, "arm_id": "damping_arm_1"}


def test_grid_order_priority_first_passing_alpha():
    d = sweep_decision(
        _grid([(0.85, ["a"]), (0.675, ["b"])])
    )
    assert d["found_candidate"]["alpha"] == 0.85
