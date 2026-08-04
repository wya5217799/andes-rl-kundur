from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r299_edge_information_probe.py"
SPEC = importlib.util.spec_from_file_location("r299_edge_information", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
r299 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r299)


def test_sentinel_matrix_and_future_eval_bank_are_frozen() -> None:
    assert len(r299.scenario_bank()) == 4
    assert len(r299.arm_bank()) == 6
    assert len(r299.job_bank()) == 24
    assert len(r299.formal_eval_bank()) == 12
    assert {row["tie_k"] for row in r299.formal_eval_bank()} == {1.375, 1.625}
    assert all(row not in r299.scenario_bank() for row in r299.formal_eval_bank())


def test_arm_bank_contains_base_all_edge_and_each_single_edge() -> None:
    arms = r299.arm_bank()
    assert arms[0]["name"] == r299.BASELINE_ARM
    assert arms[0]["extra_edges"] == []
    assert arms[1]["name"] == r299.ALL_EDGE_ARM
    assert {tuple(edge) for edge in arms[1]["extra_edges"]} == set(r299.EDGES)
    assert {
        tuple(arm["extra_edges"][0]) for arm in arms[2:]
    } == set(r299.EDGES)


def test_spearman_handles_monotonic_and_reversed_values() -> None:
    assert r299.spearman([1, 2, 3, 4], [2, 4, 6, 8]) == 1.0
    assert r299.spearman([1, 2, 3, 4], [8, 6, 4, 2]) == -1.0


def test_classification_requires_headroom_diversity_and_local_signal() -> None:
    common = {
        "valid": True,
        "adaptive_fast_ratio": 0.98,
        "adaptive_sync_ratio": 0.98,
        "distinct_nonbaseline_arms": 2,
        "best_fixed_is_nonbaseline": False,
        "fixed_fast_ratio": 1.0,
        "fixed_sync_ratio": 1.0,
    }
    assert r299.classify_probe(
        **common, local_spearman=0.6, best_edge_matches=3
    ) == "LOCALLY-SIGNALLED-EDGE-GAP"
    assert r299.classify_probe(
        **common, local_spearman=0.49, best_edge_matches=3
    ) == "OUTCOME-ONLY-EDGE-GAP"
    assert r299.classify_probe(
        **{**common, "distinct_nonbaseline_arms": 1},
        local_spearman=0.8,
        best_edge_matches=4,
    ) == "NO-ADAPTIVE-EDGE-VALUE"


def test_classification_redirects_uniform_gain_to_classical_retune() -> None:
    assert r299.classify_probe(
        valid=True,
        adaptive_fast_ratio=0.999,
        adaptive_sync_ratio=1.0,
        distinct_nonbaseline_arms=1,
        local_spearman=0.0,
        best_edge_matches=0,
        best_fixed_is_nonbaseline=True,
        fixed_fast_ratio=0.98,
        fixed_sync_ratio=0.99,
    ) == "CLASSICAL-RETUNE"
