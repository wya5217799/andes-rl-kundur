"""Offline tests for workflow A/B session measurement."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.workflow_ab.measure_sessions import (
    comparisons,
    scan_codex_file,
)


def _write_jsonl(path: Path, events: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )


def test_codex_turn_extracts_tokens_tools_and_correctness(tmp_path: Path) -> None:
    path = tmp_path / "codex.jsonl"
    turn = "turn-1"
    _write_jsonl(path, [
        {"type": "session_meta", "payload": {"id": "codex-1"}},
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": turn}},
        {"type": "turn_context", "payload": {"turn_id": turn, "model": "gpt-test"}},
        {"type": "response_item", "payload": {
            "type": "message", "role": "user",
            "content": [{"type": "input_text", "text":
                         "[WF-BENCH task=status variant=baseline replicate=1] check"}],
            "internal_chat_message_metadata_passthrough": {"turn_id": turn},
        }},
        {"type": "response_item", "payload": {
            "type": "custom_tool_call", "call_id": "call-1",
            "input": "python memory/tools/session_context.py --json",
            "internal_chat_message_metadata_passthrough": {"turn_id": turn},
        }},
        {"type": "event_msg", "payload": {"type": "token_count", "info": {
            "last_token_usage": {"input_tokens": 100, "cached_input_tokens": 40,
                                 "output_tokens": 20, "reasoning_output_tokens": 5}
        }}},
        {"type": "response_item", "payload": {
            "type": "message", "role": "assistant",
            "content": [{"type": "output_text", "text": "resume-round; active R478"}],
            "internal_chat_message_metadata_passthrough": {"turn_id": turn},
        }},
        {"type": "event_msg", "payload": {
            "type": "task_complete", "turn_id": turn, "duration_ms": 5000,
            "time_to_first_token_ms": 700,
        }},
    ])

    runs = scan_codex_file(path)

    assert len(runs) == 1
    run = runs[0]
    assert run.total_tokens == 120
    assert run.model == "gpt-test"
    assert run.fresh_input_tokens == 60
    assert run.cached_input_tokens == 40
    assert run.tool_calls == 1
    assert run.session_context_calls == 1
    assert run.correctness is True


def test_codex_manifest_marker_binds_encrypted_subagent_prompt(
    tmp_path: Path,
) -> None:
    path = tmp_path / "subagent.jsonl"
    turn = "turn-encrypted"
    _write_jsonl(path, [
        {"type": "session_meta", "payload": {"id": "codex-agent"}},
        {"type": "event_msg", "payload": {
            "type": "task_started", "turn_id": turn,
        }},
        {"type": "event_msg", "payload": {"type": "token_count", "info": {
            "last_token_usage": {"input_tokens": 80, "cached_input_tokens": 60,
                                 "output_tokens": 4, "reasoning_output_tokens": 0}
        }}},
        {"type": "event_msg", "payload": {
            "type": "task_complete", "turn_id": turn, "duration_ms": 900,
            "time_to_first_token_ms": 300,
            "last_agent_message": "resume-round R478",
        }},
    ])

    runs = scan_codex_file(path, {
        "task": "status", "variant": "tiered", "replicate": "2",
    })

    assert len(runs) == 1
    assert runs[0].variant == "tiered"
    assert runs[0].fresh_input_tokens == 20
    assert runs[0].correctness is True


def test_comparison_pairs_codex_variants() -> None:
    from scripts.workflow_ab.measure_sessions import RunMetrics

    baseline = RunMetrics(
        runtime="codex", task="status", variant="baseline", replicate="1",
        session_id="a", source_path="a", total_tokens=100, wall_time_ms=1000,
        correctness=True,
    )
    candidate = RunMetrics(
        runtime="codex", task="status", variant="tiered", replicate="1",
        session_id="b", source_path="b", total_tokens=70, wall_time_ms=700,
        correctness=True,
    )
    result = comparisons([baseline, candidate])

    assert result == [{
        "runtime": "codex",
        "task": "status",
        "replicate": "1",
        "verdict": "IMPROVED",
        "baseline_correct": True,
        "tiered_correct": True,
        "total_tokens_delta_percent": -30.000000000000004,
        "wall_time_delta_percent": -30.000000000000004,
        "tool_calls_delta": 0,
        "rule_reads_delta": 0,
        "tool_errors_delta": 0,
    }]
