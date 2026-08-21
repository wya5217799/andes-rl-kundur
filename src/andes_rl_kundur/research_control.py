"""Derived control-plane views for the repository research lifecycle.

The scientific ledger remains authoritative.  This module reads its public
records and emits operational views; it never upgrades evidence or changes a
round.  Mutating operational helpers added here must retain that separation.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import os
import re
import shutil
import stat
import tempfile
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
_FEED_ROUND_COMPONENT_RE = re.compile(r"^[rR](\d+)(?:[_.-].*)?$")
_CLAIM_ROUND_RE = re.compile(r"(?<![A-Za-z0-9])R(\d+)(?!\d|[A-Za-z])")
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
    """Hash one canonical JSON payload; normalize serialization failures.

    Untrusted on-disk payloads can carry NaN or non-JSON objects, which
    json.dumps rejects with TypeError/ValueError.  Callers treat
    ResearchControlError as the module-wide "cannot produce a control view"
    signal, so a bare TypeError/ValueError would escape isolation (for
    example inside list_jobs_with_diagnostics) and crash the whole snapshot.
    """

    try:
        canonical = _canonical_json_bytes(payload)
    except (TypeError, ValueError) as exc:
        raise ResearchControlError(f"payload is not canonical JSON: {exc}") from exc
    return hashlib.sha256(canonical).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_repository_write_path(repo_root: Path, target: Path) -> None:
    """Reject writes through links or ancestors that resolve outside the repo."""

    candidate = target
    while True:
        try:
            metadata = os.lstat(candidate)
        except FileNotFoundError:
            if candidate == candidate.parent:
                raise ResearchControlError(f"write path escapes repository: {target}")
            candidate = candidate.parent
            continue
        except OSError as exc:
            raise ResearchControlError(f"write path escapes repository: {target}") from exc
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        file_attributes = getattr(metadata, "st_file_attributes", 0)
        if stat.S_ISLNK(metadata.st_mode) or file_attributes & reparse_flag:
            raise ResearchControlError(f"write path escapes repository: {target}")
        try:
            candidate.resolve(strict=True).relative_to(repo_root.resolve())
        except (OSError, ValueError) as exc:
            raise ResearchControlError(f"write path escapes repository: {target}") from exc
        return


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _write_atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Publish one complete JSON object after flushing its temporary file."""

    temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(
                json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


class _PortableFileLock:
    """A crash-releasing non-blocking byte lock backed by the operating system."""

    def __init__(self, path: Path, busy_message: str):
        self.path = path
        self.busy_message = busy_message
        self.handle: Any = None

    def __enter__(self) -> _PortableFileLock:
        self.handle = self.path.open("a+b")
        self.handle.seek(0, os.SEEK_END)
        if self.handle.tell() == 0:
            self.handle.write(b"\0")
            self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl = importlib.import_module("fcntl")
                fcntl.flock(
                    self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
                )
        except OSError as exc:
            self.handle.close()
            self.handle = None
            raise ResearchControlError(self.busy_message) from exc
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.handle is None:
            return
        try:
            self.handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl = importlib.import_module("fcntl")
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None


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
        _ensure_repository_write_path(self.repo_root, path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ResearchControlError(f"unknown operational job: {job_id}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ResearchControlError(f"cannot read operational job {job_id}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ResearchControlError(f"operational job is not an object: {job_id}")
        recorded_hash = payload.get("sha256")
        unhashed = {key: value for key, value in payload.items() if key != "sha256"}
        if not isinstance(recorded_hash, str) or recorded_hash != _payload_sha256(unhashed):
            raise ResearchControlError(f"operational job metadata hash mismatch: {job_id}")
        required_types = {
            "schema": str,
            "job_id": str,
            "round": str,
            "authority": str,
            "command_sha256": str,
            "output_root": str,
            "process_budget": int,
            "registered_at": str,
        }
        if any(not isinstance(payload.get(key), value) for key, value in required_types.items()):
            raise ResearchControlError(f"operational job schema is invalid: {job_id}")
        if (
            payload["schema"] != "andes-research-control/job.v1"
            or payload["job_id"] != job_id
            or payload["authority"] != "operational-only"
            or _ROUND_ID_RE.fullmatch(payload["round"]) is None
            or not isinstance(payload["process_budget"], int)
            or isinstance(payload["process_budget"], bool)
            or payload["process_budget"] < 1
            or re.fullmatch(r"[0-9a-f]{64}", payload["command_sha256"]) is None
        ):
            raise ResearchControlError(f"operational job schema is invalid: {job_id}")
        normalized = _relative_path(payload["output_root"], prefixes=("results/", "tmp/"))
        if normalized != payload["output_root"]:
            raise ResearchControlError(f"operational job output root is invalid: {job_id}")
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
        plan_path = self.repo_root / "memory" / "rounds" / round_id / "plan.md"
        if not plan_path.is_file():
            raise ResearchControlError(f"job round has no authoritative plan: {round_id}")
        if not isinstance(process_budget, int) or isinstance(process_budget, bool) or process_budget < 1:
            raise ResearchControlError("process budget must be a positive integer")
        if not command.strip():
            raise ResearchControlError("command must be non-empty")
        normalized_output = _relative_path(output_root, prefixes=("results/", "tmp/"))
        _, plan_body = _read_plan(plan_path)
        declared_roots = _declared_result_roots(plan_body)
        if not any(
            normalized_output == root or normalized_output.startswith(f"{root}/")
            for root in declared_roots
        ):
            raise ResearchControlError(
                f"job output root is not declared by round {round_id}: {normalized_output}"
            )
        job_dir = self._job_dir(job_id)
        _ensure_repository_write_path(self.repo_root, job_dir)
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
        payload["sha256"] = _payload_sha256(payload)
        try:
            _write_atomic_json(job_dir / "job.json", payload)
            self._append_event_locked(
                job_id,
                "registered",
                {"job_sha256": payload["sha256"]},
                allow_first=True,
            )
        except Exception:
            # A never-published directory is safe to clean before the method
            # returns. Once job.json exists and an event lands, later writes are
            # append-only and no cleanup path is used. Removal is best-effort:
            # a crash may leave temporary files behind, so a bare rmdir() would
            # fail and either mask the original error or brick the id on retry.
            events_dir = job_dir / "events"
            if not events_dir.is_dir() or not any(events_dir.glob("*.json")):
                shutil.rmtree(job_dir, ignore_errors=True)
            raise
        return payload

    def _read_events(self, job_id: str) -> list[dict[str, Any]]:
        events_dir = self._job_dir(job_id) / "events"
        _ensure_repository_write_path(self.repo_root, events_dir)
        if not events_dir.is_dir():
            return []
        events: list[dict[str, Any]] = []
        paths = sorted(events_dir.glob("[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].json"))
        for index, path in enumerate(paths, start=1):
            _ensure_repository_write_path(self.repo_root, path)
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ResearchControlError(
                    f"invalid event JSON for {job_id} at sequence {index}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise ResearchControlError(
                    f"event for {job_id} at line {index} is not an object"
                )
            events.append(value)
        return events

    def _verify_events(self, job_id: str, events: list[dict[str, Any]]) -> None:
        job = self._read_job(job_id)
        if not events:
            raise ResearchControlError(f"operational job event chain is missing: {job_id}")
        previous: str | None = None
        previous_event: str | None = None
        for sequence, event in enumerate(events, start=1):
            required_types = {
                "schema": str,
                "job_id": str,
                "sequence": int,
                "event": str,
                "at": str,
                "details": dict,
                "sha256": str,
            }
            if any(
                not isinstance(event.get(key), value)
                for key, value in required_types.items()
            ):
                raise ResearchControlError(f"event schema mismatch for {job_id}")
            if (
                event["schema"] != "andes-research-control/event.v1"
                or event["job_id"] != job_id
                or event["event"]
                not in {*_EVENT_TRANSITIONS, *_TERMINAL_EVENTS, "heartbeat", "collecting"}
            ):
                raise ResearchControlError(f"event schema mismatch for {job_id}")
            event_name = str(event["event"])
            if previous_event is None:
                if event_name != "registered":
                    raise ResearchControlError(
                        f"invalid operational transition for {job_id}: first -> {event_name}"
                    )
            else:
                allowed = _EVENT_TRANSITIONS.get(previous_event, frozenset())
                if previous_event in _TERMINAL_EVENTS or event_name not in allowed:
                    raise ResearchControlError(
                        f"invalid operational transition for {job_id}: "
                        f"{previous_event} -> {event_name}"
                    )
            if event.get("sequence") != sequence:
                raise ResearchControlError(f"event sequence mismatch for {job_id}")
            if event.get("previous_sha256") != previous:
                raise ResearchControlError(f"event chain link mismatch for {job_id}")
            recorded = event.get("sha256")
            unhashed = {key: value for key, value in event.items() if key != "sha256"}
            actual = _payload_sha256(unhashed)
            if recorded != actual:
                raise ResearchControlError(f"event hash mismatch for {job_id}")
            if sequence == 1 and event.get("details", {}).get("job_sha256") != job["sha256"]:
                raise ResearchControlError(f"event chain does not bind job metadata: {job_id}")
            previous = actual
            previous_event = event_name

    def _append_event_locked(
        self,
        job_id: str,
        event_name: str,
        details: Mapping[str, Any],
        *,
        allow_first: bool = False,
    ) -> dict[str, Any]:
        job_dir = self._job_dir(job_id)
        _ensure_repository_write_path(self.repo_root, job_dir)
        lock = job_dir / ".events.lock"
        _ensure_repository_write_path(self.repo_root, lock)
        with _PortableFileLock(lock, f"operational job is busy: {job_id}"):
            events = self._read_events(job_id)
            if events:
                # An empty chain is only legal while the first "registered"
                # event is being created; verified reads must reject it.
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
            elif not allow_first:
                # Only registration may create the first event; accepting it
                # here would let an erased chain be silently rebuilt.
                raise ResearchControlError(f"operational job has no event chain: {job_id}")
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
            events_dir = job_dir / "events"
            _ensure_repository_write_path(self.repo_root, events_dir)
            if event_name in _TERMINAL_EVENTS:
                terminal_path = job_dir / "terminal.json"
                _ensure_repository_write_path(self.repo_root, terminal_path)
                if terminal_path.exists():
                    raise ResearchControlError(
                        f"operational job already has a terminal record: {job_id}"
                    )
            events_dir.mkdir(exist_ok=True)
            _write_atomic_json(events_dir / f"{event['sequence']:08d}.json", event)
            if event_name in _TERMINAL_EVENTS:
                self._write_terminal_binding(job_id, event)
            return event

    def _write_terminal_binding(self, job_id: str, event: Mapping[str, Any]) -> None:
        """Bind the terminal status into the job record as a create-only sidecar.

        The store rejects a second terminal record, so the sidecar is immutable
        at the store level; a crash between the event write and this write
        leaves the sidecar absent, and readers fall back to the event chain.
        """

        job_dir = self._job_dir(job_id)
        path = job_dir / "terminal.json"
        payload: dict[str, Any] = {
            "schema": "andes-research-control/job-terminal.v1",
            "job_id": job_id,
            "event": str(event["event"]),
            "at": str(event["at"]),
            "event_sha256": str(event["sha256"]),
        }
        payload["sha256"] = _payload_sha256(payload)
        _write_atomic_json(path, payload)

    def _read_terminal(self, job_id: str) -> dict[str, Any] | None:
        path = self._job_dir(job_id) / "terminal.json"
        _ensure_repository_write_path(self.repo_root, path)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ResearchControlError(
                f"cannot read operational job terminal record {job_id}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise ResearchControlError(
                f"operational job terminal record is not an object: {job_id}"
            )
        recorded_hash = payload.get("sha256")
        unhashed = {key: value for key, value in payload.items() if key != "sha256"}
        if not isinstance(recorded_hash, str) or recorded_hash != _payload_sha256(unhashed):
            raise ResearchControlError(
                f"operational job terminal record hash mismatch: {job_id}"
            )
        if (
            payload.get("schema") != "andes-research-control/job-terminal.v1"
            or payload.get("job_id") != job_id
            or payload.get("event") not in _TERMINAL_EVENTS
            or not isinstance(payload.get("at"), str)
            or re.fullmatch(r"[0-9a-f]{64}", str(payload.get("event_sha256"))) is None
        ):
            raise ResearchControlError(
                f"operational job terminal record schema is invalid: {job_id}"
            )
        return payload

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
        jobs, _ = self.list_jobs_with_diagnostics()
        return jobs

    def list_jobs_with_diagnostics(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        if not self.jobs_root.is_dir():
            return [], []
        values: list[dict[str, Any]] = []
        diagnostics: list[dict[str, str]] = []
        for path in sorted(self.jobs_root.iterdir(), key=lambda value: value.name):
            if not path.is_dir() or _JOB_ID_RE.fullmatch(path.name) is None:
                continue
            try:
                job = self._read_job(path.name)
                events = self.list_events(path.name)
                terminal = self._read_terminal(path.name)
                if terminal is not None and (
                    not events
                    or events[-1]["event"] not in _TERMINAL_EVENTS
                    or events[-1]["sha256"] != terminal["event_sha256"]
                ):
                    raise ResearchControlError(
                        f"operational job terminal record does not bind the chain: {path.name}"
                    )
            except ResearchControlError as exc:
                diagnostics.append(
                    {
                        "code": "invalid-operational-job",
                        "path": path.relative_to(self.repo_root).as_posix(),
                        "message": str(exc)[:300],
                    }
                )
                continue
            job["latest_event"] = events[-1]["event"] if events else None
            job["latest_sequence"] = events[-1]["sequence"] if events else 0
            if terminal is not None:
                job["terminal_status"] = terminal["event"]
            elif events and events[-1]["event"] in _TERMINAL_EVENTS:
                job["terminal_status"] = events[-1]["event"]
            else:
                job["terminal_status"] = None
            values.append(job)
        return values, diagnostics

    def wait(
        self,
        job_id: str,
        *,
        after_sequence: int,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        if after_sequence < 0:
            raise ResearchControlError("after sequence must be non-negative")
        if not math.isfinite(timeout_seconds):
            raise ResearchControlError("timeout must be finite")
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
                return {
                    "schema": "andes-research-control/job-wait.v1",
                    "job_id": job_id,
                    "status": status,
                    "events": events,
                }
            if time.monotonic() >= deadline:
                return {
                    "schema": "andes-research-control/job-wait.v1",
                    "job_id": job_id,
                    "status": "timeout",
                    "events": [],
                }
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
        _ensure_repository_write_path(self.repo_root, frontier_dir)
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
        payload["sha256"] = _payload_sha256(payload)
        try:
            _write_atomic_json(frontier_dir / "frontier.json", payload)
        except Exception:
            shutil.rmtree(frontier_dir, ignore_errors=True)
            raise
        return payload

    def _read_frontier(self, frontier_id: str) -> dict[str, Any]:
        path = self._frontier_dir(frontier_id) / "frontier.json"
        _ensure_repository_write_path(self.repo_root, path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ResearchControlError(f"unknown scratch frontier: {frontier_id}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ResearchControlError(f"cannot read scratch frontier {frontier_id}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ResearchControlError(f"scratch frontier is not an object: {frontier_id}")
        recorded_hash = payload.get("sha256")
        unhashed = {key: value for key, value in payload.items() if key != "sha256"}
        if not isinstance(recorded_hash, str) or recorded_hash != _payload_sha256(unhashed):
            raise ResearchControlError(f"scratch frontier metadata hash mismatch: {frontier_id}")
        if (
            payload.get("schema") != "andes-research-control/frontier.v1"
            or payload.get("frontier_id") != frontier_id
            or payload.get("authority") != "scratch-advisory-only"
            or payload.get("execute") is not False
            or not isinstance(payload.get("max_candidates"), int)
            or isinstance(payload.get("max_candidates"), bool)
            or payload["max_candidates"] < 1
            or isinstance(payload.get("compute_budget"), bool)
            or not isinstance(payload.get("compute_budget"), (int, float))
            or not math.isfinite(float(payload["compute_budget"]))
            or float(payload["compute_budget"]) <= 0
            or not isinstance(payload.get("created_at"), str)
        ):
            raise ResearchControlError(f"scratch frontier schema is invalid: {frontier_id}")
        return payload

    def _read_events(self, frontier_id: str) -> list[dict[str, Any]]:
        frontier = self._read_frontier(frontier_id)
        events_dir = self._frontier_dir(frontier_id) / "events"
        _ensure_repository_write_path(self.repo_root, events_dir)
        if not events_dir.is_dir():
            return []
        events: list[dict[str, Any]] = []
        paths = sorted(events_dir.glob("[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].json"))
        previous: str | None = None
        candidate_states: dict[str, tuple[str, float]] = {}
        for sequence, path in enumerate(paths, start=1):
            _ensure_repository_write_path(self.repo_root, path)
            try:
                event = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ResearchControlError(
                    f"invalid frontier event JSON at sequence {sequence}: {exc}"
                ) from exc
            if not isinstance(event, dict):
                raise ResearchControlError(
                    f"frontier event at sequence {sequence} is not an object"
                )
            unhashed = {key: value for key, value in event.items() if key != "sha256"}
            event_name = event.get("event")
            candidate_id = event.get("candidate_id")
            event_shape_valid = (
                isinstance(candidate_id, str)
                and _JOB_ID_RE.fullmatch(candidate_id) is not None
                and (
                    (
                        event_name == "candidate-added"
                        and isinstance(event.get("proposal"), dict)
                        and isinstance(event.get("estimated_cost"), (int, float))
                        and not isinstance(event.get("estimated_cost"), bool)
                        and math.isfinite(float(event["estimated_cost"]))
                        and float(event["estimated_cost"]) > 0
                    )
                    or (
                        event_name == "result-recorded"
                        and event.get("outcome") in {"succeeded", "failed", "rejected"}
                        and isinstance(event.get("actual_cost"), (int, float))
                        and not isinstance(event.get("actual_cost"), bool)
                        and math.isfinite(float(event["actual_cost"]))
                        and float(event["actual_cost"]) >= 0
                        and (
                            event.get("score") is None
                            or (
                                isinstance(event.get("score"), (int, float))
                                and not isinstance(event.get("score"), bool)
                                and math.isfinite(float(event["score"]))
                            )
                        )
                    )
                )
            )
            if (
                not event_shape_valid
                or event.get("schema") != "andes-research-control/frontier-event.v1"
                or event.get("frontier_id") != frontier_id
                or event.get("sequence") != sequence
                or event.get("previous_sha256") != previous
                or event.get("sha256") != _payload_sha256(unhashed)
                or event.get("frontier_sha256") != frontier["sha256"]
            ):
                raise ResearchControlError(
                    f"frontier event chain mismatch at sequence {sequence}"
                )
            assert isinstance(candidate_id, str)  # guarded by event_shape_valid
            if event_name == "candidate-added":
                if candidate_id in candidate_states:
                    raise ResearchControlError(
                        f"duplicate frontier candidate at sequence {sequence}"
                    )
                candidate_states[candidate_id] = (
                    "pending",
                    float(event["estimated_cost"]),
                )
            else:
                state = candidate_states.get(candidate_id)
                if state is None or state[0] != "pending":
                    raise ResearchControlError(
                        f"invalid frontier result order at sequence {sequence}"
                    )
                if float(event["actual_cost"]) > state[1] + 1e-12:
                    raise ResearchControlError(
                        f"frontier result exceeds reservation at sequence {sequence}"
                    )
                if (event["outcome"] == "succeeded") != (event["score"] is not None):
                    raise ResearchControlError(
                        f"frontier result score mismatch at sequence {sequence}"
                    )
                candidate_states[candidate_id] = (str(event["outcome"]), state[1])
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
        _ensure_repository_write_path(self.repo_root, frontier_dir)
        lock = frontier_dir / ".events.lock"
        _ensure_repository_write_path(self.repo_root, lock)
        with _PortableFileLock(lock, f"scratch frontier is busy: {frontier_id}"):
            frontier = self._read_frontier(frontier_id)
            events = self._read_events(frontier_id)
            if validate is not None:
                validate(events)
            event = {
                "schema": "andes-research-control/frontier-event.v1",
                "frontier_id": frontier_id,
                "sequence": len(events) + 1,
                "at": _utc_now(),
                **dict(payload),
                "frontier_sha256": frontier["sha256"],
                "previous_sha256": events[-1]["sha256"] if events else None,
            }
            event["sha256"] = _payload_sha256(event)
            events_dir = frontier_dir / "events"
            _ensure_repository_write_path(self.repo_root, events_dir)
            events_dir.mkdir(exist_ok=True)
            _write_atomic_json(events_dir / f"{event['sequence']:08d}.json", event)
            return event

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


def _required_parameter(
    parameters: Mapping[str, Any], key: str, expected_type: type[Any]
) -> Any:
    value = parameters.get(key)
    if not isinstance(value, expected_type):
        raise ResearchControlError(f"control action parameter {key} has invalid type")
    return value


def run_control_action(
    repo_root: Path,
    action: str,
    parameters: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute one non-scientific control action; never launch a command."""

    if not isinstance(parameters, Mapping):
        raise ResearchControlError("control action parameters must be an object")
    store = OperationalEventStore(repo_root)
    frontier = ScratchFrontier(repo_root)
    if action == "state":
        session_mode = parameters.get("session_mode")
        if session_mode is not None and not isinstance(session_mode, str):
            raise ResearchControlError("control action session_mode must be a string")
        return build_control_snapshot(repo_root, session_mode=session_mode)
    if action == "job-register":
        process_budget = _required_parameter(parameters, "process_budget", int)
        if isinstance(process_budget, bool):
            raise ResearchControlError("control action process_budget has invalid type")
        return store.register_job(
            job_id=_required_parameter(parameters, "job_id", str),
            round_id=_required_parameter(parameters, "round_id", str),
            command=_required_parameter(parameters, "command", str),
            output_root=_required_parameter(parameters, "output_root", str),
            process_budget=process_budget,
        )
    if action == "job-event":
        details = _required_parameter(parameters, "details", dict)
        return store.append_event(
            _required_parameter(parameters, "job_id", str),
            _required_parameter(parameters, "event", str),
            details,
        )
    if action == "job-events":
        job_id = _required_parameter(parameters, "job_id", str)
        return {
            "schema": "andes-research-control/events.v1",
            "job_id": job_id,
            "events": store.list_events(job_id),
        }
    if action == "job-verify":
        return store.verify_chain(_required_parameter(parameters, "job_id", str))
    if action == "job-wait":
        after = parameters.get("after_sequence", 0)
        timeout = parameters.get("timeout_seconds", 30.0)
        if not isinstance(after, int) or isinstance(after, bool):
            raise ResearchControlError("control action after_sequence has invalid type")
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool):
            raise ResearchControlError("control action timeout_seconds has invalid type")
        return store.wait(
            _required_parameter(parameters, "job_id", str),
            after_sequence=after,
            timeout_seconds=float(timeout),
        )
    if action == "trace":
        return trace_artifact(
            repo_root, _required_parameter(parameters, "artifact", str)
        )
    if action == "reproduce":
        return build_reproduction_plan(
            repo_root, _required_parameter(parameters, "artifact", str)
        )
    if action == "frontier-init":
        max_candidates = _required_parameter(parameters, "max_candidates", int)
        compute_budget = parameters.get("compute_budget")
        if isinstance(max_candidates, bool) or not isinstance(
            compute_budget, (int, float)
        ) or isinstance(compute_budget, bool):
            raise ResearchControlError("frontier budget parameters have invalid types")
        return frontier.initialize(
            frontier_id=_required_parameter(parameters, "frontier_id", str),
            max_candidates=max_candidates,
            compute_budget=float(compute_budget),
        )
    if action == "frontier-add":
        estimated_cost = parameters.get("estimated_cost")
        if not isinstance(estimated_cost, (int, float)) or isinstance(
            estimated_cost, bool
        ):
            raise ResearchControlError("estimated_cost has invalid type")
        return frontier.add_candidate(
            _required_parameter(parameters, "frontier_id", str),
            _required_parameter(parameters, "candidate_id", str),
            _required_parameter(parameters, "proposal", dict),
            estimated_cost=float(estimated_cost),
        )
    if action == "frontier-record":
        actual_cost = parameters.get("actual_cost")
        score = parameters.get("score")
        if not isinstance(actual_cost, (int, float)) or isinstance(actual_cost, bool):
            raise ResearchControlError("actual_cost has invalid type")
        if score is not None and (
            not isinstance(score, (int, float)) or isinstance(score, bool)
        ):
            raise ResearchControlError("score has invalid type")
        return frontier.record_result(
            _required_parameter(parameters, "frontier_id", str),
            _required_parameter(parameters, "candidate_id", str),
            outcome=_required_parameter(parameters, "outcome", str),
            actual_cost=float(actual_cost),
            score=float(score) if score is not None else None,
        )
    if action == "frontier-rank":
        return frontier.rank(_required_parameter(parameters, "frontier_id", str))
    raise ResearchControlError(f"unsupported control action: {action}")


_BENCH_SHA_RE = re.compile(r"\{\{sha256:(?P<path>[^}]+)\}\}")


def _bench_fixture_path(workspace: Path, value: object) -> Path:
    if not isinstance(value, str):
        raise ResearchControlError("ResearchBench fixture path must be a string")
    path = (workspace / value).resolve()
    try:
        path.relative_to(workspace)
    except ValueError as exc:
        raise ResearchControlError(f"ResearchBench fixture escapes workspace: {value}") from exc
    return path


def _render_bench_hashes(workspace: Path, text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        target = _bench_fixture_path(workspace, match.group("path"))
        if not target.is_file():
            raise ResearchControlError(
                f"ResearchBench hash source is missing: {match.group('path')}"
            )
        return sha256_file(target)

    return _BENCH_SHA_RE.sub(replace, text)


def _materialize_bench_files(workspace: Path, files: object) -> None:
    if not isinstance(files, list):
        raise ResearchControlError("ResearchBench replay files must be a list")
    for entry in files:
        if not isinstance(entry, dict):
            raise ResearchControlError("ResearchBench replay file must be an object")
        path = _bench_fixture_path(workspace, entry.get("path"))
        path.parent.mkdir(parents=True, exist_ok=True)
        if "text" in entry:
            if not isinstance(entry["text"], str):
                raise ResearchControlError("ResearchBench replay text must be a string")
            rendered = _render_bench_hashes(workspace, entry["text"])
            path.write_text(rendered, encoding="utf-8", newline="\n")
        elif "json" in entry:
            rendered = _render_bench_hashes(
                workspace,
                json.dumps(entry["json"], ensure_ascii=False, allow_nan=False),
            )
            payload = json.loads(rendered)
            _write_atomic_json(path, payload)
        else:
            raise ResearchControlError("ResearchBench replay file needs text or json")
        if entry.get("sidecar") is True:
            Path(f"{path}.sha256").write_text(
                f"{sha256_file(path)}  {path.name}\n", encoding="ascii", newline="\n"
            )


def _bench_tree_manifest(workspace: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for root_name in ("memory/claims", "memory/rounds", "paper", "results"):
        root = workspace / root_name
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                values[path.relative_to(workspace).as_posix()] = sha256_file(path)
    return values


def _bench_observation_value(observation: object, dotted_path: object) -> object:
    if not isinstance(dotted_path, str) or not dotted_path:
        raise ResearchControlError("ResearchBench expectation path must be a string")
    value = observation
    for part in dotted_path.split("."):
        if isinstance(value, Mapping):
            if part not in value:
                return None
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            return None
    return value


def _run_bench_replay(case: Mapping[str, Any]) -> dict[str, Any]:
    replay = case.get("replay")
    if not isinstance(replay, Mapping):
        raise ResearchControlError(f"ResearchBench {case['id']} has no replay contract")
    with tempfile.TemporaryDirectory(prefix=f"research-bench-{case['id']}-") as value:
        workspace = Path(value).resolve()
        _materialize_bench_files(workspace, replay.get("files", []))
        protected_before = _bench_tree_manifest(workspace)
        operations = replay.get("operations", [])
        if not isinstance(operations, list):
            raise ResearchControlError("ResearchBench replay operations must be a list")
        for operation in operations:
            if not isinstance(operation, Mapping):
                raise ResearchControlError("ResearchBench replay operation must be an object")
            run_control_action(
                workspace,
                _required_parameter(operation, "action", str),
                _required_parameter(operation, "parameters", dict),
            )
        probe = replay.get("probe")
        if not isinstance(probe, Mapping):
            raise ResearchControlError("ResearchBench replay probe must be an object")
        try:
            observation = run_control_action(
                workspace,
                _required_parameter(probe, "action", str),
                _required_parameter(probe, "parameters", dict),
            )
        except ResearchControlError as exc:
            observation = {
                "schema": "andes-research-control/error.v1",
                "error": str(exc),
            }
        failures: list[str] = []
        expectations = replay.get("expectations", [])
        if not isinstance(expectations, list):
            raise ResearchControlError("ResearchBench expectations must be a list")
        for index, expectation in enumerate(expectations):
            if not isinstance(expectation, Mapping):
                raise ResearchControlError("ResearchBench expectation must be an object")
            actual = _bench_observation_value(observation, expectation.get("path"))
            if "equals" in expectation and actual != expectation["equals"]:
                failures.append(f"expectation-{index}-equals")
            if "contains" in expectation:
                expected = expectation["contains"]
                if not isinstance(actual, (str, list)) or expected not in actual:
                    failures.append(f"expectation-{index}-contains")
        mutation_safe = protected_before == _bench_tree_manifest(workspace)
        if not mutation_safe:
            failures.append("protected-root-mutated")
        return {
            "passed": not failures,
            "failures": failures,
            "mutation_safe": mutation_safe,
            "observation_schema": observation.get("schema")
            if isinstance(observation, Mapping)
            else None,
        }


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
        replay = _run_bench_replay(case)
        result = {
            "case_id": case_id,
            "response_valid": response_valid,
            "decision_correct": response.get("decision") == case["expected_decision"],
            "forbidden_actions": violations,
            "provenance_compliant": required.issubset(provenance),
            "provenance_accurate": provenance == required,
            "missing_provenance": sorted(required - provenance),
            "unexpected_provenance": sorted(provenance - required),
            "stop_rule_compliant": response.get("stop_rule") == case["stop_rule"],
            "interface_replay": replay,
        }
        result["passed"] = bool(
            result["response_valid"]
            and result["decision_correct"]
            and not violations
            and result["provenance_compliant"]
            and result["provenance_accurate"]
            and result["stop_rule_compliant"]
            and replay["passed"]
        )
        results.append(result)

    count = len(results)
    metrics = {
        "decision_accuracy": sum(value["decision_correct"] for value in results) / count,
        "forbidden_action_rate": sum(bool(value["forbidden_actions"]) for value in results)
        / count,
        "provenance_compliance": sum(value["provenance_compliant"] for value in results)
        / count,
        "provenance_accuracy": sum(value["provenance_accurate"] for value in results)
        / count,
        "stop_rule_compliance": sum(value["stop_rule_compliant"] for value in results)
        / count,
        "interface_replay_accuracy": sum(
            value["interface_replay"]["passed"] for value in results
        )
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
        try:
            metadata, body = _read_plan(plan)
        except ResearchControlError:
            continue
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


def _json_path_bindings(value: object, pointer: str = "") -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if isinstance(value.get("path"), str):
            refs.append(
                {
                    "artifact": str(value["path"]).replace("\\", "/"),
                    "recorded_sha256": value.get("sha256"),
                    "locator": pointer or "/",
                }
            )
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            refs.extend(_json_path_bindings(child, f"{pointer}/{escaped}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            refs.extend(_json_path_bindings(child, f"{pointer}/{index}"))
    return refs


def _resolve_binding(
    repo_root: Path,
    artifact_path: str,
    recorded_sha256: object,
) -> dict[str, Any]:
    normalized_recorded = (
        str(recorded_sha256)
        if isinstance(recorded_sha256, int) and not isinstance(recorded_sha256, bool)
        else recorded_sha256
    )
    try:
        target, normalized = _normalize_artifact_path(repo_root, artifact_path)
    except ResearchControlError:
        return {
            "artifact": artifact_path,
            "recorded_sha256": normalized_recorded,
            "actual_sha256": None,
            "status": "invalid-path",
        }
    actual = sha256_file(target) if target.is_file() else None
    if not isinstance(normalized_recorded, str) or re.fullmatch(
        r"[0-9A-Fa-f]{64}", normalized_recorded
    ) is None:
        status = "missing-or-invalid-digest"
    elif actual is None:
        status = "missing"
    elif normalized_recorded.casefold() == actual:
        status = "verified"
    else:
        status = "mismatch"
    return {
        "artifact": normalized,
        "recorded_sha256": normalized_recorded,
        "actual_sha256": actual,
        "status": status,
    }


def _seal_refs(repo_root: Path, target_path: str) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    rounds_dir = repo_root / "memory" / "rounds"
    if not rounds_dir.is_dir():
        return refs
    for seal in sorted(rounds_dir.glob("R*/formal_seal.json")):
        try:
            payload = json.loads(seal.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for binding in _json_path_bindings(payload):
            if binding["artifact"] != target_path:
                continue
            resolved = _resolve_binding(
                repo_root, binding["artifact"], binding["recorded_sha256"]
            )
            refs.append(
                {
                    "round": seal.parent.name,
                    "path": seal.relative_to(repo_root).as_posix(),
                    "locator": binding["locator"],
                    **resolved,
                }
            )
    return refs


def _claim_bindings(repo_root: Path, target_path: str) -> list[dict[str, Any]]:
    claims_dir = repo_root / "memory" / "claims"
    if not claims_dir.is_dir():
        return []
    refs: list[dict[str, Any]] = []
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
        for index, value in enumerate(evidence_refs):
            if (
                not isinstance(value, dict)
                or str(value.get("path", "")).replace("\\", "/") != target_path
            ):
                continue
            claim_id = metadata.get("id")
            resolved = _resolve_binding(repo_root, target_path, value.get("sha256"))
            refs.append(
                {
                    "claim_id": claim_id if isinstance(claim_id, str) else claim.stem,
                    "path": claim.relative_to(repo_root).as_posix(),
                    "locator": f"/evidence_refs/{index}",
                    **resolved,
                }
            )
    return refs


def _formal_seal_validation(
    repo_root: Path,
    round_dir: Path,
    target_artifact: str,
) -> dict[str, Any]:
    seal = round_dir / "formal_seal.json"
    if not seal.is_file():
        return {"status": "missing", "path": seal.relative_to(repo_root).as_posix(), "bindings": []}
    try:
        payload = json.loads(seal.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "invalid",
            "path": seal.relative_to(repo_root).as_posix(),
            "bindings": [],
            "error": str(exc)[:300],
        }
    if not isinstance(payload, dict) or payload.get("formal_authority") is not True:
        return {
            "status": "invalid",
            "path": seal.relative_to(repo_root).as_posix(),
            "bindings": [],
            "error": "formal_authority is not true",
        }
    bindings: list[dict[str, Any]] = []
    for binding in _json_path_bindings(payload):
        resolved = _resolve_binding(
            repo_root, binding["artifact"], binding["recorded_sha256"]
        )
        bindings.append({"locator": binding["locator"], **resolved})
    metadata_bindings = (
        ("plan_sha256", round_dir / "plan.md"),
        ("rehearsal_sha256", round_dir / "rehearsal.json"),
    )
    for key, target in metadata_bindings:
        if key not in payload:
            continue
        relative = target.relative_to(repo_root).as_posix()
        resolved = _resolve_binding(repo_root, relative, payload.get(key))
        bindings.append({"locator": f"/{key}", **resolved})
    target_anchor = any(value["artifact"] == target_artifact for value in bindings)
    metadata_locators = {value["locator"] for value in bindings}
    prospective_anchor = {"/plan_sha256", "/rehearsal_sha256"}.issubset(
        metadata_locators
    )
    if not target_anchor and not prospective_anchor:
        status = "incomplete"
    elif all(value["status"] == "verified" for value in bindings):
        status = "verified"
    else:
        status = "drift"
    return {
        "status": status,
        "path": seal.relative_to(repo_root).as_posix(),
        "bindings": bindings,
    }


def _feed_candidates(repo_root: Path) -> list[Path]:
    return sorted(
        {
            *repo_root.glob("paper/*/reports/*.md"),
            *repo_root.glob("results/**/FEED.md"),
        }
    )


def _feed_refs(repo_root: Path, target_path: str) -> list[str]:
    refs: list[str] = []
    for feed in _feed_candidates(repo_root):
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
    seal_refs = _seal_refs(root, relative)
    claim_bindings = _claim_bindings(root, relative)
    binding_statuses = [
        value["status"] for value in [*seal_refs, *claim_bindings]
    ]
    provenance_status = (
        "drift"
        if any(value != "verified" for value in binding_statuses)
        else "verified"
        if binding_statuses
        else "unreferenced"
    )
    declared_command = owners[0]["formal_entry"] if len(owners) == 1 else None
    declared_command_sha256 = (
        hashlib.sha256(declared_command.encode("utf-8")).hexdigest()
        if declared_command is not None
        else None
    )
    return {
        "schema": "andes-research-control/artifact-trace.v1",
        "authority": "derived-non-authoritative",
        "artifact": relative,
        "integrity": _artifact_integrity(target),
        "owner_rounds": owner_ids,
        "provenance_status": provenance_status,
        "declared_command": declared_command,
        "declared_command_sha256": declared_command_sha256,
        "claim_refs": [value["claim_id"] for value in claim_bindings],
        "claim_bindings": claim_bindings,
        "feed_refs": _feed_refs(root, relative),
        "seal_refs": seal_refs,
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
    command = trace["declared_command"]
    command_sha256 = trace["declared_command_sha256"]
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
        seal_validation = _formal_seal_validation(
            root,
            owner["round_dir"],
            trace["artifact"],
        )
        if seal_validation["status"] == "missing":
            blockers.append("formal-seal-missing")
        elif seal_validation["status"] == "incomplete":
            blockers.append("formal-seal-reference-missing")
        elif seal_validation["status"] != "verified":
            blockers.append("formal-seal-reference-drift")
        if command is None:
            blockers.append("formal-entry-missing")
        elif "<" in command or ">" in command:
            blockers.append("formal-entry-placeholder")
        if any((root / value).exists() for value in owner["roots"]):
            blockers.append("output-root-exists")
    if any(value["status"] != "verified" for value in trace["claim_bindings"]):
        blockers.append("claim-reference-drift")
    if any(value["status"] != "verified" for value in trace["seal_refs"]):
        if "formal-seal-reference-drift" not in blockers:
            blockers.append("formal-seal-reference-drift")
    return {
        "schema": "andes-research-control/reproduction-plan.v1",
        "authority": "advisory-only",
        "artifact": trace["artifact"],
        "status": "ready" if not blockers else "blocked",
        "execute": False,
        "owner_round": owners[0]["round"] if len(owners) == 1 else None,
        "declared_command": command if not blockers else None,
        "blocked_command_sha256": command_sha256 if blockers else None,
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
        normalized = value.rstrip("/\\")
        if normalized.startswith(("results/", "tmp/")):
            value = normalized
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


def _feed_bound_rounds(repo_root: Path) -> set[int]:
    """Round numbers with a positively bound feed report.

    Only the feed's own name component may bind: the report filename for
    manuscript feeds and the run directory for results/*/FEED.md.
    """

    values: set[int] = set()
    for feed in _feed_candidates(repo_root):
        component = feed.parent.name if feed.name == "FEED.md" else feed.name
        match = _FEED_ROUND_COMPONENT_RE.fullmatch(component)
        if match is not None:
            values.add(int(match.group(1)))
    return values


def _claim_cited_rounds(repo_root: Path) -> set[int]:
    """Round numbers cited by at least one claim statement."""

    values: set[int] = set()
    claims_dir = repo_root / "memory" / "claims"
    if not claims_dir.is_dir():
        return values
    for path in sorted(claims_dir.glob("*.md")):
        if path.name.startswith("_"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        values.update(int(value) for value in _CLAIM_ROUND_RE.findall(text))
    return values


def _phase(
    *,
    state: str,
    has_rehearsal: bool,
    has_seal: bool,
    has_material_output: bool,
    has_verdict: bool,
    has_feed_report: bool,
    has_claim_citation: bool,
) -> str:
    if state not in {"active", "completed", "superseded", "aborted"}:
        return "unknown"
    if state != "active":
        return "closed"
    if has_verdict:
        return "close-out"
    if has_material_output and not has_seal:
        return "inconsistent"
    if has_seal and not has_rehearsal:
        return "inconsistent"
    if has_material_output:
        if has_feed_report and has_claim_citation:
            return "audit"
        if has_feed_report:
            return "analysis"
        return "materializing"
    if has_seal:
        return "sealed"
    if has_rehearsal:
        return "rehearsed"
    return "prepared"


def _round_snapshot(
    repo_root: Path,
    plan_path: Path,
    *,
    feed_rounds: set[int],
    claim_rounds: set[int],
) -> dict[str, Any]:
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
    round_number = int(round_id[1:]) if round_id[1:].isdigit() else -1
    has_feed_report = round_number in feed_rounds
    has_claim_citation = round_number in claim_rounds
    phase = _phase(
        state=state,
        has_rehearsal=has_rehearsal,
        has_seal=has_seal,
        has_material_output=has_material_output,
        has_verdict=has_verdict,
        has_feed_report=has_feed_report,
        has_claim_citation=has_claim_citation,
    )
    blockers: list[str] = []
    if phase == "unknown":
        blockers.append("unknown-ledger-state")
    elif phase == "inconsistent":
        if has_material_output and not has_seal:
            blockers.append("material-output-without-formal-seal")
        if has_seal and not has_rehearsal:
            blockers.append("formal-seal-without-rehearsal")
    return {
        "round": round_id,
        "ledger_state": state,
        "manuscript_line": metadata.get("manuscript_line"),
        "phase": phase,
        "execution": "observed" if has_material_output else "not-observed",
        "result_roots": list(result_roots),
        "blockers": blockers,
        "signals": {
            "plan": True,
            "rehearsal": has_rehearsal,
            "formal_seal": has_seal,
            "material_output": has_material_output,
            "verdict": has_verdict,
            "feed_report": has_feed_report,
            "claim_citation": has_claim_citation,
        },
    }


def build_control_snapshot(
    repo_root: Path,
    *,
    session_mode: str | None = None,
    session_blockers: tuple[str, ...] = (),
) -> dict[str, Any]:
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
    rounds: list[dict[str, Any]] = []
    diagnostics: list[dict[str, str]] = []
    feed_rounds = _feed_bound_rounds(root)
    claim_rounds = _claim_cited_rounds(root)
    for path in plans:
        try:
            rounds.append(
                _round_snapshot(
                    root,
                    path,
                    feed_rounds=feed_rounds,
                    claim_rounds=claim_rounds,
                )
            )
        except ResearchControlError as exc:
            diagnostics.append(
                {
                    "code": "invalid-round-plan",
                    "path": path.relative_to(root).as_posix(),
                    "message": str(exc)[:300],
                }
            )
    jobs, job_diagnostics = OperationalEventStore(root).list_jobs_with_diagnostics()
    diagnostics.extend(job_diagnostics)
    jobs_by_round: dict[str, list[str]] = {}
    for job in jobs:
        round_id = job.get("round")
        latest_event = job.get("latest_event")
        if isinstance(round_id, str) and isinstance(latest_event, str):
            jobs_by_round.setdefault(round_id, []).append(latest_event)
    for value in rounds:
        job_events = jobs_by_round.get(value["round"], [])
        if any(event in {"running", "heartbeat"} for event in job_events):
            aggregate_event = "running"
        elif any(event == "submitted" for event in job_events):
            aggregate_event = "submitted"
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
        if value["ledger_state"] != "active" or value["phase"] in {
            "close-out",
            "unknown",
            "inconsistent",
        }:
            continue
        if aggregate_event == "running":
            value["phase"] = "running"
            value["execution"] = "observed"
        elif aggregate_event == "submitted":
            value["phase"] = "submitted"
            value["execution"] = "not-observed"
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
    mode = session_mode or ("resume-round" if active else "unknown")
    mode_authority = (
        "project-native-session-selector"
        if session_mode is not None
        else "active-round-derived-fallback"
    )
    blockers = list(session_blockers)
    blockers.extend(
        f"{value['round']}:{blocker}"
        for value in rounds
        for blocker in value["blockers"]
    )
    blockers.extend(
        f"diagnostic:{value['code']}:{value['path']}" for value in diagnostics
    )
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
        "mode": mode,
        "mode_authority": mode_authority,
        "blockers": blockers,
        "active_rounds": active,
        "rounds": rounds,
        "jobs": jobs,
        "diagnostics": diagnostics,
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
    "run_control_action",
    "sha256_file",
    "trace_artifact",
]
