"""Targeted contract, shape, and inference tests for the R482 successor runner.

Windows-side only: every test here runs without WSL/ANDES. The physical
guards (basegen/rehearse/prepare) raise on non-POSIX and are asserted to fail
closed, never executed.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from andes_rl_kundur.evaluation import r482_analysis
from andes_rl_kundur.evaluation.source_factorial_design import (
    exact_signed_rank_p_one_sided,
)

_spec = importlib.util.spec_from_file_location(
    "_r482_under_test", ROOT / "scripts/run_r482_u2_confirmatory.py"
)
assert _spec is not None and _spec.loader is not None
runner = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = runner
_spec.loader.exec_module(runner)


# ---------------------------------------------------------------------------
# Roster, cells, shard lists
# ---------------------------------------------------------------------------


def test_dev_roster():
    assert len(runner.DEV_CELLS) == 16
    assert all(arm == "an_cn_r1" for arm, _seed in runner.DEV_CELLS[:8])
    assert all(seed in range(601, 609) for _arm, seed in runner.DEV_CELLS[:8])
    assert all(arm == "an_cn_r1_rms" for arm, _seed in runner.DEV_CELLS[8:])
    assert all(seed in range(609, 617) for _arm, seed in runner.DEV_CELLS[8:])
    assert len(runner.DEV_SHARD_IDS) == 16
    assert runner.DEV_SHARDS == ROOT / "tmp/andes/r482_dev_shards.json"
    assert not set(runner.DEV_SEEDS) & set(runner.SEEDS)
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert 'parts[0] == "dev"' in source
    assert '"dev": DEV_SHARD_IDS' in source
    assert "r482_formal_go.json" in source


def test_dev_shard_fails_closed_on_windows(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run_r482", "shard", "dev|an_cn_r1|601"])
    with pytest.raises(RuntimeError) as error:
        runner._main()
    assert "WSL" in str(error.value)


def test_dev_guard_wraps_dev_training(monkeypatch):
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert "_terminal_guarded_environment()" in source


def test_factorial_training_uses_captured_parent(monkeypatch):
    calls = []
    monkeypatch.setattr(
        runner,
        "_PARENT_TRAIN_ARM_SEED",
        lambda arm, seed: calls.append((arm, seed)) or "parent-result",
    )
    assert runner.train_arm_seed("an_cn_r0", 501) == "parent-result"
    assert calls == [("an_cn_r0", 501)]


def test_pipeline_resumes_without_restarting_development_wave():
    source = (ROOT / "scripts/run_r482_detached_pipeline.sh").read_text(
        encoding="utf-8"
    )
    assert "if [[ -d results/research_loop/r482_u2_confirmatory/dev ]]" in source
    assert source.index("development-completeness") < source.index(
        "if [[ ! -f tmp/andes/r482_formal_go.json ]]"
    )
    assert "owner go-file predates the development wave" in source


def test_owner_approval_requires_round_and_source(tmp_path, monkeypatch):
    approval = tmp_path / "OWNER_APPROVED.json"
    approval.write_text(
        json.dumps({"round": "R482", "approved": True, "source": "owner message"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "OWNER_APPROVED", approval)
    assert runner.owner_approval_check()["approved"] is True


def test_formal_go_requires_development_review(tmp_path, monkeypatch):
    go_file = tmp_path / "r482_formal_go.json"
    go_file.write_text(
        json.dumps(
            {
                "round": "R482",
                "approved": True,
                "development_reviewed": True,
                "source": "owner continuation message",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "FORMAL_GO", go_file)
    monkeypatch.setattr(runner, "development_check", lambda: {"passed": True})
    assert runner.formal_go_check()["development_reviewed"] is True


def test_development_check_rejects_missing_wave(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "OUT", tmp_path / "out")
    monkeypatch.setattr(runner, "load_seal", lambda: {})
    with pytest.raises(RuntimeError, match="development wave incomplete/invalid"):
        runner.development_check()


def test_formal_manifest_implementation_excludes_dev_and_does_not_delegate():
    source = Path(runner.__file__).read_text(encoding="utf-8")
    body = source[source.index("def formal_manifest"):source.index("def write_eta_recalibration")]
    assert '"dev" in path.relative_to(OUT).parts' in body
    assert "core.formal_manifest" not in body


def test_seed_and_arm_roster():
    assert runner.SEEDS == tuple(range(501, 527))
    assert len(runner.FACTORIAL_ARMS) == 8
    assert runner.PHASE3B_ARM == "an_cn_r1_rms"
    assert len(runner.RETRAIN_ARMS) == 9
    assert runner.REUSED_CELLS == ()


def test_cell_order_and_waves():
    assert len(runner.RETRAIN_CELLS) == 234
    assert all(arm == runner.PHASE3B_ARM for arm, _seed in runner.RETRAIN_CELLS[:26])
    factorial_tail = runner.RETRAIN_CELLS[26:]
    assert all(arm in runner.FACTORIAL_ARMS for arm, _seed in factorial_tail)
    assert len(runner.TRAIN_SHARD_IDS) == 234
    assert len(runner.TRAIN_WAVE_IDS) == 15
    sizes = [len(wave) for wave in runner.TRAIN_WAVE_IDS]
    assert sizes == [16] * 14 + [10]
    assert runner.TRAIN_WAVE_IDS[0] == tuple(
        f"train|{runner.PHASE3B_ARM}|{seed}" for seed in runner.SEEDS[:16]
    )
    assert len(runner.EVAL_SHARD_IDS) == 18
    assert runner.EVAL_SHARD_IDS[0] == "eval|half|an_cn_r0"
    assert f"eval|half|{runner.PHASE3B_ARM}" in runner.EVAL_SHARD_IDS
    assert f"eval|final|{runner.PHASE3B_ARM}" in runner.EVAL_SHARD_IDS


def test_arm_factors():
    assert runner.arm_factors("an_cn_r1_rms") == {
        "actor_source": "N",
        "critic_source": "N",
        "reward_access": True,
        "penalty": "r433-action-rms",
    }
    assert runner.arm_factors("ap_cp_r0") == {
        "actor_source": "P",
        "critic_source": "P",
        "reward_access": False,
    }
    with pytest.raises(ValueError):
        runner.arm_factors("a0_c0_r0")


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


def test_contract_frozen_fields():
    contract = runner.build_contract()
    body = contract["r482"]
    assert body["successor_of"] == "R477"
    assert len(body["retrain_cells"]) == 234
    assert body["reused_cells"] == []
    assert body["fresh_seed_roster"] == list(runner.SEEDS)
    assert body["phase3b"]["lambda_p"] == 10.0
    assert body["phase3b"]["coefficient_frozen"] is True
    assert body["phase3b"]["arm"] == "an_cn_r1_rms"
    assert body["power_plan_sha256"] == runner.base.base.base.core._sha256_file(
        runner.POWER
    )


def test_authority_contract_closed(monkeypatch):
    assert runner.authority_checks()["contract_closed"] is True
    monkeypatch.setattr(runner, "SEEDS", tuple(range(501, 526)))
    try:
        assert runner.authority_checks()["contract_closed"] is False
    finally:
        monkeypatch.setattr(runner, "SEEDS", tuple(range(501, 527)))


def test_penalized_reward_seam():
    joint = np.zeros((4, 7), dtype=np.float32)
    delta_m = np.zeros(4, dtype=float)
    delta_d = np.zeros(4, dtype=float)
    base_rewards = runner.base.base.base.core.legacy.step_rewards(
        joint, delta_m, delta_d, reward_access=True
    )
    action = np.asarray([[0.5, -0.5], [0.0, 0.0], [1.0, 0.25], [-0.75, 0.0]])
    penalized = runner._r482_penalized_step_rewards(
        joint, delta_m, delta_d, True, action
    )
    expected_penalty = runner.LAMBDA_P * (-np.mean(action**2, axis=1))
    assert np.allclose(penalized - base_rewards, expected_penalty, atol=1e-9)
    assert np.allclose(penalized[1], base_rewards[1], atol=1e-9)
    assert np.all(expected_penalty <= 0.0)


def test_factorial_reward_hash_frozen():
    assert runner._factorial_reward_sha() == runner.FACTORIAL_REWARD_SHA


# ---------------------------------------------------------------------------
# Seal binding (no inherited-seal bypass)
# ---------------------------------------------------------------------------


def test_load_seal_binds_r482_seal_only():
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert "seal_path=SEAL" in source
    assert "memory/rounds/R477/formal_seal" not in source
    assert "memory/rounds/R476/formal_seal" not in source
    assert runner.SEAL == ROOT / "memory/rounds/R482/formal_seal.json"
    assert runner.load_seal.__module__ == "_r482_under_test"


def test_physical_commands_fail_closed_on_windows(monkeypatch):
    for command in ("basegen", "rehearse"):
        monkeypatch.setattr(sys, "argv", ["run_r482", command])
        with pytest.raises(RuntimeError) as error:
            runner._main()
        assert "WSL" in str(error.value)
    for command in ("base", "route", "prepare"):
        monkeypatch.setattr(sys, "argv", ["run_r482", command])
        with pytest.raises((RuntimeError, OSError)):
            runner._main()


# ---------------------------------------------------------------------------
# r482_analysis inference layer
# ---------------------------------------------------------------------------


def test_symmetry_skew():
    assert r482_analysis.symmetry_skew([1.0, -1.0, 0.5, -0.5], 0.0) == pytest.approx(
        0.0, abs=1e-12
    )
    assert r482_analysis.symmetry_skew([1.0, 2.0, 3.0, 100.0], 0.0) > 1.0
    assert r482_analysis.symmetry_skew([1.0, 1.0, 1.0], 0.0) == 0.0


def test_signflip_mc_matches_exact_enumeration():
    values = [0.2, -0.7, 0.9, 0.1]
    p_value, se = r482_analysis.signflip_p_one_sided_mc(
        values, 0.0, draws=200_000, rng_seed=7
    )
    observed = float(np.mean(values))
    exact = sum(
        float(np.mean(np.asarray(values) * np.asarray(signs))) >= observed
        for signs in [(1, 1, 1, 1), (1, 1, 1, -1), (1, 1, -1, 1), (1, -1, 1, 1),
                      (-1, 1, 1, 1), (1, 1, -1, -1), (1, -1, 1, -1), (-1, 1, 1, -1),
                      (1, -1, -1, 1), (-1, 1, -1, 1), (-1, -1, 1, 1), (1, -1, -1, -1),
                      (-1, 1, -1, -1), (-1, -1, 1, -1), (-1, -1, -1, 1), (-1, -1, -1, -1)]
    ) / 16
    assert abs(p_value - exact) <= 4 * se + 1e-9


def _seed_effects_fixture():
    seeds = list(range(501, 507))
    effects = {}
    rng = np.random.default_rng(0)
    for name in r482_analysis.REGISTERED_EFFECTS:
        effects[name] = {
            seed: 0.05 + 0.06 * rng.normal() for seed in seeds
        }
    return effects


def test_boundary_rows_wilcoxon_primary_when_symmetric():
    effects = _seed_effects_fixture()
    rows = r482_analysis.boundary_test_rows(effects, math.log(1.10))
    assert set(rows) == set(r482_analysis.REGISTERED_EFFECTS)
    for name, row in rows.items():
        assert row["primary_test"] in ("wilcoxon", "signflip")
        if row["wilcoxon_exact_valid"]:
            assert row["wilcoxon_p_one_sided"] == pytest.approx(
                exact_signed_rank_p_one_sided(row["paired_log_effects"], math.log(1.10))
            )
        assert row["signflip_p_mc_se"] >= 0
        assert 0.0 <= row["signflip_p_one_sided"] <= 1.0


def test_boundary_rows_skew_triggers_fallback():
    effects = _seed_effects_fixture()
    effects["actor_main"][501] += 40.0
    rows = r482_analysis.boundary_test_rows(effects, math.log(1.10))
    assert rows["actor_main"]["symmetry_skew"] > 1.0
    assert rows["actor_main"]["primary_test"] == "signflip"
    assert rows["critic_main"]["primary_test"] in ("wilcoxon", "signflip")


def test_boundary_rows_negative_skew_triggers_fallback():
    effects = _seed_effects_fixture()
    effects["critic_main"][501] -= 40.0
    rows = r482_analysis.boundary_test_rows(effects, math.log(1.10))
    assert abs(rows["critic_main"]["symmetry_skew"]) > 1.0
    assert rows["critic_main"]["primary_test"] == "signflip"


def test_phase3_holm_decision():
    reproduced = r482_analysis.phase3_analysis(
        [0.1, 0.2, 0.3, 0.1, 0.2, 0.3], [0.4, 0.5, 0.6, 0.4, 0.5, 0.6]
    )
    assert reproduced["outcome"] == "PHASE3-TRADE-OFF-REPRODUCED"
    assert reproduced["endpoint_regression"]["holm_reject"] is True
    assert reproduced["action_stress_improvement"]["holm_reject"] is True
    not_established = r482_analysis.phase3_analysis(
        [0.01, -0.02, 0.05, 0.0, 0.03, -0.01], [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    )
    assert not_established["outcome"] == "PHASE3-TRADE-OFF-NOT-ESTABLISHED"


def test_classify_precedence():
    rows = r482_analysis.boundary_test_rows(_seed_effects_fixture(), math.log(1.10))
    phase3 = r482_analysis.phase3_analysis([0.1] * 6, [0.1] * 6)

    def classify(**overrides):
        kwargs = dict(
            design_valid=True,
            missing_shards=[],
            integrity_errors=[],
            dynamics_stable=True,
            factorial_rows=rows,
            phase3_rows=phase3,
        )
        kwargs.update(overrides)
        return r482_analysis.classify_r482(**kwargs)

    assert classify(design_valid=False)["verdict"] == "DESIGN-INVALID"
    assert classify(missing_shards=["train|an_cn_r0|501"])["verdict"] == "EXECUTION-INCOMPLETE"
    assert classify(integrity_errors=["drift"])["verdict"] == "INTEGRITY-INVALID"
    valid = classify()
    assert valid["material_effect"] in ("MAIN-EFFECT", "INTERACTION", "NOT_ESTABLISHED")
    assert valid["phase3_outcome"] == "PHASE3-TRADE-OFF-REPRODUCED"
    assert valid["verdict"] in (
        "MATERIAL-MAIN-EFFECT",
        "MATERIAL-INTERACTION",
        "MATERIAL-MAIN-EFFECT+MATERIAL-INTERACTION",
        "MATERIAL-EFFECT-NOT-ESTABLISHED",
    )
    invalid = classify(design_valid=False)
    assert invalid["material_effect"] == "NOT_TESTED"
    assert invalid["phase3_outcome"] == "NOT_TESTED"
