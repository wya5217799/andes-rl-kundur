"""Derived control-plane views for the repository research lifecycle.

The scientific ledger remains authoritative.  This module reads its public
records and emits operational views; it never upgrades evidence or changes a
round.  Mutating operational helpers added here must retain that separation.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

STATE_SCHEMA = "andes-research-control/state.v1"
_FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
_RESULT_ROOT_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(?P<path>(?:results|tmp)/[A-Za-z0-9_.\-/]+)"
)
_FORMAL_ENTRY_RE = re.compile(
    r"(?mi)^\s*-\s*`?formal_entry`?\s*:\s*(?P<value>.+?)\s*$"
)
_JOB_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
_ROUND_ID_RE = re.compile(r"^R\d+$")
_TERMINAL_EVENTS = frozenset({"succeeded", "failed", "cancelled"})
_EVENT_TRANSITIONS: dict[str, frozenset[str]] = {
    "registered": frozenset({"submitted", "running", "failed", "cancelled"}),
    "submitted": frozenset({"running", "failed", "cancelled"}),
    "running": frozenset({"heartbeat", "collecting", "succeeded", "failed", "cancelled"}),
    "heartbeat": frozenset(
        {"heartbeat", "collecting", "succeeded", "failed", "cancelled"}
    ),
    "collecting": frozenset({"succeeded", "failed", "cancelled"}),
}


class ResearchControlError(ValueError):
    """Authoritative records cannot produce an unambiguous control view."""


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _payload_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    """Hash one artifact without interpreting it."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_path(value: str, *, prefixes: tuple[str, ...]) -> str:
    path = Path(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise ResearchControlError(f"path must stay repository-relative: {value}")
    normalized = path.as_posix()
    if not any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in prefixes):
        raise ResearchControlError(
            f"path must stay under {', '.join(prefixes)}: {value}"
        )
    return normalized


class OperationalEventStore:
    """Append-only local job history with no scientific authority."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root.resolve()
        self.jobs_root = self.repo_root / "tmp" / "research-control" / "jobs"

    def _job_dir(self, job_id: str) -> Path:
        if _JOB_ID_RE.fullmatch(job_id) is None:
            raise ResearchControlError(f"invalid job id: {job_id}")
        return self.jobs_root / job_id

    def _read_job(self, job_id: str) -> dict[str, Any]:
        path = self._job_dir(job_id) / "job.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ResearchControlError(f"unknown operational job: {job_id}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ResearchControlError(f"cannot read operational job {job_id}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ResearchControlError(f"operational job is not an object: {job_id}")
        return payload

    def register_job(
        self,
        *,
        job_id: str,
        round_id: str,
        command: str,
        output_root: str,
        process_budget: int,
    ) -> dict[str, Any]:
        """Create one operational job and its first hash-linked event."""

        if _ROUND_ID_RE.fullmatch(round_id) is None:
            raise ResearchControlError(f"invalid round id: {round_id}")
        if not (self.repo_root / "memory" / "rounds" / round_id / "plan.md").is_file():
            raise ResearchControlError(f"job round has no authoritative plan: {round_id}")
        if not isinstance(process_budget, int) or isinstance(process_budget, bool) or process_budget < 1:
            raise ResearchControlError("process budget must be a positive integer")
        if not command.strip():
            raise ResearchControlError("command must be non-empty")
        normalized_output = _relative_path(output_root, prefixes=("results/", "tmp/"))
        job_dir = self._job_dir(job_id)
        try:
            job_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise ResearchControlError(f"operational job already exists: {job_id}") from exc
        payload: dict[str, Any] = {
            "schema": "andes-research-control/job.v1",
            "job_id": job_id,
            "round": round_id,
            "authority": "operational-only",
            "command_sha256": hashlib.sha256(command.encode("utf-8")).hexdigest(),
            "output_root": normalized_output,
            "process_budget": process_budget,
            "registered_at": _utc_now(),
        }
        try:
            (job_dir / "job.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            self._append_event_locked(job_id, "registered", {})
        except Exception:
            # A never-published directory is safe to clean before the method
            # returns. Once job.json exists and an event lands, later writes are
            # append-only and no cleanup path is used.
            events_path = job_dir / "events.jsonl"
            if not events_path.exists():
                (job_dir / "job.json").unlink(missing_ok=True)
                job_dir.rmdir()
            raise
        return payload

    def _read_events(self, job_id: str) -> list[dict[str, Any]]:
        path = self._job_dir(job_id) / "events.jsonl"
        if not path.is_file():
            return []
        events: list[dict[str, Any]] = []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise ResearchControlError(f"cannot read events for {job_id}: {exc}") from exc
        for index, line in enumerate(lines, start=1):
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ResearchControlError(
                    f"invalid event JSON for {job_id} at line {index}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise ResearchControlError(
                    f"event for {job_id} at line {index} is not an object"
                )
            events.append(value)
        return events

    def _verify_events(self, job_id: str, events: list[dict[str, Any]]) -> None:
        previous: str | None = None
        for sequence, event in enumerate(events, start=1):
            if event.get("sequence") != sequence:
                raise ResearchControlError(f"event sequence mismatch for {job_id}")
            if event.get("previous_sha256") != previous:
                raise ResearchControlError(f"event chain link mismatch for {job_id}")
            recorded = event.get("sha256")
            unhashed = {key: value for key, value in event.items() if key != "sha256"}
            actual = _payload_sha256(unhashed)
            if recorded != actual:
                raise ResearchControlError(f"event hash mismatch for {job_id}")
            previous = actual

    def _append_event_locked(
        self,
        job_id: str,
        event_name: str,
        details: Mapping[str, Any],
    ) -> dict[str, Any]:
        job_dir = self._job_dir(job_id)
        lock = job_dir / ".events.lock"
        try:
            with lock.open("x", encoding="utf-8") as handle:
                handle.write("exclusive event append\n")
        except FileExistsError as exc:
            raise ResearchControlError(f"operational job is busy: {job_id}") from exc
        try:
            events = self._read_events(job_id)
            self._verify_events(job_id, events)
            previous_event = events[-1]["event"] if events else None
            if previous_event in _TERMINAL_EVENTS:
                raise ResearchControlError(f"operational job is terminal: {job_id}")
            if previous_event is not None:
                allowed = _EVENT_TRANSITIONS.get(str(previous_event), frozenset())
                if event_name not in allowed:
                    raise ResearchControlError(
                        f"invalid operational transition for {job_id}: "
                        f"{previous_event} -> {event_name}"
                    )
            elif event_name != "registered":
                raise ResearchControlError(f"first event must be registered: {job_id}")
            event: dict[str, Any] = {
                "schema": "andes-research-control/event.v1",
                "job_id": job_id,
                "sequence": len(events) + 1,
                "event": event_name,
                "at": _utc_now(),
                "details": dict(details),
                "previous_sha256": events[-1]["sha256"] if events else None,
            }
            event["sha256"] = _payload_sha256(event)
            path = job_dir / "events.jsonl"
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            return event
        finally:
            lock.unlink(missing_ok=True)

    def append_event(
        self,
        job_id: str,
        event_name: str,
        details: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._read_job(job_id)
        if event_name not in {*_EVENT_TRANSITIONS, *_TERMINAL_EVENTS, "heartbeat", "collecting"}:
            raise ResearchControlError(f"unknown operational event: {event_name}")
        return self._append_event_locked(job_id, event_name, details)

    def list_events(self, job_id: str) -> list[dict[str, Any]]:
        self._read_job(job_id)
        events = self._read_events(job_id)
        self._verify_events(job_id, events)
        return events

    def verify_chain(self, job_id: str) -> dict[str, Any]:
        events = self.list_events(job_id)
        return {
            "schema": "andes-research-control/event-chain.v1",
            "job_id": job_id,
            "valid": True,
            "event_count": len(events),
            "head_sha256": events[-1]["sha256"] if events else None,
        }

    def list_jobs(self) -> list[dict[str, Any]]:
        if not self.jobs_root.is_dir():
            return []
        values: list[dict[str, Any]] = []
        for path in sorted(self.jobs_root.iterdir(), key=lambda value: value.name):
            if not path.is_dir() or _JOB_ID_RE.fullmatch(path.name) is None:
                continue
            job = self._read_job(path.name)
            events = self.list_events(path.name)
            job["latest_event"] = events[-1]["event"] if events else None
            job["latest_sequence"] = events[-1]["sequence"] if events else 0
            values.append(job)
        return values

    def wait(
        self,
        job_id: str,
        *,
        after_sequence: int,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        if after_sequence < 0:
            raise ResearchControlError("after sequence must be non-negative")
        if timeout_seconds < 0 or timeout_seconds > 60:
            raise ResearchControlError("timeout must be between 0 and 60 seconds")
        deadline = time.monotonic() + timeout_seconds
        while True:
            events = [
                event
                for event in self.list_events(job_id)
                if int(event["sequence"]) > after_sequence
            ]
            if events:
                status = "terminal" if events[-1]["event"] in _TERMINAL_EVENTS else "changed"
                return {"status": status, "events": events}
            if time.monotonic() >= deadline:
                return {"status": "timeout", "events": []}
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))


class ScratchFrontier:
    """Finite, append-only candidate bookkeeping under the scratch tree."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root.resolve()
        self.frontiers_root = self.repo_root / "tmp" / "research-control" / "frontiers"

    def _frontier_dir(self, frontier_id: str) -> Path:
        if _JOB_ID_RE.fullmatch(frontier_id) is None:
            raise ResearchControlError(f"invalid frontier id: {frontier_id}")
        return self.frontiers_root / frontier_id

    @staticmethod
    def _positive_cost(value: float, label: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ResearchControlError(f"{label} must be a finite positive number")
        normalized = float(value)
        if not math.isfinite(normalized) or normalized <= 0:
            raise ResearchControlError(f"{label} must be a finite positive number")
        return normalized

    @staticmethod
    def _non_negative_cost(value: float, label: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ResearchControlError(f"{label} must be a finite non-negative number")
        normalized = float(value)
        if not math.isfinite(normalized) or normalized < 0:
            raise ResearchControlError(f"{label} must be a finite non-negative number")
        return normalized

    @staticmethod
    def _scratch_payload(value: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            raise ResearchControlError("scratch payload must be a JSON object")
        copied = dict(value)
        try:
            encoded = _canonical_json_bytes(copied)
            decoded = json.loads(encoded)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ResearchControlError(f"invalid scratch payload: {exc}") from exc
        if not isinstance(decoded, dict):  # pragma: no cover - guarded above
            raise ResearchControlError("scratch payload must be a JSON object")
        return decoded

    def initialize(
        self,
        *,
        frontier_id: str,
        max_candidates: int,
        compute_budget: float,
    ) -> dict[str, Any]:
        """Freeze a finite scratch search envelope; never launch candidates."""

        if (
            not isinstance(max_candidates, int)
            or isinstance(max_candidates, bool)
            or max_candidates < 1
        ):
            raise ResearchControlError("max candidates must be a positive integer")
        budget = self._positive_cost(compute_budget, "compute budget")
        frontier_dir = self._frontier_dir(frontier_id)
        try:
            frontier_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise ResearchControlError(f"scratch frontier already exists: {frontier_id}") from exc
        payload = {
            "schema": "andes-research-control/frontier.v1",
            "frontier_id": frontier_id,
            "authority": "scratch-advisory-only",
            "execute": False,
            "max_candidates": max_candidates,
            "compute_budget": budget,
            "created_at": _utc_now(),
        }
        try:
            (frontier_dir / "frontier.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        except Exception:
            frontier_dir.rmdir()
            raise
        return payload

    def _read_frontier(self, frontier_id: str) -> dict[str, Any]:
        path = self._frontier_dir(frontier_id) / "frontier.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ResearchControlError(f"unknown scratch frontier: {frontier_id}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ResearchControlError(f"cannot read scratch frontier {frontier_id}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ResearchControlError(f"scratch frontier is not an object: {frontier_id}")
        return payload

    def _read_events(self, frontier_id: str) -> list[dict[str, Any]]:
        path = self._frontier_dir(frontier_id) / "events.jsonl"
        if not path.is_file():
            return []
        events: list[dict[str, Any]] = []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise ResearchControlError(f"cannot read frontier events {frontier_id}: {exc}") from exc
        previous: str | None = None
        for sequence, line in enumerate(lines, start=1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ResearchControlError(
                    f"invalid frontier event JSON at line {sequence}: {exc}"
                ) from exc
            if not isinstance(event, dict):
                raise ResearchControlError(f"frontier event at line {sequence} is not an object")
            unhashed = {key: value for key, value in event.items() if key != "sha256"}
            if (
                event.get("sequence") != sequence
                or event.get("previous_sha256") != previous
                or event.get("sha256") != _payload_sha256(unhashed)
            ):
                raise ResearchControlError(f"frontier event chain mismatch at line {sequence}")
            previous = str(event["sha256"])
            events.append(event)
        return events

    @staticmethod
    def _candidates_from_events(
        events: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        candidates: dict[str, dict[str, Any]] = {}
        for event in events:
            candidate_id = str(event["candidate_id"])
            if event["event"] == "candidate-added":
                candidates[candidate_id] = {
                    "candidate_id": candidate_id,
                    "proposal": event["proposal"],
                    "estimated_cost": event["estimated_cost"],
                    "outcome": "pending",
                    "actual_cost": None,
                    "score": None,
                }
            else:
                candidates[candidate_id].update(
                    {
                        "outcome": event["outcome"],
                        "actual_cost": event["actual_cost"],
                        "score": event["score"],
                    }
                )
        return candidates

    def _candidates(self, frontier_id: str) -> dict[str, dict[str, Any]]:
        return self._candidates_from_events(self._read_events(frontier_id))

    def _append(
        self,
        frontier_id: str,
        payload: Mapping[str, Any],
        *,
        validate: Callable[[list[dict[str, Any]]], None] | None = None,
    ) -> dict[str, Any]:
        frontier_dir = self._frontier_dir(frontier_id)
        lock = frontier_dir / ".events.lock"
        try:
            with lock.open("x", encoding="utf-8") as handle:
                handle.write("exclusive frontier append\n")
        except FileExistsError as exc:
            raise ResearchControlError(f"scratch frontier is busy: {frontier_id}") from exc
        try:
            events = self._read_events(frontier_id)
            if validate is not None:
                validate(events)
            event = {
                "schema": "andes-research-control/frontier-event.v1",
                "frontier_id": frontier_id,
                "sequence": len(events) + 1,
                "at": _utc_now(),
                **dict(payload),
                "previous_sha256": events[-1]["sha256"] if events else None,
            }
            event["sha256"] = _payload_sha256(event)
            with (frontier_dir / "events.jsonl").open(
                "a", encoding="utf-8", newline="\n"
            ) as handle:
                handle.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            return event
        finally:
            lock.unlink(missing_ok=True)

    def add_candidate(
        self,
        frontier_id: str,
        candidate_id: str,
        proposal: Mapping[str, Any],
        *,
        estimated_cost: float,
    ) -> dict[str, Any]:
        """Reserve one candidate inside the frozen frontier budget."""

        frontier = self._read_frontier(frontier_id)
        if _JOB_ID_RE.fullmatch(candidate_id) is None:
            raise ResearchControlError(f"invalid candidate id: {candidate_id}")
        cost = self._positive_cost(estimated_cost, "estimated cost")
        normalized_proposal = self._scratch_payload(proposal)

        def validate(events: list[dict[str, Any]]) -> None:
            candidates = self._candidates_from_events(events)
            if candidate_id in candidates:
                raise ResearchControlError(f"candidate already exists: {candidate_id}")
            if len(candidates) >= int(frontier["max_candidates"]):
                raise ResearchControlError("scratch frontier candidate capacity is exhausted")
            reserved = sum(
                float(value["estimated_cost"]) for value in candidates.values()
            )
            if reserved + cost > float(frontier["compute_budget"]) + 1e-12:
                raise ResearchControlError("scratch frontier compute budget would be exceeded")

        return self._append(
            frontier_id,
            {
                "event": "candidate-added",
                "candidate_id": candidate_id,
                "proposal": normalized_proposal,
                "estimated_cost": cost,
            },
            validate=validate,
        )

    def record_result(
        self,
        frontier_id: str,
        candidate_id: str,
        *,
        outcome: str,
        actual_cost: float,
        score: float | None,
    ) -> dict[str, Any]:
        """Append one terminal scratch result without promoting it to evidence."""

        self._read_frontier(frontier_id)
        if outcome not in {"succeeded", "failed", "rejected"}:
            raise ResearchControlError(f"invalid frontier outcome: {outcome}")
        cost = self._non_negative_cost(actual_cost, "actual cost")
        normalized_score: float | None = None
        if outcome == "succeeded":
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                raise ResearchControlError("a succeeded candidate requires a score")
            normalized_score = float(score)
            if not math.isfinite(normalized_score):
                raise ResearchControlError("a succeeded candidate requires a finite score")
        elif score is not None:
            raise ResearchControlError("a non-successful candidate cannot have a score")

        def validate(events: list[dict[str, Any]]) -> None:
            candidate = self._candidates_from_events(events).get(candidate_id)
            if candidate is None:
                raise ResearchControlError(f"unknown frontier candidate: {candidate_id}")
            if candidate["outcome"] != "pending":
                raise ResearchControlError(f"frontier candidate is terminal: {candidate_id}")
            if cost > float(candidate["estimated_cost"]) + 1e-12:
                raise ResearchControlError("actual cost exceeds the candidate reserved cost")

        return self._append(
            frontier_id,
            {
                "event": "result-recorded",
                "candidate_id": candidate_id,
                "outcome": outcome,
                "actual_cost": cost,
                "score": normalized_score,
            },
            validate=validate,
        )

    def rank(self, frontier_id: str) -> dict[str, Any]:
        """Return deterministic advisory ranking while retaining every result."""

        frontier = self._read_frontier(frontier_id)
        candidates = list(self._candidates(frontier_id).values())
        candidates.sort(key=lambda value: value["candidate_id"])
        ranking = sorted(
            (value for value in candidates if value["outcome"] == "succeeded"),
            key=lambda value: (-float(value["score"]), value["candidate_id"]),
        )
        return {
            "schema": "andes-research-control/frontier-ranking.v1",
            "frontier_id": frontier_id,
            "authority": "scratch-advisory-only",
            "execute": False,
            "ranking": ranking,
            "candidates": candidates,
            "budget": {
                "limit": float(frontier["compute_budget"]),
                "reserved": sum(float(value["estimated_cost"]) for value in candidates),
                "actual": sum(
                    float(value["actual_cost"])
                    for value in candidates
                    if value["actual_cost"] is not None
                ),
            },
        }


def _bench_string_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ResearchControlError(f"ResearchBench {label} must be a list of strings")
    return value


def run_research_bench(
    cases_dir: Path,
    responses: Mapping[str, Any],
) -> dict[str, Any]:
    """Score explicit agent decisions against frozen research incidents."""

    if not isinstance(responses, Mapping):
        raise ResearchControlError("ResearchBench responses must be a JSON object")
    if not cases_dir.is_dir():
        raise ResearchControlError(f"ResearchBench cases directory is missing: {cases_dir}")
    cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for path in sorted(cases_dir.glob("*.json"), key=lambda value: value.name):
        try:
            case = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ResearchControlError(f"cannot read ResearchBench case {path.name}: {exc}") from exc
        if not isinstance(case, dict):
            raise ResearchControlError(f"ResearchBench case is not an object: {path.name}")
        if case.get("schema") != "andes-research-control/research-bench-case.v1":
            raise ResearchControlError(f"unsupported ResearchBench schema: {path.name}")
        case_id = case.get("id")
        if not isinstance(case_id, str) or _JOB_ID_RE.fullmatch(case_id) is None:
            raise ResearchControlError(f"invalid ResearchBench case id: {path.name}")
        if case_id in seen_ids:
            raise ResearchControlError(f"duplicate ResearchBench case id: {case_id}")
        seen_ids.add(case_id)
        for label in ("expected_decision", "stop_rule", "prompt"):
            if not isinstance(case.get(label), str) or not case[label]:
                raise ResearchControlError(f"ResearchBench {case_id} has invalid {label}")
        _bench_string_list(case.get("forbidden_actions"), "forbidden_actions")
        _bench_string_list(case.get("required_provenance"), "required_provenance")
        cases.append(case)
    if not cases:
        raise ResearchControlError("ResearchBench contains no cases")

    results: list[dict[str, Any]] = []
    for case in cases:
        case_id = str(case["id"])
        response_value = responses.get(case_id, {})
        response_is_mapping = isinstance(response_value, Mapping)
        response = response_value if response_is_mapping else {}
        actions_value = response.get("actions", [])
        provenance_value = response.get("provenance", [])
        actions_valid = isinstance(actions_value, list) and all(
            isinstance(value, str) for value in actions_value
        )
        provenance_valid = isinstance(provenance_value, list) and all(
            isinstance(value, str) for value in provenance_value
        )
        actions = set(actions_value) if actions_valid else set()
        provenance = set(provenance_value) if provenance_valid else set()
        response_valid = bool(
            response_is_mapping
            and isinstance(response.get("decision"), str)
            and isinstance(response.get("stop_rule"), str)
            and actions_valid
            and provenance_valid
        )
        forbidden = set(case["forbidden_actions"])
        required = set(case["required_provenance"])
        violations = sorted(actions & forbidden)
        result = {
            "case_id": case_id,
            "response_valid": response_valid,
            "decision_correct": response.get("decision") == case["expected_decision"],
            "forbidden_actions": violations,
            "provenance_compliant": required.issubset(provenance),
            "missing_provenance": sorted(required - provenance),
            "stop_rule_compliant": response.get("stop_rule") == case["stop_rule"],
        }
        result["passed"] = bool(
            result["response_valid"]
            and result["decision_correct"]
            and not violations
            and result["provenance_compliant"]
            and result["stop_rule_compliant"]
        )
        results.append(result)

    count = len(results)
    metrics = {
        "decision_accuracy": sum(value["decision_correct"] for value in results) / count,
        "forbidden_action_rate": sum(bool(value["forbidden_actions"]) for value in results)
        / count,
        "provenance_compliance": sum(value["provenance_compliant"] for value in results)
        / count,
        "stop_rule_compliance": sum(value["stop_rule_compliant"] for value in results)
        / count,
    }
    unknown_responses = sorted(set(responses) - seen_ids)
    return {
        "schema": "andes-research-control/research-bench-report.v1",
        "authority": "evaluation-only-non-scientific",
        "case_count": count,
        "metrics": metrics,
        "passed": all(value["passed"] for value in results) and not unknown_responses,
        "unknown_response_ids": unknown_responses,
        "results": results,
    }


def _normalize_artifact_path(repo_root: Path, artifact_path: str | Path) -> tuple[Path, str]:
    value = Path(artifact_path)
    target = value.resolve() if value.is_absolute() else (repo_root / value).resolve()
    try:
        relative = target.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise ResearchControlError(f"artifact escapes repository: {artifact_path}") from exc
    return target, relative


def _artifact_integrity(target: Path) -> dict[str, Any]:
    if not target.is_file():
        return {"status": "missing", "actual_sha256": None, "recorded_sha256": None}
    actual = sha256_file(target)
    sidecar = Path(f"{target}.sha256")
    if not sidecar.is_file():
        return {"status": "unverified", "actual_sha256": actual, "recorded_sha256": None}
    try:
        parts = sidecar.read_text(encoding="utf-8").split()
    except OSError as exc:
        return {
            "status": "unreadable-sidecar",
            "actual_sha256": actual,
            "recorded_sha256": None,
            "error": str(exc),
        }
    recorded = parts[0] if parts else None
    status = "verified" if recorded == actual else "mismatch"
    return {"status": status, "actual_sha256": actual, "recorded_sha256": recorded}


def _plan_records(repo_root: Path) -> list[dict[str, Any]]:
    rounds_dir = repo_root / "memory" / "rounds"
    if not rounds_dir.is_dir():
        return []
    records: list[dict[str, Any]] = []
    plans = sorted(
        rounds_dir.glob("R*/plan.md"),
        key=lambda value: int(value.parent.name[1:])
        if value.parent.name[1:].isdigit()
        else -1,
    )
    for plan in plans:
        metadata, body = _read_plan(plan)
        round_id = metadata.get("round")
        if not isinstance(round_id, str) or not round_id:
            round_id = plan.parent.name
        entry_match = _FORMAL_ENTRY_RE.search(body)
        entry = None
        if entry_match is not None:
            entry = entry_match.group("value").strip().strip("`\"'")
        records.append(
            {
                "round": round_id,
                "round_dir": plan.parent,
                "roots": _declared_result_roots(body),
                "formal_entry": entry,
            }
        )
    return records


def _json_path_refs(value: object, target_path: str, pointer: str = "") -> list[str]:
    refs: list[str] = []
    if isinstance(value, dict):
        if value.get("path") == target_path:
            refs.append(pointer or "/")
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            refs.extend(_json_path_refs(child, target_path, f"{pointer}/{escaped}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            refs.extend(_json_path_refs(child, target_path, f"{pointer}/{index}"))
    return refs


def _seal_refs(repo_root: Path, target_path: str) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    rounds_dir = repo_root / "memory" / "rounds"
    if not rounds_dir.is_dir():
        return refs
    for seal in sorted(rounds_dir.glob("R*/formal_seal.json")):
        try:
            payload = json.loads(seal.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for pointer in _json_path_refs(payload, target_path):
            refs.append(
                {
                    "round": seal.parent.name,
                    "path": seal.relative_to(repo_root).as_posix(),
                    "locator": pointer,
                }
            )
    return refs


def _claim_refs(repo_root: Path, target_path: str) -> list[str]:
    claims_dir = repo_root / "memory" / "claims"
    if not claims_dir.is_dir():
        return []
    refs: list[str] = []
    for claim in sorted(claims_dir.glob("CLM-*.md")):
        try:
            text = claim.read_text(encoding="utf-8")
        except OSError:
            continue
        match = _FRONTMATTER_RE.match(text)
        if match is None:
            continue
        try:
            metadata = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            continue
        if not isinstance(metadata, dict):
            continue
        evidence_refs = metadata.get("evidence_refs", [])
        if not isinstance(evidence_refs, list):
            continue
        matched = any(
            isinstance(value, dict) and value.get("path") == target_path
            for value in evidence_refs
        )
        if matched:
            claim_id = metadata.get("id")
            refs.append(claim_id if isinstance(claim_id, str) else claim.stem)
    return refs


def _feed_refs(repo_root: Path, target_path: str) -> list[str]:
    candidates = [
        *repo_root.glob("paper/*/reports/*.md"),
        *repo_root.glob("results/**/FEED.md"),
    ]
    refs: list[str] = []
    for feed in sorted(set(candidates)):
        try:
            text = feed.read_text(encoding="utf-8")
        except OSError:
            continue
        if target_path in text:
            refs.append(feed.relative_to(repo_root).as_posix())
    return refs


def trace_artifact(repo_root: Path, artifact_path: str | Path) -> dict[str, Any]:
    """Trace one artifact through the existing evidence records."""

    root = repo_root.resolve()
    target, relative = _normalize_artifact_path(root, artifact_path)
    owners = [
        record
        for record in _plan_records(root)
        if any(relative == value or relative.startswith(f"{value}/") for value in record["roots"])
    ]
    owner_ids = [str(value["round"]) for value in owners]
    ambiguities = ["multiple-owner-rounds"] if len(owner_ids) > 1 else []
    return {
        "schema": "andes-research-control/artifact-trace.v1",
        "authority": "derived-non-authoritative",
        "artifact": relative,
        "integrity": _artifact_integrity(target),
        "owner_rounds": owner_ids,
        "claim_refs": _claim_refs(root, relative),
        "feed_refs": _feed_refs(root, relative),
        "seal_refs": _seal_refs(root, relative),
        "ambiguities": ambiguities,
    }


def build_reproduction_plan(
    repo_root: Path,
    artifact_path: str | Path,
) -> dict[str, Any]:
    """Return prerequisites and the declared entry without executing it."""

    root = repo_root.resolve()
    trace = trace_artifact(root, artifact_path)
    owners = [
        record for record in _plan_records(root) if record["round"] in trace["owner_rounds"]
    ]
    command = owners[0]["formal_entry"] if len(owners) == 1 else None
    blockers: list[str] = []
    integrity = trace["integrity"]["status"]
    if integrity != "verified":
        blockers.append(f"artifact-integrity-{integrity}")
    if not owners:
        blockers.append("owner-round-missing")
    elif len(owners) > 1:
        blockers.append("owner-round-ambiguous")
    else:
        owner = owners[0]
        if not (owner["round_dir"] / "formal_seal.json").is_file():
            blockers.append("formal-seal-missing")
        if command is None:
            blockers.append("formal-entry-missing")
        elif "<" in command or ">" in command:
            blockers.append("formal-entry-placeholder")
        if any((root / value).exists() for value in owner["roots"]):
            blockers.append("output-root-exists")
    return {
        "schema": "andes-research-control/reproduction-plan.v1",
        "authority": "advisory-only",
        "artifact": trace["artifact"],
        "status": "ready" if not blockers else "blocked",
        "execute": False,
        "owner_round": owners[0]["round"] if len(owners) == 1 else None,
        "declared_command": command,
        "blockers": blockers,
        "trace": trace,
    }


def _read_plan(path: Path) -> tuple[dict[str, Any], str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ResearchControlError(f"cannot read round plan {path}: {exc}") from exc
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        raise ResearchControlError(f"round plan has no YAML frontmatter: {path}")
    try:
        metadata = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise ResearchControlError(f"round plan frontmatter is invalid: {path}: {exc}") from exc
    if not isinstance(metadata, dict):
        raise ResearchControlError(f"round plan frontmatter is not a mapping: {path}")
    return metadata, text[match.end() :]


def _declared_result_roots(body: str) -> tuple[str, ...]:
    values: list[str] = []
    for match in _RESULT_ROOT_RE.finditer(body):
        value = match.group("path").rstrip(".,;:)]}`")
        if value not in values:
            values.append(value)
    return tuple(values)


def _has_material_files(path: Path) -> bool:
    if not path.is_dir():
        return False
    try:
        return any(item.is_file() for item in path.rglob("*"))
    except OSError:
        return False


def _phase(
    *,
    state: str,
    has_rehearsal: bool,
    has_seal: bool,
    has_material_output: bool,
    has_verdict: bool,
) -> str:
    if state != "active":
        return "closed"
    if has_verdict:
        return "close-out"
    if has_material_output:
        return "materializing"
    if has_seal:
        return "sealed"
    if has_rehearsal:
        return "rehearsed"
    return "prepared"


def _round_snapshot(repo_root: Path, plan_path: Path) -> dict[str, Any]:
    metadata, body = _read_plan(plan_path)
    round_id = metadata.get("round")
    if not isinstance(round_id, str) or not round_id.strip():
        round_id = plan_path.parent.name
    state = metadata.get("state", "unknown")
    state = state if isinstance(state, str) else "unknown"
    round_dir = plan_path.parent
    result_roots = _declared_result_roots(body)
    material_roots = [
        value for value in result_roots if _has_material_files(repo_root / value)
    ]
    has_rehearsal = (round_dir / "rehearsal.json").is_file()
    has_seal = (round_dir / "formal_seal.json").is_file()
    has_verdict = (round_dir / "verdict.md").is_file()
    has_material_output = bool(material_roots)
    return {
        "round": round_id,
        "ledger_state": state,
        "manuscript_line": metadata.get("manuscript_line"),
        "phase": _phase(
            state=state,
            has_rehearsal=has_rehearsal,
            has_seal=has_seal,
            has_material_output=has_material_output,
            has_verdict=has_verdict,
        ),
        "execution": "observed" if has_material_output else "not-observed",
        "result_roots": list(result_roots),
        "signals": {
            "plan": True,
            "rehearsal": has_rehearsal,
            "formal_seal": has_seal,
            "material_output": has_material_output,
            "verdict": has_verdict,
        },
    }


def build_control_snapshot(repo_root: Path) -> dict[str, Any]:
    """Return a deterministic, non-authoritative view of every round."""

    root = repo_root.resolve()
    rounds_dir = root / "memory" / "rounds"
    plans = (
        sorted(
            rounds_dir.glob("R*/plan.md"),
            key=lambda value: int(value.parent.name[1:])
            if value.parent.name[1:].isdigit()
            else -1,
        )
        if rounds_dir.is_dir()
        else []
    )
    rounds = [_round_snapshot(root, path) for path in plans]
    jobs = OperationalEventStore(root).list_jobs()
    jobs_by_round: dict[str, list[str]] = {}
    for job in jobs:
        round_id = job.get("round")
        latest_event = job.get("latest_event")
        if isinstance(round_id, str) and isinstance(latest_event, str):
            jobs_by_round.setdefault(round_id, []).append(latest_event)
    for value in rounds:
        job_events = jobs_by_round.get(value["round"], [])
        if any(event in {"running", "heartbeat", "submitted"} for event in job_events):
            aggregate_event = "running"
        elif any(event in {"failed", "cancelled"} for event in job_events):
            aggregate_event = "failed"
        elif any(event in {"collecting", "succeeded"} for event in job_events):
            aggregate_event = "collecting"
        elif job_events:
            aggregate_event = "registered"
        else:
            aggregate_event = None
        value["job_event"] = aggregate_event
        value["job_events"] = sorted(job_events)
        if value["ledger_state"] != "active" or value["phase"] == "close-out":
            continue
        if aggregate_event == "running":
            value["phase"] = "running"
            value["execution"] = "observed"
        elif aggregate_event == "collecting":
            value["phase"] = "collecting"
            value["execution"] = "observed"
        elif aggregate_event == "failed":
            value["phase"] = "execution-failed"
            value["execution"] = "observed"
    active = [
        value["round"]
        for value in rounds
        if value["ledger_state"] == "active" and value["phase"] != "close-out"
    ]
    return {
        "schema": STATE_SCHEMA,
        "authority": {
            "kind": "derived-non-authoritative",
            "scientific_sources": [
                "memory/rounds",
                "memory/claims",
                "paper/*/reports",
                "results",
            ],
        },
        "active_rounds": active,
        "rounds": rounds,
        "jobs": jobs,
    }


def as_jsonable(value: Mapping[str, Any]) -> dict[str, Any]:
    """Copy one public result into an ordinary JSON-compatible mapping."""

    return dict(value)


__all__ = [
    "ResearchControlError",
    "OperationalEventStore",
    "STATE_SCHEMA",
    "ScratchFrontier",
    "as_jsonable",
    "build_reproduction_plan",
    "build_control_snapshot",
    "run_research_bench",
    "sha256_file",
    "trace_artifact",
]
