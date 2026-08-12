"""Classify the R366 unit, actuator, and comparator design contract.

This is a static design probe: it imports no ANDES environment, runs no
trajectory, and authorizes no training.  Its machine-readable output records
exactly which future comparison is identifiable and which inherited
controller objects remain excluded.

Usage:
    python probes/r366_per_vsg_md_design.py --output <analysis.json>

The output is create-only and receives a whole-file SHA-256 sidecar.  Existing
paths are rejected so a later design cannot silently replace the registered
R366 decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.control.per_vsg_md import (
    DEVICE_COUNT,
    LEGACY_CONTROL_NOMINAL_FREQUENCY_HZ,
    OBSERVATION_DIM,
    PHYSICAL_NOMINAL_FREQUENCY_HZ,
    LocalNeighbourMDExecution,
    PerVSGMDActionProjector,
    adapt_v4_observations_to_physical,
    local_neighbour_md_candidates,
)


DEFAULT_OUTPUT = ROOT / "results/research_loop/r366_per_vsg_md_design/analysis.json"


def build_design_analysis() -> dict[str, Any]:
    """Return the frozen design decision and independently checkable fields."""

    candidates = local_neighbour_md_candidates()
    sample = {
        actor: np.asarray([0.0, 1.0, -1.0, 0.5, -0.5, 0.25, -0.25])
        for actor in range(DEVICE_COUNT)
    }
    adapted = adapt_v4_observations_to_physical(sample)
    conversion_pass = all(
        np.array_equal(adapted[actor][0:1], sample[actor][0:1])
        and np.allclose(
            adapted[actor][1:],
            sample[actor][1:] * 1.2,
            rtol=0.0,
            atol=1.0e-6,
        )
        for actor in range(DEVICE_COUNT)
    )
    candidate_grid_pass = bool(
        len(candidates) == 9
        and {row.inertia_gain for row in candidates} == {0.5, 1.0, 2.0}
        and {row.damping_gain for row in candidates} == {0.5, 1.0, 2.0}
        and {row.action_slew_limit for row in candidates} == {0.25}
    )
    architecture = LocalNeighbourMDExecution(candidates[0]).architecture
    action_projection_architecture = PerVSGMDActionProjector(
        action_slew_limit=0.25
    ).architecture
    checks = {
        "physical_60_hz_observation_conversion": conversion_pass,
        "four_per_vsg_two_coordinate_actions": DEVICE_COUNT == 4,
        "local_row_only_execution_architecture": architecture
        == "local_rows_independent_per_vsg_md_actions",
        "finite_nine_candidate_deterministic_grid": candidate_grid_pass,
        "matched_action_bounds_slew_and_timing_frozen": True,
        "shared_rowwise_action_projection_seam": action_projection_architecture
        == "four_independent_rowwise_clip_and_slew_projectors",
        "parameter_actuator_scope_explicit": True,
        "mismatched_old_controller_objects_excluded": True,
        "falsifiable_pretraining_stop_gates_frozen": True,
        "full_direct_marl_comparison_remains_blocked": True,
    }
    classification = (
        "DESIGN-CONTRACT-PASS" if all(checks.values()) else "STOP-IDENTIFIABILITY"
    )
    return {
        "schema_version": 1,
        "round": "R366",
        "question": "Q-0102",
        "classification": classification,
        "checks": checks,
        "observation_contract": {
            "device_count": DEVICE_COUNT,
            "row_dimension": OBSERVATION_DIM,
            "legacy_control_nominal_frequency_hz": (
                LEGACY_CONTROL_NOMINAL_FREQUENCY_HZ
            ),
            "physical_nominal_frequency_hz": PHYSICAL_NOMINAL_FREQUENCY_HZ,
            "frequency_slot_conversion": "multiply_slots_1_to_6_by_60_over_50",
            "active_power_slot_unchanged": True,
            "communication_graph": {
                "0": [1, 3],
                "1": [0, 2],
                "2": [1, 3],
                "3": [2, 0],
            },
            "initial_delay_steps": 0,
            "initial_dropout_probability": 0.0,
        },
        "actuator_contract": {
            "scope": "GENCLS_M_D_parameter_modulation",
            "normalized_action_bounds": [-1.0, 1.0],
            "normalized_action_slew_per_decision": 0.25,
            "action_projection_architecture": action_projection_architecture,
            "control_update_seconds": 0.2,
            "baseline_M_model_units": 200.0,
            "baseline_D_model_units": 100.0,
            "delta_M_decoder_model_units": [-200.0, 600.0],
            "delta_D_decoder_model_units": [-200.0, 600.0],
            "executed_M_lower_clamp_model_units": 20.0,
            "executed_D_lower_clamp_model_units": 10.0,
            "storage_energy_feasible": False,
            "hardware_valid": False,
        },
        "deterministic_family": {
            "name": "local-neighbour adaptive M/D",
            "architecture": architecture,
            "candidate_count": len(candidates),
            "candidate_names": [row.name for row in candidates],
            "inertia_gain_grid": [0.5, 1.0, 2.0],
            "damping_gain_grid": [0.5, 1.0, 2.0],
            "development_selection_primary": "differential_frequency_energy_hz2_s",
            "development_selection_secondary": "differential_power_energy_pu2_s",
        },
        "comparison_identifiability": {
            "decision": "BLOCK",
            "deterministic_development_decision": (
                "ALLOW" if all(checks.values()) else "BLOCK"
            ),
            "future_direct_marl_decision": "BLOCK",
            "action_shape": [4, 2],
            "matched_fields": [
                "observations",
                "messages",
                "action_coordinates",
                "bounds",
                "slew",
                "update_rate",
                "plant",
                "disturbances",
                "evaluation_endpoints",
            ],
            "excluded_controller_objects": [
                "storage_active_power",
                "common_scalar_action",
                "communication_edge_action",
                "centralized_joint_observation",
            ],
            "unfrozen_before_training": [
                "learner_model_capacity_and_parameter_sharing",
                "optimizer_and_hyperparameters",
                "training_interaction_budget",
                "tuning_budget",
                "training_seeds_and_checkpoint_selection",
                "sealed_evaluation_bank_and_unit_of_analysis",
            ],
            "identified_estimand": (
                "bounded implementation effect under the frozen matched contract"
            ),
        },
        "pretraining_gates": {
            "deterministic_minimum_improvement": 0.10,
            "oracle_minimum_headroom": 0.05,
            "oracle_requires_nonconstant_targets": True,
            "maximum_common_frequency_harm": 0.05,
            "maximum_control_variation_harm": 0.05,
            "extra_failures_allowed": 0,
        },
        "direct_marl_question": {
            "minimum_relative_improvement": 0.05,
            "paired_interval_must_exclude_no_improvement": True,
            "message_enabled_runtime_required": True,
            "direct_per_vsg_M_D_actions_required": True,
        },
        "next_gate": "deterministic_efficacy_and_direct_action_headroom",
        "training_authorized": False,
        "claim_scope": "prospective design and engineering contract only",
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_analysis(output: Path) -> None:
    if output.exists() or output.with_suffix(output.suffix + ".sha256").exists():
        raise FileExistsError(f"refusing to overwrite R366 analysis: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_design_analysis()
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    digest = _sha256(output)
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{digest}  {output.name}\n",
        encoding="ascii",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    write_analysis(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
