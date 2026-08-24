"""Offline tests for the prospective source-factorial estimand and power plan."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

from andes_rl_kundur.evaluation.source_factorial_design import (
    REGISTERED_EFFECTS,
    build_power_plan,
    exact_signed_rank_critical,
    exact_signed_rank_p_one_sided,
    holm_decisions,
    seed_effects,
    simulate_signed_rank_power,
)

ROOT = Path(__file__).resolve().parents[1]


def _factorial_rows(*, omit: tuple[str, str, int] | None = None):
    rows = []
    for actor in ("N", "P"):
        for critic in ("N", "P"):
            for reward in (0, 1):
                if omit == (actor, critic, reward):
                    continue
                a = int(actor == "P")
                c = int(critic == "P")
                log_loss = 0.2 * a + 0.3 * c + 0.4 * a * c + 0.5 * c * reward
                rows.append({
                    "stage": "final",
                    "seed": 1,
                    "actor_source": actor,
                    "critic_source": critic,
                    "reward_access": reward,
                    "profile": "p1",
                    "disturbance_differential_energy": math.exp(log_loss),
                })
    return rows


def test_seed_effects_use_registered_equal_weight_contrasts() -> None:
    effects = seed_effects(
        _factorial_rows(), expected_seeds=(1,), expected_profiles=("p1",)
    )
    assert effects["actor_main"][1] == pytest.approx(0.4)
    assert effects["critic_main"][1] == pytest.approx(0.75)
    assert effects["actor_x_critic"][1] == pytest.approx(-0.4)
    assert effects["critic_x_reward"][1] == pytest.approx(0.5)


def test_missing_cell_invalidates_whole_seed() -> None:
    with pytest.raises(ValueError, match="missing factorial cells"):
        seed_effects(
            _factorial_rows(omit=("P", "P", 1)),
            expected_seeds=(1,),
            expected_profiles=("p1",),
        )


def test_wholly_absent_seed_or_profile_is_not_inferred_away() -> None:
    rows = _factorial_rows()
    with pytest.raises(ValueError, match="missing factorial cells"):
        seed_effects(
            rows, expected_seeds=(1, 2), expected_profiles=("p1",)
        )
    with pytest.raises(ValueError, match="missing factorial cells"):
        seed_effects(
            rows, expected_seeds=(1,), expected_profiles=("p1", "p2")
        )


def test_exact_signed_rank_grid_matches_six_seed_boundary() -> None:
    assert exact_signed_rank_critical(6, 0.025) == 21
    effects = [0.11, 0.12, 0.13, 0.14, 0.15, 0.16]
    assert exact_signed_rank_p_one_sided(effects, null=0.10) == pytest.approx(1 / 64)


def test_exact_signed_rank_rejects_ties_and_holm_is_step_down() -> None:
    with pytest.raises(ValueError, match="tied absolute ranks"):
        exact_signed_rank_p_one_sided([0.2, 0.0], null=0.1)
    p_values = dict(zip(REGISTERED_EFFECTS, (0.01, 0.015, 0.02, 0.2)))
    decisions = holm_decisions(p_values)
    assert decisions[REGISTERED_EFFECTS[0]]["reject"] is True
    assert decisions[REGISTERED_EFFECTS[1]]["reject"] is True
    assert decisions[REGISTERED_EFFECTS[2]]["reject"] is True
    assert decisions[REGISTERED_EFFECTS[3]]["reject"] is False
    assert decisions[REGISTERED_EFFECTS[1]]["adjusted_p"] == pytest.approx(0.045)


def test_holm_rejects_an_incomplete_or_unregistered_family() -> None:
    with pytest.raises(ValueError, match="exactly the registered four"):
        holm_decisions({name: 0.01 for name in REGISTERED_EFFECTS[:-1]})
    with pytest.raises(ValueError, match="exactly the registered four"):
        holm_decisions({**{name: 0.01 for name in REGISTERED_EFFECTS}, "extra": 0.1})


def test_power_simulation_is_deterministic() -> None:
    kwargs = {
        "n": 8,
        "alternative_log": math.log(1.20),
        "null_log": math.log(1.10),
        "sd": 0.09,
        "simulations": 2_000,
        "rng_seed": 7,
    }
    assert simulate_signed_rank_power(**kwargs) == simulate_signed_rank_power(**kwargs)


def test_registered_power_artifact_is_reproducible_and_hash_valid() -> None:
    artifact = (
        ROOT
        / "paper/yang_md_decoupling_marl/working/source_factorial_power_plan.json"
    )
    source = (
        ROOT
        / "paper/yang_md_decoupling_marl/manuscript/supplement/"
        "r477_arm_seed_profile.csv"
    )
    expected = json.loads(artifact.read_text(encoding="utf-8"))
    assert build_power_plan(source) == expected
    actual_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    recorded_sha = artifact.with_suffix(".json.sha256").read_text(
        encoding="utf-8"
    ).split()[0]
    assert actual_sha == recorded_sha
