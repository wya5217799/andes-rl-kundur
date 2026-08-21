from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parents[1]
AUDIT_PATH = HERE / "code" / "r402_validation_audit.py"
SPEC = importlib.util.spec_from_file_location("r402_validation_audit", AUDIT_PATH)
assert SPEC is not None and SPEC.loader is not None
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)

PACKAGE_ROOT = Path(
    os.environ.get(
        "R402_PACKAGE_ROOT",
        "/mnt/data/r402_validation_work/r402_causal_validation_v1",
    )
)

pytestmark = pytest.mark.skipif(
    not PACKAGE_ROOT.is_dir(),
    reason="set R402_PACKAGE_ROOT to the extracted r402_causal_validation_v1 directory",
)


def test_record_count_and_registered_endpoint_recomputation(tmp_path: Path) -> None:
    contract = audit.read_contract(PACKAGE_ROOT)
    records = audit.discover_records(PACKAGE_ROOT)
    assert len(records) == 240
    assert sum(record.arm_id in audit.LEARNING_ARMS for record in records) == 216
    assert sum(record.arm_id == audit.DETERMINISTIC_ARM for record in records) == 24

    _, endpoints, profile_guards, _ = audit.registered_recomputation(
        PACKAGE_ROOT, records, contract, tmp_path
    )
    diffs = pd.read_csv(tmp_path / "registered_recomputation_diff.csv")
    assert float(diffs["abs_diff"].max()) < 1e-12
    assert endpoints.shape[0] == 10
    assert profile_guards.shape[0] == 36
    assert not profile_guards["common_guard_pass"].any()
    assert not profile_guards["action_stress_guard_pass"].any()


def test_physical_clamps_are_distinct_from_normalized_boundary_saturation(
    tmp_path: Path,
) -> None:
    contract = audit.read_contract(PACKAGE_ROOT)
    records = audit.discover_records(PACKAGE_ROOT)
    run_df, _, trajectory_df = audit.action_diagnostics(records, contract, tmp_path)
    learning = trajectory_df[trajectory_df["arm_id"].isin(audit.LEARNING_ARMS)]
    assert int(learning["any_physical_lower_clamp"].sum()) == 179
    assert int(learning["any_reference_upper_box_excursion"].sum()) == 151
    assert np.allclose(
        run_df[run_df["arm_id"].isin(audit.LEARNING_ARMS)][
            "normalized_boundary_fraction"
        ],
        0.0,
    )


def test_static_audit_finds_interface_defects(tmp_path: Path) -> None:
    findings = audit.static_source_findings(PACKAGE_ROOT, tmp_path)
    ids = set(findings["finding_id"])
    assert {"F1", "F2", "F3", "F4", "F5", "F6", "F8"}.issubset(ids)
    critical = set(findings[findings["severity"] == "CRITICAL"]["finding_id"])
    assert critical == {"F1", "F2"}


def test_copied_source_is_not_dependency_closed(tmp_path: Path) -> None:
    dependencies = audit.source_dependency_gaps(PACKAGE_ROOT, tmp_path)
    missing = set(
        dependencies.loc[
            ~dependencies["resolved_inside_bundle"], "imported_module"
        ]
    )
    assert missing == {
        "andes_rl_kundur.agents.networks",
        "andes_rl_kundur.scenarios.contract",
    }


def test_unidentified_partial_observation_credit_and_shift_are_preserved(
    tmp_path: Path,
) -> None:
    hypotheses = audit.hypothesis_verdicts(tmp_path)
    status = hypotheses.set_index("hypothesis_id")["epistemic_status"].to_dict()
    assert status["H17"] == "PLAUSIBLE-NOT-IDENTIFIED"
    assert status["H18"] == "UNAVAILABLE"
    assert status["H19"] == "PLAUSIBLE-NOT-IDENTIFIED"

    coverage = audit.evidence_coverage_matrix(tmp_path)
    c13 = coverage.set_index("coverage_id").loc["C13"]
    assert c13["status"] == "absent"
