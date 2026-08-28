"""Focused contract tests for the R485 60-Hz source factorial adapter."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r485_60hz_source_factorial.py"
CONFIG = ROOT / "memory/rounds/R485/config.json"


def _load_runner():
    spec = importlib.util.spec_from_file_location("r485_runner_test", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_config_closes_exact_roster_and_fixed_budget() -> None:
    runner = _load_runner()
    config = runner.load_config(CONFIG)

    assert runner.ARM_IDS == tuple(
        f"a{actor.lower()}_c{critic.lower()}_r{reward}"
        for actor in ("N", "P")
        for critic in ("N", "P")
        for reward in (0, 1)
    )
    assert runner.FORMAL_SEEDS == tuple(range(501, 527))
    assert runner.CANARY_SEED == 500
    assert config["training"]["interaction_steps"] == 43_200
    assert config["training"]["adaptive_stop"] is False
    assert config["evaluation"]["steps"] == 150
    assert config["evaluation"]["prefix_steps"] == 30


def test_evaluation_contract_freezes_same_and_fresh_bank_seeds() -> None:
    from andes_rl_kundur.evaluation.r485_experiment import evaluation_contracts

    contracts = evaluation_contracts()

    assert contracts["same"]["environment_seed"] == 401
    assert contracts["fresh"]["environment_seed"] == 42
    assert contracts["same"]["steps"] == contracts["fresh"]["steps"] == 150
    assert {row["environment_seed"] for row in contracts["same"]["profiles"]} == {401}
    assert {row["environment_seed"] for row in contracts["fresh"]["profiles"]} == {42}
    assert {row["bank"] for row in contracts["same"]["profiles"]} == {"same"}
    assert {row["bank"] for row in contracts["fresh"]["profiles"]} == {"fresh"}


def test_runner_overrides_scientific_environment_and_records_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("N_SUBSTEPS", "1")
    monkeypatch.setenv("DISABLE_TOGGLER", "0")

    runner = _load_runner()
    card = runner.build_parameter_card()

    assert runner.os.environ["N_SUBSTEPS"] == "5"
    assert runner.os.environ["DISABLE_TOGGLER"] == "1"
    assert card["scientific_environment"] == {
        "N_SUBSTEPS": "5",
        "DISABLE_TOGGLER": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
    }

    monkeypatch.setenv("N_SUBSTEPS", "1")
    with pytest.raises(RuntimeError, match="scientific environment drift"):
        runner._assert_physical_runtime()


def test_relative_config_path_is_anchored_to_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _load_runner()
    monkeypatch.chdir(tmp_path)

    config = runner.load_config(Path("memory/rounds/R485/config.json"))

    assert config["_path"] == CONFIG.resolve()


def test_canonical_rows_convert_frequency_slots_exactly_once() -> None:
    runner = _load_runner()
    raw = {i: np.arange(7, dtype=np.float32) + i for i in range(4)}
    original = {i: row.copy() for i, row in raw.items()}

    rows = runner.canonical_rows(raw)

    assert rows.shape == (4, 7)
    assert np.array_equal(rows[:, 0], np.asarray([0, 1, 2, 3], dtype=np.float32))
    assert np.allclose(rows[:, 1:], np.stack([original[i][1:] for i in range(4)]) * 1.2)
    assert all(np.array_equal(raw[i], original[i]) for i in range(4))
    assert not np.allclose(runner.canonical_rows({i: rows[i] for i in range(4)}), rows)


def test_reward_uses_canonical_frequency_rows_and_frozen_coefficients() -> None:
    runner = _load_runner()
    rows = np.zeros((4, 7), dtype=np.float32)
    rows[:, 1] = np.asarray([0.12, -0.06, 0.03, -0.09])
    rows[:, 3] = np.asarray([-0.03, 0.06, -0.12, 0.09])
    rows[:, 4] = np.asarray([0.09, -0.12, 0.06, -0.03])
    delta_m = np.asarray([600.0, -200.0, 0.0, 0.0])
    delta_d = np.asarray([100.0, 100.0, -100.0, -100.0])

    rewards, components = runner.step_rewards(
        rows, delta_m, delta_d, reward_access=True, return_components=True
    )

    own = rows[:, 1] * 3.0 / (2.0 * np.pi)
    neighbours = rows[:, 3:5] * 3.0 / (2.0 * np.pi)
    means = (own + neighbours.sum(axis=1)) / 3.0
    expected_rf = -(own - means) ** 2 - ((neighbours - means[:, None]) ** 2).sum(axis=1)
    expected_abs = -(own**2)
    expected_h = -(delta_m.mean() / 600.0) ** 2
    expected_d = -(delta_d.mean() / 600.0) ** 2
    expected = 100.0 * expected_rf + 50.0 * expected_abs + 0.0056 * expected_h + 0.0056 * expected_d

    assert np.allclose(rewards, expected, rtol=1e-6, atol=1e-8)
    assert np.allclose(components["frequency_differential"], expected_rf)
    assert np.allclose(components["frequency_absolute"], expected_abs)
    assert components["fleet_mean_m"] == expected_h
    assert components["fleet_mean_d"] == expected_d


def test_source_routing_changes_only_registered_neighbour_slots() -> None:
    runner = _load_runner()
    current = np.arange(28, dtype=np.float32).reshape(4, 7)
    donor = (100 + np.arange(28, dtype=np.float32)).reshape(4, 7)

    assert np.array_equal(runner.source_rows(current, donor, "N"), current)
    placebo = runner.source_rows(current, donor, "P")
    assert np.array_equal(placebo[:, :3], current[:, :3])
    for actor in range(4):
        assert np.array_equal(placebo[actor, 3:5], donor[actor, 1:3])
        assert np.array_equal(placebo[actor, 5:7], donor[(actor + 2) % 4, 1:3])


def test_direct_md_comparator_matches_independent_raw_and_projection_oracle() -> None:
    from andes_rl_kundur.agents.executed_action_sac import project_action_numpy
    from andes_rl_kundur.control.per_vsg_md import (
        LocalNeighbourMDExecution,
        local_neighbour_md_candidates,
    )

    runner = _load_runner()
    rows = np.asarray(
        [
            [0.0, 0.10, -0.04, -0.03, 0.07, 0.02, -0.06],
            [0.0, -0.08, 0.03, 0.05, -0.02, -0.04, 0.01],
            [0.0, 0.03, 0.09, -0.07, 0.02, 0.05, -0.03],
            [0.0, -0.05, -0.06, 0.04, 0.08, -0.02, 0.07],
        ],
        dtype=np.float32,
    )
    expected_raw = []
    for row in rows:
        own_severity = abs(float(row[1])) + abs(float(row[2]))
        neighbour_severity = np.mean(np.abs(row[3:5]) + np.abs(row[5:7]))
        damping_signal = (
            abs(float(row[1]))
            + np.mean(np.abs(float(row[1]) - row[3:5]))
            + np.mean(np.abs(float(row[2]) - row[5:7]))
        )
        expected_raw.append(
            np.tanh([2.0 * (own_severity - neighbour_severity), 2.0 * damping_signal])
        )
    expected_raw = np.asarray(expected_raw, dtype=np.float32)
    expected_projected = np.stack(
        [project_action_numpy(np.zeros(2), row, slew_limit=0.25) for row in expected_raw]
    )
    contract = next(
        row for row in local_neighbour_md_candidates() if row.name == "local_neighbour_md_km2_kd2"
    )
    controller = LocalNeighbourMDExecution(contract)

    assert np.allclose(runner.direct_md_raw_actions(rows), expected_raw)
    assert np.allclose(
        controller.act({index: rows[index] for index in range(4)}),
        expected_projected,
    )


def test_prefix_is_a_field_exact_view_not_a_second_simulation() -> None:
    from andes_rl_kundur.evaluation.r485_experiment import extract_prefix
    record = {
        "steps": [{"step_index": i, "time": 0.2 * (i + 1), "value": [i, i + 1]} for i in range(150)],
        "completed_steps": 150,
        "completed": True,
    }

    prefix = extract_prefix(record)

    assert prefix["steps"] == record["steps"][:30]
    assert prefix["completed_steps"] == 30
    assert prefix["derived_from_30s_trace"] is True
    assert json.dumps(prefix["steps"], sort_keys=True) == json.dumps(record["steps"][:30], sort_keys=True)


def test_objective_semantics_probe_binds_executed_action_paths() -> None:
    runner = _load_runner()

    result = runner.objective_semantics_probe()

    assert result["passed"] is True
    assert result["replay_actor_rows_are_canonical"] is True
    assert result["replay_critic_rows_are_canonical"] is True
    assert result["current_critic_uses_executed_action"] is True
    assert result["target_critic_uses_projected_action"] is True
    assert result["actor_critic_uses_projected_action"] is True
    assert result["weights_changed"] is True


def test_formal_authority_fails_closed_before_card_canary_review_and_seal() -> None:
    runner = _load_runner()
    config = runner.load_config(CONFIG)

    errors = runner.authority_errors(config, scope="formal")

    assert "resolved_parameter_card" in errors
    assert "canary_admissibility" in errors
    assert "code_review_a" in errors
    assert "code_review_b" in errors
    assert "rehearsal" in errors
    assert "capacity" in errors
    assert "formal_seal" in errors
    with pytest.raises(RuntimeError, match="formal authority failed"):
        runner.require_authority(config, scope="formal")


def test_shard_cli_rejects_identity_outside_registered_roster() -> None:
    runner = _load_runner()

    with pytest.raises(ValueError, match="unregistered R485 shard"):
        runner.main(
            [
                "shard",
                "train|formal|bogus_arm|501",
                "--config",
                str(CONFIG),
            ]
        )


def test_canary_authority_rejects_source_drift_after_parameter_card(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _load_runner()
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    source = tmp_path / "source.py"
    source.write_text("frozen = True\n", encoding="utf-8")
    case = tmp_path / "kundur_full.xlsx"
    case.write_bytes(b"case")
    card = tmp_path / "card.json"
    card.write_text(
        json.dumps(
            {
                "sources": {
                    "source": {"path": "source.py", "sha256": runner._sha256(source)}
                },
                "parents": {
                    "parent": {"path": "source.py", "sha256": runner._sha256(source)}
                },
                "installed_case": {"path": str(case), "sha256": runner._sha256(case)},
            }
        ),
        encoding="utf-8",
    )
    Path(f"{card}.sha256").write_text(
        f"{runner._sha256(card)}  {card.name}\n", encoding="ascii"
    )
    config = {"paths": {"resolved_parameter_card": "card.json"}}

    runner.require_authority(config, scope="canary")
    source.write_text("frozen = False\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="resolved sources drift: source"):
        runner.require_authority(config, scope="canary")


def test_canary_aggregate_rejects_identity_only_trace_shells(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _load_runner()
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "_profiles", lambda bank: [{"profile_id": "p"}])

    def write_hashed(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        Path(f"{path}.sha256").write_text(
            f"{runner._sha256(path)}  {path.name}\n", encoding="ascii"
        )

    source = tmp_path / "source.py"
    source.write_text("frozen = True\n", encoding="utf-8")
    case = tmp_path / "kundur_full.xlsx"
    case.write_bytes(b"case")
    write_hashed(
        tmp_path / "card.json",
        {
            "sources": {
                "source": {"path": "source.py", "sha256": runner._sha256(source)}
            },
            "parents": {
                "parent": {"path": "source.py", "sha256": runner._sha256(source)}
            },
            "installed_case": {"path": str(case), "sha256": runner._sha256(case)},
        },
    )
    card_sha = runner._sha256(tmp_path / "card.json")
    out = tmp_path / "canary-results"
    for arm in runner.ARM_IDS:
        write_hashed(
            out / "train" / arm / "seed500" / "manifest.json",
                {
                    "round": "R485",
                    "scope": "canary",
                    "arm_id": arm,
                    "seed": 500,
                    "resolved_parameter_card_sha256": card_sha,
                    "valid": True,
                "learner_admissibility": {
                    "assessment": {"passed": True, "checks": {"weights_changed": True}}
                },
            },
        )
        write_hashed(
            out / "eval" / "same" / arm / "seed500" / "p.json",
            {"records": [{"arm_id": arm, "training_seed": 500} for _ in range(6)]},
        )
    config = {
        "_canary_out": out,
        "paths": {
            "resolved_parameter_card": "card.json",
            "canary_admissibility": "canary_admissibility.json",
            "canary_out": str(out),
        },
    }

    digest = runner.assess_canary(config)
    payload = json.loads((tmp_path / "canary_admissibility.json").read_text())

    assert digest == runner._sha256(tmp_path / "canary_admissibility.json")
    assert payload["passed"] is False
    assert payload["performance_or_endpoint_selection_performed"] is False
    assert set(payload["arms"]) == set(runner.ARM_IDS)
    assert all("evaluation_schema" in failure for failure in payload["failures"])
