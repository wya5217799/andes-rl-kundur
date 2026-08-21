from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r454_m4_residual_local_audit.py"
SPEC = importlib.util.spec_from_file_location("r454_runner", RUNNER)
assert SPEC is not None and SPEC.loader is not None
R454 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = R454
SPEC.loader.exec_module(R454)


def _surface(*, slope: float, curvature: float, anchor: float = 1.0):
    values = {}
    for condition_index in range(3):
        base = anchor + 0.05 * condition_index
        condition = {0.0: {0: base}}
        for epsilon in R454.EPSILONS:
            condition[epsilon] = {
                sign: base
                + slope * sign * epsilon
                + 0.5 * curvature * epsilon**2
                for sign in (-1, 1)
            }
        values[f"condition_{condition_index}"] = condition
    return values


def test_registered_basis_is_orthonormal() -> None:
    assert R454._basis_error() <= 1.0e-12


def test_expected_shards_cover_anchor_and_ten_checkpoints() -> None:
    shards = R454.expected_shard_ids()
    assert len(shards) == 33
    assert len(set(shards)) == 33
    assert sum(value.startswith("anchor|") for value in shards) == 3
    assert sum(value.startswith("checkpoint|") for value in shards) == 30


def test_centered_geometry_recovers_linear_and_quadratic_terms() -> None:
    result = R454.centered_geometry(_surface(slope=2.0, curvature=-40.0))
    assert np.isclose(result["estimates"]["0.01"]["slope"], 2.0)
    assert np.isclose(result["estimates"]["0.01"]["curvature"], -40.0)
    assert result["slope_stable_material"]
    assert result["curvature_stable_material"]
    assert result["slope_sign"] == 1
    assert result["curvature_sign"] == -1


def test_anchor_decision_tree_precedence() -> None:
    slope = R454.centered_geometry(_surface(slope=2.0, curvature=50.0))
    positive = R454.centered_geometry(_surface(slope=0.0, curvature=50.0))
    negative = R454.centered_geometry(_surface(slope=0.0, curvature=-50.0))
    weak = R454.centered_geometry(_surface(slope=0.0, curvature=-1.0))
    assert R454.classify_anchor({"one": slope}) == "IDENTITY-NOT-STATIONARY"
    assert (
        R454.classify_anchor({"one": positive})
        == "IDENTITY-POSITIVE-CURVATURE"
    )
    assert (
        R454.classify_anchor({"one": negative, "two": negative})
        == "IDENTITY-LOCAL-MAX-SUPPORTED-ON-REGISTERED-SLICE"
    )
    assert (
        R454.classify_anchor({"one": weak})
        == "IDENTITY-LOCAL-GEOMETRY-INCONCLUSIVE"
    )


def test_twin_gradient_uses_lower_q_and_averages_ties() -> None:
    q1 = np.asarray([[1.0], [3.0], [2.0]])
    q2 = np.asarray([[2.0], [1.0], [2.0 + 1.0e-10]])
    grad1 = np.asarray([[10.0], [20.0], [30.0]])
    grad2 = np.asarray([[40.0], [50.0], [60.0]])
    selected = R454.select_twin_gradient(q1, q2, grad1, grad2)
    assert np.allclose(selected[:, 0], [10.0, 50.0, 45.0])


def test_mechanism_tags_follow_registered_thresholds() -> None:
    diagnostics = []
    geometry = {}
    for index in range(10):
        key = f"arm|{index}"
        geometry[key] = {
            direction: {
                "slope_stable_material": direction == "c",
                "slope_sign": 1,
            }
            for direction in R454.DIRECTIONS
        }
        diagnostics.append(
            {
                "arm": "arm",
                "seed": index,
                "critic": {
                    "directions": {
                        direction: {
                            "material": direction == "c",
                            "sign": -1,
                        }
                        for direction in R454.DIRECTIONS
                    }
                },
                "fresh_optimizer_fixed_state_probe": {
                    "moves": index < 8,
                    "fixed_below_both": False,
                },
            }
        )
    result = R454._mechanism_tags(
        diagnostics, geometry, [0.0] * 95 + [1.0] * 5
    )
    assert result["critic"]["tag"] == "CRITIC-MISALIGNED"
    assert result["fresh_update"]["tag"] == "FRESH-UPDATE-MOVES"
    assert result["projection"]["tag"] == "PROJECTION-SUPPRESSED"
