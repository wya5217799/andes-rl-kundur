from __future__ import annotations

import scripts.run_r473_u2_source_factorial as R473


def test_reuse_set_is_exactly_the_96_complete_r472_shards() -> None:
    expected = {
        (arm, seed)
        for arm in (
            "a0_c0_r0", "a0_c0_r1", "a0_cp_r0", "a0_cp_r1",
            "a0_cn_r0", "a0_cn_r1", "ap_c0_r0", "ap_c0_r1",
            "ap_cp_r0", "ap_cp_r1", "ap_cn_r0", "ap_cn_r1",
            "an_c0_r0", "an_c0_r1", "an_cp_r0", "an_cp_r1",
        )
        for seed in range(401, 407)
    }
    assert set(R473.EXPECTED_REUSE) == expected
    assert len(R473.EXPECTED_REUSE) == 96


def test_successor_contract_keeps_full_factorial_and_declares_reuse() -> None:
    contract = R473.build_contract()
    assert contract["round"] == "R473"
    assert "r471" not in contract
    assert "r470" not in contract
    assert contract["r473"]["successor_of"] == "R472"
    assert contract["r473"]["missing_training_shards"] == 12
    assert len(contract["r473"]["arms"]) == 18
    assert contract["r473"]["training_seeds"] == [401, 402, 403, 404, 405, 406]


def test_no_partial_r472_directory_is_in_reuse_set() -> None:
    partial = {
        (path.parent.name, int(path.name.removeprefix("seed")))
        for path in (R473.R472_OUT / "train").glob("*/*")
        if path.is_dir() and not (path / "manifest.json").is_file()
    }
    assert partial
    assert set(R473.EXPECTED_REUSE).isdisjoint(partial)


def test_shutdown_inventory_candidate_set_matches_reuse_set() -> None:
    import json

    inventory = json.loads(
        R473.SHUTDOWN_INVENTORY.read_text(encoding="utf-8")
    )
    complete = {
        (arm, int(seed.removeprefix("seed")))
        for arm, seed in (s.split("/") for s in inventory["complete_shards"])
    }
    assert complete == set(R473.EXPECTED_REUSE)
    assert inventory["complete_shard_count"] == 96
