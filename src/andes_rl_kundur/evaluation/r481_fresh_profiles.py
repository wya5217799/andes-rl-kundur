"""R481 fresh-holdout direct-M/D deterministic bank contract and Phase-1A gate.

Motivation: the corrected-plan Phase 1A re-validates the frozen nine-law
deterministic bank under the corrected card.  The R399 profile rows and the
R401 canary rows were all viewed in diagnostics and permanently lost
unseen-holdout status, so this module prospectively generates six genuinely
fresh profile rows (2 development + 4 evaluation), freezes them as a contract
JSON + sha256 sidecar, and applies the Phase-1A gate: the development-selected
winner must be finite and guard-valid on all four evaluation profiles
(one-to-three passing profiles cannot open the gate).

The classification machinery (summarise_profile / classify_bank) is reused
unchanged from ``andes_rl_kundur.evaluation.md_decoupling_headroom`` with the
fresh contract passed explicitly.  No ANDES import and no learning code.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from andes_rl_kundur.evaluation.md_decoupling_headroom import (
    DIFFERENTIAL_TRANSFORM,
    LOAD_IDS,
    PAIR_KINDS,
)

ROUND_ID = "R481"
GENERATOR_SEED = 481
MAX_DRAW_ATTEMPTS = 1000

LOCATIONS = ("PQ_0", "PQ_1", "PQ_Bus14", "PQ_Bus15")
M_GRID = tuple(range(140, 261, 10))
D_GRID = tuple(range(50, 151, 10))
LOAD14_GRID = tuple(round(1.80 + 0.02 * index, 2) for index in range(41))
LOAD15_GRID = tuple(round(0.10 + 0.02 * index, 2) for index in range(31))
PROBE_GRID = tuple(round(0.70 + 0.05 * index, 2) for index in range(10))
LOCALIZED_GRID = tuple(round(0.80 + 0.05 * index, 2) for index in range(9))

# All rows a diagnostic ever viewed: six R399 rows + eight R401 canary rows.
VIEWED_ROWS: tuple[dict[str, Any], ...] = (
    {
        "baseline_m0": (160.0, 240.0, 180.0, 220.0),
        "baseline_d0": (70.0, 130.0, 90.0, 110.0),
        "load14": 2.28,
        "load15": 0.20,
        "probe": 0.8,
        "location": "PQ_0",
        "localized": 0.9,
    },
    {
        "baseline_m0": (220.0, 180.0, 240.0, 160.0),
        "baseline_d0": (110.0, 90.0, 130.0, 70.0),
        "load14": 2.08,
        "load15": 0.60,
        "probe": 1.0,
        "location": "PQ_Bus14",
        "localized": 1.1,
    },
    {
        "baseline_m0": (150.0, 250.0, 190.0, 210.0),
        "baseline_d0": (60.0, 140.0, 80.0, 120.0),
        "load14": 2.48,
        "load15": 0.30,
        "probe": 0.9,
        "location": "PQ_1",
        "localized": 1.0,
    },
    {
        "baseline_m0": (250.0, 150.0, 210.0, 190.0),
        "baseline_d0": (140.0, 60.0, 120.0, 80.0),
        "load14": 2.18,
        "load15": 0.10,
        "probe": 0.7,
        "location": "PQ_Bus15",
        "localized": 0.8,
    },
    {
        "baseline_m0": (170.0, 230.0, 250.0, 150.0),
        "baseline_d0": (75.0, 125.0, 145.0, 55.0),
        "load14": 1.88,
        "load15": 0.60,
        "probe": 1.1,
        "location": "PQ_0",
        "localized": 1.2,
    },
    {
        "baseline_m0": (230.0, 170.0, 150.0, 250.0),
        "baseline_d0": (125.0, 75.0, 55.0, 145.0),
        "load14": 2.38,
        "load15": 0.30,
        "probe": 0.8,
        "location": "PQ_Bus14",
        "localized": 0.9,
    },
    {
        "baseline_m0": (150.0, 250.0, 170.0, 230.0),
        "baseline_d0": (60.0, 140.0, 80.0, 120.0),
        "load14": 2.24,
        "load15": 0.42,
        "probe": 0.85,
        "location": "PQ_1",
        "localized": 0.95,
    },
    {
        "baseline_m0": (230.0, 150.0, 250.0, 170.0),
        "baseline_d0": (120.0, 60.0, 140.0, 80.0),
        "load14": 2.02,
        "load15": 0.66,
        "probe": 1.05,
        "location": "PQ_Bus15",
        "localized": 1.15,
    },
    {
        "baseline_m0": (210.0, 190.0, 160.0, 240.0),
        "baseline_d0": (130.0, 70.0, 110.0, 90.0),
        "load14": 2.42,
        "load15": 0.14,
        "probe": 0.75,
        "location": "PQ_0",
        "localized": 0.85,
    },
    {
        "baseline_m0": (240.0, 160.0, 190.0, 210.0),
        "baseline_d0": (90.0, 110.0, 70.0, 130.0),
        "load14": 2.12,
        "load15": 0.54,
        "probe": 0.95,
        "location": "PQ_Bus14",
        "localized": 1.05,
    },
    {
        "baseline_m0": (140.0, 260.0, 200.0, 220.0),
        "baseline_d0": (50.0, 150.0, 90.0, 130.0),
        "load14": 2.56,
        "load15": 0.34,
        "probe": 0.9,
        "location": "PQ_0",
        "localized": 1.0,
    },
    {
        "baseline_m0": (260.0, 140.0, 220.0, 200.0),
        "baseline_d0": (150.0, 50.0, 130.0, 90.0),
        "load14": 2.06,
        "load15": 0.26,
        "probe": 0.8,
        "location": "PQ_Bus14",
        "localized": 0.9,
    },
    {
        "baseline_m0": (180.0, 240.0, 150.0, 210.0),
        "baseline_d0": (70.0, 130.0, 60.0, 110.0),
        "load14": 1.96,
        "load15": 0.64,
        "probe": 1.0,
        "location": "PQ_Bus15",
        "localized": 1.1,
    },
    {
        "baseline_m0": (220.0, 200.0, 260.0, 140.0),
        "baseline_d0": (110.0, 90.0, 150.0, 50.0),
        "load14": 2.32,
        "load15": 0.46,
        "probe": 1.1,
        "location": "PQ_1",
        "localized": 1.2,
    },
)


def _row_tuple(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        tuple(row["baseline_m0"]),
        tuple(row["baseline_d0"]),
        float(row["load14"]),
        float(row["load15"]),
        float(row["probe"]),
        str(row["location"]),
        float(row["localized"]),
    )


_VIEWED_TUPLES = {_row_tuple(row) for row in VIEWED_ROWS}
_VIEWED_TRIPLES = {
    (float(row["probe"]), str(row["location"]), float(row["localized"]))
    for row in VIEWED_ROWS
}


def _draw_row(rng: np.random.Generator) -> dict[str, Any]:
    baseline_m0 = tuple(
        int(value) for value in rng.choice(np.asarray(M_GRID), size=4, replace=False)
    )
    baseline_d0 = tuple(
        int(value) for value in rng.choice(np.asarray(D_GRID), size=4, replace=False)
    )
    load14 = float(rng.choice(np.asarray(LOAD14_GRID)))
    load15 = float(rng.choice(np.asarray(LOAD15_GRID)))
    probe = float(rng.choice(np.asarray(PROBE_GRID)))
    location = str(rng.choice(np.asarray(LOCATIONS)))
    localized = float(rng.choice(np.asarray(LOCALIZED_GRID)))
    return {
        "baseline_m0": baseline_m0,
        "baseline_d0": baseline_d0,
        "load14": load14,
        "load15": load15,
        "probe": probe,
        "location": location,
        "localized": localized,
    }


def build_fresh_rows(seed: int = GENERATOR_SEED) -> list[dict[str, Any]]:
    """Return six genuinely fresh profile rows (2 development + 4 evaluation).

    Rejection loop: a drawn row is redrawn when its full value tuple or its
    probe/location/localized triple collides with any viewed row or with an
    already-accepted fresh row.  Deterministic under the registered seed.
    """

    rng = np.random.default_rng(seed)
    accepted: list[dict[str, Any]] = []
    attempts = 0
    while len(accepted) < 6 and attempts < MAX_DRAW_ATTEMPTS:
        attempts += 1
        row = _draw_row(rng)
        if _row_tuple(row) in _VIEWED_TUPLES:
            continue
        if (row["probe"], row["location"], row["localized"]) in _VIEWED_TRIPLES:
            continue
        if any(_row_tuple(row) == _row_tuple(other) for other in accepted):
            continue
        if any(
            (row["probe"], row["location"], row["localized"])
            == (other["probe"], other["location"], other["localized"])
            for other in accepted
        ):
            continue
        accepted.append(row)
    if len(accepted) != 6:
        raise RuntimeError(
            f"fresh profile generator exhausted {attempts} attempts with "
            f"{len(accepted)} accepted rows"
        )
    return accepted


def _signed_scenarios(profile: Mapping[str, Any]) -> list[dict[str, Any]]:
    profile_id = str(profile["profile_id"])
    probe = float(profile["probe_magnitude"])
    localized = float(profile["localized_magnitude"])
    location = str(profile["localized_location"])
    common = {load_id: probe / 4.0 for load_id in LOAD_IDS}
    differential = {
        "PQ_0": probe / 4.0,
        "PQ_1": probe / 4.0,
        "PQ_Bus14": -probe / 4.0,
        "PQ_Bus15": -probe / 4.0,
    }
    bases = {
        "common": (probe, common),
        "differential": (probe, differential),
        "localized": (localized, {location: localized}),
    }
    scenarios: list[dict[str, Any]] = []
    for pair_kind in PAIR_KINDS:
        magnitude, positive = bases[pair_kind]
        for sign, multiplier in (("positive", 1.0), ("negative", -1.0)):
            scenarios.append(
                {
                    "scenario_id": f"{profile_id}_{pair_kind}_{sign}",
                    "profile_id": profile_id,
                    "pair_kind": pair_kind,
                    "sign": sign,
                    "magnitude": magnitude,
                    "delta_u": {
                        key: multiplier * float(value)
                        for key, value in positive.items()
                    },
                }
            )
    return scenarios


def _fresh_rows_to_profiles(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        split = "development" if index < 2 else "evaluation"
        profile_id = f"fresh_{split[:3]}_{'ab'[index] if index < 2 else 'abcd'[index - 2]}"
        profiles.append(
            {
                "profile_id": profile_id,
                "split": split,
                "baseline_m0": [float(value) for value in row["baseline_m0"]],
                "baseline_d0": [float(value) for value in row["baseline_d0"]],
                "steady_loads": {
                    "PQ_Bus14": float(row["load14"]),
                    "PQ_Bus15": float(row["load15"]),
                },
                "probe_magnitude": float(row["probe"]),
                "localized_location": str(row["location"]),
                "localized_magnitude": float(row["localized"]),
            }
        )
    for profile in profiles:
        profile["scenarios"] = _signed_scenarios(profile)
    return profiles


def build_contract(
    rows: Sequence[Mapping[str, Any]] | None = None,
    *,
    seed: int = GENERATOR_SEED,
) -> dict[str, Any]:
    """Return the R481 fresh-profile contract in the R399 shape."""

    from andes_rl_kundur.control.per_vsg_md import local_neighbour_md_candidates

    fresh_rows = build_fresh_rows(seed) if rows is None else [dict(row) for row in rows]
    profiles = _fresh_rows_to_profiles(fresh_rows)
    candidate_ids = [row.name for row in local_neighbour_md_candidates()]
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "manuscript_line": "yang-md-decoupling-marl",
        "fresh_profile_source": (
            "prospectively generated by r481_fresh_profiles.build_fresh_rows "
            f"with seed {seed}; all R399/R401 viewed rows excluded"
        ),
        "steps": 30,
        "dt_seconds": 0.2,
        "seed": 42,
        "physical_nominal_frequency_hz": 60.0,
        "control_nominal_frequency_hz": 50.0,
        "differential_transform": DIFFERENTIAL_TRANSFORM.tolist(),
        "action_bounds": [-1.0, 1.0],
        "action_slew_limit": 0.25,
        "decoder": {
            "delta_m_negative": -200.0,
            "delta_m_positive": 600.0,
            "delta_d_negative": -200.0,
            "delta_d_positive": 600.0,
            "m_lower_clamp": 20.0,
            "d_lower_clamp": 10.0,
            "mapping_atol": 3.0517578125e-05,
        },
        "thresholds": {
            "minimum_joint_improvement": 0.05,
            "maximum_common_harm": 0.03,
            "maximum_action_stress_harm": 0.10,
            "maximum_action_saturation_fraction": 0.05,
            "nonconstant_action_variation_floor": 1.0e-6,
            "independent_action_dispersion_floor": 1.0e-6,
        },
        "profiles": profiles,
        "candidate_arm_ids": candidate_ids,
        "arm_ids": ["zero", *candidate_ids],
        "oracle_role": "non_deployable_outcome_selector_per_evaluation_profile",
        "selection_unit": "heterogeneity_profile",
        "uncertainty": "evaluation_profile_table_plus_leave_one_profile_out_range",
        "reward_used_for_gate": False,
        "training_authorized": False,
    }


def _not_harmed(value: float, reference: float, fraction: float) -> bool:
    return bool(value <= (1.0 + fraction) * reference + 1.0e-15)


def phase1a_gate(
    summaries: Sequence[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any],
    selected_arm: str,
) -> dict[str, Any]:
    """Apply the Phase-1A 4/4 rule to the development-selected winner.

    The winner must be finite and guard-valid on ALL FOUR evaluation
    profiles; one-to-three passing profiles cannot open the gate.  Guard set
    (recommended default O1): valid summary, actuator mapping, no bound/slew
    violation, common no-harm vs zero at 3%, saturation <= 0.05, nonconstant
    variation and per-VSG dispersion floors.  The off-diagonal and
    disturbance-differential ratios to zero are report lines, not gate.
    """

    thresholds = contract["thresholds"]
    maximum_common_harm = float(thresholds["maximum_common_harm"])
    maximum_saturation = float(thresholds["maximum_action_saturation_fraction"])
    variation_floor = float(thresholds["nonconstant_action_variation_floor"])
    dispersion_floor = float(thresholds["independent_action_dispersion_floor"])
    evaluation_ids = [
        str(profile["profile_id"])
        for profile in contract["profiles"]
        if profile["split"] == "evaluation"
    ]
    by_key = {
        (str(row["profile_id"]), str(row["arm_id"])): row for row in summaries
    }
    rows: dict[str, dict[str, Any]] = {}
    per_profile: dict[str, dict[str, Any]] = {}
    reasons: list[str] = []
    for profile_id in evaluation_ids:
        winner_key = (profile_id, selected_arm)
        zero_key = (profile_id, "zero")
        if winner_key not in by_key or zero_key not in by_key:
            rows[profile_id] = {"passed": False, "reason": "missing_rows"}
            reasons.append(f"{profile_id}:missing_rows")
            continue
        winner = by_key[winner_key]
        zero = by_key[zero_key]
        zero_off = float(zero["off_diagonal_response_energy"])
        zero_differential = float(zero["disturbance_differential_energy"])
        if min(zero_off, zero_differential) <= 0.0:
            rows[profile_id] = {"passed": False, "reason": "nonpositive_zero_reference"}
            reasons.append(f"{profile_id}:nonpositive_zero_reference")
            continue
        common_guard = {
            "common_frequency_no_harm": _not_harmed(
                float(winner["common_frequency_iae_hz_s"]),
                float(zero["common_frequency_iae_hz_s"]),
                maximum_common_harm,
            ),
            "worst_peak_no_harm": _not_harmed(
                float(winner["worst_unit_peak_hz"]),
                float(zero["worst_unit_peak_hz"]),
                maximum_common_harm,
            ),
            "rocof_no_harm": _not_harmed(
                float(winner["worst_rocof_hz_s"]),
                float(zero["worst_rocof_hz_s"]),
                maximum_common_harm,
            ),
        }
        guard = {
            "valid": winner.get("valid") is True,
            "actuator_mapping_pass": winner.get("actuator_mapping_pass") is True,
            "action_bound_violation": winner.get("action_bound_violation") is False,
            "action_slew_violation": winner.get("action_slew_violation") is False,
            **common_guard,
            "saturation_budget": float(winner["action_saturation_fraction"])
            <= maximum_saturation,
            "nonconstant_action": float(winner["minimum_record_total_variation"])
            > variation_floor,
            "independent_per_vsg_action": float(
                winner["minimum_record_action_row_dispersion"]
            )
            > dispersion_floor,
        }
        passed = bool(all(guard.values()))
        row = {
            "passed": passed,
            "guard": guard,
            "off_diagonal_ratio_to_zero": float(
                winner["off_diagonal_response_energy"]
            )
            / zero_off,
            "differential_ratio_to_zero": float(
                winner["disturbance_differential_energy"]
            )
            / zero_differential,
        }
        per_profile[profile_id] = row
        rows[profile_id] = row
        if not passed:
            reasons.append(
                f"{profile_id}:"
                + ",".join(name for name, value in guard.items() if not value)
            )
    passed_count = sum(1 for row in rows.values() if row.get("passed") is True)
    gate = {
        "passed_4_of_4": passed_count == 4,
        "passed_count": passed_count,
        "selected_arm": selected_arm,
        "per_profile": per_profile,
        "failed_reasons": sorted(set(reasons)),
        "one_to_three_cannot_open": True,
        "ratios_are_report_lines_not_gate": True,
    }
    return gate


__all__ = [
    "GENERATOR_SEED",
    "ROUND_ID",
    "VIEWED_ROWS",
    "build_contract",
    "build_fresh_rows",
    "phase1a_gate",
]
