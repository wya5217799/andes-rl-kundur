"""R436 runner drift-pinning tests (Windows-safe, no ANDES import).

Pins the R436 contract pieces that do not require ANDES: reward signs,
observation slot semantics, residual scaling, ratio computation, and the
pre-registered classifier.  The ANDES-touching paths (env build, eval job
execution) are covered by the rehearsal inside the WSL runner itself.

Run: python -m pytest tests/test_run_r436_energy_residual_sac.py -q
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

_spec = importlib.util.spec_from_file_location(
    "_r436_runner", ROOT / "scripts/run_r436_energy_residual_sac.py"
)
r436 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = r436
_spec.loader.exec_module(r436)


def test_contract_frozen_shape() -> None:
    contract = r436.build_contract()
    assert contract["r436"]["training_seeds"] == list(r436.TRAINING_SEEDS)
    assert contract["r436"]["learning_arms"] == list(r436.LEARNING_ARMS)
    assert len(contract["r436"]["topology_variants"]) == 10
    assert contract["r436"]["total_interaction_steps"] == 43_200
    assert contract["r436"]["obs_dim"] == 7
    assert contract["r436"]["action_dim"] == 1
    assert contract["r436"]["residual_scale"] == pytest.approx(0.70)
    assert contract["r436"]["formulas_sha256"]


def test_obs_slots_and_masking() -> None:
    frequencies = np.asarray([60.0, 60.06, 59.94, 60.0], dtype=float)
    previous = np.asarray([60.0, 60.0, 60.0, 60.0], dtype=float)
    p_es = np.asarray([100.0, 200.0, 300.0, 400.0], dtype=float)
    prev_res = np.asarray([0.1, -0.2, 0.3, -0.4], dtype=float)
    joint_msg = r436._joint_obs(frequencies, previous, p_es, prev_res, masked=False)
    joint_masked = r436._joint_obs(frequencies, previous, p_es, prev_res, masked=True)
    assert joint_msg.shape == (4, 7)
    assert joint_msg.dtype == np.float32
    # slot 0 = per-unit frequency deviation
    assert joint_msg[1, 0] == pytest.approx(0.06 / 60.0)
    assert joint_msg[2, 0] == pytest.approx(-0.06 / 60.0)
    # slot 2 = normalized P_es
    assert joint_msg[3, 2] == pytest.approx(400.0 / 600.0)
    # slot 5 = previous residual
    assert joint_msg[3, 5] == pytest.approx(-0.4)
    # slot 6 = bias
    assert np.all(joint_msg[:, 6] == 1.0)
    # masking zeroes neighbour slots 3-4 only
    assert np.all(joint_masked[:, 3:5] == 0.0)
    assert np.allclose(joint_masked[:, [0, 1, 2, 5, 6]], joint_msg[:, [0, 1, 2, 5, 6]])


def test_reward_signs_and_message_sensitivity() -> None:
    frequencies = np.asarray([60.0, 60.03, 59.97, 60.0], dtype=float)
    previous = np.asarray([60.0, 60.0, 60.0, 60.0], dtype=float)
    p_es = np.zeros(4, dtype=float)
    residuals = np.asarray([0.2, -0.1, 0.05, -0.2], dtype=float)
    obs = r436._joint_obs(frequencies, previous, p_es, residuals, masked=False)
    reward = r436._reward(obs, residuals, masked=False)
    assert reward.shape == (4,)
    assert np.all(reward <= 0.0)  # all terms are penalties
    assert np.all(np.isfinite(reward))
    # a larger residual magnitude must lower r_abs (more negative)
    residuals_large = residuals * 2.0
    obs_large = r436._joint_obs(frequencies, previous, p_es, residuals_large, masked=False)
    reward_large = r436._reward(obs_large, residuals_large, masked=False)
    assert float(np.sum(reward_large)) < float(np.sum(reward))


def test_gradient_direction_probe() -> None:
    probe = r436._gradient_direction_probe(r436.NO_MESSAGE_ARM)
    assert probe["finite"]
    assert probe["reward_negative"]
    assert probe["r_abs_alignment_positive"]


def test_residual_scale_matches_baseline_clip() -> None:
    assert r436.RESIDUAL_SCALE == r436.ACTION_CLIP
    assert r436.ACTION_CLIP == 0.70


def test_ratio_computation() -> None:
    candidate = {
        "disturbance": {"mean_differential_frequency_energy_hz2_s": 0.9},
        "probe": {"off_diagonal_response_energy_hz2_s": 0.8},
        "guards_pass": True,
        "guard_errors": [],
    }
    local = {
        "disturbance": {"mean_differential_frequency_energy_hz2_s": 1.0},
        "probe": {"off_diagonal_response_energy_hz2_s": 1.0},
        "guards_pass": True,
        "guard_errors": [],
    }
    ratios = r436._ratio_from_summaries(candidate, local)
    assert ratios["r_d"] == pytest.approx(0.9)
    assert ratios["r_cross"] == pytest.approx(0.8)
    assert ratios["strict_cross_pass"]
    assert ratios["guards_pass"]


def test_classifier_no_learning_increment() -> None:
    def arm(r_d: float, r_cross: float, guards: bool = True) -> dict:
        return {
            "median_r_d": r_d,
            "median_r_cross": r_cross,
            "guards_pass_median": guards,
            "per_seed_ratios": [],
        }

    bp = {"r_d": 0.90, "r_cross": 0.50, "guards_pass": True, "guard_errors": []}
    per_variant = {
        "nominal": {
            "bandpass": dict(bp, **{"r_d": 0.938947, "r_cross": 0.539791}),
            r436.MESSAGE_ARM: arm(0.95, 0.60),
            r436.NO_MESSAGE_ARM: arm(0.95, 0.60),
        },
        "out_Line_4": {
            "bandpass": bp,
            r436.MESSAGE_ARM: arm(0.96, 0.62),
            r436.NO_MESSAGE_ARM: arm(0.96, 0.62),
        },
    }
    result = r436._classify(per_variant)
    assert result["nominal_anchor_passed"]
    assert result["classification"] == "NO-LEARNING-INCREMENT"


def test_classifier_message_increment() -> None:
    def arm(r_d: float, r_cross: float, guards: bool = True) -> dict:
        return {
            "median_r_d": r_d,
            "median_r_cross": r_cross,
            "guards_pass_median": guards,
            "per_seed_ratios": [],
        }

    bp = {"r_d": 0.90, "r_cross": 0.50, "guards_pass": True, "guard_errors": []}
    per_variant = {
        "nominal": {
            "bandpass": dict(bp, **{"r_d": 0.938947, "r_cross": 0.539791}),
            r436.MESSAGE_ARM: arm(0.80, 0.55),
            r436.NO_MESSAGE_ARM: arm(0.95, 0.60),
        },
    }
    result = r436._classify(per_variant)
    assert result["classification"] == "MESSAGE-INCREMENT"


def test_classifier_learned_beyond_deterministic() -> None:
    def arm(r_d: float, r_cross: float, guards: bool = True) -> dict:
        return {
            "median_r_d": r_d,
            "median_r_cross": r_cross,
            "guards_pass_median": guards,
            "per_seed_ratios": [],
        }

    bp = {"r_d": 0.90, "r_cross": 0.50, "guards_pass": True, "guard_errors": []}
    per_variant = {
        "nominal": {
            "bandpass": dict(bp, **{"r_d": 0.938947, "r_cross": 0.539791}),
            r436.MESSAGE_ARM: arm(0.94, 0.55),
            r436.NO_MESSAGE_ARM: arm(0.94, 0.55),
        },
        "out_Line_7": {
            "bandpass": dict(bp, **{"r_d": 0.98, "r_cross": 0.60}),  # reference fails
            r436.MESSAGE_ARM: arm(0.90, 0.50),  # learned passes
            r436.NO_MESSAGE_ARM: arm(0.99, 0.99, guards=False),
        },
    }
    result = r436._classify(per_variant)
    assert result["classification"] == "LEARNED-BEYOND-DETERMINISTIC"
    assert "out_Line_7" in result["beyond_deterministic_variants"][r436.MESSAGE_ARM]
