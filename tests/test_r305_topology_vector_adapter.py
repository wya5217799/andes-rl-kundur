from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_r305_topology_vector_gate.py"


def _load_adapter():
    spec = importlib.util.spec_from_file_location("run_r305_topology_vector_gate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakePFlow:
    def __init__(self, converged: bool) -> None:
        self.converged = converged

    @staticmethod
    def run() -> np.ndarray:
        return np.asarray([1.0, 2.0])


class _FakeSystem:
    def __init__(self, converged: bool) -> None:
        self.PFlow = _FakePFlow(converged)


def test_r305_pflow_uses_authoritative_scalar_state_not_array_return() -> None:
    adapter = _load_adapter()

    passed, summary = adapter._run_pflow(_FakeSystem(True))
    failed, failed_summary = adapter._run_pflow(_FakeSystem(False))

    assert passed is True
    assert failed is False
    assert summary == failed_summary == {"python_type": "ndarray", "shape": [2]}


def test_r305_opaque_return_helpers_are_scalar_only_and_fail_closed() -> None:
    adapter = _load_adapter()

    assert adapter._scalar_truth(np.bool_(True)) is True
    assert adapter._scalar_truth(np.asarray([True, True])) is False
    assert adapter._return_explicitly_failed(np.bool_(False)) is True
    assert adapter._return_explicitly_failed(np.asarray([False, False])) is False


def test_r305_canary_is_not_repeated_in_parallel_matrix_shards() -> None:
    adapter = _load_adapter()

    assignments = [
        pair
        for shard_index in range(adapter.SHARD_COUNT)
        for pair in adapter._assigned_cells(shard_index, adapter.SHARD_COUNT)
    ]

    assert adapter.CANARY_CELL == ("nominal", "q0")
    assert adapter.CANARY_CELL not in assignments
    assert len(assignments) == len(set(assignments)) == 20


def _valid_canary_cell(adapter):
    return {
        "round": adapter.ROUND_ID,
        "question": adapter.QUESTION_ID,
        "topology": "nominal",
        "opened_line": "none",
        "action": "q0",
        "m_vector": list(adapter.gate.ACTION_LIBRARY["q0"]),
        "guards": {guard: True for guard in adapter.gate.REQUIRED_CELL_GUARDS},
        "identified": {
            "freq_hz": 0.7,
            "damping_ratio": 0.1,
            "p_vector": [0.4, 0.3, 0.2, 0.1],
            "p_keys": ["g1", "g2", "g3", "g4"],
        },
        "execution_runtime": {"python": "test", "platform": "test", "andes": "test"},
    }


def test_r305_canary_validator_requires_exact_identity_action_and_guards() -> None:
    adapter = _load_adapter()
    valid = _valid_canary_cell(adapter)

    assert adapter._canary_cell_failures(valid) == []

    wrong_identity = {**valid, "topology": "line_0_out"}
    assert "topology" in adapter._canary_cell_failures(wrong_identity)

    wrong_action = {**valid, "m_vector": [351.0, 349.0, 350.0, 350.0]}
    assert "m_vector" in adapter._canary_cell_failures(wrong_action)

    missing_guard = {
        **valid,
        "guards": {
            key: value
            for key, value in valid["guards"].items()
            if key != "eig_run_pass"
        },
    }
    failures = adapter._canary_cell_failures(missing_guard)
    assert "guard_keys" in failures
    assert "guards_pass" in failures


@pytest.mark.parametrize(
    ("identified", "expected_failure"),
    [
        ({}, "identified_malformed"),
        (
            {
                "freq_hz": float("nan"),
                "damping_ratio": 0.1,
                "p_vector": [0.4],
                "p_keys": ["g1"],
            },
            "identified_frequency",
        ),
        (
            {
                "freq_hz": 1.6,
                "damping_ratio": 0.1,
                "p_vector": [0.4],
                "p_keys": ["g1"],
            },
            "identified_frequency",
        ),
        (
            {
                "freq_hz": 0.7,
                "damping_ratio": -0.1,
                "p_vector": [0.4],
                "p_keys": ["g1"],
            },
            "identified_damping",
        ),
        (
            {
                "freq_hz": 0.7,
                "damping_ratio": 0.1,
                "p_vector": [float("inf")],
                "p_keys": ["g1"],
            },
            "identified_p_vector",
        ),
        (
            {
                "freq_hz": 0.7,
                "damping_ratio": 0.1,
                "p_vector": [0.4, 0.3],
                "p_keys": ["g1"],
            },
            "identified_p_keys",
        ),
        (
            {
                "freq_hz": 0.7,
                "damping_ratio": 0.1,
                "p_vector": "12",
                "p_keys": ["g1", "g2"],
            },
            "identified_malformed",
        ),
        (
            {
                "freq_hz": 0.7,
                "damping_ratio": 0.1,
                "p_vector": [1.0, 2.0],
                "p_keys": "12",
            },
            "identified_malformed",
        ),
    ],
)
def test_r305_canary_rejects_malformed_identified_mode(
    identified: dict[str, object],
    expected_failure: str,
) -> None:
    adapter = _load_adapter()
    cell = {**_valid_canary_cell(adapter), "identified": identified}

    assert expected_failure in adapter._canary_cell_failures(cell)


@pytest.mark.parametrize(
    "runtime",
    [
        {},
        {"python": "test", "platform": "test"},
        {"python": "test", "platform": "test", "andes": "test", "extra": "x"},
        {"python": "test", "platform": "test", "andes": 1},
        {"python": "", "platform": "test", "andes": "test"},
    ],
)
def test_r305_canary_requires_exact_execution_runtime(runtime: object) -> None:
    adapter = _load_adapter()
    cell = {**_valid_canary_cell(adapter), "execution_runtime": runtime}

    assert "execution_runtime" in adapter._canary_cell_failures(cell)


def test_r305_failed_canary_has_canonical_invalid_decision() -> None:
    adapter = _load_adapter()
    failed = _valid_canary_cell(adapter)
    failed["guards"] = {guard: False for guard in adapter.gate.REQUIRED_CELL_GUARDS}
    failed["identified"] = None

    decision = adapter._canary_decision(failed)

    assert decision["classification"] == "INVALID-CANARY"
    assert decision["matrix_expansion_authorized"] is False
    assert decision["training_gate"] == {
        "authorized": False,
        "training_executed": False,
        "next_step": "STOP",
    }


def test_r305_writer_is_create_only_and_hash_checked(tmp_path: Path) -> None:
    adapter = _load_adapter()
    path = tmp_path / "artifact.json"

    digest = adapter._write_new_json(path, {"round": adapter.ROUND_ID})

    assert digest == adapter._sha256_file(path)
    with pytest.raises(FileExistsError, match="already exists"):
        adapter._write_new_json(path, {"round": adapter.ROUND_ID})

    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(RuntimeError, match="sidecar mismatch"):
        adapter._read_verified_json(path)


def test_r305_missing_canary_refuses_matrix_expansion(tmp_path: Path) -> None:
    adapter = _load_adapter()

    with pytest.raises(FileNotFoundError, match="artifact or sidecar missing"):
        adapter._verify_canary(tmp_path, "a" * 64, "b" * 64)


def test_r305_parser_freezes_canary_before_matrix_commands() -> None:
    adapter = _load_adapter()
    parser = adapter.build_parser()

    for command in ("prepare", "run-canary", "run-shard", "eval-check", "analyse"):
        parsed = parser.parse_args(
            [command]
            if command == "prepare"
            else [command, "--expected-seal-sha256", "0" * 64]
            + (
                ["--shard-index", "0", "--shard-count", "3"]
                if command == "run-shard"
                else []
            )
        )
        assert parsed.command == command
