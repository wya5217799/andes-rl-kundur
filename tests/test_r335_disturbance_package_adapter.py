from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.run_r335_disturbance_package import (
    POINTS,
    ROOT,
    _baseline_snapshot_guard,
    _manifest_entries_match,
    _record_specs,
    build_contract,
    prepare,
)


def test_contract_freezes_four_channels_two_waveforms_and_split() -> None:
    contract = build_contract()

    assert contract["round"] == "R335"
    assert contract["question"] == "Q-0086"
    assert contract["development_point"] == "HS0"
    assert contract["holdout_point"] == "HS1"
    assert contract["record_count"] == 34
    assert contract["parallel_workers_per_split"] == 4
    assert contract["development_fit_holdout_order_remains_serial"] is True
    assert [row["device_idx"] for row in contract["channels"]] == [
        "PQ_0",
        "PQ_1",
        "PQ_Bus14",
        "PQ_Bus15",
    ]
    assert contract["shapes"] == {
        "impulse": [0.05],
        "triangle": [0.02, 0.04, 0.05, 0.04, 0.02],
    }
    assert contract["controller_executed"] is False
    assert contract["distributed_runtime_executed"] is False
    assert contract["training_executed"] is False
    assert contract["eval_executed"] is False
    assert contract["title_changed"] is False

    specs = _record_specs(POINTS[0], seal_digest="seal", model_digest="model")
    assert len(specs) == 17
    assert specs[0]["channel"] is None
    assert [spec["channel"]["device_idx"] for spec in specs[1:5]] == [
        "PQ_0",
        "PQ_0",
        "PQ_0",
        "PQ_0",
    ]


def test_prepare_is_create_only_and_seals_every_source_file(tmp_path: Path) -> None:
    seal_path = tmp_path / "seal.json"
    digest = prepare(seal_path, created_utc="2026-08-04T00:00:00+00:00")
    payload = json.loads(seal_path.read_text(encoding="utf-8"))

    assert len(digest) == 64
    sealed_paths = {row["path"] for row in payload["sources"].values()}
    expected_src = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "src").rglob("*.py")
    }
    assert expected_src <= sealed_paths
    with pytest.raises(FileExistsError):
        prepare(seal_path, created_utc="2026-08-04T00:00:01+00:00")


def test_manifest_guard_rejects_duplicate_or_wrong_hash() -> None:
    expected = {"a.json": "a" * 64, "b.json": "b" * 64}
    assert _manifest_entries_match(
        {
            "entries": [
                {"path": "a.json", "sha256": "a" * 64},
                {"path": "b.json", "sha256": "b" * 64},
            ]
        },
        expected,
    )
    assert not _manifest_entries_match(
        {
            "entries": [
                {"path": "a.json", "sha256": "a" * 64},
                {"path": "a.json", "sha256": "b" * 64},
            ]
        },
        expected,
    )


def test_baseline_guard_rejects_an_active_replacement() -> None:
    snapshots = {}
    for device, bus, active, reactive in (
        ("PQ_0", 7, 11.59, -0.735),
        ("PQ_1", 8, 15.75, -0.899),
        ("PQ_Bus14", 14, 2.48, 0.0),
        ("PQ_Bus15", 15, 0.05, 0.0),
    ):
        snapshots[device] = {
            "device_idx": device,
            "bus_idx": bus,
            "raw_active": True,
            "effective_active": True,
            "active": True,
            "Ppf_system_pu": active,
            "Qpf_system_pu": reactive,
            "pq2z_config": 0,
            "vcmp_enable": 0,
            "constant_power_weights": {
                "p2p": 1.0,
                "p2i": 0.0,
                "p2z": 0.0,
                "q2q": 1.0,
                "q2i": 0.0,
                "q2z": 0.0,
            },
            "replacement_records": {"FLoad": [], "ZIP": []},
            "active_fload_replacements_for_device": 0,
            "active_zip_replacements_for_device": 0,
        }

    assert _baseline_snapshot_guard(snapshots, tolerance=1.0e-12)
    snapshots["PQ_0"]["replacement_records"]["FLoad"] = [{"raw_active": True}]
    assert not _baseline_snapshot_guard(snapshots, tolerance=1.0e-12)
