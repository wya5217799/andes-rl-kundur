from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from andes_rl_kundur.evaluation.u2_confirmatory import (
    ConfirmatoryAnalysisContext,
    TerminalGuardedEnvironment,
    build_confirmatory_analysis,
    check_artifact_budget,
    classify_confirmatory,
    git_commit_file_sha256,
    recalibrate_eta,
    terminal_invalid,
    terminal_truth_table,
    validate_review_coverage,
    verify_formal_seal,
)

COMMIT = "a" * 40


def test_commit_hash_uses_worktree_filters_for_cross_platform_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    filtered = b"line1\r\nline2\r\n"
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        del kwargs
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=filtered, stderr=b"")

    monkeypatch.setattr(
        "andes_rl_kundur.evaluation.u2_confirmatory.subprocess.run", fake_run
    )
    digest = git_commit_file_sha256(tmp_path, COMMIT, "source.py")
    assert digest == hashlib.sha256(filtered).hexdigest()
    assert calls[0][-3:] == [
        "--filters",
        "--path=source.py",
        f"{COMMIT}:source.py",
    ]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_hashed_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    Path(f"{path}.sha256").write_text(f"{_sha(path)}  {path.name}\n", encoding="ascii")


def _review(
    path: Path,
    files: dict[str, str],
    *,
    reviewer_id: str,
    commit: str = COMMIT,
) -> None:
    _write_hashed_json(
        path,
        {
            "decision": "PASS",
            "open_p0_count": 0,
            "open_p1_count": 0,
            "reviewed_commit": commit,
            "reviewer_id": reviewer_id,
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
    _review(review_a, expected, reviewer_id="correctness")
    _review(review_b, expected, reviewer_id="project-standards")

    coverage = validate_review_coverage(
        (review_a, review_b),
        repo_root=tmp_path,
        reviewed_files=(runner, tests),
        commit_file_sha256=lambda _root, _commit, relative: expected[relative],
    )
    assert coverage.reviewed_commit == COMMIT
    assert coverage.reviewed_files == expected

    drifted = dict(expected)
    drifted[tests.name] = "0" * 64
    _review(review_b, drifted, reviewer_id="project-standards")
    with pytest.raises(RuntimeError, match="reviewed_files"):
        validate_review_coverage(
            (review_a, review_b),
            repo_root=tmp_path,
            reviewed_files=(runner, tests),
            commit_file_sha256=lambda _root, _commit, relative: expected[relative],
        )


def test_full_seal_verifier_binds_files_sources_reviews_and_shards(tmp_path: Path) -> None:
    plan = tmp_path / "plan.md"
    power = tmp_path / "power.json"
    source = tmp_path / "runner.py"
    train = tmp_path / "train.json"
    evals = tmp_path / "eval.json"
    plan.write_text("round: R476\n", encoding="utf-8")
    _write_hashed_json(power, {})
    source.write_text("RUNNER = 1\n", encoding="utf-8")
    train.write_text('["train|a|1"]\n', encoding="utf-8")
    evals.write_text('["eval|final|a"]\n', encoding="utf-8")
    reviewed = {source.name: _sha(source)}
    review_a = tmp_path / "review_a.json"
    review_b = tmp_path / "review_b.json"
    _review(review_a, reviewed, reviewer_id="correctness")
    _review(review_b, reviewed, reviewer_id="project-standards")
    seal_path = tmp_path / "seal.json"
    seal = {
        "round": "R476",
        "contract_sha256": "contract",
        "formal_authority": True,
        "plan_sha256": _sha(plan),
        "power_sha256": _sha(power),
        "code_review_a_sha256": _sha(review_a),
        "code_review_b_sha256": _sha(review_b),
        "reviewed_commit": COMMIT,
        "reviewer_ids": ["correctness", "project-standards"],
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
        commit_file_sha256=lambda _root, _commit, relative: reviewed[relative],
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
            commit_file_sha256=lambda _root, _commit, relative: reviewed[relative],
        )


def test_full_seal_verifier_rejects_shard_list_drift(tmp_path: Path) -> None:
    source = tmp_path / "runner.py"
    source.write_text("RUNNER = 1\n", encoding="utf-8")
    train = tmp_path / "train.json"
    train.write_text('["train|a|1"]\n', encoding="utf-8")
    review_a = tmp_path / "review_a.json"
    review_b = tmp_path / "review_b.json"
    reviewed = {source.name: _sha(source)}
    _review(review_a, reviewed, reviewer_id="correctness")
    _review(review_b, reviewed, reviewer_id="project-standards")
    seal_path = tmp_path / "seal.json"
    _write_hashed_json(
        seal_path,
        {
            "round": "R476",
            "contract_sha256": "contract",
            "formal_authority": True,
            "reviewed_commit": COMMIT,
            "reviewer_ids": ["correctness", "project-standards"],
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
            commit_file_sha256=lambda _root, _commit, relative: reviewed[relative],
        )


def test_review_coverage_binds_commit_and_independent_reviewers(tmp_path: Path) -> None:
    source = tmp_path / "runner.py"
    source.write_text("RUNNER = 1\n", encoding="utf-8")
    reviewed = {source.name: _sha(source)}
    review_a = tmp_path / "review_a.json"
    review_b = tmp_path / "review_b.json"
    _review(review_a, reviewed, reviewer_id="same")
    _review(review_b, reviewed, reviewer_id="same")
    def callback(_root: Path, _commit: str, relative: str) -> str:
        return reviewed[relative]

    with pytest.raises(RuntimeError, match="not independent"):
        validate_review_coverage(
            (review_a, review_b),
            repo_root=tmp_path,
            reviewed_files=(source,),
            commit_file_sha256=callback,
        )

    _review(review_b, reviewed, reviewer_id="other", commit="b" * 40)
    with pytest.raises(RuntimeError, match="reviewed_commit"):
        validate_review_coverage(
            (review_a, review_b),
            repo_root=tmp_path,
            reviewed_files=(source,),
            commit_file_sha256=callback,
        )


def test_full_seal_verifier_requires_bound_json_sidecars(tmp_path: Path) -> None:
    source = tmp_path / "runner.py"
    source.write_text("RUNNER = 1\n", encoding="utf-8")
    reviewed = {source.name: _sha(source)}
    review_a = tmp_path / "review_a.json"
    review_b = tmp_path / "review_b.json"
    _review(review_a, reviewed, reviewer_id="correctness")
    _review(review_b, reviewed, reviewer_id="standards")
    power = tmp_path / "power.json"
    _write_hashed_json(power, {"targets_materiality": True})
    seal_path = tmp_path / "seal.json"
    _write_hashed_json(
        seal_path,
        {
            "round": "R476",
            "contract_sha256": "contract",
            "formal_authority": True,
            "power_sha256": _sha(power),
            "reviewed_commit": COMMIT,
            "reviewer_ids": ["correctness", "standards"],
            "reviewed_files": reviewed,
            "sources": {"runner": {"path": source.name, "sha256": _sha(source)}},
            "shard_lists": {},
        },
    )
    Path(f"{power}.sha256").unlink()
    with pytest.raises(RuntimeError, match="missing hash sidecar"):
        verify_formal_seal(
            repo_root=tmp_path,
            seal_path=seal_path,
            round_id="R476",
            contract_sha256="contract",
            bound_files={"power_sha256": power},
            review_paths=(review_a, review_b),
            reviewed_files=(source,),
            expected_shards={},
            commit_file_sha256=lambda _root, _commit, relative: reviewed[relative],
        )


class _FakeEnvironment:
    def __init__(self, rows):
        self.rows = iter(rows)

    def reset(self):
        return "observation"

    def step(self, _action):
        done, tds_failed = next(self.rows)
        return "observation", 0.0, done, {"tds_failed": tds_failed}


def test_terminal_guard_is_the_real_training_and_evaluation_gate() -> None:
    accepted = TerminalGuardedEnvironment(
        _FakeEnvironment([(False, False), (False, False), (True, False)]),
        steps=3,
    )
    accepted.reset()
    accepted.step(None)
    accepted.step(None)
    accepted.step(None)

    premature = TerminalGuardedEnvironment(
        _FakeEnvironment([(True, False)]),
        steps=3,
    )
    premature.reset()
    with pytest.raises(RuntimeError, match="premature terminal"):
        premature.step(None)

    failed = TerminalGuardedEnvironment(
        _FakeEnvironment([(False, True)]),
        steps=3,
    )
    failed.reset()
    with pytest.raises(RuntimeError, match="TDS failure"):
        failed.step(None)


def test_analysis_package_owns_fail_closed_effect_construction(tmp_path: Path) -> None:
    manifests = {}
    for arm in ("a0", "a1"):
        for seed in (1, 2):
            path = tmp_path / "train" / arm / f"seed{seed}" / "manifest.json"
            manifests[path] = {
                "valid": arm != "a1" or seed != 2,
                "interaction_steps": 43_200,
                "base_state_sha256": f"base-{seed}",
                "reward_function_sha256": "reward",
                "stability": {
                    "critic_loss": {"stable": True},
                    "actor_loss": {"stable": True},
                },
            }
    context = ConfirmatoryAnalysisContext(
        round_id="R476",
        contract_sha256="contract",
        seal_sha256="seal",
        output_root=tmp_path,
        arms=("a0", "a1"),
        seeds=(1, 2),
        primary_metric="primary",
        secondary_metric="secondary",
        materiality_log=0.1,
        scope="test",
        read_hashed_json=lambda path: manifests[path],
        arm_factors=lambda arm: {"reward_access": arm == "a1"},
        paired_main_effects=lambda _stage, _metric: {
            "actor": [0.2, 0.3],
            "critic": [0.2, 0.3],
        },
        signflip_p_one_sided=lambda _values, _threshold: 0.01,
        exact_bootstrap_ci=lambda _values: (0.15, 0.35),
        apply_holm_two=lambda rows: [row.update({"holm_reject": True}) for row in rows.values()],
        design_valid=lambda: True,
        created_utc="2026-08-23T00:00:00+00:00",
    )

    payload = build_confirmatory_analysis(context, missing_shards=[])
    assert payload["classification"]["verdict"] == "INTEGRITY-INVALID"
    assert payload["classification"]["material_effect"] == "NOT_TESTED"
    assert all(
        row["material_effect"] == "NOT_TESTED"
        for row in payload["primary_materiality_tests"].values()
    )


def test_budget_and_eta_gates_are_executable(tmp_path: Path) -> None:
    (tmp_path / "payload.bin").write_bytes(b"12345")
    assert check_artifact_budget(tmp_path, max_bytes=5)["total_bytes"] == 5
    with pytest.raises(RuntimeError, match="artifact budget exceeded"):
        check_artifact_budget(tmp_path, max_bytes=4)
    eta = recalibrate_eta(
        {
            "wall_seconds": 100.0,
            "failed": [],
            "results": {f"shard-{index}": {"exit_code": 0} for index in range(16)},
        },
        remaining_training_shards=32,
        evaluation_wave_count=1,
    )
    assert eta["estimated_remaining_seconds"] == 300.0
    assert eta["concurrency_unchanged"] is True
