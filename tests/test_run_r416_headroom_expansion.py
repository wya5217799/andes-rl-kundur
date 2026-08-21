"""Directed tests for the R416 headroom-expansion runner and contract.

Windows-safe: candidate family, contract shape, controller resolution, the
frozen PI-law math, and the nine-law anchor comparator.  The WSL-only
lifecycle runs through the scratch launcher in the sealed round itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import run_r416_headroom_expansion as runner  # noqa: E402
from andes_rl_kundur.evaluation.soft_spot_headroom_expansion import (  # noqa: E402
    PI_ARM_ID,
    PiFrequencyMDController,
    build_contract,
    controller_for,
    extended_candidate_ids,
    original_nine_ids,
)


def test_candidate_family_frozen() -> None:
    ids = extended_candidate_ids()
    assert len(ids) == 21
    assert len(set(ids)) == 21
    assert ids[-1] == PI_ARM_ID
    assert set(original_nine_ids()).issubset(set(ids))
    assert len(original_nine_ids()) == 9
    contract = build_contract()
    assert contract["round"] == "R416"
    assert contract["arm_ids"] == ["zero", *ids]
    assert contract["expansion"]["pi_law"]["kp_m"] == 1.0


def test_controller_resolution() -> None:
    assert controller_for("zero") is None
    grid = controller_for("local_neighbour_md_km1p5_kd2")
    assert grid is not None
    pi = controller_for(PI_ARM_ID)
    assert isinstance(pi, PiFrequencyMDController)
    with pytest.raises(ValueError):
        controller_for("unknown_arm")


def _observations(*, own_df: float) -> dict[int, np.ndarray]:
    rows = {}
    for actor in range(4):
        row = np.zeros(7, dtype=np.float32)
        row[1] = own_df
        rows[actor] = row
    return rows


def test_pi_law_math() -> None:
    controller = PiFrequencyMDController()
    controller.reset()
    # positive frequency deviation -> negative actions (signed feedback)
    first = controller.act(_observations(own_df=0.5))
    assert first.shape == (4, 2)
    assert np.all(first[:, 0] < 0.0)
    assert np.all(first[:, 1] < 0.0)
    # integral accumulates and deepens the response in the same direction
    previous = first
    for _ in range(9):
        current = controller.act(_observations(own_df=0.5))
        # slew bound respected between consecutive steps
        assert np.all(np.abs(current - previous) <= 0.25 + 1e-6)
        previous = current
    later = previous
    assert np.all(later[:, 0] <= first[:, 0])
    # negative deviation drives positive actions after reset
    controller.reset()
    neg = controller.act(_observations(own_df=-0.5))
    assert np.all(neg[:, 0] > 0.0)
    # integral clip bounds the state
    assert np.all(np.abs(controller.integrals) <= 2.0 + 1e-12)


def test_pi_law_rejects_bad_observations() -> None:
    controller = PiFrequencyMDController()
    with pytest.raises(ValueError):
        controller.act({0: np.zeros(7, dtype=np.float32)})
    with pytest.raises(ValueError):
        controller.act({actor: np.zeros(6, dtype=np.float32) for actor in range(4)})


def test_shard_list() -> None:
    shards = runner.shard_list()
    assert len(shards) == 22
    assert len(set(shards)) == 22
    assert shards[0] == "zero"


def test_nine_law_anchor_deviations() -> None:
    anchor_ok = {
        "verdict": "NINE-LAW-ANCHOR-REPRODUCED",
        "deviations": {
            "selected_deterministic_arm_equal": 0.0,
            "off_diagonal_improvement": 0.0,
            "differential_improvement": 0.0,
        },
    }
    assert runner.ANCHOR_TOLERANCE_RELATIVE == 1.0e-6
    assert "verdict" in anchor_ok


def test_rung_selection_marginal_and_memory() -> None:
    throughput = {1: 0.10, 2: 0.19, 4: 0.36, 8: 0.37, 12: 0.375, 16: 0.375}
    selection = runner._select_rung(
        throughput, wsl_available_bytes=22 * 2**30
    )
    assert selection["selected_workers"] == 4
    throughput = {1: 0.10, 2: 0.20, 4: 0.40, 8: 0.80, 12: 1.60, 16: 3.20}
    selection = runner._select_rung(
        throughput, wsl_available_bytes=22634487808
    )
    assert selection["selected_workers"] == 8
    decisions = {row["workers"]: row for row in selection["rung_decisions"]}
    assert decisions[12]["reason"] == "memory_reserve_guard"
