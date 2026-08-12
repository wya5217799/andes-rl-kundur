from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from probes.r369_actuator_mapping_reanalysis import (
    binary32_half_ulp_bound,
    build_corrected_contract,
    contract_diff_paths,
    validate_parent_headers,
)
from andes_rl_kundur.evaluation.deterministic_headroom import build_contract


def test_binary32_mapping_bound_is_derived_from_decoder_full_scale() -> None:
    bound = binary32_half_ulp_bound(600.0)

    assert bound == 2.0**-15
    assert bound == float(np.spacing(np.float32(600.0)) / np.float32(2.0))
    assert binary32_half_ulp_bound(200.0) < bound


def test_corrected_contract_changes_only_the_mapping_absolute_tolerance() -> None:
    parent = build_contract()
    corrected = build_corrected_contract(parent)

    assert contract_diff_paths(parent, corrected) == ["/decoder/mapping_atol"]
    assert corrected["decoder"]["mapping_atol"] == 2.0**-15
    restored = deepcopy(corrected)
    restored["decoder"]["mapping_atol"] = parent["decoder"]["mapping_atol"]
    assert restored == parent


def test_parent_header_gate_requires_the_registered_invalid_complete_bank() -> None:
    parent_analysis = {
        "classification": "ANALYSIS-INVALID",
        "checks": {
            "complete_bank": True,
            "all_rows_valid": False,
            "reward_unused": True,
            "training_forbidden": True,
        },
        "summaries": [{}] * 80,
        "training_authorized": False,
    }
    execution = {
        "record_count": 80,
        "records": [
            {"completed": True, "tds_failed": False, "training_executed": False}
            for _ in range(80)
        ],
        "training_executed": False,
    }

    validate_parent_headers(parent_analysis, execution)

    invalid = deepcopy(execution)
    invalid["records"][0]["completed"] = False
    with pytest.raises(ValueError, match="complete"):
        validate_parent_headers(parent_analysis, invalid)
