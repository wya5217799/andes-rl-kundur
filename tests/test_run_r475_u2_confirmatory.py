"""R475 runner unit tests: row-permuted P semantics, per-slot routing gate,
mutation/negative tests, all-fresh 2x2 cell split, direct materiality helper."""

from __future__ import annotations

import numpy as np
import pytest
import scripts.run_r475_u2_confirmatory as R475


def _env_wired_joint(rng: np.random.Generator) -> np.ndarray:
    """Build a joint with the REAL env neighbour wiring (COMM_ADJ =
    {0:[1,3], 1:[0,2], 2:[1,3], 3:[2,0]}): slot 3 = d_omega of COMM_ADJ[i][0],
    slot 4 = d_omega of COMM_ADJ[i][1], slot 5 = omega_dot of COMM_ADJ[i][0],
    slot 6 = omega_dot of COMM_ADJ[i][1]."""
    own = rng.normal(size=(4, 3)).astype(np.float32)
    joint = np.zeros((4, 7), dtype=np.float32)
    joint[:, :3] = own
    for i in range(4):
        adj0, adj1 = R475.COMM_ADJ[i]
        joint[i, 3] = own[adj0, 1]
        joint[i, 4] = own[adj1, 1]
        joint[i, 5] = own[adj0, 2]
        joint[i, 6] = own[adj1, 2]
    return joint


def test_cell_split_is_exactly_48_fresh_and_zero_reuse() -> None:
    retrain = set(R475.RETRAIN_CELLS)
    reuse = set(R475.REUSE_CELLS)
    assert len(retrain) == 48
    assert len(reuse) == 0
    expected = {
        (arm, seed)
        for arm in R475.RETRAIN_ARMS
        for seed in R475.core.TRAINING_SEEDS
    }
    assert retrain == expected
    assert set(R475.RETRAIN_ARMS) == {
        f"{base}_{reward}"
        for base in ("an_cn", "an_cp", "ap_cn", "ap_cp")
        for reward in ("r0", "r1")
    }


def test_retrain_arms_are_exactly_np_actor_critic() -> None:
    for arm in R475.RETRAIN_ARMS:
        factors = R475.core.arm_factors(arm)
        assert factors["actor_source"] in ("N", "P")
        assert factors["critic_source"] in ("N", "P")


def test_source_rows_n_zero_p_semantics_row_permutation() -> None:
    joint = np.arange(4 * 7, dtype=np.float32).reshape(4, 7)
    n_rows = R475.source_rows(joint, "N")
    assert np.array_equal(n_rows, joint)
    zero_rows = R475.source_rows(joint, "0")
    assert np.all(zero_rows[:, 3:7] == 0.0)
    assert np.array_equal(zero_rows[:, :3], joint[:, :3])
    p_rows = R475.source_rows(joint, "P")
    # P[i,3:7] = N[(i+1)%4,3:7]; own columns 0:2 unchanged.
    for i in range(4):
        assert np.array_equal(p_rows[i, 3:7], joint[(i + 1) % 4, 3:7])
        assert np.array_equal(p_rows[i, :3], joint[i, :3])
    with pytest.raises(ValueError):
        R475.source_rows(joint, "X")


def test_row_permutation_satisfies_per_slot_pool_equality() -> None:
    """The decisive guardrail property the aborted R474 design violated:
    per-slot value pools of the ACTUAL source_rows outputs must be equal."""
    rng = np.random.default_rng(20260823)
    joints = np.stack([_env_wired_joint(rng) for _ in range(32)])
    result = R475.routing_check(joints)
    assert result["per_slot_value_pools_equal"] is True
    assert result["tuple_multiset_equal"] is True
    assert result["every_source_tuple_changed"] is True
    assert result["no_p_source_is_true_neighbour"] is True
    assert result["no_within_tuple_source_collapse"] is True
    assert result["own_columns_unchanged"] is True
    assert result["row_perm_is_permutation"] is True
    assert result["row_perm_fixed_point_free"] is True
    assert result["same_contemporaneous_pool"] is True
    assert result["joints_checked"] == 32


def test_routing_check_realized_slots_on_env_wired_joints() -> None:
    rng = np.random.default_rng(7)
    joints = np.stack([_env_wired_joint(rng) for _ in range(8)])
    result = R475.routing_check(joints, realized_slots=True)
    assert result["per_slot_value_pools_equal"] is True
    assert result["tuple_multiset_equal"] is True
    assert result["every_source_tuple_changed"] is True
    assert result["no_p_source_is_true_neighbour"] is True
    assert result["realized_slot_identity_ok"] is True
    assert result["realized_slots_checked"] is True


def test_routing_check_realized_slots_flags_broken_wiring() -> None:
    # A joint whose slot content does NOT equal the source device's feature
    # must fail the realized-slot identity check.
    joint = np.arange(4 * 7, dtype=np.float32).reshape(4, 7)
    result = R475.routing_check(joint[np.newaxis, ...], realized_slots=True)
    assert result["realized_slot_identity_ok"] is False


def test_routing_check_rejects_wrong_shape() -> None:
    with pytest.raises(ValueError):
        R475.routing_check(np.zeros((4, 7), dtype=np.float32))


def test_aborted_diagonal_copy_fails_the_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Negative mutation 1 (F-01/F-02): the aborted R474 pi(i)=(i+2) double
    copy must FAIL per-slot pool equality and tuple multiset preservation.
    We monkeypatch source_rows to the aborted implementation (the mutation
    that the gate must kill) and run the real routing_check on it."""
    rng = np.random.default_rng(11)
    joints = np.stack([_env_wired_joint(rng) for _ in range(16)])

    def aborted_p_rows(joint_obs: np.ndarray, source: str) -> np.ndarray:
        current = np.asarray(joint_obs, dtype=np.float32).reshape(4, 7)
        if source == "N":
            return current.copy()
        rows = current.copy()
        if source == "0":
            rows[:, 3:7] = 0.0
            return rows
        if source != "P":
            raise ValueError(f"unknown source: {source}")
        for i in range(4):
            pivot = (i + 2) % 4
            rows[i, 3] = current[pivot, 1]
            rows[i, 4] = current[pivot, 1]
            rows[i, 5] = current[pivot, 2]
            rows[i, 6] = current[pivot, 2]
        return rows

    monkeypatch.setattr(R475, "source_rows", aborted_p_rows)
    result = R475.routing_check(joints)
    # The aborted design violates the per-slot pools and the tuple multiset;
    # the value-level collapse signal fires (slot3==slot4 forced); the
    # routing gate must catch it before any training.
    assert result["per_slot_value_pools_equal"] is False
    assert result["tuple_multiset_equal"] is False
    assert result["actual_row_value_collapse_absent"] is False
    assert result["actual_p_rows_match_declared_row_perm"] is False


def test_true_neighbour_source_fails_realized_slot_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Negative mutation 2: a P wiring that routes a TRUE neighbour of the
    recipient into a P slot must fail the realized-slot identity / drift /
    value-collapse gates (the source-ID non-neighbour proof is computed from
    the declared row permutation and stays True under this monkeypatch)."""
    rng = np.random.default_rng(13)
    joints = np.stack([_env_wired_joint(rng) for _ in range(16)])

    def neighbour_p_rows(joint_obs: np.ndarray, source: str) -> np.ndarray:
        current = np.asarray(joint_obs, dtype=np.float32).reshape(4, 7)
        if source == "N":
            return current.copy()
        rows = current.copy()
        if source == "0":
            rows[:, 3:7] = 0.0
            return rows
        if source != "P":
            raise ValueError(f"unknown source: {source}")
        # True-neighbour routing: recipient i receives COMM_ADJ[i][0]'s
        # features in both neighbour d_omega/omega_dot slots.
        for i in range(4):
            neighbour = R475.COMM_ADJ[i][0]
            rows[i, 3] = current[neighbour, 1]
            rows[i, 4] = current[neighbour, 1]
            rows[i, 5] = current[neighbour, 2]
            rows[i, 6] = current[neighbour, 2]
        return rows

    monkeypatch.setattr(R475, "source_rows", neighbour_p_rows)
    result = R475.routing_check(joints, realized_slots=True)
    # The true-neighbour wiring collapses each recipient's two slots to one
    # neighbour and drifts from the declared row permutation: the actual-row
    # gates and the realized-slot identity must fail.
    assert result["realized_slot_identity_ok"] is False
    assert result["actual_p_rows_match_declared_row_perm"] is False
    assert result["actual_row_value_collapse_absent"] is False


def test_row_permutation_with_fixed_point_fails_structure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Negative mutation 3: a row permutation with a fixed point (identity on
    one recipient) must fail the structure/drift checks."""
    rng = np.random.default_rng(17)
    joints = np.stack([_env_wired_joint(rng) for _ in range(16)])

    def fixed_point_p_rows(joint_obs: np.ndarray, source: str) -> np.ndarray:
        current = np.asarray(joint_obs, dtype=np.float32).reshape(4, 7)
        if source == "N":
            return current.copy()
        rows = current.copy()
        if source == "0":
            rows[:, 3:7] = 0.0
            return rows
        if source != "P":
            raise ValueError(f"unknown source: {source}")
        perm = (0, 2, 3, 1)  # rho(0)=0 -> fixed point
        rows[:, 3:7] = current[list(perm), 3:7]
        return rows

    monkeypatch.setattr(R475, "source_rows", fixed_point_p_rows)
    result = R475.routing_check(joints)
    # The fixed-point row permutation preserves pools/multisets but drifts
    # from the declared ROW_PERM and leaves recipient 0's tuple unchanged:
    # the drift gate and the tuple-changed structure check must fail.
    assert result["actual_p_rows_match_declared_row_perm"] is False
    assert result["every_source_tuple_changed"] is False


def test_single_slot_swap_fails_tuple_multiset(monkeypatch: pytest.MonkeyPatch) -> None:
    """Negative mutation 4: swapping one P slot breaks the row 4-tuple
    multiset and the declared-wiring drift gate (a within-column swap keeps
    that column's sorted pool, so per-slot pools stay equal)."""
    rng = np.random.default_rng(19)
    joints = np.stack([_env_wired_joint(rng) for _ in range(16)])

    def swapped_p_rows(joint_obs: np.ndarray, source: str) -> np.ndarray:
        current = np.asarray(joint_obs, dtype=np.float32).reshape(4, 7)
        if source == "N":
            return current.copy()
        rows = current.copy()
        if source == "0":
            rows[:, 3:7] = 0.0
            return rows
        if source != "P":
            raise ValueError(f"unknown source: {source}")
        rows[:, 3:7] = current[list(R475.ROW_PERM), 3:7]
        # Swap recipient 0's slot-3 value with recipient 1's slot-3 value.
        rows[0, 3], rows[1, 3] = rows[1, 3], rows[0, 3]
        return rows

    monkeypatch.setattr(R475, "source_rows", swapped_p_rows)
    result = R475.routing_check(joints)
    # Swapping two values within one column preserves that column's sorted
    # pool but changes the row 4-tuple multiset and the drift gate: the
    # tuple-multiset and declared-wiring gates must fire.
    assert result["tuple_multiset_equal"] is False
    assert result["actual_p_rows_match_declared_row_perm"] is False


def test_stale_time_step_source_fails_same_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Negative mutation 5: a P wiring that reads a PREVIOUS time step (or an
    exogenous bank) must fail the same-contemporaneous-pool derivation."""
    rng = np.random.default_rng(23)
    joints = np.stack([_env_wired_joint(rng) for _ in range(16)])

    def stale_p_rows(joint_obs: np.ndarray, source: str) -> np.ndarray:
        current = np.asarray(joint_obs, dtype=np.float32).reshape(4, 7)
        if source == "N":
            return current.copy()
        rows = current.copy()
        if source == "0":
            rows[:, 3:7] = 0.0
            return rows
        if source != "P":
            raise ValueError(f"unknown source: {source}")
        # Simulate an exogenous donor bank: P rows read a DIFFERENT joint
        # (here: a fixed synthetic matrix, standing in for a pre-recorded
        # donor trajectory) instead of the current joint.
        donor = np.full((4, 7), 0.25, dtype=np.float32)
        rows[:, 3:7] = donor[list(R475.ROW_PERM), 3:7]
        return rows

    monkeypatch.setattr(R475, "source_rows", stale_p_rows)
    result = R475.routing_check(joints)
    # The donor source keeps the declared permutation shape but is not a
    # function of the current joint: same_contemporaneous_pool must fail,
    # and the drift gate must fail because actual P rows != joint[ROW_PERM].
    assert result["same_contemporaneous_pool"] is False
    assert result["actual_p_rows_match_declared_row_perm"] is False


def test_no_donor_bank_functions_reachable_in_runner() -> None:
    assert R475._no_donor_reachable() is True
    text = open(R475.__file__, encoding="utf-8").read()
    for forbidden in ("generate_donor_and_base", "_load_donor", "donor_marginal_audit"):
        assert forbidden not in text


def test_import_copies_donor_sidecars_and_no_training_import() -> None:
    """Import hardlinks only base_state.pt + manifest.json sidecars; no
    training/eval shard import remains (all-fresh confirmatory design)."""
    text = open(R475.__file__, encoding="utf-8").read()
    assert 'for name in ("base_state.pt", "manifest.json")' in text
    assert "tgt_side" in text and "os.link(src_side, tgt_side)" in text
    import_src = text.split("def import_parent_artifacts", 1)[1]
    assert "imported_training_shards" in import_src
    assert "imported_eval_stages" in import_src
    # The import function must not iterate over REUSE_CELLS (all-fresh):
    # the only remaining mentions are the prepare() summary counters.
    assert "for arm, seed in REUSE_CELLS" not in import_src
    assert "REUSE_CELLS:" not in import_src.split("def prepare", 1)[0]


def test_prepare_seals_structural_parents_and_counts_eval_shards() -> None:
    text = open(R475.__file__, encoding="utf-8").read()
    for name in ("r451_structural_parent", "r438_parent", "r431_parent",
                 "r430_parent", "r429_parent", "r428_parent",
                 "base_env", "v4_config"):
        assert f'"{name}"' in text
    for name in ("run_r451_m3_message_factorial.py", "run_r438_sac_message_channels.py",
                 "base_env.py", "v4_config.py"):
        assert name in text
    prepare_src = text.split("def prepare", 1)[1]
    assert '"fresh_eval_shards": 16' in prepare_src
    assert '"fresh_training_shards": len(missing)' in prepare_src


def test_contract_declares_row_permutation_and_all_fresh_split() -> None:
    contract = R475.build_contract()
    assert contract["round"] == "R475"
    assert "r470" not in contract
    assert contract["r475"]["successor_of"] == "R473"
    assert "row permutation" in contract["r475"]["p_source_semantics"]
    assert len(contract["r475"]["retrain_cells"]) == 48
    assert len(contract["r475"]["reused_cells"]) == 0


def test_authority_checks_reflect_active_plan() -> None:
    checks = R475.authority_checks()
    assert checks["active_plan"] is True
    assert checks["active_line"] is True
    assert checks["contract_closed"] is True


def test_signflip_materiality_helper_matches_external_diagnostic() -> None:
    """The external review's diagnostic recomputation on the R473 critic
    differences must reproduce exactly: p at null 0 = 1/64, p at null
    log(1.10) = 2/64 (verification record section 6.1)."""
    values = [0.2349, 0.1372, 0.1418, 0.1901, 0.2453, 0.0849]
    p_zero = R475._signflip_p_one_sided(values, 0.0)
    p_mat = R475._signflip_p_one_sided(values, R475.MATERIALITY_LOG)
    assert p_zero == pytest.approx(1 / 64)
    assert p_mat == pytest.approx(2 / 64)


def test_signflip_materiality_all_above_bound_is_1_over_64() -> None:
    values = [0.30, 0.25, 0.20, 0.35, 0.28, 0.22]
    assert R475._signflip_p_one_sided(values, R475.MATERIALITY_LOG) == pytest.approx(1 / 64)
