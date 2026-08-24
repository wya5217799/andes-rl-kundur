"""Measure tagged Codex workflow A/B sessions.

Motivation
----------
Workflow changes need project-local evidence rather than impressions.  This
scanner extracts comparable per-turn token, latency, cache, tool-call, retry,
and completion metrics from Codex JSONL rollouts. It reads sessions whose
human prompt contains a marker such as
``[WF-BENCH task=status variant=baseline replicate=1]``.

Usage
-----
    python scripts/workflow_ab/measure_sessions.py \
      --codex-manifest tmp/workflow_ab/codex-runs.json \
      --output tmp/workflow_ab_20260825/metrics.json

Failure modes
-------------
- Missing roots and invalid manifests are reported in ``scan_warnings``.
- Files without a benchmark marker are ignored.
- Duplicate run identities are retained and reported; the scanner never
  silently chooses one observation.

The output is operational evaluation only.  It is not experiment evidence and
does not authorize edits to AGENTS.md, CLAUDE.md, active rounds, or manuscripts.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

MARKER_RE = re.compile(r"\[WF-BENCH\s+([^\]]+)\]")
ERROR_RE = re.compile(
    r"(?:^|\n)(?:Error:|Script failed|ToolCallError)|timed out|"
    r"exit code [1-9]\d*",
    re.IGNORECASE,
)
RULE_READ_RE = re.compile(
    r"(?:AGENTS\.md|CLAUDE\.md|skills[/\\]kundur-round[/\\]SKILL\.md|"
    r"resume-contract\.md)",
    re.IGNORECASE,
)
SESSION_CONTEXT_RE = re.compile(r"session_context\.py", re.IGNORECASE)


@dataclass
class RunMetrics:
    runtime: str
    task: str
    variant: str
    replicate: str
    session_id: str
    source_path: str
    model: str = "unknown"
    input_tokens: int = 0
    fresh_input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    wall_time_ms: int | None = None
    time_to_first_token_ms: int | None = None
    tool_calls: int = 0
    tool_errors: int = 0
    rule_reads: int = 0
    session_context_calls: int = 0
    final_text: str = ""
    correctness: bool = False
    correctness_reasons: list[str] = field(default_factory=list)


def _marker(text: str) -> dict[str, str] | None:
    match = MARKER_RE.search(text)
    if not match:
        return None
    fields: dict[str, str] = {}
    for item in match.group(1).split():
        key, separator, value = item.partition("=")
        if separator and key and value:
            fields[key] = value
    required = {"task", "variant", "replicate"}
    return fields if required <= fields.keys() else None


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(item.get("text", ""))
            for item in content
            if isinstance(item, dict)
        )
    return ""


def _tool_result_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_tool_result_text(item) for item in value)
    if isinstance(value, dict):
        text = str(value.get("text", ""))
        return text + "".join(_tool_result_text(v) for v in value.values())
    return ""


def _score(task: str, final_text: str) -> tuple[bool, list[str]]:
    checks = {
        "status": (
            ("resume-round" in final_text, "mode=resume-round"),
            ("R478" in final_text, "active=R478"),
        ),
        "friction-map": (
            ("mapping_complete" in final_text and "true" in final_text.lower(),
             "mapping_complete=true"),
            (re.search(r"signal_count\D+6", final_text) is not None,
             "signal_count=6"),
        ),
        "owner-gate": (
            ("BLOCK" in final_text, "decision=BLOCK"),
            ("OWNER_APPROVED" in final_text, "owner marker named"),
        ),
    }
    selected = checks.get(task)
    if not selected:
        return False, [f"unknown task validator: {task}"]
    missing = [label for passed, label in selected if not passed]
    return not missing, missing


def _new_run(runtime: str, marker: dict[str, str], session_id: str,
             path: Path) -> RunMetrics:
    return RunMetrics(
        runtime=runtime,
        task=marker["task"],
        variant=marker["variant"],
        replicate=marker["replicate"],
        session_id=session_id,
        source_path=str(path),
    )


def scan_codex_file(
    path: Path,
    fallback_marker: dict[str, str] | None = None,
) -> list[RunMetrics]:
    """Scan one Codex rollout.

    Fresh subagent task text may be encrypted in persisted rollouts.  In that
    case a preregistered manifest supplies ``fallback_marker``; it binds only
    the first turn in that rollout.
    """
    try:
        events = [json.loads(line) for line in path.read_text(
            encoding="utf-8", errors="replace").splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError):
        return []

    session_id = path.stem
    runs: dict[str, RunMetrics] = {}
    active_turn: str | None = None
    call_turn: dict[str, str] = {}
    turn_models: dict[str, str] = {}

    for event in events:
        event_type = event.get("type")
        payload = event.get("payload") or {}
        if event_type == "session_meta":
            session_id = str(payload.get("id") or payload.get("session_id") or session_id)
        elif event_type == "event_msg" and payload.get("type") == "task_started":
            active_turn = str(payload.get("turn_id") or "")
            if fallback_marker and active_turn and not runs:
                runs[active_turn] = _new_run(
                    "codex", fallback_marker, session_id, path
                )
        elif event_type == "turn_context":
            turn_id = str(payload.get("turn_id") or "")
            turn_models[turn_id] = str(payload.get("model") or "unknown")
            if turn_id in runs:
                runs[turn_id].model = turn_models[turn_id]
        elif event_type == "response_item":
            turn_id = str(
                (payload.get("internal_chat_message_metadata_passthrough") or {}).get(
                    "turn_id", active_turn or ""
                )
            )
            kind = payload.get("type")
            if kind == "message" and payload.get("role") == "user":
                text = _content_text(payload.get("content"))
                marker = _marker(text)
                if marker and turn_id:
                    runs[turn_id] = _new_run("codex", marker, session_id, path)
                    runs[turn_id].model = turn_models.get(turn_id, "unknown")
            elif turn_id in runs and kind in {"function_call", "custom_tool_call"}:
                run = runs[turn_id]
                run.tool_calls += 1
                call_id = str(payload.get("call_id") or payload.get("id") or "")
                call_turn[call_id] = turn_id
                arguments = str(payload.get("arguments") or payload.get("input") or "")
                run.rule_reads += len(RULE_READ_RE.findall(arguments))
                run.session_context_calls += len(SESSION_CONTEXT_RE.findall(arguments))
            elif kind in {"function_call_output", "custom_tool_call_output"}:
                call_id = str(payload.get("call_id") or "")
                owner = call_turn.get(call_id)
                if owner in runs and ERROR_RE.search(_tool_result_text(payload.get("output"))):
                    runs[owner].tool_errors += 1
            elif turn_id in runs and kind == "message" and payload.get("role") == "assistant":
                text = _content_text(payload.get("content"))
                if text:
                    runs[turn_id].final_text = text
        elif event_type == "event_msg" and payload.get("type") == "token_count":
            if active_turn in runs:
                usage = ((payload.get("info") or {}).get("last_token_usage") or {})
                run = runs[active_turn]
                input_tokens = int(usage.get("input_tokens") or 0)
                cached = int(usage.get("cached_input_tokens") or 0)
                run.input_tokens += input_tokens
                run.cached_input_tokens += cached
                run.fresh_input_tokens += max(0, input_tokens - cached)
                run.output_tokens += int(usage.get("output_tokens") or 0)
                run.reasoning_tokens += int(usage.get("reasoning_output_tokens") or 0)
        elif event_type == "event_msg" and payload.get("type") == "task_complete":
            turn_id = str(payload.get("turn_id") or active_turn or "")
            if turn_id in runs:
                run = runs[turn_id]
                run.wall_time_ms = int(payload.get("duration_ms") or 0)
                run.time_to_first_token_ms = int(
                    payload.get("time_to_first_token_ms") or 0
                )
                if not run.final_text:
                    run.final_text = str(payload.get("last_agent_message") or "")
            if active_turn == turn_id:
                active_turn = None

    for run in runs.values():
        run.total_tokens = run.input_tokens + run.output_tokens
        run.correctness, run.correctness_reasons = _score(run.task, run.final_text)
    return list(runs.values())


def _percent(candidate: int | None, baseline: int | None) -> float | None:
    if candidate is None or baseline in (None, 0):
        return None
    return 100.0 * (candidate / baseline - 1.0)


def comparisons(runs: Iterable[RunMetrics]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, list[RunMetrics]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for run in runs:
        grouped[(run.runtime, run.task, run.replicate)][run.variant].append(run)

    output: list[dict[str, Any]] = []
    for (runtime, task, replicate), variants in sorted(grouped.items()):
        if len(variants.get("baseline", [])) != 1 or len(variants.get("tiered", [])) != 1:
            continue
        baseline = variants["baseline"][0]
        candidate = variants["tiered"][0]
        token_delta = _percent(candidate.total_tokens, baseline.total_tokens)
        wall_delta = _percent(candidate.wall_time_ms, baseline.wall_time_ms)
        if not candidate.correctness:
            verdict = "REGRESSED"
        elif token_delta is not None and wall_delta is not None:
            verdict = "IMPROVED" if token_delta < 0 and wall_delta < 0 else "TRADEOFF"
        else:
            verdict = "INCOMPLETE"
        output.append({
            "runtime": runtime,
            "task": task,
            "replicate": replicate,
            "verdict": verdict,
            "baseline_correct": baseline.correctness,
            "tiered_correct": candidate.correctness,
            "total_tokens_delta_percent": token_delta,
            "wall_time_delta_percent": wall_delta,
            "tool_calls_delta": candidate.tool_calls - baseline.tool_calls,
            "rule_reads_delta": candidate.rule_reads - baseline.rule_reads,
            "tool_errors_delta": candidate.tool_errors - baseline.tool_errors,
        })
    return output


def _files(root: Path, patterns: tuple[str, ...]) -> Iterable[Path]:
    for pattern in patterns:
        yield from root.rglob(pattern)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-root", type=Path)
    parser.add_argument(
        "--codex-manifest",
        type=Path,
        help="JSON runs with source_path/task/variant/replicate for encrypted prompts",
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    runs: list[RunMetrics] = []
    warnings: list[str] = []
    if args.codex_root:
        if args.codex_root.is_dir():
            for path in _files(args.codex_root, ("*.jsonl",)):
                runs.extend(scan_codex_file(path))
        else:
            warnings.append(f"missing codex root: {args.codex_root}")
    if args.codex_manifest:
        try:
            manifest = json.loads(args.codex_manifest.read_text(encoding="utf-8"))
            entries = manifest.get("runs", [])
        except (OSError, json.JSONDecodeError, AttributeError) as exc:
            entries = []
            warnings.append(f"invalid codex manifest: {exc}")
        for entry in entries:
            marker = {
                key: str(entry[key])
                for key in ("task", "variant", "replicate")
                if key in entry
            }
            source = Path(str(entry.get("source_path", "")))
            if len(marker) != 3 or not source.is_file():
                warnings.append(f"invalid codex manifest entry: {entry}")
                continue
            found = scan_codex_file(source, marker)
            if len(found) != 1:
                warnings.append(
                    f"expected one codex run, found {len(found)}: {source}"
                )
            runs.extend(found)
    identities = Counter(
        (run.runtime, run.task, run.variant, run.replicate) for run in runs
    )
    duplicates = [
        {"runtime": key[0], "task": key[1], "variant": key[2],
         "replicate": key[3], "count": count}
        for key, count in identities.items() if count > 1
    ]
    payload = {
        "schema_version": 1,
        "authority": "operational-evaluation-only",
        "runs": [asdict(run) for run in runs],
        "comparisons": comparisons(runs),
        "duplicates": duplicates,
        "scan_warnings": warnings,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"workflow A/B: runs={len(runs)} comparisons={len(payload['comparisons'])} "
        f"duplicates={len(duplicates)} warnings={len(warnings)}"
    )
    return 0 if runs and not duplicates else 1


if __name__ == "__main__":
    raise SystemExit(main())
