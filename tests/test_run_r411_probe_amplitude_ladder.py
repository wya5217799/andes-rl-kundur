"""Directed tests for the R411 probe-amplitude ladder runner.

Windows-safe: only pure protocol math, shard-id parsing, amplitude-table
verdict logic, and rung selection are exercised here.  The WSL-only
lifecycle (measure-capacity / rehearse / prepare / shard / classify) runs
through the scratch launcher in the sealed round itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import run_r411_probe_amplitude_ladder as runner  # noqa: E402
from andes_rl_kundur.evaluation.cd_matd3_canary import build_contract  # noqa: E402


def _frozen() -> dict:
    return build_contract()


def test_amplitude_key_roundtrip() -> None:
    for factor in runner.AMPLITUDE_FACTORS:
        key = runner.amplitude_key(factor)
        assert "." not in key
        assert abs(runner.factor_from_key(key) - factor) < 1e-12


def test_shard_list_expansion() -> None:
    contract = _frozen()
    shards = runner.shard_list()
    assert len(shards) == 50
    assert len(set(shards)) == 50
    expected_count = len(runner.AMPLITUDE_FACTORS) * (
        len(contract["learning_arm_ids"]) * len(contract["training_seeds"]) + 1
    )
    assert len(shards) == expected_count
    for sid in shards:
        arm_id, seed, key = runner.parse_shard_id(sid)
        assert runner.factor_from_key(key) in runner.AMPLITUDE_FACTORS
        if seed is None:
            assert arm_id == contract["deterministic_arm_id"]
        else:
            assert arm_id in contract["learning_arm_ids"]
            assert seed in contract["training_seeds"]


def test_scaled_profiles_probe_only() -> None:
    contract = _frozen()
    frozen_eval = {
        row["profile_id"]: row
        for row in contract["profiles"]
        if row["split"] == "evaluation"
    }
    scaled = runner.scaled_profiles(0.5)
    assert len(scaled) == 4
    for profile in scaled:
        source = frozen_eval[profile["profile_id"]]
        assert profile["probe_magnitude"] == 0.5 * source["probe_magnitude"]
        assert profile["localized_magnitude"] == source["localized_magnitude"]
        assert profile["amplitude_factor"] == 0.5
        assert len(profile["scenarios"]) == 6
        by_kind = {
            scenario["pair_kind"]: scenario for scenario in profile["scenarios"]
        }
        assert by_kind["common"]["magnitude"] == profile["probe_magnitude"]
        assert (
            by_kind["differential"]["magnitude"] == profile["probe_magnitude"]
        )
        assert (
            by_kind["localized"]["magnitude"] == profile["localized_magnitude"]
        )
        # signed-pair symmetry: positive and negative deltas are opposites
        positive = next(
            s for s in profile["scenarios"] if s["sign"] == "positive"
        )
        negative = next(
            s for s in profile["scenarios"] if s["sign"] == "negative"
        )
        for key in positive["delta_u"]:
            assert positive["delta_u"][key] == -negative["delta_u"][key]


def test_scaled_contract_one_equals_frozen_scenarios() -> None:
    contract = _frozen()
    scaled = runner.scaled_contract(1.0)
    frozen_eval = {
        row["profile_id"]: row
        for row in contract["profiles"]
        if row["split"] == "evaluation"
    }
    scaled_eval = {
        row["profile_id"]: row
        for row in scaled["profiles"]
        if row["split"] == "evaluation"
    }
    assert set(scaled_eval) == set(frozen_eval)
    for profile_id, profile in scaled_eval.items():
        source = frozen_eval[profile_id]
        for scenario, source_scenario in zip(
            profile["scenarios"], source["scenarios"]
        ):
            assert scenario["magnitude"] == source_scenario["magnitude"]
            assert scenario["delta_u"] == source_scenario["delta_u"]


def test_rung_selection_marginal_rule() -> None:
    # gains >=5% over the selected rung 4, then below: selects 4
    throughput = {1: 0.10, 2: 0.19, 4: 0.36, 8: 0.37, 12: 0.375, 16: 0.375}
    selection = runner._select_rung(
        throughput, wsl_available_bytes=22 * 2**30
    )
    assert selection["readiness"] == "RUN-READY"
    assert selection["selected_workers"] == 4
    assert selection["host_process_budget"] == 5
    decisions = {row["workers"]: row for row in selection["rung_decisions"]}
    assert decisions[8]["reason"] == "insufficient_throughput_gain"


def test_rung_selection_memory_guard() -> None:
    throughput = {1: 0.10, 2: 0.20, 4: 0.40, 8: 0.80, 12: 1.60, 16: 3.20}
    # 22.63 GB WSL available: half = 11.32 GB; floor 944 MB => 12 workers
    # overshoot the half-memory rule, so the ladder tops out at 8
    selection = runner._select_rung(
        throughput, wsl_available_bytes=22634487808
    )
    assert selection["selected_workers"] == 8
    assert selection["host_process_budget"] == 9
    decisions = {row["workers"]: row for row in selection["rung_decisions"]}
    assert decisions[12]["reason"] == "memory_reserve_guard"
    assert decisions[16]["reason"] == "memory_reserve_guard"


def _synthetic_per_amplitude(
    deterministic_values: dict[str, float],
    learning_values: dict[str, float],
) -> dict:
    """Build a per_amplitude payload with one profile per arm-seed block."""
    contract = _frozen()
    evaluation_profiles = runner.evaluation_profiles(contract)
    assert len(evaluation_profiles) == 4
    payloads = {}
    for factor in runner.AMPLITUDE_FACTORS:
        key = runner.amplitude_key(factor)
        summaries = []
        for arm_id in [*contract["learning_arm_ids"], contract["deterministic_arm_id"]]:
            for seed in (
                [None]
                if arm_id == contract["deterministic_arm_id"]
                else contract["training_seeds"]
            ):
                for profile_id in evaluation_profiles:
                    values = (
                        deterministic_values
                        if arm_id == contract["deterministic_arm_id"]
                        else learning_values
                    )
                    summaries.append(
                        {
                            "profile_id": profile_id,
                            "arm_id": str(arm_id),
                            "training_seed": None if seed is None else int(seed),
                            "off_diagonal_response_energy": values[
                                "off_diagonal_response_energy"
                            ],
                            "disturbance_differential_energy": values[
                                "disturbance_differential_energy"
                            ],
                        }
                    )
        payloads[key] = {
            "amplitude_factor": float(factor),
            "classification": {
                "classification": "CANARY-FAIL",
                "guard_failures": [],
            },
            "summaries": summaries,
            "summary_errors": [],
        }
    return payloads


def test_amplitude_table_robust() -> None:
    per_amplitude = _synthetic_per_amplitude(
        {"off_diagonal_response_energy": 1.0, "disturbance_differential_energy": 2.0},
        {"off_diagonal_response_energy": 3.0, "disturbance_differential_energy": 4.0},
    )
    table = runner._amplitude_table({}, per_amplitude)
    assert table["invariance_verdict"] == "AMPLITUDE-ROBUST"
    assert table["classification_verdict"] == "CLASSIFICATION-AMPLITUDE-INVARIANT"
    # learning vs deterministic ratio constant across amplitudes: 3.0 and 2.0
    first = next(iter(table["invariance"].values()))
    assert first["relative_spread"] == 0.0


def test_amplitude_table_sensitive() -> None:
    per_amplitude = _synthetic_per_amplitude(
        {"off_diagonal_response_energy": 1.0, "disturbance_differential_energy": 2.0},
        {"off_diagonal_response_energy": 3.0, "disturbance_differential_energy": 4.0},
    )
    # perturb one amplitude's learning off-diagonal energy heavily
    for key, payload in per_amplitude.items():
        if key == runner.amplitude_key(1.5):
            for summary in payload["summaries"]:
                if summary["arm_id"] != _frozen()["deterministic_arm_id"]:
                    summary["off_diagonal_response_energy"] = 9.0
    table = runner._amplitude_table({}, per_amplitude)
    assert table["invariance_verdict"] == "AMPLITUDE-SENSITIVE"
    assert table["sensitive_count"] >= 9  # 9 arm-seeds on the off-diagonal axis


def test_rows_identical() -> None:
    def record(values):
        return {
            "steps": [{"freq_hz_physical": values}],
        }

    a = [record([1.0, 2.0, 3.0, 4.0])]
    b = [record([1.0, 2.0, 3.0, 4.0])]
    assert runner._rows_identical(a, b)
    c = [record([1.0, 2.0, 3.0, 4.0000001])]
    assert not runner._rows_identical(a, c)
    assert not runner._rows_identical(a, a + a)


def test_shard_id_parse_rejects_malformed() -> None:
    with pytest.raises(ValueError):
        runner.parse_shard_id("no-separators")
    with pytest.raises(ValueError):
        runner.parse_shard_id("arm|s401|x1")
    with pytest.raises(ValueError):
        runner.parse_shard_id("arm|odd|a1")


def test_scaled_contract_preserves_development_profiles() -> None:
    contract = _frozen()
    scaled = runner.scaled_contract(0.7)
    frozen_dev = [row for row in contract["profiles"] if row["split"] == "development"]
    scaled_dev = [row for row in scaled["profiles"] if row["split"] == "development"]
    assert frozen_dev == scaled_dev
    assert [row["profile_id"] for row in scaled["profiles"]] == [
        row["profile_id"] for row in contract["profiles"]
    ]


def test_guard_lookup() -> None:
    classification = {
        "guard_failures": [
            {
                "profile_id": "canary_eval_a",
                "arm_id": "cd_matd3_message",
                "training_seed": 402,
                "failed": ["rocof_no_harm", "action_rms_no_harm"],
            }
        ]
    }
    lookup = runner._guard_lookup(classification)
    assert lookup[("canary_eval_a", "cd_matd3_message", 402)] == [
        "rocof_no_harm",
        "action_rms_no_harm",
    ]
