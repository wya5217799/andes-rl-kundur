from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from probes.r366_per_vsg_md_design import build_design_analysis


def test_design_analysis_allows_deterministic_development_but_blocks_training() -> None:
    analysis = build_design_analysis()

    assert analysis["classification"] == "DESIGN-CONTRACT-PASS"
    assert all(analysis["checks"].values())
    assert analysis["comparison_identifiability"]["decision"] == "BLOCK"
    assert analysis["comparison_identifiability"]["deterministic_development_decision"] == "ALLOW"
    assert analysis["comparison_identifiability"]["future_direct_marl_decision"] == "BLOCK"
    assert analysis["comparison_identifiability"]["action_shape"] == [4, 2]
    assert analysis["observation_contract"]["physical_nominal_frequency_hz"] == 60.0
    assert analysis["observation_contract"]["legacy_control_nominal_frequency_hz"] == 50.0
    assert analysis["deterministic_family"]["candidate_count"] == 9
    assert analysis["deterministic_family"]["architecture"] == (
        "local_rows_independent_per_vsg_md_actions"
    )
    assert analysis["actuator_contract"]["scope"] == "GENCLS_M_D_parameter_modulation"
    assert analysis["actuator_contract"]["action_projection_architecture"] == (
        "four_independent_rowwise_clip_and_slew_projectors"
    )
    assert analysis["actuator_contract"]["storage_energy_feasible"] is False
    assert analysis["training_authorized"] is False
    assert analysis["next_gate"] == "deterministic_efficacy_and_direct_action_headroom"


def test_design_analysis_blocks_old_mismatched_controller_objects() -> None:
    analysis = build_design_analysis()

    excluded = analysis["comparison_identifiability"]["excluded_controller_objects"]
    assert set(excluded) == {
        "storage_active_power",
        "common_scalar_action",
        "communication_edge_action",
        "centralized_joint_observation",
    }
    assert analysis["direct_marl_question"]["minimum_relative_improvement"] == 0.05
    assert analysis["pretraining_gates"]["deterministic_minimum_improvement"] == 0.10
    assert analysis["pretraining_gates"]["oracle_minimum_headroom"] == 0.05
    assert analysis["pretraining_gates"]["oracle_requires_nonconstant_targets"] is True
    assert set(analysis["comparison_identifiability"]["unfrozen_before_training"]) == {
        "learner_model_capacity_and_parameter_sharing",
        "optimizer_and_hyperparameters",
        "training_interaction_budget",
        "tuning_budget",
        "training_seeds_and_checkpoint_selection",
        "sealed_evaluation_bank_and_unit_of_analysis",
    }


def test_direct_probe_entry_writes_create_only_analysis_and_sidecar(tmp_path: Path) -> None:
    output = tmp_path / "analysis.json"
    completed = subprocess.run(
        [
            sys.executable,
            "probes/r366_per_vsg_md_design.py",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert output.is_file()
    assert output.with_suffix(".json.sha256").is_file()
    repeated = subprocess.run(
        [
            sys.executable,
            "probes/r366_per_vsg_md_design.py",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert repeated.returncode != 0
    assert "refusing to overwrite" in repeated.stderr
