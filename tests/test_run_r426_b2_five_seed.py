"""Directed Windows-safe tests for the R426 B2 five-seed runner.

Windows-safe: constants, the seed-admission rule, the shard-id parser, the
checkpoint-source helper, the contract shape, and the five-seed aggregation
helper -- all pure, ANDES-free.  The WSL-only lifecycle runs through the
scratch launcher in the sealed round itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import run_r426_b2_five_seed as runner  # noqa: E402


def test_round_identity_and_b2_constants() -> None:
    assert runner.ROUND_ID == "R426"
    assert runner.OUT == ROOT / "results/research_loop/r426_b2_five_seed"
    assert runner.R410_OUT == ROOT / "results/research_loop/r410_message_repair"
    assert runner.OTHER_RESERVED_PROCESSES == 17
    assert runner.B2_FRESH_SEEDS == (404, 405)
    assert runner.B2_GATE_ARM == "cd_matd3_message"
    assert runner.B2_GATE_SEED == 401
    assert runner.B2_ALL_SEEDS == (401, 402, 403, 404, 405)


def test_contract_training_seeds_unchanged() -> None:
    contract = runner.build_contract()
    assert list(contract["training_seeds"]) == [401, 402, 403]
    assert len(contract["learning_arm_ids"]) == 3


def test_parse_shard_id_maps_and_rejects_malformed() -> None:
    assert runner._parse_shard_id("cd_matd3_message|401") == (
        "cd_matd3_message",
        401,
    )
    assert runner._parse_shard_id("yang_scalar_td3|405") == ("yang_scalar_td3", 405)
    for malformed in (
        "cd_matd3_message",
        "cd_matd3_message|401|extra",
        "|401",
        "cd_matd3_message|not_an_int",
    ):
        with pytest.raises(ValueError):
            runner._parse_shard_id(malformed)


def test_seed_admission_rule() -> None:
    # seed 401 requires the bit-identity gate arm
    assert runner._seed_arm_valid("cd_matd3_message", 401) is True
    assert runner._seed_arm_valid("yang_scalar_td3", 401) is False
    assert runner._seed_arm_valid("cd_matd3_no_message", 401) is False
    # seeds 404/405 are allowed on any learning arm
    for arm_id in ("yang_scalar_td3", "cd_matd3_no_message", "cd_matd3_message"):
        assert runner._seed_arm_valid(arm_id, 404) is True
        assert runner._seed_arm_valid(arm_id, 405) is True
    # seeds 402/403 are rejected (reused via stored checkpoints, never retrained)
    for seed in (402, 403):
        assert runner._seed_arm_valid("cd_matd3_message", seed) is False
        assert runner._seed_arm_valid("yang_scalar_td3", seed) is False


def test_checkpoint_source_helper() -> None:
    for seed in (401, 402, 403):
        path = runner._checkpoint_path("cd_matd3_message", seed)
        assert path == runner.R410_OUT / "train" / "cd_matd3_message" / f"seed{seed}" / "final.pt"
    for seed in (404, 405):
        path = runner._checkpoint_path("cd_matd3_message", seed)
        assert path == runner.OUT / "train" / "cd_matd3_message" / f"seed{seed}" / "final.pt"


def test_five_seed_aggregation_median_min_max() -> None:
    endpoint_e0 = {401: 5.0, 402: 1.0, 403: 3.0, 404: 2.0, 405: 4.0}
    summaries = [
        {
            "arm_id": "cd_matd3_message",
            "training_seed": seed,
            "off_diagonal_response_energy": value,
            "disturbance_differential_energy": value + 10.0,
        }
        for seed, value in endpoint_e0.items()
    ]
    table = runner._five_seed_aggregate(summaries, "cd_matd3_message")
    assert table["off_diagonal_response_energy"] == {
        "median": 3.0,
        "min": 1.0,
        "max": 5.0,
    }
    assert table["disturbance_differential_energy"] == {
        "median": 13.0,
        "min": 11.0,
        "max": 15.0,
    }
