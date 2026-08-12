from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r382_bounded_headroom_witness.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_r382", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runner_exposes_only_create_only_lifecycle_commands() -> None:
    runner = _load_runner()
    parser = runner.build_parser()
    subparsers = next(
        action
        for action in parser._actions
        if action.__class__.__name__ == "_SubParsersAction"
    )

    assert set(subparsers.choices) == {"rehearse", "prepare", "execute"}
    assert runner._contract_is_closed(runner.build_contract()) is True
    assert runner._source_paths()["runner"] == RUNNER
    assert "r381_development" in runner._parent_paths()


def test_candidate_jobs_cross_ten_parent_conditions_with_four_candidates() -> None:
    runner = _load_runner()
    baseline = runner._source_baseline_records()
    jobs = runner.candidate_jobs(baseline, contract=runner.build_contract())

    assert len(baseline) == 10
    assert len(jobs) == 40
    assert len({job["candidate_id"] for job in jobs}) == 4
    assert all(job["parent_record"]["arm_id"] == "local_feasibility_native" for job in jobs)
