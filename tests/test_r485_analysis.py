"""Outcome-blind statistical and learner-admissibility tests for R485."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r485_60hz_source_factorial.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("r485_analysis_test", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_hashed_json(path: Path, payload: dict) -> None:
    from hashlib import sha256

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    Path(f"{path}.sha256").write_text(
        f"{sha256(path.read_bytes()).hexdigest()}  {path.name}\n", encoding="ascii"
    )


def test_formal_authority_accepts_only_science_identical_post_canary_rebind(
    tmp_path: Path,
) -> None:
    from andes_rl_kundur.evaluation.r485_experiment import verify_formal_authority

    paths = {
        name: tmp_path / f"{name}.json"
        for name in (
            "resolved_parameter_card",
            "canary_admissibility",
            "code_review_a",
            "code_review_b",
            "rehearsal",
            "capacity",
            "owner_approval",
            "formal_seal",
        )
    }
    previous_path = tmp_path / "previous_parameter_card.json"
    previous = {
        "round": "R485",
        "design": {"seeds": [501, 502]},
        "objective_semantics_probe": {"passed": True},
        "sources": {"plan": {"sha256": "a" * 64}},
        "created_utc": "before",
    }
    current = {
        **previous,
        "sources": {
            "plan": {"sha256": "b" * 64},
            "power_plan": {"sha256": "c" * 64},
        },
        "created_utc": "after",
    }
    _write_hashed_json(previous_path, previous)
    _write_hashed_json(paths["resolved_parameter_card"], current)
    previous_sha = Path(f"{previous_path}.sha256").read_text().split()[0]
    current_sha = Path(f"{paths['resolved_parameter_card']}.sha256").read_text().split()[0]
    _write_hashed_json(
        paths["canary_admissibility"],
        {
            "round": "R485",
            "passed": True,
            "performance_or_endpoint_selection_performed": False,
        },
    )
    _write_hashed_json(
        paths["rehearsal"],
        {
            "round": "R485",
            "checks": {"same_path": True},
            "formal_outputs_created": False,
            "resolved_parameter_card_sha256": previous_sha,
        },
    )
    canary_root = tmp_path / "canary"
    _write_hashed_json(
        canary_root / "bases/seed500/manifest.json",
        {"resolved_parameter_card_sha256": previous_sha},
    )
    for index in range(8):
        _write_hashed_json(
            canary_root / f"train/arm{index}/seed500/manifest.json",
            {"resolved_parameter_card_sha256": previous_sha},
        )
    for index in range(48):
        _write_hashed_json(
            canary_root / f"eval/group{index // 4}/profile{index}.json",
            {"records": [{"resolved_parameter_card_sha256": previous_sha}]},
        )
    from andes_rl_kundur.evaluation.r485_experiment import _card_science_sha256

    _write_hashed_json(
        paths["capacity"],
        {
            "round": "R485",
            "safe_for_formal_launch": True,
            "selected_workers": 16,
            "native_threads_per_process": 1,
            "canary_contract_rebind": {
                "passed": True,
                "authority_only_changed_sources": ["plan", "power_plan"],
                "previous_parameter_card": {
                    "path": previous_path.relative_to(tmp_path).as_posix(),
                    "sha256": previous_sha,
                },
                "current_parameter_card_sha256": current_sha,
                "scientific_projection_sha256": _card_science_sha256(current),
                "canary_admissibility_sha256": Path(
                    f"{paths['canary_admissibility']}.sha256"
                ).read_text().split()[0],
                "rehearsal_sha256": Path(f"{paths['rehearsal']}.sha256")
                .read_text()
                .split()[0],
            },
        },
    )
    _write_hashed_json(
        paths["owner_approval"],
        {
            "round": "R485",
            "approved": False,
            "long_execution_authorized": False,
        },
    )
    for name in ("code_review_a", "code_review_b", "formal_seal"):
        _write_hashed_json(paths[name], {"round": "R485"})
    config = {
        "round": "R485",
        "execution": {"workers": 16},
        "paths": {
            **{name: str(path) for name, path in paths.items()},
            "canary_out": str(canary_root),
            "formal_out": str(tmp_path / "formal"),
        },
    }

    with pytest.raises(RuntimeError, match="owner approval"):
        verify_formal_authority(
            repo_root=tmp_path,
            config=config,
            expected_shards={},
            reviewed_files=(),
        )

    current["design"] = {"seeds": [501, 999]}
    _write_hashed_json(paths["resolved_parameter_card"], current)
    with pytest.raises(RuntimeError, match="rebind drift"):
        verify_formal_authority(
            repo_root=tmp_path,
            config=config,
            expected_shards={},
            reviewed_files=(),
        )


def test_formal_authority_rejects_hash_valid_owner_denial(tmp_path: Path) -> None:
    from andes_rl_kundur.evaluation.r485_experiment import verify_formal_authority

    paths = {
        name: tmp_path / f"{name}.json"
        for name in (
            "resolved_parameter_card",
            "canary_admissibility",
            "code_review_a",
            "code_review_b",
            "rehearsal",
            "capacity",
            "owner_approval",
            "formal_seal",
        )
    }
    for name, path in paths.items():
        _write_hashed_json(path, {"round": "R485", "name": name})
    _write_hashed_json(
        paths["resolved_parameter_card"],
        {"round": "R485", "objective_semantics_probe": {"passed": True}},
    )
    _write_hashed_json(
        paths["canary_admissibility"],
        {
            "round": "R485",
            "passed": True,
            "performance_or_endpoint_selection_performed": False,
        },
    )
    _write_hashed_json(
        paths["rehearsal"],
        {
            "round": "R485",
            "checks": {"same_path": True},
            "formal_outputs_created": False,
            "resolved_parameter_card_sha256": Path(
                f"{paths['resolved_parameter_card']}.sha256"
            )
            .read_text()
            .split()[0],
        },
    )
    _write_hashed_json(
        paths["capacity"],
        {
            "round": "R485",
            "safe_for_formal_launch": True,
            "selected_workers": 16,
            "native_threads_per_process": 1,
        },
    )
    _write_hashed_json(
        paths["owner_approval"],
        {
            "round": "R485",
            "approved": False,
            "long_execution_authorized": False,
            "approved_scope": "denied",
        },
    )
    config = {
        "round": "R485",
        "execution": {"workers": 16},
        "paths": {name: str(path) for name, path in paths.items()},
    }

    with pytest.raises(RuntimeError, match="owner approval"):
        verify_formal_authority(
            repo_root=tmp_path,
            config=config,
            expected_shards={},
            reviewed_files=(),
        )


def test_formal_authority_rejects_owner_scope_that_is_not_exact_attempt(
    tmp_path: Path,
) -> None:
    from andes_rl_kundur.evaluation.r485_experiment import verify_formal_authority

    paths = {
        name: tmp_path / f"{name}.json"
        for name in (
            "resolved_parameter_card",
            "canary_admissibility",
            "code_review_a",
            "code_review_b",
            "rehearsal",
            "capacity",
            "owner_approval",
            "formal_seal",
        )
    }
    _write_hashed_json(
        paths["resolved_parameter_card"],
        {"round": "R485", "objective_semantics_probe": {"passed": True}},
    )
    _write_hashed_json(
        paths["canary_admissibility"],
        {
            "round": "R485",
            "passed": True,
            "performance_or_endpoint_selection_performed": False,
        },
    )
    _write_hashed_json(
        paths["rehearsal"],
        {
            "round": "R485",
            "checks": {"same_path": True},
            "formal_outputs_created": False,
            "resolved_parameter_card_sha256": Path(
                f"{paths['resolved_parameter_card']}.sha256"
            )
            .read_text()
            .split()[0],
        },
    )
    _write_hashed_json(
        paths["capacity"],
        {
            "round": "R485",
            "safe_for_formal_launch": True,
            "selected_workers": 16,
            "native_threads_per_process": 1,
        },
    )
    attempt_id = "r485-formal-20260828-a"
    _write_hashed_json(
        paths["formal_seal"],
        {"round": "R485", "attempt_id": attempt_id, "resume": False},
    )
    _write_hashed_json(
        paths["owner_approval"],
        {
            "round": "R485",
            "approved": True,
            "long_execution_authorized": True,
            "approved_scope": "development-canary-only",
            "approved_action": "launch-r485-formal",
            "attempt_id": attempt_id,
        },
    )
    for name in ("code_review_a", "code_review_b"):
        _write_hashed_json(paths[name], {"round": "R485", "name": name})
    config = {
        "round": "R485",
        "execution": {"workers": 16},
        "paths": {
            **{name: str(path) for name, path in paths.items()},
            "formal_out": str(tmp_path / "formal"),
            "canary_out": str(tmp_path / "canary"),
        },
    }

    with pytest.raises(RuntimeError, match="owner approval scope"):
        verify_formal_authority(
            repo_root=tmp_path,
            config=config,
            expected_shards={},
            reviewed_files=(),
        )


def test_registered_formal_shards_close_208_cells_and_5088_traces() -> None:
    from andes_rl_kundur.evaluation.r485_experiment import (
        expected_artifacts,
        registered_shards,
    )

    runner = _load_runner()
    config = runner.load_config(ROOT / "memory/rounds/R485/config.json")

    shards = registered_shards(config, scope="formal")

    assert len(shards["base"]) == 26
    assert len(shards["train"]) == 208
    assert len(shards["eval"]) == 212
    assert len(set().union(*[set(values) for values in shards.values()])) == 446
    assert len(shards["eval"]) * 4 * 6 == 5_088
    assert "train|formal|an_cn_r0|501" in shards["train"]
    assert "eval|formal|fresh|local_neighbour_md_km2_kd2|none" in shards["eval"]
    artifacts = expected_artifacts(config, root=ROOT / "unused", scope="formal")
    assert len(artifacts["base"]) == 26
    assert len(artifacts["train"]) == 208
    assert len(artifacts["eval"]) == 212 * 4


def test_registered_shards_prepare_base_states_without_a_donor_bank() -> None:
    from andes_rl_kundur.evaluation.r485_experiment import registered_shards

    runner = _load_runner()
    config = runner.load_config(ROOT / "memory/rounds/R485/config.json")

    shards = registered_shards(config, scope="formal")

    assert "base|formal|501" in shards["base"]
    assert "donor" not in shards
    assert config["parameter_card"]["source_routing"]["placebo"] == (
        "same_time_row_permutation_rho_i_plus_1"
    )
    assert config["parameter_card"]["source_routing"]["exogenous_donor_bank"] is False


def test_formal_output_is_attempt_scoped_and_partial_attempt_is_not_resumed(
    tmp_path: Path,
) -> None:
    from andes_rl_kundur.evaluation.r485_experiment import attempt_output_root

    seal = tmp_path / "formal_seal.json"
    _write_hashed_json(
        seal,
        {"round": "R485", "attempt_id": "r485-formal-20260828-a", "resume": False},
    )
    config = {
        "paths": {
            "formal_out": "results/r485",
            "canary_out": "results/r485-canary",
            "formal_seal": str(seal),
        }
    }

    assert attempt_output_root(tmp_path, config, scope="formal") == (
        tmp_path / "results/r485/r485-formal-20260828-a"
    )
    assert attempt_output_root(tmp_path, config, scope="canary") == (
        tmp_path / "results/r485-canary"
    )


def test_analysis_fails_closed_before_any_available_case_science(
    tmp_path: Path,
) -> None:
    from andes_rl_kundur.evaluation.r485_experiment import analyse_result_root

    runner = _load_runner()
    config = runner.load_config(ROOT / "memory/rounds/R485/config.json")

    result = analyse_result_root(
        repo_root=ROOT,
        config=config,
        root=tmp_path / "missing",
        scope="formal",
    )

    assert result["status"] == "EXECUTION-INCOMPLETE"
    assert result["inventory"]["expected_terminal_artifacts"] == 26 + 208 + 848
    assert result["inventory"]["verified_terminal_artifacts"] == 0
    assert result["primary_inference"]["status"] == "NOT-TESTED"
    assert result["available_case_analysis_performed"] is False


def test_trace_validator_rejects_six_identity_only_shells() -> None:
    from andes_rl_kundur.evaluation.r485_experiment import (
        evaluation_contracts,
        validate_trace_block,
    )

    contract = evaluation_contracts()["same"]
    profile = next(row for row in contract["profiles"] if row["profile_id"] == "canary_eval_a")
    records = [
        {
            "arm_id": "an_cn_r0",
            "training_seed": 500,
            "profile_id": "canary_eval_a",
            "bank": "same",
            "bank_contract_sha256": contract["sha256"],
            "environment_seed": 401,
            "resolved_parameter_card_sha256": "a" * 64,
            "scenario_id": scenario["scenario_id"],
        }
        for scenario in profile["scenarios"]
    ]

    with pytest.raises(RuntimeError, match="lineage|150 steps"):
        validate_trace_block(
            records,
            contract=contract,
            expected_profile="canary_eval_a",
            expected_arm="an_cn_r0",
            expected_seed=500,
            expected_card_sha256="a" * 64,
        )


def test_learner_gate_accepts_floor_alpha_only_when_other_signals_are_live() -> None:
    from andes_rl_kundur.evaluation.r485_experiment import (
        assess_learner_admissibility,
    )
    live = {
        "weights_changed": True,
        "update_count": 42_945,
        "all_finite": True,
        "actor_grad_nonzero_fraction": 1.0,
        "reward_std": 0.1,
        "td_target_std": 0.2,
        "policy_state_sensitivity": 1.0e-3,
        "executed_action_std": 2.0e-3,
        "action_saturation_fraction": 0.2,
        "log_std_at_lower_bound_fraction": 0.0,
        "alpha_at_floor": True,
        "routing_oracle_passed": True,
        "executed_action_bellman_passed": True,
    }
    collapsed = {**live, "policy_state_sensitivity": 0.0, "executed_action_std": 0.0}

    assert assess_learner_admissibility(live)["passed"] is True
    result = assess_learner_admissibility(collapsed)
    assert result["passed"] is False
    assert "policy_state_sensitivity" in result["failures"]
    assert "executed_action_variation" in result["failures"]


def test_canary_requires_deterministic_same_and_fresh_reference_paths(
    tmp_path: Path,
) -> None:
    from andes_rl_kundur.evaluation.r485_experiment import (
        build_canary_admissibility,
        evaluation_contracts,
    )

    result = build_canary_admissibility(
        root=tmp_path,
        card_sha256="a" * 64,
        arms=(),
        seed=500,
        contracts=evaluation_contracts(),
    )

    assert result["passed"] is False
    assert set(result["references"]) == {"same", "fresh"}
    assert any("same:zero" in failure for failure in result["failures"])
    assert any(
        "fresh:local_neighbour_md_km2_kd2" in failure
        for failure in result["failures"]
    )


def test_learner_objective_flags_are_derived_from_probe_not_constants() -> None:
    from andes_rl_kundur.evaluation.r485_experiment import objective_gate_flags
    probe = {
        "replay_actor_rows_are_canonical": True,
        "replay_critic_rows_are_canonical": False,
        "current_critic_uses_executed_action": True,
        "target_critic_uses_projected_action": True,
        "actor_critic_uses_projected_action": False,
    }

    assert objective_gate_flags(probe) == {
        "routing_oracle_passed": False,
        "executed_action_bellman_passed": False,
    }


def test_tds_ontology_separates_integrity_from_controller_failure() -> None:
    from andes_rl_kundur.evaluation.r485_experiment import resolve_tds

    assert resolve_tds(primary_failed=False, reproduction_failed=None) == "COMPLETE"
    assert resolve_tds(primary_failed=True, reproduction_failed=None) == "REPRODUCTION-REQUIRED"
    assert resolve_tds(primary_failed=True, reproduction_failed=True) == "COMPLETE-GUARD-FAIL"
    assert resolve_tds(primary_failed=True, reproduction_failed=False) == "INTEGRITY-INVALID"
    with pytest.raises(ValueError, match="reproduction"):
        resolve_tds(primary_failed=False, reproduction_failed=True)


def test_zero_action_rehearsal_checks_command_and_runtime_md_readback() -> None:
    from andes_rl_kundur.evaluation.r485_experiment import zero_action_md_readback

    record = {
        "identity": {
            "baseline_m0": [140.0, 260.0, 200.0, 220.0],
            "baseline_d0": [50.0, 150.0, 90.0, 130.0],
        },
        "steps": [
            {
                "raw_action_norm": [[0.0, 0.0]] * 4,
                "projected_action_norm": [[0.0, 0.0]] * 4,
                "M_commanded": [140.0, 260.0, 200.0, 220.0],
                "D_commanded": [50.0, 150.0, 90.0, 130.0],
                "M_es": [140.0, 260.0, 200.0, 220.0],
                "D_es": [50.0, 150.0, 90.0, 130.0],
            }
        ],
    }

    assert zero_action_md_readback([record]) is True
    record["steps"][0]["M_es"][0] = 70.0
    assert zero_action_md_readback([record]) is False


def test_rehearsal_checks_live_60hz_observation_identity_exactly_once() -> None:
    from andes_rl_kundur.evaluation.r485_experiment import (
        canonical_observation_readback,
    )

    raw = np.asarray([[0.5, 0.1, -0.2, 0.3, -0.4, 0.5, -0.6]] * 4)
    canonical = raw.copy()
    canonical[:, 1:] *= 1.2
    frequency_deviation = canonical[:, 1] * 3.0 / (2.0 * np.pi)
    record = {
        "steps": [
            {
                "raw_observation": {
                    str(index): raw[index].tolist() for index in range(4)
                },
                "canonical_observation": canonical.tolist(),
                "observation_frequency_deviation_hz": frequency_deviation.tolist(),
                "frequency_deviation_hz": (frequency_deviation + 0.01).tolist(),
            }
        ]
    }

    assert canonical_observation_readback([record]) is True
    record["steps"][0]["canonical_observation"][0][1] *= 1.2
    assert canonical_observation_readback([record]) is False


def test_tds_path_classifies_only_unaffected_complete_policies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import andes_rl_kundur.evaluation.r485_experiment as analysis

    profiles = ("p1", "p2")
    reference = "local_neighbour_md_km2_kd2"
    summaries = [
        {"profile_id": profile, "arm_id": reference, "training_seed": None}
        for profile in profiles
    ]
    summaries.extend(
        {"profile_id": profile, "arm_id": "a", "training_seed": 1}
        for profile in profiles
    )
    summaries.append({"profile_id": "p1", "arm_id": "b", "training_seed": 2})
    observed: dict[str, object] = {}

    def classify(rows, **kwargs):
        observed["rows"] = rows
        observed.update(kwargs)
        return {"classification": "AVAILABLE", "scientific_outcome": "AVAILABLE"}

    monkeypatch.setattr(analysis, "classify_learned_guard", classify)
    result = analysis.classify_available_policy_qualification(
        summaries,
        policies=(("a", 1), ("b", 2)),
        profiles=profiles,
        deterministic_reference_gate={"gate": {"passed_4_of_4": True}},
        contract={
            "parameter_card": {
                "threshold_sensitivity": {
                    "primary": {"frequency": 1.03, "action": 1.1}
                }
            }
        },
    )

    assert observed["policies"] == (("a", 1),)
    assert observed["require_complete_policy_roster"] is False
    assert result["available_policy_count"] == 1
    assert result["excluded_policy_count"] == 1


def test_statistics_contract_has_no_data_dependent_fallback() -> None:
    runner = _load_runner()
    contract = runner.build_parameter_card()["statistics"]

    assert contract["estimand"] == "seed_level_hodges_lehmann_location_pseudomedian"
    assert contract["null_boundary"] == "theta_HL <= log(1.10)"
    assert contract["test"] == "exact_one_sided_wilcoxon_signed_rank"
    assert contract["multiplicity"] == "Holm_family_of_four"
    assert contract["ties_zeros_or_symmetry_failure"] == "ASSUMPTION-LIMITED"
    assert contract["fallback"] is None
    assert contract["main_effect_coordinate"] == (
        "log(placebo_P_loss / authentic_N_loss)"
    )


def _factorial_rows(*, tied: bool) -> list[dict]:
    rows: list[dict] = []
    for seed in range(501, 527):
        shift = 0.0 if tied else (seed - 500) / 1000.0
        for actor in ("N", "P"):
            for critic in ("N", "P"):
                for reward in (0, 1):
                    for profile in ("p1", "p2", "p3", "p4"):
                        log_loss = (
                            (actor == "P") * (0.20 + shift)
                            + (critic == "P") * (0.18 + 1.7 * shift)
                            + (actor == "P")
                            * (critic == "P")
                            * (-0.08 + 0.3 * shift)
                            + (critic == "P")
                            * reward
                            * (0.12 + 0.7 * shift)
                        )
                        rows.append(
                            {
                                "stage": "final",
                                "seed": seed,
                                "actor_source": actor,
                                "critic_source": critic,
                                "reward_access": reward,
                                "profile": profile,
                                "disturbance_differential_energy": float(
                                    np.exp(log_loss)
                                ),
                            }
                        )
    return rows


def test_factorial_inference_uses_hl_exact_rank_and_holm_without_fallback() -> None:
    from andes_rl_kundur.evaluation.r485_experiment import factorial_inference

    result = factorial_inference(
        _factorial_rows(tied=False),
        expected_seeds=range(501, 527),
        expected_profiles=("p1", "p2", "p3", "p4"),
    )

    assert result["status"] == "COMPLETE"
    assert result["fallback"] is None
    assert set(result["tests"]) == {
        "actor_main",
        "critic_main",
        "actor_x_critic",
        "critic_x_reward",
    }
    assert all(row["hodges_lehmann"] is not None for row in result["tests"].values())
    assert all("holm" in row for row in result["tests"].values())


def test_factorial_inference_names_authentic_over_placebo_direction() -> None:
    from andes_rl_kundur.evaluation.r485_experiment import factorial_inference

    result = factorial_inference(
        _factorial_rows(tied=False),
        expected_seeds=range(501, 527),
        expected_profiles=("p1", "p2", "p3", "p4"),
    )

    assert result["effect_coordinate"] == (
        "positive main effects mean the authentic N source lowers loss relative "
        "to the row-permuted P placebo; interaction signs follow each registered "
        "ratio-of-ratios"
    )
    assert result["tests"]["actor_main"]["contrast_ratio"] == (
        "placebo_loss / authentic_loss"
    )
    assert result["tests"]["actor_main"]["geometric_location_ratio"] > 1.10
    assert result["tests"]["actor_main"]["holm"]["reject"] is True


def test_factorial_inference_marks_tied_exact_ranks_assumption_limited() -> None:
    from andes_rl_kundur.evaluation.r485_experiment import factorial_inference

    result = factorial_inference(
        _factorial_rows(tied=True),
        expected_seeds=range(501, 527),
        expected_profiles=("p1", "p2", "p3", "p4"),
    )

    assert result["status"] == "ASSUMPTION-LIMITED"
    assert result["fallback"] is None
    assert all(row["p_one_sided"] is None for row in result["tests"].values())
    assert all("holm" not in row for row in result["tests"].values())


def test_outcome_mapping_keeps_source_effect_separate_from_policy_result() -> None:
    from andes_rl_kundur.evaluation.r485_experiment import (
        classify_registered_outcome,
    )

    source_only = classify_registered_outcome(
        factorial={
            "status": "COMPLETE",
            "tests": {
                "actor_main": {"holm": {"reject": True}},
                "critic_main": {"holm": {"reject": False}},
            },
        },
        guard={
            "passing_count": 0,
            "policy_decisions": [
                {
                    "aggregate_joint_endpoint_target": {
                        "off_diagonal_response_energy": False,
                        "disturbance_differential_energy": False,
                    }
                }
            ],
        },
    )
    complete_without_source = classify_registered_outcome(
        factorial={
            "status": "COMPLETE",
            "tests": {"actor_main": {"holm": {"reject": False}}},
        },
        guard={
            "passing_count": 1,
            "policy_decisions": [
                {
                    "aggregate_joint_endpoint_target": {
                        "off_diagonal_response_energy": True,
                        "disturbance_differential_energy": True,
                    }
                }
            ],
        },
    )
    endpoint_only = classify_registered_outcome(
        factorial={"status": "ASSUMPTION-LIMITED", "tests": {}},
        guard={
            "passing_count": 0,
            "policy_decisions": [
                {
                    "aggregate_joint_endpoint_target": {
                        "off_diagonal_response_energy": True,
                        "disturbance_differential_energy": True,
                    }
                }
            ],
        },
    )
    invalid_reference = classify_registered_outcome(
        factorial={"status": "COMPLETE", "tests": {}},
        guard={
            "classification": "LEARNED-COMPLETE-GUARD-REFERENCE-INVALID",
            "scientific_outcome": "NOT_TESTED",
            "passing_count": 1,
            "policy_decisions": [
                {
                    "aggregate_joint_endpoint_target": {
                        "off_diagonal_response_energy": True,
                        "disturbance_differential_energy": True,
                    }
                }
            ],
        },
    )

    assert source_only["status"] == "VALID-NEGATIVE"
    assert source_only["source_inference"]["status"] == "MATERIAL-EFFECT"
    assert source_only["source_inference"]["material_effect_established"] is True
    assert complete_without_source["status"] == "VALID-POSITIVE"
    assert complete_without_source["source_inference"]["status"] == (
        "MATERIAL-EFFECT-NOT-ESTABLISHED"
    )
    assert endpoint_only["status"] == "VALID-MIXED"
    assert endpoint_only["source_inference"]["status"] == "ASSUMPTION-LIMITED"
    assert invalid_reference["status"] == "INTEGRITY-INVALID"


def test_threshold_and_claim_contracts_are_frozen_before_results() -> None:
    runner = _load_runner()
    card = runner.build_parameter_card()

    assert card["threshold_sensitivity"]["frequency_multipliers"] == [1.0, 1.03, 1.05, 1.1]
    assert card["threshold_sensitivity"]["action_multipliers"] == [1.1, 1.2, 1.5, 2.0]
    assert card["threshold_sensitivity"]["primary"] == {"frequency": 1.03, "action": 1.1}
    assert card["threshold_sensitivity"]["post_result_threshold_additions"] is False
    assert set(card["outcome_to_claim"]) == {
        "VALID-POSITIVE",
        "VALID-MIXED",
        "VALID-NEGATIVE",
        "ASSUMPTION-LIMITED",
        "INTEGRITY-INVALID",
    }
    assert card["outcome_to_claim"]["VALID-POSITIVE"] == (
        "at least one frozen policy satisfies both endpoint targets and the "
        "registered complete guard; source inference is reported separately"
    )
    assert card["outcome_to_claim"]["VALID-MIXED"] == (
        "at least one frozen policy satisfies both endpoint targets, but none "
        "satisfies the registered complete guard"
    )
