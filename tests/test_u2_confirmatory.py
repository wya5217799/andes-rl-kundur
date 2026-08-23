from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from andes_rl_kundur.evaluation.u2_confirmatory import (
    classify_confirmatory,
    terminal_invalid,
    terminal_truth_table,
    validate_review_coverage,
    verify_formal_seal,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_hashed_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    Path(f"{path}.sha256").write_text(f"{_sha(path)}  {path.name}\n", encoding="ascii")


def _review(path: Path, files: dict[str, str]) -> None:
    _write_hashed_json(
        path,
        {
            "decision": "PASS",
            "open_p0_count": 0,
            "open_p1_count": 0,
            "reviewed_commit": "abc123",
            "reviewed_files": files,
        },
    )


def test_terminal_truth_table_executes_real_predicate() -> None:
    truth = terminal_truth_table(terminal_invalid)
    assert truth == {
        "normal_nonterminal_accepted": True,
        "normal_horizon_done_accepted": True,
        "premature_done_rejected": True,
        "tds_failure_rejected": True,
    }


@pytest.mark.parametrize(
    "mutation",
    [
        lambda **row: bool(row["done"]),
        lambda **row: bool(row["tds_failed"]),
        lambda **row: False,
    ],
)
def test_terminal_truth_table_kills_mutations(mutation) -> None:
    assert not all(terminal_truth_table(mutation).values())


def test_classifier_keeps_integrity_failure_reachable() -> None:
    result = classify_confirmatory(
        design_valid=True,
        missing_shards=[],
        integrity_errors=["reward hash drift"],
        dynamics_stable=True,
        established_factors=["critic"],
    )
    assert result["execution"] == "COMPLETE"
    assert result["integrity"] == "FAIL"
    assert result["material_effect"] == "NOT_TESTED"
    assert result["training_dynamics"] == "NOT_ASSESSED"
    assert result["verdict"] == "INTEGRITY-INVALID"


def test_classifier_suppresses_effect_for_missing_outputs() -> None:
    result = classify_confirmatory(
        design_valid=True,
        missing_shards=["eval|half|an_cn_r0"],
        integrity_errors=[],
        dynamics_stable=True,
        established_factors=["actor"],
    )
    assert result["execution"] == "INCOMPLETE"
    assert result["material_effect"] == "NOT_TESTED"
    assert result["verdict"] == "EXECUTION-INCOMPLETE"


def test_classifier_reports_effect_only_after_all_validity_gates() -> None:
    result = classify_confirmatory(
        design_valid=True,
        missing_shards=[],
        integrity_errors=[],
        dynamics_stable=False,
        established_factors=["actor"],
    )
    assert result["material_effect"] == "ESTABLISHED"
    assert result["training_dynamics"] == "UNSTABLE"
    assert result["verdict"] == "MATERIAL-EFFECT-ESTABLISHED"


def test_review_coverage_requires_identical_current_hash_maps(tmp_path: Path) -> None:
    runner = tmp_path / "runner.py"
    tests = tmp_path / "test_runner.py"
    runner.write_text("RUNNER = 1\n", encoding="utf-8")
    tests.write_text("TESTS = 1\n", encoding="utf-8")
    expected = {runner.name: _sha(runner), tests.name: _sha(tests)}
    review_a = tmp_path / "review_a.json"
    review_b = tmp_path / "review_b.json"
    _review(review_a, expected)
    _review(review_b, expected)

    assert validate_review_coverage(
        (review_a, review_b),
        repo_root=tmp_path,
        reviewed_files=(runner, tests),
    ) == expected

    drifted = dict(expected)
    drifted[tests.name] = "0" * 64
    _review(review_b, drifted)
    with pytest.raises(RuntimeError, match="reviewed_files"):
        validate_review_coverage(
            (review_a, review_b),
            repo_root=tmp_path,
            reviewed_files=(runner, tests),
        )


def test_full_seal_verifier_binds_files_sources_reviews_and_shards(tmp_path: Path) -> None:
    plan = tmp_path / "plan.md"
    power = tmp_path / "power.json"
    source = tmp_path / "runner.py"
    train = tmp_path / "train.json"
    evals = tmp_path / "eval.json"
    plan.write_text("round: R476\n", encoding="utf-8")
    power.write_text("{}\n", encoding="utf-8")
    source.write_text("RUNNER = 1\n", encoding="utf-8")
    train.write_text('["train|a|1"]\n', encoding="utf-8")
    evals.write_text('["eval|final|a"]\n', encoding="utf-8")
    reviewed = {source.name: _sha(source)}
    review_a = tmp_path / "review_a.json"
    review_b = tmp_path / "review_b.json"
    _review(review_a, reviewed)
    _review(review_b, reviewed)
    seal_path = tmp_path / "seal.json"
    seal = {
        "round": "R476",
        "contract_sha256": "contract",
        "formal_authority": True,
        "plan_sha256": _sha(plan),
        "power_sha256": _sha(power),
        "code_review_a_sha256": _sha(review_a),
        "code_review_b_sha256": _sha(review_b),
        "reviewed_files": reviewed,
        "sources": {
            "runner": {"path": source.name, "sha256": _sha(source)},
        },
        "shard_lists": {
            "train": {"path": train.name, "sha256": _sha(train)},
            "eval": {"path": evals.name, "sha256": _sha(evals)},
        },
    }
    _write_hashed_json(seal_path, seal)

    loaded = verify_formal_seal(
        repo_root=tmp_path,
        seal_path=seal_path,
        round_id="R476",
        contract_sha256="contract",
        bound_files={
            "plan_sha256": plan,
            "power_sha256": power,
            "code_review_a_sha256": review_a,
            "code_review_b_sha256": review_b,
        },
        review_paths=(review_a, review_b),
        reviewed_files=(source,),
        expected_shards={"train": ["train|a|1"], "eval": ["eval|final|a"]},
    )
    assert loaded["round"] == "R476"

    source.write_text("RUNNER = 2\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="sealed source drift"):
        verify_formal_seal(
            repo_root=tmp_path,
            seal_path=seal_path,
            round_id="R476",
            contract_sha256="contract",
            bound_files={
                "plan_sha256": plan,
                "power_sha256": power,
                "code_review_a_sha256": review_a,
                "code_review_b_sha256": review_b,
            },
            review_paths=(review_a, review_b),
            reviewed_files=(source,),
            expected_shards={"train": ["train|a|1"], "eval": ["eval|final|a"]},
        )


def test_full_seal_verifier_rejects_shard_list_drift(tmp_path: Path) -> None:
    source = tmp_path / "runner.py"
    source.write_text("RUNNER = 1\n", encoding="utf-8")
    train = tmp_path / "train.json"
    train.write_text('["train|a|1"]\n', encoding="utf-8")
    review_a = tmp_path / "review_a.json"
    review_b = tmp_path / "review_b.json"
    reviewed = {source.name: _sha(source)}
    _review(review_a, reviewed)
    _review(review_b, reviewed)
    seal_path = tmp_path / "seal.json"
    _write_hashed_json(
        seal_path,
        {
            "round": "R476",
            "contract_sha256": "contract",
            "formal_authority": True,
            "reviewed_files": reviewed,
            "sources": {"runner": {"path": source.name, "sha256": _sha(source)}},
            "shard_lists": {"train": {"path": train.name, "sha256": _sha(train)}},
        },
    )
    with pytest.raises(RuntimeError, match="shard list content drift"):
        verify_formal_seal(
            repo_root=tmp_path,
            seal_path=seal_path,
            round_id="R476",
            contract_sha256="contract",
            bound_files={},
            review_paths=(review_a, review_b),
            reviewed_files=(source,),
            expected_shards={"train": ["train|b|1"]},
        )
