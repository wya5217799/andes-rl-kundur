from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_r306_model_first_stage0.py"


def _load_adapter():
    spec = importlib.util.spec_from_file_location("run_r306_model_first_stage0", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _valid_report(adapter):
    internal = {
        name: [0.0, 0.0, 0.0, 0.0]
        for name in adapter.REQUIRED_ESD1_INTERNAL_FIELDS
    }
    for name in ("Ipmax", "Fvl", "Fvh", "Ffl", "Ffh", "v"):
        internal[name] = [1.0, 1.0, 1.0, 1.0]
    internal["Ipmin"] = [-1.0, -1.0, -1.0, -1.0]
    return {
        "schema_version": 1,
        "round": adapter.ROUND_ID,
        "question": adapter.QUESTION_ID,
        "seal_sha256": "a" * 64,
        "initial_time": 0.5,
        "structural": {
            "node_device_rows": [
                [0, "VSG_1", "R272_BESS_1", 12, 7, 1],
                [1, "VSG_2", "R272_BESS_2", 16, 8, 1],
                [2, "VSG_3", "R272_BESS_3", 14, 10, 2],
                [3, "VSG_4", "R272_BESS_4", 15, 9, 2],
            ],
            "communication_edges": [[0, 1], [0, 3], [1, 2], [2, 3]],
            "action_edges": [[0, 1], [1, 2], [2, 3]],
            "action_incidence": [
                [1.0, 0.0, 0.0],
                [-1.0, 1.0, 0.0],
                [0.0, -1.0, 1.0],
                [0.0, 0.0, -1.0],
            ],
            "action_rank": 3,
            "disturbance_graph": {"kind": "none", "edited_devices": []},
        },
        "samples": [
            {
                "time": 0.7 + 0.2 * index,
                "pflow_converged": True,
                "tds_failed": False,
                "system_exit_code": 0,
                "finite_state_algebraic": True,
                "andes_nominal_frequency_hz": 60.0,
                "dae_residual_max": 1e-12,
                "vsg_m_actual_system": [400.0] * 4,
                "vsg_d_actual_system": [200.0] * 4,
                "md_write_count": 0,
                "bess_requested_power_system_pu": [0.0] * 4,
                "bess_commanded_power_system_pu": [0.0] * 4,
                "bess_external_command_readback_system_pu": [0.0] * 4,
                "bess_internal_power_reference_system_pu": [0.0] * 4,
                "bess_actual_power_system_pu": [0.0] * 4,
                "bess_soc": [0.5] * 4,
                "bess_internal": deepcopy(internal),
                "line_8_in_service": True,
                "g4_in_service": True,
                "g4_m_actual_system": 13.0,
            }
            for index in range(5)
        ],
    }


def test_r306_valid_stage0_report_passes_only_implementation_gate() -> None:
    adapter = _load_adapter()

    result = adapter.evaluate_stage0_report(_valid_report(adapter))

    assert result["classification"] == "STAGE0-PASS"
    assert result["stage1_authorized"] is False
    assert result["training_authorized"] is False
    assert result["claim_ceiling"] == "implementation-validity-only"
    assert set(result["guards"]) == set(adapter.REQUIRED_STAGE0_GUARDS)
    assert all(result["guards"].values())


@pytest.mark.parametrize(
    ("mutate", "failed_guard"),
    [
        (lambda report: report["samples"][2].update(time=1.10000001), "time_increment"),
        (
            lambda report: report["samples"][0].update(
                vsg_m_actual_system=[200.0] * 4
            ),
            "md_readback",
        ),
        (
            lambda report: report["samples"][0]["bess_internal"].pop("Ipcmd_y"),
            "esd1_internal_telemetry",
        ),
        (
            lambda report: report["samples"][4].update(line_8_in_service=False),
            "line_8_in_service",
        ),
        (
            lambda report: report["structural"].update(action_rank=2),
            "graph_and_index_identity",
        ),
    ],
)
def test_r306_stage0_fails_closed_by_guard_family(mutate, failed_guard: str) -> None:
    adapter = _load_adapter()
    report = _valid_report(adapter)
    mutate(report)

    result = adapter.evaluate_stage0_report(report)

    assert result["classification"] == "INVALID-STAGE0"
    assert result["guards"][failed_guard] is False
    assert result["stage1_authorized"] is False
    assert result["training_authorized"] is False


def test_r306_writer_is_create_only_and_hash_checked(tmp_path: Path) -> None:
    adapter = _load_adapter()
    path = tmp_path / "stage0.json"

    digest = adapter._write_new_json(path, {"round": adapter.ROUND_ID})

    assert digest == adapter._sha256_file(path)
    with pytest.raises(FileExistsError, match="already exists"):
        adapter._write_new_json(path, {"round": adapter.ROUND_ID})
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(RuntimeError, match="sidecar mismatch"):
        adapter._read_verified_json(path)


def test_r306_parser_exposes_only_prepare_run_and_analyse() -> None:
    adapter = _load_adapter()
    parser = adapter.build_parser()

    assert parser.parse_args(["prepare"]).command == "prepare"
    assert parser.parse_args(
        ["run", "--expected-seal-sha256", "0" * 64]
    ).command == "run"
    assert parser.parse_args(
        ["analyse", "--expected-seal-sha256", "0" * 64]
    ).command == "analyse"
    with pytest.raises(SystemExit):
        parser.parse_args(["run-shard"])


def test_r306_contract_uses_exact_numeric_limits() -> None:
    adapter = _load_adapter()

    assert adapter.STAGE0_LIMITS == {
        "time_increment_seconds": 0.2,
        "time_tolerance_seconds": 1e-9,
        "dae_residual_max": 1e-8,
        "md_tolerance": 1e-10,
        "power_zero_tolerance": 1e-8,
        "soc_drift_max": 1e-8,
    }
    np.testing.assert_array_equal(adapter.EXPECTED_M_SYSTEM, np.full(4, 400.0))
    np.testing.assert_array_equal(adapter.EXPECTED_D_SYSTEM, np.full(4, 200.0))
