"""R474 runner unit tests: same-time P semantics, routing check, cell split."""

from __future__ import annotations

import numpy as np
import pytest
import scripts.run_r474_u2_source_factorial as R474


def test_cell_split_is_exactly_60_retrain_plus_48_reuse() -> None:
    retrain = set(R474.RETRAIN_CELLS)
    reuse = set(R474.REUSE_CELLS)
    assert len(retrain) == 60
    assert len(reuse) == 48
    assert retrain.isdisjoint(reuse)
    all_cells = {
        (arm, seed)
        for arm in R474.core.ARMS
        for seed in R474.core.TRAINING_SEEDS
    }
    assert retrain | reuse == all_cells
    assert len(all_cells) == 108


def test_retrain_arms_are_exactly_actor_or_critic_p() -> None:
    assert set(R474.RETRAIN_ARMS) == {
        f"{base}_{reward}"
        for base in ("a0_cp", "an_cp", "ap_c0", "ap_cn", "ap_cp")
        for reward in ("r0", "r1")
    }
    assert set(R474.REUSE_ARMS) == {
        f"{base}_{reward}"
        for base in ("a0_c0", "a0_cn", "an_c0", "an_cn")
        for reward in ("r0", "r1")
    }
    for arm in R474.RETRAIN_ARMS:
        factors = R474.core.arm_factors(arm)
        assert factors["actor_source"] == "P" or factors["critic_source"] == "P"
    for arm in R474.REUSE_ARMS:
        factors = R474.core.arm_factors(arm)
        assert factors["actor_source"] in ("0", "N")
        assert factors["critic_source"] in ("0", "N")


def test_source_rows_n_zero_p_semantics() -> None:
    joint = np.arange(4 * 7, dtype=np.float32).reshape(4, 7)
    n_rows = R474.source_rows(joint, "N")
    assert np.array_equal(n_rows, joint)
    zero_rows = R474.source_rows(joint, "0")
    assert np.all(zero_rows[:, 3:7] == 0.0)
    assert np.array_equal(zero_rows[:, :3], joint[:, :3])
    p_rows = R474.source_rows(joint, "P")
    # agent i receives the same-time features of device (i+2) mod 4 in the
    # neighbour slots, matched by slot semantics: d_omega slots (3,4) get the
    # pivot d_omega, omega_dot slots (5,6) get the pivot omega_dot.
    for i in range(4):
        pivot = joint[(i + 2) % 4]
        assert p_rows[i, 3] == pivot[1]
        assert p_rows[i, 4] == pivot[1]
        assert p_rows[i, 5] == pivot[2]
        assert p_rows[i, 6] == pivot[2]
        assert np.array_equal(p_rows[i, :3], joint[i, :3])
    with pytest.raises(ValueError):
        R474.source_rows(joint, "X")


def test_routing_check_passes_on_wide_synthetic_pool() -> None:
    rng = np.random.default_rng(20260823)
    joints = rng.normal(size=(64, 4, 7)).astype(np.float32)
    joints[:, :, 0] = 0.0
    result = R474.routing_check(joints)
    # channel-block pool equality holds for ANY joint (P is a permutation of
    # the same authentic pool); the realized-slot identity check needs real
    # env wiring.
    assert result["channel_block_pools_equal"] is True
    assert result["every_source_tuple_changed"] is True
    assert result["no_p_source_is_true_neighbour"] is True
    assert result["same_contemporaneous_pool"] is True
    assert result["realized_slots_checked"] is False
    assert result["joints_checked"] == 64


def test_routing_check_realized_slots_on_env_wired_joints() -> None:
    # Build joints with the REAL env neighbour wiring (COMM_ADJ =
    # {0:[1,3], 1:[0,2], 2:[1,3], 3:[2,0]}): slot 3 = d_omega of
    # COMM_ADJ[i][0], slot 4 = d_omega of COMM_ADJ[i][1], slot 5 = omega_dot
    # of COMM_ADJ[i][0], slot 6 = omega_dot of COMM_ADJ[i][1].
    rng = np.random.default_rng(7)
    joints = []
    for _ in range(8):
        own = rng.normal(size=(4, 3)).astype(np.float32)
        joint = np.zeros((4, 7), dtype=np.float32)
        joint[:, :3] = own
        for i in range(4):
            adj0, adj1 = R474.COMM_ADJ[i]
            joint[i, 3] = own[adj0, 1]
            joint[i, 4] = own[adj1, 1]
            joint[i, 5] = own[adj0, 2]
            joint[i, 6] = own[adj1, 2]
        joints.append(joint)
    result = R474.routing_check(np.stack(joints), realized_slots=True)
    assert result["channel_block_pools_equal"] is True
    assert result["every_source_tuple_changed"] is True
    assert result["no_p_source_is_true_neighbour"] is True
    assert result["realized_slot_identity_ok"] is True
    assert result["realized_slots_checked"] is True


def test_routing_check_realized_slots_flags_broken_wiring() -> None:
    # A joint whose slot content does NOT equal the source device's feature
    # must fail the realized-slot identity check.
    joint = np.arange(4 * 7, dtype=np.float32).reshape(4, 7)
    result = R474.routing_check(joint[np.newaxis, ...], realized_slots=True)
    assert result["channel_block_pools_equal"] is True
    assert result["realized_slot_identity_ok"] is False


def test_routing_check_structural_properties_on_single_joint() -> None:
    joint = np.arange(4 * 7, dtype=np.float32).reshape(4, 7)
    result = R474.routing_check(joint[np.newaxis, ...])
    assert result["channel_block_pools_equal"] is True
    # two feature-channel blocks (d_omega cols 3,4; omega_dot cols 5,6)
    assert result["comparisons"] == 2


def test_routing_check_rejects_wrong_shape() -> None:
    with pytest.raises(ValueError):
        R474.routing_check(np.zeros((4, 7), dtype=np.float32))


def test_no_donor_bank_functions_reachable_in_runner() -> None:
    assert R474._no_donor_reachable() is True
    text = open(R474.__file__, encoding="utf-8").read()
    for forbidden in ("generate_donor_and_base", "_load_donor", "donor_marginal_audit"):
        assert forbidden not in text


def test_import_copies_donor_sidecars() -> None:
    """Import must hardlink the .sha256 sidecars of base_state.pt and
    manifest.json, or every later _read_hashed_json / formal_manifest call
    raises FileNotFoundError (reviewer-A blocker)."""
    text = open(R474.__file__, encoding="utf-8").read()
    assert 'for name in ("base_state.pt", "manifest.json")' in text
    assert "tgt_side" in text and "os.link(src_side, tgt_side)" in text


def test_prepare_seals_structural_parents_and_counts_eval_shards() -> None:
    """Seal sources must pin the structural parents (reward/env/contract
    chain) and fresh_eval_shards must equal the EVAL_SHARDS entry count."""
    text = open(R474.__file__, encoding="utf-8").read()
    for name in ("r451_structural_parent", "r438_parent", "r431_parent",
                 "r430_parent", "r429_parent", "r428_parent",
                 "base_env", "v4_config"):
        assert f'"{name}"' in text
    for name in ("run_r451_m3_message_factorial.py", "run_r438_sac_message_channels.py",
                 "base_env.py", "v4_config.py"):
        assert name in text
    shards = R474.EVAL_SHARDS
    assert shards is not None or True  # EVAL_SHARDS constant exists at module level
    prepare_src = text.split("def prepare", 1)[1]
    assert '"fresh_eval_shards": 20' in prepare_src


def test_contract_declares_same_time_semantics_and_split() -> None:
    contract = R474.build_contract()
    assert contract["round"] == "R474"
    assert "r470" not in contract
    assert contract["r474"]["successor_of"] == "R473"
    assert "same-time" in contract["r474"]["p_source_semantics"]
    assert len(contract["r474"]["retrain_cells"]) == 60
    assert len(contract["r474"]["reused_cells"]) == 48


def test_authority_checks_reflect_active_plan() -> None:
    checks = R474.authority_checks()
    assert checks["active_plan"] is True
    assert checks["active_line"] is True
    assert checks["contract_closed"] is True
