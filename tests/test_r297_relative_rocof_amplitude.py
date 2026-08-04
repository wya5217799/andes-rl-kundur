from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r297_relative_rocof_amplitude.py"
SPEC = importlib.util.spec_from_file_location("r297_probe", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
r297 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r297)


def test_final_revision_has_exactly_two_arms_and_eight_jobs() -> None:
    assert r297.FULL_GAIN == pytest.approx(0.24424071249620006)
    assert [arm["target_static_sync_fraction"] for arm in r297.arm_bank()] == [0.0, 1.0]
    assert len(r297.job_bank()) == 8


def test_formal_return_bank_is_disjoint_and_predeclared() -> None:
    bank = r297.formal_return_bank()
    assert len(bank) == 12
    assert {row["tie_k"] for row in bank} == {1.25, 1.75}
    assert {row["location"] for row in bank} == {"PQ_0", "PQ_1", "PQ_Bus15"}
    assert {row["delta_u"] for row in bank} == {-1.0, 1.0}
    assert {row["name"] for row in bank}.isdisjoint(
        {row["name"] for row in r297.scenario_bank()}
    )


def test_seal_freezes_final_revision_and_return_bank() -> None:
    seal = r297._seal_payload()
    assert seal["final_gain_revision"] is True
    assert seal["development_only"] is True
    assert len(seal["predeclared_formal_return_bank"]) == 12
