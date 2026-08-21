"""Frozen A4 unseen condition banks for the soft-spot program (R413).

Three frozen blocks re-evaluate the R408/R409 constructive candidate (the
0.4 Hz ring-edge bandpass at K=3.5) with the frozen R409 thresholds
(r_d <= 0.95, r_cross <= 1.10, all R379 guards) on new unseen conditions:

- ``a4_conditions_b``: a new probe/disturbance set on the nominal plant;
- ``a4_md_relaxed``: plant perturbation (inertia x0.85, damping x1.15);
- ``a4_md_stiff``: plant perturbation (inertia x1.15, damping x0.85).

Each block runs the three R379 arms (zero_feedback /
local_feasibility_native / bandpass_k3p5) under identical conditions, so
r_d and r_cross are candidate-versus-local ratios on the same block.
The blocks were frozen before execution and are consumed once, create-only.
"""

from __future__ import annotations

from typing import Any

CANDIDATE_ARM = "bandpass_k3p5"
LOCAL_ARM = "local_feasibility_native"
ZERO_ARM = "zero_feedback"
EVAL_ARMS = (ZERO_ARM, LOCAL_ARM, CANDIDATE_ARM)

DIFFERENTIAL_RATIO_MAX = 0.95
PROBE_CROSS_RATIO_MAX = 1.10
STRICT_CROSS_RATIO_MAX = 0.95

NOMINAL_VSG_M0 = 200.0
NOMINAL_D0_PER_AGENT = (100.0, 100.0, 100.0, 100.0)

BLOCKS: tuple[dict[str, Any], ...] = (
    {
        "block_id": "a4_conditions_b",
        "kind": "conditions",
        "vsg_m0": NOMINAL_VSG_M0,
        "d0_per_agent": NOMINAL_D0_PER_AGENT,
        "probe_condition": {
            "condition_id": "a4_probe_b_pq1_minus_0p35",
            "delta_u": {"PQ_1": -0.35},
        },
        "disturbance_conditions": [
            {
                "condition_id": "a4_dist_b_bus14_plus_0p45",
                "delta_u": {"PQ_Bus14": 0.45},
            },
            {
                "condition_id": "a4_dist_b_bus15_minus_0p50",
                "delta_u": {"PQ_Bus15": -0.50},
            },
        ],
    },
    {
        "block_id": "a4_md_relaxed",
        "kind": "md_perturbation",
        "vsg_m0": 170.0,
        "d0_per_agent": (115.0, 115.0, 115.0, 115.0),
        "probe_condition": {
            "condition_id": "a4_probe_md_relaxed_bus15_minus_0p30",
            "delta_u": {"PQ_Bus15": -0.30},
        },
        "disturbance_conditions": [
            {
                "condition_id": "a4_dist_md_relaxed_pq0_plus_0p55",
                "delta_u": {"PQ_0": 0.55},
            },
            {
                "condition_id": "a4_dist_md_relaxed_bus14_minus_0p40",
                "delta_u": {"PQ_Bus14": -0.40},
            },
        ],
    },
    {
        "block_id": "a4_md_stiff",
        "kind": "md_perturbation",
        "vsg_m0": 230.0,
        "d0_per_agent": (85.0, 85.0, 85.0, 85.0),
        "probe_condition": {
            "condition_id": "a4_probe_md_stiff_pq0_minus_0p45",
            "delta_u": {"PQ_0": -0.45},
        },
        "disturbance_conditions": [
            {
                "condition_id": "a4_dist_md_stiff_pq1_minus_0p60",
                "delta_u": {"PQ_1": -0.60},
            },
            {
                "condition_id": "a4_dist_md_stiff_bus15_plus_0p50",
                "delta_u": {"PQ_Bus15": 0.50},
            },
        ],
    },
)


def block_ids() -> list[str]:
    return [str(block["block_id"]) for block in BLOCKS]


def block_by_id(block_id: str) -> dict[str, Any]:
    for block in BLOCKS:
        if str(block["block_id"]) == block_id:
            return block
    raise ValueError(f"unknown block: {block_id}")
