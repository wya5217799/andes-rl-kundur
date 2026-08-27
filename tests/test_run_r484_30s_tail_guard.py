from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts/run_r484_30s_tail_guard.py"
SPEC = importlib.util.spec_from_file_location("r484_runner_tested", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
CONFIG_PATH = ROOT / "memory/rounds/R484/config.json"


def _config() -> dict[str, Any]:
    return RUNNER.load_config(CONFIG_PATH)


def test_config_contract_is_exact_evaluation_only_bank() -> None:
    config = _config()
    contract = RUNNER.build_contract(config)

    assert contract["steps"] == 150
    assert contract["dt_seconds"] == 0.2
    assert contract["training_authorized"] is False
    assert contract["tuning_authorized"] is False
    assert contract["learned_policy_count"] == 208
    assert contract["expected_trajectories"] == 5_088
    assert [row["profile_id"] for row in contract["profiles"]] == [
        *RUNNER.CANARY_PROFILES,
        *RUNNER.FRESH_PROFILES,
    ]
    for key in (
        "decoder",
        "differential_transform",
        "action_bounds",
        "action_slew_limit",
    ):
        assert key in contract


def test_sixteen_shards_are_perfectly_balanced_and_complete() -> None:
    config = _config()
    shards = RUNNER.evaluation_shard_ids(config)
    works = [RUNNER.assigned_work(config, shard_id) for shard_id in shards]

    # The dynamic driver fills all sixteen worker slots before polling.  With
    # exactly sixteen shards, an early shard failure cannot prevent any other
    # registered shard from starting and the driver never kills active jobs.
    assert len(shards) == RUNNER.WORKERS == 16
    assert {row["expected_trajectories"] for row in works} == {318}
    assert {row["expected_blocks"] for row in works} == {53}
    assert all(len(row["learned_cells"]) == 13 for row in works)
    assert all(len(row["comparator_blocks"]) == 1 for row in works)
    assert len({cell for row in works for cell in row["learned_cells"]}) == 208
    assert sum(row["expected_trajectories"] for row in works) == 5_088
    all_ids = set().union(
        *(RUNNER._expected_trajectory_ids(config, shard_id) for shard_id in shards)
    )
    assert len(all_ids) == 5_088
    block_paths = {
        RUNNER._block_path(config, shard_id, spec)
        for shard_id in shards
        for spec in RUNNER._block_specs(config, shard_id)
    }
    assert len(block_paths) == 848


def test_resume_flag_is_after_the_command_and_unambiguous() -> None:
    launch = RUNNER._parser().parse_args(
        ["--config", "memory/rounds/R484/config.json", "launch-eval", "--resume"]
    )
    shard = RUNNER._parser().parse_args(
        [
            "--config",
            "memory/rounds/R484/config.json",
            "shard",
            "eval|00",
            "--resume",
        ]
    )

    assert launch.command == "launch-eval" and launch.resume is True
    assert shard.command == "shard" and shard.shard_id == "eval|00"
    assert shard.resume is True


def test_checkpoint_metadata_is_bound_to_r483_final_arm_and_base() -> None:
    metadata = {
        "round": "R483",
        "stage": "final",
        "arm_id": "an_cn_r0",
        "base_state_sha256": "a" * 64,
    }
    RUNNER._validate_checkpoint_metadata(
        metadata, arm="an_cn_r0", base_state_sha256="a" * 64
    )
    for field, value in (
        ("round", "R482"),
        ("stage", "half"),
        ("arm_id", "ap_cp_r1"),
        ("base_state_sha256", "b" * 64),
    ):
        drifted = {**metadata, field: value}
        with pytest.raises(RuntimeError, match="checkpoint metadata mismatch"):
            RUNNER._validate_checkpoint_metadata(
                drifted, arm="an_cn_r0", base_state_sha256="a" * 64
            )


class _FakeEnvironment:
    N_AGENTS = 4
    OBS_DIM = 7
    FN = 50.0
    andes_nominal_frequency_hz = 60.0

    def __init__(self) -> None:
        self._vsg_pos = [0, 1, 2, 3]
        self.vsg_idx = ["VSG_1", "VSG_2", "VSG_3", "VSG_4"]
        self.ss = SimpleNamespace(
            GENCLS=SimpleNamespace(
                bus=SimpleNamespace(v=[12, 16, 14, 15]),
                M=SimpleNamespace(v=[999.0] * 4),
                D=SimpleNamespace(v=[999.0] * 4),
            )
        )
        self.STEPS_PER_EPISODE = 0
        self._index = 0

    def seed(self, value: int) -> None:
        assert value == 401

    def reset(self, *, delta_u: dict[str, float]) -> dict[int, np.ndarray]:
        assert delta_u
        self._index = 0
        return {index: np.zeros(7, dtype=np.float32) for index in range(4)}

    def _get_vsg_omega(self) -> np.ndarray:
        return np.ones(4)

    def step(self, actions: dict[int, np.ndarray]):
        assert len(actions) == 4
        index = self._index
        self._index += 1
        done = self._index == 150
        info = {
            "time": 0.7 + 0.2 * index,
            "freq_hz_physical": np.full(4, 60.0),
            "M_es": np.full(4, 123.0),
            "D_es": np.full(4, 456.0),
            "delta_M": np.zeros(4),
            "delta_D": np.zeros(4),
            "tds_failed": False,
        }
        observation = {index: np.zeros(7, dtype=np.float32) for index in range(4)}
        return observation, {}, done, info

    def close(self) -> None:
        pass


def test_trajectory_uses_device_base_info_telemetry() -> None:
    environment = _FakeEnvironment()
    r431 = SimpleNamespace(
        _build_env=lambda _profile: environment,
        _joint_obs=lambda _observation: np.zeros(28, dtype=np.float32),
    )
    core = SimpleNamespace(r431=r431)
    runtime = SimpleNamespace(
        base=SimpleNamespace(
            base=SimpleNamespace(base=SimpleNamespace(core=core))
        )
    )
    profile = {
        "bank": "canary",
        "profile_id": "canary_eval_a",
        "environment_seed": 401,
        "baseline_m0": [100.0] * 4,
        "baseline_d0": [100.0] * 4,
    }
    scenario = {
        "scenario_id": "s",
        "pair_kind": "common",
        "sign": "positive",
        "magnitude": 1.0,
        "delta_u": {"PQ_0": 1.0},
    }

    record = RUNNER._run_trajectory(
        runtime,
        profile=profile,
        scenario=scenario,
        policy_id="zero",
    )

    assert record["completed"] is True
    assert environment.STEPS_PER_EPISODE == 150
    assert [
        index for index, row in enumerate(record["steps"]) if row["done"]
    ] == [149]
    assert record["steps"][0]["M_es"] == [123.0] * 4
    assert record["steps"][0]["D_es"] == [456.0] * 4
    assert record["steps"][0]["M_es"] != environment.ss.GENCLS.M.v


def test_nonfinite_and_close_failures_are_json_safe_engineering_records() -> None:
    class BrokenEnvironment(_FakeEnvironment):
        def step(self, actions: dict[int, np.ndarray]):
            observation, reward, done, info = super().step(actions)
            if self._index == 1:
                info["freq_hz_physical"][0] = np.nan
            return observation, reward, done, info

        def close(self) -> None:
            raise RuntimeError("close boom")

    environment = BrokenEnvironment()
    core = SimpleNamespace(
        r431=SimpleNamespace(_build_env=lambda _profile: environment)
    )
    runtime = SimpleNamespace(
        base=SimpleNamespace(base=SimpleNamespace(base=SimpleNamespace(core=core)))
    )
    record = RUNNER._run_trajectory(
        runtime,
        profile={
            "bank": "canary",
            "profile_id": "canary_eval_a",
            "environment_seed": 401,
            "baseline_m0": [100.0] * 4,
            "baseline_d0": [100.0] * 4,
        },
        scenario={
            "scenario_id": "s",
            "pair_kind": "common",
            "sign": "positive",
            "magnitude": 1.0,
            "delta_u": {"PQ_0": 1.0},
        },
        policy_id="zero",
    )

    assert record["completed"] is False
    assert "environment close failed" in record["failure"]
    assert "nonfinite numeric fields" in record["failure"]
    assert record["steps"][0]["freq_hz_physical"][0] is None
    json.dumps(record, allow_nan=False)


def test_failed_routing_gate_and_runtime_drift_block_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config()
    monkeypatch.setattr(
        RUNNER,
        "read_verified_json",
        lambda _path: (
            {
                "round": "R484",
                "passed": False,
                "checks": {"independent_reviews_passed": True},
            },
            "a" * 64,
        ),
    )
    with pytest.raises(RuntimeError, match="routing gate"):
        RUNNER._verified_routing_gate(config)

    monkeypatch.setattr(
        RUNNER,
        "read_verified_json",
        lambda _path: (
            {
                "runtime": {
                    "andes_version": "old",
                    "andes_module": "module",
                    "case_path": "case",
                    "case_sha256": "a" * 64,
                }
            },
            "b" * 64,
        ),
    )
    monkeypatch.setattr(
        RUNNER,
        "_installed_runtime",
        lambda: {
            "andes_version": "new",
            "andes_module": "module",
            "case_path": "case",
            "case_sha256": "a" * 64,
        },
    )
    with pytest.raises(RuntimeError, match="runtime drift"):
        RUNNER._verify_live_runtime(config)


def test_prefix_isolation_ignores_done_and_old_raw_m_d_but_detects_action_drift() -> None:
    current_steps = []
    reference_steps = []
    for index in range(30):
        common = {
            "time": 0.7 + 0.2 * index,
            "freq_hz_physical": [60.0] * 4,
            "action_norm": [[0.1, -0.1]] * 4,
            "delta_M": [1.0] * 4,
            "delta_D": [-1.0] * 4,
        }
        current_steps.append(
            {
                **common,
                "raw_action_norm": [[0.1, -0.1]] * 4,
                "done": False,
                "M_es": [123.0] * 4,
                "D_es": [456.0] * 4,
            }
        )
        reference_steps.append(
            {
                **common,
                "done": index == 29,
                "M_es": [999.0] * 4,
                "D_es": [999.0] * 4,
            }
        )

    passed = RUNNER._compare_prefix_rows(
        {"steps": current_steps}, {"steps": reference_steps}
    )
    assert passed["passed"] is True
    assert passed["done_excluded"] is True
    assert passed["raw_system_base_m_d_excluded"] is True

    current_steps[7]["action_norm"] = [[0.2, -0.1], *([[0.1, -0.1]] * 3)]
    failed = RUNNER._compare_prefix_rows(
        {"steps": current_steps}, {"steps": reference_steps}
    )
    assert failed["integrity_drift"] is True
    assert failed["first_mismatch"] == {"step_index": 7, "field": "action_norm"}


def test_capacity_roster_has_four_learned_cells_and_four_comparators() -> None:
    contract = RUNNER.build_contract(_config())
    selected = (
        (RUNNER.FACTORIAL_ARMS[0], RUNNER.SEEDS[0]),
        (RUNNER.FACTORIAL_ARMS[2], RUNNER.SEEDS[7]),
        (RUNNER.FACTORIAL_ARMS[5], RUNNER.SEEDS[16]),
        (RUNNER.FACTORIAL_ARMS[7], RUNNER.SEEDS[-1]),
    )
    inventory = {
        f"{arm}|{seed}": {
            "manifest_path": "manifest.json",
            "manifest_sha256": "a" * 64,
            "checkpoint_path": "final.pt",
            "checkpoint_sha256": "b" * 64,
            "base_state_sha256": "c" * 64,
        }
        for arm, seed in selected
    }

    jobs = RUNNER._capacity_jobs(contract, inventory)

    assert len(jobs) == 8
    assert sum(job["kind"] == "learned" for job in jobs) == 4
    assert sum(job["kind"] == "comparator" for job in jobs) == 4
    assert len(
        {(job["arm_id"], job["training_seed"]) for job in jobs if job["kind"] == "learned"}
    ) == 4
    assert {
        "_".join(job["arm_id"].split("_")[:2])
        for job in jobs
        if job["kind"] == "learned"
    } == {"an_cn", "an_cp", "ap_cn", "ap_cp"}
    comparator_jobs = [job for job in jobs if job["kind"] == "comparator"]
    assert {job["policy_id"] for job in comparator_jobs} == set(RUNNER.COMPARATORS)
    assert {job["profile"]["bank"] for job in comparator_jobs} == {"canary", "fresh"}


def _patch_aggregate_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    checked: dict[str, Any],
    summary_errors: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    import andes_rl_kundur.evaluation.r484_tail_guard as analysis

    config = _config()
    frozen_contract = RUNNER.build_contract(config)
    captured: dict[str, Any] = {}
    written: dict[str, Any] = {}
    monkeypatch.setattr(RUNNER, "load_seal", lambda _config: {})
    monkeypatch.setattr(
        RUNNER, "check_results", lambda _config, **_kwargs: checked
    )
    monkeypatch.setattr(RUNNER, "_summaries", lambda _config: ([], summary_errors))
    monkeypatch.setattr(RUNNER, "build_contract", lambda _config: frozen_contract)
    monkeypatch.setattr(
        RUNNER,
        "read_verified_json",
        lambda _path: ({"passed": True}, "a" * 64),
    )
    monkeypatch.setattr(RUNNER, "sha256_file", lambda _path: "b" * 64)

    def fake_write(_path: Path, payload: dict[str, Any]) -> str:
        written.update(payload)
        return "c" * 64

    monkeypatch.setattr(RUNNER, "write_new_json", fake_write)
    child = {"classification": "VALID", "scientific_outcome": "VALID"}
    monkeypatch.setattr(analysis, "classify_deterministic_tail", lambda *a, **k: child)
    monkeypatch.setattr(analysis, "analyse_tail_factorial", lambda *a, **k: child)

    def fake_learned(*args: Any, **kwargs: Any) -> dict[str, Any]:
        assert kwargs["deterministic_reference_gate"] is child
        return child

    monkeypatch.setattr(analysis, "classify_learned_guard", fake_learned)

    def fake_classify(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {"classification": "R484-VALID"}

    monkeypatch.setattr(analysis, "classify_r484", fake_classify)
    return captured, written


def test_aggregate_calls_global_classifier_with_complete_success_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shards = [{"shard_id": f"eval|{index:02d}"} for index in range(16)]
    captured, written = _patch_aggregate_dependencies(
        monkeypatch,
        checked={"errors": [], "shards": shards},
        summary_errors=[],
    )

    RUNNER.aggregate(_config())

    assert captured == {
        "design_valid": True,
        "missing_shards": [],
        "engineering_errors": [],
        "integrity_errors": [],
        "learned_guard": {"classification": "VALID", "scientific_outcome": "VALID"},
        "fresh_tail": {"classification": "VALID", "scientific_outcome": "VALID"},
        "canary_tail": {"classification": "VALID", "scientific_outcome": "VALID"},
        "tail_factorial": {"classification": "VALID", "scientific_outcome": "VALID"},
    }
    assert written["classification"] == {"classification": "R484-VALID"}


def test_aggregate_calls_global_classifier_with_error_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shards = [{"shard_id": f"eval|{index:02d}"} for index in range(15)]
    captured, _written = _patch_aggregate_dependencies(
        monkeypatch,
        checked={
            "errors": ["eval|15: missing"],
            "engineering_errors": ["trajectory failed"],
            "integrity_errors": ["prefix drift"],
            "shards": shards,
        },
        summary_errors=["summary invalid"],
    )

    RUNNER.aggregate(_config())

    assert captured["design_valid"] is True
    assert captured["missing_shards"] == ["eval|15"]
    assert captured["engineering_errors"] == ["eval|15: missing", "trajectory failed"]
    assert captured["integrity_errors"] == ["prefix drift"]
    assert captured["learned_guard"] is None
    assert captured["fresh_tail"] is None
    assert captured["canary_tail"] is None
    assert captured["tail_factorial"] is None


def test_formal_manifest_refuses_invalid_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config()
    monkeypatch.setattr(RUNNER, "load_seal", lambda _config: {})
    monkeypatch.setattr(
        RUNNER,
        "check_results",
        lambda _config, **_kwargs: {
            "errors": [],
            "engineering_errors": [],
            "integrity_errors": [],
            "valid_shards": 16,
        },
    )
    monkeypatch.setattr(
        RUNNER,
        "read_verified_json",
        lambda _path: (
            {
                "execution": {"errors": []},
                "summary_errors": ["summary invalid"],
                "classification": {
                    "classification": "INTEGRITY-INVALID",
                    "scientific_results_valid": False,
                },
            },
            "a" * 64,
        ),
    )

    with pytest.raises(RuntimeError, match="cannot finalize invalid"):
        RUNNER.formal_manifest(config)
