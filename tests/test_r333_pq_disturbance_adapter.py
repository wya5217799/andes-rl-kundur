from __future__ import annotations

import json

import numpy as np
import pytest
import scripts.run_r333_pq_disturbance_identification as r333


def test_contract_freezes_small_bank_events_thresholds_and_scope() -> None:
    contract = r333.build_contract()

    assert contract["round"] == "R333"
    assert contract["question"] == "Q-0085"
    assert contract["operating_points"] == ["HS0", "HS1"]
    assert contract["signs"] == ["zero", "positive", "negative"]
    assert contract["record_count"] == 6
    assert contract["device_idx"] == "PQ_Bus14"
    assert contract["bus_idx"] == 14
    assert contract["controlled_bus_order"] == [12, 16, 14, 15]
    assert contract["nominal_tie_lines"]["Line_4"] == {"r": 0.02201, "x": 0.22001}
    assert contract["amplitude_system_pu"] == 0.05
    assert contract["active_steps"] == 5
    assert contract["steps"] == 25
    assert contract["event_times_seconds"] == {"apply": 0.5, "restore": 1.5}
    assert contract["event_row_semantics"] == "exact-event row is pre-event"
    assert contract["node_disturbance_map"] == [0.0, 0.0, -1.0, 0.0]
    assert contract["physical_execution_planned"] is True
    assert contract["physical_execution_performed"] is False
    assert contract["controller_executed"] is False
    assert contract["distributed_runtime_executed"] is False
    assert contract["training_executed"] is False
    assert contract["eval_executed"] is False
    assert contract["allow_is_reachable"] is False


def test_node_load_map_is_reconstructed_exactly_in_frozen_input_coordinates() -> None:
    sequence = r333._coordinate_input_sequence(delta_load_system_pu=0.05)
    basis = r333._frozen_node_input_basis()
    reconstructed = (basis @ sequence.T).T
    expected = np.zeros((25, 4), dtype=float)
    expected[:5, 2] = -0.05

    np.testing.assert_allclose(reconstructed, expected, rtol=0.0, atol=1e-15)


def test_event_grid_guard_requires_exact_row_then_next_critical_point() -> None:
    valid = np.asarray(
        [0.4999, 0.5, 0.5001, 1.4999, 1.4999999999999998, 1.5, 1.5001]
    )
    missing_next = np.asarray([0.4999, 0.5, 1.4999, 1.5])
    missing_exact = np.asarray(
        [0.4999, 0.5, 0.5001, 1.4999, 1.4999999999999998, 1.5001]
    )
    disordered = np.asarray([0.5, 0.4999, 0.5001, 1.4999, 1.5, 1.5001])

    assert r333._event_grid_guard(valid)["pass"] is True
    assert r333._event_grid_guard(missing_next)["pass"] is False
    assert r333._event_grid_guard(missing_exact)["pass"] is False
    assert r333._event_grid_guard(disordered)["pass"] is False


def test_prepare_is_create_only_and_pins_official_and_installed_sources(tmp_path) -> None:
    seal_path = tmp_path / "seal.json"

    digest = r333.prepare(seal_path, created_utc="2026-08-04T00:00:00+00:00")
    seal = json.loads(seal_path.read_text(encoding="utf-8"))

    assert len(digest) == 64
    assert seal["contract"] == r333.build_contract()
    assert seal["installed_andes"]["version"] == "2.0.0"
    assert len(seal["installed_andes"]["sources"]) == 10
    assert all("v2.0.0" in url for url in seal["official_sources"])
    assert seal["contract_payload_sha256"] == r333._payload_sha256(seal["contract"])
    with pytest.raises(FileExistsError):
        r333.prepare(seal_path, created_utc="2026-08-04T00:00:00+00:00")


def test_formal_attempt_reserves_the_whole_output_before_execution(tmp_path) -> None:
    out_dir = tmp_path / "formal"

    digest = r333._reserve_formal_attempt(
        out_dir,
        seal_digest="1" * 64,
        created_utc="2026-08-04T00:00:00+00:00",
    )
    payload = json.loads((out_dir / "formal_attempt.json").read_text(encoding="utf-8"))

    assert len(digest) == 64
    assert payload["physical_execution_started"] is True
    assert payload["retry_authorized"] is False
    with pytest.raises(FileExistsError):
        r333._reserve_formal_attempt(out_dir, seal_digest="1" * 64)


def test_manifest_inventory_rejects_extra_duplicate_or_wrong_path() -> None:
    out_dir = r333.DEFAULT_OUT
    valid = {
        "records": [
            {
                "name": name,
                "path": r333._path_text(out_dir / filename),
                "sha256": str(index) * 64,
            }
            for index, (name, filename) in enumerate(
                (
                    ("formal_attempt", "formal_attempt.json"),
                    ("execution", "execution.json"),
                    ("provenance", "provenance.json"),
                ),
                start=1,
            )
        ]
    }

    assert set(r333._validated_manifest_entries(valid, out_dir)) == {
        "formal_attempt",
        "execution",
        "provenance",
    }
    for mutate in (
        lambda rows: rows.append("extra"),
        lambda rows: rows.__setitem__(2, dict(rows[1])),
        lambda rows: rows[0].update(path="wrong.json"),
    ):
        payload = json.loads(json.dumps(valid))
        mutate(payload["records"])
        with pytest.raises(RuntimeError):
            r333._validated_manifest_entries(payload, out_dir)


def test_event_receipts_use_absolute_alter_semantics() -> None:
    contract = r333.TimedPQDisturbanceContract(
        device_idx="PQ_Bus14",
        bus_idx=14,
        initial_active_system_pu=2.48,
        initial_reactive_system_pu=0.0,
        delta_active_system_pu=-0.05,
    )
    snapshots = {
        "pre": {"Ppf_system_pu": 2.48, "Qpf_system_pu": 0.0, "dae_time_seconds": 0.0},
        "apply": {"Ppf_system_pu": 2.43, "Qpf_system_pu": 0.0, "dae_time_seconds": 0.5},
        "restore": {"Ppf_system_pu": 2.48, "Qpf_system_pu": 0.0, "dae_time_seconds": 1.5},
    }
    apply, apply_q, restore, restore_q = r333._event_receipts(
        contract=contract,
        pre_event_snapshot=snapshots["pre"],
        post_apply_snapshot=snapshots["apply"],
        pre_restore_snapshot={
            "Ppf_system_pu": 2.43,
            "Qpf_system_pu": 0.0,
            "dae_time_seconds": 1.5,
        },
        post_restore_snapshot=snapshots["restore"],
    )

    assert apply["mechanism"] == "Alter"
    assert apply["method"] == "="
    assert apply["scheduled_event_time_seconds"] == 0.5
    assert apply["observation_time_seconds"] == 0.5
    assert apply["before_system_pu"] == 2.48
    assert apply["target_system_pu"] == 2.43
    assert apply["readback_system_pu"] == 2.43
    assert apply_q["parameter"] == "Qpf"
    assert apply_q["readback_system_pu"] == 0.0
    assert restore["scheduled_event_time_seconds"] == 1.5
    assert restore["observation_time_seconds"] == 1.5
    assert restore["target_system_pu"] == 2.48
    assert restore_q["parameter"] == "Qpf"
