"""R381 Gate B-4 contract over the verified R379 analysis machinery.

R381 changes exactly one scientific mechanism: the registered neighbour
message passes through two identical washouts in series.  Physical guards,
coordinate projections, endpoint calculations, and pass/fail thresholds are
reused from R379 so a new implementation cannot silently relax them.
"""

from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping
from typing import Any

from andes_rl_kundur.evaluation.gate_b3_deterministic import (
    LOCAL_ARM,
    SELECTED_ARM,
    ZERO_ARM,
    build_contract as _build_parent_contract,
    classify_summaries,
    controller_spec as _parent_controller_spec,
    phase_jobs,
    probe_request,
    project_modes,
    select_development_candidate,
    summarize_arm_records,
    summarize_phase_records,
)


CANDIDATE_ARM = "distributed_cascaded_hp_damping_ks1_kc0p5_fc0p05_order2"
FILTER_ORDER = 2
CORNER_HZ = 0.05
HIGH_PASS_ALPHA = 0.9391013674242926
SYNC_GAIN_PER_HZ = 1.0
CONSENSUS_GAIN_PER_S = 0.5


def build_contract() -> dict[str, Any]:
    """Return the JSON-safe single-candidate R381 physical contract."""
    contract = deepcopy(_build_parent_contract())
    candidate = {
        "arm_id": CANDIDATE_ARM,
        "sync_gain_per_hz": SYNC_GAIN_PER_HZ,
        "consensus_gain_per_s": CONSENSUS_GAIN_PER_S,
        "highpass_alpha": HIGH_PASS_ALPHA,
        "filter_order": FILTER_ORDER,
        "corner_hz": CORNER_HZ,
    }
    contract.update(
        {
            "round": "R381",
            "highpass_alpha": HIGH_PASS_ALPHA,
            "filter_order": FILTER_ORDER,
            "corner_hz": CORNER_HZ,
            "distributed_candidates": [candidate],
        }
    )
    development_arms = [ZERO_ARM, LOCAL_ARM, CANDIDATE_ARM]
    contract["development"]["arm_ids"] = development_arms
    contract["development"]["record_count"] = 30
    contract["evaluation"]["arm_ids"] = [ZERO_ARM, LOCAL_ARM, SELECTED_ARM]
    contract["evaluation"]["record_count"] = 30
    return contract


def controller_spec(
    arm_id: str,
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve one R381 arm without changing the parent controller registry."""
    frozen = contract or build_contract()
    if arm_id != CANDIDATE_ARM:
        return _parent_controller_spec(arm_id, contract=frozen)
    local = frozen["local_gains"]
    candidate = frozen["distributed_candidates"][0]
    return {
        "architecture": "distributed_cascaded_hp_damping",
        "kp_n_per_hz": float(local["kp_n_per_hz"]),
        "ki_n_per_hz_s": float(local["ki_n_per_hz_s"]),
        "sync_gain_per_hz": float(candidate["sync_gain_per_hz"]),
        "consensus_gain_per_s": float(candidate["consensus_gain_per_s"]),
        "highpass_alpha": float(candidate["highpass_alpha"]),
        "filter_order": int(candidate["filter_order"]),
    }
