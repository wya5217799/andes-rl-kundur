from __future__ import annotations

import scripts.run_r472_u2_source_factorial as R472


def test_reuse_set_is_exactly_the_16_complete_r471_shards() -> None:
    expected = (
        {("a0_c0_r0", seed) for seed in range(401, 407)}
        | {("a0_c0_r1", seed) for seed in range(401, 407)}
        | {("a0_cp_r0", seed) for seed in range(401, 405)}
    )
    assert set(R472.EXPECTED_REUSE) == expected
    assert len(R472.EXPECTED_REUSE) == 16


def test_successor_contract_keeps_full_factorial_and_declares_reuse() -> None:
    contract = R472.build_contract()
    assert contract["round"] == "R472"
    assert "r471" not in contract
    assert contract["r472"]["successor_of"] == "R471"
    assert contract["r472"]["missing_training_shards"] == 92
    assert len(contract["r472"]["arms"]) == 18
    assert contract["r472"]["training_seeds"] == [401, 402, 403, 404, 405, 406]


def test_no_partial_r471_directory_is_in_reuse_set() -> None:
    partial = {
        (path.parent.name, int(path.name.removeprefix("seed")))
        for path in (R472.R471_OUT / "train").glob("*/*")
        if path.is_dir() and not (path / "manifest.json").is_file()
    }
    assert partial
    assert set(R472.EXPECTED_REUSE).isdisjoint(partial)
