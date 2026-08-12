from __future__ import annotations

import io

from scripts.run_r367_deterministic_headroom import build_contract as parent_contract
from scripts.run_r368_deterministic_headroom import (
    ROUND_ID,
    build_successor_contract,
    safe_emit,
)


class _BrokenStream(io.StringIO):
    def write(self, value: str) -> int:
        raise BrokenPipeError(32, "broken pipe")


def test_safe_emit_cannot_turn_a_closed_output_pipe_into_run_failure() -> None:
    assert safe_emit("healthy", stream=io.StringIO()) is True
    assert safe_emit("detached", stream=_BrokenStream()) is False


def test_successor_changes_identity_but_not_the_scientific_contract() -> None:
    successor = build_successor_contract()

    assert ROUND_ID == "R368"
    assert successor == parent_contract()
    assert successor["round"] == "R367"
    assert successor["question"] == "Q-0103"
    assert successor["training_authorized"] is False
