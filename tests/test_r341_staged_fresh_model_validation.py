from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from andes_rl_kundur.evaluation.model_first_profile_feasibility import (
    require_profile_bank_feasible,
)
from probes.r341_staged_fresh_model_validation import (
    analyse_development_canary,
    analyse_r341_prefix,
)
from scripts import run_r341_staged_fresh_model_validation as r341


def _build_profile(spec: dict[str, object]):
    return r341._r341_profile_contract(
        channel=spec["channel"],
        shape=str(spec["profile_key"]),
        sign=str(spec["sign"]),
    )


def test_contract_freezes_fresh_points_new_shapes_and_staged_outputs() -> None:
    contract = r341.build_contract()

    assert contract["round"] == "R341"
    assert contract["question"] == "Q-0089"
    assert contract["operating_points"] == {
        "FV0": {
            "vsg_m_device": 183.75,
            "vsg_d_device": 91.875,
            "tie_rx_scale": 1.16,
            "initial_soc": 0.435,
        },
        "FV1": {
            "vsg_m_device": 211.25,
            "vsg_d_device": 105.625,
            "tie_rx_scale": 1.4,
            "initial_soc": 0.535,
        },
    }
    assert contract["waveforms"] == {
        "ramp_hold_unit": [0.25, 0.5, 0.75, 1.0, 1.0, 0.75, 0.5, 0.25],
        "separated_pulse_unit": [1.0, 0.5, 0.0, 0.0, 0.0, 0.5, 1.0],
    }
    assert contract["record_count"] == 66
    assert contract["stages"] == ["zero", "sentinel", "local", "second-wave"]


def test_registered_bank_is_feasible_and_uses_channel_capped_amplitudes() -> None:
    specs = r341._record_specs()

    assert len(specs) == 66
    require_profile_bank_feasible(specs, _build_profile)
    amplitudes = {
        str(row["channel"]["device_idx"]): set()
        for row in specs
        if row["channel"] is not None
    }
    for row in specs:
        if row["channel"] is not None:
            amplitudes[str(row["channel"]["device_idx"])].add(
                float(row["amplitude_system_pu"])
            )
    assert amplitudes == {
        "PQ_0": {0.03, 0.07},
        "PQ_1": {0.03, 0.07},
        "PQ_Bus14": {0.03, 0.07},
        "PQ_Bus15": {0.02, 0.04},
    }


def test_stage_schedule_is_complete_disjoint_and_front_loads_sensitive_channels() -> None:
    schedule = r341.staged_bank_schedule()

    assert [row["name"] for row in schedule] == [
        "zero",
        "sentinel",
        "local",
        "second-wave",
    ]
    assert [len(row["record_indices"]) for row in schedule] == [2, 16, 16, 32]
    flattened = [index for row in schedule for index in row["record_indices"]]
    assert sorted(flattened) == list(range(66))
    assert len(set(flattened)) == 66

    specs = {int(row["record_index"]): row for row in r341._record_specs()}
    sentinel = [specs[index] for index in schedule[1]["record_indices"]]
    assert {row["channel"]["device_idx"] for row in sentinel} == {"PQ_0", "PQ_1"}
    assert {row["waveform"] for row in sentinel} == {"ramp_hold_unit"}


def test_source_closure_includes_feasibility_guard_and_r341_probe() -> None:
    sources = r341._source_paths()

    assert sources["r341_runner"].name == "run_r341_staged_fresh_model_validation.py"
    assert sources["r341_probe"].name == "r341_staged_fresh_model_validation.py"
    assert sources["profile_feasibility"].name == "model_first_profile_feasibility.py"


def test_development_canary_is_short_exposed_and_physically_feasible() -> None:
    contract = r341.development_canary_contract()
    specs = r341._development_record_specs()

    assert contract["identity"] == "DEVELOPMENT"
    assert contract["points"] == ["HS0", "HS1"]
    assert contract["total_steps"] == 25
    assert contract["record_count"] == 18
    assert len(specs) == 18
    with r341._development_configuration():
        require_profile_bank_feasible(specs, _build_profile)


def test_prepare_canary_writes_source_closed_create_only_seal(tmp_path: Path) -> None:
    seal_path = tmp_path / "development_seal.json"
    digest = r341.prepare_canary(seal_path, created_utc="2026-08-05T00:00:00+00:00")
    payload = json.loads(seal_path.read_text(encoding="utf-8"))

    assert len(digest) == 64
    assert payload["phase"] == "development-canary"
    assert payload["round"] == "R341"
    assert payload["contract"] == r341.development_canary_contract()
    assert payload["formal_evidence"] is False


def _zero_candidate() -> dict[str, object]:
    realization = {
        "state_matrix": [[0.0]],
        "input_matrix": np.zeros((1, 8)).tolist(),
        "output_matrix": np.zeros((4, 1)).tolist(),
        "feedthrough_matrix": np.zeros((4, 8)).tolist(),
        "retained_singular_values": [1.0],
    }
    return {
        "construction_pass": True,
        "points": {
            point: {
                "construction_pass": True,
                "full_sampled": realization,
                "order12": realization,
            }
            for point in ("HS0", "HS1")
        },
    }


def _zero_canary_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for point in ("HS0", "HS1"):
        records.append(
            {
                "record_index": len(records),
                "operating_point": point,
                "channel": "zero",
                "record_valid": True,
                "output_coordinates": np.zeros((25, 4)).tolist(),
            }
        )
        for channel in ("PQ_0", "PQ_1", "PQ_Bus14", "PQ_Bus15"):
            for sign in ("positive", "negative"):
                records.append(
                    {
                        "record_index": len(records),
                        "operating_point": point,
                        "channel": channel,
                        "record_valid": True,
                        "waveform": "ramp_hold_unit",
                        "amplitude_system_pu": 0.01,
                        "sign": sign,
                        "delta_profile_system_pu": np.zeros(25).tolist(),
                        "output_coordinates": np.zeros((25, 4)).tolist(),
                    }
                )
    return records


def test_canary_analysis_returns_pass_or_first_valid_model_block() -> None:
    records = _zero_canary_records()
    passed = analyse_development_canary(
        candidate_payload=_zero_candidate(), records=records, chain_valid=True
    )
    assert passed["classification"] == "PASS-DEVELOPMENT"

    records[1]["output_coordinates"] = np.ones((25, 4)).tolist()
    blocked = analyse_development_canary(
        candidate_payload=_zero_candidate(), records=records, chain_valid=True
    )
    assert blocked["classification"] == "BLOCK-FULL-LINEARIZATION"


def test_formal_prefix_can_end_early_on_one_valid_failure() -> None:
    candidate = _zero_candidate()
    candidate["points"] = {
        point.replace("HS", "FV"): payload
        for point, payload in candidate["points"].items()
    }
    records = _zero_canary_records()
    for row in records:
        row["operating_point"] = str(row["operating_point"]).replace("HS", "FV")
    expected = [int(row["record_index"]) for row in records]

    passed = analyse_r341_prefix(
        candidate_payload=candidate,
        records=records,
        expected_record_indices=expected,
        stage_name="sentinel",
        chain_valid=True,
    )
    assert passed["classification"] == "PASS-PREFIX"

    records[1]["output_coordinates"] = np.ones((25, 4)).tolist()
    blocked = analyse_r341_prefix(
        candidate_payload=candidate,
        records=records,
        expected_record_indices=expected,
        stage_name="sentinel",
        chain_valid=True,
    )
    assert blocked["classification"] == "BLOCK-FULL-LINEARIZATION"
